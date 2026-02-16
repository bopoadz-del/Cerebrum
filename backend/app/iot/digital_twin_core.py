"""
Digital Twin Core
BIM linked to physical asset tags for digital twin
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class BIMElement:
    """BIM element from model"""
    element_id: str
    global_id: str  # IFC GlobalId
    element_type: str
    name: str
    level: str
    category: str
    properties: Dict[str, Any] = field(default_factory=dict)
    geometry: Optional[Dict[str, Any]] = None


@dataclass
class PhysicalAsset:
    """Physical asset linked to BIM"""
    asset_id: str
    asset_tag: str  # RFID/QR code
    bim_element_id: Optional[str]
    name: str
    asset_type: str
    location: str
    installation_date: Optional[datetime] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    warranty_expiry: Optional[datetime] = None
    maintenance_schedule: Dict[str, Any] = field(default_factory=dict)
    sensors: List[str] = field(default_factory=list)
    documents: List[str] = field(default_factory=list)


@dataclass
class AssetRelationship:
    """Relationship between assets"""
    parent_id: str
    child_id: str
    relationship_type: str  # contains, connects_to, feeds, etc.


class DigitalTwin:
    """Digital twin model"""
    
    def __init__(self):
        self.bim_elements: Dict[str, BIMElement] = {}
        self.physical_assets: Dict[str, PhysicalAsset] = {}
        self.relationships: List[AssetRelationship] = []
        self.asset_sensor_data: Dict[str, List[Dict[str, Any]]] = {}
    
    def import_bim_model(self, ifc_data: Dict[str, Any]) -> int:
        """Import BIM model from IFC data"""
        count = 0
        
        for element_data in ifc_data.get('elements', []):
            element = BIMElement(
                element_id=element_data['id'],
                global_id=element_data['global_id'],
                element_type=element_data['type'],
                name=element_data['name'],
                level=element_data.get('level', ''),
                category=element_data.get('category', ''),
                properties=element_data.get('properties', {}),
                geometry=element_data.get('geometry')
            )
            
            self.bim_elements[element.element_id] = element
            count += 1
        
        logger.info(f"Imported {count} BIM elements")
        return count
    
    def link_asset_to_bim(
        self,
        asset_id: str,
        bim_element_id: str
    ) -> bool:
        """Link physical asset to BIM element"""
        if asset_id not in self.physical_assets:
            return False
        
        if bim_element_id not in self.bim_elements:
            return False
        
        self.physical_assets[asset_id].bim_element_id = bim_element_id
        
        logger.info(f"Linked asset {asset_id} to BIM element {bim_element_id}")
        return True
    
    def register_asset(self, asset: PhysicalAsset) -> str:
        """Register a physical asset"""
        self.physical_assets[asset.asset_id] = asset
        logger.info(f"Registered asset: {asset.asset_id}")
        return asset.asset_id
    
    def get_asset_by_tag(self, asset_tag: str) -> Optional[PhysicalAsset]:
        """Get asset by its physical tag"""
        for asset in self.physical_assets.values():
            if asset.asset_tag == asset_tag:
                return asset
        return None
    
    def get_assets_in_space(self, level: str, room: str = None) -> List[PhysicalAsset]:
        """Get all assets in a space"""
        assets = []
        
        for asset in self.physical_assets.values():
            if asset.location.startswith(level):
                if room is None or room in asset.location:
                    assets.append(asset)
        
        return assets
    
    def get_asset_twin_data(self, asset_id: str) -> Dict[str, Any]:
        """Get complete digital twin data for an asset"""
        if asset_id not in self.physical_assets:
            return {'error': 'Asset not found'}
        
        asset = self.physical_assets[asset_id]
        
        # Get linked BIM element
        bim_element = None
        if asset.bim_element_id and asset.bim_element_id in self.bim_elements:
            bim_element = self.bim_elements[asset.bim_element_id]
        
        # Get sensor data
        sensor_data = self.asset_sensor_data.get(asset_id, [])
        
        return {
            'asset': {
                'id': asset.asset_id,
                'tag': asset.asset_tag,
                'name': asset.name,
                'type': asset.asset_type,
                'location': asset.location,
                'manufacturer': asset.manufacturer,
                'model': asset.model_number,
                'installation_date': asset.installation_date.isoformat() if asset.installation_date else None,
                'warranty_expiry': asset.warranty_expiry.isoformat() if asset.warranty_expiry else None
            },
            'bim_element': {
                'id': bim_element.element_id if bim_element else None,
                'global_id': bim_element.global_id if bim_element else None,
                'type': bim_element.element_type if bim_element else None,
                'name': bim_element.name if bim_element else None,
                'properties': bim_element.properties if bim_element else {}
            },
            'sensors': asset.sensors,
            'sensor_data': sensor_data[-100:],  # Last 100 readings
            'documents': asset.documents
        }
    
    def update_sensor_data(self, asset_id: str, data: Dict[str, Any]):
        """Update sensor data for an asset"""
        if asset_id not in self.asset_sensor_data:
            self.asset_sensor_data[asset_id] = []
        
        self.asset_sensor_data[asset_id].append({
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        })
        
        # Keep only last 1000 readings
        if len(self.asset_sensor_data[asset_id]) > 1000:
            self.asset_sensor_data[asset_id] = self.asset_sensor_data[asset_id][-1000:]
    
    def get_building_overview(self) -> Dict[str, Any]:
        """Get building digital twin overview"""
        return {
            'bim_elements_count': len(self.bim_elements),
            'physical_assets_count': len(self.physical_assets),
            'linked_assets': sum(
                1 for a in self.physical_assets.values()
                if a.bim_element_id is not None
            ),
            'assets_by_type': self._get_assets_by_type(),
            'assets_by_level': self._get_assets_by_level()
        }
    
    def _get_assets_by_type(self) -> Dict[str, int]:
        """Get asset counts by type"""
        counts = {}
        for asset in self.physical_assets.values():
            counts[asset.asset_type] = counts.get(asset.asset_type, 0) + 1
        return counts
    
    def _get_assets_by_level(self) -> Dict[str, int]:
        """Get asset counts by building level"""
        counts = {}
        for asset in self.physical_assets.values():
            level = asset.location.split('/')[0] if '/' in asset.location else asset.location
            counts[level] = counts.get(level, 0) + 1
        return counts


# Global digital twin
digital_twin = DigitalTwin()
