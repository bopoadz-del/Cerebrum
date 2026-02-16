"""
Cash flow analysis and forecasting for construction projects.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
import numpy as np
from enum import Enum


class PaymentTerms(Enum):
    """Standard payment terms for construction contracts."""
    NET_15 = 15
    NET_30 = 30
    NET_45 = 45
    NET_60 = 60
    PROGRESS_BILLING = "progress"
    MILESTONE = "milestone"


@dataclass
class CashFlowItem:
    """Single cash flow item."""
    date: date
    amount: Decimal
    category: str
    description: str
    project_id: Optional[str] = None
    is_inflow: bool = True
    probability: float = 1.0


@dataclass
class CashFlowProjection:
    """Projected cash flow over time."""
    start_date: date
    end_date: date
    daily_flows: List[CashFlowItem]
    cumulative_balance: List[Decimal]
    peak_positive: Tuple[date, Decimal]
    peak_negative: Tuple[date, Decimal]
    average_daily_balance: Decimal


@dataclass
class PaymentSchedule:
    """Scheduled payment with probability weighting."""
    scheduled_date: date
    amount: Decimal
    terms: PaymentTerms
    probability: float = 1.0
    actual_payment_date: Optional[date] = None


class CashFlowAnalyzer:
    """Analyze and project cash flows for construction projects."""
    
    def __init__(self):
        self.payment_delay_stats: Dict[PaymentTerms, Dict[str, float]] = {
            PaymentTerms.NET_15: {"mean": 18, "std": 3},
            PaymentTerms.NET_30: {"mean": 35, "std": 7},
            PaymentTerms.NET_45: {"mean": 50, "std": 10},
            PaymentTerms.NET_60: {"mean": 68, "std": 12},
            PaymentTerms.PROGRESS_BILLING: {"mean": 45, "std": 15},
            PaymentTerms.MILESTONE: {"mean": 30, "std": 20},
        }
    
    async def analyze_historical_cash_flow(
        self,
        project_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Analyze historical cash flow patterns."""
        # Placeholder for database query
        # In production, query actual payment and expense data
        
        return {
            "project_id": project_id,
            "period": {"start": start_date, "end": end_date},
            "total_inflows": Decimal("0"),
            "total_outflows": Decimal("0"),
            "net_cash_flow": Decimal("0"),
            "average_payment_delay": 0,
            "payment_reliability_score": 0.0,
        }
    
    async def create_projection(
        self,
        inflows: List[PaymentSchedule],
        outflows: List[PaymentSchedule],
        start_date: date,
        end_date: date,
        initial_balance: Decimal = Decimal("0"),
        confidence_level: float = 0.95
    ) -> CashFlowProjection:
        """Create cash flow projection with Monte Carlo simulation."""
        
        # Generate daily date range
        date_range = [
            start_date + timedelta(days=i)
            for i in range((end_date - start_date).days + 1)
        ]
        
        # Run Monte Carlo simulations
        num_simulations = 1000
        all_balances = []
        
        for _ in range(num_simulations):
            daily_balance = self._simulate_single_scenario(
                inflows, outflows, date_range, initial_balance
            )
            all_balances.append(daily_balance)
        
        # Calculate statistics
        balance_array = np.array([[float(b) for b in sim] for sim in all_balances])
        
        # Use confidence interval
        lower_idx = int((1 - confidence_level) / 2 * num_simulations)
        upper_idx = int((1 + confidence_level) / 2 * num_simulations)
        
        mean_balances = [Decimal(str(np.mean(balance_array[:, i]))) 
                        for i in range(len(date_range))]
        
        # Find peaks
        peak_positive = max(enumerate(mean_balances), key=lambda x: x[1])
        peak_negative = min(enumerate(mean_balances), key=lambda x: x[1])
        
        # Combine flows
        all_flows = []
        for sched in inflows + outflows:
            all_flows.append(CashFlowItem(
                date=sched.scheduled_date,
                amount=sched.amount,
                category="payment",
                description=f"Payment - {sched.terms.value}",
                is_inflow=sched in inflows,
                probability=sched.probability
            ))
        
        return CashFlowProjection(
            start_date=start_date,
            end_date=end_date,
            daily_flows=sorted(all_flows, key=lambda x: x.date),
            cumulative_balance=mean_balances,
            peak_positive=(date_range[peak_positive[0]], peak_positive[1]),
            peak_negative=(date_range[peak_negative[0]], peak_negative[1]),
            average_daily_balance=sum(mean_balances) / len(mean_balances)
        )
    
    def _simulate_single_scenario(
        self,
        inflows: List[PaymentSchedule],
        outflows: List[PaymentSchedule],
        date_range: List[date],
        initial_balance: Decimal
    ) -> List[Decimal]:
        """Simulate a single cash flow scenario."""
        
        balances = []
        current_balance = initial_balance
        
        # Apply random delays to payments
        actual_inflows = []
        for sched in inflows:
            if np.random.random() > sched.probability:
                continue
            
            stats = self.payment_delay_stats.get(sched.terms, {"mean": 30, "std": 10})
            delay = max(0, int(np.random.normal(stats["mean"], stats["std"])))
            actual_date = sched.scheduled_date + timedelta(days=delay)
            actual_inflows.append((actual_date, sched.amount))
        
        actual_outflows = []
        for sched in outflows:
            if np.random.random() > sched.probability:
                continue
            
            stats = self.payment_delay_stats.get(sched.terms, {"mean": 30, "std": 10})
            delay = max(0, int(np.random.normal(stats["mean"], stats["std"])))
            actual_date = sched.scheduled_date + timedelta(days=delay)
            actual_outflows.append((actual_date, sched.amount))
        
        # Calculate daily balances
        for current_date in date_range:
            for inflow_date, amount in actual_inflows:
                if inflow_date == current_date:
                    current_balance += amount
            
            for outflow_date, amount in actual_outflows:
                if outflow_date == current_date:
                    current_balance -= amount
            
            balances.append(current_balance)
        
        return balances
    
    async def identify_cash_gaps(
        self,
        projection: CashFlowProjection,
        minimum_balance: Decimal = Decimal("0")
    ) -> List[Dict[str, Any]]:
        """Identify periods where cash flow falls below minimum."""
        
        gaps = []
        in_gap = False
        gap_start = None
        
        date_range = [
            projection.start_date + timedelta(days=i)
            for i in range((projection.end_date - projection.start_date).days + 1)
        ]
        
        for i, (current_date, balance) in enumerate(zip(date_range, projection.cumulative_balance)):
            if balance < minimum_balance:
                if not in_gap:
                    in_gap = True
                    gap_start = current_date
            else:
                if in_gap:
                    in_gap = False
                    gaps.append({
                        "start_date": gap_start,
                        "end_date": date_range[i - 1],
                        "duration_days": (date_range[i - 1] - gap_start).days + 1,
                        "minimum_balance": min(
                            projection.cumulative_balance[
                                date_range.index(gap_start):i
                            ]
                        ),
                        "recommended_action": "Consider adjusting payment schedule or securing credit line"
                    })
        
        # Handle gap that extends to end
        if in_gap:
            gaps.append({
                "start_date": gap_start,
                "end_date": projection.end_date,
                "duration_days": (projection.end_date - gap_start).days + 1,
                "minimum_balance": min(
                    projection.cumulative_balance[date_range.index(gap_start):]
                ),
                "recommended_action": "Urgent: Secure funding or renegotiate terms"
            })
        
        return gaps
    
    async def optimize_payment_timing(
        self,
        payables: List[PaymentSchedule],
        receivables: List[PaymentSchedule],
        target_balance: Decimal = Decimal("100000")
    ) -> Dict[str, Any]:
        """Optimize payment timing to maintain target balance."""
        
        # Sort by scheduled date
        payables_sorted = sorted(payables, key=lambda x: x.scheduled_date)
        receivables_sorted = sorted(receivables, key=lambda x: x.scheduled_date)
        
        recommendations = []
        
        # Simple optimization: delay payments when possible, accelerate receivables
        for payable in payables_sorted:
            if payable.terms in [PaymentTerms.NET_60, PaymentTerms.NET_45]:
                # Can potentially delay
                recommendations.append({
                    "payment": payable,
                    "action": "delay",
                    "suggested_date": payable.scheduled_date + timedelta(days=7),
                    "rationale": "Maximize float without penalty"
                })
        
        for receivable in receivables_sorted:
            recommendations.append({
                "payment": receivable,
                "action": "accelerate",
                "suggested_date": receivable.scheduled_date - timedelta(days=3),
                "rationale": "Offer early payment discount to improve cash position"
            })
        
        return {
            "recommendations": recommendations,
            "estimated_improvement": "TBD based on implementation"
        }
