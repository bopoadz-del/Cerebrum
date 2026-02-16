"""
Vendor performance analysis and cost benchmarking.
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
import statistics


@dataclass
class VendorPerformance:
    """Performance metrics for a vendor."""
    vendor_id: str
    vendor_name: str
    total_contracts: int
    total_value: Decimal
    on_time_delivery_rate: float
    quality_score: float
    cost_variance: float
    safety_incidents: int
    dispute_count: int
    average_response_time_days: float
    payment_terms: str
    
    @property
    def overall_score(self) -> float:
        """Calculate overall vendor score."""
        weights = {
            "delivery": 0.25,
            "quality": 0.25,
            "cost": 0.20,
            "safety": 0.20,
            "response": 0.10
        }
        
        # Normalize each metric to 0-100 scale
        delivery_score = self.on_time_delivery_rate * 100
        quality_score = self.quality_score
        cost_score = max(0, 100 - abs(self.cost_variance))
        safety_score = max(0, 100 - self.safety_incidents * 10)
        response_score = max(0, 100 - self.average_response_time_days * 5)
        
        return (
            weights["delivery"] * delivery_score +
            weights["quality"] * quality_score +
            weights["cost"] * cost_score +
            weights["safety"] * safety_score +
            weights["response"] * response_score
        )


@dataclass
class CostBenchmark:
    """Cost benchmark for a specific item/activity."""
    item_code: str
    description: str
    unit: str
    vendor_costs: Dict[str, Decimal]
    market_average: Decimal
    market_low: Decimal
    market_high: Decimal
    rsmeans_reference: Optional[Decimal] = None
    
    def get_variance_from_market(self, vendor_id: str) -> float:
        """Calculate variance from market average for a vendor."""
        if vendor_id not in self.vendor_costs:
            return 0.0
        
        vendor_cost = float(self.vendor_costs[vendor_id])
        market_avg = float(self.market_average)
        
        return ((vendor_cost - market_avg) / market_avg) * 100


class VendorAnalyzer:
    """Analyze vendor performance and costs."""
    
    def __init__(self):
        self.performance_history: Dict[str, List[VendorPerformance]] = {}
    
    async def analyze_vendor(
        self,
        vendor_id: str,
        project_ids: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> VendorPerformance:
        """Analyze vendor performance across projects."""
        
        # Placeholder for database queries
        # In production, query actual vendor data
        
        return VendorPerformance(
            vendor_id=vendor_id,
            vendor_name="Sample Vendor",
            total_contracts=10,
            total_value=Decimal("500000"),
            on_time_delivery_rate=0.85,
            quality_score=88.5,
            cost_variance=2.5,
            safety_incidents=0,
            dispute_count=1,
            average_response_time_days=3.5,
            payment_terms="Net 30"
        )
    
    async def compare_vendors(
        self,
        vendor_ids: List[str],
        metric: str = "overall_score"
    ) -> List[Dict[str, Any]]:
        """Compare multiple vendors on a specific metric."""
        
        performances = []
        for vendor_id in vendor_ids:
            perf = await self.analyze_vendor(vendor_id)
            performances.append(perf)
        
        # Sort by metric
        if metric == "overall_score":
            performances.sort(key=lambda x: x.overall_score, reverse=True)
        elif metric == "on_time_delivery_rate":
            performances.sort(key=lambda x: x.on_time_delivery_rate, reverse=True)
        elif metric == "cost_variance":
            performances.sort(key=lambda x: abs(x.cost_variance))
        
        return [
            {
                "vendor_id": p.vendor_id,
                "vendor_name": p.vendor_name,
                "overall_score": p.overall_score,
                "on_time_delivery_rate": p.on_time_delivery_rate,
                "quality_score": p.quality_score,
                "cost_variance": p.cost_variance,
                "total_value": float(p.total_value)
            }
            for p in performances
        ]
    
    async def create_cost_benchmark(
        self,
        item_code: str,
        vendor_ids: List[str],
        project_ids: Optional[List[str]] = None
    ) -> CostBenchmark:
        """Create cost benchmark for an item across vendors."""
        
        # Placeholder for database queries
        vendor_costs = {}
        
        for vendor_id in vendor_ids:
            # Query actual costs from database
            vendor_costs[vendor_id] = Decimal("100.00")
        
        costs = [float(c) for c in vendor_costs.values()]
        
        return CostBenchmark(
            item_code=item_code,
            description="Sample Item",
            unit="EA",
            vendor_costs=vendor_costs,
            market_average=Decimal(str(statistics.mean(costs))),
            market_low=Decimal(str(min(costs))),
            market_high=Decimal(str(max(costs))),
            rsmeans_reference=Decimal("95.00")
        )
    
    async def identify_cost_savings(
        self,
        project_id: str,
        threshold_percent: float = 10.0
    ) -> List[Dict[str, Any]]:
        """Identify potential cost savings opportunities."""
        
        opportunities = []
        
        # Placeholder for analysis
        # In production, compare actual costs to benchmarks
        
        opportunities.append({
            "category": "vendor_consolidation",
            "description": "Consolidate purchases with top-performing vendor",
            "potential_savings": 25000,
            "confidence": 0.8,
            "implementation_complexity": "low"
        })
        
        opportunities.append({
            "category": "payment_terms",
            "description": "Negotiate early payment discounts",
            "potential_savings": 15000,
            "confidence": 0.7,
            "implementation_complexity": "low"
        })
        
        return opportunities
    
    async def generate_vendor_scorecard(
        self,
        vendor_id: str,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Generate comprehensive vendor scorecard."""
        
        perf = await self.analyze_vendor(vendor_id)
        
        return {
            "vendor_id": vendor_id,
            "vendor_name": perf.vendor_name,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            },
            "performance_summary": {
                "overall_score": round(perf.overall_score, 2),
                "grade": self._calculate_grade(perf.overall_score),
                "rank": "top_25%"  # Placeholder
            },
            "detailed_metrics": {
                "delivery": {
                    "score": perf.on_time_delivery_rate * 100,
                    "grade": self._calculate_grade(perf.on_time_delivery_rate * 100)
                },
                "quality": {
                    "score": perf.quality_score,
                    "grade": self._calculate_grade(perf.quality_score)
                },
                "cost": {
                    "variance": perf.cost_variance,
                    "grade": self._calculate_grade(100 - abs(perf.cost_variance))
                },
                "safety": {
                    "incidents": perf.safety_incidents,
                    "grade": "A" if perf.safety_incidents == 0 else "B"
                }
            },
            "contract_summary": {
                "total_contracts": perf.total_contracts,
                "total_value": float(perf.total_value),
                "active_contracts": perf.total_contracts  # Placeholder
            },
            "recommendations": self._generate_vendor_recommendations(perf)
        }
    
    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _generate_vendor_recommendations(self, perf: VendorPerformance) -> List[str]:
        """Generate recommendations for vendor improvement."""
        
        recommendations = []
        
        if perf.on_time_delivery_rate < 0.90:
            recommendations.append(
                "Improve delivery schedule adherence - currently below 90%"
            )
        
        if perf.quality_score < 85:
            recommendations.append(
                "Implement quality improvement program"
            )
        
        if perf.cost_variance > 5:
            recommendations.append(
                "Review pricing competitiveness - above market average"
            )
        
        return recommendations
