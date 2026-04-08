#!/bin/bash
# Trigger GitHub Actions workflow to build Ollama base image
# Usage: ./trigger-base-image-build.sh [models]

MODELS="${1:-gemma3:270m,nomic-embed-text}"
REPO="bopoadz-del/Cerebrum"

echo "Triggering base image build for models: $MODELS"
echo ""

# Option 1: Using gh CLI (if installed)
if command -v gh &> /dev/null; then
    echo "Using GitHub CLI..."
    gh workflow run build-base-image.yml \
        --repo $REPO \
        --field models="$MODELS"
    echo "✅ Workflow triggered! Check: https://github.com/$REPO/actions"
    exit 0
fi

# Option 2: Using curl with GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ GITHUB_TOKEN not set"
    echo ""
    echo "Set it with: export GITHUB_TOKEN='your_token_here'"
    echo "Or install gh CLI: https://cli.github.com/"
    exit 1
fi

echo "Using curl with GITHUB_TOKEN..."
curl -X POST \
    -H "Authorization: token $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/$REPO/actions/workflows/build-base-image.yml/dispatches" \
    -d "{\"ref\":\"main\",\"inputs\":{\"models\":\"$MODELS\"}}"

echo ""
echo "✅ Workflow triggered! Check: https://github.com/$REPO/actions"
