# Cerebrum Android App - Build Instructions

## Overview

This document provides comprehensive instructions for building and deploying the Cerebrum Android app.

## Current Configuration

- **App ID**: `com.cerebrum.app`
- **App Name**: Cerebrum
- **Version**: 1.0.1
- **Version Code**: 2
- **Min SDK**: 23 (Android 6.0)
- **Target SDK**: 35 (Android 15)
- **Compile SDK**: 35

## Prerequisites

1. **Android Studio** (latest stable version recommended)
2. **JDK 17** or higher
3. **Node.js** 18+ and npm/yarn
4. **Capacitor CLI** installed globally:
   ```bash
   npm install -g @capacitor/cli
   ```

## Quick Build

### Option 1: Using the Build Script

```bash
cd /mnt/okcomputer/output/Cerebrum-main/frontend/android
./build.sh
```

### Option 2: Manual Build

```bash
cd /mnt/okcomputer/output/Cerebrum-main/frontend/android

# Clean previous builds
./gradlew clean

# Build debug APK
./gradlew assembleDebug

# Build release APK (unsigned)
./gradlew assembleRelease
```

## Full Build Workflow (from web to APK)

### Step 1: Build the Web App

```bash
cd /mnt/okcomputer/output/Cerebrum-main/frontend

# Install dependencies (if needed)
npm install

# Build for production
npm run build
```

### Step 2: Sync with Capacitor

```bash
cd /mnt/okcomputer/output/Cerebrum-main/frontend

# Sync web assets to Android platform
npx cap sync android

# Or copy only (faster, but doesn't update plugins)
npx cap copy android
```

### Step 3: Build the Android App

```bash
cd /mnt/okcomputer/output/Cerebrum-main/frontend/android

# Build debug APK
./gradlew assembleDebug

# Build release APK
./gradlew assembleRelease
```

## Output Locations

After a successful build, the APK files will be located at:

- **Debug APK**: `app/build/outputs/apk/debug/app-debug.apk`
- **Release APK**: `app/build/outputs/apk/release/app-release-unsigned.apk`

## Installation

### Install Debug APK on Connected Device

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Install Release APK

```bash
adb install -r app/build/outputs/apk/release/app-release-unsigned.apk
```

## Signing for Production

To publish on Google Play Store, you must sign the release APK:

### Step 1: Create a Keystore (one-time)

```bash
keytool -genkey -v -keystore cerebrum-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias cerebrum
```

### Step 2: Sign the APK

```bash
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 -keystore cerebrum-release-key.jks app/build/outputs/apk/release/app-release-unsigned.apk cerebrum
```

### Step 3: Align the APK (recommended)

```bash
zipalign -v 4 app/build/outputs/apk/release/app-release-unsigned.apk app-release-signed.apk
```

## Permissions

The app requires the following permissions (defined in `AndroidManifest.xml`):

| Permission | Purpose |
|------------|---------|
| `INTERNET` | Network access for API calls |
| `CAMERA` | Camera access for image upload |
| `READ_EXTERNAL_STORAGE` | Read files from device storage |
| `WRITE_EXTERNAL_STORAGE` | Write files to device storage (API 32 and below) |
| `READ_MEDIA_IMAGES` | Read images on Android 13+ |
| `READ_MEDIA_VIDEO` | Read videos on Android 13+ |
| `READ_MEDIA_AUDIO` | Read audio files on Android 13+ |
| `ACCESS_NETWORK_STATE` | Check network connectivity |

## Capacitor Configuration

The Capacitor configuration is defined in `capacitor.config.ts`:

- **Web Directory**: `dist`
- **Android Scheme**: `https`
- **Hostname**: `app.cerebrum.local`
- **Logging**: Production mode
- **Mixed Content**: Allowed for development

## Troubleshooting

### Build Errors

1. **Gradle sync failed**:
   ```bash
   ./gradlew clean
   ./gradlew build
   ```

2. **Capacitor sync issues**:
   ```bash
   npx cap sync android --force
   ```

3. **Dependency conflicts**:
   ```bash
   cd android
   ./gradlew app:dependencies --configuration implementation
   ```

### Runtime Issues

1. **White screen on launch**:
   - Check that web assets are properly synced
   - Verify `webDir` in capacitor.config.ts

2. **Camera not working**:
   - Ensure CAMERA permission is granted
   - Check that the Camera plugin is installed:
     ```bash
     npm install @capacitor/camera
     npx cap sync
     ```

3. **File upload not working**:
   - Verify storage permissions are granted
   - Check FileProvider configuration in AndroidManifest.xml

## Development Tips

### Live Reload

For development with live reload:

```bash
cd /mnt/okcomputer/output/Cerebrum-main/frontend

# Start dev server with external IP
npm run dev -- --host

# In another terminal, sync and open Android Studio
npx cap sync android
npx cap open android
```

### Debugging

1. **Android Studio**: Use Logcat to view logs
2. **Chrome DevTools**: Navigate to `chrome://inspect` to debug WebView
3. **Capacitor Logging**: Set `loggingBehavior: 'debug'` in capacitor.config.ts

## Release Checklist

Before releasing to production:

- [ ] Update versionCode in `app/build.gradle`
- [ ] Update versionName in `app/build.gradle`
- [ ] Test on multiple Android versions (6.0 - 15)
- [ ] Verify all permissions work correctly
- [ ] Test camera and file upload functionality
- [ ] Sign the APK with release keystore
- [ ] Test the signed APK on a physical device
- [ ] Upload to Google Play Console

## Support

For issues or questions:
1. Check Capacitor documentation: https://capacitorjs.com/docs
2. Review Android developer guides: https://developer.android.com/
3. Check the project README for additional information
