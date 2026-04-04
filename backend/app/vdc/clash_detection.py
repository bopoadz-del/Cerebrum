"""
Clash Detection Engine - AABB Collision Detection
Detects hard clashes, soft clashes, and clearance violations between BIM elements.
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from .federated_models import ModelElement, BoundingBox, Point3D, FederatedModel, Discipline

logger = logging.getLogger(__name__)


class ClashType(str, Enum):
    """Types of clashes."""
    HARD_CLASH = "hard_clash"           # Physical intersection
    SOFT_CLASH = "soft_clash"           # Proximity violation
    CLEARANCE_VIOLATION = "clearance"   # Insufficient clearance
    DUPLICATE = "duplicate"             # Duplicate elements
    WORKSPACE_CLASH = "workspace"       # Workspace interference


class ClashStatus(str, Enum):
    """Status of a clash."""
    NEW = "new"
    ACTIVE = "active"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    APPROVED = "approved"


class ClashSeverity(str, Enum):
    """Severity levels for clashes."""
    CRITICAL = "critical"    # Must be resolved
    HIGH = "high"            # Should be resolved
    MEDIUM = "medium"        # Should be reviewed
    LOW = "low"              # Informational


@dataclass
class Clash:
    """Represents a clash between two elements."""
    id: str
    clash_type: ClashType
    element_a: ModelElement
    element_b: ModelElement
    intersection_volume: float
    intersection_center: Point3D
    penetration_depth: float
    status: ClashStatus = ClashStatus.NEW
    severity: ClashSeverity = ClashSeverity.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    assigned_to: Optional[str] = None
    grid_location: Optional[str] = None
    level: Optional[str] = None
    
    @property
    def element_a_id(self) -> str:
        return self.element_a.id
    
    @property
    def element_b_id(self) -> str:
        return self.element_b.id
    
    @property
    def is_cross_discipline(self) -> bool:
        """Check if clash is between different disciplines."""
        return self.element_a.discipline != self.element_b.discipline
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'clash_type': self.clash_type.value,
            'severity': self.severity.value,
            'status': self.status.value,
            'element_a': {
                'id': self.element_a.id,
                'name': self.element_a.name,
                'type': self.element_a.element_type.value,
                'discipline': self.element_a.discipline.value
            },
            'element_b': {
                'id': self.element_b.id,
                'name': self.element_b.name,
                'type': self.element_b.element_type.value,
                'discipline': self.element_b.discipline.value
            },
            'intersection': {
                'volume': self.intersection_volume,
                'center': {
                    'x': self.intersection_center.x,
                    'y': self.intersection_center.y,
                    'z': self.intersection_center.z
                },
                'penetration_depth': self.penetration_depth
            },
            'is_cross_discipline': self.is_cross_discipline,
            'grid_location': self.grid_location,
            'level': self.level,
            'created_at': self.created_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


@dataclass
class ClashRule:
    """Rule for clash detection."""
    name: str
    clash_type: ClashType
    element_types_a: List[str]
    element_types_b: List[str]
    disciplines_a: Optional[List[Discipline]] = None
    disciplines_b: Optional[List[Discipline]] = None
    tolerance: float = 0.001  # meters
    clearance: float = 0.0    # minimum clearance required
    enabled: bool = True
    severity: ClashSeverity = ClashSeverity.MEDIUM


@dataclass
class ClashResult:
    """Result of clash detection run."""
    id: str
    run_at: datetime
    total_elements_checked: int
    total_pairs_checked: int
    clashes: List[Clash] = field(default_factory=list)
    execution_time_ms: float = 0.0
    rules_applied: List[str] = field(default_factory=list)
    
    @property
    def clash_count(self) -> int:
        return len(self.clashes)
    
    @property
    def clashes_by_type(self) -> Dict[str, int]:
        counts = {}
        for clash in self.clashes:
            ct = clash.clash_type.value
            counts[ct] = counts.get(ct, 0) + 1
        return counts
    
    @property
    def clashes_by_severity(self) -> Dict[str, int]:
        counts = {}
        for clash in self.clashes:
            sev = clash.severity.value
            counts[sev] = counts.get(sev, 0) + 1
        return counts
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'run_at': self.run_at.isoformat(),
            'total_elements_checked': self.total_elements_checked,
            'total_pairs_checked': self.total_pairs_checked,
            'clash_count': self.clash_count,
            'execution_time_ms': self.execution_time_ms,
            'clashes_by_type': self.clashes_by_type,
            'clashes_by_severity': self.clashes_by_severity,
            'rules_applied': self.rules_applied,
            'clashes': [c.to_dict() for c in self.clashes]
        }


class AABBTree:
    """Axis-Aligned Bounding Box tree for spatial indexing."""
    
    def __init__(self, max_elements_per_node: int = 10):
        self.root: Optional['AABBNode'] = None
        self.max_elements = max_elements_per_node
        self.elements: List[ModelElement] = []
    
    def build(self, elements: List[ModelElement]):
        """Build the AABB tree from elements."""
        self.elements = elements
        if elements:
            self.root = self._build_node(elements)
    
    def _build_node(self, elements: List[ModelElement]) -> 'AABBNode':
        """Recursively build tree nodes."""
        if len(elements) <= self.max_elements:
            return AABBNode(elements=elements, is_leaf=True)
        
        # Calculate bounding box for all elements
        bbox = self._calculate_bbox(elements)
        
        # Split along longest axis
        dimensions = bbox.dimensions
        axis = dimensions.index(max(dimensions))
        
        # Sort elements by center along split axis
        sorted_elements = sorted(
            elements,
            key=lambda e: e.bounding_box.center.to_array()[axis]
        )
        
        # Split in half
        mid = len(sorted_elements) // 2
        left_elements = sorted_elements[:mid]
        right_elements = sorted_elements[mid:]
        
        # Create node
        node = AABBNode(bounding_box=bbox, is_leaf=False)
        node.left = self._build_node(left_elements)
        node.right = self._build_node(right_elements)
        
        return node
    
    def _calculate_bbox(self, elements: List[ModelElement]) -> BoundingBox:
        """Calculate combined bounding box."""
        min_coords = [
            min(e.bounding_box.min_point.x for e in elements),
            min(e.bounding_box.min_point.y for e in elements),
            min(e.bounding_box.min_point.z for e in elements)
        ]
        max_coords = [
            max(e.bounding_box.max_point.x for e in elements),
            max(e.bounding_box.max_point.y for e in elements),
            max(e.bounding_box.max_point.z for e in elements)
        ]
        return BoundingBox(
            Point3D(*min_coords),
            Point3D(*max_coords)
        )
    
    def query_intersections(self, bbox: BoundingBox) -> List[ModelElement]:
        """Query elements that intersect with given bounding box."""
        if not self.root:
            return []
        return self._query_node(self.root, bbox)
    
    def _query_node(self, node: 'AABBNode', 
                   bbox: BoundingBox) -> List[ModelElement]:
        """Recursively query tree nodes."""
        if not node.bounding_box.intersects(bbox):
            return []
        
        if node.is_leaf:
            return [
                e for e in node.elements
                if e.bounding_box.intersects(bbox)
            ]
        
        results = []
        if node.left:
            results.extend(self._query_node(node.left, bbox))
        if node.right:
            results.extend(self._query_node(node.right, bbox))
        
        return results


@dataclass
class AABBNode:
    """Node in AABB tree."""
    bounding_box: Optional[BoundingBox] = None
    elements: List[ModelElement] = field(default_factory=list)
    is_leaf: bool = True
    left: Optional['AABBNode'] = None
    right: Optional['AABBNode'] = None


class ClashDetectionEngine:
    """Engine for detecting clashes between BIM elements."""
    
    DEFAULT_RULES = [
        # Hard clash rules
        ClashRule(
            name="Structural-Architectural Hard Clash",
            clash_type=ClashType.HARD_CLASH,
            element_types_a=["IfcColumn", "IfcBeam"],
            element_types_b=["IfcWall", "IfcDoor", "IfcWindow"],
            disciplines_a=[Discipline.STRUCTURAL],
            disciplines_b=[Discipline.ARCHITECTURAL],
            severity=ClashSeverity.CRITICAL
        ),
        ClashRule(
            name="MEP-MEP Hard Clash",
            clash_type=ClashType.HARD_CLASH,
            element_types_a=["IfcDistributionElement"],
            element_types_b=["IfcDistributionElement"],
            disciplines_a=[Discipline.MEP],
            disciplines_b=[Discipline.MEP],
            severity=ClashSeverity.HIGH
        ),
        # Clearance rules
        ClashRule(
            name="MEP Clearance",
            clash_type=ClashType.CLEARANCE_VIOLATION,
            element_types_a=["IfcDistributionElement"],
            element_types_b=["IfcWall", "IfcSlab"],
            clearance=0.05,  # 50mm clearance
            severity=ClashSeverity.MEDIUM
        ),
    ]
    
    def __init__(self, rules: Optional[List[ClashRule]] = None):
        self.rules = rules or self.DEFAULT_RULES
        self.spatial_index: Optional[AABBTree] = None
        self.progress_callback: Optional[Callable[[int, int], None]] = None
    
    def set_progress_callback(self, callback: Callable[[int, int], None]):
        """Set callback for progress updates."""
        self.progress_callback = callback
    
    def detect_clashes(self, elements: List[ModelElement],
                      use_spatial_index: bool = True,
                      parallel: bool = True,
                      max_workers: int = 4) -> ClashResult:
        """Run clash detection on elements."""
        import time
        start_time = time.time()
        
        result = ClashResult(
            id=str(uuid.uuid4()),
            run_at=datetime.utcnow(),
            total_elements_checked=len(elements)
        )
        
        # Build spatial index
        if use_spatial_index:
            self.spatial_index = AABBTree()
            self.spatial_index.build(elements)
        
        # Generate element pairs to check
        pairs = self._generate_pairs(elements, use_spatial_index)
        result.total_pairs_checked = len(pairs)
        
        logger.info(f"Checking {len(pairs)} pairs from {len(elements)} elements")
        
        # Check pairs
        if parallel and len(pairs) > 1000:
            clashes = self._check_pairs_parallel(pairs, max_workers)
        else:
            clashes = self._check_pairs_sequential(pairs)
        
        result.clashes = clashes
        result.execution_time_ms = (time.time() - start_time) * 1000
        result.rules_applied = [r.name for r in self.rules if r.enabled]
        
        logger.info(f"Clash detection complete: {len(clashes)} clashes found in {result.execution_time_ms:.2f}ms")
        
        return result
    
    def _generate_pairs(self, elements: List[ModelElement],
                       use_spatial_index: bool) -> List[Tuple[ModelElement, ModelElement]]:
        """Generate pairs of elements to check."""
        pairs = []
        
        for i, elem_a in enumerate(elements):
            if use_spatial_index and self.spatial_index:
                # Query spatial index for potential intersections
                candidates = self.spatial_index.query_intersections(elem_a.bounding_box)
                for elem_b in candidates:
                    if elem_a.id < elem_b.id:  # Avoid duplicates
                        pairs.append((elem_a, elem_b))
            else:
                # Brute force
                for elem_b in elements[i+1:]:
                    pairs.append((elem_a, elem_b))
            
            if self.progress_callback and i % 100 == 0:
                self.progress_callback(i, len(elements))
        
        return pairs
    
    def _check_pairs_sequential(self, 
                                pairs: List[Tuple[ModelElement, ModelElement]]) -> List[Clash]:
        """Check pairs sequentially."""
        clashes = []
        for i, (elem_a, elem_b) in enumerate(pairs):
            clash = self._check_pair(elem_a, elem_b)
            if clash:
                clashes.append(clash)
            
            if self.progress_callback and i % 1000 == 0:
                self.progress_callback(i, len(pairs))
        
        return clashes
    
    def _check_pairs_parallel(self, 
                             pairs: List[Tuple[ModelElement, ModelElement]],
                             max_workers: int) -> List[Clash]:
        """Check pairs in parallel."""
        clashes = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._check_pair, elem_a, elem_b): (elem_a, elem_b)
                for elem_a, elem_b in pairs
            }
            
            for i, future in enumerate(as_completed(futures)):
                clash = future.result()
                if clash:
                    clashes.append(clash)
                
                if self.progress_callback and i % 1000 == 0:
                    self.progress_callback(i, len(pairs))
        
        return clashes
    
    def _check_pair(self, elem_a: ModelElement, 
                   elem_b: ModelElement) -> Optional[Clash]:
        """Check a pair of elements for clashes."""
        # Check if bounding boxes intersect
        if not elem_a.bounding_box.intersects(elem_b.bounding_box):
            return None
        
        # Find applicable rules
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if self._rule_applies(rule, elem_a, elem_b):
                clash = self._create_clash(elem_a, elem_b, rule)
                if clash:
                    return clash
        
        return None
    
    def _rule_applies(self, rule: ClashRule, elem_a: ModelElement,
                     elem_b: ModelElement) -> bool:
        """Check if rule applies to element pair."""
        # Check element types
        type_a_match = elem_a.element_type.value in rule.element_types_a
        type_b_match = elem_b.element_type.value in rule.element_types_b
        
        if not (type_a_match and type_b_match):
            # Try reversed
            type_a_match = elem_b.element_type.value in rule.element_types_a
            type_b_match = elem_a.element_type.value in rule.element_types_b
        
        if not (type_a_match and type_b_match):
            return False
        
        # Check disciplines if specified
        if rule.disciplines_a:
            if elem_a.discipline not in rule.disciplines_a:
                return False
        if rule.disciplines_b:
            if elem_b.discipline not in rule.disciplines_b:
                return False
        
        return True
    
    def _create_clash(self, elem_a: ModelElement, elem_b: ModelElement,
                     rule: ClashRule) -> Optional[Clash]:
        """Create a clash object from intersecting elements."""
        # Calculate intersection
        intersection = self._calculate_intersection(
            elem_a.bounding_box, elem_b.bounding_box
        )
        
        if not intersection:
            return None
        
        volume, center, penetration = intersection
        
        # Check clearance for clearance violations
        if rule.clash_type == ClashType.CLEARANCE_VIOLATION:
            if penetration >= rule.clearance:
                return None
        
        return Clash(
            id=str(uuid.uuid4()),
            clash_type=rule.clash_type,
            element_a=elem_a,
            element_b=elem_b,
            intersection_volume=volume,
            intersection_center=center,
            penetration_depth=penetration,
            severity=rule.severity
        )
    
    def _calculate_intersection(self, bbox_a: BoundingBox, 
                                bbox_b: BoundingBox) -> Optional[Tuple[float, Point3D, float]]:
        """Calculate intersection volume and center."""
        # Calculate intersection bounds
        min_x = max(bbox_a.min_point.x, bbox_b.min_point.x)
        min_y = max(bbox_a.min_point.y, bbox_b.min_point.y)
        min_z = max(bbox_a.min_point.z, bbox_b.min_point.z)
        max_x = min(bbox_a.max_point.x, bbox_b.max_point.x)
        max_y = min(bbox_a.max_point.y, bbox_b.max_point.y)
        max_z = min(bbox_a.max_point.z, bbox_b.max_point.z)
        
        # Check if there's an intersection
        if min_x >= max_x or min_y >= max_y or min_z >= max_z:
            return None
        
        # Calculate volume
        volume = (max_x - min_x) * (max_y - min_y) * (max_z - min_z)
        
        # Calculate center
        center = Point3D(
            (min_x + max_x) / 2,
            (min_y + max_y) / 2,
            (min_z + max_z) / 2
        )
        
        # Calculate maximum penetration depth
        penetration = max(
            max_x - min_x,
            max_y - min_y,
            max_z - min_z
        )
        
        return volume, center, penetration
    
    def resolve_clash(self, clash: Clash, resolved_by: str,
                     notes: str = "") -> bool:
        """Mark a clash as resolved."""
        clash.status = ClashStatus.RESOLVED
        clash.resolved_at = datetime.utcnow()
        clash.resolved_by = resolved_by
        clash.resolution_notes = notes
        
        logger.info(f"Clash {clash.id} resolved by {resolved_by}")
        return True
    
    def ignore_clash(self, clash: Clash, reason: str) -> bool:
        """Mark a clash as ignored."""
        clash.status = ClashStatus.IGNORED
        clash.resolution_notes = reason
        
        logger.info(f"Clash {clash.id} ignored: {reason}")
        return True
