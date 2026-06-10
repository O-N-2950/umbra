"""
MATCHO — Crash Monitor
Leçon PEP's : Le crash monitor de PEP's a été construit APRÈS les catastrophes.
MATCHO l'a dès le jour 1.

Vérifie la santé toutes les 5 minutes en arrière-plan.
Si 2 échecs consécutifs → alerte email admin.
Si recovery après incident → notification de recovery.

© 2026 PEP's Swiss SA
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from monitoring.health_check import HealthChecker, ServiceStatus

logger = logging.getLogger("umbra.monitor")


@dataclass
class Incident:
    """Un incident détecté par le crash monitor"""
    service: str
    started_at: datetime
    resolved_at: Optional[datetime] = None
    failure_count: int = 0
    last_message: str = ""
    alerted: bool = False

    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None

    @property
    def duration_minutes(self) -> float:
        end = self.resolved_at or datetime.utcnow()
        return (end - self.started_at).total_seconds() / 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "service": self.service,
            "started_at": self.started_at.isoformat() + "Z",
            "resolved_at": self.resolved_at.isoformat() + "Z" if self.resolved_at else None,
            "failure_count": self.failure_count,
            "duration_minutes": round(self.duration_minutes, 1),
            "last_message": self.last_message,
            "alerted": self.alerted,
        }


class CrashMonitor:
    """
    Surveillance périodique des services MATCHO.
    
    Usage:
        monitor = CrashMonitor(health_checker, alert_service)
        asyncio.create_task(monitor.start())  # Lance en arrière-plan
    """

    CHECK_INTERVAL = 300  # 5 minutes
    ALERT_AFTER_FAILURES = 2  # Alerte après 2 échecs consécutifs (10 min)
    MAX_INCIDENTS_HISTORY = 100

    def __init__(self, health_checker: HealthChecker, alert_service=None):
        self.checker = health_checker
        self.alerts = alert_service
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # État
        self.active_incidents: Dict[str, Incident] = {}
        self.incident_history: List[Incident] = []
        self._consecutive_failures: Dict[str, int] = {}

    async def start(self):
        """Démarre la surveillance en arrière-plan"""
        if self._running:
            logger.warning("[MONITOR] Déjà en cours d'exécution")
            return
        
        self._running = True
        logger.info(f"🔍 Crash Monitor démarré (intervalle: {self.CHECK_INTERVAL}s)")
        
        # Attendre 60s avant le premier check (laisser l'app démarrer)
        await asyncio.sleep(60)
        
        while self._running:
            try:
                await self._run_check()
            except Exception as e:
                # Leçon PEP's #10 : JAMAIS avaler les erreurs
                logger.error(f"[MONITOR] ❌ Erreur dans le check: {e}", exc_info=True)
            
            await asyncio.sleep(self.CHECK_INTERVAL)

    def stop(self):
        """Arrête la surveillance"""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("🔍 Crash Monitor arrêté")

    async def _run_check(self):
        """Exécute un cycle de vérification"""
        report = await self.checker.full_check()
        
        for service_name, check_data in report["checks"].items():
            status = check_data["status"]
            message = check_data.get("message", "")
            
            if status == "down":
                await self._handle_failure(service_name, message)
            elif status == "ok":
                await self._handle_recovery(service_name)
            # "degraded" : on log mais pas d'incident

    async def _handle_failure(self, service: str, message: str):
        """Gère un échec de service"""
        self._consecutive_failures[service] = self._consecutive_failures.get(service, 0) + 1
        count = self._consecutive_failures[service]
        
        if service not in self.active_incidents:
            # Nouvel incident
            incident = Incident(
                service=service,
                started_at=datetime.utcnow(),
                failure_count=1,
                last_message=message,
            )
            self.active_incidents[service] = incident
            logger.warning(f"🔴 [MONITOR] Incident ouvert: {service} — {message}")
        else:
            # Incident existant
            incident = self.active_incidents[service]
            incident.failure_count += 1
            incident.last_message = message
        
        # Alerter après N échecs consécutifs
        incident = self.active_incidents[service]
        if count >= self.ALERT_AFTER_FAILURES and not incident.alerted:
            incident.alerted = True
            logger.error(
                f"🚨 [MONITOR] ALERTE: {service} DOWN depuis "
                f"{incident.duration_minutes:.0f} min ({count} échecs)"
            )
            if self.alerts:
                try:
                    await self.alerts.send_service_down_alert(
                        service=service,
                        message=message,
                        failure_count=count,
                        duration_minutes=incident.duration_minutes,
                    )
                except Exception as e:
                    # Leçon PEP's #10 : Logger même les erreurs de notification
                    logger.error(f"[MONITOR] ❌ Échec envoi alerte: {e}")

    async def _handle_recovery(self, service: str):
        """Gère la recovery d'un service"""
        if service in self.active_incidents:
            incident = self.active_incidents.pop(service)
            incident.resolved_at = datetime.utcnow()
            
            # Archiver
            self.incident_history.append(incident)
            if len(self.incident_history) > self.MAX_INCIDENTS_HISTORY:
                self.incident_history = self.incident_history[-self.MAX_INCIDENTS_HISTORY:]
            
            logger.info(
                f"🟢 [MONITOR] Recovery: {service} "
                f"(down pendant {incident.duration_minutes:.0f} min)"
            )
            
            # Notification de recovery
            if incident.alerted and self.alerts:
                try:
                    await self.alerts.send_service_recovery_alert(
                        service=service,
                        duration_minutes=incident.duration_minutes,
                    )
                except Exception as e:
                    logger.error(f"[MONITOR] ❌ Échec envoi recovery: {e}")
        
        # Reset compteur
        self._consecutive_failures[service] = 0

    # ══════════════════════════════════════════════════════
    # API pour l'admin dashboard
    # ══════════════════════════════════════════════════════

    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut actuel du monitoring"""
        return {
            "running": self._running,
            "check_interval_seconds": self.CHECK_INTERVAL,
            "active_incidents": {
                name: inc.to_dict() for name, inc in self.active_incidents.items()
            },
            "recent_incidents": [
                inc.to_dict() for inc in self.incident_history[-10:]
            ],
            "last_health_report": self.checker.get_last_report(),
        }
