"""
BIM Execution Plan (BEP) Compliance
BEP management and compliance checking
"""
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class BEPLevel(Enum):
    """BEP levels per ISO 19650"""
    PRE_CONTRACT = "pre_contract"  # BEP before contract award
    POST_CONTRACT = "post_contract"  # BEP after contract award
    MASTER = "master"  # Master BEP for organization


class ComplianceStatus(Enum):
    """Compliance check status"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class BEPRequirement:
    """BEP requirement definition"""
    requirement_id: str
    category: str
    description: str
    reference_standard: str  # e.g., "ISO 19650-2:2018"
    clause_reference: str
    mandatory: bool
    verification_method: str
    acceptance_criteria: str


@dataclass
class BEPDeliverable:
    """BEP deliverable specification"""
    deliverable_id: str
    name: str
    description: str
    discipline: str
    format: str
    lod: str  # Level of Development
    loi: str  # Level of Information
    responsible_party: str
    delivery_milestone: str
    approval_required: bool = True


@dataclass
class BIMExecutionPlan:
    """BIM Execution Plan"""
    bep_id: str
    project_id: str
    name: str
    bep_level: BEPLevel
    version: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    project_information: Dict[str, Any] = field(default_factory=dict)
    project_team: List[Dict] = field(default_factory=list)
    information_requirements: List[Dict] = field(default_factory=list)
    deliverables: List[BEPDeliverable] = field(default_factory=list)
    standards_and_methods: Dict[str, Any] = field(default_factory=dict)
    collaboration_processes: Dict[str, Any] = field(default_factory=dict)
    compliance_requirements: List[BEPRequirement] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceCheck:
    """BEP compliance check result"""
    check_id: str
    bep_id: str
    requirement_id: str
    status: ComplianceStatus
    checked_at: datetime = field(default_factory=datetime.utcnow)
    checked_by: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    findings: List[str] = field(default_factory=list)
    corrective_actions: List[str] = field(default_factory=list)


class BEPManager:
    """Manages BIM Execution Plans"""
    
    def __init__(self):
        self._beps: Dict[str, BIMExecutionPlan] = {}
        self._templates: Dict[str, Dict] = {}
        self._compliance_checks: Dict[str, List[ComplianceCheck]] = {}
    
    def create_bep(self, project_id: str, name: str,
                   bep_level: BEPLevel,
                   created_by: str) -> BIMExecutionPlan:
        """Create new BIM Execution Plan"""
        bep = BIMExecutionPlan(
            bep_id=str(uuid4()),
            project_id=project_id,
            name=name,
            bep_level=bep_level,
            version="1.0",
            created_by=created_by
        )
        
        self._beps[bep.bep_id] = bep
        self._compliance_checks[bep.bep_id] = []
        
        logger.info(f"Created BEP: {bep.bep_id}")
        
        return bep
    
    def load_template(self, template_name: str, 
                      bep_id: str) -> bool:
        """Load template into BEP"""
        bep = self._beps.get(bep_id)
        template = self._templates.get(template_name)
        
        if not bep or not template:
            return False
        
        # Apply template
        bep.information_requirements = template.get('information_requirements', [])
        bep.deliverables = [
            BEPDeliverable(**d) for d in template.get('deliverables', [])
        ]
        bep.standards_and_methods = template.get('standards_and_methods', {})
        bep.collaboration_processes = template.get('collaboration_processes', {})
        
        bep.updated_at = datetime.utcnow()
        
        return True
    
    def add_deliverable(self, bep_id: str,
                        deliverable: BEPDeliverable) -> bool:
        """Add deliverable to BEP"""
        bep = self._beps.get(bep_id)
        if not bep:
            return False
        
        bep.deliverables.append(deliverable)
        bep.updated_at = datetime.utcnow()
        
        return True
    
    def approve_bep(self, bep_id: str,
                    approved_by: str) -> bool:
        """Approve BEP"""
        bep = self._beps.get(bep_id)
        if not bep:
            return False
        
        bep.approved_by = approved_by
        bep.approved_at = datetime.utcnow()
        bep.updated_at = datetime.utcnow()
        
        logger.info(f"BEP approved: {bep_id} by {approved_by}")
        
        return True
    
    def get_bep(self, bep_id: str) -> Optional[BIMExecutionPlan]:
        """Get BEP by ID"""
        return self._beps.get(bep_id)
    
    def get_project_bep(self, project_id: str) -> Optional[BIMExecutionPlan]:
        """Get BEP for project"""
        for bep in self._beps.values():
            if bep.project_id == project_id:
                return bep
        return None


class BEPComplianceChecker:
    """Checks BEP compliance"""
    
    def __init__(self):
        self._requirements: Dict[str, BEPRequirement] = {}
        self._initialize_iso19650_requirements()
    
    def _initialize_iso19650_requirements(self):
        """Initialize ISO 19650 requirements"""
        iso_requirements = [
            BEPRequirement(
                requirement_id="ISO19650-2-5.1.1",
                category="project_info",
                description="Project information shall be documented",
                reference_standard="ISO 19650-2:2018",
                clause_reference="5.1.1",
                mandatory=True,
                verification_method="document_review",
                acceptance_criteria="Project name, location, description provided"
            ),
            BEPRequirement(
                requirement_id="ISO19650-2-5.1.2",
                category="project_team",
                description="Project team roles and responsibilities defined",
                reference_standard="ISO 19650-2:2018",
                clause_reference="5.1.2",
                mandatory=True,
                verification_method="document_review",
                acceptance_criteria="All key roles identified with responsibilities"
            ),
            BEPRequirement(
                requirement_id="ISO19650-2-5.2.1",
                category="information_requirements",
                description="Exchange Information Requirements (EIR) addressed",
                reference_standard="ISO 19650-2:2018",
                clause_reference="5.2.1",
                mandatory=True,
                verification_method="cross_reference",
                acceptance_criteria="All EIR items have corresponding BEP response"
            ),
            BEPRequirement(
                requirement_id="ISO19650-2-5.3.1",
                category="deliverables",
                description="Deliverables schedule defined",
                reference_standard="ISO 19650-2:2018",
                clause_reference="5.3.1",
                mandatory=True,
                verification_method="document_review",
                acceptance_criteria="All deliverables with dates and responsible parties"
            ),
            BEPRequirement(
                requirement_id="ISO19650-2-5.4.1",
                category="standards",
                description="Standards and methods documented",
                reference_standard="ISO 19650-2:2018",
                clause_reference="5.4.1",
                mandatory=True,
                verification_method="document_review",
                acceptance_criteria="All applicable standards listed"
            ),
            BEPRequirement(
                requirement_id="ISO19650-2-5.5.1",
                category="collaboration",
                description="Collaboration processes defined",
                reference_standard="ISO 19650-2:2018",
                clause_reference="5.5.1",
                mandatory=True,
                verification_method="document_review",
                acceptance_criteria="CDE processes and file naming defined"
            ),
        ]
        
        for req in iso_requirements:
            self._requirements[req.requirement_id] = req
    
    def check_compliance(self, bep: BIMExecutionPlan) -> List[ComplianceCheck]:
        """Check BEP compliance against requirements"""
        checks = []
        
        for req in self._requirements.values():
            check = self._check_requirement(bep, req)
            checks.append(check)
        
        # Store checks
        self._store_checks(bep.bep_id, checks)
        
        return checks
    
    def _check_requirement(self, bep: BIMExecutionPlan,
                           requirement: BEPRequirement) -> ComplianceCheck:
        """Check single requirement"""
        status = ComplianceStatus.COMPLIANT
        findings = []
        evidence = {}
        
        if requirement.category == "project_info":
            if not bep.project_information.get('name'):
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("Project name not specified")
            else:
                evidence['project_name'] = bep.project_information.get('name')
        
        elif requirement.category == "project_team":
            if not bep.project_team:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("Project team not defined")
            else:
                evidence['team_count'] = len(bep.project_team)
        
        elif requirement.category == "information_requirements":
            if not bep.information_requirements:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("Information requirements not documented")
            else:
                evidence['requirements_count'] = len(bep.information_requirements)
        
        elif requirement.category == "deliverables":
            if not bep.deliverables:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("Deliverables not defined")
            else:
                evidence['deliverables_count'] = len(bep.deliverables)
        
        elif requirement.category == "standards":
            if not bep.standards_and_methods:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("Standards and methods not documented")
            else:
                evidence['standards_defined'] = True
        
        elif requirement.category == "collaboration":
            if not bep.collaboration_processes:
                status = ComplianceStatus.NON_COMPLIANT
                findings.append("Collaboration processes not defined")
            else:
                evidence['processes_defined'] = True
        
        return ComplianceCheck(
            check_id=str(uuid4()),
            bep_id=bep.bep_id,
            requirement_id=requirement.requirement_id,
            status=status,
            evidence=evidence,
            findings=findings
        )
    
    def _store_checks(self, bep_id: str, checks: List[ComplianceCheck]):
        """Store compliance checks"""
        # This would store in database
        pass
    
    def generate_compliance_report(self, checks: List[ComplianceCheck]) -> Dict:
        """Generate compliance report"""
        total = len(checks)
        compliant = len([c for c in checks if c.status == ComplianceStatus.COMPLIANT])
        non_compliant = len([c for c in checks if c.status == ComplianceStatus.NON_COMPLIANT])
        partial = len([c for c in checks if c.status == ComplianceStatus.PARTIAL])
        
        compliance_percent = (compliant / total * 100) if total > 0 else 0
        
        return {
            'summary': {
                'total_requirements': total,
                'compliant': compliant,
                'non_compliant': non_compliant,
                'partial': partial,
                'compliance_percent': compliance_percent
            },
            'non_compliant_items': [
                {
                    'requirement_id': c.requirement_id,
                    'findings': c.findings,
                    'corrective_actions': c.corrective_actions
                }
                for c in checks if c.status == ComplianceStatus.NON_COMPLIANT
            ],
            'grade': self._calculate_grade(compliance_percent)
        }
    
    def _calculate_grade(self, percent: float) -> str:
        """Calculate compliance grade"""
        if percent >= 95:
            return 'A'
        elif percent >= 85:
            return 'B'
        elif percent >= 75:
            return 'C'
        elif percent >= 65:
            return 'D'
        else:
            return 'F'


class BEPDeliverableTracker:
    """Tracks BEP deliverables"""
    
    def __init__(self):
        self._deliverable_status: Dict[str, Dict] = {}
    
    def register_deliverable(self, deliverable_id: str,
                             bep_id: str) -> Dict:
        """Register deliverable for tracking"""
        self._deliverable_status[deliverable_id] = {
            'bep_id': bep_id,
            'status': 'planned',
            'planned_date': None,
            'actual_date': None,
            'approved': False,
            'history': []
        }
        
        return self._deliverable_status[deliverable_id]
    
    def update_status(self, deliverable_id: str,
                      status: str,
                      notes: str = "") -> bool:
        """Update deliverable status"""
        if deliverable_id not in self._deliverable_status:
            return False
        
        entry = self._deliverable_status[deliverable_id]
        
        entry['history'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'from_status': entry['status'],
            'to_status': status,
            'notes': notes
        })
        
        entry['status'] = status
        
        if status == 'delivered':
            entry['actual_date'] = datetime.utcnow().isoformat()
        
        return True
    
    def approve_deliverable(self, deliverable_id: str,
                            approved_by: str) -> bool:
        """Approve deliverable"""
        if deliverable_id not in self._deliverable_status:
            return False
        
        entry = self._deliverable_status[deliverable_id]
        entry['approved'] = True
        entry['approved_by'] = approved_by
        entry['approved_at'] = datetime.utcnow().isoformat()
        
        return True
    
    def get_deliverable_status(self, bep_id: str) -> Dict:
        """Get status of all deliverables for BEP"""
        deliverables = {
            k: v for k, v in self._deliverable_status.items()
            if v['bep_id'] == bep_id
        }
        
        total = len(deliverables)
        delivered = len([d for d in deliverables.values() if d['status'] == 'delivered'])
        approved = len([d for d in deliverables.values() if d['approved']])
        
        return {
            'total': total,
            'delivered': delivered,
            'approved': approved,
            'completion_percent': (delivered / total * 100) if total > 0 else 0,
            'approval_percent': (approved / total * 100) if total > 0 else 0,
            'deliverables': deliverables
        }


# Global instances
bep_manager = BEPManager()
compliance_checker = BEPComplianceChecker()
deliverable_tracker = BEPDeliverableTracker()