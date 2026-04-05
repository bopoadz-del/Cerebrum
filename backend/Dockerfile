# Cerebrum API - Uses pre-built ML base image
# Heavy ML deps (torch, chromadb, etc.) are cached in the base image
# This layer only installs lightweight app dependencies
# 
# CACHING STRATEGY (Render optimized):
# 1. System deps (rarely change) - heavily cached
# 2. PostgreSQL client (rarely change) - cached
# 3. Python deps (only when requirements.txt changes) - cached
# 4. App code (changes frequently) - NOT cached

FROM ghcr.io/bopoadz-del/cerebrum-ml-base:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PIP_CACHE_DIR=/data/pip-cache

WORKDIR /app

# =============================================================================
# LAYER 1: System dependencies (rarely changes - heavily cached)
# =============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    lsb-release \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-spa \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    tesseract-ocr-jpn \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# LAYER 2: PostgreSQL client (rarely changes - cached)
# =============================================================================
RUN wget --quiet -O /usr/share/keyrings/postgresql.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.asc] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y postgresql-client-18 && \
    rm -rf /var/lib/apt/lists/*

# =============================================================================
# LAYER 3: Python dependencies (changes when requirements.txt changes - cached)
# =============================================================================
COPY requirements.txt .
RUN --mount=type=cache,target=/data/pip-cache \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# =============================================================================
# LAYER 4: Application code (changes frequently - NOT cached)
# =============================================================================
COPY .docker_nocache /tmp/.docker_nocache
COPY websocket_diagnostic.py .
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
