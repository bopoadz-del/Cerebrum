# 🔥 Firebase Full Stack Deployment Guide

Deploy your entire Cerebrum application (backend + frontend) on Firebase infrastructure using **Cloud Run** for the backend and **Firebase Hosting** for the frontend.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FIREBASE INFRASTRUCTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Firebase Hosting (CDN)                      │   │
│  │         https://cerebrum-30d9c.web.app                  │   │
│  └──────────────┬────────────────────────────┬─────────────┘   │
│                 │                            │                  │
│        Static Files                API Requests                │
│    (frontend/dist/)             (/api/*, /docs)               │
│                 │                            │                  │
│                 ▼                            ▼                  │
│  ┌──────────────────────┐      ┌──────────────────────────┐   │
│  │   Static Content     │      │     Cloud Run            │   │
│  │   (Cached Globally)  │      │  (Python/FastAPI)        │   │
│  └──────────────────────┘      │  Auto-scaling            │   │
│                                │  Serverless              │   │
│                                └──────────────────────────┘   │
│                                             │                  │
│                              ┌──────────────┼──────────────┐   │
│                              ▼              ▼              ▼   │
│                         ┌────────┐    ┌─────────┐    ┌────────┐│
│                         │Cloud SQL│    │  Redis  │    │Secret  ││
│                         │(Postgres│    │(Memorystore│   │Manager ││
│                         └────────┘    └─────────┘    └────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Benefits

| Feature | Description |
|---------|-------------|
| 🌍 **Global CDN** | Static assets served from 200+ edge locations |
| ⚡ **Auto-scaling** | Backend scales from 0 to thousands of instances |
| 💰 **Pay-per-use** | Only pay for actual compute and requests |
| 🔒 **Managed** | No server maintenance, automatic security patches |
| 🔄 **CI/CD** | Automatic deployments on every push |
| 📱 **Unified Domain** | Single domain for frontend and API |

## Prerequisites

1. **Google Cloud SDK**: [Install gcloud](https://cloud.google.com/sdk/docs/install)
2. **Firebase CLI**: `npm install -g firebase-tools`
3. **GitHub CLI** (optional): `npm install -g gh`
4. **GCP Project**: `cerebrum-30d9c` (already set up)

## Quick Start

### Step 1: Run Setup Script

```bash
./scripts/setup-gcp.sh
```

This will:
- ✅ Enable required GCP APIs
- ✅ Configure Firebase
- ✅ Set up Secret Manager
- ✅ Create IAM service accounts
- ✅ Grant permissions

### Step 2: Generate Service Account Key

After running the setup script:

```bash
# Generate service account key for GitHub Actions
gcloud iam service-accounts keys create gcp-sa-key.json \
  --iam-account=github-actions@cerebrum-30d9c.iam.gserviceaccount.com
```

### Step 3: Add GitHub Secrets

Go to: `https://github.com/bopoadz-del/Cerebrum/settings/secrets/actions`

| Secret Name | Value | How to Get |
|-------------|-------|------------|
| `GCP_SA_KEY` | Content of `gcp-sa-key.json` | Generated above |
| `FIREBASE_SERVICE_ACCOUNT_CEREBRUM_30D9C` | Firebase service account JSON | [Firebase Console](https://console.firebase.google.com/project/cerebrum-30d9c/settings/serviceaccounts/adminsdk) |

### Step 4: Set Up Secrets in Secret Manager

```bash
# Add your database connection string
echo -n "postgresql+asyncpg://user:pass@host/db" | \
  gcloud secrets create database-url --data-file=-

# Add Redis URL
echo -n "redis://your-redis-url:6379/0" | \
  gcloud secrets create redis-url --data-file=-

# Generate and add secret key
openssl rand -hex 32 | \
  gcloud secrets create secret-key --data-file=-

# Add OpenAI API key
echo -n "sk-your-openai-key" | \
  gcloud secrets create openai-api-key --data-file=-
```

### Step 5: Deploy!

```bash
git push origin main
```

GitHub Actions will:
1. Build backend Docker image
2. Push to Google Container Registry
3. Deploy to Cloud Run
4. Build frontend
5. Deploy to Firebase Hosting
6. Configure URL rewrites

## URL Structure

| URL | Description |
|-----|-------------|
| `https://cerebrum-30d9c.web.app` | Main application (React) |
| `https://cerebrum-30d9c.web.app/api/*` | API endpoints (proxied to Cloud Run) |
| `https://cerebrum-30d9c.web.app/docs` | FastAPI Swagger UI |
| `https://cerebrum-30d9c.web.app/openapi.json` | OpenAPI schema |
| `https://cerebrum-landing.web.app` | Landing page |

## Firebase Configuration

### firebase.json

```json
{
  "hosting": {
    "public": "frontend/dist",
    "rewrites": [
      {
        "source": "/api/**",
        "run": {
          "serviceId": "cerebrum-backend",
          "region": "us-central1"
        }
      },
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

This configuration:
- Routes `/api/*` requests to Cloud Run
- Serves static files for all other routes
- Handles SPA routing (React Router)

## Cloud Run Configuration

### Resources
- **Memory**: 2 GiB
- **CPU**: 2 cores
- **Concurrency**: 80 requests per instance
- **Min instances**: 0 (scales to zero when not in use)
- **Max instances**: 10

### Environment Variables
- `ENVIRONMENT=production`
- `DEBUG=false`
- `CORS_ORIGINS` (set automatically)

### Secrets (from Secret Manager)
- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `OPENAI_API_KEY`

## Database Options

### Option 1: Cloud SQL (Recommended for GCP)

```bash
# Create PostgreSQL instance
gcloud sql instances create cerebrum-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-size=10GB

# Create database
gcloud sql databases create cerebrum --instance=cerebrum-db

# Get connection string
gcloud sql instances describe cerebrum-db --format="value(connectionName)"
```

### Option 2: Keep Render/Supabase

Continue using your existing database and update the `database-url` secret:

```bash
echo -n "your-render-postgres-url" | \
  gcloud secrets versions add database-url --data-file=-
```

## Monitoring & Logs

### View Cloud Run Logs

```bash
# Stream logs
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=cerebrum-backend"

# Or use Cloud Console
gcloud run services list
```

### Firebase Hosting Analytics

```bash
firebase hosting:clone cerebrum-30d9c:live cerebrum-30d9c:debug
google-chrome https://console.firebase.google.com/project/cerebrum-30d9c/hosting/main
```

## Troubleshooting

### Build Fails

```bash
# Test build locally
cd backend
docker build -f Dockerfile.cloudrun -t test-build .
```

### Cloud Run Service Not Accessible

```bash
# Check service status
gcloud run services describe cerebrum-backend --region us-central1

# Make sure it's public
gcloud run services add-iam-policy-binding cerebrum-backend \
  --region us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

### Secrets Not Accessible

```bash
# Verify secret exists
gcloud secrets list

# Check IAM permissions
gcloud secrets get-iam-policy database-url
```

### API Not Responding

```bash
# Test directly
curl https://cerebrum-backend-uc.a.run.app/health/live

# Test through Firebase
curl https://cerebrum-30d9c.web.app/api/health/live
```

## Cost Estimation

| Component | Estimated Monthly Cost |
|-----------|----------------------|
| Firebase Hosting | Free (10 GB/month) |
| Cloud Run | $0-50 (depends on traffic) |
| Cloud SQL (optional) | $7-25 |
| Secret Manager | Free (6 secrets) |
| **Total** | **$0-75/month** |

> Note: Cloud Run has a generous free tier: 2 million requests/month, 360,000 GB-seconds of memory, 180,000 vCPU-seconds of compute time per month.

## Migration from Render

If you're currently on Render and want to migrate:

1. **Database**: Keep using Render PostgreSQL or migrate to Cloud SQL
2. **Backend**: Deploy to Cloud Run (automatic via GitHub Actions)
3. **Frontend**: Deploy to Firebase Hosting (automatic via GitHub Actions)
4. **DNS**: Update your custom domain to point to Firebase Hosting
5. **Workers**: Consider Cloud Run Jobs or keep Celery workers on Render

## Additional Resources

- [Firebase Hosting + Cloud Run](https://firebase.google.com/docs/hosting/cloud-run)
- [Cloud Run Python Tutorial](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service)
- [GitHub Actions for Cloud Run](https://github.com/google-github-actions/deploy-cloudrun)

## Support

For issues or questions:
1. Check GitHub Actions logs
2. View Cloud Run logs: `gcloud logging tail`
3. Check Firebase Hosting status in console
