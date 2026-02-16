import React, { useState } from 'react';
import {
  FileText,
  Plus,
  Search,
  Filter,
  Download,
  Upload,
  MoreVertical,
  CheckCircle,
  Clock,
  AlertCircle,
  Wifi,
  WifiOff,
  MapPin,
  Calendar,
  User,
  Edit2,
  Trash2,
  Save,
  X,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface Form {
  id: string;
  title: string;
  description: string;
  status: 'draft' | 'submitted' | 'synced' | 'pending';
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
  location?: string;
  responses: number;
  isOffline: boolean;
}

const mockForms: Form[] = [
  {
    id: '1',
    title: 'Daily Safety Inspection',
    description: 'Checklist for daily site safety inspection',
    status: 'synced',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7),
    updatedAt: new Date(Date.now() - 1000 * 60 * 30),
    createdBy: 'John Doe',
    location: 'Building A',
    responses: 45,
    isOffline: false,
  },
  {
    id: '2',
    title: 'Quality Control Check',
    description: 'Material quality verification form',
    status: 'pending',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
    createdBy: 'Jane Smith',
    location: 'Building B',
    responses: 12,
    isOffline: true,
  },
  {
    id: '3',
    title: 'Equipment Inspection',
    description: 'Weekly equipment maintenance checklist',
    status: 'draft',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60),
    createdBy: 'Bob Wilson',
    responses: 0,
    isOffline: false,
  },
  {
    id: '4',
    title: 'Incident Report',
    description: 'Report workplace incidents and near-misses',
    status: 'submitted',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 5),
    updatedAt: new Date(Date.now() - 1000 * 60 * 10),
    createdBy: 'Alice Brown',
    location: 'Site Office',
    responses: 3,
    isOffline: false,
  },
];

const FieldData: React.FC = () => {
  const [forms, setForms] = useState<Form[]>(mockForms);
  const [searchQuery, setSearchQuery] = useState('');
  const [showNewFormModal, setShowNewFormModal] = useState(false);
  const [editingForm, setEditingForm] = useState<Form | null>(null);

  const filteredForms = forms.filter(
    (form) =>
      form.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      form.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getStatusIcon = (status: Form['status']) => {
    switch (status) {
      case 'synced':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'submitted':
        return <Upload size={16} className="text-blue-500" />;
      case 'pending':
        return <Clock size={16} className="text-yellow-500" />;
      default:
        return <Edit2 size={16} className="text-gray-500" />;
    }
  };

  const getStatusColor = (status: Form['status']) => {
    switch (status) {
      case 'synced':
        return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400';
      case 'submitted':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
      case 'pending':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Field Data</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Create and manage offline-capable forms
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowNewFormModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
          >
            <Plus size={18} />
            New Form
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Forms', value: forms.length },
          { label: 'Synced', value: forms.filter((f) => f.status === 'synced').length },
          { label: 'Pending', value: forms.filter((f) => f.status === 'pending').length },
          { label: 'Drafts', value: forms.filter((f) => f.status === 'draft').length },
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
            placeholder="Search forms..."
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

      {/* Forms Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredForms.map((form) => (
          <div
            key={form.id}
            className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5 hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <FileText size={20} className="text-blue-600 dark:text-blue-400" />
              </div>
              <div className="flex items-center gap-2">
                {form.isOffline ? (
                  <WifiOff size={16} className="text-gray-400" title="Offline mode" />
                ) : (
                  <Wifi size={16} className="text-green-500" title="Online" />
                )}
                <button
                  onClick={() => setEditingForm(form)}
                  className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                >
                  <MoreVertical size={16} className="text-gray-400" />
                </button>
              </div>
            </div>

            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">{form.title}</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 line-clamp-2">
              {form.description}
            </p>

            <div className="flex items-center gap-2 mb-4">
              <span
                className={cn(
                  'inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full',
                  getStatusColor(form.status)
                )}
              >
                {getStatusIcon(form.status)}
                {form.status}
              </span>
            </div>

            <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 mb-4">
              <div className="flex items-center gap-1">
                <User size={14} />
                {form.createdBy}
              </div>
              <div className="flex items-center gap-1">
                <Calendar size={14} />
                {form.updatedAt.toLocaleDateString()}
              </div>
            </div>

            {form.location && (
              <div className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 mb-4">
                <MapPin size={14} />
                {form.location}
              </div>
            )}

            <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {form.responses} responses
              </span>
              <button className="text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400">
                View Details
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* New Form Modal */}
      {showNewFormModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-lg w-full p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Create New Form
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Form Title
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg"
                  placeholder="e.g., Daily Inspection"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg resize-none"
                  rows={3}
                  placeholder="Describe the purpose of this form"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Location (Optional)
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg"
                  placeholder="e.g., Building A"
                />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="offline" className="w-4 h-4 rounded" />
                <label htmlFor="offline" className="text-sm text-gray-700 dark:text-gray-300">
                  Enable offline mode
                </label>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowNewFormModal(false)}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => setShowNewFormModal(false)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
              >
                Create Form
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FieldData;
