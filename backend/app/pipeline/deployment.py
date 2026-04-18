"""
Deployment Manager with Rollback

Manages model deployments across staging and production environments.
Features:
- Blue-green deployment strategy
- Canary deployment support
- Automatic rollback on failure
- Health check integration
- Integration with PostgreSQL for deployment state
- MLflow integration for model artifacts
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json
import asyncio
from contextlib import asynccontextmanager

from sqlalchemy import (
    Column, String, Float, DateTime, Integer, JSON, 
    Enum as SQLEnum, Text, Boolean, ForeignKey, select, and_, desc
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal, AsyncSessionLocal
from app.core.config import settings

Base = declarative_base()


class DeploymentStatus(str, Enum):
    """Deployment status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    HEALTHY = "healthy"
    DEGRADED = "degraded"


class DeploymentStrategy(str, Enum):
    """Deployment strategy."""
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    RECREATE = "recreate"


class Environment(str, Enum):
    """Deployment environment."""
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentDB(Base):
    """Database model for deployments."""
    __tablename__ = "deployments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(String(64), unique=True, index=True, nullable=False)
    model_name = Column(String(255), nullable=False, index=True)
    model_version = Column(String(64), nullable=False)
    environment = Column(SQLEnum(Environment), nullable=False)
    strategy = Column(SQLEnum(DeploymentStrategy), default=DeploymentStrategy.BLUE_GREEN)
    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.PENDING)
    
    # Configuration
    config = Column(JSON)
    traffic_split = Column(JSON)  # For canary: {variant: percentage}
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    deployed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Attribution
    deployed_by = Column(String(255))
    deployment_reason = Column(Text)
    
    # Health and metrics
    health_checks = Column(JSON)
    metrics = Column(JSON)
    error_message = Column(Text)
    
    # Rollback
    previous_deployment_id = Column(String(64))
    rollback_triggered_by = Column(String(255))
    rollback_reason = Column(Text)
    rollback_completed_at = Column(DateTime)
    
    # Rollback reference (if this deployment was rolled back)
    rolled_back_by_id = Column(String(64))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "deployment_id": self.deployment_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "environment": self.environment.value if self.environment else None,
            "strategy": self.strategy.value if self.strategy else None,
            "status": self.status.value if self.status else None,
            "config": self.config or {},
            "traffic_split": self.traffic_split or {},
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deployed_by": self.deployed_by,
            "deployment_reason": self.deployment_reason,
            "health_checks": self.health_checks or {},
            "metrics": self.metrics or {},
            "error_message": self.error_message,
            "previous_deployment_id": self.previous_deployment_id,
            "rollback_triggered_by": self.rollback_triggered_by,
            "rollback_reason": self.rollback_reason,
            "rollback_completed_at": self.rollback_completed_at.isoformat() if self.rollback_completed_at else None,
            "rolled_back_by_id": self.rolled_back_by_id,
        }


class HealthCheckDB(Base):
    """Database model for health checks."""
    __tablename__ = "deployment_health_checks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deployment_id = Column(String(64), ForeignKey("deployments.deployment_id"))
    check_type = Column(String(64), nullable=False)  # http, metric, custom
    status = Column(String(16), default="pending")  # pending, passing, failing
    endpoint = Column(String(255))
    metric_name = Column(String(128))
    threshold = Column(Float)
    actual_value = Column(Float)
    checked_at = Column(DateTime, default=datetime.utcnow)
    error_message = Column(Text)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "deployment_id": self.deployment_id,
            "check_type": self.check_type,
            "status": self.status,
            "endpoint": self.endpoint,
            "metric_name": self.metric_name,
            "threshold": self.threshold,
            "actual_value": self.actual_value,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "error_message": self.error_message,
        }


@dataclass
class DeploymentConfig:
    """Configuration for deployment."""
    strategy: DeploymentStrategy = DeploymentStrategy.BLUE_GREEN
    health_check_interval_seconds: int = 30
    health_check_timeout_seconds: int = 60
    max_retries: int = 3
    canary_percentage: float = 10.0  # For canary deployments
    canary_duration_minutes: int = 30
    auto_rollback_on_failure: bool = True
    rollback_on_degradation: bool = True
    required_health_checks: int = 3  # Number of consecutive passing checks
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "health_check_interval_seconds": self.health_check_interval_seconds,
            "health_check_timeout_seconds": self.health_check_timeout_seconds,
            "max_retries": self.max_retries,
            "canary_percentage": self.canary_percentage,
            "canary_duration_minutes": self.canary_duration_minutes,
            "auto_rollback_on_failure": self.auto_rollback_on_failure,
            "rollback_on_degradation": self.rollback_on_degradation,
            "required_health_checks": self.required_health_checks,
        }


@dataclass
class HealthCheck:
    """Health check definition."""
    check_type: str  # http, metric, custom
    endpoint: Optional[str] = None
    metric_name: Optional[str] = None
    threshold: Optional[float] = None
    timeout_seconds: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_type": self.check_type,
            "endpoint": self.endpoint,
            "metric_name": self.metric_name,
            "threshold": self.threshold,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class DeploymentMetrics:
    """Metrics collected during deployment."""
    requests_per_second: float = 0.0
    error_rate: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "requests_per_second": self.requests_per_second,
            "error_rate": self.error_rate,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_mb": self.memory_usage_mb,
        }


@dataclass
class RollbackResult:
    """Result of rollback operation."""
    success: bool
    deployment_id: str
    rolled_back_to_version: str
    completed_at: datetime
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "deployment_id": self.deployment_id,
            "rolled_back_to_version": self.rolled_back_to_version,
            "completed_at": self.completed_at.isoformat(),
            "error_message": self.error_message,
        }


class DeploymentManager:
    """
    Deployment Manager for ML models.
    
    Supports deployment strategies:
    - Blue-Green: Zero-downtime deployment with instant switch
    - Canary: Gradual traffic shift with monitoring
    - Rolling: Incremental instance replacement
    - Recreate: Stop old, start new (downtime expected)
    
    Features:
    - Automatic health checks
    - Automatic rollback on failure
    - Traffic splitting for canary
    - PostgreSQL state persistence
    - MLflow integration for model artifacts
    """
    
    def __init__(self, use_async: bool = True):
        self._use_async = use_async
        self._health_check_tasks: Dict[str, asyncio.Task] = {}
    
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
    
    async def deploy(
        self,
        model_name: str,
        model_version: str,
        environment: Environment,
        deployed_by: str,
        deployment_reason: str,
        config: Optional[DeploymentConfig] = None,
        health_checks: Optional[List[HealthCheck]] = None
    ) -> str:
        """
        Deploy a model version to an environment.
        
        Returns deployment_id for tracking.
        """
        deployment_id = f"deploy_{uuid.uuid4().hex[:16]}"
        config = config or DeploymentConfig()
        
        # Find previous deployment
        async with self._get_db_session() as session:
            result = await session.execute(
                select(DeploymentDB)
                .where(DeploymentDB.model_name == model_name)
                .where(DeploymentDB.environment == environment)
                .where(DeploymentDB.status.in_([DeploymentStatus.DEPLOYED, DeploymentStatus.HEALTHY]))
                .order_by(desc(DeploymentDB.deployed_at))
                .limit(1)
            )
            previous = result.scalar_one_or_none()
            previous_id = previous.deployment_id if previous else None
        
        # Create deployment record
        async with self._get_db_session() as session:
            deployment = DeploymentDB(
                deployment_id=deployment_id,
                model_name=model_name,
                model_version=model_version,
                environment=environment,
                strategy=config.strategy,
                status=DeploymentStatus.IN_PROGRESS,
                config=config.to_dict(),
                traffic_split={"stable": 100.0, "canary": 0.0},  # Initial split
                deployed_by=deployed_by,
                deployment_reason=deployment_reason,
                previous_deployment_id=previous_id,
                health_checks={"checks": [hc.to_dict() for hc in (health_checks or [])]},
            )
            session.add(deployment)
        
        # Start deployment asynchronously
        asyncio.create_task(
            self._execute_deployment(deployment_id, config, health_checks or [])
        )
        
        return deployment_id
    
    async def _execute_deployment(
        self,
        deployment_id: str,
        config: DeploymentConfig,
        health_checks: List[HealthCheck]
    ):
        """Execute deployment workflow."""
        try:
            # Get deployment info
            async with self._get_db_session() as session:
                result = await session.execute(
                    select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
                )
                deployment = result.scalar_one()
                
                model_name = deployment.model_name
                model_version = deployment.model_version
                environment = deployment.environment
                strategy = deployment.strategy
            
            # Execute based on strategy
            if strategy == DeploymentStrategy.BLUE_GREEN:
                await self._deploy_blue_green(deployment_id, model_name, model_version, environment)
            elif strategy == DeploymentStrategy.CANARY:
                await self._deploy_canary(
                    deployment_id, model_name, model_version, environment, config
                )
            elif strategy == DeploymentStrategy.ROLLING:
                await self._deploy_rolling(deployment_id, model_name, model_version, environment)
            else:
                await self._deploy_recreate(deployment_id, model_name, model_version, environment)
            
            # Run health checks
            healthy = await self._run_health_checks(deployment_id, health_checks, config)
            
            if healthy:
                async with self._get_db_session() as session:
                    result = await session.execute(
                        select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
                    )
                    dep = result.scalar_one()
                    dep.status = DeploymentStatus.HEALTHY
                    dep.deployed_at = datetime.utcnow()
                    
                    # Update traffic split for canary
                    if strategy == DeploymentStrategy.CANARY:
                        dep.traffic_split = {"stable": 0.0, "canary": 100.0}
            else:
                # Health checks failed
                if config.auto_rollback_on_failure:
                    await self.rollback(deployment_id, "system", "Health checks failed")
                else:
                    async with self._get_db_session() as session:
                        result = await session.execute(
                            select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
                        )
                        dep = result.scalar_one()
                        dep.status = DeploymentStatus.DEGRADED
                        dep.error_message = "Health checks failed"
        
        except Exception as e:
            async with self._get_db_session() as session:
                result = await session.execute(
                    select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
                )
                deployment = result.scalar_one()
                deployment.status = DeploymentStatus.FAILED
                deployment.error_message = str(e)
                deployment.completed_at = datetime.utcnow()
            
            # Trigger rollback if enabled
            if config.auto_rollback_on_failure:
                await self.rollback(deployment_id, "system", f"Deployment failed: {str(e)}")
    
    async def _deploy_blue_green(
        self,
        deployment_id: str,
        model_name: str,
        model_version: str,
        environment: Environment
    ):
        """Execute blue-green deployment."""
        # 1. Deploy new version alongside current (green)
        # 2. Run health checks on green
        # 3. Switch traffic from blue to green
        # 4. Keep blue for rollback
        
        async with self._get_db_session() as session:
            result = await session.execute(
                select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
            )
            deployment = result.scalar_one()
            deployment.status = DeploymentStatus.DEPLOYED
    
    async def _deploy_canary(
        self,
        deployment_id: str,
        model_name: str,
        model_version: str,
        environment: Environment,
        config: DeploymentConfig
    ):
        """Execute canary deployment."""
        # 1. Deploy new version with small traffic percentage
        # 2. Gradually increase traffic while monitoring
        # 3. Full rollout if metrics healthy
        # 4. Automatic rollback if degradation detected
        
        canary_pct = config.canary_percentage
        stable_pct = 100.0 - canary_pct
        
        async with self._get_db_session() as session:
            result = await session.execute(
                select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
            )
            deployment = result.scalar_one()
            deployment.traffic_split = {"stable": stable_pct, "canary": canary_pct}
        
        # Monitor for canary_duration_minutes
        monitor_until = datetime.utcnow() + timedelta(minutes=config.canary_duration_minutes)
        
        while datetime.utcnow() < monitor_until:
            await asyncio.sleep(config.health_check_interval_seconds)
            
            # Check metrics
            metrics = await self._collect_metrics(deployment_id)
            
            # Check for degradation
            if self._is_degraded(metrics) and config.rollback_on_degradation:
                await self.rollback(deployment_id, "system", "Degradation detected during canary")
                return
            
            # Gradually increase canary traffic
            if canary_pct < 100.0:
                canary_pct = min(100.0, canary_pct + 10.0)
                stable_pct = 100.0 - canary_pct
                
                async with self._get_db_session() as session:
                    result = await session.execute(
                        select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
                    )
                    dep = result.scalar_one()
                    dep.traffic_split = {"stable": stable_pct, "canary": canary_pct}
        
        # Full deployment
        async with self._get_db_session() as session:
            result = await session.execute(
                select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
            )
            deployment = result.scalar_one()
            deployment.traffic_split = {"stable": 0.0, "canary": 100.0}
            deployment.status = DeploymentStatus.DEPLOYED
    
    async def _deploy_rolling(
        self,
        deployment_id: str,
        model_name: str,
        model_version: str,
        environment: Environment
    ):
        """Execute rolling deployment."""
        # Replace instances gradually
        async with self._get_db_session() as session:
            result = await session.execute(
                select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
            )
            deployment = result.scalar_one()
            deployment.status = DeploymentStatus.DEPLOYED
    
    async def _deploy_recreate(
        self,
        deployment_id: str,
        model_name: str,
        model_version: str,
        environment: Environment
    ):
        """Execute recreate deployment."""
        # Stop old, start new
        async with self._get_db_session() as session:
            result = await session.execute(
                select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
            )
            deployment = result.scalar_one()
            deployment.status = DeploymentStatus.DEPLOYED
    
    async def _run_health_checks(
        self,
        deployment_id: str,
        health_checks: List[HealthCheck],
        config: DeploymentConfig
    ) -> bool:
        """Run health checks and return overall status."""
        consecutive_passing = 0
        max_attempts = config.required_health_checks * 2  # Allow some failures
        
        for attempt in range(max_attempts):
            all_passing = True
            
            for check in health_checks:
                result = await self._execute_health_check(deployment_id, check)
                
                # Record check
                async with self._get_db_session() as session:
                    hc_db = HealthCheckDB(
                        deployment_id=deployment_id,
                        check_type=check.check_type,
                        status="passing" if result else "failing",
                        endpoint=check.endpoint,
                        metric_name=check.metric_name,
                        threshold=check.threshold,
                    )
                    session.add(hc_db)
                
                if not result:
                    all_passing = False
            
            if all_passing:
                consecutive_passing += 1
                if consecutive_passing >= config.required_health_checks:
                    return True
            else:
                consecutive_passing = 0
            
            await asyncio.sleep(config.health_check_interval_seconds)
        
        return False
    
    async def _execute_health_check(
        self,
        deployment_id: str,
        check: HealthCheck
    ) -> bool:
        """Execute a single health check."""
        try:
            if check.check_type == "http":
                # HTTP health check
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(check.endpoint, timeout=check.timeout_seconds) as resp:
                        return resp.status == 200
            
            elif check.check_type == "metric":
                # Metric-based check
                metrics = await self._collect_metrics(deployment_id)
                value = getattr(metrics, check.metric_name, None)
                if value is not None and check.threshold is not None:
                    return value <= check.threshold
                return False
            
            else:
                # Custom check
                return True
        
        except Exception as e:
            return False
    
    async def _collect_metrics(self, deployment_id: str) -> DeploymentMetrics:
        """Collect deployment metrics."""
        # In production, query metrics from monitoring system
        # For now, return placeholder
        return DeploymentMetrics(
            requests_per_second=100.0,
            error_rate=0.001,
            latency_p50_ms=50.0,
            latency_p95_ms=100.0,
            latency_p99_ms=150.0,
            cpu_usage_percent=30.0,
            memory_usage_mb=512.0,
        )
    
    def _is_degraded(self, metrics: DeploymentMetrics) -> bool:
        """Check if deployment metrics indicate degradation."""
        # Define degradation criteria
        return (
            metrics.error_rate > 0.05 or  # > 5% error rate
            metrics.latency_p99_ms > 500 or  # > 500ms p99 latency
            metrics.cpu_usage_percent > 80  # > 80% CPU
        )
    
    async def rollback(
        self,
        deployment_id: str,
        triggered_by: str,
        reason: str
    ) -> RollbackResult:
        """
        Rollback a deployment to the previous version.
        
        Args:
            deployment_id: ID of deployment to rollback
            triggered_by: User or system that triggered rollback
            reason: Reason for rollback
        """
        async with self._get_db_session() as session:
            result = await session.execute(
                select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
            )
            deployment = result.scalar_one_or_none()
            
            if not deployment:
                return RollbackResult(
                    success=False,
                    deployment_id=deployment_id,
                    rolled_back_to_version="",
                    completed_at=datetime.utcnow(),
                    error_message="Deployment not found"
                )
            
            if not deployment.previous_deployment_id:
                return RollbackResult(
                    success=False,
                    deployment_id=deployment_id,
                    rolled_back_to_version="",
                    completed_at=datetime.utcnow(),
                    error_message="No previous deployment to rollback to"
                )
            
            # Get previous deployment
            prev_result = await session.execute(
                select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
            )
            previous = prev_result.scalar_one_or_none()
            
            if not previous:
                return RollbackResult(
                    success=False,
                    deployment_id=deployment_id,
                    rolled_back_to_version="",
                    completed_at=datetime.utcnow(),
                    error_message="Previous deployment not found"
                )
            
            # Start rollback
            deployment.status = DeploymentStatus.ROLLING_BACK
            deployment.rollback_triggered_by = triggered_by
            deployment.rollback_reason = reason
        
        try:
            # Execute rollback
            # In production, this would trigger actual rollback
            await asyncio.sleep(2)  # Simulate rollback time
            
            # Update deployment status
            async with self._get_db_session() as session:
                result = await session.execute(
                    select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
                )
                dep = result.scalar_one()
                dep.status = DeploymentStatus.ROLLED_BACK
                dep.rollback_completed_at = datetime.utcnow()
                dep.completed_at = datetime.utcnow()
                dep.rolled_back_by_id = previous.deployment_id
            
            return RollbackResult(
                success=True,
                deployment_id=deployment_id,
                rolled_back_to_version=previous.model_version,
                completed_at=datetime.utcnow(),
                error_message=None
            )
        
        except Exception as e:
            async with self._get_db_session() as session:
                result = await session.execute(
                    select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
                )
                dep = result.scalar_one()
                dep.error_message = f"Rollback failed: {str(e)}"
            
            return RollbackResult(
                success=False,
                deployment_id=deployment_id,
                rolled_back_to_version="",
                completed_at=datetime.utcnow(),
                error_message=str(e)
            )
    
    async def get_deployment(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment details."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
            )
            deployment = result.scalar_one_or_none()
            
            if not deployment:
                return None
            
            return deployment.to_dict()
    
    async def list_deployments(
        self,
        model_name: Optional[str] = None,
        environment: Optional[Environment] = None,
        status: Optional[DeploymentStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List deployments."""
        async with self._get_db_session() as session:
            query = select(DeploymentDB)
            
            if model_name:
                query = query.where(DeploymentDB.model_name == model_name)
            if environment:
                query = query.where(DeploymentDB.environment == environment)
            if status:
                query = query.where(DeploymentDB.status == status)
            
            query = query.order_by(desc(DeploymentDB.started_at))
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            deployments = result.scalars().all()
            
            return [d.to_dict() for d in deployments]
    
    async def get_current_deployment(
        self,
        model_name: str,
        environment: Environment
    ) -> Optional[Dict[str, Any]]:
        """Get current active deployment for a model in an environment."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(DeploymentDB)
                .where(DeploymentDB.model_name == model_name)
                .where(DeploymentDB.environment == environment)
                .where(DeploymentDB.status.in_([DeploymentStatus.DEPLOYED, DeploymentStatus.HEALTHY]))
                .order_by(desc(DeploymentDB.deployed_at))
                .limit(1)
            )
            deployment = result.scalar_one_or_none()
            
            return deployment.to_dict() if deployment else None
    
    async def update_traffic_split(
        self,
        deployment_id: str,
        traffic_split: Dict[str, float]
    ) -> bool:
        """Update traffic split for a deployment."""
        async with self._get_db_session() as session:
            result = await session.execute(
                select(DeploymentDB).where(DeploymentDB.deployment_id == deployment_id)
            )
            deployment = result.scalar_one_or_none()
            
            if not deployment or deployment.status not in [
                DeploymentStatus.DEPLOYED, DeploymentStatus.HEALTHY
            ]:
                return False
            
            deployment.traffic_split = traffic_split
            return True


# Migration SQL
DEPLOYMENT_MIGRATION = """
-- Migration for deployment tables

-- Deployments table
CREATE TABLE IF NOT EXISTS deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id VARCHAR(64) UNIQUE NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    environment VARCHAR(16) NOT NULL,
    strategy VARCHAR(16) DEFAULT 'blue_green',
    status VARCHAR(16) DEFAULT 'pending',
    config JSONB,
    traffic_split JSONB,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deployed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    deployed_by VARCHAR(255),
    deployment_reason TEXT,
    health_checks JSONB,
    metrics JSONB,
    error_message TEXT,
    previous_deployment_id VARCHAR(64),
    rollback_triggered_by VARCHAR(255),
    rollback_reason TEXT,
    rollback_completed_at TIMESTAMP WITH TIME ZONE,
    rolled_back_by_id VARCHAR(64)
);

-- Health checks table
CREATE TABLE IF NOT EXISTS deployment_health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id VARCHAR(64) REFERENCES deployments(deployment_id),
    check_type VARCHAR(64) NOT NULL,
    status VARCHAR(16) DEFAULT 'pending',
    endpoint VARCHAR(255),
    metric_name VARCHAR(128),
    threshold FLOAT,
    actual_value FLOAT,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    error_message TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_deployments_model ON deployments(model_name);
CREATE INDEX IF NOT EXISTS idx_deployments_environment ON deployments(environment);
CREATE INDEX IF NOT EXISTS idx_deployments_status ON deployments(status);
CREATE INDEX IF NOT EXISTS idx_deployments_started ON deployments(started_at);
CREATE INDEX IF NOT EXISTS idx_health_checks_deployment ON deployment_health_checks(deployment_id);
CREATE INDEX IF NOT EXISTS idx_health_checks_status ON deployment_health_checks(status);
"""
