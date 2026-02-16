import React, { useState, useRef, useCallback } from 'react';
import {
  Play,
  Square,
  Save,
  Download,
  Upload,
  Plus,
  Trash2,
  Copy,
  MoreVertical,
  ChevronRight,
  ChevronDown,
  Terminal,
  Code,
  FileCode,
  Settings,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface Cell {
  id: string;
  type: 'code' | 'markdown' | 'raw';
  content: string;
  output?: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  executionCount?: number;
}

interface Notebook {
  id: string;
  name: string;
  cells: Cell[];
  kernel: string;
  createdAt: Date;
  updatedAt: Date;
}

const mockNotebook: Notebook = {
  id: 'nb-1',
  name: 'Untitled-1.ipynb',
  kernel: 'python3',
  cells: [
    {
      id: 'cell-1',
      type: 'markdown',
      content: '# Data Analysis Notebook\n\nThis notebook demonstrates data processing capabilities.',
      status: 'completed',
    },
    {
      id: 'cell-2',
      type: 'code',
      content: `import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load sample data
data = pd.DataFrame({
    'x': np.random.randn(100),
    'y': np.random.randn(100)
})

print(f"Data shape: {data.shape}")
data.head()`,
      status: 'completed',
      executionCount: 1,
      output: `Data shape: (100, 2)
          x         y
0  0.234521 -0.876234
1 -0.654321  0.345678
2  1.234567 -0.987654`,
    },
    {
      id: 'cell-3',
      type: 'code',
      content: `# Visualize data
plt.figure(figsize=(10, 6))
plt.scatter(data['x'], data['y'], alpha=0.6)
plt.xlabel('X')
plt.ylabel('Y')
plt.title('Sample Scatter Plot')
plt.show()`,
      status: 'idle',
    },
  ],
  createdAt: new Date(),
  updatedAt: new Date(),
};

const Sandbox: React.FC = () => {
  const [notebook, setNotebook] = useState<Notebook>(mockNotebook);
  const [activeCell, setActiveCell] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const addCell = useCallback((type: Cell['type'], index?: number) => {
    const newCell: Cell = {
      id: `cell-${Date.now()}`,
      type,
      content: '',
      status: 'idle',
    };

    setNotebook((prev) => {
      const cells = [...prev.cells];
      const insertIndex = index !== undefined ? index + 1 : cells.length;
      cells.splice(insertIndex, 0, newCell);
      return { ...prev, cells, updatedAt: new Date() };
    });

    setActiveCell(newCell.id);
  }, []);

  const deleteCell = useCallback((cellId: string) => {
    setNotebook((prev) => ({
      ...prev,
      cells: prev.cells.filter((c) => c.id !== cellId),
      updatedAt: new Date(),
    }));
  }, []);

  const updateCell = useCallback((cellId: string, updates: Partial<Cell>) => {
    setNotebook((prev) => ({
      ...prev,
      cells: prev.cells.map((c) => (c.id === cellId ? { ...c, ...updates } : c)),
      updatedAt: new Date(),
    }));
  }, []);

  const runCell = useCallback((cellId: string) => {
    updateCell(cellId, { status: 'running' });

    // Simulate execution
    setTimeout(() => {
      updateCell(cellId, {
        status: 'completed',
        executionCount: (notebook.cells.find((c) => c.id === cellId)?.executionCount || 0) + 1,
        output: `Output generated at ${new Date().toLocaleTimeString()}\nCell executed successfully.`,
      });
    }, 1500);
  }, [notebook.cells, updateCell]);

  const runAllCells = useCallback(() => {
    notebook.cells.forEach((cell, index) => {
      if (cell.type === 'code') {
        setTimeout(() => runCell(cell.id), index * 500);
      }
    });
  }, [notebook.cells, runCell]);

  return (
    <div className="h-[calc(100vh-4rem)] flex">
      {/* Sidebar */}
      <div
        className={cn(
          'border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 transition-all duration-300',
          sidebarOpen ? 'w-64' : 'w-0 overflow-hidden'
        )}
      >
        <div className="p-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
            File Browser
          </h3>
          <div className="space-y-1">
            <FileTreeItem
              name="notebooks"
              type="folder"
              expanded
              items={[
                { name: 'analysis.ipynb', type: 'file', active: true },
                { name: 'experiments.ipynb', type: 'file' },
                { name: 'visualization.ipynb', type: 'file' },
              ]}
            />
            <FileTreeItem name="data" type="folder" />
            <FileTreeItem name="models" type="folder" />
            <FileTreeItem name="scripts" type="folder" />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            >
              <ChevronRight
                size={18}
                className={cn(
                  'text-gray-500 transition-transform',
                  sidebarOpen && 'rotate-180'
                )}
              />
            </button>
            <Breadcrumb />
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 text-sm rounded-full">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              {notebook.kernel}
            </div>
            <button
              onClick={runAllCells}
              className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
            >
              <Play size={14} />
              Run All
            </button>
            <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              <Save size={18} className="text-gray-500" />
            </button>
            <button className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
              <Settings size={18} className="text-gray-500" />
            </button>
          </div>
        </div>

        {/* Notebook Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {notebook.cells.map((cell, index) => (
            <NotebookCell
              key={cell.id}
              cell={cell}
              index={index}
              isActive={activeCell === cell.id}
              onActivate={() => setActiveCell(cell.id)}
              onUpdate={(updates) => updateCell(cell.id, updates)}
              onRun={() => runCell(cell.id)}
              onDelete={() => deleteCell(cell.id)}
              onAddCellBelow={(type) => addCell(type, index)}
            />
          ))}

          {/* Add cell button at bottom */}
          <div className="flex justify-center py-4">
            <div className="flex items-center gap-2">
              <button
                onClick={() => addCell('code')}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <Plus size={14} />
                Code
              </button>
              <button
                onClick={() => addCell('markdown')}
                className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              >
                <Plus size={14} />
                Markdown
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

interface FileTreeItemProps {
  name: string;
  type: 'file' | 'folder';
  expanded?: boolean;
  active?: boolean;
  items?: FileTreeItemProps[];
}

const FileTreeItem: React.FC<FileTreeItemProps> = ({
  name,
  type,
  expanded = false,
  active = false,
  items = [],
}) => {
  const [isExpanded, setIsExpanded] = useState(expanded);

  return (
    <div>
      <button
        onClick={() => type === 'folder' && setIsExpanded(!isExpanded)}
        className={cn(
          'w-full flex items-center gap-2 px-2 py-1 rounded text-sm transition-colors',
          active
            ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
        )}
      >
        {type === 'folder' && (
          <ChevronRight
            size={14}
            className={cn('text-gray-400 transition-transform', isExpanded && 'rotate-90')}
          />
        )}
        {type === 'folder' ? (
          <ChevronDown size={14} className="text-yellow-500" />
        ) : (
          <FileCode size={14} className="text-blue-500" />
        )}
        <span className="truncate">{name}</span>
      </button>
      {type === 'folder' && isExpanded && items.length > 0 && (
        <div className="ml-4 mt-1 space-y-1">
          {items.map((item, i) => (
            <FileTreeItem key={i} {...item} />
          ))}
        </div>
      )}
    </div>
  );
};

interface NotebookCellProps {
  cell: Cell;
  index: number;
  isActive: boolean;
  onActivate: () => void;
  onUpdate: (updates: Partial<Cell>) => void;
  onRun: () => void;
  onDelete: () => void;
  onAddCellBelow: (type: Cell['type']) => void;
}

const NotebookCell: React.FC<NotebookCellProps> = ({
  cell,
  index,
  isActive,
  onActivate,
  onUpdate,
  onRun,
  onDelete,
  onAddCellBelow,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const getCellLabel = () => {
    switch (cell.type) {
      case 'code':
        return 'In';
      case 'markdown':
        return 'Md';
      default:
        return 'Raw';
    }
  };

  return (
    <div
      className={cn(
        'group relative rounded-lg border transition-all',
        isActive
          ? 'border-blue-300 dark:border-blue-700 ring-1 ring-blue-300 dark:ring-blue-700'
          : 'border-transparent hover:border-gray-200 dark:hover:border-gray-800'
      )}
      onClick={onActivate}
    >
      {/* Cell Toolbar */}
      <div className="flex items-center justify-between px-2 py-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-400 font-mono">[{getCellLabel()}]</span>
          {cell.executionCount !== undefined && (
            <span className="text-xs text-gray-400 font-mono">
              [{cell.executionCount}]
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRun();
            }}
            disabled={cell.status === 'running'}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            title="Run cell"
          >
            <Play size={14} className="text-gray-500" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAddCellBelow('code');
            }}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            title="Add cell below"
          >
            <Plus size={14} className="text-gray-500" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            title="Delete cell"
          >
            <Trash2 size={14} className="text-gray-500" />
          </button>
        </div>
      </div>

      {/* Cell Content */}
      <div className="flex">
        {/* Input Area */}
        <div className="flex-1">
          {cell.type === 'code' ? (
            <div className="relative">
              <textarea
                ref={textareaRef}
                value={cell.content}
                onChange={(e) => onUpdate({ content: e.target.value })}
                className="w-full p-3 bg-gray-50 dark:bg-gray-900 font-mono text-sm text-gray-800 dark:text-gray-200 resize-none focus:outline-none"
                rows={Math.max(3, cell.content.split('\n').length)}
                spellCheck={false}
              />
              <div className="absolute top-2 right-2">
                <Code size={14} className="text-gray-400" />
              </div>
            </div>
          ) : (
            <textarea
              value={cell.content}
              onChange={(e) => onUpdate({ content: e.target.value })}
              className="w-full p-3 bg-white dark:bg-gray-900 text-sm text-gray-800 dark:text-gray-200 resize-none focus:outline-none"
              rows={Math.max(2, cell.content.split('\n').length)}
              placeholder="Type markdown here..."
            />
          )}
        </div>
      </div>

      {/* Output Area */}
      {cell.output && (
        <div className="border-t border-gray-200 dark:border-gray-800">
          <div className="p-3 bg-gray-50 dark:bg-gray-900/50">
            <div className="flex items-center gap-2 mb-2">
              <Terminal size={14} className="text-gray-400" />
              <span className="text-xs text-gray-400">Output</span>
            </div>
            <pre className="font-mono text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
              {cell.output}
            </pre>
          </div>
        </div>
      )}

      {/* Status Indicator */}
      {cell.status === 'running' && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 animate-pulse" />
      )}
    </div>
  );
};

export default Sandbox;
