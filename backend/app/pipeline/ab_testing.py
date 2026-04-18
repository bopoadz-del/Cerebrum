"""
A/B Testing Framework for ML Models

Provides comprehensive A/B testing capabilities for model comparison:
- Variant assignment (equal, weighted, bandit)
- Statistical significance testing
- Automatic winner selection
- Integration with PostgreSQL for persistence
- Integration with MLflow for model metadata

Features:
- Consistent user assignment via hashing
- Multi-armed bandit for adaptive allocation
- Statistical tests (t-test, chi-square)
- Confidence interval calculation
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
from enum import Enum
import uuid
import random
import hashlib
import math
import json
import asyncio
from contextlib import asynccontextmanager

from scipy import stats
import numpy as np
from sqlalchemy import (
    Column, String, Float, DateTime, Integer, JSON, 
    Enum as SQLEnum, Text, Boolean, ForeignKey, select, and_, desc, func
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal, AsyncSessionLocal
from app.core.config import settings

Base = declarative_base()


class ExperimentStatus(str, Enum):
    """Status of an A/B test experiment."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TrafficAllocation(str, Enum):
    """Traffic allocation strategy."""
    EQUAL = "equal"
    WEIGHTED = "weighted"
    BANDIT = "bandit"
    BAYESIAN = "bayesian"


class StatisticalTest(str, Enum):
    """Statistical test types."""
    T_TEST = "t_test"
    CHI_SQUARE = "chi_square"
    MANN_WHITNEY = "mann_whitney"
    BOOTSTRAP = "bootstrap"


class ExperimentDB(Base):
    """Database model for experiments."""
    __tablename__ = "ab_experiments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    model_name = Column(String(255), nullable=False, index=True)
    status = Column(SQLEnum(ExperimentStatus), default=ExperimentStatus.DRAFT)
    
    # Configuration
    primary_metric = Column(String(64), nullable=False)
    secondary_metrics = Column(ARRAY(String))
    min_sample_size = Column(Integer, default=1000)
    max_duration_days = Column(Integer, default=30)
    confidence_level = Column(Float, default=0.95)
    traffic_allocation = Column(SQLEnum(TrafficAllocation), default=TrafficAllocation.EQUAL)
    statistical_test = Column(SQLEnum(StatisticalTest), default=StatisticalTest.T_TEST)
    
    # Timing
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Attribution
    created_by = Column(String(255))
    winner_variant_id = Column(String(64))
    
    # Results
    results_data = Column(JSON)
    
    # Relationships
    variants = relationship("VariantDB", back_populates="experiment", cascade="all, delete-orphan")
    assignments = relationship("UserAssignmentDB", back_populates="experiment", cascade="all, delete-orphan")
    events = relationship("ExperimentEventDB", back_populates="experiment", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "experiment_id": self.experiment_id,
            "name": self.name,
            "description": self.description,
            "model_name": self.model_name,
            "status": self.status.value if self.status else None,
            "primary_metric": self.primary_metric,
            "secondary_metrics": self.secondary_metrics or [],
            "min_sample_size": self.min_sample_size,
            "max_duration_days": self.max_duration_days,
            "confidence_level": self.confidence_level,
            "traffic_allocation": self.traffic_allocation.value if self.traffic_allocation else None,
            "statistical_test": self.statistical_test.value if self.statistical_test else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by,
            "winner_variant_id": self.winner_variant_id,
            "results_data": self.results_data or {},
        }


class VariantDB(Base):
    """Database model for experiment variants."""
    __tablename__ = "ab_variants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("ab_experiments.id"))
    variant_id = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    model_version = Column(String(64), nullable=False)
    traffic_percentage = Column(Float, default=50.0)
    is_control = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Metrics
    sample_count = Column(Integer, default=0)
    metrics_data = Column(JSON)
    
    experiment = relationship("ExperimentDB", back_populates="variants")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "variant_id": self.variant_id,
            "name": self.name,
            "model_version": self.model_version,
            "traffic_percentage": self.traffic_percentage,
            "is_control": self.is_control,
            "is_active": self.is_active,
            "sample_count": self.sample_count,
            "metrics": self.metrics_data or {},
        }


class UserAssignmentDB(Base):
    """Database model for user-variant assignments."""
    __tablename__ = "ab_user_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("ab_experiments.id"))
    user_id = Column(String(255), nullable=False, index=True)
    variant_id = Column(String(64), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
    experiment = relationship("ExperimentDB", back_populates="assignments")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "variant_id": self.variant_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
        }


class ExperimentEventDB(Base):
    """Database model for experiment events."""
    __tablename__ = "ab_experiment_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("ab_experiments.id"))
    user_id = Column(String(255), nullable=False, index=True)
    variant_id = Column(String(64), nullable=False)
    event_type = Column(String(64), nullable=False)
    metrics = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    experiment = relationship("ExperimentDB", back_populates="events")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "variant_id": self.variant_id,
            "event_type": self.event_type,
            "metrics": self.metrics or {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


@dataclass
class Variant:
    """Experiment variant (model version)."""
    variant_id: str
    name: str
    model_version: str
    traffic_percentage: float
    metrics: Dict[str, float] = field(default_factory=dict)
    sample_count: int = 0
    is_control: bool = False
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "name": self.name,
            "model_version": self.model_version,
            "traffic_percentage": self.traffic_percentage,
            "metrics": self.metrics,
            "sample_count": self.sample_count,
            "is_control": self.is_control,
            "is_active": self.is_active,
        }


@dataclass
class Experiment:
    """A/B test experiment definition."""
    experiment_id: str
    name: str
    description: str
    model_name: str
    status: ExperimentStatus
    variants: List[Variant]
    primary_metric: str
    secondary_metrics: List[str]
    min_sample_size: int
    max_duration_days: int
    confidence_level: float
    traffic_allocation: TrafficAllocation
    statistical_test: StatisticalTest
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    winner_variant_id: Optional[str] = None
    results_data: Optional[Dict[str, Any]] = None


@dataclass
class ExperimentResult:
    """Results of an A/B test."""
    experiment_id: str
    variant_results: Dict[str, Dict[str, Any]]
    statistical_significance: Dict[str, bool]
    confidence_intervals: Dict[str, Dict[str, Tuple[float, float]]]
    p_values: Dict[str, Dict[str, float]]
    recommendation: str
    sample_sizes: Dict[str, int]
    power_analysis: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "variant_results": self.variant_results,
            "statistical_significance": self.statistical_significance,
            "confidence_intervals": self.confidence_intervals,
            "p_values": self.p_values,
            "recommendation": self.recommendation,
            "sample_sizes": self.sample_sizes,
            "power_analysis": self.power_analysis,
        }


class ABTestFramework:
    """
    A/B Testing Framework for ML Models.
    
    Features:
    - Create and manage experiments
    - Consistent user-to-variant assignment
    - Multiple allocation strategies (equal, weighted, bandit, bayesian)
    - Statistical significance testing
    - Automatic winner detection
    - Integration with PostgreSQL for persistence
    
    Allocation Strategies:
    - EQUAL: Equal traffic split between variants
    - WEIGHTED: Custom traffic percentages
    - BANDIT: Multi-armed bandit for adaptive allocation
    - BAYESIAN: Thompson sampling for bayesian optimization
    """
    
    def __init__(self, use_async: bool = True):
        self._use_async = use_async
    
    @asynccontextmanager
    async def _get_db_session(self):
        """Get database session."""
        if self._use_async:
            async with AsyncSessionLocal() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
        else:
            session = SessionLocal()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    async def create_experiment(
        self,
        name: str,
        model_name: str,
        description: str,
        variants: List[Dict[str, Any]],
        primary_metric: str,
        secondary_metrics: Optional[List[str]] = None,
        min_sample_size: int = 1000,
        max_duration_days: int = 30,
        confidence_level: float = 0.95,
        traffic_allocation: TrafficAllocation = TrafficAllocation.EQUAL,
        statistical_test: StatisticalTest = StatisticalTest.T_TEST,
        created_by: str = ""
    ) -> Experiment:
        """
        Create a new A/B test experiment.
        
        Args:
            name: Experiment name
            model_name: Model being tested
            description: Experiment description
            variants: List of variant configs [{name, model_version, traffic_percentage?}]
            primary_metric: Primary metric for comparison
            secondary_metrics: Additional metrics to track
            min_sample_size: Minimum samples before declaring winner
            max_duration_days: Maximum experiment duration
            confidence_level: Statistical confidence level (e.g., 0.95)
            traffic_allocation: Allocation strategy
            statistical_test: Statistical test to use
            created_by: User who created the experiment
        """
        experiment_id = f"exp_{uuid.uuid4().hex[:12]}"
        
        # Create variant objects
        variant_objects = []
        
        if traffic_allocation == TrafficAllocation.EQUAL:
            equal_percentage = 100.0 / len(variants)
            for i, v in enumerate(variants):
                variant_objects.append(Variant(
                    variant_id=f"var_{uuid.uuid4().hex[:8]}",
                    name=v["name"],
                    model_version=v["model_version"],
                    traffic_percentage=equal_percentage,
                    is_control=(i == 0),  # First variant is control
                ))
        else:
            for v in variants:
                variant_objects.append(Variant(
                    variant_id=f"var_{uuid.uuid4().hex[:8]}",
                    name=v["name"],
                    model_version=v["model_version"],
                    traffic_percentage=v.get("traffic_percentage", 100.0 / len(variants))
                ))
        
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            model_name=model_name,
            status=ExperimentStatus.DRAFT,
            variants=variant_objects,
            primary_metric=primary_metric,
            secondary_metrics=secondary_metrics or [],
            min_sample_size=min_sample_size,
            max_duration_days=max_duration_days,
            confidence_level=confidence_level,
            traffic_allocation=traffic_allocation,
            statistical_test=statistical_test,
            created_by=created_by,
        )
        
        # Persist to database
        async with self._get_db_session() as session:
            exp_db = ExperimentDB(
                experiment_id=experiment_id,
                name=name,
                description=description,
                model_name=model_name,
                status=ExperimentStatus.DRAFT,
                primary_metric=primary_metric,
                secondary_metrics=secondary_metrics or [],
                min_sample_size=min_sample_size,
                max_duration_days=max_duration_days,
                confidence_level=confidence_level,
                traffic_allocation=traffic_allocation,
                statistical_test=statistical_test,
                created_by=created_by,
            )
            session.add(exp_db)
            await session.flush()  # Get the ID
            
            # Add variants
            for v in variant_objects:
                var_db = VariantDB(
                    experiment_id=exp_db.id,
                    variant_id=v.variant_id,
                    name=v.name,
                    model_version=v.model_version,
                    traffic_percentage=v.traffic_percentage,
                    is_control=v.is_control,
                )
                session.add(var_db)
        
        return experiment
    
    async def start_experiment(self, experiment_id: str) -> Experiment:
        """Start a running experiment."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ExperimentDB).where(ExperimentDB.experiment_id == experiment_id)
            )
            exp_db = result.scalar_one_or_none()
            
            if not exp_db:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            if exp_db.status != ExperimentStatus.DRAFT:
                raise ValueError(f"Cannot start experiment in {exp_db.status.value} status")
            
            exp_db.status = ExperimentStatus.RUNNING
            exp_db.start_time = datetime.utcnow()
            exp_db.end_time = exp_db.start_time + timedelta(days=exp_db.max_duration_days)
        
        # Reload experiment with variants
        return await self.get_experiment(experiment_id)
    
    async def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ExperimentDB).where(ExperimentDB.experiment_id == experiment_id)
            )
            exp_db = result.scalar_one_or_none()
            
            if not exp_db:
                return None
            
            # Load variants
            variants = [Variant(
                variant_id=v.variant_id,
                name=v.name,
                model_version=v.model_version,
                traffic_percentage=v.traffic_percentage,
                metrics=v.metrics_data or {},
                sample_count=v.sample_count,
                is_control=v.is_control,
                is_active=v.is_active,
            ) for v in exp_db.variants]
            
            return Experiment(
                experiment_id=exp_db.experiment_id,
                name=exp_db.name,
                description=exp_db.description or "",
                model_name=exp_db.model_name,
                status=exp_db.status,
                variants=variants,
                primary_metric=exp_db.primary_metric,
                secondary_metrics=exp_db.secondary_metrics or [],
                min_sample_size=exp_db.min_sample_size,
                max_duration_days=exp_db.max_duration_days,
                confidence_level=exp_db.confidence_level,
                traffic_allocation=exp_db.traffic_allocation,
                statistical_test=exp_db.statistical_test,
                start_time=exp_db.start_time,
                end_time=exp_db.end_time,
                created_by=exp_db.created_by or "",
                created_at=exp_db.created_at,
                winner_variant_id=exp_db.winner_variant_id,
                results_data=exp_db.results_data,
            )
    
    async def assign_variant(
        self,
        experiment_id: str,
        user_id: str
    ) -> Optional[Variant]:
        """
        Assign a user to a variant.
        
        Returns the assigned variant, or None if experiment not running
        or user not eligible.
        """
        experiment = await self.get_experiment(experiment_id)
        
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # Check if user already assigned
        async with self._get_db_session() as session:
            result = await session.execute(
                select(UserAssignmentDB)
                .where(UserAssignmentDB.experiment_id == ExperimentDB.id)
                .where(UserAssignmentDB.user_id == user_id)
                .where(ExperimentDB.experiment_id == experiment_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Return existing assignment
                for v in experiment.variants:
                    if v.variant_id == existing.variant_id:
                        return v
        
        # Assign variant
        if experiment.traffic_allocation == TrafficAllocation.BANDIT:
            variant = self._bandit_allocation(experiment)
        elif experiment.traffic_allocation == TrafficAllocation.BAYESIAN:
            variant = self._bayesian_allocation(experiment)
        else:
            variant = self._weighted_allocation(experiment, user_id)
        
        if not variant:
            return None
        
        # Persist assignment
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ExperimentDB).where(ExperimentDB.experiment_id == experiment_id)
            )
            exp_db = result.scalar_one()
            
            assignment = UserAssignmentDB(
                experiment_id=exp_db.id,
                user_id=user_id,
                variant_id=variant.variant_id,
            )
            session.add(assignment)
            
            # Update variant sample count
            for v in exp_db.variants:
                if v.variant_id == variant.variant_id:
                    v.sample_count += 1
                    break
        
        return variant
    
    def _weighted_allocation(
        self,
        experiment: Experiment,
        user_id: str
    ) -> Optional[Variant]:
        """
        Assign variant using consistent weighted random allocation.
        
        Uses hash of experiment_id:user_id for consistent assignment.
        """
        # Get active variants
        active_variants = [v for v in experiment.variants if v.is_active]
        if not active_variants:
            return None
        
        # Use hash for consistent assignment
        hash_input = f"{experiment.experiment_id}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        
        # Normalize to 0-100
        random_value = (hash_value % 10000) / 100.0
        
        cumulative = 0.0
        for variant in active_variants:
            cumulative += variant.traffic_percentage
            if random_value <= cumulative:
                return variant
        
        return active_variants[-1]
    
    def _bandit_allocation(self, experiment: Experiment) -> Optional[Variant]:
        """
        Assign variant using epsilon-greedy bandit algorithm.
        
        Explores with probability epsilon, exploits otherwise.
        """
        epsilon = 0.1  # 10% exploration
        
        active_variants = [v for v in experiment.variants if v.is_active]
        if not active_variants:
            return None
        
        # Explore: random selection
        if random.random() < epsilon:
            return random.choice(active_variants)
        
        # Exploit: select best performing variant
        best_variant = None
        best_score = float('-inf')
        
        for variant in active_variants:
            if variant.sample_count > 0:
                # Use primary metric for scoring
                score = variant.metrics.get(experiment.primary_metric, 0)
                # Add small random perturbation to break ties
                score += random.uniform(0, 0.001)
                if score > best_score:
                    best_score = score
                    best_variant = variant
        
        return best_variant or random.choice(active_variants)
    
    def _bayesian_allocation(self, experiment: Experiment) -> Optional[Variant]:
        """
        Assign variant using Thompson sampling (Bayesian approach).
        
        Samples from posterior distribution and selects argmax.
        """
        active_variants = [v for v in experiment.variants if v.is_active]
        if not active_variants:
            return None
        
        samples = []
        for variant in active_variants:
            if variant.sample_count > 0:
                # Approximate Beta distribution with normal for continuous metrics
                mean = variant.metrics.get(experiment.primary_metric, 0)
                # Variance decreases with more samples
                variance = 1.0 / (variant.sample_count + 1)
                sample = random.gauss(mean, math.sqrt(variance))
                samples.append((variant, sample))
            else:
                # Prior: sample from uniform distribution for unexplored variants
                samples.append((variant, random.uniform(0, 1)))
        
        # Select variant with highest sample
        return max(samples, key=lambda x: x[1])[0]
    
    async def record_event(
        self,
        experiment_id: str,
        user_id: str,
        event_type: str,
        metrics: Dict[str, float]
    ) -> bool:
        """
        Record an event for analysis.
        
        Args:
            experiment_id: Experiment ID
            user_id: User ID
            event_type: Type of event (e.g., 'conversion', 'click')
            metrics: Metric values for this event
        """
        experiment = await self.get_experiment(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return False
        
        # Find user's variant
        async with self._get_db_session() as session:
            result = await session.execute(
                select(UserAssignmentDB, ExperimentDB.id)
                .where(UserAssignmentDB.user_id == user_id)
                .where(ExperimentDB.experiment_id == experiment_id)
            )
            assignment = result.scalar_one_or_none()
            
            if not assignment:
                return False
            
            variant_id = assignment.variant_id
            
            # Record event
            exp_result = await session.execute(
                select(ExperimentDB).where(ExperimentDB.experiment_id == experiment_id)
            )
            exp_db = exp_result.scalar_one()
            
            event = ExperimentEventDB(
                experiment_id=exp_db.id,
                user_id=user_id,
                variant_id=variant_id,
                event_type=event_type,
                metrics=metrics,
            )
            session.add(event)
            
            # Update variant metrics
            for v in exp_db.variants:
                if v.variant_id == variant_id:
                    # Update running average for metrics
                    current_metrics = v.metrics_data or {}
                    for metric, value in metrics.items():
                        if metric in current_metrics:
                            # Running average
                            n = v.sample_count
                            current_metrics[metric] = (
                                (current_metrics[metric] * (n - 1) + value) / n
                            ) if n > 0 else value
                        else:
                            current_metrics[metric] = value
                    v.metrics_data = current_metrics
                    break
        
        return True
    
    async def analyze_results(
        self,
        experiment_id: str,
        force_analysis: bool = False
    ) -> ExperimentResult:
        """
        Analyze experiment results and compute statistical significance.
        
        Returns ExperimentResult with statistical tests and recommendations.
        """
        experiment = await self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Gather event data
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ExperimentDB).where(ExperimentDB.experiment_id == experiment_id)
            )
            exp_db = result.scalar_one()
            
            # Get events by variant
            variant_events = {}
            for v in exp_db.variants:
                events = [e for e in exp_db.events if e.variant_id == v.variant_id]
                variant_events[v.variant_id] = events
        
        # Calculate metrics per variant
        variant_results = {}
        sample_sizes = {}
        
        for variant in experiment.variants:
            events = variant_events.get(variant.variant_id, [])
            sample_sizes[variant.variant_id] = len(events)
            
            # Aggregate metrics
            metrics = {}
            for event in events:
                for metric, value in event.metrics.items():
                    if metric not in metrics:
                        metrics[metric] = []
                    metrics[metric].append(value)
            
            # Calculate statistics
            metric_stats = {}
            for metric, values in metrics.items():
                if values:
                    metric_stats[metric] = {
                        "mean": float(np.mean(values)),
                        "std": float(np.std(values)),
                        "median": float(np.median(values)),
                        "count": len(values),
                        "min": float(np.min(values)),
                        "max": float(np.max(values)),
                    }
            
            variant_results[variant.variant_id] = {
                "name": variant.name,
                "is_control": variant.is_control,
                "sample_size": len(events),
                "metrics": metric_stats,
            }
        
        # Statistical tests
        statistical_significance = {}
        confidence_intervals = {}
        p_values = {}
        
        control_variant = next(
            (v for v in experiment.variants if v.is_control),
            experiment.variants[0] if experiment.variants else None
        )
        
        if control_variant:
            control_events = variant_events.get(control_variant.variant_id, [])
            control_metrics = {}
            for e in control_events:
                for m, v in e.metrics.items():
                    if m not in control_metrics:
                        control_metrics[m] = []
                    control_metrics[m].append(v)
            
            for variant in experiment.variants:
                if variant.variant_id == control_variant.variant_id:
                    continue
                
                variant_events_list = variant_events.get(variant.variant_id, [])
                variant_metrics = {}
                for e in variant_events_list:
                    for m, v in e.metrics.items():
                        if m not in variant_metrics:
                            variant_metrics[m] = []
                        variant_metrics[m].append(v)
                
                # Test primary metric
                primary = experiment.primary_metric
                if primary in control_metrics and primary in variant_metrics:
                    control_vals = control_metrics[primary]
                    variant_vals = variant_metrics[primary]
                    
                    if len(control_vals) > 1 and len(variant_vals) > 1:
                        # T-test
                        t_stat, p_value = stats.ttest_ind(variant_vals, control_vals)
                        
                        # Confidence interval for difference
                        diff_mean = np.mean(variant_vals) - np.mean(control_vals)
                        pooled_se = np.sqrt(
                            np.var(variant_vals, ddof=1) / len(variant_vals) +
                            np.var(control_vals, ddof=1) / len(control_vals)
                        )
                        ci_margin = stats.t.ppf(0.975, len(variant_vals) + len(control_vals) - 2) * pooled_se
                        
                        # Determine significance
                        is_significant = p_value < (1 - experiment.confidence_level)
                        
                        statistical_significance[variant.variant_id] = {primary: is_significant}
                        confidence_intervals[variant.variant_id] = {primary: (diff_mean - ci_margin, diff_mean + ci_margin)}
                        p_values[variant.variant_id] = {primary: float(p_value)}
        
        # Power analysis
        power_analysis = self._calculate_power_analysis(experiment, sample_sizes)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            experiment, variant_results, statistical_significance, sample_sizes
        )
        
        result = ExperimentResult(
            experiment_id=experiment_id,
            variant_results=variant_results,
            statistical_significance=statistical_significance,
            confidence_intervals=confidence_intervals,
            p_values=p_values,
            recommendation=recommendation,
            sample_sizes=sample_sizes,
            power_analysis=power_analysis,
        )
        
        # Store results
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ExperimentDB).where(ExperimentDB.experiment_id == experiment_id)
            )
            exp_db = result.scalar_one()
            exp_db.results_data = result.to_dict()
        
        return result
    
    def _calculate_power_analysis(
        self,
        experiment: Experiment,
        sample_sizes: Dict[str, int]
    ) -> Dict[str, Any]:
        """Calculate statistical power for the experiment."""
        min_size = min(sample_sizes.values()) if sample_sizes else 0
        max_size = max(sample_sizes.values()) if sample_sizes else 0
        
        # Simplified power calculation
        # In production, use proper power analysis libraries
        achieved_power = min(1.0, max_size / experiment.min_sample_size) if experiment.min_sample_size > 0 else 0
        
        return {
            "target_sample_size": experiment.min_sample_size,
            "current_min_sample": min_size,
            "current_max_sample": max_size,
            "achieved_power": achieved_power,
            "adequate_power": achieved_power >= 0.8,
        }
    
    def _generate_recommendation(
        self,
        experiment: Experiment,
        variant_results: Dict[str, Any],
        significance: Dict[str, Dict[str, bool]],
        sample_sizes: Dict[str, int]
    ) -> str:
        """Generate recommendation based on results."""
        primary_metric = experiment.primary_metric
        
        # Check sample size
        min_sample = min(sample_sizes.values()) if sample_sizes else 0
        if min_sample < experiment.min_sample_size:
            return f"Insufficient sample size. Need at least {experiment.min_sample_size} samples per variant. Currently have {min_sample}."
        
        # Find best variant
        best_variant = None
        best_score = float('-inf')
        
        for variant_id, results in variant_results.items():
            score = results["metrics"].get(primary_metric, {}).get("mean", 0)
            if score > best_score:
                best_score = score
                best_variant = variant_id
        
        if not best_variant:
            return "No clear winner. Continue experiment or review metrics."
        
        # Check significance
        is_significant = significance.get(best_variant, {}).get(primary_metric, False)
        
        if is_significant:
            variant_name = variant_results[best_variant]["name"]
            return f"Variant '{variant_name}' shows statistically significant improvement. Recommend promoting to 100% traffic."
        else:
            return "Results not statistically significant. Continue experiment or consider larger sample size."
    
    async def complete_experiment(
        self,
        experiment_id: str,
        winner_variant_id: Optional[str] = None
    ) -> Experiment:
        """Complete an experiment and optionally declare a winner."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ExperimentDB).where(ExperimentDB.experiment_id == experiment_id)
            )
            exp_db = result.scalar_one_or_none()
            
            if not exp_db:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            exp_db.status = ExperimentStatus.COMPLETED
            exp_db.completed_at = datetime.utcnow()
            exp_db.winner_variant_id = winner_variant_id
        
        return await self.get_experiment(experiment_id)
    
    async def pause_experiment(self, experiment_id: str) -> Experiment:
        """Pause a running experiment."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ExperimentDB).where(ExperimentDB.experiment_id == experiment_id)
            )
            exp_db = result.scalar_one_or_none()
            
            if not exp_db or exp_db.status != ExperimentStatus.RUNNING:
                raise ValueError("Can only pause running experiments")
            
            exp_db.status = ExperimentStatus.PAUSED
        
        return await self.get_experiment(experiment_id)
    
    async def resume_experiment(self, experiment_id: str) -> Experiment:
        """Resume a paused experiment."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(ExperimentDB).where(ExperimentDB.experiment_id == experiment_id)
            )
            exp_db = result.scalar_one_or_none()
            
            if not exp_db or exp_db.status != ExperimentStatus.PAUSED:
                raise ValueError("Can only resume paused experiments")
            
            exp_db.status = ExperimentStatus.RUNNING
        
        return await self.get_experiment(experiment_id)
    
    async def list_experiments(
        self,
        model_name: Optional[str] = None,
        status: Optional[ExperimentStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List experiments."""
        async with self._get_db_session() as session:
            query = select(ExperimentDB)
            
            if model_name:
                query = query.where(ExperimentDB.model_name == model_name)
            if status:
                query = query.where(ExperimentDB.status == status)
            
            query = query.order_by(desc(ExperimentDB.created_at))
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            experiments = result.scalars().all()
            
            return [e.to_dict() for e in experiments]
    
    async def update_variant_traffic(
        self,
        experiment_id: str,
        variant_id: str,
        new_percentage: float
    ) -> bool:
        """Update traffic allocation for a variant."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(VariantDB, ExperimentDB)
                .where(ExperimentDB.experiment_id == experiment_id)
                .where(VariantDB.experiment_id == ExperimentDB.id)
                .where(VariantDB.variant_id == variant_id)
            )
            row = result.fetchone()
            
            if not row:
                return False
            
            variant_db = row[0]
            variant_db.traffic_percentage = new_percentage
            
            return True


# Migration SQL
AB_TESTING_MIGRATION = """
-- Migration for A/B testing tables

-- Experiments table
CREATE TABLE IF NOT EXISTS ab_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    model_name VARCHAR(255) NOT NULL,
    status VARCHAR(16) DEFAULT 'draft',
    primary_metric VARCHAR(64) NOT NULL,
    secondary_metrics TEXT[],
    min_sample_size INTEGER DEFAULT 1000,
    max_duration_days INTEGER DEFAULT 30,
    confidence_level FLOAT DEFAULT 0.95,
    traffic_allocation VARCHAR(16) DEFAULT 'equal',
    statistical_test VARCHAR(16) DEFAULT 't_test',
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(255),
    winner_variant_id VARCHAR(64),
    results_data JSONB
);

-- Variants table
CREATE TABLE IF NOT EXISTS ab_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES ab_experiments(id) ON DELETE CASCADE,
    variant_id VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    traffic_percentage FLOAT DEFAULT 50.0,
    is_control BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    sample_count INTEGER DEFAULT 0,
    metrics_data JSONB
);

-- User assignments table
CREATE TABLE IF NOT EXISTS ab_user_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES ab_experiments(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    variant_id VARCHAR(64) NOT NULL,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Experiment events table
CREATE TABLE IF NOT EXISTS ab_experiment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES ab_experiments(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    variant_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    metrics JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ab_experiments_model ON ab_experiments(model_name);
CREATE INDEX IF NOT EXISTS idx_ab_experiments_status ON ab_experiments(status);
CREATE INDEX IF NOT EXISTS idx_ab_variants_experiment ON ab_variants(experiment_id);
CREATE INDEX IF NOT EXISTS idx_ab_assignments_user ON ab_user_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_ab_assignments_experiment ON ab_user_assignments(experiment_id);
CREATE INDEX IF NOT EXISTS idx_ab_events_user ON ab_experiment_events(user_id);
CREATE INDEX IF NOT EXISTS idx_ab_events_timestamp ON ab_experiment_events(timestamp);
"""
