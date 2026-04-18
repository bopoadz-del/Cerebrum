# MLflow Integration for Cerebrum

Complete MLflow integration with experiment tracking, model registry, and S3 artifact storage.

## Quick Start

```bash
# Start everything
docker-compose -f docker-compose.local.yml -f docker-compose.mlflow.yml up -d

# Access:
# - Cerebrum API: http://localhost:8000
# - MLflow UI: http://localhost:5000
# - MinIO Console: http://localhost:9001 (minioadmin/minioadmin123)
```

## Services

| Service | URL | Credentials |
|---------|-----|-------------|
| MLflow UI | http://localhost:5000 | - |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin123 |
| MinIO S3 API | http://localhost:9000 | minioadmin / minioadmin123 |
| MLflow DB | localhost:5433 | mlflow / mlflow_password |

## Backend Integration

```python
from app.ml.tracking import get_mlflow_tracker, FormulaExecutionMetrics

tracker = get_mlflow_tracker()

# Track formula execution
metrics = FormulaExecutionMetrics(execution_time_ms=150.5)
tracker.track_formula_execution(
    formula_id="cost_calc",
    formula_name="Cost Calculator",
    metrics=metrics
)
```

See [backend/app/ml/README.md](backend/app/ml/README.md) for full documentation.
