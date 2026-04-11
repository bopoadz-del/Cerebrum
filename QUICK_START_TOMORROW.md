# ⚡ Quick Start - Tomorrow Morning

## 1. Check Status (2 minutes)

```bash
# Check if everything is still running
curl https://cerebrum-30d9c.web.app/health/live

# Check backend logs
gcloud logging tail "resource.type=cloud_run_revision" --limit=10
```

## 2. Start Development

### Terminal 1: Backend
```bash
cd /workspaces/Cerebrum/backend
export GOOGLE_APPLICATION_CREDENTIALS=/workspaces/Cerebrum/gcp-sa-key.json

# Start Cloud SQL proxy for local dev
cloud-sql-proxy --port 5433 cerebrum-30d9c:us-central1:cerebrum-db &

# Run backend locally (for testing)
# python -m uvicorn app.main:app --reload --port 8000
```

### Terminal 2: Frontend
```bash
cd /workspaces/Cerebrum/frontend
npm run dev
# Open http://localhost:5173
```

## 3. Today's Top 3 Tasks

1. **Agent AI** → `backend/app/agent/enhanced_endpoints.py`
2. **File Storage** → Create GCS bucket + update `documents.py`
3. **Chat Persistence** → Database tables + `chat.py`

## 4. Deploy When Ready

```bash
# Frontend
cd /workspaces/Cerebrum/frontend
npm run build
firebase deploy --only hosting:frontend

# Backend
cd /workspaces/Cerebrum
gcloud builds submit --config=cloudbuild.yaml .
```

## 5. Key URLs

- **Live App:** https://cerebrum-30d9c.web.app
- **Firebase Console:** https://console.firebase.google.com/project/cerebrum-30d9c
- **Cloud Run:** https://console.cloud.google.com/run/detail/us-central1/cerebrum-backend

---

**See `TODO_TOMORROW.md` for full details!**
