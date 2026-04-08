# Cerebrum Prototype - Smoke Test Checklist

## Overview
This checklist provides a quick verification that the Cerebrum prototype is ready for deployment or demonstration.

## Quick Start

```bash
# Run the automated validation script
python scripts/validate_prototype.py

# Or run with verbose output
python scripts/validate_prototype.py --verbose
```

## Manual Smoke Test Checklist

### Pre-Flight Checks

- [ ] **Environment Variables Set**
  - [ ] `SECRET_KEY` (min 32 chars)
  - [ ] `DATABASE_URL` (PostgreSQL)
  - [ ] `REDIS_URL` (Redis connection)
  - [ ] `DEBUG=false` (for production)

- [ ] **Dependencies Installed**
  - [ ] Python 3.11+
  - [ ] PostgreSQL 14+
  - [ ] Redis 6+
  - [ ] Python packages: `pip install -r backend/requirements.txt`

### Infrastructure Checks

- [ ] **Database**
  - [ ] PostgreSQL service running
  - [ ] Database `cerebrum` exists
  - [ ] Migrations applied: `alembic upgrade head`
  - [ ] Can connect: `psql $DATABASE_URL -c "SELECT 1"`

- [ ] **Redis**
  - [ ] Redis service running
  - [ ] Can connect: `redis-cli ping` returns `PONG`
  - [ ] Multiple DBs accessible (0-3)

### Application Startup

- [ ] **Backend Starts**
  ```bash
  cd backend
  uvicorn app.main:app --host 0.0.0.0 --port 8000
  ```
  - [ ] No import errors
  - [ ] Database connection successful
  - [ ] Redis connection successful
  - [ ] Rate limiter initialized

- [ ] **Health Endpoints Respond**
  - [ ] `GET /health` → 200 OK
  - [ ] `GET /health/live` → 200 OK (liveness)
  - [ ] `GET /health/ready` → 200 or 503 (readiness)
  - [ ] `GET /healthz` → 200 OK (K8s liveness)
  - [ ] `GET /readyz` → 200 or 503 (K8s readiness)

### Core Functionality

- [ ] **14 Agent Layers Load**
  - [ ] coding
  - [ ] registry
  - [ ] validation
  - [ ] hotswap
  - [ ] healing
  - [ ] prompts
  - [ ] triggers
  - [ ] economics
  - [ ] vdc
  - [ ] edge
  - [ ] portal
  - [ ] enterprise
  - [ ] connectors
  - [ ] monitoring

- [ ] **API Endpoints Accessible**
  - [ ] `GET /api` → Lists all v1 endpoints
  - [ ] `GET /api/v1/auth/me` → 401 (protected)
  - [ ] `POST /api/v1/auth/login` → 422 (validation error, not 500)

- [ ] **Self-Modification System**
  - [ ] Git repository accessible
  - [ ] Can create checkpoint commits
  - [ ] Layer template generation works
  - [ ] File modification capability verified

### Background Tasks

- [ ] **Celery Worker**
  ```bash
  cd backend
  celery -A app.tasks worker --loglevel=info
  ```
  - [ ] Worker starts without errors
  - [ ] Connects to Redis broker
  - [ ] Registers tasks

- [ ] **Celery Beat (Scheduler)**
  ```bash
  cd backend
  celery -A app.tasks beat --loglevel=info
  ```
  - [ ] Beat starts
  - [ ] Scheduled tasks loaded

### Integration Checks

- [ ] **Run Existing Tests**
  ```bash
  cd backend
  pytest tests/test_smoke.py -v
  ```
  - [ ] All smoke tests pass
  - [ ] No critical test failures

- [ ] **Frontend (if applicable)**
  - [ ] `npm install` completes
  - [ ] `npm run build` succeeds
  - [ ] Can connect to backend API

## Troubleshooting Common Issues

### Database Connection Failed
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Create database if missing
createdb cerebrum

# Run migrations
cd backend
alembic upgrade head
```

### Redis Connection Failed
```bash
# Check Redis is running
redis-cli ping

# Start Redis
redis-server
```

### Import Errors
```bash
# Ensure correct Python path
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Secret Key Issues
```bash
# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Set it
export SECRET_KEY="<generated-key>"
```

## Sign-Off

| Check | Status | Notes |
|-------|--------|-------|
| Automated validation passed | ☐ | Run `python scripts/validate_prototype.py` |
| Database connectivity verified | ☐ | |
| Redis connectivity verified | ☐ | |
| All 14 layers loaded | ☐ | |
| API endpoints responding | ☐ | |
| Celery configured | ☐ | |
| Self-modification functional | ☐ | |
| Existing tests passing | ☐ | |

**Overall Status:** ☐ GO / ☐ NO-GO

**Validated By:** _________________ **Date:** _________________

## Post-Validation Actions

If validation passes:
1. ✅ Proceed with deployment
2. ✅ Monitor logs for any runtime issues
3. ✅ Set up health check alerts

If validation fails:
1. ❌ Review failed checks above
2. ❌ Fix critical issues
3. ❌ Re-run validation
4. ❌ Document workarounds for non-critical issues
