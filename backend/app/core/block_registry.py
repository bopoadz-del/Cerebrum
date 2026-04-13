"""
Global registry for domain blocks.
"""

from typing import Dict, Optional
from app.core.block import BaseBlock


class BlockRegistry:
    def __init__(self):
        self._blocks: Dict[str, BaseBlock] = {}

    def register(self, block: BaseBlock) -> None:
        self._blocks[block.config.name] = block

    def get(self, name: str) -> Optional[BaseBlock]:
        return self._blocks.get(name)

    def list_blocks(self) -> Dict[str, str]:
        return {name: block.config.version for name, block in self._blocks.items()}


BLOCK_REGISTRY = BlockRegistry()
