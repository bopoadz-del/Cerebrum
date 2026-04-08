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
  BarChart3,
  Calendar,
  TrendingUp,
  DollarSign,
  Users,
  Building2
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

type TabType = 'reports' | 'previews' | 'steps';

interface OutcomeItem {
  id: string;
  title: string;
  type: 'report' | 'preview' | 'step';
  status?: 'pending' | 'running' | 'completed' | 'error';
  timestamp: Date;
  content?: string;
  expandable?: boolean;
  data?: {
    label: string;
    value: string;
    change?: string;
  }[];
}

// High contrast mock data for construction/finance
const mockOutcomes: OutcomeItem[] = [
  {
    id: '1',
    title: 'Cost Analysis Report',
    type: 'report',
    status: 'completed',
    timestamp: new Date(Date.now() - 1000 * 60 * 5),
    content: 'Total project cost estimated at $2.4M based on RSMeans 2024 data. Material costs increased 8% from Q3. Labor rates stable in Riyadh region.',
    expandable: true,
    data: [
      { label: 'Materials', value: '$1,280,000', change: '+8%' },
      { label: 'Labor', value: '$720,000', change: '+2%' },
      { label: 'Equipment', value: '$280,000', change: '-3%' },
      { label: 'Overhead', value: '$120,000', change: '0%' },
    ]
  },
  {
    id: '2',
    title: 'Q4-Budget.xlsx',
    type: 'preview',
    status: 'completed',
    timestamp: new Date(Date.now() - 1000 * 60 * 10),
    expandable: false,
  },
  {
    id: '3',
    title: 'Parsing spreadsheet data',
    type: 'step',
    status: 'completed',
    timestamp: new Date(Date.now() - 1000 * 60 * 15),
    expandable: false,
  },
  {
    id: '4',
    title: 'Generating cost breakdown',
    type: 'step',
    status: 'running',
    timestamp: new Date(Date.now() - 1000 * 60 * 2),
    expandable: false,
  },
];

const tabs = [
  { id: 'reports' as TabType, label: 'Reports', icon: FileText },
  { id: 'previews' as TabType, label: 'Files', icon: Eye },
  { id: 'steps' as TabType, label: 'Activity', icon: ListOrdered },
];

const statusIcons = {
  pending: Clock,
  running: Clock,
  completed: CheckCircle,
  error: AlertCircle,
};

const statusColors = {
  pending: 'text-gray-600',
  running: 'text-amber-600',
  completed: 'text-emerald-600',
  error: 'text-red-600',
};

const statusBgColors = {
  pending: 'bg-gray-100',
  running: 'bg-amber-100',
  completed: 'bg-emerald-100',
  error: 'bg-red-100',
};

export function OutcomesTab() {
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
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-semibold text-gray-900">Outcomes</h2>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          Reports and analysis results
        </p>
      </div>

      {/* Tab Switcher - Large touch targets */}
      <div className="px-4 py-3 border-b border-gray-200">
        <div className="flex gap-2">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium text-base transition-all',
                  'min-h-[48px] touch-manipulation',
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                )}
                style={{ minHeight: '48px' }}
              >
                <tab.icon className="w-5 h-5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="space-y-4"
          >
            {filteredOutcomes.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mx-auto mb-4">
                  <FileText className="w-8 h-8 text-gray-400" />
                </div>
                <p className="text-lg text-gray-900 font-medium">No {activeTab} yet</p>
                <p className="text-base text-gray-500 mt-1">Results will appear here</p>
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
                    className="bg-white rounded-xl border-2 border-gray-200 overflow-hidden shadow-sm"
                  >
                    {/* Header - Large touch target */}
                    <div
                      onClick={() =>
                        outcome.expandable && setExpandedId(isExpanded ? null : outcome.id)
                      }
                      className={cn(
                        'flex items-center gap-3 p-4',
                        outcome.expandable && 'cursor-pointer active:bg-gray-50',
                        'min-h-[64px]'
                      )}
                      style={{ minHeight: '64px' }}
                    >
                      {StatusIcon && outcome.status && (
                        <div className={cn(
                          'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
                          statusBgColors[outcome.status]
                        )}>
                          <StatusIcon
                            className={cn(
                              'w-6 h-6',
                              statusColors[outcome.status]
                            )}
                          />
                        </div>
                      )}
                      
                      <div className="flex-1 min-w-0">
                        <p className="text-base font-semibold text-gray-900 truncate">
                          {outcome.title}
                        </p>
                        <p className="text-sm text-gray-500 mt-0.5">
                          {formatTime(outcome.timestamp)}
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {outcome.type === 'report' && outcome.status === 'completed' && outcome.content && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopy(outcome.content!, outcome.id);
                            }}
                            className="w-12 h-12 rounded-xl hover:bg-gray-100 flex-shrink-0"
                          >
                            {isCopied ? (
                              <Check className="w-6 h-6 text-emerald-600" />
                            ) : (
                              <Copy className="w-6 h-6 text-gray-400" />
                            )}
                          </Button>
                        )}
                        {outcome.expandable && (
                          <div className="w-12 h-12 rounded-xl bg-gray-100 flex items-center justify-center flex-shrink-0">
                            {isExpanded ? (
                              <ChevronUp className="w-6 h-6 text-gray-600" />
                            ) : (
                              <ChevronDown className="w-6 h-6 text-gray-600" />
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Expanded Content with High Contrast Table */}
                    <AnimatePresence>
                      {isExpanded && outcome.content && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="border-t-2 border-gray-200"
                        >
                          <div className="p-4">
                            {/* Summary Text */}
                            <p className="text-base text-gray-900 leading-relaxed mb-4">
                              {outcome.content}
                            </p>
                            
                            {/* High Contrast Data Table */}
                            {outcome.data && (
                              <div className="mt-4 rounded-xl border-2 border-gray-900 overflow-hidden">
                                <div className="bg-gray-900 text-white px-4 py-3">
                                  <div className="flex items-center gap-2">
                                    <DollarSign className="w-5 h-5" />
                                    <span className="text-lg font-bold">Cost Breakdown</span>
                                  </div>
                                </div>
                                <div className="divide-y divide-gray-300">
                                  {outcome.data.map((row, idx) => (
                                    <div 
                                      key={idx} 
                                      className={cn(
                                        'flex items-center justify-between px-4 py-4',
                                        idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                                      )}
                                    >
                                      <span className="text-lg font-semibold text-black">
                                        {row.label}
                                      </span>
                                      <div className="flex items-center gap-3">
                                        <span className="text-lg font-bold text-black">
                                          {row.value}
                                        </span>
                                        {row.change && (
                                          <span className={cn(
                                            'text-base font-bold px-2 py-1 rounded-lg',
                                            row.change.startsWith('+') 
                                              ? 'bg-red-100 text-red-700' 
                                              : row.change.startsWith('-')
                                              ? 'bg-emerald-100 text-emerald-700'
                                              : 'bg-gray-100 text-gray-700'
                                          )}>
                                            {row.change}
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  ))}
                                  <div className="flex items-center justify-between px-4 py-4 bg-gray-900">
                                    <span className="text-lg font-bold text-white">Total</span>
                                    <span className="text-xl font-bold text-white">$2,400,000</span>
                                  </div>
                                </div>
                              </div>
                            )}
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
