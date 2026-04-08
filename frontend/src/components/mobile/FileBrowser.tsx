import { useState, useEffect, useCallback } from 'react';
import { 
  Folder, 
  File, 
  Image, 
  FileText, 
  Music, 
  Video, 
  ChevronLeft,
  MoreVertical,
  RefreshCw,
  CloudUpload,
  Trash2,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMobileFileSystem } from '@/hooks/useMobileFileSystem';
import { offlineQueue, type QueueStats } from '@/mobile/offlineQueue';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { formatFileSize } from '@/lib/utils';

interface FileBrowserProps {
  onFileSelect?: (path: string, name: string) => void;
  onUpload?: (files: string[]) => void;
  allowMultiSelect?: boolean;
  showUploadQueue?: boolean;
}

interface FileItem {
  name: string;
  path: string;
  isDirectory: boolean;
  size: number;
  modified?: string;
  mimeType?: string;
}

export function FileBrowser({ 
  onFileSelect, 
  onUpload,
  allowMultiSelect = false,
  showUploadQueue = true 
}: FileBrowserProps) {
  const { 
    currentPath, 
    entries, 
    isLoading, 
    error,
    navigateTo,
    navigateUp,
    refresh,
    deleteItem,
    freeSpace,
    totalSpace 
  } = useMobileFileSystem();

  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [queueStats, setQueueStats] = useState<QueueStats | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');

  // Poll queue stats
  useEffect(() => {
    if (!showUploadQueue) return;
    
    const updateStats = async () => {
      const stats = await offlineQueue.getStats();
      setQueueStats(stats);
    };

    updateStats();
    const interval = setInterval(updateStats, 5000);
    return () => clearInterval(interval);
  }, [showUploadQueue]);

  const toggleSelection = useCallback((path: string) => {
    setSelectedFiles(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        if (!allowMultiSelect) next.clear();
        next.add(path);
      }
      return next;
    });
  }, [allowMultiSelect]);

  const handleUploadSelected = useCallback(async () => {
    const files = entries.filter(e => selectedFiles.has(e.path) && !e.isDirectory);
    
    for (const file of files) {
      await offlineQueue.enqueue({
        filePath: file.path,
        fileName: file.name,
        mimeType: file.mimeType || 'application/octet-stream',
        targetEndpoint: '/api/v1/documents/upload/chat',
        metadata: { source: 'mobile_file_browser' },
        priority: 'normal',
      });
    }

    setSelectedFiles(new Set());
    onUpload?.(Array.from(selectedFiles));
  }, [entries, selectedFiles, onUpload]);

  const getFileIcon = (item: FileItem) => {
    if (item.isDirectory) return <Folder className="w-5 h-5 text-blue-500" />;
    if (item.mimeType?.startsWith('image/')) return <Image className="w-5 h-5 text-green-500" />;
    if (item.mimeType?.startsWith('video/')) return <Video className="w-5 h-5 text-red-500" />;
    if (item.mimeType?.startsWith('audio/')) return <Music className="w-5 h-5 text-purple-500" />;
    if (item.mimeType?.includes('pdf') || item.mimeType?.includes('text')) {
      return <FileText className="w-5 h-5 text-orange-500" />;
    }
    return <File className="w-5 h-5 text-gray-500" />;
  };

  const usagePercent = totalSpace > 0 
    ? Math.round(((totalSpace - freeSpace) / totalSpace) * 100) 
    : 0;

  return (
    <div className="flex flex-col h-full bg-background rounded-lg border">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          {currentPath !== '/' && (
            <Button variant="ghost" size="icon" onClick={navigateUp}>
              <ChevronLeft className="w-5 h-5" />
            </Button>
          )}
          <span className="text-sm font-medium truncate max-w-[200px]">
            {currentPath === '/' ? 'Files' : currentPath.split('/').pop()}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {selectedFiles.size > 0 && (
            <Button 
              size="sm" 
              onClick={handleUploadSelected}
              className="gap-1"
            >
              <CloudUpload className="w-4 h-4" />
              Upload {selectedFiles.size}
            </Button>
          )}
          
          <Button variant="ghost" size="icon" onClick={refresh} disabled={isLoading}>
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => setViewMode('list')}>
                List View
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setViewMode('grid')}>
                Grid View
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Storage Bar */}
      {totalSpace > 0 && (
        <div className="px-3 py-2 border-b bg-muted/50">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-muted-foreground">Storage</span>
            <span className="text-muted-foreground">
              {formatFileSize(freeSpace)} free of {formatFileSize(totalSpace)}
            </span>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <motion.div 
              className={`h-full rounded-full ${
                usagePercent > 90 ? 'bg-red-500' : 
                usagePercent > 70 ? 'bg-yellow-500' : 'bg-green-500'
              }`}
              initial={{ width: 0 }}
              animate={{ width: `${usagePercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Upload Queue Status */}
      {showUploadQueue && queueStats && queueStats.total > 0 && (
        <div className="px-3 py-2 border-b bg-blue-50 dark:bg-blue-950/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              <CloudUpload className="w-4 h-4 text-blue-500" />
              <span>{queueStats.total} uploads queued</span>
              {queueStats.nextRetryIn && (
                <span className="text-xs text-muted-foreground">
                  (retry in {Math.ceil(queueStats.nextRetryIn / 1000)}s)
                </span>
              )}
            </div>
            {queueStats.failed > 0 && (
              <div className="flex items-center gap-1 text-xs text-red-500">
                <AlertCircle className="w-3 h-3" />
                {queueStats.failed} failed
              </div>
            )}
          </div>
        </div>
      )}

      {/* File List */}
      <div className="flex-1 overflow-auto">
        {error ? (
          <div className="p-4 text-center text-red-500">
            <AlertCircle className="w-8 h-8 mx-auto mb-2" />
            {error}
          </div>
        ) : entries.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Folder className="w-12 h-12 mx-auto mb-2 opacity-50" />
            Empty folder
          </div>
        ) : (
          <AnimatePresence>
            <div className={viewMode === 'grid' ? 'grid grid-cols-3 gap-2 p-2' : 'divide-y'}>
              {entries.map((item) => (
                <motion.div
                  key={item.path}
                  layout
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={() => {
                    if (item.isDirectory) {
                      navigateTo(item.path);
                    } else {
                      toggleSelection(item.path);
                      onFileSelect?.(item.path, item.name);
                    }
                  }}
                  className={`
                    ${viewMode === 'grid' 
                      ? 'flex flex-col items-center p-3 rounded-lg hover:bg-accent cursor-pointer' 
                      : 'flex items-center gap-3 p-3 hover:bg-accent cursor-pointer'
                    }
                    ${selectedFiles.has(item.path) ? 'bg-accent' : ''}
                  `}
                >
                  {viewMode === 'list' && allowMultiSelect && (
                    <Checkbox 
                      checked={selectedFiles.has(item.path)}
                      onCheckedChange={() => toggleSelection(item.path)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  )}
                  
                  {getFileIcon(item)}
                  
                  <div className={`${viewMode === 'grid' ? 'text-center mt-2' : 'flex-1 min-w-0'}`}>
                    <p className={`text-sm font-medium truncate ${viewMode === 'grid' ? 'max-w-full' : ''}`}>
                      {item.name}
                    </p>
                    {viewMode === 'list' && !item.isDirectory && (
                      <p className="text-xs text-muted-foreground">
                        {formatFileSize(item.size)}{item.modified ? ` • ${new Date(item.modified).toLocaleDateString()}` : ''}
                      </p>
                    )}
                  </div>

                  {viewMode === 'list' && selectedFiles.has(item.path) && (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  )}

                  {!item.isDirectory && viewMode === 'list' && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon">
                          <MoreVertical className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem 
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteItem(item.path, item.isDirectory);
                          }}
                          className="text-red-500"
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </motion.div>
              ))}
            </div>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
