"""
Recommendations Module for Heavy Reasoning Engine

Generates actionable recommendations based on:
- Variance analysis
- Compliance checks
- Risk assessment
- Best practices
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from app.reasoning.engine import (
    HeavyReasoningEngine,
    RiskLevel,
    VarianceResult,
    ComplianceCheck,
)
from app.reasoning.integrations import MergedProjectData


class ActionType(Enum):
    """Types of recommended actions."""
    GENERATE_RFI = "Generate RFI"
    GENERATE_VARIATION = "Generate Variation Order"
    GENERATE_NCR = "Generate Non-Conformance Report"
    GENERATE_CORRECTIVE_ACTION = "Generate Corrective Action"
    REVIEW_REQUIRED = "Review Required"
    APPROVAL_RECOMMENDED = "Approval Recommended"
    APPROVAL_WITH_CONDITIONS = "Approval with Conditions"
    REJECT = "Reject / Requires Redesign"
    OPTIMIZE = "Optimize"
    MONITOR = "Monitor"
    NONE = "No Action Required"


@dataclass
class Recommendation:
    """A single recommendation with actionable guidance."""
    type: str
    severity: str
    message: str
    action: str
    related_items: List[str]
    supporting_data: Dict[str, Any]
    priority_score: float = 0.0


class RecommendationEngine:
    """
    Generates actionable recommendations from reasoning results.
    
    Based on Vietnam Doc logic:
    - Variance > 15% → Generate RFI + Variation Order
    - Grade mismatch → Critical compliance risk
    - Strength shortfall → Generate NCR + Rework
    """
    
    def __init__(self, reasoning_engine: Optional[HeavyReasoningEngine] = None):
        self.reasoning = reasoning_engine or HeavyReasoningEngine()
    
    def generate_recommendations(
        self,
        merged_data: MergedProjectData,
        variances: List[VarianceResult],
        compliance_checks: List[ComplianceCheck],
    ) -> List[Recommendation]:
        """
        Generate comprehensive recommendations from analysis results.
        
        Args:
            merged_data: Merged data from all sources
            variances: List of variance results
            compliance_checks: List of compliance check results
        
        Returns:
            List of actionable recommendations
        """
        recommendations = []
        
        # Generate recommendations from variances
        for variance in variances:
            recs = self._recommendations_from_variance(variance)
            recommendations.extend(recs)
        
        # Generate recommendations from compliance checks
        for check in compliance_checks:
            rec = self._recommendation_from_compliance(check)
            if rec:
                recommendations.append(rec)
        
        # Generate recommendations from merged data conflicts
        for conflict in merged_data.conflicts:
            rec = self._recommendation_from_conflict(conflict)
            if rec:
                recommendations.append(rec)
        
        # Sort by priority score (highest first)
        recommendations.sort(key=lambda r: r.priority_score, reverse=True)
        
        return recommendations
    
    def _recommendations_from_variance(
        self,
        variance: VarianceResult
    ) -> List[Recommendation]:
        """Generate recommendations from a variance result."""
        recommendations = []
        
        variance_pct = abs(variance.variance_percent)
        
        # Critical variance (> 15%)
        if variance_pct > 0.15:
            recommendations.append(Recommendation(
                type="compliance_risk",
                severity=RiskLevel.CRITICAL.value,
                message=f"CRITICAL: {variance.symbol} variance of {variance_pct*100:.1f}% exceeds 15% threshold. High risk of non-compliance.",
                action=f"{ActionType.GENERATE_RFI.value} + {ActionType.GENERATE_VARIATION.value}",
                related_items=[variance.symbol],
                supporting_data={
                    "variance_percent": variance_pct,
                    "boq_value": variance.boq_value,
                    "drawing_value": variance.drawing_value,
                },
                priority_score=1.0,
            ))
        
        # Warning variance (5-15%)
        elif variance_pct > 0.05:
            recommendations.append(Recommendation(
                type="quantity_variance",
                severity=RiskLevel.HIGH.value,
                message=f"HIGH: {variance.symbol} variance of {variance_pct*100:.1f}% requires investigation.",
                action=f"{ActionType.REVIEW_REQUIRED.value}. Verify quantities with both parties before proceeding.",
                related_items=[variance.symbol],
                supporting_data={
                    "variance_percent": variance_pct,
                    "boq_value": variance.boq_value,
                    "drawing_value": variance.drawing_value,
                },
                priority_score=0.7,
            ))
        
        return recommendations
    
    def _recommendation_from_compliance(
        self,
        check: ComplianceCheck
    ) -> Optional[Recommendation]:
        """Generate recommendation from a compliance check."""
        if check.compliant:
            return None
        
        severity = check.severity
        
        if severity == RiskLevel.CRITICAL:
            return Recommendation(
                type="spec_mismatch",
                severity=severity.value,
                message=f"CRITICAL: {check.item} does not meet specification. Spec: {check.spec_value}, Actual: {check.actual_value}",
                action=f"{ActionType.GENERATE_RFI.value} + {ActionType.GENERATE_VARIATION.value} - Non-compliance detected",
                related_items=[check.item],
                supporting_data={
                    "spec_value": check.spec_value,
                    "actual_value": check.actual_value,
                },
                priority_score=1.0,
            )
        
        elif severity == RiskLevel.HIGH:
            return Recommendation(
                type="spec_mismatch",
                severity=severity.value,
                message=f"HIGH: {check.item} deviation from spec requires review. Spec: {check.spec_value}, Actual: {check.actual_value}",
                action=f"{ActionType.REVIEW_REQUIRED.value}. Request clarification from Engineer.",
                related_items=[check.item],
                supporting_data={
                    "spec_value": check.spec_value,
                    "actual_value": check.actual_value,
                },
                priority_score=0.8,
            )
        
        return None
    
    def _recommendation_from_conflict(
        self,
        conflict: Dict[str, Any]
    ) -> Optional[Recommendation]:
        """Generate recommendation from a data conflict."""
        conflict_type = conflict.get("type", "")
        
        if conflict_type == "quantity_variance_critical":
            return Recommendation(
                type="compliance_risk",
                severity=RiskLevel.CRITICAL.value,
                message=f"CRITICAL: Significant quantity variance detected in {conflict.get('item', 'unknown')} across source documents.",
                action=f"{ActionType.GENERATE_RFI.value} + {ActionType.REVIEW_REQUIRED.value} - Resolve discrepancy before procurement",
                related_items=[conflict.get("item", "")],
                supporting_data={
                    "variance_percent": conflict.get("variance_percent"),
                    "sources": conflict.get("sources", []),
                },
                priority_score=0.95,
            )
        
        elif conflict_type == "material_non_compliance":
            return Recommendation(
                type="compliance_risk",
                severity=RiskLevel.CRITICAL.value,
                message=f"CRITICAL: Material non-compliance for {conflict.get('material', 'unknown')}",
                action=f"{ActionType.GENERATE_NCR.value} + {ActionType.GENERATE_CORRECTIVE_ACTION.value} - Non-compliant material usage",
                related_items=[conflict.get("material", "")],
                supporting_data={"issues": conflict.get("issues", [])},
                priority_score=1.0,
            )
        
        return None
    
    def generate_approval_recommendation(
        self,
        item_data: Dict[str, Any],
        variances: List[VarianceResult],
        compliance_issues: List[ComplianceCheck]
    ) -> Dict[str, Any]:
        """
        Generate approval recommendation for an item.
        
        Returns approval status with supporting rationale.
        """
        # Count critical issues
        critical_count = sum(
            1 for v in variances
            if abs(v.variance_percent) > 0.15
        ) + sum(
            1 for c in compliance_issues
            if c.severity == RiskLevel.CRITICAL
        )
        
        # Count warning issues
        warning_count = sum(
            1 for v in variances
            if 0.05 < abs(v.variance_percent) <= 0.15
        ) + sum(
            1 for c in compliance_issues
            if c.severity == RiskLevel.HIGH
        )
        
        if critical_count > 0:
            return {
                "status": "reject",
                "recommendation": ActionType.REJECT.value,
                "rationale": f"{critical_count} critical issues identified. Item cannot be approved as-is.",
                "actions_required": [
                    ActionType.GENERATE_RFI.value,
                    ActionType.GENERATE_VARIATION.value,
                    ActionType.REVIEW_REQUIRED.value,
                ],
                "severity": RiskLevel.CRITICAL.value,
            }
        
        elif warning_count > 0:
            return {
                "status": "conditional",
                "recommendation": ActionType.APPROVAL_WITH_CONDITIONS.value,
                "rationale": f"{warning_count} warnings require resolution before approval.",
                "actions_required": [
                    ActionType.REVIEW_REQUIRED.value,
                    "Resolve identified issues",
                ],
                "severity": RiskLevel.MEDIUM.value,
            }
        
        else:
            return {
                "status": "approve",
                "recommendation": ActionType.APPROVAL_RECOMMENDED.value,
                "rationale": "No significant variances or compliance issues identified.",
                "actions_required": [ActionType.NONE.value],
                "severity": RiskLevel.LOW.value,
            }
    
    def generate_cost_recommendations(
        self,
        cost_variance: Dict[str, Any],
        merged_data: MergedProjectData
    ) -> List[Recommendation]:
        """Generate recommendations based on cost analysis."""
        recommendations = []
        
        status = cost_variance.get("status", "")
        variance_pct = cost_variance.get("variance_percent", 0)
        
        if status == "critical_overrun":
            recommendations.append(Recommendation(
                type="cost_impact",
                severity=RiskLevel.CRITICAL.value,
                message=f"CRITICAL: Cost overrun of {variance_pct*100:.1f}% exceeds acceptable threshold.",
                action=f"{ActionType.REVIEW_REQUIRED.value}. Investigate cost drivers and consider value engineering.",
                related_items=["budget"],
                supporting_data=cost_variance,
                priority_score=0.9,
            ))
        
        elif status == "warning_overrun":
            recommendations.append(Recommendation(
                type="cost_impact",
                severity=RiskLevel.HIGH.value,
                message=f"HIGH: Cost overrun of {variance_pct*100:.1f}% requires monitoring.",
                action=f"{ActionType.MONITOR.value}. Track costs closely and identify savings opportunities.",
                related_items=["budget"],
                supporting_data=cost_variance,
                priority_score=0.6,
            ))
        
        return recommendations
    
    def generate_schedule_recommendations(
        self,
        schedule_variance: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate recommendations based on schedule analysis."""
        recommendations = []
        
        status = schedule_variance.get("status", "")
        variance_days = schedule_variance.get("variance_days", 0)
        
        if status == "critical_delay":
            recommendations.append(Recommendation(
                type="schedule_impact",
                severity=RiskLevel.CRITICAL.value,
                message=f"CRITICAL: Schedule delay of {variance_days} days. Critical path impact likely.",
                action=f"{ActionType.GENERATE_VARIATION.value} (EOT) + {ActionType.REVIEW_REQUIRED.value}. Assess acceleration options.",
                related_items=[schedule_variance.get("activity", "schedule")],
                supporting_data=schedule_variance,
                priority_score=0.95,
            ))
        
        elif status == "warning_delay":
            recommendations.append(Recommendation(
                type="schedule_impact",
                severity=RiskLevel.MEDIUM.value,
                message=f"WARNING: Schedule delay of {variance_days} days detected.",
                action=f"{ActionType.MONITOR.value}. Implement recovery measures.",
                related_items=[schedule_variance.get("activity", "schedule")],
                supporting_data=schedule_variance,
                priority_score=0.5,
            ))
        
        return recommendations
    
    def generate_summary_report(
        self,
        recommendations: List[Recommendation]
    ) -> Dict[str, Any]:
        """Generate a summary report from all recommendations."""
        if not recommendations:
            return {
                "status": "all_clear",
                "message": "No issues identified. All checks passed.",
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "total_actions": 0,
            }
        
        # Count by severity
        critical = sum(1 for r in recommendations if r.severity == RiskLevel.CRITICAL.value)
        high = sum(1 for r in recommendations if r.severity == RiskLevel.HIGH.value)
        medium = sum(1 for r in recommendations if r.severity == RiskLevel.MEDIUM.value)
        low = sum(1 for r in recommendations if r.severity == RiskLevel.LOW.value or r.severity == RiskLevel.INFO.value)
        
        # Determine overall status
        if critical > 0:
            status = "critical"
            message = f"{critical} critical issues require immediate attention."
        elif high > 0:
            status = "warning"
            message = f"{high} high-priority issues require resolution."
        elif medium > 0:
            status = "attention"
            message = f"{medium} medium-priority items need review."
        else:
            status = "ok"
            message = "Minor items identified. Overall compliance acceptable."
        
        # Get required actions
        all_actions = set()
        for rec in recommendations:
            all_actions.add(rec.action)
        
        return {
            "status": status,
            "message": message,
            "critical_count": critical,
            "high_count": high,
            "medium_count": medium,
            "low_count": low,
            "total_actions": len(recommendations),
            "required_actions": list(all_actions),
            "top_priority": recommendations[0].action if recommendations else None,
        }
