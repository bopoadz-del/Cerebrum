# Cerebrum Prototype - Startup Procedure

This document describes the complete startup procedure for the Cerebrum AI platform prototype.

## Prerequisites

### System Requirements
- Python 3.11 or higher
- PostgreSQL 14 or higher
- Redis 6 or higher
- Git (for self-modification features)

### Environment Setup

1. **Clone/Navigate to Repository**
   ```bash
   cd /root/.openclaw/workspace/cerebrum-fix
   ```

2. **Set Required Environment Variables**
   ```bash
   export SECRET_KEY="your-32-char-minimum-secret-key-here"
   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/cerebrum"
   export REDIS_URL="redis://localhost:6379/0"
   export DEBUG="true"  # Set to "false" for production
   ```

3. **Optional Environment Variables**
   ```bash
   export CORS_ORIGINS="http://localhost:3000,https://your-frontend.com"
   export SENTRY_DSN="https://..."  # For error tracking
   export BRAVE_API_KEY="..."       # For web search
   ```

## Step-by-Step Startup

### Step 1: Start Infrastructure Services

**PostgreSQL**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# If not running, start it
sudo systemctl start postgresql

# Verify connection
psql $DATABASE_URL -c "SELECT version();"
```

**Redis**
```bash
# Check if Redis is running
redis-cli ping

# If not running, start it
redis-server

# Or with specific config
redis-server /etc/redis/redis.conf
```

### Step 2: Database Setup

**Create Database (if not exists)**
```bash
# Create the database
psql -U postgres -c "CREATE DATABASE cerebrum;"

# Or using environment variable
psql $DATABASE_URL -c "SELECT 1;"
```

**Apply Migrations**
```bash
cd backend

# Check current migration status
alembic current

# Apply all pending migrations
alembic upgrade head

# Verify
alembic history --verbose
```

### Step 3: Install Dependencies

```bash
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 4: Validate Installation

**Run the validation script**
```bash
cd /root/.openclaw/workspace/cerebrum-fix
python scripts/validate_prototype.py --verbose
```

Expected output:
```
======================================================================
CEREBRUM PROTOTYPE VALIDATION
======================================================================
...
✅ ALL CHECKS PASSED
```

### Step 5: Start the Application

**Development Mode (with auto-reload)**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Production Mode**
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Using Gunicorn (Production)**
```bash
cd backend
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Step 6: Verify Startup

**Check Application Logs**
Look for these key startup messages:
```
INFO:     Starting Cerebrum AI Platform
INFO:     Security configuration validated
INFO:     Rate limiter storage (Redis) verified
INFO:     Database connection established
INFO:     Initializing trigger engine
INFO:     Trigger managers initialized
INFO:     Application startup complete
```

**Test Health Endpoints**
```bash
# In another terminal
curl http://localhost:8000/health
```

Expected response:
```json
{
  "ok": true,
  "service": "cerebrum-api",
  "uptime_seconds": 5.42
}
```

### Step 7: Start Background Workers (Optional)

**Celery Worker**
```bash
cd backend
celery -A app.tasks worker --loglevel=info --queues=celery_fast,celery_slow
```

**Celery Beat (Scheduler)**
```bash
cd backend
celery -A app.tasks beat --loglevel=info
```

## Configuration Reference

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | Required | 32+ character secret for encryption |
| `DATABASE_URL` | Required | PostgreSQL connection string |
| `REDIS_URL` | Required | Redis connection string |
| `DEBUG` | `false` | Enable debug mode |
| `ENVIRONMENT` | `development` | Environment name |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

### Redis Databases

| DB | Purpose |
|----|---------|
| 0 | Cache |
| 1 | Queue (Celery) |
| 2 | Sessions |
| 3 | Rate Limiting |

### Celery Queues

| Queue | Purpose |
|-------|---------|
| `celery_fast` | Quick tasks (OCR, notifications) |
| `celery_slow` | Heavy tasks (BIM, ML processing) |

## Troubleshooting Startup

### Issue: "SECRET_KEY must be at least 32 characters"
**Solution:**
```bash
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

### Issue: "Database connection failed"
**Solution:**
```bash
# Verify PostgreSQL is running
sudo systemctl start postgresql

# Check connection string format
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/cerebrum"
```

### Issue: "Rate limiter storage (Redis) unavailable"
**Solution:**
```bash
# Start Redis
redis-server

# Verify
redis-cli ping  # Should return PONG
```

### Issue: Import errors when starting
**Solution:**
```bash
# Ensure you're in the backend directory
cd /root/.openclaw/workspace/cerebrum-fix/backend

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: Migration errors
**Solution:**
```bash
# Reset migrations (WARNING: Destroys data)
dropdb cerebrum
createdb cerebrum
alembic upgrade head

# Or create migration
cd backend
alembic revision --autogenerate -m "fix_migration"
alembic upgrade head
```

## Docker Startup (Alternative)

If using Docker:

```bash
# Build and start all services
docker-compose up --build

# Or in detached mode
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop
docker-compose down
```

## Health Check Commands

```bash
# Full validation
python scripts/validate_prototype.py

# Quick health check
curl http://localhost:8000/health/live

# Readiness check (includes DB/Redis)
curl http://localhost:8000/health/ready

# API info
curl http://localhost:8000/api

# Metrics
curl http://localhost:8000/metrics
```

## Startup Verification Script

Create a `startup.sh` script:

```bash
#!/bin/bash
set -e

echo "Starting Cerebrum AI Platform..."

# Load environment
export $(grep -v '^#' .env | xargs)

# Start services
echo "Checking PostgreSQL..."
pg_isready || { echo "PostgreSQL not ready"; exit 1; }

echo "Checking Redis..."
redis-cli ping || { echo "Redis not ready"; exit 1; }

# Run migrations
echo "Applying migrations..."
cd backend
alembic upgrade head

# Validate
echo "Running validation..."
python ../scripts/validate_prototype.py

# Start application
echo "Starting application..."
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Make it executable:
```bash
chmod +x startup.sh
./startup.sh
```
