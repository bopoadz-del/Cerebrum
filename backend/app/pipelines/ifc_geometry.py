"""
IFC Geometry Extraction Pipeline using IfcOpenShell
Extracts 3D geometry from IFC files for visualization and analysis.
"""

import os
import json
import asyncio
import tempfile
from typing import Optional, Dict, List, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import hashlib
import numpy as np

# IfcOpenShell imports
try:
    import ifcopenshell
    import ifcopenshell.geom
    from ifcopenshell import entity_instance
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class GeometryFormat(Enum):
    """Output geometry formats."""
    OBJ = "obj"
    GLTF = "gltf"
    GLB = "glb"
    DAE = "dae"
    STL = "stl"
    THREE_JS = "three_js"


@dataclass
class GeometryData:
    """Extracted geometry data."""
    element_id: str
    global_id: str
    element_type: str
    name: str
    vertices: np.ndarray = field(default_factory=lambda: np.array([]))
    faces: np.ndarray = field(default_factory=lambda: np.array([]))
    normals: np.ndarray = field(default_factory=lambda: np.array([]))
    uvs: np.ndarray = field(default_factory=lambda: np.array([]))
    bounds: Dict[str, List[float]] = field(default_factory=dict)
    material_ids: List[int] = field(default_factory=list)
    transformation: np.ndarray = field(default_factory=lambda: np.eye(4))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "element_id": self.element_id,
            "global_id": self.global_id,
            "element_type": self.element_type,
            "name": self.name,
            "vertices": self.vertices.tolist() if len(self.vertices) > 0 else [],
            "faces": self.faces.tolist() if len(self.faces) > 0 else [],
            "normals": self.normals.tolist() if len(self.normals) > 0 else [],
            "uvs": self.uvs.tolist() if len(self.uvs) > 0 else [],
            "bounds": self.bounds,
            "material_ids": self.material_ids,
            "transformation": self.transformation.tolist(),
            "vertex_count": len(self.vertices) // 3 if len(self.vertices) > 0 else 0,
            "face_count": len(self.faces) // 3 if len(self.faces) > 0 else 0,
        }


@dataclass
class ExtractionResult:
    """Result of geometry extraction."""
    success: bool
    geometries: List[GeometryData] = field(default_factory=list)
    element_count: int = 0
    total_vertices: int = 0
    total_faces: int = 0
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class IFCGeometryExtractor:
    """
    Extracts 3D geometry from IFC files using IfcOpenShell.
    Supports multiple output formats and optimization options.
    """
    
    def __init__(self, ifc_file_path: str):
        self.ifc_file_path = ifc_file_path
        self._ifc_file: Optional[Any] = None
        self._settings: Optional[Any] = None
        self._serializer: Optional[Any] = None
        
        if not IFC_AVAILABLE:
            raise ImportError("IfcOpenShell is required for IFC processing")
    
    def open_file(self) -> bool:
        """Open and validate IFC file."""
        try:
            self._ifc_file = ifcopenshell.open(self.ifc_file_path)
            logger.info(f"Opened IFC file: {self.ifc_file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to open IFC file: {e}")
            return False
    
    def initialize_settings(
        self,
        use_world_coords: bool = True,
        weld_vertices: bool = True,
        use_brep_data: bool = False,
        convert_back_units: bool = False,
        sew_shells: bool = True,
        validate: bool = False
    ) -> None:
        """Initialize geometry settings."""
        self._settings = ifcopenshell.geom.settings()
        self._settings.set(self._settings.USE_WORLD_COORDS, use_world_coords)
        self._settings.set(self._settings.WELD_VERTICES, weld_vertices)
        self._settings.set(self._settings.USE_BREP_DATA, use_brep_data)
        self._settings.set(self._settings.CONVERT_BACK_UNITS, convert_back_units)
        self._settings.set(self._settings.SEW_SHELLS, sew_shells)
        self._settings.set(self._settings.VALIDATE, validate)
    
    async def extract_all_geometry(
        self,
        element_types: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> ExtractionResult:
        """
        Extract geometry for all elements in the IFC file.
        
        Args:
            element_types: Optional list of IFC element types to extract (e.g., ['IfcWall', 'IfcDoor'])
            progress_callback: Optional callback(current, total) for progress updates
        
        Returns:
            ExtractionResult with all extracted geometries
        """
        import time
        start_time = time.time()
        
        result = ExtractionResult(success=False)
        
        try:
            if not self._ifc_file:
                if not self.open_file():
                    result.errors.append("Failed to open IFC file")
                    return result
            
            if not self._settings:
                self.initialize_settings()
            
            # Get elements to process
            if element_types:
                elements = []
                for elem_type in element_types:
                    elements.extend(self._ifc_file.by_type(elem_type))
            else:
                # Get all geometric elements
                elements = self._ifc_file.by_type('IfcElement')
            
            result.element_count = len(elements)
            logger.info(f"Extracting geometry for {len(elements)} elements")
            
            # Process elements
            geometries = []
            total_vertices = 0
            total_faces = 0
            
            for i, element in enumerate(elements):
                try:
                    geom_data = await self._extract_element_geometry(element)
                    if geom_data:
                        geometries.append(geom_data)
                        total_vertices += len(geom_data.vertices) // 3
                        total_faces += len(geom_data.faces) // 3
                    
                    if progress_callback and i % 10 == 0:
                        progress_callback(i + 1, len(elements))
                        
                except Exception as e:
                    error_msg = f"Failed to extract geometry for {element.GlobalId}: {e}"
                    logger.warning(error_msg)
                    result.warnings.append(error_msg)
            
            result.geometries = geometries
            result.total_vertices = total_vertices
            result.total_faces = total_faces
            result.success = True
            result.processing_time = time.time() - start_time
            
            logger.info(
                f"Extraction complete: {len(geometries)} geometries, "
                f"{total_vertices} vertices, {total_faces} faces"
            )
            
        except Exception as e:
            logger.error(f"Geometry extraction failed: {e}")
            result.errors.append(str(e))
        
        return result
    
    async def extract_element_by_guid(self, global_id: str) -> Optional[GeometryData]:
        """Extract geometry for a specific element by GlobalId."""
        try:
            if not self._ifc_file:
                self.open_file()
            
            if not self._settings:
                self.initialize_settings()
            
            element = self._ifc_file.by_guid(global_id)
            if not element:
                logger.warning(f"Element with GlobalId {global_id} not found")
                return None
            
            return await self._extract_element_geometry(element)
            
        except Exception as e:
            logger.error(f"Failed to extract element {global_id}: {e}")
            return None
    
    async def extract_spatial_structure(
        self,
        structure_type: str = 'IfcBuildingStorey'
    ) -> Dict[str, List[GeometryData]]:
        """Extract geometry organized by spatial structure."""
        structure: Dict[str, List[GeometryData]] = {}
        
        try:
            if not self._ifc_file:
                self.open_file()
            
            spatial_elements = self._ifc_file.by_type(structure_type)
            
            for spatial_elem in spatial_elements:
                elem_name = spatial_elem.Name if hasattr(spatial_elem, 'Name') else spatial_elem.GlobalId
                structure[elem_name] = []
                
                # Get contained elements
                if hasattr(spatial_elem, 'ContainsElements'):
                    for rel in spatial_elem.ContainsElements:
                        for element in rel.RelatedElements:
                            geom_data = await self._extract_element_geometry(element)
                            if geom_data:
                                structure[elem_name].append(geom_data)
            
            return structure
            
        except Exception as e:
            logger.error(f"Failed to extract spatial structure: {e}")
            return structure
    
    async def _extract_element_geometry(
        self, 
        element: Any
    ) -> Optional[GeometryData]:
        """Extract geometry for a single IFC element."""
        try:
            # Check if element has geometry
            if not hasattr(element, 'Representation') or not element.Representation:
                return None
            
            # Create geometry iterator
            iterator = ifcopenshell.geom.iterator(
                self._settings, 
                self._ifc_file, 
                include=[element]
            )
            
            if not iterator.initialize():
                return None
            
            # Process geometry
            shape = iterator.get()
            
            # Extract mesh data
            vertices = np.array(shape.geometry.verts)
            faces = np.array(shape.geometry.faces)
            normals = np.array(shape.geometry.normals) if shape.geometry.normals else np.array([])
            
            # Calculate bounds
            if len(vertices) > 0:
                verts_reshaped = vertices.reshape(-1, 3)
                bounds = {
                    "min": verts_reshaped.min(axis=0).tolist(),
                    "max": verts_reshaped.max(axis=0).tolist(),
                    "center": verts_reshaped.mean(axis=0).tolist()
                }
            else:
                bounds = {}
            
            # Get transformation matrix
            transformation = np.array(shape.transformation.matrix).reshape(4, 4)
            
            return GeometryData(
                element_id=str(element.id()),
                global_id=element.GlobalId,
                element_type=element.is_a(),
                name=getattr(element, 'Name', ''),
                vertices=vertices,
                faces=faces,
                normals=normals,
                bounds=bounds,
                transformation=transformation
            )
            
        except Exception as e:
            logger.warning(f"Geometry extraction failed for element {element.GlobalId}: {e}")
            return None
    
    def export_to_format(
        self,
        geometries: List[GeometryData],
        output_path: str,
        format: GeometryFormat = GeometryFormat.GLTF
    ) -> bool:
        """Export geometries to specified format."""
        try:
            if format == GeometryFormat.OBJ:
                return self._export_obj(geometries, output_path)
            elif format == GeometryFormat.GLTF:
                return self._export_gltf(geometries, output_path)
            elif format == GeometryFormat.THREE_JS:
                return self._export_three_js(geometries, output_path)
            else:
                logger.error(f"Export format {format} not yet implemented")
                return False
                
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def _export_obj(
        self, 
        geometries: List[GeometryData], 
        output_path: str
    ) -> bool:
        """Export to OBJ format."""
        try:
            with open(output_path, 'w') as f:
                vertex_offset = 0
                
                for geom in geometries:
                    f.write(f"# {geom.name} ({geom.global_id})\n")
                    f.write(f"o {geom.global_id}\n")
                    
                    # Write vertices
                    verts = geom.vertices.reshape(-1, 3)
                    for v in verts:
                        f.write(f"v {v[0]} {v[1]} {v[2]}\n")
                    
                    # Write normals
                    if len(geom.normals) > 0:
                        norms = geom.normals.reshape(-1, 3)
                        for n in norms:
                            f.write(f"vn {n[0]} {n[1]} {n[2]}\n")
                    
                    # Write faces
                    faces = geom.faces.reshape(-1, 3)
                    for face in faces:
                        v1, v2, v3 = face[0] + vertex_offset + 1, face[1] + vertex_offset + 1, face[2] + vertex_offset + 1
                        f.write(f"f {v1} {v2} {v3}\n")
                    
                    vertex_offset += len(verts)
                    f.write("\n")
            
            return True
            
        except Exception as e:
            logger.error(f"OBJ export failed: {e}")
            return False
    
    def _export_gltf(
        self, 
        geometries: List[GeometryData], 
        output_path: str
    ) -> bool:
        """Export to glTF format."""
        try:
            # Simplified glTF export - would use a library like pygltflib in production
            gltf_data = {
                "asset": {"version": "2.0", "generator": "Cerebrum IFC Exporter"},
                "scene": 0,
                "scenes": [{"nodes": list(range(len(geometries)))}],
                "nodes": [],
                "meshes": [],
                "buffers": [],
                "bufferViews": [],
                "accessors": []
            }
            
            # Build glTF structure
            buffer_data = bytearray()
            
            for i, geom in enumerate(geometries):
                # Add node
                gltf_data["nodes"].append({
                    "mesh": i,
                    "name": geom.name or geom.global_id
                })
                
                # Add mesh
                gltf_data["meshes"].append({
                    "primitives": [{
                        "attributes": {"POSITION": i * 2},
                        "indices": i * 2 + 1
                    }]
                })
                
                # Add vertex data to buffer
                verts_bytes = geom.vertices.astype(np.float32).tobytes()
                faces_bytes = geom.faces.astype(np.uint32).tobytes()
                
                # ... (full implementation would build complete glTF structure)
            
            # Write glTF JSON
            with open(output_path, 'w') as f:
                json.dump(gltf_data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"glTF export failed: {e}")
            return False
    
    def _export_three_js(
        self, 
        geometries: List[GeometryData], 
        output_path: str
    ) -> bool:
        """Export to Three.js compatible JSON format."""
        try:
            three_js_data = {
                "metadata": {
                    "version": 4.5,
                    "type": "Object",
                    "generator": "Cerebrum IFC Exporter"
                },
                "object": {
                    "type": "Scene",
                    "children": []
                },
                "geometries": [],
                "materials": []
            }
            
            for i, geom in enumerate(geometries):
                # Add geometry
                geometry_data = {
                    "uuid": geom.global_id,
                    "type": "BufferGeometry",
                    "data": {
                        "attributes": {
                            "position": {
                                "itemSize": 3,
                                "type": "Float32Array",
                                "array": geom.vertices.tolist()
                            }
                        },
                        "index": {
                            "type": "Uint32Array",
                            "array": geom.faces.tolist()
                        }
                    }
                }
                
                if len(geom.normals) > 0:
                    geometry_data["data"]["attributes"]["normal"] = {
                        "itemSize": 3,
                        "type": "Float32Array",
                        "array": geom.normals.tolist()
                    }
                
                three_js_data["geometries"].append(geometry_data)
                
                # Add scene object
                three_js_data["object"]["children"].append({
                    "uuid": geom.global_id,
                    "type": "Mesh",
                    "name": geom.name,
                    "geometry": geom.global_id,
                    "matrix": geom.transformation.flatten().tolist()
                })
            
            with open(output_path, 'w') as f:
                json.dump(three_js_data, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Three.js export failed: {e}")
            return False
    
    def get_file_metadata(self) -> Dict[str, Any]:
        """Get IFC file metadata."""
        if not self._ifc_file:
            return {}
        
        try:
            # Get header info
            header = self._ifc_file.wrapped_data.header
            
            # Get project info
            projects = self._ifc_file.by_type('IfcProject')
            project = projects[0] if projects else None
            
            # Get units
            units = self._ifc_file.by_type('IfcUnitAssignment')
            unit_assignment = units[0] if units else None
            
            return {
                "file_name": os.path.basename(self.ifc_file_path),
                "file_schema": header.file_schema.schema_identifiers[0] if header.file_schema else None,
                "file_description": header.file_description.description[0] if header.file_description else None,
                "project_name": project.Name if project else None,
                "project_description": project.Description if project else None,
                "element_counts": {
                    elem_type: len(self._ifc_file.by_type(elem_type))
                    for elem_type in ['IfcWall', 'IfcDoor', 'IfcWindow', 'IfcSlab', 'IfcRoof', 'IfcBeam', 'IfcColumn']
                },
                "total_elements": len(self._ifc_file.by_type('IfcElement')),
                "unit_assignment": str(unit_assignment) if unit_assignment else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get metadata: {e}")
            return {}
    
    def close(self) -> None:
        """Close IFC file and cleanup."""
        self._ifc_file = None
        self._settings = None
        self._serializer = None


class GeometryCache:
    """Cache for extracted geometry data."""
    
    def __init__(self, cache_dir: str = "/tmp/ifc_geometry_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_key(self, ifc_path: str, options: Dict[str, Any]) -> str:
        """Generate cache key for IFC file and options."""
        data = f"{ifc_path}:{json.dumps(options, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def get_cached_geometry(self, cache_key: str) -> Optional[ExtractionResult]:
        """Get cached geometry if available."""
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct result
                result = ExtractionResult(success=True)
                result.geometries = [GeometryData(**g) for g in data.get('geometries', [])]
                result.element_count = data.get('element_count', 0)
                result.total_vertices = data.get('total_vertices', 0)
                result.total_faces = data.get('total_faces', 0)
                
                logger.info(f"Loaded cached geometry: {cache_key}")
                return result
                
            except Exception as e:
                logger.warning(f"Failed to load cached geometry: {e}")
        
        return None
    
    def cache_geometry(
        self, 
        cache_key: str, 
        result: ExtractionResult
    ) -> bool:
        """Cache extracted geometry."""
        try:
            cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
            
            data = {
                'geometries': [g.to_dict() for g in result.geometries],
                'element_count': result.element_count,
                'total_vertices': result.total_vertices,
                'total_faces': result.total_faces,
                'cached_at': datetime.utcnow().isoformat()
            }
            
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            
            logger.info(f"Cached geometry: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache geometry: {e}")
            return False


# Singleton cache instance
geometry_cache = GeometryCache()


async def extract_ifc_geometry(
    ifc_file_path: str,
    element_types: Optional[List[str]] = None,
    use_cache: bool = True,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> ExtractionResult:
    """
    Convenience function to extract geometry from IFC file.
    
    Args:
        ifc_file_path: Path to IFC file
        element_types: Optional list of element types to extract
        use_cache: Whether to use caching
        progress_callback: Optional progress callback
    
    Returns:
        ExtractionResult with all geometries
    """
    cache_key = None
    
    if use_cache:
        cache_key = geometry_cache.get_cache_key(ifc_file_path, {
            'element_types': element_types
        })
        cached = geometry_cache.get_cached_geometry(cache_key)
        if cached:
            return cached
    
    extractor = IFCGeometryExtractor(ifc_file_path)
    result = await extractor.extract_all_geometry(element_types, progress_callback)
    
    if use_cache and cache_key and result.success:
        geometry_cache.cache_geometry(cache_key, result)
    
    extractor.close()
    
    return result
