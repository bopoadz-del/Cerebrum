# Capacitor Mobile File Access Setup Guide

This guide explains how to set up and use the mobile file system integration for Cerebrum, enabling persistent access to mobile device storage like a local drive.

## Overview

Cerebrum uses Capacitor to provide native mobile file system access, allowing the app to:
- Browse and access files from Downloads, Documents, and Camera folders
- Auto-sync new files from monitored directories
- Request persistent storage permissions
- Work offline with local file caching

## Prerequisites

- Node.js 18+ and npm
- Android Studio (for Android development)
- Xcode 14+ (for iOS development)
- Capacitor CLI installed globally: `npm install -g @capacitor/cli`

## Initial Setup

### 1. Install Dependencies

From the frontend directory:

```bash
cd /root/.openclaw/workspace/cerebrum-fix/frontend
npm install @capacitor/core @capacitor/cli
npm install @capacitor/android @capacitor/ios
npm install @capacitor/filesystem @capacitor/camera @capacitor/preferences
npm install @capacitor/local-notifications @capacitor/background-runner
```

### 2. Initialize Capacitor Platforms

```bash
# Initialize Android
npx cap add android

# Initialize iOS
npx cap add ios
```

### 3. Build and Sync

```bash
# Build the web app
npm run build

# Sync changes to native platforms
npx cap sync
```

### 4. Open Native IDEs

```bash
# Open Android Studio
npx cap open android

# Open Xcode
npx cap open ios
```

## Platform-Specific Configuration

### Android Permissions

Add these permissions to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
<uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
<uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE" 
    tools:ignore="ScopedStorage" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

### iOS Permissions

Add these entries to `ios/App/App/Info.plist`:

```xml
<key>NSPhotoLibraryUsageDescription</key>
<string>Cerebrum needs access to your photo library to upload and manage files.</string>
<key>NSPhotoLibraryAddUsageDescription</key>
<string>Cerebrum needs permission to save files to your photo library.</string>
<key>NSCameraUsageDescription</key>
<string>Cerebrum needs camera access to capture photos for upload.</string>
<key>NSFileProviderDomainUsageDescription</key>
<string>Cerebrum needs access to your files for document management.</string>
```

Also enable the following capabilities in Xcode:
- iCloud (with iCloud Documents)
- Background Modes (Background fetch, Background processing)

## Usage

### Basic File System Operations

```typescript
import { fileSystem } from '@/mobile/fileSystem';

// Request permissions
const hasPermission = await fileSystem.requestPermissions();

// List files in Downloads folder
const files = await fileSystem.listFiles('DOWNLOADS');

// Read file content
const content = await fileSystem.readFile(filePath);

// Write file
await fileSystem.writeFile(filePath, data, 'Downloads/document.txt');

// Delete file
await fileSystem.deleteFile(filePath);
```

### Background Sync

```typescript
import { backgroundSync } from '@/mobile/sync';

// Start monitoring a folder
await backgroundSync.startMonitoring({
  folder: 'DOWNLOADS',
  onNewFile: async (file) => {
    console.log('New file detected:', file.name);
    // Auto-upload or process file
  }
});

// Check sync status
const status = backgroundSync.getStatus();
console.log(`Scanned ${status.filesScanned} files, uploaded ${status.filesUploaded}`);

// Stop monitoring
await backgroundSync.stopMonitoring();
```

### Mobile File Browser Component

```tsx
import { MobileFileBrowser } from '@/components/MobileFileBrowser';

function MyComponent() {
  return (
    <MobileFileBrowser
      initialFolder="DOWNLOADS"
      onFileSelect={(file) => console.log('Selected:', file)}
      onFolderSelect={(folder) => console.log('Folder:', folder)}
      allowMultiSelect={true}
      filterTypes={['.pdf', '.jpg', '.png']}
    />
  );
}
```

## Folder Types

The following special folder types are supported:

| Folder Type | Description | Android Path | iOS Path |
|------------|-------------|--------------|----------|
| `DOWNLOADS` | Downloads folder | `/storage/emulated/0/Download` | Files app Downloads |
| `DOCUMENTS` | Documents folder | `/storage/emulated/0/Documents` | App Documents |
| `PICTURES` | Pictures/Photos | Media Store | Photo Library |
| `DCIM` | Camera folder | `/DCIM/Camera` | Photo Library |
| `AUDIO` | Music/Audio files | Media Store | Media Library |
| `CACHE` | App cache (private) | App cache dir | App cache dir |

## Troubleshooting

### Android Issues

**Permission denied errors:**
- Ensure `MANAGE_EXTERNAL_STORAGE` permission is granted for Android 11+
- User must manually enable "All files access" in Settings > Apps > Cerebrum > Permissions

**Files not appearing:**
- Media files may need MediaScanner to be triggered
- Try restarting the app after granting permissions

### iOS Issues

**Cannot access files:**
- Ensure iCloud Documents capability is enabled
- Files must be in the app's sandbox or shared container
- Use the Files app to move files to the Cerebrum folder

**Background sync not working:**
- iOS background processing has strict time limits
- Use BGTaskScheduler for reliable background operations

## Development Workflow

1. Make changes to web code
2. Build: `npm run build`
3. Sync: `npx cap sync`
4. Test on device/emulator via Android Studio or Xcode

For live reload during development:
```bash
npm run dev
# In another terminal
npx cap run android --livereload --external
npx cap run ios --livereload --external
```

## Security Considerations

- Always request permissions before accessing files
- Sanitize file paths to prevent directory traversal
- Validate file types before processing
- Use HTTPS for all network operations
- Encrypt sensitive files at rest when possible

## Building for Production

### Android

```bash
npm run build
npx cap sync android
npx cap open android
# In Android Studio: Build > Generate Signed Bundle/APK
```

### iOS

```bash
npm run build
npx cap sync ios
npx cap open ios
# In Xcode: Product > Archive > Distribute App
```

## API Reference

See the source files for detailed API documentation:
- `src/mobile/fileSystem.ts` - File system operations
- `src/mobile/sync.ts` - Background sync functionality
- `src/components/MobileFileBrowser.tsx` - File browser UI component
