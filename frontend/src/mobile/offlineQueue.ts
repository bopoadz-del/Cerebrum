import { Preferences } from '@capacitor/preferences';
import { Filesystem, Directory } from '@capacitor/filesystem';

/**
 * Offline Upload Queue
 * Stores pending uploads in local SQLite-like storage for retry when online
 */

const QUEUE_KEY = 'offline_upload_queue';
const MAX_RETRIES = 5;
const RETRY_DELAYS = [5000, 15000, 60000, 300000, 900000]; // 5s, 15s, 1m, 5m, 15m

export interface QueuedUpload {
  id: string;
  filePath: string;
  fileName: string;
  mimeType: string;
  targetEndpoint: string;
  metadata?: Record<string, any>;
  retryCount: number;
  queuedAt: string;
  lastAttempt?: string;
  error?: string;
  priority: 'high' | 'normal' | 'low';
}

export interface QueueStats {
  total: number;
  pending: number;
  failed: number;
  uploading: number;
  nextRetryIn?: number;
}

class OfflineQueue {
  private isProcessing: boolean = false;
  private abortController: AbortController | null = null;

  /**
   * Add file to upload queue
   */
  async enqueue(upload: Omit<QueuedUpload, 'id' | 'retryCount' | 'queuedAt'>): Promise<string> {
    const id = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const queuedUpload: QueuedUpload = {
      ...upload,
      id,
      retryCount: 0,
      queuedAt: new Date().toISOString(),
    };

    const queue = await this.getQueue();
    queue.push(queuedUpload);
    await this.saveQueue(queue);

    // Start processing if not already running
    if (!this.isProcessing) {
      this.processQueue();
    }

    return id;
  }

  /**
   * Get all queued uploads
   */
  async getQueue(): Promise<QueuedUpload[]> {
    try {
      const { value } = await Preferences.get({ key: QUEUE_KEY });
      return value ? JSON.parse(value) : [];
    } catch (e) {
      console.error('Failed to load upload queue:', e);
      return [];
    }
  }

  /**
   * Save queue to storage
   */
  private async saveQueue(queue: QueuedUpload[]): Promise<void> {
    await Preferences.set({
      key: QUEUE_KEY,
      value: JSON.stringify(queue),
    });
  }

  /**
   * Get queue statistics
   */
  async getStats(): Promise<QueueStats> {
    const queue = await this.getQueue();
    const now = Date.now();
    
    let nextRetryIn: number | undefined;
    
    for (const item of queue) {
      if (item.retryCount < MAX_RETRIES && item.lastAttempt) {
        const lastAttempt = new Date(item.lastAttempt).getTime();
        const delay = RETRY_DELAYS[Math.min(item.retryCount, RETRY_DELAYS.length - 1)];
        const retryTime = lastAttempt + delay;
        
        if (retryTime > now) {
          const waitTime = retryTime - now;
          if (!nextRetryIn || waitTime < nextRetryIn) {
            nextRetryIn = waitTime;
          }
        }
      }
    }

    return {
      total: queue.length,
      pending: queue.filter(u => u.retryCount === 0).length,
      failed: queue.filter(u => u.retryCount >= MAX_RETRIES).length,
      uploading: queue.filter(u => !u.lastAttempt && u.retryCount > 0).length,
      nextRetryIn,
    };
  }

  /**
   * Remove item from queue
   */
  async remove(id: string): Promise<void> {
    const queue = await this.getQueue();
    const filtered = queue.filter(u => u.id !== id);
    await this.saveQueue(filtered);
  }

  /**
   * Clear completed/failed uploads
   */
  async clearCompleted(): Promise<number> {
    const queue = await this.getQueue();
    const remaining = queue.filter(u => u.retryCount < MAX_RETRIES);
    const cleared = queue.length - remaining.length;
    await this.saveQueue(remaining);
    return cleared;
  }

  /**
   * Process upload queue
   */
  async processQueue(): Promise<void> {
    if (this.isProcessing) return;
    
    this.isProcessing = true;
    this.abortController = new AbortController();

    try {
      // Check network connectivity
      if (!navigator.onLine) {
        console.log('Offline - queue processing paused');
        return;
      }

      const queue = await this.getQueue();
      const now = Date.now();

      // Sort by priority and retry time
      const sorted = queue
        .filter(u => u.retryCount < MAX_RETRIES)
        .sort((a, b) => {
          // Priority order: high > normal > low
          const priorityOrder = { high: 0, normal: 1, low: 2 };
          const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
          if (priorityDiff !== 0) return priorityDiff;
          
          // Then by retry time (earliest first)
          const aTime = a.lastAttempt 
            ? new Date(a.lastAttempt).getTime() + RETRY_DELAYS[Math.min(a.retryCount, RETRY_DELAYS.length - 1)]
            : 0;
          const bTime = b.lastAttempt 
            ? new Date(b.lastAttempt).getTime() + RETRY_DELAYS[Math.min(b.retryCount, RETRY_DELAYS.length - 1)]
            : 0;
          return aTime - bTime;
        });

      for (const upload of sorted) {
        if (this.abortController.signal.aborted) break;

        // Check if it's time to retry
        if (upload.lastAttempt && upload.retryCount > 0) {
          const lastAttempt = new Date(upload.lastAttempt).getTime();
          const delay = RETRY_DELAYS[Math.min(upload.retryCount, RETRY_DELAYS.length - 1)];
          if (now < lastAttempt + delay) continue;
        }

        await this.processUpload(upload);
      }
    } finally {
      this.isProcessing = false;
      this.abortController = null;
    }
  }

  /**
   * Process single upload
   */
  private async processUpload(upload: QueuedUpload): Promise<void> {
    try {
      // Read file
      const { data } = await Filesystem.readFile({
        path: upload.filePath,
        directory: Directory.Data,
      });

      // Prepare form data
      const formData = new FormData();
      const blob = await (await fetch(`data:${upload.mimeType};base64,${data}`)).blob();
      formData.append('file', blob, upload.fileName);
      
      if (upload.metadata) {
        formData.append('metadata', JSON.stringify(upload.metadata));
      }

      // Upload with timeout and abort support
      const response = await fetch(upload.targetEndpoint, {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        signal: this.abortController?.signal,
      });

      if (response.ok) {
        // Success - remove from queue
        await this.remove(upload.id);
        console.log(`Upload completed: ${upload.fileName}`);
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      console.error(`Upload failed (${upload.fileName}):`, error);
      
      // Update retry count
      const queue = await this.getQueue();
      const index = queue.findIndex(u => u.id === upload.id);
      if (index !== -1) {
        queue[index].retryCount++;
        queue[index].lastAttempt = new Date().toISOString();
        queue[index].error = error instanceof Error ? error.message : 'Unknown error';
        await this.saveQueue(queue);
      }
    }
  }

  /**
   * Pause queue processing
   */
  pause(): void {
    this.abortController?.abort();
    this.isProcessing = false;
  }

  /**
   * Retry a specific failed upload
   */
  async retry(id: string): Promise<void> {
    const queue = await this.getQueue();
    const upload = queue.find(u => u.id === id);
    if (upload && upload.retryCount >= MAX_RETRIES) {
      upload.retryCount = 0;
      upload.error = undefined;
      await this.saveQueue(queue);
      this.processQueue();
    }
  }
}

export const offlineQueue = new OfflineQueue();

// Auto-process on network change
window.addEventListener('online', () => {
  console.log('Network online - resuming upload queue');
  offlineQueue.processQueue();
});

window.addEventListener('offline', () => {
  console.log('Network offline - pausing upload queue');
  offlineQueue.pause();
});
