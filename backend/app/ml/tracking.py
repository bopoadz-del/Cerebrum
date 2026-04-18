"""
MLflow Tracking Wrapper for Formula Executions

Tracks formula execution metrics, credibility tier changes, and model performance.
Integrates with the Cerebrum execution pipeline.
"""

import os
import json
import time
import inspect
from typing import Optional, Dict, List, Any, Callable, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from contextlib import contextmanager
from functools import wraps

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# Try to import MLflow
try:
    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient
    from mlflow.entities import Experiment, Run, RunStatus
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None
    MlflowClient = None


@dataclass
class FormulaExecutionMetrics:
    """Metrics captured during formula execution."""
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    input_size: int = 0
    output_size: int = 0
    cache_hit: bool = False
    retry_count: int = 0
    error_count: int = 0
    validation_time_ms: float = 0.0
    computation_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CredibilityTierChange:
    """Records credibility tier transitions."""
    formula_id: str
    old_tier: str
    new_tier: str
    confidence_score: float
    verification_count: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "formula_id": self.formula_id,
            "old_tier": self.old_tier,
            "new_tier": self.new_tier,
            "confidence_score": self.confidence_score,
            "verification_count": self.verification_count,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ModelPerformanceMetrics:
    """Model performance over time."""
    model_name: str
    version: str
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    latency_p50_ms: Optional[float] = None
    latency_p99_ms: Optional[float] = None
    throughput_qps: Optional[float] = None
    training_time_seconds: Optional[float] = None
    inference_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class HyperparameterTuningResult:
    """Hyperparameter tuning results."""
    tuning_method: str  # grid, random, bayesian
    best_params: Dict[str, Any]
    best_score: float
    total_runs: int
    search_space: Dict[str, List[Any]]
    all_results: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tuning_method": self.tuning_method,
            "best_params": json.dumps(self.best_params),
            "best_score": self.best_score,
            "total_runs": self.total_runs,
            "search_space": json.dumps(self.search_space),
        }


class MLflowTracker:
    """
    MLflow tracker for Cerebrum formula executions and ML experiments.
    
    Tracks:
    - Formula execution metrics (time, memory, errors)
    - Credibility tier changes
    - Model performance over time
    - Hyperparameter tuning results
    """
    
    DEFAULT_EXPERIMENT_NAME = "cerebrum_formula_executions"
    TIER_CHANGE_EXPERIMENT = "cerebrum_credibility_tiers"
    MODEL_PERFORMANCE_EXPERIMENT = "cerebrum_model_performance"
    HYPERPARAMETER_EXPERIMENT = "cerebrum_hyperparameter_tuning"
    
    def __init__(self, tracking_uri: Optional[str] = None):
        self.tracking_uri = tracking_uri or self._get_tracking_uri()
        self._client: Optional[Any] = None
        self._initialized = False
        self._experiments: Dict[str, str] = {}  # name -> id cache
        
        if MLFLOW_AVAILABLE:
            self._initialize()
    
    def _get_tracking_uri(self) -> str:
        """Get MLflow tracking URI from settings or env."""
        return (
            settings.MLFLOW_TRACKING_URI
            or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        )
    
    def _initialize(self) -> None:
        """Initialize MLflow connection."""
        try:
            if not MLFLOW_AVAILABLE:
                logger.warning("MLflow not installed. Tracking disabled.")
                return
            
            mlflow.set_tracking_uri(self.tracking_uri)
            self._client = MlflowClient()
            self._initialized = True
            logger.info(f"MLflow tracker initialized: {self.tracking_uri}")
            
            # Ensure default experiments exist
            self._ensure_experiment(self.DEFAULT_EXPERIMENT_NAME)
            self._ensure_experiment(self.TIER_CHANGE_EXPERIMENT)
            self._ensure_experiment(self.MODEL_PERFORMANCE_EXPERIMENT)
            self._ensure_experiment(self.HYPERPARAMETER_EXPERIMENT)
            
        except Exception as e:
            logger.error(f"Failed to initialize MLflow: {e}")
            self._initialized = False
    
    def _ensure_experiment(self, name: str) -> str:
        """Get or create experiment."""
        if name in self._experiments:
            return self._experiments[name]
        
        try:
            experiment = self._client.get_experiment_by_name(name)
            if experiment:
                experiment_id = experiment.experiment_id
            else:
                experiment_id = self._client.create_experiment(
                    name=name,
                    tags={"created_by": "cerebrum", "type": "system"}
                )
            self._experiments[name] = experiment_id
            return experiment_id
        except Exception as e:
            logger.error(f"Failed to ensure experiment {name}: {e}")
            return ""
    
    @property
    def is_available(self) -> bool:
        """Check if MLflow is available and initialized."""
        return MLFLOW_AVAILABLE and self._initialized and self._client is not None
    
    def start_run(
        self,
        experiment_name: Optional[str] = None,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        nested: bool = False
    ) -> Optional[str]:
        """Start a new MLflow run."""
        if not self.is_available:
            logger.debug("MLflow not available, run not started")
            return None
        
        try:
            experiment_id = None
            if experiment_name:
                experiment_id = self._ensure_experiment(experiment_name)
            
            run = mlflow.start_run(
                experiment_id=experiment_id,
                run_name=run_name,
                tags=tags or {},
                nested=nested
            )
            
            logger.debug(f"Started MLflow run: {run.info.run_id}")
            return run.info.run_id
            
        except Exception as e:
            logger.error(f"Failed to start MLflow run: {e}")
            return None
    
    def end_run(self, status: str = "FINISHED") -> None:
        """End current MLflow run."""
        if not self.is_available:
            return
        
        try:
            mlflow.end_run(status=status)
            logger.debug("Ended MLflow run")
        except Exception as e:
            logger.error(f"Failed to end MLflow run: {e}")
    
    def log_param(self, key: str, value: Any) -> None:
        """Log a parameter to current run."""
        if not self.is_available:
            return
        
        try:
            # Convert value to string for MLflow
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            mlflow.log_param(key, value)
        except Exception as e:
            logger.error(f"Failed to log param {key}: {e}")
    
    def log_params(self, params: Dict[str, Any]) -> None:
        """Log multiple parameters."""
        for key, value in params.items():
            self.log_param(key, value)
    
    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        """Log a metric to current run."""
        if not self.is_available:
            return
        
        try:
            mlflow.log_metric(key, value, step=step)
        except Exception as e:
            logger.error(f"Failed to log metric {key}: {e}")
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log multiple metrics."""
        for key, value in metrics.items():
            self.log_metric(key, value, step=step)
    
    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None) -> None:
        """Log an artifact file."""
        if not self.is_available:
            return
        
        try:
            mlflow.log_artifact(local_path, artifact_path)
        except Exception as e:
            logger.error(f"Failed to log artifact: {e}")
    
    def log_dict(self, dictionary: Dict[str, Any], artifact_file: str) -> None:
        """Log a dictionary as an artifact."""
        if not self.is_available:
            return
        
        try:
            mlflow.log_dict(dictionary, artifact_file)
        except Exception as e:
            logger.error(f"Failed to log dict artifact: {e}")
    
    # =========================================================================
    # Formula Execution Tracking
    # =========================================================================
    
    def track_formula_execution(
        self,
        formula_id: str,
        formula_name: str,
        metrics: FormulaExecutionMetrics,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        artifacts: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Track a formula execution.
        
        Args:
            formula_id: Unique formula identifier
            formula_name: Human-readable formula name
            metrics: Execution metrics
            parameters: Formula parameters
            tags: Additional tags
            artifacts: Paths to artifact files
            
        Returns:
            Run ID if successful
        """
        run_id = self.start_run(
            experiment_name=self.DEFAULT_EXPERIMENT_NAME,
            run_name=f"formula_{formula_id}_{datetime.utcnow().isoformat()}",
            tags={
                "formula_id": formula_id,
                "formula_name": formula_name,
                **(tags or {})
            }
        )
        
        if not run_id:
            return None
        
        try:
            # Log parameters
            self.log_params({
                "formula_id": formula_id,
                "formula_name": formula_name,
                **(parameters or {})
            })
            
            # Log execution metrics
            self.log_metrics(metrics.to_dict())
            
            # Log artifacts
            if artifacts:
                for artifact_path in artifacts:
                    if os.path.exists(artifact_path):
                        self.log_artifact(artifact_path)
            
            self.end_run("FINISHED")
            return run_id
            
        except Exception as e:
            logger.error(f"Error tracking formula execution: {e}")
            self.end_run("FAILED")
            return None
    
    # =========================================================================
    # Credibility Tier Tracking
    # =========================================================================
    
    def track_tier_change(
        self,
        change: CredibilityTierChange,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Track a credibility tier change.
        
        Args:
            change: Tier change details
            metadata: Additional metadata
            
        Returns:
            Run ID if successful
        """
        run_id = self.start_run(
            experiment_name=self.TIER_CHANGE_EXPERIMENT,
            run_name=f"tier_change_{change.formula_id}",
            tags={
                "formula_id": change.formula_id,
                "old_tier": change.old_tier,
                "new_tier": change.new_tier,
            }
        )
        
        if not run_id:
            return None
        
        try:
            self.log_params({
                "formula_id": change.formula_id,
                "old_tier": change.old_tier,
                "new_tier": change.new_tier,
                "verification_count": change.verification_count,
                **(metadata or {})
            })
            
            self.log_metrics({
                "confidence_score": change.confidence_score,
            })
            
            self.log_dict(change.to_dict(), "tier_change.json")
            
            self.end_run("FINISHED")
            return run_id
            
        except Exception as e:
            logger.error(f"Error tracking tier change: {e}")
            self.end_run("FAILED")
            return None
    
    # =========================================================================
    # Model Performance Tracking
    # =========================================================================
    
    def track_model_performance(
        self,
        metrics: ModelPerformanceMetrics,
        step: Optional[int] = None,
        artifacts: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Track model performance metrics.
        
        Args:
            metrics: Performance metrics
            step: Optional step number (for time series)
            artifacts: Paths to performance artifacts
            
        Returns:
            Run ID if successful
        """
        run_id = self.start_run(
            experiment_name=self.MODEL_PERFORMANCE_EXPERIMENT,
            run_name=f"model_{metrics.model_name}_v{metrics.version}",
            tags={
                "model_name": metrics.model_name,
                "version": metrics.version,
            }
        )
        
        if not run_id:
            return None
        
        try:
            self.log_params({
                "model_name": metrics.model_name,
                "version": metrics.version,
            })
            
            # Log only non-None metrics
            self.log_metrics(metrics.to_dict(), step=step)
            
            # Log metrics as artifact for detailed view
            self.log_dict(metrics.to_dict(), "performance_metrics.json")
            
            if artifacts:
                for artifact_path in artifacts:
                    if os.path.exists(artifact_path):
                        self.log_artifact(artifact_path)
            
            self.end_run("FINISHED")
            return run_id
            
        except Exception as e:
            logger.error(f"Error tracking model performance: {e}")
            self.end_run("FAILED")
            return None
    
    # =========================================================================
    # Hyperparameter Tuning Tracking
    # =========================================================================
    
    def track_hyperparameter_tuning(
        self,
        result: HyperparameterTuningResult,
        model_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Track hyperparameter tuning results.
        
        Args:
            result: Tuning results
            model_name: Associated model name
            
        Returns:
            Run ID if successful
        """
        run_id = self.start_run(
            experiment_name=self.HYPERPARAMETER_EXPERIMENT,
            run_name=f"tuning_{result.tuning_method}_{datetime.utcnow().isoformat()}",
            tags={
                "tuning_method": result.tuning_method,
                "model_name": model_name or "unknown",
            }
        )
        
        if not run_id:
            return None
        
        try:
            self.log_params(result.to_dict())
            
            # Log individual runs as nested runs
            for i, run_result in enumerate(result.all_results[:10]):  # Limit to 10 nested runs
                with mlflow.start_run(nested=True, run_name=f"run_{i}"):
                    mlflow.log_params(run_result.get("params", {}))
                    mlflow.log_metrics({"score": run_result.get("score", 0)})
            
            # Log all results as artifact
            self.log_dict({
                "tuning_method": result.tuning_method,
                "best_params": result.best_params,
                "best_score": result.best_score,
                "total_runs": result.total_runs,
                "all_results": result.all_results,
            }, "tuning_results.json")
            
            self.end_run("FINISHED")
            return run_id
            
        except Exception as e:
            logger.error(f"Error tracking hyperparameter tuning: {e}")
            self.end_run("FAILED")
            return None
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    def get_experiment_runs(
        self,
        experiment_name: str,
        filter_string: str = "",
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Get runs for an experiment."""
        if not self.is_available:
            return []
        
        try:
            experiment = self._client.get_experiment_by_name(experiment_name)
            if not experiment:
                return []
            
            runs = self._client.search_runs(
                experiment_ids=[experiment.experiment_id],
                filter_string=filter_string,
                max_results=max_results
            )
            
            return [
                {
                    "run_id": r.info.run_id,
                    "status": r.info.status,
                    "params": dict(r.data.params),
                    "metrics": dict(r.data.metrics),
                    "tags": dict(r.data.tags),
                    "start_time": r.info.start_time,
                    "end_time": r.info.end_time,
                }
                for r in runs
            ]
        except Exception as e:
            logger.error(f"Failed to get experiment runs: {e}")
            return []
    
    def get_formula_execution_history(
        self,
        formula_id: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Get formula execution history."""
        filter_string = f"tags.formula_id = '{formula_id}'" if formula_id else ""
        return self.get_experiment_runs(
            self.DEFAULT_EXPERIMENT_NAME,
            filter_string,
            max_results
        )
    
    def compare_formula_executions(
        self,
        run_id_1: str,
        run_id_2: str
    ) -> Dict[str, Any]:
        """Compare two formula execution runs."""
        if not self.is_available:
            return {"error": "MLflow not available"}
        
        try:
            run1 = self._client.get_run(run_id_1)
            run2 = self._client.get_run(run_id_2)
            
            return {
                "run_1": {
                    "run_id": run1.info.run_id,
                    "params": dict(run1.data.params),
                    "metrics": dict(run1.data.metrics),
                },
                "run_2": {
                    "run_id": run2.info.run_id,
                    "params": dict(run2.data.params),
                    "metrics": dict(run2.data.metrics),
                },
                "metric_differences": {
                    k: run2.data.metrics.get(k, 0) - run1.data.metrics.get(k, 0)
                    for k in set(run1.data.metrics.keys()) | set(run2.data.metrics.keys())
                }
            }
        except Exception as e:
            logger.error(f"Failed to compare runs: {e}")
            return {"error": str(e)}


# Singleton instance
_tracker: Optional[MLflowTracker] = None


def get_mlflow_tracker() -> MLflowTracker:
    """Get or create MLflow tracker singleton."""
    global _tracker
    if _tracker is None:
        _tracker = MLflowTracker()
    return _tracker


@contextmanager
def track_formula_execution(
    formula_id: str,
    formula_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None
):
    """
    Context manager for tracking formula execution.
    
    Usage:
        with track_formula_execution("formula_123", "Cost Calculator"):
            result = execute_formula(...)
    """
    tracker = get_mlflow_tracker()
    metrics = FormulaExecutionMetrics()
    
    run_id = tracker.start_run(
        experiment_name=tracker.DEFAULT_EXPERIMENT_NAME,
        run_name=f"formula_{formula_id}_{datetime.utcnow().isoformat()}",
        tags={
            "formula_id": formula_id,
            "formula_name": formula_name,
            **(tags or {})
        }
    )
    
    start_time = time.time()
    
    try:
        yield metrics
        
        # Calculate execution time
        metrics.execution_time_ms = (time.time() - start_time) * 1000
        
        # Log everything
        if run_id:
            tracker.log_params({
                "formula_id": formula_id,
                "formula_name": formula_name,
                **(parameters or {})
            })
            tracker.log_metrics(metrics.to_dict())
            tracker.end_run("FINISHED")
            
    except Exception as e:
        metrics.error_count += 1
        if run_id:
            tracker.log_metrics(metrics.to_dict())
            tracker.end_run("FAILED")
        raise


def with_mlflow_tracking(
    experiment_name: Optional[str] = None,
    run_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
):
    """
    Decorator for tracking function execution with MLflow.
    
    Usage:
        @with_mlflow_tracking(experiment_name="my_experiment")
        def my_function(param1, param2):
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracker = get_mlflow_tracker()
            run_id = tracker.start_run(
                experiment_name=experiment_name,
                run_name=run_name or func.__name__,
                tags=tags
            )
            
            start_time = time.time()
            
            try:
                # Log function parameters
                bound = inspect.signature(func).bind(*args, **kwargs)
                bound.apply_defaults()
                for key, value in bound.arguments.items():
                    if isinstance(value, (int, float, str, bool)):
                        tracker.log_param(f"param_{key}", value)
                
                result = func(*args, **kwargs)
                
                # Log execution metrics
                execution_time = (time.time() - start_time) * 1000
                tracker.log_metrics({
                    "execution_time_ms": execution_time,
                    "success": 1.0
                })
                
                if run_id:
                    tracker.end_run("FINISHED")
                
                return result
                
            except Exception as e:
                tracker.log_metrics({"success": 0.0, "error": 1.0})
                tracker.log_param("error_message", str(e))
                if run_id:
                    tracker.end_run("FAILED")
                raise
        
        return wrapper
    return decorator
