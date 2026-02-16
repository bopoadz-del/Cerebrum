import React, { useState } from 'react';
import {
  Search,
  Plus,
  Filter,
  MoreVertical,
  GitBranch,
  Clock,
  CheckCircle,
  XCircle,
  Play,
  Pause,
  BarChart3,
  Settings,
  Download,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface Model {
  id: string;
  name: string;
  description: string;
  version: string;
  status: 'training' | 'completed' | 'failed' | 'idle';
  accuracy?: number;
  loss?: number;
  createdAt: Date;
  updatedAt: Date;
  framework: string;
  tags: string[];
}

interface Experiment {
  id: string;
  name: string;
  modelId: string;
  status: 'running' | 'completed' | 'failed';
  metrics: {
    accuracy: number;
    loss: number;
    epoch: number;
    totalEpochs: number;
  };
  startedAt: Date;
  duration?: number;
}

const mockModels: Model[] = [
  {
    id: '1',
    name: 'Defect Detection CNN',
    description: 'Convolutional neural network for construction defect detection',
    version: '1.2.0',
    status: 'training',
    accuracy: 0.87,
    loss: 0.23,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 7),
    updatedAt: new Date(),
    framework: 'PyTorch',
    tags: ['CNN', 'Vision', 'Defect Detection'],
  },
  {
    id: '2',
    name: 'Cost Estimator LSTM',
    description: 'LSTM model for project cost estimation',
    version: '2.0.1',
    status: 'completed',
    accuracy: 0.92,
    loss: 0.15,
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 14),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
    framework: 'TensorFlow',
    tags: ['LSTM', 'Time Series', 'Cost'],
  },
  {
    id: '3',
    name: 'Safety Classifier',
    description: 'Image classification for safety compliance',
    version: '1.0.5',
    status: 'idle',
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3),
    framework: 'PyTorch',
    tags: ['Classification', 'Safety', 'Vision'],
  },
];

const mockExperiments: Experiment[] = [
  {
    id: 'exp-1',
    name: 'Training Run #42',
    modelId: '1',
    status: 'running',
    metrics: {
      accuracy: 0.87,
      loss: 0.23,
      epoch: 45,
      totalEpochs: 100,
    },
    startedAt: new Date(Date.now() - 1000 * 60 * 30),
  },
  {
    id: 'exp-2',
    name: 'Hyperparameter Tuning',
    modelId: '2',
    status: 'completed',
    metrics: {
      accuracy: 0.92,
      loss: 0.15,
      epoch: 50,
      totalEpochs: 50,
    },
    startedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
    duration: 7200,
  },
];

const Learning: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'models' | 'experiments'>('models');
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Model Registry
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Manage ML models and track experiments
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
            <Plus size={18} />
            New Model
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-800">
        <div className="flex gap-6">
          {[
            { id: 'models', label: 'Models', count: mockModels.length },
            { id: 'experiments', label: 'Experiments', count: mockExperiments.length },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={cn(
                'pb-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              {tab.label}
              <span className="ml-2 px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs rounded-full">
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder={`Search ${activeTab}...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <button className="inline-flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800">
          <Filter size={18} />
          Filter
        </button>
      </div>

      {/* Content */}
      {activeTab === 'models' ? (
        <ModelsList models={mockModels} searchQuery={searchQuery} />
      ) : (
        <ExperimentsList experiments={mockExperiments} searchQuery={searchQuery} />
      )}
    </div>
  );
};

const ModelsList: React.FC<{ models: Model[]; searchQuery: string }> = ({
  models,
  searchQuery,
}) => {
  const filtered = models.filter(
    (m) =>
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {filtered.map((model) => (
        <ModelCard key={model.id} model={model} />
      ))}
    </div>
  );
};

const ModelCard: React.FC<{ model: Model }> = ({ model }) => {
  const getStatusIcon = () => {
    switch (model.status) {
      case 'training':
        return <Play size={16} className="text-blue-500" />;
      case 'completed':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'failed':
        return <XCircle size={16} className="text-red-500" />;
      default:
        return <Pause size={16} className="text-gray-500" />;
    }
  };

  const getStatusColor = () => {
    switch (model.status) {
      case 'training':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
      case 'completed':
        return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400';
      case 'failed':
        return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
            <GitBranch size={20} className="text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">{model.name}</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">{model.framework}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn('px-2 py-1 text-xs rounded-full flex items-center gap-1', getStatusColor())}>
            {getStatusIcon()}
            {model.status}
          </span>
          <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
            <MoreVertical size={16} className="text-gray-400" />
          </button>
        </div>
      </div>

      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">{model.description}</p>

      <div className="flex flex-wrap gap-1 mb-4">
        {model.tags.map((tag) => (
          <span
            key={tag}
            className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs rounded"
          >
            {tag}
          </span>
        ))}
      </div>

      {model.accuracy !== undefined && (
        <div className="grid grid-cols-2 gap-4 mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Accuracy</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {(model.accuracy * 100).toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400">Loss</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {model.loss?.toFixed(4)}
            </p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1">
            <Clock size={12} />
            Updated {model.updatedAt.toLocaleDateString()}
          </span>
          <span>v{model.version}</span>
        </div>
        <div className="flex items-center gap-1">
          <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg" title="Metrics">
            <BarChart3 size={16} className="text-gray-400" />
          </button>
          <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg" title="Settings">
            <Settings size={16} className="text-gray-400" />
          </button>
          <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg" title="Download">
            <Download size={16} className="text-gray-400" />
          </button>
        </div>
      </div>
    </div>
  );
};

const ExperimentsList: React.FC<{ experiments: Experiment[]; searchQuery: string }> = ({
  experiments,
  searchQuery,
}) => {
  const filtered = experiments.filter((e) =>
    e.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-3">
      {filtered.map((exp) => (
        <ExperimentRow key={exp.id} experiment={exp} />
      ))}
    </div>
  );
};

const ExperimentRow: React.FC<{ experiment: Experiment }> = ({ experiment }) => {
  const progress = (experiment.metrics.epoch / experiment.metrics.totalEpochs) * 100;

  const getStatusColor = () => {
    switch (experiment.status) {
      case 'running':
        return 'text-blue-600 dark:text-blue-400';
      case 'completed':
        return 'text-green-600 dark:text-green-400';
      case 'failed':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4">
      <div className="flex items-center gap-4">
        <div className={cn('p-2 rounded-lg bg-gray-100 dark:bg-gray-800', getStatusColor())}>
          {experiment.status === 'running' ? (
            <Play size={18} />
          ) : experiment.status === 'completed' ? (
            <CheckCircle size={18} />
          ) : (
            <XCircle size={18} />
          )}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-gray-900 dark:text-white">{experiment.name}</h4>
            <span className={cn('text-xs', getStatusColor())}>{experiment.status}</span>
          </div>
          <div className="mt-2">
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
              <span>
                Epoch {experiment.metrics.epoch}/{experiment.metrics.totalEpochs}
              </span>
              <span>{progress.toFixed(0)}%</span>
            </div>
            <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full transition-all duration-500',
                  experiment.status === 'running' ? 'bg-blue-500' : 'bg-green-500'
                )}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {(experiment.metrics.accuracy * 100).toFixed(1)}%
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">Accuracy</p>
        </div>
        <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
          <MoreVertical size={16} className="text-gray-400" />
        </button>
      </div>
    </div>
  );
};

export default Learning;
