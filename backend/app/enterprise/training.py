"""
Training Module - Training Portals and Documentation
Item 293: Training portals and documentation
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
from app.db.base_class import Base

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


class ContentType(str, Enum):
    """Training content types"""
    VIDEO = "video"
    ARTICLE = "article"
    INTERACTIVE = "interactive"
    QUIZ = "quiz"
    WEBINAR = "webinar"
    DOCUMENTATION = "documentation"
    TUTORIAL = "tutorial"


class DifficultyLevel(str, Enum):
    """Content difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class EnrollmentStatus(str, Enum):
    """Course enrollment status"""
    ENROLLED = "enrolled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DROPPED = "dropped"


# Database Models

class TrainingCourse(Base):
    """Training course"""
    __tablename__ = 'training_courses'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    # Course info
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    
    # Content
    content_type = Column(String(50), default=ContentType.VIDEO.value)
    difficulty = Column(String(50), default=DifficultyLevel.BEGINNER.value)
    
    # Media
    thumbnail_url = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    content_html = Column(Text, nullable=True)
    
    # Metadata
    duration_minutes = Column(Integer, nullable=True)
    tags = Column(JSONB, default=list)
    category = Column(String(100), nullable=True)
    
    # Requirements
    prerequisites = Column(JSONB, default=list)
    required_roles = Column(JSONB, default=list)
    
    # Settings
    is_published = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    is_required = Column(Boolean, default=False)
    
    # Progress tracking
    has_quiz = Column(Boolean, default=False)
    passing_score = Column(Integer, default=80)
    
    # Timestamps
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class CourseModule(Base):
    """Course module/lesson"""
    __tablename__ = 'course_modules'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey('training_courses.id', ondelete='CASCADE'), nullable=False)
    
    # Module info
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Content
    content_type = Column(String(50), default=ContentType.VIDEO.value)
    content_url = Column(String(500), nullable=True)
    content_html = Column(Text, nullable=True)
    
    # Ordering
    order_index = Column(Integer, default=0)
    
    # Metadata
    duration_minutes = Column(Integer, nullable=True)
    
    # Settings
    is_required = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class UserEnrollment(Base):
    """User course enrollment"""
    __tablename__ = 'user_enrollments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey('training_courses.id', ondelete='CASCADE'), nullable=False)
    
    # Progress
    status = Column(String(50), default=EnrollmentStatus.ENROLLED.value)
    progress_percentage = Column(Integer, default=0)
    completed_modules = Column(JSONB, default=list)
    
    # Timestamps
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Quiz results
    quiz_score = Column(Integer, nullable=True)
    quiz_attempts = Column(Integer, default=0)
    
    # Certificate
    certificate_issued = Column(Boolean, default=False)
    certificate_url = Column(String(500), nullable=True)
    
    __table_args__ = (
        Index('ix_enrollments_user_course', 'user_id', 'course_id', unique=True),
    )


class DocumentationPage(Base):
    """Documentation page"""
    __tablename__ = 'documentation_pages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True)
    
    # Page info
    title = Column(String(500), nullable=False)
    slug = Column(String(255), nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    content_format = Column(String(20), default='markdown')  # markdown, html
    
    # Organization
    category = Column(String(100), nullable=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('documentation_pages.id'), nullable=True)
    order_index = Column(Integer, default=0)
    
    # Metadata
    tags = Column(JSONB, default=list)
    
    # Settings
    is_published = Column(Boolean, default=True)
    is_searchable = Column(Boolean, default=True)
    
    # SEO
    meta_description = Column(String(500), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)


class TrainingCertificate(Base):
    """Training certificates"""
    __tablename__ = 'training_certificates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey('user_enrollments.id', ondelete='CASCADE'), nullable=False)
    
    # Certificate info
    certificate_number = Column(String(100), unique=True, nullable=False)
    
    # Verification
    verification_code = Column(String(255), unique=True, nullable=False)
    
    # Status
    is_valid = Column(Boolean, default=True)
    
    # Expiration
    issued_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # PDF URL
    pdf_url = Column(String(500), nullable=True)


# Pydantic Schemas

class CreateCourseRequest(BaseModel):
    """Create training course"""
    title: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    content_type: ContentType = ContentType.VIDEO
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    duration_minutes: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    prerequisites: List[str] = Field(default_factory=list)
    has_quiz: bool = False
    passing_score: int = 80


class CreateModuleRequest(BaseModel):
    """Create course module"""
    title: str
    description: Optional[str] = None
    content_type: ContentType = ContentType.VIDEO
    content_url: Optional[str] = None
    content_html: Optional[str] = None
    duration_minutes: Optional[int] = None
    order_index: int = 0
    is_required: bool = True


class CreateDocPageRequest(BaseModel):
    """Create documentation page"""
    title: str
    slug: str
    content: str
    content_format: str = 'markdown'
    category: Optional[str] = None
    parent_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    meta_description: Optional[str] = None


class EnrollmentResponse(BaseModel):
    """Enrollment response"""
    id: str
    course_id: str
    status: str
    progress_percentage: int
    enrolled_at: datetime
    completed_at: Optional[datetime]


class CourseProgressResponse(BaseModel):
    """Course progress response"""
    course_id: str
    course_title: str
    status: str
    progress_percentage: int
    completed_modules: int
    total_modules: int
    time_spent_minutes: int
    quiz_score: Optional[int]


# Service Classes

class TrainingService:
    """Service for training management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_course(
        self,
        tenant_id: Optional[str],
        request: CreateCourseRequest,
        created_by: Optional[str] = None
    ) -> TrainingCourse:
        """Create training course"""
        
        course = TrainingCourse(
            tenant_id=tenant_id,
            title=request.title,
            description=request.description,
            short_description=request.short_description,
            content_type=request.content_type.value,
            difficulty=request.difficulty.value,
            duration_minutes=request.duration_minutes,
            tags=request.tags,
            category=request.category,
            prerequisites=request.prerequisites,
            has_quiz=request.has_quiz,
            passing_score=request.passing_score,
            created_by=created_by
        )
        
        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)
        
        return course
    
    def get_course(self, course_id: str) -> Optional[TrainingCourse]:
        """Get course by ID"""
        return self.db.query(TrainingCourse).filter(TrainingCourse.id == course_id).first()
    
    def list_courses(
        self,
        tenant_id: Optional[str] = None,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        is_published: Optional[bool] = True
    ) -> List[TrainingCourse]:
        """List training courses"""
        
        query = self.db.query(TrainingCourse)
        
        if tenant_id:
            query = query.filter(
                (TrainingCourse.tenant_id == tenant_id) | (TrainingCourse.tenant_id.is_(None))
            )
        
        if category:
            query = query.filter(TrainingCourse.category == category)
        
        if difficulty:
            query = query.filter(TrainingCourse.difficulty == difficulty)
        
        if is_published is not None:
            query = query.filter(TrainingCourse.is_published == is_published)
        
        return query.order_by(TrainingCourse.created_at.desc()).all()
    
    def add_module(
        self,
        course_id: str,
        request: CreateModuleRequest
    ) -> CourseModule:
        """Add module to course"""
        
        course = self.get_course(course_id)
        if not course:
            raise HTTPException(404, "Course not found")
        
        module = CourseModule(
            course_id=course_id,
            title=request.title,
            description=request.description,
            content_type=request.content_type.value,
            content_url=request.content_url,
            content_html=request.content_html,
            duration_minutes=request.duration_minutes,
            order_index=request.order_index,
            is_required=request.is_required
        )
        
        self.db.add(module)
        self.db.commit()
        self.db.refresh(module)
        
        return module
    
    def enroll_user(
        self,
        user_id: str,
        course_id: str
    ) -> UserEnrollment:
        """Enroll user in course"""
        
        # Check if already enrolled
        existing = self.db.query(UserEnrollment).filter(
            UserEnrollment.user_id == user_id,
            UserEnrollment.course_id == course_id
        ).first()
        
        if existing:
            return existing
        
        enrollment = UserEnrollment(
            user_id=user_id,
            course_id=course_id,
            status=EnrollmentStatus.ENROLLED.value
        )
        
        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)
        
        return enrollment
    
    def update_progress(
        self,
        user_id: str,
        course_id: str,
        module_id: str,
        completed: bool = True
    ) -> UserEnrollment:
        """Update user progress"""
        
        enrollment = self.db.query(UserEnrollment).filter(
            UserEnrollment.user_id == user_id,
            UserEnrollment.course_id == course_id
        ).first()
        
        if not enrollment:
            raise HTTPException(404, "Enrollment not found")
        
        # Update completed modules
        completed_modules = set(enrollment.completed_modules or [])
        
        if completed:
            completed_modules.add(module_id)
        else:
            completed_modules.discard(module_id)
        
        enrollment.completed_modules = list(completed_modules)
        enrollment.last_accessed_at = datetime.utcnow()
        
        # Calculate progress
        course = self.get_course(course_id)
        if course:
            total_modules = self.db.query(CourseModule).filter(
                CourseModule.course_id == course_id
            ).count()
            
            if total_modules > 0:
                enrollment.progress_percentage = int(
                    len(completed_modules) / total_modules * 100
                )
        
        # Update status
        if enrollment.progress_percentage == 100:
            enrollment.status = EnrollmentStatus.COMPLETED.value
            enrollment.completed_at = datetime.utcnow()
        elif enrollment.progress_percentage > 0:
            enrollment.status = EnrollmentStatus.IN_PROGRESS.value
            if not enrollment.started_at:
                enrollment.started_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(enrollment)
        
        return enrollment
    
    def get_user_progress(
        self,
        user_id: str,
        course_id: str
    ) -> Dict[str, Any]:
        """Get user's progress in a course"""
        
        enrollment = self.db.query(UserEnrollment).filter(
            UserEnrollment.user_id == user_id,
            UserEnrollment.course_id == course_id
        ).first()
        
        if not enrollment:
            return {
                'enrolled': False,
                'status': None,
                'progress_percentage': 0
            }
        
        course = self.get_course(course_id)
        total_modules = self.db.query(CourseModule).filter(
            CourseModule.course_id == course_id
        ).count()
        
        return {
            'enrolled': True,
            'status': enrollment.status,
            'progress_percentage': enrollment.progress_percentage,
            'completed_modules': len(enrollment.completed_modules or []),
            'total_modules': total_modules,
            'started_at': enrollment.started_at.isoformat() if enrollment.started_at else None,
            'completed_at': enrollment.completed_at.isoformat() if enrollment.completed_at else None,
            'quiz_score': enrollment.quiz_score,
            'certificate_issued': enrollment.certificate_issued
        }
    
    def submit_quiz(
        self,
        user_id: str,
        course_id: str,
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit quiz answers"""
        
        enrollment = self.db.query(UserEnrollment).filter(
            UserEnrollment.user_id == user_id,
            UserEnrollment.course_id == course_id
        ).first()
        
        if not enrollment:
            raise HTTPException(404, "Enrollment not found")
        
        course = self.get_course(course_id)
        if not course or not course.has_quiz:
            raise HTTPException(400, "Course does not have a quiz")
        
        # Calculate score (simplified)
        # In production, compare answers against correct answers
        score = answers.get('score', 0)
        
        enrollment.quiz_score = score
        enrollment.quiz_attempts += 1
        
        # Issue certificate if passed
        if score >= course.passing_score:
            self._issue_certificate(enrollment)
        
        self.db.commit()
        
        return {
            'score': score,
            'passing_score': course.passing_score,
            'passed': score >= course.passing_score,
            'attempts': enrollment.quiz_attempts
        }
    
    def _issue_certificate(self, enrollment: UserEnrollment):
        """Issue certificate for completed course"""
        
        if enrollment.certificate_issued:
            return
        
        # Generate certificate number
        cert_number = f"CER-{datetime.utcnow().strftime('%Y%m%d')}-{str(enrollment.id)[:8].upper()}"
        verification_code = str(uuid.uuid4()).replace('-', '')
        
        certificate = TrainingCertificate(
            enrollment_id=enrollment.id,
            certificate_number=cert_number,
            verification_code=verification_code
        )
        
        self.db.add(certificate)
        
        enrollment.certificate_issued = True
        enrollment.certificate_url = f"/certificates/{cert_number}"


class DocumentationService:
    """Service for documentation management"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_page(
        self,
        tenant_id: Optional[str],
        request: CreateDocPageRequest,
        created_by: Optional[str] = None
    ) -> DocumentationPage:
        """Create documentation page"""
        
        # Check for duplicate slug
        existing = self.db.query(DocumentationPage).filter(
            DocumentationPage.tenant_id == tenant_id,
            DocumentationPage.slug == request.slug
        ).first()
        
        if existing:
            raise HTTPException(409, "Page with this slug already exists")
        
        page = DocumentationPage(
            tenant_id=tenant_id,
            title=request.title,
            slug=request.slug,
            content=request.content,
            content_format=request.content_format,
            category=request.category,
            parent_id=request.parent_id,
            tags=request.tags,
            meta_description=request.meta_description,
            updated_by=created_by
        )
        
        self.db.add(page)
        self.db.commit()
        self.db.refresh(page)
        
        return page
    
    def get_page(self, page_id: str) -> Optional[DocumentationPage]:
        """Get page by ID"""
        return self.db.query(DocumentationPage).filter(DocumentationPage.id == page_id).first()
    
    def get_page_by_slug(
        self,
        slug: str,
        tenant_id: Optional[str] = None
    ) -> Optional[DocumentationPage]:
        """Get page by slug"""
        
        query = self.db.query(DocumentationPage).filter(DocumentationPage.slug == slug)
        
        if tenant_id:
            query = query.filter(
                (DocumentationPage.tenant_id == tenant_id) | (DocumentationPage.tenant_id.is_(None))
            )
        
        return query.first()
    
    def list_pages(
        self,
        tenant_id: Optional[str] = None,
        category: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> List[DocumentationPage]:
        """List documentation pages"""
        
        query = self.db.query(DocumentationPage).filter(
            DocumentationPage.is_published == True
        )
        
        if tenant_id:
            query = query.filter(
                (DocumentationPage.tenant_id == tenant_id) | (DocumentationPage.tenant_id.is_(None))
            )
        
        if category:
            query = query.filter(DocumentationPage.category == category)
        
        if parent_id:
            query = query.filter(DocumentationPage.parent_id == parent_id)
        else:
            query = query.filter(DocumentationPage.parent_id.is_(None))
        
        return query.order_by(DocumentationPage.order_index, DocumentationPage.title).all()
    
    def search_pages(
        self,
        query: str,
        tenant_id: Optional[str] = None
    ) -> List[DocumentationPage]:
        """Search documentation pages"""
        
        search = f"%{query}%"
        
        db_query = self.db.query(DocumentationPage).filter(
            DocumentationPage.is_published == True,
            DocumentationPage.is_searchable == True
        ).filter(
            (DocumentationPage.title.ilike(search)) |
            (DocumentationPage.content.ilike(search)) |
            (DocumentationPage.tags.contains([query]))
        )
        
        if tenant_id:
            db_query = db_query.filter(
                (DocumentationPage.tenant_id == tenant_id) | (DocumentationPage.tenant_id.is_(None))
            )
        
        return db_query.limit(20).all()


# Export
__all__ = [
    'ContentType',
    'DifficultyLevel',
    'EnrollmentStatus',
    'TrainingCourse',
    'CourseModule',
    'UserEnrollment',
    'DocumentationPage',
    'TrainingCertificate',
    'CreateCourseRequest',
    'CreateModuleRequest',
    'CreateDocPageRequest',
    'EnrollmentResponse',
    'CourseProgressResponse',
    'TrainingService',
    'DocumentationService'
]
