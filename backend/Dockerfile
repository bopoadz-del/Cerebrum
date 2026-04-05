# Use pre-built base image with Ollama + ML stack
FROM ghcr.io/bopoadz-del/cerebrum-ml-base:ollama

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_MODELS=/root/.ollama/models

WORKDIR /app

# Install PostgreSQL client (bookworm base)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy app code (requirements already installed in base)
COPY . .
RUN chmod +x start.sh

EXPOSE 8000 11434

CMD ["./start.sh"]
