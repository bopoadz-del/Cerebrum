# 📝 TODO - Continue from Here

**Date:** 2026-04-11  
**Status:** Backend deployed, file upload needs testing, frontend on Firebase

---

## 🔥 URGENT - File Upload Issue

**Problem:** File upload to GCS returns 500 error  
**Status:** Fixed signed URL generation, needs testing  
**Last Change:** `56adcf1` - Use signed URLs instead of public ACLs

### Test Command:
```bash
curl -X POST "https://cerebrum-backend-rtmyy2f3na-uc.a.run.app/api/v1/documents/upload/public" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/test.txt"
```

### If Still Failing:
1. Check logs: `gcloud logging read --limit=50`
2. May need to add `roles/storage.admin` to service account
3. Or use uniform bucket-level access instead of ACLs

---

## ✅ COMPLETED TODAY

### Backend (Cloud Run)
- ✅ DeepSeek AI integration (`/api/v1/agent/*`)
- ✅ DuckDuckGo web search (`/api/v1/web-search/*`)
- ✅ Chat persistence (messages table)
- ✅ GCS bucket created (`cerebrum-documents-30d9c`)
- ⚠️ File upload (deployed, needs testing)
- ✅ Database migrations (messages, file_uploads tables)

### Frontend (Firebase)
- ✅ Deployed to: https://cerebrum-30d9c.web.app
- ✅ API proxy configured

---

## 🔑 ACCESS & KEYS

### SSH Keys
```bash
# GitHub SSH key
~/.ssh/github_ed25519      # For git push
~/.ssh/github_ed25519.pub  # Public key

# Render SSH key  
~/.ssh/render_ed25519      # For Render deploys
~/.ssh/render_ed25519.pub  # Public key

# SSH config
cat ~/.ssh/config
```

### API Keys (Secret Manager)
```bash
# View secrets
gcloud secrets list --project=cerebrum-30d9c

# Get values (if needed)
gcloud secrets versions access latest --secret=deepseek-api-key --project=cerebrum-30d9c
gcloud secrets versions access latest --secret=database-url --project=cerebrum-30d9c
gcloud secrets versions access latest --secret=redis-url --project=cerebrum-30d9c
gcloud secrets versions access latest --secret=secret-key --project=cerebrum-30d9c
```

### Service Account
```bash
# Key location
/workspaces/Cerebrum/gcp-sa-key.json

# Set env var
export GOOGLE_APPLICATION_CREDENTIALS=/workspaces/Cerebrum/gcp-sa-key.json
```

---

## 🛠️ COMMON COMMANDS

### Deploy Backend
```bash
cd /workspaces/Cerebrum

# Build
gcloud builds submit --config=cloudbuild.yaml .

# Deploy (wait for build SUCCESS first)
gcloud run deploy cerebrum-backend \
  --image gcr.io/cerebrum-30d9c/cerebrum-backend:latest \
  --region=us-central1 --project=cerebrum-30d9c \
  --platform=managed --revision-suffix=fix \
  --set-env-vars="ENVIRONMENT=production,DEBUG=false" \
  --update-secrets="DEEPSEEK_API_KEY=deepseek-api-key:latest,DATABASE_URL=database-url:2,REDIS_URL=redis-url:2,SECRET_KEY=secret-key:latest" \
  --timeout=300 --memory=1Gi --cpu=1
```

### Deploy Frontend (Firebase)
```bash
cd /workspaces/Cerebrum
export GOOGLE_APPLICATION_CREDENTIALS=/workspaces/Cerebrum/gcp-sa-key.json
firebase deploy --only hosting:frontend --project cerebrum-30d9c
```

### Database Migration
```bash
cd /workspaces/Cerebrum/backend
export GOOGLE_APPLICATION_CREDENTIALS=/workspaces/Cerebrum/gcp-sa-key.json

# Start proxy
cloud-sql-proxy --port 5433 cerebrum-30d9c:us-central1:cerebrum-db &

# Get DB URL
DB_URL=$(gcloud secrets versions access latest --secret=database-url --project=cerebrum-30d9c)
PROXY_URL=$(echo "$DB_URL" | sed 's|/cloudsql/cerebrum-30d9c:us-central1:cerebrum-db|localhost:5433|')
SYNC_URL=$(echo "$PROXY_URL" | sed 's/postgresql+asyncpg/postgresql/')

# Run migration
export DATABASE_URL="$SYNC_URL"
alembic upgrade head

# Kill proxy
pkill cloud-sql-proxy
```

### Check Logs
```bash
# Latest logs
gcloud logging read "resource.labels.service_name=cerebrum-backend" --limit=20

# Errors only
gcloud logging read "resource.labels.service_name=cerebrum-backend AND severity>=ERROR" --limit=20
```

---

## 🎯 TOMORROW'S PRIORITIES

1. **Fix File Upload** ⚠️ KNOWN ISSUE
   - **Error:** `AttributeError: you need a private key to sign credentials`
   - **Problem:** Cloud Run compute credentials can't sign URLs
   - **Solution Options:**
     - Option A: Mount service account JSON key to Cloud Run
     - Option B: Use public bucket with uniform access (no signed URLs)
     - Option C: Use a separate service with the JSON key
   
   **Quick Fix (Option B):**
   ```bash
   # Make bucket publicly readable
   gsutil uniformbucketlevelaccess set on gs://cerebrum-documents-30d9c
   gsutil iam ch allUsers:objectViewer gs://cerebrum-documents-30d9c
   
   # Then modify code to return blob.public_url without signing
   # Remove: blob.generate_signed_url(...)
   # Use: return blob.public_url
   ```

2. **Frontend Testing**
   - Test file upload from UI
   - Test chat with file attachments
   - Test DeepSeek AI responses

3. **Optional Enhancements**
   - Add file size limit validation
   - Add file type whitelist
   - Add image preview in chat

---

## 🔗 LIVE URLS

| Service | URL |
|---------|-----|
| Frontend | https://cerebrum-30d9c.web.app |
| Backend | https://cerebrum-backend-rtmyy2f3na-uc.a.run.app |
| Health | https://cerebrum-backend-rtmyy2f3na-uc.a.run.app/health/live |
| Agent Status | https://cerebrum-backend-rtmyy2f3na-uc.a.run.app/api/v1/agent/v2/status/enhanced |
| Web Search | https://cerebrum-backend-rtmyy2f3na-uc.a.run.app/api/v1/web-search/status |

---

## 📁 IMPORTANT FILES

- `backend/app/api/v1/endpoints/documents.py` - File upload logic
- `backend/app/agent/enhanced_endpoints.py` - AI agent endpoints
- `backend/app/services/ai_service.py` - DeepSeek service
- `backend/alembic/versions/` - Database migrations
- `firebase.json` - Firebase hosting config

---

**Last Updated:** 2026-04-11  
**Last Commit:** 56adcf1 - Use signed URLs instead of public ACLs
