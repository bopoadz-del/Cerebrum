"""
Base block infrastructure for domain-specific containers.
"""

from dataclasses import dataclass
from typing import Dict, Any, Callable


@dataclass
class BlockConfig:
    name: str
    version: str
    description: str = ""


class BaseBlock:
    """Base class for all domain containers."""

    def __init__(self):
        self.config = BlockConfig(name="base", version="0.1")

    async def execute(self, action: str, input_data: dict, params: dict) -> dict:
        actions = self.get_actions()
        handler = actions.get(action)
        if not handler:
            return {
                "status": "error",
                "error": f"Action '{action}' not found in {self.config.name}",
            }
        return await handler(input_data, params)

    def get_actions(self) -> Dict[str, Callable]:
        return {}
