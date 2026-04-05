FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_MODELS=/root/.ollama/models
ENV PATH="/usr/local/bin:${PATH}"

WORKDIR /app

# System dependencies + Tesseract OCR + lsb-release for PostgreSQL repo
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl ca-certificates lsb-release \
    tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama from .tgz archive (contains bin/ollama and lib/)
RUN curl -fsSL https://github.com/ollama/ollama/releases/download/v0.5.7/ollama-linux-amd64.tgz -o /tmp/ollama.tgz \
    && tar -xzf /tmp/ollama.tgz -C /usr/local \
    && rm /tmp/ollama.tgz \
    && ln -sf /usr/local/bin/ollama /usr/local/bin/ollama-cli \
    && ollama --version

# PostgreSQL client
RUN wget --quiet -O /usr/share/keyrings/postgresql.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/keyrings/postgresql.asc] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-18 \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .
RUN chmod +x start.sh

EXPOSE 8000 11434

CMD ["./start.sh"]
