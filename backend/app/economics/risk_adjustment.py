"""
Risk-adjusted cost estimation and contingency calculation.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import numpy as np
from enum import Enum


class RiskLevel(Enum):
    """Risk level classification."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RiskFactor:
    """Individual risk factor for cost estimation."""
    id: str
    name: str
    description: str
    category: str
    probability: float  # 0-1
    impact_min: Decimal
    impact_max: Decimal
    impact_distribution: str = "uniform"  # uniform, triangular, normal
    mitigation_cost: Decimal = Decimal("0")
    mitigation_effectiveness: float = 0.0  # 0-1


@dataclass
class RiskAnalysis:
    """Complete risk analysis results."""
    base_estimate: Decimal
    contingency_amount: Decimal
    contingency_percent: float
    risk_adjusted_estimate: Decimal
    confidence_interval_80: Tuple[Decimal, Decimal]
    confidence_interval_95: Tuple[Decimal, Decimal]
    risk_register: List[RiskFactor]
    top_risks: List[RiskFactor]
    expected_risk_value: Decimal


class RiskAdjustedEstimator:
    """Perform risk-adjusted cost estimation."""
    
    # Standard risk categories for construction
    RISK_CATEGORIES = {
        "design": "Design and documentation risks",
        "site": "Site conditions and access",
        "market": "Market conditions and availability",
        "regulatory": "Permits and regulatory approval",
        "weather": "Weather and environmental",
        "labor": "Labor availability and productivity",
        "material": "Material availability and pricing",
        "subcontractor": "Subcontractor performance",
        "safety": "Safety incidents",
        "force_majeure": "Force majeure events"
    }
    
    def __init__(self):
        self.default_contingency_rates = {
            RiskLevel.LOW: 0.05,
            RiskLevel.MEDIUM: 0.10,
            RiskLevel.HIGH: 0.20,
            RiskLevel.CRITICAL: 0.35
        }
    
    async def analyze_project_risks(
        self,
        project_id: str,
        base_estimate: Decimal,
        risk_factors: List[RiskFactor],
        confidence_level: float = 0.80,
        num_simulations: int = 10000
    ) -> RiskAnalysis:
        """Perform comprehensive risk analysis."""
        
        # Run Monte Carlo simulation
        simulation_results = self._run_monte_carlo(
            base_estimate, risk_factors, num_simulations
        )
        
        # Calculate contingency
        contingency_amount, contingency_percent = self._calculate_contingency(
            base_estimate, simulation_results, confidence_level
        )
        
        # Calculate confidence intervals
        ci_80 = self._calculate_confidence_interval(simulation_results, 0.80)
        ci_95 = self._calculate_confidence_interval(simulation_results, 0.95)
        
        # Calculate expected risk value
        expected_risk_value = self._calculate_expected_risk_value(risk_factors)
        
        # Identify top risks
        top_risks = sorted(
            risk_factors,
            key=lambda r: float(r.probability) * float(r.impact_max),
            reverse=True
        )[:5]
        
        return RiskAnalysis(
            base_estimate=base_estimate,
            contingency_amount=contingency_amount,
            contingency_percent=contingency_percent,
            risk_adjusted_estimate=base_estimate + contingency_amount,
            confidence_interval_80=ci_80,
            confidence_interval_95=ci_95,
            risk_register=risk_factors,
            top_risks=top_risks,
            expected_risk_value=expected_risk_value
        )
    
    def _run_monte_carlo(
        self,
        base_estimate: Decimal,
        risk_factors: List[RiskFactor],
        num_simulations: int
    ) -> np.ndarray:
        """Run Monte Carlo simulation for risk analysis."""
        
        results = np.zeros(num_simulations)
        base = float(base_estimate)
        
        for i in range(num_simulations):
            total_impact = 0.0
            
            for risk in risk_factors:
                # Check if risk occurs
                if np.random.random() < risk.probability:
                    # Generate impact based on distribution
                    if risk.impact_distribution == "uniform":
                        impact = np.random.uniform(
                            float(risk.impact_min),
                            float(risk.impact_max)
                        )
                    elif risk.impact_distribution == "triangular":
                        impact = np.random.triangular(
                            float(risk.impact_min),
                            (float(risk.impact_min) + float(risk.impact_max)) / 2,
                            float(risk.impact_max)
                        )
                    else:  # normal
                        mean = (float(risk.impact_min) + float(risk.impact_max)) / 2
                        std = (float(risk.impact_max) - float(risk.impact_min)) / 4
                        impact = np.random.normal(mean, std)
                        impact = max(float(risk.impact_min), min(float(risk.impact_max), impact))
                    
                    # Apply mitigation effectiveness
                    impact *= (1 - risk.mitigation_effectiveness)
                    total_impact += impact
            
            results[i] = base + total_impact
        
        return results
    
    def _calculate_contingency(
        self,
        base_estimate: Decimal,
        simulation_results: np.ndarray,
        confidence_level: float
    ) -> Tuple[Decimal, float]:
        """Calculate recommended contingency."""
        
        # Use percentile method
        percentile = int(confidence_level * 100)
        value_at_confidence = np.percentile(simulation_results, percentile)
        
        contingency = Decimal(str(value_at_confidence)) - base_estimate
        contingency_percent = float(contingency / base_estimate * 100)
        
        return contingency, contingency_percent
    
    def _calculate_confidence_interval(
        self,
        simulation_results: np.ndarray,
        confidence_level: float
    ) -> Tuple[Decimal, Decimal]:
        """Calculate confidence interval."""
        
        alpha = 1 - confidence_level
        lower_percentile = int(alpha / 2 * 100)
        upper_percentile = int((1 - alpha / 2) * 100)
        
        lower = Decimal(str(np.percentile(simulation_results, lower_percentile)))
        upper = Decimal(str(np.percentile(simulation_results, upper_percentile)))
        
        return (lower, upper)
    
    def _calculate_expected_risk_value(
        self,
        risk_factors: List[RiskFactor]
    ) -> Decimal:
        """Calculate total expected risk value."""
        
        total = Decimal("0")
        
        for risk in risk_factors:
            expected_impact = (risk.impact_min + risk.impact_max) / 2
            total += Decimal(str(risk.probability)) * expected_impact
        
        return total
    
    async def recommend_mitigation_strategies(
        self,
        risk_analysis: RiskAnalysis,
        budget_available: Decimal
    ) -> List[Dict]:
        """Recommend risk mitigation strategies within budget."""
        
        recommendations = []
        remaining_budget = budget_available
        
        # Sort risks by cost-benefit of mitigation
        mitigatable_risks = [
            r for r in risk_analysis.risk_register
            if r.mitigation_cost > 0 and r.mitigation_effectiveness > 0
        ]
        
        # Calculate benefit/cost ratio
        for risk in mitigatable_risks:
            expected_impact = (risk.impact_min + risk.impact_max) / 2 * Decimal(str(risk.probability))
            benefit = expected_impact * Decimal(str(risk.mitigation_effectiveness))
            
            if risk.mitigation_cost > 0:
                benefit_cost_ratio = float(benefit / risk.mitigation_cost)
                
                if benefit_cost_ratio > 1.0 and risk.mitigation_cost <= remaining_budget:
                    recommendations.append({
                        "risk_id": risk.id,
                        "risk_name": risk.name,
                        "mitigation_cost": float(risk.mitigation_cost),
                        "expected_benefit": float(benefit),
                        "benefit_cost_ratio": benefit_cost_ratio,
                        "effectiveness": risk.mitigation_effectiveness,
                        "recommended": True
                    })
                    remaining_budget -= risk.mitigation_cost
        
        # Sort by benefit/cost ratio
        recommendations.sort(key=lambda x: x["benefit_cost_ratio"], reverse=True)
        
        return recommendations
    
    async def calculate_reserve_drawdown(
        self,
        risk_analysis: RiskAnalysis,
        actual_issues: List[Dict],
        period: str
    ) -> Dict:
        """Calculate contingency reserve drawdown."""
        
        total_drawn = Decimal("0")
        draws_by_category: Dict[str, Decimal] = {}
        
        for issue in actual_issues:
            amount = Decimal(str(issue.get("cost_impact", 0)))
            category = issue.get("category", "unknown")
            
            total_drawn += amount
            draws_by_category[category] = draws_by_category.get(category, Decimal("0")) + amount
        
        remaining = risk_analysis.contingency_amount - total_drawn
        utilization_rate = float(total_drawn / risk_analysis.contingency_amount * 100) if risk_analysis.contingency_amount > 0 else 0
        
        return {
            "period": period,
            "original_contingency": float(risk_analysis.contingency_amount),
            "drawn_to_date": float(total_drawn),
            "remaining": float(remaining),
            "utilization_rate": utilization_rate,
            "by_category": {k: float(v) for k, v in draws_by_category.items()},
            "status": "adequate" if remaining > 0 else "depleted",
            "projected_adequacy": "TBD based on remaining risks"
        }
