"""
Design Alternatives - Branching for Design Options
Version control for design alternatives
"""
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class AlternativeStatus(Enum):
    """Design alternative status"""
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    MERGED = "merged"
    ARCHIVED = "archived"


class AlternativeType(Enum):
    """Type of design alternative"""
    SCHEME = "scheme"  # Major design scheme
    OPTION = "option"  # Design option within scheme
    VARIANT = "variant"  # Minor variation
    WHAT_IF = "what_if"  # Exploration


@dataclass
class DesignAlternative:
    """Design alternative"""
    alternative_id: str
    parent_id: Optional[str]  # Parent alternative or base design
    project_id: str
    name: str
    description: str
    alternative_type: AlternativeType
    status: AlternativeStatus
    created_by: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    model_references: Dict[str, str] = field(default_factory=dict)  # discipline -> model_id
    changed_elements: List[str] = field(default_factory=list)
    cost_estimate: Optional[float] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    review_comments: List[Dict] = field(default_factory=list)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlternativeComparison:
    """Comparison between alternatives"""
    comparison_id: str
    base_alternative_id: str
    compare_alternative_id: str
    compared_at: datetime = field(default_factory=datetime.utcnow)
    compared_by: str = ""
    differences: List[Dict] = field(default_factory=list)
    metrics_comparison: Dict[str, Dict] = field(default_factory=dict)
    cost_comparison: Dict[str, float] = field(default_factory=dict)
    recommendation: str = ""


class DesignBranchManager:
    """Manages design branches/alternatives"""
    
    def __init__(self):
        self._alternatives: Dict[str, DesignAlternative] = {}
        self._base_designs: Dict[str, str] = {}  # project_id -> alternative_id
        self._comparisons: Dict[str, AlternativeComparison] = {}
        self._merge_history: List[Dict] = []
    
    def create_base_design(self, project_id: str, name: str,
                           created_by: str) -> DesignAlternative:
        """Create base design for project"""
        alternative = DesignAlternative(
            alternative_id=str(uuid4()),
            parent_id=None,
            project_id=project_id,
            name=name,
            description="Base design",
            alternative_type=AlternativeType.SCHEME,
            status=AlternativeStatus.APPROVED,
            created_by=created_by
        )
        
        self._alternatives[alternative.alternative_id] = alternative
        self._base_designs[project_id] = alternative.alternative_id
        
        logger.info(f"Created base design: {alternative.alternative_id}")
        
        return alternative
    
    def create_alternative(self, parent_id: str, name: str,
                           description: str,
                           alternative_type: AlternativeType,
                           created_by: str) -> DesignAlternative:
        """Create design alternative from parent"""
        parent = self._alternatives.get(parent_id)
        if not parent:
            raise ValueError(f"Parent alternative not found: {parent_id}")
        
        alternative = DesignAlternative(
            alternative_id=str(uuid4()),
            parent_id=parent_id,
            project_id=parent.project_id,
            name=name,
            description=description,
            alternative_type=alternative_type,
            status=AlternativeStatus.DRAFT,
            created_by=created_by,
            model_references=parent.model_references.copy()
        )
        
        self._alternatives[alternative.alternative_id] = alternative
        
        logger.info(f"Created alternative: {alternative.alternative_id} from {parent_id}")
        
        return alternative
    
    def update_model_reference(self, alternative_id: str,
                               discipline: str,
                               model_id: str) -> bool:
        """Update model reference for alternative"""
        alternative = self._alternatives.get(alternative_id)
        if not alternative:
            return False
        
        alternative.model_references[discipline] = model_id
        alternative.updated_at = datetime.utcnow()
        
        # Track changed elements
        if model_id not in alternative.changed_elements:
            alternative.changed_elements.append(model_id)
        
        return True
    
    def submit_for_review(self, alternative_id: str) -> bool:
        """Submit alternative for review"""
        alternative = self._alternatives.get(alternative_id)
        if not alternative:
            return False
        
        if alternative.status != AlternativeStatus.DRAFT:
            return False
        
        alternative.status = AlternativeStatus.UNDER_REVIEW
        alternative.updated_at = datetime.utcnow()
        
        logger.info(f"Alternative submitted for review: {alternative_id}")
        
        return True
    
    def approve_alternative(self, alternative_id: str,
                            approved_by: str,
                            comments: str = "") -> bool:
        """Approve design alternative"""
        alternative = self._alternatives.get(alternative_id)
        if not alternative:
            return False
        
        alternative.status = AlternativeStatus.APPROVED
        alternative.approved_by = approved_by
        alternative.approved_at = datetime.utcnow()
        alternative.updated_at = datetime.utcnow()
        
        if comments:
            alternative.review_comments.append({
                'timestamp': datetime.utcnow().isoformat(),
                'reviewer': approved_by,
                'comment': comments,
                'decision': 'approved'
            })
        
        logger.info(f"Alternative approved: {alternative_id} by {approved_by}")
        
        return True
    
    def reject_alternative(self, alternative_id: str,
                           rejected_by: str,
                           reason: str) -> bool:
        """Reject design alternative"""
        alternative = self._alternatives.get(alternative_id)
        if not alternative:
            return False
        
        alternative.status = AlternativeStatus.REJECTED
        alternative.updated_at = datetime.utcnow()
        
        alternative.review_comments.append({
            'timestamp': datetime.utcnow().isoformat(),
            'reviewer': rejected_by,
            'comment': reason,
            'decision': 'rejected'
        })
        
        logger.info(f"Alternative rejected: {alternative_id} by {rejected_by}")
        
        return True
    
    def merge_alternative(self, alternative_id: str,
                          merged_by: str) -> Dict:
        """Merge alternative into base design"""
        alternative = self._alternatives.get(alternative_id)
        if not alternative:
            raise ValueError(f"Alternative not found: {alternative_id}")
        
        if alternative.status != AlternativeStatus.APPROVED:
            raise ValueError("Alternative must be approved before merging")
        
        # Get base design
        base_id = self._base_designs.get(alternative.project_id)
        base = self._alternatives.get(base_id)
        
        if not base:
            raise ValueError("Base design not found")
        
        # Merge model references
        for discipline, model_id in alternative.model_references.items():
            if discipline in alternative.changed_elements or \
               model_id != base.model_references.get(discipline):
                base.model_references[discipline] = model_id
        
        # Update alternative status
        alternative.status = AlternativeStatus.MERGED
        alternative.updated_at = datetime.utcnow()
        
        # Log merge
        merge_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'alternative_id': alternative_id,
            'base_id': base_id,
            'merged_by': merged_by,
            'changed_disciplines': list(alternative.changed_elements)
        }
        self._merge_history.append(merge_record)
        
        logger.info(f"Alternative merged: {alternative_id} into {base_id}")
        
        return merge_record
    
    def compare_alternatives(self, base_id: str,
                             compare_id: str,
                             compared_by: str = "") -> AlternativeComparison:
        """Compare two alternatives"""
        base = self._alternatives.get(base_id)
        compare = self._alternatives.get(compare_id)
        
        if not base or not compare:
            raise ValueError("One or both alternatives not found")
        
        # Find differences
        differences = []
        
        # Compare model references
        all_disciplines = set(base.model_references.keys()) | set(compare.model_references.keys())
        
        for discipline in all_disciplines:
            base_model = base.model_references.get(discipline)
            compare_model = compare.model_references.get(discipline)
            
            if base_model != compare_model:
                differences.append({
                    'type': 'model_change',
                    'discipline': discipline,
                    'base_value': base_model,
                    'compare_value': compare_model
                })
        
        # Compare cost estimates
        cost_comparison = {}
        if base.cost_estimate is not None and compare.cost_estimate is not None:
            cost_comparison = {
                'base_cost': base.cost_estimate,
                'compare_cost': compare.cost_estimate,
                'difference': compare.cost_estimate - base.cost_estimate,
                'percent_change': ((compare.cost_estimate - base.cost_estimate) / base.cost_estimate * 100) \
                                 if base.cost_estimate != 0 else 0
            }
        
        # Compare metrics
        metrics_comparison = {}
        all_metrics = set(base.performance_metrics.keys()) | set(compare.performance_metrics.keys())
        
        for metric in all_metrics:
            base_val = base.performance_metrics.get(metric)
            compare_val = compare.performance_metrics.get(metric)
            
            if base_val != compare_val:
                metrics_comparison[metric] = {
                    'base': base_val,
                    'compare': compare_val,
                    'difference': compare_val - base_val if isinstance(compare_val, (int, float)) else None
                }
        
        comparison = AlternativeComparison(
            comparison_id=str(uuid4()),
            base_alternative_id=base_id,
            compare_alternative_id=compare_id,
            compared_by=compared_by,
            differences=differences,
            metrics_comparison=metrics_comparison,
            cost_comparison=cost_comparison
        )
        
        self._comparisons[comparison.comparison_id] = comparison
        
        return comparison
    
    def get_alternative_tree(self, project_id: str) -> Dict:
        """Get alternative tree structure for project"""
        alternatives = [
            alt for alt in self._alternatives.values()
            if alt.project_id == project_id
        ]
        
        # Build tree
        tree = {
            'project_id': project_id,
            'base_design': None,
            'alternatives': []
        }
        
        for alt in alternatives:
            node = {
                'alternative_id': alt.alternative_id,
                'name': alt.name,
                'type': alt.alternative_type.value,
                'status': alt.status.value,
                'parent_id': alt.parent_id,
                'created_at': alt.created_at.isoformat(),
                'children': []
            }
            
            if alt.parent_id is None:
                tree['base_design'] = node
            else:
                tree['alternatives'].append(node)
        
        # Link children
        alt_map = {a['alternative_id']: a for a in tree['alternatives']}
        for alt in tree['alternatives']:
            if alt['parent_id'] in alt_map:
                alt_map[alt['parent_id']]['children'].append(alt)
        
        return tree
    
    def get_alternative(self, alternative_id: str) -> Optional[DesignAlternative]:
        """Get alternative by ID"""
        return self._alternatives.get(alternative_id)


class AlternativeVisualization:
    """Visualizes design alternatives"""
    
    def generate_comparison_view(self, comparison: AlternativeComparison) -> Dict:
        """Generate data for comparison view"""
        return {
            'comparison_id': comparison.comparison_id,
            'base_alternative': comparison.base_alternative_id,
            'compare_alternative': comparison.compare_alternative_id,
            'view_config': {
                'split_screen': True,
                'highlight_differences': True,
                'show_unchanged': False
            },
            'differences': comparison.differences,
            'cost_impact': comparison.cost_comparison,
            'performance_impact': comparison.metrics_comparison
        }
    
    def generate_alternative_gallery(self, project_id: str,
                                     branch_manager: DesignBranchManager) -> Dict:
        """Generate gallery view of all alternatives"""
        alternatives = [
            alt for alt in branch_manager._alternatives.values()
            if alt.project_id == project_id
        ]
        
        return {
            'project_id': project_id,
            'alternatives': [
                {
                    'alternative_id': alt.alternative_id,
                    'name': alt.name,
                    'description': alt.description,
                    'type': alt.alternative_type.value,
                    'status': alt.status.value,
                    'thumbnail': alt.metadata.get('thumbnail_url'),
                    'cost_estimate': alt.cost_estimate,
                    'created_at': alt.created_at.isoformat()
                }
                for alt in sorted(alternatives, key=lambda a: a.created_at, reverse=True)
            ]
        }


# Global instances
branch_manager = DesignBranchManager()
alt_visualization = AlternativeVisualization()