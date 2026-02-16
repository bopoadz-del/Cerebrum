"""
Celery Configuration - 3-Queue Worker Pool
Configures Celery with separate queues for different task priorities.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from kombu import Queue, Exchange
from celery import Celery
import os
import logging

logger = logging.getLogger(__name__)


# Queue names - matching docker-compose
QUEUE_FAST = "celery_fast"
QUEUE_SLOW = "celery_slow"
QUEUE_BEATS = "celery_beats"

# Legacy queue names for compatibility
QUEUE_DEFAULT = "default"
QUEUE_HIGH_PRIORITY = "high"
QUEUE_LOW_PRIORITY = "low"
QUEUE_VDC = "vdc"
QUEUE_EMAIL = "email"
QUEUE_NOTIFICATIONS = "notifications"
QUEUE_REPORTS = "reports"


@dataclass
class CeleryConfig:
    """Celery configuration settings."""
    
    # Broker settings - read from environment
    broker_url: str = None
    result_backend: str = None
    
    # Serialization
    task_serializer: str = "json"
    accept_content: List[str] = None
    result_serializer: str = "json"
    
    # Task settings
    task_track_started: bool = True
    task_time_limit: int = 3600  # 1 hour
    task_soft_time_limit: int = 3300  # 55 minutes
    worker_prefetch_multiplier: int = 4
    worker_max_tasks_per_child: int = 1000
    
    # Result settings
    result_expires: int = 86400  # 24 hours
    result_extended: bool = True
    
    # Monitoring
    task_send_sent_event: bool = True
    worker_send_task_events: bool = True
    
    # Retry settings
    task_default_retry_delay: int = 60
    task_max_retries: int = 3
    
    # Concurrency
    worker_concurrency: int = 4
    
    def __post_init__(self):
        if self.accept_content is None:
            self.accept_content = ["json"]
        
        # Read from environment if not set
        if self.broker_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            # Use DB 1 for broker
            self.broker_url = redis_url.replace("/0", "/1") if "/0" in redis_url else f"{redis_url}/1"
        
        if self.result_backend is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            # Use DB 2 for results
            self.result_backend = redis_url.replace("/0", "/2") if "/0" in redis_url else f"{redis_url}/2"


def create_celery_app(app_name: str = "cerebrum", config: Optional[CeleryConfig] = None) -> Celery:
    """Create and configure Celery application."""
    config = config or CeleryConfig()
    
    app = Celery(app_name)
    
    # Configure broker
    app.conf.broker_url = config.broker_url
    app.conf.result_backend = config.result_backend
    
    # Configure serialization
    app.conf.task_serializer = config.task_serializer
    app.conf.accept_content = config.accept_content
    app.conf.result_serializer = config.result_serializer
    
    # Configure task settings
    app.conf.task_track_started = config.task_track_started
    app.conf.task_time_limit = config.task_time_limit
    app.conf.task_soft_time_limit = config.task_soft_time_limit
    app.conf.worker_prefetch_multiplier = config.worker_prefetch_multiplier
    app.conf.worker_max_tasks_per_child = config.worker_max_tasks_per_child
    
    # Configure results
    app.conf.result_expires = config.result_expires
    app.conf.result_extended = config.result_extended
    
    # Configure monitoring
    app.conf.task_send_sent_event = config.task_send_sent_event
    app.conf.worker_send_task_events = config.worker_send_task_events
    
    # Configure retry
    app.conf.task_default_retry_delay = config.task_default_retry_delay
    app.conf.task_max_retries = config.task_max_retries
    
    # Configure queues - include both docker-compose queues and legacy queues
    app.conf.task_queues = (
        # Docker-compose queues
        Queue(QUEUE_FAST, Exchange(QUEUE_FAST), routing_key=QUEUE_FAST),
        Queue(QUEUE_SLOW, Exchange(QUEUE_SLOW), routing_key=QUEUE_SLOW),
        Queue(QUEUE_BEATS, Exchange(QUEUE_BEATS), routing_key=QUEUE_BEATS),
        # Legacy queues
        Queue(QUEUE_DEFAULT, Exchange(QUEUE_DEFAULT), routing_key=QUEUE_DEFAULT),
        Queue(QUEUE_HIGH_PRIORITY, Exchange(QUEUE_HIGH_PRIORITY), routing_key=QUEUE_HIGH_PRIORITY),
        Queue(QUEUE_LOW_PRIORITY, Exchange(QUEUE_LOW_PRIORITY), routing_key=QUEUE_LOW_PRIORITY),
        Queue(QUEUE_VDC, Exchange(QUEUE_VDC), routing_key=QUEUE_VDC),
        Queue(QUEUE_EMAIL, Exchange(QUEUE_EMAIL), routing_key=QUEUE_EMAIL),
        Queue(QUEUE_NOTIFICATIONS, Exchange(QUEUE_NOTIFICATIONS), routing_key=QUEUE_NOTIFICATIONS),
        Queue(QUEUE_REPORTS, Exchange(QUEUE_REPORTS), routing_key=QUEUE_REPORTS),
    )
    
    app.conf.task_default_queue = QUEUE_DEFAULT
    app.conf.task_default_exchange = QUEUE_DEFAULT
    app.conf.task_default_routing_key = QUEUE_DEFAULT
    
    # Configure routes
    app.conf.task_routes = {
        # Fast queue - high priority tasks
        'tasks.notifications.*': {'queue': QUEUE_FAST, 'routing_key': QUEUE_FAST},
        'tasks.auth.*': {'queue': QUEUE_FAST, 'routing_key': QUEUE_FAST},
        
        # Slow queue - background processing
        'tasks.vdc.clash_detection': {'queue': QUEUE_SLOW, 'routing_key': QUEUE_SLOW},
        'tasks.vdc.model_processing': {'queue': QUEUE_SLOW, 'routing_key': QUEUE_SLOW},
        'tasks.vdc.federation': {'queue': QUEUE_SLOW, 'routing_key': QUEUE_SLOW},
        
        # Beats queue - scheduled tasks
        'tasks.scheduled.*': {'queue': QUEUE_BEATS, 'routing_key': QUEUE_BEATS},
        'tasks.cleanup.*': {'queue': QUEUE_BEATS, 'routing_key': QUEUE_BEATS},
        
        # Legacy routes
        'tasks.email.*': {'queue': QUEUE_EMAIL, 'routing_key': QUEUE_EMAIL},
        'tasks.reports.*': {'queue': QUEUE_REPORTS, 'routing_key': QUEUE_REPORTS},
        'tasks.analytics.*': {'queue': QUEUE_LOW_PRIORITY, 'routing_key': QUEUE_LOW_PRIORITY},
    }
    
    logger.info(f"Celery app '{app_name}' configured with broker: {config.broker_url}")
    
    return app


# Create default app instance
celery_app = create_celery_app()


# Task decorators with queue routing
def fast_task(*args, **kwargs):
    """Decorator for fast queue tasks."""
    kwargs['queue'] = QUEUE_FAST
    kwargs['routing_key'] = QUEUE_FAST
    kwargs['default_retry_delay'] = kwargs.get('default_retry_delay', 30)
    kwargs['max_retries'] = kwargs.get('max_retries', 5)
    return celery_app.task(*args, **kwargs)


def slow_task(*args, **kwargs):
    """Decorator for slow queue tasks."""
    kwargs['queue'] = QUEUE_SLOW
    kwargs['routing_key'] = QUEUE_SLOW
    kwargs['default_retry_delay'] = kwargs.get('default_retry_delay', 60)
    kwargs['max_retries'] = kwargs.get('max_retries', 3)
    return celery_app.task(*args, **kwargs)


def beats_task(*args, **kwargs):
    """Decorator for scheduled/beat tasks."""
    kwargs['queue'] = QUEUE_BEATS
    kwargs['routing_key'] = QUEUE_BEATS
    kwargs['default_retry_delay'] = kwargs.get('default_retry_delay', 300)
    return celery_app.task(*args, **kwargs)


# Legacy decorators
def high_priority_task(*args, **kwargs):
    """Decorator for high priority tasks."""
    kwargs['queue'] = QUEUE_HIGH_PRIORITY
    kwargs['routing_key'] = QUEUE_HIGH_PRIORITY
    kwargs['default_retry_delay'] = kwargs.get('default_retry_delay', 30)
    kwargs['max_retries'] = kwargs.get('max_retries', 5)
    return celery_app.task(*args, **kwargs)


def vdc_task(*args, **kwargs):
    """Decorator for VDC processing tasks."""
    kwargs['queue'] = QUEUE_VDC
    kwargs['routing_key'] = QUEUE_VDC
    kwargs['time_limit'] = kwargs.get('time_limit', 7200)  # 2 hours
    kwargs['soft_time_limit'] = kwargs.get('soft_time_limit', 6600)  # 1h 50m
    return celery_app.task(*args, **kwargs)


def email_task(*args, **kwargs):
    """Decorator for email tasks."""
    kwargs['queue'] = QUEUE_EMAIL
    kwargs['routing_key'] = QUEUE_EMAIL
    kwargs['default_retry_delay'] = kwargs.get('default_retry_delay', 300)
    kwargs['max_retries'] = kwargs.get('max_retries', 3)
    return celery_app.task(*args, **kwargs)


def report_task(*args, **kwargs):
    """Decorator for report generation tasks."""
    kwargs['queue'] = QUEUE_REPORTS
    kwargs['routing_key'] = QUEUE_REPORTS
    kwargs['time_limit'] = kwargs.get('time_limit', 1800)  # 30 minutes
    return celery_app.task(*args, **kwargs)


def low_priority_task(*args, **kwargs):
    """Decorator for low priority tasks."""
    kwargs['queue'] = QUEUE_LOW_PRIORITY
    kwargs['routing_key'] = QUEUE_LOW_PRIORITY
    kwargs['default_retry_delay'] = kwargs.get('default_retry_delay', 300)
    return celery_app.task(*args, **kwargs)


# Worker pool configuration
WORKER_POOL_CONFIGS = {
    'fast': {
        'queues': [QUEUE_FAST, QUEUE_HIGH_PRIORITY],
        'concurrency': 8,
        'prefetch_multiplier': 8,
        'max_tasks_per_child': 1000,
    },
    'slow': {
        'queues': [QUEUE_SLOW, QUEUE_VDC],
        'concurrency': 2,
        'prefetch_multiplier': 1,
        'max_tasks_per_child': 50,
        'pool': 'prefork',
    },
    'beats': {
        'queues': [QUEUE_BEATS],
        'concurrency': 2,
        'prefetch_multiplier': 1,
        'max_tasks_per_child': 100,
    },
    # Legacy configs
    'default': {
        'queues': [QUEUE_DEFAULT, QUEUE_NOTIFICATIONS],
        'concurrency': 4,
        'prefetch_multiplier': 4,
        'max_tasks_per_child': 1000,
    },
    'vdc': {
        'queues': [QUEUE_VDC],
        'concurrency': 2,
        'prefetch_multiplier': 1,
        'max_tasks_per_child': 50,
        'pool': 'prefork',
    },
    'high_priority': {
        'queues': [QUEUE_HIGH_PRIORITY],
        'concurrency': 8,
        'prefetch_multiplier': 8,
        'max_tasks_per_child': 1000,
    },
    'reports': {
        'queues': [QUEUE_REPORTS],
        'concurrency': 2,
        'prefetch_multiplier': 1,
        'max_tasks_per_child': 100,
    },
    'email': {
        'queues': [QUEUE_EMAIL],
        'concurrency': 4,
        'prefetch_multiplier': 4,
        'max_tasks_per_child': 500,
    },
}


def get_worker_command(pool_name: str) -> str:
    """Get Celery worker command for a specific pool."""
    config = WORKER_POOL_CONFIGS.get(pool_name)
    if not config:
        raise ValueError(f"Unknown worker pool: {pool_name}")
    
    queues = ','.join(config['queues'])
    concurrency = config['concurrency']
    prefetch = config['prefetch_multiplier']
    max_tasks = config['max_tasks_per_child']
    pool_type = config.get('pool', 'prefork')
    
    cmd = (
        f"celery -A app.workers.celery_config worker "
        f"-Q {queues} "
        f"-c {concurrency} "
        f"--prefetch-multiplier={prefetch} "
        f"--max-tasks-per-child={max_tasks} "
        f"-P {pool_type} "
        f"-n {pool_name}_worker@%h"
    )
    
    return cmd


def start_all_workers():
    """Generate commands to start all worker pools."""
    commands = []
    for pool_name in ['fast', 'slow', 'beats']:
        cmd = get_worker_command(pool_name)
        commands.append(cmd)
    return commands


# Example tasks
@fast_task(bind=True, max_retries=3)
def send_notification(self, user_id: str, message: str, channel: str = "email"):
    """Send notification to user."""
    try:
        logger.info(f"Sending {channel} notification to user {user_id}")
        # Implementation here
        return {"status": "sent", "user_id": user_id}
    except Exception as exc:
        logger.error(f"Failed to send notification: {exc}")
        raise self.retry(exc=exc, countdown=60)


@slow_task(bind=True, max_retries=2)
def process_ifc_model(self, model_id: str, file_path: str):
    """Process uploaded IFC model."""
    try:
        logger.info(f"Processing IFC model {model_id}")
        # Implementation here
        return {"status": "processed", "model_id": model_id}
    except Exception as exc:
        logger.error(f"Failed to process IFC model: {exc}")
        raise self.retry(exc=exc, countdown=300)


@slow_task(bind=True, max_retries=1)
def run_clash_detection(self, federated_model_id: str, tolerance: float = 0.001):
    """Run clash detection on federated model."""
    try:
        logger.info(f"Running clash detection on {federated_model_id}")
        # Implementation here
        return {"status": "completed", "clash_count": 0}
    except Exception as exc:
        logger.error(f"Clash detection failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@email_task(bind=True, max_retries=3)
def send_email(self, to: str, subject: str, body: str, html: bool = False):
    """Send email."""
    try:
        logger.info(f"Sending email to {to}")
        # Implementation here
        return {"status": "sent", "to": to}
    except Exception as exc:
        logger.error(f"Failed to send email: {exc}")
        raise self.retry(exc=exc, countdown=300)


@report_task(bind=True, max_retries=2)
def generate_report(self, report_type: str, params: Dict[str, Any]):
    """Generate report."""
    try:
        logger.info(f"Generating {report_type} report")
        # Implementation here
        return {"status": "generated", "report_type": report_type}
    except Exception as exc:
        logger.error(f"Report generation failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@beats_task(bind=True)
def cleanup_old_files(self, days: int = 30):
    """Clean up old temporary files."""
    try:
        logger.info(f"Cleaning up files older than {days} days")
        # Implementation here
        return {"status": "completed", "files_deleted": 0}
    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        # Don't retry cleanup tasks
        raise exc


@beats_task(bind=True)
def update_analytics(self):
    """Update analytics aggregates."""
    try:
        logger.info("Updating analytics")
        # Implementation here
        return {"status": "updated"}
    except Exception as exc:
        logger.error(f"Analytics update failed: {exc}")
        raise exc

# Celery CLI (-A) expects an attribute named `app` by default.
app = celery_app
