FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_MODELS=/root/.ollama/models

WORKDIR /app

# System dependencies + Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama (download binary directly, no install script)
RUN curl -fsSL https://ollama.com/download/ollama-linux-amd64 -o /usr/local/bin/ollama \
    && chmod +x /usr/local/bin/ollama

# Install PostgreSQL client from Debian repos (not PGDG)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

EXPOSE 8000 11434

# Start Ollama + FastAPI via main.py lifespan
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
