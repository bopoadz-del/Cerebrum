#!/bin/bash

# Reasoner AI Platform - Termux Build Script
# This script builds the full UI for deployment

set -e

echo "=========================================="
echo "  Reasoner AI Platform - Full UI Build"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running in Termux
if [ -d "/data/data/com.termux" ]; then
    echo -e "${BLUE}Detected Termux environment${NC}"
    export NODE_OPTIONS="--max-old-space-size=2048"
fi

# Navigate to project directory
cd "$(dirname "$0")/app" || exit 1

echo -e "${YELLOW}Step 1: Installing dependencies...${NC}"
npm install 2>&1 | grep -v "deprecated" || true

echo ""
echo -e "${YELLOW}Step 2: Building production bundle...${NC}"
npm run build 2>&1

echo ""
echo -e "${GREEN}Build completed successfully!${NC}"
echo ""

# Check if dist folder exists
if [ -d "dist" ]; then
    echo -e "${BLUE}Build artifacts:${NC}"
    ls -lh dist/
    echo ""
    echo -e "${GREEN}Output directory: $(pwd)/dist${NC}"
else
    echo -e "${RED}Build failed - dist folder not found${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo "  Build Complete!"
echo "=========================================="
echo ""
echo "To deploy, run:"
echo "  npx surge dist/"
echo "  # OR"
echo "  npx netlify deploy --prod --dir=dist"
echo ""
