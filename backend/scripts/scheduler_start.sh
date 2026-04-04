#!/bin/bash
cd /app
celery -A app.tasks beat --loglevel=info
