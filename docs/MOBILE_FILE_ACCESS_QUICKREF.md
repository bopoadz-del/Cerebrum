# Mobile File Access - Quick Reference

## Installation

```bash
cd /root/.openclaw/workspace/cerebrum-fix/frontend
./scripts/setup-capacitor.sh
```

## Basic Usage

### File System Operations

```typescript
import { fileSystem, SpecialFolder } from '@/mobile';

// Request permissions
const granted = await fileSystem.requestPermissions();

// List files in Downloads
const files = await fileSystem.listFiles('DOWNLOADS');

// Read a file
const content = await fileSystem.readFile('document.pdf', 'DOWNLOADS');

// Write a file
await fileSystem.writeFile('notes.txt', 'Hello World', 'DOCUMENTS');

// Delete a file
await fileSystem.deleteFile('old-file.pdf', 'DOWNLOADS');

// Create directory
await fileSystem.createDirectory('MyFolder', 'DOCUMENTS');
```

### Using React Hooks

```typescript
import { useMobileFileSystem, useBackgroundSync } from '@/hooks/useMobileFileSystem';

// Basic file system hook
function FileManager() {
  const { 
    files, 
    isLoading, 
    error, 
    permissions,
    refresh,
    readFile,
    writeFile,
    deleteFile 
  } = useMobileFileSystem({ 
    folder: 'DOWNLOADS',
    autoLoad: true 
  });

  if (!permissions) {
    return <button onClick={requestPermissions}>Grant Access</button>;
  }

  return (
    <ul>
      {files.map(file => (
        <li key={file.path}>{file.name} ({fileSystem.formatFileSize(file.size)})</li>
      ))}
    </ul>
  );
}

// Background sync hook
function SyncManager() {
  const { status, startMonitoring, stopMonitoring, syncNow } = useBackgroundSync();

  const start = () => {
    startMonitoring({
      folder: 'DOWNLOADS',
      filterTypes: ['.pdf', '.jpg'],
      uploadEndpoint: '/api/upload',
      backgroundSync: true,
    });
  };

  return (
    <div>
      <p>Files scanned: {status.filesScanned}</p>
      <p>Files uploaded: {status.filesUploaded}</p>
      <button onClick={start}>Start Sync</button>
      <button onClick={syncNow}>Sync Now</button>
    </div>
  );
}
```

### Mobile File Browser Component

```tsx
import { MobileFileBrowser } from '@/components/MobileFileBrowser';

function MyComponent() {
  return (
    <MobileFileBrowser
      initialFolder="DOWNLOADS"
      allowMultiSelect={true}
      filterTypes={['.pdf', '.jpg', '.png']}
      onFileSelect={(files) => console.log('Selected:', files)}
      onFolderSelect={(folder, path) => console.log('Navigated:', folder, path)}
      showUpload={true}
      onUpload={async (files) => {
        // Upload files to server
        for (const file of files) {
          const content = await fileSystem.readFileAsBase64(file.path, 'DOWNLOADS');
          await fetch('/api/upload', {
            method: 'POST',
            body: JSON.stringify({ name: file.name, data: content })
          });
        }
      }}
    />
  );
}
```

## Folder Types

| Type | Android Location | iOS Location | Access |
|------|-----------------|--------------|--------|
| `DOWNLOADS` | `/Download` | Files app | Read/Write |
| `DOCUMENTS` | `/Documents` | App Documents | Read/Write |
| `PICTURES` | `/Pictures` | Photo Library | Read only |
| `DCIM` | `/DCIM/Camera` | Photo Library | Read only |
| `AUDIO` | Media Store | Media Library | Read only |
| `CACHE` | App cache | App cache | Read/Write |

## Camera Integration

```typescript
import { fileSystem } from '@/mobile';

// Take a photo
const photo = await fileSystem.takePhoto();
if (photo) {
  console.log('Photo saved:', photo.path);
}

// Pick from gallery
const photos = await fileSystem.pickPhotos(10); // max 10 photos
```

## Background Sync

```typescript
import { backgroundSync } from '@/mobile';

// Start monitoring a folder
const folderId = await backgroundSync.startMonitoring({
  folder: 'DOWNLOADS',
  subPath: 'Invoices',
  filterTypes: ['.pdf'],
  maxFileSizeMB: 50,
  uploadEndpoint: 'https://api.example.com/upload',
  backgroundSync: true,
  syncIntervalMinutes: 15,
});

// Listen for events
backgroundSync.onNewFile((file, folder) => {
  console.log('New file detected:', file.name);
});

backgroundSync.onSyncComplete((results) => {
  console.log('Sync complete:', results);
});

// Get current status
const status = backgroundSync.getStatus();
console.log(`Scanned: ${status.filesScanned}, Uploaded: ${status.filesUploaded}`);

// Stop monitoring
await backgroundSync.stopMonitoring(folderId);
```

## Platform-Specific Notes

### Android

- Requires `MANAGE_EXTERNAL_STORAGE` permission for full file access on Android 11+
- User must manually enable "All files access" in Settings
- Files are accessed via Storage Access Framework

### iOS

- Files are sandboxed to app container
- Use `EXTERNAL` folder for iCloud Drive access
- Photo Library requires user permission
- Background sync limited by iOS background execution rules

### Web

- Falls back to browser File API
- File system access requires user interaction
- Limited to selected files/folders via file picker

## Troubleshooting

### Permission Denied

```typescript
// Check current permissions
const status = await fileSystem.checkPermissions();

// Request permissions
const granted = await fileSystem.requestPermissions();
if (!granted.read) {
  // Guide user to app settings
}
```

### File Not Found

```typescript
// Check if file exists
const exists = await fileSystem.fileExists('file.pdf', 'DOWNLOADS');

// Get file info
const info = await fileSystem.getFileInfo('file.pdf', 'DOWNLOADS');
```

### Large Files

```typescript
// Read as base64 for upload
const base64 = await fileSystem.readFileAsBase64('large-file.pdf', 'DOWNLOADS');

// Upload in chunks if needed
const chunkSize = 1024 * 1024; // 1MB chunks
```

## Development Commands

```bash
# Build web app
npm run build

# Sync to native platforms
npm run cap:sync

# Open Android Studio
npm run cap:open:android

# Open Xcode
npm run cap:open:ios

# Run on Android device
npm run cap:android

# Run on iOS device
npm run cap:ios

# Live reload development
npx cap run android --livereload --external
```
