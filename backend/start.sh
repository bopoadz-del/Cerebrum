#!/bin/bash
# Startup script for Cerebrum API with Ollama
# Runs both Ollama server and FastAPI application

set -e

echo "========================================"
echo "Cerebrum API + Ollama Startup"
echo "========================================"

# Start Ollama in background
echo "[1/3] Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "[2/3] Waiting for Ollama to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✓ Ollama is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Ollama failed to start"
        exit 1
    fi
    sleep 1
done

# List available models
echo "[3/3] Available models:"
curl -s http://localhost:11434/api/tags | python3 -c "import sys, json; data=json.load(sys.stdin); print('\n'.join([f'  - {m[\"name\"]}' for m in data.get('models', [])]))" || echo "  (Could not list models)"

echo ""
echo "========================================"
echo "Starting FastAPI application..."
echo "========================================"

# Start FastAPI (foreground)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
