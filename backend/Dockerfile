# Cerebrum API - Production Dockerfile
# Uses pre-built base image with Ollama + models baked in
#
# CACHE STRATEGY:
# - Base image: Ollama + Python ML stack (rarely changes)
# - Layer 1: PostgreSQL client (rarely changes)
# - Layer 2: Python deps (requirements.txt changes)
# - Layer 3: App code (daily changes - only this layer rebuilds!)
#
# Build context optimization: Use .dockerignore to exclude:
# - .git/, __pycache__/, *.pyc
# - node_modules/, .env files
# - Tests, docs, local dev files

FROM ghcr.io/bopoadz-del/cerebrum-ml-base:ollama

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV OLLAMA_HOST=0.0.0.0:11434

WORKDIR /app

# =============================================================================
# LAYER 1: PostgreSQL client (CACHE HIT 99% of builds)
# Only rebuilds if PostgreSQL version changes
# =============================================================================
RUN wget --quiet -O /usr/share/keyrings/postgresql.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.asc] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client-18 && \
    rm -rf /var/lib/apt/lists/*

# =============================================================================
# LAYER 2: Python packages (CACHE HIT 90% of builds)
# Only rebuilds when requirements.txt changes
# BuildKit cache mount persists pip cache across builds
# =============================================================================
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# LAYER 3: Application code (ALWAYS rebuilds)
# This is the only layer that changes on every deploy
# Keep this as small as possible
# =============================================================================
COPY . .

# Make startup script executable
RUN chmod +x start.sh

EXPOSE 8000 11434

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["./start.sh"]
# Base image: Sun Apr  5 08:12:20 PM CST 2026
