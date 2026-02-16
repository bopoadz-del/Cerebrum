"""
Model registry with staging (dev/staging/prod) for ML models.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json
import hashlib
import uuid


class ModelStage(Enum):
    """Model lifecycle stages."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class ModelFramework(Enum):
    """Supported ML frameworks."""
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    SKLEARN = "sklearn"
    ONNX = "onnx"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


@dataclass
class ModelVersion:
    """Model version metadata."""
    version_id: str
    model_name: str
    version: str
    stage: ModelStage
    framework: ModelFramework
    description: str
    metrics: Dict[str, float] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    signature: Dict[str, Any] = field(default_factory=dict)
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def full_name(self) -> str:
        """Get full model name with version."""
        return f"{self.model_name}:{self.version}"


@dataclass
class ModelArtifact:
    """Model artifact file."""
    artifact_id: str
    version_id: str
    name: str
    path: str
    checksum: str
    size_bytes: int
    content_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    """Central registry for ML models with staging support."""
    
    def __init__(self, storage_backend: Optional[Any] = None):
        self.storage = storage_backend
        self._models: Dict[str, List[ModelVersion]] = {}
        self._artifacts: Dict[str, ModelArtifact] = {}
        self._stage_callbacks: Dict[ModelStage, List[Callable]] = {
            stage: [] for stage in ModelStage
        }
    
    async def register_model(
        self,
        model_name: str,
        version: str,
        framework: ModelFramework,
        description: str,
        artifacts: List[Dict[str, Any]],
        metrics: Optional[Dict[str, float]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        created_by: str = "",
        stage: ModelStage = ModelStage.DEVELOPMENT
    ) -> ModelVersion:
        """Register a new model version."""
        
        version_id = str(uuid.uuid4())
        
        # Create model version
        model_version = ModelVersion(
            version_id=version_id,
            model_name=model_name,
            version=version,
            stage=stage,
            framework=framework,
            description=description,
            metrics=metrics or {},
            parameters=parameters or {},
            tags=tags or [],
            created_by=created_by
        )
        
        # Store artifacts
        for artifact_data in artifacts:
            artifact = await self._store_artifact(
                version_id=version_id,
                name=artifact_data["name"],
                path=artifact_data["path"],
                content_type=artifact_data.get("content_type", "application/octet-stream"),
                metadata=artifact_data.get("metadata", {})
            )
            model_version.artifacts.append(artifact.artifact_id)
        
        # Add to registry
        if model_name not in self._models:
            self._models[model_name] = []
        self._models[model_name].append(model_version)
        
        return model_version
    
    async def _store_artifact(
        self,
        version_id: str,
        name: str,
        path: str,
        content_type: str,
        metadata: Dict[str, Any]
    ) -> ModelArtifact:
        """Store model artifact."""
        
        # Calculate checksum
        checksum = await self._calculate_checksum(path)
        
        # Get file size
        size_bytes = await self._get_file_size(path)
        
        artifact = ModelArtifact(
            artifact_id=str(uuid.uuid4()),
            version_id=version_id,
            name=name,
            path=path,
            checksum=checksum,
            size_bytes=size_bytes,
            content_type=content_type,
            metadata=metadata
        )
        
        self._artifacts[artifact.artifact_id] = artifact
        
        return artifact
    
    async def _calculate_checksum(self, path: str) -> str:
        """Calculate file checksum."""
        # Placeholder - in production, use actual file hashing
        return hashlib.sha256(path.encode()).hexdigest()
    
    async def _get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        # Placeholder - in production, use actual file system
        return 0
    
    async def transition_stage(
        self,
        model_name: str,
        version: str,
        new_stage: ModelStage,
        reason: str = ""
    ) -> ModelVersion:
        """Transition model to new stage."""
        
        model_version = await self.get_model_version(model_name, version)
        if not model_version:
            raise ValueError(f"Model {model_name}:{version} not found")
        
        old_stage = model_version.stage
        model_version.stage = new_stage
        model_version.updated_at = datetime.utcnow()
        
        # Execute stage transition callbacks
        for callback in self._stage_callbacks.get(new_stage, []):
            await callback(model_version, old_stage, reason)
        
        return model_version
    
    def on_stage_transition(
        self,
        stage: ModelStage,
        callback: Callable[[ModelVersion, ModelStage, str], None]
    ):
        """Register callback for stage transition."""
        self._stage_callbacks[stage].append(callback)
    
    async def get_model_version(
        self,
        model_name: str,
        version: str
    ) -> Optional[ModelVersion]:
        """Get specific model version."""
        
        versions = self._models.get(model_name, [])
        for v in versions:
            if v.version == version:
                return v
        return None
    
    async def get_latest_version(
        self,
        model_name: str,
        stage: Optional[ModelStage] = None
    ) -> Optional[ModelVersion]:
        """Get latest model version, optionally filtered by stage."""
        
        versions = self._models.get(model_name, [])
        
        if stage:
            versions = [v for v in versions if v.stage == stage]
        
        if not versions:
            return None
        
        # Sort by created_at descending
        return sorted(versions, key=lambda v: v.created_at, reverse=True)[0]
    
    async def list_models(
        self,
        stage: Optional[ModelStage] = None,
        framework: Optional[ModelFramework] = None,
        tags: Optional[List[str]] = None
    ) -> List[ModelVersion]:
        """List all models with optional filtering."""
        
        all_versions = []
        for versions in self._models.values():
            all_versions.extend(versions)
        
        # Apply filters
        if stage:
            all_versions = [v for v in all_versions if v.stage == stage]
        
        if framework:
            all_versions = [v for v in all_versions if v.framework == framework]
        
        if tags:
            all_versions = [
                v for v in all_versions
                if any(tag in v.tags for tag in tags)
            ]
        
        return sorted(all_versions, key=lambda v: v.created_at, reverse=True)
    
    async def compare_versions(
        self,
        model_name: str,
        version_a: str,
        version_b: str
    ) -> Dict[str, Any]:
        """Compare two model versions."""
        
        v_a = await self.get_model_version(model_name, version_a)
        v_b = await self.get_model_version(model_name, version_b)
        
        if not v_a or not v_b:
            raise ValueError("One or both versions not found")
        
        # Compare metrics
        metric_comparison = {}
        all_metrics = set(v_a.metrics.keys()) | set(v_b.metrics.keys())
        
        for metric in all_metrics:
            val_a = v_a.metrics.get(metric)
            val_b = v_b.metrics.get(metric)
            
            if val_a is not None and val_b is not None:
                diff = val_b - val_a
                pct_change = (diff / val_a * 100) if val_a != 0 else 0
                metric_comparison[metric] = {
                    "version_a": val_a,
                    "version_b": val_b,
                    "difference": diff,
                    "percent_change": pct_change
                }
        
        return {
            "model_name": model_name,
            "version_a": version_a,
            "version_b": version_b,
            "stage_a": v_a.stage.value,
            "stage_b": v_b.stage.value,
            "metric_comparison": metric_comparison,
            "parameter_changes": self._compare_parameters(v_a.parameters, v_b.parameters),
            "created_a": v_a.created_at.isoformat(),
            "created_b": v_b.created_at.isoformat()
        }
    
    def _compare_parameters(
        self,
        params_a: Dict[str, Any],
        params_b: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare model parameters."""
        
        changes = {}
        all_keys = set(params_a.keys()) | set(params_b.keys())
        
        for key in all_keys:
            val_a = params_a.get(key)
            val_b = params_b.get(key)
            
            if val_a != val_b:
                changes[key] = {"from": val_a, "to": val_b}
        
        return changes
    
    async def delete_version(
        self,
        model_name: str,
        version: str,
        permanent: bool = False
    ) -> bool:
        """Delete or archive a model version."""
        
        model_version = await self.get_model_version(model_name, version)
        if not model_version:
            return False
        
        if permanent:
            # Remove from registry
            self._models[model_name] = [
                v for v in self._models[model_name]
                if v.version != version
            ]
            
            # Remove artifacts
            for artifact_id in model_version.artifacts:
                if artifact_id in self._artifacts:
                    del self._artifacts[artifact_id]
        else:
            # Archive
            model_version.stage = ModelStage.ARCHIVED
            model_version.updated_at = datetime.utcnow()
        
        return True
    
    async def get_model_lineage(
        self,
        model_name: str,
        version: str
    ) -> Dict[str, Any]:
        """Get model lineage and dependencies."""
        
        model_version = await self.get_model_version(model_name, version)
        if not model_version:
            raise ValueError("Model version not found")
        
        return {
            "model_name": model_name,
            "version": version,
            "version_id": model_version.version_id,
            "parent_versions": [],  # Placeholder for actual lineage tracking
            "derived_versions": [],
            "dependencies": model_version.dependencies,
            "artifacts": [
                {
                    "id": aid,
                    "name": self._artifacts[aid].name if aid in self._artifacts else "unknown"
                }
                for aid in model_version.artifacts
            ]
        }
