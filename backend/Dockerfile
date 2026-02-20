FROM python:3.11-slim

# Disable AVX/SIMD instructions that cause SIGILL on some cloud providers
# These are read by numpy at runtime
ENV OPENBLAS_CORETYPE=ARMV8
ENV MKL_ENABLE_INSTRUCTIONS=SSE4_2
ENV OMP_NUM_THREADS=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set deployment environment
ENV ENVIRONMENT=production

WORKDIR /app
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Force rebuild: Fri Feb 20 16:01:54 UTC 2026
# Force rebuild: Fri Feb 20 16:36:53 UTC 2026
# Force rebuild Fri Feb 20 16:50:58 UTC 2026
# Force rebuild Fri Feb 20 17:20:06 UTC 2026
