"""
Temporary Works - Scaffolding/Shoring Modeling
Temporary structure design and analysis
"""
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4
import math

logger = logging.getLogger(__name__)


class TemporaryWorkType(Enum):
    """Types of temporary works"""
    SCAFFOLDING = "scaffolding"
    SHORING = "shoring"
    FORMWORK = "formwork"
    FALSEWORK = "falsework"
    TRENCH_BOX = "trench_box"
    COFFERDAM = "cofferdam"
    CRANE_BASE = "crane_base"
    ACCESS_PLATFORM = "access_platform"


class TemporaryWorkStatus(Enum):
    """Temporary work status"""
    PLANNED = "planned"
    DESIGNED = "designed"
    APPROVED = "approved"
    INSTALLED = "installed"
    IN_USE = "in_use"
    BEING_REMOVED = "being_removed"
    REMOVED = "removed"


@dataclass
class TemporaryWork:
    """Temporary work structure"""
    work_id: str
    project_id: str
    name: str
    description: str
    work_type: TemporaryWorkType
    status: TemporaryWorkStatus
    location: Dict[str, Any] = field(default_factory=dict)
    design_parameters: Dict[str, Any] = field(default_factory=dict)
    load_capacity: Dict[str, float] = field(default_factory=dict)
    installation_date: Optional[datetime] = None
    removal_date: Optional[datetime] = None
    designed_by: str = ""
    approved_by: str = ""
    inspection_records: List[Dict] = field(default_factory=list)
    associated_permanent_elements: List[str] = field(default_factory=list)
    safety_factors: Dict[str, float] = field(default_factory=dict)


@dataclass
class ScaffoldBay:
    """Scaffolding bay configuration"""
    bay_id: str
    length_m: float
    width_m: float
    height_m: float
    load_class: str  # Light, Medium, Heavy
    number_of_lifts: int
    has_stair_access: bool = False
    has_guardrails: bool = True
    has_toeboards: bool = True


@dataclass
class ShoringTower:
    """Shoring tower configuration"""
    tower_id: str
    height_m: float
    base_area_m2: float
    leg_spacing_m: float
    load_capacity_kn: float
    number_of_legs: int = 4
    has_base_jacks: bool = True
    has_u_heads: bool = True
    bracing_pattern: str = "cross"  # cross, zigzag, etc.


class ScaffoldingDesigner:
    """Designs scaffolding systems"""
    
    def __init__(self):
        self._scaffolds: Dict[str, TemporaryWork] = {}
        self._bays: Dict[str, ScaffoldBay] = {}
    
    def design_scaffold(self, project_id: str,
                        name: str,
                        location: Dict,
                        height_m: float,
                        length_m: float,
                        width_m: float,
                        load_class: str = "Medium",
                        designed_by: str = "") -> TemporaryWork:
        """Design scaffolding system"""
        # Calculate number of bays
        bay_length = 2.5  # Standard bay length
        num_bays = math.ceil(length_m / bay_length)
        
        # Calculate number of lifts
        lift_height = 2.0  # Standard lift height
        num_lifts = math.ceil(height_m / lift_height)
        
        # Calculate load capacity
        load_classes = {
            'Light': 1.5,    # kN/m2
            'Medium': 2.0,
            'Heavy': 3.0
        }
        
        load_capacity = load_classes.get(load_class, 2.0)
        
        scaffold = TemporaryWork(
            work_id=str(uuid4()),
            project_id=project_id,
            name=name,
            description=f"{load_class} duty scaffold",
            work_type=TemporaryWorkType.SCAFFOLDING,
            status=TemporaryWorkStatus.DESIGNED,
            location=location,
            design_parameters={
                'height_m': height_m,
                'length_m': length_m,
                'width_m': width_m,
                'bay_length_m': bay_length,
                'num_bays': num_bays,
                'lift_height_m': lift_height,
                'num_lifts': num_lifts,
                'load_class': load_class
            },
            load_capacity={
                'uniform_load_kn_m2': load_capacity,
                'point_load_kn': load_capacity * 1.5
            },
            designed_by=designed_by,
            safety_factors={
                'working_load': 2.0,
                'overturning': 1.5,
                'foundation': 2.0
            }
        )
        
        self._scaffolds[scaffold.work_id] = scaffold
        
        # Create bays
        for i in range(num_bays):
            bay = ScaffoldBay(
                bay_id=f"{scaffold.work_id}-bay-{i+1}",
                length_m=bay_length,
                width_m=width_m,
                height_m=height_m,
                load_class=load_class,
                number_of_lifts=num_lifts
            )
            self._bays[bay.bay_id] = bay
        
        logger.info(f"Designed scaffold: {scaffold.work_id}")
        
        return scaffold
    
    def calculate_material_quantities(self, scaffold_id: str) -> Dict:
        """Calculate scaffolding material quantities"""
        scaffold = self._scaffolds.get(scaffold_id)
        if not scaffold:
            return {}
        
        params = scaffold.design_parameters
        
        num_bays = params.get('num_bays', 1)
        num_lifts = params.get('num_lifts', 1)
        
        # Standard quantities per bay per lift
        quantities = {
            'standards': num_bays * 2 * (num_lifts + 1),  # Vertical tubes
            'ledgers': num_bays * num_lifts,  # Horizontal tubes
            'transoms': num_bays * num_lifts,  # Cross tubes
            'braces': num_bays * num_lifts * 2,  # Diagonal braces
            'base_plates': num_bays * 2,
            'decking_panels': num_bays * num_lifts,
            'guardrails': num_bays * (num_lifts + 1),
            'toeboards': num_bays * num_lifts * 2
        }
        
        return quantities
    
    def check_stability(self, scaffold_id: str,
                        wind_load_kn_m2: float = 0.5) -> Dict:
        """Check scaffold stability"""
        scaffold = self._scaffolds.get(scaffold_id)
        if not scaffold:
            return {'stable': False, 'error': 'Scaffold not found'}
        
        params = scaffold.design_parameters
        height = params.get('height_m', 0)
        width = params.get('width_m', 0)
        
        # Check height-to-width ratio
        h_w_ratio = height / width if width > 0 else float('inf')
        
        issues = []
        
        if h_w_ratio > 4:
            issues.append("Height-to-width ratio exceeds 4:1 - bracing required")
        
        if height > 30:
            issues.append("Height exceeds 30m - engineered design required")
        
        # Calculate overturning moment
        wind_force = wind_load_kn_m2 * height * params.get('length_m', 0)
        overturning_moment = wind_force * height / 2
        
        return {
            'stable': len(issues) == 0,
            'height_width_ratio': h_w_ratio,
            'overturning_moment_knm': overturning_moment,
            'issues': issues,
            'recommendations': [
                "Install tie-ins at maximum 4m vertical spacing" if height > 4 else None,
                "Install face bracing if height exceeds 2m" if height > 2 else None
            ]
        }


class ShoringDesigner:
    """Designs shoring systems"""
    
    def __init__(self):
        self._shoring: Dict[str, TemporaryWork] = {}
        self._towers: Dict[str, ShoringTower] = {}
    
    def design_shoring(self, project_id: str,
                       name: str,
                       location: Dict,
                       height_m: float,
                       load_kn: float,
                       load_distribution: str = "uniform",
                       designed_by: str = "") -> TemporaryWork:
        """Design shoring system"""
        # Calculate number of towers needed
        tower_capacity = 50.0  # kN per tower (typical)
        num_towers = math.ceil(load_kn / tower_capacity)
        
        # Calculate tower spacing
        if num_towers > 1:
            tower_spacing = 1.5  # meters
        else:
            tower_spacing = 0
        
        shoring = TemporaryWork(
            work_id=str(uuid4()),
            project_id=project_id,
            name=name,
            description=f"Shoring for {load_kn}kN load",
            work_type=TemporaryWorkType.SHORING,
            status=TemporaryWorkStatus.DESIGNED,
            location=location,
            design_parameters={
                'height_m': height_m,
                'design_load_kn': load_kn,
                'num_towers': num_towers,
                'tower_spacing_m': tower_spacing,
                'load_distribution': load_distribution
            },
            load_capacity={
                'working_load_kn': load_kn,
                'ultimate_load_kn': load_kn * 2.0
            },
            designed_by=designed_by,
            safety_factors={
                'working_load': 2.0,
                'buckling': 3.0,
                'foundation': 2.0
            }
        )
        
        self._shoring[shoring.work_id] = shoring
        
        # Create towers
        for i in range(num_towers):
            tower = ShoringTower(
                tower_id=f"{shoring.work_id}-tower-{i+1}",
                height_m=height_m,
                base_area_m2=0.25,  # 500mm x 500mm
                leg_spacing_m=0.5,
                load_capacity_kn=tower_capacity
            )
            self._towers[tower.tower_id] = tower
        
        logger.info(f"Designed shoring: {shoring.work_id}")
        
        return shoring
    
    def calculate_leg_loads(self, shoring_id: str) -> Dict:
        """Calculate load on each shoring leg"""
        shoring = self._shoring.get(shoring_id)
        if not shoring:
            return {}
        
        params = shoring.design_parameters
        total_load = params.get('design_load_kn', 0)
        num_towers = params.get('num_towers', 1)
        
        load_per_tower = total_load / num_towers
        load_per_leg = load_per_tower / 4  # 4 legs per tower
        
        return {
            'total_load_kn': total_load,
            'load_per_tower_kn': load_per_tower,
            'load_per_leg_kn': load_per_leg,
            'utilization_percent': (load_per_leg / 50.0) * 100  # Assuming 50kN capacity
        }
    
    def check_buckling(self, shoring_id: str) -> Dict:
        """Check shoring for buckling"""
        shoring = self._shoring.get(shoring_id)
        if not shoring:
            return {'safe': False}
        
        params = shoring.design_parameters
        height = params.get('height_m', 0)
        
        # Simplified buckling check
        # Critical buckling load for typical shoring leg
        E = 210000  # MPa (steel modulus)
        I = 10000   # mm4 (typical moment of inertia)
        L = height * 1000  # mm
        
        P_critical = (math.pi**2 * E * I) / (L**2) / 1000  # kN
        
        leg_loads = self.calculate_leg_loads(shoring_id)
        actual_load = leg_loads.get('load_per_leg_kn', 0)
        
        safety_factor = P_critical / actual_load if actual_load > 0 else float('inf')
        
        return {
            'safe': safety_factor >= 3.0,
            'critical_load_kn': P_critical,
            'actual_load_kn': actual_load,
            'safety_factor': safety_factor
        }


class FormworkDesigner:
    """Designs formwork systems"""
    
    def __init__(self):
        self._formwork: Dict[str, TemporaryWork] = {}
    
    def design_wall_formwork(self, project_id: str,
                             name: str,
                             wall_length_m: float,
                             wall_height_m: float,
                             wall_thickness_mm: float,
                             concrete_pressure_kpa: float = 25.0,
                             designed_by: str = "") -> TemporaryWork:
        """Design wall formwork"""
        # Calculate concrete pressure
        # Simplified: pressure increases with depth up to certain limit
        max_pressure = min(concrete_pressure_kpa * wall_height_m, 100.0)
        
        # Calculate panel requirements
        panel_height = 2.7  # Standard panel height
        num_panels_height = math.ceil(wall_height_m / panel_height)
        
        panel_width = 1.2  # Standard panel width
        num_panels_width = math.ceil(wall_length_m / panel_width)
        
        formwork = TemporaryWork(
            work_id=str(uuid4()),
            project_id=project_id,
            name=name,
            description=f"Wall formwork - {wall_length_m}m x {wall_height_m}m",
            work_type=TemporaryWorkType.FORMWORK,
            status=TemporaryWorkStatus.DESIGNED,
            design_parameters={
                'wall_length_m': wall_length_m,
                'wall_height_m': wall_height_m,
                'wall_thickness_mm': wall_thickness_mm,
                'concrete_pressure_kpa': max_pressure,
                'panel_height_m': panel_height,
                'panel_width_m': panel_width,
                'num_panels_height': num_panels_height,
                'num_panels_width': num_panels_width
            },
            load_capacity={
                'concrete_pressure_kpa': max_pressure,
                'pour_rate_m_h': 1.5
            },
            designed_by=designed_by,
            safety_factors={
                'concrete_pressure': 1.5,
                'panel_strength': 2.0
            }
        )
        
        self._formwork[formwork.work_id] = formwork
        
        logger.info(f"Designed formwork: {formwork.work_id}")
        
        return formwork
    
    def calculate_formwork_quantities(self, formwork_id: str) -> Dict:
        """Calculate formwork material quantities"""
        formwork = self._formwork.get(formwork_id)
        if not formwork:
            return {}
        
        params = formwork.design_parameters
        
        num_panels = params.get('num_panels_height', 0) * params.get('num_panels_width', 0)
        
        # Each panel needs ties, walers, and braces
        quantities = {
            'panels': num_panels * 2,  # Both sides
            'form_ties': num_panels * 4,
            'walers_m': params.get('wall_length_m', 0) * params.get('num_panels_height', 0) * 2,
            'braces': num_panels * 2,
            'release_agent_liters': num_panels * 0.5
        }
        
        return quantities


class TemporaryWorksManager:
    """Manages temporary works across project"""
    
    def __init__(self):
        self.scaffolding = ScaffoldingDesigner()
        self.shoring = ShoringDesigner()
        self.formwork = FormworkDesigner()
        self._inspections: Dict[str, List[Dict]] = {}
    
    def schedule_inspection(self, work_id: str,
                            inspection_type: str,
                            scheduled_date: datetime,
                            inspector: str) -> Dict:
        """Schedule temporary works inspection"""
        inspection = {
            'inspection_id': str(uuid4()),
            'work_id': work_id,
            'type': inspection_type,  # pre-use, weekly, after_event, etc.
            'scheduled_date': scheduled_date.isoformat(),
            'inspector': inspector,
            'status': 'scheduled'
        }
        
        if work_id not in self._inspections:
            self._inspections[work_id] = []
        
        self._inspections[work_id].append(inspection)
        
        return inspection
    
    def record_inspection(self, inspection_id: str,
                          findings: str,
                          result: str,  # pass, fail, pass_with_conditions
                          photos: List[str] = None) -> Dict:
        """Record inspection results"""
        # Find inspection
        for work_id, inspections in self._inspections.items():
            for inspection in inspections:
                if inspection['inspection_id'] == inspection_id:
                    inspection['findings'] = findings
                    inspection['result'] = result
                    inspection['photos'] = photos or []
                    inspection['completed_at'] = datetime.utcnow().isoformat()
                    inspection['status'] = 'completed'
                    
                    return inspection
        
        return None
    
    def get_project_temporary_works(self, project_id: str) -> List[TemporaryWork]:
        """Get all temporary works for project"""
        all_works = []
        
        all_works.extend([
            w for w in self.scaffolding._scaffolds.values()
            if w.project_id == project_id
        ])
        
        all_works.extend([
            w for w in self.shoring._shoring.values()
            if w.project_id == project_id
        ])
        
        all_works.extend([
            w for w in self.formwork._formwork.values()
            if w.project_id == project_id
        ])
        
        return all_works


# Global instance
temporary_works = TemporaryWorksManager()