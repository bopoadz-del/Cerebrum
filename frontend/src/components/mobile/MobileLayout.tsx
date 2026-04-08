import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Plus, 
  Brain,
  Loader2,
  Folder,
  MessageSquare,
  FileText
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useProjects } from '@/hooks/useProjects';
import { ChatInterfaceV2 } from '@/components/ChatInterfaceV2';
import { AgentChatInterface } from '@/components/AgentChatInterface';
import { OutcomesPanel } from '@/components/OutcomesPanel';
import { ProjectSidebar } from '@/components/ProjectSidebar';

type MobileTab = 'chat' | 'projects' | 'outcomes';

export function MobileLayout() {
  const [activeTab, setActiveTab] = useState<MobileTab>('chat');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [agentMode, setAgentMode] = useState(false);

  const {
    projects,
    scanning,
    loading,
    backendAvailable,
    connectionError,
    indexingStatus,
    scanResults,
    refreshProjects,
    getProjectFiles,
  } = useProjects();

  const initialized = useRef(false);

  // Auto-select first project when loaded - use layout effect to avoid re-renders
  useEffect(() => {
    if (initialized.current) return;
    if (projects.length > 0 && !selectedProjectId) {
      initialized.current = true;
      // Use setTimeout to move state update outside of render cycle
      const timeoutId = setTimeout(() => {
        setSelectedProjectId(projects[0].id);
      }, 0);
      return () => clearTimeout(timeoutId);
    }
  }, [projects, selectedProjectId]);

  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  const handleSelectProject = (projectId: string) => {
    setSelectedProjectId(projectId);
    setActiveTab('chat');
  };

  const handleNewChat = () => {
    // TODO: Implement new chat modal or navigation
    console.log('New chat requested');
  };

  if (loading) {
    return (
      <div className="flex h-screen bg-white items-center justify-center">
        <div className="flex items-center gap-3 text-gray-500">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Header */}
      <header className="h-14 border-b border-gray-200 flex items-center justify-between px-4 bg-white shrink-0 safe-area-top">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <span className="text-white font-semibold text-sm">C</span>
          </div>
          <span className="font-semibold text-gray-900">Cerebrum</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAgentMode(!agentMode)}
            className={cn(
              'flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
              agentMode
                ? 'bg-indigo-100 text-indigo-700'
                : 'bg-gray-100 text-gray-600'
            )}
          >
            <Brain className="w-4 h-4" />
            {agentMode ? 'Agent' : 'Chat'}
          </button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleNewChat}
            className="h-11 w-11"
          >
            <Plus className="w-5 h-5" />
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden relative">
        <AnimatePresence mode="wait">
          {activeTab === 'chat' && (
            <motion.div
              key="chat"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="h-full"
            >
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
            </motion.div>
          )}

          {activeTab === 'projects' && (
            <motion.div
              key="projects"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="h-full overflow-y-auto"
            >
              <ProjectSidebar
                projects={projects}
                selectedProjectId={selectedProjectId}
                selectedChatId={selectedChatId}
                onSelectProject={handleSelectProject}
                onSelectChat={setSelectedChatId}
                onNewChat={handleNewChat}
                isScanning={scanning}
                isDemoMode={!backendAvailable}
                connectionError={connectionError}
                indexingStatus={indexingStatus}
                scanResults={scanResults}
                onRefreshProjects={refreshProjects}
                onOpenSettings={() => {
                  // TODO: Implement settings
                  console.log('Settings opened');
                }}
                getProjectFiles={getProjectFiles}
              />
            </motion.div>
          )}

          {activeTab === 'outcomes' && (
            <motion.div
              key="outcomes"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="h-full"
            >
              <OutcomesPanel />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom Navigation */}
      <nav className="h-16 border-t border-gray-200 bg-white shrink-0 safe-area-bottom">
        <div className="flex items-center justify-around h-full">
          <NavButton
            active={activeTab === 'projects'}
            onClick={() => setActiveTab('projects')}
            icon={Folder}
            label="Projects"
          />
          <NavButton
            active={activeTab === 'chat'}
            onClick={() => setActiveTab('chat')}
            icon={MessageSquare}
            label="Chat"
            isMain
          />
          <NavButton
            active={activeTab === 'outcomes'}
            onClick={() => setActiveTab('outcomes')}
            icon={FileText}
            label="Outcomes"
          />
        </div>
      </nav>
    </div>
  );
}

interface NavButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  isMain?: boolean;
}

function NavButton({ active, onClick, icon: Icon, label, isMain }: NavButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex flex-col items-center justify-center gap-1 flex-1 h-full transition-colors',
        active ? 'text-indigo-600' : 'text-gray-400 hover:text-gray-600'
      )}
    >
      <div
        className={cn(
          'flex items-center justify-center rounded-xl transition-all',
          isMain
            ? active
              ? 'w-12 h-12 bg-indigo-600 text-white'
              : 'w-12 h-12 bg-gray-100 text-gray-600'
            : 'w-11 h-11'
        )}
      >
        <Icon className={cn('transition-all', isMain ? 'w-6 h-6' : 'w-5 h-5')} />
      </div>
      <span className="text-xs font-medium">{label}</span>
    </button>
  );
}
