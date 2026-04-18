# MLflow Integration for Cerebrum

This directory contains MLflow integration for experiment tracking, model registry, and ML lifecycle management.

## Overview

The MLflow integration provides:

1. **Experiment Tracking** - Track formula executions, metrics, and artifacts
2. **Model Registry** - Version and stage ML models (dev/staging/prod)
3. **Credibility Tier Tracking** - Monitor formula credibility changes over time
4. **Hyperparameter Tuning** - Track hyperparameter search results
5. **REST API** - FastAPI endpoints for MLflow operations

## Quick Start

### Option 1: Start Core Services Only
```bash
docker-compose -f docker-compose.local.yml up -d
```

### Option 2: Start with MLflow
```bash
# Start MLflow stack first
docker-compose -f docker-compose.mlflow.yml up -d

# Then start Cerebrum (connects to MLflow network)
docker-compose -f docker-compose.local.yml up -d
```

### Option 3: Start Everything
```bash
docker-compose -f docker-compose.local.yml -f docker-compose.mlflow.yml up -d
```

## Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Cerebrum API | http://localhost:8000 | Main API server |
| Cerebrum Frontend | http://localhost:5173 | Web UI |
| MLflow UI | http://localhost:5000 | MLflow tracking UI |
| MLflow API | http://localhost:5000/api/2.0/mlflow | MLflow REST API |
| MinIO Console | http://localhost:9001 | S3 artifact store UI (admin/adminadmin123) |
| MinIO S3 | http://localhost:9000 | S3 API endpoint |

## MLflow API Endpoints

The Cerebrum API provides MLflow integration at `/mlflow/*`:

### Status
- `GET /mlflow/status` - Check MLflow availability
- `GET /mlflow/ui-url` - Get MLflow UI URL

### Formula Execution Tracking
- `POST /mlflow/track/formula-execution` - Track formula execution
- `POST /mlflow/track/tier-change` - Track credibility tier change
- `GET /mlflow/formula-executions` - Get execution history
- `GET /mlflow/formula-executions/compare` - Compare executions

### Experiment Management
- `POST /mlflow/experiments` - Create experiment
- `GET /mlflow/experiments` - List experiments
- `GET /mlflow/experiments/{id}` - Get experiment details
- `POST /mlflow/experiments/{id}/runs` - Start run
- `GET /mlflow/experiments/{id}/runs` - Get experiment runs

### Model Registry
- `POST /mlflow/models/register` - Register model
- `GET /mlflow/models` - List registered models
- `GET /mlflow/models/{name}` - Get model details
- `POST /mlflow/models/{name}/versions/{version}/stage` - Transition stage
- `POST /mlflow/models/{name}/versions/{version}/promote` - Promote to production
- `GET /mlflow/models/{name}/compare` - Compare model versions

## Usage Examples

### Track Formula Execution
```python
from app.ml.tracking import get_mlflow_tracker, FormulaExecutionMetrics

tracker = get_mlflow_tracker()

metrics = FormulaExecutionMetrics(
    execution_time_ms=150.5,
    memory_usage_mb=128.0,
    cache_hit=False
)

run_id = tracker.track_formula_execution(
    formula_id="cost_calculator_v1",
    formula_name="Construction Cost Calculator",
    metrics=metrics,
    parameters={"region": "saudi", "currency": "SAR"}
)
```

### Using Context Manager
```python
from app.ml.tracking import track_formula_execution

with track_formula_execution("formula_123", "Cost Calculator") as metrics:
    result = execute_formula(data)
    metrics.execution_time_ms = result.duration
    metrics.cache_hit = result.from_cache
```

### Track Tier Change
```python
from app.ml.tracking import CredibilityTierChange

change = CredibilityTierChange(
    formula_id="formula_123",
    old_tier="bronze",
    new_tier="silver",
    confidence_score=0.85,
    verification_count=50
)

tracker.track_tier_change(change)
```

### Register Model
```python
from app.ml.registry import get_model_registry

registry = get_model_registry()

# Register from MLflow run
version = registry.register_model(
    name="cost_predictor",
    run_id="abc123",
    artifact_path="model",
    description="Cost prediction model v1"
)

# Promote to production
registry.promote_to_production("cost_predictor", version.version)
```

### Run Hyperparameter Tuning
```python
from app.ml.tracking import HyperparameterTuningResult

result = HyperparameterTuningResult(
    tuning_method="bayesian",
    best_params={"lr": 0.001, "epochs": 100},
    best_score=0.95,
    total_runs=50,
    search_space={"lr": [0.0001, 0.001, 0.01], "epochs": [50, 100, 200]}
)

tracker.track_hyperparameter_tuning(result, model_name="cost_predictor")
```

## Configuration

MLflow configuration is set via environment variables:

```bash
# Tracking URI (required)
MLFLOW_TRACKING_URI=http://mlflow-server:5000

# S3 Artifact Store (optional, for MinIO)
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin123
AWS_DEFAULT_REGION=us-east-1
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Cerebrum API                         │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐  │
│  │  tracking   │ │  experiment  │ │    registry     │  │
│  │    .py      │ │     .py      │ │      .py        │  │
│  └──────┬──────┘ └──────┬───────┘ └────────┬────────┘  │
│         └────────────────┼──────────────────┘          │
│                          │                              │
│                   ┌──────┴──────┐                        │
│                   │ endpoints   │                        │
│                   │    .py      │                        │
│                   └──────┬──────┘                        │
└──────────────────────────┼──────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌────▼────┐ ┌─────▼──────┐
        │  MLflow   │ │   S3    │ │ PostgreSQL │
        │  Server   │ │ (MinIO) │ │            │
        │  :5000    │ │  :9000  │ │   :5433    │
        └───────────┘ └─────────┘ └────────────┘
```

## Files

| File | Description |
|------|-------------|
| `__init__.py` | Module exports and initialization |
| `tracking.py` | MLflow wrapper for formula execution tracking |
| `experiment.py` | High-level experiment management |
| `registry.py` | Model registry with staging support |
| `endpoints.py` | FastAPI REST endpoints |

## Docker Services

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| mlflow-db | cerebrum-mlflow-db | 5433 | PostgreSQL for MLflow metadata |
| minio | cerebrum-minio | 9000/9001 | S3-compatible artifact storage |
| mlflow-server | cerebrum-mlflow-server | 5000 | MLflow tracking server |

## Troubleshooting

### MLflow not connecting
1. Check MLflow container status: `docker-compose -f docker-compose.mlflow.yml ps`
2. Verify network connection: `docker network ls`
3. Check logs: `docker-compose -f docker-compose.mlflow.yml logs mlflow-server`

### S3 artifact errors
1. Ensure MinIO is healthy: http://localhost:9001
2. Check bucket exists: `mc ls local/mlflow`
3. Verify AWS credentials in environment

### Database connection issues
1. Check postgres container: `docker-compose -f docker-compose.mlflow.yml logs mlflow-db`
2. Verify connection string in MLflow server env

## Resources

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [MLflow REST API](https://mlflow.org/docs/latest/rest-api.html)
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
