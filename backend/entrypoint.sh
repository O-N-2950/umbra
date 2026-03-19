#!/bin/sh
# MATCHO — Entrypoint (Railway / Docker)
# Leçon PEP's #7 : Alembic migrations AVANT démarrage.
# Leçon PEP's #8 : Si migration échoue, on démarre quand même.

set -e

echo "═══════════════════════════════════════"
echo "🚀 MATCHO API — Initialisation"
echo "   Env: ${ENVIRONMENT:-production}"
echo "   Port: ${PORT:-8000}"
echo "═══════════════════════════════════════"

# ── 0. Fix DATABASE_URL pour Railway ──
# Railway fournit postgresql:// mais SQLAlchemy async veut postgresql+asyncpg://
if [ -n "$DATABASE_URL" ]; then
    case "$DATABASE_URL" in
        postgresql+asyncpg://*)
            echo "✅ DB: PostgreSQL (déjà async)"
            ;;
        postgresql://*)
            export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|^postgresql://|postgresql+asyncpg://|')
            echo "✅ DB: PostgreSQL (converti → asyncpg)"
            ;;
        *)
            echo "✅ DB: $DATABASE_URL"
            ;;
    esac

    # ── 1. Migrations Alembic (seulement si PostgreSQL) ──
    echo "📦 Alembic migrations..."
    if alembic upgrade head 2>&1; then
        echo "✅ Migrations OK"
    else
        echo "⚠️ Migrations échouées — démarrage sans migration"
    fi
else
    echo "⚠️ DATABASE_URL non définie — skip migrations, SQLite par défaut"
fi

# ── 2. Démarrage Uvicorn ──
echo "🌐 Démarrage sur :${PORT:-8000}"
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --no-access-log \
    --timeout-keep-alive 65
