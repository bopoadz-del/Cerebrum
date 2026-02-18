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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';

interface Project {
  id: string;
  name: string;
  chats: Chat[];
  isExpanded?: boolean;
}

interface Chat {
  id: string;
  title: string;
  timestamp: Date;
}

const mockProjects: Project[] = [
  {
    id: '1',
    name: 'Q4 Financial Analysis',
    isExpanded: true,
    chats: [
      { id: 'c1', title: 'Revenue breakdown', timestamp: new Date() },
      { id: 'c2', title: 'Expense review', timestamp: new Date() },
      { id: 'c3', title: 'Budget forecast', timestamp: new Date() },
    ],
  },
  {
    id: '2',
    name: 'Construction Project A',
    isExpanded: false,
    chats: [
      { id: 'c4', title: 'Schedule analysis', timestamp: new Date() },
      { id: 'c5', title: 'CAD review', timestamp: new Date() },
    ],
  },
  {
    id: '3',
    name: 'Marketing Campaign',
    isExpanded: false,
    chats: [
      { id: 'c6', title: 'Content analysis', timestamp: new Date() },
    ],
  },
];

interface ProjectSidebarProps {
  selectedProjectId: string | null;
  selectedChatId: string | null;
  onSelectProject: (projectId: string) => void;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
  isGoogleDriveConnected: boolean;
  onConnectGoogleDrive: () => void;
  onOpenSettings: () => void;
}

export function ProjectSidebar({
  selectedProjectId,
  selectedChatId,
  onSelectProject,
  onSelectChat,
  onNewChat,
  isGoogleDriveConnected,
  onConnectGoogleDrive,
  onOpenSettings,
}: ProjectSidebarProps) {
  const [projects, setProjects] = useState<Project[]>(mockProjects);
  const { user, logout } = useAuth();

  const toggleProject = (projectId: string) => {
    setProjects((prev) =>
      prev.map((p) =>
        p.id === projectId ? { ...p, isExpanded: !p.isExpanded } : p
      )
    );
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
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Projects
            </span>
            <span className="text-xs text-gray-400">{projects.length} total</span>
          </div>

          {/* Project Tree */}
          <div className="space-y-0.5">
            {projects.map((project) => (
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
                  {project.isExpanded ? (
                    <ChevronDown className="w-4 h-4 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 flex-shrink-0" />
                  )}
                  {project.isExpanded ? (
                    <FolderOpen className="w-4 h-4 flex-shrink-0" />
                  ) : (
                    <Folder className="w-4 h-4 flex-shrink-0" />
                  )}
                  <span className="text-sm font-medium truncate">{project.name}</span>
                  <span className="ml-auto text-xs text-gray-400">{project.chats.length}</span>
                </button>

                {/* Chat History (appears under selected project) */}
                <AnimatePresence>
                  {project.isExpanded && selectedProjectId === project.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="pl-8 pr-2 py-1 space-y-0.5">
                        {project.chats.map((chat) => (
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
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Section */}
      <div className="border-t border-gray-200 bg-white">
        {/* Google Drive Connector */}
        <div className="p-3">
          <button
            onClick={onConnectGoogleDrive}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
              isGoogleDriveConnected
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
            )}
          >
            {isGoogleDriveConnected ? (
              <>
                <div className="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
                  <Check className="w-3 h-3 text-white" />
                </div>
                <div className="flex-1 text-left">
                  <span className="text-sm font-medium">Google Drive</span>
                  <p className="text-xs text-emerald-600">Connected</p>
                </div>
              </>
            ) : (
              <>
                <Cloud className="w-5 h-5" />
                <div className="flex-1 text-left">
                  <span className="text-sm font-medium">Connect Google Drive</span>
                  <p className="text-xs text-gray-500">Access your files</p>
                </div>
                <Link className="w-4 h-4" />
              </>
            )}
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
