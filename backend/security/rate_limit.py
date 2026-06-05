"""
UMBRA — Rate Limiting + Security Headers Middleware
Protection anti-brute force sur les routes auth.
© 2026 PEP's Swiss SA — UMBRA
"""

import os
import time
import logging
from collections import defaultdict
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger("umbra.security")

# ── In-memory rate limiter (Redis en prod) ────────────────────────────────────
# Structure: {ip: [(timestamp, route), ...]}
_rate_store: dict = defaultdict(list)

RATE_LIMITS = {
    "/api/v1/auth/login":    (5,  60),   # 5 req / 60s
    "/api/v1/auth/register": (3,  60),   # 3 req / 60s
    "/api/v1/auth/verify":   (10, 60),   # 10 req / 60s
}
DEFAULT_LIMIT = (60, 60)  # 60 req / 60s pour les autres


def _get_client_ip(request: Request) -> str:
    """IP réelle, respecte X-Forwarded-For de Railway."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "0.0.0.0"


def _is_rate_limited(ip: str, path: str) -> bool:
    limit, window = RATE_LIMITS.get(path, DEFAULT_LIMIT)
    now = time.time()
    history = _rate_store[f"{ip}:{path}"]
    # Nettoyer les vieilles entrées
    _rate_store[f"{ip}:{path}"] = [t for t in history if now - t < window]
    if len(_rate_store[f"{ip}:{path}"]) >= limit:
        return True
    _rate_store[f"{ip}:{path}"].append(now)
    return False


async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware FastAPI — rate limiting + headers sécurité."""
    ip = _get_client_ip(request)
    path = request.url.path

    # Rate limiting
    if _is_rate_limited(ip, path):
        logger.warning("[RATE_LIMIT] %s bloqué sur %s", ip[:8]+"...", path)
        return JSONResponse(
            status_code=429,
            content={"detail": "Trop de requêtes. Réessayez dans 60 secondes."},
            headers={"Retry-After": "60"}
        )

    response = await call_next(request)

    # Security headers (OWASP)
    response.headers["X-Content-Type-Options"]  = "nosniff"
    response.headers["X-Frame-Options"]          = "DENY"
    response.headers["X-XSS-Protection"]         = "1; mode=block"
    response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]        = "geolocation=(), camera=(), microphone=()"
    if os.getenv("ENVIRONMENT", "production") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response
