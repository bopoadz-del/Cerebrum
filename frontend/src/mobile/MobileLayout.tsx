import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Folder, 
  MessageSquare, 
  BarChart3,
  Brain,
  Menu,
  Settings
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ProjectsTab } from './ProjectsTab';
import { ChatTab } from './ChatTab';
import { OutcomesTab } from './OutcomesTab';
import { useProjects } from '@/hooks/useProjects';
import { useChat } from '@/hooks/useChat';

type TabId = 'projects' | 'chat' | 'outcomes';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ElementType;
}

const TABS: Tab[] = [
  { id: 'projects', label: 'Projects', icon: Folder },
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'outcomes', label: 'Outcomes', icon: BarChart3 },
];

export function MobileLayout() {
  const [activeTab, setActiveTab] = useState<TabId>('chat');
  const [showSettings, setShowSettings] = useState(false);
  const [isKeyboardOpen, setIsKeyboardOpen] = useState(false);
  
  const {
    projects,
    scanning,
    loading,
    backendAvailable,
    indexingStatus,
    scanResults,
    refreshProjects,
  } = useProjects();
  
  const {
    attachments,
    addAttachment,
    removeAttachment,
    isUploading,
  } = useChat();

  const selectedProject = projects[0];

  // Handle keyboard detection for Android
  useEffect(() => {
    const handleResize = () => {
      // Detect if keyboard is likely open (viewport shrunk significantly)
      const viewportHeight = window.visualViewport?.height || window.innerHeight;
      const windowHeight = window.innerHeight;
      const keyboardOpen = windowHeight - viewportHeight > 150;
      setIsKeyboardOpen(keyboardOpen);
    };

    window.visualViewport?.addEventListener('resize', handleResize);
    window.addEventListener('resize', handleResize);
    
    return () => {
      window.visualViewport?.removeEventListener('resize', handleResize);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const renderTabContent = () => {
    switch (activeTab) {
      case 'projects':
        return (
          <ProjectsTab
            projectName={selectedProject?.name}
            onAttachFile={addAttachment}
            attachments={attachments}
            onRemoveAttachment={removeAttachment}
            isUploading={isUploading}
          />
        );
      case 'chat':
        return <ChatTab projectName={selectedProject?.name} />;
      case 'outcomes':
        return <OutcomesTab />;
      default:
        return <ChatTab projectName={selectedProject?.name} />;
    }
  };

  return (
    <div 
      className="flex flex-col bg-white"
      style={{ 
        minHeight: '100dvh', // Dynamic viewport height - fixes Android keyboard overlap
        height: '100dvh'
      }}
    >
      {/* Top Header */}
      <header className="flex-shrink-0 px-4 py-3 bg-white border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-bold text-gray-900">Cerebrum</span>
        </div>
        
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center active:bg-gray-200 transition-colors"
        >
          <Settings className="w-5 h-5 text-gray-600" />
        </button>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="h-full"
          >
            {renderTabContent()}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Bottom Tab Bar - Hidden when keyboard is open */}
      <AnimatePresence>
        {!isKeyboardOpen && (
          <motion.nav
            initial={{ y: 100 }}
            animate={{ y: 0 }}
            exit={{ y: 100 }}
            transition={{ duration: 0.2 }}
            className="flex-shrink-0 bg-white border-t border-gray-200 px-2 pb-safe"
            style={{ paddingBottom: 'env(safe-area-inset-bottom, 8px)' }}
          >
            <div className="flex items-center justify-around py-2">
              {TABS.map((tab) => {
                const isActive = activeTab === tab.id;
                const Icon = tab.icon;
                
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                      'flex flex-col items-center justify-center gap-1 px-4 py-2 rounded-xl transition-all duration-200',
                      'min-w-[80px] min-h-[56px] touch-manipulation',
                      isActive 
                        ? 'text-indigo-600 bg-indigo-50' 
                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                    )}
                    style={{ minHeight: '56px', minWidth: '80px' }}
                  >
                    <Icon className={cn(
                      'w-6 h-6 transition-transform',
                      isActive && 'scale-110'
                    )} />
                    <span className={cn(
                      'text-sm font-medium',
                      isActive && 'font-semibold'
                    )}>
                      {tab.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </motion.nav>
        )}
      </AnimatePresence>

      {/* Settings Overlay */}
      <AnimatePresence>
        {showSettings && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 z-40"
              onClick={() => setShowSettings(false)}
            />
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed bottom-0 left-0 right-0 bg-white rounded-t-3xl z-50 max-h-[80vh] overflow-y-auto"
            >
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-bold text-gray-900">Settings</h2>
                  <button
                    onClick={() => setShowSettings(false)}
                    className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center"
                  >
                    <span className="text-gray-500">✕</span>
                  </button>
                </div>
                
                <div className="space-y-4">
                  <div className="p-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center">
                        <Brain className="w-6 h-6 text-indigo-600" />
                      </div>
                      <div>
                        <p className="font-semibold text-gray-900">Cerebrum AI</p>
                        <p className="text-sm text-gray-500">Version 1.0.0</p>
                      </div>
                    </div>
                  </div>
                  
                  <button className="w-full p-4 bg-gray-50 rounded-xl flex items-center justify-between active:bg-gray-100 transition-colors">
                    <span className="font-medium text-gray-900">Account</span>
                    <span className="text-gray-400">→</span>
                  </button>
                  
                  <button className="w-full p-4 bg-gray-50 rounded-xl flex items-center justify-between active:bg-gray-100 transition-colors">
                    <span className="font-medium text-gray-900">Help & Support</span>
                    <span className="text-gray-400">→</span>
                  </button>
                  
                  {backendAvailable ? (
                    <div className="p-4 bg-emerald-50 rounded-xl flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full bg-emerald-500" />
                      <span className="text-emerald-700 font-medium">Backend Connected</span>
                    </div>
                  ) : (
                    <div className="p-4 bg-amber-50 rounded-xl flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full bg-amber-500" />
                      <span className="text-amber-700 font-medium">Demo Mode</span>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
