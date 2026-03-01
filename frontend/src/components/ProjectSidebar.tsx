import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,

  Cloud,
  CloudOff,
  Settings,
  Plus,
  Link,
  Check,
  LogOut,
  User,
  Loader2,
  RefreshCw,
  Brain,
  Database,
  FileText,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';

interface Project {
  id: string;
  name: string;
  file_count: number;
  status: string;
  updated_at?: string;
  indexed?: number;
  total?: number;
  percent?: number;
}

interface DriveFile {
  id: string;
  name: string;
  mime_type: string;
  is_folder: boolean;
  modified_time?: string;
}

interface IndexingStatus {
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

interface ProjectSidebarProps {
  projects: Project[];
  selectedProjectId: string | null;
  selectedChatId: string | null;
  onSelectProject: (projectId: string) => void;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  isDriveConnected: boolean;
  isScanning: boolean;
  isDemoMode?: boolean;
  connectionError?: string | null;
  indexingStatus?: IndexingStatus | null;
  scanResults?: { detected: number; queued: number; zvecReady: boolean } | null;
  onConnectDrive: () => void;
  onDisconnectDrive?: () => void;
  onScanDrive: () => void;
  onRefreshProjects: () => void;
  onOpenSettings: () => void;
  getProjectFiles?: (projectId: string) => Promise<DriveFile[]>;
}

// Drive file icon based on mime type
const getFileIcon = (mimeType: string, isFolder: boolean) => {
  if (isFolder) return <Folder className="w-3.5 h-3.5 flex-shrink-0 text-blue-500" />;
  if (mimeType.includes('pdf')) return <span className="text-red-500 text-xs">PDF</span>;
  if (mimeType.includes('document') || mimeType.includes('word')) return <span className="text-blue-500 text-xs">DOC</span>;
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return <span className="text-green-500 text-xs">XLS</span>;
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return <span className="text-orange-500 text-xs">PPT</span>;
  return <span className="text-gray-400 text-xs">FILE</span>;
};

export function ProjectSidebar({
  projects,
  selectedProjectId,
  selectedChatId,
  onSelectProject,
  onSelectChat,
  onNewChat,
  isDriveConnected,
  isScanning,
  isDemoMode,
  connectionError,
  indexingStatus,
  scanResults,
  onConnectDrive,
  onDisconnectDrive,
  onScanDrive,
  onRefreshProjects,
  onOpenSettings,
  getProjectFiles,
}: ProjectSidebarProps) {
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set(['1']));
  const [projectFiles, setProjectFiles] = useState<Record<string, DriveFile[]>>({});
  const [loadingFiles, setLoadingFiles] = useState<Record<string, boolean>>({});
  const { user, logout } = useAuth();

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



  return (
    <div className="w-[280px] h-screen bg-gray-50 border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="h-14 flex items-center justify-between px-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <span className="text-white font-semibold text-sm">R</span>
          </div>
          <span className="font-semibold text-gray-900">Reasoner</span>
        </div>
        {/* New Chat Button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onNewChat}
          className="h-8 px-2 text-indigo-600 hover:bg-indigo-50"
        >
          <Plus className="w-4 h-4 mr-1" />
          New Chat
        </Button>
      </div>

      {/* Projects Section - Always visible */}
      <div className="flex-1 overflow-y-auto py-2">
        <div className="px-3 pb-2">
          <div className="flex items-center justify-between px-2 mb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Projects
              </span>
              {(isDriveConnected || projects.length > 0) && (
                <button
                  onClick={onRefreshProjects}
                  disabled={isScanning}
                  className="p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors"
                  title="Refresh projects"
                >
                  <RefreshCw className={cn("w-3 h-3", isScanning && "animate-spin")} />
                </button>
              )}
            </div>
            <div className="flex items-center gap-2">
              {isScanning && (
                <span className="text-xs text-blue-500 animate-pulse flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Scanning...
                </span>
              )}
              <span className="text-xs text-gray-400">{projects.length} total</span>
            </div>
          </div>

          {/* ZVec Indexing Status Panel */}
          {(isScanning || indexingStatus || scanResults) && (
            <div className="mx-2 mb-3 p-3 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-100">
              <div className="flex items-center gap-2 mb-2">
                <Brain className="w-4 h-4 text-indigo-600" />
                <span className="font-medium text-sm text-indigo-900">ZVec AI Indexing</span>
                {isScanning && <Loader2 className="w-3 h-3 text-indigo-600 animate-spin" />}
              </div>
              
              {/* Scan Results */}
              {scanResults && (
                <div className="text-xs text-indigo-700 mb-2 space-y-0.5">
                  <p>Detected {scanResults.detected} projects</p>
                  <p>Queued {scanResults.queued} files for indexing</p>
                  <p className="text-indigo-500">
                    ZVec AI: {scanResults.zvecReady ? 'Ready ✓' : 'Initializing...'}
                  </p>
                </div>
              )}
              
              {/* Overall Progress */}
              {indexingStatus?.summary && (
                <div className="mt-2">
                  <div className="flex justify-between text-xs text-indigo-600 mb-1">
                    <span>Overall Progress</span>
                    <span>{indexingStatus.summary.overall_percent}%</span>
                  </div>
                  <div className="h-1.5 bg-indigo-100 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                      style={{ width: `${indexingStatus.summary.overall_percent}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-xs text-gray-500 mt-1.5">
                    <span><Database className="w-3 h-3 inline mr-0.5" />{indexingStatus.summary.total_indexed}</span>
                    <span><FileText className="w-3 h-3 inline mr-0.5" />{indexingStatus.summary.total_files}</span>
                    <span>ZVec: {indexingStatus.summary.zvec_count}</span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Project Tree */}
          <div className="space-y-0.5">
            {!isDriveConnected ? (
              <div className="px-3 py-6 text-center border border-dashed border-gray-300 rounded-lg mx-2">
                <Cloud className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-500 mb-1">Connect Google Drive</p>
                <p className="text-xs text-gray-400 mb-3">to auto-discover projects</p>
                <button
                  onClick={onConnectDrive}
                  className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                >
                  Connect now →
                </button>
              </div>
            ) : projects.length === 0 ? (
              <div className="px-3 py-8 text-center">
                <p className="text-sm text-gray-500">No projects found</p>
                <button
                  onClick={onScanDrive}
                  disabled={isScanning}
                  className="text-xs text-blue-500 hover:text-blue-600 mt-2 disabled:opacity-50"
                >
                  {isScanning ? 'Scanning...' : 'Scan Drive'}
                </button>
              </div>
            ) : (
              projects.map((project) => {
                const isExpanded = expandedProjects.has(project.id);
                const isIndexing = project.status === 'queued' || project.status === 'running';
                const isDone = project.status === 'done' || (project.percent !== undefined && project.percent >= 100);
                
                return (
                  <div key={project.id}>
                    {/* Project Item */}
                    <button
                      onClick={() => toggleProject(project.id)}
                      className={cn(
                        'w-full flex items-center gap-2 px-2 py-2 rounded-lg text-left transition-colors',
                        selectedProjectId === project.id
                          ? 'bg-indigo-50 text-indigo-700'
                          : 'hover:bg-gray-100 text-gray-700'
                      )}
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 flex-shrink-0" />
                      ) : (
                        <ChevronRight className="w-4 h-4 flex-shrink-0" />
                      )}
                      {isExpanded ? (
                        <FolderOpen className="w-4 h-4 flex-shrink-0" />
                      ) : (
                        <Folder className="w-4 h-4 flex-shrink-0" />
                      )}
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium truncate block">{project.name}</span>
                        {/* Indexing progress bar */}
                        {project.total !== undefined && project.total > 0 && (
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
                              <div 
                                className={cn(
                                  "h-full rounded-full transition-all duration-300",
                                  isDone ? "bg-emerald-500" : "bg-indigo-500"
                                )}
                                style={{ width: `${project.percent || 0}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-400">
                              {isIndexing && <Loader2 className="w-3 h-3 inline animate-spin mr-0.5" />}
                              {project.indexed}/{project.total}
                            </span>
                            {isDone && <Check className="w-3 h-3 text-emerald-500" />}
                          </div>
                        )}
                      </div>
                      <span className="ml-2 text-xs text-gray-400">{project.file_count}</span>
                    </button>

                    {/* Files in Project (appears under selected project) */}
                    <AnimatePresence>
                      {isExpanded && selectedProjectId === project.id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="pl-8 pr-2 py-1 space-y-0.5">
                            {loadingFiles[project.id] ? (
                              <div className="flex items-center gap-2 px-2 py-1.5 text-gray-400">
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                <span className="text-xs">Loading files...</span>
                              </div>
                            ) : projectFiles[project.id]?.length > 0 ? (
                              projectFiles[project.id].map((file) => (
                                <button
                                  key={file.id}
                                  onClick={() => file.is_folder ? onSelectChat(file.id) : onSelectChat(file.id)}
                                  className={cn(
                                    'w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors',
                                    selectedChatId === file.id
                                      ? 'bg-indigo-100 text-indigo-700'
                                      : 'hover:bg-gray-100 text-gray-600'
                                  )}
                                >
                                  {getFileIcon(file.mime_type, file.is_folder)}
                                  <span className="text-sm truncate flex-1">{file.name}</span>
                                </button>
                              ))
                            ) : (
                              <div className="px-2 py-1.5 text-xs text-gray-400">
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
      </div>

      {/* Bottom Section */}
      <div className="border-t border-gray-200 bg-white">
        {/* Demo Mode Indicator */}
        {isDemoMode && (
          <div className="px-3 pt-3">
            <div className="px-3 py-1.5 bg-amber-50 text-amber-700 text-xs rounded-md text-center">
              Demo Mode - Backend Unavailable
            </div>
          </div>
        )}
        
        {/* Connection Error */}
        {connectionError && !isDriveConnected && (
          <div className="px-3 pt-2">
            <div className="px-3 py-2 bg-red-50 text-red-700 text-xs rounded-md">
              <p className="font-medium">Connection Issue</p>
              <p>{connectionError}</p>
              <button 
                onClick={onConnectDrive}
                className="text-red-600 underline mt-1 hover:text-red-800"
              >
                Try connecting anyway →
              </button>
            </div>
          </div>
        )}
        
        {/* Google Drive Status */}
        <div className="p-3">
          {isDriveConnected ? (
            <div className="relative group">
              <button
                onClick={onScanDrive}
                disabled={isScanning}
                className={cn(
                  'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                  isDemoMode 
                    ? 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                    : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                )}
              >
                <div className={cn(
                  'w-5 h-5 rounded-full flex items-center justify-center',
                  isDemoMode ? 'bg-amber-500' : 'bg-emerald-500'
                )}>
                  <Check className="w-3 h-3 text-white" />
                </div>
                <div className="flex-1 text-left">
                  <span className="text-sm font-medium">Google Drive</span>
                  <p className={cn(
                    'text-xs flex items-center gap-1',
                    isDemoMode ? 'text-amber-600' : 'text-emerald-600'
                  )}>
                    {isScanning ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        Scanning...
                      </>
                    ) : isDemoMode ? (
                      'Demo Mode'
                    ) : (
                      'Connected'
                    )}
                  </p>
                </div>
                <RefreshCw className={cn('w-4 h-4', isScanning && 'animate-spin')} />
              </button>
              
              {/* Disconnect button - shows on hover */}
              {onDisconnectDrive && (
                <button
                  onClick={onDisconnectDrive}
                  className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center shadow-sm hover:bg-red-600"
                  title="Disconnect Google Drive"
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
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                'bg-gray-100 text-gray-600 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-50'
              )}
            >
              {isScanning ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <CloudOff className="w-5 h-5" />
              )}
              <div className="flex-1 text-left">
                <span className="text-sm font-medium">Google Drive</span>
                <p className="text-xs text-gray-500">
                  {isScanning ? 'Connecting...' : 'Click to connect'}
                </p>
              </div>
              {!isScanning && <Link className="w-4 h-4" />}
            </button>
          )}
        </div>

        {/* User & Settings */}
        <div className="px-3 pb-3 space-y-1">
          {user && (
            <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-50">
              <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
                <User className="w-4 h-4 text-indigo-600" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{user.full_name}</p>
                <p className="text-xs text-gray-500 truncate">{user.email}</p>
              </div>
            </div>
          )}
          
          <button
            onClick={onOpenSettings}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-100 text-gray-700 transition-colors"
          >
            <Settings className="w-5 h-5" />
            <span className="text-sm font-medium">Settings</span>
          </button>
          
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-red-50 text-gray-700 hover:text-red-600 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span className="text-sm font-medium">Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  );
}
