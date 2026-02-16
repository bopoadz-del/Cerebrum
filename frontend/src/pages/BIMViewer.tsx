import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import {
  Box,
  Layers,
  Eye,
  EyeOff,
  Grid3X3,
  Maximize2,
  RotateCcw,
  Settings,
  Info,
  Ruler,
  Camera,
} from 'lucide-react';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { cn } from '@/lib/utils';

interface BIMElement {
  id: string;
  name: string;
  type: string;
  visible: boolean;
  color: string;
  count: number;
}

const mockLayers: BIMElement[] = [
  { id: '1', name: 'Walls', type: 'structural', visible: true, color: '#8B7355', count: 245 },
  { id: '2', name: 'Floors', type: 'structural', visible: true, color: '#A9A9A9', count: 12 },
  { id: '3', name: 'Columns', type: 'structural', visible: true, color: '#696969', count: 48 },
  { id: '4', name: 'Doors', type: 'opening', visible: true, color: '#8B4513', count: 86 },
  { id: '5', name: 'Windows', type: 'opening', visible: true, color: '#87CEEB', count: 124 },
  { id: '6', name: 'MEP - HVAC', type: 'mep', visible: false, color: '#FF6347', count: 234 },
  { id: '7', name: 'MEP - Electrical', type: 'mep', visible: false, color: '#FFD700', count: 567 },
  { id: '8', name: 'MEP - Plumbing', type: 'mep', visible: false, color: '#4169E1', count: 189 },
  { id: '9', name: 'Furniture', type: 'interior', visible: true, color: '#D2691E', count: 423 },
];

const BIMViewer: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const [layers, setLayers] = useState<BIMElement[]>(mockLayers);
  const [selectedElement, setSelectedElement] = useState<BIMElement | null>(null);
  const [viewMode, setViewMode] = useState<'3d' | 'top' | 'front' | 'side'>('3d');
  const [showGrid, setShowGrid] = useState(true);

  useEffect(() => {
    if (!canvasRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);
    sceneRef.current = scene;

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      canvasRef.current.clientWidth / canvasRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(10, 10, 10);
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.current,
      antialias: true,
      alpha: true,
    });
    renderer.setSize(canvasRef.current.clientWidth, canvasRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    rendererRef.current = renderer;

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controlsRef.current = controls;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 20, 10);
    directionalLight.castShadow = true;
    scene.add(directionalLight);

    // Grid
    const gridHelper = new THREE.GridHelper(50, 50, 0x888888, 0xcccccc);
    scene.add(gridHelper);

    // Mock building geometry
    const createBuilding = () => {
      const buildingGroup = new THREE.Group();

      // Floor
      const floorGeometry = new THREE.BoxGeometry(20, 0.5, 15);
      const floorMaterial = new THREE.MeshStandardMaterial({ color: 0xa9a9a9 });
      const floor = new THREE.Mesh(floorGeometry, floorMaterial);
      floor.position.y = -0.25;
      floor.receiveShadow = true;
      buildingGroup.add(floor);

      // Walls
      const wallMaterial = new THREE.MeshStandardMaterial({ color: 0x8b7355 });
      
      // Front wall with opening for door
      const frontWallLeft = new THREE.Mesh(
        new THREE.BoxGeometry(7, 4, 0.5),
        wallMaterial
      );
      frontWallLeft.position.set(-5.5, 2, 7.25);
      buildingGroup.add(frontWallLeft);

      const frontWallRight = new THREE.Mesh(
        new THREE.BoxGeometry(7, 4, 0.5),
        wallMaterial
      );
      frontWallRight.position.set(5.5, 2, 7.25);
      buildingGroup.add(frontWallRight);

      const frontWallTop = new THREE.Mesh(
        new THREE.BoxGeometry(2, 1.5, 0.5),
        wallMaterial
      );
      frontWallTop.position.set(0, 3.25, 7.25);
      buildingGroup.add(frontWallTop);

      // Back wall
      const backWall = new THREE.Mesh(
        new THREE.BoxGeometry(20, 4, 0.5),
        wallMaterial
      );
      backWall.position.set(0, 2, -7.25);
      buildingGroup.add(backWall);

      // Side walls
      const leftWall = new THREE.Mesh(
        new THREE.BoxGeometry(0.5, 4, 15),
        wallMaterial
      );
      leftWall.position.set(-9.75, 2, 0);
      buildingGroup.add(leftWall);

      const rightWall = new THREE.Mesh(
        new THREE.BoxGeometry(0.5, 4, 15),
        wallMaterial
      );
      rightWall.position.set(9.75, 2, 0);
      buildingGroup.add(rightWall);

      // Columns
      const columnMaterial = new THREE.MeshStandardMaterial({ color: 0x696969 });
      const columnPositions = [
        [-8, -5], [-8, 5], [8, -5], [8, 5],
        [0, -5], [0, 5], [-4, 0], [4, 0],
      ];
      columnPositions.forEach(([x, z]) => {
        const column = new THREE.Mesh(
          new THREE.BoxGeometry(0.8, 4, 0.8),
          columnMaterial
        );
        column.position.set(x, 2, z);
        buildingGroup.add(column);
      });

      // Windows
      const windowMaterial = new THREE.MeshStandardMaterial({
        color: 0x87ceeb,
        transparent: true,
        opacity: 0.7,
      });
      const windowPositions = [
        { pos: [-5, 2.5, 7.25], size: [2, 1.5, 0.1] },
        { pos: [5, 2.5, 7.25], size: [2, 1.5, 0.1] },
        { pos: [-9.75, 2.5, -3], size: [0.1, 1.5, 2] },
        { pos: [-9.75, 2.5, 3], size: [0.1, 1.5, 2] },
        { pos: [9.75, 2.5, -3], size: [0.1, 1.5, 2] },
        { pos: [9.75, 2.5, 3], size: [0.1, 1.5, 2] },
      ];
      windowPositions.forEach(({ pos, size }) => {
        const window = new THREE.Mesh(
          new THREE.BoxGeometry(size[0], size[1], size[2]),
          windowMaterial
        );
        window.position.set(pos[0], pos[1], pos[2]);
        buildingGroup.add(window);
      });

      scene.add(buildingGroup);
    };

    createBuilding();

    // Animation loop
    const animate = () => {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // Handle resize
    const handleResize = () => {
      if (!canvasRef.current || !camera || !renderer) return;
      const { clientWidth, clientHeight } = canvasRef.current;
      camera.aspect = clientWidth / clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(clientWidth, clientHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      scene.clear();
    };
  }, []);

  const toggleLayer = (layerId: string) => {
    setLayers((prev) =>
      prev.map((l) => (l.id === layerId ? { ...l, visible: !l.visible } : l))
    );
  };

  const resetView = () => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(10, 10, 10);
      controlsRef.current.target.set(0, 0, 0);
      controlsRef.current.update();
    }
  };

  const setCameraView = (mode: typeof viewMode) => {
    if (!cameraRef.current || !controlsRef.current) return;
    
    const camera = cameraRef.current;
    const controls = controlsRef.current;

    switch (mode) {
      case 'top':
        camera.position.set(0, 20, 0);
        break;
      case 'front':
        camera.position.set(0, 5, 20);
        break;
      case 'side':
        camera.position.set(20, 5, 0);
        break;
      default:
        camera.position.set(10, 10, 10);
    }
    
    controls.target.set(0, 0, 0);
    controls.update();
    setViewMode(mode);
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex">
      {/* Sidebar - Layer Control */}
      <div className="w-72 border-r border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 flex flex-col">
        <div className="p-4 border-b border-gray-200 dark:border-gray-800">
          <Breadcrumb />
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white mt-2">
            BIM Viewer
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Project Alpha - Building A
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
            Layers
          </h3>
          <div className="space-y-1">
            {layers.map((layer) => (
              <button
                key={layer.id}
                onClick={() => toggleLayer(layer.id)}
                className={cn(
                  'w-full flex items-center gap-3 p-2 rounded-lg transition-colors',
                  layer.visible
                    ? 'bg-blue-50 dark:bg-blue-900/20'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                )}
              >
                {layer.visible ? (
                  <Eye size={16} className="text-blue-600 dark:text-blue-400" />
                ) : (
                  <EyeOff size={16} className="text-gray-400" />
                )}
                <div
                  className="w-3 h-3 rounded"
                  style={{ backgroundColor: layer.color }}
                />
                <div className="flex-1 text-left">
                  <p
                    className={cn(
                      'text-sm',
                      layer.visible
                        ? 'text-gray-900 dark:text-white'
                        : 'text-gray-500 dark:text-gray-400'
                    )}
                  >
                    {layer.name}
                  </p>
                  <p className="text-xs text-gray-400">{layer.count} elements</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Properties Panel */}
        {selectedElement && (
          <div className="p-4 border-t border-gray-200 dark:border-gray-800">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
              Properties
            </h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500 dark:text-gray-400">Type</span>
                <span className="text-gray-900 dark:text-white">{selectedElement.type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500 dark:text-gray-400">Count</span>
                <span className="text-gray-900 dark:text-white">{selectedElement.count}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Canvas */}
      <div className="flex-1 flex flex-col bg-gray-100 dark:bg-gray-950">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-1">
            {(['3d', 'top', 'front', 'side'] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setCameraView(mode)}
                className={cn(
                  'px-3 py-1.5 text-sm font-medium rounded-lg transition-colors capitalize',
                  viewMode === mode
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                )}
              >
                {mode}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowGrid(!showGrid)}
              className={cn(
                'p-2 rounded-lg transition-colors',
                showGrid
                  ? 'bg-blue-100 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                  : 'text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800'
              )}
              title="Toggle Grid"
            >
              <Grid3X3 size={18} />
            </button>
            <button
              onClick={resetView}
              className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              title="Reset View"
            >
              <RotateCcw size={18} />
            </button>
            <button
              className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              title="Fullscreen"
            >
              <Maximize2 size={18} />
            </button>
            <button
              className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
              title="Settings"
            >
              <Settings size={18} />
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div className="flex-1 relative">
          <canvas
            ref={canvasRef}
            className="w-full h-full block"
            style={{ cursor: 'grab' }}
          />

          {/* Overlay Info */}
          <div className="absolute bottom-4 left-4 bg-white/90 dark:bg-gray-900/90 backdrop-blur rounded-lg p-3 shadow-lg">
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1">
                <Ruler size={14} className="text-gray-500" />
                <span className="text-gray-700 dark:text-gray-300">Scale: 1:100</span>
              </div>
              <div className="flex items-center gap-1">
                <Camera size={14} className="text-gray-500" />
                <span className="text-gray-700 dark:text-gray-300">{viewMode.toUpperCase()}</span>
              </div>
            </div>
          </div>

          {/* Element Count */}
          <div className="absolute bottom-4 right-4 bg-white/90 dark:bg-gray-900/90 backdrop-blur rounded-lg p-3 shadow-lg">
            <div className="text-sm text-gray-700 dark:text-gray-300">
              <span className="font-medium">{layers.reduce((acc, l) => acc + l.count, 0)}</span>
              {' '}elements
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BIMViewer;
