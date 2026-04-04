# Cerebrum API - Uses pre-built ML base image
# Heavy ML deps (torch, chromadb, etc.) are cached in the base image
# This layer only installs lightweight app dependencies

FROM ghcr.io/bopoadz-del/cerebrum-ml-base:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PIP_CACHE_DIR=/data/pip-cache

WORKDIR /app

# Install PostgreSQL client (for pg_dump/pg_restore) and Tesseract OCR
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

# Add PostgreSQL 18 repo for matching pg_dump version
RUN wget --quiet -O /usr/share/keyrings/postgresql.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.asc] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y postgresql-client-18 && \
    rm -rf /var/lib/apt/lists/*

# Install lightweight app dependencies (ML deps already in base image)
# Use cache mount for pip packages (persistent across builds)
COPY requirements.txt .
RUN --mount=type=cache,target=/data/pip-cache \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Cache-bust layer
COPY .docker_nocache /tmp/.docker_nocache
COPY websocket_diagnostic.py .
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
