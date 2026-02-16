import React, { useState } from 'react';
import {
  ClipboardCheck,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Plus,
  Search,
  Filter,
  Download,
  Calendar,
  User,
  MoreVertical,
  Clock,
  FileText,
  Image,
  BarChart3,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface Checklist {
  id: string;
  title: string;
  category: string;
  status: 'pending' | 'in-progress' | 'completed' | 'failed';
  totalItems: number;
  completedItems: number;
  assignedTo: string;
  dueDate: Date;
  lastUpdated: Date;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

interface InspectionItem {
  id: string;
  description: string;
  status: 'pass' | 'fail' | 'na' | 'pending';
  notes?: string;
  photos?: string[];
}

const mockChecklists: Checklist[] = [
  {
    id: '1',
    title: 'Foundation Inspection',
    category: 'Structural',
    status: 'completed',
    totalItems: 24,
    completedItems: 24,
    assignedTo: 'John Doe',
    dueDate: new Date(Date.now() + 1000 * 60 * 60 * 24 * 2),
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 2),
    priority: 'high',
  },
  {
    id: '2',
    title: 'Electrical System Check',
    category: 'MEP',
    status: 'in-progress',
    totalItems: 18,
    completedItems: 12,
    assignedTo: 'Jane Smith',
    dueDate: new Date(Date.now() + 1000 * 60 * 60 * 24),
    lastUpdated: new Date(Date.now() - 1000 * 60 * 30),
    priority: 'critical',
  },
  {
    id: '3',
    title: 'Fire Safety Inspection',
    category: 'Safety',
    status: 'pending',
    totalItems: 15,
    completedItems: 0,
    assignedTo: 'Bob Wilson',
    dueDate: new Date(Date.now() + 1000 * 60 * 60 * 24 * 3),
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 5),
    priority: 'high',
  },
  {
    id: '4',
    title: 'HVAC Commissioning',
    category: 'MEP',
    status: 'failed',
    totalItems: 20,
    completedItems: 16,
    assignedTo: 'Alice Brown',
    dueDate: new Date(Date.now() - 1000 * 60 * 60 * 24),
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 12),
    priority: 'medium',
  },
];

const Quality: React.FC = () => {
  const [checklists, setChecklists] = useState<Checklist[]>(mockChecklists);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedChecklist, setSelectedChecklist] = useState<Checklist | null>(null);

  const filteredChecklists = checklists.filter(
    (checklist) =>
      checklist.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      checklist.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const stats = {
    total: checklists.length,
    completed: checklists.filter((c) => c.status === 'completed').length,
    inProgress: checklists.filter((c) => c.status === 'in-progress').length,
    pending: checklists.filter((c) => c.status === 'pending').length,
    failed: checklists.filter((c) => c.status === 'failed').length,
  };

  const getStatusIcon = (status: Checklist['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'in-progress':
        return <Clock size={16} className="text-blue-500" />;
      case 'failed':
        return <XCircle size={16} className="text-red-500" />;
      default:
        return <AlertTriangle size={16} className="text-yellow-500" />;
    }
  };

  const getStatusColor = (status: Checklist['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400';
      case 'in-progress':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
      case 'failed':
        return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400';
      default:
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400';
    }
  };

  const getPriorityColor = (priority: Checklist['priority']) => {
    switch (priority) {
      case 'critical':
        return 'text-red-600 dark:text-red-400';
      case 'high':
        return 'text-orange-600 dark:text-orange-400';
      case 'medium':
        return 'text-yellow-600 dark:text-yellow-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Quality Control</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Manage inspection checklists and quality assurance
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium">
            <Plus size={18} />
            New Checklist
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: 'Total', value: stats.total },
          { label: 'Completed', value: stats.completed, color: 'green' },
          { label: 'In Progress', value: stats.inProgress, color: 'blue' },
          { label: 'Pending', value: stats.pending, color: 'yellow' },
          { label: 'Failed', value: stats.failed, color: 'red' },
        ].map((stat) => (
          <div
            key={stat.label}
            className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4"
          >
            <p className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search checklists..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800">
            <Filter size={18} />
            Filter
          </button>
          <button className="inline-flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800">
            <Download size={18} />
            Export
          </button>
        </div>
      </div>

      {/* Checklists Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredChecklists.map((checklist) => (
          <div
            key={checklist.id}
            onClick={() => setSelectedChecklist(checklist)}
            className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5 hover:border-blue-300 dark:hover:border-blue-700 transition-colors cursor-pointer"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <ClipboardCheck size={20} className="text-blue-600 dark:text-blue-400" />
              </div>
              <span
                className={cn(
                  'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full',
                  getStatusColor(checklist.status)
                )}
              >
                {getStatusIcon(checklist.status)}
                {checklist.status}
              </span>
            </div>

            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
              {checklist.title}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
              {checklist.category}
            </p>

            <div className="flex items-center gap-2 mb-4">
              <span className={cn('text-sm font-medium', getPriorityColor(checklist.priority))}>
                {checklist.priority}
              </span>
            </div>

            <div className="mb-4">
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-gray-600 dark:text-gray-400">
                  {checklist.completedItems}/{checklist.totalItems} items
                </span>
                <span className="text-gray-900 dark:text-white">
                  {Math.round((checklist.completedItems / checklist.totalItems) * 100)}%
                </span>
              </div>
              <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full transition-all',
                    checklist.status === 'completed' && 'bg-green-500',
                    checklist.status === 'in-progress' && 'bg-blue-500',
                    checklist.status === 'failed' && 'bg-red-500',
                    checklist.status === 'pending' && 'bg-yellow-500'
                  )}
                  style={{
                    width: `${(checklist.completedItems / checklist.totalItems) * 100}%`,
                  }}
                />
              </div>
            </div>

            <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
              <div className="flex items-center gap-1">
                <User size={14} />
                {checklist.assignedTo}
              </div>
              <div className="flex items-center gap-1">
                <Calendar size={14} />
                {checklist.dueDate.toLocaleDateString()}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Checklist Detail Modal */}
      {selectedChecklist && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-auto">
            <div className="p-6 border-b border-gray-200 dark:border-gray-800">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    {selectedChecklist.title}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {selectedChecklist.category} · {selectedChecklist.id}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedChecklist(null)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Status</p>
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full mt-1',
                      getStatusColor(selectedChecklist.status)
                    )}
                  >
                    {getStatusIcon(selectedChecklist.status)}
                    {selectedChecklist.status}
                  </span>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Priority</p>
                  <p className={cn('font-medium', getPriorityColor(selectedChecklist.priority))}>
                    {selectedChecklist.priority}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Assigned To</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {selectedChecklist.assignedTo}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Due Date</p>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {selectedChecklist.dueDate.toLocaleDateString()}
                  </p>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Inspection Items
                </h4>
                <div className="space-y-2">
                  {Array.from({ length: selectedChecklist.totalItems }).map((_, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg"
                    >
                      <div
                        className={cn(
                          'w-5 h-5 rounded border flex items-center justify-center',
                          i < selectedChecklist.completedItems
                            ? 'bg-green-500 border-green-500'
                            : 'border-gray-300 dark:border-gray-600'
                        )}
                      >
                        {i < selectedChecklist.completedItems && (
                          <CheckCircle size={14} className="text-white" />
                        )}
                      </div>
                      <span className="flex-1 text-sm text-gray-700 dark:text-gray-300">
                        Inspection item {i + 1}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="p-6 border-t border-gray-200 dark:border-gray-800 flex gap-2">
              <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg">
                <ClipboardCheck size={18} />
                Start Inspection
              </button>
              <button className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800">
                <FileText size={18} />
                View Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Quality;
