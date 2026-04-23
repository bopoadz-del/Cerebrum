import { useState, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PanelLeft,
  PanelRight,
  Plus,
  MessageSquare,
  Loader2,
  X,
  LogOut,
  Brain,
  ChevronRight,
  Folder,
  HardDrive,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { useGoogleDrive } from '@/hooks/useGoogleDrive';
import { ProjectSidebar } from '@/components/ProjectSidebar';
import { ChatInterfaceV2 } from '@/components/ChatInterfaceV2';
import { AgentChatInterface } from '@/components/AgentChatInterface';
import { OutcomesPanel } from '@/components/OutcomesPanel';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/context/AuthContext';
import Login from '@/pages/Login';
import ImagePage from '@/pages/ImagePage';
import { useProjects } from "@/hooks/useProjects";
import { MobileLayout } from '@/components/mobile';
import { cn } from '@/lib/utils';

// Protected Route - AUTH DISABLED
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

// Kimi-style Layout
function DesktopLayout() {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>('1');
  const [selectedChatId, setSelectedChatId] = useState<string | null>('c1');
  const [showSettings, setShowSettings] = useState(false);
  const [showNewChatModal, setShowNewChatModal] = useState(false);
  const [agentMode, setAgentMode] = useState(false);
  
  // Panel visibility states
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(false);
  
  const {
    projects,
    scanning,
    loading,
    backendAvailable,
    connectionError,
    indexingStatus,
    scanResults,
    refreshProjects,
    getProjectFiles
  } = useProjects();
  
  const selectedProject = projects.find(p => p.id === selectedProjectId) || projects[0];

  const handleNewChat = () => {
    setShowNewChatModal(true);
  };

  const createNewChat = (title: string) => {
    console.log('Creating new chat:', title);
    setShowNewChatModal(false);
  };

  if (loading) {
    return (
      <div className="flex bg-[#f9f9f9] items-center justify-center" style={{ minHeight: '100dvh', height: '100dvh' }}>
        <div className="flex items-center gap-3 text-gray-500">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex bg-[#f9f9f9] overflow-hidden" style={{ minHeight: '100dvh', height: '100dvh' }}>
      {/* Left Sidebar - Collapsible */}
      <AnimatePresence initial={false}>
        {leftPanelOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="flex-shrink-0 border-r border-gray-200 bg-white flex flex-col"
          >
            <ProjectSidebar
              projects={projects}
              selectedProjectId={selectedProjectId}
              selectedChatId={selectedChatId}
              onSelectProject={setSelectedProjectId}
              onSelectChat={setSelectedChatId}
              onNewChat={handleNewChat}
              isScanning={scanning}
              isDemoMode={!backendAvailable}
              connectionError={connectionError}
              indexingStatus={indexingStatus}
              scanResults={scanResults}
              onRefreshProjects={refreshProjects}
              onOpenSettings={() => setShowSettings(true)}
              getProjectFiles={getProjectFiles}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navigation Bar */}
        <header className="h-14 border-b border-gray-200 bg-white flex items-center justify-between px-4 flex-shrink-0">
          {/* Left controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setLeftPanelOpen(!leftPanelOpen)}
              className={cn(
                "p-2 rounded-lg transition-colors",
                leftPanelOpen ? "bg-gray-100 text-gray-700" : "hover:bg-gray-100 text-gray-500"
              )}
              title={leftPanelOpen ? "Close sidebar" : "Open sidebar"}
            >
              <PanelLeft className="w-5 h-5" />
            </button>
            
            {selectedProject && (
              <div className="flex items-center gap-2 ml-2">
                <Folder className="w-4 h-4 text-gray-400" />
                <span className="text-sm text-gray-600 truncate max-w-[150px]">
                  {selectedProject.name}
                </span>
                <ChevronRight className="w-4 h-4 text-gray-300" />
                <span className="text-sm font-medium text-gray-900">New Chat</span>
              </div>
            )}
          </div>

          {/* Center - Mode Toggle */}
          <div className="flex items-center gap-3">
            <span className={`text-sm ${!agentMode ? 'text-gray-900 font-medium' : 'text-gray-400'}`}>
              Standard
            </span>
            <button
              onClick={() => setAgentMode(!agentMode)}
              className={cn(
                "relative w-11 h-6 rounded-full transition-colors duration-200",
                agentMode ? 'bg-indigo-600' : 'bg-gray-300'
              )}
            >
              <span
                className={cn(
                  "absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform duration-200",
                  agentMode ? 'translate-x-5' : 'translate-x-0'
                )}
              />
            </button>
            <span className={cn(
              "text-sm flex items-center gap-1.5",
              agentMode ? 'text-gray-900 font-medium' : 'text-gray-400'
            )}>
              <Brain className="w-4 h-4" />
              Agent
            </span>
          </div>

          {/* Right controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setRightPanelOpen(!rightPanelOpen)}
              className={cn(
                "p-2 rounded-lg transition-colors",
                rightPanelOpen ? "bg-gray-100 text-gray-700" : "hover:bg-gray-100 text-gray-500"
              )}
              title={rightPanelOpen ? "Close outcomes" : "Open outcomes"}
            >
              <PanelRight className="w-5 h-5" />
            </button>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={handleNewChat}
              className="ml-2 gap-1.5"
            >
              <Plus className="w-4 h-4" />
              New Chat
            </Button>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-hidden">
          {agentMode ? (
            <AgentChatInterface
              projectName={selectedProject?.name}
              chatTitle="New Chat"
              onNewChat={handleNewChat}
            />
          ) : (
            <ChatInterfaceV2
              projectName={selectedProject?.name}
              chatTitle="New Chat"
              onNewChat={handleNewChat}
              onSwitchToAgent={() => setAgentMode(true)}
            />
          )}
        </div>
      </div>

      {/* Right Panel - Outcomes - Collapsible */}
      <AnimatePresence initial={false}>
        {rightPanelOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 320, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="flex-shrink-0 border-l border-gray-200 bg-white"
          >
            <OutcomesPanel />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Modals */}
      <AnimatePresence>
        {showNewChatModal && (
          <NewChatModal
            onClose={() => setShowNewChatModal(false)}
            onCreate={createNewChat}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showSettings && (
          <SettingsModal onClose={() => setShowSettings(false)} />
        )}
      </AnimatePresence>
    </div>
  );
}

// Simplified New Chat Modal
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
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

// Google Drive connector panel
function GoogleDrivePanel() {
  const { status, loading, error, connect, disconnect } = useGoogleDrive();

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 p-3 border border-gray-200 rounded-xl">
        <div className="w-9 h-9 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
          <HardDrive className="w-5 h-5 text-blue-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium text-gray-900">Google Drive</p>
            {status?.connected ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <AlertCircle className="w-4 h-4 text-gray-400" />
            )}
          </div>
          {status?.connected ? (
            <p className="text-xs text-gray-500 truncate">{status.account_email || 'Connected'}</p>
          ) : (
            <p className="text-xs text-gray-400">Not connected</p>
          )}
        </div>
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
        ) : status?.connected ? (
          <Button
            size="sm"
            variant="outline"
            className="text-red-600 border-red-200 hover:bg-red-50 text-xs h-7 px-2"
            onClick={disconnect}
          >
            Disconnect
          </Button>
        ) : (
          <Button
            size="sm"
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs h-7 px-2"
            onClick={connect}
          >
            Connect
          </Button>
        )}
      </div>
      {error && (
        <p className="text-xs text-red-500 px-1">{error}</p>
      )}
      {status?.connected && status.last_sync && (
        <p className="text-xs text-gray-400 px-1">
          Last sync: {new Date(status.last_sync).toLocaleString()}
        </p>
      )}
    </div>
  );
}

// Simplified Settings Modal
function SettingsModal({ onClose }: { onClose: () => void }) {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'profile' | 'connectors'>('profile');

  const handleLogin = () => {
    onClose();
    navigate('/login');
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6"
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-gray-900">Settings</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-5 h-5" />
          </Button>
        </div>

        {isAuthenticated ? (
          <>
            {/* Tab bar */}
            <div className="flex gap-1 mb-5 bg-gray-100 rounded-lg p-1">
              {(['profile', 'connectors'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    'flex-1 py-1.5 text-sm font-medium rounded-md transition-colors capitalize',
                    activeTab === tab
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-500 hover:text-gray-700'
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>

            {activeTab === 'profile' && (
              <div className="space-y-4">
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-gray-500 uppercase tracking-wide">Name</label>
                    <input
                      type="text"
                      defaultValue={user?.full_name || 'John Doe'}
                      className="w-full mt-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 uppercase tracking-wide">Email</label>
                    <input
                      type="email"
                      defaultValue={user?.email || 'john@example.com'}
                      className="w-full mt-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                    />
                  </div>
                </div>
                <div className="pt-3 border-t border-gray-200">
                  <Button
                    variant="destructive"
                    className="w-full"
                    onClick={() => { logout(); onClose(); }}
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Sign Out
                  </Button>
                </div>
              </div>
            )}

            {activeTab === 'connectors' && (
              <div className="space-y-3">
                <p className="text-xs text-gray-500 mb-3">
                  Connect external services to import files and data into your projects.
                </p>
                <GoogleDrivePanel />
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-4">
            <p className="text-gray-600 mb-4">Sign in to access your account and upload files</p>
            <Button
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
              onClick={handleLogin}
            >
              Sign In / Register
            </Button>
          </div>
        )}
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
    <div style={{ minHeight: '100dvh' }} className="flex flex-col">
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/image" element={<ImagePage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              {isMobile ? <MobileLayout /> : <DesktopLayout />}
            </ProtectedRoute>
          }
        />
      </Routes>
    </div>
  );
}

function App() {
  return <AppContent />;
}

export default App;
