import React, { useState } from 'react';
import {
  Search,
  Filter,
  Grid,
  List,
  Star,
  Download,
  MoreVertical,
  Plus,
  Box,
  Cpu,
  Database,
  Cloud,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { SkeletonGrid } from '@/components/ui/SkeletonCard';
import { cn } from '@/lib/utils';

interface Service {
  id: string;
  name: string;
  description: string;
  category: string;
  version: string;
  rating: number;
  downloads: number;
  icon: React.ElementType;
  tags: string[];
  installed?: boolean;
}

const mockServices: Service[] = [
  {
    id: '1',
    name: 'Data Pipeline Engine',
    description: 'Automated ETL pipeline processing for construction data',
    category: 'Data Processing',
    version: '2.4.1',
    rating: 4.8,
    downloads: 1240,
    icon: Database,
    tags: ['ETL', 'Automation', 'Popular'],
    installed: true,
  },
  {
    id: '2',
    name: 'BIM Analyzer',
    description: 'Advanced BIM model analysis and validation tools',
    category: 'BIM',
    version: '1.8.0',
    rating: 4.6,
    downloads: 892,
    icon: Box,
    tags: ['BIM', 'Analysis', 'IFC'],
  },
  {
    id: '3',
    name: 'ML Model Trainer',
    description: 'Distributed machine learning model training service',
    category: 'Machine Learning',
    version: '3.1.2',
    rating: 4.9,
    downloads: 2156,
    icon: Cpu,
    tags: ['ML', 'Training', 'GPU'],
    installed: true,
  },
  {
    id: '4',
    name: 'Cloud Sync',
    description: 'Synchronize project data across cloud providers',
    category: 'Integration',
    version: '1.2.0',
    rating: 4.3,
    downloads: 567,
    icon: Cloud,
    tags: ['Cloud', 'Sync', 'AWS'],
  },
  {
    id: '5',
    name: 'Quality Inspector',
    description: 'Automated quality control and inspection tools',
    category: 'Quality',
    version: '2.0.5',
    rating: 4.5,
    downloads: 743,
    icon: Box,
    tags: ['QC', 'Inspection', 'Auto'],
  },
  {
    id: '6',
    name: 'Report Generator',
    description: 'Generate custom reports from project data',
    category: 'Reporting',
    version: '1.5.0',
    rating: 4.2,
    downloads: 432,
    icon: Database,
    tags: ['Reports', 'PDF', 'Excel'],
  },
];

const categories = ['All', 'Data Processing', 'BIM', 'Machine Learning', 'Integration', 'Quality', 'Reporting'];

const Registry: React.FC = () => {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [loading, setLoading] = useState(false);

  const filteredServices = mockServices.filter((service) => {
    const matchesSearch =
      service.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      service.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || service.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Service Registry
          </h1>
          <p className="text-gray-500 dark:text-gray-400">
            Discover and manage services for your projects
          </p>
        </div>
        <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors">
          <Plus size={18} />
          Add Service
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search services..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
          >
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
          <div className="flex items-center border border-gray-200 dark:border-gray-800 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                'p-2 transition-colors',
                viewMode === 'grid'
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                  : 'bg-white dark:bg-gray-900 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800'
              )}
            >
              <Grid size={18} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                'p-2 transition-colors',
                viewMode === 'list'
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                  : 'bg-white dark:bg-gray-900 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800'
              )}
            >
              <List size={18} />
            </button>
          </div>
        </div>
      </div>

      {/* Services Grid/List */}
      {loading ? (
        <SkeletonGrid count={6} columns={viewMode === 'grid' ? 3 : 1} />
      ) : (
        <div
          className={cn(
            viewMode === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
              : 'space-y-2'
          )}
        >
          {filteredServices.map((service) => (
            <ServiceCard
              key={service.id}
              service={service}
              viewMode={viewMode}
            />
          ))}
        </div>
      )}

      {filteredServices.length === 0 && !loading && (
        <div className="text-center py-12">
          <Box className="w-16 h-16 text-gray-300 dark:text-gray-700 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-1">
            No services found
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            Try adjusting your search or filters
          </p>
        </div>
      )}
    </div>
  );
};

const ServiceCard: React.FC<{ service: Service; viewMode: 'grid' | 'list' }> = ({
  service,
  viewMode,
}) => {
  const Icon = service.icon;

  if (viewMode === 'list') {
    return (
      <div className="flex items-center gap-4 p-4 bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 hover:border-blue-300 dark:hover:border-blue-700 transition-colors">
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <Icon size={24} className="text-blue-600 dark:text-blue-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {service.name}
            </h3>
            {service.installed && (
              <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-xs rounded-full">
                Installed
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
            {service.description}
          </p>
          <div className="flex items-center gap-4 mt-1 text-xs text-gray-500 dark:text-gray-400">
            <span>v{service.version}</span>
            <span className="flex items-center gap-1">
              <Star size={12} className="text-yellow-500" />
              {service.rating}
            </span>
            <span className="flex items-center gap-1">
              <Download size={12} />
              {service.downloads}
            </span>
          </div>
        </div>
        <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
          <MoreVertical size={18} className="text-gray-400" />
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-5 hover:border-blue-300 dark:hover:border-blue-700 transition-colors group">
      <div className="flex items-start justify-between mb-4">
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30 transition-colors">
          <Icon size={24} className="text-blue-600 dark:text-blue-400" />
        </div>
        <div className="flex items-center gap-1">
          {service.installed && (
            <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-xs rounded-full">
              Installed
            </span>
          )}
          <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
            <MoreVertical size={16} className="text-gray-400" />
          </button>
        </div>
      </div>

      <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
        {service.name}
      </h3>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">
        {service.description}
      </p>

      <div className="flex flex-wrap gap-1 mb-4">
        {service.tags.map((tag) => (
          <span
            key={tag}
            className="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-xs rounded"
          >
            {tag}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1">
            <Star size={14} className="text-yellow-500" />
            {service.rating}
          </span>
          <span className="flex items-center gap-1">
            <Download size={14} />
            {service.downloads}
          </span>
        </div>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          v{service.version}
        </span>
      </div>
    </div>
  );
};

export default Registry;
