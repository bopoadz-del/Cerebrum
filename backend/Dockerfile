FROM python:3.11-slim as builder

WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

# Install runtime libs
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder (fix permissions)
COPY --from=builder /root/.local /home/appuser/.local
RUN chown -R root:root /home/appuser/.local && chmod -R 755 /home/appuser/.local

# Set environment to find packages
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/home/appuser/.local/lib/python3.11/site-packages:$PYTHONPATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy app
COPY . .

# Switch to non-root
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
