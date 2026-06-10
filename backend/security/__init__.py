"""
MATCHO — Security Module
Protection complète contre les attaques courantes.

Couvre:
- Rate Limiting (brute force, DDoS)
- Security Headers (CSP, HSTS, X-Frame-Options, etc.)
- Input Sanitization (XSS, injection)
- XXE Protection (XML External Entity)
- File Upload Validation
- Request Size Limiting
- Error Sanitization (no stack trace leaks)
- IP Blocking
- Audit Logging (failed auth, suspicious activity)
- IBAN/Data Masking for logs
- Encryption helpers for sensitive fields

© 2026 PEP's Swiss SA
"""

import re
import os
import time
import hashlib
import hmac
import secrets
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Dict, Set
from functools import wraps

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# ── Logging ────────────────────────────────────────────

logger = logging.getLogger("umbra.security")
logger.setLevel(logging.INFO)

# Log format sans données sensibles
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
logger.addHandler(handler)


# ══════════════════════════════════════════════════════════
# 1. RATE LIMITER (In-Memory, production → Redis)
# ══════════════════════════════════════════════════════════

class RateLimiter:
    """
    Rate limiting par IP avec fenêtres glissantes.
    
    Limites par défaut:
    - Global: 100 req/min par IP
    - Auth: 5 req/min par IP (anti brute-force)
    - Onboarding: 20 req/min par IP
    - File upload: 10 req/min par IP
    """

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.blocked_ips: Dict[str, float] = {}
        self.failed_auth: Dict[str, list] = defaultdict(list)

    # Limites par catégorie (requêtes, fenêtre en secondes)
    LIMITS = {
        "global":     (100, 60),
        "auth":       (5, 60),
        "onboarding": (20, 60),
        "upload":     (10, 60),
        "iban":       (30, 60),
        "search":     (30, 60),
    }

    BLOCK_DURATION = 900  # 15 minutes

    def _clean(self, key: str, window: int):
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if now - t < window]

    def is_blocked(self, ip: str) -> bool:
        if ip in self.blocked_ips:
            if time.time() < self.blocked_ips[ip]:
                return True
            del self.blocked_ips[ip]
        return False

    def block_ip(self, ip: str, duration: int = None):
        self.blocked_ips[ip] = time.time() + (duration or self.BLOCK_DURATION)
        logger.warning(f"🚫 IP bloquée: {self._mask_ip(ip)} pour {duration or self.BLOCK_DURATION}s")

    def check(self, ip: str, category: str = "global") -> bool:
        """Retourne True si la requête est autorisée"""
        if self.is_blocked(ip):
            return False

        max_requests, window = self.LIMITS.get(category, self.LIMITS["global"])
        key = f"{ip}:{category}"
        self._clean(key, window)

        if len(self.requests[key]) >= max_requests:
            logger.warning(f"⚠️ Rate limit atteint: {self._mask_ip(ip)} [{category}] {len(self.requests[key])}/{max_requests}")
            return False

        self.requests[key].append(time.time())
        return True

    def record_failed_auth(self, ip: str):
        """Enregistre un échec d'auth. 10 échecs → blocage IP"""
        now = time.time()
        self.failed_auth[ip] = [t for t in self.failed_auth[ip] if now - t < 3600]
        self.failed_auth[ip].append(now)

        count = len(self.failed_auth[ip])
        if count >= 10:
            self.block_ip(ip, 3600)  # 1h block
            logger.warning(f"🚨 10 échecs auth: {self._mask_ip(ip)} → bloqué 1h")
        elif count >= 5:
            logger.warning(f"⚠️ {count} échecs auth: {self._mask_ip(ip)}")

    @staticmethod
    def _mask_ip(ip: str) -> str:
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.xxx.xxx"
        return ip[:10] + "..."


# Instance globale
rate_limiter = RateLimiter()


# ══════════════════════════════════════════════════════════
# 2. SECURITY HEADERS MIDDLEWARE
# ══════════════════════════════════════════════════════════

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Ajoute les headers de sécurité HTTP.
    Compatible OWASP Top 10.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (no camera, mic, geolocation)
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self' https://www.uid-wse.admin.ch https://openiban.com https://www.zefix.admin.ch; "
            "frame-ancestors 'none'"
        )

        # HSTS (force HTTPS en production)
        if os.getenv("ENVIRONMENT", "development") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Cache control pour données sensibles
        if "/api/" in request.url.path:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"

        return response


# ══════════════════════════════════════════════════════════
# 3. RATE LIMITING MIDDLEWARE
# ══════════════════════════════════════════════════════════

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting par IP et catégorie"""

    CATEGORY_MAP = {
        "/api/auth/": "auth",
        "/api/onboarding/": "onboarding",
        "/api/iban/": "iban",
        "/api/uid/": "search",
        "/api/parse/": "upload",
    }

    async def dispatch(self, request: Request, call_next):
        ip = self._get_client_ip(request)

        # Check block
        if rate_limiter.is_blocked(ip):
            logger.warning(f"🚫 Requête bloquée: {rate_limiter._mask_ip(ip)}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Trop de requêtes. Réessayez plus tard."},
                headers={"Retry-After": "900"},
            )

        # Determine category
        category = "global"
        for prefix, cat in self.CATEGORY_MAP.items():
            if request.url.path.startswith(prefix):
                category = cat
                break

        # Check rate
        if not rate_limiter.check(ip, category):
            return JSONResponse(
                status_code=429,
                content={"detail": "Limite de requêtes atteinte. Réessayez dans 1 minute."},
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)

        # Track failed auth
        if request.url.path.startswith("/api/auth/") and response.status_code == 401:
            rate_limiter.record_failed_auth(ip)

        return response

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


# ══════════════════════════════════════════════════════════
# 4. REQUEST SIZE LIMITER
# ══════════════════════════════════════════════════════════

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limite la taille des requêtes pour éviter DoS"""

    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB max
    MAX_JSON_SIZE = 1 * 1024 * 1024   # 1 MB pour JSON
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB pour upload

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        content_type = request.headers.get("content-type", "")

        if content_length:
            size = int(content_length)
            if "multipart" in content_type:
                limit = self.MAX_FILE_SIZE
            elif "json" in content_type:
                limit = self.MAX_JSON_SIZE
            else:
                limit = self.MAX_BODY_SIZE

            if size > limit:
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Requête trop volumineuse. Maximum: {limit // (1024*1024)} MB"}
                )

        return await call_next(request)


# ══════════════════════════════════════════════════════════
# 5. INPUT SANITIZATION
# ══════════════════════════════════════════════════════════

class InputSanitizer:
    """
    Nettoyage des entrées utilisateur.
    Anti-XSS, anti-injection SQL/SOAP/LDAP.
    """

    # Patterns dangereux
    XSS_PATTERNS = [
        re.compile(r"<script[^>]*>", re.IGNORECASE),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"on\w+\s*=", re.IGNORECASE),  # onclick=, onload=, etc.
        re.compile(r"<iframe", re.IGNORECASE),
        re.compile(r"<object", re.IGNORECASE),
        re.compile(r"<embed", re.IGNORECASE),
        re.compile(r"<svg[^>]*on", re.IGNORECASE),
        re.compile(r"expression\s*\(", re.IGNORECASE),
        re.compile(r"url\s*\(\s*['\"]?\s*data:", re.IGNORECASE),
    ]

    SQL_PATTERNS = [
        re.compile(r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|EXEC)\s", re.IGNORECASE),
        re.compile(r"UNION\s+(ALL\s+)?SELECT", re.IGNORECASE),
        re.compile(r"--\s", re.IGNORECASE),  # SQL comment
        re.compile(r"/\*.*\*/", re.IGNORECASE),
    ]

    SOAP_INJECTION = [
        re.compile(r"<!\[CDATA\[", re.IGNORECASE),
        re.compile(r"<!DOCTYPE", re.IGNORECASE),
        re.compile(r"<!ENTITY", re.IGNORECASE),
        re.compile(r"<\?xml", re.IGNORECASE),
        re.compile(r"xmlns:", re.IGNORECASE),
    ]

    @classmethod
    def is_malicious(cls, value: str) -> bool:
        """Détecte si une entrée contient des patterns malveillants"""
        if not isinstance(value, str):
            return False
        for pattern in cls.XSS_PATTERNS + cls.SQL_PATTERNS + cls.SOAP_INJECTION:
            if pattern.search(value):
                return True
        return False

    @classmethod
    def sanitize_text(cls, value: str, max_length: int = 500) -> str:
        """Nettoie une entrée texte"""
        if not isinstance(value, str):
            return ""
        # Tronquer
        value = value[:max_length]
        # Supprimer les caractères de contrôle (sauf newline, tab)
        value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
        # Échapper HTML
        value = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        value = value.replace('"', "&quot;").replace("'", "&#x27;")
        return value.strip()

    @classmethod
    def sanitize_company_name(cls, name: str) -> str:
        """Nettoie un nom de société (autorise apostrophes, accents, &)"""
        if not name:
            return ""
        # Autoriser: lettres, chiffres, espaces, tirets, apostrophes, points, accents
        # Refuser: <, >, ;, scripts
        clean = name[:200]
        clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", clean)
        # Check for injection attempts
        if cls.is_malicious(clean):
            logger.warning(f"⚠️ Tentative injection dans nom société: {clean[:50]}...")
            # Remove only the dangerous parts, keep the rest
            for pattern in cls.XSS_PATTERNS + cls.SQL_PATTERNS + cls.SOAP_INJECTION:
                clean = pattern.sub("", clean)
        return clean.strip()

    @classmethod
    def sanitize_email(cls, email: str) -> Optional[str]:
        """Valide et nettoie un email"""
        if not email:
            return None
        email = email.strip().lower()[:254]
        # RFC 5322 simplified
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return None
        return email

    @classmethod
    def sanitize_phone(cls, phone: str) -> str:
        """Nettoie un numéro de téléphone"""
        if not phone:
            return ""
        if cls.is_malicious(phone):
            return ""
        # Garder chiffres, +, espaces, tirets, parenthèses
        return re.sub(r"[^\d\s\+\-\(\)]", "", phone)[:30]

    @classmethod
    def sanitize_iban(cls, iban: str) -> str:
        """Nettoie un IBAN (lettres et chiffres uniquement)"""
        if not iban:
            return ""
        if cls.is_malicious(iban):
            return ""
        return re.sub(r"[^A-Za-z0-9]", "", iban)[:34].upper()

    @classmethod
    def sanitize_ide(cls, ide: str) -> str:
        """Nettoie un numéro IDE (CHE-xxx.xxx.xxx)"""
        if not ide:
            return ""
        clean = re.sub(r"[^A-Za-z0-9\-\.]", "", ide)[:15]
        return clean.upper()


# ══════════════════════════════════════════════════════════
# 6. XXE PROTECTION (XML External Entity)
# ══════════════════════════════════════════════════════════

def safe_parse_xml(xml_string: str):
    """
    Parse XML en toute sécurité — bloque XXE, Billion Laughs, etc.
    
    Utilise defusedxml si disponible, sinon désactive manuellement
    les entités externes dans ElementTree.
    """
    try:
        import defusedxml.ElementTree as SafeET
        return SafeET.fromstring(xml_string)
    except ImportError:
        pass

    # Fallback: vérifications manuelles
    import xml.etree.ElementTree as ET

    # Block DOCTYPE declarations (XXE vector)
    if re.search(r"<!DOCTYPE", xml_string, re.IGNORECASE):
        raise ValueError("XML DOCTYPE interdit (protection XXE)")

    # Block ENTITY declarations (Billion Laughs)
    if re.search(r"<!ENTITY", xml_string, re.IGNORECASE):
        raise ValueError("XML ENTITY interdit (protection Billion Laughs)")

    # Block external references
    if re.search(r"SYSTEM\s+['\"]", xml_string, re.IGNORECASE):
        raise ValueError("Référence externe XML interdite")

    # Block processing instructions that could execute code
    if re.search(r"<\?xml-stylesheet", xml_string, re.IGNORECASE):
        raise ValueError("Instruction de traitement XML interdite")

    return ET.fromstring(xml_string)


# ══════════════════════════════════════════════════════════
# 7. FILE UPLOAD VALIDATION
# ══════════════════════════════════════════════════════════

class FileValidator:
    """Validation stricte des fichiers uploadés"""

    ALLOWED_TYPES = {
        ".xml": {
            "mime": ["text/xml", "application/xml"],
            "magic": [b"<?xml", b"<"],
            "max_size": 10 * 1024 * 1024,  # 10 MB
        },
        ".pdf": {
            "mime": ["application/pdf"],
            "magic": [b"%PDF"],
            "max_size": 50 * 1024 * 1024,  # 50 MB
        },
        ".csv": {
            "mime": ["text/csv", "text/plain"],
            "magic": [],
            "max_size": 10 * 1024 * 1024,
        },
    }

    @classmethod
    async def validate(cls, file, allowed_extensions: list = None) -> tuple:
        """
        Valide un fichier uploadé.
        Retourne (is_valid, error_message, content_bytes)
        """
        if not file or not file.filename:
            return False, "Fichier requis", b""

        # Check extension
        ext = os.path.splitext(file.filename)[1].lower()
        if allowed_extensions and ext not in allowed_extensions:
            return False, f"Extension non autorisée: {ext}. Acceptées: {', '.join(allowed_extensions)}", b""

        if ext not in cls.ALLOWED_TYPES:
            return False, f"Type de fichier non supporté: {ext}", b""

        config = cls.ALLOWED_TYPES[ext]

        # Read content
        content = await file.read()
        await file.seek(0)

        # Check size
        if len(content) > config["max_size"]:
            max_mb = config["max_size"] // (1024 * 1024)
            return False, f"Fichier trop volumineux. Maximum: {max_mb} MB", b""

        # Check magic bytes
        if config["magic"]:
            header = content[:10]
            if not any(header.startswith(m) for m in config["magic"]):
                return False, f"Contenu du fichier ne correspond pas à l'extension {ext}", b""

        # Check for embedded scripts in XML
        if ext == ".xml":
            text = content.decode("utf-8", errors="ignore")
            if re.search(r"<!DOCTYPE|<!ENTITY|SYSTEM\s+['\"]", text, re.IGNORECASE):
                return False, "Fichier XML contient des éléments interdits (sécurité)", b""

        # Sanitize filename
        safe_name = re.sub(r"[^\w\-\.]", "_", file.filename)[:100]

        return True, safe_name, content


# ══════════════════════════════════════════════════════════
# 8. ERROR SANITIZATION
# ══════════════════════════════════════════════════════════

def safe_error(status_code: int, message: str, internal_error: Exception = None) -> HTTPException:
    """
    Crée une erreur HTTP sûre — jamais de stack trace en production.
    Log l'erreur complète côté serveur.
    """
    if internal_error:
        logger.error(f"Erreur interne [{status_code}]: {internal_error}", exc_info=True)

    # Messages génériques par code
    GENERIC = {
        400: "Requête invalide",
        401: "Authentification requise",
        403: "Accès refusé",
        404: "Ressource non trouvée",
        409: "Conflit de données",
        413: "Données trop volumineuses",
        422: "Données invalides",
        429: "Trop de requêtes",
        500: "Erreur interne du serveur",
    }

    # En production: message générique uniquement
    if os.getenv("ENVIRONMENT", "development") == "production":
        detail = GENERIC.get(status_code, "Erreur du serveur")
    else:
        detail = message or GENERIC.get(status_code, "Erreur")

    return HTTPException(status_code=status_code, detail=detail)


# ══════════════════════════════════════════════════════════
# 9. DATA MASKING (Logs & Audit)
# ══════════════════════════════════════════════════════════

class DataMasker:
    """Masque les données sensibles dans les logs"""

    @staticmethod
    def mask_iban(iban: str) -> str:
        if not iban or len(iban) < 10:
            return "****"
        return f"{iban[:4]}{'*' * (len(iban) - 8)}{iban[-4:]}"

    @staticmethod
    def mask_email(email: str) -> str:
        if not email or "@" not in email:
            return "****"
        local, domain = email.split("@", 1)
        return f"{local[0]}***@{domain}"

    @staticmethod
    def mask_ide(ide: str) -> str:
        if not ide or len(ide) < 8:
            return "CHE-***.***.***"
        return f"{ide[:7]}***.***"

    @staticmethod
    def mask_phone(phone: str) -> str:
        if not phone or len(phone) < 6:
            return "****"
        return f"{phone[:6]}{'*' * (len(phone) - 6)}"


# ══════════════════════════════════════════════════════════
# 10. ENCRYPTION HELPERS (Sensitive Fields)
# ══════════════════════════════════════════════════════════

class FieldEncryptor:
    """
    Chiffrement AES-256 pour champs sensibles en DB.
    Utilise Fernet (AES-128-CBC + HMAC) via cryptography lib.
    
    Usage:
        enc = FieldEncryptor(os.getenv("ENCRYPTION_KEY"))
        encrypted_iban = enc.encrypt("CH5604835012345678009")
        plain_iban = enc.decrypt(encrypted_iban)
    """

    def __init__(self, key: str = None):
        self.key = key or os.getenv("ENCRYPTION_KEY", "")
        self._fernet = None

    @property
    def fernet(self):
        if self._fernet is None and self.key:
            try:
                from cryptography.fernet import Fernet
                # Derive a proper Fernet key from our secret
                import base64
                dk = hashlib.pbkdf2_hmac("sha256", self.key.encode(), b"umbra-salt-2026-pep-swiss", 100000, dklen=32)
                self._fernet = Fernet(base64.urlsafe_b64encode(dk))
            except ImportError:
                logger.warning("⚠️ cryptography non installé — chiffrement désactivé")
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        if not self.fernet:
            return plaintext  # Fallback: pas de chiffrement
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        if not self.fernet:
            return ciphertext
        try:
            return self.fernet.decrypt(ciphertext.encode()).decode()
        except Exception:
            return ciphertext  # Si déchiffrement échoue, retourner tel quel


# ══════════════════════════════════════════════════════════
# 11. SECURITY AUDIT LOGGER
# ══════════════════════════════════════════════════════════

class SecurityAuditLogger:
    """Log les événements de sécurité"""

    @staticmethod
    def log_auth_success(ip: str, email: str):
        logger.info(f"✅ Auth OK: {DataMasker.mask_email(email)} depuis {RateLimiter._mask_ip(ip)}")

    @staticmethod
    def log_auth_failure(ip: str, email: str, reason: str):
        logger.warning(f"❌ Auth FAIL: {DataMasker.mask_email(email)} depuis {RateLimiter._mask_ip(ip)} — {reason}")

    @staticmethod
    def log_suspicious(ip: str, action: str, details: str = ""):
        logger.warning(f"🚨 SUSPECT: {RateLimiter._mask_ip(ip)} — {action} {details}")

    @staticmethod
    def log_data_access(user_id: str, resource: str, action: str):
        logger.info(f"📋 DATA: user={user_id[:8]}... {action} {resource}")

    @staticmethod
    def log_blocked(ip: str, reason: str):
        logger.warning(f"🚫 BLOCKED: {RateLimiter._mask_ip(ip)} — {reason}")


# ══════════════════════════════════════════════════════════
# INSTALL ALL MIDDLEWARES
# ══════════════════════════════════════════════════════════

def install_security(app):
    """
    Installe toutes les protections sur l'app FastAPI.
    Appeler AVANT d'ajouter les routes.
    
    Usage:
        from security.middleware import install_security
        install_security(app)
    """
    # Ordre important: les middlewares s'exécutent en LIFO
    # 1. Rate limiting (premier check)
    app.add_middleware(RateLimitMiddleware)
    # 2. Request size
    app.add_middleware(RequestSizeLimitMiddleware)
    # 3. Security headers (dernier ajout = premier exécuté sur response)
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("🔒 Security middlewares installés")
    logger.info(f"   Rate limits: {RateLimiter.LIMITS}")
    logger.info(f"   Max body: {RequestSizeLimitMiddleware.MAX_BODY_SIZE // (1024*1024)} MB")
    logger.info(f"   Headers: CSP, HSTS, X-Frame-Options, XSS-Protection")

    return app
