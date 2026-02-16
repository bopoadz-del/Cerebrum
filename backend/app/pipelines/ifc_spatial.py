"""
IFC Spatial Indexing Pipeline using R-tree
Implements spatial indexing for efficient geometry queries and clash detection.
"""

import numpy as np
from typing import Optional, Dict, List, Any, Tuple, Iterator, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

try:
    from rtree import index
    RTREE_AVAILABLE = True
except ImportError:
    RTREE_AVAILABLE = False

try:
    import ifcopenshell
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class BoundingBox:
    """3D bounding box."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float
    
    @property
    def center(self) -> Tuple[float, float, float]:
        """Get center point of bounding box."""
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2
        )
    
    @property
    def dimensions(self) -> Tuple[float, float, float]:
        """Get dimensions (width, height, depth)."""
        return (
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z
        )
    
    @property
    def volume(self) -> float:
        """Get volume of bounding box."""
        w, h, d = self.dimensions
        return w * h * d
    
    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if this bounding box intersects with another."""
        return (
            self.min_x <= other.max_x and self.max_x >= other.min_x and
            self.min_y <= other.max_y and self.max_y >= other.min_y and
            self.min_z <= other.max_z and self.max_z >= other.min_z
        )
    
    def contains_point(self, point: Tuple[float, float, float]) -> bool:
        """Check if point is inside bounding box."""
        x, y, z = point
        return (
            self.min_x <= x <= self.max_x and
            self.min_y <= y <= self.max_y and
            self.min_z <= z <= self.max_z
        )
    
    def to_tuple(self) -> Tuple[float, float, float, float, float, float]:
        """Convert to tuple (minx, miny, minz, maxx, maxy, maxz)."""
        return (self.min_x, self.min_y, self.min_z, self.max_x, self.max_y, self.max_z)
    
    @classmethod
    def from_points(cls, points: np.ndarray) -> 'BoundingBox':
        """Create bounding box from array of points."""
        if len(points) == 0:
            return cls(0, 0, 0, 0, 0, 0)
        
        return cls(
            min_x=float(np.min(points[:, 0])),
            min_y=float(np.min(points[:, 1])),
            min_z=float(np.min(points[:, 2])),
            max_x=float(np.max(points[:, 0])),
            max_y=float(np.max(points[:, 1])),
            max_z=float(np.max(points[:, 2]))
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "min_x": self.min_x,
            "min_y": self.min_y,
            "min_z": self.min_z,
            "max_x": self.max_x,
            "max_y": self.max_y,
            "max_z": self.max_z
        }


@dataclass
class SpatialObject:
    """Object with spatial information."""
    id: str
    global_id: str
    element_type: str
    name: str
    bounding_box: BoundingBox
    geometry_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "global_id": self.global_id,
            "element_type": self.element_type,
            "name": self.name,
            "bounding_box": self.bounding_box.to_dict(),
            "geometry_hash": self.geometry_hash,
            "metadata": self.metadata
        }


@dataclass
class SpatialQueryResult:
    """Result of a spatial query."""
    objects: List[SpatialObject]
    query_time_ms: float
    query_type: str
    
    def __len__(self) -> int:
        return len(self.objects)


class RTreeSpatialIndex:
    """
    R-tree based spatial index for IFC elements.
    Provides efficient spatial queries for clash detection and selection.
    """
    
    def __init__(self, dimension: int = 3):
        self.dimension = dimension
        self._index: Optional[index.Index] = None
        self._objects: Dict[str, SpatialObject] = {}
        self._id_counter = 0
        
        if not RTREE_AVAILABLE:
            raise ImportError("R-tree library is required for spatial indexing")
    
    def create_index(self, temp_dir: Optional[str] = None) -> None:
        """Create new R-tree index."""
        p = index.Property()
        p.dimension = self.dimension
        
        if temp_dir:
            p.dat_extension = 'rtree_dat'
            p.idx_extension = 'rtree_idx'
        
        self._index = index.Index(properties=p)
        logger.info(f"Created {self.dimension}D R-tree index")
    
    def insert(self, obj: SpatialObject) -> bool:
        """Insert object into spatial index."""
        if not self._index:
            self.create_index()
        
        try:
            self._id_counter += 1
            idx_id = self._id_counter
            
            bbox = obj.bounding_box.to_tuple()
            self._index.insert(idx_id, bbox, obj=obj.global_id)
            self._objects[obj.global_id] = obj
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert object {obj.global_id}: {e}")
            return False
    
    def insert_many(self, objects: List[SpatialObject]) -> int:
        """Insert multiple objects into index."""
        inserted = 0
        for obj in objects:
            if self.insert(obj):
                inserted += 1
        
        logger.info(f"Inserted {inserted}/{len(objects)} objects into index")
        return inserted
    
    def remove(self, global_id: str) -> bool:
        """Remove object from index."""
        if not self._index or global_id not in self._objects:
            return False
        
        try:
            obj = self._objects[global_id]
            
            # Find and remove from index
            # Note: R-tree doesn't support direct deletion by object ID
            # We need to rebuild or use a different approach
            
            del self._objects[global_id]
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove object {global_id}: {e}")
            return False
    
    def intersects(
        self, 
        bbox: BoundingBox,
        objects_only: bool = True
    ) -> List[Union[str, SpatialObject]]:
        """
        Find objects that intersect with bounding box.
        
        Args:
            bbox: Query bounding box
            objects_only: If True, return SpatialObjects; else return IDs
        
        Returns:
            List of intersecting objects or IDs
        """
        if not self._index:
            return []
        
        try:
            results = list(self._index.intersection(bbox.to_tuple(), objects=objects_only))
            
            if objects_only:
                # Return SpatialObjects
                return [self._objects.get(r) for r in results if r in self._objects]
            else:
                # Return IDs
                return results
                
        except Exception as e:
            logger.error(f"Intersection query failed: {e}")
            return []
    
    def nearest(
        self,
        point: Tuple[float, float, float],
        num_results: int = 1
    ) -> List[SpatialObject]:
        """
        Find nearest objects to a point.
        
        Args:
            point: Query point (x, y, z)
            num_results: Number of nearest results to return
        
        Returns:
            List of nearest SpatialObjects
        """
        if not self._index:
            return []
        
        try:
            # Create small bbox around point for nearest query
            epsilon = 0.001
            bbox = (
                point[0] - epsilon, point[1] - epsilon, point[2] - epsilon,
                point[0] + epsilon, point[1] + epsilon, point[2] + epsilon
            )
            
            results = list(self._index.nearest(bbox, num_results, objects=True))
            
            return [self._objects.get(r) for r in results if r in self._objects]
            
        except Exception as e:
            logger.error(f"Nearest query failed: {e}")
            return []
    
    def contains_point(self, point: Tuple[float, float, float]) -> List[SpatialObject]:
        """Find all objects that contain a point."""
        if not self._index:
            return []
        
        try:
            # Query with small bbox around point
            epsilon = 0.0001
            bbox = (
                point[0] - epsilon, point[1] - epsilon, point[2] - epsilon,
                point[0] + epsilon, point[1] + epsilon, point[2] + epsilon
            )
            
            candidates = list(self._index.intersection(bbox, objects=True))
            
            # Filter to those that actually contain the point
            results = []
            for global_id in candidates:
                obj = self._objects.get(global_id)
                if obj and obj.bounding_box.contains_point(point):
                    results.append(obj)
            
            return results
            
        except Exception as e:
            logger.error(f"Contains point query failed: {e}")
            return []
    
    def window_query(
        self,
        min_point: Tuple[float, float, float],
        max_point: Tuple[float, float, float]
    ) -> List[SpatialObject]:
        """
        Query objects within a window (axis-aligned bounding box).
        
        Args:
            min_point: Minimum corner (x, y, z)
            max_point: Maximum corner (x, y, z)
        
        Returns:
            List of SpatialObjects within window
        """
        bbox = BoundingBox(
            min_point[0], min_point[1], min_point[2],
            max_point[0], max_point[1], max_point[2]
        )
        return self.intersects(bbox, objects_only=True)
    
    def find_clashes(
        self,
        tolerance: float = 0.001
    ) -> List[Tuple[SpatialObject, SpatialObject, float]]:
        """
        Find all potential clashes (intersections) between objects.
        
        Args:
            tolerance: Minimum overlap distance to consider a clash
        
        Returns:
            List of (object1, object2, overlap_volume) tuples
        """
        clashes = []
        checked_pairs = set()
        
        for obj_id, obj in self._objects.items():
            # Find candidates that intersect
            candidates = self.intersects(obj.bounding_box, objects_only=True)
            
            for other in candidates:
                if other.global_id == obj.global_id:
                    continue
                
                # Create unique pair key
                pair_key = tuple(sorted([obj.global_id, other.global_id]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                # Check for actual intersection
                if obj.bounding_box.intersects(other.bounding_box):
                    # Calculate overlap volume
                    overlap = self._calculate_overlap(
                        obj.bounding_box, 
                        other.bounding_box
                    )
                    
                    if overlap > tolerance:
                        clashes.append((obj, other, overlap))
        
        return clashes
    
    def _calculate_overlap(
        self, 
        bbox1: BoundingBox, 
        bbox2: BoundingBox
    ) -> float:
        """Calculate overlap volume between two bounding boxes."""
        # Calculate intersection bounds
        min_x = max(bbox1.min_x, bbox2.min_x)
        min_y = max(bbox1.min_y, bbox2.min_y)
        min_z = max(bbox1.min_z, bbox2.min_z)
        max_x = min(bbox1.max_x, bbox2.max_x)
        max_y = min(bbox1.max_y, bbox2.max_y)
        max_z = min(bbox1.max_z, bbox2.max_z)
        
        # Calculate overlap dimensions
        overlap_x = max(0, max_x - min_x)
        overlap_y = max(0, max_y - min_y)
        overlap_z = max(0, max_z - min_z)
        
        return overlap_x * overlap_y * overlap_z
    
    def get_bounds(self) -> Optional[BoundingBox]:
        """Get bounding box of entire index."""
        if not self._index:
            return None
        
        try:
            bounds = self._index.bounds
            return BoundingBox(
                min_x=bounds[0],
                min_y=bounds[1],
                min_z=bounds[2],
                max_x=bounds[3],
                max_y=bounds[4],
                max_z=bounds[5]
            )
        except Exception as e:
            logger.error(f"Failed to get bounds: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "object_count": len(self._objects),
            "dimension": self.dimension,
            "bounds": self.get_bounds().to_dict() if self.get_bounds() else None
        }
    
    def clear(self) -> None:
        """Clear the index."""
        self._objects.clear()
        self._id_counter = 0
        if self._index:
            self._index.close()
            self._index = None
    
    def save(self, filepath: str) -> bool:
        """Save index to file."""
        try:
            data = {
                "objects": {k: v.to_dict() for k, v in self._objects.items()},
                "dimension": self.dimension,
                "id_counter": self._id_counter
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f)
            
            logger.info(f"Saved spatial index to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False
    
    @classmethod
    def load(cls, filepath: str) -> Optional['RTreeSpatialIndex']:
        """Load index from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            instance = cls(dimension=data.get('dimension', 3))
            instance._id_counter = data.get('id_counter', 0)
            
            # Rebuild index
            instance.create_index()
            
            for global_id, obj_data in data.get('objects', {}).items():
                bbox = BoundingBox(**obj_data['bounding_box'])
                obj = SpatialObject(
                    id=obj_data['id'],
                    global_id=obj_data['global_id'],
                    element_type=obj_data['element_type'],
                    name=obj_data['name'],
                    bounding_box=bbox,
                    geometry_hash=obj_data.get('geometry_hash'),
                    metadata=obj_data.get('metadata', {})
                )
                instance.insert(obj)
            
            logger.info(f"Loaded spatial index from {filepath}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return None


class IFCSpatialIndexer:
    """Builds spatial index from IFC file."""
    
    def __init__(self, ifc_file_path: str):
        self.ifc_file_path = ifc_file_path
        self._ifc_file: Optional[Any] = None
        
        if not IFC_AVAILABLE:
            raise ImportError("IfcOpenShell is required for IFC processing")
    
    def open_file(self) -> bool:
        """Open IFC file."""
        try:
            self._ifc_file = ifcopenshell.open(self.ifc_file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to open IFC file: {e}")
            return False
    
    def build_index(
        self,
        element_types: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> RTreeSpatialIndex:
        """
        Build spatial index from IFC elements.
        
        Args:
            element_types: Optional list of element types to index
            progress_callback: Optional callback(current, total)
        
        Returns:
            RTreeSpatialIndex with all elements
        """
        if not self._ifc_file:
            if not self.open_file():
                raise ValueError("Failed to open IFC file")
        
        spatial_index = RTreeSpatialIndex(dimension=3)
        spatial_index.create_index()
        
        # Get elements to index
        if element_types:
            elements = []
            for elem_type in element_types:
                elements.extend(self._ifc_file.by_type(elem_type))
        else:
            elements = self._ifc_file.by_type('IfcElement')
        
        logger.info(f"Building spatial index for {len(elements)} elements")
        
        # Process each element
        for i, element in enumerate(elements):
            try:
                spatial_obj = self._create_spatial_object(element)
                if spatial_obj:
                    spatial_index.insert(spatial_obj)
                
                if progress_callback and i % 100 == 0:
                    progress_callback(i + 1, len(elements))
                    
            except Exception as e:
                logger.warning(f"Failed to index element {element.GlobalId}: {e}")
        
        logger.info(f"Built spatial index with {len(spatial_index._objects)} objects")
        
        return spatial_index
    
    def _create_spatial_object(self, element: Any) -> Optional[SpatialObject]:
        """Create SpatialObject from IFC element."""
        try:
            # Get element bounds from geometry
            # This is a simplified version - full implementation would
            # extract actual geometry bounds
            
            # Try to get from object placement
            if hasattr(element, 'ObjectPlacement'):
                placement = element.ObjectPlacement
                # Extract placement information
            
            # Default bounds (would be calculated from actual geometry)
            bbox = BoundingBox(
                min_x=0, min_y=0, min_z=0,
                max_x=1, max_y=1, max_z=1
            )
            
            return SpatialObject(
                id=str(element.id()),
                global_id=element.GlobalId,
                element_type=element.is_a(),
                name=getattr(element, 'Name', ''),
                bounding_box=bbox,
                metadata={
                    "description": getattr(element, 'Description', None),
                    "tag": getattr(element, 'Tag', None)
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to create spatial object: {e}")
            return None
    
    def close(self) -> None:
        """Close IFC file."""
        self._ifc_file = None


# Convenience function
async def build_ifc_spatial_index(
    ifc_file_path: str,
    element_types: Optional[List[str]] = None
) -> RTreeSpatialIndex:
    """
    Build spatial index from IFC file.
    
    Args:
        ifc_file_path: Path to IFC file
        element_types: Optional list of element types to index
    
    Returns:
        RTreeSpatialIndex
    """
    indexer = IFCSpatialIndexer(ifc_file_path)
    index = indexer.build_index(element_types)
    indexer.close()
    return index
