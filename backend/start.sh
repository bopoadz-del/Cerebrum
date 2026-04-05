#!/bin/bash
# Startup script for Cerebrum API with Ollama

# Start Ollama in background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama ready!"
        break
    fi
    sleep 1
done

# Pull models on first run (Render ephemeral filesystem)
echo "Checking models..."
if ! ollama list | grep -q "gemma3:270m"; then
    echo "Pulling gemma3:270m (this may take a few minutes)..."
    ollama pull gemma3:270m
fi
if ! ollama list | grep -q "qwen2.5:0.5b"; then
    echo "Pulling qwen2.5:0.5b (this may take a few minutes)..."
    ollama pull qwen2.5:0.5b
fi

echo "Models ready. Starting FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
