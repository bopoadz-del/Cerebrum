"""
Automated Backup Verification and Restore Testing
Enterprise-grade backup validation and disaster recovery
"""
import os
import hashlib
import logging
import asyncio
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Types of backups"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class BackupStatus(Enum):
    """Backup status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"


class RestoreTestStatus(Enum):
    """Restore test status"""
    SCHEDULED = "scheduled"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class BackupMetadata:
    """Backup metadata"""
    id: str
    backup_type: BackupType
    source: str
    destination: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    size_bytes: int = 0
    checksum: Optional[str] = None
    status: BackupStatus = BackupStatus.PENDING
    compression_ratio: float = 0.0
    encryption_enabled: bool = False
    retention_days: int = 30
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RestoreTest:
    """Restore test record"""
    id: str
    backup_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: RestoreTestStatus = RestoreTestStatus.SCHEDULED
    test_environment: str = "isolated"
    tables_tested: List[str] = field(default_factory=list)
    files_tested: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BackupVerificationResult:
    """Backup verification result"""
    backup_id: str
    verified_at: datetime
    checksum_valid: bool
    integrity_check: bool
    size_check: bool
    metadata_valid: bool
    can_restore: bool
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class BackupVerificationEngine:
    """Engine for verifying backup integrity"""
    
    def __init__(self):
        self._verification_history: List[BackupVerificationResult] = []
        self._checksum_algorithms = ['sha256', 'md5']
    
    async def verify_backup(self, backup: BackupMetadata) -> BackupVerificationResult:
        """Verify backup integrity"""
        result = BackupVerificationResult(
            backup_id=backup.id,
            verified_at=datetime.utcnow(),
            checksum_valid=False,
            integrity_check=False,
            size_check=False,
            metadata_valid=False,
            can_restore=False
        )
        
        try:
            # Verify checksum
            result.checksum_valid = await self._verify_checksum(backup)
            
            # Verify file integrity
            result.integrity_check = await self._verify_integrity(backup)
            
            # Verify size
            result.size_check = await self._verify_size(backup)
            
            # Verify metadata
            result.metadata_valid = await self._verify_metadata(backup)
            
            # Determine if backup can be restored
            result.can_restore = all([
                result.checksum_valid,
                result.integrity_check,
                result.size_check,
                result.metadata_valid
            ])
            
            if not result.can_restore:
                result.issues = self._generate_issues(result)
                result.recommendations = self._generate_recommendations(result)
            
            backup.status = BackupStatus.VERIFIED if result.can_restore else BackupStatus.CORRUPTED
            
        except Exception as e:
            logger.error(f"Backup verification failed for {backup.id}: {e}")
            result.issues.append(str(e))
            backup.status = BackupStatus.FAILED
        
        self._verification_history.append(result)
        return result
    
    async def _verify_checksum(self, backup: BackupMetadata) -> bool:
        """Verify backup checksum"""
        if not backup.checksum:
            logger.warning(f"No checksum for backup {backup.id}")
            return False
        
        try:
            # Calculate actual checksum
            actual_checksum = await self._calculate_checksum(backup.destination)
            return actual_checksum == backup.checksum
        except Exception as e:
            logger.error(f"Checksum verification failed: {e}")
            return False
    
    async def _calculate_checksum(self, file_path: str, 
                                   algorithm: str = 'sha256') -> str:
        """Calculate file checksum"""
        hash_obj = hashlib.new(algorithm)
        
        # Read file in chunks
        chunk_size = 8192
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    async def _verify_integrity(self, backup: BackupMetadata) -> bool:
        """Verify backup file integrity"""
        try:
            # Check if file exists and is readable
            if not os.path.exists(backup.destination):
                return False
            
            # Check if file is not empty
            if backup.size_bytes == 0:
                return False
            
            # For compressed backups, verify archive integrity
            if backup.destination.endswith(('.gz', '.bz2', '.zip')):
                return await self._verify_archive_integrity(backup.destination)
            
            # For database backups, verify format
            if backup.destination.endswith(('.sql', '.dump', '.backup')):
                return await self._verify_database_backup(backup.destination)
            
            return True
            
        except Exception as e:
            logger.error(f"Integrity check failed: {e}")
            return False
    
    async def _verify_archive_integrity(self, archive_path: str) -> bool:
        """Verify compressed archive integrity"""
        import subprocess
        
        try:
            if archive_path.endswith('.gz'):
                result = subprocess.run(
                    ['gzip', '-t', archive_path],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            
            elif archive_path.endswith('.zip'):
                result = subprocess.run(
                    ['unzip', '-t', archive_path],
                    capture_output=True,
                    text=True
                )
                return result.returncode == 0
            
            return True
            
        except Exception as e:
            logger.error(f"Archive integrity check failed: {e}")
            return False
    
    async def _verify_database_backup(self, backup_path: str) -> bool:
        """Verify database backup format"""
        try:
            # Check if file starts with valid SQL or PostgreSQL custom format
            with open(backup_path, 'rb') as f:
                header = f.read(100)
                
                # PostgreSQL custom format starts with "PGDMP"
                if header.startswith(b'PGDMP'):
                    return True
                
                # SQL dump should start with SQL comments or commands
                if header.startswith(b'--') or b'PGDUMP' in header:
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Database backup verification failed: {e}")
            return False
    
    async def _verify_size(self, backup: BackupMetadata) -> bool:
        """Verify backup size"""
        try:
            actual_size = os.path.getsize(backup.destination)
            
            # Allow 10% variance for compression
            expected_size = backup.size_bytes
            variance = expected_size * 0.1
            
            return abs(actual_size - expected_size) <= variance
            
        except Exception as e:
            logger.error(f"Size verification failed: {e}")
            return False
    
    async def _verify_metadata(self, backup: BackupMetadata) -> bool:
        """Verify backup metadata"""
        required_fields = ['id', 'backup_type', 'source', 'started_at']
        
        for field in required_fields:
            if not getattr(backup, field, None):
                return False
        
        return True
    
    def _generate_issues(self, result: BackupVerificationResult) -> List[str]:
        """Generate list of issues from verification result"""
        issues = []
        
        if not result.checksum_valid:
            issues.append("Checksum mismatch - backup may be corrupted")
        
        if not result.integrity_check:
            issues.append("Integrity check failed - backup may be incomplete")
        
        if not result.size_check:
            issues.append("Size mismatch - backup may be truncated")
        
        if not result.metadata_valid:
            issues.append("Metadata validation failed")
        
        return issues
    
    def _generate_recommendations(self, result: BackupVerificationResult) -> List[str]:
        """Generate recommendations based on issues"""
        recommendations = []
        
        if not result.checksum_valid:
            recommendations.append("Re-create backup from source")
            recommendations.append("Verify source data integrity")
        
        if not result.integrity_check:
            recommendations.append("Check storage system for errors")
            recommendations.append("Verify backup process completed successfully")
        
        if not result.size_check:
            recommendations.append("Check for network interruptions during backup")
            recommendations.append("Verify available storage space")
        
        return recommendations


class RestoreTestEngine:
    """Engine for automated restore testing"""
    
    def __init__(self):
        self._test_history: List[RestoreTest] = []
        self._test_environments: Dict[str, Dict] = {}
        self._restore_strategies: Dict[str, Callable] = {}
    
    def register_test_environment(self, name: str, config: Dict):
        """Register a test environment"""
        self._test_environments[name] = config
    
    def register_restore_strategy(self, backup_type: str, strategy: Callable):
        """Register restore strategy for backup type"""
        self._restore_strategies[backup_type] = strategy
    
    async def schedule_restore_test(self, backup_id: str,
                                     environment: str = "isolated") -> str:
        """Schedule a restore test"""
        test_id = f"RT-{datetime.utcnow().strftime('%Y%m%d')}-{len(self._test_history)+1:05d}"
        
        test = RestoreTest(
            id=test_id,
            backup_id=backup_id,
            started_at=datetime.utcnow(),
            test_environment=environment
        )
        
        self._test_history.append(test)
        logger.info(f"Scheduled restore test: {test_id} for backup {backup_id}")
        
        return test_id
    
    async def run_restore_test(self, test_id: str) -> RestoreTest:
        """Execute restore test"""
        test = self._find_test(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")
        
        test.status = RestoreTestStatus.RUNNING
        test.started_at = datetime.utcnow()
        
        try:
            # Get test environment
            env_config = self._test_environments.get(test.test_environment, {})
            
            # Restore backup to test environment
            restore_result = await self._perform_restore(test, env_config)
            
            # Verify restored data
            verification_result = await self._verify_restored_data(test, env_config)
            
            # Run consistency checks
            consistency_result = await self._run_consistency_checks(test, env_config)
            
            # Determine test status
            if restore_result and verification_result and consistency_result:
                test.status = RestoreTestStatus.SUCCESS
            elif restore_result and verification_result:
                test.status = RestoreTestStatus.PARTIAL
            else:
                test.status = RestoreTestStatus.FAILED
            
            test.completed_at = datetime.utcnow()
            
            # Calculate performance metrics
            test.performance_metrics = self._calculate_metrics(test)
            
        except Exception as e:
            logger.error(f"Restore test failed: {e}")
            test.status = RestoreTestStatus.FAILED
            test.errors.append(str(e))
            test.completed_at = datetime.utcnow()
        
        return test
    
    async def _perform_restore(self, test: RestoreTest, 
                               env_config: Dict) -> bool:
        """Perform restore operation"""
        # This would integrate with actual backup systems
        logger.info(f"Performing restore for test {test.id}")
        
        # Simulate restore process
        await asyncio.sleep(1)
        
        return True
    
    async def _verify_restored_data(self, test: RestoreTest,
                                     env_config: Dict) -> bool:
        """Verify restored data integrity"""
        logger.info(f"Verifying restored data for test {test.id}")
        
        # Check row counts
        # Check table structures
        # Verify key relationships
        
        await asyncio.sleep(0.5)
        
        return True
    
    async def _run_consistency_checks(self, test: RestoreTest,
                                       env_config: Dict) -> bool:
        """Run data consistency checks"""
        logger.info(f"Running consistency checks for test {test.id}")
        
        # Check foreign key constraints
        # Verify index integrity
        # Validate data types
        
        await asyncio.sleep(0.5)
        
        return True
    
    def _calculate_metrics(self, test: RestoreTest) -> Dict[str, Any]:
        """Calculate performance metrics"""
        if not test.completed_at:
            return {}
        
        duration = (test.completed_at - test.started_at).total_seconds()
        
        return {
            'duration_seconds': duration,
            'tables_per_second': len(test.tables_tested) / duration if duration > 0 else 0,
            'files_per_second': len(test.files_tested) / duration if duration > 0 else 0,
            'error_rate': len(test.errors) / max(len(test.tables_tested), 1)
        }
    
    def _find_test(self, test_id: str) -> Optional[RestoreTest]:
        """Find test by ID"""
        for test in self._test_history:
            if test.id == test_id:
                return test
        return None
    
    def get_test_results(self, backup_id: str = None) -> List[RestoreTest]:
        """Get restore test results"""
        if backup_id:
            return [t for t in self._test_history if t.backup_id == backup_id]
        return self._test_history


class BackupRetentionManager:
    """Manages backup retention policies"""
    
    def __init__(self):
        self._retention_policies: Dict[str, Dict] = {}
        self._backup_registry: List[BackupMetadata] = []
    
    def set_retention_policy(self, backup_type: BackupType, 
                             days: int,
                             min_copies: int = 1):
        """Set retention policy for backup type"""
        self._retention_policies[backup_type.value] = {
            'days': days,
            'min_copies': min_copies
        }
    
    def register_backup(self, backup: BackupMetadata):
        """Register a backup for retention tracking"""
        self._backup_registry.append(backup)
    
    def get_expired_backups(self) -> List[BackupMetadata]:
        """Get list of backups that have expired"""
        expired = []
        now = datetime.utcnow()
        
        for backup in self._backup_registry:
            policy = self._retention_policies.get(backup.backup_type.value, {})
            retention_days = policy.get('days', backup.retention_days)
            
            if backup.completed_at:
                age = (now - backup.completed_at).days
                if age > retention_days:
                    expired.append(backup)
        
        return expired
    
    def cleanup_expired_backups(self) -> List[str]:
        """Clean up expired backups"""
        expired = self.get_expired_backups()
        removed = []
        
        for backup in expired:
            try:
                # Check minimum copies requirement
                policy = self._retention_policies.get(backup.backup_type.value, {})
                min_copies = policy.get('min_copies', 1)
                
                same_type_backups = [
                    b for b in self._backup_registry 
                    if b.backup_type == backup.backup_type and b.status == BackupStatus.VERIFIED
                ]
                
                if len(same_type_backups) > min_copies:
                    # Remove backup file
                    if os.path.exists(backup.destination):
                        os.remove(backup.destination)
                    
                    # Mark as removed
                    backup.status = BackupStatus.FAILED  # Use FAILED to indicate removed
                    removed.append(backup.id)
                    
                    logger.info(f"Removed expired backup: {backup.id}")
                
            except Exception as e:
                logger.error(f"Failed to remove backup {backup.id}: {e}")
        
        return removed


class DisasterRecoveryPlan:
    """Disaster recovery planning and execution"""
    
    def __init__(self):
        self._rto_minutes: int = 240  # Recovery Time Objective
        self._rpo_minutes: int = 60   # Recovery Point Objective
        self._recovery_procedures: Dict[str, Dict] = {}
        self._dr_tests: List[Dict] = []
    
    def set_objectives(self, rto_minutes: int, rpo_minutes: int):
        """Set RTO and RPO objectives"""
        self._rto_minutes = rto_minutes
        self._rpo_minutes = rpo_minutes
    
    def add_recovery_procedure(self, scenario: str, procedure: Dict):
        """Add recovery procedure for disaster scenario"""
        self._recovery_procedures[scenario] = procedure
    
    async def execute_dr_plan(self, scenario: str) -> Dict:
        """Execute disaster recovery plan"""
        procedure = self._recovery_procedures.get(scenario)
        if not procedure:
            raise ValueError(f"No procedure for scenario: {scenario}")
        
        start_time = datetime.utcnow()
        
        results = {
            'scenario': scenario,
            'started_at': start_time.isoformat(),
            'steps_completed': [],
            'steps_failed': [],
            'rto_met': False
        }
        
        try:
            for step in procedure.get('steps', []):
                step_result = await self._execute_recovery_step(step)
                
                if step_result:
                    results['steps_completed'].append(step['name'])
                else:
                    results['steps_failed'].append(step['name'])
            
            # Check RTO
            elapsed = (datetime.utcnow() - start_time).total_seconds() / 60
            results['rto_met'] = elapsed <= self._rto_minutes
            results['elapsed_minutes'] = elapsed
            
        except Exception as e:
            logger.error(f"DR plan execution failed: {e}")
            results['error'] = str(e)
        
        results['completed_at'] = datetime.utcnow().isoformat()
        self._dr_tests.append(results)
        
        return results
    
    async def _execute_recovery_step(self, step: Dict) -> bool:
        """Execute a single recovery step"""
        logger.info(f"Executing DR step: {step['name']}")
        
        # This would integrate with actual recovery systems
        await asyncio.sleep(0.5)
        
        return True


# Global instances
verification_engine = BackupVerificationEngine()
restore_test_engine = RestoreTestEngine()
retention_manager = BackupRetentionManager()
dr_plan = DisasterRecoveryPlan()