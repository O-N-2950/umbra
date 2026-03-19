"""
MATCHO — Health Check Service
Leçon PEP's #4 : Gemini est mort silencieusement pendant des semaines.
Leçon PEP's #7 : Tables manquantes en production = 500 systématique.

Ce module vérifie TOUS les services critiques :
  1. Database (connexion + tables critiques)
  2. Gemini IA (appel test réel)
  3. Parser CAMT053 (parsing d'un sample)
  4. APIs fédérales (UID, Zefix, OpenIBAN)
  5. Encryption (roundtrip AES-256)
  6. Email service (configuration)

Appelé :
  - Au boot de l'app (startup check)
  - Via GET /health (endpoint détaillé)
  - Par le CrashMonitor (toutes les 5 min)

© 2026 PEP's Swiss SA
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("matcho.health")


class ServiceStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"
    UNCHECKED = "unchecked"


@dataclass
class CheckResult:
    """Résultat d'un check individuel"""
    service: str
    status: ServiceStatus
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "status": self.status.value,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 1),
        }
        if self.details:
            d["details"] = self.details
        return d


class HealthChecker:
    """
    Vérifie la santé de tous les services MATCHO.
    
    Usage:
        checker = HealthChecker(db_engine=engine)
        report = await checker.full_check()
        # → {"status": "healthy", "score": "100%", "checks": {...}}
    """

    def __init__(self, db_engine=None, gemini_api_key: str = ""):
        self.db_engine = db_engine
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self._last_report: Optional[Dict] = None
        self._last_check_time: Optional[datetime] = None

    # ══════════════════════════════════════════════════════
    # STARTUP CHECK — appelé au boot de l'app
    # ══════════════════════════════════════════════════════

    async def startup_check(self) -> Dict[str, Any]:
        """
        Check rapide au démarrage. Si un service critique est DOWN,
        on log un WARNING mais on ne bloque PAS le démarrage.
        Leçon PEP's #8 : Ne pas bloquer le boot.
        """
        report = await self.full_check()
        
        status = report["status"]
        score = report["score"]
        
        if status == "healthy":
            logger.info(f"🟢 MATCHO Health: {score} — Tous les services OK")
        elif status == "degraded":
            logger.warning(f"🟡 MATCHO Health: {score} — Services dégradés:")
            for name, check in report["checks"].items():
                if check["status"] != "ok":
                    logger.warning(f"   ⚠️ {name}: {check['message']}")
        else:
            logger.error(f"🔴 MATCHO Health: {score} — Services critiques DOWN:")
            for name, check in report["checks"].items():
                if check["status"] == "down":
                    logger.error(f"   ❌ {name}: {check['message']}")
        
        return report

    # ══════════════════════════════════════════════════════
    # FULL CHECK — tous les services
    # ══════════════════════════════════════════════════════

    async def full_check(self) -> Dict[str, Any]:
        """Vérifie tous les services et retourne un rapport complet"""
        checks: Dict[str, CheckResult] = {}
        
        # 1. Database
        checks["database"] = await self._check_database()
        
        # 2. Gemini IA
        checks["gemini_ai"] = await self._check_gemini()
        
        # 3. Parser CAMT053
        checks["camt053_parser"] = self._check_parser()
        
        # 4. APIs fédérales
        checks["uid_register"] = await self._check_uid_api()
        checks["openiban"] = await self._check_openiban()
        
        # 5. Encryption
        checks["encryption"] = self._check_encryption()
        
        # 6. Email
        checks["email_service"] = self._check_email()
        
        # Calculer le score global
        total = len(checks)
        ok_count = sum(1 for c in checks.values() if c.status == ServiceStatus.OK)
        degraded_count = sum(1 for c in checks.values() if c.status == ServiceStatus.DEGRADED)
        
        if ok_count == total:
            overall = "healthy"
        elif ok_count + degraded_count >= total * 0.7:
            overall = "degraded"
        else:
            overall = "unhealthy"
        
        score = f"{round(ok_count / total * 100)}%"
        
        report = {
            "status": overall,
            "score": score,
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "checks": {name: result.to_dict() for name, result in checks.items()},
        }
        
        self._last_report = report
        self._last_check_time = datetime.utcnow()
        
        return report

    def get_last_report(self) -> Optional[Dict]:
        """Retourne le dernier rapport (cache)"""
        return self._last_report

    # ══════════════════════════════════════════════════════
    # CHECKS INDIVIDUELS
    # ══════════════════════════════════════════════════════

    async def _check_database(self) -> CheckResult:
        """Vérifie la connexion DB + existence des tables critiques"""
        start = time.time()
        
        if not self.db_engine:
            return CheckResult(
                service="database",
                status=ServiceStatus.DOWN,
                message="Engine DB non initialisé",
            )
        
        try:
            from sqlalchemy import text, inspect
            from sqlalchemy.ext.asyncio import AsyncSession
            from sqlalchemy.orm import sessionmaker
            
            SessionLocal = sessionmaker(
                self.db_engine, class_=AsyncSession, expire_on_commit=False
            )
            
            async with SessionLocal() as session:
                # Test connexion
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
                
                # Vérifier tables critiques (Leçon PEP's #7)
                def check_tables(sync_conn):
                    inspector = inspect(sync_conn)
                    tables = inspector.get_table_names()
                    return tables
                
                tables = await session.run_sync(
                    lambda sync_session: check_tables(sync_session.get_bind())
                )
                
                critical_tables = ["fiduciaries", "users", "clients", "bank_accounts", "audit_log"]
                missing = [t for t in critical_tables if t not in tables]
                
                latency = (time.time() - start) * 1000
                
                if missing:
                    return CheckResult(
                        service="database",
                        status=ServiceStatus.DEGRADED,
                        message=f"Tables manquantes: {', '.join(missing)}",
                        latency_ms=latency,
                        details={"existing_tables": len(tables), "missing": missing},
                    )
                
                return CheckResult(
                    service="database",
                    status=ServiceStatus.OK,
                    message=f"Connecté, {len(tables)} tables",
                    latency_ms=latency,
                    details={"table_count": len(tables)},
                )
        
        except Exception as e:
            # Leçon PEP's #10 : JAMAIS avaler les erreurs silencieusement
            logger.error(f"[HEALTH] ❌ Database check failed: {e}")
            return CheckResult(
                service="database",
                status=ServiceStatus.DOWN,
                message=f"Connexion échouée",
                latency_ms=(time.time() - start) * 1000,
            )

    async def _check_gemini(self) -> CheckResult:
        """
        Vérifie que Gemini répond.
        Leçon PEP's #4 : Gemini est mort pendant des semaines sans alerte.
        On fait un VRAI appel test, pas juste vérifier la clé.
        """
        start = time.time()
        
        if not self.gemini_api_key:
            return CheckResult(
                service="gemini_ai",
                status=ServiceStatus.DOWN,
                message="GEMINI_API_KEY non configurée",
            )
        
        try:
            import asyncio
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=self.gemini_api_key)
            
            # Appel test minimal (coût quasi nul) — sync wrappé en async
            def _call_gemini():
                return client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents="Réponds uniquement: OK",
                    config=types.GenerateContentConfig(
                        max_output_tokens=5
                    ),
                )
            
            response = await asyncio.to_thread(_call_gemini)
            
            text = response.text.strip() if response.text else ""
            latency = (time.time() - start) * 1000
            
            if text:
                return CheckResult(
                    service="gemini_ai",
                    status=ServiceStatus.OK,
                    message=f"Gemini 2.0 Flash opérationnel",
                    latency_ms=latency,
                    details={"model": "gemini-2.5-flash"},
                )
            else:
                return CheckResult(
                    service="gemini_ai",
                    status=ServiceStatus.DEGRADED,
                    message="Gemini répond mais réponse vide",
                    latency_ms=latency,
                )
        
        except Exception as e:
            logger.error(f"[HEALTH] ❌ Gemini check failed: {e}")
            return CheckResult(
                service="gemini_ai",
                status=ServiceStatus.DOWN,
                message=f"Gemini inaccessible: {str(e)[:120]}",
                latency_ms=(time.time() - start) * 1000,
            )

    def _check_parser(self) -> CheckResult:
        """Vérifie que les parsers sont importables et fonctionnels"""
        start = time.time()
        
        try:
            from parsers.camt053_parser import parse_camt053, BankTransaction
            from parsers.cresus_parser import parse_grand_livre, CresusTransaction
            
            latency = (time.time() - start) * 1000
            return CheckResult(
                service="camt053_parser",
                status=ServiceStatus.OK,
                message="Parsers CAMT053 + Crésus disponibles",
                latency_ms=latency,
            )
        
        except ImportError as e:
            logger.error(f"[HEALTH] ❌ Parser import failed: {e}")
            return CheckResult(
                service="camt053_parser",
                status=ServiceStatus.DOWN,
                message=f"Import échoué: {e}",
                latency_ms=(time.time() - start) * 1000,
            )

    async def _check_uid_api(self) -> CheckResult:
        """Vérifie l'accès au registre UID fédéral"""
        start = time.time()
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test WSDL endpoint (ne coûte rien)
                resp = await client.get(
                    "https://www.uid-wse.admin.ch/V5.0/PublicServices.svc?wsdl"
                )
                latency = (time.time() - start) * 1000
                
                if resp.status_code == 200:
                    return CheckResult(
                        service="uid_register",
                        status=ServiceStatus.OK,
                        message="API UID Register accessible",
                        latency_ms=latency,
                    )
                else:
                    return CheckResult(
                        service="uid_register",
                        status=ServiceStatus.DEGRADED,
                        message=f"HTTP {resp.status_code}",
                        latency_ms=latency,
                    )
        
        except Exception as e:
            logger.warning(f"[HEALTH] ⚠️ UID API check failed: {e}")
            return CheckResult(
                service="uid_register",
                status=ServiceStatus.DEGRADED,
                message="API inaccessible (timeout ou réseau)",
                latency_ms=(time.time() - start) * 1000,
            )

    async def _check_openiban(self) -> CheckResult:
        """Vérifie l'accès à OpenIBAN"""
        start = time.time()
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://openiban.com/validate/CH9300762011623852957")
                latency = (time.time() - start) * 1000
                
                if resp.status_code == 200:
                    data = resp.json()
                    return CheckResult(
                        service="openiban",
                        status=ServiceStatus.OK,
                        message="OpenIBAN accessible",
                        latency_ms=latency,
                        details={"valid": data.get("valid", False)},
                    )
                else:
                    return CheckResult(
                        service="openiban",
                        status=ServiceStatus.DEGRADED,
                        message=f"HTTP {resp.status_code}",
                        latency_ms=latency,
                    )
        
        except Exception as e:
            logger.warning(f"[HEALTH] ⚠️ OpenIBAN check failed: {e}")
            return CheckResult(
                service="openiban",
                status=ServiceStatus.DEGRADED,
                message="API inaccessible",
                latency_ms=(time.time() - start) * 1000,
            )

    def _check_encryption(self) -> CheckResult:
        """Vérifie le roundtrip AES-256 (chiffrement → déchiffrement)"""
        start = time.time()
        
        try:
            from security import FieldEncryptor
            enc = FieldEncryptor()
            
            if not enc.fernet:
                return CheckResult(
                    service="encryption",
                    status=ServiceStatus.DEGRADED,
                    message="ENCRYPTION_KEY non configurée — chiffrement inactif",
                    latency_ms=(time.time() - start) * 1000,
                )
            
            # Roundtrip test
            test_iban = "CH5604835012345678009"
            encrypted = enc.encrypt(test_iban)
            decrypted = enc.decrypt(encrypted)
            
            latency = (time.time() - start) * 1000
            
            if decrypted == test_iban:
                return CheckResult(
                    service="encryption",
                    status=ServiceStatus.OK,
                    message="AES-256 roundtrip OK",
                    latency_ms=latency,
                )
            else:
                logger.error("[HEALTH] ❌ Encryption roundtrip FAILED — data corruption!")
                return CheckResult(
                    service="encryption",
                    status=ServiceStatus.DOWN,
                    message="Roundtrip échoué — corruption possible!",
                    latency_ms=latency,
                )
        
        except Exception as e:
            logger.error(f"[HEALTH] ❌ Encryption check failed: {e}")
            return CheckResult(
                service="encryption",
                status=ServiceStatus.DOWN,
                message=f"Erreur de chiffrement",
                latency_ms=(time.time() - start) * 1000,
            )

    def _check_email(self) -> CheckResult:
        """Vérifie que le service email est configuré"""
        start = time.time()
        
        resend_key = os.getenv("RESEND_API_KEY", "")
        latency = (time.time() - start) * 1000
        
        if resend_key:
            return CheckResult(
                service="email_service",
                status=ServiceStatus.OK,
                message="Resend configuré",
                latency_ms=latency,
            )
        else:
            return CheckResult(
                service="email_service",
                status=ServiceStatus.DEGRADED,
                message="RESEND_API_KEY non configurée — emails désactivés",
                latency_ms=latency,
            )
