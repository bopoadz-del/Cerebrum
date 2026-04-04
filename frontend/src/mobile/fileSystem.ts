/**
 * Mobile File System Access Wrapper
 * 
 * Provides a unified interface for accessing native mobile file systems
 * using Capacitor's Filesystem plugin with enhanced functionality for
 * Downloads, Documents, and Camera folders.
 */

import type { ReadFileResult, ReaddirResult } from '@capacitor/filesystem';
import { Filesystem, Directory, Encoding } from '@capacitor/filesystem';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { Preferences } from '@capacitor/preferences';
import { Capacitor } from '@capacitor/core';

// Platform detection
export const isNativePlatform = () => Capacitor.isNativePlatform();
export const getPlatform = () => Capacitor.getPlatform();

// Folder type definitions
export type SpecialFolder = 
  | 'DOWNLOADS' 
  | 'DOCUMENTS' 
  | 'PICTURES' 
  | 'DCIM' 
  | 'AUDIO' 
  | 'CACHE' 
  | 'EXTERNAL';

// File metadata interface
export interface FileMetadata {
  name: string;
  path: string;
  size: number;
  type: string;
  lastModified: number;
  uri?: string;
  isDirectory: boolean;
}

// Permission status
export interface PermissionStatus {
  read: boolean;
  write: boolean;
  camera: boolean;
  photos: boolean;
}

// File content types
export type FileContent = string | Blob | ArrayBuffer;

/**
 * Maps special folder types to Capacitor Directory enums
 */
function getDirectoryForFolder(folder: SpecialFolder): Directory {
  switch (folder) {
    case 'DOWNLOADS':
    case 'DOCUMENTS':
      return Directory.Documents;
    case 'PICTURES':
    case 'DCIM':
      return Directory.External;
    case 'AUDIO':
      return Directory.External;
    case 'CACHE':
      return Directory.Cache;
    case 'EXTERNAL':
      return Directory.External;
    default:
      return Directory.Data;
  }
}

/**
 * Gets the folder path based on platform and folder type
 */
function getFolderPath(folder: SpecialFolder): string {
  const platform = getPlatform();
  
  if (platform === 'android') {
    switch (folder) {
      case 'DOWNLOADS':
        return 'Download';
      case 'DOCUMENTS':
        return 'Documents';
      case 'PICTURES':
        return 'Pictures';
      case 'DCIM':
        return 'DCIM/Camera';
      case 'AUDIO':
        return 'Music';
      case 'CACHE':
        return '';
      case 'EXTERNAL':
        return '';
      default:
        return '';
    }
  }
  
  // iOS and web use relative paths
  switch (folder) {
    case 'DOWNLOADS':
      return 'Downloads';
    case 'DOCUMENTS':
      return 'Documents';
    case 'PICTURES':
      return 'Pictures';
    case 'DCIM':
      return 'Camera';
    case 'AUDIO':
      return 'Audio';
    case 'CACHE':
      return '';
    case 'EXTERNAL':
      return 'Files';
    default:
      return '';
  }
}

/**
 * Request all necessary permissions for file system access
 */
async function requestPermissions(): Promise<PermissionStatus> {
  if (!isNativePlatform()) {
    // Web platform - permissions handled by browser
    return { read: true, write: true, camera: true, photos: true };
  }

  const status: PermissionStatus = {
    read: false,
    write: false,
    camera: false,
    photos: false,
  };

  try {
    // Request camera permissions
    const cameraPermission = await Camera.requestPermissions();
    status.camera = cameraPermission.camera === 'granted';
    status.photos = cameraPermission.photos === 'granted';

    // Filesystem permissions on mobile are handled at the OS level
    // For Android 11+, MANAGE_EXTERNAL_STORAGE is required for broad access
    status.read = true;
    status.write = true;

    // Store permission status
    await Preferences.set({
      key: 'filesystem_permissions',
      value: JSON.stringify(status),
    });

    return status;
  } catch (error) {
    console.error('Error requesting permissions:', error);
    return status;
  }
}

/**
 * Check current permission status
 */
async function checkPermissions(): Promise<PermissionStatus> {
  if (!isNativePlatform()) {
    return { read: true, write: true, camera: true, photos: true };
  }

  try {
    const { value } = await Preferences.get({ key: 'filesystem_permissions' });
    if (value) {
      return JSON.parse(value);
    }
  } catch (error) {
    console.error('Error checking permissions:', error);
  }

  return { read: false, write: false, camera: false, photos: false };
}

/**
 * List files in a special folder
 */
async function listFiles(
  folder: SpecialFolder,
  subPath: string = ''
): Promise<FileMetadata[]> {
  try {
    const directory = getDirectoryForFolder(folder);
    const folderPath = getFolderPath(folder);
    const fullPath = subPath 
      ? `${folderPath}/${subPath}`.replace(/\/+/g, '/')
      : folderPath;

    const result: ReaddirResult = await Filesystem.readdir({
      path: fullPath,
      directory,
    });

    const files: FileMetadata[] = [];

    for (const item of result.files) {
      try {
        const itemName = typeof item === 'string' ? item : item.name;
        const itemPath = fullPath ? `${fullPath}/${itemName}` : itemName;
        const statResult = await Filesystem.stat({
          path: itemPath,
          directory,
        });

        files.push({
          name: itemName,
          path: itemPath,
          size: statResult.size || 0,
          type: getFileType(itemName),
          lastModified: statResult.mtime || Date.now(),
          uri: statResult.uri,
          isDirectory: statResult.type === 'directory',
        });
      } catch (statError) {
        // If stat fails, still include the file with basic info
        const itemName = typeof item === 'string' ? item : item.name;
        files.push({
          name: itemName,
          path: fullPath ? `${fullPath}/${itemName}` : itemName,
          size: 0,
          type: getFileType(itemName),
          lastModified: Date.now(),
          isDirectory: false,
        });
      }
    }

    return files.sort((a, b) => {
      // Directories first, then alphabetical
      if (a.isDirectory !== b.isDirectory) {
        return a.isDirectory ? -1 : 1;
      }
      return a.name.localeCompare(b.name);
    });
  } catch (error) {
    console.error(`Error listing files in ${folder}:`, error);
    return [];
  }
}

/**
 * Read file content
 */
async function readFile(
  path: string,
  folder: SpecialFolder = 'DOCUMENTS',
  encoding: Encoding = Encoding.UTF8
): Promise<string | Blob> {
  try {
    const directory = getDirectoryForFolder(folder);
    const folderPath = getFolderPath(folder);
    const fullPath = path.startsWith(folderPath) ? path : `${folderPath}/${path}`;

    const result: ReadFileResult = await Filesystem.readFile({
      path: fullPath,
      directory,
      encoding: encoding === Encoding.UTF8 ? Encoding.UTF8 : undefined,
    });

    return result.data || '';
  } catch (error) {
    console.error(`Error reading file ${path}:`, error);
    throw error;
  }
}

/**
 * Read file as base64
 */
async function readFileAsBase64(
  path: string,
  folder: SpecialFolder = 'DOCUMENTS'
): Promise<string> {
  try {
    const directory = getDirectoryForFolder(folder);
    const folderPath = getFolderPath(folder);
    const fullPath = path.startsWith(folderPath) ? path : `${folderPath}/${path}`;

    const result = await Filesystem.readFile({
      path: fullPath,
      directory,
    });

    return result.data as string;
  } catch (error) {
    console.error(`Error reading file as base64 ${path}:`, error);
    throw error;
  }
}

/**
 * Write file content
 */
async function writeFile(
  path: string,
  data: string,
  folder: SpecialFolder = 'DOCUMENTS',
  encoding: Encoding = Encoding.UTF8,
  recursive: boolean = true
): Promise<void> {
  try {
    const directory = getDirectoryForFolder(folder);
    const folderPath = getFolderPath(folder);
    const fullPath = path.startsWith(folderPath) ? path : `${folderPath}/${path}`;

    // Ensure parent directory exists
    if (recursive) {
      const parentDir = fullPath.substring(0, fullPath.lastIndexOf('/'));
      if (parentDir) {
        try {
          await Filesystem.mkdir({
            path: parentDir,
            directory,
            recursive: true,
          });
        } catch (mkdirError) {
          // Directory may already exist
        }
      }
    }

    await Filesystem.writeFile({
      path: fullPath,
      data,
      directory,
      encoding: encoding === Encoding.UTF8 ? Encoding.UTF8 : undefined,
    });
  } catch (error) {
    console.error(`Error writing file ${path}:`, error);
    throw error;
  }
}

/**
 * Delete a file
 */
async function deleteFile(
  path: string,
  folder: SpecialFolder = 'DOCUMENTS'
): Promise<void> {
  try {
    const directory = getDirectoryForFolder(folder);
    const folderPath = getFolderPath(folder);
    const fullPath = path.startsWith(folderPath) ? path : `${folderPath}/${path}`;

    await Filesystem.deleteFile({
      path: fullPath,
      directory,
    });
  } catch (error) {
    console.error(`Error deleting file ${path}:`, error);
    throw error;
  }
}

/**
 * Create a directory
 */
async function createDirectory(
  path: string,
  folder: SpecialFolder = 'DOCUMENTS',
  recursive: boolean = true
): Promise<void> {
  try {
    const directory = getDirectoryForFolder(folder);
    const folderPath = getFolderPath(folder);
    const fullPath = path.startsWith(folderPath) ? path : `${folderPath}/${path}`;

    await Filesystem.mkdir({
      path: fullPath,
      directory,
      recursive,
    });
  } catch (error) {
    console.error(`Error creating directory ${path}:`, error);
    throw error;
  }
}

/**
 * Delete a directory
 */
async function deleteDirectory(
  path: string,
  folder: SpecialFolder = 'DOCUMENTS',
  recursive: boolean = true
): Promise<void> {
  try {
    const directory = getDirectoryForFolder(folder);
    const folderPath = getFolderPath(folder);
    const fullPath = path.startsWith(folderPath) ? path : `${folderPath}/${path}`;

    await Filesystem.rmdir({
      path: fullPath,
      directory,
      recursive,
    });
  } catch (error) {
    console.error(`Error deleting directory ${path}:`, error);
    throw error;
  }
}

/**
 * Check if a file exists
 */
async function fileExists(
  path: string,
  folder: SpecialFolder = 'DOCUMENTS'
): Promise<boolean> {
  try {
    const directory = getDirectoryForFolder(folder);
    const folderPath = getFolderPath(folder);
    const fullPath = path.startsWith(folderPath) ? path : `${folderPath}/${path}`;

    await Filesystem.stat({
      path: fullPath,
      directory,
    });

    return true;
  } catch {
    return false;
  }
}

/**
 * Copy a file
 */
async function copyFile(
  fromPath: string,
  toPath: string,
  fromFolder: SpecialFolder = 'DOCUMENTS',
  toFolder: SpecialFolder = 'DOCUMENTS'
): Promise<void> {
  try {
    const fromDirectory = getDirectoryForFolder(fromFolder);
    const toDirectory = getDirectoryForFolder(toFolder);
    const fromFolderPath = getFolderPath(fromFolder);
    const toFolderPath = getFolderPath(toFolder);
    
    const fullFromPath = fromPath.startsWith(fromFolderPath) ? fromPath : `${fromFolderPath}/${fromPath}`;
    const fullToPath = toPath.startsWith(toFolderPath) ? toPath : `${toFolderPath}/${toPath}`;

    await Filesystem.copy({
      from: fullFromPath,
      to: fullToPath,
      directory: fromDirectory,
      toDirectory,
    });
  } catch (error) {
    console.error(`Error copying file from ${fromPath} to ${toPath}:`, error);
    throw error;
  }
}

/**
 * Rename/move a file
 */
async function renameFile(
  fromPath: string,
  toPath: string,
  folder: SpecialFolder = 'DOCUMENTS',
  toFolder?: SpecialFolder
): Promise<void> {
  try {
    const directory = getDirectoryForFolder(folder);
    const toDirectory = toFolder ? getDirectoryForFolder(toFolder) : directory;
    const folderPath = getFolderPath(folder);
    const toFolderPath = toFolder ? getFolderPath(toFolder) : folderPath;
    
    const fullFromPath = fromPath.startsWith(folderPath) ? fromPath : `${folderPath}/${fromPath}`;
    const fullToPath = toPath.startsWith(toFolderPath) ? toPath : `${toFolderPath}/${toPath}`;

    await Filesystem.rename({
      from: fullFromPath,
      to: fullToPath,
      directory,
      toDirectory,
    });
  } catch (error) {
    console.error(`Error renaming file from ${fromPath} to ${toPath}:`, error);
    throw error;
  }
}

/**
 * Get file info/stat
 */
async function getFileInfo(
  path: string,
  folder: SpecialFolder = 'DOCUMENTS'
): Promise<FileMetadata | null> {
  try {
    const directory = getDirectoryForFolder(folder);
    const folderPath = getFolderPath(folder);
    const fullPath = path.startsWith(folderPath) ? path : `${folderPath}/${path}`;

    const statResult = await Filesystem.stat({
      path: fullPath,
      directory,
    });

    const name = path.split('/').pop() || path;

    return {
      name,
      path: fullPath,
      size: statResult.size || 0,
      type: getFileType(name),
      lastModified: statResult.mtime || Date.now(),
      uri: statResult.uri,
      isDirectory: statResult.type === 'directory',
    };
  } catch (error) {
    console.error(`Error getting file info for ${path}:`, error);
    return null;
  }
}

/**
 * Get free disk space
 */
async function getFreeSpace(): Promise<number> {
  try {
    await Filesystem.getUri({
      path: '',
      directory: Directory.Data,
    });
    
    // Capacitor doesn't provide direct disk space API
    // This would need a custom plugin for accurate space calculation
    // Returning a placeholder that indicates "unknown"
    return -1;
  } catch (error) {
    console.error('Error getting free space:', error);
    return -1;
  }
}

/**
 * Take a photo using the camera
 */
async function takePhoto(): Promise<FileMetadata | null> {
  try {
    const photo = await Camera.getPhoto({
      resultType: CameraResultType.Uri,
      source: CameraSource.Camera,
      quality: 90,
      allowEditing: false,
      saveToGallery: true,
    });

    if (photo.path || photo.webPath) {
      const fileName = `camera_${Date.now()}.jpg`;
      return {
        name: fileName,
        path: photo.path || photo.webPath || '',
        size: 0, // Would need to stat the file
        type: 'image/jpeg',
        lastModified: Date.now(),
        uri: photo.webPath || photo.path,
        isDirectory: false,
      };
    }

    return null;
  } catch (error) {
    console.error('Error taking photo:', error);
    return null;
  }
}

/**
 * Pick photos from the gallery
 */
async function pickPhotos(limit: number = 10): Promise<FileMetadata[]> {
  try {
    const photos = await Camera.pickImages({
      quality: 90,
      limit,
    });

    return photos.photos.map((photo, index) => ({
      name: `gallery_${Date.now()}_${index}.jpg`,
      path: photo.path || '',
      size: 0,
      type: 'image/jpeg',
      lastModified: Date.now(),
      uri: photo.webPath || photo.path,
      isDirectory: false,
    }));
  } catch (error) {
    console.error('Error picking photos:', error);
    return [];
  }
}

/**
 * Helper function to determine file type from extension
 */
function getFileType(filename: string): string {
  const extension = filename.split('.').pop()?.toLowerCase() || '';
  
  const mimeTypes: Record<string, string> = {
    // Images
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    png: 'image/png',
    gif: 'image/gif',
    webp: 'image/webp',
    bmp: 'image/bmp',
    svg: 'image/svg+xml',
    // Documents
    pdf: 'application/pdf',
    doc: 'application/msword',
    docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    xls: 'application/vnd.ms-excel',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    ppt: 'application/vnd.ms-powerpoint',
    pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    txt: 'text/plain',
    csv: 'text/csv',
    json: 'application/json',
    xml: 'application/xml',
    html: 'text/html',
    md: 'text/markdown',
    // Audio
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
    ogg: 'audio/ogg',
    m4a: 'audio/mp4',
    flac: 'audio/flac',
    // Video
    mp4: 'video/mp4',
    mov: 'video/quicktime',
    avi: 'video/x-msvideo',
    mkv: 'video/x-matroska',
    webm: 'video/webm',
    // Archives
    zip: 'application/zip',
    rar: 'application/x-rar-compressed',
    '7z': 'application/x-7z-compressed',
    tar: 'application/x-tar',
    gz: 'application/gzip',
  };

  return mimeTypes[extension] || 'application/octet-stream';
}

/**
 * Get file extension from MIME type
 */
function getExtensionFromMimeType(mimeType: string): string {
  const extensions: Record<string, string> = {
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/gif': '.gif',
    'image/webp': '.webp',
    'application/pdf': '.pdf',
    'text/plain': '.txt',
    'text/csv': '.csv',
    'application/json': '.json',
    'text/html': '.html',
    'audio/mpeg': '.mp3',
    'video/mp4': '.mp4',
  };

  return extensions[mimeType] || '';
}

/**
 * Format file size for display
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${units[i]}`;
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleString();
}

// Export the file system API
export const fileSystem = {
  // Platform info
  isNativePlatform,
  getPlatform,
  
  // Permissions
  requestPermissions,
  checkPermissions,
  
  // File operations
  listFiles,
  readFile,
  readFileAsBase64,
  writeFile,
  deleteFile,
  createDirectory,
  deleteDirectory,
  fileExists,
  copyFile,
  renameFile,
  getFileInfo,
  getFreeSpace,
  
  // Camera/Gallery
  takePhoto,
  pickPhotos,
  
  // Utilities
  getFileType,
  getExtensionFromMimeType,
  formatFileSize,
  formatTimestamp,
  
  // Constants
  Directory,
  Encoding,
};

export default fileSystem;
