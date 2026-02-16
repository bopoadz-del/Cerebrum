"""
Tenant Analytics Module - Usage Analytics and Reporting
Item 291: Tenant-specific usage analytics
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
from app.db.base_class import Base

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Float, func, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum

from app.enterprise.tenant_isolation import Tenant
from app.enterprise.graphql import Document


class MetricType(str, Enum):
    """Types of metrics"""
    COUNT = "count"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    COUNTER = "counter"


class TimeGranularity(str, Enum):
    """Time granularity for analytics"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# Database Models

class TenantMetric(Base):
    """Tenant usage metrics"""
    __tablename__ = 'tenant_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    # Metric details
    metric_name = Column(String(100), nullable=False)
    metric_type = Column(String(50), default=MetricType.COUNT.value)
    
    # Value
    value = Column(Float, nullable=False)
    value_int = Column(Integer, nullable=True)
    
    # Dimensions
    dimensions = Column(JSONB, default=dict)
    
    # Timestamp
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_metrics_tenant_name_time', 'tenant_id', 'metric_name', 'recorded_at'),
    )


class TenantUsageSummary(Base):
    """Daily/periodic usage summaries"""
    __tablename__ = 'tenant_usage_summaries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    granularity = Column(String(50), nullable=False)
    
    # Usage metrics
    total_logins = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    new_users = Column(Integer, default=0)
    
    # Project activity
    projects_created = Column(Integer, default=0)
    projects_active = Column(Integer, default=0)
    
    # Document activity
    documents_uploaded = Column(Integer, default=0)
    documents_viewed = Column(Integer, default=0)
    storage_used_gb = Column(Float, default=0)
    
    # Feature usage
    feature_usage = Column(JSONB, default=dict)
    
    # API usage
    api_calls = Column(Integer, default=0)
    api_errors = Column(Integer, default=0)
    
    # Performance
    avg_response_time_ms = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_usage_summary_tenant_period', 'tenant_id', 'period_start', 'granularity'),
    )


class FeatureFlagUsage(Base):
    """Track feature flag usage"""
    __tablename__ = 'feature_flag_usage'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    
    feature_name = Column(String(100), nullable=False)
    flag_value = Column(String(50), nullable=False)
    
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class UserActivityEvent(Base):
    """Individual user activity events"""
    __tablename__ = 'user_activity_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    event_type = Column(String(100), nullable=False)
    event_category = Column(String(50), nullable=False)
    
    # Context
    page_url = Column(String(500), nullable=True)
    feature_used = Column(String(100), nullable=True)
    
    # Metadata
    metadata = Column(JSONB, default=dict)
    session_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_activity_tenant_user', 'tenant_id', 'user_id', 'created_at'),
        Index('ix_activity_event_type', 'event_type', 'created_at'),
    )


# Pydantic Schemas

class RecordMetricRequest(BaseModel):
    """Record metric request"""
    metric_name: str
    value: float
    metric_type: MetricType = MetricType.COUNT
    dimensions: Dict[str, Any] = Field(default_factory=dict)


class UsageQueryRequest(BaseModel):
    """Query usage data"""
    metric_names: List[str] = Field(default_factory=list)
    start_date: datetime
    end_date: datetime
    granularity: TimeGranularity = TimeGranularity.DAILY
    dimensions: Dict[str, Any] = Field(default_factory=dict)


class AnalyticsDashboardData(BaseModel):
    """Analytics dashboard data"""
    period: Dict[str, Any]
    summary: Dict[str, Any]
    trends: List[Dict[str, Any]]
    top_features: List[Dict[str, Any]]
    user_activity: Dict[str, Any]


class UsageReportRequest(BaseModel):
    """Generate usage report"""
    report_type: str = 'summary'
    start_date: datetime
    end_date: datetime
    include_charts: bool = True


# Service Classes

class AnalyticsService:
    """Service for tenant analytics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_metric(
        self,
        tenant_id: str,
        request: RecordMetricRequest
    ) -> TenantMetric:
        """Record a metric"""
        
        metric = TenantMetric(
            tenant_id=tenant_id,
            metric_name=request.metric_name,
            metric_type=request.metric_type.value,
            value=request.value,
            value_int=int(request.value) if request.value == int(request.value) else None,
            dimensions=request.dimensions
        )
        
        self.db.add(metric)
        self.db.commit()
        self.db.refresh(metric)
        
        return metric
    
    def record_event(
        self,
        tenant_id: str,
        user_id: str,
        event_type: str,
        event_category: str,
        page_url: Optional[str] = None,
        feature_used: Optional[str] = None,
        metadata: Optional[Dict] = None,
        session_id: Optional[str] = None
    ) -> UserActivityEvent:
        """Record user activity event"""
        
        event = UserActivityEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            page_url=page_url,
            feature_used=feature_used,
            metadata=metadata or {},
            session_id=session_id
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        return event
    
    def query_metrics(
        self,
        tenant_id: str,
        metric_names: List[str],
        start_date: datetime,
        end_date: datetime,
        granularity: TimeGranularity = TimeGranularity.DAILY
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Query metrics with aggregation"""
        
        results = {}
        
        for metric_name in metric_names:
            query = self.db.query(
                func.date_trunc(granularity.value, TenantMetric.recorded_at).label('period'),
                func.sum(TenantMetric.value).label('total'),
                func.avg(TenantMetric.value).label('average'),
                func.count(TenantMetric.id).label('count')
            ).filter(
                TenantMetric.tenant_id == tenant_id,
                TenantMetric.metric_name == metric_name,
                TenantMetric.recorded_at >= start_date,
                TenantMetric.recorded_at <= end_date
            ).group_by('period').order_by('period')
            
            data = [
                {
                    'period': row.period.isoformat() if row.period else None,
                    'total': float(row.total) if row.total else 0,
                    'average': float(row.average) if row.average else 0,
                    'count': row.count
                }
                for row in query.all()
            ]
            
            results[metric_name] = data
        
        return results
    
    def get_dashboard_data(
        self,
        tenant_id: str,
        days: int = 30
    ) -> AnalyticsDashboardData:
        """Get analytics dashboard data"""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get usage summary
        summary = self.db.query(TenantUsageSummary).filter(
            TenantUsageSummary.tenant_id == tenant_id,
            TenantUsageSummary.period_start >= start_date,
            TenantUsageSummary.granularity == 'daily'
        ).all()
        
        # Aggregate totals
        total_logins = sum(s.total_logins for s in summary)
        total_documents = sum(s.documents_uploaded for s in summary)
        total_api_calls = sum(s.api_calls for s in summary)
        avg_storage = sum(s.storage_used_gb for s in summary) / len(summary) if summary else 0
        
        # Get trends
        trends = self._get_trends(tenant_id, start_date, end_date)
        
        # Get top features
        top_features = self._get_top_features(tenant_id, start_date, end_date)
        
        # Get user activity
        user_activity = self._get_user_activity(tenant_id, start_date, end_date)
        
        return AnalyticsDashboardData(
            period={
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days
            },
            summary={
                'total_logins': total_logins,
                'total_documents_uploaded': total_documents,
                'total_api_calls': total_api_calls,
                'average_storage_gb': round(avg_storage, 2)
            },
            trends=trends,
            top_features=top_features,
            user_activity=user_activity
        )
    
    def _get_trends(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get usage trends"""
        
        # Daily active users trend
        daily_activity = self.db.query(
            func.date_trunc('day', UserActivityEvent.created_at).label('date'),
            func.count(func.distinct(UserActivityEvent.user_id)).label('unique_users')
        ).filter(
            UserActivityEvent.tenant_id == tenant_id,
            UserActivityEvent.created_at >= start_date,
            UserActivityEvent.created_at <= end_date
        ).group_by('date').order_by('date').all()
        
        return [
            {
                'date': row.date.isoformat() if row.date else None,
                'active_users': row.unique_users
            }
            for row in daily_activity
        ]
    
    def _get_top_features(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get most used features"""
        
        feature_usage = self.db.query(
            UserActivityEvent.feature_used,
            func.count(UserActivityEvent.id).label('usage_count')
        ).filter(
            UserActivityEvent.tenant_id == tenant_id,
            UserActivityEvent.created_at >= start_date,
            UserActivityEvent.created_at <= end_date,
            UserActivityEvent.feature_used.isnot(None)
        ).group_by(UserActivityEvent.feature_used).order_by(
            func.count(UserActivityEvent.id).desc()
        ).limit(10).all()
        
        return [
            {
                'feature': row.feature_used,
                'usage_count': row.usage_count
            }
            for row in feature_usage
        ]
    
    def _get_user_activity(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get user activity statistics"""
        
        # Total unique users
        total_users = self.db.query(func.count(func.distinct(UserActivityEvent.user_id))).filter(
            UserActivityEvent.tenant_id == tenant_id,
            UserActivityEvent.created_at >= start_date,
            UserActivityEvent.created_at <= end_date
        ).scalar()
        
        # New users (first activity in period)
        # This would require tracking first login date
        
        # Active users by day
        daily_active = self.db.query(
            func.date_trunc('day', UserActivityEvent.created_at),
            func.count(func.distinct(UserActivityEvent.user_id))
        ).filter(
            UserActivityEvent.tenant_id == tenant_id,
            UserActivityEvent.created_at >= start_date,
            UserActivityEvent.created_at <= end_date
        ).group_by(func.date_trunc('day', UserActivityEvent.created_at)).all()
        
        avg_daily_active = sum(count for _, count in daily_active) / len(daily_active) if daily_active else 0
        
        return {
            'total_unique_users': total_users,
            'average_daily_active': round(avg_daily_active, 0),
            'peak_daily_active': max((count for _, count in daily_active), default=0)
        }
    
    def generate_usage_report(
        self,
        tenant_id: str,
        request: UsageReportRequest
    ) -> Dict[str, Any]:
        """Generate comprehensive usage report"""
        
        # Get all metrics
        metrics = self.query_metrics(
            tenant_id,
            ['logins', 'documents_uploaded', 'api_calls', 'storage_used'],
            request.start_date,
            request.end_date,
            TimeGranularity.DAILY
        )
        
        # Get dashboard data
        dashboard = self.get_dashboard_data(
            tenant_id,
            (request.end_date - request.start_date).days
        )
        
        return {
            'report_type': request.report_type,
            'period': {
                'start': request.start_date.isoformat(),
                'end': request.end_date.isoformat()
            },
            'metrics': metrics,
            'summary': dashboard.summary,
            'top_features': dashboard.top_features,
            'user_activity': dashboard.user_activity
        }
    
    def check_usage_limits(self, tenant_id: str) -> Dict[str, Any]:
        """Check if tenant is approaching usage limits"""
        
        # Get tenant limits
        tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
        
        if not tenant:
            raise HTTPException(404, "Tenant not found")
        
        limits = tenant.usage_limits or {}
        current_usage = tenant.current_usage or {}
        
        alerts = []
        
        for resource, limit in limits.items():
            used = current_usage.get(resource, 0)
            percentage = (used / limit * 100) if limit > 0 else 0
            
            if percentage >= 90:
                alerts.append({
                    'resource': resource,
                    'severity': 'critical',
                    'message': f'{resource} usage at {percentage:.1f}% of limit',
                    'used': used,
                    'limit': limit,
                    'remaining': limit - used
                })
            elif percentage >= 75:
                alerts.append({
                    'resource': resource,
                    'severity': 'warning',
                    'message': f'{resource} usage at {percentage:.1f}% of limit',
                    'used': used,
                    'limit': limit,
                    'remaining': limit - used
                })
        
        return {
            'has_alerts': len(alerts) > 0,
            'alerts': alerts,
            'usage': current_usage,
            'limits': limits
        }


class UsageAggregationService:
    """Service for aggregating usage data"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def aggregate_daily_usage(self, date: datetime):
        """Aggregate daily usage for all tenants"""
        
        # Get all active tenants
        tenants = self.db.query(Tenant).filter(Tenant.status == 'active').all()
        
        for tenant in tenants:
            self._aggregate_tenant_daily(tenant.id, date)
    
    def _aggregate_tenant_daily(self, tenant_id: str, date: datetime):
        """Aggregate daily usage for a tenant"""
        
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # Count logins
        logins = self.db.query(func.count(UserActivityEvent.id)).filter(
            UserActivityEvent.tenant_id == tenant_id,
            UserActivityEvent.event_type == 'login',
            UserActivityEvent.created_at >= day_start,
            UserActivityEvent.created_at < day_end
        ).scalar()
        
        # Count unique users
        unique_users = self.db.query(func.count(func.distinct(UserActivityEvent.user_id))).filter(
            UserActivityEvent.tenant_id == tenant_id,
            UserActivityEvent.created_at >= day_start,
            UserActivityEvent.created_at < day_end
        ).scalar()
        
        # Count documents uploaded
        documents = self.db.query(func.count(Document.id)).filter(
            Document.tenant_id == tenant_id,
            Document.created_at >= day_start,
            Document.created_at < day_end
        ).scalar()
        
        # Create or update summary
        summary = self.db.query(TenantUsageSummary).filter(
            TenantUsageSummary.tenant_id == tenant_id,
            TenantUsageSummary.period_start == day_start,
            TenantUsageSummary.granularity == 'daily'
        ).first()
        
        if not summary:
            summary = TenantUsageSummary(
                tenant_id=tenant_id,
                period_start=day_start,
                period_end=day_end,
                granularity='daily'
            )
            self.db.add(summary)
        
        summary.total_logins = logins
        summary.unique_users = unique_users
        summary.documents_uploaded = documents
        
        self.db.commit()


# Export
__all__ = [
    'MetricType',
    'TimeGranularity',
    'TenantMetric',
    'TenantUsageSummary',
    'FeatureFlagUsage',
    'UserActivityEvent',
    'RecordMetricRequest',
    'UsageQueryRequest',
    'AnalyticsDashboardData',
    'UsageReportRequest',
    'AnalyticsService',
    'UsageAggregationService'
]
