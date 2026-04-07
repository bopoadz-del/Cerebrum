FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# System dependencies + Tesseract OCR + PostgreSQL client + PDF support
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    tesseract-ocr tesseract-ocr-eng \
    postgresql-client \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# App code
COPY . .
RUN chmod +x start.sh

EXPOSE 8000

# Render overrides this, but we keep it for reference
CMD ["./start.sh"]
