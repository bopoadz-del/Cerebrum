#!/bin/bash
set -euo pipefail

echo "=== Cerebrum AI Startup ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Environment: ${ENVIRONMENT:-production}"
echo

echo "[1/5] Validating environment..."
: "${DATABASE_URL:?FATAL: DATABASE_URL not set}"
: "${SECRET_KEY:?FATAL: SECRET_KEY not set}"
: "${REDIS_URL:?FATAL: REDIS_URL not set}"
echo "OK: Environment variables validated"
echo

echo "[2/5] Verifying Redis connection..."
python3 << 'PY'
import os, sys, redis
try:
    r = redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
    print("OK: Redis connection verified")
except Exception as e:
    print(f"ERROR: Redis connection failed: {e}", file=sys.stderr)
    sys.exit(1)
PY
echo

echo "[3/5] Starting Ollama (Local LLM)..."
# Start Ollama in the background
ollama serve &
OLLAMA_PID=$!
echo "Ollama started with PID: $OLLAMA_PID"

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "OK: Ollama is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "WARNING: Ollama did not become ready in time, continuing anyway..."
    fi
    sleep 1
done
echo

echo "[4/5] Pulling required models..."
# Pull the default model if not already present
ollama pull gemma3:270m || echo "WARNING: Failed to pull gemma3:270m"
echo

echo "[5/5] Running WebSocket diagnostic..."
python3 /app/websocket_diagnostic.py || echo "WARNING: WebSocket diagnostic failed"
echo

echo "=== Starting Uvicorn server ==="
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --proxy-headers \
  --workers "${WEB_CONCURRENCY:-1}" \
  --access-log \
  --log-level info
