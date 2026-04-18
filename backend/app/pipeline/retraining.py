"""
Retraining Orchestrator

Main orchestrator for the automated model retraining pipeline.
Coordinates all pipeline components:
- Drift detection
- CI/CD pipeline
- A/B testing
- Deployment management
- Scheduling

Integration points:
- PostgreSQL for state persistence
- MLflow for model registry
- Celery for async execution
- Formula executor for testing
"""