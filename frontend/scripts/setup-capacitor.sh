#!/bin/bash
# Capacitor Setup Script for Cerebrum Mobile
# This script initializes Capacitor and sets up Android/iOS platforms

set -e

echo "🚀 Setting up Capacitor for Cerebrum Mobile..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    print_error "package.json not found. Please run this script from the frontend directory."
    exit 1
fi

# Install dependencies
print_info "Installing Capacitor dependencies..."
npm install @capacitor/core @capacitor/cli --save
npm install @capacitor/android @capacitor/ios --save
npm install @capacitor/filesystem @capacitor/camera @capacitor/preferences @capacitor/local-notifications --save

print_success "Dependencies installed"

# Initialize Capacitor if not already initialized
if [ ! -f "capacitor.config.ts" ]; then
    print_error "capacitor.config.ts not found. Please ensure the configuration file exists."
    exit 1
fi

print_success "Capacitor configuration found"

# Build the web app
print_info "Building web application..."
npm run build

print_success "Web application built"

# Initialize Android platform
if [ -d "android" ]; then
    print_warning "Android platform already exists. Skipping initialization."
else
    print_info "Initializing Android platform..."
    npx cap add android
    print_success "Android platform initialized"
    
    # Copy Android manifest template
    if [ -f "android/AndroidManifest.template.xml" ]; then
        print_info "Setting up Android permissions..."
        cp android/AndroidManifest.template.xml android/app/src/main/AndroidManifest.xml
        print_success "Android permissions configured"
    fi
fi

# Initialize iOS platform
if [ -d "ios" ]; then
    print_warning "iOS platform already exists. Skipping initialization."
else
    print_info "Initializing iOS platform..."
    npx cap add ios
    print_success "iOS platform initialized"
    
    # Copy iOS plist template
    if [ -f "ios/Info.template.plist" ]; then
        print_info "Setting up iOS permissions..."
        cp ios/Info.template.plist ios/App/App/Info.plist
        print_success "iOS permissions configured"
    fi
fi

# Sync web assets to native platforms
print_info "Syncing web assets to native platforms..."
npx cap sync

print_success "Capacitor setup complete!"

echo ""
echo "📱 Next steps:"
echo ""
echo "  Android:"
echo "    1. Open Android Studio: npm run cap:open:android"
echo "    2. Build and run on your device or emulator"
echo ""
echo "  iOS (Mac only):"
echo "    1. Open Xcode: npm run cap:open:ios"
echo "    2. Select your team in Signing & Capabilities"
echo "    3. Build and run on your device or simulator"
echo ""
echo "  Development:"
echo "    1. Start dev server: npm run dev"
echo "    2. Run with live reload: npx cap run android --livereload --external"
echo ""
echo "📖 See docs/MOBILE_FILE_ACCESS.md for detailed usage instructions"
