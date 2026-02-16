"""
Horizontal Pod Autoscaling - Kubernetes HPA Configuration
Configures autoscaling for microservices based on metrics.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class MetricType(str, Enum):
    """Types of metrics for autoscaling."""
    CPU = "cpu"
    MEMORY = "memory"
    CUSTOM = "custom"
    EXTERNAL = "external"
    PODS = "pods"
    OBJECT = "object"
    RESOURCE = "resource"
    CONTAINER_RESOURCE = "container_resource"


class MetricTargetType(str, Enum):
    """Types of metric targets."""
    UTILIZATION = "Utilization"
    AVERAGE_VALUE = "AverageValue"
    VALUE = "Value"


@dataclass
class MetricSpec:
    """Metric specification for HPA."""
    metric_type: MetricType
    target_type: MetricTargetType
    target_value: Any  # int for Utilization, str for Value
    container: Optional[str] = None
    metric_name: Optional[str] = None


@dataclass
class HPASpec:
    """Horizontal Pod Autoscaler specification."""
    name: str
    namespace: str = "default"
    scale_target_ref: Dict[str, str] = None
    min_replicas: int = 1
    max_replicas: int = 10
    metrics: List[MetricSpec] = None
    behavior: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.scale_target_ref is None:
            self.scale_target_ref = {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "name": self.name
            }
        if self.metrics is None:
            self.metrics = [
                MetricSpec(
                    metric_type=MetricType.CPU,
                    target_type=MetricTargetType.UTILIZATION,
                    target_value=70
                )
            ]


class AutoscalingConfig:
    """Generates Kubernetes HPA configurations."""
    
    @staticmethod
    def generate_hpa(spec: HPASpec) -> Dict[str, Any]:
        """Generate HPA manifest."""
        metrics = []
        for metric in spec.metrics:
            metric_dict = {
                "type": metric.metric_type.value,
                "resource" if metric.metric_type == MetricType.RESOURCE else "pods": {
                    "name": metric.metric_name or metric.metric_type.value,
                    "target": {
                        "type": metric.target_type.value,
                    }
                }
            }
            
            if metric.target_type == MetricTargetType.UTILIZATION:
                metric_dict["resource"]["target"]["averageUtilization"] = metric.target_value
            else:
                metric_dict["resource"]["target"]["averageValue"] = metric.target_value
            
            metrics.append(metric_dict)
        
        hpa = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": f"{spec.name}-hpa",
                "namespace": spec.namespace
            },
            "spec": {
                "scaleTargetRef": spec.scale_target_ref,
                "minReplicas": spec.min_replicas,
                "maxReplicas": spec.max_replicas,
                "metrics": metrics
            }
        }
        
        if spec.behavior:
            hpa["spec"]["behavior"] = spec.behavior
        
        return hpa
    
    @staticmethod
    def generate_api_hpa() -> Dict[str, Any]:
        """Generate HPA for API service."""
        spec = HPASpec(
            name="cerebrum-api",
            namespace="default",
            min_replicas=2,
            max_replicas=20,
            metrics=[
                MetricSpec(
                    metric_type=MetricType.CPU,
                    target_type=MetricTargetType.UTILIZATION,
                    target_value=70
                ),
                MetricSpec(
                    metric_type=MetricType.MEMORY,
                    target_type=MetricTargetType.UTILIZATION,
                    target_value=80
                )
            ],
            behavior={
                "scaleDown": {
                    "stabilizationWindowSeconds": 300,
                    "policies": [
                        {
                            "type": "Percent",
                            "value": 10,
                            "periodSeconds": 60
                        }
                    ]
                },
                "scaleUp": {
                    "stabilizationWindowSeconds": 0,
                    "policies": [
                        {
                            "type": "Percent",
                            "value": 100,
                            "periodSeconds": 15
                        },
                        {
                            "type": "Pods",
                            "value": 4,
                            "periodSeconds": 15
                        }
                    ],
                    "selectPolicy": "Max"
                }
            }
        )
        
        return AutoscalingConfig.generate_hpa(spec)
    
    @staticmethod
    def generate_vdc_worker_hpa() -> Dict[str, Any]:
        """Generate HPA for VDC worker pool."""
        spec = HPASpec(
            name="cerebrum-vdc-worker",
            namespace="default",
            min_replicas=1,
            max_replicas=10,
            metrics=[
                MetricSpec(
                    metric_type=MetricType.CPU,
                    target_type=MetricTargetType.UTILIZATION,
                    target_value=60
                ),
                MetricSpec(
                    metric_type=MetricType.CUSTOM,
                    target_type=MetricTargetType.AVERAGE_VALUE,
                    target_value="10",
                    metric_name="celery_tasks_pending"
                )
            ],
            behavior={
                "scaleUp": {
                    "stabilizationWindowSeconds": 60,
                    "policies": [
                        {
                            "type": "Pods",
                            "value": 2,
                            "periodSeconds": 60
                        }
                    ]
                }
            }
        )
        
        return AutoscalingConfig.generate_hpa(spec)
    
    @staticmethod
    def generate_webhook_worker_hpa() -> Dict[str, Any]:
        """Generate HPA for webhook worker pool."""
        spec = HPASpec(
            name="cerebrum-webhook-worker",
            namespace="default",
            min_replicas=2,
            max_replicas=50,
            metrics=[
                MetricSpec(
                    metric_type=MetricType.CPU,
                    target_type=MetricTargetType.UTILIZATION,
                    target_value=75
                )
            ],
            behavior={
                "scaleUp": {
                    "stabilizationWindowSeconds": 0,
                    "policies": [
                        {
                            "type": "Percent",
                            "value": 200,
                            "periodSeconds": 30
                        }
                    ]
                }
            }
        )
        
        return AutoscalingConfig.generate_hpa(spec)


# KEDA (Kubernetes Event-driven Autoscaling) configuration
KEDA_CONFIGS = {
    "celery_worker": """
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: celery-worker-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: cerebrum-celery-worker
  pollingInterval: 15
  cooldownPeriod: 300
  minReplicaCount: 1
  maxReplicaCount: 20
  triggers:
  - type: redis
    metadata:
      address: redis:6379
      listName: celery
      listLength: "10"
      activationListLength: "5"
""",
    "rabbitmq_consumer": """
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: rabbitmq-consumer-scaler
  namespace: default
spec:
  scaleTargetRef:
    name: cerebrum-rabbitmq-consumer
  triggers:
  - type: rabbitmq
    metadata:
      queueName: tasks
      queueLength: "20"
    authenticationRef:
      name: rabbitmq-trigger-auth
"""
}


# Vertical Pod Autoscaler configuration
VPA_CONFIG = """
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: cerebrum-api-vpa
  namespace: default
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: cerebrum-api
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: cerebrum-api
      minAllowed:
        cpu: 100m
        memory: 128Mi
      maxAllowed:
        cpu: 2000m
        memory: 2Gi
      controlledResources: ["cpu", "memory"]
"""


# Cluster Autoscaler configuration
CLUSTER_AUTOSCALER_CONFIG = """
# Cluster Autoscaler deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
      - name: cluster-autoscaler
        image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.24.0
        command:
        - ./cluster-autoscaler
        - --cloud-provider=aws
        - --namespace=kube-system
        - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/<cluster-name>
        - --balance-similar-node-groups
        - --skip-nodes-with-system-pods=false
        - --skip-nodes-with-local-storage=false
        resources:
          requests:
            cpu: 100m
            memory: 300Mi
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cluster-autoscaler
  namespace: kube-system
"""


# Prometheus Adapter for custom metrics
PROMETHEUS_ADAPTER_CONFIG = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: adapter-config
  namespace: monitoring
data:
  config.yaml: |
    rules:
    - seriesQuery: 'celery_tasks_pending{namespace!=""}'
      resources:
        overrides:
          namespace:
            resource: namespace
      name:
        matches: "^(.*)_pending$"
        as: "${1}_pending"
      metricsQuery: sum(<<.Series>>{<<.LabelMatchers>>}) by (<<.GroupBy>>)
"""
