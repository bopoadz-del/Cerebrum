#!/bin/bash

# Cerebrum Android App Build Script
# This script builds the Android app for production deployment

set -e

echo "=========================================="
echo "Cerebrum Android App Build Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "build.gradle" ]; then
    print_error "Please run this script from the android directory"
    exit 1
fi

# Get version info
VERSION_NAME=$(grep "versionName" app/build.gradle | awk '{print $2}' | tr -d '"')
VERSION_CODE=$(grep "versionCode" app/build.gradle | awk '{print $2}')

print_info "Building Cerebrum Android App"
print_info "Version: $VERSION_NAME (Build $VERSION_CODE)"
echo ""

# Clean previous builds
print_info "Cleaning previous builds..."
./gradlew clean

# Build APK
print_info "Building debug APK..."
./gradlew assembleDebug

# Build release APK (unsigned)
print_info "Building release APK (unsigned)..."
./gradlew assembleRelease

echo ""
echo "=========================================="
print_info "Build completed successfully!"
echo "=========================================="
echo ""
echo "Output files:"
echo "  Debug APK:   app/build/outputs/apk/debug/app-debug.apk"
echo "  Release APK: app/build/outputs/apk/release/app-release-unsigned.apk"
echo ""
echo "To install the debug APK on a connected device:"
echo "  adb install -r app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "To sign the release APK, use:"
echo "  jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 -keystore my-release-key.jks app-release-unsigned.apk alias_name"
echo ""
