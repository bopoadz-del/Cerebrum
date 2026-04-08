// Mobile module exports
export { fileSystem, type SpecialFolder, type FileMetadata, type PermissionStatus, type FileContent } from './fileSystem';
export type { 
  SyncConfig, 
  SyncStatus, 
  FileSyncResult 
} from './sync';
export { backgroundSync } from './sync';
export { offlineQueue, type QueuedUpload, type QueueStats } from './offlineQueue';

// Mobile UI Components
export { MobileLayout } from './MobileLayout';
export { ProjectsTab } from './ProjectsTab';
export { ChatTab } from './ChatTab';
export { OutcomesTab } from './OutcomesTab';
