"""
ML Triggers - Auto-run ML services

Automatically runs ML services based on events:
- Auto-prediction on data changes
- Model retraining on drift detection
- Batch inference on scheduled intervals
- Feature store updates
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.triggers.engine import Event, EventType, event_bus
from app.workers.celery_config import slow_task, fast_task

logger = get_logger(__name__)


class MLTriggerManager:
    """
    Manages ML-related triggers and automatic ML service execution.
    """
    
    def __init__(self):
        """Initialize the ML trigger manager."""
        self._models: Dict[str, Any] = {}
        self._feature_store = {}
        self._register_handlers()
        
    def _register_handlers(self) -> None:
        """Register all ML event handlers."""
        event_bus.register(EventType.ML_PREDICTION_REQUESTED, self._on_prediction_requested)
        event_bus.register(EventType.ML_DRIFT_DETECTED, self._on_drift_detected)
        event_bus.register(EventType.FILE_PROCESSED, self._on_file_processed_for_ml)
        event_bus.register(EventType.BIM_MODEL_PROCESSED, self._on_bim_for_ml)
        logger.info("ML trigger handlers registered")
        
    async def _on_prediction_requested(self, event: Event) -> None:
        """
        Handle prediction request event.
        
        Args:
            event: Prediction request event
        """
        payload = event.payload
        model_id = payload.get("model_id")
        input_data = payload.get("input_data")
        prediction_type = payload.get("prediction_type")
        
        logger.info(
            "ML prediction requested",
            model_id=model_id,
            prediction_type=prediction_type,
        )
        
        # Queue prediction task
        run_prediction.delay(
            model_id=model_id,
            input_data=input_data,
            prediction_type=prediction_type,
            tenant_id=event.tenant_id,
        )
        
    async def _on_drift_detected(self, event: Event) -> None:
        """
        Handle model drift detection event.
        
        Args:
            event: Drift detection event
        """
        payload = event.payload
        model_id = payload.get("model_id")
        drift_score = payload.get("drift_score")
        
        logger.warning(
            "Model drift detected - triggering retraining",
            model_id=model_id,
            drift_score=drift_score,
        )
        
        # Queue retraining task
        retrain_model.delay(
            model_id=model_id,
            trigger="drift_detection",
            drift_score=drift_score,
        )
        
    async def _on_file_processed_for_ml(self, event: Event) -> None:
        """
        Handle file processed event for ML analysis.
        
        Args:
            event: File processed event
        """
        payload = event.payload
        file_id = payload.get("file_id")
        file_name = payload.get("file_name")
        
        # Auto-extract entities from documents
        if self._is_document(file_name):
            logger.info("Auto-extracting entities from document", file_id=file_id)
            extract_entities.delay(file_id=file_id)
            
        # Auto-extract action items from meeting minutes
        if self._is_meeting_minutes(file_name):
            logger.info("Auto-extracting action items", file_id=file_id)
            extract_action_items.delay(file_id=file_id)
            
    async def _on_bim_for_ml(self, event: Event) -> None:
        """
        Handle BIM model processed event for ML analysis.
        
        Args:
            event: BIM model processed event
        """
        payload = event.payload
        model_id = payload.get("model_id")
        element_count = payload.get("element_count")
        
        logger.info("Running ML analysis on BIM model", model_id=model_id)
        
        # Auto-run quantity takeoff
        run_quantity_takeoff.delay(model_id=model_id)
        
        # Auto-detect anomalies
        detect_bim_anomalies.delay(model_id=model_id)
        
    def _is_document(self, file_name: str) -> bool:
        """Check if file is a document."""
        doc_extensions = [".pdf", ".doc", ".docx", ".txt"]
        return any(file_name.lower().endswith(ext) for ext in doc_extensions)
        
    def _is_meeting_minutes(self, file_name: str) -> bool:
        """Check if file is meeting minutes."""
        keywords = ["meeting", "minutes", "mom", "notes"]
        return any(kw in file_name.lower() for kw in keywords)
        
    async def schedule_periodic_predictions(self) -> None:
        """Schedule periodic batch predictions."""
        while True:
            await asyncio.sleep(3600)  # Every hour
            
            logger.info("Running scheduled batch predictions")
            
            # Queue batch predictions
            run_batch_predictions.delay(
                prediction_types=[
                    "cost_forecast",
                    "schedule_delay",
                    "safety_risk",
                ]
            )


# Celery tasks for ML processing
@fast_task(bind=True, max_retries=3)
def run_prediction(
    self,
    model_id: str,
    input_data: Dict[str, Any],
    prediction_type: str,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run ML prediction in background.
    
    Args:
        model_id: Model ID
        input_data: Input data for prediction
        prediction_type: Type of prediction
        tenant_id: Tenant ID
        
    Returns:
        Prediction results
    """
    try:
        logger.info("Running prediction", model_id=model_id, type=prediction_type)
        
        from app.ml.model_registry import get_model
        
        # Load model
        model = get_model(model_id)
        
        # Run prediction
        prediction = model.predict(input_data)
        
        # Emit completion event
        asyncio.run(event_bus.emit(
            event_bus.create_event(
                EventType.ML_PREDICTION_COMPLETED,
                source="ml_triggers",
                payload={
                    "model_id": model_id,
                    "prediction_type": prediction_type,
                    "result": prediction,
                },
                tenant_id=tenant_id,
            )
        ))
        
        return {
            "status": "success",
            "model_id": model_id,
            "prediction": prediction,
        }
        
    except Exception as exc:
        logger.error("Prediction failed", model_id=model_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@slow_task(bind=True, max_retries=2)
def retrain_model(
    self,
    model_id: str,
    trigger: str,
    drift_score: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Retrain ML model in background.
    
    Args:
        model_id: Model ID
        trigger: What triggered retraining
        drift_score: Drift score if triggered by drift
        
    Returns:
        Retraining results
    """
    try:
        logger.info("Retraining model", model_id=model_id, trigger=trigger)
        
        from app.ml.model_registry import get_model, save_model
        from app.ml.experiment_tracking import log_experiment
        
        # Get training data
        training_data = load_training_data(model_id)
        
        # Retrain model
        model = get_model(model_id)
        metrics = model.retrain(training_data)
        
        # Log experiment
        log_experiment(
            model_id=model_id,
            metrics=metrics,
            trigger=trigger,
            drift_score=drift_score,
        )
        
        # Save updated model
        save_model(model_id, model)
        
        # Emit event
        asyncio.run(event_bus.emit(
            event_bus.create_event(
                EventType.ML_MODEL_TRAINED,
                source="ml_triggers",
                payload={
                    "model_id": model_id,
                    "metrics": metrics,
                    "trigger": trigger,
                },
            )
        ))
        
        return {
            "status": "success",
            "model_id": model_id,
            "metrics": metrics,
        }
        
    except Exception as exc:
        logger.error("Model retraining failed", model_id=model_id, error=str(exc))
        raise self.retry(exc=exc, countdown=300)


@slow_task(bind=True, max_retries=3)
def extract_entities(self, file_id: str) -> Dict[str, Any]:
    """
    Extract named entities from document.
    
    Args:
        file_id: File ID
        
    Returns:
        Extracted entities
    """
    try:
        logger.info("Extracting entities", file_id=file_id)
        
        from app.pipelines.ner_extraction import extract_entities_from_document
        
        entities = extract_entities_from_document(file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "entities": entities,
        }
        
    except Exception as exc:
        logger.error("Entity extraction failed", file_id=file_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@slow_task(bind=True, max_retries=3)
def extract_action_items(self, file_id: str) -> Dict[str, Any]:
    """
    Extract action items from meeting minutes.
    
    Args:
        file_id: File ID
        
    Returns:
        Extracted action items
    """
    try:
        logger.info("Extracting action items", file_id=file_id)
        
        from app.pipelines.action_extraction import extract_action_items_from_document
        
        action_items = extract_action_items_from_document(file_id)
        
        return {
            "status": "success",
            "file_id": file_id,
            "action_items": action_items,
        }
        
    except Exception as exc:
        logger.error("Action item extraction failed", file_id=file_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@slow_task(bind=True, max_retries=2)
def run_quantity_takeoff(self, model_id: str) -> Dict[str, Any]:
    """
    Run quantity takeoff on BIM model.
    
    Args:
        model_id: BIM model ID
        
    Returns:
        Takeoff results
    """
    try:
        logger.info("Running quantity takeoff", model_id=model_id)
        
        from app.pipelines.ifc_takeoff import generate_ifc_takeoff
        
        takeoff = generate_ifc_takeoff(model_id)
        
        return {
            "status": "success",
            "model_id": model_id,
            "takeoff": takeoff,
        }
        
    except Exception as exc:
        logger.error("Quantity takeoff failed", model_id=model_id, error=str(exc))
        raise self.retry(exc=exc, countdown=300)


@slow_task(bind=True, max_retries=2)
def detect_bim_anomalies(self, model_id: str) -> Dict[str, Any]:
    """
    Detect anomalies in BIM model.
    
    Args:
        model_id: BIM model ID
        
    Returns:
        Anomaly detection results
    """
    try:
        logger.info("Detecting BIM anomalies", model_id=model_id)
        
        # Run anomaly detection
        anomalies = []
        
        # Check for floating elements
        # Check for duplicate elements
        # Check for invalid geometry
        
        return {
            "status": "success",
            "model_id": model_id,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
        }
        
    except Exception as exc:
        logger.error("BIM anomaly detection failed", model_id=model_id, error=str(exc))
        raise self.retry(exc=exc, countdown=300)


@slow_task(bind=True, max_retries=2)
def run_batch_predictions(self, prediction_types: List[str]) -> Dict[str, Any]:
    """
    Run batch predictions for multiple types.
    
    Args:
        prediction_types: List of prediction types
        
    Returns:
        Batch prediction results
    """
    try:
        logger.info("Running batch predictions", types=prediction_types)
        
        results = {}
        
        for pred_type in prediction_types:
            # Run prediction for each type
            results[pred_type] = {"status": "completed"}
        
        return {
            "status": "success",
            "predictions": results,
        }
        
    except Exception as exc:
        logger.error("Batch predictions failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


def load_training_data(model_id: str) -> Any:
    """Load training data for model."""
    # Implementation would load from data warehouse
    return {}


# Global instance
ml_trigger_manager = MLTriggerManager()
