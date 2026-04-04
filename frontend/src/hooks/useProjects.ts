import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

// File System Access API type declarations - using type aliases to avoid conflicts
type FileSystemDirectoryHandle = {
  kind: 'directory';
  name: string;
  entries(): AsyncIterableIterator<[string, FileSystemHandle]>;
  requestPermission(descriptor?: { mode: 'read' | 'readwrite' }): Promise<PermissionState>;
};

type FileSystemFileHandle = {
  kind: 'file';
  name: string;
  getFile(): Promise<File>;
};

type FileSystemHandle = FileSystemDirectoryHandle | FileSystemFileHandle;

// Extend Window interface
declare global {
  interface Window {
    showDirectoryPicker?: () => Promise<FileSystemDirectoryHandle>;
  }
  
  interface HTMLInputElement {
    webkitdirectory: boolean;
    directory: string;
  }
}

// Match the existing Project type EXACTLY
export interface Project {
  id: string;
  name: string;
  file_count: number;
  status: string;
}

// DriveFile type matching ProjectSidebar expectations
export interface DriveFile {
  id: string;
  name: string;
  mime_type: string;
  is_folder: boolean;
  modified_time?: string;
}

// IndexingStatus type matching ProjectSidebar expectations
export interface IndexingStatus {
  projects: Array<{
    project_id: string;
    name: string;
    status: string;
    progress: { indexed: number; total: number };
    indexed: number;
    total: number;
    percent: number;
  }>;
  summary: {
    total_projects: number;
    total_indexed: number;
    total_files: number;
    overall_percent: number;
    zvec_ready: boolean;
    zvec_count: number;
  };
}

// Scan results type matching expectations
export interface ScanResults {
  detected: number;
  queued: number;
  zvecReady: boolean;
}

// Extended project with local file metadata
export interface LocalProject extends Project {
  handle?: FileSystemDirectoryHandle | null;
  files: LocalFileInfo[];
  createdAt: number;
  updatedAt: number;
}

export interface LocalFileInfo {
  id: string;
  name: string;
  path: string;
  size: number;
  type: string;
  lastModified: number;
  content?: ArrayBuffer | string;
  handle?: FileSystemFileHandle;
}

// IndexedDB configuration
const DB_NAME = 'CerebrumLocalDrive';
const DB_VERSION = 1;
const PROJECTS_STORE = 'projects';
const FILES_STORE = 'files';

// Check if File System Access API is supported
const isFileSystemAccessSupported = (): boolean => {
  return typeof window !== 'undefined' && 
         'showDirectoryPicker' in window &&
         'FileSystemDirectoryHandle' in window;
};

// Check if running on mobile
const isMobileDevice = (): boolean => {
  if (typeof window === 'undefined') return false;
  const userAgent = navigator.userAgent.toLowerCase();
  return /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini|mobile/.test(userAgent);
};

// Initialize IndexedDB
const initDB = (): Promise<IDBDatabase> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      // Projects store
      if (!db.objectStoreNames.contains(PROJECTS_STORE)) {
        const projectStore = db.createObjectStore(PROJECTS_STORE, { keyPath: 'id' });
        projectStore.createIndex('name', 'name', { unique: false });
        projectStore.createIndex('status', 'status', { unique: false });
      }
      
      // Files store
      if (!db.objectStoreNames.contains(FILES_STORE)) {
        const fileStore = db.createObjectStore(FILES_STORE, { keyPath: 'id' });
        fileStore.createIndex('projectId', 'projectId', { unique: false });
      }
    };
  });
};

// Save project to IndexedDB
const saveProjectToDB = async (project: LocalProject): Promise<void> => {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([PROJECTS_STORE, FILES_STORE], 'readwrite');
    const projectStore = transaction.objectStore(PROJECTS_STORE);
    const fileStore = transaction.objectStore(FILES_STORE);
    
    // Save project metadata (without handle - can't serialize FileSystemHandle)
    const projectData = {
      ...project,
      handle: null,
    };
    projectStore.put(projectData);
    
    // Save files metadata
    project.files.forEach(file => {
      const fileData = {
        ...file,
        projectId: project.id,
        handle: null,
      };
      fileStore.put(fileData);
    });
    
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

// Get all projects from IndexedDB
const getProjectsFromDB = async (): Promise<LocalProject[]> => {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([PROJECTS_STORE, FILES_STORE], 'readonly');
    const projectStore = transaction.objectStore(PROJECTS_STORE);
    const fileStore = transaction.objectStore(FILES_STORE);
    
    const projects: LocalProject[] = [];
    
    const projectRequest = projectStore.getAll();
    projectRequest.onsuccess = () => {
      const projectData = projectRequest.result;
      
      const fileRequest = fileStore.getAll();
      fileRequest.onsuccess = () => {
        const allFiles = fileRequest.result;
        
        projectData.forEach((p: LocalProject & { projectId?: string }) => {
          const projectFiles = allFiles.filter((f: LocalFileInfo & { projectId: string }) => f.projectId === p.id);
          projects.push({
            ...p,
            files: projectFiles,
            file_count: projectFiles.length,
          });
        });
        
        resolve(projects);
      };
      fileRequest.onerror = () => reject(fileRequest.error);
    };
    projectRequest.onerror = () => reject(projectRequest.error);
  });
};

// Delete project from IndexedDB
const deleteProjectFromDB = async (projectId: string): Promise<void> => {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([PROJECTS_STORE, FILES_STORE], 'readwrite');
    const projectStore = transaction.objectStore(PROJECTS_STORE);
    const fileStore = transaction.objectStore(FILES_STORE);
    
    projectStore.delete(projectId);
    
    const fileIndex = fileStore.index('projectId');
    const fileRequest = fileIndex.getAll(projectId);
    fileRequest.onsuccess = () => {
      fileRequest.result.forEach((file: { id: string }) => {
        fileStore.delete(file.id);
      });
    };
    
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

// Save file content to IndexedDB
const saveFileContent = async (fileId: string, content: ArrayBuffer | string): Promise<void> => {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([FILES_STORE], 'readwrite');
    const fileStore = transaction.objectStore(FILES_STORE);
    
    const request = fileStore.get(fileId);
    request.onsuccess = () => {
      const fileData = request.result;
      if (fileData) {
        fileData.content = content;
        fileStore.put(fileData);
      }
    };
    
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

// Get file content from IndexedDB
const getFileContent = async (fileId: string): Promise<ArrayBuffer | string | undefined> => {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction([FILES_STORE], 'readonly');
    const fileStore = transaction.objectStore(FILES_STORE);
    
    const request = fileStore.get(fileId);
    request.onsuccess = () => {
      const fileData = request.result;
      resolve(fileData?.content);
    };
    request.onerror = () => reject(request.error);
  });
};

// Scan directory recursively using File System Access API
const scanDirectory = async (
  dirHandle: FileSystemDirectoryHandle,
  path = ''
): Promise<LocalFileInfo[]> => {
  const files: LocalFileInfo[] = [];
  
  for await (const [name, handle] of dirHandle.entries()) {
    const currentPath = path ? `${path}/${name}` : name;
    
    if (handle.kind === 'directory') {
      const subFiles = await scanDirectory(handle as FileSystemDirectoryHandle, currentPath);
      files.push(...subFiles);
    } else {
      const fileHandle = handle as FileSystemFileHandle;
      const file = await fileHandle.getFile();
      
      files.push({
        id: uuidv4(),
        name: file.name,
        path: currentPath,
        size: file.size,
        type: file.type || getFileTypeFromName(file.name),
        lastModified: file.lastModified,
        handle: fileHandle,
      });
    }
  }
  
  return files;
};

// Get file type from extension
const getFileTypeFromName = (filename: string): string => {
  const extension = filename.split('.').pop()?.toLowerCase() || '';
  
  const mimeTypes: Record<string, string> = {
    jpg: 'image/jpeg',
    jpeg: 'image/jpeg',
    png: 'image/png',
    gif: 'image/gif',
    webp: 'image/webp',
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
    mp3: 'audio/mpeg',
    wav: 'audio/wav',
    ogg: 'audio/ogg',
    m4a: 'audio/mp4',
    mp4: 'video/mp4',
    mov: 'video/quicktime',
    avi: 'video/x-msvideo',
    mkv: 'video/x-matroska',
    webm: 'video/webm',
    zip: 'application/zip',
    rar: 'application/x-rar-compressed',
    '7z': 'application/x-7z-compressed',
    dwg: 'application/acad',
    dxf: 'application/dxf',
    ifc: 'application/x-step',
    xer: 'application/octet-stream',
  };
  
  return mimeTypes[extension] || 'application/octet-stream';
};

// Process files from file input (fallback for mobile)
const processFileList = async (fileList: FileList): Promise<LocalFileInfo[]> => {
  const files: LocalFileInfo[] = [];
  
  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i];
    const arrayBuffer = await file.arrayBuffer();
    
    files.push({
      id: uuidv4(),
      name: file.name,
      path: file.name,
      size: file.size,
      type: file.type || getFileTypeFromName(file.name),
      lastModified: file.lastModified,
      content: arrayBuffer,
    });
  }
  
  return files;
};

// Format bytes to human-readable
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

// Convert LocalFileInfo to DriveFile
const toDriveFile = (file: LocalFileInfo): DriveFile => ({
  id: file.id,
  name: file.name,
  mime_type: file.type,
  is_folder: false,
  modified_time: new Date(file.lastModified).toISOString(),
});

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [localProjects, setLocalProjects] = useState<LocalProject[]>([]);
  const [loading, setLoading] = useState(false);
  const [backendAvailable, setBackendAvailable] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [indexingStatus, setIndexingStatus] = useState<IndexingStatus | null>(null);
  const [scanResults, setScanResults] = useState<ScanResults | null>(null);
  
  // Load projects from IndexedDB on mount
  useEffect(() => {
    loadLocalProjects();
  }, []);
  
  const loadLocalProjects = async () => {
    try {
      const projects = await getProjectsFromDB();
      setLocalProjects(projects);
      
      const simpleProjects: Project[] = projects.map(p => ({
        id: p.id,
        name: p.name,
        file_count: p.files.length,
        status: p.status,
      }));
      setProjects(simpleProjects);
      
      if (projects.length > 0) {
        setIsConnected(true);
      }
    } catch (error) {
      console.error('Error loading local projects:', error);
    }
  };
  
  const refreshProjects = useCallback(async () => {
    setLoading(true);
    try {
      await loadLocalProjects();
      setBackendAvailable(true);
    } catch (error) {
      console.error('Error:', error);
      setBackendAvailable(false);
    } finally {
      setLoading(false);
    }
  }, []);
  
  // Build indexing status from local projects
  const buildIndexingStatus = (projects: LocalProject[]): IndexingStatus => {
    const totalFiles = projects.reduce((acc, p) => acc + p.files.length, 0);
    return {
      projects: projects.map(p => ({
        project_id: p.id,
        name: p.name,
        status: p.status,
        progress: { indexed: p.files.length, total: p.files.length },
        indexed: p.files.length,
        total: p.files.length,
        percent: 100,
      })),
      summary: {
        total_projects: projects.length,
        total_indexed: totalFiles,
        total_files: totalFiles,
        overall_percent: 100,
        zvec_ready: true,
        zvec_count: totalFiles,
      },
    };
  };
  
  // Connect to local drive using File System Access API or file input fallback
  const connectDrive = async (): Promise<boolean> => {
    setConnectionError(null);
    setScanning(true);
    setIndexingStatus(null);
    
    try {
      if (isFileSystemAccessSupported() && !isMobileDevice()) {
        if (!window.showDirectoryPicker) {
          throw new Error('File System Access API not available');
        }
        const dirHandle = await window.showDirectoryPicker();
        
        const permission = await dirHandle.requestPermission({ mode: 'read' });
        
        if (permission !== 'granted') {
          throw new Error('Permission denied to access directory');
        }
        
        const files = await scanDirectory(dirHandle);
        
        const project: LocalProject = {
          id: uuidv4(),
          name: dirHandle.name,
          file_count: files.length,
          status: 'active',
          handle: dirHandle,
          files: files,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        
        await saveProjectToDB(project);
        
        const updatedProjects = [...localProjects, project];
        setLocalProjects(updatedProjects);
        setProjects(prev => [...prev, {
          id: project.id,
          name: project.name,
          file_count: project.files.length,
          status: project.status,
        }]);
        
        setScanResults({ detected: files.length, queued: files.length, zvecReady: true });
        setIndexingStatus(buildIndexingStatus(updatedProjects));
        setIsConnected(true);
        
        return true;
      } else {
        return new Promise((resolve) => {
          const input = document.createElement('input');
          input.type = 'file';
          input.webkitdirectory = true;
          input.directory = '';
          input.multiple = true;
          
          input.onchange = async (e) => {
            const files = (e.target as HTMLInputElement).files;
            if (!files || files.length === 0) {
              setScanning(false);
              resolve(false);
              return;
            }
            
            try {
              const localFiles = await processFileList(files);
              
              const project: LocalProject = {
                id: uuidv4(),
                name: 'Local Files',
                file_count: localFiles.length,
                status: 'active',
                handle: null,
                files: localFiles,
                createdAt: Date.now(),
                updatedAt: Date.now(),
              };
              
              for (let i = 0; i < localFiles.length; i++) {
                const file = localFiles[i];
                if (file.content) {
                  await saveFileContent(file.id, file.content);
                }
              }
              
              await saveProjectToDB(project);
              
              const updatedProjects = [...localProjects, project];
              setLocalProjects(updatedProjects);
              setProjects(prev => [...prev, {
                id: project.id,
                name: project.name,
                file_count: project.files.length,
                status: project.status,
              }]);
              
              setScanResults({ detected: localFiles.length, queued: localFiles.length, zvecReady: true });
              setIndexingStatus(buildIndexingStatus(updatedProjects));
              setIsConnected(true);
              resolve(true);
            } catch (error) {
              console.error('Error processing files:', error);
              setConnectionError(error instanceof Error ? error.message : 'Failed to process files');
              resolve(false);
            } finally {
              setScanning(false);
            }
          };
          
          input.oncancel = () => {
            setScanning(false);
            resolve(false);
          };
          
          input.click();
        });
      }
    } catch (error) {
      console.error('Error connecting drive:', error);
      setConnectionError(error instanceof Error ? error.message : 'Failed to connect drive');
      setIsConnected(false);
      return false;
    } finally {
      setScanning(false);
    }
  };
  
  // Connect using multiple file selection (alternative for mobile)
  const connectWithFileInput = async (): Promise<boolean> => {
    setConnectionError(null);
    setScanning(true);
    
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.multiple = true;
      input.accept = '*/*';
      
      input.onchange = async (e) => {
        const files = (e.target as HTMLInputElement).files;
        if (!files || files.length === 0) {
          setScanning(false);
          resolve(false);
          return;
        }
        
        try {
          const localFiles = await processFileList(files);
          
          const project: LocalProject = {
            id: uuidv4(),
            name: `Files - ${new Date().toLocaleDateString()}`,
            file_count: localFiles.length,
            status: 'active',
            handle: null,
            files: localFiles,
            createdAt: Date.now(),
            updatedAt: Date.now(),
          };
          
          for (const file of localFiles) {
            if (file.content) {
              await saveFileContent(file.id, file.content);
            }
          }
          
          await saveProjectToDB(project);
          
          const updatedProjects = [...localProjects, project];
          setLocalProjects(updatedProjects);
          setProjects(prev => [...prev, {
            id: project.id,
            name: project.name,
            file_count: project.files.length,
            status: project.status,
          }]);
          
          setScanResults({ detected: localFiles.length, queued: localFiles.length, zvecReady: true });
          setIndexingStatus(buildIndexingStatus(updatedProjects));
          setIsConnected(true);
          resolve(true);
        } catch (error) {
          console.error('Error processing files:', error);
          setConnectionError(error instanceof Error ? error.message : 'Failed to process files');
          resolve(false);
        } finally {
          setScanning(false);
        }
      };
      
      input.oncancel = () => {
        setScanning(false);
        resolve(false);
      };
      
      input.click();
    });
  };
  
  // Disconnect drive - clear local projects
  const disconnectDrive = async (): Promise<void> => {
    try {
      for (const project of localProjects) {
        await deleteProjectFromDB(project.id);
      }
      
      setLocalProjects([]);
      setProjects([]);
      setIsConnected(false);
      setScanResults(null);
      setIndexingStatus(null);
    } catch (error) {
      console.error('Error disconnecting drive:', error);
    }
  };
  
  // Scan drive for new files
  const scanDrive = async (): Promise<void> => {
    setScanning(true);
    
    try {
      for (const project of localProjects) {
        if (project.handle) {
          const newFiles = await scanDirectory(project.handle);
          
          const existingPaths = new Set(project.files.map(f => f.path));
          const addedFiles = newFiles.filter(f => !existingPaths.has(f.path));
          
          if (addedFiles.length > 0) {
            const updatedProject = {
              ...project,
              files: [...project.files, ...addedFiles],
              file_count: project.files.length + addedFiles.length,
              updatedAt: Date.now(),
            };
            
            await saveProjectToDB(updatedProject);
            
            setLocalProjects(prev => 
              prev.map(p => p.id === updatedProject.id ? updatedProject : p)
            );
            setProjects(prev =>
              prev.map(p => p.id === updatedProject.id ? {
                ...p,
                file_count: updatedProject.files.length,
              } : p)
            );
          }
          
          setScanResults({ detected: newFiles.length, queued: addedFiles.length, zvecReady: true });
        }
      }
      
      setIndexingStatus(buildIndexingStatus(localProjects));
    } catch (error) {
      console.error('Error scanning drive:', error);
    } finally {
      setScanning(false);
    }
  };
  
  // Get files for a project - returns DriveFile[] for compatibility
  const getProjectFiles = async (projectId: string): Promise<DriveFile[]> => {
    const project = localProjects.find(p => p.id === projectId);
    if (!project) return [];
    
    const files: DriveFile[] = [];
    
    for (const file of project.files) {
      if (file.handle) {
        try {
          const fileData = await file.handle.getFile();
          files.push({
            id: file.id,
            name: file.name,
            mime_type: file.type,
            is_folder: false,
            modified_time: new Date(fileData.lastModified).toISOString(),
          });
        } catch {
          files.push(toDriveFile(file));
        }
      } else {
        files.push(toDriveFile(file));
      }
    }
    
    return files;
  };
  
  // Get file content
  const getFile = async (fileId: string): Promise<LocalFileInfo | null> => {
    for (const project of localProjects) {
      const file = project.files.find(f => f.id === fileId);
      if (file) {
        if (file.handle) {
          try {
            const fileData = await file.handle.getFile();
            const arrayBuffer = await fileData.arrayBuffer();
            return {
              ...file,
              size: fileData.size,
              lastModified: fileData.lastModified,
              content: arrayBuffer,
            };
          } catch (error) {
            console.error('Error reading file:', error);
            return file;
          }
        } else {
          const content = await getFileContent(file.id);
          return {
            ...file,
            content,
          };
        }
      }
    }
    return null;
  };
  
  // Delete a project
  const deleteProject = async (projectId: string): Promise<void> => {
    try {
      await deleteProjectFromDB(projectId);
      
      const updatedProjects = localProjects.filter(p => p.id !== projectId);
      setLocalProjects(updatedProjects);
      setProjects(prev => prev.filter(p => p.id !== projectId));
      
      if (updatedProjects.length === 0) {
        setIsConnected(false);
        setScanResults(null);
        setIndexingStatus(null);
      } else {
        setIndexingStatus(buildIndexingStatus(updatedProjects));
      }
    } catch (error) {
      console.error('Error deleting project:', error);
    }
  };
  
  // Get connection status
  const getConnectionStatus = (): {
    isConnected: boolean;
    isFileSystemAccessSupported: boolean;
    isMobile: boolean;
    projectCount: number;
    totalFiles: number;
  } => {
    return {
      isConnected,
      isFileSystemAccessSupported: isFileSystemAccessSupported(),
      isMobile: isMobileDevice(),
      projectCount: localProjects.length,
      totalFiles: localProjects.reduce((acc, p) => acc + p.files.length, 0),
    };
  };

  useEffect(() => {
    refreshProjects();
  }, [refreshProjects]);

  return {
    projects,
    localProjects,
    loading,
    backendAvailable,
    refreshProjects,
    getProjectFiles,
    scanning,
    connectionError,
    indexingStatus,
    scanResults,
    isConnected,
    connectDrive,
    connectWithFileInput,
    disconnectDrive,
    scanDrive,
    getFile,
    deleteProject,
    getConnectionStatus,
    formatFileSize,
  };
}

export default useProjects;
