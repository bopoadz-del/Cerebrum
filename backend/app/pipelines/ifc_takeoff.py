"""
IFC Quantity Takeoff Engine
Extracts quantities from IFC models for cost estimation and material planning.
"""

import json
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np

try:
    import ifcopenshell
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False

from app.core.logging import get_logger
from app.pipelines.ifc_properties import (
    IFCPropertyExtractor, PropertyValue, PropertySet
)

logger = get_logger(__name__)


class QuantityType(Enum):
    """Types of quantities."""
    LENGTH = "length"
    AREA = "area"
    VOLUME = "volume"
    WEIGHT = "weight"
    COUNT = "count"
    TIME = "time"
    CURRENCY = "currency"


@dataclass
class Quantity:
    """A single quantity value."""
    name: str
    value: float
    unit: str
    quantity_type: QuantityType
    description: Optional[str] = None
    formula: Optional[str] = None
    source: Optional[str] = None  # 'ifc', 'calculated', 'manual'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "quantity_type": self.quantity_type.value,
            "description": self.description,
            "formula": self.formula,
            "source": self.source
        }


@dataclass
class ElementTakeoff:
    """Quantity takeoff for a single element."""
    element_id: str
    global_id: str
    element_type: str
    name: str
    quantities: List[Quantity] = field(default_factory=list)
    classification: Dict[str, Any] = field(default_factory=dict)
    material: Dict[str, Any] = field(default_factory=dict)
    
    def get_quantity(self, name: str) -> Optional[Quantity]:
        """Get quantity by name."""
        for q in self.quantities:
            if q.name == name:
                return q
        return None
    
    def get_total_by_type(self, quantity_type: QuantityType) -> float:
        """Get total value for a quantity type."""
        return sum(q.value for q in self.quantities if q.quantity_type == quantity_type)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "global_id": self.global_id,
            "element_type": self.element_type,
            "name": self.name,
            "quantities": [q.to_dict() for q in self.quantities],
            "classification": self.classification,
            "material": self.material
        }


@dataclass
class TakeoffSummary:
    """Summary of quantity takeoff."""
    total_elements: int
    total_by_type: Dict[str, int] = field(default_factory=dict)
    total_quantities: Dict[str, Dict[str, float]] = field(default_factory=dict)
    grand_totals: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_elements": self.total_elements,
            "total_by_type": self.total_by_type,
            "total_quantities": self.total_quantities,
            "grand_totals": self.grand_totals
        }


class QuantityTakeoffEngine:
    """
    Extracts quantities from IFC models for cost estimation.
    Supports both IFC-defined quantities and calculated quantities.
    """
    
    # Standard quantity sets by element type
    QUANTITY_SETS = {
        'IfcWall': ['Qto_WallBaseQuantities'],
        'IfcDoor': ['Qto_DoorBaseQuantities'],
        'IfcWindow': ['Qto_WindowBaseQuantities'],
        'IfcSlab': ['Qto_SlabBaseQuantities'],
        'IfcRoof': ['Qto_RoofBaseQuantities'],
        'IfcBeam': ['Qto_BeamBaseQuantities'],
        'IfcColumn': ['Qto_ColumnBaseQuantities'],
        'IfcFooting': ['Qto_FootingBaseQuantities'],
        'IfcStair': ['Qto_StairFlightBaseQuantities'],
        'IfcRailing': ['Qto_RailingBaseQuantities'],
        'IfcSpace': ['Qto_SpaceBaseQuantities'],
        'IfcCovering': ['Qto_CoveringBaseQuantities'],
        'IfcPlate': ['Qto_PlateBaseQuantities'],
        'IfcMember': ['Qto_MemberBaseQuantities'],
        'IfcBuildingStorey': ['Qto_BuildingStoreyBaseQuantities']
    }
    
    # Unit conversion factors to metric
    UNIT_CONVERSIONS = {
        'INCH': 0.0254,
        'FOOT': 0.3048,
        'YARD': 0.9144,
        'MILE': 1609.34,
        'SQUARE_INCH': 0.00064516,
        'SQUARE_FOOT': 0.092903,
        'SQUARE_YARD': 0.836127,
        'CUBIC_INCH': 0.000016387,
        'CUBIC_FOOT': 0.0283168,
        'CUBIC_YARD': 0.764555,
        'POUND': 0.453592,
        'TON': 907.185,
        'GALLON': 3.78541,
        'LITER': 1.0
    }
    
    def __init__(self, ifc_file_path: str):
        self.ifc_file_path = ifc_file_path
        self._ifc_file: Optional[Any] = None
        self._property_extractor: Optional[IFCPropertyExtractor] = None
        
        if not IFC_AVAILABLE:
            raise ImportError("IfcOpenShell is required for IFC processing")
    
    def open_file(self) -> bool:
        """Open IFC file."""
        try:
            self._ifc_file = ifcopenshell.open(self.ifc_file_path)
            self._property_extractor = IFCPropertyExtractor(self.ifc_file_path)
            self._property_extractor.open_file()
            return True
        except Exception as e:
            logger.error(f"Failed to open IFC file: {e}")
            return False
    
    def generate_takeoff(
        self,
        element_types: Optional[List[str]] = None,
        include_calculated: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[ElementTakeoff]:
        """
        Generate quantity takeoff for all elements.
        
        Args:
            element_types: Optional list of element types
            include_calculated: Whether to include calculated quantities
            progress_callback: Optional progress callback
        
        Returns:
            List of ElementTakeoff
        """
        if not self._ifc_file:
            if not self.open_file():
                return []
        
        takeoffs = []
        
        # Get elements
        if element_types:
            elements = []
            for elem_type in element_types:
                elements.extend(self._ifc_file.by_type(elem_type))
        else:
            elements = self._ifc_file.by_type('IfcElement')
        
        logger.info(f"Generating takeoff for {len(elements)} elements")
        
        for i, element in enumerate(elements):
            try:
                takeoff = self._generate_element_takeoff(element, include_calculated)
                if takeoff:
                    takeoffs.append(takeoff)
                
                if progress_callback and i % 100 == 0:
                    progress_callback(i + 1, len(elements))
                    
            except Exception as e:
                logger.warning(f"Failed to generate takeoff for {element.GlobalId}: {e}")
        
        logger.info(f"Generated takeoff for {len(takeoffs)} elements")
        
        return takeoffs
    
    def _generate_element_takeoff(
        self, 
        element: Any,
        include_calculated: bool
    ) -> Optional[ElementTakeoff]:
        """Generate takeoff for a single element."""
        try:
            takeoff = ElementTakeoff(
                element_id=str(element.id()),
                global_id=element.GlobalId,
                element_type=element.is_a(),
                name=getattr(element, 'Name', '')
            )
            
            # Extract IFC quantities
            ifc_quantities = self._extract_ifc_quantities(element)
            takeoff.quantities.extend(ifc_quantities)
            
            # Calculate additional quantities if requested
            if include_calculated:
                calculated = self._calculate_quantities(element)
                takeoff.quantities.extend(calculated)
            
            # Get classification
            takeoff.classification = self._property_extractor._extract_classification(element)
            
            # Get material
            takeoff.material = self._property_extractor._extract_material_info(element)
            
            return takeoff
            
        except Exception as e:
            logger.warning(f"Failed to generate element takeoff: {e}")
            return None
    
    def _extract_ifc_quantities(self, element: Any) -> List[Quantity]:
        """Extract quantities defined in IFC."""
        quantities = []
        
        try:
            # Get quantity sets
            if hasattr(element, 'IsDefinedBy'):
                for definition in element.IsDefinedBy:
                    if definition.is_a('IfcRelDefinesByProperties'):
                        quantity_def = definition.RelatingPropertyDefinition
                        
                        if quantity_def.is_a('IfcElementQuantity'):
                            for q in quantity_def.Quantities:
                                quantity = self._parse_ifc_quantity(q)
                                if quantity:
                                    quantities.append(quantity)
        
        except Exception as e:
            logger.warning(f"Failed to extract IFC quantities: {e}")
        
        return quantities
    
    def _parse_ifc_quantity(self, ifc_quantity: Any) -> Optional[Quantity]:
        """Parse an IFC quantity into Quantity object."""
        try:
            quantity_type = ifc_quantity.is_a()
            name = ifc_quantity.Name
            
            if quantity_type == 'IfcQuantityLength':
                return Quantity(
                    name=name,
                    value=float(ifc_quantity.LengthValue),
                    unit=getattr(ifc_quantity, 'Unit', 'm'),
                    quantity_type=QuantityType.LENGTH,
                    description=getattr(ifc_quantity, 'Description', None),
                    source='ifc'
                )
            
            elif quantity_type == 'IfcQuantityArea':
                return Quantity(
                    name=name,
                    value=float(ifc_quantity.AreaValue),
                    unit=getattr(ifc_quantity, 'Unit', 'm2'),
                    quantity_type=QuantityType.AREA,
                    description=getattr(ifc_quantity, 'Description', None),
                    source='ifc'
                )
            
            elif quantity_type == 'IfcQuantityVolume':
                return Quantity(
                    name=name,
                    value=float(ifc_quantity.VolumeValue),
                    unit=getattr(ifc_quantity, 'Unit', 'm3'),
                    quantity_type=QuantityType.VOLUME,
                    description=getattr(ifc_quantity, 'Description', None),
                    source='ifc'
                )
            
            elif quantity_type == 'IfcQuantityWeight':
                return Quantity(
                    name=name,
                    value=float(ifc_quantity.WeightValue),
                    unit=getattr(ifc_quantity, 'Unit', 'kg'),
                    quantity_type=QuantityType.WEIGHT,
                    description=getattr(ifc_quantity, 'Description', None),
                    source='ifc'
                )
            
            elif quantity_type == 'IfcQuantityCount':
                return Quantity(
                    name=name,
                    value=float(ifc_quantity.CountValue),
                    unit='ea',
                    quantity_type=QuantityType.COUNT,
                    description=getattr(ifc_quantity, 'Description', None),
                    source='ifc'
                )
            
            elif quantity_type == 'IfcQuantityTime':
                return Quantity(
                    name=name,
                    value=float(ifc_quantity.TimeValue),
                    unit=getattr(ifc_quantity, 'Unit', 'h'),
                    quantity_type=QuantityType.TIME,
                    description=getattr(ifc_quantity, 'Description', None),
                    source='ifc'
                )
            
        except Exception as e:
            logger.warning(f"Failed to parse quantity: {e}")
        
        return None
    
    def _calculate_quantities(self, element: Any) -> List[Quantity]:
        """Calculate additional quantities from geometry."""
        calculated = []
        
        try:
            element_type = element.is_a()
            
            # Get dimensions from properties
            props = self._property_extractor.extract_element_properties(element)
            
            # Calculate based on element type
            if element_type == 'IfcWall':
                calculated.extend(self._calculate_wall_quantities(element, props))
            elif element_type == 'IfcSlab':
                calculated.extend(self._calculate_slab_quantities(element, props))
            elif element_type == 'IfcDoor':
                calculated.extend(self._calculate_door_quantities(element, props))
            elif element_type == 'IfcWindow':
                calculated.extend(self._calculate_window_quantities(element, props))
            
        except Exception as e:
            logger.warning(f"Failed to calculate quantities: {e}")
        
        return calculated
    
    def _calculate_wall_quantities(
        self, 
        element: Any, 
        props: Any
    ) -> List[Quantity]:
        """Calculate wall-specific quantities."""
        quantities = []
        
        # Try to get from properties
        width = props.get_property_value('Pset_WallCommon', 'Width')
        length = props.get_property_value('Pset_WallCommon', 'Length')
        height = props.get_property_value('Pset_WallCommon', 'Height')
        
        if width and length and height:
            gross_volume = width * length * height
            quantities.append(Quantity(
                name="GrossVolume",
                value=gross_volume,
                unit="m3",
                quantity_type=QuantityType.VOLUME,
                formula="width * length * height",
                source="calculated"
            ))
            
            gross_area = length * height
            quantities.append(Quantity(
                name="GrossSideArea",
                value=gross_area,
                unit="m2",
                quantity_type=QuantityType.AREA,
                formula="length * height",
                source="calculated"
            ))
        
        return quantities
    
    def _calculate_slab_quantities(
        self, 
        element: Any, 
        props: Any
    ) -> List[Quantity]:
        """Calculate slab-specific quantities."""
        quantities = []
        
        thickness = props.get_property_value('Pset_SlabCommon', 'Thickness')
        
        if thickness:
            quantities.append(Quantity(
                name="CalculatedThickness",
                value=thickness,
                unit="m",
                quantity_type=QuantityType.LENGTH,
                source="calculated"
            ))
        
        return quantities
    
    def _calculate_door_quantities(
        self, 
        element: Any, 
        props: Any
    ) -> List[Quantity]:
        """Calculate door-specific quantities."""
        quantities = []
        
        width = props.get_property_value('Pset_DoorCommon', 'Width')
        height = props.get_property_value('Pset_DoorCommon', 'Height')
        
        if width and height:
            area = width * height
            quantities.append(Quantity(
                name="OpeningArea",
                value=area,
                unit="m2",
                quantity_type=QuantityType.AREA,
                formula="width * height",
                source="calculated"
            ))
        
        return quantities
    
    def _calculate_window_quantities(
        self, 
        element: Any, 
        props: Any
    ) -> List[Quantity]:
        """Calculate window-specific quantities."""
        quantities = []
        
        width = props.get_property_value('Pset_WindowCommon', 'Width')
        height = props.get_property_value('Pset_WindowCommon', 'Height')
        
        if width and height:
            area = width * height
            quantities.append(Quantity(
                name="OpeningArea",
                value=area,
                unit="m2",
                quantity_type=QuantityType.AREA,
                formula="width * height",
                source="calculated"
            ))
        
        return quantities
    
    def generate_summary(self, takeoffs: List[ElementTakeoff]) -> TakeoffSummary:
        """Generate summary of takeoff results."""
        summary = TakeoffSummary(total_elements=len(takeoffs))
        
        # Count by element type
        for takeoff in takeoffs:
            elem_type = takeoff.element_type
            summary.total_by_type[elem_type] = summary.total_by_type.get(elem_type, 0) + 1
            
            # Sum quantities
            for q in takeoff.quantities:
                qtype = q.quantity_type.value
                if qtype not in summary.total_quantities:
                    summary.total_quantities[qtype] = {}
                
                summary.total_quantities[qtype][q.name] = (
                    summary.total_quantities[qtype].get(q.name, 0) + q.value
                )
        
        # Calculate grand totals
        for qtype, quantities in summary.total_quantities.items():
            summary.grand_totals[qtype] = sum(quantities.values())
        
        return summary
    
    def export_to_csv(
        self, 
        takeoffs: List[ElementTakeoff], 
        output_path: str
    ) -> bool:
        """Export takeoff to CSV format."""
        try:
            import csv
            
            # Collect all unique quantity names
            all_quantities = set()
            for takeoff in takeoffs:
                for q in takeoff.quantities:
                    all_quantities.add(q.name)
            
            quantity_names = sorted(all_quantities)
            
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Header
                header = ['Element ID', 'Global ID', 'Type', 'Name', 'Classification']
                header.extend(quantity_names)
                writer.writerow(header)
                
                # Data rows
                for takeoff in takeoffs:
                    row = [
                        takeoff.element_id,
                        takeoff.global_id,
                        takeoff.element_type,
                        takeoff.name,
                        takeoff.classification.get('reference', '')
                    ]
                    
                    # Add quantities
                    quantity_values = {q.name: q.value for q in takeoff.quantities}
                    for qname in quantity_names:
                        row.append(quantity_values.get(qname, ''))
                    
                    writer.writerow(row)
            
            logger.info(f"Exported takeoff to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return False
    
    def export_to_json(
        self, 
        takeoffs: List[ElementTakeoff], 
        output_path: str
    ) -> bool:
        """Export takeoff to JSON format."""
        try:
            data = {
                "exported_at": datetime.utcnow().isoformat(),
                "file_path": self.ifc_file_path,
                "elements": [t.to_dict() for t in takeoffs],
                "summary": self.generate_summary(takeoffs).to_dict()
            }
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported takeoff to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return False
    
    def close(self) -> None:
        """Close IFC file."""
        self._ifc_file = None
        if self._property_extractor:
            self._property_extractor.close()


# Convenience function
async def generate_ifc_takeoff(
    ifc_file_path: str,
    element_types: Optional[List[str]] = None,
    include_calculated: bool = True
) -> List[ElementTakeoff]:
    """
    Generate quantity takeoff from IFC file.
    
    Args:
        ifc_file_path: Path to IFC file
        element_types: Optional list of element types
        include_calculated: Whether to include calculated quantities
    
    Returns:
        List of ElementTakeoff
    """
    engine = QuantityTakeoffEngine(ifc_file_path)
    takeoffs = engine.generate_takeoff(element_types, include_calculated)
    engine.close()
    return takeoffs
