"""
UMBRA API — Point d'entrée principal
Plateforme de recrutement anonyme — Suisse & frontaliers

Architecture :
  - Profils anonymes dissociés des comptes réels
  - Matching multicritères (compétences × culture × géo × salary × durabilité)
  - Révélation mutuelle protocole (double confirmation)
  - Système de confiance event-sourcing
  - Intelligence marché temps réel

Patterns Groupe NEO :
  - Health check au boot
  - Crash Monitor arrière-plan
  - Alerte email si service down
  - Migrations Alembic
  - Lazy imports

© 2026 PEP's Swiss SA — UMBRA
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ══════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("umbra")


# ══════════════════════════════════════════════════════════════
# LIFESPAN
# ══════════════════════════════════════════════════════════════

_crash_monitor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _crash_monitor

    logger.info("=" * 60)
    logger.info("🌑 UMBRA API — Démarrage")
    logger.info("=" * 60)

    # ── 1. Migrations Alembic ──────────────────────────────────
    try:
        from alembic import command
        from alembic.config import Config
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Migrations OK")
    except Exception as e:
        logger.error("❌ Migrations failed: %s", e)

    # ── 2. Seed data (idempotent) ──────────────────────────────
    try:
        from db.session import SessionLocal
        from db.seed_data import seed_all
        with SessionLocal() as db:
            result = seed_all(db)
        logger.info("✅ Seed OK: %s", result)
    except Exception as e:
        logger.warning("⚠️ Seed failed (non-bloquant): %s", e)

    # ── 3. Crash Monitor ───────────────────────────────────────
    try:
        from monitoring.crash_monitor import CrashMonitor
        _crash_monitor = CrashMonitor()
        asyncio.create_task(_crash_monitor.start())
        logger.info("✅ Crash monitor actif")
    except Exception as e:
        logger.warning("⚠️ Crash monitor non disponible: %s", e)

    logger.info("🌑 UMBRA prêt — %s", os.getenv("ENV", "dev"))
    logger.info("=" * 60)

    yield

    # ── Shutdown ───────────────────────────────────────────────
    if _crash_monitor:
        await _crash_monitor.stop()
    logger.info("🌑 UMBRA arrêté proprement")


# ══════════════════════════════════════════════════════════════
# APPLICATION
# ══════════════════════════════════════════════════════════════

app = FastAPI(
    title="UMBRA API",
    description="Plateforme de recrutement anonyme — Suisse & frontaliers",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENV", "dev") == "dev" else None,
    redoc_url=None,
)


# ══════════════════════════════════════════════════════════════
# CORS
# ══════════════════════════════════════════════════════════════

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://umbra.work",
    "https://www.umbra.work",
    "https://umbra.jobs",
    os.getenv("APP_URL", ""),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in ALLOWED_ORIGINS if o],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════
# ROUTERS
# ══════════════════════════════════════════════════════════════

# Auth UMBRA
from api.umbra_auth import router as auth_router
app.include_router(auth_router, prefix="/api/v1")

# Profiles
from api.umbra_profiles import router as profiles_router
app.include_router(profiles_router, prefix="/api/v1")

# Matches + Signals + Questions
from api.umbra_matches import router_matches, router_signals, router_questions
app.include_router(router_matches,   prefix="/api/v1")
app.include_router(router_signals,   prefix="/api/v1")
app.include_router(router_questions, prefix="/api/v1")

# Trust / Passeport
from api.umbra_trust import router as trust_router
app.include_router(trust_router, prefix="/api/v1")

# Credits
from api.umbra_credits import router as credits_router
app.include_router(credits_router, prefix="/api/v1")

# ── Anciens routers MATCHO (conservés) ────────────────────────
try:
    from api.export_routes import router as export_router
    app.include_router(export_router, prefix="/api/v1")
    logger.info("MATCHO export router chargé")
except ImportError:
    pass


# ══════════════════════════════════════════════════════════════
# HEALTH + ROOT
# ══════════════════════════════════════════════════════════════

@app.get("/")
def root():
    return {
        "service": "UMBRA API",
        "version": "1.0.0",
        "status":  "operational",
        "tagline": "Le talent se cache. Nous le trouvons.",
    }


@app.get("/health")
def health():
    """Health check Railway."""
    checks = {}

    # DB
    try:
        from db.session import SessionLocal
        with SessionLocal() as db:
            db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    code   = 200 if status == "healthy" else 503

    return JSONResponse(
        status_code=code,
        content={
            "status":  status,
            "service": "umbra-api",
            "checks":  checks,
            "env":     os.getenv("ENV", "dev"),
        }
    )


@app.get("/api/v1/sectors")
def get_sectors(db=None):
    """Liste des secteurs disponibles (public — pas d'auth requise)."""
    from db.session import SessionLocal
    from db.umbra_models import Sector
    with SessionLocal() as session:
        sectors = session.query(Sector).filter(Sector.is_active == True).order_by(Sector.order).all()
        return {
            "sectors": [
                {
                    "id":     s.id,
                    "slug":   s.slug,
                    "label":  s.label,
                    "symbol": s.symbol,
                    "color":  s.color,
                }
                for s in sectors
            ]
        }
