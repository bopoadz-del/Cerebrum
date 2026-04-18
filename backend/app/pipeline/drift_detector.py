"""
Drift Detection Module

Detects data drift, concept drift, and performance drift in production ML models.
Integrates with PostgreSQL for drift history storage and MLflow for model metadata.

Drift Types:
- Data Drift: Change in feature distributions
- Concept Drift: Change in relationship between features and target
- Prediction Drift: Change in model output distributions
- Performance Drift: Degradation in model performance metrics
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json
import asyncio
from contextlib import asynccontextmanager

import numpy as np
from scipy import stats
from sqlalchemy import (
    Column, String, Float, DateTime, Integer, JSON, 
    Enum as SQLEnum, Text, select, and_, desc, func
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import db_manager, get_db_context, get_sync_db_context
from app.core.config import settings

Base = declarative_base()


class DriftType(str, Enum):
    """Types of model drift."""
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    FEATURE_DRIFT = "feature_drift"
    PREDICTION_DRIFT = "prediction_drift"
    PERFORMANCE_DRIFT = "performance_drift"


class DriftSeverity(str, Enum):
    """Severity levels for drift detection."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DriftReportDB(Base):
    """Database model for drift reports."""
    __tablename__ = "drift_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(String(64), unique=True, index=True)
    model_name = Column(String(255), index=True, nullable=False)
    model_version = Column(String(64), nullable=False)
    drift_type = Column(SQLEnum(DriftType), nullable=False)
    severity = Column(SQLEnum(DriftSeverity), nullable=False)
    drift_score = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    features_analyzed = Column(ARRAY(String))
    drifted_features = Column(ARRAY(String))
    statistics = Column(JSON)
    reference_period_start = Column(DateTime)
    reference_period_end = Column(DateTime)
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    recommended_action = Column(Text)
    acknowledged = Column(Integer, default=0)  # 0=unacknowledged, 1=acknowledged
    acknowledged_by = Column(String(255))
    acknowledged_at = Column(DateTime)
    resolution_notes = Column(Text)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "report_id": self.report_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "drift_score": self.drift_score,
            "threshold": self.threshold,
            "features_analyzed": self.features_analyzed or [],
            "drifted_features": self.drifted_features or [],
            "statistics": self.statistics or {},
            "reference_period": {
                "start": self.reference_period_start.isoformat() if self.reference_period_start else None,
                "end": self.reference_period_end.isoformat() if self.reference_period_end else None,
            },
            "current_period": {
                "start": self.current_period_start.isoformat() if self.current_period_start else None,
                "end": self.current_period_end.isoformat() if self.current_period_end else None,
            },
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "recommended_action": self.recommended_action,
            "acknowledged": bool(self.acknowledged),
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "resolution_notes": self.resolution_notes,
        }


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


@dataclass
class FeatureDistribution:
    """Feature distribution statistics."""
    feature_name: str
    mean: float
    std: float
    min: float
    max: float
    percentiles: Dict[str, float]
    histogram: List[int]
    sample_count: int


@dataclass
class ReferenceDistribution:
    """Reference distribution for a model."""
    model_name: str
    model_version: str
    features: Dict[str, FeatureDistribution]
    predictions: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class DriftDetector:
    """
    Detect drift in production ML models.
    
    Supports:
    - Data drift detection using Kolmogorov-Smirnov test
    - Prediction drift using PSI (Population Stability Index)
    - Performance drift tracking
    - Concept drift detection
    
    Integrates with PostgreSQL for persistence and MLflow for model metadata.
    """
    
    # Default thresholds for drift detection
    DEFAULT_THRESHOLDS = {
        DriftType.DATA_DRIFT: 0.05,  # p-value threshold
        DriftType.CONCEPT_DRIFT: 0.1,
        DriftType.FEATURE_DRIFT: 0.05,
        DriftType.PREDICTION_DRIFT: 0.05,
        DriftType.PERFORMANCE_Drift: 0.15,  # 15% performance drop
    }
    
    # PSI thresholds
    PSI_THRESHOLDS = {
        "stable": 0.1,
        "moderate": 0.25,
        "significant": float("inf"),
    }
    
    def __init__(self, use_async: bool = True):
        self.thresholds = self.DEFAULT_THRESHOLDS.copy()
        self._reference_distributions: Dict[str, ReferenceDistribution] = {}
        self._use_async = use_async
    
    @asynccontextmanager
    async def _get_db_session(self):
        """Get database session."""
        if self._use_async:
            async with AsyncSessionLocal() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
        else:
            session = SessionLocal()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    async def set_reference_distribution(
        self,
        model_name: str,
        model_version: str,
        feature_data: Dict[str, np.ndarray],
        prediction_data: Optional[np.ndarray] = None
    ) -> ReferenceDistribution:
        """
        Set reference distribution for drift detection.
        
        This establishes the baseline against which future data will be compared.
        Typically set when a model is first deployed or after retraining.
        """
        key = f"{model_name}:{model_version}"
        
        features = {}
        for feature_name, data in feature_data.items():
            features[feature_name] = FeatureDistribution(
                feature_name=feature_name,
                mean=float(np.mean(data)),
                std=float(np.std(data)),
                min=float(np.min(data)),
                max=float(np.max(data)),
                percentiles={
                    str(p): float(np.percentile(data, p))
                    for p in [5, 25, 50, 75, 95]
                },
                histogram=np.histogram(data, bins=50)[0].tolist(),
                sample_count=len(data)
            )
        
        predictions = None
        if prediction_data is not None:
            predictions = {
                "mean": float(np.mean(prediction_data)),
                "std": float(np.std(prediction_data)),
                "distribution": np.histogram(prediction_data, bins=50)[0].tolist(),
                "sample_count": len(prediction_data)
            }
        
        ref_dist = ReferenceDistribution(
            model_name=model_name,
            model_version=model_version,
            features=features,
            predictions=predictions
        )
        
        self._reference_distributions[key] = ref_dist
        
        # Store in database for persistence
        async with self._get_db_session() as session:
            # Check if reference already exists
            from sqlalchemy import text
            stmt = text("""
                INSERT INTO model_reference_distributions 
                (model_name, model_version, distribution_data, created_at)
                VALUES (:model_name, :model_version, :data, :created_at)
                ON CONFLICT (model_name, model_version) 
                DO UPDATE SET distribution_data = EXCLUDED.distribution_data,
                              created_at = EXCLUDED.created_at
            """
            )
            await session.execute(stmt, {
                "model_name": model_name,
                "model_version": model_version,
                "data": json.dumps({
                    "features": {
                        name: {
                            "mean": f.mean,
                            "std": f.std,
                            "min": f.min,
                            "max": f.max,
                            "percentiles": f.percentiles,
                            "histogram": f.histogram,
                            "sample_count": f.sample_count,
                        }
                        for name, f in features.items()
                    },
                    "predictions": predictions,
                }),
                "created_at": datetime.utcnow()
            })
        
        return ref_dist
    
    async def detect_data_drift(
        self,
        model_name: str,
        model_version: str,
        current_data: Dict[str, np.ndarray],
        reference_period: Optional[Tuple[datetime, datetime]] = None,
        current_period: Optional[Tuple[datetime, datetime]] = None
    ) -> DriftReport:
        """
        Detect data drift using statistical tests.
        
        Uses Kolmogorov-Smirnov test to compare current feature distributions
        against reference distributions.
        """
        key = f"{model_name}:{model_version}"
        reference = self._reference_distributions.get(key)
        
        if not reference:
            # Try to load from database
            reference = await self._load_reference_distribution(model_name, model_version)
            if not reference:
                raise ValueError(f"No reference distribution set for {key}")
            self._reference_distributions[key] = reference
        
        drifted_features = []
        feature_scores = {}
        
        for feature_name, current_values in current_data.items():
            ref_dist = reference.features.get(feature_name)
            if not ref_dist:
                continue
            
            if len(current_values) == 0:
                continue
            
            # Kolmogorov-Smirnov test
            # Generate reference samples from stored statistics
            np.random.seed(42)  # For reproducibility
            ref_samples = np.random.normal(
                ref_dist.mean,
                ref_dist.std,
                size=min(len(current_values), ref_dist.sample_count)
            )
            
            statistic, p_value = stats.ks_2samp(ref_samples, current_values)
            
            # Calculate additional metrics
            current_mean = np.mean(current_values)
            mean_shift = abs(current_mean - ref_dist.mean) / (ref_dist.std or 1)
            
            feature_scores[feature_name] = {
                "ks_statistic": float(statistic),
                "p_value": float(p_value),
                "mean_shift_sigma": float(mean_shift),
                "reference_mean": ref_dist.mean,
                "current_mean": float(current_mean),
            }
            
            # Drift detected if p-value < threshold
            if p_value < self.thresholds[DriftType.DATA_DRIFT]:
                drifted_features.append(feature_name)
        
        # Calculate overall drift score
        drift_score = len(drifted_features) / len(current_data) if current_data else 0
        
        # Determine severity
        severity = self._calculate_severity(drift_score, DriftType.DATA_DRIFT)
        
        # Set default periods if not provided
        now = datetime.utcnow()
        if reference_period is None:
            ref_end = reference.created_at or now - timedelta(days=7)
            reference_period = (ref_end - timedelta(days=7), ref_end)
        if current_period is None:
            current_period = (now - timedelta(days=1), now)
        
        report = DriftReport(
            report_id=f"drift_{uuid.uuid4().hex[:12]}",
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
            detected_at=now,
            recommended_action=self._get_recommendation(severity, DriftType.DATA_DRIFT)
        )
        
        # Persist to database
        await self._save_drift_report(report)
        
        return report
    
    async def detect_prediction_drift(
        self,
        model_name: str,
        model_version: str,
        current_predictions: np.ndarray,
        reference_period: Optional[Tuple[datetime, datetime]] = None,
        current_period: Optional[Tuple[datetime, datetime]] = None
    ) -> DriftReport:
        """
        Detect drift in model predictions.
        
        Uses KS test and PSI (Population Stability Index) to detect changes
        in the distribution of model outputs.
        """
        key = f"{model_name}:{model_version}"
        reference = self._reference_distributions.get(key)
        
        if not reference or reference.predictions is None:
            reference = await self._load_reference_distribution(model_name, model_version)
            if not reference or reference.predictions is None:
                raise ValueError(f"No reference predictions set for {key}")
        
        ref_preds = reference.predictions
        
        # Generate reference samples
        np.random.seed(42)
        ref_samples = np.random.normal(
            ref_preds["mean"],
            ref_preds["std"],
            size=len(current_predictions)
        )
        
        # KS test
        statistic, p_value = stats.ks_2samp(ref_samples, current_predictions)
        
        # Calculate PSI
        psi = self._calculate_psi(ref_samples, current_predictions)
        
        drift_score = 1.0 - p_value
        
        # Determine severity based on PSI
        if psi < self.PSI_THRESHOLDS["stable"]:
            severity = DriftSeverity.NONE
        elif psi < self.PSI_THRESHOLDS["moderate"]:
            severity = DriftSeverity.MEDIUM
        else:
            severity = DriftSeverity.HIGH
        
        now = datetime.utcnow()
        if reference_period is None:
            ref_end = reference.created_at or now - timedelta(days=7)
            reference_period = (ref_end - timedelta(days=7), ref_end)
        if current_period is None:
            current_period = (now - timedelta(days=1), now)
        
        report = DriftReport(
            report_id=f"drift_{uuid.uuid4().hex[:12]}",
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
                "psi": float(psi),
                "reference_mean": ref_preds["mean"],
                "current_mean": float(np.mean(current_predictions)),
            },
            reference_period=reference_period,
            current_period=current_period,
            detected_at=now,
            recommended_action=self._get_recommendation(severity, DriftType.PREDICTION_DRIFT)
        )
        
        await self._save_drift_report(report)
        
        return report
    
    async def detect_performance_drift(
        self,
        model_name: str,
        model_version: str,
        current_metrics: Dict[str, float],
        baseline_metrics: Dict[str, float],
        metric_thresholds: Optional[Dict[str, float]] = None
    ) -> DriftReport:
        """
        Detect performance drift by comparing current metrics against baseline.
        """
        if metric_thresholds is None:
            metric_thresholds = {k: 0.15 for k in current_metrics.keys()}
        
        drifted_metrics = []
        metric_changes = {}
        
        for metric_name, current_value in current_metrics.items():
            baseline = baseline_metrics.get(metric_name)
            if baseline is None:
                continue
            
            threshold = metric_thresholds.get(metric_name, 0.15)
            
            # Calculate relative change
            if baseline != 0:
                relative_change = (baseline - current_value) / baseline
            else:
                relative_change = 0 if current_value == 0 else 1
            
            metric_changes[metric_name] = {
                "baseline": baseline,
                "current": current_value,
                "absolute_change": current_value - baseline,
                "relative_change": relative_change,
                "threshold": threshold,
            }
            
            # Performance degraded if relative change exceeds threshold
            if relative_change > threshold:
                drifted_metrics.append(metric_name)
        
        # Overall drift score based on proportion of degraded metrics
        drift_score = len(drifted_metrics) / len(current_metrics) if current_metrics else 0
        
        severity = self._calculate_severity(drift_score, DriftType.PERFORMANCE_DRIFT)
        
        now = datetime.utcnow()
        reference_period = (now - timedelta(days=7), now)
        current_period = (now - timedelta(days=1), now)
        
        report = DriftReport(
            report_id=f"drift_{uuid.uuid4().hex[:12]}",
            model_name=model_name,
            model_version=model_version,
            drift_type=DriftType.PERFORMANCE_DRIFT,
            severity=severity,
            drift_score=drift_score,
            threshold=self.thresholds.get(DriftType.PERFORMANCE_DRIFT, 0.15),
            features_analyzed=list(current_metrics.keys()),
            drifted_features=drifted_metrics,
            statistics=metric_changes,
            reference_period=reference_period,
            current_period=current_period,
            detected_at=now,
            recommended_action=self._get_recommendation(severity, DriftType.PERFORMANCE_DRIFT)
        )
        
        await self._save_drift_report(report)
        
        return report
    
    def _calculate_psi(
        self,
        expected: np.ndarray,
        actual: np.ndarray,
        buckets: int = 10
    ) -> float:
        """Calculate Population Stability Index."""
        
        # Create breakpoints
        min_val = min(np.min(expected), np.min(actual))
        max_val = max(np.max(expected), np.max(actual))
        
        if min_val == max_val:
            return 0.0
        
        breakpoints = np.linspace(min_val, max_val, buckets + 1)
        
        expected_counts, _ = np.histogram(expected, breakpoints)
        actual_counts, _ = np.histogram(actual, breakpoints)
        
        # Convert to percentages
        expected_percents = expected_counts / len(expected)
        actual_percents = actual_counts / len(actual)
        
        # Avoid division by zero
        expected_percents = np.clip(expected_percents, 0.0001, 1)
        actual_percents = np.clip(actual_percents, 0.0001, 1)
        
        # Calculate PSI
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
        """Get recommended action based on severity and drift type."""
        
        recommendations = {
            (DriftSeverity.NONE, DriftType.DATA_DRIFT): "No data drift detected. Continue monitoring.",
            (DriftSeverity.LOW, DriftType.DATA_DRIFT): "Minor data drift detected. Increase monitoring frequency.",
            (DriftSeverity.MEDIUM, DriftType.DATA_DRIFT): "Data drift detected. Review feature distributions and consider retraining.",
            (DriftSeverity.HIGH, DriftType.DATA_DRIFT): "Significant data drift detected. Initiate model retraining.",
            (DriftSeverity.CRITICAL, DriftType.DATA_DRIFT): "Critical data drift detected. Consider immediate model rollback or retraining.",
            
            (DriftSeverity.NONE, DriftType.PREDICTION_DRIFT): "No prediction drift detected. Continue monitoring.",
            (DriftSeverity.MEDIUM, DriftType.PREDICTION_DRIFT): "Prediction drift detected. Investigate model behavior and input data quality.",
            (DriftSeverity.HIGH, DriftType.PREDICTION_DRIFT): "Significant prediction drift. Recommend retraining with recent data.",
            
            (DriftSeverity.NONE, DriftType.PERFORMANCE_DRIFT): "Performance stable. Continue monitoring.",
            (DriftSeverity.LOW, DriftType.PERFORMANCE_DRIFT): "Minor performance degradation. Monitor closely.",
            (DriftSeverity.MEDIUM, DriftType.PERFORMANCE_DRIFT): "Performance degradation detected. Investigate causes and consider retraining.",
            (DriftSeverity.HIGH, DriftType.PERFORMANCE_DRIFT): "Significant performance degradation. Initiate retraining pipeline.",
            (DriftSeverity.CRITICAL, DriftType.PERFORMANCE_DRIFT): "Critical performance degradation. Immediate action required - rollback or retrain.",
        }
        
        return recommendations.get(
            (severity, drift_type),
            f"{severity.value} {drift_type.value} detected. Review and take appropriate action."
        )
    
    async def _save_drift_report(self, report: DriftReport):
        """Save drift report to database."""
        async with self._get_db_session() as session:
            db_report = DriftReportDB(
                report_id=report.report_id,
                model_name=report.model_name,
                model_version=report.model_version,
                drift_type=report.drift_type,
                severity=report.severity,
                drift_score=report.drift_score,
                threshold=report.threshold,
                features_analyzed=report.features_analyzed,
                drifted_features=report.drifted_features,
                statistics=report.statistics,
                reference_period_start=report.reference_period[0],
                reference_period_end=report.reference_period[1],
                current_period_start=report.current_period[0],
                current_period_end=report.current_period[1],
                detected_at=report.detected_at,
                recommended_action=report.recommended_action,
            )
            session.add(db_report)
    
    async def _load_reference_distribution(
        self,
        model_name: str,
        model_version: str
    ) -> Optional[ReferenceDistribution]:
        """Load reference distribution from database."""
        from sqlalchemy import text
        
        async with self._get_db_session() as session:
            stmt = text("""
                SELECT distribution_data, created_at 
                FROM model_reference_distributions
                WHERE model_name = :model_name AND model_version = :model_version
            """)
            result = await session.execute(stmt, {
                "model_name": model_name,
                "model_version": model_version
            })
            row = result.fetchone()
            
            if row:
                data = json.loads(row.distribution_data)
                features = {}
                
                for name, feat_data in data.get("features", {}).items():
                    features[name] = FeatureDistribution(
                        feature_name=name,
                        mean=feat_data["mean"],
                        std=feat_data["std"],
                        min=feat_data["min"],
                        max=feat_data["max"],
                        percentiles=feat_data["percentiles"],
                        histogram=feat_data["histogram"],
                        sample_count=feat_data["sample_count"]
                    )
                
                return ReferenceDistribution(
                    model_name=model_name,
                    model_version=model_version,
                    features=features,
                    predictions=data.get("predictions"),
                    created_at=row.created_at
                )
            
            return None
    
    async def acknowledge_drift(
        self,
        report_id: str,
        acknowledged_by: str,
        resolution_notes: Optional[str] = None
    ) -> bool:
        """Acknowledge a drift report."""
        async with self._get_db_session() as session:
            from sqlalchemy import text
            stmt = text("""
                UPDATE drift_reports 
                SET acknowledged = 1, 
                    acknowledged_by = :acknowledged_by,
                    acknowledged_at = :acknowledged_at,
                    resolution_notes = :resolution_notes
                WHERE report_id = :report_id
            """)
            result = await session.execute(stmt, {
                "report_id": report_id,
                "acknowledged_by": acknowledged_by,
                "acknowledged_at": datetime.utcnow(),
                "resolution_notes": resolution_notes
            })
            return result.rowcount > 0
    
    async def get_drift_history(
        self,
        model_name: Optional[str] = None,
        drift_type: Optional[DriftType] = None,
        severity: Optional[DriftSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get drift detection history from database."""
        async with self._get_db_session() as session:
            query = select(DriftReportDB)
            
            if model_name:
                query = query.where(DriftReportDB.model_name == model_name)
            if drift_type:
                query = query.where(DriftReportDB.drift_type == drift_type)
            if severity:
                query = query.where(DriftReportDB.severity == severity)
            if start_date:
                query = query.where(DriftReportDB.detected_at >= start_date)
            if end_date:
                query = query.where(DriftReportDB.detected_at <= end_date)
            
            query = query.order_by(desc(DriftReportDB.detected_at))
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            reports = result.scalars().all()
            
            return [r.to_dict() for r in reports]
    
    async def get_drift_summary(
        self,
        model_name: str,
        model_version: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get drift summary for a model."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        reports = await self.get_drift_history(
            model_name=model_name,
            start_date=cutoff_date,
            limit=1000
        )
        
        # Filter for specific version
        reports = [r for r in reports if r["model_version"] == model_version]
        
        # Count by severity
        severity_counts = {}
        for r in reports:
            sev = r["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        # Count by type
        type_counts = {}
        for r in reports:
            t = r["drift_type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        
        # Latest report
        latest = reports[0] if reports else None
        
        # Check if attention needed
        requires_attention = any(
            r["severity"] in [DriftSeverity.HIGH.value, DriftSeverity.CRITICAL.value]
            for r in reports
        )
        
        return {
            "model_name": model_name,
            "model_version": model_version,
            "period_days": days,
            "total_reports": len(reports),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "latest_report": latest,
            "requires_attention": requires_attention,
            "unacknowledged_critical": sum(
                1 for r in reports 
                if r["severity"] == DriftSeverity.CRITICAL.value 
                and not r["acknowledged"]
            ),
        }
    
    async def set_threshold(
        self,
        drift_type: DriftType,
        threshold: float
    ):
        """Set custom threshold for drift type."""
        self.thresholds[drift_type] = threshold


# Create migration SQL
DRIFT_DETECTION_MIGRATION = """
-- Migration for drift detection tables

-- Reference distributions table
CREATE TABLE IF NOT EXISTS model_reference_distributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(255) NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    distribution_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(model_name, model_version)
);

-- Drift reports table (matches DriftReportDB model)
CREATE TABLE IF NOT EXISTS drift_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id VARCHAR(64) UNIQUE NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    drift_type VARCHAR(32) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    drift_score FLOAT NOT NULL,
    threshold FLOAT NOT NULL,
    features_analyzed TEXT[],
    drifted_features TEXT[],
    statistics JSONB,
    reference_period_start TIMESTAMP WITH TIME ZONE,
    reference_period_end TIMESTAMP WITH TIME ZONE,
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    recommended_action TEXT,
    acknowledged INTEGER DEFAULT 0,
    acknowledged_by VARCHAR(255),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_drift_reports_model_name ON drift_reports(model_name);
CREATE INDEX IF NOT EXISTS idx_drift_reports_detected_at ON drift_reports(detected_at);
CREATE INDEX IF NOT EXISTS idx_drift_reports_severity ON drift_reports(severity);
CREATE INDEX IF NOT EXISTS idx_drift_reports_type ON drift_reports(drift_type);
CREATE INDEX IF NOT EXISTS idx_drift_reports_acknowledged ON drift_reports(acknowledged) WHERE acknowledged = 0;

-- Index for model lookup
CREATE INDEX IF NOT EXISTS idx_ref_dist_model ON model_reference_distributions(model_name, model_version);
"""
