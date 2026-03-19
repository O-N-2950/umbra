"""
MATCHO Email Service — SÉCURISÉ
Leçon PEP's #1  : Kill switch + anti-doublon obligatoires.
Leçon PEP's #10 : JAMAIS d'erreur silencieuse.
Leçon PEP's #11 : Lazy import Resend (import bloquant = site inaccessible).

© 2026 PEP's Swiss SA
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger("matcho.email")


class EmailService:
    """
    Service d'envoi d'emails via Resend avec protections PEP's.
    
    Protections :
    1. KILL SWITCH : EMAIL_ENABLED=false -> aucun email envoye
    2. ANTI-DOUBLON : 1 email max par destinataire par 10 min (meme sujet)
    3. LOG AVANT ENVOI : trace avant d'appeler Resend
    4. LAZY IMPORT : Resend importe dans la fonction, pas au top-level
    5. ERREURS LOGGEES : aucun except: pass
    """

    COOLDOWN_SECONDS = 600  # 10 min anti-doublon

    def __init__(self):
        # Lecon PEP's #1 : Kill switch par defaut = ACTIF (pas d'envoi)
        self.enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
        self.from_email = os.getenv("EMAIL_FROM", "noreply@matcho.digital")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "MATCHO")
        self._sent_log: Dict[str, float] = {}
        
        if not self.enabled:
            logger.info("Email service: KILL SWITCH ACTIF")
        else:
            logger.info("Email service: active via Resend")

    def _dedup_key(self, to: str, subject: str) -> str:
        return f"{to.lower().strip()}:{subject.strip()[:50]}"

    def _is_duplicate(self, to: str, subject: str) -> bool:
        key = self._dedup_key(to, subject)
        now = time.time()
        last = self._sent_log.get(key, 0)
        if now - last < self.COOLDOWN_SECONDS:
            logger.warning(f"Anti-doublon: email bloque pour {to[:20]}...")
            return True
        return False

    def _record_sent(self, to: str, subject: str):
        key = self._dedup_key(to, subject)
        self._sent_log[key] = time.time()
        if len(self._sent_log) > 1000:
            now = time.time()
            self._sent_log = {k: v for k, v in self._sent_log.items() if now - v < self.COOLDOWN_SECONDS}

    def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: Optional[str] = None,
        bypass_killswitch: bool = False,
    ) -> Dict[str, Any]:
        # Kill switch
        if not self.enabled and not bypass_killswitch:
            logger.info(f"Kill switch: email non envoye -> {to[:20]}...")
            return {"success": False, "error": "Kill switch actif", "id": None}
        
        # Anti-doublon
        if self._is_duplicate(to, subject):
            return {"success": False, "error": "Doublon detecte", "id": None}
        
        # Log AVANT envoi
        logger.info(f"Envoi email: {to[:20]}... - {subject[:50]}")
        self._record_sent(to, subject)
        
        # Lazy import (Lecon PEP's #11)
        try:
            import resend as resend_lib
        except ImportError:
            logger.error("Module 'resend' non installe")
            return {"success": False, "error": "Module resend manquant", "id": None}
        
        api_key = os.getenv("RESEND_API_KEY", "")
        if not api_key:
            logger.warning("RESEND_API_KEY manquante")
            return {"success": False, "error": "API key manquante", "id": None}
        
        try:
            resend_lib.api_key = api_key
            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to],
                "subject": subject,
                "html": html,
            }
            if text:
                params["text"] = text
            
            response = resend_lib.Emails.send(params)
            email_id = response.get("id") if isinstance(response, dict) else str(response)
            logger.info(f"Email envoye: {email_id}")
            return {"success": True, "error": None, "id": email_id}
        except Exception as e:
            # JAMAIS avaler l'erreur (Lecon PEP's #10)
            logger.error(f"Echec envoi email a {to[:20]}...: {e}", exc_info=True)
            return {"success": False, "error": str(e), "id": None}

    def send_welcome_email(self, to: str, name: str) -> Dict[str, Any]:
        subject = "Bienvenue sur MATCHO !"
        html = f"""<div style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;">
<div style="background:linear-gradient(135deg,#059669,#0D9488);color:white;padding:30px;border-radius:10px 10px 0 0;text-align:center;"><h1>Bienvenue sur MATCHO !</h1></div>
<div style="background:#F9FAFB;padding:30px;border-radius:0 0 10px 10px;">
<p>Bonjour {name},</p>
<p>Merci d'avoir choisi <strong>MATCHO</strong> pour votre reconciliation bancaire automatique.</p>
<p>A tres bientot,<br>L'equipe MATCHO</p></div>
<div style="text-align:center;padding:15px;color:#9CA3AF;font-size:12px;">PEP's Swiss SA</div></div>"""
        return self.send_email(to, subject, html)

    def send_reconciliation_complete(self, to: str, name: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        total = stats.get("total_bank", 0)
        matched = stats.get("auto_matched", 0)
        rate = round(matched / total * 100) if total else 0
        subject = f"Reconciliation terminee - {rate}% matchees"
        html = f"""<div style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;">
<div style="background:#059669;color:white;padding:25px;border-radius:10px 10px 0 0;text-align:center;"><h2>Reconciliation Terminee</h2></div>
<div style="background:#F9FAFB;padding:25px;border-radius:0 0 10px 10px;">
<p>Bonjour {name}, votre reconciliation est terminee : {matched}/{total} transactions matchees ({rate}%).</p></div></div>"""
        return self.send_email(to, subject, html)

    def send_magic_link(self, to: str, link: str, name: str = "") -> Dict[str, Any]:
        greeting = f"Bonjour {name}," if name else "Bonjour,"
        subject = "Votre lien de connexion MATCHO"
        html = f"""<div style="font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;">
<div style="background:linear-gradient(135deg,#059669,#0D9488);color:white;padding:25px;border-radius:10px 10px 0 0;text-align:center;"><h2>Connexion MATCHO</h2></div>
<div style="background:#F9FAFB;padding:25px;border-radius:0 0 10px 10px;">
<p>{greeting}</p>
<p style="text-align:center;margin:25px 0;"><a href="{link}" style="background:#059669;color:white;padding:14px 35px;text-decoration:none;border-radius:6px;display:inline-block;">Se connecter</a></p>
<p style="color:#6B7280;font-size:13px;">Ce lien expire dans 15 minutes.</p></div></div>"""
        return self.send_email(to, subject, html)


# Instance globale
email_service = EmailService()

def send_email(to, subject, html, text=None):
    return email_service.send_email(to, subject, html, text)

def send_welcome_email(to, name):
    return email_service.send_welcome_email(to, name)

def send_reconciliation_complete(to, name, stats):
    return email_service.send_reconciliation_complete(to, name, stats)

def send_magic_link(to, link, name=""):
    return email_service.send_magic_link(to, link, name)
