#!/bin/sh
# UMBRA — Entrypoint (Railway / Docker)
# Leçon PEP's #7 : Alembic migrations AVANT démarrage.
# Leçon PEP's #8 : Si migration échoue, on démarre quand même.

set -e

echo "═══════════════════════════════════════"
echo "🌑 UMBRA API — Initialisation"
echo "   Env: ${ENVIRONMENT:-production}"
echo "   Port: ${PORT:-8000}"
echo "═══════════════════════════════════════"

# ── 0. Fix DATABASE_URL pour Railway ──
# Railway fournit postgres:// mais SQLAlchemy veut postgresql://
if [ -n "$DATABASE_URL" ]; then
    case "$DATABASE_URL" in
        postgresql://*|sqlite://*)
            echo "✅ DB: URL OK"
            ;;
        postgres://*)
            export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's|^postgres://|postgresql://|')
            echo "✅ DB: PostgreSQL (converti postgres → postgresql)"
            ;;
        *)
            echo "✅ DB: $DATABASE_URL"
            ;;
    esac

    # ── 1. Migrations Alembic (seulement si PostgreSQL) ──
    echo "📦 Alembic migrations..."
    # Vérifier si la table alembic_version existe déjà
    python3 -c "
import os, sys
from sqlalchemy import create_engine, text
db_url = os.getenv('DATABASE_URL', '').replace('postgres://', 'postgresql://')
if not db_url:
    sys.exit(0)
try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        # Vérifier si alembic_version existe
        result = conn.execute(text(\"SELECT to_regclass('alembic_version')\"))
        row = result.fetchone()
        if row and row[0]:
            # Vérifier la version courante
            ver = conn.execute(text('SELECT version_num FROM alembic_version')).fetchone()
            if ver:
                print(f'Alembic version: {ver[0]}')
            else:
                # Stamper si vide
                print('Stamp head...')
        else:
            print('Nouvelle base — migrations fresh')
except Exception as e:
    print(f'Check failed: {e}', file=sys.stderr)
    sys.exit(0)
" 2>&1 || true
    
    if alembic upgrade head 2>&1; then
        echo "✅ Migrations OK"
    else
        echo "⚠️ Tentative stamp + retry..."
        alembic stamp head 2>&1 || true
        alembic upgrade head 2>&1 || echo "❌ Migrations échouées définitivement — démarrage quand même"
    fi
else
    echo "⚠️ DATABASE_URL non définie — skip migrations, SQLite par défaut"
fi

# ── 2. Démarrage Uvicorn ──
echo "🌐 Démarrage sur :${PORT:-8000}"
exec uvicorn umbra_main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --no-access-log \
    --timeout-keep-alive 65
