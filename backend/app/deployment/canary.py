"""
Canary Releases with Feature Flags
Implements gradual rollouts with feature flag support.
"""
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import random
import logging

logger = logging.getLogger(__name__)


class CanaryStrategy(str, Enum):
    """Canary release strategies."""
    PERCENTAGE = "percentage"
    USER_SEGMENT = "user_segment"
    GEOGRAPHIC = "geographic"
    RANDOM = "random"
    HASH = "hash"


class FeatureFlagStatus(str, Enum):
    """Feature flag status."""
    OFF = "off"
    DEVELOPMENT = "development"
    CANARY = "canary"
    ENABLED = "enabled"


@dataclass
class FeatureFlag:
    """Feature flag configuration."""
    name: str
    description: str = ""
    status: FeatureFlagStatus = FeatureFlagStatus.OFF
    owner: str = ""
    created_at: str = ""
    
    # Canary settings
    canary_percentage: int = 0  # 0-100
    canary_users: List[str] = field(default_factory=list)
    canary_groups: List[str] = field(default_factory=list)
    
    # Rules
    rules: List[Dict[str, Any]] = field(default_factory=list)
    
    def is_enabled(self, user_id: Optional[str] = None,
                   user_groups: Optional[List[str]] = None,
                   context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if feature is enabled for user/context."""
        if self.status == FeatureFlagStatus.OFF:
            return False
        
        if self.status == FeatureFlagStatus.ENABLED:
            return True
        
        if self.status == FeatureFlagStatus.DEVELOPMENT:
            # Only for development/internal users
            if context and context.get('environment') == 'development':
                return True
            return False
        
        if self.status == FeatureFlagStatus.CANARY:
            return self._check_canary(user_id, user_groups, context)
        
        return False
    
    def _check_canary(self, user_id: Optional[str],
                     user_groups: Optional[List[str]],
                     context: Optional[Dict[str, Any]]) -> bool:
        """Check canary eligibility."""
        # Check specific users
        if user_id and user_id in self.canary_users:
            return True
        
        # Check groups
        if user_groups:
            for group in user_groups:
                if group in self.canary_groups:
                    return True
        
        # Check percentage rollout
        if self.canary_percentage > 0 and user_id:
            user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
            user_percentile = user_hash % 100
            return user_percentile < self.canary_percentage
        
        return False


@dataclass
class CanaryRelease:
    """Canary release configuration."""
    name: str
    version: str
    current_percentage: int = 0
    target_percentage: int = 100
    step_size: int = 10
    step_interval_minutes: int = 30
    
    # Success criteria
    error_rate_threshold: float = 0.01  # 1%
    latency_threshold_ms: float = 500
    
    # Current metrics
    current_error_rate: float = 0.0
    current_latency_p99: float = 0.0
    
    # Status
    status: str = "pending"  # pending, running, paused, completed, rolled_back
    
    def should_advance(self) -> bool:
        """Check if canary should advance to next step."""
        if self.status != "running":
            return False
        
        # Check error rate
        if self.current_error_rate > self.error_rate_threshold:
            logger.warning(f"Error rate {self.current_error_rate} exceeds threshold")
            return False
        
        # Check latency
        if self.current_latency_p99 > self.latency_threshold_ms:
            logger.warning(f"Latency {self.current_latency_p99}ms exceeds threshold")
            return False
        
        return True


class FeatureFlagManager:
    """Manages feature flags and canary releases."""
    
    def __init__(self, storage_backend=None):
        self.storage = storage_backend
        self.flags: Dict[str, FeatureFlag] = {}
        self.canaries: Dict[str, CanaryRelease] = {}
        self._load_flags()
    
    def _load_flags(self):
        """Load flags from storage."""
        if self.storage:
            flags_data = self.storage.load_flags()
            for name, data in flags_data.items():
                self.flags[name] = FeatureFlag(**data)
    
    def create_flag(self, name: str, description: str = "",
                   owner: str = "") -> FeatureFlag:
        """Create a new feature flag."""
        from datetime import datetime
        
        flag = FeatureFlag(
            name=name,
            description=description,
            owner=owner,
            created_at=datetime.utcnow().isoformat()
        )
        
        self.flags[name] = flag
        self._save_flags()
        
        logger.info(f"Created feature flag: {name}")
        return flag
    
    def get_flag(self, name: str) -> Optional[FeatureFlag]:
        """Get feature flag by name."""
        return self.flags.get(name)
    
    def update_flag(self, name: str, **kwargs) -> Optional[FeatureFlag]:
        """Update feature flag."""
        flag = self.flags.get(name)
        if not flag:
            return None
        
        for key, value in kwargs.items():
            if hasattr(flag, key):
                setattr(flag, key, value)
        
        self._save_flags()
        logger.info(f"Updated feature flag: {name}")
        return flag
    
    def delete_flag(self, name: str) -> bool:
        """Delete feature flag."""
        if name in self.flags:
            del self.flags[name]
            self._save_flags()
            logger.info(f"Deleted feature flag: {name}")
            return True
        return False
    
    def is_enabled(self, flag_name: str, user_id: Optional[str] = None,
                   user_groups: Optional[List[str]] = None,
                   context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if feature is enabled."""
        flag = self.flags.get(flag_name)
        if not flag:
            return False
        
        return flag.is_enabled(user_id, user_groups, context)
    
    def _save_flags(self):
        """Save flags to storage."""
        if self.storage:
            flags_data = {
                name: {
                    'name': f.name,
                    'description': f.description,
                    'status': f.status.value,
                    'owner': f.owner,
                    'created_at': f.created_at,
                    'canary_percentage': f.canary_percentage,
                    'canary_users': f.canary_users,
                    'canary_groups': f.canary_groups,
                }
                for name, f in self.flags.items()
            }
            self.storage.save_flags(flags_data)
    
    # Canary release methods
    def start_canary(self, name: str, version: str,
                    step_size: int = 10,
                    step_interval_minutes: int = 30) -> CanaryRelease:
        """Start a new canary release."""
        canary = CanaryRelease(
            name=name,
            version=version,
            step_size=step_size,
            step_interval_minutes=step_interval_minutes,
            status="running"
        )
        
        self.canaries[name] = canary
        logger.info(f"Started canary release: {name} v{version}")
        return canary
    
    def advance_canary(self, name: str) -> Optional[CanaryRelease]:
        """Advance canary to next step."""
        canary = self.canaries.get(name)
        if not canary:
            return None
        
        if not canary.should_advance():
            logger.warning(f"Canary {name} cannot advance - metrics exceeded thresholds")
            return canary
        
        canary.current_percentage = min(
            canary.current_percentage + canary.step_size,
            canary.target_percentage
        )
        
        if canary.current_percentage >= canary.target_percentage:
            canary.status = "completed"
            logger.info(f"Canary {name} completed at 100%")
        
        return canary
    
    def pause_canary(self, name: str) -> Optional[CanaryRelease]:
        """Pause canary release."""
        canary = self.canaries.get(name)
        if canary:
            canary.status = "paused"
            logger.info(f"Paused canary: {name}")
        return canary
    
    def resume_canary(self, name: str) -> Optional[CanaryRelease]:
        """Resume canary release."""
        canary = self.canaries.get(name)
        if canary:
            canary.status = "running"
            logger.info(f"Resumed canary: {name}")
        return canary
    
    def rollback_canary(self, name: str) -> Optional[CanaryRelease]:
        """Rollback canary release."""
        canary = self.canaries.get(name)
        if canary:
            canary.status = "rolled_back"
            canary.current_percentage = 0
            logger.info(f"Rolled back canary: {name}")
        return canary
    
    def get_canary_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get canary release status."""
        canary = self.canaries.get(name)
        if not canary:
            return None
        
        return {
            "name": canary.name,
            "version": canary.version,
            "current_percentage": canary.current_percentage,
            "target_percentage": canary.target_percentage,
            "status": canary.status,
            "current_error_rate": canary.current_error_rate,
            "current_latency_p99": canary.current_latency_p99,
            "error_threshold": canary.error_rate_threshold,
            "latency_threshold": canary.latency_threshold_ms
        }


# Decorator for feature-flagged functions
def feature_flagged(flag_name: str, default_value: Any = None):
    """Decorator to make a function feature-flagged."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Get feature flag manager (would be injected or singleton)
            from flask import request
            
            user_id = kwargs.get('user_id') or request.headers.get('X-User-ID')
            user_groups = kwargs.get('user_groups', [])
            
            # Check if feature is enabled
            # In production, use proper manager instance
            is_enabled = True  # Placeholder
            
            if is_enabled:
                return func(*args, **kwargs)
            else:
                return default_value
        
        return wrapper
    return decorator


# Kubernetes Canary Deployment configuration
K8S_CANARY_DEPLOYMENT = """
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: cerebrum-api
  namespace: default
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cerebrum-api
  service:
    port: 80
    targetPort: 8000
    gateways:
    - cerebrum-gateway
    hosts:
    - api.cerebrum.local
  analysis:
    interval: 30s
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500
      interval: 1m
    webhooks:
    - name: load-test
      url: http://flagger-loadtester.test/
      timeout: 5s
      metadata:
        cmd: "hey -z 1m -q 10 -c 2 http://cerebrum-api-canary/"
    - name: conformance-test
      type: pre-rollout
      url: http://flagger-loadtester.test/
      timeout: 30s
      metadata:
        type: bash
        cmd: "curl -sf http://cerebrum-api-canary/health"
  progressDeadlineSeconds: 600
"""


# Istio VirtualService for canary
ISTIO_CANARY_VIRTUALSERVICE = """
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: cerebrum-api
spec:
  hosts:
  - api.cerebrum.local
  gateways:
  - cerebrum-gateway
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: cerebrum-api-canary
      weight: 100
  - route:
    - destination:
        host: cerebrum-api
      weight: 90
    - destination:
        host: cerebrum-api-canary
      weight: 10
"""


# Example feature flags
DEFAULT_FEATURE_FLAGS = {
    "new_dashboard": {
        "description": "New dashboard UI",
        "status": "canary",
        "canary_percentage": 10
    },
    "enhanced_search": {
        "description": "Enhanced search with AI",
        "status": "development"
    },
    "realtime_collaboration": {
        "description": "Real-time model collaboration",
        "status": "off"
    },
    "advanced_analytics": {
        "description": "Advanced analytics dashboard",
        "status": "enabled"
    }
}
