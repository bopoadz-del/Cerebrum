#!/bin/bash
# GCP + Firebase Full Stack Setup Script
# This script sets up Cloud Run, Firebase, and required secrets

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=========================================="
echo "  🚀 Cerebrum Full Stack GCP Setup"
echo "=========================================="
echo -e "${NC}"
echo ""

# Configuration
PROJECT_ID="cerebrum-30d9c"
REGION="us-central1"
BACKEND_SERVICE="cerebrum-backend"

# ==========================================
# Check Prerequisites
# ==========================================
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found.${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v firebase &> /dev/null; then
    echo -e "${RED}❌ firebase CLI not found.${NC}"
    echo "Install with: npm install -g firebase-tools"
    exit 1
fi

echo -e "${GREEN}✅ gcloud and firebase CLIs found${NC}"
echo ""

# ==========================================
# Authenticate and Set Project
# ==========================================
echo -e "${BLUE}=========================================="
echo "Step 1: Authentication"
echo "==========================================${NC}"
echo ""

echo "Ensuring you're logged in to gcloud..."
gcloud auth list --filter=status:ACTIVE --format="value(account)" || gcloud auth login

echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

echo -e "${GREEN}✅ Project set to $PROJECT_ID${NC}"
echo ""

# ==========================================
# Enable Required APIs
# ==========================================
echo -e "${BLUE}=========================================="
echo "Step 2: Enable GCP APIs"
echo "==========================================${NC}"
echo ""

echo "Enabling required APIs (this may take a minute)..."
gcloud services enable \
    run.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    firebase.googleapis.com \
    firebasehosting.googleapis.com \
    --quiet

echo -e "${GREEN}✅ APIs enabled${NC}"
echo ""

# ==========================================
# Setup Firebase
# ==========================================
echo -e "${BLUE}=========================================="
echo "Step 3: Firebase Setup"
echo "==========================================${NC}"
echo ""

# Check if Firebase is initialized
if [ ! -f "firebase.json" ]; then
    echo -e "${RED}firebase.json not found. Run from project root.${NC}"
    exit 1
fi

echo "Initializing Firebase..."
firebase use $PROJECT_ID --add 2>/dev/null || firebase use $PROJECT_ID

echo -e "${GREEN}✅ Firebase configured${NC}"
echo ""

# ==========================================
# Create Additional Firebase Hosting Site (Optional)
# ==========================================
echo -e "${BLUE}=========================================="
echo "Step 4: Firebase Hosting Sites"
echo "==========================================${NC}"
echo ""

echo "Checking existing hosting sites..."
firebase hosting:sites:list 2>/dev/null || true

echo ""
echo -e "${YELLOW}Note: If you want a separate site for landing page, run:${NC}"
echo "  firebase hosting:sites:create cerebrum-landing --project $PROJECT_ID"
echo ""

# ==========================================
# Create Cloud Run Service (if not exists)
# ==========================================
echo -e "${BLUE}=========================================="
echo "Step 5: Cloud Run Service"
echo "==========================================${NC}"
echo ""

SERVICE_EXISTS=$(gcloud run services list --filter="metadata.name=$BACKEND_SERVICE" --format="value(metadata.name)" 2>/dev/null || true)

if [ -z "$SERVICE_EXISTS" ]; then
    echo -e "${YELLOW}Cloud Run service '$BACKEND_SERVICE' not found.${NC}"
    echo "It will be created on first deployment via GitHub Actions."
else
    echo -e "${GREEN}✅ Cloud Run service '$BACKEND_SERVICE' exists${NC}"
fi
echo ""

# ==========================================
# Setup Secret Manager
# ==========================================
echo -e "${BLUE}=========================================="
echo "Step 6: Secret Manager Setup"
echo "==========================================${NC}"
echo ""

echo "You'll need to create the following secrets in Secret Manager:"
echo ""
echo -e "${YELLOW}Required Secrets:${NC}"
echo "  1. database-url      - PostgreSQL connection string"
echo "  2. redis-url         - Redis connection string"
echo "  3. secret-key        - Django/FastAPI secret key"
echo "  4. openai-api-key    - OpenAI API key"
echo ""

read -p "Do you want to create these secrets now? (y/n): " CREATE_SECRETS

if [ "$CREATE_SECRETS" = "y" ] || [ "$CREATE_SECRETS" = "Y" ]; then
    # database-url
    echo ""
    read -p "Enter DATABASE_URL (PostgreSQL): " DB_URL
    if [ -n "$DB_URL" ]; then
        echo -n "$DB_URL" | gcloud secrets create database-url --data-file=- --replication-policy="automatic" 2>/dev/null || \
        echo -n "$DB_URL" | gcloud secrets versions add database-url --data-file=-
        echo -e "${GREEN}✅ database-url created/updated${NC}"
    fi
    
    # redis-url
    echo ""
    read -p "Enter REDIS_URL: " REDIS_URL
    if [ -n "$REDIS_URL" ]; then
        echo -n "$REDIS_URL" | gcloud secrets create redis-url --data-file=- --replication-policy="automatic" 2>/dev/null || \
        echo -n "$REDIS_URL" | gcloud secrets versions add redis-url --data-file=-
        echo -e "${GREEN}✅ redis-url created/updated${NC}"
    fi
    
    # secret-key
    echo ""
    read -p "Enter SECRET_KEY (generate a secure random key): " SECRET_KEY
    if [ -n "$SECRET_KEY" ]; then
        echo -n "$SECRET_KEY" | gcloud secrets create secret-key --data-file=- --replication-policy="automatic" 2>/dev/null || \
        echo -n "$SECRET_KEY" | gcloud secrets versions add secret-key --data-file=-
        echo -e "${GREEN}✅ secret-key created/updated${NC}"
    fi
    
    # openai-api-key
    echo ""
    read -p "Enter OPENAI_API_KEY: " OPENAI_KEY
    if [ -n "$OPENAI_KEY" ]; then
        echo -n "$OPENAI_KEY" | gcloud secrets create openai-api-key --data-file=- --replication-policy="automatic" 2>/dev/null || \
        echo -n "$OPENAI_KEY" | gcloud secrets versions add openai-api-key --data-file=-
        echo -e "${GREEN}✅ openai-api-key created/updated${NC}"
    fi
fi

echo ""

# ==========================================
# Grant Cloud Run Access to Secrets
# ==========================================
echo -e "${BLUE}=========================================="
echo "Step 7: IAM Permissions"
echo "==========================================${NC}"
echo ""

SERVICE_ACCOUNT="$PROJECT_ID-compute@developer.gserviceaccount.com"

echo "Granting secret accessor permissions to Cloud Run service account..."
gcloud secrets add-iam-policy-binding database-url \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" 2>/dev/null || true

gcloud secrets add-iam-policy-binding redis-url \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" 2>/dev/null || true

gcloud secrets add-iam-policy-binding secret-key \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" 2>/dev/null || true

gcloud secrets add-iam-policy-binding openai-api-key \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" 2>/dev/null || true

echo -e "${GREEN}✅ IAM permissions configured${NC}"
echo ""

# ==========================================
# Create Service Account for GitHub Actions
# ==========================================
echo -e "${BLUE}=========================================="
echo "Step 8: GitHub Actions Service Account"
echo "==========================================${NC}"
echo ""

SA_NAME="github-actions"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

echo "Creating service account for GitHub Actions..."
gcloud iam service-accounts create $SA_NAME \
    --display-name="GitHub Actions" \
    --description="Service account for GitHub Actions deployments" 2>/dev/null || true

echo "Granting required roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.admin" \
    --condition=None 2>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.admin" \
    --condition=None 2>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudbuild.builds.editor" \
    --condition=None 2>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/iam.serviceAccountUser" \
    --condition=None 2>/dev/null || true

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None 2>/dev/null || true

echo ""
echo -e "${YELLOW}Generate and download service account key:${NC}"
echo "  gcloud iam service-accounts keys create gcp-sa-key.json \\"
echo "    --iam-account=$SA_EMAIL"
echo ""
echo -e "${YELLOW}Then add to GitHub Secrets as: GCP_SA_KEY${NC}"
echo ""

# ==========================================
# Summary
# ==========================================
echo -e "${GREEN}"
echo "=========================================="
echo "  🎉 GCP Setup Complete!"
echo "=========================================="
echo -e "${NC}"
echo ""
echo "Next Steps:"
echo ""
echo "1. ${YELLOW}Generate GitHub Actions Service Account Key:${NC}"
echo "   gcloud iam service-accounts keys create gcp-sa-key.json \\"
echo "     --iam-account=$SA_EMAIL"
echo ""
echo "2. ${YELLOW}Add GitHub Secrets:${NC}"
echo "   Go to: https://github.com/YOUR_USERNAME/cerebrum/settings/secrets/actions"
echo "   - GCP_SA_KEY: (content of gcp-sa-key.json)"
echo "   - FIREBASE_SERVICE_ACCOUNT_CEREBRUM_30D9C: (from Firebase Console)"
echo ""
echo "3. ${YELLOW}Setup Database:${NC}"
echo "   - You can use Cloud SQL PostgreSQL or keep Render/Supabase"
echo "   - Update database-url secret with your DB connection string"
echo ""
echo "4. ${YELLOW}Push to trigger deployment:${NC}"
echo "   git push origin main"
echo ""
echo "=========================================="
echo "Architecture:"
echo ""
echo "  User → Firebase Hosting (CDN)"
echo "         ├── /api/* → Cloud Run (Python/FastAPI)"
echo "         └── /*     → Static Files (React/Vite)"
echo ""
echo "URLs after deployment:"
echo "  Frontend: https://cerebrum-30d9c.web.app"
echo "  Landing:  https://cerebrum-landing.web.app"
echo "  API:      https://cerebrum-30d9c.web.app/api/"
echo "=========================================="
