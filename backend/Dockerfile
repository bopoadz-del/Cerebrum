FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_MODELS=/root/.ollama/models

WORKDIR /app

# System dependencies + Tesseract OCR + PostgreSQL client + zstd for Ollama
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates zstd \
    tesseract-ocr tesseract-ocr-eng \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .
RUN chmod +x start.sh

EXPOSE 8000 11434

# Render overrides this, but we keep it for reference
CMD ["./start.sh"]
