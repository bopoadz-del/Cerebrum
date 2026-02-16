"""
Prompt Registry Models

Versioned prompts table with performance metrics.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, JSON, Integer, Float, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PromptDB(Base):
    """SQLAlchemy model for versioned prompts."""
    __tablename__ = "prompts"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    
    # Prompt content
    system_prompt = Column(Text, nullable=True)
    user_prompt_template = Column(Text, nullable=False)
    
    # Metadata
    description = Column(String(1000), nullable=True)
    purpose = Column(String(255), nullable=False)  # e.g., "code_generation", "explanation"
    model = Column(String(100), default="gpt-4-turbo-preview")
    
    # Parameters
    temperature = Column(Float, default=0.2)
    max_tokens = Column(Integer, default=4000)
    top_p = Column(Float, default=1.0)
    frequency_penalty = Column(Float, default=0.0)
    presence_penalty = Column(Float, default=0.0)
    
    # Few-shot examples (stored as JSON)
    few_shot_examples = Column(JSON, default=list)
    
    # Performance metrics
    total_uses = Column(Integer, default=0)
    successful_uses = Column(Integer, default=0)
    failed_uses = Column(Integer, default=0)
    avg_tokens_used = Column(Float, default=0.0)
    avg_response_time_ms = Column(Float, default=0.0)
    user_rating_avg = Column(Float, default=0.0)
    user_rating_count = Column(Integer, default=0)
    
    # Quality metrics
    syntax_success_rate = Column(Float, default=0.0)
    security_pass_rate = Column(Float, default=0.0)
    test_pass_rate = Column(Float, default=0.0)
    
    # A/B testing
    is_active = Column(Integer, default=1)
    ab_test_group = Column(String(50), nullable=True)  # "control", "variant_a", etc.
    traffic_percentage = Column(Float, default=100.0)
    
    # Parent prompt (for versioning)
    parent_prompt_id = Column(String(36), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deprecated_at = Column(DateTime, nullable=True)
    
    # Author
    created_by = Column(String(255), nullable=False)


class Prompt(BaseModel):
    """Pydantic model for prompt data validation."""
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    version: int = Field(default=1, ge=1)
    
    system_prompt: Optional[str] = None
    user_prompt_template: str = Field(..., min_length=10)
    
    description: Optional[str] = None
    purpose: str = Field(..., min_length=1)
    model: str = "gpt-4-turbo-preview"
    
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, ge=1, le=8000)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    
    few_shot_examples: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metrics
    total_uses: int = 0
    successful_uses: int = 0
    failed_uses: int = 0
    avg_tokens_used: float = 0.0
    avg_response_time_ms: float = 0.0
    user_rating_avg: float = 0.0
    user_rating_count: int = 0
    
    syntax_success_rate: float = 0.0
    security_pass_rate: float = 0.0
    test_pass_rate: float = 0.0
    
    # A/B testing
    is_active: bool = True
    ab_test_group: Optional[str] = None
    traffic_percentage: float = Field(default=100.0, ge=0.0, le=100.0)
    
    parent_prompt_id: Optional[str] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None
    created_by: str = Field(..., min_length=1)
    
    class Config:
        from_attributes = True


class PromptCreate(BaseModel):
    """Model for creating a new prompt."""
    name: str = Field(..., min_length=1, max_length=255)
    system_prompt: Optional[str] = None
    user_prompt_template: str = Field(..., min_length=10)
    description: Optional[str] = None
    purpose: str = Field(..., min_length=1)
    model: str = "gpt-4-turbo-preview"
    temperature: float = 0.2
    max_tokens: int = 4000
    few_shot_examples: List[Dict[str, Any]] = Field(default_factory=list)
    created_by: str = Field(..., min_length=1)


class PromptUpdate(BaseModel):
    """Model for updating a prompt."""
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = Field(None, min_length=10)
    description: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=8000)
    few_shot_examples: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
    traffic_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)


class PromptMetricsUpdate(BaseModel):
    """Model for updating prompt metrics."""
    tokens_used: Optional[int] = None
    response_time_ms: Optional[float] = None
    success: Optional[bool] = None
    syntax_valid: Optional[bool] = None
    security_passed: Optional[bool] = None
    tests_passed: Optional[bool] = None
    user_rating: Optional[int] = Field(None, ge=1, le=5)


class PromptVersion(BaseModel):
    """Model for prompt version info."""
    version: int
    created_at: datetime
    created_by: str
    is_active: bool
    metrics_summary: Dict[str, float]


class PromptComparison(BaseModel):
    """Model for comparing prompt versions."""
    prompt_a: Prompt
    prompt_b: Prompt
    metrics_comparison: Dict[str, Dict[str, float]]
    winner: Optional[str]
    confidence: float
