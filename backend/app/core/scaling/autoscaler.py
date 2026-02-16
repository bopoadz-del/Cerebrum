"""
Kubernetes Autoscaler Integration - HPA and VPA
Horizontal and Vertical Pod Autoscaler configuration and monitoring.
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import kubernetes
from kubernetes import client, config
from kubernetes.client.models import V2HorizontalPodAutoscaler, V2MetricSpec
import logging

logger = logging.getLogger(__name__)


@dataclass
class HPASpec:
    """Horizontal Pod Autoscaler specification."""
    name: str
    namespace: str
    min_replicas: int
    max_replicas: int
    target_cpu_utilization: Optional[int] = None
    target_memory_utilization: Optional[int] = None
    custom_metrics: List[Dict[str, Any]] = None
    scale_down_stabilization: int = 300  # seconds
    scale_up_stabilization: int = 0  # seconds


@dataclass
class VPASpec:
    """Vertical Pod Autoscaler specification."""
    name: str
    namespace: str
    mode: str = "Auto"  # Auto, Off, Initial
    update_mode: str = "Auto"  # Auto, Off, Initial, Recreate
    container_policies: List[Dict[str, Any]] = None


@dataclass
class ScalingMetrics:
    """Scaling metrics snapshot."""
    timestamp: datetime
    current_replicas: int
    desired_replicas: int
    current_cpu_percent: float
    current_memory_percent: float
    cpu_requests: int
    memory_requests: int


class HPAController:
    """Controller for Horizontal Pod Autoscaler."""
    
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.logger = logging.getLogger(__name__)
        
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        
        self.k8s_autoscaling = client.AutoscalingV2Api()
        self.k8s_apps = client.AppsV1Api()
    
    def create_hpa(self, spec: HPASpec, target_deployment: str) -> V2HorizontalPodAutoscaler:
        """Create HPA for a deployment."""
        metrics = []
        
        # CPU metric
        if spec.target_cpu_utilization:
            metrics.append({
                'type': 'Resource',
                'resource': {
                    'name': 'cpu',
                    'target': {
                        'type': 'Utilization',
                        'averageUtilization': spec.target_cpu_utilization
                    }
                }
            })
        
        # Memory metric
        if spec.target_memory_utilization:
            metrics.append({
                'type': 'Resource',
                'resource': {
                    'name': 'memory',
                    'target': {
                        'type': 'Utilization',
                        'averageUtilization': spec.target_memory_utilization
                    }
                }
            })
        
        # Custom metrics
        if spec.custom_metrics:
            metrics.extend(spec.custom_metrics)
        
        hpa = V2HorizontalPodAutoscaler(
            api_version='autoscaling/v2',
            kind='HorizontalPodAutoscaler',
            metadata={
                'name': spec.name,
                'namespace': spec.namespace
            },
            spec={
                'scaleTargetRef': {
                    'apiVersion': 'apps/v1',
                    'kind': 'Deployment',
                    'name': target_deployment
                },
                'minReplicas': spec.min_replicas,
                'maxReplicas': spec.max_replicas,
                'metrics': metrics,
                'behavior': {
                    'scaleDown': {
                        'stabilizationWindowSeconds': spec.scale_down_stabilization,
                        'policies': [
                            {
                                'type': 'Percent',
                                'value': 10,
                                'periodSeconds': 60
                            }
                        ]
                    },
                    'scaleUp': {
                        'stabilizationWindowSeconds': spec.scale_up_stabilization,
                        'policies': [
                            {
                                'type': 'Percent',
                                'value': 100,
                                'periodSeconds': 15
                            },
                            {
                                'type': 'Pods',
                                'value': 4,
                                'periodSeconds': 15
                            }
                        ],
                        'selectPolicy': 'Max'
                    }
                }
            }
        )
        
        try:
            created = self.k8s_autoscaling.create_namespaced_horizontal_pod_autoscaler(
                namespace=spec.namespace,
                body=hpa
            )
            self.logger.info(f"Created HPA: {spec.name}")
            return created
        except client.exceptions.ApiException as e:
            if e.status == 409:
                # Already exists, update instead
                return self.update_hpa(spec, target_deployment)
            raise
    
    def update_hpa(self, spec: HPASpec, target_deployment: str) -> V2HorizontalPodAutoscaler:
        """Update existing HPA."""
        return self.create_hpa(spec, target_deployment)  # Kubernetes handles updates
    
    def delete_hpa(self, name: str, namespace: Optional[str] = None):
        """Delete HPA."""
        namespace = namespace or self.namespace
        
        self.k8s_autoscaling.delete_namespaced_horizontal_pod_autoscaler(
            name=name,
            namespace=namespace
        )
        self.logger.info(f"Deleted HPA: {name}")
    
    def get_hpa(self, name: str, namespace: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get HPA status."""
        namespace = namespace or self.namespace
        
        try:
            hpa = self.k8s_autoscaling.read_namespaced_horizontal_pod_autoscaler(
                name=name,
                namespace=namespace
            )
            
            return {
                'name': hpa.metadata.name,
                'namespace': hpa.metadata.namespace,
                'min_replicas': hpa.spec.min_replicas,
                'max_replicas': hpa.spec.max_replicas,
                'current_replicas': hpa.status.current_replicas,
                'desired_replicas': hpa.status.desired_replicas,
                'current_metrics': [
                    {
                        'type': m.type,
                        'resource': m.resource.name if m.resource else None,
                        'current': {
                            'averageUtilization': m.resource.current.average_utilization if m.resource and m.resource.current else None,
                            'averageValue': m.resource.current.average_value if m.resource and m.resource.current else None
                        }
                    }
                    for m in (hpa.status.current_metrics or [])
                ],
                'conditions': [
                    {
                        'type': c.type,
                        'status': c.status,
                        'reason': c.reason,
                        'message': c.message
                    }
                    for c in (hpa.status.conditions or [])
                ]
            }
            
        except client.exceptions.ApiException as e:
            if e.status == 404:
                return None
            raise
    
    def list_hpas(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all HPAs in namespace."""
        namespace = namespace or self.namespace
        
        hpas = self.k8s_autoscaling.list_namespaced_horizontal_pod_autoscaler(
            namespace=namespace
        )
        
        return [
            {
                'name': hpa.metadata.name,
                'target': hpa.spec.scale_target_ref.name,
                'min_replicas': hpa.spec.min_replicas,
                'max_replicas': hpa.spec.max_replicas,
                'current_replicas': hpa.status.current_replicas,
                'desired_replicas': hpa.status.desired_replicas
            }
            for hpa in hpas.items
        ]


class ClusterAutoscaler:
    """Interface to cluster autoscaler."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        
        self.k8s_core = client.CoreV1Api()
    
    def get_node_pools(self) -> List[Dict[str, Any]]:
        """Get cluster node pool information."""
        nodes = self.k8s_core.list_node()
        
        pools = {}
        for node in nodes.items:
            pool_name = node.metadata.labels.get('cloud.google.com/gke-nodepool', 'default')
            
            if pool_name not in pools:
                pools[pool_name] = {
                    'name': pool_name,
                    'nodes': [],
                    'total_cpu': 0,
                    'total_memory': 0,
                    'allocatable_cpu': 0,
                    'allocatable_memory': 0
                }
            
            pools[pool_name]['nodes'].append(node.metadata.name)
            
            # Parse capacity
            capacity = node.status.capacity
            allocatable = node.status.allocatable
            
            pools[pool_name]['total_cpu'] += self._parse_cpu(capacity.get('cpu', '0'))
            pools[pool_name]['total_memory'] += self._parse_memory(capacity.get('memory', '0'))
            pools[pool_name]['allocatable_cpu'] += self._parse_cpu(allocatable.get('cpu', '0'))
            pools[pool_name]['allocatable_memory'] += self._parse_memory(allocatable.get('memory', '0'))
        
        return list(pools.values())
    
    def _parse_cpu(self, cpu_str: str) -> int:
        """Parse CPU string to millicores."""
        if cpu_str.endswith('m'):
            return int(cpu_str[:-1])
        return int(cpu_str) * 1000
    
    def _parse_memory(self, mem_str: str) -> int:
        """Parse memory string to bytes."""
        units = {'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'Ti': 1024**4}
        
        for unit, multiplier in units.items():
            if mem_str.endswith(unit):
                return int(mem_str[:-len(unit)]) * multiplier
        
        return int(mem_str)
    
    def get_scaling_activities(self) -> List[Dict[str, Any]]:
        """Get recent cluster scaling activities."""
        # This would query cluster autoscaler logs/metrics
        return []


class PodDisruptionBudgetManager:
    """Manage Pod Disruption Budgets for availability during scaling."""
    
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.logger = logging.getLogger(__name__)
        
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        
        self.k8s_policy = client.PolicyV1Api()
    
    def create_pdb(
        self,
        name: str,
        selector: Dict[str, str],
        min_available: Optional[int] = None,
        max_unavailable: Optional[int] = None
    ):
        """Create Pod Disruption Budget."""
        pdb = {
            'apiVersion': 'policy/v1',
            'kind': 'PodDisruptionBudget',
            'metadata': {
                'name': name,
                'namespace': self.namespace
            },
            'spec': {
                'selector': {
                    'matchLabels': selector
                }
            }
        }
        
        if min_available is not None:
            pdb['spec']['minAvailable'] = min_available
        
        if max_unavailable is not None:
            pdb['spec']['maxUnavailable'] = max_unavailable
        
        try:
            self.k8s_policy.create_namespaced_pod_disruption_budget(
                namespace=self.namespace,
                body=pdb
            )
            self.logger.info(f"Created PDB: {name}")
        except client.exceptions.ApiException as e:
            if e.status == 409:
                self.logger.info(f"PDB already exists: {name}")
            else:
                raise
    
    def delete_pdb(self, name: str):
        """Delete Pod Disruption Budget."""
        self.k8s_policy.delete_namespaced_pod_disruption_budget(
            name=name,
            namespace=self.namespace
        )
        self.logger.info(f"Deleted PDB: {name}")


class ScalingMonitor:
    """Monitor scaling events and metrics."""
    
    def __init__(self, hpa_controller: HPAController):
        self.hpa = hpa_controller
        self.logger = logging.getLogger(__name__)
        self.metrics_history: List[ScalingMetrics] = []
        self.alert_callbacks: List[Callable] = []
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for scaling alerts."""
        self.alert_callbacks.append(callback)
    
    async def collect_metrics(self, hpa_name: str) -> Optional[ScalingMetrics]:
        """Collect current scaling metrics."""
        hpa = self.hpa.get_hpa(hpa_name)
        
        if not hpa:
            return None
        
        metrics = ScalingMetrics(
            timestamp=datetime.utcnow(),
            current_replicas=hpa['current_replicas'],
            desired_replicas=hpa['desired_replicas'],
            current_cpu_percent=0.0,
            current_memory_percent=0.0,
            cpu_requests=0,
            memory_requests=0
        )
        
        # Extract metrics
        for m in hpa.get('current_metrics', []):
            if m['resource'] == 'cpu':
                metrics.current_cpu_percent = m['current'].get('averageUtilization', 0) or 0
            elif m['resource'] == 'memory':
                metrics.current_memory_percent = m['current'].get('averageUtilization', 0) or 0
        
        self.metrics_history.append(metrics)
        
        # Keep only last 1000 metrics
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        return metrics
    
    async def check_scaling_issues(self, hpa_name: str):
        """Check for scaling issues."""
        hpa = self.hpa.get_hpa(hpa_name)
        
        if not hpa:
            return
        
        # Check if at max replicas
        if hpa['current_replicas'] == hpa['max_replicas']:
            await self._send_alert(
                'scaling_at_max',
                f"HPA {hpa_name} is at maximum replicas ({hpa['max_replicas']})",
                hpa
            )
        
        # Check if desired > current (scale up blocked)
        if hpa['desired_replicas'] > hpa['current_replicas']:
            await self._send_alert(
                'scale_up_blocked',
                f"HPA {hpa_name} wants {hpa['desired_replicas']} replicas but has {hpa['current_replicas']}",
                hpa
            )
    
    async def _send_alert(self, alert_type: str, message: str, data: Dict[str, Any]):
        """Send scaling alert."""
        for callback in self.alert_callbacks:
            try:
                await callback(alert_type, message, data)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    def get_scaling_recommendations(self) -> List[Dict[str, Any]]:
        """Get scaling recommendations based on metrics history."""
        recommendations = []
        
        if len(self.metrics_history) < 10:
            return recommendations
        
        recent = self.metrics_history[-100:]
        
        # Check for frequent scaling
        replica_changes = sum(
            1 for i in range(1, len(recent))
            if recent[i].current_replicas != recent[i-1].current_replicas
        )
        
        if replica_changes > 20:  # More than 20 changes in last 100 samples
            recommendations.append({
                'type': 'reduce_flapping',
                'message': 'High scaling frequency detected - consider increasing stabilization window',
                'severity': 'warning'
            })
        
        # Check for underutilization
        avg_cpu = sum(m.current_cpu_percent for m in recent) / len(recent)
        if avg_cpu < 20:
            recommendations.append({
                'type': 'reduce_replicas',
                'message': f'Low average CPU utilization ({avg_cpu:.1f}%) - consider reducing min replicas',
                'severity': 'info'
            })
        
        return recommendations


# Pre-configured HPA specs for common workloads
class HPATemplates:
    """Pre-configured HPA templates."""
    
    @staticmethod
    def web_service(name: str, namespace: str = "default") -> HPASpec:
        """HPA spec for web service."""
        return HPASpec(
            name=f"{name}-hpa",
            namespace=namespace,
            min_replicas=2,
            max_replicas=20,
            target_cpu_utilization=70,
            target_memory_utilization=80,
            scale_down_stabilization=300
        )
    
    @staticmethod
    def worker(name: str, namespace: str = "default") -> HPASpec:
        """HPA spec for background worker."""
        return HPASpec(
            name=f"{name}-hpa",
            namespace=namespace,
            min_replicas=1,
            max_replicas=50,
            target_cpu_utilization=80,
            custom_metrics=[
                {
                    'type': 'Pods',
                    'pods': {
                        'metric': {
                            'name': 'queue_depth'
                        },
                        'target': {
                            'type': 'AverageValue',
                            'averageValue': '100'
                        }
                    }
                }
            ]
        )
    
    @staticmethod
    def api_service(name: str, namespace: str = "default") -> HPASpec:
        """HPA spec for API service."""
        return HPASpec(
            name=f"{name}-hpa",
            namespace=namespace,
            min_replicas=3,
            max_replicas=30,
            target_cpu_utilization=60,
            target_memory_utilization=70,
            scale_up_stabilization=0,
            scale_down_stabilization=600
        )
