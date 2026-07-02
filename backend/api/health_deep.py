"""
backend/api/health_deep.py — Healthcheck profond de Merito (pattern soluris).

GET /health/deep : vérifie chaque dépendance critique, chronométrée et isolée.
- database   : SELECT 1 réel + comptage des tables du schéma public
- migrations : présence/valeur de alembic_version
- smtp       : joignabilité TCP de SMTP_HOST:SMTP_PORT (pas de login → rapide, sans spam)
- ai_llm     : configuration de la clé (GEMINI/LLM) — pas d'appel réseau (coût/latence)
- disk       : espace libre sur /

Codes retour : 200 healthy · 200 degraded (dépendances non vitales KO) · 503 critical (DB KO).
Le /health historique (léger, DB only) reste inchangé : c'est lui que Railway/Jelastic sondent.
`?verbose=1` ajoute les durées de chaque check.
"""
from __future__ import annotations

import os
import socket
import shutil
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])

CRITICAL_CHECKS = {"database"}  # KO ⇒ 503 ; le reste ⇒ degraded (200)


def _timed(fn):
    t0 = time.perf_counter()
    try:
        value = fn()
        return {"status": "ok", **(value or {})}, round((time.perf_counter() - t0) * 1000, 1)
    except Exception as e:  # noqa: BLE001 — chaque check est volontairement isolé
        return {"status": f"error: {type(e).__name__}: {str(e)[:120]}"}, round((time.perf_counter() - t0) * 1000, 1)


def _check_database():
    from sqlalchemy import text
    from db.session import engine
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        tables = conn.execute(text(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
        )).scalar()
    return {"tables": int(tables or 0)}


def _check_migrations():
    from sqlalchemy import text
    from db.session import engine
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
    if not version:
        raise RuntimeError("alembic_version vide")
    return {"revision": str(version)[:12]}


def _check_smtp():
    host = os.getenv("SMTP_HOST")
    if not host:
        raise RuntimeError("SMTP_HOST non configuré")
    port = int(os.getenv("SMTP_PORT", "465"))
    with socket.create_connection((host, port), timeout=3):
        pass
    return {"host": host, "port": port}


def _check_ai_llm():
    # Souverain (Infomaniak) prioritaire le jour où il est branché, sinon Gemini.
    if os.getenv("INFOMANIAK_AI_KEY") or os.getenv("LLM_API_KEY"):
        return {"provider": "infomaniak (souverain)"}
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return {"provider": "gemini (US, PII-shield actif)"}
    raise RuntimeError("aucune clé LLM configurée")


def _check_disk():
    du = shutil.disk_usage("/")
    free_pct = round(du.free / du.total * 100, 1)
    if free_pct < 5:
        raise RuntimeError(f"espace critique: {free_pct}% libre")
    return {"free_percent": free_pct}


@router.get("/health/deep")
def health_deep(request: Request, verbose: int = 0):
    checks, timings = {}, {}
    for name, fn in {
        "database":   _check_database,
        "migrations": _check_migrations,
        "smtp":       _check_smtp,
        "ai_llm":     _check_ai_llm,
        "disk":       _check_disk,
    }.items():
        checks[name], timings[name] = _timed(fn)

    critical_ko = any(checks[c]["status"] != "ok" for c in CRITICAL_CHECKS)
    any_ko      = any(v["status"] != "ok" for v in checks.values())
    status = "critical" if critical_ko else ("degraded" if any_ko else "healthy")

    body = {
        "status":  status,
        "service": "umbra-api",
        "env":     os.getenv("ENV", "dev"),
        "checks":  checks,
    }
    if verbose:
        body["timings_ms"] = timings
    return JSONResponse(status_code=503 if critical_ko else 200, content=body)
