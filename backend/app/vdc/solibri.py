"""
Solibri Quality Assurance Integration
Solibri model checking and quality assurance
"""
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class SolibriRuleSet(Enum):
    """Solibri rule sets"""
    COORDINATION = "coordination"
    STRUCTURAL = "structural"
    ARCHITECTURAL = "architectural"
    MEP = "mep"
    ACCESSIBILITY = "accessibility"
    SAFETY = "safety"
    INFORMATION = "information"


class IssueSeverity(Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class SolibriRule:
    """Solibri checking rule"""
    rule_id: str
    name: str
    description: str
    rule_set: SolibriRuleSet
    severity: IssueSeverity
    entity_types: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class SolibriIssue:
    """Issue found by Solibri"""
    issue_id: str
    rule_id: str
    rule_name: str
    severity: IssueSeverity
    element_id: str
    element_type: str
    component_name: str
    description: str
    location: Dict[str, float] = field(default_factory=dict)
    screenshot_path: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "open"
    assigned_to: Optional[str] = None
    comments: List[Dict] = field(default_factory=list)


@dataclass
class SolibriReport:
    """Solibri checking report"""
    report_id: str
    model_id: str
    checked_at: datetime
    rule_set: SolibriRuleSet
    issues: List[SolibriIssue]
    summary: Dict[str, Any] = field(default_factory=dict)


class SolibriRuleManager:
    """Manages Solibri checking rules"""
    
    def __init__(self):
        self._rules: Dict[str, SolibriRule] = {}
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default Solibri rules"""
        default_rules = [
            # Coordination rules
            SolibriRule(
                rule_id="SOL-COORD-001",
                name="Clash Detection",
                description="Detect clashes between building elements",
                rule_set=SolibriRuleSet.COORDINATION,
                severity=IssueSeverity.ERROR,
                entity_types=["all"],
                parameters={'tolerance_mm': 1.0}
            ),
            SolibriRule(
                rule_id="SOL-COORD-002",
                name="Duplicate Elements",
                description="Detect duplicate building elements",
                rule_set=SolibriRuleSet.COORDINATION,
                severity=IssueSeverity.WARNING,
                entity_types=["all"]
            ),
            SolibriRule(
                rule_id="SOL-COORD-003",
                name="Clearance Check",
                description="Verify minimum clearances between elements",
                rule_set=SolibriRuleSet.COORDINATION,
                severity=IssueSeverity.WARNING,
                entity_types=["all"],
                parameters={'min_clearance_mm': 50}
            ),
            
            # Structural rules
            SolibriRule(
                rule_id="SOL-STRUC-001",
                name="Column Alignment",
                description="Check vertical alignment of columns",
                rule_set=SolibriRuleSet.STRUCTURAL,
                severity=IssueSeverity.ERROR,
                entity_types=["IfcColumn"],
                parameters={'max_offset_mm': 25}
            ),
            SolibriRule(
                rule_id="SOL-STRUC-002",
                name="Beam Support",
                description="Verify beams are properly supported",
                rule_set=SolibriRuleSet.STRUCTURAL,
                severity=IssueSeverity.CRITICAL,
                entity_types=["IfcBeam"]
            ),
            
            # Architectural rules
            SolibriRule(
                rule_id="SOL-ARCH-001",
                name="Door Swing Clearance",
                description="Check door swing clearance",
                rule_set=SolibriRuleSet.ARCHITECTURAL,
                severity=IssueSeverity.ERROR,
                entity_types=["IfcDoor"],
                parameters={'min_swing_clearance_mm': 900}
            ),
            SolibriRule(
                rule_id="SOL-ARCH-002",
                name="Room Height",
                description="Verify minimum room heights",
                rule_set=SolibriRuleSet.ARCHITECTURAL,
                severity=IssueSeverity.WARNING,
                entity_types=["IfcSpace"],
                parameters={'min_height_mm': 2400}
            ),
            
            # MEP rules
            SolibriRule(
                rule_id="SOL-MEP-001",
                name="Duct Slope",
                description="Check ductwork slope for drainage",
                rule_set=SolibriRuleSet.MEP,
                severity=IssueSeverity.WARNING,
                entity_types=["IfcDuctSegment"],
                parameters={'min_slope_percent': 0.5}
            ),
            SolibriRule(
                rule_id="SOL-MEP-002",
                name="Pipe Insulation",
                description="Verify pipe insulation where required",
                rule_set=SolibriRuleSet.MEP,
                severity=IssueSeverity.WARNING,
                entity_types=["IfcPipeSegment"]
            ),
            
            # Accessibility rules
            SolibriRule(
                rule_id="SOL-ACC-001",
                name="Door Width",
                description="Check minimum door width for accessibility",
                rule_set=SolibriRuleSet.ACCESSIBILITY,
                severity=IssueSeverity.ERROR,
                entity_types=["IfcDoor"],
                parameters={'min_width_mm': 810}
            ),
            SolibriRule(
                rule_id="SOL-ACC-002",
                name="Ramp Slope",
                description="Verify ramp slope for accessibility",
                rule_set=SolibriRuleSet.ACCESSIBILITY,
                severity=IssueSeverity.ERROR,
                entity_types=["IfcRamp"],
                parameters={'max_slope_ratio': 12}
            ),
            
            # Safety rules
            SolibriRule(
                rule_id="SOL-SAFE-001",
                name="Guardrail Height",
                description="Check guardrail heights",
                rule_set=SolibriRuleSet.SAFETY,
                severity=IssueSeverity.CRITICAL,
                entity_types=["IfcRailing"],
                parameters={'min_height_mm': 1070}
            ),
            SolibriRule(
                rule_id="SOL-SAFE-002",
                name="Stair Tread Depth",
                description="Verify stair tread depth",
                rule_set=SolibriRuleSet.SAFETY,
                severity=IssueSeverity.ERROR,
                entity_types=["IfcStair"],
                parameters={'min_tread_depth_mm': 280}
            ),
            
            # Information rules
            SolibriRule(
                rule_id="SOL-INFO-001",
                name="Missing Properties",
                description="Check for missing required properties",
                rule_set=SolibriRuleSet.INFORMATION,
                severity=IssueSeverity.WARNING,
                entity_types=["all"],
                parameters={'required_properties': ['Name', 'Description', 'GlobalId']}
            ),
            SolibriRule(
                rule_id="SOL-INFO-002",
                name="Classification",
                description="Verify element classification",
                rule_set=SolibriRuleSet.INFORMATION,
                severity=IssueSeverity.INFO,
                entity_types=["all"]
            ),
        ]
        
        for rule in default_rules:
            self._rules[rule.rule_id] = rule
    
    def get_rules(self, rule_set: SolibriRuleSet = None) -> List[SolibriRule]:
        """Get rules, optionally filtered by rule set"""
        rules = list(self._rules.values())
        
        if rule_set:
            rules = [r for r in rules if r.rule_set == rule_set]
        
        return [r for r in rules if r.is_active]
    
    def get_rule(self, rule_id: str) -> Optional[SolibriRule]:
        """Get rule by ID"""
        return self._rules.get(rule_id)
    
    def add_rule(self, rule: SolibriRule):
        """Add custom rule"""
        self._rules[rule.rule_id] = rule


class SolibriChecker:
    """Performs Solibri-style model checking"""
    
    def __init__(self):
        self.rule_manager = SolibriRuleManager()
        self._issues: List[SolibriIssue] = []
        self._reports: Dict[str, SolibriReport] = {}
    
    def check_model(self, model_id: str,
                    model_elements: List[Dict],
                    rule_set: SolibriRuleSet = None) -> SolibriReport:
        """Check model against Solibri rules"""
        issues = []
        
        # Get rules to check
        rules = self.rule_manager.get_rules(rule_set)
        
        for rule in rules:
            rule_issues = self._check_rule(model_elements, rule)
            issues.extend(rule_issues)
        
        # Create report
        report = SolibriReport(
            report_id=str(uuid4()),
            model_id=model_id,
            checked_at=datetime.utcnow(),
            rule_set=rule_set or SolibriRuleSet.COORDINATION,
            issues=issues,
            summary=self._generate_summary(issues)
        )
        
        self._reports[report.report_id] = report
        
        logger.info(f"Completed Solibri check: {report.report_id}")
        
        return report
    
    def _check_rule(self, elements: List[Dict],
                    rule: SolibriRule) -> List[SolibriIssue]:
        """Check elements against single rule"""
        issues = []
        
        # Filter elements by type
        if 'all' not in rule.entity_types:
            elements = [e for e in elements if e.get('type') in rule.entity_types]
        
        # Apply rule-specific checking
        if rule.rule_id == "SOL-COORD-001":
            issues.extend(self._check_clashes(elements, rule))
        elif rule.rule_id == "SOL-COORD-002":
            issues.extend(self._check_duplicates(elements, rule))
        elif rule.rule_id == "SOL-ARCH-001":
            issues.extend(self._check_door_swing(elements, rule))
        elif rule.rule_id == "SOL-INFO-001":
            issues.extend(self._check_missing_properties(elements, rule))
        # Add more rule checks as needed
        
        return issues
    
    def _check_clashes(self, elements: List[Dict],
                       rule: SolibriRule) -> List[SolibriIssue]:
        """Check for clashes between elements"""
        # This would use actual clash detection
        return []
    
    def _check_duplicates(self, elements: List[Dict],
                          rule: SolibriRule) -> List[SolibriIssue]:
        """Check for duplicate elements"""
        issues = []
        seen_guids = {}
        
        for element in elements:
            guid = element.get('attributes', {}).get('GlobalId')
            if guid:
                if guid in seen_guids:
                    issues.append(SolibriIssue(
                        issue_id=str(uuid4()),
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        element_id=element.get('id', ''),
                        element_type=element.get('type', ''),
                        component_name=element.get('attributes', {}).get('Name', 'Unknown'),
                        description=f"Duplicate element with GlobalId: {guid}"
                    ))
                else:
                    seen_guids[guid] = element.get('id')
        
        return issues
    
    def _check_door_swing(self, elements: List[Dict],
                          rule: SolibriRule) -> List[SolibriIssue]:
        """Check door swing clearance"""
        issues = []
        min_clearance = rule.parameters.get('min_swing_clearance_mm', 900)
        
        for element in elements:
            # Check if door has swing clearance property
            properties = element.get('properties', {})
            swing_clearance = properties.get('Pset_DoorCommon', {}).get('SwingClearance')
            
            if swing_clearance and swing_clearance < min_clearance:
                issues.append(SolibriIssue(
                    issue_id=str(uuid4()),
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    element_id=element.get('id', ''),
                    element_type=element.get('type', ''),
                    component_name=element.get('attributes', {}).get('Name', 'Unknown'),
                    description=f"Door swing clearance ({swing_clearance}mm) is less than required ({min_clearance}mm)"
                ))
        
        return issues
    
    def _check_missing_properties(self, elements: List[Dict],
                                   rule: SolibriRule) -> List[SolibriIssue]:
        """Check for missing required properties"""
        issues = []
        required_props = rule.parameters.get('required_properties', [])
        
        for element in elements:
            attributes = element.get('attributes', {})
            
            for prop in required_props:
                if prop not in attributes or not attributes[prop]:
                    issues.append(SolibriIssue(
                        issue_id=str(uuid4()),
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        element_id=element.get('id', ''),
                        element_type=element.get('type', ''),
                        component_name=attributes.get('Name', 'Unknown'),
                        description=f"Missing required property: {prop}"
                    ))
        
        return issues
    
    def _generate_summary(self, issues: List[SolibriIssue]) -> Dict:
        """Generate issue summary"""
        by_severity = {}
        by_rule = {}
        
        for issue in issues:
            sev = issue.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            rule = issue.rule_name
            by_rule[rule] = by_rule.get(rule, 0) + 1
        
        return {
            'total_issues': len(issues),
            'by_severity': by_severity,
            'by_rule': by_rule
        }
    
    def export_issues_to_bcf(self, report_id: str) -> bytes:
        """Export issues to BCF format"""
        report = self._reports.get(report_id)
        if not report:
            return b""
        
        # This would convert issues to BCF
        from .navisworks import bcf_exporter
        
        topic_ids = []
        for issue in report.issues:
            # Create BCF topic from issue
            pass
        
        return b""


# Global instance
solibri_checker = SolibriChecker()