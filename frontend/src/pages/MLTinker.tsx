import React, { useState } from 'react';
import {
  Play,
  Pause,
  Save,
  Download,
  Upload,
  Settings,
  BarChart3,
  Layers,
  Cpu,
  Database,
  Target,
  Zap,
  ChevronRight,
  ChevronDown,
  Plus,
  Trash2,
  MoreVertical,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface ModelConfig {
  id: string;
  name: string;
  type: 'classification' | 'regression' | 'clustering' | 'detection';
  algorithm: string;
  parameters: Record<string, number | string | boolean>;
  status: 'draft' | 'training' | 'completed' | 'failed';
}

interface Dataset {
  id: string;
  name: string;
  rows: number;
  columns: number;
  size: string;
  lastUpdated: Date;
}

const mockModels: ModelConfig[] = [
  {
    id: '1',
    name: 'Defect Detection CNN',
    type: 'detection',
    algorithm: 'YOLOv8',
    parameters: {
      epochs: 100,
      batchSize: 16,
      learningRate: 0.001,
      imageSize: 640,
    },
    status: 'completed',
  },
  {
    id: '2',
    name: 'Cost Estimator',
    type: 'regression',
    algorithm: 'XGBoost',
    parameters: {
      maxDepth: 6,
      learningRate: 0.1,
      nEstimators: 200,
    },
    status: 'training',
  },
  {
    id: '3',
    name: 'Safety Classifier',
    type: 'classification',
    algorithm: 'ResNet50',
    parameters: {
      epochs: 50,
      batchSize: 32,
      learningRate: 0.0001,
    },
    status: 'draft',
  },
];

const mockDatasets: Dataset[] = [
  {
    id: '1',
    name: 'construction_defects_v2.csv',
    rows: 15000,
    columns: 24,
    size: '2.4 GB',
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 24),
  },
  {
    id: '2',
    name: 'cost_data_2024.xlsx',
    rows: 8500,
    columns: 18,
    size: '45 MB',
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 48),
  },
  {
    id: '3',
    name: 'safety_images.zip',
    rows: 25000,
    columns: 1,
    size: '12.8 GB',
    lastUpdated: new Date(Date.now() - 1000 * 60 * 60 * 12),
  },
];

const MLTinker: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'models' | 'datasets' | 'training'>('models');
  const [selectedModel, setSelectedModel] = useState<ModelConfig | null>(null);
  const [showNewModelModal, setShowNewModelModal] = useState(false);

  const getStatusColor = (status: ModelConfig['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400';
      case 'training':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400';
      case 'failed':
        return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    }
  };

  const getTypeIcon = (type: ModelConfig['type']) => {
    switch (type) {
      case 'classification':
        return <Target size={18} className="text-purple-500" />;
      case 'regression':
        return <BarChart3 size={18} className="text-blue-500" />;
      case 'clustering':
        return <Layers size={18} className="text-green-500" />;
      case 'detection':
        return <Zap size={18} className="text-orange-500" />;
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">ML Tinker</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Build and train custom machine learning models
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowNewModelModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
          >
            <Plus size={18} />
            New Model
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-800">
        <div className="flex gap-6">
          {[
            { id: 'models', label: 'Models', icon: Cpu },
            { id: 'datasets', label: 'Datasets', icon: Database },
            { id: 'training', label: 'Training Jobs', icon: Play },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={cn(
                'flex items-center gap-2 pb-3 text-sm font-medium border-b-2 transition-colors',
                activeTab === tab.id
                  ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {activeTab === 'models' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mockModels.map((model) => (
            <div
              key={model.id}
              onClick={() => setSelectedModel(model)}
              className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5 hover:border-blue-300 dark:hover:border-blue-700 transition-colors cursor-pointer"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                  {getTypeIcon(model.type)}
                </div>
                <span
                  className={cn(
                    'px-2 py-1 text-xs rounded-full',
                    getStatusColor(model.status)
                  )}
                >
                  {model.status}
                </span>
              </div>

              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                {model.name}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                {model.algorithm}
              </p>

              <div className="flex flex-wrap gap-1 mb-4">
                <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs rounded">
                  {model.type}
                </span>
              </div>

              <div className="pt-4 border-t border-gray-100 dark:border-gray-800">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Parameters</p>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(model.parameters).slice(0, 4).map(([key, value]) => (
                    <div key={key} className="text-xs">
                      <span className="text-gray-400">{key}:</span>{' '}
                      <span className="text-gray-700 dark:text-gray-300">{value}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2 mt-4">
                <button className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg">
                  <Play size={14} />
                  Train
                </button>
                <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
                  <Settings size={16} className="text-gray-500" />
                </button>
                <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
                  <MoreVertical size={16} className="text-gray-500" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'datasets' && (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Datasets</h2>
            <button className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg">
              <Upload size={16} />
              Upload
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Name
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Rows
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Columns
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Size
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Last Updated
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {mockDatasets.map((dataset) => (
                  <tr key={dataset.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Database size={18} className="text-blue-500" />
                        <span className="text-sm font-medium text-gray-900 dark:text-white">
                          {dataset.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600 dark:text-gray-400">
                      {dataset.rows.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600 dark:text-gray-400">
                      {dataset.columns}
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-gray-600 dark:text-gray-400">
                      {dataset.size}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                      {dataset.lastUpdated.toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                          <Download size={16} className="text-gray-400" />
                        </button>
                        <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                          <Trash2 size={16} className="text-gray-400" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'training' && (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-8 text-center">
          <Cpu className="w-16 h-16 text-gray-300 dark:text-gray-700 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No Active Training Jobs
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Start training a model to see jobs here
          </p>
          <button
            onClick={() => setActiveTab('models')}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
          >
            Go to Models
          </button>
        </div>
      )}

      {/* New Model Modal */}
      {showNewModelModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-lg w-full p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Create New Model
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Model Name
                </label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg"
                  placeholder="e.g., Defect Detection v2"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Type
                  </label>
                  <select className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg">
                    <option>Classification</option>
                    <option>Regression</option>
                    <option>Clustering</option>
                    <option>Object Detection</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Algorithm
                  </label>
                  <select className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg">
                    <option>YOLOv8</option>
                    <option>ResNet50</option>
                    <option>XGBoost</option>
                    <option>Random Forest</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowNewModelModal(false)}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => setShowNewModelModal(false)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
              >
                Create Model
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MLTinker;
