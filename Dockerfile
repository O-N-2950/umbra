# ═══════════════════════════════════════════════════════════
# UMBRA — Image Docker pour Jelastic Cloud Infomaniak
# Publiée sur GHCR: ghcr.io/o-n-2950/umbra:latest
# ═══════════════════════════════════════════════════════════

# ── Stage 1: Build ───────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev libffi-dev libssl-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Packages Python
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Code source
COPY backend/ .

# Répertoire static (UI React UMBRA)
RUN mkdir -p /app/static

# Healthcheck ultra-rapide /ping (pas /health qui appelle Gemini)
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/ping || exit 1

EXPOSE 8000

CMD ["sh", "entrypoint.sh"]
