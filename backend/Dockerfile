# Cerebrum API - Uses pre-built ML base image with Ollama
# Heavy ML deps (torch, chromadb, etc.) are cached in the base image
# Ollama runs locally for air-gapped LLM inference

FROM ghcr.io/bopoadz-del/cerebrum-ml-base:latest

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PIP_CACHE_DIR=/data/pip-cache
ENV OLLAMA_HOST=http://localhost:11434

WORKDIR /app

# Install PostgreSQL client, Tesseract OCR, and Ollama dependencies
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

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Add PostgreSQL 18 repo for matching pg_dump version
RUN wget --quiet -O /usr/share/keyrings/postgresql.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.asc] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y postgresql-client-18 && \
    rm -rf /var/lib/apt/lists/*

# Pull small Ollama models (gemma3:270m is ~200MB, qwen2.5:0.5b is ~400MB)
# Start Ollama temporarily to pull models
RUN ollama serve & \
    sleep 5 && \
    ollama pull gemma3:270m && \
    ollama pull qwen2.5:0.5b && \
    pkill ollama

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

# Create startup script that runs Ollama + FastAPI
RUN echo '#!/bin/bash\n\
# Start Ollama in background\n\
ollama serve &\n\
OLLAMA_PID=$!\n\
\n\
# Wait for Ollama to be ready\n\
echo "Waiting for Ollama..."\n\
for i in {1..30}; do\n\
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then\n\
        echo "Ollama ready!"\n\
        break\n\
    fi\n\
    sleep 1\n\
done\n\
\n\
# Start FastAPI\n\
exec uvicorn app.main:app --host 0.0.0.0 --port 8000\n\
' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["/app/start.sh"]
