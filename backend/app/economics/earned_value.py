"""
Earned Value Management (EVM) calculations and reporting.
"""
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import numpy as np


@dataclass
class EVMBaseline:
    """Baseline data for EVM calculations."""
    total_budget_at_completion: Decimal
    planned_value_curve: List[Tuple[date, Decimal]]
    start_date: date
    end_date: date
    work_packages: List[Dict]


@dataclass
class EVMMetrics:
    """Current EVM metrics."""
    # Basic metrics
    planned_value: Decimal  # PV / BCWS
    earned_value: Decimal   # EV / BCWP
    actual_cost: Decimal    # AC / ACWP
    
    # Performance indices
    schedule_performance_index: float  # SPI = EV / PV
    cost_performance_index: float      # CPI = EV / AC
    
    # Variances
    schedule_variance: Decimal         # SV = EV - PV
    cost_variance: Decimal             # CV = EV - AC
    schedule_variance_percent: float   # SV% = SV / PV
    cost_variance_percent: float       # CV% = CV / PV
    
    # Forecasts
    estimate_at_completion: Decimal    # EAC
    estimate_to_complete: Decimal      # ETC
    variance_at_completion: Decimal    # VAC
    to_complete_performance_index: float  # TCPI
    
    # Independent estimates
    budget_at_completion: Decimal      # BAC
    
    # Status
    data_date: date
    percent_complete: float
    percent_spent: float


class EarnedValueAnalyzer:
    """Perform Earned Value Management analysis."""
    
    def __init__(self):
        pass
    
    async def calculate_metrics(
        self,
        baseline: EVMBaseline,
        actual_costs: Dict[date, Decimal],
        percent_complete_by_package: Dict[str, float],
        data_date: date
    ) -> EVMMetrics:
        """Calculate all EVM metrics for current period."""
        
        # Calculate Planned Value (PV)
        pv = self._calculate_planned_value(baseline, data_date)
        
        # Calculate Earned Value (EV)
        ev = self._calculate_earned_value(
            baseline, percent_complete_by_package
        )
        
        # Calculate Actual Cost (AC)
        ac = self._calculate_actual_cost(actual_costs, data_date)
        
        # Calculate performance indices
        spi = float(ev / pv) if pv > 0 else 1.0
        cpi = float(ev / ac) if ac > 0 else 1.0
        
        # Calculate variances
        sv = ev - pv
        cv = ev - ac
        sv_percent = float(sv / pv * 100) if pv > 0 else 0.0
        cv_percent = float(cv / pv * 100) if pv > 0 else 0.0
        
        # Calculate forecasts
        bac = baseline.total_budget_at_completion
        
        # EAC = AC + (BAC - EV) / CPI (typical)
        eac = ac + (bac - ev) / Decimal(str(cpi)) if cpi != 0 else bac
        
        # ETC = EAC - AC
        etc = eac - ac
        
        # VAC = BAC - EAC
        vac = bac - eac
        
        # TCPI = (BAC - EV) / (EAC - AC)
        tcpi = float((bac - ev) / (eac - ac)) if (eac - ac) > 0 else 1.0
        
        # Percentages
        percent_complete = float(ev / bac * 100) if bac > 0 else 0.0
        percent_spent = float(ac / bac * 100) if bac > 0 else 0.0
        
        return EVMMetrics(
            planned_value=pv,
            earned_value=ev,
            actual_cost=ac,
            schedule_performance_index=spi,
            cost_performance_index=cpi,
            schedule_variance=sv,
            cost_variance=cv,
            schedule_variance_percent=sv_percent,
            cost_variance_percent=cv_percent,
            estimate_at_completion=eac,
            estimate_to_complete=etc,
            variance_at_completion=vac,
            to_complete_performance_index=tcpi,
            budget_at_completion=bac,
            data_date=data_date,
            percent_complete=percent_complete,
            percent_spent=percent_spent
        )
    
    def _calculate_planned_value(
        self,
        baseline: EVMBaseline,
        data_date: date
    ) -> Decimal:
        """Calculate Planned Value (PV) as of data date."""
        pv = Decimal("0")
        
        for curve_date, value in baseline.planned_value_curve:
            if curve_date <= data_date:
                pv = value
            else:
                break
        
        return pv
    
    def _calculate_earned_value(
        self,
        baseline: EVMBaseline,
        percent_complete_by_package: Dict[str, float]
    ) -> Decimal:
        """Calculate Earned Value (EV) based on work package completion."""
        ev = Decimal("0")
        
        for wp in baseline.work_packages:
            wp_id = wp["id"]
            wp_budget = Decimal(str(wp["budget"]))
            percent_complete = percent_complete_by_package.get(wp_id, 0.0)
            ev += wp_budget * Decimal(str(percent_complete / 100))
        
        return ev
    
    def _calculate_actual_cost(
        self,
        actual_costs: Dict[date, Decimal],
        data_date: date
    ) -> Decimal:
        """Calculate Actual Cost (AC) as of data date."""
        ac = Decimal("0")
        
        for cost_date, cost in actual_costs.items():
            if cost_date <= data_date:
                ac += cost
        
        return ac
    
    async def generate_performance_report(
        self,
        metrics: EVMMetrics,
        previous_metrics: Optional[EVMMetrics] = None
    ) -> Dict:
        """Generate comprehensive EVM performance report."""
        
        report = {
            "data_date": metrics.data_date.isoformat(),
            "summary": {
                "budget_at_completion": float(metrics.budget_at_completion),
                "earned_value": float(metrics.earned_value),
                "actual_cost": float(metrics.actual_cost),
                "planned_value": float(metrics.planned_value),
                "percent_complete": metrics.percent_complete,
                "percent_spent": metrics.percent_spent
            },
            "performance_indices": {
                "spi": metrics.schedule_performance_index,
                "cpi": metrics.cost_performance_index,
                "spi_status": self._get_spi_status(metrics.schedule_performance_index),
                "cpi_status": self._get_cpi_status(metrics.cost_performance_index)
            },
            "variances": {
                "schedule_variance": float(metrics.schedule_variance),
                "cost_variance": float(metrics.cost_variance),
                "schedule_variance_percent": metrics.schedule_variance_percent,
                "cost_variance_percent": metrics.cost_variance_percent,
                "sv_status": self._get_variance_status(metrics.schedule_variance),
                "cv_status": self._get_variance_status(metrics.cost_variance)
            },
            "forecasts": {
                "estimate_at_completion": float(metrics.estimate_at_completion),
                "estimate_to_complete": float(metrics.estimate_to_complete),
                "variance_at_completion": float(metrics.variance_at_completion),
                "tcpi": metrics.to_complete_performance_index
            },
            "trends": self._calculate_trends(metrics, previous_metrics),
            "recommendations": self._generate_recommendations(metrics)
        }
        
        return report
    
    def _get_spi_status(self, spi: float) -> str:
        """Get status based on SPI."""
        if spi >= 1.05:
            return "ahead_of_schedule"
        elif spi >= 0.95:
            return "on_schedule"
        elif spi >= 0.85:
            return "slightly_behind"
        else:
            return "significantly_behind"
    
    def _get_cpi_status(self, cpi: float) -> str:
        """Get status based on CPI."""
        if cpi >= 1.05:
            return "under_budget"
        elif cpi >= 0.95:
            return "on_budget"
        elif cpi >= 0.85:
            return "slightly_over"
        else:
            return "significantly_over"
    
    def _get_variance_status(self, variance: Decimal) -> str:
        """Get status based on variance."""
        if variance > 0:
            return "favorable"
        elif variance == 0:
            return "neutral"
        else:
            return "unfavorable"
    
    def _calculate_trends(
        self,
        current: EVMMetrics,
        previous: Optional[EVMMetrics]
    ) -> Dict:
        """Calculate trends from previous period."""
        if previous is None:
            return {"spi_trend": "insufficient_data", "cpi_trend": "insufficient_data"}
        
        spi_change = current.schedule_performance_index - previous.schedule_performance_index
        cpi_change = current.cost_performance_index - previous.cost_performance_index
        
        return {
            "spi_trend": "improving" if spi_change > 0.02 else "declining" if spi_change < -0.02 else "stable",
            "cpi_trend": "improving" if cpi_change > 0.02 else "declining" if cpi_change < -0.02 else "stable",
            "spi_change": spi_change,
            "cpi_change": cpi_change
        }
    
    def _generate_recommendations(self, metrics: EVMMetrics) -> List[str]:
        """Generate recommendations based on EVM metrics."""
        recommendations = []
        
        # Schedule recommendations
        if metrics.schedule_performance_index < 0.85:
            recommendations.append(
                "CRITICAL: Schedule performance significantly below target. "
                "Consider schedule recovery plan or scope reduction."
            )
        elif metrics.schedule_performance_index < 0.95:
            recommendations.append(
                "WARNING: Schedule performance below target. "
                "Review critical path and resource allocation."
            )
        
        # Cost recommendations
        if metrics.cost_performance_index < 0.85:
            recommendations.append(
                "CRITICAL: Cost performance significantly below target. "
                "Implement immediate cost control measures."
            )
        elif metrics.cost_performance_index < 0.95:
            recommendations.append(
                "WARNING: Cost performance below target. "
                "Review cost drivers and implement controls."
            )
        
        # TCPI recommendations
        if metrics.to_complete_performance_index > 1.2:
            recommendations.append(
                f"TCPI of {metrics.to_complete_performance_index:.2f} indicates "
                "remaining work must be performed very efficiently to meet budget."
            )
        
        return recommendations
    
    async def calculate_independent_estimates(
        self,
        metrics: EVMMetrics,
        method: str = "cpi"
    ) -> Dict[str, Decimal]:
        """Calculate independent EAC estimates using different methods."""
        
        bac = metrics.budget_at_completion
        ev = metrics.earned_value
        ac = metrics.actual_cost
        cpi = Decimal(str(metrics.cost_performance_index))
        spi = Decimal(str(metrics.schedule_performance_index))
        
        estimates = {}
        
        # Method 1: AC + (BAC - EV) - assumes future work at budget
        estimates["method_1"] = ac + (bac - ev)
        
        # Method 2: AC + (BAC - EV) / CPI - assumes future work at current CPI
        estimates["method_2"] = ac + (bac - ev) / cpi if cpi > 0 else bac
        
        # Method 3: AC + (BAC - EV) / (CPI * SPI) - assumes both cost and schedule impact
        estimates["method_3"] = ac + (bac - ev) / (cpi * spi) if (cpi * spi) > 0 else bac
        
        # Method 4: AC + Bottom-up ETC - requires manual input
        estimates["method_4"] = None
        
        return estimates
