# Pre-Deployment Final Checklist

## ✅ Status: READY FOR DEPLOYMENT

---

## 1. Render Blueprint (render.yaml)

| Check | Status |
|-------|--------|
| Backend service (cerebrum-api) configured | ✅ |
| Docker runtime with correct paths | ✅ |
| Database URL from cerebrum-db | ✅ |
| Redis URL from cerebrum-redis keyvalue | ✅ |
| Health check at /health/live | ✅ |
| Migration script (render_start.sh) | ✅ |
| Frontend static site with VITE_API_URL | ✅ |
| Celery workers (fast/slow/beat) | ✅ |
| DB backup cron job | ✅ |

---

## 2. Backend Configuration

| Check | Status |
|-------|--------|
| Dockerfile multi-stage build | ✅ |
| Python 3.11 runtime | ✅ |
| PostgreSQL client installed | ✅ |
| Bash available for scripts | ✅ |
| Data directory copied | ✅ |
| Non-root user (appuser) | ✅ |
| Healthcheck in Dockerfile | ✅ |

---

## 3. Database Migrations

| Check | Status |
|-------|--------|
| Alembic initialized | ✅ |
| Migration 001 (base schema) | ✅ |
| Migration 002 (conversation sessions) | ✅ |
| Migration chain correct (002 → 001) | ✅ |
| Advisory lock in env.py | ✅ |

---

## 4. API Endpoints

| Check | Status |
|-------|--------|
| Health /health/live | ✅ |
| Health /health/ready | ✅ |
| Health /healthz (K8s) | ✅ |
| Health /readyz (K8s) | ✅ |
| Auth /api/v1/auth/* | ✅ |
| Formulas /api/v1/formulas/* | ✅ |
| Sessions /api/v1/sessions/* | ✅ |
| Connectors /api/v1/connectors/* | ✅ |
| All routers wired in main.py | ✅ |

---

## 5. Security

| Check | Status |
|-------|--------|
| JWT implementation (PyJWT) | ✅ |
| Password hashing (bcrypt) | ✅ |
| CORS configured | ✅ |
| Rate limiting (SlowAPI) | ✅ |
| Security headers middleware | ✅ |
| Secret key generation in render.yaml | ✅ |

---

## 6. Frontend

| Check | Status |
|-------|--------|
| package.json exists | ✅ |
| package-lock.json exists | ✅ |
| VITE_API_URL env var configured | ✅ |
| API base URL builder correct | ✅ |
| ManualChunks fixed (no react-hook-form) | ✅ |
| Build command ready | ✅ |

---

## 7. Workers/Queues

| Check | Status |
|-------|--------|
| Celery configuration | ✅ |
| Redis broker setup | ✅ |
| Fast queue worker | ✅ |
| Slow queue worker | ✅ |
| Beat scheduler | ✅ |
| Trigger events queue | ✅ |

---

## 8. Git Status

| Check | Status |
|-------|--------|
| All changes committed | ✅ |
| Pushed to origin/main | ✅ |
| No uncommitted changes | ✅ |

---

## Deployment Steps

1. **Push to GitHub** (already done)
   ```bash
   git push origin main
   ```

2. **Connect to Render**
   - Go to https://dashboard.render.com
   - Click "New" → "Blueprint"
   - Connect GitHub repository
   - Select `render.yaml`

3. **Deploy Services**
   Render will create:
   - PostgreSQL database (cerebrum-db)
   - Redis keyvalue (cerebrum-redis)
   - Web service (cerebrum-api)
   - Static site (cerebrum-frontend)
   - 3 Celery workers
   - Cron job (db-backup)

4. **Verify Deployment**
   - Check health endpoint: `https://cerebrum-api.onrender.com/health/live`
   - Check ready endpoint: `https://cerebrum-api.onrender.com/health/ready`
   - Check API docs: `https://cerebrum-api.onrender.com/api/docs` (if DEBUG=true)

---

## Environment Variables (Auto-set by Render)

| Variable | Source |
|----------|--------|
| DATABASE_URL | From cerebrum-db |
| REDIS_URL | From cerebrum-redis |
| SECRET_KEY | Auto-generated |
| VITE_API_URL | From cerebrum-api RENDER_EXTERNAL_URL |

---

## Post-Deployment Verification

```bash
# Test health endpoint
curl https://<your-api>.onrender.com/health/live

# Test auth endpoint
curl -X POST https://<your-api>.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'

# Test formulas endpoint
curl https://<your-api>.onrender.com/api/v1/formulas
```

---

**Ready for deployment!** ✅
