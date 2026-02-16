"""
ML Tinker API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from app.api.deps import get_current_user
from app.ml.experiment_tracking import MLflowTracker, Experiment, Run
from app.ml.model_registry import ModelRegistry, ModelVersion, ModelStage, ModelFramework
from app.ml.automl import AutoMLRunner, AutoMLConfig, AutoMLBackend, SearchAlgorithm
from app.ml.feature_store import FeatureStore
from app.ml.data_versioning import DataVersionControl
from app.ml.ab_testing import ABTestFramework
from app.ml.drift_detection import DriftDetector, DriftType
from app.ml.retraining import RetrainingOrchestrator, RetrainingTriggerType
from app.ml.explainability import ExplainabilityEngine, ExplanationMethod


router = APIRouter(prefix="/ml", tags=["ml"])


# Pydantic models
class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = []


class RunCreate(BaseModel):
    experiment_name: Optional[str] = None
    run_name: Optional[str] = None
    params: Optional[Dict[str, Any]] = {}
    tags: Optional[List[str]] = []


class LogMetricsRequest(BaseModel):
    metrics: Dict[str, float]


class LogParamsRequest(BaseModel):
    params: Dict[str, Any]


class ModelRegisterRequest(BaseModel):
    model_name: str
    version: str
    framework: str
    description: str
    metrics: Optional[Dict[str, float]] = {}
    parameters: Optional[Dict[str, Any]] = {}
    tags: Optional[List[str]] = []


class StageTransitionRequest(BaseModel):
    new_stage: str
    reason: Optional[str] = ""


class AutoMLStartRequest(BaseModel):
    experiment_name: str
    backend: str = "optuna"
    search_algorithm: str = "bayesian"
    max_iterations: int = 100
    max_time_seconds: Optional[int] = None
    metric: str = "val_loss"
    mode: str = "min"


class FeatureViewCreate(BaseModel):
    name: str
    entities: List[str]
    features: List[Dict[str, Any]]
    ttl_days: int = 7
    online: bool = True


class ABTestCreate(BaseModel):
    name: str
    description: str
    variants: List[Dict[str, Any]]
    primary_metric: str
    secondary_metrics: Optional[List[str]] = []
    min_sample_size: int = 1000
    max_duration_days: int = 30


class DriftCheckRequest(BaseModel):
    model_name: str
    model_version: str
    drift_type: str = "data_drift"


class ExplainRequest(BaseModel):
    model_name: str
    model_version: str
    input_data: Dict[str, Any]
    method: str = "shap"
    num_features: int = 10


# Dependencies
async def get_mlflow_tracker():
    return MLflowTracker(tracking_uri="http://localhost:5000")


async def get_model_registry():
    return ModelRegistry()


async def get_automl_runner():
    return AutoMLRunner()


async def get_feature_store():
    return FeatureStore()


async def get_data_versioning():
    return DataVersionControl()


async def get_ab_testing():
    return ABTestFramework()


async def get_drift_detector():
    return DriftDetector()


async def get_retraining_orchestrator():
    return RetrainingOrchestrator()


async def get_explainability_engine():
    return ExplainabilityEngine()


# Experiment tracking endpoints
@router.post("/experiments")
async def create_experiment(
    request: ExperimentCreate,
    tracker: MLflowTracker = Depends(get_mlflow_tracker),
    current_user = Depends(get_current_user)
):
    """Create a new MLflow experiment."""
    experiment = await tracker.create_experiment(
        name=request.name,
        description=request.description,
        tags=request.tags
    )
    return {"experiment_id": experiment.experiment_id, "name": experiment.name}


@router.get("/experiments")
async def list_experiments(
    tracker: MLflowTracker = Depends(get_mlflow_tracker),
    current_user = Depends(get_current_user)
):
    """List all experiments."""
    experiments = await tracker.list_experiments()
    return {"experiments": [e.__dict__ for e in experiments]}


@router.post("/runs/start")
async def start_run(
    request: RunCreate,
    tracker: MLflowTracker = Depends(get_mlflow_tracker),
    current_user = Depends(get_current_user)
):
    """Start a new MLflow run."""
    run = await tracker.start_run(
        experiment_name=request.experiment_name,
        run_name=request.run_name,
        params=request.params,
        tags=request.tags
    )
    return {"run_id": run.run_id, "experiment_id": run.experiment_id}


@router.post("/runs/{run_id}/metrics")
async def log_metrics(
    run_id: str,
    request: LogMetricsRequest,
    tracker: MLflowTracker = Depends(get_mlflow_tracker),
    current_user = Depends(get_current_user)
):
    """Log metrics for a run."""
    await tracker.log_metrics(run_id, request.metrics)
    return {"status": "logged"}


@router.post("/runs/{run_id}/params")
async def log_params(
    run_id: str,
    request: LogParamsRequest,
    tracker: MLflowTracker = Depends(get_mlflow_tracker),
    current_user = Depends(get_current_user)
):
    """Log parameters for a run."""
    await tracker.log_params(run_id, request.params)
    return {"status": "logged"}


@router.post("/runs/{run_id}/end")
async def end_run(
    run_id: str,
    status: str = "completed",
    tracker: MLflowTracker = Depends(get_mlflow_tracker),
    current_user = Depends(get_current_user)
):
    """End a run."""
    await tracker.end_run(run_id, status)
    return {"status": "ended"}


# Model registry endpoints
@router.post("/models/register")
async def register_model(
    request: ModelRegisterRequest,
    registry: ModelRegistry = Depends(get_model_registry),
    current_user = Depends(get_current_user)
):
    """Register a new model version."""
    version = await registry.register_model(
        model_name=request.model_name,
        version=request.version,
        framework=ModelFramework(request.framework),
        description=request.description,
        artifacts=[],
        metrics=request.metrics,
        parameters=request.parameters,
        tags=request.tags,
        created_by=current_user["id"]
    )
    return {"version_id": version.version_id, "full_name": version.full_name}


@router.get("/models")
async def list_models(
    stage: Optional[str] = None,
    framework: Optional[str] = None,
    registry: ModelRegistry = Depends(get_model_registry),
    current_user = Depends(get_current_user)
):
    """List registered models."""
    models = await registry.list_models(
        stage=ModelStage(stage) if stage else None,
        framework=ModelFramework(framework) if framework else None
    )
    return {"models": [m.__dict__ for m in models]}


@router.post("/models/{model_name}/versions/{version}/transition")
async def transition_stage(
    model_name: str,
    version: str,
    request: StageTransitionRequest,
    registry: ModelRegistry = Depends(get_model_registry),
    current_user = Depends(get_current_user)
):
    """Transition model to new stage."""
    model_version = await registry.transition_stage(
        model_name=model_name,
        version=version,
        new_stage=ModelStage(request.new_stage),
        reason=request.reason
    )
    return {"version_id": model_version.version_id, "new_stage": model_version.stage.value}


# AutoML endpoints
@router.post("/automl/start")
async def start_automl(
    request: AutoMLStartRequest,
    background_tasks: BackgroundTasks,
    automl: AutoMLRunner = Depends(get_automl_runner),
    current_user = Depends(get_current_user)
):
    """Start an AutoML optimization."""
    config = AutoMLConfig(
        experiment_name=request.experiment_name,
        backend=AutoMLBackend(request.backend),
        search_algorithm=SearchAlgorithm(request.search_algorithm),
        max_iterations=request.max_iterations,
        max_time_seconds=request.max_time_seconds,
        metric=request.metric,
        mode=request.mode
    )
    
    run_id = await automl.create_study(config)
    
    return {"run_id": run_id, "status": "started"}


@router.get("/automl/{run_id}/status")
async def get_automl_status(
    run_id: str,
    automl: AutoMLRunner = Depends(get_automl_runner),
    current_user = Depends(get_current_user)
):
    """Get AutoML run status."""
    status = await automl.get_run_status(run_id)
    return status


# Feature store endpoints
@router.post("/features/views")
async def create_feature_view(
    request: FeatureViewCreate,
    store: FeatureStore = Depends(get_feature_store),
    current_user = Depends(get_current_user)
):
    """Create a feature view."""
    feature_view = await store.register_feature_view(
        name=request.name,
        entities=request.entities,
        features=request.features,
        ttl_days=request.ttl_days,
        online=request.online,
        owner=current_user["id"]
    )
    return {"view_name": feature_view.name, "feature_count": len(feature_view.features)}


@router.get("/features/views")
async def list_feature_views(
    store: FeatureStore = Depends(get_feature_store),
    current_user = Depends(get_current_user)
):
    """List feature views."""
    views = await store.list_feature_views()
    return {"views": views}


# A/B testing endpoints
@router.post("/ab-tests")
async def create_ab_test(
    request: ABTestCreate,
    ab_testing: ABTestFramework = Depends(get_ab_testing),
    current_user = Depends(get_current_user)
):
    """Create an A/B test."""
    experiment = await ab_testing.create_experiment(
        name=request.name,
        description=request.description,
        variants=request.variants,
        primary_metric=request.primary_metric,
        secondary_metrics=request.secondary_metrics,
        min_sample_size=request.min_sample_size,
        max_duration_days=request.max_duration_days,
        created_by=current_user["id"]
    )
    return {"experiment_id": experiment.experiment_id, "status": experiment.status.value}


@router.post("/ab-tests/{experiment_id}/start")
async def start_ab_test(
    experiment_id: str,
    ab_testing: ABTestFramework = Depends(get_ab_testing),
    current_user = Depends(get_current_user)
):
    """Start an A/B test."""
    experiment = await ab_testing.start_experiment(experiment_id)
    return {"experiment_id": experiment_id, "status": experiment.status.value}


@router.get("/ab-tests/{experiment_id}/results")
async def get_ab_test_results(
    experiment_id: str,
    ab_testing: ABTestFramework = Depends(get_ab_testing),
    current_user = Depends(get_current_user)
):
    """Get A/B test results."""
    results = await ab_testing.analyze_results(experiment_id)
    return {
        "experiment_id": results.experiment_id,
        "variant_results": results.variant_results,
        "recommendation": results.recommendation
    }


# Drift detection endpoints
@router.post("/drift/check")
async def check_drift(
    request: DriftCheckRequest,
    detector: DriftDetector = Depends(get_drift_detector),
    current_user = Depends(get_current_user)
):
    """Check for model drift."""
    # Placeholder - actual implementation would need data
    return {"status": "checked", "drift_detected": False}


@router.get("/drift/history")
async def get_drift_history(
    model_name: Optional[str] = None,
    detector: DriftDetector = Depends(get_drift_detector),
    current_user = Depends(get_current_user)
):
    """Get drift detection history."""
    history = await detector.get_drift_history(model_name=model_name)
    return {"history": [h.__dict__ for h in history]}


# Explainability endpoints
@router.post("/explain")
async def explain_prediction(
    request: ExplainRequest,
    engine: ExplainabilityEngine = Depends(get_explainability_engine),
    current_user = Depends(get_current_user)
):
    """Generate explanation for a prediction."""
    explanation = await engine.explain_prediction(
        model_name=request.model_name,
        model_version=request.model_version,
        input_data=request.input_data,
        prediction=None,  # Would come from model
        method=ExplanationMethod(request.method),
        num_features=request.num_features
    )
    return {
        "explanation_id": explanation.explanation_id,
        "feature_contributions": [
            {
                "feature_name": c.feature_name,
                "value": c.value,
                "contribution": c.contribution
            }
            for c in explanation.feature_contributions
        ],
        "visualization_data": explanation.visualization_data
    }


# Retraining endpoints
@router.post("/retraining/triggers")
async def create_retraining_trigger(
    model_name: str,
    trigger_type: str,
    conditions: Dict[str, Any],
    orchestrator: RetrainingOrchestrator = Depends(get_retraining_orchestrator),
    current_user = Depends(get_current_user)
):
    """Create a retraining trigger."""
    trigger = await orchestrator.create_trigger(
        model_name=model_name,
        trigger_type=RetrainingTriggerType(trigger_type),
        conditions=conditions
    )
    return {"trigger_id": trigger.trigger_id, "enabled": trigger.enabled}


@router.get("/retraining/jobs")
async def list_retraining_jobs(
    model_name: Optional[str] = None,
    orchestrator: RetrainingOrchestrator = Depends(get_retraining_orchestrator),
    current_user = Depends(get_current_user)
):
    """List retraining jobs."""
    jobs = await orchestrator.list_jobs(model_name=model_name)
    return {"jobs": jobs}
