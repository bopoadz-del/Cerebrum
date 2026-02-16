"""
A/B Testing Framework for Prompts

Statistical comparison and traffic splitting for prompt optimization.
"""
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExperimentStatus(str, Enum):
    """Status of an A/B test experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Experiment:
    """Represents an A/B testing experiment."""
    id: str
    name: str
    description: str
    prompt_id_a: str  # Control
    prompt_id_b: str  # Variant
    status: ExperimentStatus
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    traffic_split: float  # Percentage to variant (0-100)
    min_sample_size: int
    success_metric: str  # e.g., "syntax_success_rate"
    created_by: str
    created_at: datetime


@dataclass
class ExperimentResult:
    """Results of an A/B test experiment."""
    experiment_id: str
    prompt_a_uses: int
    prompt_b_uses: int
    prompt_a_success_rate: float
    prompt_b_success_rate: float
    improvement_percentage: float
    statistical_significance: float  # p-value
    winner: Optional[str]  # "a", "b", or None (no significant difference)
    recommendation: str


class ABTestFramework:
    """
    A/B testing framework for prompt optimization.
    
    Features:
    - Traffic splitting
    - Statistical significance calculation
    - Automatic winner selection
    - Experiment management
    """
    
    def __init__(self):
        self._experiments: Dict[str, Experiment] = {}
        self._assignments: Dict[str, str] = {}  # user/session -> prompt_id
        self._results: Dict[str, Dict[str, Any]] = {}
    
    def create_experiment(
        self,
        name: str,
        description: str,
        prompt_id_a: str,
        prompt_id_b: str,
        traffic_split: float = 50.0,
        min_sample_size: int = 100,
        success_metric: str = "syntax_success_rate",
        created_by: str = "system"
    ) -> str:
        """
        Create a new A/B testing experiment.
        
        Args:
            name: Experiment name
            description: Experiment description
            prompt_id_a: Control prompt ID
            prompt_id_b: Variant prompt ID
            traffic_split: Percentage of traffic to variant (0-100)
            min_sample_size: Minimum samples before declaring winner
            success_metric: Metric to optimize for
            created_by: Who created the experiment
        
        Returns:
            Experiment ID
        """
        import uuid
        
        experiment_id = str(uuid.uuid4())
        
        experiment = Experiment(
            id=experiment_id,
            name=name,
            description=description,
            prompt_id_a=prompt_id_a,
            prompt_id_b=prompt_id_b,
            status=ExperimentStatus.DRAFT,
            start_date=None,
            end_date=None,
            traffic_split=traffic_split,
            min_sample_size=min_sample_size,
            success_metric=success_metric,
            created_by=created_by,
            created_at=datetime.utcnow()
        )
        
        self._experiments[experiment_id] = experiment
        self._results[experiment_id] = {
            "a": {"uses": 0, "successes": 0},
            "b": {"uses": 0, "successes": 0}
        }
        
        logger.info(f"Created experiment {experiment_id}: {name}")
        return experiment_id
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            logger.error(f"Experiment {experiment_id} not found")
            return False
        
        if experiment.status != ExperimentStatus.DRAFT:
            logger.error(f"Experiment {experiment_id} is not in draft status")
            return False
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.start_date = datetime.utcnow()
        
        logger.info(f"Started experiment {experiment_id}")
        return True
    
    def stop_experiment(self, experiment_id: str) -> bool:
        """Stop an experiment."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False
        
        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_date = datetime.utcnow()
        
        logger.info(f"Stopped experiment {experiment_id}")
        return True
    
    def get_prompt_for_request(
        self,
        experiment_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Determine which prompt to use for a request.
        
        Args:
            experiment_id: Experiment ID
            user_id: Optional user ID for consistent assignment
            session_id: Optional session ID for consistent assignment
        
        Returns:
            Prompt ID to use
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            # Return control if experiment not running
            return experiment.prompt_id_a if experiment else ""
        
        # Check for existing assignment
        assignment_key = user_id or session_id or str(random.random())
        
        if assignment_key in self._assignments:
            assigned_prompt = self._assignments[assignment_key]
            # Verify it's part of this experiment
            if assigned_prompt in [experiment.prompt_id_a, experiment.prompt_id_b]:
                return assigned_prompt
        
        # New assignment
        roll = random.random() * 100
        if roll < experiment.traffic_split:
            prompt_id = experiment.prompt_id_b
        else:
            prompt_id = experiment.prompt_id_a
        
        self._assignments[assignment_key] = prompt_id
        
        # Track assignment
        variant = "b" if prompt_id == experiment.prompt_id_b else "a"
        self._results[experiment_id][variant]["uses"] += 1
        
        return prompt_id
    
    def record_result(
        self,
        experiment_id: str,
        prompt_id: str,
        success: bool,
        metrics: Dict[str, Any] = None
    ):
        """Record the result of using a prompt."""
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return
        
        variant = "b" if prompt_id == experiment.prompt_id_b else "a"
        
        if success:
            self._results[experiment_id][variant]["successes"] += 1
        
        # Store additional metrics
        if metrics:
            if "metrics" not in self._results[experiment_id][variant]:
                self._results[experiment_id][variant]["metrics"] = []
            self._results[experiment_id][variant]["metrics"].append(metrics)
    
    def analyze_experiment(self, experiment_id: str) -> Optional[ExperimentResult]:
        """
        Analyze experiment results and determine winner.
        
        Returns:
            ExperimentResult with analysis
        """
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return None
        
        results = self._results.get(experiment_id, {})
        
        a_uses = results["a"]["uses"]
        a_successes = results["a"]["successes"]
        b_uses = results["b"]["uses"]
        b_successes = results["b"]["successes"]
        
        # Calculate success rates
        a_rate = a_successes / a_uses if a_uses > 0 else 0
        b_rate = b_successes / b_uses if b_uses > 0 else 0
        
        # Calculate improvement
        improvement = ((b_rate - a_rate) / a_rate * 100) if a_rate > 0 else 0
        
        # Calculate statistical significance (simplified)
        p_value = self._calculate_p_value(
            a_successes, a_uses,
            b_successes, b_uses
        )
        
        # Determine winner
        winner = None
        if p_value < 0.05:  # 95% confidence
            if b_rate > a_rate:
                winner = "b"
            elif a_rate > b_rate:
                winner = "a"
        
        # Build recommendation
        if winner == "b":
            recommendation = f"Variant B shows {improvement:.1f}% improvement. Consider promoting to control."
        elif winner == "a":
            recommendation = "Control performs better. Keep current prompt."
        else:
            if a_uses + b_uses < experiment.min_sample_size:
                recommendation = f"Need more data. Current sample: {a_uses + b_uses}/{experiment.min_sample_size}"
            else:
                recommendation = "No statistically significant difference detected."
        
        return ExperimentResult(
            experiment_id=experiment_id,
            prompt_a_uses=a_uses,
            prompt_b_uses=b_uses,
            prompt_a_success_rate=a_rate,
            prompt_b_success_rate=b_rate,
            improvement_percentage=improvement,
            statistical_significance=p_value,
            winner=winner,
            recommendation=recommendation
        )
    
    def _calculate_p_value(
        self,
        a_successes: int,
        a_total: int,
        b_successes: int,
        b_total: int
    ) -> float:
        """
        Calculate p-value using two-proportion z-test.
        
        Returns:
            p-value (lower = more significant)
        """
        try:
            from scipy import stats
            
            # Two-proportion z-test
            count = [a_successes, b_successes]
            nobs = [a_total, b_total]
            
            z_stat, p_value = stats.proportions_ztest(count, nobs)
            
            return p_value
        except ImportError:
            # Fallback: simple approximation
            # This is not statistically rigorous but provides a rough estimate
            p1 = a_successes / a_total if a_total > 0 else 0
            p2 = b_successes / b_total if b_total > 0 else 0
            
            # Pooled proportion
            p = (a_successes + b_successes) / (a_total + b_total)
            
            # Standard error
            se = (p * (1 - p) * (1/a_total + 1/b_total)) ** 0.5
            
            # Z-score
            z = (p2 - p1) / se if se > 0 else 0
            
            # Approximate p-value (two-tailed)
            import math
            p_value = 2 * (1 - self._normal_cdf(abs(z)))
            
            return p_value
    
    def _normal_cdf(self, x: float) -> float:
        """Approximation of normal CDF."""
        import math
        # Abramowitz and Stegun approximation
        b1 = 0.319381530
        b2 = -0.356563782
        b3 = 1.781477937
        b4 = -1.821255978
        b5 = 1.330274429
        p = 0.2316419
        c = 0.39894228
        
        if x >= 0.0:
            t = 1.0 / (1.0 + p * x)
            return 1.0 - c * math.exp(-x * x / 2.0) * t * (t * (t * (t * (t * b5 + b4) + b3) + b2) + b1)
        else:
            return 1.0 - self._normal_cdf(-x)
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        return self._experiments.get(experiment_id)
    
    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None
    ) -> List[Experiment]:
        """List experiments with optional filtering."""
        experiments = list(self._experiments.values())
        
        if status:
            experiments = [e for e in experiments if e.status == status]
        
        return sorted(experiments, key=lambda e: e.created_at, reverse=True)
    
    def auto_promote_winner(self, experiment_id: str) -> bool:
        """
        Automatically promote the winning prompt to control.
        
        Returns:
            True if promotion occurred
        """
        result = self.analyze_experiment(experiment_id)
        if not result or not result.winner:
            return False
        
        experiment = self._experiments.get(experiment_id)
        if not experiment:
            return False
        
        # Check minimum sample size
        total_uses = result.prompt_a_uses + result.prompt_b_uses
        if total_uses < experiment.min_sample_size:
            logger.info(f"Not enough samples for auto-promotion: {total_uses}/{experiment.min_sample_size}")
            return False
        
        # Promote winner
        if result.winner == "b":
            logger.info(f"Promoting variant B to control for experiment {experiment_id}")
            # This would update the prompt registry
            return True
        
        return False


class PromptOptimizer:
    """Optimizes prompts based on performance metrics."""
    
    def __init__(self, ab_framework: ABTestFramework):
        self.ab_framework = ab_framework
    
    def suggest_improvements(self, prompt_id: str, metrics: Dict[str, float]) -> List[str]:
        """
        Suggest prompt improvements based on metrics.
        
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check syntax success rate
        if metrics.get("syntax_success_rate", 1.0) < 0.9:
            suggestions.append("Add more explicit syntax examples to few-shot prompts")
        
        # Check security pass rate
        if metrics.get("security_pass_rate", 1.0) < 0.95:
            suggestions.append("Add security guidelines to system prompt")
        
        # Check test pass rate
        if metrics.get("test_pass_rate", 1.0) < 0.8:
            suggestions.append("Add more comprehensive test examples")
        
        # Check response time
        if metrics.get("avg_response_time_ms", 0) > 5000:
            suggestions.append("Consider reducing max_tokens or simplifying prompt")
        
        return suggestions
    
    def generate_variant(
        self,
        base_prompt_id: str,
        improvement: str
    ) -> Dict[str, Any]:
        """
        Generate a prompt variant with an improvement.
        
        Returns:
            Variant prompt data
        """
        # This would use GPT-4 to generate an improved variant
        return {
            "parent_prompt_id": base_prompt_id,
            "improvement": improvement,
            "variant_type": "optimized"
        }
