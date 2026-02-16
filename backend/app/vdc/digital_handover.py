"""
Digital Handover - COBie-compliant Data Export
Exports facility data in COBie (Construction Operations Building Information Exchange) format.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import csv
import io
import json
import logging

logger = logging.getLogger(__name__)


class COBieSheet(str, Enum):
    """COBie spreadsheet sheets."""
    INSTRUCTION = "Instruction"
    CONTACT = "Contact"
    FACILITY = "Facility"
    FLOOR = "Floor"
    SPACE = "Space"
    ZONE = "Zone"
    TYPE = "Type"
    COMPONENT = "Component"
    SYSTEM = "System"
    ASSEMBLY = "Assembly"
    CONNECTION = "Connection"
    SPARE = "Spare"
    RESOURCE = "Resource"
    JOB = "Job"
    IMPACT = "Impact"
    DOCUMENT = "Document"
    ATTRIBUTE = "Attribute"
    COORDINATE = "Coordinate"
    ISSUE = "Issue"


@dataclass
class COBieContact:
    """COBie Contact entry."""
    email: str
    created_by: str
    created_on: date
    category: str
    company: str
    phone: str
    ext_system: str = "Cerebrum"
    ext_object: str = ""
    ext_identifier: str = ""
    department: str = ""
    organization_code: str = ""
    given_name: str = ""
    family_name: str = ""
    street: str = ""
    postal_box: str = ""
    town: str = ""
    state_region: str = ""
    postal_code: str = ""
    country: str = ""


@dataclass
class COBieFacility:
    """COBie Facility entry."""
    name: str
    created_by: str
    created_on: date
    category: str
    project_name: str
    site_name: str
    linear_units: str = "meters"
    area_units: str = "square meters"
    volume_units: str = "cubic meters"
    currency_unit: str = "USD"
    area_measurement: str = "Gross"
    ext_system: str = "Cerebrum"
    ext_object: str = ""
    ext_identifier: str = ""
    description: str = ""
    project_description: str = ""
    site_description: str = ""
    phase: str = ""


@dataclass
class COBieFloor:
    """COBie Floor entry."""
    name: str
    created_by: str
    created_on: date
    category: str
    ext_system: str = "Cerebrum"
    ext_object: str = ""
    ext_identifier: str = ""
    description: str = ""
    elevation: float = 0.0
    height: float = 0.0


@dataclass
class COBieSpace:
    """COBie Space entry."""
    name: str
    created_by: str
    created_on: date
    category: str
    floor_name: str
    ext_system: str = "Cerebrum"
    ext_object: str = ""
    ext_identifier: str = ""
    description: str = ""
    room_tag: str = ""
    usable_height: float = 0.0
    gross_area: float = 0.0
    net_area: float = 0.0


@dataclass
class COBieComponent:
    """COBie Component entry."""
    name: str
    created_by: str
    created_on: date
    type_name: str
    space: str
    ext_system: str = "Cerebrum"
    ext_object: str = ""
    ext_identifier: str = ""
    serial_number: str = ""
    installation_date: Optional[date] = None
    warranty_start_date: Optional[date] = None
    tag_number: str = ""
    bar_code: str = ""
    asset_identifier: str = ""


@dataclass
class COBieType:
    """COBie Type entry."""
    name: str
    created_by: str
    created_on: date
    category: str
    ext_system: str = "Cerebrum"
    ext_object: str = ""
    ext_identifier: str = ""
    description: str = ""
    asset_type: str = ""  # Fixed or Moveable
    manufacturer: str = ""
    model_number: str = ""
    warranty_guarantor_parts: str = ""
    warranty_duration_parts: int = 0
    warranty_guarantor_labor: str = ""
    warranty_duration_labor: int = 0
    warranty_duration_unit: str = "year"
    replacement_cost: float = 0.0
    expected_life: int = 0
    duration_unit: str = "year"
    nominal_length: float = 0.0
    nominal_width: float = 0.0
    nominal_height: float = 0.0
    model_reference: str = ""
    shape: str = ""
    size: str = ""
    color: str = ""
    finish: str = ""
    grade: str = ""
    material: str = ""
    constituents: str = ""
    features: str = ""
    accessibility_performance: str = ""
    code_performance: str = ""
    sustainability_performance: str = ""


@dataclass
class COBieDocument:
    """COBie Document entry."""
    name: str
    created_by: str
    created_on: date
    category: str
    approval_by: str
    stage: str
    sheet_name: str
    row_name: str
    directory: str
    file: str
    ext_system: str = "Cerebrum"
    ext_object: str = ""
    ext_identifier: str = ""
    description: str = ""
    reference: str = ""


class COBieExporter:
    """Exports facility data to COBie format."""
    
    COBIE_VERSION = "2.4"
    
    def __init__(self):
        self.contacts: List[COBieContact] = []
        self.facilities: List[COBieFacility] = []
        self.floors: List[COBieFloor] = []
        self.spaces: List[COBieSpace] = []
        self.zones: List[Dict[str, Any]] = []
        self.types: List[COBieType] = []
        self.components: List[COBieComponent] = []
        self.systems: List[Dict[str, Any]] = []
        self.assemblies: List[Dict[str, Any]] = []
        self.connections: List[Dict[str, Any]] = []
        self.spares: List[Dict[str, Any]] = []
        self.resources: List[Dict[str, Any]] = []
        self.jobs: List[Dict[str, Any]] = []
        self.impacts: List[Dict[str, Any]] = []
        self.documents: List[COBieDocument] = []
        self.attributes: List[Dict[str, Any]] = []
        self.coordinates: List[Dict[str, Any]] = []
        self.issues: List[Dict[str, Any]] = []
    
    def add_contact(self, contact: COBieContact):
        """Add a contact entry."""
        self.contacts.append(contact)
    
    def add_facility(self, facility: COBieFacility):
        """Add a facility entry."""
        self.facilities.append(facility)
    
    def add_floor(self, floor: COBieFloor):
        """Add a floor entry."""
        self.floors.append(floor)
    
    def add_space(self, space: COBieSpace):
        """Add a space entry."""
        self.spaces.append(space)
    
    def add_type(self, type_entry: COBieType):
        """Add a type entry."""
        self.types.append(type_entry)
    
    def add_component(self, component: COBieComponent):
        """Add a component entry."""
        self.components.append(component)
    
    def add_document(self, document: COBieDocument):
        """Add a document entry."""
        self.documents.append(document)
    
    def export_to_excel(self, output_path: str) -> str:
        """Export to Excel format (placeholder)."""
        # Would use openpyxl or similar
        logger.info(f"Exporting COBie to Excel: {output_path}")
        
        # For now, export as CSV files
        import os
        os.makedirs(output_path, exist_ok=True)
        
        self.export_sheet_to_csv(self._contacts_to_rows(), 
                                os.path.join(output_path, "Contact.csv"))
        self.export_sheet_to_csv(self._facilities_to_rows(),
                                os.path.join(output_path, "Facility.csv"))
        self.export_sheet_to_csv(self._floors_to_rows(),
                                os.path.join(output_path, "Floor.csv"))
        self.export_sheet_to_csv(self._spaces_to_rows(),
                                os.path.join(output_path, "Space.csv"))
        self.export_sheet_to_csv(self._types_to_rows(),
                                os.path.join(output_path, "Type.csv"))
        self.export_sheet_to_csv(self._components_to_rows(),
                                os.path.join(output_path, "Component.csv"))
        self.export_sheet_to_csv(self._documents_to_rows(),
                                os.path.join(output_path, "Document.csv"))
        
        return output_path
    
    def export_sheet_to_csv(self, rows: List[List[str]], file_path: str):
        """Export a sheet to CSV."""
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    
    def export_to_json(self) -> Dict[str, Any]:
        """Export to JSON format."""
        return {
            'version': self.COBIE_VERSION,
            'generated_at': datetime.utcnow().isoformat(),
            'Contact': [self._contact_to_dict(c) for c in self.contacts],
            'Facility': [self._facility_to_dict(f) for f in self.facilities],
            'Floor': [self._floor_to_dict(f) for f in self.floors],
            'Space': [self._space_to_dict(s) for s in self.spaces],
            'Type': [self._type_to_dict(t) for t in self.types],
            'Component': [self._component_to_dict(c) for c in self.components],
            'Document': [self._document_to_dict(d) for d in self.documents],
        }
    
    def _contacts_to_rows(self) -> List[List[str]]:
        """Convert contacts to CSV rows."""
        headers = ["Email", "CreatedBy", "CreatedOn", "Category", "Company", 
                  "Phone", "ExtSystem", "ExtObject", "ExtIdentifier", "Department",
                  "OrganizationCode", "GivenName", "FamilyName", "Street", 
                  "PostalBox", "Town", "StateRegion", "PostalCode", "Country"]
        
        rows = [headers]
        for c in self.contacts:
            rows.append([
                c.email, c.created_by, str(c.created_on), c.category, c.company,
                c.phone, c.ext_system, c.ext_object, c.ext_identifier, c.department,
                c.organization_code, c.given_name, c.family_name, c.street,
                c.postal_box, c.town, c.state_region, c.postal_code, c.country
            ])
        return rows
    
    def _facilities_to_rows(self) -> List[List[str]]:
        """Convert facilities to CSV rows."""
        headers = ["Name", "CreatedBy", "CreatedOn", "Category", "ProjectName",
                  "SiteName", "LinearUnits", "AreaUnits", "VolumeUnits",
                  "CurrencyUnit", "AreaMeasurement", "ExtSystem", "ExtObject",
                  "ExtIdentifier", "Description", "ProjectDescription",
                  "SiteDescription", "Phase"]
        
        rows = [headers]
        for f in self.facilities:
            rows.append([
                f.name, f.created_by, str(f.created_on), f.category, f.project_name,
                f.site_name, f.linear_units, f.area_units, f.volume_units,
                f.currency_unit, f.area_measurement, f.ext_system, f.ext_object,
                f.ext_identifier, f.description, f.project_description,
                f.site_description, f.phase
            ])
        return rows
    
    def _floors_to_rows(self) -> List[List[str]]:
        """Convert floors to CSV rows."""
        headers = ["Name", "CreatedBy", "CreatedOn", "Category", "ExtSystem",
                  "ExtObject", "ExtIdentifier", "Description", "Elevation", "Height"]
        
        rows = [headers]
        for f in self.floors:
            rows.append([
                f.name, f.created_by, str(f.created_on), f.category, f.ext_system,
                f.ext_object, f.ext_identifier, f.description, str(f.elevation),
                str(f.height)
            ])
        return rows
    
    def _spaces_to_rows(self) -> List[List[str]]:
        """Convert spaces to CSV rows."""
        headers = ["Name", "CreatedBy", "CreatedOn", "Category", "FloorName",
                  "ExtSystem", "ExtObject", "ExtIdentifier", "Description",
                  "RoomTag", "UsableHeight", "GrossArea", "NetArea"]
        
        rows = [headers]
        for s in self.spaces:
            rows.append([
                s.name, s.created_by, str(s.created_on), s.category, s.floor_name,
                s.ext_system, s.ext_object, s.ext_identifier, s.description,
                s.room_tag, str(s.usable_height), str(s.gross_area), str(s.net_area)
            ])
        return rows
    
    def _types_to_rows(self) -> List[List[str]]:
        """Convert types to CSV rows."""
        headers = ["Name", "CreatedBy", "CreatedOn", "Category", "ExtSystem",
                  "ExtObject", "ExtIdentifier", "Description", "AssetType",
                  "Manufacturer", "ModelNumber", "WarrantyGuarantorParts",
                  "WarrantyDurationParts", "WarrantyGuarantorLabor",
                  "WarrantyDurationLabor", "WarrantyDurationUnit",
                  "ReplacementCost", "ExpectedLife", "DurationUnit"]
        
        rows = [headers]
        for t in self.types:
            rows.append([
                t.name, t.created_by, str(t.created_on), t.category, t.ext_system,
                t.ext_object, t.ext_identifier, t.description, t.asset_type,
                t.manufacturer, t.model_number, t.warranty_guarantor_parts,
                str(t.warranty_duration_parts), t.warranty_guarantor_labor,
                str(t.warranty_duration_labor), t.warranty_duration_unit,
                str(t.replacement_cost), str(t.expected_life), t.duration_unit
            ])
        return rows
    
    def _components_to_rows(self) -> List[List[str]]:
        """Convert components to CSV rows."""
        headers = ["Name", "CreatedBy", "CreatedOn", "TypeName", "Space",
                  "ExtSystem", "ExtObject", "ExtIdentifier", "SerialNumber",
                  "InstallationDate", "WarrantyStartDate", "TagNumber",
                  "BarCode", "AssetIdentifier"]
        
        rows = [headers]
        for c in self.components:
            rows.append([
                c.name, c.created_by, str(c.created_on), c.type_name, c.space,
                c.ext_system, c.ext_object, c.ext_identifier, c.serial_number,
                str(c.installation_date) if c.installation_date else "",
                str(c.warranty_start_date) if c.warranty_start_date else "",
                c.tag_number, c.bar_code, c.asset_identifier
            ])
        return rows
    
    def _documents_to_rows(self) -> List[List[str]]:
        """Convert documents to CSV rows."""
        headers = ["Name", "CreatedBy", "CreatedOn", "Category", "ApprovalBy",
                  "Stage", "SheetName", "RowName", "Directory", "File",
                  "ExtSystem", "ExtObject", "ExtIdentifier", "Description", "Reference"]
        
        rows = [headers]
        for d in self.documents:
            rows.append([
                d.name, d.created_by, str(d.created_on), d.category, d.approval_by,
                d.stage, d.sheet_name, d.row_name, d.directory, d.file,
                d.ext_system, d.ext_object, d.ext_identifier, d.description, d.reference
            ])
        return rows
    
    def _contact_to_dict(self, c: COBieContact) -> Dict[str, Any]:
        return {
            'email': c.email, 'created_by': c.created_by, 'created_on': str(c.created_on),
            'category': c.category, 'company': c.company, 'phone': c.phone
        }
    
    def _facility_to_dict(self, f: COBieFacility) -> Dict[str, Any]:
        return {
            'name': f.name, 'created_by': f.created_by, 'created_on': str(f.created_on),
            'category': f.category, 'project_name': f.project_name, 'site_name': f.site_name
        }
    
    def _floor_to_dict(self, f: COBieFloor) -> Dict[str, Any]:
        return {
            'name': f.name, 'created_by': f.created_by, 'created_on': str(f.created_on),
            'category': f.category, 'elevation': f.elevation, 'height': f.height
        }
    
    def _space_to_dict(self, s: COBieSpace) -> Dict[str, Any]:
        return {
            'name': s.name, 'created_by': s.created_by, 'created_on': str(s.created_on),
            'category': s.category, 'floor_name': s.floor_name, 'room_tag': s.room_tag
        }
    
    def _type_to_dict(self, t: COBieType) -> Dict[str, Any]:
        return {
            'name': t.name, 'created_by': t.created_by, 'created_on': str(t.created_on),
            'category': t.category, 'manufacturer': t.manufacturer, 'model_number': t.model_number
        }
    
    def _component_to_dict(self, c: COBieComponent) -> Dict[str, Any]:
        return {
            'name': c.name, 'created_by': c.created_by, 'created_on': str(c.created_on),
            'type_name': c.type_name, 'space': c.space, 'serial_number': c.serial_number
        }
    
    def _document_to_dict(self, d: COBieDocument) -> Dict[str, Any]:
        return {
            'name': d.name, 'created_by': d.created_by, 'created_on': str(d.created_on),
            'category': d.category, 'file': d.file, 'directory': d.directory
        }


class COBieGenerator:
    """Generates COBie data from BIM models."""
    
    def __init__(self):
        self.exporter = COBieExporter()
    
    def generate_from_model(self, model_data: Dict[str, Any],
                           project_info: Dict[str, Any]) -> COBieExporter:
        """Generate COBie data from BIM model."""
        # Add facility
        facility = COBieFacility(
            name=project_info.get('facility_name', 'Main Facility'),
            created_by=project_info.get('created_by', 'Cerebrum'),
            created_on=date.today(),
            category=project_info.get('facility_category', 'Commercial'),
            project_name=project_info.get('project_name', ''),
            site_name=project_info.get('site_name', ''),
            linear_units=project_info.get('linear_units', 'meters'),
            area_units=project_info.get('area_units', 'square meters'),
            currency_unit=project_info.get('currency', 'USD')
        )
        self.exporter.add_facility(facility)
        
        # Add contact
        contact = COBieContact(
            email=project_info.get('contact_email', 'info@cerebrum.ai'),
            created_by='Cerebrum',
            created_on=date.today(),
            category='Facility Manager',
            company=project_info.get('company_name', ''),
            phone=project_info.get('contact_phone', '')
        )
        self.exporter.add_contact(contact)
        
        # Process floors
        for floor_data in model_data.get('floors', []):
            floor = COBieFloor(
                name=floor_data.get('name', 'Floor'),
                created_by='Cerebrum',
                created_on=date.today(),
                category=floor_data.get('category', 'Level'),
                elevation=floor_data.get('elevation', 0.0),
                height=floor_data.get('height', 3.0)
            )
            self.exporter.add_floor(floor)
        
        # Process spaces
        for space_data in model_data.get('spaces', []):
            space = COBieSpace(
                name=space_data.get('name', 'Space'),
                created_by='Cerebrum',
                created_on=date.today(),
                category=space_data.get('category', 'Room'),
                floor_name=space_data.get('floor_name', ''),
                room_tag=space_data.get('room_tag', ''),
                gross_area=space_data.get('gross_area', 0.0),
                net_area=space_data.get('net_area', 0.0)
            )
            self.exporter.add_space(space)
        
        # Process types
        for type_data in model_data.get('types', []):
            type_entry = COBieType(
                name=type_data.get('name', 'Type'),
                created_by='Cerebrum',
                created_on=date.today(),
                category=type_data.get('category', ''),
                manufacturer=type_data.get('manufacturer', ''),
                model_number=type_data.get('model_number', ''),
                asset_type=type_data.get('asset_type', 'Fixed'),
                replacement_cost=type_data.get('replacement_cost', 0.0),
                expected_life=type_data.get('expected_life', 0)
            )
            self.exporter.add_type(type_entry)
        
        # Process components
        for comp_data in model_data.get('components', []):
            component = COBieComponent(
                name=comp_data.get('name', 'Component'),
                created_by='Cerebrum',
                created_on=date.today(),
                type_name=comp_data.get('type_name', ''),
                space=comp_data.get('space', ''),
                serial_number=comp_data.get('serial_number', ''),
                tag_number=comp_data.get('tag_number', ''),
                asset_identifier=comp_data.get('asset_identifier', '')
            )
            self.exporter.add_component(component)
        
        return self.exporter


# Convenience functions
def create_sample_cobie() -> COBieExporter:
    """Create sample COBie data for testing."""
    generator = COBieGenerator()
    
    model_data = {
        'floors': [
            {'name': 'Level 1', 'elevation': 0.0, 'height': 3.5},
            {'name': 'Level 2', 'elevation': 3.5, 'height': 3.5},
        ],
        'spaces': [
            {'name': '101', 'floor_name': 'Level 1', 'category': 'Office', 'gross_area': 50.0},
            {'name': '102', 'floor_name': 'Level 1', 'category': 'Conference', 'gross_area': 30.0},
            {'name': '201', 'floor_name': 'Level 2', 'category': 'Office', 'gross_area': 45.0},
        ],
        'types': [
            {'name': 'HVAC-Unit-Type-A', 'category': 'Equipment', 'manufacturer': 'Carrier'},
            {'name': 'Door-Type-01', 'category': 'Door', 'manufacturer': 'Steelcraft'},
        ],
        'components': [
            {'name': 'HVAC-001', 'type_name': 'HVAC-Unit-Type-A', 'space': '101'},
            {'name': 'Door-001', 'type_name': 'Door-Type-01', 'space': '101'},
        ]
    }
    
    project_info = {
        'facility_name': 'Sample Building',
        'project_name': 'Sample Project',
        'company_name': 'Cerebrum AI',
        'contact_email': 'info@cerebrum.ai'
    }
    
    return generator.generate_from_model(model_data, project_info)
