import React, { useState, useCallback } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Connection,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import {
  Play,
  Save,
  Plus,
  Trash2,
  Settings,
  Download,
  Upload,
  MoreVertical,
  Database,
  FileInput,
  FileOutput,
  Cpu,
  Filter,
  Merge,
  Split,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

// Custom node types
interface CustomNodeData {
  label: string;
  description?: string;
  icon: React.ElementType;
  status?: 'idle' | 'running' | 'completed' | 'error';
  config?: Record<string, unknown>;
}

const nodeTypes = {
  input: InputNode,
  output: OutputNode,
  process: ProcessNode,
  transform: TransformNode,
  ml: MLNode,
};

function InputNode({ data, selected }: { data: CustomNodeData; selected?: boolean }) {
  const Icon = data.icon;
  return (
    <div
      className={cn(
        'px-4 py-3 bg-white dark:bg-gray-900 rounded-lg border-2 shadow-sm min-w-[160px]',
        selected
          ? 'border-blue-500 ring-2 ring-blue-500/20'
          : 'border-green-300 dark:border-green-700'
      )}
    >
      <div className="flex items-center gap-2">
        <div className="p-1.5 bg-green-100 dark:bg-green-900/20 rounded">
          <Icon size={16} className="text-green-600 dark:text-green-400" />
        </div>
        <span className="font-medium text-sm text-gray-900 dark:text-white">{data.label}</span>
      </div>
      <div className="handle-top" />
      <div className="handle-bottom" />
    </div>
  );
}

function OutputNode({ data, selected }: { data: CustomNodeData; selected?: boolean }) {
  const Icon = data.icon;
  return (
    <div
      className={cn(
        'px-4 py-3 bg-white dark:bg-gray-900 rounded-lg border-2 shadow-sm min-w-[160px]',
        selected
          ? 'border-blue-500 ring-2 ring-blue-500/20'
          : 'border-red-300 dark:border-red-700'
      )}
    >
      <div className="flex items-center gap-2">
        <div className="p-1.5 bg-red-100 dark:bg-red-900/20 rounded">
          <Icon size={16} className="text-red-600 dark:text-red-400" />
        </div>
        <span className="font-medium text-sm text-gray-900 dark:text-white">{data.label}</span>
      </div>
      <div className="handle-top" />
      <div className="handle-bottom" />
    </div>
  );
}

function ProcessNode({ data, selected }: { data: CustomNodeData; selected?: boolean }) {
  const Icon = data.icon;
  const statusColors = {
    idle: 'border-gray-300 dark:border-gray-700',
    running: 'border-blue-400 dark:border-blue-600',
    completed: 'border-green-400 dark:border-green-600',
    error: 'border-red-400 dark:border-red-600',
  };

  return (
    <div
      className={cn(
        'px-4 py-3 bg-white dark:bg-gray-900 rounded-lg border-2 shadow-sm min-w-[180px]',
        selected ? 'ring-2 ring-blue-500/20' : '',
        statusColors[data.status || 'idle']
      )}
    >
      <div className="flex items-center gap-2">
        <div className="p-1.5 bg-blue-100 dark:bg-blue-900/20 rounded">
          <Icon size={16} className="text-blue-600 dark:text-blue-400" />
        </div>
        <span className="font-medium text-sm text-gray-900 dark:text-white">{data.label}</span>
      </div>
      {data.description && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{data.description}</p>
      )}
      {data.status === 'running' && (
        <div className="mt-2 h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 animate-pulse w-2/3" />
        </div>
      )}
      <div className="handle-top" />
      <div className="handle-bottom" />
    </div>
  );
}

function TransformNode({ data, selected }: { data: CustomNodeData; selected?: boolean }) {
  const Icon = data.icon;
  return (
    <div
      className={cn(
        'px-4 py-3 bg-white dark:bg-gray-900 rounded-lg border-2 shadow-sm min-w-[180px]',
        selected
          ? 'border-purple-500 ring-2 ring-purple-500/20'
          : 'border-purple-300 dark:border-purple-700'
      )}
    >
      <div className="flex items-center gap-2">
        <div className="p-1.5 bg-purple-100 dark:bg-purple-900/20 rounded">
          <Icon size={16} className="text-purple-600 dark:text-purple-400" />
        </div>
        <span className="font-medium text-sm text-gray-900 dark:text-white">{data.label}</span>
      </div>
      <div className="handle-top" />
      <div className="handle-bottom" />
    </div>
  );
}

function MLNode({ data, selected }: { data: CustomNodeData; selected?: boolean }) {
  const Icon = data.icon;
  return (
    <div
      className={cn(
        'px-4 py-3 bg-white dark:bg-gray-900 rounded-lg border-2 shadow-sm min-w-[180px]',
        selected
          ? 'border-orange-500 ring-2 ring-orange-500/20'
          : 'border-orange-300 dark:border-orange-700'
      )}
    >
      <div className="flex items-center gap-2">
        <div className="p-1.5 bg-orange-100 dark:bg-orange-900/20 rounded">
          <Icon size={16} className="text-orange-600 dark:text-orange-400" />
        </div>
        <span className="font-medium text-sm text-gray-900 dark:text-white">{data.label}</span>
      </div>
      <div className="handle-top" />
      <div className="handle-bottom" />
    </div>
  );
}

const initialNodes: Node<CustomNodeData>[] = [
  {
    id: '1',
    type: 'input',
    position: { x: 100, y: 200 },
    data: { label: 'Data Source', icon: Database, description: 'BIM data input' },
  },
  {
    id: '2',
    type: 'transform',
    position: { x: 350, y: 200 },
    data: { label: 'Data Filter', icon: Filter, description: 'Filter invalid records' },
  },
  {
    id: '3',
    type: 'process',
    position: { x: 600, y: 200 },
    data: { label: 'Preprocessing', icon: Cpu, description: 'Normalize data' },
  },
  {
    id: '4',
    type: 'ml',
    position: { x: 850, y: 200 },
    data: { label: 'ML Model', icon: Cpu, description: 'Defect detection' },
  },
  {
    id: '5',
    type: 'output',
    position: { x: 1100, y: 200 },
    data: { label: 'Results', icon: FileOutput, description: 'Save predictions' },
  },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e2-3', source: '2', target: '3', animated: true },
  { id: 'e3-4', source: '3', target: '4', animated: true },
  { id: 'e4-5', source: '4', target: '5', animated: true },
];

const Pipelines: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node<CustomNodeData> | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true }, eds)),
    [setEdges]
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node as Node<CustomNodeData>);
  }, []);

  const addNode = useCallback(
    (type: keyof typeof nodeTypes) => {
      const newNode: Node<CustomNodeData> = {
        id: `${nodes.length + 1}`,
        type,
        position: { x: 400, y: 300 },
        data: {
          label: `New ${type}`,
          icon: type === 'input' ? FileInput : type === 'output' ? FileOutput : Cpu,
        },
      };
      setNodes((nds) => [...nds, newNode]);
    },
    [nodes.length, setNodes]
  );

  const deleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId));
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
      if (selectedNode?.id === nodeId) {
        setSelectedNode(null);
      }
    },
    [selectedNode, setNodes, setEdges]
  );

  const runPipeline = useCallback(() => {
    setIsRunning(true);
    // Simulate pipeline execution
    setTimeout(() => setIsRunning(false), 3000);
  }, []);

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
        <div className="flex items-center gap-4">
          <Breadcrumb />
          <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Pipeline Builder</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={runPipeline}
            disabled={isRunning}
            className={cn(
              'inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors',
              isRunning
                ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                : 'bg-green-600 hover:bg-green-700 text-white'
            )}
          >
            <Play size={18} />
            {isRunning ? 'Running...' : 'Run Pipeline'}
          </button>
          <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
            <Save size={18} className="text-gray-500" />
          </button>
          <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg">
            <Settings size={18} className="text-gray-500" />
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Sidebar - Node Palette */}
        <div className="w-64 border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 p-4">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
            Node Palette
          </h3>
          <div className="space-y-2">
            <PaletteItem
              icon={FileInput}
              label="Input"
              color="green"
              onClick={() => addNode('input')}
            />
            <PaletteItem
              icon={FileOutput}
              label="Output"
              color="red"
              onClick={() => addNode('output')}
            />
            <PaletteItem
              icon={Cpu}
              label="Process"
              color="blue"
              onClick={() => addNode('process')}
            />
            <PaletteItem
              icon={Filter}
              label="Transform"
              color="purple"
              onClick={() => addNode('transform')}
            />
            <PaletteItem icon={Cpu} label="ML Model" color="orange" onClick={() => addNode('ml')} />
            <PaletteItem icon={Merge} label="Merge" color="blue" onClick={() => addNode('process')} />
            <PaletteItem icon={Split} label="Split" color="blue" onClick={() => addNode('process')} />
          </div>
        </div>

        {/* Flow Canvas */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background color="#94a3b8" gap={16} size={1} />
            <Controls />
            <MiniMap
              nodeStrokeWidth={3}
              zoomable
              pannable
            />
            <Panel position="top-right" className="bg-white dark:bg-gray-900 p-2 rounded-lg shadow-lg">
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {nodes.length} nodes · {edges.length} connections
              </div>
            </Panel>
          </ReactFlow>
        </div>

        {/* Properties Panel */}
        {selectedNode && (
          <div className="w-80 border-l border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                Node Properties
              </h3>
              <button
                onClick={() => deleteNode(selectedNode.id)}
                className="p-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded text-red-500"
              >
                <Trash2 size={16} />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Label
                </label>
                <input
                  type="text"
                  value={selectedNode.data.label}
                  onChange={(e) => {
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id
                          ? { ...n, data: { ...n.data, label: e.target.value } }
                          : n
                      )
                    );
                  }}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Description
                </label>
                <textarea
                  value={selectedNode.data.description || ''}
                  onChange={(e) => {
                    setNodes((nds) =>
                      nds.map((n) =>
                        n.id === selectedNode.id
                          ? { ...n, data: { ...n.data, description: e.target.value } }
                          : n
                      )
                    );
                  }}
                  className="w-full px-3 py-2 border border-gray-200 dark:border-gray-800 rounded-lg text-sm resize-none"
                  rows={3}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Node Type
                </label>
                <p className="text-sm text-gray-900 dark:text-white capitalize">
                  {selectedNode.type}
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                  Position
                </label>
                <p className="text-sm text-gray-900 dark:text-white font-mono">
                  X: {Math.round(selectedNode.position.x)}, Y:{' '}
                  {Math.round(selectedNode.position.y)}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

interface PaletteItemProps {
  icon: React.ElementType;
  label: string;
  color: string;
  onClick: () => void;
}

const PaletteItem: React.FC<PaletteItemProps> = ({ icon: Icon, label, color, onClick }) => {
  const colorClasses: Record<string, string> = {
    green: 'bg-green-100 text-green-600 dark:bg-green-900/20 dark:text-green-400',
    red: 'bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400',
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400',
    orange: 'bg-orange-100 text-orange-600 dark:bg-orange-900/20 dark:text-orange-400',
  };

  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 p-3 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
    >
      <div className={cn('p-1.5 rounded', colorClasses[color])}>
        <Icon size={18} />
      </div>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
    </button>
  );
};

export default Pipelines;
