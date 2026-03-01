import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  MessageSquare,
  Cloud,
  CloudOff,
  Link,
  Check,
  Plus,
  Clock,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface Project {
  id: string;
  name: string;
  file_count: number;
  status: string;
  updated_at?: string;
}

interface DriveFile {
  id: string;
  name: string;
  mime_type: string;
  is_folder: boolean;
  modified_time?: string;
}

interface MobileProjectsProps {
  projects: Project[];
  selectedProjectId: string | null;
  selectedChatId: string | null;
  onSelectProject: (projectId: string) => void;
  onSelectChat: (chatId: string) => void;
  isDriveConnected: boolean;
  isScanning: boolean;
  isDemoMode?: boolean;
  connectionError?: string | null;
  onConnectDrive: () => void;
  onDisconnectDrive?: () => void;
  onScanDrive: () => void;
  onRefreshProjects: () => void;
  getProjectFiles?: (projectId: string) => Promise<DriveFile[]>;
}

// Drive file icon based on mime type
const getFileIcon = (mimeType: string, isFolder: boolean) => {
  if (isFolder) return <Folder className="w-4 h-4 flex-shrink-0 text-blue-500" />;
  if (mimeType?.includes('pdf')) return <span className="text-red-500 text-xs">PDF</span>;
  if (mimeType?.includes('document') || mimeType?.includes('word')) return <span className="text-blue-500 text-xs">DOC</span>;
  if (mimeType?.includes('spreadsheet') || mimeType?.includes('excel')) return <span className="text-green-500 text-xs">XLS</span>;
  if (mimeType?.includes('presentation') || mimeType?.includes('powerpoint')) return <span className="text-orange-500 text-xs">PPT</span>;
  return <span className="text-gray-400 text-xs">FILE</span>;
};

export function MobileProjects({
  projects,
  selectedProjectId,
  selectedChatId,
  onSelectProject,
  onSelectChat,
  isDriveConnected,
  isScanning,
  isDemoMode,
  connectionError,
  onConnectDrive,
  onDisconnectDrive,
  onScanDrive,
  onRefreshProjects,
  getProjectFiles,
}: MobileProjectsProps) {
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set());
  const [projectFiles, setProjectFiles] = useState<Record<string, DriveFile[]>>({});
  const [loadingFiles, setLoadingFiles] = useState<Record<string, boolean>>({});
  const [showNewChatModal, setShowNewChatModal] = useState(false);

  const loadProjectFiles = async (projectId: string) => {
    if (!getProjectFiles || projectFiles[projectId]) return;
    
    setLoadingFiles(prev => ({ ...prev, [projectId]: true }));
    try {
      const files = await getProjectFiles(projectId);
      setProjectFiles(prev => ({ ...prev, [projectId]: files }));
    } catch (e) {
      console.error('Failed to load project files:', e);
    } finally {
      setLoadingFiles(prev => ({ ...prev, [projectId]: false }));
    }
  };

  const toggleProject = (projectId: string) => {
    setExpandedProjects((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) {
        next.delete(projectId);
      } else {
        next.add(projectId);
        // Load files when expanding
        loadProjectFiles(projectId);
      }
      return next;
    });
    onSelectProject(projectId);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(date);
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4">
        <span className="font-semibold text-gray-900">Projects</span>
        <div className="flex items-center gap-2">
          {(isDriveConnected || projects.length > 0) && (
            <button
              onClick={onRefreshProjects}
              disabled={isScanning}
              className="p-2 rounded-lg hover:bg-gray-100 text-gray-400 disabled:opacity-50"
            >
              <RefreshCw className={cn("w-4 h-4", isScanning && "animate-spin")} />
            </button>
          )}
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => setShowNewChatModal(true)}
            className="text-indigo-600"
          >
            <Plus className="w-4 h-4 mr-1" />
            New Chat
          </Button>
        </div>
      </div>

      {/* Project List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {!isDriveConnected ? (
            <div className="px-6 py-12 text-center">
              <Cloud className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 mb-1">Connect Google Drive</p>
              <p className="text-sm text-gray-400 mb-4">to auto-discover projects</p>
              <Button onClick={onConnectDrive} className="bg-indigo-600">
                <Cloud className="w-4 h-4 mr-2" />
                Connect
              </Button>
            </div>
          ) : projects.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-gray-500 mb-2">No projects found</p>
              <button
                onClick={onScanDrive}
                disabled={isScanning}
                className="text-sm text-indigo-600 disabled:opacity-50"
              >
                {isScanning ? 'Scanning...' : 'Scan Drive'}
              </button>
            </div>
          ) : (
            projects.map((project) => {
              const isExpanded = expandedProjects.has(project.id);
              
              return (
                <div key={project.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  {/* Project Header */}
                  <button
                    onClick={() => toggleProject(project.id)}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-3 text-left',
                      selectedProjectId === project.id && 'bg-indigo-50'
                    )}
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    )}
                    {isExpanded ? (
                      <FolderOpen className="w-5 h-5 text-indigo-500" />
                    ) : (
                      <Folder className="w-5 h-5 text-gray-400" />
                    )}
                    <span className="font-medium text-gray-900 flex-1">{project.name}</span>
                    <span className="text-xs text-gray-400">{project.file_count} files</span>
                  </button>

                  {/* Files List */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0 }}
                        animate={{ height: 'auto' }}
                        exit={{ height: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="border-t border-gray-100">
                          {loadingFiles[project.id] ? (
                            <div className="flex items-center gap-2 px-4 py-3 pl-12 text-gray-400">
                              <Loader2 className="w-4 h-4 animate-spin" />
                              <span className="text-sm">Loading files...</span>
                            </div>
                          ) : projectFiles[project.id]?.length > 0 ? (
                            projectFiles[project.id].map((file) => (
                              <button
                                key={file.id}
                                onClick={() => onSelectChat(file.id)}
                                className={cn(
                                  'w-full flex items-center gap-3 px-4 py-3 pl-12 text-left',
                                  selectedChatId === file.id && 'bg-indigo-100'
                                )}
                              >
                                {getFileIcon(file.mime_type, file.is_folder)}
                                <span className="text-sm text-gray-700 truncate flex-1">{file.name}</span>
                              </button>
                            ))
                          ) : (
                            <div className="px-4 py-3 pl-12 text-sm text-gray-400">
                              No files found
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Google Drive Section */}
      <div className="p-4 bg-white border-t border-gray-200">
        {isDriveConnected ? (
          <div className="relative">
            <button
              onClick={onScanDrive}
              disabled={isScanning}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-colors',
                isDemoMode 
                  ? 'bg-amber-50 text-amber-700'
                  : 'bg-emerald-50 text-emerald-700'
              )}
            >
              <div className={cn(
                'w-8 h-8 rounded-full flex items-center justify-center',
                isDemoMode ? 'bg-amber-500' : 'bg-emerald-500'
              )}>
                <Check className="w-4 h-4 text-white" />
              </div>
              <div className="flex-1 text-left">
                <span className="font-medium">Google Drive</span>
                <p className={cn(
                  'text-sm',
                  isDemoMode ? 'text-amber-600' : 'text-emerald-600'
                )}>
                  {isScanning ? 'Scanning...' : isDemoMode ? 'Demo Mode' : 'Connected'}
                </p>
              </div>
              <RefreshCw className={cn("w-5 h-5", isScanning && "animate-spin")} />
            </button>
            
            {/* Disconnect button */}
            {onDisconnectDrive && (
              <button
                onClick={onDisconnectDrive}
                className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center shadow-sm"
              >
                <span className="text-xs">×</span>
              </button>
            )}
          </div>
        ) : (
          <button
            onClick={onConnectDrive}
            disabled={isScanning}
            className={cn(
              'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-colors',
              'bg-gray-100 text-gray-700 disabled:opacity-50'
            )}
          >
            {isScanning ? (
              <Loader2 className="w-6 h-6 animate-spin" />
            ) : (
              <CloudOff className="w-6 h-6" />
            )}
            <div className="flex-1 text-left">
              <span className="font-medium">Connect Google Drive</span>
              <p className="text-sm text-gray-500">
                {isScanning ? 'Connecting...' : 'Access your files'}
              </p>
            </div>
            {!isScanning && <Link className="w-5 h-5" />}
          </button>
        )}
        
        {/* Demo Mode Indicator */}
        {isDemoMode && isDriveConnected && (
          <div className="mt-2 px-3 py-1.5 bg-amber-50 text-amber-700 text-xs rounded-lg text-center">
            Demo Mode - Backend Unavailable
          </div>
        )}
        
        {/* Connection Error */}
        {connectionError && !isDriveConnected && (
          <div className="mt-2 px-3 py-2 bg-red-50 text-red-700 text-xs rounded-lg">
            <p className="font-medium">Connection Issue</p>
            <p>{connectionError}</p>
          </div>
        )}
      </div>

      {/* New Chat Modal */}
      {showNewChatModal && (
        <NewChatModal onClose={() => setShowNewChatModal(false)} />
      )}
    </div>
  );
}

function NewChatModal({ onClose }: { onClose: () => void }) {
  const [title, setTitle] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim()) {
      console.log('Creating new chat:', title);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50">
      <motion.div
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        className="bg-white rounded-t-2xl sm:rounded-2xl w-full max-w-md p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">New Chat</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            Close
          </button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <label className="block text-sm text-gray-600 mb-2">Chat Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter chat title..."
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none transition-all mb-4"
            autoFocus
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 border border-gray-200 rounded-xl text-gray-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!title.trim()}
              className="flex-1 px-4 py-3 bg-indigo-600 text-white rounded-xl disabled:opacity-50"
            >
              Create Chat
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
