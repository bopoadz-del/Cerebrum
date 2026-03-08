import { useState, useEffect } from 'react';
import { useProjects } from "@/hooks/useProjects";
import { AnimatePresence } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { MobileProjectSidebar } from './MobileProjectSidebar';
import { MobileChat } from './MobileChat';
import { MobileOutcomes } from './MobileOutcomes';
import { MobileNav } from './MobileNav';
import { MobileSettings } from './MobileSettings';

export function MobileLayout() {
  const [activeTab, setActiveTab] = useState<'projects' | 'chat' | 'outcomes'>('chat');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showNewChatModal, setShowNewChatModal] = useState(false);

  // Use Drive integration hook (same as desktop)
  const { 
    projects, 
    scanning, 
    isConnected, 
    loading,
    backendAvailable,
    connectionError,
    indexingStatus,
    scanResults,
    connectDrive, 
    disconnectDrive,
    scanDrive,
    refreshProjects,
    getProjectFiles

  // Update selected project when projects load
  } = useProjects();
  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  const selectedProject = projects.find(p => p.id === selectedProjectId);

  const handleSelectProject = (projectId: string) => {
    setSelectedProjectId(projectId);
    // Auto-switch to chat when selecting a project
    setActiveTab('chat');
  };

  const handleNewChat = () => {
    setShowNewChatModal(true);
  };

  const createNewChat = (title: string) => {
    console.log('Creating new chat:', title);
    setShowNewChatModal(false);
  };

  // Show loading state while checking Drive connection
  if (loading) {
    return (
      <div className="flex h-screen bg-white items-center justify-center">
        <div className="flex items-center gap-3 text-gray-500">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Checking OneDrive...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'projects' && (
          <MobileProjectSidebar
            projects={projects}
            selectedProjectId={selectedProjectId}
            selectedChatId={selectedChatId}
            onSelectProject={handleSelectProject}
            onSelectChat={setSelectedChatId}
            onNewChat={handleNewChat}
            isDriveConnected={isConnected}
            isScanning={scanning}
            isDemoMode={!backendAvailable}
            connectionError={connectionError}
            indexingStatus={indexingStatus}
            scanResults={scanResults}
            onConnectDrive={connectDrive}
            onDisconnectDrive={disconnectDrive}
            onScanDrive={scanDrive}
            onRefreshProjects={refreshProjects}
            onOpenSettings={() => setShowSettings(true)}
            getProjectFiles={getProjectFiles}
          />
        )}
        {activeTab === 'chat' && (
          <MobileChat
            projectName={selectedProject?.name || 'Select a project'}
            chatTitle="New Chat"
          />
        )}
        {activeTab === 'outcomes' && <MobileOutcomes />}
      </div>

      {/* Bottom Navigation */}
      <MobileNav activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Settings Modal */}
      <AnimatePresence>
        {showSettings && (
          <MobileSettings onClose={() => setShowSettings(false)} />
        )}
      </AnimatePresence>

      {/* New Chat Modal - Simple version for mobile */}
      <AnimatePresence>
        {showNewChatModal && (
          <NewChatModal 
            onClose={() => setShowNewChatModal(false)} 
            onCreate={createNewChat}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// Simple New Chat Modal for mobile
import { motion } from 'framer-motion';
import { X, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';

function NewChatModal({ onClose, onCreate }: { onClose: () => void; onCreate: (title: string) => void }) {
  const [title, setTitle] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim()) {
      onCreate(title.trim());
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">New Chat</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
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
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">
              Cancel
            </Button>
            <Button 
              type="submit" 
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white"
              disabled={!title.trim()}
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              Create
            </Button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}
