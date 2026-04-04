"""
Safety AI models for PPE detection and hazard alerts.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import numpy as np


class PPEType(Enum):
    """Types of Personal Protective Equipment."""
    HARD_HAT = "hard_hat"
    SAFETY_VEST = "safety_vest"
    SAFETY_GLASSES = "safety_glasses"
    GLOVES = "gloves"
    STEEL_TOE_BOOTS = "steel_toe_boots"
    HARNESS = "harness"
    HEARING_PROTECTION = "hearing_protection"
    RESPIRATOR = "respirator"


class HazardLevel(Enum):
    """Hazard severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PPEDetection:
    """PPE detection result."""
    ppe_type: PPEType
    detected: bool
    confidence: float
    bbox: Optional[Tuple[int, int, int, int]] = None
    person_id: Optional[str] = None


@dataclass
class PersonDetection:
    """Person detection with PPE status."""
    person_id: str
    bbox: Tuple[int, int, int, int]
    confidence: float
    ppe_status: Dict[PPEType, PPEDetection] = field(default_factory=dict)
    compliance_score: float = 0.0
    zone_id: Optional[str] = None


@dataclass
class HazardAlert:
    """Hazard detection alert."""
    alert_id: str
    hazard_type: str
    level: HazardLevel
    description: str
    location: Optional[Tuple[float, float]] = None
    zone_id: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)
    image_snapshot: Optional[str] = None
    related_persons: List[str] = field(default_factory=list)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


@dataclass
class SafetyZone:
    """Defined safety zone with PPE requirements."""
    zone_id: str
    name: str
    polygon: List[Tuple[int, int]]
    required_ppe: List[PPEType]
    hazard_level: HazardLevel
    max_occupancy: int
    current_occupancy: int = 0


class SafetyAIDetector:
    """AI-powered safety detection for construction sites."""
    
    # PPE requirements by zone type
    ZONE_PPE_REQUIREMENTS = {
        "general": [PPEType.HARD_HAT, PPEType.SAFETY_VEST, PPEType.STEEL_TOE_BOOTS],
        "excavation": [PPEType.HARD_HAT, PPEType.SAFETY_VEST, PPEType.STEEL_TOE_BOOTS],
        "height_work": [PPEType.HARD_HAT, PPEType.SAFETY_VEST, PPEType.HARNESS],
        "welding": [PPEType.HARD_HAT, PPEType.SAFETY_VEST, PPEType.SAFETY_GLASSES, PPEType.GLOVES],
        "chemical": [PPEType.HARD_HAT, PPEType.SAFETY_VEST, PPEType.RESPIRATOR, PPEType.GLOVES],
        "noise": [PPEType.HARD_HAT, PPEType.SAFETY_VEST, PPEType.HEARING_PROTECTION]
    }
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._person_model = None
        self._ppe_models: Dict[PPEType, Any] = {}
        self._hazard_model = None
        self._safety_zones: Dict[str, SafetyZone] = {}
        self._alert_history: List[HazardAlert] = []
        self._detection_threshold = 0.5
    
    async def load_models(self):
        """Load safety detection models."""
        
        # Load person detection model (YOLO or similar)
        # Placeholder - in production, load actual models
        self._person_model = {"loaded": True, "type": "person_detection"}
        
        # Load PPE detection models
        for ppe_type in PPEType:
            self._ppe_models[ppe_type] = {"loaded": True, "type": ppe_type.value}
        
        # Load hazard detection model
        self._hazard_model = {"loaded": True, "type": "hazard_detection"}
    
    async def detect_persons(
        self,
        image: np.ndarray,
        zone_id: Optional[str] = None
    ) -> List[PersonDetection]:
        """Detect persons in an image."""
        
        # Placeholder - in production, run actual person detection
        # This would use YOLO, Faster R-CNN, etc.
        
        detections = []
        
        # Simulate detection
        # In production, this would be: results = self._person_model(image)
        
        return detections
    
    async def detect_ppe(
        self,
        image: np.ndarray,
        person_detections: List[PersonDetection]
    ) -> List[PersonDetection]:
        """Detect PPE on detected persons."""
        
        for person in person_detections:
            # Get zone requirements
            zone = self._safety_zones.get(person.zone_id) if person.zone_id else None
            required_ppe = zone.required_ppe if zone else self.ZONE_PPE_REQUIREMENTS["general"]
            
            # Detect each PPE type
            person.ppe_status = {}
            detected_count = 0
            
            for ppe_type in required_ppe:
                # Placeholder - run actual PPE detection
                # In production: detection = self._ppe_models[ppe_type](person_crop)
                
                # Simulate detection with random values
                import random
                detected = random.random() > 0.3
                confidence = random.uniform(0.7, 0.95) if detected else random.uniform(0.3, 0.6)
                
                person.ppe_status[ppe_type] = PPEDetection(
                    ppe_type=ppe_type,
                    detected=detected,
                    confidence=confidence,
                    person_id=person.person_id
                )
                
                if detected:
                    detected_count += 1
            
            # Calculate compliance score
            person.compliance_score = (
                detected_count / len(required_ppe) * 100
            ) if required_ppe else 100
        
        return person_detections
    
    async def detect_hazards(
        self,
        image: np.ndarray,
        zone_id: Optional[str] = None
    ) -> List[HazardAlert]:
        """Detect safety hazards in an image."""
        
        alerts = []
        
        # Placeholder - run actual hazard detection
        # In production: hazards = self._hazard_model(image)
        
        # Simulate hazard detection
        hazard_types = [
            ("falling_object", HazardLevel.HIGH),
            ("uneven_surface", HazardLevel.MEDIUM),
            ("exposed_wiring", HazardLevel.HIGH),
            ("missing_guardrail", HazardLevel.CRITICAL),
            ("spill", HazardLevel.LOW)
        ]
        
        import random
        for hazard_type, level in hazard_types:
            if random.random() < 0.1:  # 10% chance of detecting each hazard
                alert = HazardAlert(
                    alert_id=str(random.randint(10000, 99999)),
                    hazard_type=hazard_type,
                    level=level,
                    description=f"Detected {hazard_type.replace('_', ' ')}",
                    zone_id=zone_id,
                    image_snapshot="base64_encoded_image"  # Placeholder
                )
                alerts.append(alert)
                self._alert_history.append(alert)
        
        return alerts
    
    async def process_frame(
        self,
        image: np.ndarray,
        camera_id: str,
        zone_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a complete frame for safety detection."""
        
        # Detect persons
        persons = await self.detect_persons(image, zone_id)
        
        # Detect PPE
        persons_with_ppe = await self.detect_ppe(image, persons)
        
        # Detect hazards
        hazards = await self.detect_hazards(image, zone_id)
        
        # Check for PPE violations
        ppe_violations = [
            p for p in persons_with_ppe
            if p.compliance_score < 100
        ]
        
        # Generate alerts for violations
        for person in ppe_violations:
            missing_ppe = [
                ppe.value for ppe, detection in person.ppe_status.items()
                if not detection.detected
            ]
            
            if missing_ppe:
                alert = HazardAlert(
                    alert_id=str(len(self._alert_history)),
                    hazard_type="ppe_violation",
                    level=HazardLevel.MEDIUM,
                    description=f"Missing PPE: {', '.join(missing_ppe)}",
                    zone_id=zone_id,
                    related_persons=[person.person_id]
                )
                hazards.append(alert)
                self._alert_history.append(alert)
        
        # Update zone occupancy
        if zone_id and zone_id in self._safety_zones:
            self._safety_zones[zone_id].current_occupancy = len(persons)
        
        return {
            "camera_id": camera_id,
            "zone_id": zone_id,
            "timestamp": datetime.utcnow().isoformat(),
            "persons_detected": len(persons),
            "persons": [
                {
                    "person_id": p.person_id,
                    "bbox": p.bbox,
                    "compliance_score": p.compliance_score,
                    "ppe_status": {
                        ppe.value: {
                            "detected": d.detected,
                            "confidence": d.confidence
                        }
                        for ppe, d in p.ppe_status.items()
                    }
                }
                for p in persons_with_ppe
            ],
            "hazards_detected": len(hazards),
            "hazards": [
                {
                    "alert_id": h.alert_id,
                    "hazard_type": h.hazard_type,
                    "level": h.level.value,
                    "description": h.description
                }
                for h in hazards
            ],
            "ppe_violations": len(ppe_violations)
        }
    
    async def register_safety_zone(self, zone: SafetyZone):
        """Register a safety zone."""
        self._safety_zones[zone.zone_id] = zone
    
    async def get_zone_compliance(
        self,
        zone_id: str,
        time_window_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get PPE compliance statistics for a zone."""
        
        zone = self._safety_zones.get(zone_id)
        if not zone:
            return {"error": "Zone not found"}
        
        # Calculate compliance from recent detections
        # Placeholder - in production, query from database
        
        return {
            "zone_id": zone_id,
            "zone_name": zone.name,
            "required_ppe": [p.value for p in zone.required_ppe],
            "compliance_rate": 85.5,  # Placeholder
            "total_detections": 150,
            "compliant_detections": 128,
            "by_ppe_type": {
                ppe.value: {"compliance_rate": 90.0 + i * 2}
                for i, ppe in enumerate(zone.required_ppe)
            },
            "time_window_minutes": time_window_minutes
        }
    
    async def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str
    ) -> bool:
        """Acknowledge a hazard alert."""
        
        for alert in self._alert_history:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.utcnow()
                return True
        
        return False
    
    async def get_alerts(
        self,
        zone_id: Optional[str] = None,
        level: Optional[HazardLevel] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get hazard alerts with filtering."""
        
        alerts = self._alert_history
        
        if zone_id:
            alerts = [a for a in alerts if a.zone_id == zone_id]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        alerts = sorted(alerts, key=lambda a: a.detected_at, reverse=True)[:limit]
        
        return [
            {
                "alert_id": a.alert_id,
                "hazard_type": a.hazard_type,
                "level": a.level.value,
                "description": a.description,
                "zone_id": a.zone_id,
                "detected_at": a.detected_at.isoformat(),
                "acknowledged": a.acknowledged,
                "acknowledged_by": a.acknowledged_by
            }
            for a in alerts
        ]
    
    async def generate_safety_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate a safety compliance report."""
        
        # Filter alerts in date range
        alerts_in_range = [
            a for a in self._alert_history
            if start_date <= a.detected_at <= end_date
        ]
        
        # Count by type and level
        by_type: Dict[str, int] = {}
        by_level: Dict[str, int] = {}
        
        for alert in alerts_in_range:
            by_type[alert.hazard_type] = by_type.get(alert.hazard_type, 0) + 1
            by_level[alert.level.value] = by_level.get(alert.level.value, 0) + 1
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_alerts": len(alerts_in_range),
            "by_hazard_type": by_type,
            "by_severity_level": by_level,
            "acknowledged_count": sum(1 for a in alerts_in_range if a.acknowledged),
            "unacknowledged_count": sum(1 for a in alerts_in_range if not a.acknowledged),
            "zones_covered": list(self._safety_zones.keys()),
            "recommendations": self._generate_recommendations(alerts_in_range)
        }
    
    def _generate_recommendations(
        self,
        alerts: List[HazardAlert]
    ) -> List[str]:
        """Generate safety recommendations based on alerts."""
        
        recommendations = []
        
        # Count PPE violations
        ppe_violations = sum(1 for a in alerts if a.hazard_type == "ppe_violation")
        if ppe_violations > len(alerts) * 0.3:
            recommendations.append(
                "High rate of PPE violations detected. Consider additional training."
            )
        
        # Check for repeated hazards
        hazard_counts: Dict[str, int] = {}
        for alert in alerts:
            hazard_counts[alert.hazard_type] = hazard_counts.get(alert.hazard_type, 0) + 1
        
        for hazard_type, count in hazard_counts.items():
            if count > 5:
                recommendations.append(
                    f"Recurring {hazard_type} detected. Investigate root cause."
                )
        
        return recommendations
