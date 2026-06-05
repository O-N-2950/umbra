# ═══════════════════════════════════════════════════════════
# UMBRA — Dockerfile Jelastic Infomaniak
# Python 3.12 slim, multi-stage, optimisé taille + sécurité
# Image finale : ~280 MB
# ═══════════════════════════════════════════════════════════

# ── Stage 1: Build deps ──────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Compiler les dépendances natives (psycopg2, cryptography, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime deps (libpq pour psycopg2, curl pour healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copier les packages Python depuis le builder
COPY --from=builder /root/.local /root/.local

# Copier le code source
COPY backend/ .

# Utilisateur non-root (sécurité Jelastic)
RUN useradd -m -u 1000 umbra && chown -R umbra:umbra /app
USER umbra

# PATH pour les packages user
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Healthcheck Jelastic — doit répondre < 5s (utilise /ping, pas /health)
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/ping || exit 1

EXPOSE 8000

# Point d'entrée
CMD ["sh", "entrypoint.sh"]
