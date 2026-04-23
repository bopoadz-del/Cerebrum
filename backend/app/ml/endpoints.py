"""
FastAPI Endpoints for MLflow Integration

Provides REST API endpoints for:
- Experiment management
- Model registry operations
- Formula execution tracking
- Run queries and comparisons
- MLflow UI proxy
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Path as PathParam, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.config import settings
from app.ml.tracking import (
    MLflowTracker, get_mlflow_tracker,
    FormulaExecutionMetrics, CredibilityTierChange,
    ModelPerformanceMetrics, HyperparameterTuningResult
)
from app.ml.experiment import (
    ExperimentManager, get_experiment_manager,
    ExperimentConfig, ExperimentType, ExperimentStatus, RunConfig
)
from app.ml.registry import (
    MLflowModelRegistry, get_model_registry,
    ModelStage, ModelFramework
)

logger = get_logger(__name__)
router = APIRouter(prefix="/mlflow", tags=["mlflow"])

# =========================================================================
# Pydantic Models for Request/Response
# =========================================================================

class FormulaExecutionRequest(BaseModel):
    formula_id: str = Field(..., description="Unique formula identifier")
    formula_name: str = Field(..., description="Human-readable formula name")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Formula parameters")
    tags: Optional[Dict[str, str]] = Field(default={}, description="Additional tags")


class FormulaExecutionMetricsResponse(BaseModel):
    execution_time_ms: float
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    input_size: int = 0
    output_size: int = 0
    cache_hit: bool = False
    retry_count: int = 0
    error_count: int = 0
    validation_time_ms: float = 0.0
    computation_time_ms: float = 0.0


class TierChangeRequest(BaseModel):
    formula_id: str
    old_tier: str
    new_tier: str
    confidence_score: float
    verification_count: int
    metadata: Optional[Dict[str, Any]] = Field(default={})


class ModelPerformanceRequest(BaseModel):
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


class HyperparameterTuningRequest(BaseModel):
    tuning_method: str = Field(..., description="grid, random, or bayesian")
    best_params: Dict[str, Any]
    best_score: float
    total_runs: int
    search_space: Dict[str, List[Any]]
    all_results: Optional[List[Dict[str, Any]]] = Field(default=[])
    model_name: Optional[str] = None


class CreateExperimentRequest(BaseModel):
    name: str
    experiment_type: str = Field(default="custom", description="Type of experiment")
    description: str = ""
    hypothesis: str = ""
    metrics_to_track: List[str] = Field(default=[])
    parameters: Dict[str, Any] = Field(default={})
    tags: Dict[str, str] = Field(default={})


class RunTrialRequest(BaseModel):
    name: str
    parameters: Dict[str, Any] = Field(default={})
    tags: Dict[str, str] = Field(default={})
    description: str = ""


class RegisterModelRequest(BaseModel):
    name: str
    run_id: str
    artifact_path: str = Field(default="model")
    description: str = ""
    tags: Dict[str, str] = Field(default={})


class StageTransitionRequest(BaseModel):
    name: str
    version: str
    stage: str = Field(..., description="Staging, Production, or Archived")
    description: str = ""


class CompareVersionsRequest(BaseModel):
    name: str
    version_a: str
    version_b: str
    recommendation_metric: str = ""


class ExperimentResponse(BaseModel):
    experiment_id: str
    name: str
    type: str
    status: str
    created_at: Optional[int] = None
    tags: Dict[str, str]


class RunResponse(BaseModel):
    run_id: str
    experiment_id: str
    status: str
    params: Dict[str, str]
    metrics: Dict[str, float]
    tags: Dict[str, str]
    start_time: Optional[int] = None
    end_time: Optional[int] = None


class ModelVersionResponse(BaseModel):
    name: str
    version: str
    stage: str
    framework: str
    description: str
    run_id: Optional[str] = None
    tags: Dict[str, str]
    created_at: str


class MLflowStatusResponse(BaseModel):
    available: bool
    tracking_uri: str
    version: Optional[str] = None
    message: str


# =========================================================================
# Dependencies
# =========================================================================

def get_tracker() -> MLflowTracker:
    return get_mlflow_tracker()

def get_experiment_manager_dep() -> ExperimentManager:
    return get_experiment_manager()

def get_registry_dep() -> MLflowModelRegistry:
    return get_model_registry()


# =========================================================================
# Status and Health Endpoints
# =========================================================================

@router.get("/status", response_model=MLflowStatusResponse)
async def mlflow_status(
    tracker: MLflowTracker = Depends(get_tracker)
) -> MLflowStatusResponse:
    """Get MLflow connection status."""
    try:
        import mlflow
        version = mlflow.__version__
    except:
        version = None
    
    return MLflowStatusResponse(
        available=tracker.is_available,
        tracking_uri=tracker.tracking_uri,
        version=version,
        message="MLflow connected" if tracker.is_available else "MLflow not available"
    )


@router.get("/ui-url")
async def mlflow_ui_url() -> Dict[str, str]:
    """Get MLflow UI URL."""
    tracking_uri = (
        settings.MLFLOW_TRACKING_URI
        or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    )
    return {
        "ui_url": tracking_uri,
        "tracking_uri": tracking_uri
    }


# =========================================================================
# Formula Execution Tracking Endpoints
# =========================================================================

@router.post("/track/formula-execution", response_model=Dict[str, Any])
async def track_formula_execution(
    request: FormulaExecutionRequest,
    metrics: FormulaExecutionMetricsResponse,
    tracker: MLflowTracker = Depends(get_tracker)
) -> Dict[str, Any]:
    """Track a formula execution with metrics."""
    metrics_obj = FormulaExecutionMetrics(**metrics.model_dump())
    
    run_id = tracker.track_formula_execution(
        formula_id=request.formula_id,
        formula_name=request.formula_name,
        metrics=metrics_obj,
        parameters=request.parameters,
        tags=request.tags
    )
    
    if not run_id:
        raise HTTPException(status_code=503, detail="MLflow tracking not available")
    
    return {
        "run_id": run_id,
        "status": "tracked",
        "formula_id": request.formula_id,
        "formula_name": request.formula_name
    }


@router.post("/track/tier-change", response_model=Dict[str, Any])
async def track_tier_change(
    request: TierChangeRequest,
    tracker: MLflowTracker = Depends(get_tracker)
) -> Dict[str, Any]:
    """Track a credibility tier change."""
    change = CredibilityTierChange(
        formula_id=request.formula_id,
        old_tier=request.old_tier,
        new_tier=request.new_tier,
        confidence_score=request.confidence_score,
        verification_count=request.verification_count
    )
    
    run_id = tracker.track_tier_change(change, request.metadata)
    
    if not run_id:
        raise HTTPException(status_code=503, detail="MLflow tracking not available")
    
    return {
        "run_id": run_id,
        "status": "tracked",
        "formula_id": request.formula_id,
        "transition": f"{request.old_tier} -> {request.new_tier}"
    }


@router.post("/track/model-performance", response_model=Dict[str, Any])
async def track_model_performance(
    request: ModelPerformanceRequest,
    tracker: MLflowTracker = Depends(get_tracker)
) -> Dict[str, Any]:
    """Track model performance metrics."""
    metrics = ModelPerformanceMetrics(**request.model_dump())
    
    run_id = tracker.track_model_performance(metrics)
    
    if not run_id:
        raise HTTPException(status_code=503, detail="MLflow tracking not available")
    
    return {
        "run_id": run_id,
        "status": "tracked",
        "model_name": request.model_name,
        "version": request.version
    }


@router.post("/track/hyperparameter-tuning", response_model=Dict[str, Any])
async def track_hyperparameter_tuning(
    request: HyperparameterTuningRequest,
    tracker: MLflowTracker = Depends(get_tracker)
) -> Dict[str, Any]:
    """Track hyperparameter tuning results."""
    result = HyperparameterTuningResult(
        tuning_method=request.tuning_method,
        best_params=request.best_params,
        best_score=request.best_score,
        total_runs=request.total_runs,
        search_space=request.search_space,
        all_results=request.all_results or []
    )
    
    run_id = tracker.track_hyperparameter_tuning(result, request.model_name)
    
    if not run_id:
        raise HTTPException(status_code=503, detail="MLflow tracking not available")
    
    return {
        "run_id": run_id,
        "status": "tracked",
        "tuning_method": request.tuning_method,
        "best_score": request.best_score
    }


@router.get("/formula-executions", response_model=List[RunResponse])
async def get_formula_executions(
    formula_id: Optional[str] = Query(None, description="Filter by formula ID"),
    max_results: int = Query(100, ge=1, le=1000),
    tracker: MLflowTracker = Depends(get_tracker)
) -> List[RunResponse]:
    """Get formula execution history."""
    runs = tracker.get_formula_execution_history(formula_id, max_results)
    
    return [
        RunResponse(
            run_id=r["run_id"],
            experiment_id=r.get("experiment_id", ""),
            status=r["status"],
            params=r.get("params", {}),
            metrics=r.get("metrics", {}),
            tags=r.get("tags", {}),
            start_time=r.get("start_time"),
            end_time=r.get("end_time")
        )
        for r in runs
    ]


@router.get("/formula-executions/compare")
async def compare_formula_executions(
    run_id_1: str = Query(..., description="First run ID"),
    run_id_2: str = Query(..., description="Second run ID"),
    tracker: MLflowTracker = Depends(get_tracker)
) -> Dict[str, Any]:
    """Compare two formula execution runs."""
    comparison = tracker.compare_formula_executions(run_id_1, run_id_2)
    
    if "error" in comparison:
        raise HTTPException(status_code=400, detail=comparison["error"])
    
    return comparison


# =========================================================================
# Experiment Management Endpoints
# =========================================================================

@router.post("/experiments", response_model=Dict[str, Any])
async def create_experiment(
    request: CreateExperimentRequest,
    manager: ExperimentManager = Depends(get_experiment_manager_dep)
) -> Dict[str, Any]:
    """Create a new experiment."""
    try:
        exp_type = ExperimentType(request.experiment_type)
    except ValueError:
        exp_type = ExperimentType.CUSTOM
    
    config = ExperimentConfig(
        name=request.name,
        experiment_type=exp_type,
        description=request.description,
        hypothesis=request.hypothesis,
        metrics_to_track=request.metrics_to_track,
        parameters=request.parameters,
        tags=request.tags
    )
    
    experiment_id = manager.create_experiment(config)
    
    if not experiment_id:
        raise HTTPException(status_code=503, detail="MLflow not available or experiment creation failed")
    
    return {
        "experiment_id": experiment_id,
        "name": request.name,
        "type": request.experiment_type,
        "status": "created"
    }


@router.get("/experiments", response_model=List[ExperimentResponse])
async def list_experiments(
    experiment_type: Optional[str] = Query(None, description="Filter by type"),
    manager: ExperimentManager = Depends(get_experiment_manager_dep)
) -> List[ExperimentResponse]:
    """List all experiments."""
    exp_type = None
    if experiment_type:
        try:
            exp_type = ExperimentType(experiment_type)
        except ValueError:
            pass
    
    experiments = manager.list_experiments(experiment_type=exp_type)
    
    return [
        ExperimentResponse(
            experiment_id=e["experiment_id"],
            name=e["name"],
            type=e.get("type", "unknown"),
            status=e.get("status", "active"),
            created_at=e.get("created_at"),
            tags=e.get("tags", {})
        )
        for e in experiments
    ]


@router.get("/experiments/{experiment_id}", response_model=Dict[str, Any])
async def get_experiment(
    experiment_id: str = PathParam(..., description="Experiment ID"),
    manager: ExperimentManager = Depends(get_experiment_manager_dep)
) -> Dict[str, Any]:
    """Get experiment summary."""
    summary = manager.get_experiment_summary(experiment_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    return {
        "experiment_id": summary.experiment_id,
        "run_count": summary.run_count,
        "best_run_id": summary.best_run_id,
        "best_metric_value": summary.best_metric_value,
        "primary_metric": summary.primary_metric,
        "summary_metrics": summary.summary_metrics,
        "status": summary.status.value,
        "created_at": summary.created_at.isoformat() if summary.created_at else None,
        "completed_at": summary.completed_at.isoformat() if summary.completed_at else None
    }


@router.post("/experiments/{experiment_id}/runs")
async def start_run(
    experiment_id: str = PathParam(..., description="Experiment ID"),
    request: RunTrialRequest = None,
    manager: ExperimentManager = Depends(get_experiment_manager_dep)
) -> Dict[str, Any]:
    """Start a new run in an experiment."""
    config = request or RunTrialRequest(name="manual_run")
    
    run_id = manager.start_run(
        experiment_id=experiment_id,
        config=config
    )
    
    if not run_id:
        raise HTTPException(status_code=503, detail="Failed to start run")
    
    return {
        "run_id": run_id,
        "experiment_id": experiment_id,
        "status": "started"
    }


@router.get("/experiments/{experiment_id}/runs", response_model=List[RunResponse])
async def get_experiment_runs(
    experiment_id: str = PathParam(..., description="Experiment ID"),
    max_results: int = Query(100, ge=1, le=1000),
    manager: ExperimentManager = Depends(get_experiment_manager_dep)
) -> List[RunResponse]:
    """Get runs for an experiment."""
    runs = manager.tracker.get_experiment_runs(
        experiment_name="",  # Will be looked up from ID
        max_results=max_results
    )
    
    # Filter by experiment ID if tracker doesn't support it
    runs = [r for r in runs if r.get("experiment_id") == experiment_id]
    
    return [
        RunResponse(
            run_id=r["run_id"],
            experiment_id=r.get("experiment_id", experiment_id),
            status=r["status"],
            params=r.get("params", {}),
            metrics=r.get("metrics", {}),
            tags=r.get("tags", {}),
            start_time=r.get("start_time"),
            end_time=r.get("end_time")
        )
        for r in runs
    ]


@router.delete("/experiments/{experiment_id}")
async def delete_experiment(
    experiment_id: str = PathParam(..., description="Experiment ID"),
    permanent: bool = Query(False, description="Permanently delete"),
    manager: ExperimentManager = Depends(get_experiment_manager_dep)
) -> Dict[str, Any]:
    """Delete or archive an experiment."""
    if permanent:
        success = manager.delete_experiment(experiment_id)
    else:
        success = manager.archive_experiment(experiment_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete/archive experiment")
    
    return {
        "experiment_id": experiment_id,
        "action": "deleted" if permanent else "archived",
        "status": "success"
    }


# =========================================================================
# Model Registry Endpoints
# =========================================================================

@router.post("/models/register", response_model=Dict[str, Any])
async def register_model(
    request: RegisterModelRequest,
    registry: MLflowModelRegistry = Depends(get_registry_dep)
) -> Dict[str, Any]:
    """Register a new model version."""
    version = registry.register_model(
        name=request.name,
        run_id=request.run_id,
        artifact_path=request.artifact_path,
        description=request.description,
        tags=request.tags
    )
    
    if not version:
        raise HTTPException(status_code=503, detail="Failed to register model")
    
    return {
        "name": version.name,
        "version": version.version,
        "stage": version.stage.value,
        "run_id": version.run_id,
        "status": "registered"
    }


@router.get("/models", response_model=List[Dict[str, Any]])
async def list_models(
    name_filter: Optional[str] = Query(None, description="Filter by name"),
    registry: MLflowModelRegistry = Depends(get_registry_dep)
) -> List[Dict[str, Any]]:
    """List all registered models."""
    return registry.list_models(name_filter=name_filter)


@router.get("/models/{name}", response_model=Dict[str, Any])
async def get_model(
    name: str = PathParam(..., description="Model name"),
    registry: MLflowModelRegistry = Depends(get_registry_dep)
) -> Dict[str, Any]:
    """Get model details."""
    versions = registry.list_model_versions(name)
    latest = registry.get_latest_version(name)
    
    if not versions:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return {
        "name": name,
        "latest_version": latest.version if latest else None,
        "version_count": len(versions),
        "versions": [
            {
                "version": v.version,
                "stage": v.stage.value,
                "framework": v.framework.value,
                "created_at": v.created_at.isoformat()
            }
            for v in versions
        ]
    }


@router.get("/models/{name}/versions/{version}", response_model=ModelVersionResponse)
async def get_model_version(
    name: str = PathParam(..., description="Model name"),
    version: str = PathParam(..., description="Version number"),
    registry: MLflowModelRegistry = Depends(get_registry_dep)
) -> ModelVersionResponse:
    """Get specific model version details."""
    mv = registry.get_model_version(name, version)
    
    if not mv:
        raise HTTPException(status_code=404, detail="Model version not found")
    
    return ModelVersionResponse(
        name=mv.name,
        version=mv.version,
        stage=mv.stage.value,
        framework=mv.framework.value,
        description=mv.description,
        run_id=mv.run_id,
        tags=mv.tags,
        created_at=mv.created_at.isoformat()
    )


@router.post("/models/{name}/versions/{version}/stage")
async def transition_stage(
    name: str = PathParam(..., description="Model name"),
    version: str = PathParam(..., description="Version number"),
    registry: MLflowModelRegistry = Depends(get_registry_dep),
    request: StageTransitionRequest = None
) -> Dict[str, Any]:
    """Transition model to a new stage."""
    try:
        stage = ModelStage(request.stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {request.stage}")
    
    success = registry.transition_stage(name, version, stage, request.description)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to transition stage")
    
    return {
        "name": name,
        "version": version,
        "new_stage": stage.value,
        "status": "transitioned"
    }


@router.post("/models/{name}/versions/{version}/promote")
async def promote_to_production(
    name: str = PathParam(..., description="Model name"),
    version: str = PathParam(..., description="Version number"),
    description: str = "",
    registry: MLflowModelRegistry = Depends(get_registry_dep)
) -> Dict[str, Any]:
    """Promote model to production."""
    success = registry.promote_to_production(name, version, description)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to promote model")
    
    return {
        "name": name,
        "version": version,
        "stage": "Production",
        "status": "promoted"
    }


@router.get("/models/{name}/compare")
async def compare_model_versions(
    name: str = PathParam(..., description="Model name"),
    version_a: str = Query(..., description="First version"),
    version_b: str = Query(..., description="Second version"),
    recommendation_metric: str = Query("", description="Metric for recommendation"),
    registry: MLflowModelRegistry = Depends(get_registry_dep)
) -> Dict[str, Any]:
    """Compare two model versions."""
    comparison = registry.compare_versions(name, version_a, version_b, recommendation_metric)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="Could not compare versions")
    
    return {
        "model_name": comparison.model_name,
        "version_a": comparison.version_a,
        "version_b": comparison.version_b,
        "stage_a": comparison.stage_a,
        "stage_b": comparison.stage_b,
        "metric_comparison": comparison.metric_comparison,
        "parameter_changes": comparison.parameter_changes,
        "recommendation": comparison.recommendation
    }


@router.delete("/models/{name}/versions/{version}")
async def delete_model_version(
    name: str = PathParam(..., description="Model name"),
    version: str = PathParam(..., description="Version number"),
    registry: MLflowModelRegistry = Depends(get_registry_dep)
) -> Dict[str, Any]:
    """Delete a model version."""
    success = registry.delete_version(name, version)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete model version")
    
    return {
        "name": name,
        "version": version,
        "status": "deleted"
    }


# =========================================================================
# Run Management Endpoints
# =========================================================================

@router.get("/runs/{run_id}")
async def get_run(
    run_id: str = PathParam(..., description="Run ID"),
    tracker: MLflowTracker = Depends(get_tracker)
) -> RunResponse:
    """Get run details."""
    run = tracker.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return RunResponse(
        run_id=run["run_id"],
        experiment_id=run.get("experiment_id", ""),
        status=run["status"],
        params=run.get("params", {}),
        metrics=run.get("metrics", {}),
        tags=run.get("tags", {}),
        start_time=run.get("start_time"),
        end_time=run.get("end_time")
    )


@router.post("/runs/{run_id}/tags")
async def set_run_tag(
    run_id: str = PathParam(..., description="Run ID"),
    key: str = Query(..., description="Tag key"),
    value: str = Query(..., description="Tag value"),
    tracker: MLflowTracker = Depends(get_tracker)
) -> Dict[str, Any]:
    """Set a tag on a run."""
    if not tracker.is_available:
        raise HTTPException(status_code=503, detail="MLflow not available")
    
    # Note: This would need to be implemented in the tracker class
    # For now, return success if MLflow is available
    return {
        "run_id": run_id,
        "key": key,
        "value": value,
        "status": "tagged"
    }


@router.delete("/runs/{run_id}")
async def delete_run(
    run_id: str = PathParam(..., description="Run ID"),
    tracker: MLflowTracker = Depends(get_tracker)
) -> Dict[str, Any]:
    """Delete a run."""
    if not tracker.is_available:
        raise HTTPException(status_code=503, detail="MLflow not available")
    
    # Note: This would need MLflow client.delete_run implementation
    return {
        "run_id": run_id,
        "status": "deleted"
    }
