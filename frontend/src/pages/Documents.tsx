import React, { useState } from 'react';
import {
  Search,
  Folder,
  FileText,
  Image,
  FileSpreadsheet,
  MoreVertical,
  Download,
  Share2,
  Trash2,
  Upload,
  Grid,
  List,
  ChevronRight,
  Plus,
  Filter,
  Clock,
  User,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface Document {
  id: string;
  name: string;
  type: 'folder' | 'pdf' | 'image' | 'spreadsheet' | 'document' | 'dwg';
  size?: string;
  modifiedAt: Date;
  modifiedBy: string;
  thumbnail?: string;
}

const mockDocuments: Document[] = [
  {
    id: '1',
    name: 'Project Documents',
    type: 'folder',
    modifiedAt: new Date(Date.now() - 1000 * 60 * 60 * 24),
    modifiedBy: 'John Doe',
  },
  {
    id: '2',
    name: 'BIM Models',
    type: 'folder',
    modifiedAt: new Date(Date.now() - 1000 * 60 * 60 * 48),
    modifiedBy: 'Jane Smith',
  },
  {
    id: '3',
    name: 'Building_Plan_v2.dwg',
    type: 'dwg',
    size: '45.2 MB',
    modifiedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
    modifiedBy: 'Bob Wilson',
  },
  {
    id: '4',
    name: 'Cost_Estimate_Q3.xlsx',
    type: 'spreadsheet',
    size: '1.8 MB',
    modifiedAt: new Date(Date.now() - 1000 * 60 * 60 * 4),
    modifiedBy: 'Alice Brown',
  },
  {
    id: '5',
    name: 'Safety_Inspection_Report.pdf',
    type: 'pdf',
    size: '3.2 MB',
    modifiedAt: new Date(Date.now() - 1000 * 60 * 60 * 24),
    modifiedBy: 'John Doe',
  },
  {
    id: '6',
    name: 'Site_Photo_001.jpg',
    type: 'image',
    size: '5.6 MB',
    modifiedAt: new Date(Date.now() - 1000 * 60 * 60 * 6),
    modifiedBy: 'Jane Smith',
  },
  {
    id: '7',
    name: 'Meeting_Notes_Oct15.docx',
    type: 'document',
    size: '245 KB',
    modifiedAt: new Date(Date.now() - 1000 * 60 * 60 * 12),
    modifiedBy: 'Bob Wilson',
  },
];

const getFileIcon = (type: Document['type']) => {
  switch (type) {
    case 'folder':
      return <Folder size={40} className="text-yellow-500" />;
    case 'pdf':
      return <FileText size={40} className="text-red-500" />;
    case 'image':
      return <Image size={40} className="text-purple-500" />;
    case 'spreadsheet':
      return <FileSpreadsheet size={40} className="text-green-500" />;
    case 'dwg':
      return <FileText size={40} className="text-blue-500" />;
    default:
      return <FileText size={40} className="text-gray-500" />;
  }
};

const Documents: React.FC = () => {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());

  const filteredDocs = mockDocuments.filter((doc) =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const toggleSelection = (id: string) => {
    setSelectedDocs((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const formatDate = (date: Date): string => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    if (hours < 48) return 'Yesterday';
    return date.toLocaleDateString();
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <Breadcrumb className="mb-2" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Documents</h1>
          <p className="text-gray-500 dark:text-gray-400">
            Manage project files and documents
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium">
            <Upload size={18} />
            Upload
          </button>
          <button className="inline-flex items-center gap-2 px-4 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-800">
            <Plus size={18} />
            New Folder
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search documents..."
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

      {/* Selection Actions */}
      {selectedDocs.size > 0 && (
        <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <span className="text-sm text-blue-700 dark:text-blue-400">
            {selectedDocs.size} selected
          </span>
          <div className="flex-1" />
          <button className="p-2 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded">
            <Download size={18} className="text-blue-600 dark:text-blue-400" />
          </button>
          <button className="p-2 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded">
            <Share2 size={18} className="text-blue-600 dark:text-blue-400" />
          </button>
          <button className="p-2 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded">
            <Trash2 size={18} className="text-blue-600 dark:text-blue-400" />
          </button>
        </div>
      )}

      {/* Documents Grid/List */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {filteredDocs.map((doc) => (
            <div
              key={doc.id}
              onClick={() => toggleSelection(doc.id)}
              className={cn(
                'group relative p-4 rounded-lg border transition-all cursor-pointer',
                selectedDocs.has(doc.id)
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-blue-300 dark:hover:border-blue-700'
              )}
            >
              <div className="flex flex-col items-center text-center">
                <div className="mb-3">{getFileIcon(doc.type)}</div>
                <p className="text-sm font-medium text-gray-900 dark:text-white line-clamp-2">
                  {doc.name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {doc.size || 'Folder'} · {formatDate(doc.modifiedAt)}
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                }}
                className="absolute top-2 right-2 p-1 opacity-0 group-hover:opacity-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
              >
                <MoreVertical size={16} className="text-gray-400" />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-800/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Name
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Modified
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Size
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {filteredDocs.map((doc) => (
                <tr
                  key={doc.id}
                  onClick={() => toggleSelection(doc.id)}
                  className={cn(
                    'hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors cursor-pointer',
                    selectedDocs.has(doc.id) && 'bg-blue-50 dark:bg-blue-900/20'
                  )}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {getFileIcon(doc.type)}
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {doc.name}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                      <Clock size={14} />
                      {formatDate(doc.modifiedAt)}
                      <span className="text-gray-400">by {doc.modifiedBy}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {doc.size || '--'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                        <Download size={16} className="text-gray-400" />
                      </button>
                      <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                        <Share2 size={16} className="text-gray-400" />
                      </button>
                      <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                        <MoreVertical size={16} className="text-gray-400" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default Documents;
