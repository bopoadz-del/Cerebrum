"""
Performance Tracking Module
Handles subcontractor scorecards and performance metrics.
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer, Date, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class ScorecardPeriod(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    PROJECT = "project"


class ScorecardStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DISPUTED = "disputed"
    FINAL = "final"


class SubcontractorScorecard(Base):
    """Subcontractor performance scorecard."""
    __tablename__ = 'subcontractor_scorecards'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'), nullable=False)
    
    period = Column(String(50), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Quality metrics (0-100)
    quality_score = Column(Float)
    punch_list_items = Column(Integer, default=0)
    punch_list_completion = Column(Float, default=0)
    rework_required = Column(Integer, default=0)
    inspection_pass_rate = Column(Float, default=0)
    
    # Schedule metrics (0-100)
    schedule_score = Column(Float)
    on_time_completion = Column(Float, default=0)
    schedule_adherence = Column(Float, default=0)
    lookahead_compliance = Column(Float, default=0)
    
    # Safety metrics (0-100)
    safety_score = Column(Float)
    incidents = Column(Integer, default=0)
    near_misses = Column(Integer, default=0)
    safety_violations = Column(Integer, default=0)
    toolbox_talks = Column(Integer, default=0)
    
    # Documentation metrics (0-100)
    documentation_score = Column(Float)
    submittal_response_time = Column(Float, default=0)  # days
    rfi_response_time = Column(Float, default=0)  # days
    daily_report_compliance = Column(Float, default=0)
    
    # Communication metrics (0-100)
    communication_score = Column(Float)
    responsiveness = Column(Float, default=0)
    meeting_attendance = Column(Float, default=0)
    
    # Overall score
    overall_score = Column(Float)
    grade = Column(String(10))
    
    status = Column(String(50), default=ScorecardStatus.DRAFT)
    
    evaluator_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    evaluated_at = Column(DateTime)
    
    notes = Column(Text)
    improvement_areas = Column(JSONB, default=list)
    
    disputed_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    disputed_at = Column(DateTime)
    dispute_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PerformanceMetric(Base):
    """Individual performance metric tracking."""
    __tablename__ = 'performance_metrics'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'), nullable=False)
    
    metric_type = Column(String(100), nullable=False)  # quality, schedule, safety, documentation, communication
    metric_name = Column(String(255), nullable=False)
    
    value = Column(Float)
    target = Column(Float)
    unit = Column(String(50))
    
    measured_at = Column(Date, default=date.today)
    measured_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class PerformanceBenchmark(Base):
    """Industry/company performance benchmarks."""
    __tablename__ = 'performance_benchmarks'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    
    trade_type = Column(String(100))
    metric_type = Column(String(100), nullable=False)
    metric_name = Column(String(255), nullable=False)
    
    excellent_threshold = Column(Float)
    good_threshold = Column(Float)
    acceptable_threshold = Column(Float)
    poor_threshold = Column(Float)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Models

class ScorecardCreateRequest(BaseModel):
    project_id: str
    company_id: str
    period: ScorecardPeriod
    period_start: str
    period_end: str
    quality_score: float
    schedule_score: float
    safety_score: float
    documentation_score: float
    communication_score: float
    notes: Optional[str] = None
    improvement_areas: List[str] = []


class ScorecardUpdateRequest(BaseModel):
    quality_score: Optional[float] = None
    schedule_score: Optional[float] = None
    safety_score: Optional[float] = None
    documentation_score: Optional[float] = None
    communication_score: Optional[float] = None
    notes: Optional[str] = None
    improvement_areas: Optional[List[str]] = None


class DisputeScorecardRequest(BaseModel):
    reason: str


class MetricCreateRequest(BaseModel):
    project_id: str
    company_id: str
    metric_type: str
    metric_name: str
    value: float
    target: Optional[float] = None
    unit: Optional[str] = None
    notes: Optional[str] = None


class ScorecardResponse(BaseModel):
    id: str
    project_id: str
    company_id: str
    company_name: str
    period: str
    period_start: date
    period_end: date
    quality_score: float
    schedule_score: float
    safety_score: float
    documentation_score: float
    communication_score: float
    overall_score: float
    grade: str
    status: str
    evaluator_id: Optional[str]
    evaluator_name: Optional[str]
    evaluated_at: Optional[datetime]
    notes: Optional[str]
    improvement_areas: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PerformanceRanking(BaseModel):
    company_id: str
    company_name: str
    trade_type: str
    overall_score: float
    grade: str
    project_count: int
    rank: int


class PerformanceService:
    """Service for performance tracking."""
    
    GRADE_THRESHOLDS = {
        'A+': 97, 'A': 93, 'A-': 90,
        'B+': 87, 'B': 83, 'B-': 80,
        'C+': 77, 'C': 73, 'C-': 70,
        'D+': 67, 'D': 63, 'D-': 60,
        'F': 0
    }
    
    def __init__(self, db_session):
        self.db = db_session
    
    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        for grade, threshold in sorted(self.GRADE_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
            if score >= threshold:
                return grade
        return 'F'
    
    def _calculate_overall_score(
        self,
        quality: float,
        schedule: float,
        safety: float,
        documentation: float,
        communication: float
    ) -> float:
        """Calculate weighted overall score."""
        weights = {
            'quality': 0.25,
            'schedule': 0.25,
            'safety': 0.25,
            'documentation': 0.15,
            'communication': 0.10
        }
        
        overall = (
            quality * weights['quality'] +
            schedule * weights['schedule'] +
            safety * weights['safety'] +
            documentation * weights['documentation'] +
            communication * weights['communication']
        )
        
        return round(overall, 1)
    
    def create_scorecard(
        self,
        tenant_id: str,
        user_id: str,
        request: ScorecardCreateRequest
    ) -> SubcontractorScorecard:
        """Create a performance scorecard."""
        overall = self._calculate_overall_score(
            request.quality_score,
            request.schedule_score,
            request.safety_score,
            request.documentation_score,
            request.communication_score
        )
        
        scorecard = SubcontractorScorecard(
            tenant_id=tenant_id,
            project_id=request.project_id,
            company_id=request.company_id,
            period=request.period,
            period_start=datetime.strptime(request.period_start, "%Y-%m-%d").date(),
            period_end=datetime.strptime(request.period_end, "%Y-%m-%d").date(),
            quality_score=request.quality_score,
            schedule_score=request.schedule_score,
            safety_score=request.safety_score,
            documentation_score=request.documentation_score,
            communication_score=request.communication_score,
            overall_score=overall,
            grade=self._calculate_grade(overall),
            evaluator_id=user_id,
            evaluated_at=datetime.utcnow(),
            notes=request.notes,
            improvement_areas=request.improvement_areas
        )
        
        self.db.add(scorecard)
        self.db.commit()
        return scorecard
    
    def update_scorecard(
        self,
        tenant_id: str,
        scorecard_id: str,
        request: ScorecardUpdateRequest
    ) -> SubcontractorScorecard:
        """Update a scorecard."""
        scorecard = self.db.query(SubcontractorScorecard).filter(
            SubcontractorScorecard.tenant_id == tenant_id,
            SubcontractorScorecard.id == scorecard_id
        ).first()
        
        if not scorecard:
            raise ValueError("Scorecard not found")
        
        if request.quality_score is not None:
            scorecard.quality_score = request.quality_score
        if request.schedule_score is not None:
            scorecard.schedule_score = request.schedule_score
        if request.safety_score is not None:
            scorecard.safety_score = request.safety_score
        if request.documentation_score is not None:
            scorecard.documentation_score = request.documentation_score
        if request.communication_score is not None:
            scorecard.communication_score = request.communication_score
        if request.notes is not None:
            scorecard.notes = request.notes
        if request.improvement_areas is not None:
            scorecard.improvement_areas = request.improvement_areas
        
        # Recalculate overall score
        scorecard.overall_score = self._calculate_overall_score(
            scorecard.quality_score,
            scorecard.schedule_score,
            scorecard.safety_score,
            scorecard.documentation_score,
            scorecard.communication_score
        )
        scorecard.grade = self._calculate_grade(scorecard.overall_score)
        
        self.db.commit()
        return scorecard
    
    def publish_scorecard(
        self,
        tenant_id: str,
        scorecard_id: str
    ) -> SubcontractorScorecard:
        """Publish a scorecard."""
        scorecard = self.db.query(SubcontractorScorecard).filter(
            SubcontractorScorecard.tenant_id == tenant_id,
            SubcontractorScorecard.id == scorecard_id
        ).first()
        
        if not scorecard:
            raise ValueError("Scorecard not found")
        
        scorecard.status = ScorecardStatus.PUBLISHED
        self.db.commit()
        return scorecard
    
    def dispute_scorecard(
        self,
        tenant_id: str,
        scorecard_id: str,
        user_id: str,
        request: DisputeScorecardRequest
    ) -> SubcontractorScorecard:
        """Dispute a scorecard."""
        scorecard = self.db.query(SubcontractorScorecard).filter(
            SubcontractorScorecard.tenant_id == tenant_id,
            SubcontractorScorecard.id == scorecard_id
        ).first()
        
        if not scorecard:
            raise ValueError("Scorecard not found")
        
        scorecard.status = ScorecardStatus.DISPUTED
        scorecard.disputed_by = user_id
        scorecard.disputed_at = datetime.utcnow()
        scorecard.dispute_reason = request.reason
        
        self.db.commit()
        return scorecard
    
    def add_metric(
        self,
        tenant_id: str,
        user_id: str,
        request: MetricCreateRequest
    ) -> PerformanceMetric:
        """Add a performance metric."""
        metric = PerformanceMetric(
            tenant_id=tenant_id,
            project_id=request.project_id,
            company_id=request.company_id,
            metric_type=request.metric_type,
            metric_name=request.metric_name,
            value=request.value,
            target=request.target,
            unit=request.unit,
            measured_by=user_id,
            notes=request.notes
        )
        
        self.db.add(metric)
        self.db.commit()
        return metric
    
    def get_scorecards(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        company_id: Optional[str] = None,
        period: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[SubcontractorScorecard]:
        """Get scorecards with filters."""
        query = self.db.query(SubcontractorScorecard).filter(
            SubcontractorScorecard.tenant_id == tenant_id
        )
        
        if project_id:
            query = query.filter(SubcontractorScorecard.project_id == project_id)
        if company_id:
            query = query.filter(SubcontractorScorecard.company_id == company_id)
        if period:
            query = query.filter(SubcontractorScorecard.period == period)
        if status:
            query = query.filter(SubcontractorScorecard.status == status)
        
        return query.order_by(SubcontractorScorecard.period_end.desc()).all()
    
    def get_company_performance_summary(
        self,
        tenant_id: str,
        company_id: str
    ) -> Dict[str, Any]:
        """Get performance summary for a company."""
        scorecards = self.db.query(SubcontractorScorecard).filter(
            SubcontractorScorecard.tenant_id == tenant_id,
            SubcontractorScorecard.company_id == company_id,
            SubcontractorScorecard.status == ScorecardStatus.PUBLISHED
        ).all()
        
        if not scorecards:
            return {
                "company_id": company_id,
                "scorecard_count": 0,
                "average_score": None,
                "grade": None
            }
        
        avg_quality = sum(s.quality_score for s in scorecards) / len(scorecards)
        avg_schedule = sum(s.schedule_score for s in scorecards) / len(scorecards)
        avg_safety = sum(s.safety_score for s in scorecards) / len(scorecards)
        avg_documentation = sum(s.documentation_score for s in scorecards) / len(scorecards)
        avg_communication = sum(s.communication_score for s in scorecards) / len(scorecards)
        avg_overall = sum(s.overall_score for s in scorecards) / len(scorecards)
        
        return {
            "company_id": company_id,
            "scorecard_count": len(scorecards),
            "average_scores": {
                "quality": round(avg_quality, 1),
                "schedule": round(avg_schedule, 1),
                "safety": round(avg_safety, 1),
                "documentation": round(avg_documentation, 1),
                "communication": round(avg_communication, 1),
                "overall": round(avg_overall, 1)
            },
            "grade": self._calculate_grade(avg_overall),
            "latest_scorecard": scorecards[0] if scorecards else None
        }
    
    def get_leaderboard(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        trade_type: Optional[str] = None,
        limit: int = 10
    ) -> List[PerformanceRanking]:
        """Get subcontractor performance leaderboard."""
        query = self.db.query(SubcontractorScorecard).filter(
            SubcontractorScorecard.tenant_id == tenant_id,
            SubcontractorScorecard.status == ScorecardStatus.PUBLISHED
        )
        
        if project_id:
            query = query.filter(SubcontractorScorecard.project_id == project_id)
        
        scorecards = query.all()
        
        # Group by company and calculate average
        company_scores = {}
        for sc in scorecards:
            if sc.company_id not in company_scores:
                company_scores[sc.company_id] = {
                    'scores': [],
                    'company_name': '',  # Would be populated from company record
                    'trade_type': ''  # Would be populated from company record
                }
            company_scores[sc.company_id]['scores'].append(sc.overall_score)
        
        rankings = []
        for company_id, data in company_scores.items():
            avg_score = sum(data['scores']) / len(data['scores'])
            rankings.append({
                'company_id': company_id,
                'company_name': data['company_name'],
                'trade_type': data['trade_type'],
                'overall_score': round(avg_score, 1),
                'grade': self._calculate_grade(avg_score),
                'project_count': len(data['scores']),
                'rank': 0  # Will be assigned after sorting
            })
        
        # Sort and assign ranks
        rankings.sort(key=lambda x: x['overall_score'], reverse=True)
        for i, r in enumerate(rankings):
            r['rank'] = i + 1
        
        return rankings[:limit]
    
    def calculate_auto_scores(
        self,
        tenant_id: str,
        project_id: str,
        company_id: str,
        period_start: date,
        period_end: date
    ) -> Dict[str, float]:
        """Calculate automatic scores from system data."""
        # This would integrate with other modules to calculate scores
        # For now, return placeholder calculations
        
        # Quality - from punch list and inspections
        # Schedule - from schedule tasks
        # Safety - from incidents
        # Documentation - from submittals/RFIs
        # Communication - from response times
        
        return {
            "quality_score": 85.0,
            "schedule_score": 90.0,
            "safety_score": 95.0,
            "documentation_score": 80.0,
            "communication_score": 88.0
        }
