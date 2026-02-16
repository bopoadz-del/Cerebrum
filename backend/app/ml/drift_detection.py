"""
Model drift detection for production ML models.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
from scipy import stats
import uuid


class DriftType(Enum):
    """Types of model drift."""
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    FEATURE_DRIFT = "feature_drift"
    PREDICTION_DRIFT = "prediction_drift"


class DriftSeverity(Enum):
    """Severity levels for drift detection."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftReport:
    """Drift detection report."""
    report_id: str
    model_name: str
    model_version: str
    drift_type: DriftType
    severity: DriftSeverity
    drift_score: float
    threshold: float
    features_analyzed: List[str]
    drifted_features: List[str]
    statistics: Dict[str, Any]
    reference_period: Tuple[datetime, datetime]
    current_period: Tuple[datetime, datetime]
    detected_at: datetime
    recommended_action: str


class DriftDetector:
    """Detect drift in production ML models."""
    
    # Default thresholds for drift detection
    DEFAULT_THRESHOLDS = {
        DriftType.DATA_DRIFT: 0.05,  # p-value threshold
        DriftType.CONCEPT_DRIFT: 0.1,
        DriftType.FEATURE_DRIFT: 0.05,
        DriftType.PREDICTION_DRIFT: 0.05
    }
    
    def __init__(self):
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()
        self._reference_distributions: Dict[str, Dict[str, Any]] = {}
        self._detection_history: List[DriftReport] = []
    
    async def set_reference_distribution(
        self,
        model_name: str,
        model_version: str,
        feature_data: Dict[str, np.ndarray],
        prediction_data: Optional[np.ndarray] = None
    ):
        """Set reference distribution for drift detection."""
        
        key = f"{model_name}:{model_version}"
        
        self._reference_distributions[key] = {
            "features": {},
            "predictions": None,
            "timestamp": datetime.utcnow()
        }
        
        # Store feature statistics
        for feature_name, data in feature_data.items():
            self._reference_distributions[key]["features"][feature_name] = {
                "mean": float(np.mean(data)),
                "std": float(np.std(data)),
                "min": float(np.min(data)),
                "max": float(np.max(data)),
                "percentiles": {
                    str(p): float(np.percentile(data, p))
                    for p in [5, 25, 50, 75, 95]
                },
                "histogram": np.histogram(data, bins=50)[0].tolist()
            }
        
        # Store prediction distribution
        if prediction_data is not None:
            self._reference_distributions[key]["predictions"] = {
                "mean": float(np.mean(prediction_data)),
                "std": float(np.std(prediction_data)),
                "distribution": np.histogram(prediction_data, bins=50)[0].tolist()
            }
    
    async def detect_data_drift(
        self,
        model_name: str,
        model_version: str,
        current_data: Dict[str, np.ndarray],
        reference_period: Tuple[datetime, datetime],
        current_period: Tuple[datetime, datetime]
    ) -> DriftReport:
        """Detect data drift using statistical tests."""
        
        key = f"{model_name}:{model_version}"
        reference = self._reference_distributions.get(key)
        
        if not reference:
            raise ValueError(f"No reference distribution set for {key}")
        
        drifted_features = []
        feature_scores = {}
        
        for feature_name, current_values in current_data.items():
            ref_stats = reference["features"].get(feature_name)
            if not ref_stats:
                continue
            
            # KS test for numerical features
            if len(current_values) > 0:
                # Generate reference samples from stored statistics
                ref_samples = np.random.normal(
                    ref_stats["mean"],
                    ref_stats["std"],
                    size=len(current_values)
                )
                
                statistic, p_value = stats.ks_2samp(ref_samples, current_values)
                feature_scores[feature_name] = {
                    "ks_statistic": float(statistic),
                    "p_value": float(p_value)
                }
                
                if p_value < self.thresholds[DriftType.DATA_DRIFT]:
                    drifted_features.append(feature_name)
        
        # Calculate overall drift score
        drift_score = len(drifted_features) / len(current_data) if current_data else 0
        
        # Determine severity
        severity = self._calculate_severity(drift_score, DriftType.DATA_DRIFT)
        
        report = DriftReport(
            report_id=str(uuid.uuid4()),
            model_name=model_name,
            model_version=model_version,
            drift_type=DriftType.DATA_DRIFT,
            severity=severity,
            drift_score=drift_score,
            threshold=self.thresholds[DriftType.DATA_DRIFT],
            features_analyzed=list(current_data.keys()),
            drifted_features=drifted_features,
            statistics=feature_scores,
            reference_period=reference_period,
            current_period=current_period,
            detected_at=datetime.utcnow(),
            recommended_action=self._get_recommendation(severity, DriftType.DATA_DRIFT)
        )
        
        self._detection_history.append(report)
        
        return report
    
    async def detect_prediction_drift(
        self,
        model_name: str,
        model_version: str,
        current_predictions: np.ndarray,
        reference_period: Tuple[datetime, datetime],
        current_period: Tuple[datetime, datetime]
    ) -> DriftReport:
        """Detect drift in model predictions."""
        
        key = f"{model_name}:{model_version}"
        reference = self._reference_distributions.get(key)
        
        if not reference or reference.get("predictions") is None:
            raise ValueError(f"No reference predictions set for {key}")
        
        ref_preds = reference["predictions"]
        
        # Generate reference samples
        ref_samples = np.random.normal(
            ref_preds["mean"],
            ref_preds["std"],
            size=len(current_predictions)
        )
        
        # KS test
        statistic, p_value = stats.ks_2samp(ref_samples, current_predictions)
        
        # Calculate PSI (Population Stability Index)
        psi = self._calculate_psi(ref_samples, current_predictions)
        
        drift_score = 1.0 - p_value
        severity = self._calculate_severity(drift_score, DriftType.PREDICTION_DRIFT)
        
        report = DriftReport(
            report_id=str(uuid.uuid4()),
            model_name=model_name,
            model_version=model_version,
            drift_type=DriftType.PREDICTION_DRIFT,
            severity=severity,
            drift_score=drift_score,
            threshold=self.thresholds[DriftType.PREDICTION_DRIFT],
            features_analyzed=["predictions"],
            drifted_features=["predictions"] if severity != DriftSeverity.NONE else [],
            statistics={
                "ks_statistic": float(statistic),
                "p_value": float(p_value),
                "psi": float(psi)
            },
            reference_period=reference_period,
            current_period=current_period,
            detected_at=datetime.utcnow(),
            recommended_action=self._get_recommendation(severity, DriftType.PREDICTION_DRIFT)
        )
        
        self._detection_history.append(report)
        
        return report
    
    def _calculate_psi(
        self,
        expected: np.ndarray,
        actual: np.ndarray,
        buckets: int = 10
    ) -> float:
        """Calculate Population Stability Index."""
        
        def scale_range(input, min_val, max_val):
            input += -(np.min(input))
            input /= np.max(input) / (max_val - min_val)
            input += min_val
            return input
        
        breakpoints = np.linspace(0, buckets, buckets + 1)
        breakpoints = scale_range(
            breakpoints,
            np.min(expected),
            np.max(expected)
        )
        
        expected_percents = np.histogram(expected, breakpoints)[0] / len(expected)
        actual_percents = np.histogram(actual, breakpoints)[0] / len(actual)
        
        # Avoid division by zero
        expected_percents = np.clip(expected_percents, 0.0001, 1)
        actual_percents = np.clip(actual_percents, 0.0001, 1)
        
        psi = np.sum((actual_percents - expected_percents) * 
                     np.log(actual_percents / expected_percents))
        
        return float(psi)
    
    def _calculate_severity(
        self,
        drift_score: float,
        drift_type: DriftType
    ) -> DriftSeverity:
        """Calculate drift severity based on score."""
        
        if drift_score < 0.1:
            return DriftSeverity.NONE
        elif drift_score < 0.3:
            return DriftSeverity.LOW
        elif drift_score < 0.5:
            return DriftSeverity.MEDIUM
        elif drift_score < 0.7:
            return DriftSeverity.HIGH
        else:
            return DriftSeverity.CRITICAL
    
    def _get_recommendation(
        self,
        severity: DriftSeverity,
        drift_type: DriftType
    ) -> str:
        """Get recommended action based on severity."""
        
        recommendations = {
            DriftSeverity.NONE: "No action needed. Continue monitoring.",
            DriftSeverity.LOW: "Minor drift detected. Increase monitoring frequency.",
            DriftSeverity.MEDIUM: f"{drift_type.value} detected. Review model performance and consider retraining.",
            DriftSeverity.HIGH: f"Significant {drift_type.value} detected. Initiate model retraining.",
            DriftSeverity.CRITICAL: f"Critical {drift_type.value} detected. Consider model rollback immediately."
        }
        
        return recommendations.get(severity, "Unknown severity level")
    
    async def get_drift_history(
        self,
        model_name: Optional[str] = None,
        drift_type: Optional[DriftType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[DriftReport]:
        """Get drift detection history."""
        
        reports = self._detection_history
        
        if model_name:
            reports = [r for r in reports if r.model_name == model_name]
        
        if drift_type:
            reports = [r for r in reports if r.drift_type == drift_type]
        
        if start_date:
            reports = [r for r in reports if r.detected_at >= start_date]
        
        if end_date:
            reports = [r for r in reports if r.detected_at <= end_date]
        
        return sorted(reports, key=lambda r: r.detected_at, reverse=True)
    
    async def set_threshold(
        self,
        drift_type: DriftType,
        threshold: float
    ):
        """Set custom threshold for drift type."""
        
        self.thresholds[drift_type] = threshold
    
    async def get_drift_summary(
        self,
        model_name: str,
        model_version: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get drift summary for a model."""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        reports = [
            r for r in self._detection_history
            if r.model_name == model_name
            and r.model_version == model_version
            and r.detected_at >= cutoff_date
        ]
        
        # Count by severity
        severity_counts = {}
        for r in reports:
            severity_counts[r.severity.value] = severity_counts.get(r.severity.value, 0) + 1
        
        # Count by type
        type_counts = {}
        for r in reports:
            type_counts[r.drift_type.value] = type_counts.get(r.drift_type.value, 0) + 1
        
        return {
            "model_name": model_name,
            "model_version": model_version,
            "period_days": days,
            "total_reports": len(reports),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "latest_report": reports[-1].__dict__ if reports else None,
            "requires_attention": any(
                r.severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]
                for r in reports
            )
        }
