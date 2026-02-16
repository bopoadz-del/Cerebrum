"""
Blue-Green Deployment Strategy
Zero-downtime deployment using blue-green switching.
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import kubernetes
from kubernetes import client, config
import logging

logger = logging.getLogger(__name__)


class DeploymentColor(Enum):
    """Deployment color (blue or green)."""
    BLUE = "blue"
    GREEN = "green"


class DeploymentStatus(Enum):
    """Deployment status."""
    IDLE = "idle"
    DEPLOYING = "deploying"
    VALIDATING = "validating"
    SWITCHING = "switching"
    COMPLETED = "completed"
    ROLLING_BACK = "rolling_back"
    FAILED = "failed"


@dataclass
class DeploymentConfig:
    """Blue-green deployment configuration."""
    app_name: str
    namespace: str = "default"
    blue_deployment: str = ""
    green_deployment: str = ""
    service_name: str = ""
    ingress_name: str = ""
    health_check_url: str = ""
    validation_timeout: int = 300
    switch_timeout: int = 60


@dataclass
class DeploymentState:
    """Current deployment state."""
    active_color: DeploymentColor
    target_color: DeploymentColor
    status: DeploymentStatus
    version: str
    previous_version: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]


class BlueGreenDeployer:
    """Manager for blue-green deployments."""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.state: Optional[DeploymentState] = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize Kubernetes client
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        
        self.k8s_apps = client.AppsV1Api()
        self.k8s_core = client.CoreV1Api()
        self.k8s_networking = client.NetworkingV1Api()
    
    async def deploy(self, version: str, image: str) -> bool:
        """Deploy new version using blue-green strategy."""
        try:
            # Determine target color (opposite of active)
            current_state = await self.get_current_state()
            active_color = current_state['active_color']
            target_color = DeploymentColor.GREEN if active_color == DeploymentColor.BLUE else DeploymentColor.BLUE
            
            self.logger.info(f"Starting blue-green deployment: {active_color.value} -> {target_color.value}")
            
            # Update state
            self.state = DeploymentState(
                active_color=active_color,
                target_color=target_color,
                status=DeploymentStatus.DEPLOYING,
                version=version,
                previous_version=current_state['version'],
                started_at=datetime.utcnow(),
                completed_at=None,
                error_message=None
            )
            
            # Deploy to target environment
            await self._deploy_to_target(target_color, version, image)
            
            # Validate deployment
            self.state.status = DeploymentStatus.VALIDATING
            if not await self._validate_deployment(target_color):
                self.state.status = DeploymentStatus.FAILED
                self.state.error_message = "Deployment validation failed"
                return False
            
            # Switch traffic
            self.state.status = DeploymentStatus.SWITCHING
            await self._switch_traffic(target_color)
            
            # Update state
            self.state.active_color = target_color
            self.state.status = DeploymentStatus.COMPLETED
            self.state.completed_at = datetime.utcnow()
            
            self.logger.info(f"Blue-green deployment completed: now active on {target_color.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Blue-green deployment failed: {e}")
            if self.state:
                self.state.status = DeploymentStatus.FAILED
                self.state.error_message = str(e)
            return False
    
    async def rollback(self) -> bool:
        """Rollback to previous version."""
        if not self.state or not self.state.previous_version:
            self.logger.error("No previous version to rollback to")
            return False
        
        try:
            self.state.status = DeploymentStatus.ROLLING_BACK
            
            # Switch back to previous color
            await self._switch_traffic(self.state.active_color)
            
            self.state.status = DeploymentStatus.COMPLETED
            self.logger.info(f"Rollback completed: restored {self.state.active_color.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    async def _deploy_to_target(
        self,
        color: DeploymentColor,
        version: str,
        image: str
    ):
        """Deploy to target environment."""
        deployment_name = self.config.green_deployment if color == DeploymentColor.GREEN else self.config.blue_deployment
        
        self.logger.info(f"Deploying to {deployment_name}: {image}")
        
        # Get current deployment
        deployment = self.k8s_apps.read_namespaced_deployment(
            name=deployment_name,
            namespace=self.config.namespace
        )
        
        # Update image
        deployment.spec.template.spec.containers[0].image = image
        
        # Update labels
        deployment.spec.template.metadata.labels['version'] = version
        deployment.spec.template.metadata.labels['color'] = color.value
        
        # Apply deployment
        self.k8s_apps.patch_namespaced_deployment(
            name=deployment_name,
            namespace=self.config.namespace,
            body=deployment
        )
        
        # Wait for rollout
        await self._wait_for_rollout(deployment_name)
    
    async def _wait_for_rollout(self, deployment_name: str, timeout: int = 300):
        """Wait for deployment rollout to complete."""
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            deployment = self.k8s_apps.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.config.namespace
            )
            
            if deployment.status.ready_replicas == deployment.spec.replicas:
                self.logger.info(f"Rollout complete for {deployment_name}")
                return
            
            await asyncio.sleep(5)
        
        raise TimeoutError(f"Rollout timeout for {deployment_name}")
    
    async def _validate_deployment(self, color: DeploymentColor) -> bool:
        """Validate deployment health."""
        self.logger.info(f"Validating {color.value} deployment")
        
        # Get pods for target deployment
        deployment_name = self.config.green_deployment if color == DeploymentColor.GREEN else self.config.blue_deployment
        
        pods = self.k8s_core.list_namespaced_pod(
            namespace=self.config.namespace,
            label_selector=f"color={color.value}"
        )
        
        # Check pod health
        for pod in pods.items:
            if pod.status.phase != 'Running':
                self.logger.error(f"Pod {pod.metadata.name} is not running: {pod.status.phase}")
                return False
            
            # Check readiness
            if pod.status.conditions:
                ready_condition = next(
                    (c for c in pod.status.conditions if c.type == 'Ready'),
                    None
                )
                if not ready_condition or ready_condition.status != 'True':
                    self.logger.error(f"Pod {pod.metadata.name} is not ready")
                    return False
        
        # Health check endpoint
        if self.config.health_check_url:
            # Would make HTTP request to health endpoint
            pass
        
        return True
    
    async def _switch_traffic(self, color: DeploymentColor):
        """Switch traffic to target color."""
        self.logger.info(f"Switching traffic to {color.value}")
        
        # Update service selector
        service = self.k8s_core.read_namespaced_service(
            name=self.config.service_name,
            namespace=self.config.namespace
        )
        
        service.spec.selector['color'] = color.value
        
        self.k8s_core.patch_namespaced_service(
            name=self.config.service_name,
            namespace=self.config.namespace,
            body=service
        )
        
        # Wait for switch to propagate
        await asyncio.sleep(10)
    
    async def get_current_state(self) -> Dict[str, Any]:
        """Get current deployment state."""
        try:
            # Get service to determine active color
            service = self.k8s_core.read_namespaced_service(
                name=self.config.service_name,
                namespace=self.config.namespace
            )
            
            active_color = service.spec.selector.get('color', 'blue')
            
            # Get deployment versions
            blue_deployment = self.k8s_apps.read_namespaced_deployment(
                name=self.config.blue_deployment,
                namespace=self.config.namespace
            )
            green_deployment = self.k8s_apps.read_namespaced_deployment(
                name=self.config.green_deployment,
                namespace=self.config.namespace
            )
            
            return {
                'active_color': DeploymentColor(active_color),
                'blue_version': blue_deployment.spec.template.metadata.labels.get('version', 'unknown'),
                'green_version': green_deployment.spec.template.metadata.labels.get('version', 'unknown'),
                'blue_replicas': blue_deployment.status.ready_replicas or 0,
                'green_replicas': green_deployment.status.ready_replicas or 0,
                'version': blue_deployment.spec.template.metadata.labels.get('version', 'unknown')
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get current state: {e}")
            return {
                'active_color': DeploymentColor.BLUE,
                'version': 'unknown'
            }
    
    def get_state(self) -> Optional[DeploymentState]:
        """Get deployment state."""
        return self.state


class CanaryDeployer:
    """Canary deployment strategy for gradual rollouts."""
    
    CANARY_STEPS = [5, 10, 25, 50, 75, 100]
    
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.logger = logging.getLogger(__name__)
        
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        
        self.k8s_apps = client.AppsV1Api()
    
    async def deploy(
        self,
        deployment_name: str,
        version: str,
        image: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """Deploy using canary strategy."""
        try:
            # Get current deployment
            deployment = self.k8s_apps.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )
            
            total_replicas = deployment.spec.replicas
            
            for percentage in self.CANARY_STEPS:
                canary_replicas = max(1, int(total_replicas * percentage / 100))
                
                self.logger.info(f"Canary step {percentage}%: {canary_replicas} replicas")
                
                # Update deployment
                deployment.spec.replicas = canary_replicas
                deployment.spec.template.spec.containers[0].image = image
                deployment.spec.template.metadata.labels['version'] = version
                deployment.spec.template.metadata.labels['canary'] = 'true'
                
                self.k8s_apps.patch_namespaced_deployment(
                    name=deployment_name,
                    namespace=self.namespace,
                    body=deployment
                )
                
                # Wait for rollout
                await self._wait_for_rollout(deployment_name)
                
                # Validate
                if not await self._validate_canary(deployment_name):
                    self.logger.error(f"Canary validation failed at {percentage}%")
                    await self.rollback(deployment_name)
                    return False
                
                if progress_callback:
                    progress_callback(percentage)
                
                # Wait between steps (except final)
                if percentage < 100:
                    await asyncio.sleep(60)  # 1 minute observation
            
            # Remove canary label
            deployment.spec.template.metadata.labels.pop('canary', None)
            self.k8s_apps.patch_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace,
                body=deployment
            )
            
            self.logger.info("Canary deployment completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Canary deployment failed: {e}")
            return False
    
    async def _wait_for_rollout(self, deployment_name: str, timeout: int = 300):
        """Wait for rollout to complete."""
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            deployment = self.k8s_apps.read_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace
            )
            
            if deployment.status.ready_replicas == deployment.spec.replicas:
                return
            
            await asyncio.sleep(5)
        
        raise TimeoutError(f"Rollout timeout for {deployment_name}")
    
    async def _validate_canary(self, deployment_name: str) -> bool:
        """Validate canary deployment."""
        # Would check error rates, latency, etc.
        return True
    
    async def rollback(self, deployment_name: str):
        """Rollback canary deployment."""
        self.logger.info(f"Rolling back {deployment_name}")
        
        # Would restore previous version
        pass


# Feature flags for gradual rollout
class FeatureFlagManager:
    """Manage feature flags for gradual rollout."""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.flags: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    def set_flag(
        self,
        flag_name: str,
        enabled: bool,
        rollout_percentage: int = 100,
        target_users: Optional[List[str]] = None
    ):
        """Set feature flag configuration."""
        self.flags[flag_name] = {
            'enabled': enabled,
            'rollout_percentage': rollout_percentage,
            'target_users': target_users or []
        }
    
    def is_enabled(self, flag_name: str, user_id: Optional[str] = None) -> bool:
        """Check if feature is enabled for user."""
        flag = self.flags.get(flag_name)
        
        if not flag:
            return False
        
        if not flag['enabled']:
            return False
        
        # Check user targeting
        if user_id and flag['target_users']:
            return user_id in flag['target_users']
        
        # Check percentage rollout
        if flag['rollout_percentage'] < 100:
            import hashlib
            hash_val = int(hashlib.md5(f"{flag_name}:{user_id or ''}".encode()).hexdigest(), 16)
            user_percentage = hash_val % 100
            return user_percentage < flag['rollout_percentage']
        
        return True
