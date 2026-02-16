"""
Flower Monitoring Dashboard Configuration
Configures Flower for Celery task monitoring.
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import os


@dataclass
class FlowerConfig:
    """Flower dashboard configuration."""
    
    # Server settings
    port: int = 5555
    address: str = "0.0.0.0"
    url_prefix: str = ""
    
    # Authentication
    basic_auth: Optional[List[str]] = None  # ["user:password"]
    oauth2_key: Optional[str] = None
    oauth2_secret: Optional[str] = None
    oauth2_redirect_uri: Optional[str] = None
    
    # SSL
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    
    # Broker settings
    broker_api: Optional[str] = None  # HTTP API for RabbitMQ management
    
    # Database
    persistent: bool = True
    db: str = "flower.db"
    state_save_interval: int = 0  # 0 = disabled
    
    # UI settings
    max_tasks: int = 10000
    format_task: Optional[str] = None  # Custom task formatter
    natural_time: bool = True
    
    # Auto refresh
    auto_refresh: bool = True
    refresh_interval: int = 2000  # milliseconds
    
    # Logging
    logging: str = "INFO"
    
    # Security
    xheaders: bool = False
    cookie_secret: Optional[str] = None
    
    # Custom
    inspect_timeout: int = 1000  # milliseconds
    tasks_columns: str = "name,uuid,state,args,kwargs,result,received,started,runtime,worker"


def get_flower_command(config: Optional[FlowerConfig] = None) -> str:
    """Generate Flower startup command."""
    config = config or FlowerConfig()
    
    cmd_parts = [
        "celery -A app.workers.celery_config flower",
        f"--port={config.port}",
        f"--address={config.address}",
    ]
    
    if config.url_prefix:
        cmd_parts.append(f"--url-prefix={config.url_prefix}")
    
    if config.basic_auth:
        auth_str = ','.join(config.basic_auth)
        cmd_parts.append(f"--basic-auth={auth_str}")
    
    if config.broker_api:
        cmd_parts.append(f"--broker-api={config.broker_api}")
    
    if config.persistent:
        cmd_parts.append(f"--persistent=True")
        cmd_parts.append(f"--db={config.db}")
    
    if config.max_tasks != 10000:
        cmd_parts.append(f"--max-tasks={config.max_tasks}")
    
    if not config.auto_refresh:
        cmd_parts.append("--auto-refresh=False")
    
    if config.refresh_interval != 2000:
        cmd_parts.append(f"--refresh-interval={config.refresh_interval}")
    
    if config.logging != "INFO":
        cmd_parts.append(f"--logging={config.logging}")
    
    if config.inspect_timeout != 1000:
        cmd_parts.append(f"--inspect-timeout={config.inspect_timeout}")
    
    return ' '.join(cmd_parts)


def get_flower_docker_compose() -> str:
    """Generate Docker Compose configuration for Flower."""
    return """
  flower:
    image: mher/flower:latest
    container_name: cerebrum-flower
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - FLOWER_PORT=5555
      - FLOWER_BASIC_AUTH=admin:secretpassword
      - FLOWER_PERSISTENT=True
      - FLOWER_DB=/data/flower.db
    ports:
      - "5555:5555"
    volumes:
      - flower-data:/data
    depends_on:
      - redis
      - celery-worker
    networks:
      - cerebrum-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5555/healthcheck"]
      interval: 30s
      timeout: 10s
      retries: 3
"""


def get_flower_kubernetes_deployment() -> Dict[str, Any]:
    """Generate Kubernetes deployment for Flower."""
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "flower",
            "labels": {"app": "flower"}
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {"app": "flower"}
            },
            "template": {
                "metadata": {
                    "labels": {"app": "flower"}
                },
                "spec": {
                    "containers": [{
                        "name": "flower",
                        "image": "mher/flower:latest",
                        "ports": [{"containerPort": 5555}],
                        "env": [
                            {"name": "CELERY_BROKER_URL", "value": "redis://redis:6379/0"},
                            {"name": "FLOWER_PORT", "value": "5555"},
                            {"name": "FLOWER_BASIC_AUTH", 
                             "valueFrom": {"secretKeyRef": {"name": "flower-auth", "key": "credentials"}}},
                            {"name": "FLOWER_PERSISTENT", "value": "True"},
                            {"name": "FLOWER_DB", "value": "/data/flower.db"}
                        ],
                        "volumeMounts": [{
                            "name": "flower-data",
                            "mountPath": "/data"
                        }],
                        "livenessProbe": {
                            "httpGet": {"path": "/healthcheck", "port": 5555},
                            "initialDelaySeconds": 30,
                            "periodSeconds": 30
                        },
                        "readinessProbe": {
                            "httpGet": {"path": "/healthcheck", "port": 5555},
                            "initialDelaySeconds": 10,
                            "periodSeconds": 10
                        }
                    }],
                    "volumes": [{
                        "name": "flower-data",
                        "persistentVolumeClaim": {"claimName": "flower-pvc"}
                    }]
                }
            }
        }
    }


def get_flower_kubernetes_service() -> Dict[str, Any]:
    """Generate Kubernetes service for Flower."""
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "flower",
            "labels": {"app": "flower"}
        },
        "spec": {
            "selector": {"app": "flower"},
            "ports": [{
                "port": 5555,
                "targetPort": 5555,
                "name": "http"
            }],
            "type": "ClusterIP"
        }
    }


def get_flower_kubernetes_ingress() -> Dict[str, Any]:
    """Generate Kubernetes ingress for Flower."""
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {
            "name": "flower-ingress",
            "annotations": {
                "nginx.ingress.kubernetes.io/auth-type": "basic",
                "nginx.ingress.kubernetes.io/auth-secret": "flower-auth",
                "nginx.ingress.kubernetes.io/auth-realm": "Authentication Required"
            }
        },
        "spec": {
            "rules": [{
                "host": "flower.cerebrum.local",
                "http": {
                    "paths": [{
                        "path": "/",
                        "pathType": "Prefix",
                        "backend": {
                            "service": {
                                "name": "flower",
                                "port": {"number": 5555}
                            }
                        }
                    }]
                }
            }]
        }
    }


# Flower URL patterns for reverse proxy
FLOWER_URL_PATTERNS = {
    "dashboard": "/",
    "tasks": "/tasks",
    "task": "/task/{task_id}",
    "workers": "/workers",
    "worker": "/worker/{worker_name}",
    "broker": "/broker",
    "monitor": "/monitor",
    "api_tasks": "/api/tasks",
    "api_task_info": "/api/task/info/{task_id}",
    "api_workers": "/api/workers",
}


def get_flower_nginx_config() -> str:
    """Generate Nginx configuration for Flower reverse proxy."""
    return """
upstream flower {
    server localhost:5555;
}

server {
    listen 80;
    server_name flower.cerebrum.local;
    
    location / {
        proxy_pass http://flower;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}
"""


# Prometheus metrics endpoint for Flower
FLOWER_PROMETHEUS_METRICS = """
# Flower metrics for Prometheus
# These can be scraped from Flower's /metrics endpoint when enabled

flower_tasks_total{state="SUCCESS"} 100
flower_tasks_total{state="FAILURE"} 5
flower_tasks_total{state="PENDING"} 10
flower_tasks_total{state="RETRY"} 2

flower_workers_online 4
flower_workers_offline 0

flower_task_runtime_seconds_bucket{le="1.0"} 50
flower_task_runtime_seconds_bucket{le="5.0"} 80
flower_task_runtime_seconds_bucket{le="10.0"} 95
flower_task_runtime_seconds_bucket{le="+Inf"} 100
"""
