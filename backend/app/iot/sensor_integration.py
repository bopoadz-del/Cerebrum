"""
Sensor Integration
Concrete maturity, structural health, and environmental sensors
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SensorType(Enum):
    """Types of construction sensors"""
    CONCRETE_MATURITY = 'concrete_maturity'
    STRUCTURAL_HEALTH = 'structural_health'
    TEMPERATURE = 'temperature'
    HUMIDITY = 'humidity'
    VIBRATION = 'vibration'
    STRAIN = 'strain'
    DISPLACEMENT = 'displacement'
    PRESSURE = 'pressure'
    CRACK_MONITORING = 'crack_monitoring'


@dataclass
class Sensor:
    """Sensor definition"""
    id: str
    name: str
    sensor_type: SensorType
    location: str
    project_id: str
    manufacturer: str
    model: str
    calibration_date: Optional[datetime] = None
    calibration_coefficients: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class ConcreteMaturityData:
    """Concrete maturity sensor data"""
    sensor_id: str
    timestamp: datetime
    temperature_c: float
    maturity_index: float  # Temperature-time factor
    strength_estimate_mpa: float
    pour_id: str
    mix_design: str
    target_strength_mpa: float


@dataclass
class StructuralHealthData:
    """Structural health monitoring data"""
    sensor_id: str
    timestamp: datetime
    strain_microstrain: float
    stress_mpa: Optional[float]
    displacement_mm: Optional[float]
    vibration_hz: Optional[float]
    temperature_c: float
    alert_status: str = 'normal'  # normal, warning, critical


@dataclass
class EnvironmentalData:
    """Environmental sensor data"""
    sensor_id: str
    timestamp: datetime
    temperature_c: float
    humidity_percent: float
    pressure_kpa: Optional[float]
    wind_speed_ms: Optional[float]
    precipitation_mm: Optional[float]


class ConcreteMaturityCalculator:
    """Calculate concrete maturity and strength"""
    
    def __init__(self):
        self.datum_temperature = 0  # °C
        self.reference_maturity = {}  # Pour ID -> maturity data
    
    def calculate_maturity_index(
        self,
        temperatures: List[float],
        interval_hours: float
    ) -> float:
        """Calculate maturity index (temperature-time factor)"""
        # Maturity = Σ(T - T₀) × Δt
        # where T is temperature, T₀ is datum temperature, Δt is time interval
        
        maturity = sum(
            max(0, t - self.datum_temperature) * interval_hours
            for t in temperatures
        )
        
        return maturity
    
    def estimate_strength(
        self,
        maturity_index: float,
        mix_design: str
    ) -> float:
        """Estimate concrete strength based on maturity"""
        # Simplified strength estimation
        # In production, use established maturity-strength relationship
        
        # Typical values for standard mix
        strength_coefficients = {
            'standard': {'a': 20, 'b': 0.001},
            'high_early': {'a': 25, 'b': 0.002},
            'slow_cure': {'a': 15, 'b': 0.0005}
        }
        
        coeffs = strength_coefficients.get(mix_design, strength_coefficients['standard'])
        
        # S-curve approximation for strength development
        import math
        strength = coeffs['a'] * (1 - math.exp(-coeffs['b'] * maturity_index))
        
        return min(strength, 60)  # Cap at 60 MPa
    
    def get_strength_at_time(
        self,
        pour_id: str,
        hours_after_pour: float
    ) -> Optional[float]:
        """Get estimated strength at specific time after pour"""
        if pour_id not in self.reference_maturity:
            return None
        
        pour_data = self.reference_maturity[pour_id]
        
        # Find closest maturity reading
        target_maturity = hours_after_pour * pour_data.get('avg_temp', 20)
        
        return self.estimate_strength(target_maturity, pour_data.get('mix_design', 'standard'))


class SensorIntegrationManager:
    """Manage sensor integrations"""
    
    def __init__(self):
        self.sensors: Dict[str, Sensor] = {}
        self.concrete_data: List[ConcreteMaturityData] = []
        self.structural_data: List[StructuralHealthData] = []
        self.environmental_data: List[EnvironmentalData] = []
        self.max_data_points = 10000
        self.maturity_calculator = ConcreteMaturityCalculator()
        self.alert_handlers: List[Callable] = []
    
    def register_sensor(self, sensor: Sensor) -> str:
        """Register a new sensor"""
        self.sensors[sensor.id] = sensor
        logger.info(f"Registered sensor: {sensor.id} ({sensor.sensor_type.value})")
        return sensor.id
    
    def process_concrete_maturity_data(self, data: ConcreteMaturityData):
        """Process concrete maturity sensor data"""
        # Estimate strength
        data.strength_estimate_mpa = self.maturity_calculator.estimate_strength(
            data.maturity_index,
            data.mix_design
        )
        
        self.concrete_data.append(data)
        
        # Check if target strength reached
        if data.strength_estimate_mpa >= data.target_strength_mpa:
            self._alert_target_strength_reached(data)
        
        # Trim old data
        if len(self.concrete_data) > self.max_data_points:
            self.concrete_data = self.concrete_data[-self.max_data_points:]
    
    def process_structural_health_data(self, data: StructuralHealthData):
        """Process structural health monitoring data"""
        # Determine alert status
        if abs(data.strain_microstrain) > 2000:
            data.alert_status = 'critical'
            self._alert_critical_strain(data)
        elif abs(data.strain_microstrain) > 1500:
            data.alert_status = 'warning'
        
        self.structural_data.append(data)
        
        if len(self.structural_data) > self.max_data_points:
            self.structural_data = self.structural_data[-self.max_data_points:]
    
    def process_environmental_data(self, data: EnvironmentalData):
        """Process environmental sensor data"""
        self.environmental_data.append(data)
        
        if len(self.environmental_data) > self.max_data_points:
            self.environmental_data = self.environmental_data[-self.max_data_points:]
    
    def _alert_target_strength_reached(self, data: ConcreteMaturityData):
        """Alert when concrete reaches target strength"""
        logger.info(f"Target strength reached for pour {data.pour_id}: {data.strength_estimate_mpa:.1f} MPa")
        
        for handler in self.alert_handlers:
            try:
                handler({
                    'type': 'target_strength_reached',
                    'pour_id': data.pour_id,
                    'strength': data.strength_estimate_mpa,
                    'sensor_id': data.sensor_id
                })
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    def _alert_critical_strain(self, data: StructuralHealthData):
        """Alert on critical strain readings"""
        logger.warning(f"Critical strain detected: {data.strain_microstrain} microstrain")
        
        for handler in self.alert_handlers:
            try:
                handler({
                    'type': 'critical_strain',
                    'sensor_id': data.sensor_id,
                    'strain': data.strain_microstrain
                })
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    def on_alert(self, handler: Callable):
        """Register alert handler"""
        self.alert_handlers.append(handler)
    
    def get_sensor_data(
        self,
        sensor_id: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get data for a specific sensor"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        sensor = self.sensors.get(sensor_id)
        if not sensor:
            return []
        
        if sensor.sensor_type == SensorType.CONCRETE_MATURITY:
            data = [d for d in self.concrete_data if d.sensor_id == sensor_id and d.timestamp > cutoff]
            return [{'timestamp': d.timestamp.isoformat(), 'temperature': d.temperature_c, 
                    'maturity': d.maturity_index, 'strength': d.strength_estimate_mpa} for d in data]
        
        elif sensor.sensor_type == SensorType.STRUCTURAL_HEALTH:
            data = [d for d in self.structural_data if d.sensor_id == sensor_id and d.timestamp > cutoff]
            return [{'timestamp': d.timestamp.isoformat(), 'strain': d.strain_microstrain,
                    'stress': d.stress_mpa, 'displacement': d.displacement_mm} for d in data]
        
        elif sensor.sensor_type in [SensorType.TEMPERATURE, SensorType.HUMIDITY]:
            data = [d for d in self.environmental_data if d.sensor_id == sensor_id and d.timestamp > cutoff]
            return [{'timestamp': d.timestamp.isoformat(), 'temperature': d.temperature_c,
                    'humidity': d.humidity_percent} for d in data]
        
        return []
    
    def get_sensor_summary(self) -> Dict[str, Any]:
        """Get sensor summary"""
        return {
            'total_sensors': len(self.sensors),
            'by_type': {
                sensor_type.value: sum(1 for s in self.sensors.values() if s.sensor_type == sensor_type)
                for sensor_type in SensorType
            },
            'active_sensors': sum(1 for s in self.sensors.values() if s.is_active),
            'data_points': {
                'concrete_maturity': len(self.concrete_data),
                'structural_health': len(self.structural_data),
                'environmental': len(self.environmental_data)
            }
        }


# Global sensor integration manager
sensor_manager = SensorIntegrationManager()
