# Cerebrum API - Production Dockerfile
# Optimized for Render with aggressive caching
# 
# CACHE STRATEGY:
# - Layer 1-2: System deps (months between changes)
# - Layer 3: Python deps (weeks between changes)  
# - Layer 4: App code (daily changes)
#
# Build context optimization: Use .dockerignore to exclude:
# - .git/, __pycache__/, *.pyc
# - node_modules/, .env files
# - Tests, docs, local dev files

FROM ghcr.io/bopoadz-del/cerebrum-ml-base:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

WORKDIR /app

# =============================================================================
# LAYER 1: System dependencies (CACHE HIT 99% of builds)
# Only rebuilds if we add new system packages
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
# LAYER 2: PostgreSQL (CACHE HIT 99% of builds)
# Only rebuilds if PostgreSQL version changes
# =============================================================================
RUN wget --quiet -O /usr/share/keyrings/postgresql.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.asc] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y postgresql-client-18 && \
    rm -rf /var/lib/apt/lists/*

# =============================================================================
# LAYER 3: Python packages (CACHE HIT 90% of builds)
# Only rebuilds when requirements.txt changes
# BuildKit cache mount persists pip cache across builds
# =============================================================================
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# LAYER 4: Application code (ALWAYS rebuilds)
# This is the only layer that changes on every deploy
# Keep this as small as possible
# =============================================================================
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
