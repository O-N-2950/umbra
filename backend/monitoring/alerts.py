"""
MATCHO — Alert Service
Envoie des alertes email à l'admin quand un service tombe ou récupère.

Leçon PEP's #1 : Kill switch + anti-doublon.
Leçon PEP's #10 : JAMAIS d'erreur silencieuse dans les notifications.

© 2026 PEP's Swiss SA
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger("umbra.alerts")


class AlertService:
    """
    Service d'alertes admin.
    
    Protections (leçons PEP's) :
    - Anti-doublon : max 1 alerte par service par 30 min
    - Kill switch : ALERT_ENABLED=false désactive tout
    - Log AVANT envoi : on trace même si l'envoi échoue
    """

    # Anti-doublon : 1 alerte max par service par 30 min
    COOLDOWN_SECONDS = 1800

    def __init__(self):
        self.admin_email = os.getenv("ADMIN_ALERT_EMAIL", "olivier@peps.swiss")
        self.enabled = os.getenv("ALERT_ENABLED", "true").lower() == "true"
        self._last_alert_time: Dict[str, float] = {}

    def _can_send(self, key: str) -> bool:
        """Anti-doublon : vérifie le cooldown"""
        now = time.time()
        last = self._last_alert_time.get(key, 0)
        if now - last < self.COOLDOWN_SECONDS:
            logger.info(f"[ALERT] Cooldown actif pour '{key}' ({int(now - last)}s/{self.COOLDOWN_SECONDS}s)")
            return False
        return True

    def _record_sent(self, key: str):
        """Enregistre l'heure d'envoi pour l'anti-doublon"""
        self._last_alert_time[key] = time.time()

    async def send_service_down_alert(
        self,
        service: str,
        message: str,
        failure_count: int,
        duration_minutes: float,
    ):
        """Alerte : un service est DOWN"""
        key = f"down:{service}"
        
        # Leçon PEP's #1 : Anti-doublon AVANT envoi
        if not self._can_send(key):
            return
        
        # Leçon PEP's #10 : Log AVANT envoi
        logger.error(
            f"🚨 [ALERT] Envoi alerte DOWN: {service} "
            f"({failure_count} échecs, {duration_minutes:.0f} min)"
        )
        
        subject = f"🔴 MATCHO — {service} DOWN"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #DC2626; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0;">🔴 Service DOWN — {service}</h2>
            </div>
            <div style="background: #FEF2F2; padding: 20px; border-radius: 0 0 8px 8px;">
                <p><strong>Service :</strong> {service}</p>
                <p><strong>Message :</strong> {message}</p>
                <p><strong>Échecs consécutifs :</strong> {failure_count}</p>
                <p><strong>Durée :</strong> {duration_minutes:.0f} minutes</p>
                <p><strong>Heure :</strong> {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}</p>
                <hr style="border: 1px solid #FCA5A5;">
                <p style="color: #666; font-size: 13px;">
                    MATCHO Crash Monitor — PEP's Swiss SA
                </p>
            </div>
        </div>
        """
        
        await self._send_email(subject, html)
        self._record_sent(key)

    async def send_service_recovery_alert(
        self,
        service: str,
        duration_minutes: float,
    ):
        """Notification : un service a récupéré"""
        key = f"recovery:{service}"
        
        if not self._can_send(key):
            return
        
        logger.info(f"🟢 [ALERT] Envoi recovery: {service} (down {duration_minutes:.0f} min)")
        
        subject = f"🟢 MATCHO — {service} RECOVERED"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #059669; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0;">🟢 Service Récupéré — {service}</h2>
            </div>
            <div style="background: #ECFDF5; padding: 20px; border-radius: 0 0 8px 8px;">
                <p><strong>Service :</strong> {service}</p>
                <p><strong>Temps d'indisponibilité :</strong> {duration_minutes:.0f} minutes</p>
                <p><strong>Récupéré à :</strong> {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}</p>
                <hr style="border: 1px solid #6EE7B7;">
                <p style="color: #666; font-size: 13px;">
                    MATCHO Crash Monitor — PEP's Swiss SA
                </p>
            </div>
        </div>
        """
        
        await self._send_email(subject, html)
        self._record_sent(key)

    async def send_startup_report(self, health_report: Dict):
        """Envoie le rapport de santé au démarrage (si problèmes)"""
        status = health_report.get("status", "unknown")
        
        if status == "healthy":
            return  # Pas d'email si tout va bien
        
        logger.warning(f"[ALERT] Envoi rapport startup: {status}")
        
        checks_html = ""
        for name, check in health_report.get("checks", {}).items():
            icon = "✅" if check["status"] == "ok" else ("⚠️" if check["status"] == "degraded" else "❌")
            checks_html += f"<tr><td>{icon} {name}</td><td>{check['status']}</td><td>{check.get('message', '')}</td></tr>"
        
        subject = f"⚠️ MATCHO Startup — {status} ({health_report.get('score', '?')})"
        html = f"""
        <div style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #D97706; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0;">⚠️ MATCHO Démarrage — {status}</h2>
            </div>
            <div style="background: #FFFBEB; padding: 20px; border-radius: 0 0 8px 8px;">
                <p><strong>Score :</strong> {health_report.get('score', '?')}</p>
                <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                    <tr style="background: #FEF3C7;">
                        <th style="padding: 8px; text-align: left;">Service</th>
                        <th style="padding: 8px;">Status</th>
                        <th style="padding: 8px; text-align: left;">Message</th>
                    </tr>
                    {checks_html}
                </table>
                <hr style="border: 1px solid #FCD34D;">
                <p style="color: #666; font-size: 13px;">
                    MATCHO Health Check — PEP's Swiss SA
                </p>
            </div>
        </div>
        """
        
        await self._send_email(subject, html)

    async def _send_email(self, subject: str, html: str):
        """
        Envoie un email via Resend.
        
        Protections PEP's :
        - Kill switch vérifié
        - Lazy import (Leçon #11 : import bloquant)
        - Log l'erreur si envoi échoue (Leçon #10)
        """
        if not self.enabled:
            logger.info(f"[ALERT] Kill switch actif — email non envoyé: {subject}")
            return
        
        try:
            # Leçon PEP's #11 : Lazy import pour ne pas bloquer le démarrage
            import resend
            
            api_key = os.getenv("RESEND_API_KEY", "")
            if not api_key:
                logger.warning("[ALERT] RESEND_API_KEY manquante — email non envoyé")
                return
            
            resend.api_key = api_key
            
            resend.Emails.send({
                "from": "UMBRA Monitor <noreply@umbra.ch>",
                "to": [self.admin_email],
                "subject": subject,
                "html": html,
            })
            
            logger.info(f"[ALERT] ✅ Email envoyé: {subject}")
        
        except Exception as e:
            # Leçon PEP's #10 : JAMAIS avaler l'erreur de notification
            logger.error(f"[ALERT] ❌ Échec envoi email: {e}", exc_info=True)
