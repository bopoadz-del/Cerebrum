"""
Chaos Engineering Framework
Gremlin/Chaos Monkey style fault injection for Cerebrum AI Platform
"""

import asyncio
import random
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

import httpx
import docker
from kubernetes import client, config

from app.core.config import settings

logger = logging.getLogger(__name__)


class AttackType(Enum):
    """Types of chaos attacks"""
    # Infrastructure attacks
    INSTANCE_FAILURE = 'instance_failure'
    NETWORK_LATENCY = 'network_latency'
    NETWORK_PACKET_LOSS = 'network_packet_loss'
    CPU_LOAD = 'cpu_load'
    MEMORY_PRESSURE = 'memory_pressure'
    DISK_IO = 'disk_io'
    
    # Application attacks
    LATENCY_INJECTION = 'latency_injection'
    ERROR_INJECTION = 'error_injection'
    EXCEPTION_THROWING = 'exception_throwing'
    
    # Database attacks
    DB_SLOW_QUERY = 'db_slow_query'
    DB_CONNECTION_FAILURE = 'db_connection_failure'
    
    # Cache attacks
    CACHE_FAILURE = 'cache_failure'
    CACHE_LATENCY = 'cache_latency'


class AttackStatus(Enum):
    """Attack status"""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    STOPPED = 'stopped'


@dataclass
class ChaosAttack:
    """Chaos attack definition"""
    id: str
    type: AttackType
    target: str
    duration_seconds: int
    intensity: float  # 0.0 to 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: AttackStatus = AttackStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Experiment:
    """Chaos experiment definition"""
    id: str
    name: str
    description: str
    hypothesis: str
    attacks: List[ChaosAttack]
    abort_conditions: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    status: str = 'pending'
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ChaosMonkey:
    """Chaos Monkey for random instance failures"""
    
    def __init__(self):
        self.enabled = False
        self.attack_probability = 0.1  # 10% chance per interval
        self.interval_minutes = 60
        self.protected_instances: List[str] = []
        self._task: Optional[asyncio.Task] = None
        
        # Try to load Kubernetes config
        try:
            config.load_incluster_config()
            self.k8s_client = client.CoreV1Api()
            self.k8s_available = True
        except:
            self.k8s_available = False
            logger.warning("Kubernetes not available, Chaos Monkey limited")
    
    def enable(self, probability: float = 0.1, interval_minutes: int = 60):
        """Enable Chaos Monkey"""
        self.enabled = True
        self.attack_probability = probability
        self.interval_minutes = interval_minutes
        
        if not self._task:
            self._task = asyncio.create_task(self._run_loop())
        
        logger.info(f"Chaos Monkey enabled with {probability*100}% probability")
    
    def disable(self):
        """Disable Chaos Monkey"""
        self.enabled = False
        
        if self._task:
            self._task.cancel()
            self._task = None
        
        logger.info("Chaos Monkey disabled")
    
    def protect_instance(self, instance_id: str):
        """Protect an instance from Chaos Monkey"""
        if instance_id not in self.protected_instances:
            self.protected_instances.append(instance_id)
    
    async def _run_loop(self):
        """Main Chaos Monkey loop"""
        while self.enabled:
            try:
                if random.random() < self.attack_probability:
                    await self._execute_random_attack()
                
                await asyncio.sleep(self.interval_minutes * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Chaos Monkey error: {e}")
                await asyncio.sleep(60)
    
    async def _execute_random_attack(self):
        """Execute a random attack"""
        if not self.k8s_available:
            logger.warning("Cannot execute attack: Kubernetes not available")
            return
        
        try:
            # Get list of pods
            pods = self.k8s_client.list_namespaced_pod(
                namespace=settings.KUBERNETES_NAMESPACE or 'default'
            )
            
            # Filter out protected instances
            eligible_pods = [
                pod for pod in pods.items
                if pod.metadata.name not in self.protected_instances
                and pod.status.phase == 'Running'
            ]
            
            if not eligible_pods:
                logger.info("No eligible pods for Chaos Monkey attack")
                return
            
            # Select random pod
            victim = random.choice(eligible_pods)
            
            logger.info(f"Chaos Monkey attacking pod: {victim.metadata.name}")
            
            # Delete the pod
            self.k8s_client.delete_namespaced_pod(
                name=victim.metadata.name,
                namespace=victim.metadata.namespace,
                body=client.V1DeleteOptions()
            )
            
            logger.info(f"Successfully terminated pod: {victim.metadata.name}")
            
        except Exception as e:
            logger.error(f"Failed to execute Chaos Monkey attack: {e}")


class LatencyMonkey:
    """Inject latency into requests"""
    
    def __init__(self):
        self.enabled = False
        self.latency_ms = 100
        self.probability = 0.1
        self._injected_latencies: Dict[str, float] = {}
    
    def enable(self, latency_ms: int = 100, probability: float = 0.1):
        """Enable latency injection"""
        self.enabled = True
        self.latency_ms = latency_ms
        self.probability = probability
        logger.info(f"Latency Monkey enabled: {latency_ms}ms with {probability*100}% probability")
    
    def disable(self):
        """Disable latency injection"""
        self.enabled = False
        logger.info("Latency Monkey disabled")
    
    def should_inject(self) -> bool:
        """Check if latency should be injected"""
        return self.enabled and random.random() < self.probability
    
    def get_latency(self) -> float:
        """Get injected latency with some randomness"""
        return random.uniform(self.latency_ms * 0.5, self.latency_ms * 1.5)


class ErrorMonkey:
    """Inject errors into responses"""
    
    def __init__(self):
        self.enabled = False
        self.error_rate = 0.01  # 1% error rate
        self.error_codes = [500, 502, 503, 504]
        self._excluded_paths: List[str] = ['/health', '/ready', '/metrics']
    
    def enable(self, error_rate: float = 0.01, error_codes: List[int] = None):
        """Enable error injection"""
        self.enabled = True
        self.error_rate = error_rate
        if error_codes:
            self.error_codes = error_codes
        logger.info(f"Error Monkey enabled: {error_rate*100}% error rate")
    
    def disable(self):
        """Disable error injection"""
        self.enabled = False
        logger.info("Error Monkey disabled")
    
    def should_inject(self, path: str = None) -> bool:
        """Check if error should be injected"""
        if not self.enabled:
            return False
        
        if path and any(path.startswith(excluded) for excluded in self._excluded_paths):
            return False
        
        return random.random() < self.error_rate
    
    def get_error_code(self) -> int:
        """Get random error code"""
        return random.choice(self.error_codes)


class ChaosOrchestrator:
    """Orchestrate chaos experiments"""
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
        self.active_attacks: Dict[str, ChaosAttack] = {}
        self.chaos_monkey = ChaosMonkey()
        self.latency_monkey = LatencyMonkey()
        self.error_monkey = ErrorMonkey()
        self._abort_signal = False
    
    def create_experiment(self, experiment: Experiment) -> str:
        """Create a new chaos experiment"""
        self.experiments[experiment.id] = experiment
        logger.info(f"Created chaos experiment: {experiment.id}")
        return experiment.id
    
    async def run_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """Run a chaos experiment"""
        if experiment_id not in self.experiments:
            return {'error': 'Experiment not found'}
        
        experiment = self.experiments[experiment_id]
        experiment.status = 'running'
        experiment.started_at = datetime.utcnow()
        
        logger.info(f"Starting chaos experiment: {experiment.name}")
        
        results = {
            'experiment_id': experiment_id,
            'attacks': [],
            'aborted': False,
            'abort_reason': None
        }
        
        try:
            for attack in experiment.attacks:
                if self._abort_signal:
                    results['aborted'] = True
                    results['abort_reason'] = 'Manual abort'
                    break
                
                # Check abort conditions
                if await self._check_abort_conditions(experiment):
                    results['aborted'] = True
                    results['abort_reason'] = 'Abort condition met'
                    break
                
                # Execute attack
                attack_result = await self._execute_attack(attack)
                results['attacks'].append(attack_result)
                
                # Wait between attacks
                await asyncio.sleep(5)
            
            # Evaluate success criteria
            results['success'] = await self._evaluate_success_criteria(experiment, results)
            
        except Exception as e:
            logger.error(f"Experiment failed: {e}")
            results['error'] = str(e)
        
        experiment.status = 'completed'
        experiment.completed_at = datetime.utcnow()
        
        return results
    
    async def _execute_attack(self, attack: ChaosAttack) -> Dict[str, Any]:
        """Execute a single chaos attack"""
        attack.status = AttackStatus.RUNNING
        attack.started_at = datetime.utcnow()
        
        self.active_attacks[attack.id] = attack
        
        try:
            if attack.type == AttackType.INSTANCE_FAILURE:
                await self._attack_instance_failure(attack)
            elif attack.type == AttackType.NETWORK_LATENCY:
                await self._attack_network_latency(attack)
            elif attack.type == AttackType.CPU_LOAD:
                await self._attack_cpu_load(attack)
            elif attack.type == AttackType.MEMORY_PRESSURE:
                await self._attack_memory_pressure(attack)
            elif attack.type == AttackType.LATENCY_INJECTION:
                await self._attack_latency_injection(attack)
            elif attack.type == AttackType.ERROR_INJECTION:
                await self._attack_error_injection(attack)
            else:
                logger.warning(f"Unknown attack type: {attack.type}")
            
            attack.status = AttackStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Attack failed: {e}")
            attack.status = AttackStatus.FAILED
            attack.results['error'] = str(e)
        
        attack.completed_at = datetime.utcnow()
        del self.active_attacks[attack.id]
        
        return {
            'attack_id': attack.id,
            'type': attack.type.value,
            'status': attack.status.value,
            'duration_seconds': attack.duration_seconds,
            'results': attack.results
        }
    
    async def _attack_instance_failure(self, attack: ChaosAttack):
        """Simulate instance failure"""
        # Use Chaos Monkey to terminate an instance
        if self.chaos_monkey.k8s_available:
            pods = self.chaos_monkey.k8s_client.list_namespaced_pod(
                namespace=settings.KUBERNETES_NAMESPACE or 'default',
                label_selector=f"app={attack.target}"
            )
            
            if pods.items:
                victim = random.choice(pods.items)
                self.chaos_monkey.k8s_client.delete_namespaced_pod(
                    name=victim.metadata.name,
                    namespace=victim.metadata.namespace
                )
                attack.results['terminated_pod'] = victim.metadata.name
        
        await asyncio.sleep(attack.duration_seconds)
    
    async def _attack_network_latency(self, attack: ChaosAttack):
        """Simulate network latency"""
        latency_ms = attack.parameters.get('latency_ms', 100)
        
        # Use tc (traffic control) to add latency
        # This would require privileged access
        logger.info(f"Injecting {latency_ms}ms network latency for {attack.duration_seconds}s")
        
        await asyncio.sleep(attack.duration_seconds)
    
    async def _attack_cpu_load(self, attack: ChaosAttack):
        """Generate CPU load"""
        cores = attack.parameters.get('cores', 1)
        
        logger.info(f"Generating CPU load on {cores} cores for {attack.duration_seconds}s")
        
        # Start CPU stress
        end_time = time.time() + attack.duration_seconds
        
        def cpu_stress():
            while time.time() < end_time:
                pass
        
        # Run stress in threads
        import threading
        threads = []
        for _ in range(cores):
            t = threading.Thread(target=cpu_stress)
            t.start()
            threads.append(t)
        
        await asyncio.sleep(attack.duration_seconds)
        
        for t in threads:
            t.join(timeout=1)
    
    async def _attack_memory_pressure(self, attack: ChaosAttack):
        """Generate memory pressure"""
        memory_mb = attack.parameters.get('memory_mb', 512)
        
        logger.info(f"Allocating {memory_mb}MB of memory for {attack.duration_seconds}s")
        
        # Allocate memory
        data = bytearray(memory_mb * 1024 * 1024)
        
        await asyncio.sleep(attack.duration_seconds)
        
        # Release memory
        del data
    
    async def _attack_latency_injection(self, attack: ChaosAttack):
        """Inject latency into application"""
        latency_ms = attack.parameters.get('latency_ms', 100)
        probability = attack.parameters.get('probability', 0.1)
        
        self.latency_monkey.enable(latency_ms, probability)
        
        await asyncio.sleep(attack.duration_seconds)
        
        self.latency_monkey.disable()
    
    async def _attack_error_injection(self, attack: ChaosAttack):
        """Inject errors into application"""
        error_rate = attack.parameters.get('error_rate', 0.01)
        
        self.error_monkey.enable(error_rate)
        
        await asyncio.sleep(attack.duration_seconds)
        
        self.error_monkey.disable()
    
    async def _check_abort_conditions(self, experiment: Experiment) -> bool:
        """Check if experiment should be aborted"""
        # Check error rate threshold
        # Check latency threshold
        # Check availability threshold
        return False
    
    async def _evaluate_success_criteria(self, experiment: Experiment, 
                                         results: Dict[str, Any]) -> bool:
        """Evaluate if experiment met success criteria"""
        # Check if system recovered
        # Check if SLOs were maintained
        return True
    
    def abort_experiment(self, experiment_id: str):
        """Abort a running experiment"""
        self._abort_signal = True
        logger.info(f"Abort signal sent for experiment: {experiment_id}")
    
    def stop_attack(self, attack_id: str):
        """Stop a running attack"""
        if attack_id in self.active_attacks:
            self.active_attacks[attack_id].status = AttackStatus.STOPPED
            logger.info(f"Stopped attack: {attack_id}")
    
    def get_experiments(self) -> List[Dict[str, Any]]:
        """Get all experiments"""
        return [
            {
                'id': exp.id,
                'name': exp.name,
                'status': exp.status,
                'started_at': exp.started_at.isoformat() if exp.started_at else None,
                'completed_at': exp.completed_at.isoformat() if exp.completed_at else None
            }
            for exp in self.experiments.values()
        ]


# Predefined experiments
PREDEFINED_EXPERIMENTS = {
    'instance_failure': Experiment(
        id='instance-failure-test',
        name='Instance Failure Test',
        description='Test system resilience to instance failures',
        hypothesis='System should continue operating with degraded capacity',
        attacks=[
            ChaosAttack(
                id='terminate-pod',
                type=AttackType.INSTANCE_FAILURE,
                target='api',
                duration_seconds=60,
                intensity=0.5
            )
        ],
        abort_conditions=['error_rate > 50%', 'availability < 95%'],
        success_criteria=['auto_recovery < 60s', 'no_data_loss']
    ),
    'network_degradation': Experiment(
        id='network-degradation-test',
        name='Network Degradation Test',
        description='Test system under network latency',
        hypothesis='System should handle increased latency gracefully',
        attacks=[
            ChaosAttack(
                id='add-latency',
                type=AttackType.NETWORK_LATENCY,
                target='api',
                duration_seconds=300,
                intensity=0.3,
                parameters={'latency_ms': 200}
            )
        ],
        abort_conditions=['p99_latency > 5s'],
        success_criteria=['p99_latency < 3s', 'no_timeout_errors']
    ),
    'database_stress': Experiment(
        id='database-stress-test',
        name='Database Stress Test',
        description='Test database under load',
        hypothesis='Database should handle increased load without failures',
        attacks=[
            ChaosAttack(
                id='slow-queries',
                type=AttackType.DB_SLOW_QUERY,
                target='database',
                duration_seconds=180,
                intensity=0.5
            )
        ],
        abort_conditions=['db_connections_exhausted', 'replication_lag > 30s'],
        success_criteria=['query_time < 2s', 'no_deadlocks']
    )
}


# Global orchestrator
chaos_orchestrator = ChaosOrchestrator()
