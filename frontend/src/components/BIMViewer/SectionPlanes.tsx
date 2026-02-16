
import React, { useState, useCallback, useRef, useEffect } from 'react';
import * as THREE from 'three';
import { useThree } from '@react-three/fiber';
import {
  Box,
  Paper,
  Typography,
  Slider,
  IconButton,
  Button,
  Tooltip,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Crop as CropIcon,
  Close as CloseIcon,
  Flip as FlipIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';

interface SectionPlane {
  id: string;
  normal: THREE.Vector3;
  constant: number;
  visible: boolean;
  color: string;
}

interface SectionPlanesProps {
  onPlanesChange?: (planes: THREE.Plane[]) => void;
  enabled?: boolean;
  maxBounds?: THREE.Box3;
}

interface SectionPlaneControlsProps {
  planes: SectionPlane[];
  onPlaneUpdate: (id: string, updates: Partial<SectionPlane>) => void;
  onPlaneAdd: (normal: THREE.Vector3) => void;
  onPlaneRemove: (id: string) => void;
  onPlaneFlip: (id: string) => void;
  maxBounds?: THREE.Box3;
}

// Predefined section orientations
const SECTION_PRESETS = {
  'top': { normal: new THREE.Vector3(0, -1, 0), name: 'Top' },
  'bottom': { normal: new THREE.Vector3(0, 1, 0), name: 'Bottom' },
  'front': { normal: new THREE.Vector3(0, 0, -1), name: 'Front' },
  'back': { normal: new THREE.Vector3(0, 0, 1), name: 'Back' },
  'left': { normal: new THREE.Vector3(-1, 0, 0), name: 'Left' },
  'right': { normal: new THREE.Vector3(1, 0, 0), name: 'Right' },
};

// Section plane visualizer component
const SectionPlaneVisualizer: React.FC<{
  plane: SectionPlane;
  bounds: THREE.Box3;
}> = ({ plane, bounds }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  
  const planeGeometry = useRef(() => {
    const size = bounds.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    return new THREE.PlaneGeometry(maxDim * 2, maxDim * 2);
  });
  
  if (!plane.visible) return null;
  
  return (
    <mesh
      ref={meshRef}
      geometry={planeGeometry.current()}
      position={plane.normal.clone().multiplyScalar(-plane.constant)}
      rotation={new THREE.Euler().setFromQuaternion(
        new THREE.Quaternion().setFromUnitVectors(
          new THREE.Vector3(0, 0, 1),
          plane.normal
        )
      )}
    >
      <meshBasicMaterial
        color={plane.color}
        transparent
        opacity={0.3}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

// Section plane controls UI
const SectionPlaneControls: React.FC<SectionPlaneControlsProps> = ({
  planes,
  onPlaneUpdate,
  onPlaneAdd,
  onPlaneRemove,
  onPlaneFlip,
  maxBounds,
}) => {
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  
  const getPlaneRange = useCallback((plane: SectionPlane): [number, number] => {
    if (!maxBounds) return [-100, 100];
    
    const min = maxBounds.min.clone().dot(plane.normal);
    const max = maxBounds.max.clone().dot(plane.normal);
    
    return [min, max];
  }, [maxBounds]);
  
  const handleAddPlane = () => {
    if (selectedPreset && SECTION_PRESETS[selectedPreset as keyof typeof SECTION_PRESETS]) {
      const preset = SECTION_PRESETS[selectedPreset as keyof typeof SECTION_PRESETS];
      onPlaneAdd(preset.normal);
      setSelectedPreset('');
    }
  };
  
  return (
    <Paper elevation={2} sx={{ p: 2, maxWidth: 350 }}>
      <Typography variant="h6" gutterBottom>
        Section Planes
      </Typography>
      
      {/* Add new plane */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <FormControl size="small" sx={{ flexGrow: 1 }}>
          <InputLabel>Add Section</InputLabel>
          <Select
            value={selectedPreset}
            onChange={(e) => setSelectedPreset(e.target.value)}
            label="Add Section"
          >
            {Object.entries(SECTION_PRESETS).map(([key, preset]) => (
              <MenuItem key={key} value={key}>
                {preset.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button
          variant="contained"
          onClick={handleAddPlane}
          disabled={!selectedPreset}
        >
          Add
        </Button>
      </Box>
      
      <Divider sx={{ my: 2 }} />
      
      {/* Existing planes */}
      {planes.length === 0 ? (
        <Typography color="text.secondary" align="center">
          No section planes added
        </Typography>
      ) : (
        planes.map((plane, index) => {
          const [min, max] = getPlaneRange(plane);
          
          return (
            <Box key={plane.id} sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                  Plane {index + 1}
                </Typography>
                <Tooltip title="Flip normal">
                  <IconButton size="small" onClick={() => onPlaneFlip(plane.id)}>
                    <FlipIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title={plane.visible ? 'Hide' : 'Show'}>
                  <IconButton
                    size="small"
                    onClick={() => onPlaneUpdate(plane.id, { visible: !plane.visible })}
                  >
                    {plane.visible ? (
                      <VisibilityIcon fontSize="small" />
                    ) : (
                      <VisibilityOffIcon fontSize="small" />
                    )}
                  </IconButton>
                </Tooltip>
                <Tooltip title="Remove">
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => onPlaneRemove(plane.id)}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
              
              <Slider
                value={-plane.constant}
                min={min}
                max={max}
                step={(max - min) / 100}
                onChange={(_, value) => {
                  onPlaneUpdate(plane.id, { constant: -(value as number) });
                }}
                valueLabelDisplay="auto"
                valueLabelFormat={(value) => `${value.toFixed(2)}m`}
              />
              
              <Typography variant="caption" color="text.secondary">
                Normal: ({plane.normal.x.toFixed(2)}, {plane.normal.y.toFixed(2)}, {plane.normal.z.toFixed(2)})
              </Typography>
            </Box>
          );
        })
      )}
    </Paper>
  );
};

// Main component
export const SectionPlanes: React.FC<SectionPlanesProps> = ({
  onPlanesChange,
  enabled = true,
  maxBounds,
}) => {
  const { scene } = useThree();
  const [planes, setPlanes] = useState<SectionPlane[]>([]);
  const planeIdCounter = useRef(0);
  
  // Generate unique ID
  const generateId = () => {
    planeIdCounter.current += 1;
    return `plane_${planeIdCounter.current}`;
  };
  
  // Add new plane
  const handlePlaneAdd = useCallback((normal: THREE.Vector3) => {
    const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7'];
    
    const newPlane: SectionPlane = {
      id: generateId(),
      normal: normal.clone(),
      constant: 0,
      visible: true,
      color: colors[planes.length % colors.length],
    };
    
    setPlanes(prev => [...prev, newPlane]);
  }, [planes.length]);
  
  // Update plane
  const handlePlaneUpdate = useCallback((id: string, updates: Partial<SectionPlane>) => {
    setPlanes(prev =>
      prev.map(p => (p.id === id ? { ...p, ...updates } : p))
    );
  }, []);
  
  // Remove plane
  const handlePlaneRemove = useCallback((id: string) => {
    setPlanes(prev => prev.filter(p => p.id !== id));
  }, []);
  
  // Flip plane normal
  const handlePlaneFlip = useCallback((id: string) => {
    setPlanes(prev =>
      prev.map(p =>
        p.id === id ? { ...p, normal: p.normal.clone().negate() } : p
      )
    );
  }, []);
  
  // Apply clipping planes to scene
  useEffect(() => {
    const clippingPlanes = planes
      .filter(p => p.visible)
      .map(p => new THREE.Plane(p.normal.clone(), p.constant));
    
    // Update renderer
    scene.traverse((obj) => {
      if (obj instanceof THREE.Mesh) {
        obj.material.clippingPlanes = clippingPlanes;
      }
    });
    
    onPlanesChange?.(clippingPlanes);
  }, [planes, scene, onPlanesChange]);
  
  if (!enabled) return null;
  
  return (
    <>
      {/* Visual plane indicators */}
      {maxBounds && planes.map(plane => (
        <SectionPlaneVisualizer
          key={plane.id}
          plane={plane}
          bounds={maxBounds}
        />
      ))}
      
      {/* Controls */}
      <SectionPlaneControls
        planes={planes}
        onPlaneUpdate={handlePlaneUpdate}
        onPlaneAdd={handlePlaneAdd}
        onPlaneRemove={handlePlaneRemove}
        onPlaneFlip={handlePlaneFlip}
        maxBounds={maxBounds}
      />
    </>
  );
};

export default SectionPlanes;
