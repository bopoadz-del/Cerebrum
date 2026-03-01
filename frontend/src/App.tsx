import { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, MessageSquare, Loader2 } from 'lucide-react';
import { ProjectSidebar } from '@/components/ProjectSidebar';
import { ChatInterfaceV2 } from '@/components/ChatInterfaceV2';
import { OutcomesPanel } from '@/components/OutcomesPanel';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import { useDrive } from '@/hooks/useDrive';
import Login from '@/pages/Login';

// Mobile components
import { MobileNav } from '@/components/mobile/MobileNav';
import { MobileChat } from '@/components/mobile/MobileChat';
import { MobileOutcomes } from '@/components/mobile/MobileOutcomes';
import { MobileProjects } from '@/components/mobile/MobileProjects';
import { MobileSettings } from '@/components/mobile/MobileSettings';

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
}

function DesktopLayout() {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>('1');
  const [selectedChatId, setSelectedChatId] = useState<string | null>('c1');
  const [showSettings, setShowSettings] = useState(false);
  const [showNewChatModal, setShowNewChatModal] = useState(false);
  
  // Use Drive integration hook
  const { 
    projects, 
    scanning, 
    isConnected, 
    loading,
    backendAvailable,
    connectionError,
    connectDrive, 
    disconnectDrive,
    scanDrive,
    refreshProjects,
    getProjectFiles
  } = useDrive();

  // Update selected project to use real data from Drive
  const selectedProject = projects.find(p => p.id === selectedProjectId) || projects[0];

  const selectedChat = {
    id: 'c1',
    title: 'Revenue breakdown',
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
          <span>Checking Google Drive connection...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      {/* Left Panel - Project Sidebar */}
      <ProjectSidebar
        projects={projects}
        selectedProjectId={selectedProjectId}
        selectedChatId={selectedChatId}
        onSelectProject={setSelectedProjectId}
        onSelectChat={setSelectedChatId}
        onNewChat={handleNewChat}
        isDriveConnected={isConnected}
        isScanning={scanning}
        isDemoMode={!backendAvailable}
        connectionError={connectionError}
        onConnectDrive={connectDrive}
        onDisconnectDrive={disconnectDrive}
        onScanDrive={scanDrive}
        onRefreshProjects={refreshProjects}
        onOpenSettings={() => setShowSettings(true)}
        getProjectFiles={getProjectFiles}
      />

      {/* Center Panel - Chat */}
      <div className="flex-1 min-w-0">
        <ChatInterfaceV2
          projectName={selectedProject?.name}
          chatTitle={selectedChat?.title}
          onNewChat={handleNewChat}
        />
      </div>

      {/* Right Panel - Outcomes */}
      <OutcomesPanel />

      {/* New Chat Modal */}
      <AnimatePresence>
        {showNewChatModal && (
          <NewChatModal
            onClose={() => setShowNewChatModal(false)}
            onCreate={createNewChat}
          />
        )}
      </AnimatePresence>

      {/* Settings Modal */}
      <AnimatePresence>
        {showSettings && (
          <SettingsModal onClose={() => setShowSettings(false)} />
        )}
      </AnimatePresence>
    </div>
  );
}

function MobileLayout() {
  const [activeTab, setActiveTab] = useState<'projects' | 'chat' | 'outcomes' | 'settings'>('chat');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  
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
  } = useDrive();

  // Update selected project when projects load
  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  const selectedProject = projects.find(p => p.id === selectedProjectId);

  // Show loading state while checking Drive connection
  if (loading) {
    return (
      <div className="flex h-screen bg-white items-center justify-center">
        <div className="flex items-center gap-3 text-gray-500">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Checking Google Drive...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'projects' && (
          <MobileProjects
            projects={projects}
            selectedProjectId={selectedProjectId}
            selectedChatId={selectedChatId}
            onSelectProject={(id) => {
              setSelectedProjectId(id);
              setActiveTab('chat');
            }}
            onSelectChat={setSelectedChatId}
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
        {activeTab === 'settings' && <MobileSettings />}
      </div>

      {/* Bottom Navigation */}
      <MobileNav activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  );
}

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
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6"
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
              Create Chat
            </Button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}

function SettingsModal({ onClose }: { onClose: () => void }) {
  const { user, logout } = useAuth();

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
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] overflow-hidden"
      >
        <div className="h-14 border-b border-gray-200 flex items-center justify-between px-4">
          <h2 className="font-semibold text-gray-900">Settings</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>
        <div className="p-6 overflow-y-auto">
          <div className="space-y-6">
            {/* Profile Section */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Profile</h3>
              <div className="space-y-3">
                <div>
                  <label className="text-sm text-gray-600">Name</label>
                  <input
                    type="text"
                    defaultValue={user?.full_name || 'John Doe'}
                    className="w-full mt-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm text-gray-600">Email</label>
                  <input
                    type="email"
                    defaultValue={user?.email || 'john@example.com'}
                    className="w-full mt-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                  />
                </div>
              </div>
            </div>

            {/* Notifications */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Notifications</h3>
              <div className="space-y-2">
                {['Email notifications', 'Analysis complete alerts', 'New features'].map((item) => (
                  <label key={item} className="flex items-center justify-between py-2">
                    <span className="text-sm text-gray-700">{item}</span>
                    <input type="checkbox" defaultChecked className="w-4 h-4 rounded border-gray-300" />
                  </label>
                ))}
              </div>
            </div>

            {/* API Keys */}
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">API Keys</h3>
              <div className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between">
                  <code className="text-sm text-gray-600">sk_live_xxxxxxxxxxxx</code>
                  <Button variant="outline" size="sm">Copy</Button>
                </div>
              </div>
            </div>

            {/* Sign Out */}
            <div className="pt-4 border-t border-gray-200">
              <Button 
                variant="destructive" 
                className="w-full"
                onClick={() => {
                  logout();
                  onClose();
                }}
              >
                Sign Out
              </Button>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

function AppContent() {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 1024);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 1024);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            {isMobile ? <MobileLayout /> : <DesktopLayout />}
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

function App() {
  return <AppContent />;
}

export default App;
