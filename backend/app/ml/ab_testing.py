"""
A/B testing framework for ML models.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import uuid
import random
import hashlib


class ExperimentStatus(Enum):
    """Status of an A/B test experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TrafficAllocation(Enum):
    """Traffic allocation strategy."""
    EQUAL = "equal"
    WEIGHTED = "weighted"
    BANDIT = "bandit"


@dataclass
class Variant:
    """Experiment variant (model version)."""
    variant_id: str
    name: str
    model_name: str
    model_version: str
    traffic_percentage: float
    metrics: Dict[str, float] = field(default_factory=dict)
    sample_count: int = 0
    is_control: bool = False


@dataclass
class Experiment:
    """A/B test experiment definition."""
    experiment_id: str
    name: str
    description: str
    status: ExperimentStatus
    variants: List[Variant]
    primary_metric: str
    secondary_metrics: List[str]
    min_sample_size: int
    max_duration_days: int
    confidence_level: float
    traffic_allocation: TrafficAllocation
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    winner_variant_id: Optional[str] = None


@dataclass
class ExperimentResult:
    """Results of an A/B test."""
    experiment_id: str
    variant_results: Dict[str, Dict[str, Any]]
    statistical_significance: Dict[str, bool]
    confidence_intervals: Dict[str, Dict[str, tuple]]
    recommendation: str
    sample_sizes: Dict[str, int]


class ABTestFramework:
    """Framework for running A/B tests on ML models."""
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        self.assignments: Dict[str, str] = {}  # user_id -> variant_id
        self.events: List[Dict[str, Any]] = []
    
    async def create_experiment(
        self,
        name: str,
        description: str,
        variants: List[Dict[str, Any]],
        primary_metric: str,
        secondary_metrics: Optional[List[str]] = None,
        min_sample_size: int = 1000,
        max_duration_days: int = 30,
        confidence_level: float = 0.95,
        traffic_allocation: TrafficAllocation = TrafficAllocation.EQUAL,
        created_by: str = ""
    ) -> Experiment:
        """Create a new A/B test experiment."""
        
        experiment_id = str(uuid.uuid4())
        
        # Create variants
        variant_objects = []
        total_traffic = sum(v.get("traffic_percentage", 0) for v in variants)
        
        if traffic_allocation == TrafficAllocation.EQUAL:
            equal_percentage = 100.0 / len(variants)
            for i, v in enumerate(variants):
                variant_objects.append(Variant(
                    variant_id=str(uuid.uuid4()),
                    name=v["name"],
                    model_name=v["model_name"],
                    model_version=v["model_version"],
                    traffic_percentage=equal_percentage,
                    is_control=(i == 0)  # First variant is control
                ))
        else:
            for v in variants:
                variant_objects.append(Variant(
                    variant_id=str(uuid.uuid4()),
                    name=v["name"],
                    model_name=v["model_name"],
                    model_version=v["model_version"],
                    traffic_percentage=v.get("traffic_percentage", 100.0 / len(variants))
                ))
        
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            status=ExperimentStatus.DRAFT,
            variants=variant_objects,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics or [],
            min_sample_size=min_sample_size,
            max_duration_days=max_duration_days,
            confidence_level=confidence_level,
            traffic_allocation=traffic_allocation,
            created_by=created_by
        )
        
        self.experiments[experiment_id] = experiment
        
        return experiment
    
    async def start_experiment(self, experiment_id: str) -> Experiment:
        """Start a running experiment."""
        
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if experiment.status != ExperimentStatus.DRAFT:
            raise ValueError(f"Cannot start experiment in {experiment.status.value} status")
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.start_time = datetime.utcnow()
        experiment.end_time = experiment.start_time + timedelta(
            days=experiment.max_duration_days
        )
        
        return experiment
    
    async def assign_variant(
        self,
        experiment_id: str,
        user_id: str
    ) -> Optional[Variant]:
        """Assign a user to a variant."""
        
        experiment = self.experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # Check if already assigned
        if user_id in self.assignments:
            variant_id = self.assignments[user_id]
            for v in experiment.variants:
                if v.variant_id == variant_id:
                    return v
        
        # Assign based on traffic allocation
        if experiment.traffic_allocation == TrafficAllocation.BANDIT:
            # Multi-armed bandit allocation
            variant = self._bandit_allocation(experiment)
        else:
            # Weighted random allocation
            variant = self._weighted_allocation(experiment, user_id)
        
        if variant:
            self.assignments[user_id] = variant.variant_id
            variant.sample_count += 1
        
        return variant
    
    def _weighted_allocation(
        self,
        experiment: Experiment,
        user_id: str
    ) -> Optional[Variant]:
        """Assign variant using weighted random allocation."""
        
        # Use hash for consistent assignment
        hash_input = f"{experiment.experiment_id}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # Normalize to 0-100
        random_value = (hash_value % 10000) / 100.0
        
        cumulative = 0.0
        for variant in experiment.variants:
            cumulative += variant.traffic_percentage
            if random_value <= cumulative:
                return variant
        
        return experiment.variants[-1] if experiment.variants else None
    
    def _bandit_allocation(self, experiment: Experiment) -> Optional[Variant]:
        """Assign variant using epsilon-greedy bandit algorithm."""
        
        epsilon = 0.1  # Exploration rate
        
        # Explore: random selection
        if random.random() < epsilon:
            return random.choice(experiment.variants)
        
        # Exploit: select best performing variant
        best_variant = None
        best_score = float('-inf')
        
        for variant in experiment.variants:
            if variant.sample_count > 0:
                score = variant.metrics.get(experiment.primary_metric, 0)
                if score > best_score:
                    best_score = score
                    best_variant = variant
        
        return best_variant or random.choice(experiment.variants)
    
    async def record_event(
        self,
        experiment_id: str,
        user_id: str,
        event_type: str,
        metrics: Dict[str, float]
    ) -> bool:
        """Record an event for analysis."""
        
        experiment = self.experiments.get(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return False
        
        variant_id = self.assignments.get(user_id)
        if not variant_id:
            return False
        
        # Record event
        self.events.append({
            "experiment_id": experiment_id,
            "variant_id": variant_id,
            "user_id": user_id,
            "event_type": event_type,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Update variant metrics
        for variant in experiment.variants:
            if variant.variant_id == variant_id:
                for metric, value in metrics.items():
                    # Simple running average
                    if metric in variant.metrics:
                        n = variant.sample_count
                        variant.metrics[metric] = (
                            (variant.metrics[metric] * (n - 1) + value) / n
                        )
                    else:
                        variant.metrics[metric] = value
        
        return True
    
    async def analyze_results(
        self,
        experiment_id: str
    ) -> ExperimentResult:
        """Analyze experiment results."""
        
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Calculate variant results
        variant_results = {}
        sample_sizes = {}
        
        for variant in experiment.variants:
            variant_events = [
                e for e in self.events
                if e["experiment_id"] == experiment_id
                and e["variant_id"] == variant.variant_id
            ]
            
            sample_sizes[variant.variant_id] = len(variant_events)
            
            # Calculate metrics
            metrics = {}
            for event in variant_events:
                for metric, value in event["metrics"].items():
                    if metric not in metrics:
                        metrics[metric] = []
                    metrics[metric].append(value)
            
            variant_results[variant.variant_id] = {
                "name": variant.name,
                "is_control": variant.is_control,
                "sample_size": len(variant_events),
                "metrics": {
                    m: {
                        "mean": sum(v) / len(v) if v else 0,
                        "count": len(v)
                    }
                    for m, v in metrics.items()
                }
            }
        
        # Calculate statistical significance (placeholder)
        statistical_significance = {}
        confidence_intervals = {}
        
        for metric in [experiment.primary_metric] + experiment.secondary_metrics:
            # Placeholder for actual statistical test
            statistical_significance[metric] = False
            confidence_intervals[metric] = {}
            
            for variant_id in variant_results:
                confidence_intervals[metric][variant_id] = (0, 0)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            experiment, variant_results, statistical_significance
        )
        
        return ExperimentResult(
            experiment_id=experiment_id,
            variant_results=variant_results,
            statistical_significance=statistical_significance,
            confidence_intervals=confidence_intervals,
            recommendation=recommendation,
            sample_sizes=sample_sizes
        )
    
    def _generate_recommendation(
        self,
        experiment: Experiment,
        variant_results: Dict[str, Any],
        significance: Dict[str, bool]
    ) -> str:
        """Generate recommendation based on results."""
        
        primary = experiment.primary_metric
        
        # Find best performing variant
        best_variant = None
        best_score = float('-inf')
        
        for variant_id, results in variant_results.items():
            score = results["metrics"].get(primary, {}).get("mean", 0)
            if score > best_score:
                best_score = score
                best_variant = variant_id
        
        if not best_variant:
            return "Insufficient data for recommendation"
        
        # Check if significant
        if significance.get(primary, False):
            variant_name = variant_results[best_variant]["name"]
            return f"Variant '{variant_name}' shows statistically significant improvement. Recommend rollout."
        else:
            return "Results not statistically significant. Continue experiment or consider larger sample size."
    
    async def complete_experiment(
        self,
        experiment_id: str,
        winner_variant_id: Optional[str] = None
    ) -> Experiment:
        """Complete an experiment."""
        
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_time = datetime.utcnow()
        experiment.winner_variant_id = winner_variant_id
        
        return experiment
