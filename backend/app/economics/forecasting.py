"""
Cost Forecasting with Monte Carlo Simulation
Predicts project costs using probabilistic modeling.
"""

import numpy as np
from typing import Optional, Dict, List, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RiskFactor:
    """Risk factor for cost forecasting."""
    name: str
    probability: float  # 0-1
    impact_low: float  # Percentage impact
    impact_high: float  # Percentage impact
    correlation: float = 0.0  # Correlation with other factors


@dataclass
class ForecastScenario:
    """A single forecast scenario."""
    name: str
    probability: float
    cost_adjustment: float  # Percentage adjustment
    description: str = ""


@dataclass
class ForecastResult:
    """Result of cost forecasting."""
    base_cost: float
    mean_forecast: float
    median_forecast: float
    std_deviation: float
    confidence_intervals: Dict[str, Tuple[float, float]]
    percentiles: Dict[str, float]
    scenarios: List[Dict[str, Any]]
    risk_adjusted_cost: float
    simulation_count: int
    processing_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_cost": self.base_cost,
            "mean_forecast": self.mean_forecast,
            "median_forecast": self.median_forecast,
            "std_deviation": self.std_deviation,
            "confidence_intervals": self.confidence_intervals,
            "percentiles": self.percentiles,
            "scenarios": self.scenarios,
            "risk_adjusted_cost": self.risk_adjusted_cost,
            "simulation_count": self.simulation_count,
            "processing_time": self.processing_time
        }


class MonteCarloSimulator:
    """
    Monte Carlo simulation for cost forecasting.
    Models uncertainty in project costs through probabilistic simulation.
    """
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.RandomState(seed)
    
    async def simulate(
        self,
        base_cost: float,
        risk_factors: List[RiskFactor],
        num_simulations: int = 10000,
        confidence_levels: List[float] = None
    ) -> ForecastResult:
        """
        Run Monte Carlo simulation for cost forecasting.
        
        Args:
            base_cost: Base project cost
            risk_factors: List of risk factors
            num_simulations: Number of simulation iterations
            confidence_levels: Confidence levels for intervals
        
        Returns:
            ForecastResult with simulation results
        """
        import time
        start_time = time.time()
        
        if confidence_levels is None:
            confidence_levels = [0.80, 0.90, 0.95]
        
        # Run simulations
        results = np.zeros(num_simulations)
        
        for i in range(num_simulations):
            adjusted_cost = base_cost
            
            for factor in risk_factors:
                # Determine if risk occurs
                if self.rng.random() < factor.probability:
                    # Sample impact from uniform distribution
                    impact = self.rng.uniform(factor.impact_low, factor.impact_high)
                    adjusted_cost *= (1 + impact / 100)
            
            results[i] = adjusted_cost
        
        # Calculate statistics
        mean = np.mean(results)
        median = np.median(results)
        std = np.std(results)
        
        # Calculate percentiles
        percentiles = {
            "p10": np.percentile(results, 10),
            "p25": np.percentile(results, 25),
            "p50": np.percentile(results, 50),
            "p75": np.percentile(results, 75),
            "p90": np.percentile(results, 90),
        }
        
        # Calculate confidence intervals
        confidence_intervals = {}
        for level in confidence_levels:
            alpha = (1 - level) / 2
            lower = np.percentile(results, alpha * 100)
            upper = np.percentile(results, (1 - alpha) * 100)
            confidence_intervals[f"{int(level*100)}%"] = (lower, upper)
        
        # Generate scenarios
        scenarios = self._generate_scenarios(base_cost, risk_factors, results)
        
        # Calculate risk-adjusted cost (P70)
        risk_adjusted = np.percentile(results, 70)
        
        processing_time = time.time() - start_time
        
        return ForecastResult(
            base_cost=base_cost,
            mean_forecast=mean,
            median_forecast=median,
            std_deviation=std,
            confidence_intervals=confidence_intervals,
            percentiles=percentiles,
            scenarios=scenarios,
            risk_adjusted_cost=risk_adjusted,
            simulation_count=num_simulations,
            processing_time=processing_time
        )
    
    def _generate_scenarios(
        self,
        base_cost: float,
        risk_factors: List[RiskFactor],
        results: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Generate forecast scenarios."""
        scenarios = []
        
        # Optimistic scenario (P10)
        scenarios.append({
            "name": "Optimistic",
            "probability": 0.10,
            "cost": np.percentile(results, 10),
            "description": "Best case - minimal risks materialize"
        })
        
        # Most likely scenario (P50)
        scenarios.append({
            "name": "Most Likely",
            "probability": 0.50,
            "cost": np.percentile(results, 50),
            "description": "Expected case - average risk impact"
        })
        
        # Pessimistic scenario (P75)
        scenarios.append({
            "name": "Pessimistic",
            "probability": 0.25,
            "cost": np.percentile(results, 75),
            "description": "Challenging case - several risks materialize"
        })
        
        # Worst case scenario (P90)
        scenarios.append({
            "name": "Worst Case",
            "probability": 0.10,
            "cost": np.percentile(results, 90),
            "description": "Worst case - multiple major risks occur"
        })
        
        return scenarios
    
    async def sensitivity_analysis(
        self,
        base_cost: float,
        risk_factors: List[RiskFactor],
        num_simulations: int = 5000
    ) -> Dict[str, Any]:
        """
        Perform sensitivity analysis on risk factors.
        
        Args:
            base_cost: Base project cost
            risk_factors: List of risk factors
            num_simulations: Number of simulations per factor
        
        Returns:
            Sensitivity analysis results
        """
        sensitivities = []
        
        for factor in risk_factors:
            # Run simulation with only this factor
            single_factor = [factor]
            result = await self.simulate(base_cost, single_factor, num_simulations)
            
            sensitivities.append({
                "factor": factor.name,
                "mean_impact": result.mean_forecast - base_cost,
                "std_impact": result.std_deviation,
                "max_impact": result.percentiles["p90"] - base_cost
            })
        
        # Sort by impact
        sensitivities.sort(key=lambda x: abs(x["max_impact"]), reverse=True)
        
        return {
            "sensitivities": sensitivities,
            "most_critical": sensitivities[0] if sensitivities else None
        }


class CostForecaster:
    """
    Cost forecasting engine using Monte Carlo simulation.
    Provides probabilistic cost estimates with confidence intervals.
    """
    
    # Default risk factors for construction projects
    DEFAULT_RISKS = [
        RiskFactor("Material Price Escalation", 0.6, 2, 15),
        RiskFactor("Labor Shortage", 0.4, 5, 20),
        RiskFactor("Weather Delays", 0.3, 3, 10),
        RiskFactor("Design Changes", 0.5, 2, 12),
        RiskFactor("Site Conditions", 0.25, 5, 25),
        RiskFactor("Permit Delays", 0.2, 2, 8),
        RiskFactor("Supply Chain Issues", 0.35, 3, 18),
        RiskFactor("Regulatory Changes", 0.15, 2, 10),
    ]
    
    def __init__(self):
        self.simulator = MonteCarloSimulator()
    
    async def forecast_project_cost(
        self,
        budget_items: List[Dict[str, Any]],
        risk_factors: Optional[List[RiskFactor]] = None,
        num_simulations: int = 10000
    ) -> ForecastResult:
        """
        Forecast total project cost.
        
        Args:
            budget_items: List of budget line items
            risk_factors: Optional custom risk factors
            num_simulations: Number of Monte Carlo iterations
        
        Returns:
            ForecastResult with probabilistic cost estimates
        """
        # Calculate base cost
        base_cost = sum(item.get('amount', 0) for item in budget_items)
        
        # Use default risks if none provided
        risks = risk_factors or self.DEFAULT_RISKS
        
        # Run simulation
        result = await self.simulator.simulate(
            base_cost,
            risks,
            num_simulations
        )
        
        return result
    
    async def forecast_line_item(
        self,
        line_item: Dict[str, Any],
        risk_factors: Optional[List[RiskFactor]] = None
    ) -> ForecastResult:
        """
        Forecast cost for a single line item.
        
        Args:
            line_item: Budget line item
            risk_factors: Optional custom risk factors
        
        Returns:
            ForecastResult for the line item
        """
        base_cost = line_item.get('amount', 0)
        
        # Adjust risks for line item scale
        risks = risk_factors or [
            RiskFactor("Quantity Variance", 0.5, -10, 15),
            RiskFactor("Unit Price Variance", 0.6, -5, 20),
            RiskFactor("Productivity", 0.4, -10, 10),
        ]
        
        result = await self.simulator.simulate(base_cost, risks, 5000)
        
        return result
    
    async def compare_scenarios(
        self,
        base_cost: float,
        scenarios: List[ForecastScenario],
        num_simulations: int = 5000
    ) -> Dict[str, Any]:
        """
        Compare multiple forecast scenarios.
        
        Args:
            base_cost: Base project cost
            scenarios: List of forecast scenarios
            num_simulations: Simulations per scenario
        
        Returns:
            Scenario comparison results
        """
        results = []
        
        for scenario in scenarios:
            # Create risk factor for scenario
            risk = RiskFactor(
                scenario.name,
                scenario.probability,
                scenario.cost_adjustment,
                scenario.cost_adjustment
            )
            
            forecast = await self.simulator.simulate(
                base_cost,
                [risk],
                num_simulations
            )
            
            results.append({
                "scenario": scenario.name,
                "description": scenario.description,
                "mean_cost": forecast.mean_forecast,
                "p50": forecast.percentiles["p50"],
                "p90": forecast.percentiles["p90"],
                "probability": scenario.probability
            })
        
        return {
            "scenarios": results,
            "expected_value": sum(s["mean_cost"] * s["probability"] for s in results)
        }
    
    async def generate_contingency_recommendation(
        self,
        base_cost: float,
        risk_factors: List[RiskFactor],
        target_confidence: float = 0.80
    ) -> Dict[str, Any]:
        """
        Generate contingency recommendation based on risk analysis.
        
        Args:
            base_cost: Base project cost
            risk_factors: Risk factors
            target_confidence: Target confidence level
        
        Returns:
            Contingency recommendation
        """
        # Run simulation
        result = await self.simulator.simulate(base_cost, risk_factors, 10000)
        
        # Get cost at target confidence level
        percentile = int((1 - target_confidence) * 100)
        target_cost = np.percentile(
            np.random.normal(result.mean_forecast, result.std_deviation, 10000),
            100 - percentile
        )
        
        contingency_amount = target_cost - base_cost
        contingency_percent = (contingency_amount / base_cost) * 100 if base_cost > 0 else 0
        
        return {
            "base_cost": base_cost,
            "target_confidence": target_confidence,
            "recommended_contingency": contingency_amount,
            "contingency_percent": contingency_percent,
            "total_budget_recommendation": target_cost,
            "risk_level": self._assess_risk_level(result.std_deviation / base_cost if base_cost > 0 else 0)
        }
    
    def _assess_risk_level(self, coefficient_of_variation: float) -> str:
        """Assess risk level based on coefficient of variation."""
        if coefficient_of_variation < 0.05:
            return "Low"
        elif coefficient_of_variation < 0.10:
            return "Medium"
        elif coefficient_of_variation < 0.20:
            return "High"
        else:
            return "Very High"


# Singleton instance
forecaster = CostForecaster()


async def get_forecaster() -> CostForecaster:
    """Get cost forecaster instance."""
    return forecaster
