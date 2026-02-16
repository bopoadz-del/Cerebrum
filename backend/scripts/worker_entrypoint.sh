#!/usr/bin/env bash
set -euo pipefail

if [ "${NOOP_WORKER:-false}" = "true" ]; then
  echo "[worker_entrypoint] NOOP_WORKER=true -> running noop worker"
  exec python scripts/noop_worker.py
fi

echo "[worker_entrypoint] running: $*"
exec "$@"
