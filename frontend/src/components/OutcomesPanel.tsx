import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  Eye,
  ListOrdered,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  CheckCircle,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

type TabType = 'reports' | 'previews' | 'steps';

interface OutcomeItem {
  id: string;
  title: string;
  type: 'report' | 'preview' | 'step';
  status?: 'pending' | 'running' | 'completed' | 'error';
  timestamp: Date;
  content?: string;
  expandable?: boolean;
}

const mockOutcomes: OutcomeItem[] = [
  {
    id: '1',
    title: 'Financial Analysis Report',
    type: 'report',
    status: 'completed',
    timestamp: new Date(Date.now() - 1000 * 60 * 5),
    content: 'Revenue increased by 15% compared to Q3. Operating expenses well-controlled. Net profit margin improved by 3.2%.',
    expandable: true,
  },
  {
    id: '2',
    title: 'Q4-Report.pdf',
    type: 'preview',
    status: 'completed',
    timestamp: new Date(Date.now() - 1000 * 60 * 10),
    expandable: false,
  },
  {
    id: '3',
    title: 'Extracting text from PDF',
    type: 'step',
    status: 'completed',
    timestamp: new Date(Date.now() - 1000 * 60 * 15),
    expandable: false,
  },
  {
    id: '4',
    title: 'Analyzing tables',
    type: 'step',
    status: 'running',
    timestamp: new Date(Date.now() - 1000 * 60 * 2),
    expandable: false,
  },
];

const tabs = [
  { id: 'reports' as TabType, label: 'Reports', icon: FileText },
  { id: 'previews' as TabType, label: 'Previews', icon: Eye },
  { id: 'steps' as TabType, label: 'Steps', icon: ListOrdered },
];

const statusIcons = {
  pending: Clock,
  running: Clock,
  completed: CheckCircle,
  error: AlertCircle,
};

const statusColors = {
  pending: 'text-gray-400',
  running: 'text-amber-500',
  completed: 'text-emerald-500',
  error: 'text-red-500',
};

export function OutcomesPanel() {
  const [activeTab, setActiveTab] = useState<TabType>('reports');
  const [expandedId, setExpandedId] = useState<string | null>('1');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const filteredOutcomes = mockOutcomes.filter((o) => {
    if (activeTab === 'reports') return o.type === 'report';
    if (activeTab === 'previews') return o.type === 'preview';
    if (activeTab === 'steps') return o.type === 'step';
    return true;
  });

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const handleCopy = async (content: string, id: string) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header Tabs */}
      <div className="h-12 border-b border-gray-100 flex items-center px-3">
        <div className="flex gap-1 bg-gray-100/70 p-1 rounded-lg w-full">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all flex-1',
                activeTab === tab.id
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              )}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="space-y-2"
          >
            {filteredOutcomes.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-2">
                  <FileText className="w-5 h-5 text-gray-400" />
                </div>
                <p className="text-sm text-gray-400">No {activeTab} yet</p>
              </div>
            ) : (
              filteredOutcomes.map((outcome) => {
                const StatusIcon = outcome.status ? statusIcons[outcome.status] : null;
                const isExpanded = expandedId === outcome.id;
                const isCopied = copiedId === outcome.id;

                return (
                  <motion.div
                    key={outcome.id}
                    layout
                    className="bg-gray-50 rounded-lg border border-gray-100 overflow-hidden"
                  >
                    {/* Header */}
                    <div
                      className={cn(
                        'flex items-center gap-2 p-2.5',
                        outcome.expandable && 'cursor-pointer hover:bg-gray-100'
                      )}
                      onClick={() =>
                        outcome.expandable && setExpandedId(isExpanded ? null : outcome.id)
                      }
                    >
                      {StatusIcon && outcome.status && (
                        <StatusIcon
                          className={cn(
                            'w-4 h-4 flex-shrink-0',
                            statusColors[outcome.status]
                          )}
                        />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-900 truncate">
                          {outcome.title}
                        </p>
                        <p className="text-xs text-gray-400">
                          {formatTime(outcome.timestamp)}
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-0.5">
                        {outcome.type === 'report' && outcome.status === 'completed' && outcome.content && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopy(outcome.content!, outcome.id);
                            }}
                            className="p-1.5 hover:bg-white rounded-md transition-colors"
                          >
                            {isCopied ? (
                              <Check className="w-3.5 h-3.5 text-emerald-500" />
                            ) : (
                              <Copy className="w-3.5 h-3.5 text-gray-400" />
                            )}
                          </button>
                        )}
                        {outcome.expandable && (
                          <button className="p-1.5 hover:bg-white rounded-md transition-colors">
                            {isExpanded ? (
                              <ChevronUp className="w-4 h-4 text-gray-400" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-gray-400" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Expanded Content */}
                    <AnimatePresence>
                      {isExpanded && outcome.content && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.15 }}
                          className="border-t border-gray-100"
                        >
                          <div className="p-3">
                            <p className="text-sm text-gray-600 leading-relaxed">
                              {outcome.content}
                            </p>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
