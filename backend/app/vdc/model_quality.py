"""
Model Quality - IFC Validation (bSI IDS Compliance)
Validates IFC models against buildingSMART IDS (Information Delivery Specification).
"""
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Validation severity levels."""
    ERROR = "error"       # Must be fixed
    WARNING = "warning"   # Should be fixed
    INFO = "info"         # Good practice
    PASS = "pass"         # Validation passed


class ValidationCategory(str, Enum):
    """Categories of validation checks."""
    GEOMETRY = "geometry"
    SEMANTIC = "semantic"
    CLASSIFICATION = "classification"
    PROPERTY = "property"
    RELATIONSHIP = "relationship"
    MATERIAL = "material"
    NAMING = "naming"
    UNITS = "units"
    IFC_SCHEMA = "ifc_schema"


@dataclass
class ValidationRule:
    """A validation rule for IFC models."""
    id: str
    name: str
    category: ValidationCategory
    description: str
    applicability: str  # Which elements this applies to
    requirement: str    # What is required
    severity: ValidationLevel
    enabled: bool = True
    custom_check: Optional[str] = None


@dataclass
class ValidationFinding:
    """A finding from validation."""
    rule_id: str
    rule_name: str
    category: ValidationCategory
    severity: ValidationLevel
    element_id: Optional[str]
    element_type: Optional[str]
    element_name: Optional[str]
    message: str
    expected: Optional[str] = None
    actual: Optional[str] = None
    recommendation: str = ""


@dataclass
class ValidationResult:
    """Result of model validation."""
    model_id: str
    model_name: str
    validated_at: datetime
    ifc_schema: str
    total_elements: int
    findings: List[ValidationFinding] = field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ValidationLevel.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ValidationLevel.WARNING)
    
    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == ValidationLevel.INFO)
    
    @property
    def is_valid(self) -> bool:
        return self.error_count == 0
    
    @property
    def score(self) -> float:
        """Calculate quality score (0-100)."""
        if not self.findings:
            return 100.0
        
        weights = {
            ValidationLevel.ERROR: 10,
            ValidationLevel.WARNING: 3,
            ValidationLevel.INFO: 1
        }
        
        total_penalty = sum(
            weights.get(f.severity, 1) 
            for f in self.findings
        )
        
        # Normalize score
        max_penalty = self.total_elements * 10
        score = max(0, 100 - (total_penalty / max_penalty * 100))
        return round(score, 2)
    
    def get_findings_by_category(self, category: ValidationCategory) -> List[ValidationFinding]:
        """Get findings filtered by category."""
        return [f for f in self.findings if f.category == category]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'model_id': self.model_id,
            'model_name': self.model_name,
            'validated_at': self.validated_at.isoformat(),
            'ifc_schema': self.ifc_schema,
            'total_elements': self.total_elements,
            'score': self.score,
            'is_valid': self.is_valid,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'info_count': self.info_count,
            'findings_by_category': {
                cat.value: len(self.get_findings_by_category(cat))
                for cat in ValidationCategory
            },
            'findings': [
                {
                    'rule': f.rule_name,
                    'category': f.category.value,
                    'severity': f.severity.value,
                    'element': f.element_name or f.element_id,
                    'message': f.message,
                    'recommendation': f.recommendation
                }
                for f in self.findings
            ]
        }


class IDSComplianceChecker:
    """Checker for buildingSMART IDS compliance."""
    
    # Standard IDS validation rules
    DEFAULT_RULES = [
        # IFC Schema Rules
        ValidationRule(
            id="IDS-001",
            name="IFC Schema Version",
            category=ValidationCategory.IFC_SCHEMA,
            description="Model must use supported IFC schema version",
            applicability="All models",
            requirement="IFC2X3, IFC4, or IFC4X3",
            severity=ValidationLevel.ERROR
        ),
        
        # Geometry Rules
        ValidationRule(
            id="IDS-002",
            name="Valid Geometry",
            category=ValidationCategory.GEOMETRY,
            description="Elements must have valid geometry representations",
            applicability="All physical elements",
            requirement="Geometry must be valid and non-zero volume",
            severity=ValidationLevel.ERROR
        ),
        ValidationRule(
            id="IDS-003",
            name="Placement Defined",
            category=ValidationCategory.GEOMETRY,
            description="Elements must have defined placement",
            applicability="All physical elements",
            requirement="ObjectPlacement must be defined",
            severity=ValidationLevel.ERROR
        ),
        
        # Semantic Rules
        ValidationRule(
            id="IDS-004",
            name="GlobalId Present",
            category=ValidationCategory.SEMANTIC,
            description="All elements must have a GlobalId",
            applicability="All elements",
            requirement="GlobalId attribute must be present and valid UUID",
            severity=ValidationLevel.ERROR
        ),
        ValidationRule(
            id="IDS-005",
            name="Name Attribute",
            category=ValidationCategory.SEMANTIC,
            description="Elements should have meaningful names",
            applicability="All elements",
            requirement="Name attribute should be present and meaningful",
            severity=ValidationLevel.WARNING
        ),
        
        # Classification Rules
        ValidationRule(
            id="IDS-006",
            name="Element Classification",
            category=ValidationCategory.CLASSIFICATION,
            description="Elements should have classification references",
            applicability="All physical elements",
            requirement="IfcClassificationReference should be present",
            severity=ValidationLevel.WARNING
        ),
        ValidationRule(
            id="IDS-007",
            name="Uniformat Classification",
            category=ValidationCategory.CLASSIFICATION,
            description="Major elements should have Uniformat classification",
            applicability="IfcBuildingElement subtypes",
            requirement="Uniformat classification should be present",
            severity=ValidationLevel.INFO
        ),
        
        # Property Rules
        ValidationRule(
            id="IDS-008",
            name="Required Properties",
            category=ValidationCategory.PROPERTY,
            description="Elements must have required properties",
            applicability="All physical elements",
            requirement="IfcPropertySet with required properties",
            severity=ValidationLevel.WARNING
        ),
        ValidationRule(
            id="IDS-009",
            name="Property Data Types",
            category=ValidationCategory.PROPERTY,
            description="Properties must have correct data types",
            applicability="All properties",
            requirement="Property values must match expected types",
            severity=ValidationLevel.ERROR
        ),
        ValidationRule(
            id="IDS-010",
            name="Fire Rating Property",
            category=ValidationCategory.PROPERTY,
            description="Walls and doors should have fire rating",
            applicability="IfcWall, IfcDoor",
            requirement="FireRating property should be present",
            severity=ValidationLevel.INFO
        ),
        
        # Material Rules
        ValidationRule(
            id="IDS-011",
            name="Material Assignment",
            category=ValidationCategory.MATERIAL,
            description="Physical elements should have materials assigned",
            applicability="All physical elements",
            requirement="IfcMaterial or IfcMaterialLayerSet should be present",
            severity=ValidationLevel.WARNING
        ),
        
        # Naming Rules
        ValidationRule(
            id="IDS-012",
            name="Consistent Naming",
            category=ValidationCategory.NAMING,
            description="Element names should follow naming convention",
            applicability="All elements",
            requirement="Names should be consistent and descriptive",
            severity=ValidationLevel.INFO
        ),
        
        # Unit Rules
        ValidationRule(
            id="IDS-013",
            name="Unit Assignment",
            category=ValidationCategory.UNITS,
            description="Model must have unit assignment",
            applicability="Project",
            requirement="IfcUnitAssignment must be present",
            severity=ValidationLevel.ERROR
        ),
        
        # Relationship Rules
        ValidationRule(
            id="IDS-014",
            name="Spatial Containment",
            category=ValidationCategory.RELATIONSHIP,
            description="Elements must be contained in spatial structure",
            applicability="All physical elements",
            requirement="IfcRelContainedInSpatialStructure must exist",
            severity=ValidationLevel.ERROR
        ),
    ]
    
    def __init__(self, custom_rules: Optional[List[ValidationRule]] = None):
        self.rules = self.DEFAULT_RULES + (custom_rules or [])
    
    def validate_model(self, model_data: Dict[str, Any],
                      model_id: str = "",
                      model_name: str = "") -> ValidationResult:
        """Validate an IFC model against IDS rules."""
        result = ValidationResult(
            model_id=model_id,
            model_name=model_name,
            validated_at=datetime.utcnow(),
            ifc_schema=model_data.get('schema', 'UNKNOWN'),
            total_elements=len(model_data.get('elements', []))
        )
        
        elements = model_data.get('elements', [])
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            findings = self._check_rule(rule, elements, model_data)
            result.findings.extend(findings)
        
        logger.info(f"Validation complete: {result.error_count} errors, "
                   f"{result.warning_count} warnings, score: {result.score}")
        
        return result
    
    def _check_rule(self, rule: ValidationRule, 
                   elements: List[Dict], 
                   model_data: Dict) -> List[ValidationFinding]:
        """Check a single rule against model elements."""
        findings = []
        
        if rule.id == "IDS-001":
            # Check IFC schema version
            schema = model_data.get('schema', '')
            valid_schemas = ['IFC2X3', 'IFC4', 'IFC4X3']
            if not any(s in schema for s in valid_schemas):
                findings.append(ValidationFinding(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    category=rule.category,
                    severity=rule.severity,
                    element_id=None,
                    element_type=None,
                    element_name=None,
                    message=f"Unsupported IFC schema: {schema}",
                    expected="IFC2X3, IFC4, or IFC4X3",
                    actual=schema,
                    recommendation="Export model using supported IFC schema version"
                ))
        
        elif rule.id == "IDS-004":
            # Check GlobalId presence
            for elem in elements:
                global_id = elem.get('GlobalId')
                if not global_id or not self._is_valid_uuid(global_id):
                    findings.append(ValidationFinding(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        category=rule.category,
                        severity=rule.severity,
                        element_id=elem.get('id'),
                        element_type=elem.get('type'),
                        element_name=elem.get('Name'),
                        message="Missing or invalid GlobalId",
                        expected="Valid UUID format GlobalId",
                        actual=global_id,
                        recommendation="Assign valid GlobalId to element"
                    ))
        
        elif rule.id == "IDS-005":
            # Check Name attribute
            for elem in elements:
                name = elem.get('Name', '')
                if not name or name in ['', 'None', 'null']:
                    findings.append(ValidationFinding(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        category=rule.category,
                        severity=rule.severity,
                        element_id=elem.get('id'),
                        element_type=elem.get('type'),
                        element_name=name,
                        message="Element name is missing or empty",
                        expected="Meaningful element name",
                        actual=name,
                        recommendation="Assign descriptive name to element"
                    ))
        
        elif rule.id == "IDS-011":
            # Check material assignment
            for elem in elements:
                if elem.get('type', '').startswith('Ifc'):
                    # Check if it's a physical element
                    physical_types = ['IfcWall', 'IfcSlab', 'IfcColumn', 
                                     'IfcBeam', 'IfcDoor', 'IfcWindow',
                                     'IfcRoof', 'IfcStair', 'IfcPlate']
                    if any(elem.get('type', '').startswith(pt) for pt in physical_types):
                        if not elem.get('HasAssociations'):
                            findings.append(ValidationFinding(
                                rule_id=rule.id,
                                rule_name=rule.name,
                                category=rule.category,
                                severity=rule.severity,
                                element_id=elem.get('id'),
                                element_type=elem.get('type'),
                                element_name=elem.get('Name'),
                                message="Physical element has no material assigned",
                                expected="Material assignment via IfcRelAssociatesMaterial",
                                actual="No material",
                                recommendation="Assign appropriate material to element"
                            ))
        
        return findings
    
    def _is_valid_uuid(self, value: str) -> bool:
        """Check if value is a valid UUID."""
        if not value:
            return False
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(value))
    
    def generate_ids_specification(self, requirements: List[Dict[str, Any]]) -> str:
        """Generate IDS XML specification from requirements."""
        # Placeholder - would generate proper IDS XML
        ids_xml = """<?xml version="1.0" encoding="UTF-8"?>
<ids:ids xmlns:ids="http://standards.buildingsmart.org/IDS" 
         xmlns:xs="http://www.w3.org/2001/XMLSchema"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://standards.buildingsmart.org/IDS http://standards.buildingsmart.org/IDS/ids_09.xsd">
    <ids:info>
        <ids:title>Cerebrum IDS Specification</ids:title>
        <ids:copyright>Cerebrum AI</ids:copyright>
        <ids:version>1.0</ids:version>
        <ids:description>Information Delivery Specification for Cerebrum Projects</ids:description>
    </ids:info>
    <ids:specifications>
"""
        
        for req in requirements:
            ids_xml += f"""        <ids:specification name="{req.get('name', 'Unnamed')}" ifcVersion="IFC4">
            <ids:applicability>
                <ids:entity>
                    <ids:name>
                        <ids:simpleValue>{req.get('entity', 'IfcElement')}</ids:simpleValue>
                    </ids:name>
                </ids:entity>
            </ids:applicability>
            <ids:requirements>
                <ids:attribute cardinality="required">
                    <ids:name>
                        <ids:simpleValue>Name</ids:simpleValue>
                    </ids:name>
                </ids:attribute>
            </ids:requirements>
        </ids:specification>
"""
        
        ids_xml += """    </ids:specifications>
</ids:ids>"""
        
        return ids_xml


class ModelQualityDashboard:
    """Dashboard for model quality metrics."""
    
    def __init__(self):
        self.validation_history: List[ValidationResult] = []
    
    def add_result(self, result: ValidationResult):
        """Add validation result to history."""
        self.validation_history.append(result)
    
    def get_quality_trend(self, model_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get quality score trend over time."""
        results = self.validation_history
        if model_id:
            results = [r for r in results if r.model_id == model_id]
        
        return [
            {
                'date': r.validated_at.isoformat(),
                'score': r.score,
                'errors': r.error_count,
                'warnings': r.warning_count
            }
            for r in sorted(results, key=lambda x: x.validated_at)
        ]
    
    def get_common_issues(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most common validation issues."""
        issue_counts = {}
        
        for result in self.validation_history:
            for finding in result.findings:
                key = (finding.rule_name, finding.category.value)
                if key not in issue_counts:
                    issue_counts[key] = {'count': 0, 'rule': finding.rule_name, 
                                        'category': finding.category.value}
                issue_counts[key]['count'] += 1
        
        sorted_issues = sorted(
            issue_counts.values(), 
            key=lambda x: x['count'], 
            reverse=True
        )
        
        return sorted_issues[:limit]
