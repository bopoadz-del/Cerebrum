"""
IFC Property Set Extraction Pipeline
Extracts property sets (Pset_WallCommon, etc.) from IFC elements.
"""

import json
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

try:
    import ifcopenshell
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False

from app.core.logging import get_logger

logger = get_logger(__name__)


class PropertyType(Enum):
    """IFC property value types."""
    SINGLE_VALUE = "IfcPropertySingleValue"
    ENUMERATED_VALUE = "IfcPropertyEnumeratedValue"
    BOUNDED_VALUE = "IfcPropertyBoundedValue"
    TABLE_VALUE = "IfcPropertyTableValue"
    LIST_VALUE = "IfcPropertyListValue"
    REFERENCE_VALUE = "IfcPropertyReferenceValue"


@dataclass
class PropertyValue:
    """Represents a single property value."""
    name: str
    value: Any
    nominal_value: Optional[Any] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    property_type: str = "single"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "nominal_value": self.nominal_value,
            "unit": self.unit,
            "description": self.description,
            "property_type": self.property_type
        }


@dataclass
class PropertySet:
    """Represents a property set with its properties."""
    name: str
    description: Optional[str] = None
    properties: List[PropertyValue] = field(default_factory=list)
    global_id: Optional[str] = None
    
    def get_property(self, name: str) -> Optional[PropertyValue]:
        """Get a property by name."""
        for prop in self.properties:
            if prop.name == name:
                return prop
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "global_id": self.global_id,
            "properties": [p.to_dict() for p in self.properties]
        }


@dataclass
class ElementProperties:
    """All properties for an IFC element."""
    element_id: str
    global_id: str
    element_type: str
    name: str
    property_sets: List[PropertySet] = field(default_factory=list)
    quantity_sets: List[PropertySet] = field(default_factory=list)
    material_info: Dict[str, Any] = field(default_factory=dict)
    classification: Dict[str, Any] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_property_set(self, name: str) -> Optional[PropertySet]:
        """Get a property set by name."""
        for pset in self.property_sets:
            if pset.name == name:
                return pset
        return None
    
    def get_property_value(
        self, 
        pset_name: str, 
        prop_name: str
    ) -> Optional[Any]:
        """Get a specific property value."""
        pset = self.get_property_set(pset_name)
        if pset:
            prop = pset.get_property(prop_name)
            if prop:
                return prop.value
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "global_id": self.global_id,
            "element_type": self.element_type,
            "name": self.name,
            "property_sets": [p.to_dict() for p in self.property_sets],
            "quantity_sets": [q.to_dict() for q in self.quantity_sets],
            "material_info": self.material_info,
            "classification": self.classification,
            "extracted_at": self.extracted_at.isoformat()
        }


@dataclass
class ExtractionSummary:
    """Summary of property extraction."""
    total_elements: int
    elements_with_properties: int
    total_property_sets: int
    total_properties: int
    property_set_names: List[str] = field(default_factory=list)
    quantity_set_names: List[str] = field(default_factory=list)
    processing_time: float = 0.0


class IFCPropertyExtractor:
    """
    Extracts property sets and quantities from IFC elements.
    Supports standard property sets like Pset_WallCommon, Qto_WallBaseQuantities, etc.
    """
    
    # Standard property sets by element type
    STANDARD_PROPERTY_SETS = {
        'IfcWall': [
            'Pset_WallCommon',
            'Pset_PrecastConcreteElementGeneral',
            'Pset_ConcreteElementGeneral'
        ],
        'IfcDoor': [
            'Pset_DoorCommon',
            'Pset_DoorWindowGlazingType',
            'Pset_DoorWindowShadingType'
        ],
        'IfcWindow': [
            'Pset_WindowCommon',
            'Pset_DoorWindowGlazingType',
            'Pset_DoorWindowShadingType'
        ],
        'IfcSlab': [
            'Pset_SlabCommon',
            'Pset_PrecastConcreteElementGeneral',
            'Pset_ConcreteElementGeneral'
        ],
        'IfcRoof': [
            'Pset_RoofCommon'
        ],
        'IfcBeam': [
            'Pset_BeamCommon',
            'Pset_ProfileArbitraryDoubleT',
            'Pset_ProfileArbitraryTShape'
        ],
        'IfcColumn': [
            'Pset_ColumnCommon',
            'Pset_ProfileMechanical'
        ],
        'IfcFooting': [
            'Pset_FootingCommon'
        ],
        'IfcStair': [
            'Pset_StairCommon',
            'Pset_StairFlightCommon'
        ],
        'IfcRailing': [
            'Pset_RailingCommon'
        ],
        'IfcCovering': [
            'Pset_CoveringCommon',
            'Pset_CoveringCeiling',
            'Pset_CoveringFlooring'
        ],
        'IfcSpace': [
            'Pset_SpaceCommon',
            'Pset_SpaceThermalRequirements',
            'Pset_SpaceFireSafetyRequirements',
            'Pset_SpaceLightingRequirements'
        ],
        'IfcBuildingStorey': [
            'Pset_BuildingStoreyCommon'
        ],
        'IfcBuilding': [
            'Pset_BuildingCommon',
            'Pset_BuildingUse',
            'Pset_BuildingThermalView'
        ],
        'IfcSite': [
            'Pset_SiteCommon',
            'Pset_LandRegistration'
        ]
    }
    
    # Standard quantity sets by element type
    STANDARD_QUANTITY_SETS = {
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
        'IfcBuildingStorey': ['Qto_BuildingStoreyBaseQuantities']
    }
    
    def __init__(self, ifc_file_path: str):
        self.ifc_file_path = ifc_file_path
        self._ifc_file: Optional[Any] = None
        
        if not IFC_AVAILABLE:
            raise ImportError("IfcOpenShell is required for IFC processing")
    
    def open_file(self) -> bool:
        """Open IFC file."""
        try:
            self._ifc_file = ifcopenshell.open(self.ifc_file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to open IFC file: {e}")
            return False
    
    def extract_element_properties(
        self, 
        element: Any,
        include_quantities: bool = True
    ) -> ElementProperties:
        """
        Extract all properties for an element.
        
        Args:
            element: IFC element instance
            include_quantities: Whether to include quantity sets
        
        Returns:
            ElementProperties with all extracted data
        """
        element_props = ElementProperties(
            element_id=str(element.id()),
            global_id=element.GlobalId,
            element_type=element.is_a(),
            name=getattr(element, 'Name', '')
        )
        
        # Extract property sets
        element_props.property_sets = self._extract_property_sets(element)
        
        # Extract quantity sets
        if include_quantities:
            element_props.quantity_sets = self._extract_quantity_sets(element)
        
        # Extract material information
        element_props.material_info = self._extract_material_info(element)
        
        # Extract classification
        element_props.classification = self._extract_classification(element)
        
        return element_props
    
    def extract_all_properties(
        self,
        element_types: Optional[List[str]] = None
    ) -> List[ElementProperties]:
        """
        Extract properties for all elements.
        
        Args:
            element_types: Optional list of element types to extract
        
        Returns:
            List of ElementProperties
        """
        if not self._ifc_file:
            if not self.open_file():
                return []
        
        all_properties = []
        
        if element_types:
            elements = []
            for elem_type in element_types:
                elements.extend(self._ifc_file.by_type(elem_type))
        else:
            elements = self._ifc_file.by_type('IfcElement')
        
        logger.info(f"Extracting properties for {len(elements)} elements")
        
        for element in elements:
            try:
                props = self.extract_element_properties(element)
                all_properties.append(props)
            except Exception as e:
                logger.warning(f"Failed to extract properties for {element.GlobalId}: {e}")
        
        return all_properties
    
    def _extract_property_sets(self, element: Any) -> List[PropertySet]:
        """Extract property sets from element."""
        property_sets = []
        
        try:
            # Get property set relations
            if hasattr(element, 'IsDefinedBy'):
                for definition in element.IsDefinedBy:
                    if definition.is_a('IfcRelDefinesByProperties'):
                        property_set_def = definition.RelatingPropertyDefinition
                        
                        if property_set_def.is_a('IfcPropertySet'):
                            pset = self._parse_property_set(property_set_def)
                            if pset:
                                property_sets.append(pset)
                        
                        elif property_set_def.is_a('IfcPropertySetDefinition'):
                            # Handle other property set definition types
                            pass
        
        except Exception as e:
            logger.warning(f"Failed to extract property sets: {e}")
        
        return property_sets
    
    def _parse_property_set(self, pset_def: Any) -> Optional[PropertySet]:
        """Parse a property set definition."""
        try:
            pset = PropertySet(
                name=pset_def.Name,
                description=getattr(pset_def, 'Description', None),
                global_id=pset_def.GlobalId
            )
            
            # Extract properties
            if hasattr(pset_def, 'HasProperties'):
                for prop in pset_def.HasProperties:
                    prop_value = self._parse_property(prop)
                    if prop_value:
                        pset.properties.append(prop_value)
            
            return pset
            
        except Exception as e:
            logger.warning(f"Failed to parse property set: {e}")
            return None
    
    def _parse_property(self, prop: Any) -> Optional[PropertyValue]:
        """Parse a single property."""
        try:
            prop_type = prop.is_a()
            
            if prop_type == 'IfcPropertySingleValue':
                return PropertyValue(
                    name=prop.Name,
                    value=self._convert_value(prop.NominalValue),
                    nominal_value=self._convert_value(prop.NominalValue),
                    unit=str(prop.Unit) if hasattr(prop, 'Unit') and prop.Unit else None,
                    description=getattr(prop, 'Description', None),
                    property_type='single'
                )
            
            elif prop_type == 'IfcPropertyEnumeratedValue':
                return PropertyValue(
                    name=prop.Name,
                    value=[self._convert_value(v) for v in prop.EnumerationValues],
                    description=getattr(prop, 'Description', None),
                    property_type='enumerated'
                )
            
            elif prop_type == 'IfcPropertyBoundedValue':
                return PropertyValue(
                    name=prop.Name,
                    value={
                        'lower': self._convert_value(prop.LowerBoundValue),
                        'upper': self._convert_value(prop.UpperBoundValue)
                    },
                    description=getattr(prop, 'Description', None),
                    property_type='bounded'
                )
            
            elif prop_type == 'IfcPropertyListValue':
                return PropertyValue(
                    name=prop.Name,
                    value=[self._convert_value(v) for v in prop.ListValues],
                    description=getattr(prop, 'Description', None),
                    property_type='list'
                )
            
            else:
                # Handle other property types
                return PropertyValue(
                    name=prop.Name,
                    value=str(prop),
                    description=getattr(prop, 'Description', None),
                    property_type='unknown'
                )
                
        except Exception as e:
            logger.warning(f"Failed to parse property {prop.Name}: {e}")
            return None
    
    def _extract_quantity_sets(self, element: Any) -> List[PropertySet]:
        """Extract quantity sets from element."""
        quantity_sets = []
        
        try:
            if hasattr(element, 'IsDefinedBy'):
                for definition in element.IsDefinedBy:
                    if definition.is_a('IfcRelDefinesByProperties'):
                        quantity_def = definition.RelatingPropertyDefinition
                        
                        if quantity_def.is_a('IfcElementQuantity'):
                            qset = self._parse_quantity_set(quantity_def)
                            if qset:
                                quantity_sets.append(qset)
        
        except Exception as e:
            logger.warning(f"Failed to extract quantity sets: {e}")
        
        return quantity_sets
    
    def _parse_quantity_set(self, quantity_def: Any) -> Optional[PropertySet]:
        """Parse a quantity set definition."""
        try:
            qset = PropertySet(
                name=quantity_def.Name,
                description=getattr(quantity_def, 'Description', None),
                global_id=quantity_def.GlobalId
            )
            
            # Extract quantities
            if hasattr(quantity_def, 'Quantities'):
                for quantity in quantity_def.Quantities:
                    quantity_value = self._parse_quantity(quantity)
                    if quantity_value:
                        qset.properties.append(quantity_value)
            
            return qset
            
        except Exception as e:
            logger.warning(f"Failed to parse quantity set: {e}")
            return None
    
    def _parse_quantity(self, quantity: Any) -> Optional[PropertyValue]:
        """Parse a single quantity."""
        try:
            quantity_type = quantity.is_a()
            
            if quantity_type == 'IfcQuantityLength':
                return PropertyValue(
                    name=quantity.Name,
                    value=quantity.LengthValue,
                    unit=quantity.Unit,
                    description=getattr(quantity, 'Description', None),
                    property_type='length'
                )
            
            elif quantity_type == 'IfcQuantityArea':
                return PropertyValue(
                    name=quantity.Name,
                    value=quantity.AreaValue,
                    unit=quantity.Unit,
                    description=getattr(quantity, 'Description', None),
                    property_type='area'
                )
            
            elif quantity_type == 'IfcQuantityVolume':
                return PropertyValue(
                    name=quantity.Name,
                    value=quantity.VolumeValue,
                    unit=quantity.Unit,
                    description=getattr(quantity, 'Description', None),
                    property_type='volume'
                )
            
            elif quantity_type == 'IfcQuantityWeight':
                return PropertyValue(
                    name=quantity.Name,
                    value=quantity.WeightValue,
                    unit=quantity.Unit,
                    description=getattr(quantity, 'Description', None),
                    property_type='weight'
                )
            
            elif quantity_type == 'IfcQuantityCount':
                return PropertyValue(
                    name=quantity.Name,
                    value=quantity.CountValue,
                    description=getattr(quantity, 'Description', None),
                    property_type='count'
                )
            
            else:
                return PropertyValue(
                    name=quantity.Name,
                    value=str(quantity),
                    description=getattr(quantity, 'Description', None),
                    property_type='unknown'
                )
                
        except Exception as e:
            logger.warning(f"Failed to parse quantity: {e}")
            return None
    
    def _extract_material_info(self, element: Any) -> Dict[str, Any]:
        """Extract material information for element."""
        material_info = {}
        
        try:
            if hasattr(element, 'HasAssociations'):
                for association in element.HasAssociations:
                    if association.is_a('IfcRelAssociatesMaterial'):
                        material = association.RelatingMaterial
                        
                        if material.is_a('IfcMaterial'):
                            material_info['name'] = material.Name
                            material_info['category'] = getattr(material, 'Category', None)
                        
                        elif material.is_a('IfcMaterialLayerSet'):
                            material_info['type'] = 'layer_set'
                            material_info['layers'] = [
                                {
                                    'material': layer.Material.Name if layer.Material else None,
                                    'thickness': layer.LayerThickness
                                }
                                for layer in material.MaterialLayers
                            ]
                        
                        elif material.is_a('IfcMaterialProfileSet'):
                            material_info['type'] = 'profile_set'
                            material_info['profiles'] = [
                                {
                                    'name': profile.Name,
                                    'material': profile.Material.Name if profile.Material else None
                                }
                                for profile in material.MaterialProfiles
                            ]
        
        except Exception as e:
            logger.warning(f"Failed to extract material info: {e}")
        
        return material_info
    
    def _extract_classification(self, element: Any) -> Dict[str, Any]:
        """Extract classification information for element."""
        classification = {}
        
        try:
            if hasattr(element, 'HasAssociations'):
                for association in element.HasAssociations:
                    if association.is_a('IfcRelAssociatesClassification'):
                        classification_ref = association.RelatingClassification
                        
                        if classification_ref.is_a('IfcClassificationReference'):
                            classification['reference'] = classification_ref.Identification
                            classification['name'] = classification_ref.Name
                            
                            if classification_ref.ReferencedSource:
                                source = classification_ref.ReferencedSource
                                classification['source'] = source.Name if hasattr(source, 'Name') else None
        
        except Exception as e:
            logger.warning(f"Failed to extract classification: {e}")
        
        return classification
    
    def _convert_value(self, value: Any) -> Any:
        """Convert IFC value to Python value."""
        if value is None:
            return None
        
        # Handle wrapped values
        if hasattr(value, 'wrappedValue'):
            return value.wrappedValue
        
        # Handle direct values
        if hasattr(value, 'value'):
            return value.value
        
        return str(value)
    
    def get_extraction_summary(
        self, 
        properties: List[ElementProperties]
    ) -> ExtractionSummary:
        """Generate summary of extraction results."""
        summary = ExtractionSummary(
            total_elements=len(properties),
            elements_with_properties=0,
            total_property_sets=0,
            total_properties=0,
            property_set_names=set(),
            quantity_set_names=set()
        )
        
        for elem_props in properties:
            if elem_props.property_sets or elem_props.quantity_sets:
                summary.elements_with_properties += 1
            
            summary.total_property_sets += len(elem_props.property_sets)
            summary.total_property_sets += len(elem_props.quantity_sets)
            
            for pset in elem_props.property_sets:
                summary.property_set_names.add(pset.name)
                summary.total_properties += len(pset.properties)
            
            for qset in elem_props.quantity_sets:
                summary.quantity_set_names.add(qset.name)
                summary.total_properties += len(qset.properties)
        
        summary.property_set_names = list(summary.property_set_names)
        summary.quantity_set_names = list(summary.quantity_set_names)
        
        return summary
    
    def export_to_json(
        self, 
        properties: List[ElementProperties], 
        output_path: str
    ) -> bool:
        """Export properties to JSON file."""
        try:
            data = {
                "exported_at": datetime.utcnow().isoformat(),
                "file_path": self.ifc_file_path,
                "elements": [p.to_dict() for p in properties],
                "summary": asdict(self.get_extraction_summary(properties))
            }
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported properties to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def close(self) -> None:
        """Close IFC file."""
        self._ifc_file = None


# Convenience function
async def extract_ifc_properties(
    ifc_file_path: str,
    element_types: Optional[List[str]] = None
) -> List[ElementProperties]:
    """
    Extract properties from IFC file.
    
    Args:
        ifc_file_path: Path to IFC file
        element_types: Optional list of element types to extract
    
    Returns:
        List of ElementProperties
    """
    extractor = IFCPropertyExtractor(ifc_file_path)
    properties = extractor.extract_all_properties(element_types)
    extractor.close()
    return properties
