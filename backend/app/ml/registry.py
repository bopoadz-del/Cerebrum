"""
MLflow Model Registry Integration for Cerebrum

Provides model versioning, staging (dev/staging/prod), and model lifecycle management.
Integrates with MLflow's model registry for production-grade model management.
"""

import os
import json
import hashlib
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

from app.core.logging import get_logger
from app.core.config import settings
from app.ml.tracking import get_mlflow_tracker

logger = get_logger(__name__)

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    from mlflow.models.model import ModelInfo
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None
    MlflowClient = None
    ModelInfo = None


class ModelStage(Enum):
    """Model lifecycle stages aligned with MLflow."""
    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


class ModelFramework(Enum):
    """Supported ML frameworks."""
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    SKLEARN = "sklearn"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    ONNX = "onnx"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


@dataclass
class ModelVersion:
    """Model version metadata."""
    name: str
    version: str
    stage: ModelStage
    framework: ModelFramework
    description: str = ""
    run_id: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    signature: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    @property
    def full_name(self) -> str:
        """Get full model name with version."""
        return f"{self.name}:{self.version}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "stage": self.stage.value,
            "framework": self.framework.value
        }


@dataclass
class ModelComparison:
    """Comparison between two model versions."""
    model_name: str
    version_a: str
    version_b: str
    stage_a: str
    stage_b: str
    metric_comparison: Dict[str, Dict[str, float]]
    parameter_changes: Dict[str, Dict[str, Any]]
    recommendation: str = ""


class MLflowModelRegistry:
    """
    MLflow-based model registry for Cerebrum.
    
    Features:
    - Model versioning with semantic versioning
    - Stage transitions (Staging → Production)
    - Model artifact management
    - Version comparison
    - Batch model operations
    """
    
    def __init__(self):
        self._client: Optional[Any] = None
        self._initialized = False
        
        if MLFLOW_AVAILABLE:
            self._initialize()
    
    def _initialize(self) -> None:
        """Initialize MLflow client."""
        try:
            tracking_uri = (
                settings.MLFLOW_TRACKING_URI
                or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
            )
            mlflow.set_tracking_uri(tracking_uri)
            self._client = MlflowClient()
            self._initialized = True
            logger.info(f"Model registry initialized: {tracking_uri}")
        except Exception as e:
            logger.error(f"Failed to initialize model registry: {e}")
            self._initialized = False
    
    @property
    def is_available(self) -> bool:
        """Check if model registry is available."""
        return MLFLOW_AVAILABLE and self._initialized and self._client is not None
    
    # =====================================================================
    # Model Registration
    # =====================================================================
    
    def register_model(
        self,
        name: str,
        run_id: str,
        artifact_path: str = "model",
        description: str = "",
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[ModelVersion]:
        """
        Register a model from an MLflow run.
        
        Args:
            name: Model name
            run_id: Source run ID
            artifact_path: Path to model artifact in run
            description: Model description
            tags: Additional tags
            
        Returns:
            Model version info if successful
        """
        if not self.is_available:
            logger.warning("Model registry not available")
            return None
        
        try:
            # Register model
            model_version = mlflow.register_model(
                model_uri=f"runs:/{run_id}/{artifact_path}",
                name=name
            )
            
            # Add tags
            if tags:
                for key, value in tags.items():
                    self._client.set_model_version_tag(
                        name=name,
                        version=model_version.version,
                        key=key,
                        value=value
                    )
            
            # Add description
            if description:
                self._client.update_model_version(
                    name=name,
                    version=model_version.version,
                    description=description
                )
            
            # Get run info for additional metadata
            run = self._client.get_run(run_id)
            
            logger.info(f"Registered model: {name} v{model_version.version}")
            
            return ModelVersion(
                name=name,
                version=model_version.version,
                stage=ModelStage.NONE,
                framework=self._detect_framework(run.data.tags),
                description=description,
                run_id=run_id,
                metrics=dict(run.data.metrics),
                parameters=dict(run.data.params),
                tags=tags or {},
                created_by=run.data.tags.get("created_by", "unknown")
            )
            
        except Exception as e:
            logger.error(f"Failed to register model: {e}")
            return None
    
    def register_model_from_local(
        self,
        name: str,
        local_path: str,
        flavor: str = "sklearn",
        description: str = "",
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[ModelVersion]:
        """
        Register a model from local path.
        
        Args:
            name: Model name
            local_path: Path to model files
            flavor: MLflow model flavor (sklearn, pytorch, tensorflow, etc.)
            description: Model description
            tags: Additional tags
            
        Returns:
            Model version info if successful
        """
        if not self.is_available:
            logger.warning("Model registry not available")
            return None
        
        try:
            # Start a run to log the model
            with mlflow.start_run(run_name=f"register_{name}") as run:
                # Log model with appropriate flavor
                if flavor == "sklearn":
                    mlflow.sklearn.log_model(
                        sk_model=None,  # Model loaded from path
                        artifact_path="model",
                        registered_model_name=name
                    )
                elif flavor == "pytorch":
                    mlflow.pytorch.log_model(
                        pytorch_model=None,
                        artifact_path="model",
                        registered_model_name=name
                    )
                else:
                    # Generic artifact logging
                    mlflow.log_artifact(local_path, "model")
                    model_version = self._client.create_model_version(
                        name=name,
                        source=f"runs:/{run.info.run_id}/model",
                        run_id=run.info.run_id
                    )
                
                # Add tags
                if tags:
                    for key, value in tags.items():
                        self._client.set_model_version_tag(
                            name=name,
                            version=model_version.version,
                            key=key,
                            value=value
                        )
                
                if description:
                    self._client.update_model_version(
                        name=name,
                        version=model_version.version,
                        description=description
                    )
                
                logger.info(f"Registered local model: {name} v{model_version.version}")
                
                return ModelVersion(
                    name=name,
                    version=model_version.version,
                    stage=ModelStage.NONE,
                    framework=ModelFramework(flavor),
                    description=description,
                    run_id=run.info.run_id,
                    tags=tags or {}
                )
                
        except Exception as e:
            logger.error(f"Failed to register local model: {e}")
            return None
    
    # =====================================================================
    # Model Staging
    # =====================================================================
    
    def transition_stage(
        self,
        name: str,
        version: str,
        stage: ModelStage,
        description: str = ""
    ) -> bool:
        """
        Transition model to a new stage.
        
        Args:
            name: Model name
            version: Version number
            stage: Target stage
            description: Transition description
            
        Returns:
            True if successful
        """
        if not self.is_available:
            logger.warning("Model registry not available")
            return False
        
        try:
            self._client.transition_model_version_stage(
                name=name,
                version=version,
                stage=stage.value,
                archive_existing_versions=(stage == ModelStage.PRODUCTION)
            )
            
            # Update description if provided
            if description:
                current = self._client.get_model_version(name, version)
                new_desc = f"{current.description}\n\nTransition: {description}" if current.description else description
                self._client.update_model_version(
                    name=name,
                    version=version,
                    description=new_desc
                )
            
            logger.info(f"Transitioned {name}:{version} to {stage.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to transition stage: {e}")
            return False
    
    def promote_to_production(
        self,
        name: str,
        version: str,
        description: str = ""
    ) -> bool:
        """Promote model to production."""
        return self.transition_stage(
            name, version, ModelStage.PRODUCTION, description
        )
    
    def stage_for_testing(
        self,
        name: str,
        version: str,
        description: str = ""
    ) -> bool:
        """Stage model for testing."""
        return self.transition_stage(
            name, version, ModelStage.STAGING, description
        )
    
    def archive_model(
        self,
        name: str,
        version: str,
        description: str = ""
    ) -> bool:
        """Archive a model version."""
        return self.transition_stage(
            name, version, ModelStage.ARCHIVED, description
        )
    
    # =====================================================================
    # Model Retrieval
    # =====================================================================
    
    def get_model_version(
        self,
        name: str,
        version: str
    ) -> Optional[ModelVersion]:
        """Get specific model version."""
        if not self.is_available:
            return None
        
        try:
            mv = self._client.get_model_version(name, version)
            
            return ModelVersion(
                name=mv.name,
                version=mv.version,
                stage=ModelStage(mv.current_stage),
                framework=self._detect_framework(mv.tags),
                description=mv.description,
                run_id=mv.run_id,
                tags=dict(mv.tags) if mv.tags else {}
            )
            
        except Exception as e:
            logger.error(f"Failed to get model version: {e}")
            return None
    
    def get_latest_version(
        self,
        name: str,
        stage: Optional[ModelStage] = None
    ) -> Optional[ModelVersion]:
        """Get latest model version, optionally by stage."""
        if not self.is_available:
            return None
        
        try:
            if stage:
                latest = self._client.get_latest_versions(name, stages=[stage.value])
            else:
                latest = self._client.get_latest_versions(name)
            
            if not latest:
                return None
            
            mv = latest[0]
            return ModelVersion(
                name=mv.name,
                version=mv.version,
                stage=ModelStage(mv.current_stage),
                framework=self._detect_framework(mv.tags),
                description=mv.description,
                run_id=mv.run_id,
                tags=dict(mv.tags) if mv.tags else {}
            )
            
        except Exception as e:
            logger.error(f"Failed to get latest version: {e}")
            return None
    
    def get_production_model(self, name: str) -> Optional[ModelVersion]:
        """Get the production version of a model."""
        return self.get_latest_version(name, ModelStage.PRODUCTION)
    
    def list_models(
        self,
        name_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List registered models."""
        if not self.is_available:
            return []
        
        try:
            models = self._client.list_registered_models()
            
            result = []
            for model in models:
                if name_filter and name_filter not in model.name:
                    continue
                
                # Get latest version info
                latest_versions = self._client.get_latest_versions(model.name)
                
                result.append({
                    "name": model.name,
                    "creation_timestamp": model.creation_timestamp,
                    "last_updated_timestamp": model.last_updated_timestamp,
                    "description": model.description,
                    "latest_versions": [
                        {
                            "version": v.version,
                            "stage": v.current_stage
                        }
                        for v in latest_versions
                    ],
                    "version_count": len(latest_versions)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def list_model_versions(
        self,
        name: str,
        stage: Optional[ModelStage] = None
    ) -> List[ModelVersion]:
        """List all versions of a model."""
        if not self.is_available:
            return []
        
        try:
            versions = self._client.search_model_versions(f"name='{name}'")
            
            result = []
            for mv in versions:
                if stage and mv.current_stage != stage.value:
                    continue
                
                result.append(ModelVersion(
                    name=mv.name,
                    version=mv.version,
                    stage=ModelStage(mv.current_stage),
                    framework=self._detect_framework(mv.tags),
                    description=mv.description,
                    run_id=mv.run_id,
                    tags=dict(mv.tags) if mv.tags else {}
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list model versions: {e}")
            return []
    
    # =====================================================================
    # Model Comparison
    # =====================================================================
    
    def compare_versions(
        self,
        name: str,
        version_a: str,
        version_b: str,
        recommendation_metric: str = ""
    ) -> Optional[ModelComparison]:
        """
        Compare two model versions.
        
        Args:
            name: Model name
            version_a: First version to compare
            version_b: Second version to compare
            recommendation_metric: Metric to base recommendation on
            
        Returns:
            Comparison result
        """
        if not self.is_available:
            return None
        
        try:
            mv_a = self._client.get_model_version(name, version_a)
            mv_b = self._client.get_model_version(name, version_b)
            
            # Get run metrics
            run_a = self._client.get_run(mv_a.run_id) if mv_a.run_id else None
            run_b = self._client.get_run(mv_b.run_id) if mv_b.run_id else None
            
            metrics_a = dict(run_a.data.metrics) if run_a else {}
            metrics_b = dict(run_b.data.metrics) if run_b else {}
            
            # Compare metrics
            metric_comparison = {}
            all_metrics = set(metrics_a.keys()) | set(metrics_b.keys())
            
            for metric in all_metrics:
                val_a = metrics_a.get(metric)
                val_b = metrics_b.get(metric)
                
                if val_a is not None and val_b is not None:
                    diff = val_b - val_a
                    pct_change = (diff / val_a * 100) if val_a != 0 else 0
                    
                    metric_comparison[metric] = {
                        "version_a": val_a,
                        "version_b": val_b,
                        "difference": diff,
                        "percent_change": pct_change
                    }
            
            # Compare parameters
            params_a = dict(run_a.data.params) if run_a else {}
            params_b = dict(run_b.data.params) if run_b else {}
            
            param_changes = {}
            all_params = set(params_a.keys()) | set(params_b.keys())
            
            for param in all_params:
                val_a = params_a.get(param)
                val_b = params_b.get(param)
                if val_a != val_b:
                    param_changes[param] = {"from": val_a, "to": val_b}
            
            # Generate recommendation
            recommendation = ""
            if recommendation_metric and recommendation_metric in metric_comparison:
                comp = metric_comparison[recommendation_metric]
                if comp["percent_change"] > 5:
                    recommendation = f"Version {version_b} shows {comp['percent_change']:.1f}% improvement in {recommendation_metric}"
                elif comp["percent_change"] < -5:
                    recommendation = f"Version {version_a} performs better by {-comp['percent_change']:.1f}% in {recommendation_metric}"
                else:
                    recommendation = f"Both versions perform similarly on {recommendation_metric}"
            
            return ModelComparison(
                model_name=name,
                version_a=version_a,
                version_b=version_b,
                stage_a=mv_a.current_stage,
                stage_b=mv_b.current_stage,
                metric_comparison=metric_comparison,
                parameter_changes=param_changes,
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.error(f"Failed to compare versions: {e}")
            return None
    
    # =====================================================================
    # Model Artifacts
    # =====================================================================
    
    def download_model(
        self,
        name: str,
        version: str,
        dst_path: str
    ) -> bool:
        """Download model artifacts to local path."""
        if not self.is_available:
            return False
        
        try:
            model_uri = f"models:/{name}/{version}"
            mlflow.artifacts.download_artifacts(
                artifact_uri=model_uri,
                dst_path=dst_path
            )
            logger.info(f"Downloaded model {name}:{version} to {dst_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            return False
    
    def load_model(
        self,
        name: str,
        version: Optional[str] = None,
        stage: Optional[ModelStage] = None
    ) -> Any:
        """
        Load a model for inference.
        
        Args:
            name: Model name
            version: Specific version (overrides stage)
            stage: Stage to load from (used if version not specified)
            
        Returns:
            Loaded model
        """
        if not self.is_available:
            return None
        
        try:
            if version:
                model_uri = f"models:/{name}/{version}"
            elif stage:
                model_uri = f"models:/{name}/{stage.value}"
            else:
                model_uri = f"models:/{name}/latest"
            
            # Detect flavor and load accordingly
            mv = self._client.get_model_version(name, version or "1")
            flavor = self._detect_framework(mv.tags)
            
            if flavor == ModelFramework.SKLEARN:
                return mlflow.sklearn.load_model(model_uri)
            elif flavor == ModelFramework.PYTORCH:
                return mlflow.pytorch.load_model(model_uri)
            elif flavor == ModelFramework.TENSORFLOW:
                return mlflow.tensorflow.load_model(model_uri)
            else:
                return mlflow.pyfunc.load_model(model_uri)
                
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return None
    
    # =====================================================================
    # Model Deletion
    # =====================================================================
    
    def delete_version(self, name: str, version: str) -> bool:
        """Delete a specific model version."""
        if not self.is_available:
            return False
        
        try:
            self._client.delete_model_version(name, version)
            logger.info(f"Deleted model version: {name}:{version}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete model version: {e}")
            return False
    
    def delete_model(self, name: str) -> bool:
        """Delete entire registered model."""
        if not self.is_available:
            return False
        
        try:
            self._client.delete_registered_model(name)
            logger.info(f"Deleted model: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            return False
    
    # =====================================================================
    # Utilities
    # =====================================================================
    
    def _detect_framework(self, tags: Dict[str, str]) -> ModelFramework:
        """Detect ML framework from tags."""
        if not tags:
            return ModelFramework.CUSTOM
        
        framework_tag = tags.get("framework", "").lower()
        
        if "sklearn" in framework_tag or "scikit" in framework_tag:
            return ModelFramework.SKLEARN
        elif "pytorch" in framework_tag or "torch" in framework_tag:
            return ModelFramework.PYTORCH
        elif "tensorflow" in framework_tag or "tf" in framework_tag:
            return ModelFramework.TENSORFLOW
        elif "xgboost" in framework_tag or "xgb" in framework_tag:
            return ModelFramework.XGBOOST
        elif "lightgbm" in framework_tag or "lgb" in framework_tag:
            return ModelFramework.LIGHTGBM
        elif "onnx" in framework_tag:
            return ModelFramework.ONNX
        elif "huggingface" in framework_tag or "transformers" in framework_tag:
            return ModelFramework.HUGGINGFACE
        
        return ModelFramework.CUSTOM
    
    def set_model_tag(
        self,
        name: str,
        version: str,
        key: str,
        value: str
    ) -> bool:
        """Set a tag on a model version."""
        if not self.is_available:
            return False
        
        try:
            self._client.set_model_version_tag(name, version, key, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set model tag: {e}")
            return False
    
    def get_model_tags(self, name: str, version: str) -> Dict[str, str]:
        """Get all tags for a model version."""
        if not self.is_available:
            return {}
        
        try:
            mv = self._client.get_model_version(name, version)
            return dict(mv.tags) if mv.tags else {}
        except Exception as e:
            logger.error(f"Failed to get model tags: {e}")
            return {}


# Singleton instance
_registry: Optional[MLflowModelRegistry] = None


def get_model_registry() -> MLflowModelRegistry:
    """Get or create model registry singleton."""
    global _registry
    if _registry is None:
        _registry = MLflowModelRegistry()
    return _registry
