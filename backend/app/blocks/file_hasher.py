"""
File Hasher Block - Infrastructure layer for file fingerprinting and metadata.
"""

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.block import BaseBlock, BlockConfig
from app.core.block_registry import BLOCK_REGISTRY


class FileHasherBlock(BaseBlock):
    """SHA256/MD5 hashing and metadata extraction for files."""

    def __init__(self):
        super().__init__()
        self.config = BlockConfig(
            name="file_hasher",
            version="1.0",
            description="SHA256/MD5 hashing and file metadata extraction",
        )

    async def execute(self, action: str, input_data: dict, params: dict) -> dict:
        return await super().execute(action, input_data, params)

    async def hash_sha256(self, input_data: dict, params: dict) -> dict:
        """Compute SHA256 hash of a file."""
        file_path = input_data.get("file_path") or input_data.get("path")
        if not file_path or not os.path.exists(file_path):
            return {"status": "error", "error": f"File not found: {file_path}"}
        try:
            h = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return {"status": "success", "algorithm": "sha256", "hash": h.hexdigest(), "file_path": file_path}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def hash_md5(self, input_data: dict, params: dict) -> dict:
        """Compute MD5 hash of a file."""
        file_path = input_data.get("file_path") or input_data.get("path")
        if not file_path or not os.path.exists(file_path):
            return {"status": "error", "error": f"File not found: {file_path}"}
        try:
            h = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return {"status": "success", "algorithm": "md5", "hash": h.hexdigest(), "file_path": file_path}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_metadata(self, input_data: dict, params: dict) -> dict:
        """Extract file metadata (size, mtime, extension)."""
        file_path = input_data.get("file_path") or input_data.get("path")
        if not file_path or not os.path.exists(file_path):
            return {"status": "error", "error": f"File not found: {file_path}"}
        try:
            stat = os.stat(file_path)
            path = Path(file_path)
            return {
                "status": "success",
                "file_path": file_path,
                "file_name": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 4),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def fingerprint(self, input_data: dict, params: dict) -> dict:
        """Full fingerprint: metadata + SHA256 + MD5."""
        file_path = input_data.get("file_path") or input_data.get("path")
        if not file_path or not os.path.exists(file_path):
            return {"status": "error", "error": f"File not found: {file_path}"}
        meta = await self.get_metadata(input_data, params)
        if meta.get("status") == "error":
            return meta
        sha = await self.hash_sha256(input_data, params)
        md = await self.hash_md5(input_data, params)
        return {
            "status": "success",
            "file_path": file_path,
            "metadata": meta,
            "sha256": sha.get("hash"),
            "md5": md.get("hash"),
        }

    def get_actions(self) -> Dict[str, Any]:
        return {
            "hash_sha256": self.hash_sha256,
            "hash_md5": self.hash_md5,
            "get_metadata": self.get_metadata,
            "fingerprint": self.fingerprint,
        }


# Auto-register on import
BLOCK_REGISTRY.register(FileHasherBlock())
