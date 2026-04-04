"""
MLflow Experiment Tracking Integration
Tracks ML experiments, parameters, metrics, and artifacts.
"""

import os
import json
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager

try:
    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


@dataclass
class Experiment:
    """ML experiment definition."""
    id: str
    name: str
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Run:
    """ML experiment run."""
    id: str
    experiment_id: str
    status: str = "running"
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    artifact_uri: Optional[str] = None


class MLflowTracker:
    """
    MLflow experiment tracker.
    Manages experiments, runs, parameters, and metrics.
    """
    
    def __init__(self, tracking_uri: Optional[str] = None):
        self.tracking_uri = tracking_uri or settings.MLFLOW_TRACKING_URI
        self.client: Optional[MlflowClient] = None
        
        if MLFLOW_AVAILABLE:
            self._initialize()
    
    def _initialize(self) -> None:
        """Initialize MLflow connection."""
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            self.client = MlflowClient()
            logger.info(f"MLflow tracker initialized: {self.tracking_uri}")
        except Exception as e:
            logger.error(f"Failed to initialize MLflow: {e}")
    
    def create_experiment(
        self,
        name: str,
        description: str = "",
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a new experiment.
        
        Args:
            name: Experiment name
            description: Experiment description
            tags: Experiment tags
        
        Returns:
            Experiment ID
        """
        if not MLFLOW_AVAILABLE or not self.client:
            logger.warning("MLflow not available")
            return ""
        
        try:
            experiment_id = self.client.create_experiment(
                name=name,
                tags=tags or {}
            )
            
            logger.info(f"Created experiment: {name} ({experiment_id})")
            return experiment_id
            
        except Exception as e:
            logger.error(f"Failed to create experiment: {e}")
            # Return existing experiment ID if name exists
            try:
                experiment = self.client.get_experiment_by_name(name)
                return experiment.experiment_id if experiment else ""
            except:
                return ""
    
    def start_run(
        self,
        experiment_id: Optional[str] = None,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        nested: bool = False
    ) -> str:
        """
        Start a new run.
        
        Args:
            experiment_id: Experiment ID
            run_name: Run name
            tags: Run tags
            nested: Whether this is a nested run
        
        Returns:
            Run ID
        """
        if not MLFLOW_AVAILABLE:
            logger.warning("MLflow not available")
            return ""
        
        try:
            run = mlflow.start_run(
                experiment_id=experiment_id,
                run_name=run_name,
                tags=tags,
                nested=nested
            )
            
            logger.info(f"Started run: {run.info.run_id}")
            return run.info.run_id
            
        except Exception as e:
            logger.error(f"Failed to start run: {e}")
            return ""
    
    def end_run(self, status: str = "finished") -> None:
        """End current run."""
        if not MLFLOW_AVAILABLE:
            return
        
        try:
            mlflow.end_run(status=status)
            logger.info(f"Ended run with status: {status}")
        except Exception as e:
            logger.error(f"Failed to end run: {e}")
    
    def log_param(self, key: str, value: Any) -> None:
        """Log a parameter."""
        if not MLFLOW_AVAILABLE:
            return
        
        try:
            mlflow.log_param(key, value)
        except Exception as e:
            logger.error(f"Failed to log param {key}: {e}")
    
    def log_params(self, params: Dict[str, Any]) -> None:
        """Log multiple parameters."""
        if not MLFLOW_AVAILABLE:
            return
        
        try:
            mlflow.log_params(params)
        except Exception as e:
            logger.error(f"Failed to log params: {e}")
    
    def log_metric(self, key: str, value: float, step: Optional[int] = None) -> None:
        """Log a metric."""
        if not MLFLOW_AVAILABLE:
            return
        
        try:
            mlflow.log_metric(key, value, step=step)
        except Exception as e:
            logger.error(f"Failed to log metric {key}: {e}")
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log multiple metrics."""
        if not MLFLOW_AVAILABLE:
            return
        
        try:
            mlflow.log_metrics(metrics, step=step)
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
    
    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None) -> None:
        """Log an artifact file."""
        if not MLFLOW_AVAILABLE:
            return
        
        try:
            mlflow.log_artifact(local_path, artifact_path)
        except Exception as e:
            logger.error(f"Failed to log artifact: {e}")
    
    def log_artifacts(self, local_dir: str, artifact_path: Optional[str] = None) -> None:
        """Log all artifacts from a directory."""
        if not MLFLOW_AVAILABLE:
            return
        
        try:
            mlflow.log_artifacts(local_dir, artifact_path)
        except Exception as e:
            logger.error(f"Failed to log artifacts: {e}")
    
    def log_model(
        self,
        model: Any,
        artifact_path: str,
        registered_model_name: Optional[str] = None
    ) -> None:
        """Log a model."""
        if not MLFLOW_AVAILABLE:
            return
        
        try:
            mlflow.sklearn.log_model(
                model,
                artifact_path,
                registered_model_name=registered_model_name
            )
        except Exception as e:
            logger.error(f"Failed to log model: {e}")
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID."""
        if not MLFLOW_AVAILABLE or not self.client:
            return None
        
        try:
            exp = self.client.get_experiment(experiment_id)
            return Experiment(
                id=exp.experiment_id,
                name=exp.name,
                tags=dict(exp.tags) if exp.tags else {}
            )
        except Exception as e:
            logger.error(f"Failed to get experiment: {e}")
            return None
    
    def get_run(self, run_id: str) -> Optional[Run]:
        """Get run by ID."""
        if not MLFLOW_AVAILABLE or not self.client:
            return None
        
        try:
            run = self.client.get_run(run_id)
            return Run(
                id=run.info.run_id,
                experiment_id=run.info.experiment_id,
                status=run.info.status,
                params=dict(run.data.params) if run.data.params else {},
                metrics=dict(run.data.metrics) if run.data.metrics else {},
                tags=dict(run.data.tags) if run.data.tags else {},
                artifact_uri=run.info.artifact_uri
            )
        except Exception as e:
            logger.error(f"Failed to get run: {e}")
            return None
    
    def search_runs(
        self,
        experiment_ids: List[str],
        filter_string: str = "",
        order_by: Optional[List[str]] = None,
        max_results: int = 100
    ) -> List[Run]:
        """Search for runs."""
        if not MLFLOW_AVAILABLE or not self.client:
            return []
        
        try:
            runs = self.client.search_runs(
                experiment_ids=experiment_ids,
                filter_string=filter_string,
                order_by=order_by,
                max_results=max_results
            )
            
            return [
                Run(
                    id=r.info.run_id,
                    experiment_id=r.info.experiment_id,
                    status=r.info.status,
                    params=dict(r.data.params) if r.data.params else {},
                    metrics=dict(r.data.metrics) if r.data.metrics else {},
                    tags=dict(r.data.tags) if r.data.tags else {}
                )
                for r in runs
            ]
        except Exception as e:
            logger.error(f"Failed to search runs: {e}")
            return []
    
    @contextmanager
    def track_run(
        self,
        experiment_name: Optional[str] = None,
        run_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Context manager for tracking a run."""
        experiment_id = None
        if experiment_name:
            experiment_id = self.create_experiment(experiment_name)
        
        run_id = self.start_run(experiment_id, run_name, tags)
        
        if params:
            self.log_params(params)
        
        try:
            yield run_id
        finally:
            self.end_run()


# Singleton instance
mlflow_tracker = MLflowTracker()


def get_mlflow_tracker() -> MLflowTracker:
    """Get MLflow tracker instance."""
    return mlflow_tracker
