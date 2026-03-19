FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get purge -y build-essential pkg-config && \
    apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY backend/ .
RUN chmod +x entrypoint.sh

RUN mkdir -p /data && \
    groupadd -r umbra && \
    useradd -r -g umbra -d /app -s /sbin/nologin umbra && \
    chown -R umbra:umbra /app /data

USER umbra

ENV ENVIRONMENT=production
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
