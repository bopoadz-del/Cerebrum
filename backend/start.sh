#!/bin/bash
echo "Starting Cerebrum API (migrations disabled)..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
