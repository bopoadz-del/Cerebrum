# =============================================================================
# Cerebrum AI Platform - Production Dockerfile
# Multi-stage build for optimized image size and security
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# Installs dependencies and builds application
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# Minimal runtime image with only necessary dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app \
    PORT=8000

# Install runtime dependencies (bash + postgresql-client for render_start.sh)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    bash \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR $APP_HOME

# Copy application code
COPY --chown=appuser:appgroup app/ ./app/
COPY --chown=appuser:appgroup scripts/ ./scripts/
COPY --chown=appuser:appgroup data/ ./data/

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health/live || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
