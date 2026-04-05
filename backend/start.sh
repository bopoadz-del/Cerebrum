#!/bin/bash
# Startup script for Cerebrum API with Ollama
# Runs both Ollama server and FastAPI application

set -e

echo "========================================"
echo "Cerebrum API + Ollama Startup"
echo "========================================"

# Default models to download
MODELS="${OLLAMA_MODELS:-gemma3:270m nomic-embed-text}"

# Start Ollama in background
echo "[1/4] Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "[2/4] Waiting for Ollama to be ready..."
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

# Pull models if they don't exist
echo "[3/4] Checking/pulling models: $MODELS"
for model in $MODELS; do
    if ! ollama list | grep -q "$model"; then
        echo "  → Pulling $model..."
        ollama pull $model
        echo "  ✓ $model ready"
    else
        echo "  ✓ $model already exists"
    fi
done

# List available models
echo "[4/4] Available models:"
ollama list | tail -n +2 | while read line; do
    echo "  → $line"
done

echo ""
echo "========================================"
echo "Starting FastAPI application..."
echo "========================================"

# Start FastAPI (foreground)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
