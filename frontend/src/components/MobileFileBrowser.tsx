/**
 * MobileFileBrowser Component
 * 
 * A native mobile-optimized file browser that provides access to
 * device storage (Downloads, Documents, Camera, etc.) with a
 * touch-friendly interface.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { 
  Folder, 
  File, 
  Image, 
  Music, 
  Video, 
  FileText, 
  ChevronLeft,
  ChevronRight,
  Check,
  X,
  Camera,
  Grid,
  List,
  Search,
  MoreVertical,
  Upload,
  Trash2,
  RefreshCw,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';
import { fileSystem, type SpecialFolder, type FileMetadata } from '@/mobile/fileSystem';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// View mode type
type ViewMode = 'grid' | 'list';

// Sort option type
type SortOption = 'name' | 'date' | 'size' | 'type';

// Props interface
export interface MobileFileBrowserProps {
  /** Initial folder to display */
  initialFolder?: SpecialFolder;
  /** Initial sub-path within the folder */
  initialPath?: string;
  /** Callback when a file is selected */
  onFileSelect?: (files: FileMetadata[]) => void;
  /** Callback when navigating to a folder */
  onFolderSelect?: (folder: SpecialFolder, path: string) => void;
  /** Allow multiple file selection */
  allowMultiSelect?: boolean;
  /** Filter by file extensions (e.g., ['.pdf', '.jpg']) */
  filterTypes?: string[];
  /** Show hidden files */
  showHidden?: boolean;
  /** Enable camera capture */
  enableCamera?: boolean;
  /** Custom class name */
  className?: string;
  /** Show upload button */
  showUpload?: boolean;
  /** Upload handler */
  onUpload?: (files: FileMetadata[]) => Promise<void>;
}

// Breadcrumb item
interface Breadcrumb {
  name: string;
  folder: SpecialFolder;
  path: string;
}

export const MobileFileBrowser: React.FC<MobileFileBrowserProps> = ({
  initialFolder = 'DOWNLOADS',
  initialPath = '',
  onFileSelect,
  onFolderSelect,
  allowMultiSelect = false,
  filterTypes,
  showHidden = false,
  enableCamera = true,
  className,
  showUpload = false,
  onUpload,
}) => {
  // State
  const [currentFolder, setCurrentFolder] = useState<SpecialFolder>(initialFolder);
  const [currentPath, setCurrentPath] = useState<string>(initialPath);
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [sortBy, setSortBy] = useState<SortOption>('name');
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);
  const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([]);
  const [deleteConfirmFile, setDeleteConfirmFile] = useState<FileMetadata | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [_permissionGranted, setPermissionGranted] = useState(false);

  // Folder display names
  const folderNames: Record<SpecialFolder, string> = {
    DOWNLOADS: 'Downloads',
    DOCUMENTS: 'Documents',
    PICTURES: 'Pictures',
    DCIM: 'Camera',
    AUDIO: 'Audio',
    CACHE: 'Cache',
    EXTERNAL: 'Files',
  };

  // Load files when folder or path changes
  useEffect(() => {
    loadFiles();
  }, [currentFolder, currentPath]);

  // Check permissions on mount
  useEffect(() => {
    checkPermissions();
  }, []);

  // Update breadcrumbs
  useEffect(() => {
    const crumbs: Breadcrumb[] = [{ name: folderNames[currentFolder], folder: currentFolder, path: '' }];
    
    if (currentPath) {
      const parts = currentPath.split('/').filter(Boolean);
      let accumulatedPath = '';
      
      for (const part of parts) {
        accumulatedPath += `${accumulatedPath ? '/' : ''}${part}`;
        crumbs.push({
          name: part,
          folder: currentFolder,
          path: accumulatedPath,
        });
      }
    }
    
    setBreadcrumbs(crumbs);
  }, [currentFolder, currentPath]);

  // Check file permissions
  const checkPermissions = async () => {
    try {
      const status = await fileSystem.requestPermissions();
      setPermissionGranted(status.read);
      
      if (!status.read) {
        setError('Storage permission is required to access files. Please enable it in settings.');
      }
    } catch (err) {
      setError('Failed to check permissions');
    }
  };

  // Load files from current folder
  const loadFiles = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const fileList = await fileSystem.listFiles(currentFolder, currentPath);
      setFiles(fileList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files');
      setFiles([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter and sort files
  const filteredFiles = useMemo(() => {
    let _result = [...files];
    
    // Filter hidden files
    if (!showHidden) {
      _result = _result.filter(f => !f.name.startsWith('.'));
    }
    
    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      _result = _result.filter(f => f.name.toLowerCase().includes(query));
    }
    
    // Filter by file types
    if (filterTypes && filterTypes.length > 0) {
      _result = _result.filter(f => {
        if (f.isDirectory) return true;
        const ext = `.${f.name.split('.').pop()?.toLowerCase()}`;
        return filterTypes.some(type => 
          type.toLowerCase() === ext || type.toLowerCase() === ext.slice(1)
        );
      });
    }
    
    // Sort
    _result.sort((a, b) => {
      // Directories always first
      if (a.isDirectory !== b.isDirectory) {
        return a.isDirectory ? -1 : 1;
      }
      
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'date':
          return b.lastModified - a.lastModified;
        case 'size':
          return b.size - a.size;
        case 'type':
          return a.type.localeCompare(b.type);
        default:
          return 0;
      }
    });
    
    return _result;
  }, [files, showHidden, searchQuery, filterTypes, sortBy]);

  // Handle file/folder click
  const handleItemClick = (file: FileMetadata) => {
    if (file.isDirectory) {
      const newPath = currentPath 
        ? `${currentPath}/${file.name}` 
        : file.name;
      setCurrentPath(newPath);
      onFolderSelect?.(currentFolder, newPath);
    } else {
      if (allowMultiSelect) {
        const newSelected = new Set(selectedFiles);
        if (newSelected.has(file.path)) {
          newSelected.delete(file.path);
        } else {
          newSelected.add(file.path);
        }
        setSelectedFiles(newSelected);
      } else {
        onFileSelect?.([file]);
      }
    }
  };

  // Handle breadcrumb navigation
  const handleBreadcrumbClick = (crumb: Breadcrumb, _index: number) => {
    setCurrentFolder(crumb.folder);
    setCurrentPath(crumb.path);
    setSelectedFiles(new Set());
  };

  // Navigate up
  const navigateUp = () => {
    if (!currentPath) {
      // Already at root, do nothing
      return;
    }
    
    const parts = currentPath.split('/').filter(Boolean);
    parts.pop();
    const newPath = parts.join('/');
    setCurrentPath(newPath);
    setSelectedFiles(new Set());
  };

  // Handle camera capture
  const handleCameraCapture = async () => {
    try {
      const photo = await fileSystem.takePhoto();
      if (photo) {
        toast.success('Photo captured successfully');
        if (allowMultiSelect) {
          setSelectedFiles(new Set([photo.path]));
        } else {
          onFileSelect?.([photo]);
        }
      }
    } catch (err) {
      toast.error('Failed to capture photo');
    }
  };

  // Handle file deletion
  const handleDelete = async () => {
    if (!deleteConfirmFile) return;
    
    try {
      if (deleteConfirmFile.isDirectory) {
        await fileSystem.deleteDirectory(deleteConfirmFile.path, currentFolder);
      } else {
        await fileSystem.deleteFile(deleteConfirmFile.path, currentFolder);
      }
      
      toast.success(`${deleteConfirmFile.name} deleted`);
      await loadFiles();
      setDeleteConfirmFile(null);
    } catch (err) {
      toast.error('Failed to delete file');
    }
  };

  // Handle upload
  const handleUpload = async () => {
    if (!onUpload || selectedFiles.size === 0) return;
    
    setIsUploading(true);
    try {
      const filesToUpload = files.filter(f => selectedFiles.has(f.path));
      await onUpload(filesToUpload);
      toast.success(`${filesToUpload.length} file(s) uploaded`);
      setSelectedFiles(new Set());
    } catch (err) {
      toast.error('Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  // Confirm selection
  const handleConfirmSelection = () => {
    const selected = files.filter(f => selectedFiles.has(f.path));
    onFileSelect?.(selected);
    setSelectedFiles(new Set());
  };

  // Get file icon based on type
  const getFileIcon = (file: FileMetadata) => {
    if (file.isDirectory) {
      return <Folder className="w-6 h-6 text-blue-500" />;
    }
    
    if (file.type.startsWith('image/')) {
      return <Image className="w-6 h-6 text-purple-500" />;
    }
    
    if (file.type.startsWith('audio/')) {
      return <Music className="w-6 h-6 text-green-500" />;
    }
    
    if (file.type.startsWith('video/')) {
      return <Video className="w-6 h-6 text-red-500" />;
    }
    
    if (file.type.includes('pdf') || file.type.includes('document') || file.type.includes('text')) {
      return <FileText className="w-6 h-6 text-orange-500" />;
    }
    
    return <File className="w-6 h-6 text-gray-500" />;
  };

  // Get file icon for grid view
  const getGridFileIcon = (file: FileMetadata) => {
    const iconClass = "w-12 h-12";
    
    if (file.isDirectory) {
      return <Folder className={`${iconClass} text-blue-500`} />;
    }
    
    if (file.type.startsWith('image/')) {
      return <Image className={`${iconClass} text-purple-500`} />;
    }
    
    if (file.type.startsWith('audio/')) {
      return <Music className={`${iconClass} text-green-500`} />;
    }
    
    if (file.type.startsWith('video/')) {
      return <Video className={`${iconClass} text-red-500`} />;
    }
    
    if (file.type.includes('pdf') || file.type.includes('document')) {
      return <FileText className={`${iconClass} text-orange-500`} />;
    }
    
    return <File className={`${iconClass} text-gray-500`} />;
  };

  // Render breadcrumb navigation
  const renderBreadcrumbs = () => (
    <div className="flex items-center gap-1 px-4 py-2 bg-muted/50 overflow-x-auto scrollbar-hide">
      {breadcrumbs.map((crumb, index) => (
        <React.Fragment key={index}>
          {index > 0 && (
            <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          )}
          <button
            onClick={() => handleBreadcrumbClick(crumb, index)}
            className={cn(
              "text-sm whitespace-nowrap hover:underline",
              index === breadcrumbs.length - 1 
                ? "font-medium text-foreground" 
                : "text-muted-foreground"
            )}
          >
            {crumb.name}
          </button>
        </React.Fragment>
      ))}
    </div>
  );

  // Render toolbar
  const renderToolbar = () => (
    <div className="flex items-center justify-between px-4 py-2 border-b">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={navigateUp}
          disabled={!currentPath}
          className="h-11 w-11"
        >
          <ChevronLeft className="w-5 h-5" />
        </Button>
        
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setShowSearch(!showSearch)}
          className={cn("h-11 w-11", showSearch && "bg-accent")}
        >
          <Search className="w-5 h-5" />
        </Button>
        
        {enableCamera && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleCameraCapture}
            className="h-11 w-11"
          >
            <Camera className="w-5 h-5" />
          </Button>
        )}
        
        <Button
          variant="ghost"
          size="icon"
          onClick={loadFiles}
          disabled={isLoading}
          className="h-11 w-11"
        >
          <RefreshCw className={cn("w-5 h-5", isLoading && "animate-spin")} />
        </Button>
      </div>
      
      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-11 px-3">
              Sort: {sortBy}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setSortBy('name')}>Name</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSortBy('date')}>Date</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSortBy('size')}>Size</DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSortBy('type')}>Type</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        
        <div className="flex items-center border rounded-md">
          <Button
            variant={viewMode === 'grid' ? 'secondary' : 'ghost'}
            size="icon"
            onClick={() => setViewMode('grid')}
            className="h-11 w-11 rounded-none rounded-l-md"
          >
            <Grid className="w-5 h-5" />
          </Button>
          <Button
            variant={viewMode === 'list' ? 'secondary' : 'ghost'}
            size="icon"
            onClick={() => setViewMode('list')}
            className="h-11 w-11 rounded-none rounded-r-md"
          >
            <List className="w-5 h-5" />
          </Button>
        </div>
      </div>
    </div>
  );

  // Render search bar
  const renderSearchBar = () => {
    if (!showSearch) return null;
    
    return (
      <div className="px-4 py-2 border-b">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 pr-10 text-base"
            autoFocus
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2"
            >
              <X className="w-5 h-5 text-muted-foreground" />
            </button>
          )}
        </div>
      </div>
    );
  };

  // Render file list item
  const renderFileItem = (file: FileMetadata) => {
    const isSelected = selectedFiles.has(file.path);
    const fileSize = fileSystem.formatFileSize(file.size);
    const fileDate = fileSystem.formatTimestamp(file.lastModified);
    
    if (viewMode === 'grid') {
      return (
        <button
          key={file.path}
          onClick={() => handleItemClick(file)}
          className={cn(
            "flex flex-col items-center p-4 rounded-lg border transition-colors",
            isSelected 
              ? "border-primary bg-primary/5" 
              : "border-border hover:bg-accent"
          )}
        >
          <div className="mb-2">{getGridFileIcon(file)}</div>
          <span className="text-xs text-center truncate w-full" title={file.name}>
            {file.name}
          </span>
          {!file.isDirectory && (
            <span className="text-xs text-muted-foreground">{fileSize}</span>
          )}
          {isSelected && allowMultiSelect && (
            <div className="absolute top-2 right-2">
              <CheckCircle2 className="w-5 h-5 text-primary" />
            </div>
          )}
        </button>
      );
    }
    
    return (
      <button
        key={file.path}
        onClick={() => handleItemClick(file)}
        className={cn(
          "flex items-center gap-3 p-3 w-full text-left transition-colors",
          isSelected 
            ? "bg-primary/5" 
            : "hover:bg-accent"
        )}
      >
        <div className="flex-shrink-0">{getFileIcon(file)}</div>
        
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{file.name}</p>
          <p className="text-xs text-muted-foreground">
            {!file.isDirectory && (
              <>
                {fileSize} <span className="mx-1">•</span>
              </>
            )}
            {fileDate}
          </p>
        </div>
        
        {allowMultiSelect && (
          <div className={cn(
            "w-6 h-6 rounded border flex items-center justify-center flex-shrink-0",
            isSelected && "bg-primary border-primary"
          )}>
            {isSelected && <Check className="w-4 h-4 text-primary-foreground" />}
          </div>
        )}
        
        <DropdownMenu>
          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
            <Button variant="ghost" size="icon" className="h-11 w-11 flex-shrink-0">
              <MoreVertical className="w-5 h-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={(e) => {
              e.stopPropagation();
              onFileSelect?.([file]);
            }}>
              Select
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              onClick={(e) => {
                e.stopPropagation();
                setDeleteConfirmFile(file);
              }}
              className="text-destructive"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </button>
    );
  };

  // Render empty state
  const renderEmptyState = () => (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Folder className="w-16 h-16 text-muted-foreground/50 mb-4" />
      <p className="text-muted-foreground">
        {searchQuery 
          ? 'No files match your search' 
          : 'This folder is empty'}
      </p>
    </div>
  );

  // Render error state
  const renderErrorState = () => (
    <div className="flex flex-col items-center justify-center py-12 text-center px-4">
      <AlertCircle className="w-16 h-16 text-destructive/50 mb-4" />
      <p className="text-destructive mb-2">{error}</p>
      <Button onClick={checkPermissions} variant="outline">
        Grant Permissions
      </Button>
    </div>
  );

  // Render loading state
  const renderLoadingState = () => (
    <div className="flex items-center justify-center py-12">
      <RefreshCw className="w-8 h-8 animate-spin text-muted-foreground" />
    </div>
  );

  return (
    <div className={cn("flex flex-col h-full bg-background rounded-lg border", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h3 className="font-semibold">{folderNames[currentFolder]}</h3>
        
        {allowMultiSelect && selectedFiles.size > 0 && (
          <Badge variant="secondary">{selectedFiles.size} selected</Badge>
        )}
      </div>
      
      {/* Breadcrumbs */}
      {renderBreadcrumbs()}
      
      {/* Toolbar */}
      {renderToolbar()}
      
      {/* Search */}
      {renderSearchBar()}
      
      {/* File List */}
      <ScrollArea className="flex-1">
        {error ? (
          renderErrorState()
        ) : isLoading ? (
          renderLoadingState()
        ) : filteredFiles.length === 0 ? (
          renderEmptyState()
        ) : (
          <div className={cn(
            viewMode === 'grid' 
              ? "grid grid-cols-3 sm:grid-cols-4 gap-2 p-4" 
              : "divide-y"
          )}>
            {filteredFiles.map(renderFileItem)}
          </div>
        )}
      </ScrollArea>
      
      {/* Footer Actions */}
      {(allowMultiSelect && selectedFiles.size > 0) || showUpload ? (
        <div className="flex items-center justify-between px-4 py-3 border-t gap-2">
          <div className="text-sm text-muted-foreground">
            {selectedFiles.size} file{selectedFiles.size !== 1 ? 's' : ''} selected
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedFiles(new Set())}
            >
              Clear
            </Button>
            
            {showUpload && (
              <Button
                size="sm"
                onClick={handleUpload}
                disabled={isUploading || selectedFiles.size === 0}
                className="gap-2"
              >
                <Upload className="w-4 h-4" />
                {isUploading ? 'Uploading...' : 'Upload'}
              </Button>
            )}
            
            {onFileSelect && (
              <Button
                size="sm"
                onClick={handleConfirmSelection}
                disabled={selectedFiles.size === 0}
              >
                Select
              </Button>
            )}
          </div>
        </div>
      ) : null}
      
      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteConfirmFile} onOpenChange={() => setDeleteConfirmFile(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {deleteConfirmFile?.isDirectory ? 'Folder' : 'File'}?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{deleteConfirmFile?.name}"? 
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default MobileFileBrowser;
