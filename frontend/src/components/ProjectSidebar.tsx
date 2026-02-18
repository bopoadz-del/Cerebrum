import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  MessageSquare,
  Cloud,
  Settings,
  Plus,
  Link,
  Check,
  LogOut,
  User,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';

interface Chat {
  id: string;
  title: string;
  timestamp: Date;
}

interface Project {
  id: string;
  name: string;
  file_count: number;
  status: string;
  updated_at?: string;
  chats?: Chat[];
  isExpanded?: boolean;
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
  onConnectDrive: () => void;
  onScanDrive: () => void;
  onRefreshProjects: () => void;
  onOpenSettings: () => void;
}

// Mock chats for each project
const getMockChats = (projectName: string): Chat[] => [
  { id: 'c1', title: `${projectName} - Analysis`, timestamp: new Date() },
  { id: 'c2', title: `${projectName} - Review`, timestamp: new Date(Date.now() - 86400000) },
  { id: 'c3', title: `${projectName} - Summary`, timestamp: new Date(Date.now() - 172800000) },
];

export function ProjectSidebar({
  projects,
  selectedProjectId,
  selectedChatId,
  onSelectProject,
  onSelectChat,
  onNewChat,
  isDriveConnected,
  isScanning,
  onConnectDrive,
  onScanDrive,
  onRefreshProjects,
  onOpenSettings,
}: ProjectSidebarProps) {
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set(['1']));
  const { user, logout } = useAuth();

  const toggleProject = (projectId: string) => {
    setExpandedProjects((prev) => {
      const next = new Set(prev);
      if (next.has(projectId)) {
        next.delete(projectId);
      } else {
        next.add(projectId);
      }
      return next;
    });
    onSelectProject(projectId);
  };

  const formatChatDate = (date: Date) => {
    const now = new Date();
    const chatDate = new Date(date);
    const diffMs = now.getTime() - chatDate.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(chatDate);
  };

  // If Drive is not connected, show connect prompt
  if (!isDriveConnected) {
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
        </div>

        {/* Connect Drive Prompt */}
        <div className="flex-1 flex flex-col items-center justify-center p-6">
          <div className="w-16 h-16 rounded-2xl bg-blue-100 flex items-center justify-center mb-4">
            <Cloud className="w-8 h-8 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Connect Google Drive</h3>
          <p className="text-sm text-gray-500 text-center mb-6">
            Connect your Google Drive to auto-discover projects and access your files for AI analysis.
          </p>
          <Button
            onClick={onConnectDrive}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Link className="w-4 h-4 mr-2" />
            Connect Google Drive
          </Button>
        </div>

        {/* Bottom - Settings & Logout */}
        <div className="border-t border-gray-200 bg-white p-3 space-y-1">
          {user && (
            <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-50 mb-2">
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
    );
  }

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

      {/* Projects Section */}
      <div className="flex-1 overflow-y-auto py-2">
        <div className="px-3 pb-2">
          <div className="flex items-center justify-between px-2 mb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                Projects
              </span>
              <button
                onClick={onRefreshProjects}
                disabled={isScanning}
                className="p-1 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors"
                title="Refresh projects"
              >
                <RefreshCw className={cn("w-3 h-3", isScanning && "animate-spin")} />
              </button>
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

          {/* Project Tree */}
          <div className="space-y-0.5">
            {projects.length === 0 ? (
              <div className="px-3 py-8 text-center">
                <p className="text-sm text-gray-500">No projects found</p>
                <button
                  onClick={onScanDrive}
                  className="text-xs text-blue-500 hover:text-blue-600 mt-2"
                >
                  Scan Drive
                </button>
              </div>
            ) : (
              projects.map((project) => {
                const isExpanded = expandedProjects.has(project.id);
                const chats = project.chats || getMockChats(project.name);
                
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
                      <span className="text-sm font-medium truncate">{project.name}</span>
                      <span className="ml-auto text-xs text-gray-400">{project.file_count} files</span>
                    </button>

                    {/* Chat History (appears under selected project) */}
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
                            {chats.map((chat) => (
                              <button
                                key={chat.id}
                                onClick={() => onSelectChat(chat.id)}
                                className={cn(
                                  'w-full flex items-center justify-between px-2 py-1.5 rounded-md text-left transition-colors',
                                  selectedChatId === chat.id
                                    ? 'bg-indigo-100 text-indigo-700'
                                    : 'hover:bg-gray-100 text-gray-600'
                                )}
                              >
                                <div className="flex items-center gap-2 min-w-0">
                                  <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                                  <span className="text-sm truncate">{chat.title}</span>
                                </div>
                                <span className="text-xs text-gray-400 flex-shrink-0">
                                  {formatChatDate(chat.timestamp)}
                                </span>
                              </button>
                            ))}
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
        {/* Google Drive Status */}
        <div className="p-3">
          <button
            onClick={onScanDrive}
            disabled={isScanning}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
              'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
            )}
          >
            <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
              <Check className="w-3 h-3 text-white" />
            </div>
            <div className="flex-1 text-left">
              <span className="text-sm font-medium">Google Drive</span>
              <p className="text-xs text-emerald-600 flex items-center gap-1">
                {isScanning ? (
                  <>
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Scanning...
                  </>
                ) : (
                  'Connected'
                )}
              </p>
            </div>
            <RefreshCw className={cn('w-4 h-4', isScanning && 'animate-spin')} />
          </button>
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
