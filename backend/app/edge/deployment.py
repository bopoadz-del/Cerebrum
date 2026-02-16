"""
OTA deployment for edge models.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import uuid
import hashlib
import asyncio


class DeploymentStatus(Enum):
    """Status of a deployment."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentType(Enum):
    """Type of deployment."""
    MODEL = "model"
    SOFTWARE = "software"
    CONFIG = "config"
    FIRMWARE = "firmware"


@dataclass
class DeploymentPackage:
    """Package to be deployed to edge device."""
    package_id: str
    name: str
    version: str
    type: DeploymentType
    file_url: str
    checksum: str
    size_bytes: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DeploymentJob:
    """Deployment job for a device."""
    job_id: str
    device_id: str
    package_id: str
    status: DeploymentStatus
    progress_percent: float
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    verification_result: Optional[bool] = None
    rollback_available: bool = True


class EdgeDeploymentManager:
    """Manage OTA deployments to edge devices."""
    
    def __init__(self, heartbeat_manager: Optional[Any] = None):
        self.heartbeat_manager = heartbeat_manager
        self.packages: Dict[str, DeploymentPackage] = {}
        self.jobs: Dict[str, DeploymentJob] = {}
        self._deployment_callbacks: List[Callable[[DeploymentJob], None]] = []
        self._chunk_size = 1024 * 1024  # 1MB chunks
    
    async def create_package(
        self,
        name: str,
        version: str,
        package_type: DeploymentType,
        file_path: str,
        file_url: str,
        metadata: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None
    ) -> DeploymentPackage:
        """Create a new deployment package."""
        
        package_id = str(uuid.uuid4())
        
        # Calculate checksum and size
        checksum = await self._calculate_checksum(file_path)
        size_bytes = await self._get_file_size(file_path)
        
        package = DeploymentPackage(
            package_id=package_id,
            name=name,
            version=version,
            type=package_type,
            file_url=file_url,
            checksum=checksum,
            size_bytes=size_bytes,
            metadata=metadata or {},
            dependencies=dependencies or []
        )
        
        self.packages[package_id] = package
        
        return package
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file."""
        # Placeholder - in production, read and hash actual file
        return hashlib.sha256(file_path.encode()).hexdigest()
    
    async def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        # Placeholder - in production, use actual file system
        return 0
    
    async def deploy_to_device(
        self,
        device_id: str,
        package_id: str,
        force: bool = False
    ) -> DeploymentJob:
        """Deploy a package to a device."""
        
        package = self.packages.get(package_id)
        if not package:
            raise ValueError(f"Package {package_id} not found")
        
        # Check if device is online
        if self.heartbeat_manager:
            status = await self.heartbeat_manager.get_device_status(device_id)
            if not status or status["status"] != "online":
                raise ValueError(f"Device {device_id} is not online")
        
        # Create deployment job
        job_id = str(uuid.uuid4())
        job = DeploymentJob(
            job_id=job_id,
            device_id=device_id,
            package_id=package_id,
            status=DeploymentStatus.PENDING,
            progress_percent=0.0
        )
        
        self.jobs[job_id] = job
        
        # Start deployment asynchronously
        asyncio.create_task(self._execute_deployment(job_id))
        
        return job
    
    async def _execute_deployment(self, job_id: str):
        """Execute the deployment process."""
        
        job = self.jobs[job_id]
        package = self.packages[job.package_id]
        
        try:
            job.status = DeploymentStatus.DOWNLOADING
            job.started_at = datetime.utcnow()
            await self._notify_deployment_update(job)
            
            # Send deployment command to device
            if self.heartbeat_manager:
                await self.heartbeat_manager.send_command(
                    job.device_id,
                    "start_deployment",
                    {
                        "job_id": job_id,
                        "package_id": package.package_id,
                        "file_url": package.file_url,
                        "checksum": package.checksum,
                        "size_bytes": package.size_bytes,
                        "type": package.type.value
                    }
                )
            
            # Wait for device to acknowledge and complete
            # In production, this would use a more robust mechanism
            await asyncio.sleep(5)
            
            job.status = DeploymentStatus.VERIFYING
            job.progress_percent = 75.0
            await self._notify_deployment_update(job)
            
            # Verify deployment
            job.verification_result = await self._verify_deployment(job)
            
            if job.verification_result:
                job.status = DeploymentStatus.COMPLETED
                job.progress_percent = 100.0
            else:
                job.status = DeploymentStatus.FAILED
                job.error_message = "Verification failed"
            
            job.completed_at = datetime.utcnow()
            
        except Exception as e:
            job.status = DeploymentStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
        
        await self._notify_deployment_update(job)
    
    async def _verify_deployment(self, job: DeploymentJob) -> bool:
        """Verify a deployment was successful."""
        # Placeholder - in production, query device for verification
        return True
    
    async def _notify_deployment_update(self, job: DeploymentJob):
        """Notify deployment update callbacks."""
        
        for callback in self._deployment_callbacks:
            try:
                await callback(job)
            except Exception:
                pass
    
    def on_deployment_update(self, callback: Callable[[DeploymentJob], None]):
        """Register a deployment update callback."""
        self._deployment_callbacks.append(callback)
    
    async def handle_deployment_status(
        self,
        device_id: str,
        job_id: str,
        status: str,
        progress: float,
        error_message: Optional[str] = None
    ):
        """Handle deployment status update from device."""
        
        job = self.jobs.get(job_id)
        if not job or job.device_id != device_id:
            return
        
        job.status = DeploymentStatus(status)
        job.progress_percent = progress
        
        if error_message:
            job.error_message = error_message
        
        await self._notify_deployment_update(job)
    
    async def rollback_deployment(self, job_id: str) -> bool:
        """Rollback a deployment."""
        
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        if not job.rollback_available:
            return False
        
        # Send rollback command
        if self.heartbeat_manager:
            success = await self.heartbeat_manager.send_command(
                job.device_id,
                "rollback_deployment",
                {"job_id": job_id}
            )
            
            if success:
                job.status = DeploymentStatus.ROLLED_BACK
                await self._notify_deployment_update(job)
            
            return success
        
        return False
    
    async def get_deployment_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a deployment job."""
        
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        package = self.packages.get(job.package_id)
        
        return {
            "job_id": job_id,
            "device_id": job.device_id,
            "package_name": package.name if package else "unknown",
            "package_version": package.version if package else "unknown",
            "status": job.status.value,
            "progress_percent": job.progress_percent,
            "error_message": job.error_message,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "rollback_available": job.rollback_available
        }
    
    async def list_deployments(
        self,
        device_id: Optional[str] = None,
        status: Optional[DeploymentStatus] = None
    ) -> List[Dict[str, Any]]:
        """List deployment jobs."""
        
        jobs = list(self.jobs.values())
        
        if device_id:
            jobs = [j for j in jobs if j.device_id == device_id]
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        return [
            await self.get_deployment_status(j.job_id)
            for j in sorted(jobs, key=lambda x: x.started_at or datetime.min, reverse=True)
        ]
    
    async def deploy_to_group(
        self,
        device_ids: List[str],
        package_id: str,
        rollout_strategy: str = "parallel",
        batch_size: int = 5
    ) -> Dict[str, Any]:
        """Deploy to a group of devices."""
        
        jobs = []
        
        if rollout_strategy == "parallel":
            # Deploy to all devices in parallel
            for device_id in device_ids:
                try:
                    job = await self.deploy_to_device(device_id, package_id)
                    jobs.append({"device_id": device_id, "job_id": job.job_id, "status": "started"})
                except Exception as e:
                    jobs.append({"device_id": device_id, "error": str(e), "status": "failed"})
        
        elif rollout_strategy == "sequential":
            # Deploy to devices one by one
            for device_id in device_ids:
                try:
                    job = await self.deploy_to_device(device_id, package_id)
                    jobs.append({"device_id": device_id, "job_id": job.job_id, "status": "started"})
                    
                    # Wait for completion before next
                    await self._wait_for_completion(job.job_id)
                except Exception as e:
                    jobs.append({"device_id": device_id, "error": str(e), "status": "failed"})
        
        elif rollout_strategy == "canary":
            # Deploy to small batch first, then rest
            canary_batch = device_ids[:batch_size]
            rest_batch = device_ids[batch_size:]
            
            # Deploy canary
            for device_id in canary_batch:
                try:
                    job = await self.deploy_to_device(device_id, package_id)
                    jobs.append({"device_id": device_id, "job_id": job.job_id, "status": "canary"})
                except Exception as e:
                    jobs.append({"device_id": device_id, "error": str(e), "status": "failed"})
            
            # Wait for canary to complete
            await asyncio.gather(*[
                self._wait_for_completion(j["job_id"])
                for j in jobs if j.get("status") == "canary"
            ])
            
            # Deploy to rest
            for device_id in rest_batch:
                try:
                    job = await self.deploy_to_device(device_id, package_id)
                    jobs.append({"device_id": device_id, "job_id": job.job_id, "status": "started"})
                except Exception as e:
                    jobs.append({"device_id": device_id, "error": str(e), "status": "failed"})
        
        return {
            "package_id": package_id,
            "rollout_strategy": rollout_strategy,
            "total_devices": len(device_ids),
            "jobs": jobs
        }
    
    async def _wait_for_completion(self, job_id: str, timeout: int = 300):
        """Wait for a deployment to complete."""
        
        start_time = datetime.utcnow()
        
        while True:
            job = self.jobs.get(job_id)
            if not job:
                return
            
            if job.status in [DeploymentStatus.COMPLETED, DeploymentStatus.FAILED]:
                return
            
            if (datetime.utcnow() - start_time).total_seconds() > timeout:
                return
            
            await asyncio.sleep(5)
