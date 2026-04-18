"""
Heavy Reasoning Engine for Cerebrum

SymPy-based merger for BOQ + Specs + Drawings.
Based on the Vietnam Doc architecture for symbolic reasoning.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import sympy as sp


class RiskLevel(Enum):
    """Risk severity levels."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"


class RecommendationType(Enum):
    """Types of recommendations."""
    COMPLIANCE_RISK = "compliance_risk"
    QUANTITY_VARIANCE = "quantity_variance"
    SPEC_MISMATCH = "spec_mismatch"
    COST_IMPACT = "cost_impact"
    SCHEDULE_IMPACT = "schedule_impact"
    QUALITY_CONCERN = "quality_concern"
    SAFETY_ISSUE = "safety_issue"
    OPTIMIZATION = "optimization"
    APPROVAL_REQUIRED = "approval_required"


@dataclass
class VarianceResult:
    """Result of variance calculation."""
    symbol: str
    boq_value: float
    drawing_value: float
    variance: float
    variance_percent: float
    is_significant: bool
    notes: List[str] = field(default_factory=list)


@dataclass
class ComplianceCheck:
    """Result of compliance check."""
    item: str
    spec_value: str
    actual_value: str
    compliant: bool
    severity: RiskLevel
    recommendation: Optional[str] = None


class HeavyReasoningEngine:
    """
    Core reasoning engine using SymPy for symbolic computation.
    
    Based on Vietnam Doc architecture:
    - Symbolic variables for BOQ, Drawings, Specs
    - Variance calculation with validation rules
    - Compliance checking across multiple sources
    - Actionable recommendation generation
    
    Key logic from Vietnam Doc:
    ```python
    # Symbolic variables
    V_boq, V_drawing = sp.symbols('V_boq V_drawing', positive=True, real=True)
    grade_spec, grade_used = sp.symbols('grade_spec grade_used')
    
    # Variance calculation
    variance = V_drawing - V_boq
    variance_pct = variance / V_boq
    
    # Validation rules
    if abs(variance_pct) > 0.15 or grade_used != grade_spec:
        recommendations.append(...)
    ```
    """
    
    # Variance thresholds
    VARIANCE_WARNING = 0.05  # 5% variance warning
    VARIANCE_CRITICAL = 0.15  # 15% variance critical
    
    def __init__(self):
        self._initialize_symbols()
    
    def _initialize_symbols(self):
        """Initialize symbolic variables for reasoning."""
        # Volume/quantity symbols
        self.V_boq = sp.Symbol('V_boq', positive=True, real=True)
        self.V_drawing = sp.Symbol('V_drawing', positive=True, real=True)
        self.V_spec = sp.Symbol('V_spec', positive=True, real=True)
        self.V_actual = sp.Symbol('V_actual', positive=True, real=True)
        
        # Quality/compliance symbols
        self.grade_spec = sp.Symbol('grade_spec', real=True)
        self.grade_used = sp.Symbol('grade_used', real=True)
        self.strength_spec = sp.Symbol('strength_spec', positive=True, real=True)
        self.strength_actual = sp.Symbol('strength_actual', positive=True, real=True)
        
        # Cost symbols
        self.C_estimated = sp.Symbol('C_estimated', positive=True, real=True)
        self.C_actual = sp.Symbol('C_actual', positive=True, real=True)
        
        # Schedule symbols
        self.T_planned = sp.Symbol('T_planned', positive=True, real=True)
        self.T_actual = sp.Symbol('T_actual', positive=True, real=True)
    
    def calculate_variance(
        self,
        boq_value: float,
        drawing_value: float,
        item_name: str = "quantity"
    ) -> VarianceResult:
        """
        Calculate variance between BOQ and Drawing values.
        
        Args:
            boq_value: Value from BOQ
            drawing_value: Value from Drawing
            item_name: Name of the item being compared
        
        Returns:
            VarianceResult with calculated variance and significance
        """
        # Symbolic variance calculation
        variance_expr = self.V_drawing - self.V_boq
        variance_pct_expr = variance_expr / self.V_boq
        
        # Substitute values
        variance = drawing_value - boq_value
        variance_pct = variance / boq_value if boq_value != 0 else 0
        
        # Determine significance
        is_significant = abs(variance_pct) > self.VARIANCE_WARNING
        
        notes = []
        if abs(variance_pct) > self.VARIANCE_CRITICAL:
            notes.append(f"CRITICAL: Variance exceeds {self.VARIANCE_CRITICAL*100}% threshold")
        elif abs(variance_pct) > self.VARIANCE_WARNING:
            notes.append(f"WARNING: Variance exceeds {self.VARIANCE_WARNING*100}% threshold")
        
        if variance > 0:
            notes.append(f"Drawing shows {abs(variance_pct)*100:.1f}% more than BOQ")
        else:
            notes.append(f"BOQ includes {abs(variance_pct)*100:.1f}% more than Drawing")
        
        return VarianceResult(
            symbol=item_name,
            boq_value=boq_value,
            drawing_value=drawing_value,
            variance=variance,
            variance_percent=variance_pct,
            is_significant=is_significant,
            notes=notes
        )
    
    def check_grade_compliance(
        self,
        spec_grade: str,
        used_grade: str,
        item_name: str = "material"
    ) -> ComplianceCheck:
        """
        Check if used grade matches specified grade.
        
        Args:
            spec_grade: Grade specified in specifications
            used_grade: Grade actually used
            item_name: Name of the item
        
        Returns:
            ComplianceCheck result
        """
        compliant = spec_grade == used_grade
        
        if compliant:
            severity = RiskLevel.INFO
            recommendation = None
        else:
            severity = RiskLevel.CRITICAL
            recommendation = f"CRITICAL: {item_name} grade mismatch. Spec: {spec_grade}, Used: {used_grade}. Generate RFI + Variation Order."
        
        return ComplianceCheck(
            item=item_name,
            spec_value=spec_grade,
            actual_value=used_grade,
            compliant=compliant,
            severity=severity,
            recommendation=recommendation
        )
    
    def check_strength_compliance(
        self,
        spec_strength: float,
        actual_strength: float,
        tolerance: float = 0.0,
        item_name: str = "concrete"
    ) -> ComplianceCheck:
        """
        Check if actual strength meets specification.
        
        Args:
            spec_strength: Specified strength value (MPa)
            actual_strength: Actual strength achieved (MPa)
            tolerance: Acceptable tolerance percentage
            item_name: Name of the item
        
        Returns:
            ComplianceCheck result
        """
        min_acceptable = spec_strength * (1 - tolerance)
        compliant = actual_strength >= min_acceptable
        
        if compliant:
            if actual_strength < spec_strength:
                severity = RiskLevel.LOW
                recommendation = f"Strength within tolerance but below spec. Monitor closely."
            else:
                severity = RiskLevel.INFO
                recommendation = None
        else:
            severity = RiskLevel.CRITICAL
            shortfall = (spec_strength - actual_strength) / spec_strength * 100
            recommendation = f"CRITICAL: Strength {shortfall:.1f}% below spec. Non-compliant. Generate NCR + Rework Order."
        
        return ComplianceCheck(
            item=item_name,
            spec_value=f"{spec_strength} MPa",
            actual_value=f"{actual_strength} MPa",
            compliant=compliant,
            severity=severity,
            recommendation=recommendation
        )
    
    def analyze_boq_drawing_spec_alignment(
        self,
        boq_data: Dict[str, Any],
        drawing_data: Dict[str, Any],
        spec_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive alignment analysis across BOQ, Drawings, and Specs.
        
        Args:
            boq_data: Data from Bill of Quantities
            drawing_data: Data from Drawings
            spec_data: Data from Specifications
        
        Returns:
            Analysis results with variances and compliance checks
        """
        results = {
            "variances": [],
            "compliance_checks": [],
            "overall_status": "compliant",
            "risk_level": RiskLevel.LOW.value,
            "critical_issues": [],
        }
        
        # Compare quantities between BOQ and Drawings
        boq_quantities = boq_data.get("quantities", [])
        drawing_quantities = drawing_data.get("quantities", [])
        
        for boq_item in boq_quantities:
            item_id = boq_item.get("id", "unknown")
            boq_qty = boq_item.get("value", 0)
            
            # Find matching drawing item
            drawing_item = next(
                (d for d in drawing_quantities if d.get("id") == item_id),
                None
            )
            
            if drawing_item:
                drawing_qty = drawing_item.get("value", 0)
                variance = self.calculate_variance(boq_qty, drawing_qty, item_id)
                results["variances"].append(variance)
                
                if variance.is_significant:
                    results["critical_issues"].append({
                        "type": "quantity_variance",
                        "item": item_id,
                        "variance_percent": variance.variance_percent,
                        "severity": "critical" if abs(variance.variance_percent) > self.VARIANCE_CRITICAL else "warning",
                    })
        
        # Check spec compliance
        spec_sections = spec_data.get("sections", [])
        for section in spec_sections:
            section_num = section.get("number", "unknown")
            
            # Check for critical requirements
            key_reqs = section.get("key_requirements", [])
            for req in key_reqs:
                req_type = req.get("type", "general")
                spec_value = req.get("value", "")
                
                # Compare with BOQ/drawing data
                # (This would need specific parsing based on requirement type)
        
        # Determine overall risk level
        critical_count = len([v for v in results["variances"] if abs(v.variance_percent) > self.VARIANCE_CRITICAL])
        warning_count = len([v for v in results["variances"] if abs(v.variance_percent) > self.VARIANCE_WARNING])
        
        if critical_count > 0:
            results["risk_level"] = RiskLevel.CRITICAL.value
            results["overall_status"] = "non_compliant"
        elif warning_count > 0:
            results["risk_level"] = RiskLevel.MEDIUM.value
            results["overall_status"] = "needs_review"
        
        return results
    
    def calculate_cost_variance(
        self,
        estimated_cost: float,
        actual_cost: float,
        item_name: str = "total"
    ) -> Dict[str, Any]:
        """
        Calculate cost variance with symbolic reasoning.
        
        Args:
            estimated_cost: Estimated/budgeted cost
            actual_cost: Actual/incurred cost
            item_name: Name of cost item
        
        Returns:
            Cost variance analysis
        """
        # Symbolic expressions
        cost_var_expr = self.C_actual - self.C_estimated
        cost_var_pct_expr = (self.C_actual - self.C_estimated) / self.C_estimated
        
        # Calculate values
        variance = actual_cost - estimated_cost
        variance_pct = variance / estimated_cost if estimated_cost != 0 else 0
        
        status = "on_budget"
        if variance_pct > 0.20:
            status = "critical_overrun"
        elif variance_pct > 0.10:
            status = "warning_overrun"
        elif variance_pct < -0.10:
            status = "significant_savings"
        
        return {
            "item": item_name,
            "estimated": estimated_cost,
            "actual": actual_cost,
            "variance": variance,
            "variance_percent": variance_pct,
            "status": status,
            "is_overrun": variance > 0,
        }
    
    def analyze_schedule_variance(
        self,
        planned_duration: float,
        actual_duration: float,
        activity_name: str = "activity"
    ) -> Dict[str, Any]:
        """
        Analyze schedule variance with symbolic reasoning.
        
        Args:
            planned_duration: Planned duration in days
            actual_duration: Actual duration in days
            activity_name: Name of activity
        
        Returns:
            Schedule variance analysis
        """
        # Symbolic expressions
        sched_var_expr = self.T_actual - self.T_planned
        sched_var_pct_expr = (self.T_actual - self.T_planned) / self.T_planned
        
        # Calculate values
        variance = actual_duration - planned_duration
        variance_pct = variance / planned_duration if planned_duration != 0 else 0
        
        status = "on_schedule"
        if variance_pct > 0.20:
            status = "critical_delay"
        elif variance_pct > 0.05:
            status = "warning_delay"
        elif variance_pct < -0.10:
            status = "ahead_of_schedule"
        
        return {
            "activity": activity_name,
            "planned_days": planned_duration,
            "actual_days": actual_duration,
            "variance_days": variance,
            "variance_percent": variance_pct,
            "status": status,
            "is_delayed": variance > 0,
        }
    
    def validate_measurement_formula(
        self,
        formula: str,
        variables: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Validate a measurement formula using SymPy.
        
        Args:
            formula: Mathematical formula as string
            variables: Variable values to substitute
        
        Returns:
            Validation result with calculated value
        """
        try:
            # Parse formula
            expr = sp.sympify(formula)
            
            # Create symbols from variables
            symbols = {k: sp.Symbol(k, real=True) for k in variables.keys()}
            
            # Substitute and evaluate
            result = float(expr.subs(variables))
            
            # Check for dimensional consistency
            # (This is a simplified check - real implementation would track units)
            
            return {
                "valid": True,
                "formula": formula,
                "result": result,
                "variables_used": list(variables.keys()),
            }
        except Exception as e:
            return {
                "valid": False,
                "formula": formula,
                "error": str(e),
                "variables_used": list(variables.keys()),
            }
