"""
Federated Models - Multi-discipline IFC Model Merging
Combines architectural, structural, and MEP models into unified federated model.
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
import json
import logging

logger = logging.getLogger(__name__)


class Discipline(str, Enum):
    """BIM disciplines."""
    ARCHITECTURAL = "architectural"
    STRUCTURAL = "structural"
    MEP = "mep"  # Mechanical, Electrical, Plumbing
    CIVIL = "civil"
    LANDSCAPE = "landscape"
    FIRE = "fire"
    INTERIOR = "interior"


class ElementType(str, Enum):
    """IFC element types."""
    WALL = "IfcWall"
    SLAB = "IfcSlab"
    COLUMN = "IfcColumn"
    BEAM = "IfcBeam"
    DOOR = "IfcDoor"
    WINDOW = "IfcWindow"
    ROOF = "IfcRoof"
    STAIR = "IfcStair"
    RAILING = "IfcRailing"
    PLATE = "IfcPlate"
    MEMBER = "IfcMember"
    COVERING = "IfcCovering"
    FURNITURE = "IfcFurniture"
    SYSTEM = "IfcSystem"
    DISTRIBUTION_ELEMENT = "IfcDistributionElement"
    BUILDING_ELEMENT_PROXY = "IfcBuildingElementProxy"


@dataclass
class Point3D:
    """3D point representation."""
    x: float
    y: float
    z: float
    
    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])
    
    def distance_to(self, other: 'Point3D') -> float:
        return np.linalg.norm(self.to_array() - other.to_array())


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""
    min_point: Point3D
    max_point: Point3D
    
    @property
    def center(self) -> Point3D:
        return Point3D(
            (self.min_point.x + self.max_point.x) / 2,
            (self.min_point.y + self.max_point.y) / 2,
            (self.min_point.z + self.max_point.z) / 2
        )
    
    @property
    def dimensions(self) -> Tuple[float, float, float]:
        return (
            self.max_point.x - self.min_point.x,
            self.max_point.y - self.min_point.y,
            self.max_point.z - self.min_point.z
        )
    
    @property
    def volume(self) -> float:
        dx, dy, dz = self.dimensions
        return dx * dy * dz
    
    def intersects(self, other: 'BoundingBox', tolerance: float = 0.001) -> bool:
        """Check if two bounding boxes intersect."""
        return (
            self.min_point.x <= other.max_point.x + tolerance and
            self.max_point.x >= other.min_point.x - tolerance and
            self.min_point.y <= other.max_point.y + tolerance and
            self.max_point.y >= other.min_point.y - tolerance and
            self.min_point.z <= other.max_point.z + tolerance and
            self.max_point.z >= other.min_point.z - tolerance
        )
    
    def contains_point(self, point: Point3D) -> bool:
        """Check if point is inside bounding box."""
        return (
            self.min_point.x <= point.x <= self.max_point.x and
            self.min_point.y <= point.y <= self.max_point.y and
            self.min_point.z <= point.z <= self.max_point.z
        )


@dataclass
class ModelElement:
    """Represents an element in an IFC model."""
    id: str
    global_id: str
    element_type: ElementType
    name: str
    description: Optional[str]
    discipline: Discipline
    bounding_box: BoundingBox
    geometry: Optional[Dict[str, Any]] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    material: Optional[str] = None
    layer: Optional[str] = None
    is_load_bearing: bool = False
    is_external: bool = False
    discipline_color: Optional[str] = None
    
    def __post_init__(self):
        if not self.discipline_color:
            self.discipline_color = self._get_discipline_color()
    
    def _get_discipline_color(self) -> str:
        """Get default color for discipline."""
        colors = {
            Discipline.ARCHITECTURAL: "#E8B4B8",  # Light red
            Discipline.STRUCTURAL: "#A8D5BA",     # Light green
            Discipline.MEP: "#9BB5CE",            # Light blue
            Discipline.CIVIL: "#D4A574",          # Brown
            Discipline.LANDSCAPE: "#90EE90",      # Green
            Discipline.FIRE: "#FF6B6B",           # Red
            Discipline.INTERIOR: "#DDA0DD",       # Plum
        }
        return colors.get(self.discipline, "#CCCCCC")


@dataclass
class DisciplineModel:
    """Represents a single discipline's IFC model."""
    id: str
    name: str
    discipline: Discipline
    version: str
    file_path: str
    file_size: int
    elements: List[ModelElement] = field(default_factory=list)
    bounding_box: Optional[BoundingBox] = None
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    uploaded_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.bounding_box is None and self.elements:
            self._calculate_bounding_box()
    
    def _calculate_bounding_box(self):
        """Calculate overall bounding box from elements."""
        if not self.elements:
            return
        
        min_x = min(e.bounding_box.min_point.x for e in self.elements)
        min_y = min(e.bounding_box.min_point.y for e in self.elements)
        min_z = min(e.bounding_box.min_point.z for e in self.elements)
        max_x = max(e.bounding_box.max_point.x for e in self.elements)
        max_y = max(e.bounding_box.max_point.y for e in self.elements)
        max_z = max(e.bounding_box.max_point.z for e in self.elements)
        
        self.bounding_box = BoundingBox(
            Point3D(min_x, min_y, min_z),
            Point3D(max_x, max_y, max_z)
        )
    
    @property
    def element_count(self) -> int:
        return len(self.elements)
    
    def get_elements_by_type(self, element_type: ElementType) -> List[ModelElement]:
        """Get elements filtered by type."""
        return [e for e in self.elements if e.element_type == element_type]


@dataclass
class FederatedModel:
    """Combined federated model from multiple disciplines."""
    id: str
    name: str
    project_id: str
    discipline_models: Dict[Discipline, DisciplineModel] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_elements(self) -> int:
        return sum(dm.element_count for dm in self.discipline_models.values())
    
    @property
    def disciplines_present(self) -> List[Discipline]:
        return list(self.discipline_models.keys())
    
    @property
    def overall_bounding_box(self) -> Optional[BoundingBox]:
        """Calculate overall bounding box of federated model."""
        boxes = [dm.bounding_box for dm in self.discipline_models.values() if dm.bounding_box]
        if not boxes:
            return None
        
        min_x = min(b.min_point.x for b in boxes)
        min_y = min(b.min_point.y for b in boxes)
        min_z = min(b.min_point.z for b in boxes)
        max_x = max(b.max_point.x for b in boxes)
        max_y = max(b.max_point.y for b in boxes)
        max_z = max(b.max_point.z for b in boxes)
        
        return BoundingBox(
            Point3D(min_x, min_y, min_z),
            Point3D(max_x, max_y, max_z)
        )
    
    def add_discipline_model(self, model: DisciplineModel):
        """Add a discipline model to the federation."""
        self.discipline_models[model.discipline] = model
        self.updated_at = datetime.utcnow()
    
    def remove_discipline_model(self, discipline: Discipline):
        """Remove a discipline model from the federation."""
        if discipline in self.discipline_models:
            del self.discipline_models[discipline]
            self.updated_at = datetime.utcnow()
    
    def get_all_elements(self) -> List[ModelElement]:
        """Get all elements from all disciplines."""
        elements = []
        for dm in self.discipline_models.values():
            elements.extend(dm.elements)
        return elements
    
    def get_elements_by_discipline(self, discipline: Discipline) -> List[ModelElement]:
        """Get elements from a specific discipline."""
        model = self.discipline_models.get(discipline)
        return model.elements if model else []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'project_id': self.project_id,
            'total_elements': self.total_elements,
            'disciplines': [d.value for d in self.disciplines_present],
            'bounding_box': self._bbox_to_dict(self.overall_bounding_box),
            'discipline_models': {
                d.value: {
                    'id': m.id,
                    'name': m.name,
                    'element_count': m.element_count,
                    'bounding_box': self._bbox_to_dict(m.bounding_box)
                }
                for d, m in self.discipline_models.items()
            },
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def _bbox_to_dict(self, bbox: Optional[BoundingBox]) -> Optional[Dict]:
        if not bbox:
            return None
        return {
            'min': {'x': bbox.min_point.x, 'y': bbox.min_point.y, 'z': bbox.min_point.z},
            'max': {'x': bbox.max_point.x, 'y': bbox.max_point.y, 'z': bbox.max_point.z},
            'center': {'x': bbox.center.x, 'y': bbox.center.y, 'z': bbox.center.z},
            'dimensions': {'x': bbox.dimensions[0], 'y': bbox.dimensions[1], 'z': bbox.dimensions[2]}
        }


class ModelFederationEngine:
    """Engine for federating multiple discipline models."""
    
    def __init__(self):
        self.transformations: Dict[str, np.ndarray] = {}
    
    def create_federated_model(self, name: str, project_id: str,
                               discipline_models: List[DisciplineModel],
                               auto_align: bool = True) -> FederatedModel:
        """Create a federated model from discipline models."""
        federated = FederatedModel(
            id=str(uuid.uuid4()),
            name=name,
            project_id=project_id
        )
        
        # Auto-align models if needed
        if auto_align and len(discipline_models) > 1:
            reference_model = discipline_models[0]
            for model in discipline_models[1:]:
                self._align_model(model, reference_model)
        
        # Add all models
        for model in discipline_models:
            federated.add_discipline_model(model)
        
        logger.info(f"Created federated model '{name}' with {federated.total_elements} elements")
        return federated
    
    def _align_model(self, model: DisciplineModel, 
                    reference: DisciplineModel):
        """Align model to reference using bounding box centers."""
        if not model.bounding_box or not reference.bounding_box:
            return
        
        model_center = model.bounding_box.center
        ref_center = reference.bounding_box.center
        
        translation = Point3D(
            ref_center.x - model_center.x,
            ref_center.y - model_center.y,
            ref_center.z - model_center.z
        )
        
        # Store transformation
        self.transformations[model.id] = np.array([
            translation.x, translation.y, translation.z
        ])
        
        # Apply to all elements
        for element in model.elements:
            self._translate_element(element, translation)
        
        # Recalculate bounding box
        model._calculate_bounding_box()
        
        logger.info(f"Aligned model {model.name} with translation ({translation.x}, {translation.y}, {translation.z})")
    
    def _translate_element(self, element: ModelElement, translation: Point3D):
        """Apply translation to an element."""
        element.bounding_box = BoundingBox(
            Point3D(
                element.bounding_box.min_point.x + translation.x,
                element.bounding_box.min_point.y + translation.y,
                element.bounding_box.min_point.z + translation.z
            ),
            Point3D(
                element.bounding_box.max_point.x + translation.x,
                element.bounding_box.max_point.y + translation.y,
                element.bounding_box.max_point.z + translation.z
            )
        )
    
    def export_to_ifc(self, federated_model: FederatedModel, 
                     output_path: str) -> bool:
        """Export federated model to combined IFC file."""
        # Placeholder - would use ifcopenshell or similar library
        logger.info(f"Exporting federated model to {output_path}")
        return True
    
    def export_to_gltf(self, federated_model: FederatedModel,
                      output_path: str) -> bool:
        """Export federated model to glTF for web viewing."""
        # Placeholder - would convert to glTF format
        logger.info(f"Exporting federated model to glTF: {output_path}")
        return True
    
    def get_model_statistics(self, federated_model: FederatedModel) -> Dict[str, Any]:
        """Get statistics about the federated model."""
        stats = {
            'total_elements': federated_model.total_elements,
            'by_discipline': {},
            'by_element_type': {},
            'bounding_box': {}
        }
        
        for discipline, model in federated_model.discipline_models.items():
            stats['by_discipline'][discipline.value] = {
                'element_count': model.element_count,
                'file_size': model.file_size
            }
            
            # Count by element type
            for element in model.elements:
                et = element.element_type.value
                if et not in stats['by_element_type']:
                    stats['by_element_type'][et] = 0
                stats['by_element_type'][et] += 1
        
        bbox = federated_model.overall_bounding_box
        if bbox:
            stats['bounding_box'] = {
                'dimensions': bbox.dimensions,
                'volume': bbox.volume
            }
        
        return stats


class ModelVersionManager:
    """Manages versions of federated models."""
    
    def __init__(self):
        self.versions: Dict[str, List[FederatedModel]] = {}
    
    def create_version(self, federated_model: FederatedModel,
                      comment: str = "") -> str:
        """Create a new version of a federated model."""
        version_id = str(uuid.uuid4())
        
        if federated_model.id not in self.versions:
            self.versions[federated_model.id] = []
        
        # Store version metadata
        version_info = {
            'version_id': version_id,
            'created_at': datetime.utcnow().isoformat(),
            'element_count': federated_model.total_elements,
            'disciplines': [d.value for d in federated_model.disciplines_present],
            'comment': comment
        }
        
        self.versions[federated_model.id].append(version_info)
        
        logger.info(f"Created version {version_id} for model {federated_model.id}")
        return version_id
    
    def get_version_history(self, model_id: str) -> List[Dict[str, Any]]:
        """Get version history for a model."""
        return self.versions.get(model_id, [])
