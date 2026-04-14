"""
Async Processor Block - Infrastructure layer for Celery task dispatching.
"""

from typing import Any, Dict

from app.core.block import BaseBlock, BlockConfig
from app.core.block_registry import BLOCK_REGISTRY
from app.workers.celery_config import celery_app


class AsyncProcessorBlock(BaseBlock):
    """Celery task dispatcher for background job processing."""

    def __init__(self):
        super().__init__()
        self.config = BlockConfig(
            name="async_processor",
            version="1.0",
            description="Celery task dispatcher for background processing",
        )

    async def execute(self, action: str, input_data: dict, params: dict) -> dict:
        return await super().execute(action, input_data, params)

    async def dispatch(self, input_data: dict, params: dict) -> dict:
        """Dispatch a generic background task via Celery."""
        task_name = input_data.get("task_name") or input_data.get("task")
        task_args = input_data.get("args", [])
        task_kwargs = input_data.get("kwargs", {})
        queue = params.get("queue", "default")

        if not task_name:
            return {"status": "error", "error": "Missing 'task_name' in input_data"}

        try:
            task = celery_app.send_task(task_name, args=task_args, kwargs=task_kwargs, queue=queue)
            return {
                "status": "success",
                "task_id": task.id,
                "task_name": task_name,
                "queue": queue,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def status(self, input_data: dict, params: dict) -> dict:
        """Check the status of a Celery task."""
        task_id = input_data.get("task_id")
        if not task_id:
            return {"status": "error", "error": "Missing 'task_id' in input_data"}
        try:
            result = celery_app.AsyncResult(task_id)
            return {
                "status": "success",
                "task_id": task_id,
                "state": result.state,
                "ready": result.ready(),
                "successful": result.successful(),
                "failed": result.failed(),
                "result": result.result if result.ready() else None,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def revoke(self, input_data: dict, params: dict) -> dict:
        """Revoke/cancel a running Celery task."""
        task_id = input_data.get("task_id")
        if not task_id:
            return {"status": "error", "error": "Missing 'task_id' in input_data"}
        try:
            celery_app.control.revoke(task_id, terminate=params.get("terminate", False))
            return {"status": "success", "task_id": task_id, "revoked": True}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def inspect_queues(self, input_data: dict, params: dict) -> dict:
        """Inspect active Celery queues."""
        try:
            inspector = celery_app.control.inspect()
            active = inspector.active() or {}
            scheduled = inspector.scheduled() or {}
            reserved = inspector.reserved() or {}
            return {
                "status": "success",
                "active_tasks": {k: len(v) for k, v in active.items()},
                "scheduled_tasks": {k: len(v) for k, v in scheduled.items()},
                "reserved_tasks": {k: len(v) for k, v in reserved.items()},
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_actions(self) -> Dict[str, Any]:
        return {
            "dispatch": self.dispatch,
            "status": self.status,
            "revoke": self.revoke,
            "inspect_queues": self.inspect_queues,
        }


# Auto-register on import
BLOCK_REGISTRY.register(AsyncProcessorBlock())
