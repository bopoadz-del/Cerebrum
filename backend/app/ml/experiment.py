"""
Experiment Management for Cerebrum MLflow Integration

Provides high-level experiment management with Cerebrum-specific abstractions.
"""

import os
import json
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

from app.core.logging import get_logger
from app.core.config import settings
from app.ml.tracking import MLflowTracker, get_mlflow_tracker

logger = get_logger(__name__)

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None
    MlflowClient = None


class ExperimentType(Enum):
    """Types of experiments in Cerebrum."""
    FORMULA_EXECUTION = "formula_execution"
    CREDIBILITY_EVALUATION = "credibility_evaluation"
    MODEL_TRAINING = "model_training"
    HYPERPARAMETER_TUNING = "hyperparameter_tuning"
    A_B_TESTING = "a_b_testing"
    DRIFT_DETECTION = "drift_detection"
    CUSTOM = "custom"


class ExperimentStatus(Enum):
    """Experiment status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class ExperimentConfig:
    """Experiment configuration."""
    name: str
    experiment_type: ExperimentType
    description: str = ""
    hypothesis: str = ""
    metrics_to_track: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    artifact_paths: List[str] = field(default_factory=list)
    parent_experiment_id: Optional[str] = None


@dataclass
class ExperimentResult:
    """Experiment result summary."""
    experiment_id: str
    run_count: int = 0
    best_run_id: Optional[str] = None
    best_metric_value: Optional[float] = None
    primary_metric: str = ""
    summary_metrics: Dict[str, float] = field(default_factory=dict)
    status: ExperimentStatus = ExperimentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


@dataclass
class RunConfig:
    """Configuration for a single run."""
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    description: str = ""


class ExperimentManager:
    """
    High-level experiment management for Cerebrum.
    
    Provides abstractions for:
    - Creating and managing experiments
    - Running experiments with multiple trials
    - Comparing experiment results
    - Archiving and cleaning up experiments
    """
    
    def __init__(self, tracker: Optional[MLflowTracker] = None):
        self.tracker = tracker or get_mlflow_tracker()
        self._experiments: Dict[str, Any] = {}  # Local cache
        self._client: Optional[Any] = None
        
        if MLFLOW_AVAILABLE and self.tracker.is_available:
            try:
                self._client = MlflowClient()
            except Exception as e:
                logger.error(f"Failed to initialize MLflow client: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if experiment management is available."""
        return MLFLOW_AVAILABLE and self.tracker.is_available
    
    def create_experiment(
        self,
        config: ExperimentConfig
    ) -> Optional[str]:
        """
        Create a new experiment.
        
        Args:
            config: Experiment configuration
            
        Returns:
            Experiment ID if successful
        """
        if not self.is_available:
            logger.warning("MLflow not available, experiment not created")
            return None
        
        try:
            # Create experiment with tags
            experiment_tags = {
                "type": config.experiment_type.value,
                "description": config.description,
                "hypothesis": config.hypothesis,
                "created_by": "cerebrum",
                **config.tags
            }
            
            experiment_id = mlflow.create_experiment(
                name=config.name,
                tags=experiment_tags,
                artifact_location=None  # Use default
            )
            
            # Log experiment configuration
            with mlflow.start_run(experiment_id=experiment_id, run_name="config"):
                mlflow.log_params({
                    "config_name": config.name,
                    "config_type": config.experiment_type.value,
                    "config_description": config.description,
                    "config_hypothesis": config.hypothesis,
                    "metrics_to_track": json.dumps(config.metrics_to_track),
                    "artifact_paths": json.dumps(config.artifact_paths),
                })
                mlflow.log_dict(config.parameters, "experiment_config.json")
            
            logger.info(f"Created experiment: {config.name} ({experiment_id})")
            return experiment_id
            
        except Exception as e:
            logger.error(f"Failed to create experiment: {e}")
            # Return existing experiment if name exists
            try:
                exp = self._client.get_experiment_by_name(config.name)
                if exp:
                    return exp.experiment_id
            except:
                pass
            return None
    
    def get_or_create_experiment(
        self,
        name: str,
        experiment_type: ExperimentType = ExperimentType.CUSTOM,
        description: str = ""
    ) -> Optional[str]:
        """Get existing or create new experiment."""
        if not self.is_available:
            return None
        
        try:
            experiment = self._client.get_experiment_by_name(name)
            if experiment:
                return experiment.experiment_id
        except:
            pass
        
        # Create new
        config = ExperimentConfig(
            name=name,
            experiment_type=experiment_type,
            description=description
        )
        return self.create_experiment(config)
    
    def start_run(
        self,
        experiment_id: str,
        config: RunConfig
    ) -> Optional[str]:
        """
        Start a new run in an experiment.
        
        Args:
            experiment_id: Target experiment ID
            config: Run configuration
            
        Returns:
            Run ID if successful
        """
        return self.tracker.start_run(
            experiment_id=experiment_id,
            run_name=config.name,
            tags=config.tags
        )
    
    def run_trial(
        self,
        experiment_id: str,
        config: RunConfig,
        trial_func: Callable[[], Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a single trial/run within an experiment.
        
        Args:
            experiment_id: Experiment ID
            config: Run configuration
            trial_func: Function that returns metrics dict
            
        Returns:
            Run summary if successful
        """
        if not self.is_available:
            logger.warning("MLflow not available, trial not executed")
            return None
        
        run_id = self.start_run(experiment_id, config)
        if not run_id:
            return None
        
        try:
            # Log parameters
            self.tracker.log_params(config.parameters)
            
            # Execute trial
            result = trial_func()
            
            # Log metrics
            metrics = result.get("metrics", {})
            self.tracker.log_metrics(metrics)
            
            # Log artifacts
            artifacts = result.get("artifacts", [])
            for artifact_path in artifacts:
                if os.path.exists(artifact_path):
                    self.tracker.log_artifact(artifact_path)
            
            # Log additional data
            if "data" in result:
                self.tracker.log_dict(result["data"], "run_data.json")
            
            self.tracker.end_run("FINISHED")
            
            return {
                "run_id": run_id,
                "experiment_id": experiment_id,
                "metrics": metrics,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Trial failed: {e}")
            self.tracker.log_params({"error": str(e)})
            self.tracker.end_run("FAILED")
            return {
                "run_id": run_id,
                "experiment_id": experiment_id,
                "error": str(e),
                "status": "failed"
            }
    
    def run_experiment(
        self,
        config: ExperimentConfig,
        trial_configs: List[RunConfig],
        trial_func: Callable[[Dict[str, Any]], Dict[str, Any]],
        primary_metric: str = "",
        maximize: bool = True
    ) -> Optional[ExperimentResult]:
        """
        Run a full experiment with multiple trials.
        
        Args:
            config: Experiment configuration
            trial_configs: List of run configurations (one per trial)
            trial_func: Function taking parameters, returning results
            primary_metric: Metric to optimize
            maximize: Whether to maximize (True) or minimize (False)
            
        Returns:
            Experiment result summary
        """
        experiment_id = self.create_experiment(config)
        if not experiment_id:
            return None
        
        results = []
        best_run_id = None
        best_value = float('-inf') if maximize else float('inf')
        
        for trial_config in trial_configs:
            result = self.run_trial(
                experiment_id,
                trial_config,
                lambda: trial_func(trial_config.parameters)
            )
            
            if result and result.get("status") == "completed":
                results.append(result)
                
                # Track best run
                if primary_metric and primary_metric in result.get("metrics", {}):
                    value = result["metrics"][primary_metric]
                    if maximize and value > best_value:
                        best_value = value
                        best_run_id = result["run_id"]
                    elif not maximize and value < best_value:
                        best_value = value
                        best_run_id = result["run_id"]
        
        # Calculate summary metrics
        summary = {}
        for metric in config.metrics_to_track:
            values = [
                r["metrics"].get(metric)
                for r in results
                if metric in r.get("metrics", {})
            ]
            if values:
                summary[f"{metric}_mean"] = sum(values) / len(values)
                summary[f"{metric}_min"] = min(values)
                summary[f"{metric}_max"] = max(values)
        
        return ExperimentResult(
            experiment_id=experiment_id,
            run_count=len(results),
            best_run_id=best_run_id,
            best_metric_value=best_value if best_run_id else None,
            primary_metric=primary_metric,
            summary_metrics=summary,
            status=ExperimentStatus.COMPLETED,
            completed_at=datetime.utcnow()
        )
    
    def get_experiment_summary(self, experiment_id: str) -> Optional[ExperimentResult]:
        """Get summary of experiment results."""
        if not self.is_available:
            return None
        
        try:
            experiment = self._client.get_experiment(experiment_id)
            runs = self._client.search_runs([experiment_id])
            
            # Find best run (based on first metric)
            best_run = None
            best_value = float('-inf')
            
            for run in runs:
                metrics = dict(run.data.metrics)
                if metrics:
                    first_metric = list(metrics.values())[0]
                    if isinstance(first_metric, (int, float)) and first_metric > best_value:
                        best_value = first_metric
                        best_run = run
            
            return ExperimentResult(
                experiment_id=experiment_id,
                run_count=len(runs),
                best_run_id=best_run.info.run_id if best_run else None,
                best_metric_value=best_value if best_run else None,
                status=ExperimentStatus.COMPLETED if runs else ExperimentStatus.PENDING
            )
            
        except Exception as e:
            logger.error(f"Failed to get experiment summary: {e}")
            return None
    
    def compare_experiments(
        self,
        experiment_ids: List[str],
        metric_name: str
    ) -> Dict[str, Any]:
        """
        Compare multiple experiments on a specific metric.
        
        Args:
            experiment_ids: List of experiment IDs to compare
            metric_name: Metric to compare
            
        Returns:
            Comparison results
        """
        if not self.is_available:
            return {"error": "MLflow not available"}
        
        comparison = {}
        
        for exp_id in experiment_ids:
            try:
                experiment = self._client.get_experiment(exp_id)
                runs = self._client.search_runs([exp_id])
                
                metric_values = [
                    r.data.metrics.get(metric_name)
                    for r in runs
                    if metric_name in r.data.metrics
                ]
                
                if metric_values:
                    comparison[experiment.name] = {
                        "experiment_id": exp_id,
                        "mean": sum(metric_values) / len(metric_values),
                        "min": min(metric_values),
                        "max": max(metric_values),
                        "count": len(metric_values)
                    }
            except Exception as e:
                logger.error(f"Failed to compare experiment {exp_id}: {e}")
        
        return {
            "metric": metric_name,
            "experiments": comparison,
            "best_experiment": min(
                comparison.keys(),
                key=lambda k: comparison[k]["mean"]
            ) if comparison else None
        }
    
    def archive_experiment(self, experiment_id: str) -> bool:
        """Archive an experiment."""
        if not self.is_available:
            return False
        
        try:
            self._client.set_experiment_tag(experiment_id, "status", "archived")
            logger.info(f"Archived experiment: {experiment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to archive experiment: {e}")
            return False
    
    def delete_experiment(self, experiment_id: str) -> bool:
        """Delete an experiment (moves to trash)."""
        if not self.is_available:
            return False
        
        try:
            self._client.delete_experiment(experiment_id)
            logger.info(f"Deleted experiment: {experiment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete experiment: {e}")
            return False
    
    def restore_experiment(self, experiment_id: str) -> bool:
        """Restore a deleted experiment."""
        if not self.is_available:
            return False
        
        try:
            self._client.restore_experiment(experiment_id)
            logger.info(f"Restored experiment: {experiment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore experiment: {e}")
            return False
    
    def list_experiments(
        self,
        experiment_type: Optional[ExperimentType] = None,
        status: Optional[ExperimentStatus] = None
    ) -> List[Dict[str, Any]]:
        """List experiments with optional filtering."""
        if not self.is_available:
            return []
        
        try:
            experiments = self._client.search_experiments()
            
            result = []
            for exp in experiments:
                if exp.name == "Default":  # Skip default experiment
                    continue
                
                exp_type = exp.tags.get("type", "unknown")
                exp_status = exp.tags.get("status", "active")
                
                # Apply filters
                if experiment_type and exp_type != experiment_type.value:
                    continue
                if status and exp_status != status.value:
                    continue
                
                result.append({
                    "experiment_id": exp.experiment_id,
                    "name": exp.name,
                    "type": exp_type,
                    "status": exp_status,
                    "created_at": exp.creation_time,
                    "tags": dict(exp.tags)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list experiments: {e}")
            return []
    
    def export_experiment(
        self,
        experiment_id: str,
        output_path: str
    ) -> bool:
        """Export experiment data to JSON file."""
        if not self.is_available:
            return False
        
        try:
            experiment = self._client.get_experiment(experiment_id)
            runs = self._client.search_runs([experiment_id])
            
            export_data = {
                "experiment": {
                    "id": experiment.experiment_id,
                    "name": experiment.name,
                    "tags": dict(experiment.tags),
                },
                "runs": [
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
            }
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported experiment to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export experiment: {e}")
            return False


# Singleton instance
_manager: Optional[ExperimentManager] = None


def get_experiment_manager() -> ExperimentManager:
    """Get or create experiment manager singleton."""
    global _manager
    if _manager is None:
        _manager = ExperimentManager()
    return _manager
