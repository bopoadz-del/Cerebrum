"""
Change order management and impact analysis.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
from enum import Enum
import uuid


class ChangeOrderStatus(Enum):
    """Status of a change order."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    CLOSED = "closed"


class ChangeOrderType(Enum):
    """Type of change order."""
    ADDITION = "addition"
    DELETION = "deletion"
    MODIFICATION = "modification"
    TIME_EXTENSION = "time_extension"
    ACCELERATION = "acceleration"
    SCOPE_CHANGE = "scope_change"


@dataclass
class ChangeOrderImpact:
    """Impact analysis for a change order."""
    cost_impact: Decimal
    schedule_impact_days: int
    quality_impact: Optional[str] = None
    safety_impact: Optional[str] = None
    risk_factors: List[str] = field(default_factory=list)
    affected_work_packages: List[str] = field(default_factory=list)


@dataclass
class ChangeOrderLineItem:
    """Individual line item in a change order."""
    id: str
    description: str
    quantity: Decimal
    unit: str
    unit_cost: Decimal
    total_cost: Decimal
    cost_code: Optional[str] = None
    wbs_element: Optional[str] = None


@dataclass
class ChangeOrder:
    """Complete change order entity."""
    id: str
    project_id: str
    co_number: str
    title: str
    description: str
    type: ChangeOrderType
    status: ChangeOrderStatus
    requested_by: str
    submitted_date: datetime
    line_items: List[ChangeOrderLineItem]
    impact: ChangeOrderImpact
    attachments: List[str] = field(default_factory=list)
    approval_workflow: List[Dict[str, Any]] = field(default_factory=list)
    related_rfi_id: Optional[str] = None
    related_submittal_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ChangeOrderManager:
    """Manage change orders and their impacts."""
    
    def __init__(self):
        self.approval_thresholds = {
            "project_manager": Decimal("25000"),
            "director": Decimal("100000"),
            "executive": Decimal("500000"),
        }
    
    async def create_change_order(
        self,
        project_id: str,
        title: str,
        description: str,
        type: ChangeOrderType,
        requested_by: str,
        line_items: List[Dict[str, Any]],
        schedule_impact_days: int = 0
    ) -> ChangeOrder:
        """Create a new change order."""
        
        # Generate CO number
        co_number = await self._generate_co_number(project_id)
        
        # Create line items
        items = []
        total_cost = Decimal("0")
        
        for item_data in line_items:
            item = ChangeOrderLineItem(
                id=str(uuid.uuid4()),
                description=item_data["description"],
                quantity=Decimal(str(item_data["quantity"])),
                unit=item_data["unit"],
                unit_cost=Decimal(str(item_data["unit_cost"])),
                total_cost=Decimal(str(item_data["quantity"])) * Decimal(str(item_data["unit_cost"])),
                cost_code=item_data.get("cost_code"),
                wbs_element=item_data.get("wbs_element")
            )
            items.append(item)
            total_cost += item.total_cost
        
        # Create impact analysis
        impact = ChangeOrderImpact(
            cost_impact=total_cost,
            schedule_impact_days=schedule_impact_days,
            quality_impact=None,
            safety_impact=None,
            affected_work_packages=[item.wbs_element for item in items if item.wbs_element]
        )
        
        # Determine initial approval workflow
        workflow = self._determine_approval_workflow(total_cost)
        
        return ChangeOrder(
            id=str(uuid.uuid4()),
            project_id=project_id,
            co_number=co_number,
            title=title,
            description=description,
            type=type,
            status=ChangeOrderStatus.DRAFT,
            requested_by=requested_by,
            submitted_date=datetime.utcnow(),
            line_items=items,
            impact=impact,
            approval_workflow=workflow
        )
    
    async def _generate_co_number(self, project_id: str) -> str:
        """Generate unique change order number."""
        # In production, query database for next number
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        return f"CO-{project_id[:6]}-{timestamp}-{str(uuid.uuid4())[:4].upper()}"
    
    def _determine_approval_workflow(self, total_cost: Decimal) -> List[Dict[str, Any]]:
        """Determine approval workflow based on cost."""
        
        workflow = []
        
        if total_cost <= self.approval_thresholds["project_manager"]:
            workflow.append({
                "role": "project_manager",
                "required": True,
                "approved": False,
                "approved_at": None
            })
        elif total_cost <= self.approval_thresholds["director"]:
            workflow.extend([
                {
                    "role": "project_manager",
                    "required": True,
                    "approved": False,
                    "approved_at": None
                },
                {
                    "role": "director",
                    "required": True,
                    "approved": False,
                    "approved_at": None
                }
            ])
        else:
            workflow.extend([
                {
                    "role": "project_manager",
                    "required": True,
                    "approved": False,
                    "approved_at": None
                },
                {
                    "role": "director",
                    "required": True,
                    "approved": False,
                    "approved_at": None
                },
                {
                    "role": "executive",
                    "required": True,
                    "approved": False,
                    "approved_at": None
                }
            ])
        
        return workflow
    
    async def analyze_cumulative_impact(
        self,
        project_id: str,
        change_orders: List[ChangeOrder]
    ) -> Dict[str, Any]:
        """Analyze cumulative impact of all change orders on a project."""
        
        approved_cos = [co for co in change_orders if co.status == ChangeOrderStatus.APPROVED]
        pending_cos = [co for co in change_orders if co.status in 
                      [ChangeOrderStatus.SUBMITTED, ChangeOrderStatus.UNDER_REVIEW]]
        
        # Calculate totals
        approved_cost = sum(co.impact.cost_impact for co in approved_cos)
        pending_cost = sum(co.impact.cost_impact for co in pending_cos)
        approved_schedule = sum(co.impact.schedule_impact_days for co in approved_cos)
        pending_schedule = sum(co.impact.schedule_impact_days for co in pending_cos)
        
        # Identify trends
        by_type: Dict[str, Decimal] = {}
        for co in change_orders:
            type_key = co.type.value
            by_type[type_key] = by_type.get(type_key, Decimal("0")) + co.impact.cost_impact
        
        # Calculate contingency impact
        original_contingency = Decimal("500000")  # Placeholder
        contingency_used_pct = (approved_cost / original_contingency * 100) if original_contingency > 0 else 0
        
        return {
            "project_id": project_id,
            "summary": {
                "total_change_orders": len(change_orders),
                "approved_count": len(approved_cos),
                "pending_count": len(pending_cos),
                "approved_cost_impact": approved_cost,
                "pending_cost_impact": pending_cost,
                "total_potential_impact": approved_cost + pending_cost,
                "approved_schedule_impact_days": approved_schedule,
                "pending_schedule_impact_days": pending_schedule
            },
            "by_type": by_type,
            "contingency_analysis": {
                "original_contingency": original_contingency,
                "used": approved_cost,
                "remaining": original_contingency - approved_cost,
                "used_percentage": contingency_used_pct,
                "at_risk": contingency_used_pct > 75
            },
            "recommendations": self._generate_recommendations(
                approved_cos, pending_cos, contingency_used_pct
            )
        }
    
    def _generate_recommendations(
        self,
        approved: List[ChangeOrder],
        pending: List[ChangeOrder],
        contingency_used: float
    ) -> List[str]:
        """Generate recommendations based on change order analysis."""
        
        recommendations = []
        
        if contingency_used > 75:
            recommendations.append(
                "URGENT: Contingency nearly exhausted. Consider change order freeze or contingency increase."
            )
        elif contingency_used > 50:
            recommendations.append(
                "WARNING: Contingency usage above 50%. Implement stricter change control procedures."
            )
        
        if len(pending) > 5:
            recommendations.append(
                f"High volume of pending change orders ({len(pending)}). Expedite review process."
            )
        
        # Check for patterns
        addition_cos = [co for co in approved if co.type == ChangeOrderType.ADDITION]
        if len(addition_cos) > len(approved) * 0.6:
            recommendations.append(
                "Majority of changes are additions. Review initial scope definition process."
            )
        
        return recommendations
    
    async def calculate_impact_on_schedule(
        self,
        change_order: ChangeOrder,
        current_schedule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate detailed schedule impact of a change order."""
        
        # Placeholder for CPM schedule analysis
        # In production, integrate with scheduling system
        
        return {
            "change_order_id": change_order.id,
            "direct_impact_days": change_order.impact.schedule_impact_days,
            "critical_path_impact": change_order.impact.schedule_impact_days,
            "float_consumption": 0,
            "affected_activities": change_order.impact.affected_work_packages,
            "recommended_sequence_changes": [],
            "resource_reallocation_needed": len(change_order.impact.affected_work_packages) > 3
        }
