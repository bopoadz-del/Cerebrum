"""
Drawing Distribution Module
Handles trade-specific drawing sets and distribution to subcontractors.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class DrawingStatus(str, Enum):
    PUBLISHED = "published"
    REVISED = "revised"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class DistributionStatus(str, Enum):
    PENDING = "pending"
    DISTRIBUTED = "distributed"
    ACKNOWLEDGED = "acknowledged"
    REJECTED = "rejected"


class DrawingSet(Base):
    """Drawing set for specific trades."""
    __tablename__ = 'drawing_sets'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    discipline = Column(String(100), nullable=False)  # electrical, plumbing, etc.
    drawing_number_prefix = Column(String(50))
    
    version = Column(String(20), default="1.0")
    status = Column(String(50), default=DrawingStatus.PUBLISHED)
    
    distributed_to = Column(JSONB, default=list)  # List of company IDs
    distribution_date = Column(DateTime)
    
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    drawings = relationship("Drawing", back_populates="drawing_set")


class Drawing(Base):
    """Individual drawing within a set."""
    __tablename__ = 'drawings'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    drawing_set_id = Column(PG_UUID(as_uuid=True), ForeignKey('drawing_sets.id'), nullable=False)
    
    drawing_number = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    revision = Column(String(20), default="0")
    
    file_url = Column(String(1000))
    file_name = Column(String(500))
    file_size = Column(Integer)
    file_type = Column(String(50))
    
    scale = Column(String(50))
    sheet_size = Column(String(50))
    
    status = Column(String(50), default=DrawingStatus.PUBLISHED)
    superseded_by = Column(PG_UUID(as_uuid=True), ForeignKey('drawings.id'))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    drawing_set = relationship("DrawingSet", back_populates="drawings")
    distributions = relationship("DrawingDistribution", back_populates="drawing")


class DrawingDistribution(Base):
    """Tracks drawing distribution to subcontractors."""
    __tablename__ = 'drawing_distributions'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    drawing_id = Column(PG_UUID(as_uuid=True), ForeignKey('drawings.id'), nullable=False)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'), nullable=False)
    
    status = Column(String(50), default=DistributionStatus.PENDING)
    distributed_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    distributed_at = Column(DateTime)
    
    acknowledged_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    acknowledged_at = Column(DateTime)
    acknowledgment_notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    drawing = relationship("Drawing", back_populates="distributions")


# Pydantic Models

class DrawingCreateRequest(BaseModel):
    drawing_number: str
    title: str
    description: Optional[str] = None
    revision: str = "0"
    file_url: str
    file_name: str
    file_size: int
    file_type: str
    scale: Optional[str] = None
    sheet_size: Optional[str] = None


class DrawingSetCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    discipline: str
    drawing_number_prefix: Optional[str] = None
    drawings: List[DrawingCreateRequest]


class DrawingSetUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[DrawingStatus] = None


class DistributeDrawingsRequest(BaseModel):
    drawing_ids: List[str]
    company_ids: List[str]
    notes: Optional[str] = None


class AcknowledgeDrawingRequest(BaseModel):
    acknowledgment_notes: Optional[str] = None


class DrawingResponse(BaseModel):
    id: str
    drawing_number: str
    title: str
    description: Optional[str]
    revision: str
    file_url: str
    file_name: str
    file_size: int
    file_type: str
    scale: Optional[str]
    sheet_size: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DrawingSetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    discipline: str
    drawing_number_prefix: Optional[str]
    version: str
    status: str
    drawing_count: int
    distributed_to: List[str]
    distribution_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DrawingDistributionResponse(BaseModel):
    id: str
    drawing_id: str
    company_id: str
    company_name: str
    status: str
    distributed_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    acknowledgment_notes: Optional[str]
    
    class Config:
        from_attributes = True


class DrawingDistributionService:
    """Service for managing drawing distribution."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_drawing_set(
        self,
        tenant_id: str,
        project_id: str,
        user_id: str,
        request: DrawingSetCreateRequest
    ) -> DrawingSet:
        """Create a new drawing set with drawings."""
        drawing_set = DrawingSet(
            tenant_id=tenant_id,
            project_id=project_id,
            name=request.name,
            description=request.description,
            discipline=request.discipline,
            drawing_number_prefix=request.drawing_number_prefix,
            created_by=user_id
        )
        
        self.db.add(drawing_set)
        self.db.flush()
        
        # Create drawings
        for drawing_req in request.drawings:
            drawing = Drawing(
                tenant_id=tenant_id,
                drawing_set_id=drawing_set.id,
                drawing_number=drawing_req.drawing_number,
                title=drawing_req.title,
                description=drawing_req.description,
                revision=drawing_req.revision,
                file_url=drawing_req.file_url,
                file_name=drawing_req.file_name,
                file_size=drawing_req.file_size,
                file_type=drawing_req.file_type,
                scale=drawing_req.scale,
                sheet_size=drawing_req.sheet_size
            )
            self.db.add(drawing)
        
        self.db.commit()
        return drawing_set
    
    def get_drawing_sets(
        self,
        tenant_id: str,
        project_id: Optional[str] = None,
        discipline: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[DrawingSet]:
        """Get drawing sets with optional filters."""
        query = self.db.query(DrawingSet).filter(DrawingSet.tenant_id == tenant_id)
        
        if project_id:
            query = query.filter(DrawingSet.project_id == project_id)
        if discipline:
            query = query.filter(DrawingSet.discipline == discipline)
        if status:
            query = query.filter(DrawingSet.status == status)
        
        return query.order_by(DrawingSet.created_at.desc()).all()
    
    def get_drawings_in_set(
        self,
        tenant_id: str,
        drawing_set_id: str
    ) -> List[Drawing]:
        """Get all drawings in a set."""
        return self.db.query(Drawing).filter(
            Drawing.tenant_id == tenant_id,
            Drawing.drawing_set_id == drawing_set_id
        ).order_by(Drawing.drawing_number).all()
    
    def distribute_drawings(
        self,
        tenant_id: str,
        user_id: str,
        request: DistributeDrawingsRequest
    ) -> List[DrawingDistribution]:
        """Distribute drawings to subcontractor companies."""
        distributions = []
        
        for drawing_id in request.drawing_ids:
            for company_id in request.company_ids:
                # Check if distribution already exists
                existing = self.db.query(DrawingDistribution).filter(
                    DrawingDistribution.tenant_id == tenant_id,
                    DrawingDistribution.drawing_id == drawing_id,
                    DrawingDistribution.company_id == company_id
                ).first()
                
                if existing:
                    continue
                
                distribution = DrawingDistribution(
                    tenant_id=tenant_id,
                    drawing_id=drawing_id,
                    company_id=company_id,
                    status=DistributionStatus.DISTRIBUTED,
                    distributed_by=user_id,
                    distributed_at=datetime.utcnow()
                )
                
                self.db.add(distribution)
                distributions.append(distribution)
        
        self.db.commit()
        return distributions
    
    def acknowledge_drawing(
        self,
        tenant_id: str,
        distribution_id: str,
        user_id: str,
        request: AcknowledgeDrawingRequest
    ) -> DrawingDistribution:
        """Subcontractor acknowledges receipt of drawing."""
        distribution = self.db.query(DrawingDistribution).filter(
            DrawingDistribution.tenant_id == tenant_id,
            DrawingDistribution.id == distribution_id
        ).first()
        
        if not distribution:
            raise ValueError("Distribution not found")
        
        distribution.status = DistributionStatus.ACKNOWLEDGED
        distribution.acknowledged_by = user_id
        distribution.acknowledged_at = datetime.utcnow()
        distribution.acknowledgment_notes = request.acknowledgment_notes
        
        self.db.commit()
        return distribution
    
    def get_company_drawings(
        self,
        tenant_id: str,
        company_id: str,
        project_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get drawings distributed to a specific company."""
        query = self.db.query(Drawing, DrawingDistribution).join(
            DrawingDistribution,
            Drawing.id == DrawingDistribution.drawing_id
        ).filter(
            Drawing.tenant_id == tenant_id,
            DrawingDistribution.company_id == company_id
        )
        
        if project_id:
            query = query.filter(Drawing.drawing_set.has(project_id=project_id))
        if status:
            query = query.filter(DrawingDistribution.status == status)
        
        results = query.all()
        
        drawings = []
        for drawing, distribution in results:
            drawings.append({
                "drawing": drawing,
                "distribution": distribution,
                "distribution_status": distribution.status
            })
        
        return drawings
    
    def create_revision(
        self,
        tenant_id: str,
        drawing_id: str,
        user_id: str,
        new_file_url: str,
        new_file_name: str,
        revision_notes: Optional[str] = None
    ) -> Drawing:
        """Create a new revision of a drawing."""
        original = self.db.query(Drawing).filter(
            Drawing.tenant_id == tenant_id,
            Drawing.id == drawing_id
        ).first()
        
        if not original:
            raise ValueError("Drawing not found")
        
        # Mark original as superseded
        original.status = DrawingStatus.SUPERSEDED
        
        # Parse and increment revision
        try:
            current_rev = int(original.revision)
            new_revision = str(current_rev + 1)
        except ValueError:
            new_revision = "A" if original.revision == "0" else chr(ord(original.revision) + 1)
        
        # Create new revision
        new_drawing = Drawing(
            tenant_id=tenant_id,
            drawing_set_id=original.drawing_set_id,
            drawing_number=original.drawing_number,
            title=original.title,
            description=f"{original.description or ''}\n\nRevision Notes: {revision_notes}" if revision_notes else original.description,
            revision=new_revision,
            file_url=new_file_url,
            file_name=new_file_name,
            file_size=original.file_size,
            file_type=original.file_type,
            scale=original.scale,
            sheet_size=original.sheet_size,
            status=DrawingStatus.REVISED
        )
        
        self.db.add(new_drawing)
        self.db.flush()
        
        # Update original to point to new revision
        original.superseded_by = new_drawing.id
        
        self.db.commit()
        return new_drawing
    
    def get_distribution_summary(
        self,
        tenant_id: str,
        drawing_set_id: str
    ) -> Dict[str, Any]:
        """Get distribution summary for a drawing set."""
        drawings = self.get_drawings_in_set(tenant_id, drawing_set_id)
        
        total_distributions = 0
        acknowledged_count = 0
        pending_count = 0
        
        for drawing in drawings:
            for dist in drawing.distributions:
                total_distributions += 1
                if dist.status == DistributionStatus.ACKNOWLEDGED:
                    acknowledged_count += 1
                elif dist.status == DistributionStatus.PENDING:
                    pending_count += 1
        
        return {
            "drawing_set_id": drawing_set_id,
            "total_drawings": len(drawings),
            "total_distributions": total_distributions,
            "acknowledged": acknowledged_count,
            "pending": pending_count,
            "acknowledgment_rate": (acknowledged_count / total_distributions * 100) if total_distributions > 0 else 0
        }
