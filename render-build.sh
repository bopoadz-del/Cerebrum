#!/usr/bin/env bash
set -euo pipefail

echo "[render-build] starting"

if [ -f "backend/requirements.txt" ]; then
  echo "[render-build] installing backend deps"
  python -m pip install -r backend/requirements.txt
fi

if [ -f "frontend/package.json" ]; then
  echo "[render-build] building frontend"
  cd frontend
  if command -v npm >/dev/null 2>&1; then
    npm ci --no-audit --no-fund
    npm run build
  else
    echo "[render-build] npm not found; skipping frontend build"
  fi
  cd ..
else
  echo "[render-build] no frontend found; skipping"
fi

echo "[render-build] done"
