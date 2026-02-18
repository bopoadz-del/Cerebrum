#!/bin/bash
cd /app
celery -A app.tasks worker --loglevel=info --concurrency=2
