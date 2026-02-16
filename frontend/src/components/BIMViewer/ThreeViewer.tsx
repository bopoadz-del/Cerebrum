"""
ThreeViewer.tsx - React Three Fiber BIM Viewer Component
Main 3D viewer for IFC models using React Three Fiber and Three.js.
"""

import React, { useRef, useMemo, useEffect, useState, useCallback } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import {
  OrbitControls,
  Grid,
  Box,
  PerspectiveCamera,
  useHelper,
  Environment,
  ContactShadows,
  Bounds,
  useBounds,
  Select,
} from '@react-three/drei';
import * as THREE from 'three';
import { EffectComposer, SSAO, Bloom, Selection } from '@react-three/postprocessing';

// Types
interface GeometryData {
  element_id: string;
  global_id: string;
  element_type: string;
  name: string;
  vertices: number[];
  faces: number[];
  normals?: number[];
  color?: string;
  opacity?: number;
}

interface ThreeViewerProps {
  geometries: GeometryData[];
  selectedElements?: string[];
  onElementClick?: (elementId: string, globalId: string) => void;
  onElementHover?: (elementId: string | null) => void;
  backgroundColor?: string;
  showGrid?: boolean;
  showShadows?: boolean;
  enablePostProcessing?: boolean;
  cameraPosition?: [number, number, number];
  clippingPlanes?: THREE.Plane[];
}

interface MeshProps {
  geometry: GeometryData;
  isSelected: boolean;
  isHovered: boolean;
  onClick: () => void;
  onPointerOver: () => void;
  onPointerOut: () => void;
}

// Element type colors
const ELEMENT_COLORS: Record<string, string> = {
  'IfcWall': '#E8D5B7',
  'IfcDoor': '#8B4513',
  'IfcWindow': '#87CEEB',
  'IfcSlab': '#D3D3D3',
  'IfcRoof': '#8B0000',
  'IfcBeam': '#696969',
  'IfcColumn': '#A9A9A9',
  'IfcFooting': '#8B7355',
  'IfcStair': '#DEB887',
  'IfcRailing': '#C0C0C0',
  'IfcPlate': '#DCDCDC',
  'IfcMember': '#BEBEBE',
  'IfcCovering': '#F5F5DC',
  'IfcSpace': '#E6E6FA',
  'default': '#CCCCCC'
};

// Convert geometry data to Three.js buffer geometry
const createBufferGeometry = (data: GeometryData): THREE.BufferGeometry => {
  const geometry = new THREE.BufferGeometry();
  
  // Set vertices
  const vertices = new Float32Array(data.vertices);
  geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
  
  // Set indices
  if (data.faces && data.faces.length > 0) {
    const indices = new Uint32Array(data.faces);
    geometry.setIndex(new THREE.BufferAttribute(indices, 1));
  }
  
  // Set normals
  if (data.normals && data.normals.length > 0) {
    const normals = new Float32Array(data.normals);
    geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
  } else {
    geometry.computeVertexNormals();
  }
  
  geometry.computeBoundingSphere();
  geometry.computeBoundingBox();
  
  return geometry;
};

// Individual mesh component
const BIMMesh: React.FC<MeshProps> = ({
  geometry,
  isSelected,
  isHovered,
  onClick,
  onPointerOver,
  onPointerOut
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  
  const bufferGeometry = useMemo(() => createBufferGeometry(geometry), [geometry]);
  
  const color = useMemo(() => {
    return ELEMENT_COLORS[geometry.element_type] || ELEMENT_COLORS.default;
  }, [geometry.element_type]);
  
  const material = useMemo(() => {
    return new THREE.MeshStandardMaterial({
      color: isSelected ? '#ff6b6b' : isHovered ? '#ffd93d' : color,
      transparent: geometry.opacity !== undefined && geometry.opacity < 1,
      opacity: geometry.opacity ?? 1,
      side: THREE.DoubleSide,
      roughness: 0.7,
      metalness: 0.1,
    });
  }, [color, isSelected, isHovered, geometry.opacity]);
  
  // Selection outline effect
  useEffect(() => {
    if (meshRef.current) {
      if (isSelected) {
        // Add selection glow
        meshRef.current.material = material.clone();
        meshRef.current.material.emissive = new THREE.Color('#ff6b6b');
        meshRef.current.material.emissiveIntensity = 0.3;
      }
    }
  }, [isSelected, material]);
  
  return (
    <mesh
      ref={meshRef}
      geometry={bufferGeometry}
      material={material}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      onPointerOver={(e) => {
        e.stopPropagation();
        onPointerOver();
      }}
      onPointerOut={() => onPointerOut()}
      castShadow
      receiveShadow
    />
  );
};

// Scene content component
const SceneContent: React.FC<ThreeViewerProps> = ({
  geometries,
  selectedElements = [],
  onElementClick,
  onElementHover,
  showGrid = true,
  showShadows = true,
  clippingPlanes = [],
}) => {
  const [hoveredElement, setHoveredElement] = useState<string | null>(null);
  const controlsRef = useRef<any>(null);
  const bounds = useBounds();
  
  // Auto-fit camera to scene
  useEffect(() => {
    if (geometries.length > 0) {
      bounds.refresh().clip().fit();
    }
  }, [geometries, bounds]);
  
  const handleElementClick = useCallback((elementId: string, globalId: string) => {
    onElementClick?.(elementId, globalId);
  }, [onElementClick]);
  
  const handleElementHover = useCallback((elementId: string | null) => {
    setHoveredElement(elementId);
    onElementHover?.(elementId);
  }, [onElementHover]);
  
  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[10, 20, 10]}
        intensity={1}
        castShadow={showShadows}
        shadow-mapSize={[2048, 2048]}
        shadow-camera-near={0.1}
        shadow-camera-far={100}
        shadow-camera-left={-50}
        shadow-camera-right={50}
        shadow-camera-top={50}
        shadow-camera-bottom={-50}
      />
      <directionalLight position={[-10, 10, -5]} intensity={0.3} />
      
      {/* Grid */}
      {showGrid && (
        <Grid
          position={[0, -0.01, 0]}
          args={[100, 100]}
          cellSize={1}
          cellThickness={0.5}
          cellColor="#6f6f6f"
          sectionSize={10}
          sectionThickness={1}
          sectionColor="#9d4b4b"
          fadeDistance={50}
          fadeStrength={1}
          infiniteGrid
        />
      )}
      
      {/* Contact shadows */}
      {showShadows && (
        <ContactShadows
          position={[0, 0, 0]}
          opacity={0.4}
          scale={50}
          blur={2}
          far={10}
        />
      )}
      
      {/* Geometry meshes */}
      <Select multiple box>
        {geometries.map((geom) => (
          <BIMMesh
            key={geom.global_id}
            geometry={geom}
            isSelected={selectedElements.includes(geom.global_id)}
            isHovered={hoveredElement === geom.global_id}
            onClick={() => handleElementClick(geom.element_id, geom.global_id)}
            onPointerOver={() => handleElementHover(geom.global_id)}
            onPointerOut={() => handleElementHover(null)}
          />
        ))}
      </Select>
      
      {/* Clipping planes */}
      {clippingPlanes.length > 0 && (
        <group>
          {clippingPlanes.map((plane, index) => (
            <primitive key={index} object={new THREE.PlaneHelper(plane, 10, 0xff0000)} />
          ))}
        </group>
      )}
      
      {/* Controls */}
      <OrbitControls
        ref={controlsRef}
        makeDefault
        enableDamping
        dampingFactor={0.05}
        minDistance={0.1}
        maxDistance={1000}
        maxPolarAngle={Math.PI / 2 - 0.05}
      />
    </>
  );
};

// Main viewer component
export const ThreeViewer: React.FC<ThreeViewerProps> = ({
  geometries,
  selectedElements = [],
  onElementClick,
  onElementHover,
  backgroundColor = '#f0f0f0',
  showGrid = true,
  showShadows = true,
  enablePostProcessing = false,
  cameraPosition = [20, 20, 20],
  clippingPlanes = [],
}) => {
  return (
    <div style={{ width: '100%', height: '100%' }}>
      <Canvas
        shadows={showShadows}
        camera={{ position: cameraPosition, fov: 50 }}
        gl={{
          antialias: true,
          alpha: true,
          localClippingEnabled: clippingPlanes.length > 0,
        }}
        style={{ background: backgroundColor }}
      >
        <Bounds fit clip observe margin={1.2}>
          <SceneContent
            geometries={geometries}
            selectedElements={selectedElements}
            onElementClick={onElementClick}
            onElementHover={onElementHover}
            showGrid={showGrid}
            showShadows={showShadows}
            clippingPlanes={clippingPlanes}
          />
        </Bounds>
        
        {/* Post-processing effects */}
        {enablePostProcessing && (
          <EffectComposer>
            <SSAO
              radius={0.5}
              intensity={50}
              luminanceInfluence={0.5}
              color="black"
            />
            <Bloom
              intensity={0.3}
              luminanceThreshold={0.9}
              luminanceSmoothing={0.025}
            />
          </EffectComposer>
        )}
      </Canvas>
    </div>
  );
};

export default ThreeViewer;
