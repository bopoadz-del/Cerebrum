"""
Data versioning with DVC-like functionality.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from enum import Enum
import hashlib
import json
import uuid


class DatasetStatus(Enum):
    """Dataset version status."""
    DRAFT = "draft"
    COMMITTED = "committed"
    TAGGED = "tagged"
    ARCHIVED = "archived"


@dataclass
class DatasetVersion:
    """Version of a dataset."""
    version_id: str
    dataset_name: str
    version: str
    status: DatasetStatus
    file_hashes: Dict[str, str]
    total_size_bytes: int
    record_count: int
    schema: Dict[str, str]
    tags: List[str] = field(default_factory=list)
    parent_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    commit_message: str = ""


@dataclass
class DataFile:
    """Individual data file tracking."""
    file_id: str
    path: str
    checksum: str
    size_bytes: int
    content_type: str
    version_ids: List[str] = field(default_factory=list)
    storage_backend: str = "local"
    remote_path: Optional[str] = None


class DataVersionControl:
    """Version control for datasets."""
    
    def __init__(self, storage_path: str = ".dvc"):
        self.storage_path = storage_path
        self._datasets: Dict[str, List[DatasetVersion]] = {}
        self._files: Dict[str, DataFile] = {}
        self._tags: Dict[str, str] = {}  # tag -> version_id
    
    async def init_dataset(
        self,
        dataset_name: str,
        description: str = "",
        created_by: str = ""
    ) -> Dict[str, Any]:
        """Initialize a new dataset for versioning."""
        
        if dataset_name in self._datasets:
            raise ValueError(f"Dataset {dataset_name} already exists")
        
        self._datasets[dataset_name] = []
        
        return {
            "dataset_name": dataset_name,
            "initialized": True,
            "storage_path": f"{self.storage_path}/{dataset_name}",
            "description": description,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def add_files(
        self,
        dataset_name: str,
        files: List[Dict[str, Any]]
    ) -> List[DataFile]:
        """Add files to dataset staging area."""
        
        if dataset_name not in self._datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        added_files = []
        
        for file_data in files:
            file_path = file_data["path"]
            
            # Calculate checksum
            checksum = await self._calculate_file_hash(file_path)
            
            # Check if file already exists
            existing = None
            for f in self._files.values():
                if f.path == file_path:
                    existing = f
                    break
            
            if existing:
                # Update checksum if changed
                if existing.checksum != checksum:
                    existing.checksum = checksum
                    existing.size_bytes = file_data.get("size_bytes", 0)
                added_files.append(existing)
            else:
                # Create new file entry
                data_file = DataFile(
                    file_id=str(uuid.uuid4()),
                    path=file_path,
                    checksum=checksum,
                    size_bytes=file_data.get("size_bytes", 0),
                    content_type=file_data.get("content_type", "application/octet-stream"),
                    storage_backend=file_data.get("storage_backend", "local"),
                    remote_path=file_data.get("remote_path")
                )
                self._files[data_file.file_id] = data_file
                added_files.append(data_file)
        
        return added_files
    
    async def commit(
        self,
        dataset_name: str,
        message: str,
        created_by: str = "",
        tags: Optional[List[str]] = None
    ) -> DatasetVersion:
        """Commit staged files as new version."""
        
        if dataset_name not in self._datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        # Get staged files
        staged_files = [
            f for f in self._files.values()
            if dataset_name not in [v.dataset_name for v in self._get_file_versions(f)]
        ]
        
        if not staged_files:
            raise ValueError("No files staged for commit")
        
        # Generate version
        existing_versions = self._datasets[dataset_name]
        if existing_versions:
            # Increment version
            last_version = existing_versions[-1].version
            version_parts = last_version.split(".")
            new_version = f"{version_parts[0]}.{int(version_parts[1]) + 1}"
            parent_version = existing_versions[-1].version_id
        else:
            new_version = "v1.0"
            parent_version = None
        
        # Create file hashes
        file_hashes = {f.path: f.checksum for f in staged_files}
        total_size = sum(f.size_bytes for f in staged_files)
        
        # Infer schema from files (placeholder)
        schema = await self._infer_schema(staged_files)
        
        # Create version
        dataset_version = DatasetVersion(
            version_id=str(uuid.uuid4()),
            dataset_name=dataset_name,
            version=new_version,
            status=DatasetStatus.COMMITTED,
            file_hashes=file_hashes,
            total_size_bytes=total_size,
            record_count=await self._count_records(staged_files),
            schema=schema,
            tags=tags or [],
            parent_version=parent_version,
            created_by=created_by,
            commit_message=message
        )
        
        # Update file version tracking
        for f in staged_files:
            f.version_ids.append(dataset_version.version_id)
        
        self._datasets[dataset_name].append(dataset_version)
        
        return dataset_version
    
    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file."""
        # Placeholder - in production, read and hash actual file
        return hashlib.md5(file_path.encode()).hexdigest()
    
    def _get_file_versions(self, data_file: DataFile) -> List[DatasetVersion]:
        """Get all versions containing a file."""
        versions = []
        for dataset_versions in self._datasets.values():
            for version in dataset_versions:
                if data_file.path in version.file_hashes:
                    versions.append(version)
        return versions
    
    async def _infer_schema(self, files: List[DataFile]) -> Dict[str, str]:
        """Infer schema from data files."""
        # Placeholder - in production, parse actual data
        return {"column_1": "string", "column_2": "float"}
    
    async def _count_records(self, files: List[DataFile]) -> int:
        """Count records in files."""
        # Placeholder - in production, count actual records
        return sum(f.size_bytes // 100 for f in files)  # Rough estimate
    
    async def checkout(
        self,
        dataset_name: str,
        version: str
    ) -> DatasetVersion:
        """Checkout a specific version."""
        
        if dataset_name not in self._datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        for v in self._datasets[dataset_name]:
            if v.version == version:
                return v
        
        raise ValueError(f"Version {version} not found for dataset {dataset_name}")
    
    async def tag_version(
        self,
        dataset_name: str,
        version: str,
        tag: str
    ) -> bool:
        """Tag a specific version."""
        
        dataset_version = await self.checkout(dataset_name, version)
        
        if tag in self._tags:
            raise ValueError(f"Tag {tag} already exists")
        
        self._tags[tag] = dataset_version.version_id
        dataset_version.tags.append(tag)
        dataset_version.status = DatasetStatus.TAGGED
        
        return True
    
    async def get_version_history(
        self,
        dataset_name: str
    ) -> List[Dict[str, Any]]:
        """Get version history for a dataset."""
        
        if dataset_name not in self._datasets:
            raise ValueError(f"Dataset {dataset_name} not found")
        
        return [
            {
                "version_id": v.version_id,
                "version": v.version,
                "status": v.status.value,
                "message": v.commit_message,
                "created_by": v.created_by,
                "created_at": v.created_at.isoformat(),
                "tags": v.tags,
                "file_count": len(v.file_hashes),
                "total_size_mb": v.total_size_bytes / (1024 * 1024)
            }
            for v in self._datasets[dataset_name]
        ]
    
    async def diff_versions(
        self,
        dataset_name: str,
        version_a: str,
        version_b: str
    ) -> Dict[str, Any]:
        """Compare two versions."""
        
        v_a = await self.checkout(dataset_name, version_a)
        v_b = await self.checkout(dataset_name, version_b)
        
        # Find added, removed, modified files
        files_a = set(v_a.file_hashes.keys())
        files_b = set(v_b.file_hashes.keys())
        
        added = files_b - files_a
        removed = files_a - files_b
        common = files_a & files_b
        
        modified = [
            f for f in common
            if v_a.file_hashes[f] != v_b.file_hashes[f]
        ]
        
        return {
            "dataset_name": dataset_name,
            "version_a": version_a,
            "version_b": version_b,
            "added_files": list(added),
            "removed_files": list(removed),
            "modified_files": modified,
            "unchanged_files": list(common - set(modified)),
            "size_change_mb": (
                (v_b.total_size_bytes - v_a.total_size_bytes) / (1024 * 1024)
            )
        }
    
    async def push_to_remote(
        self,
        dataset_name: str,
        remote_name: str = "origin"
    ) -> Dict[str, Any]:
        """Push dataset to remote storage."""
        
        # Placeholder for remote push
        return {
            "dataset_name": dataset_name,
            "remote": remote_name,
            "status": "pushed",
            "files_synced": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def pull_from_remote(
        self,
        dataset_name: str,
        remote_name: str = "origin",
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pull dataset from remote storage."""
        
        # Placeholder for remote pull
        return {
            "dataset_name": dataset_name,
            "remote": remote_name,
            "version": version,
            "status": "pulled",
            "files_downloaded": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
