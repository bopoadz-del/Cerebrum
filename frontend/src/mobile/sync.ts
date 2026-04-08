/**
 * Background File Sync Module
 * 
 * Monitors specified folders for new files and automatically
 * syncs them to the server. Uses Capacitor Background Runner
 * for reliable background execution.
 */

import type { SpecialFolder, FileMetadata } from './fileSystem';
import { fileSystem } from './fileSystem';
import { Preferences } from '@capacitor/preferences';
import { LocalNotifications } from '@capacitor/local-notifications';

// Sync configuration
export interface SyncConfig {
  /** Folder to monitor */
  folder: SpecialFolder;
  /** Sub-path within the folder */
  subPath?: string;
  /** File types to sync (e.g., ['.pdf', '.jpg']) */
  filterTypes?: string[];
  /** Maximum file size in MB */
  maxFileSizeMB?: number;
  /** Whether to delete local file after successful sync */
  deleteAfterSync?: boolean;
  /** Custom upload endpoint */
  uploadEndpoint?: string;
  /** Whether to run in background */
  backgroundSync?: boolean;
  /** Sync interval in minutes (minimum 15) */
  syncIntervalMinutes?: number;
}

// Sync status
export interface SyncStatus {
  isRunning: boolean;
  folder: SpecialFolder | null;
  filesScanned: number;
  filesUploaded: number;
  filesFailed: number;
  lastSyncTime: number | null;
  nextSyncTime: number | null;
  errors: string[];
}

// Sync result for a single file
export interface FileSyncResult {
  file: FileMetadata;
  success: boolean;
  error?: string;
  serverId?: string;
  uploadedAt: number;
}

// Monitored folder entry
interface MonitoredFolder {
  id: string;
  config: SyncConfig;
  lastScannedFiles: Set<string>;
}

// In-memory state
const state: {
  monitoredFolders: Map<string, MonitoredFolder>;
  syncStatus: SyncStatus;
  syncIntervalId: ReturnType<typeof setInterval> | null;
  isInitialized: boolean;
} = {
  monitoredFolders: new Map(),
  syncStatus: {
    isRunning: false,
    folder: null,
    filesScanned: 0,
    filesUploaded: 0,
    filesFailed: 0,
    lastSyncTime: null,
    nextSyncTime: null,
    errors: [],
  },
  syncIntervalId: null,
  isInitialized: false,
};

// Event callbacks
const callbacks: {
  onNewFile?: (file: FileMetadata, folder: SpecialFolder) => void | Promise<void>;
  onSyncComplete?: (results: FileSyncResult[]) => void | Promise<void>;
  onSyncError?: (error: string) => void;
  onProgress?: (status: SyncStatus) => void;
} = {};

/**
 * Initialize the sync module
 */
async function initialize(): Promise<void> {
  if (state.isInitialized) return;

  try {
    // Load saved monitored folders
    const { value } = await Preferences.get({ key: 'sync_monitored_folders' });
    if (value) {
      const saved = JSON.parse(value);
      for (const [id, folder] of Object.entries(saved)) {
        state.monitoredFolders.set(id, {
          ...(folder as MonitoredFolder),
          lastScannedFiles: new Set((folder as MonitoredFolder).lastScannedFiles),
        });
      }
    }

    // Load sync status
    const { value: statusValue } = await Preferences.get({ key: 'sync_status' });
    if (statusValue) {
      const savedStatus = JSON.parse(statusValue);
      state.syncStatus = { ...state.syncStatus, ...savedStatus };
    }

    // Request notification permissions
    await LocalNotifications.requestPermissions();

    state.isInitialized = true;
    console.log('Background sync initialized');
  } catch (error) {
    console.error('Error initializing sync:', error);
  }
}

/**
 * Save monitored folders to persistent storage
 */
async function saveMonitoredFolders(): Promise<void> {
  const serializable: Record<string, Omit<MonitoredFolder, 'lastScannedFiles'> & { lastScannedFiles: string[] }> = {};
  
  for (const [id, folder] of state.monitoredFolders) {
    serializable[id] = {
      ...folder,
      lastScannedFiles: Array.from(folder.lastScannedFiles),
    };
  }

  await Preferences.set({
    key: 'sync_monitored_folders',
    value: JSON.stringify(serializable),
  });
}

/**
 * Save sync status to persistent storage
 */
async function saveSyncStatus(): Promise<void> {
  await Preferences.set({
    key: 'sync_status',
    value: JSON.stringify(state.syncStatus),
  });
}

/**
 * Generate unique folder ID
 */
function generateFolderId(folder: SpecialFolder, subPath?: string): string {
  return `${folder}_${subPath || 'root'}_${Date.now()}`;
}

/**
 * Start monitoring a folder for new files
 */
async function startMonitoring(config: SyncConfig): Promise<string> {
  await initialize();

  const folderId = generateFolderId(config.folder, config.subPath);
  
  const monitoredFolder: MonitoredFolder = {
    id: folderId,
    config,
    lastScannedFiles: new Set(),
  };

  state.monitoredFolders.set(folderId, monitoredFolder);
  await saveMonitoredFolders();

  // Perform initial scan
  await scanFolder(monitoredFolder);

  // Start background sync if enabled
  if (config.backgroundSync && !state.syncIntervalId) {
    startBackgroundSync(config.syncIntervalMinutes || 15);
  }

  console.log(`Started monitoring ${config.folder}${config.subPath ? '/' + config.subPath : ''}`);
  
  return folderId;
}

/**
 * Stop monitoring a folder
 */
async function stopMonitoring(folderId?: string): Promise<void> {
  if (folderId) {
    state.monitoredFolders.delete(folderId);
  } else {
    // Stop all monitoring
    state.monitoredFolders.clear();
    stopBackgroundSync();
  }

  await saveMonitoredFolders();
  console.log(`Stopped monitoring ${folderId || 'all folders'}`);
}

/**
 * Get list of monitored folders
 */
function getMonitoredFolders(): Array<{ id: string; config: SyncConfig }> {
  return Array.from(state.monitoredFolders.entries()).map(([id, folder]) => ({
    id,
    config: folder.config,
  }));
}

/**
 * Scan a folder for new files
 */
async function scanFolder(monitoredFolder: MonitoredFolder): Promise<FileSyncResult[]> {
  const { config, lastScannedFiles } = monitoredFolder;
  const results: FileSyncResult[] = [];

  try {
    state.syncStatus.isRunning = true;
    state.syncStatus.folder = config.folder;
    state.syncStatus.filesScanned = 0;
    state.syncStatus.filesUploaded = 0;
    state.syncStatus.filesFailed = 0;
    state.syncStatus.errors = [];

    callbacks.onProgress?.(state.syncStatus);

    // List files in the folder
    const files = await fileSystem.listFiles(config.folder, config.subPath);
    
    // Filter by type and size
    const filteredFiles = files.filter(file => {
      // Skip directories
      if (file.isDirectory) return false;

      // Check file type filter
      if (config.filterTypes && config.filterTypes.length > 0) {
        const ext = file.name.split('.').pop()?.toLowerCase();
        if (!ext || !config.filterTypes.some(type => 
          type.toLowerCase() === `.${ext}` || type.toLowerCase() === ext
        )) {
          return false;
        }
      }

      // Check file size
      if (config.maxFileSizeMB) {
        const maxBytes = config.maxFileSizeMB * 1024 * 1024;
        if (file.size > maxBytes) return false;
      }

      return true;
    });

    state.syncStatus.filesScanned = filteredFiles.length;
    callbacks.onProgress?.(state.syncStatus);

    // Check for new files
    const currentFiles = new Set(filteredFiles.map(f => f.path));
    const newFiles = filteredFiles.filter(file => !lastScannedFiles.has(file.path));

    for (const file of newFiles) {
      try {
        // Notify about new file
        callbacks.onNewFile?.(file, config.folder);

        // Auto-upload if endpoint is provided
        if (config.uploadEndpoint) {
          const result = await uploadFile(file, config);
          results.push(result);

          if (result.success) {
            state.syncStatus.filesUploaded++;
            
            // Delete local file if configured
            if (config.deleteAfterSync) {
              await fileSystem.deleteFile(file.path, config.folder);
            }
          } else {
            state.syncStatus.filesFailed++;
            if (result.error) {
              state.syncStatus.errors.push(result.error);
            }
          }
        }

        // Update scanned files
        monitoredFolder.lastScannedFiles.add(file.path);
        callbacks.onProgress?.(state.syncStatus);
      } catch (error) {
        const errorMsg = `Failed to process ${file.name}: ${error instanceof Error ? error.message : 'Unknown error'}`;
        state.syncStatus.errors.push(errorMsg);
        state.syncStatus.filesFailed++;
        
        results.push({
          file,
          success: false,
          error: errorMsg,
          uploadedAt: Date.now(),
        });
      }
    }

    // Remove deleted files from tracked set
    for (const trackedPath of lastScannedFiles) {
      if (!currentFiles.has(trackedPath)) {
        monitoredFolder.lastScannedFiles.delete(trackedPath);
      }
    }

    // Update status
    state.syncStatus.lastSyncTime = Date.now();
    state.syncStatus.isRunning = false;
    await saveSyncStatus();
    await saveMonitoredFolders();

    // Notify completion
    callbacks.onSyncComplete?.(results);

    return results;
  } catch (error) {
    const errorMsg = `Scan failed: ${error instanceof Error ? error.message : 'Unknown error'}`;
    state.syncStatus.errors.push(errorMsg);
    state.syncStatus.isRunning = false;
    callbacks.onSyncError?.(errorMsg);
    await saveSyncStatus();
    return results;
  }
}

/**
 * Upload a single file to the server
 */
async function uploadFile(
  file: FileMetadata,
  config: SyncConfig
): Promise<FileSyncResult> {
  try {
    if (!config.uploadEndpoint) {
      throw new Error('No upload endpoint configured');
    }

    // Read file as base64
    const base64Data = await fileSystem.readFileAsBase64(file.path, config.folder);
    
    // Create FormData-like payload
    const payload = {
      name: file.name,
      type: file.type,
      size: file.size,
      data: base64Data,
      folder: config.folder,
      uploadedAt: new Date().toISOString(),
    };

    // Upload to server
    const response = await fetch(config.uploadEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
    }

    const result = await response.json();

    return {
      file,
      success: true,
      serverId: result.id || result.fileId,
      uploadedAt: Date.now(),
    };
  } catch (error) {
    return {
      file,
      success: false,
      error: error instanceof Error ? error.message : 'Upload failed',
      uploadedAt: Date.now(),
    };
  }
}

/**
 * Trigger manual sync for all monitored folders
 */
async function syncNow(): Promise<FileSyncResult[]> {
  await initialize();
  
  const allResults: FileSyncResult[] = [];
  
  for (const [, folder] of state.monitoredFolders) {
    const results = await scanFolder(folder);
    allResults.push(...results);
  }

  return allResults;
}

/**
 * Start background sync interval
 */
function startBackgroundSync(intervalMinutes: number = 15): void {
  if (state.syncIntervalId) {
    clearInterval(state.syncIntervalId);
  }

  // Minimum 15 minutes to respect battery life
  const interval = Math.max(intervalMinutes, 15) * 60 * 1000;
  
  state.syncIntervalId = setInterval(() => {
    syncNow().catch(console.error);
  }, interval);

  state.syncStatus.nextSyncTime = Date.now() + interval;
  console.log(`Background sync started with ${intervalMinutes} minute interval`);
}

/**
 * Stop background sync
 */
function stopBackgroundSync(): void {
  if (state.syncIntervalId) {
    clearInterval(state.syncIntervalId);
    state.syncIntervalId = null;
  }
  state.syncStatus.nextSyncTime = null;
  console.log('Background sync stopped');
}

/**
 * Get current sync status
 */
function getStatus(): SyncStatus {
  return { ...state.syncStatus };
}

/**
 * Register event callbacks
 */
function onNewFile(callback: (file: FileMetadata, folder: SpecialFolder) => void | Promise<void>): void {
  callbacks.onNewFile = callback;
}

function onSyncComplete(callback: (results: FileSyncResult[]) => void | Promise<void>): void {
  callbacks.onSyncComplete = callback;
}

function onSyncError(callback: (error: string) => void): void {
  callbacks.onSyncError = callback;
}

function onProgress(callback: (status: SyncStatus) => void): void {
  callbacks.onProgress = callback;
}

/**
 * Clear sync history and reset state
 */
async function clearHistory(): Promise<void> {
  state.monitoredFolders.clear();
  state.syncStatus = {
    isRunning: false,
    folder: null,
    filesScanned: 0,
    filesUploaded: 0,
    filesFailed: 0,
    lastSyncTime: null,
    nextSyncTime: null,
    errors: [],
  };
  
  await Preferences.remove({ key: 'sync_monitored_folders' });
  await Preferences.remove({ key: 'sync_status' });
  
  console.log('Sync history cleared');
}

/**
 * Send local notification about sync status
 */
async function sendSyncNotification(
  title: string,
  body: string,
  actionTypeId?: string
): Promise<void> {
  try {
    await LocalNotifications.schedule({
      notifications: [{
        id: Date.now(),
        title,
        body,
        actionTypeId,
        extra: {
          type: 'sync',
          timestamp: Date.now(),
        },
      }],
    });
  } catch (error) {
    console.error('Error sending notification:', error);
  }
}

// Export the background sync API
export const backgroundSync = {
  initialize,
  startMonitoring,
  stopMonitoring,
  getMonitoredFolders,
  syncNow,
  getStatus,
  clearHistory,
  onNewFile,
  onSyncComplete,
  onSyncError,
  onProgress,
  sendSyncNotification,
};

export default backgroundSync;
