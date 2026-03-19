"""
UMBRA — Database Session
Pool de connexions PostgreSQL synchrone (SQLAlchemy).
Async via asyncpg pour les routes haute performance (à venir).

Configuration :
  DATABASE_URL=postgresql://user:pass@host/umbra
  (Railway injecte automatiquement DATABASE_URL)

© 2026 PEP's Swiss SA — UMBRA
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger("umbra.db")

# ── CONFIG ────────────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///matcho_dev.db"
)

# Railway injecte postgres:// mais SQLAlchemy 2.x veut postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── ENGINE ────────────────────────────────────────────────────────────────────

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,           # connexions simultanées
    max_overflow=20,        # burst au-delà du pool
    pool_pre_ping=True,     # vérif connexion avant usage (Railway ↔ PostgreSQL)
    pool_recycle=3600,      # recycle après 1h (évite connexions mortes)
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

# ── SESSION ───────────────────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,   # évite les lazy-load après commit
)


# ── DEPENDENCY FastAPI ────────────────────────────────────────────────────────

def get_db() -> Session:
    """
    Dependency injection FastAPI.
    Usage : db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── HEALTH CHECK ──────────────────────────────────────────────────────────────

def ping_db() -> bool:
    """Vérifie que la base répond. Utilisé par le health check."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("DB ping failed: %s", e)
        return False


# ── INIT TABLES ───────────────────────────────────────────────────────────────

def create_all_tables():
    """
    Crée toutes les tables depuis les modèles SQLAlchemy.
    À utiliser en dev uniquement — en prod, utiliser Alembic.
    """
    from .umbra_models import Base as UmbraBase
    from .models import Base as MatchoBase

    UmbraBase.metadata.create_all(bind=engine)
    MatchoBase.metadata.create_all(bind=engine)
    logger.info("all tables created")
