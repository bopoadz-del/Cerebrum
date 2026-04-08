// File processing utilities for chat context
// Processes PDF, Audio, Images and indexes them with session context

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';

// File size limits (in bytes)
export const FILE_SIZE_LIMITS = {
  IMAGE: 10 * 1024 * 1024,      // 10 MB
  DOCUMENT: 50 * 1024 * 1024,   // 50 MB
  AUDIO: 100 * 1024 * 1024,     // 100 MB
  VIDEO: 500 * 1024 * 1024,     // 500 MB
};

// Supported MIME types
export const SUPPORTED_TYPES = {
  IMAGES: ['image/jpeg', 'image/png', 'image/webp', 'image/gif'],
  DOCUMENTS: ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'text/plain'],
  AUDIO: ['audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/mp4', 'audio/x-m4a', 'audio/ogg', 'audio/webm'],
};

// All supported types combined
export const ALL_SUPPORTED_TYPES = [
  ...SUPPORTED_TYPES.IMAGES,
  ...SUPPORTED_TYPES.DOCUMENTS,
  ...SUPPORTED_TYPES.AUDIO,
];

/**
 * Validate file on selection before upload
 * Returns detailed validation result for inline error display
 */
export interface FileValidationResult {
  valid: boolean;
  error?: string;
  errorType?: 'size' | 'type' | 'unknown';
  maxSize?: number;
  fileSize?: number;
}

export function validateFileOnSelect(file: File): FileValidationResult {
  // Check file type first
  const isSupported = ALL_SUPPORTED_TYPES.includes(file.type);
  if (!isSupported) {
    // Allow unknown types to be uploaded as generic files (with size limit)
    if (file.size > FILE_SIZE_LIMITS.DOCUMENT) {
      return { 
        valid: false, 
        error: `File too large. Max size: ${formatFileSize(FILE_SIZE_LIMITS.DOCUMENT)}`,
        errorType: 'size',
        maxSize: FILE_SIZE_LIMITS.DOCUMENT,
        fileSize: file.size,
      };
    }
    // Unknown type but within size limit - allow as generic file
    return { valid: true };
  }
  
  // Check file size based on type
  if (SUPPORTED_TYPES.IMAGES.includes(file.type)) {
    if (file.size > FILE_SIZE_LIMITS.IMAGE) {
      return { 
        valid: false, 
        error: `Image too large. Max size: ${formatFileSize(FILE_SIZE_LIMITS.IMAGE)}`,
        errorType: 'size',
        maxSize: FILE_SIZE_LIMITS.IMAGE,
        fileSize: file.size,
      };
    }
  } else if (SUPPORTED_TYPES.DOCUMENTS.includes(file.type)) {
    if (file.size > FILE_SIZE_LIMITS.DOCUMENT) {
      return { 
        valid: false, 
        error: `Document too large. Max size: ${formatFileSize(FILE_SIZE_LIMITS.DOCUMENT)}`,
        errorType: 'size',
        maxSize: FILE_SIZE_LIMITS.DOCUMENT,
        fileSize: file.size,
      };
    }
  } else if (SUPPORTED_TYPES.AUDIO.includes(file.type)) {
    if (file.size > FILE_SIZE_LIMITS.AUDIO) {
      return { 
        valid: false, 
        error: `Audio file too large. Max size: ${formatFileSize(FILE_SIZE_LIMITS.AUDIO)}`,
        errorType: 'size',
        maxSize: FILE_SIZE_LIMITS.AUDIO,
        fileSize: file.size,
      };
    }
  }
  
  return { valid: true };
}

/**
 * Validate file before upload
 * Returns { valid: true } or { valid: false, error: string }
 */
export function validateFile(file: File): { valid: boolean; error?: string } {
  // Check file size based on type
  if (SUPPORTED_TYPES.IMAGES.includes(file.type)) {
    if (file.size > FILE_SIZE_LIMITS.IMAGE) {
      return { valid: false, error: `Image too large. Max size: ${formatFileSize(FILE_SIZE_LIMITS.IMAGE)}` };
    }
  } else if (SUPPORTED_TYPES.DOCUMENTS.includes(file.type)) {
    if (file.size > FILE_SIZE_LIMITS.DOCUMENT) {
      return { valid: false, error: `Document too large. Max size: ${formatFileSize(FILE_SIZE_LIMITS.DOCUMENT)}` };
    }
  } else if (SUPPORTED_TYPES.AUDIO.includes(file.type)) {
    if (file.size > FILE_SIZE_LIMITS.AUDIO) {
      return { valid: false, error: `Audio file too large. Max size: ${formatFileSize(FILE_SIZE_LIMITS.AUDIO)}` };
    }
  } else {
    // Unknown type - use document limit as default
    if (file.size > FILE_SIZE_LIMITS.DOCUMENT) {
      return { valid: false, error: `File too large. Max size: ${formatFileSize(FILE_SIZE_LIMITS.DOCUMENT)}` };
    }
  }
  
  return { valid: true };
}

/**
 * Format bytes to human-readable string
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
const getApiUrl = () => {
  const url = API_BASE_URL.replace(/\/?$/, '');
  return url.endsWith('/api/v1') ? url : `${url}/api/v1`;
};

export interface ProcessingResult {
  success: boolean;
  text: string;
  metadata: {
    type: string;
    wordCount?: number;
    duration?: string;
    confidence?: number;
    entities?: string[];
    fileName: string;
  };
  error?: string;
}

export interface IndexResult {
  success: boolean;
  message: string;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

const getAuthToken = () => localStorage.getItem('cerebrum_auth_token_v1') || localStorage.getItem('token') || '';
const getSessionId = () => localStorage.getItem('cerebrum_chat_session_id') || '';

/**
 * Upload file with progress tracking using XMLHttpRequest
 * Enhanced for mobile compatibility with better error handling
 */
export function uploadFileWithProgress(
  url: string,
  formData: FormData,
  onProgress?: (progress: UploadProgress) => void,
  onLoad?: (response: string) => void,
  onError?: (error: string) => void
): XMLHttpRequest {
  const xhr = new XMLHttpRequest();
  const token = getAuthToken();
  
  xhr.open('POST', url, true);
  
  // Set timeout for mobile networks (2 minutes for large files on slow connections)
  xhr.timeout = 120000;
  
  // Always set Authorization header if token exists
  // IMPORTANT: For mobile, we need explicit headers for CORS preflight
  if (token) {
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
  }
  
  // Track upload progress
  xhr.upload.onprogress = (event) => {
    if (event.lengthComputable && onProgress) {
      const percentage = Math.round((event.loaded / event.total) * 100);
      onProgress({
        loaded: event.loaded,
        total: event.total,
        percentage,
      });
    }
  };
  
  xhr.onload = () => {
    if (xhr.status >= 200 && xhr.status < 300) {
      onLoad?.(xhr.responseText);
    } else {
      // Handle specific HTTP error codes with user-friendly messages
      let errorMsg: string;
      
      if (xhr.status === 401) {
        errorMsg = 'Please sign in to upload files';
      } else {
        errorMsg = `Upload failed: ${xhr.status} ${xhr.statusText}`;
        try {
          const errorData = JSON.parse(xhr.responseText);
          errorMsg = errorData.detail || errorMsg;
        } catch {
          // Use default error message
        }
      }
      
      console.error('[Upload] Server error:', xhr.status, xhr.statusText, xhr.responseText);
      onError?.(errorMsg);
    }
  };
  
  xhr.onerror = () => {
    // Enhanced error logging for mobile debugging
    console.error('[Upload] Network error details:', {
      url,
      readyState: xhr.readyState,
      status: xhr.status,
      statusText: xhr.statusText,
      hasToken: !!token,
    });

    // Provide more specific error messages based on common mobile issues
    let errorMessage: string;

    if (xhr.status === 0) {
      // Status 0 typically means CORS error or network failure
      errorMessage = 'Connection failed. This may be due to: (1) CORS policy issue, (2) Network connectivity, or (3) Server unavailable. Please try again.';
    } else if (xhr.status === 401) {
      errorMessage = 'Please sign in to upload files';
    } else if (xhr.status === 413) {
      errorMessage = 'File too large. Please choose a smaller file.';
    } else {
      errorMessage = 'Network error. Please check your connection and try again.';
    }

    onError?.(errorMessage);
  };
  
  xhr.ontimeout = () => {
    console.error('[Upload] Request timeout');
    onError?.('Upload timed out. Please try again with a smaller file or better connection.');
  };
  
  xhr.onabort = () => {
    onError?.('Upload cancelled.');
  };
  
  xhr.send(formData);
  return xhr;
}

/**
 * Process PDF/Image file via public upload endpoint with progress tracking
 */
export function processDocument(
  file: File,
  onProgress?: (stage: 'uploading' | 'processing' | 'indexing', percentage?: number) => void
): Promise<ProcessingResult> {
  return new Promise((resolve) => {
    // Validate file before upload
    const validation = validateFile(file);
    if (!validation.valid) {
      resolve({
        success: false,
        text: '',
        metadata: {
          type: file.type,
          fileName: file.name,
        },
        error: validation.error,
      });
      return;
    }

    onProgress?.('uploading', 0);

    const formData = new FormData();
    formData.append('file', file);

    uploadFileWithProgress(
      `${API_BASE_URL}/api/v1/documents/upload/public`,
      formData,
      (progress) => {
        onProgress?.('uploading', progress.percentage);
      },
      (responseText) => {
        try {
          const data = JSON.parse(responseText);
          const text = data.text || '';

          resolve({
            success: data.success && data.can_extract_text,
            text,
            metadata: {
              type: data.document_type || file.type.split('/')[0].toUpperCase(),
              wordCount: data.text_length || 0,
              fileName: file.name,
            },
          });
        } catch (error) {
          resolve({
            success: false,
            text: '',
            metadata: { type: 'unknown', fileName: file.name },
            error: 'Failed to parse server response',
          });
        }
      },
      (error) => {
        resolve({
          success: false,
          text: '',
          metadata: { type: 'unknown', fileName: file.name },
          error,
        });
      }
    );
  });
}

/**
 * Process Audio file via transcribe endpoint with progress tracking
 */
export function processAudio(
  file: File,
  onProgress?: (stage: 'uploading' | 'processing' | 'indexing', percentage?: number) => void
): Promise<ProcessingResult> {
  return new Promise((resolve) => {
    // Validate file before upload
    const validation = validateFile(file);
    if (!validation.valid) {
      resolve({
        success: false,
        text: '',
        metadata: {
          type: file.type,
          fileName: file.name,
        },
        error: validation.error,
      });
      return;
    }

    onProgress?.('uploading', 0);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('use_parallel', 'true');

    uploadFileWithProgress(
      `${API_BASE_URL}/api/v1/documents/transcribe`,
      formData,
      (progress) => {
        onProgress?.('uploading', progress.percentage);
      },
      (responseText) => {
        try {
          const data = JSON.parse(responseText);
          const durationFormatted = formatDuration(data.duration);

          resolve({
            success: true,
            text: data.text,
            metadata: {
              type: 'Audio Transcription',
              wordCount: data.word_count,
              duration: durationFormatted,
              fileName: file.name,
            },
          });
        } catch (error) {
          resolve({
            success: false,
            text: '',
            metadata: { type: 'audio', fileName: file.name },
            error: 'Failed to parse server response',
          });
        }
      },
      (error) => {
        resolve({
          success: false,
          text: '',
          metadata: { type: 'audio', fileName: file.name },
          error,
        });
      }
    );
  });
}

/**
 * Upload file to chat endpoint with progress tracking
 * Enhanced for mobile browser compatibility
 */
export function uploadChatFile(
  file: File,
  onProgress?: (percentage: number) => void
): Promise<{ success: boolean; data?: { url: string; text_length?: number; text_extracted?: boolean }; error?: string }> {
  return new Promise((resolve) => {
    // Validate file before attempting upload
    const validation = validateFile(file);
    if (!validation.valid) {
      resolve({
        success: false,
        error: validation.error,
      });
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const uploadUrl = `${getApiUrl()}/documents/upload/chat`;
    
    // Debug logging for mobile
    console.log('[Upload] Starting chat file upload:', {
      filename: file.name,
      size: file.size,
      type: file.type,
      url: uploadUrl,
      hasToken: !!getAuthToken(),
    });

    uploadFileWithProgress(
      uploadUrl,
      formData,
      (progress) => {
        onProgress?.(progress.percentage);
      },
      (responseText) => {
        try {
          const data = JSON.parse(responseText);
          console.log('[Upload] Upload successful:', data);
          resolve({
            success: true,
            data: {
              url: data.url,
              text_length: data.text_length,
              text_extracted: data.text_extracted,
            },
          });
        } catch (error) {
          console.error('[Upload] Failed to parse response:', error, responseText);
          resolve({
            success: false,
            error: 'Failed to parse server response',
          });
        }
      },
      (error) => {
        console.error('[Upload] Upload failed:', error);
        resolve({
          success: false,
          error,
        });
      }
    );
  });
}

/**
 * Index processed content to chat with session context
 */
export async function indexToChatWithSession(
  fileName: string,
  text: string,
  metadata: ProcessingResult['metadata'],
  sessionId?: string
): Promise<IndexResult> {
  try {
    const token = getAuthToken();
    const activeSessionId = sessionId || getSessionId() || 'default';
    
    // Build rich metadata header
    const metaLines = [
      `[Processed File: ${fileName}]`,
      `Session: ${activeSessionId}`,
      `Type: ${metadata.type}`,
    ];
    
    if (metadata.wordCount) metaLines.push(`Word Count: ${metadata.wordCount}`);
    if (metadata.duration) metaLines.push(`Duration: ${metadata.duration}`);
    if (metadata.confidence) metaLines.push(`Confidence: ${Math.round(metadata.confidence * 100)}%`);
    if (metadata.entities?.length) metaLines.push(`Entities: ${metadata.entities.slice(0, 10).join(', ')}`);
    
    const contentWithMetadata = `${metaLines.join('\n')}\n\n---\n\n${text}`;

    const textBlob = new Blob([contentWithMetadata], { type: 'text/plain' });
    const indexFile = new File([textBlob], `${fileName}.txt`, { type: 'text/plain' });
    
    const formData = new FormData();
    formData.append('file', indexFile);
    // Add session_id as metadata for the backend to use
    formData.append('session_id', activeSessionId);

    const response = await fetch(`${getApiUrl()}/documents/upload/chat`, {
      method: 'POST',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Indexing failed: ${errorText}`);
    }

    return {
      success: true,
      message: 'Indexed to chat context',
    };
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : 'Indexing failed',
    };
  }
}

/**
 * Process and index any file type with one call
 */
export async function processAndIndexFile(
  file: File,
  sessionId?: string,
  onProgress?: (stage: 'uploading' | 'processing' | 'indexing', percentage?: number) => void
): Promise<{ processing: ProcessingResult; indexing: IndexResult }> {
  const fileType = file.type;
  let processing: ProcessingResult;
  
  // Route to appropriate processor
  if (fileType.startsWith('audio/') || fileType.startsWith('video/')) {
    processing = await processAudio(file, onProgress);
  } else {
    // PDF, Image, or document
    processing = await processDocument(file, onProgress);
  }
  
  if (!processing.success || !processing.text) {
    return {
      processing,
      indexing: { 
        success: false, 
        message: processing.error || 'OCR could not extract text. Please try a clearer image or PDF with selectable text.' 
      },
    };
  }
  
  onProgress?.('indexing');
  const indexing = await indexToChatWithSession(
    processing.metadata.fileName,
    processing.text,
    processing.metadata,
    sessionId
  );
  
  return { processing, indexing };
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}
