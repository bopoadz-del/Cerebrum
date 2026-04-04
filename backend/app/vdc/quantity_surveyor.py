"""
Quantity Surveyor - Digital Takeoff Tools
Automated quantity extraction and cost estimation
"""
import json
import logging
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class MeasurementType(Enum):
    """Types of measurements"""
    COUNT = "count"
    LENGTH = "length"
    AREA = "area"
    VOLUME = "volume"
    WEIGHT = "weight"
    TIME = "time"


class MeasurementStatus(Enum):
    """Measurement status"""
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    LOCKED = "locked"


@dataclass
class Measurement:
    """Single measurement"""
    measurement_id: str
    item_code: str
    description: str
    measurement_type: MeasurementType
    quantity: Decimal
    unit: str
    unit_rate: Decimal
    total_cost: Decimal
    location: str = ""
    drawing_reference: str = ""
    measured_by: str = ""
    measured_at: datetime = field(default_factory=datetime.utcnow)
    status: MeasurementStatus = MeasurementStatus.DRAFT
    notes: str = ""
    related_elements: List[str] = field(default_factory=list)
    wbs_code: str = ""


@dataclass
class TakeoffItem:
    """Takeoff item specification"""
    item_id: str
    item_code: str
    description: str
    category: str
    measurement_type: MeasurementType
    unit: str
    unit_rate: Decimal
    specifications: Dict[str, Any] = field(default_factory=dict)
    applicable_elements: List[str] = field(default_factory=list)


@dataclass
class QuantityTakeoff:
    """Complete quantity takeoff"""
    takeoff_id: str
    project_id: str
    name: str
    description: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    measurements: List[Measurement] = field(default_factory=list)
    total_cost: Decimal = Decimal('0')
    status: MeasurementStatus = MeasurementStatus.DRAFT


class DigitalTakeoff:
    """Digital takeoff from BIM models"""
    
    def __init__(self):
        self._takeoffs: Dict[str, QuantityTakeoff] = {}
        self._item_library: Dict[str, TakeoffItem] = {}
    
    def create_takeoff(self, project_id: str, name: str,
                       description: str = "",
                       created_by: str = "") -> QuantityTakeoff:
        """Create new quantity takeoff"""
        takeoff = QuantityTakeoff(
            takeoff_id=str(uuid4()),
            project_id=project_id,
            name=name,
            description=description,
            created_by=created_by
        )
        
        self._takeoffs[takeoff.takeoff_id] = takeoff
        
        logger.info(f"Created takeoff: {takeoff.takeoff_id}")
        
        return takeoff
    
    def add_measurement(self, takeoff_id: str,
                        measurement: Measurement) -> bool:
        """Add measurement to takeoff"""
        takeoff = self._takeoffs.get(takeoff_id)
        if not takeoff:
            return False
        
        # Calculate total cost
        measurement.total_cost = measurement.quantity * measurement.unit_rate
        
        takeoff.measurements.append(measurement)
        
        # Update total
        takeoff.total_cost += measurement.total_cost
        
        return True
    
    def measure_from_elements(self, takeoff_id: str,
                              item_code: str,
                              elements: List[Dict],
                              unit_rate: Decimal = None) -> List[Measurement]:
        """Create measurements from BIM elements"""
        takeoff = self._takeoffs.get(takeoff_id)
        if not takeoff:
            return []
        
        item = self._item_library.get(item_code)
        if not item:
            return []
        
        measurements = []
        
        for element in elements:
            quantity = self._extract_quantity(element, item.measurement_type)
            
            if quantity > 0:
                measurement = Measurement(
                    measurement_id=str(uuid4()),
                    item_code=item_code,
                    description=f"{item.description} - {element.get('name', '')}",
                    measurement_type=item.measurement_type,
                    quantity=Decimal(str(quantity)),
                    unit=item.unit,
                    unit_rate=unit_rate or item.unit_rate,
                    total_cost=Decimal('0'),
                    related_elements=[element.get('id', '')],
                    wbs_code=item.category
                )
                
                measurement.total_cost = measurement.quantity * measurement.unit_rate
                
                self.add_measurement(takeoff_id, measurement)
                measurements.append(measurement)
        
        return measurements
    
    def _extract_quantity(self, element: Dict,
                          measurement_type: MeasurementType) -> float:
        """Extract quantity from element based on measurement type"""
        params = element.get('parameters', {})
        
        if measurement_type == MeasurementType.COUNT:
            return 1
        
        elif measurement_type == MeasurementType.LENGTH:
            return params.get('Length', params.get('length', 0))
        
        elif measurement_type == MeasurementType.AREA:
            return params.get('Area', params.get('area', 0))
        
        elif measurement_type == MeasurementType.VOLUME:
            return params.get('Volume', params.get('volume', 0))
        
        elif measurement_type == MeasurementType.WEIGHT:
            return params.get('Weight', params.get('weight', 0))
        
        return 0
    
    def get_takeoff_summary(self, takeoff_id: str) -> Dict:
        """Get takeoff summary"""
        takeoff = self._takeoffs.get(takeoff_id)
        if not takeoff:
            return None
        
        # Group by item code
        by_item = {}
        for m in takeoff.measurements:
            if m.item_code not in by_item:
                by_item[m.item_code] = {
                    'description': m.description,
                    'unit': m.unit,
                    'total_quantity': Decimal('0'),
                    'total_cost': Decimal('0'),
                    'count': 0
                }
            
            by_item[m.item_code]['total_quantity'] += m.quantity
            by_item[m.item_code]['total_cost'] += m.total_cost
            by_item[m.item_code]['count'] += 1
        
        # Group by WBS code
        by_wbs = {}
        for m in takeoff.measurements:
            if m.wbs_code not in by_wbs:
                by_wbs[m.wbs_code] = Decimal('0')
            by_wbs[m.wbs_code] += m.total_cost
        
        return {
            'takeoff_id': takeoff_id,
            'name': takeoff.name,
            'total_measurements': len(takeoff.measurements),
            'total_cost': float(takeoff.total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'by_item': {
                k: {
                    'description': v['description'],
                    'unit': v['unit'],
                    'total_quantity': float(v['total_quantity']),
                    'total_cost': float(v['total_cost'].quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                    'count': v['count']
                }
                for k, v in by_item.items()
            },
            'by_wbs': {
                k: float(v.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
                for k, v in by_wbs.items()
            }
        }


class MeasurementCalculator:
    """Calculates measurements from geometry"""
    
    @staticmethod
    def calculate_length(start_point: Tuple[float, float, float],
                         end_point: Tuple[float, float, float]) -> float:
        """Calculate length between two points"""
        import math
        
        dx = end_point[0] - start_point[0]
        dy = end_point[1] - start_point[1]
        dz = end_point[2] - start_point[2]
        
        return math.sqrt(dx**2 + dy**2 + dz**2)
    
    @staticmethod
    def calculate_area_from_points(points: List[Tuple[float, float]]) -> float:
        """Calculate area from polygon points using shoelace formula"""
        n = len(points)
        area = 0.0
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return abs(area) / 2.0
    
    @staticmethod
    def calculate_volume_from_dimensions(length: float,
                                          width: float,
                                          height: float) -> float:
        """Calculate volume from dimensions"""
        return length * width * height
    
    @staticmethod
    def calculate_weight(volume: float,
                         density: float) -> float:
        """Calculate weight from volume and density"""
        return volume * density


class CostDatabase:
    """Cost database for unit rates"""
    
    def __init__(self):
        self._rates: Dict[str, Dict] = {}
        self._location_factors: Dict[str, Decimal] = {}
    
    def add_rate(self, item_code: str,
                 description: str,
                 unit: str,
                 base_rate: Decimal,
                 location: str = "national"):
        """Add unit rate to database"""
        if item_code not in self._rates:
            self._rates[item_code] = {}
        
        self._rates[item_code][location] = {
            'description': description,
            'unit': unit,
            'base_rate': base_rate,
            'effective_date': datetime.utcnow().isoformat()
        }
    
    def get_rate(self, item_code: str,
                 location: str = "national") -> Optional[Decimal]:
        """Get unit rate for item"""
        item_rates = self._rates.get(item_code, {})
        rate_info = item_rates.get(location) or item_rates.get('national')
        
        if not rate_info:
            return None
        
        base_rate = rate_info['base_rate']
        
        # Apply location factor
        location_factor = self._location_factors.get(location, Decimal('1.0'))
        
        return base_rate * location_factor
    
    def set_location_factor(self, location: str, factor: Decimal):
        """Set location adjustment factor"""
        self._location_factors[location] = factor


class TakeoffExporter:
    """Exports takeoff data"""
    
    def export_to_excel(self, takeoff: QuantityTakeoff,
                        output_path: str = None) -> str:
        """Export takeoff to Excel"""
        output_path = output_path or f"/takeoffs/{takeoff.takeoff_id}.xlsx"
        
        # In practice, this would generate actual Excel file
        logger.info(f"Exported takeoff to Excel: {output_path}")
        
        return output_path
    
    def export_to_csv(self, takeoff: QuantityTakeoff,
                      output_path: str = None) -> str:
        """Export takeoff to CSV"""
        output_path = output_path or f"/takeoffs/{takeoff.takeoff_id}.csv"
        
        logger.info(f"Exported takeoff to CSV: {output_path}")
        
        return output_path
    
    def export_to_cobie(self, takeoff: QuantityTakeoff) -> Dict:
        """Export takeoff to COBie format"""
        return {
            'type': 'COBie',
            'version': '2.4',
            'project': takeoff.project_id,
            'takeoff': takeoff.takeoff_id,
            'components': [
                {
                    'name': m.description,
                    'type': m.item_code,
                    'quantity': float(m.quantity),
                    'unit': m.unit
                }
                for m in takeoff.measurements
            ]
        }


# Global instances
digital_takeoff = DigitalTakeoff()
measurement_calc = MeasurementCalculator()
cost_database = CostDatabase()
takeoff_exporter = TakeoffExporter()