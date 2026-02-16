
import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface ElementSelectorProps {
  onSelect?: (elementIds: string[]) => void;
  onHover?: (elementId: string | null) => void;
  multiSelect?: boolean;
  enabled?: boolean;
  selectionColor?: string;
  hoverColor?: string;
  children: React.ReactNode;
}

interface SelectionBox {
  start: THREE.Vector2;
  end: THREE.Vector2;
}

export const ElementSelector: React.FC<ElementSelectorProps> = ({
  onSelect,
  onHover,
  multiSelect = false,
  enabled = true,
  selectionColor = '#ff6b6b',
  hoverColor = '#ffd93d',
  children,
}) => {
  const { camera, scene, gl, size } = useThree();
  const raycaster = useRef(new THREE.Raycaster());
  const mouse = useRef(new THREE.Vector2());
  const [selectedElements, setSelectedElements] = useState<Set<string>>(new Set());
  const [hoveredElement, setHoveredElement] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [selectionBox, setSelectionBox] = useState<SelectionBox | null>(null);
  const selectionBoxRef = useRef<HTMLDivElement>(null);
  
  // Update raycaster with current mouse position
  const updateRaycaster = useCallback((clientX: number, clientY: number) => {
    mouse.current.x = (clientX / size.width) * 2 - 1;
    mouse.current.y = -(clientY / size.height) * 2 + 1;
    raycaster.current.setFromCamera(mouse.current, camera);
  }, [camera, size]);
  
  // Get intersected element
  const getIntersectedElement = useCallback((): string | null => {
    const intersects = raycaster.current.intersectObjects(scene.children, true);
    
    for (const intersect of intersects) {
      // Find the parent mesh with element ID
      let obj: THREE.Object3D | null = intersect.object;
      while (obj) {
        if (obj.userData.elementId) {
          return obj.userData.elementId;
        }
        obj = obj.parent;
      }
    }
    
    return null;
  }, [scene]);
  
  // Get elements in selection box
  const getElementsInBox = useCallback((box: SelectionBox): string[] => {
    const elements: string[] = [];
    const selectionFrustum = new THREE.Frustum();
    
    // Create frustum from selection box
    const startNDC = new THREE.Vector3(
      (box.start.x / size.width) * 2 - 1,
      -(box.start.y / size.height) * 2 + 1,
      -1
    );
    const endNDC = new THREE.Vector3(
      (box.end.x / size.width) * 2 - 1,
      -(box.end.y / size.height) * 2 + 1,
      1
    );
    
    // Traverse scene and find elements within selection
    scene.traverse((obj) => {
      if (obj.userData.elementId && obj instanceof THREE.Mesh) {
        const boundingBox = new THREE.Box3().setFromObject(obj);
        const center = boundingBox.getCenter(new THREE.Vector3());
        
        // Project center to screen space
        center.project(camera);
        
        const screenX = (center.x + 1) * size.width / 2;
        const screenY = (-center.y + 1) * size.height / 2;
        
        // Check if within selection box
        const minX = Math.min(box.start.x, box.end.x);
        const maxX = Math.max(box.start.x, box.end.x);
        const minY = Math.min(box.start.y, box.end.y);
        const maxY = Math.max(box.start.y, box.end.y);
        
        if (screenX >= minX && screenX <= maxX && screenY >= minY && screenY <= maxY) {
          elements.push(obj.userData.elementId);
        }
      }
    });
    
    return elements;
  }, [camera, scene, size]);
  
  // Handle mouse down
  const handleMouseDown = useCallback((event: MouseEvent) => {
    if (!enabled) return;
    
    if (event.button === 0) { // Left click
      setIsDragging(true);
      setSelectionBox({
        start: new THREE.Vector2(event.clientX, event.clientY),
        end: new THREE.Vector2(event.clientX, event.clientY),
      });
    }
  }, [enabled]);
  
  // Handle mouse move
  const handleMouseMove = useCallback((event: MouseEvent) => {
    if (!enabled) return;
    
    updateRaycaster(event.clientX, event.clientY);
    
    // Update selection box
    if (isDragging && selectionBox) {
      setSelectionBox({
        ...selectionBox,
        end: new THREE.Vector2(event.clientX, event.clientY),
      });
    }
    
    // Handle hover
    if (!isDragging) {
      const hovered = getIntersectedElement();
      if (hovered !== hoveredElement) {
        setHoveredElement(hovered);
        onHover?.(hovered);
      }
    }
  }, [enabled, isDragging, selectionBox, updateRaycaster, getIntersectedElement, hoveredElement, onHover]);
  
  // Handle mouse up
  const handleMouseUp = useCallback((event: MouseEvent) => {
    if (!enabled || !isDragging) return;
    
    setIsDragging(false);
    
    if (selectionBox) {
      const boxWidth = Math.abs(selectionBox.end.x - selectionBox.start.x);
      const boxHeight = Math.abs(selectionBox.end.y - selectionBox.start.y);
      
      // If box is small, treat as click
      if (boxWidth < 5 && boxHeight < 5) {
        // Single click - select single element
        updateRaycaster(event.clientX, event.clientY);
        const clicked = getIntersectedElement();
        
        if (clicked) {
          const newSelection = new Set(multiSelect ? selectedElements : []);
          
          if (newSelection.has(clicked)) {
            newSelection.delete(clicked);
          } else {
            newSelection.add(clicked);
          }
          
          setSelectedElements(newSelection);
          onSelect?.(Array.from(newSelection));
        } else if (!multiSelect) {
          // Clicked on empty space - clear selection
          setSelectedElements(new Set());
          onSelect?.([]);
        }
      } else {
        // Box selection
        const elementsInBox = getElementsInBox(selectionBox);
        
        if (multiSelect) {
          const newSelection = new Set(selectedElements);
          elementsInBox.forEach(id => newSelection.add(id));
          setSelectedElements(newSelection);
          onSelect?.(Array.from(newSelection));
        } else {
          setSelectedElements(new Set(elementsInBox));
          onSelect?.(elementsInBox);
        }
      }
    }
    
    setSelectionBox(null);
  }, [enabled, isDragging, selectionBox, multiSelect, selectedElements, updateRaycaster, getIntersectedElement, getElementsInBox, onSelect]);
  
  // Add event listeners
  useEffect(() => {
    const canvas = gl.domElement;
    
    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      canvas.removeEventListener('mousedown', handleMouseDown);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('mouseup', handleMouseUp);
    };
  }, [gl, handleMouseDown, handleMouseMove, handleMouseUp]);
  
  // Highlight selected and hovered elements
  useFrame(() => {
    scene.traverse((obj) => {
      if (obj.userData.elementId && obj instanceof THREE.Mesh) {
        const material = obj.material as THREE.MeshStandardMaterial;
        
        if (selectedElements.has(obj.userData.elementId)) {
          material.emissive.setHex(parseInt(selectionColor.replace('#', '0x')));
          material.emissiveIntensity = 0.3;
        } else if (obj.userData.elementId === hoveredElement) {
          material.emissive.setHex(parseInt(hoverColor.replace('#', '0x')));
          material.emissiveIntensity = 0.2;
        } else {
          material.emissive.setHex(0x000000);
          material.emissiveIntensity = 0;
        }
      }
    });
  });
  
  return (
    <>
      {children}
      
      {/* Selection box overlay */}
      {selectionBox && (
        <div
          ref={selectionBoxRef}
          style={{
            position: 'absolute',
            border: '2px dashed #007bff',
            backgroundColor: 'rgba(0, 123, 255, 0.1)',
            pointerEvents: 'none',
            left: Math.min(selectionBox.start.x, selectionBox.end.x),
            top: Math.min(selectionBox.start.y, selectionBox.end.y),
            width: Math.abs(selectionBox.end.x - selectionBox.start.x),
            height: Math.abs(selectionBox.end.y - selectionBox.start.y),
          }}
        />
      )}
    </>
  );
};

export default ElementSelector;
