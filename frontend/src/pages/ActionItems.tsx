import React, { useState } from 'react';
import {
  Plus,
  MoreHorizontal,
  Calendar,
  User,
  Tag,
  Clock,
  AlertCircle,
  CheckCircle2,
  Circle,
  ArrowRight,
  Filter,
  Search,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

type ColumnId = 'todo' | 'in-progress' | 'review' | 'done';

interface Task {
  id: string;
  title: string;
  description: string;
  column: ColumnId;
  priority: 'low' | 'medium' | 'high' | 'critical';
  assignee?: {
    name: string;
    avatar?: string;
  };
  dueDate?: Date;
  tags: string[];
  createdAt: Date;
}

interface Column {
  id: ColumnId;
  title: string;
  color: string;
}

const columns: Column[] = [
  { id: 'todo', title: 'To Do', color: 'bg-gray-100 dark:bg-gray-800' },
  { id: 'in-progress', title: 'In Progress', color: 'bg-blue-50 dark:bg-blue-900/20' },
  { id: 'review', title: 'Review', color: 'bg-yellow-50 dark:bg-yellow-900/20' },
  { id: 'done', title: 'Done', color: 'bg-green-50 dark:bg-green-900/20' },
];

const mockTasks: Task[] = [
  {
    id: '1',
    title: 'Review BIM Model v2',
    description: 'Check structural integrity and clash detection',
    column: 'todo',
    priority: 'high',
    assignee: { name: 'John Doe' },
    dueDate: new Date(Date.now() + 1000 * 60 * 60 * 24 * 2),
    tags: ['BIM', 'Review'],
    createdAt: new Date(),
  },
  {
    id: '2',
    title: 'Update Cost Estimates',
    description: 'Recalculate based on new material prices',
    column: 'in-progress',
    priority: 'medium',
    assignee: { name: 'Jane Smith' },
    dueDate: new Date(Date.now() + 1000 * 60 * 60 * 24 * 5),
    tags: ['Cost', 'Finance'],
    createdAt: new Date(),
  },
  {
    id: '3',
    title: 'Safety Inspection',
    description: 'Weekly site safety check',
    column: 'review',
    priority: 'critical',
    assignee: { name: 'Bob Wilson' },
    dueDate: new Date(Date.now() + 1000 * 60 * 60 * 24),
    tags: ['Safety', 'Compliance'],
    createdAt: new Date(),
  },
  {
    id: '4',
    title: 'Submit Permit Application',
    description: 'Building permit for phase 2',
    column: 'done',
    priority: 'high',
    assignee: { name: 'Alice Brown' },
    tags: ['Permits', 'Legal'],
    createdAt: new Date(),
  },
  {
    id: '5',
    title: 'Schedule Subcontractor Meeting',
    description: 'Coordinate with electrical contractor',
    column: 'todo',
    priority: 'low',
    tags: ['Meeting', 'Coordination'],
    createdAt: new Date(),
  },
];

const ActionItems: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>(mockTasks);
  const [searchQuery, setSearchQuery] = useState('');
  const [draggedTask, setDraggedTask] = useState<Task | null>(null);
  const [showNewTaskModal, setShowNewTaskModal] = useState(false);

  const filteredTasks = tasks.filter(
    (task) =>
      task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      task.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getTasksByColumn = (columnId: ColumnId) =>
    filteredTasks.filter((task) => task.column === columnId);

  const handleDragStart = (task: Task) => {
    setDraggedTask(task);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, columnId: ColumnId) => {
    e.preventDefault();
    if (draggedTask) {
      setTasks((prev) =>
        prev.map((t) => (t.id === draggedTask.id ? { ...t, column: columnId } : t))
      );
      setDraggedTask(null);
    }
  };

  const getPriorityColor = (priority: Task['priority']) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400';
      case 'high':
        return 'bg-orange-100 text-orange-700 dark:bg-orange-900/20 dark:text-orange-400';
      case 'medium':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  const formatDueDate = (date: Date): string => {
    const days = Math.ceil((date.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (days < 0) return 'Overdue';
    if (days === 0) return 'Today';
    if (days === 1) return 'Tomorrow';
    return `${days} days`;
  };

  return (
    <div className="p-6 space-y-6 h-[calc(100vh-4rem)] flex flex-col">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Action Items</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Track and manage project tasks
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
            />
          </div>
          <button
            onClick={() => setShowNewTaskModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
          >
            <Plus size={18} />
            New Task
          </button>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto">
        <div className="flex gap-4 min-w-max h-full">
          {columns.map((column) => (
            <div
              key={column.id}
              className={cn(
                'w-80 flex flex-col rounded-lg',
                column.color
              )}
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, column.id)}
            >
              {/* Column Header */}
              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    {column.title}
                  </h3>
                  <span className="px-2 py-0.5 bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs rounded-full">
                    {getTasksByColumn(column.id).length}
                  </span>
                </div>
                <button className="p-1 hover:bg-white/50 dark:hover:bg-gray-700/50 rounded">
                  <MoreHorizontal size={16} className="text-gray-500" />
                </button>
              </div>

              {/* Tasks */}
              <div className="flex-1 p-2 space-y-2 overflow-y-auto">
                {getTasksByColumn(column.id).map((task) => (
                  <TaskCard
                    key={task.id}
                    task={task}
                    onDragStart={() => handleDragStart(task)}
                    priorityColor={getPriorityColor(task.priority)}
                    formatDueDate={formatDueDate}
                  />
                ))}
              </div>

              {/* Add Task Button */}
              <button className="flex items-center gap-2 p-3 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 transition-colors">
                <Plus size={16} />
                Add task
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* New Task Modal */}
      {showNewTaskModal && (
        <NewTaskModal onClose={() => setShowNewTaskModal(false)} />
      )}
    </div>
  );
};

interface TaskCardProps {
  task: Task;
  onDragStart: () => void;
  priorityColor: string;
  formatDueDate: (date: Date) => string;
}

const TaskCard: React.FC<TaskCardProps> = ({
  task,
  onDragStart,
  priorityColor,
  formatDueDate,
}) => {
  return (
    <div
      draggable
      onDragStart={onDragStart}
      className="bg-white dark:bg-gray-900 rounded-lg p-3 shadow-sm border border-gray-200 dark:border-gray-800 cursor-move hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between mb-2">
        <span className={cn('px-2 py-0.5 text-xs rounded-full', priorityColor)}>
          {task.priority}
        </span>
        <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
          <MoreHorizontal size={14} className="text-gray-400" />
        </button>
      </div>

      <h4 className="font-medium text-gray-900 dark:text-white mb-1">{task.title}</h4>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">
        {task.description}
      </p>

      <div className="flex flex-wrap gap-1 mb-3">
        {task.tags.map((tag) => (
          <span
            key={tag}
            className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs rounded"
          >
            {tag}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {task.assignee ? (
            <div className="flex items-center gap-1">
              <div className="w-6 h-6 bg-blue-100 dark:bg-blue-900/20 rounded-full flex items-center justify-center">
                <User size={12} className="text-blue-600 dark:text-blue-400" />
              </div>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {task.assignee.name.split(' ')[0]}
              </span>
            </div>
          ) : (
            <span className="text-xs text-gray-400">Unassigned</span>
          )}
        </div>

        {task.dueDate && (
          <div
            className={cn(
              'flex items-center gap-1 text-xs',
              task.dueDate < new Date() ? 'text-red-500' : 'text-gray-500 dark:text-gray-400'
            )}
          >
            <Clock size={12} />
            {formatDueDate(task.dueDate)}
          </div>
        )}
      </div>
    </div>
  );
};

const NewTaskModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-md w-full p-6">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          New Task
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Title
            </label>
            <input
              type="text"
              className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg"
              placeholder="Enter task title"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg resize-none"
              rows={3}
              placeholder="Enter task description"
            />
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Priority
              </label>
              <select className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg">
                <option>Low</option>
                <option>Medium</option>
                <option>High</option>
                <option>Critical</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Due Date
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg"
              />
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
          >
            Create Task
          </button>
        </div>
      </div>
    </div>
  );
};

export default ActionItems;
