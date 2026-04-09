# 🚀 Cerebrum Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        USERS                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│   Firebase   │ │ Firebase │ │    Render    │
│   Hosting    │ │ Hosting  │ │   (Backend)  │
│  (Frontend)  │ │ (Landing)│ │              │
└──────────────┘ └──────────┘ └──────────────┘
│cerebrum-30d9c│ │cerebrum- │ │cerebrum-api  │
│   .web.app   │ │landing   │ │.onrender.com │
└──────────────┘ └──────────┘ └──────────────┘
```

## Quick Start

### Prerequisites
- Firebase CLI: `npm install -g firebase-tools`
- GitHub CLI (optional): `gh auth login`

### Automated Setup

Run the setup script:
```bash
./scripts/setup-deployment.sh
```

### Manual Setup

#### 1. Firebase Service Account

1. Go to [Firebase Console → Project Settings → Service Accounts](https://console.firebase.google.com/project/cerebrum-30d9c/settings/serviceaccounts/adminsdk)
2. Click **"Generate new private key"**
3. Add to GitHub Secrets as: `FIREBASE_SERVICE_ACCOUNT_CEREBRUM_30D9C`

#### 2. SSH Key (for Git operations in CI)

```bash
# The SSH key is already in .ssh-keys/github_ed25519
cat .ssh-keys/github_ed25519 | gh secret set SSH_PRIVATE_KEY
```

Add to GitHub Secrets as: `SSH_PRIVATE_KEY`

#### 3. API URL

```bash
gh secret set VITE_API_URL --body "https://cerebrum-api.onrender.com"
```

#### 4. Render Deploy Hook (Optional - for auto backend deploy)

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Select your service → Settings → Deploy Hook
3. Add to GitHub Secrets as: `RENDER_DEPLOY_HOOK`

## GitHub Secrets Required

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `FIREBASE_SERVICE_ACCOUNT_CEREBRUM_30D9C` | Firebase service account JSON | Firebase Console → Settings → Service Accounts |
| `SSH_PRIVATE_KEY` | SSH key for git operations | `.ssh-keys/github_ed25519` |
| `VITE_API_URL` | Backend API URL | Your Render backend URL |
| `RENDER_DEPLOY_HOOK` | Render deploy webhook URL | Render Dashboard → Settings |

## Deployment Workflows

### On Push to Main
- ✅ Builds and deploys Frontend to Firebase
- ✅ Deploys Landing page to Firebase
- ✅ Triggers backend deploy on Render (if backend files changed)

### On Pull Request
- ✅ Builds PR preview of Frontend
- ✅ Posts preview URL as PR comment
- ✅ Preview expires after 7 days

## URLs After Deployment

| Service | URL |
|---------|-----|
| Frontend | `https://cerebrum-30d9c.web.app` |
| Landing | `https://cerebrum-landing.web.app` |
| Backend | `https://cerebrum-api.onrender.com` |

## Firebase Hosting Targets

Configured in `firebase.json`:
- **frontend**: Deploys `frontend/dist/` (main app)
- **landing**: Deploys `landing/` (marketing page)

## Troubleshooting

### Deploy Failed?

1. Check GitHub Actions logs
2. Verify all secrets are set
3. Ensure Firebase project exists: `cerebrum-30d9c`

### Need to Create Firebase Sites?

```bash
firebase hosting:sites:create cerebrum-landing --project cerebrum-30d9c
```

### Test Locally

```bash
# Frontend
cd frontend && npm run build
firebase emulators:start --only hosting

# Backend
cd backend && docker-compose up
```
