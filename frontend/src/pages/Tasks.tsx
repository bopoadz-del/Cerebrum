import React, { useState } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  CheckCircle,
  XCircle,
  Clock,
  MoreVertical,
  Filter,
  Search,
  BarChart3,
  AlertTriangle,
  Cpu,
  MemoryStick,
  HardDrive,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface Task {
  id: string;
  name: string;
  type: 'training' | 'inference' | 'data-processing' | 'pipeline';
  status: 'queued' | 'running' | 'completed' | 'failed' | 'paused';
  progress: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  estimatedDuration?: number;
  worker?: string;
  resourceUsage: {
    cpu: number;
    memory: number;
    gpu?: number;
  };
}

const mockTasks: Task[] = [
  {
    id: 'task-1',
    name: 'Model Training - Defect Detection',
    type: 'training',
    status: 'running',
    progress: 67,
    priority: 'high',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
    startedAt: new Date(Date.now() - 1000 * 60 * 60),
    estimatedDuration: 7200,
    worker: 'gpu-worker-1',
    resourceUsage: { cpu: 85, memory: 72, gpu: 91 },
  },
  {
    id: 'task-2',
    name: 'Data Pipeline - BIM Processing',
    type: 'data-processing',
    status: 'queued',
    progress: 0,
    priority: 'medium',
    createdAt: new Date(Date.now() - 1000 * 60 * 30),
    resourceUsage: { cpu: 0, memory: 0 },
  },
  {
    id: 'task-3',
    name: 'Inference Batch - Safety Check',
    type: 'inference',
    status: 'completed',
    progress: 100,
    priority: 'low',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 3),
    startedAt: new Date(Date.now() - 1000 * 60 * 60 * 3),
    completedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
    resourceUsage: { cpu: 45, memory: 38 },
  },
  {
    id: 'task-4',
    name: 'Pipeline - Cost Estimation',
    type: 'pipeline',
    status: 'failed',
    progress: 45,
    priority: 'critical',
    createdAt: new Date(Date.now() - 1000 * 60 * 45),
    startedAt: new Date(Date.now() - 1000 * 60 * 40),
    resourceUsage: { cpu: 0, memory: 0 },
  },
  {
    id: 'task-5',
    name: 'Model Training - Quality Classifier',
    type: 'training',
    status: 'paused',
    progress: 23,
    priority: 'medium',
    createdAt: new Date(Date.now() - 1000 * 60 * 90),
    startedAt: new Date(Date.now() - 1000 * 60 * 60),
    resourceUsage: { cpu: 0, memory: 15 },
  },
];

const Tasks: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>(mockTasks);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  const filteredTasks = tasks.filter((task) => {
    const matchesSearch = task.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'all' || task.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const stats = {
    total: tasks.length,
    running: tasks.filter((t) => t.status === 'running').length,
    queued: tasks.filter((t) => t.status === 'queued').length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    failed: tasks.filter((t) => t.status === 'failed').length,
  };

  const getStatusIcon = (status: Task['status']) => {
    switch (status) {
      case 'running':
        return <Play size={16} className="text-blue-500" />;
      case 'completed':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'failed':
        return <XCircle size={16} className="text-red-500" />;
      case 'paused':
        return <Pause size={16} className="text-yellow-500" />;
      default:
        return <Clock size={16} className="text-gray-500" />;
    }
  };

  const getStatusColor = (status: Task['status']) => {
    switch (status) {
      case 'running':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
      case 'completed':
        return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400';
      case 'failed':
        return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400';
      case 'paused':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  const getPriorityColor = (priority: Task['priority']) => {
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

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Task Queue</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Monitor and manage background tasks
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium">
            <Play size={18} />
            Resume All
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: 'Total', value: stats.total, color: 'blue' },
          { label: 'Running', value: stats.running, color: 'green' },
          { label: 'Queued', value: stats.queued, color: 'gray' },
          { label: 'Completed', value: stats.completed, color: 'blue' },
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
            placeholder="Search tasks..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
        >
          <option value="all">All Status</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="paused">Paused</option>
        </select>
      </div>

      {/* Tasks List */}
      <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-800/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Task
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Progress
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Priority
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Resources
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {filteredTasks.map((task) => (
                <tr
                  key={task.id}
                  className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {task.name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {task.type} · {task.worker || 'Unassigned'}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full',
                        getStatusColor(task.status)
                      )}
                    >
                      {getStatusIcon(task.status)}
                      {task.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="w-32">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-gray-600 dark:text-gray-400">
                          {task.progress}%
                        </span>
                        {task.estimatedDuration && task.status === 'running' && (
                          <span className="text-gray-500">
                            ~{formatDuration(task.estimatedDuration * (1 - task.progress / 100))}
                          </span>
                        )}
                      </div>
                      <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-full transition-all duration-500',
                            task.status === 'running' && 'bg-blue-500',
                            task.status === 'completed' && 'bg-green-500',
                            task.status === 'failed' && 'bg-red-500',
                            task.status === 'paused' && 'bg-yellow-500'
                          )}
                          style={{ width: `${task.progress}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn('text-sm font-medium', getPriorityColor(task.priority))}>
                      {task.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                      {task.resourceUsage.cpu > 0 && (
                        <span className="flex items-center gap-1">
                          <Cpu size={12} />
                          {task.resourceUsage.cpu}%
                        </span>
                      )}
                      {task.resourceUsage.memory > 0 && (
                        <span className="flex items-center gap-1">
                          <MemoryStick size={12} />
                          {task.resourceUsage.memory}%
                        </span>
                      )}
                      {task.resourceUsage.gpu !== undefined && task.resourceUsage.gpu > 0 && (
                        <span className="flex items-center gap-1">
                          <HardDrive size={12} />
                          GPU {task.resourceUsage.gpu}%
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {task.status === 'running' && (
                        <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                          <Pause size={16} className="text-gray-500" />
                        </button>
                      )}
                      {task.status === 'paused' && (
                        <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                          <Play size={16} className="text-gray-500" />
                        </button>
                      )}
                      {(task.status === 'failed' || task.status === 'paused') && (
                        <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                          <RotateCcw size={16} className="text-gray-500" />
                        </button>
                      )}
                      <button
                        onClick={() => setSelectedTask(task)}
                        className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                      >
                        <BarChart3 size={16} className="text-gray-500" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Task Detail Modal */}
      {selectedTask && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-2xl w-full">
            <div className="p-6 border-b border-gray-200 dark:border-gray-800">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    {selectedTask.name}
                  </h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {selectedTask.id} · {selectedTask.type}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedTask(null)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
                >
                  <XCircle size={20} className="text-gray-500" />
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
                      getStatusColor(selectedTask.status)
                    )}
                  >
                    {getStatusIcon(selectedTask.status)}
                    {selectedTask.status}
                  </span>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Priority</p>
                  <p className={cn('font-medium', getPriorityColor(selectedTask.priority))}>
                    {selectedTask.priority}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Created</p>
                  <p className="text-sm text-gray-900 dark:text-white">
                    {selectedTask.createdAt.toLocaleString()}
                  </p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Worker</p>
                  <p className="text-sm text-gray-900 dark:text-white">
                    {selectedTask.worker || 'Unassigned'}
                  </p>
                </div>
              </div>

              {/* Resource Usage */}
              <div>
                <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                  Resource Usage
                </h4>
                <div className="space-y-2">
                  {selectedTask.resourceUsage.cpu > 0 && (
                    <ResourceBar label="CPU" value={selectedTask.resourceUsage.cpu} color="blue" />
                  )}
                  {selectedTask.resourceUsage.memory > 0 && (
                    <ResourceBar
                      label="Memory"
                      value={selectedTask.resourceUsage.memory}
                      color="purple"
                    />
                  )}
                  {selectedTask.resourceUsage.gpu !== undefined &&
                    selectedTask.resourceUsage.gpu > 0 && (
                      <ResourceBar
                        label="GPU"
                        value={selectedTask.resourceUsage.gpu}
                        color="orange"
                      />
                    )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const ResourceBar: React.FC<{ label: string; value: number; color: string }> = ({
  label,
  value,
  color,
}) => {
  const colors: Record<string, string> = {
    blue: 'bg-blue-500',
    purple: 'bg-purple-500',
    orange: 'bg-orange-500',
    green: 'bg-green-500',
    red: 'bg-red-500',
  };

  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        <span className="text-gray-900 dark:text-white">{value}%</span>
      </div>
      <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div className={cn('h-full transition-all', colors[color])} style={{ width: `${value}%` }} />
      </div>
    </div>
  );
};

export default Tasks;
