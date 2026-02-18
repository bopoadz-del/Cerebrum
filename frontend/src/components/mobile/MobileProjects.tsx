import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FolderOpen,
  MessageSquare,
  Cloud,
  Link,
  Check,
  Plus,
  Clock,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

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
      { id: 'c1', title: 'Revenue breakdown', timestamp: new Date(Date.now() - 1000 * 60 * 30) },
      { id: 'c2', title: 'Expense review', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2) },
      { id: 'c3', title: 'Budget forecast', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24) },
    ],
  },
  {
    id: '2',
    name: 'Construction Project A',
    isExpanded: false,
    chats: [
      { id: 'c4', title: 'Schedule analysis', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 48) },
      { id: 'c5', title: 'CAD review', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 72) },
    ],
  },
  {
    id: '3',
    name: 'Marketing Campaign',
    isExpanded: false,
    chats: [
      { id: 'c6', title: 'Content analysis', timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 5) },
    ],
  },
];

interface MobileProjectsProps {
  selectedProjectId: string | null;
  selectedChatId: string | null;
  onSelectProject: (projectId: string) => void;
  onSelectChat: (chatId: string) => void;
  isGoogleDriveConnected: boolean;
  onConnectGoogleDrive: () => void;
}

export function MobileProjects({
  selectedProjectId,
  selectedChatId,
  onSelectProject,
  onSelectChat,
  isGoogleDriveConnected,
  onConnectGoogleDrive,
}: MobileProjectsProps) {
  const [projects, setProjects] = useState<Project[]>(mockProjects);
  const [showNewChatModal, setShowNewChatModal] = useState(false);

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
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-4">
        <span className="font-semibold text-gray-900">Projects</span>
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

      {/* Project List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {projects.map((project) => (
            <div key={project.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {/* Project Header */}
              <button
                onClick={() => toggleProject(project.id)}
                className={cn(
                  'w-full flex items-center gap-3 px-4 py-3 text-left',
                  selectedProjectId === project.id && 'bg-indigo-50'
                )}
              >
                {project.isExpanded ? (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-gray-400" />
                )}
                {project.isExpanded ? (
                  <FolderOpen className="w-5 h-5 text-indigo-500" />
                ) : (
                  <Folder className="w-5 h-5 text-gray-400" />
                )}
                <span className="font-medium text-gray-900 flex-1">{project.name}</span>
                <span className="text-xs text-gray-400">{project.chats.length}</span>
              </button>

              {/* Chat List */}
              <AnimatePresence>
                {project.isExpanded && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 'auto' }}
                    exit={{ height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="border-t border-gray-100">
                      {project.chats.map((chat) => (
                        <button
                          key={chat.id}
                          onClick={() => onSelectChat(chat.id)}
                          className={cn(
                            'w-full flex items-center justify-between px-4 py-3 pl-12 text-left',
                            selectedChatId === chat.id && 'bg-indigo-100'
                          )}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            <span className="text-sm text-gray-700 truncate">{chat.title}</span>
                          </div>
                          <div className="flex items-center gap-1 text-xs text-gray-400 flex-shrink-0">
                            <Clock className="w-3 h-3" />
                            {formatChatDate(chat.timestamp)}
                          </div>
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

      {/* Google Drive Section */}
      <div className="p-4 bg-white border-t border-gray-200">
        <button
          onClick={onConnectGoogleDrive}
          className={cn(
            'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-colors',
            isGoogleDriveConnected
              ? 'bg-emerald-50 text-emerald-700'
              : 'bg-gray-100 text-gray-700'
          )}
        >
          {isGoogleDriveConnected ? (
            <>
              <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center">
                <Check className="w-4 h-4 text-white" />
              </div>
              <div className="flex-1 text-left">
                <span className="font-medium">Google Drive Connected</span>
              </div>
            </>
          ) : (
            <>
              <Cloud className="w-6 h-6" />
              <div className="flex-1 text-left">
                <span className="font-medium">Connect Google Drive</span>
                <p className="text-sm text-gray-500">Access your files</p>
              </div>
              <Link className="w-5 h-5" />
            </>
          )}
        </button>
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
