"""
Retraining Scheduler

Schedules and manages automated model retraining jobs.
Integrates with Celery for async execution.

Trigger Types:
- SCHEDULED: Time-based triggers (cron schedule)
- DRIFT: Triggered by drift detection
- PERFORMANCE: Triggered by performance degradation
- DATA_VOLUME: Triggered when sufficient new data collected
- MANUAL: Manually triggered

Features:
- Cron-based scheduling
- Drift-based triggers
- Performance-based triggers
- Integration with Celery for async execution
- PostgreSQL for job state persistence
"""