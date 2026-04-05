# Cerebrum API - Uses pre-built ML base image with Ollama
# Heavy ML deps (torch, chromadb, etc.) are cached in the base image
# Ollama runs locally for air-gapped LLM inference
# 
# OPTIMIZED FOR RENDER: Heavy installs are early (cached), code is late (frequent changes)

FROM ghcr.io/bopoadz-del/cerebrum-ml-base:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PIP_CACHE_DIR=/data/pip-cache
ENV OLLAMA_HOST=http://localhost:11434

WORKDIR /app

# =============================================================================
# LAYER 1: System dependencies (rarely changes - heavily cached)
# =============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    lsb-release \
    curl \
    zstd \
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
# LAYER 2: Ollama installation (rarely changes - heavily cached)
# =============================================================================
RUN curl -fsSL https://ollama.com/install.sh | sh && \
    mkdir -p /root/.ollama/models

# =============================================================================
# LAYER 3: PostgreSQL client (rarely changes - cached)
# =============================================================================
RUN wget --quiet -O /usr/share/keyrings/postgresql.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.asc] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y postgresql-client-18 && \
    rm -rf /var/lib/apt/lists/*

# =============================================================================
# LAYER 4: Python dependencies (changes when requirements.txt changes - cached)
# =============================================================================
COPY requirements.txt .
RUN --mount=type=cache,target=/data/pip-cache \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# =============================================================================
# LAYER 5: Application code (changes frequently - NOT cached)
# =============================================================================
COPY .docker_nocache /tmp/.docker_nocache
COPY websocket_diagnostic.py .
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh
COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["/app/start.sh"]
