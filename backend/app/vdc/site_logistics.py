"""
Site Logistics - Crane Reach Analysis
Construction site logistics and equipment planning
"""
import json
import logging
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4
import math

logger = logging.getLogger(__name__)


class EquipmentType(Enum):
    """Construction equipment types"""
    TOWER_CRANE = "tower_crane"
    MOBILE_CRANE = "mobile_crane"
    CRAWLER_CRANE = "crawler_crane"
    FORKLIFT = "forklift"
    TELEHANDLER = "telehandler"
    CONCRETE_PUMP = "concrete_pump"
    EXCAVATOR = "excavator"


class EquipmentStatus(Enum):
    """Equipment status"""
    AVAILABLE = "available"
    SCHEDULED = "scheduled"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    OFF_SITE = "off_site"


@dataclass
class Crane:
    """Crane specification"""
    crane_id: str
    name: str
    equipment_type: EquipmentType
    model: str
    max_capacity_tons: float
    max_radius_m: float
    max_height_m: float
    jib_length_m: float
    counterweight_tons: float
    base_dimensions: Dict[str, float] = field(default_factory=dict)
    lift_chart: Dict[str, List[Dict]] = field(default_factory=dict)
    location: Dict[str, float] = field(default_factory=dict)
    status: EquipmentStatus = EquipmentStatus.AVAILABLE


@dataclass
class LiftPlan:
    """Crane lift plan"""
    plan_id: str
    crane_id: str
    load_weight_tons: float
    load_dimensions: Dict[str, float]
    pickup_location: Dict[str, float]
    setdown_location: Dict[str, float]
    required_radius_m: float
    required_height_m: float
    planned_date: datetime
    rigging_config: Dict[str, Any] = field(default_factory=dict)
    safety_factors: Dict[str, float] = field(default_factory=dict)
    approved: bool = False
    approved_by: str = ""


@dataclass
class SiteZone:
    """Site logistics zone"""
    zone_id: str
    name: str
    zone_type: str  # laydown, access, crane_stand, etc.
    polygon: List[Tuple[float, float]]
    elevation_m: float
    capacity_kg_m2: float
    restrictions: List[str] = field(default_factory=list)
    active_hours: Dict[str, str] = field(default_factory=dict)


class CraneReachAnalyzer:
    """Analyzes crane reach and capacity"""
    
    def __init__(self):
        self._cranes: Dict[str, Crane] = {}
        self._lift_plans: Dict[str, LiftPlan] = {}
    
    def add_crane(self, crane: Crane):
        """Add crane to analysis"""
        self._cranes[crane.crane_id] = crane
    
    def calculate_reach(self, crane_id: str,
                        load_weight_tons: float) -> Dict:
        """Calculate crane reach for given load"""
        crane = self._cranes.get(crane_id)
        if not crane:
            return {'error': 'Crane not found'}
        
        # Get lift chart for this load
        lift_chart = crane.lift_chart
        
        # Find maximum radius for this load
        max_radius = 0
        max_height = 0
        
        for radius_entry in lift_chart.get(str(int(load_weight_tons)), []):
            radius = radius_entry.get('radius_m', 0)
            height = radius_entry.get('height_m', 0)
            
            if radius > max_radius:
                max_radius = radius
                max_height = height
        
        # Calculate coverage area
        coverage_area = math.pi * max_radius ** 2
        
        return {
            'crane_id': crane_id,
            'load_weight_tons': load_weight_tons,
            'max_radius_m': max_radius,
            'max_height_m': max_height,
            'coverage_area_m2': coverage_area,
            'utilization_percent': (load_weight_tons / crane.max_capacity_tons) * 100
        }
    
    def check_lift_feasibility(self, crane_id: str,
                               load_weight_tons: float,
                               radius_m: float,
                               height_m: float) -> Dict:
        """Check if lift is feasible with given crane"""
        crane = self._cranes.get(crane_id)
        if not crane:
            return {'feasible': False, 'error': 'Crane not found'}
        
        # Check basic limits
        if radius_m > crane.max_radius_m:
            return {
                'feasible': False,
                'error': f'Radius {radius_m}m exceeds maximum {crane.max_radius_m}m'
            }
        
        if height_m > crane.max_height_m:
            return {
                'feasible': False,
                'error': f'Height {height_m}m exceeds maximum {crane.max_height_m}m'
            }
        
        # Check lift chart
        lift_chart = crane.lift_chart
        capacity_at_radius = None
        
        for entry in lift_chart.get(str(int(load_weight_tons)), []):
            if entry.get('radius_m', 0) >= radius_m:
                capacity_at_radius = entry.get('capacity_tons', 0)
                break
        
        if capacity_at_radius is None:
            return {
                'feasible': False,
                'error': 'Load exceeds capacity at this radius'
            }
        
        if load_weight_tons > capacity_at_radius:
            return {
                'feasible': False,
                'error': f'Load {load_weight_tons}t exceeds capacity {capacity_at_radius}t at {radius_m}m'
            }
        
        # Calculate safety factor
        safety_factor = capacity_at_radius / load_weight_tons
        
        return {
            'feasible': True,
            'capacity_at_radius_tons': capacity_at_radius,
            'safety_factor': safety_factor,
            'utilization_percent': (load_weight_tons / capacity_at_radius) * 100,
            'recommendations': [
                "Lift is feasible with current configuration"
            ] if safety_factor >= 1.5 else [
                "Lift is feasible but near capacity - consider larger crane"
            ]
        }
    
    def create_lift_plan(self, crane_id: str,
                         load_weight_tons: float,
                         load_dimensions: Dict[str, float],
                         pickup_location: Dict[str, float],
                         setdown_location: Dict[str, float],
                         planned_date: datetime) -> LiftPlan:
        """Create crane lift plan"""
        crane = self._cranes.get(crane_id)
        if not crane:
            raise ValueError(f"Crane not found: {crane_id}")
        
        # Calculate required radius
        crane_pos = crane.location
        pickup_dist = math.sqrt(
            (pickup_location['x'] - crane_pos['x'])**2 +
            (pickup_location['y'] - crane_pos['y'])**2
        )
        setdown_dist = math.sqrt(
            (setdown_location['x'] - crane_pos['x'])**2 +
            (setdown_location['y'] - crane_pos['y'])**2
        )
        required_radius = max(pickup_dist, setdown_dist)
        
        # Calculate required height
        required_height = max(
            pickup_location.get('z', 0),
            setdown_location.get('z', 0)
        ) + load_dimensions.get('height', 0) + 5  # 5m clearance
        
        plan = LiftPlan(
            plan_id=str(uuid4()),
            crane_id=crane_id,
            load_weight_tons=load_weight_tons,
            load_dimensions=load_dimensions,
            pickup_location=pickup_location,
            setdown_location=setdown_location,
            required_radius_m=required_radius,
            required_height_m=required_height,
            planned_date=planned_date,
            safety_factors={
                'structural': 2.0,
                'stability': 1.5
            }
        )
        
        self._lift_plans[plan.plan_id] = plan
        
        logger.info(f"Created lift plan: {plan.plan_id}")
        
        return plan
    
    def generate_reach_diagram(self, crane_id: str) -> Dict:
        """Generate crane reach diagram data"""
        crane = self._cranes.get(crane_id)
        if not crane:
            return {}
        
        # Generate reach envelope
        angles = list(range(0, 91, 5))
        reach_points = []
        
        for angle in angles:
            rad = math.radians(angle)
            radius = crane.jib_length_m * math.cos(rad)
            height = crane.jib_length_m * math.sin(rad)
            
            reach_points.append({
                'angle': angle,
                'radius_m': radius,
                'height_m': height
            })
        
        return {
            'crane_id': crane_id,
            'crane_location': crane.location,
            'max_radius_m': crane.max_radius_m,
            'max_height_m': crane.max_height_m,
            'reach_envelope': reach_points,
            'load_chart': crane.lift_chart
        }


class SiteLayoutManager:
    """Manages site layout and logistics zones"""
    
    def __init__(self):
        self._zones: Dict[str, SiteZone] = {}
        self._access_routes: List[Dict] = []
        self._equipment_positions: Dict[str, Dict] = {}
    
    def add_zone(self, zone: SiteZone):
        """Add logistics zone"""
        self._zones[zone.zone_id] = zone
    
    def check_zone_access(self, zone_id: str,
                          equipment_type: str,
                          time: datetime) -> Dict:
        """Check if equipment can access zone"""
        zone = self._zones.get(zone_id)
        if not zone:
            return {'accessible': False, 'error': 'Zone not found'}
        
        # Check time restrictions
        active_hours = zone.active_hours
        if active_hours:
            hour = time.hour
            start = int(active_hours.get('start', '00:00').split(':')[0])
            end = int(active_hours.get('end', '23:59').split(':')[0])
            
            if not (start <= hour <= end):
                return {
                    'accessible': False,
                    'error': f'Zone not accessible at {time.hour}:00'
                }
        
        # Check equipment restrictions
        if equipment_type in zone.restrictions:
            return {
                'accessible': False,
                'error': f'{equipment_type} not allowed in this zone'
            }
        
        return {
            'accessible': True,
            'zone_capacity_kg_m2': zone.capacity_kg_m2
        }
    
    def optimize_crane_position(self, crane_id: str,
                                lift_locations: List[Dict]) -> Dict:
        """Optimize crane position for multiple lifts"""
        if not lift_locations:
            return {'error': 'No lift locations provided'}
        
        # Calculate centroid of lift locations
        sum_x = sum(loc['x'] for loc in lift_locations)
        sum_y = sum(loc['y'] for loc in lift_locations)
        
        centroid = {
            'x': sum_x / len(lift_locations),
            'y': sum_y / len(lift_locations)
        }
        
        # Calculate maximum distance from centroid
        max_dist = 0
        for loc in lift_locations:
            dist = math.sqrt(
                (loc['x'] - centroid['x'])**2 +
                (loc['y'] - centroid['y'])**2
            )
            if dist > max_dist:
                max_dist = dist
        
        return {
            'optimal_position': centroid,
            'max_radius_required_m': max_dist,
            'coverage_assessment': 'adequate' if max_dist < 50 else 'check crane capacity'
        }


class DeliveryScheduler:
    """Schedules material deliveries"""
    
    def __init__(self):
        self._deliveries: Dict[str, Dict] = {}
        self._constraints: Dict[str, Any] = {
            'max_trucks_per_hour': 4,
            'delivery_hours_start': 7,
            'delivery_hours_end': 17,
            'unloading_time_minutes': 30
        }
    
    def schedule_delivery(self, material_type: str,
                          quantity: float,
                          unit: str,
                          requested_time: datetime,
                          unloading_zone: str) -> Dict:
        """Schedule material delivery"""
        delivery_id = str(uuid4())
        
        # Check constraints
        scheduled_time = self._find_available_slot(requested_time)
        
        delivery = {
            'delivery_id': delivery_id,
            'material_type': material_type,
            'quantity': quantity,
            'unit': unit,
            'scheduled_time': scheduled_time.isoformat(),
            'unloading_zone': unloading_zone,
            'status': 'scheduled'
        }
        
        self._deliveries[delivery_id] = delivery
        
        return delivery
    
    def _find_available_slot(self, requested_time: datetime) -> datetime:
        """Find available delivery slot"""
        # Simplified - would check existing deliveries
        return requested_time
    
    def get_daily_schedule(self, date: datetime) -> List[Dict]:
        """Get delivery schedule for date"""
        date_str = date.strftime('%Y-%m-%d')
        
        return [
            d for d in self._deliveries.values()
            if d['scheduled_time'].startswith(date_str)
        ]


# Global instances
crane_analyzer = CraneReachAnalyzer()
site_layout = SiteLayoutManager()
delivery_scheduler = DeliveryScheduler()