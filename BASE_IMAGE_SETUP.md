# ML Base Image Setup

## Problem
Every deploy reinstalls 2GB+ of ML packages (torch, chromadb, etc.) taking 3-4 minutes.

## Solution
Pre-build a base image with all heavy ML dependencies, push to GitHub Container Registry.
Render deploys use this base image - only lightweight app deps are installed.

## Build Time Improvement
- Before: ~3.5 minutes (pip install torch, chromadb, transformers...)
- After: ~30 seconds (pip install fastapi, sqlalchemy...)

## Setup Steps

### 1. Enable GitHub Container Registry
In your GitHub repo:
- Settings → Packages (left sidebar)
- Ensure "Packages" is enabled
- Or just push the workflow - GHCR is free for public repos

### 2. Trigger First Base Image Build
```bash
git add Dockerfile.base backend/requirements-ml.txt .github/workflows/
git commit -m "Add ML base image for faster deploys"
git push origin main
```

The GitHub Action will automatically build and push the base image.

### 3. Check Build Status
Go to: https://github.com/bopoadz-del/Cerebrum/actions

Wait for "Build ML Base Image" workflow to complete (takes ~10-15 min first time).

### 4. Update Render Service
Once the base image is built, Render will automatically use it on next deploy.

## How It Works

### Dockerfile.base
- Based on `python:3.11-slim`
- Installs system deps (gcc, libpq-dev)
- Installs heavy ML packages from `requirements-ml.txt`
- Pushed to `ghcr.io/bopoadz-del/cerebrum-ml-base:latest`

### backend/Dockerfile
- Based on `ghcr.io/bopoadz-del/cerebrum-ml-base:latest`
- Only installs lightweight deps from `requirements.txt`
- Copies app code

### Auto-Rebuild
The base image automatically rebuilds:
- Weekly (Sundays at 2 AM UTC)
- When `requirements-ml.txt` changes
- When `Dockerfile.base` changes
- Manual trigger via GitHub Actions UI

## Updating ML Packages

To upgrade torch, chromadb, etc.:

1. Edit `backend/requirements-ml.txt`
2. Push to main
3. GitHub Action rebuilds base image
4. Next Render deploy uses updated base

## Troubleshooting

### "Pull access denied" on Render
The base image might be private. Make it public:
```bash
# After first push, run locally:
docker pull ghcr.io/bopoadz-del/cerebrum-ml-base:latest
docker push ghcr.io/bopoadz-del/cerebrum-ml-base:latest
```

Or in GitHub: Packages → cerebrum-ml-base → Package settings → Change visibility → Public

### Image not found
Wait for the GitHub Action to complete. Check status at:
https://github.com/bopoadz-del/Cerebrum/actions/workflows/build-base-image.yml

## Files Changed
- `Dockerfile.base` - New: base image definition
- `backend/requirements-ml.txt` - New: heavy ML packages
- `backend/requirements.txt` - Modified: removed heavy deps
- `backend/Dockerfile` - Modified: uses base image
- `.github/workflows/build-base-image.yml` - New: auto-build workflow
