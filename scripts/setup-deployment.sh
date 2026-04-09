#!/bin/bash
# Firebase + Render Deployment Setup Script
# Run this to configure all deployment secrets

set -e

echo "=========================================="
echo "🔥 Cerebrum Deployment Setup"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}This script helps you set up deployment secrets for GitHub Actions${NC}"
echo ""

# ==========================================
# Check for required tools
# ==========================================
if ! command -v firebase &> /dev/null; then
    echo -e "${RED}❌ firebase CLI not found. Install with: npm install -g firebase-tools${NC}"
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo -e "${YELLOW}⚠️  GitHub CLI (gh) not found. You'll need to manually add secrets.${NC}"
    GH_CLI=false
else
    GH_CLI=true
fi

echo -e "${GREEN}✅ Firebase CLI found${NC}"
echo ""

# ==========================================
# 1. Firebase Service Account
# ==========================================
echo "=========================================="
echo "Step 1: Firebase Service Account Setup"
echo "=========================================="
echo ""
echo "You need to generate a Firebase service account key:"
echo "1. Go to: https://console.firebase.google.com/project/cerebrum-30d9c/settings/serviceaccounts/adminsdk"
echo "2. Click 'Generate new private key'"
echo "3. Save the JSON file"
echo ""

if [ "$GH_CLI" = true ]; then
    echo -n "Path to your Firebase service account JSON file: "
    read -r FIREBASE_SA_PATH
    
    if [ -f "$FIREBASE_SA_PATH" ]; then
        # Read and encode the JSON
        FIREBASE_SA_JSON=$(cat "$FIREBASE_SA_PATH")
        echo ""
        echo "Adding FIREBASE_SERVICE_ACCOUNT_CEREBRUM_30D9C secret..."
        echo "$FIREBASE_SA_JSON" | gh secret set FIREBASE_SERVICE_ACCOUNT_CEREBRUM_30D9C --repo="$(git remote get-url origin | sed 's/.*github.com[:/]//;s/.git$//')"
        echo -e "${GREEN}✅ Firebase Service Account secret added!${NC}"
    else
        echo -e "${RED}❌ File not found. Please add manually.${NC}"
    fi
else
    echo -e "${YELLOW}Add this secret manually in GitHub:${NC}"
    echo "Secret Name: FIREBASE_SERVICE_ACCOUNT_CEREBRUM_30D9C"
    echo "Value: Contents of your Firebase service account JSON file"
    echo "URL: https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]//;s/.git$//')/settings/secrets/actions"
fi

echo ""

# ==========================================
# 2. SSH Private Key for Git Operations
# ==========================================
echo "=========================================="
echo "Step 2: SSH Key Setup"
echo "=========================================="
echo ""
echo "Adding SSH private key for git operations..."

SSH_KEY_PATH=".ssh-keys/github_ed25519"
if [ -f "$SSH_KEY_PATH" ]; then
    SSH_KEY=$(cat "$SSH_KEY_PATH")
    
    if [ "$GH_CLI" = true ]; then
        echo "$SSH_KEY" | gh secret set SSH_PRIVATE_KEY --repo="$(git remote get-url origin | sed 's/.*github.com[:/]//;s/.git$//')"
        echo -e "${GREEN}✅ SSH_PRIVATE_KEY secret added!${NC}"
    else
        echo -e "${YELLOW}Add this secret manually in GitHub:${NC}"
        echo "Secret Name: SSH_PRIVATE_KEY"
        echo "Value: Contents of .ssh-keys/github_ed25519"
    fi
else
    echo -e "${RED}❌ SSH key not found at $SSH_KEY_PATH${NC}"
    echo "Generate one with: ssh-keygen -t ed25519 -f .ssh-keys/github_ed25519 -C 'github-access'"
fi

echo ""

# ==========================================
# 3. VITE_API_URL
# ==========================================
echo "=========================================="
echo "Step 3: API URL Configuration"
echo "=========================================="
echo ""
echo -n "Enter your backend API URL (default: https://cerebrum-api.onrender.com): "
read -r API_URL
API_URL=${API_URL:-"https://cerebrum-api.onrender.com"}

if [ "$GH_CLI" = true ]; then
    echo "$API_URL" | gh secret set VITE_API_URL --repo="$(git remote get-url origin | sed 's/.*github.com[:/]//;s/.git$//')"
    echo -e "${GREEN}✅ VITE_API_URL secret set to: $API_URL${NC}"
else
    echo -e "${YELLOW}Add this secret manually:${NC}"
    echo "Secret Name: VITE_API_URL"
    echo "Value: $API_URL"
fi

echo ""

# ==========================================
# 4. Render Deploy Hook (Optional)
# ==========================================
echo "=========================================="
echo "Step 4: Render Deploy Hook (Optional)"
echo "=========================================="
echo ""
echo "To auto-deploy backend on Render:"
echo "1. Go to your Render dashboard: https://dashboard.render.com"
echo "2. Select your web service (cerebrum-api)"
echo "3. Settings → Deploy Hook"
echo "4. Copy the Deploy Hook URL"
echo ""
echo -n "Enter your Render Deploy Hook URL (or press Enter to skip): "
read -r RENDER_HOOK

if [ -n "$RENDER_HOOK" ]; then
    if [ "$GH_CLI" = true ]; then
        echo "$RENDER_HOOK" | gh secret set RENDER_DEPLOY_HOOK --repo="$(git remote get-url origin | sed 's/.*github.com[:/]//;s/.git$//')"
        echo -e "${GREEN}✅ RENDER_DEPLOY_HOOK secret added!${NC}"
    else
        echo -e "${YELLOW}Add this secret manually:${NC}"
        echo "Secret Name: RENDER_DEPLOY_HOOK"
        echo "Value: $RENDER_HOOK"
    fi
else
    echo "Skipped. You can add this later for automatic backend deploys."
fi

echo ""
echo "=========================================="
echo -e "${GREEN}🎉 Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Push your changes to GitHub"
echo "2. Check the Actions tab for deployment status"
echo "3. Your frontend will deploy to: https://cerebrum-30d9c.web.app"
echo "4. Your landing page will deploy to: https://cerebrum-landing.web.app"
echo ""
