import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  HardDrive,
  CloudOff,
  Loader2,
  RefreshCw,
  Brain,
  Settings,
  LogOut,
  User,
  Cpu,
} from 'lucide-react';
import { cn } from '@/lib/utils';
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

export interface DriveFile {
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
  onNewChat?: () => void;
  isDriveConnected?: boolean;
  isScanning: boolean;
  isDemoMode?: boolean;
  connectionError?: string | null;
  indexingStatus?: IndexingStatus | null;
  scanResults?: { detected: number; queued: number; zvecReady: boolean } | null;
  onConnectDrive?: () => void;
  onDisconnectDrive?: () => void;
  onScanDrive?: () => void;
  onRefreshProjects: () => void;
  onOpenSettings: () => void;
  getProjectFiles?: (projectId: string) => Promise<DriveFile[]>;
  isMobile?: boolean;
  onToggleSidebar?: () => void;
}

const getFileIcon = (mimeType: string, isFolder: boolean) => {
  if (isFolder) return <Folder className="w-3.5 h-3.5 flex-shrink-0 text-blue-500" />;
  if (mimeType.includes('pdf')) return <span className="text-red-500 text-[10px] font-medium">PDF</span>;
  if (mimeType.includes('document') || mimeType.includes('word')) return <span className="text-blue-500 text-[10px] font-medium">DOC</span>;
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return <span className="text-green-500 text-[10px] font-medium">XLS</span>;
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return <span className="text-orange-500 text-[10px] font-medium">PPT</span>;
  return <span className="text-gray-400 text-[10px] font-medium">FILE</span>;
};

export function ProjectSidebar({
  projects,
  selectedProjectId,
  selectedChatId,
  onSelectProject,
  onSelectChat,
  isDriveConnected,
  isScanning,
  indexingStatus,
  onConnectDrive,
  onScanDrive,
  onRefreshProjects,
  onOpenSettings,
  getProjectFiles,
}: ProjectSidebarProps) {
  const navigate = useNavigate();
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set(['1']));
  const [projectFiles, setProjectFiles] = useState<Record<string, DriveFile[]>>({});
  const [loadingFiles, setLoadingFiles] = useState<Record<string, boolean>>({});
  const [fileErrors, setFileErrors] = useState<Record<string, string>>({});
  const { user, logout } = useAuth();

  const loadProjectFiles = async (projectId: string) => {
    if (!getProjectFiles || projectFiles[projectId]) return;
    
    setLoadingFiles(prev => ({ ...prev, [projectId]: true }));
    setFileErrors(prev => ({ ...prev, [projectId]: '' }));
    try {
      const files = await getProjectFiles(projectId);
      setProjectFiles(prev => ({ ...prev, [projectId]: files }));
    } catch (e: unknown) {
      console.error('Failed to load project files:', e);
      const errorMessage = e instanceof Error ? e.message : 'Failed to load files';
      setFileErrors(prev => ({ ...prev, [projectId]: errorMessage }));
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
        loadProjectFiles(projectId);
      }
      return next;
    });
    onSelectProject(projectId);
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header - Simplified */}
      <div className="h-12 flex items-center justify-between px-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-900">Projects</span>
          {(isDriveConnected || projects.length > 0) && (
            <button
              onClick={onRefreshProjects}
              disabled={isScanning}
              className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={cn("w-3.5 h-3.5", isScanning && "animate-spin")} />
            </button>
          )}
        </div>
        <span className="text-xs text-gray-400">{projects.length}</span>
      </div>

      {/* Indexing Status - Compact */}
      <AnimatePresence>
        {(isScanning || indexingStatus) && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mx-3 mt-3 p-2.5 bg-indigo-50 rounded-lg border border-indigo-100"
          >
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-3.5 h-3.5 text-indigo-600" />
              <span className="text-xs font-medium text-indigo-900">AI Indexing</span>
              {isScanning && <Loader2 className="w-3 h-3 text-indigo-600 animate-spin" />}
            </div>
            
            {indexingStatus?.summary && (
              <>
                <div className="h-1 bg-indigo-100 rounded-full overflow-hidden mb-1.5">
                  <div 
                    className="h-full bg-indigo-500 rounded-full transition-all duration-500"
                    style={{ width: `${indexingStatus.summary.overall_percent}%` }}
                  />
                </div>
                <div className="flex justify-between text-[10px] text-indigo-600">
                  <span>{indexingStatus.summary.total_indexed} indexed</span>
                  <span>{indexingStatus.summary.zvec_count} vectors</span>
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Projects List */}
      <div className="flex-1 overflow-y-auto p-2">
        {!isDriveConnected ? (
          <div className="p-4 text-center border border-dashed border-gray-200 rounded-lg mx-1">
            <HardDrive className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p className="text-xs text-gray-500 mb-2">Connect Local Drive</p>
            <button
              onClick={onConnectDrive}
              className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
            >
              Connect →
            </button>
          </div>
        ) : projects.length === 0 ? (
          <div className="p-6 text-center">
            <p className="text-xs text-gray-400">No projects found</p>
            <button
              onClick={onScanDrive}
              disabled={isScanning}
              className="text-xs text-indigo-500 hover:text-indigo-600 mt-2"
            >
              {isScanning ? 'Scanning...' : 'Scan Drive'}
            </button>
          </div>
        ) : (
          <div className="space-y-0.5">
            {projects.map((project) => {
              const isExpanded = expandedProjects.has(project.id);
              const isSelected = selectedProjectId === project.id;
              const isDone = project.status === 'done' || (project.percent !== undefined && project.percent >= 100);
              
              return (
                <div key={project.id}>
                  <button
                    onClick={() => toggleProject(project.id)}
                    className={cn(
                      'w-full flex items-center gap-1.5 px-2 py-1.5 rounded-md text-left transition-colors',
                      isSelected
                        ? 'bg-gray-100 text-gray-900'
                        : 'hover:bg-gray-50 text-gray-700'
                    )}
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-3.5 h-3.5 flex-shrink-0 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 flex-shrink-0 text-gray-400" />
                    )}
                    {isExpanded ? (
                      <FolderOpen className="w-4 h-4 flex-shrink-0 text-indigo-500" />
                    ) : (
                      <Folder className="w-4 h-4 flex-shrink-0 text-gray-400" />
                    )}
                    
                    <div className="flex-1 min-w-0">
                      <span className="text-sm truncate block">{project.name}</span>
                      {project.total !== undefined && project.total > 0 && (
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
                            <div 
                              className={cn(
                                "h-full rounded-full transition-all duration-300",
                                isDone ? "bg-emerald-400" : "bg-indigo-400"
                              )}
                              style={{ width: `${project.percent || 0}%` }}
                            />
                          </div>
                          <span className="text-[10px] text-gray-400">
                            {project.indexed}/{project.total}
                          </span>
                        </div>
                      )}
                    </div>
                  </button>

                  {/* Files */}
                  <AnimatePresence>
                    {isExpanded && isSelected && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.15 }}
                        className="overflow-hidden"
                      >
                        <div className="pl-7 pr-1 py-1 space-y-0.5">
                          {loadingFiles[project.id] ? (
                            <div className="flex items-center gap-2 px-2 py-1.5 text-gray-400">
                              <Loader2 className="w-3 h-3 animate-spin" />
                              <span className="text-xs">Loading...</span>
                            </div>
                          ) : fileErrors[project.id] ? (
                            <div className="px-2 py-1.5">
                              <p className="text-[10px] text-red-500">{fileErrors[project.id]}</p>
                            </div>
                          ) : projectFiles[project.id]?.length > 0 ? (
                            projectFiles[project.id].map((file) => (
                              <button
                                key={file.id}
                                onClick={() => onSelectChat(file.id)}
                                className={cn(
                                  'w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors',
                                  selectedChatId === file.id
                                    ? 'bg-indigo-50 text-indigo-700'
                                    : 'hover:bg-gray-50 text-gray-600'
                                )}
                              >
                                {getFileIcon(file.mime_type, file.is_folder)}
                                <span className="text-xs truncate flex-1">{file.name}</span>
                              </button>
                            ))
                          ) : (
                            <div className="px-2 py-1 text-[10px] text-gray-400">
                              No files
                            </div>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-100 p-2 space-y-1">
        {/* Local Drive Status */}
        <button
          onClick={isDriveConnected ? onScanDrive : onConnectDrive}
          disabled={isScanning}
          className={cn(
            'w-full flex items-center gap-2 px-2 py-2 rounded-md transition-colors text-left',
            isDriveConnected
              ? 'hover:bg-gray-50 text-gray-700'
              : 'hover:bg-indigo-50 text-indigo-600'
          )}
        >
          {isScanning ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />
              <span className="text-xs">Scanning...</span>
            </>
          ) : isDriveConnected ? (
            <>
              <HardDrive className="w-4 h-4 text-emerald-500" />
              <span className="text-xs text-gray-600">Local Drive Connected</span>
              <RefreshCw className="w-3 h-3 ml-auto text-gray-400" />
            </>
          ) : (
            <>
              <CloudOff className="w-4 h-4" />
              <span className="text-xs">Connect Local Drive</span>
            </>
          )}
        </button>

        {/* Edge devices */}
        <button
          onClick={() => navigate('/edge')}
          className="w-full flex items-center gap-2 px-2 py-2 rounded-md hover:bg-cyan-50 text-gray-700 hover:text-cyan-700 transition-colors"
        >
          <Cpu className="w-4 h-4" />
          <span className="text-xs">Edge devices</span>
        </button>

        {/* Settings */}
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center gap-2 px-2 py-2 rounded-md hover:bg-gray-50 text-gray-700 transition-colors"
        >
          <Settings className="w-4 h-4" />
          <span className="text-xs">Settings</span>
        </button>

        {/* User / Logout */}
        {user ? (
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 px-2 py-2 rounded-md hover:bg-red-50 text-gray-600 hover:text-red-600 transition-colors"
          >
            <div className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center">
              <User className="w-3 h-3" />
            </div>
            <span className="text-xs truncate flex-1">{user.full_name}</span>
            <LogOut className="w-3 h-3" />
          </button>
        ) : null}
      </div>
    </div>
  );
}
