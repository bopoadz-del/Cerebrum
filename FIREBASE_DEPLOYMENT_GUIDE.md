# 🔥 Firebase Full Stack Deployment - Step-by-Step Guide

## Overview
Deploy Cerebrum (backend + frontend) to Firebase infrastructure using:
- **Cloud Run** for the backend (FastAPI)
- **Firebase Hosting** for the frontend (React/Vite)

---

## ✅ Prerequisites

1. **Google Cloud SDK** installed
2. **Firebase CLI** installed: `npm install -g firebase-tools`
3. **Access to GCP Project**: `cerebrum-30d9c`

---

## 🚀 Deployment Steps

### Step 1: Authenticate with Google Cloud

Run this on your local machine (requires browser for authentication):

```bash
# Login to gcloud
gcloud auth login

# Set the project
gcloud config set project cerebrum-30d9c

# Verify
gcloud auth list
gcloud config get-value project
```

### Step 2: Enable Required APIs

```bash
gcloud services enable \
    run.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    firebase.googleapis.com \
    firebasehosting.googleapis.com \
    --project=cerebrum-30d9c
```

### Step 3: Firebase Login

```bash
# Login to Firebase (opens browser)
firebase login

# Set the project
firebase use cerebrum-30d9c
```

### Step 4: Create GitHub Actions Service Account

```bash
# Create service account for GitHub Actions
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions" \
    --description="Service account for GitHub Actions deployments" \
    --project=cerebrum-30d9c

# Grant required roles
gcloud projects add-iam-policy-binding cerebrum-30d9c \
    --member="serviceAccount:github-actions@cerebrum-30d9c.iam.gserviceaccount.com" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding cerebrum-30d9c \
    --member="serviceAccount:github-actions@cerebrum-30d9c.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

gcloud projects add-iam-policy-binding cerebrum-30d9c \
    --member="serviceAccount:github-actions@cerebrum-30d9c.iam.gserviceaccount.com" \
    --role="roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding cerebrum-30d9c \
    --member="serviceAccount:github-actions@cerebrum-30d9c.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding cerebrum-30d9c \
    --member="serviceAccount:github-actions@cerebrum-30d9c.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### Step 5: Generate Service Account Key

```bash
# Generate the service account key file
gcloud iam service-accounts keys create gcp-sa-key.json \
    --iam-account=github-actions@cerebrum-30d9c.iam.gserviceaccount.com \
    --project=cerebrum-30d9c

# View the key content (we'll need this for GitHub Secrets)
cat gcp-sa-key.json
```

### Step 6: Get Firebase Service Account

1. Go to [Firebase Console Service Accounts](https://console.firebase.google.com/project/cerebrum-30d9c/settings/serviceaccounts/adminsdk)
2. Click "Generate new private key"
3. Save the JSON file
4. Copy the contents for GitHub Secrets

### Step 7: Add GitHub Secrets

Go to: `https://github.com/bopoadz-del/Cerebrum/settings/secrets/actions`

Add these secrets:

| Secret Name | Value | Source |
|-------------|-------|--------|
| `GCP_SA_KEY` | Content of `gcp-sa-key.json` | Generated in Step 5 |
| `FIREBASE_SERVICE_ACCOUNT_CEREBRUM_30D9C` | Firebase service account JSON | From Firebase Console |
| `SSH_PRIVATE_KEY` | GitHub SSH private key | `/workspaces/Cerebrum/.ssh-keys/github_ed25519` |

### Step 8: Set Up Secret Manager

Create the following secrets in Google Secret Manager:

```bash
# 1. Database URL (PostgreSQL)
echo -n "postgresql+asyncpg://user:password@host:5432/dbname" | \
  gcloud secrets create database-url --data-file=- --replication-policy="automatic"

# 2. Redis URL
echo -n "redis://your-redis-host:6379/0" | \
  gcloud secrets create redis-url --data-file=- --replication-policy="automatic"

# 3. Secret Key (generate a secure random key)
openssl rand -hex 32 | \
  gcloud secrets create secret-key --data-file=- --replication-policy="automatic"

# 4. OpenAI API Key (optional, for AI features)
echo -n "sk-your-openai-key" | \
  gcloud secrets create openai-api-key --data-file=- --replication-policy="automatic"
```

### Step 9: Grant Cloud Run Access to Secrets

```bash
SERVICE_ACCOUNT="cerebrum-30d9c-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding database-url \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding redis-url \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding secret-key \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding openai-api-key \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"
```

### Step 10: Trigger Deployment

```bash
# Push to main branch to trigger deployment
git push origin main
```

Or manually trigger from GitHub Actions tab.

---

## 🔗 Deployment URLs

After successful deployment:

| Component | URL |
|-----------|-----|
| **Frontend** | https://cerebrum-30d9c.web.app |
| **Landing Page** | https://cerebrum-landing.web.app |
| **API** | https://cerebrum-30d9c.web.app/api/ |
| **Health Check** | https://cerebrum-30d9c.web.app/health/live |
| **API Docs** | https://cerebrum-30d9c.web.app/docs |
| **Cloud Run Direct** | https://cerebrum-backend-uc.a.run.app |

---

## 🏗️ Architecture

```
User → Firebase Hosting (CDN)
       ├── /api/* → Cloud Run (Python/FastAPI Backend)
       └── /*     → Static Files (React/Vite Frontend)
```

---

## 🛠️ Troubleshooting

### Cloud Run Service Not Accessible

```bash
# Make service public
gcloud run services add-iam-policy-binding cerebrum-backend \
    --region=us-central1 \
    --member="allUsers" \
    --role="roles/run.invoker"
```

### Check Deployment Status

```bash
# Check Cloud Run service
gcloud run services describe cerebrum-backend --region=us-central1

# View logs
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=cerebrum-backend"

# List secrets
gcloud secrets list
```

### Test Backend Directly

```bash
curl https://cerebrum-backend-uc.a.run.app/health/live

# Or through Firebase
curl https://cerebrum-30d9c.web.app/api/health/live
```

---

## 📦 Local Development

### Build Backend Docker Image Locally

```bash
cd backend
docker build -f Dockerfile.cloudrun -t cerebrum-backend:test .
docker run -p 8000:8000 cerebrum-backend:test
```

### Build Frontend Locally

```bash
cd frontend
npm ci
npm run build
# Output in frontend/dist/
```

---

## 💰 Cost Estimation

| Component | Monthly Cost |
|-----------|-------------|
| Firebase Hosting | Free (10 GB/month) |
| Cloud Run | $0-50 (depends on traffic) |
| Secret Manager | Free (6 secrets) |
| **Total** | **$0-75/month** |

Cloud Run free tier: 2M requests/month, 360K GB-seconds memory, 180K vCPU-seconds.

---

## 📚 Additional Resources

- [Firebase Hosting + Cloud Run](https://firebase.google.com/docs/hosting/cloud-run)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GitHub Actions for Cloud Run](https://github.com/google-github-actions/deploy-cloudrun)
