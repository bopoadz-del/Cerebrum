"""
Performance Testing Framework
K6/Locust-style load testing for Cerebrum AI Platform
"""

import asyncio
import time
import random
import statistics
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

import aiohttp
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TestPhase(Enum):
    """Load test phases"""
    RAMP_UP = 'ramp_up'
    STEADY_STATE = 'steady_state'
    RAMP_DOWN = 'ramp_down'
    SPIKE = 'spike'


@dataclass
class TestScenario:
    """Load test scenario"""
    id: str
    name: str
    endpoint: str
    method: str = 'GET'
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None
    weight: int = 1  # Relative frequency
    expected_status: int = 200
    timeout_seconds: float = 30.0


@dataclass
class TestResult:
    """Individual test result"""
    scenario_id: str
    timestamp: datetime
    duration_ms: float
    status_code: int
    success: bool
    error_message: Optional[str] = None
    response_size: int = 0


@dataclass
class TestMetrics:
    """Aggregated test metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0
    durations: List[float] = field(default_factory=list)
    status_codes: Dict[int, int] = field(default_factory=dict)
    errors: Dict[str, int] = field(default_factory=dict)
    
    def add_result(self, result: TestResult):
        """Add a test result"""
        self.total_requests += 1
        
        if result.success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_duration_ms += result.duration_ms
        self.min_duration_ms = min(self.min_duration_ms, result.duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, result.duration_ms)
        self.durations.append(result.duration_ms)
        
        self.status_codes[result.status_code] = self.status_codes.get(result.status_code, 0) + 1
        
        if result.error_message:
            self.errors[result.error_message] = self.errors.get(result.error_message, 0) + 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        if not self.durations:
            return {}
        
        sorted_durations = sorted(self.durations)
        n = len(sorted_durations)
        
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (self.successful_requests / self.total_requests) * 100,
            'avg_duration_ms': statistics.mean(self.durations),
            'min_duration_ms': self.min_duration_ms,
            'max_duration_ms': self.max_duration_ms,
            'p50_duration_ms': sorted_durations[int(n * 0.50)],
            'p90_duration_ms': sorted_durations[int(n * 0.90)],
            'p95_duration_ms': sorted_durations[int(n * 0.95)],
            'p99_duration_ms': sorted_durations[int(n * 0.99)],
            'requests_per_second': self.total_requests / (sum(self.durations) / 1000),
            'status_codes': self.status_codes,
            'errors': self.errors
        }


class LoadTestEngine:
    """Load testing engine"""
    
    def __init__(self):
        self.scenarios: List[TestScenario] = []
        self.results: List[TestResult] = []
        self.metrics = TestMetrics()
        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialize the test engine"""
        connector = aiohttp.TCPConnector(
            limit=1000,
            limit_per_host=100,
            enable_cleanup_closed=True,
            force_close=True
        )
        
        timeout = aiohttp.ClientTimeout(total=30)
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
    
    async def close(self):
        """Close the test engine"""
        if self._session:
            await self._session.close()
    
    def add_scenario(self, scenario: TestScenario):
        """Add a test scenario"""
        self.scenarios.append(scenario)
    
    async def run_load_test(
        self,
        duration_seconds: int = 60,
        concurrent_users: int = 100,
        ramp_up_seconds: int = 10
    ) -> Dict[str, Any]:
        """Run a load test"""
        self._running = True
        self.results = []
        self.metrics = TestMetrics()
        
        start_time = time.time()
        
        # Create virtual users
        tasks = []
        for i in range(concurrent_users):
            # Stagger user starts during ramp-up
            delay = (i / concurrent_users) * ramp_up_seconds
            task = asyncio.create_task(
                self._virtual_user(duration_seconds, delay)
            )
            tasks.append(task)
        
        # Wait for all users to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        self._running = False
        
        return {
            'test_duration_seconds': total_time,
            'configuration': {
                'duration_seconds': duration_seconds,
                'concurrent_users': concurrent_users,
                'ramp_up_seconds': ramp_up_seconds
            },
            'metrics': self.metrics.get_summary(),
            'scenarios_tested': [s.id for s in self.scenarios]
        }
    
    async def _virtual_user(self, duration_seconds: float, start_delay: float):
        """Simulate a virtual user"""
        # Wait for ramp-up delay
        await asyncio.sleep(start_delay)
        
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time and self._running:
            # Select a scenario based on weights
            scenario = self._select_scenario()
            
            # Execute the scenario
            result = await self._execute_scenario(scenario)
            
            # Record result
            self.results.append(result)
            self.metrics.add_result(result)
            
            # Small delay between requests (think time)
            await asyncio.sleep(random.uniform(0.1, 1.0))
    
    def _select_scenario(self) -> TestScenario:
        """Select a scenario based on weights"""
        if not self.scenarios:
            raise ValueError("No scenarios defined")
        
        total_weight = sum(s.weight for s in self.scenarios)
        r = random.uniform(0, total_weight)
        
        cumulative = 0
        for scenario in self.scenarios:
            cumulative += scenario.weight
            if r <= cumulative:
                return scenario
        
        return self.scenarios[-1]
    
    async def _execute_scenario(self, scenario: TestScenario) -> TestResult:
        """Execute a single scenario"""
        start_time = time.time()
        
        try:
            method = getattr(self._session, scenario.method.lower())
            
            async with method(
                scenario.endpoint,
                headers=scenario.headers,
                data=scenario.body
            ) as response:
                duration_ms = (time.time() - start_time) * 1000
                
                success = response.status == scenario.expected_status
                
                body = await response.read()
                
                return TestResult(
                    scenario_id=scenario.id,
                    timestamp=datetime.utcnow(),
                    duration_ms=duration_ms,
                    status_code=response.status,
                    success=success,
                    response_size=len(body)
                )
                
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                scenario_id=scenario.id,
                timestamp=datetime.utcnow(),
                duration_ms=duration_ms,
                status_code=0,
                success=False,
                error_message='Timeout'
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                scenario_id=scenario.id,
                timestamp=datetime.utcnow(),
                duration_ms=duration_ms,
                status_code=0,
                success=False,
                error_message=str(e)
            )
    
    def get_results(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get test results"""
        return [
            {
                'scenario_id': r.scenario_id,
                'timestamp': r.timestamp.isoformat(),
                'duration_ms': r.duration_ms,
                'status_code': r.status_code,
                'success': r.success,
                'error_message': r.error_message
            }
            for r in self.results[-limit:]
        ]


class StressTest:
    """Stress testing utilities"""
    
    def __init__(self, engine: LoadTestEngine):
        self.engine = engine
    
    async def find_breaking_point(
        self,
        initial_users: int = 100,
        max_users: int = 10000,
        step_size: int = 100,
        step_duration: int = 60
    ) -> Dict[str, Any]:
        """Find the system's breaking point"""
        results = []
        current_users = initial_users
        
        while current_users <= max_users:
            logger.info(f"Testing with {current_users} users...")
            
            result = await self.engine.run_load_test(
                duration_seconds=step_duration,
                concurrent_users=current_users,
                ramp_up_seconds=10
            )
            
            metrics = result['metrics']
            
            results.append({
                'concurrent_users': current_users,
                'success_rate': metrics['success_rate'],
                'avg_duration_ms': metrics['avg_duration_ms'],
                'p95_duration_ms': metrics['p95_duration_ms']
            })
            
            # Check if we've hit the breaking point
            if metrics['success_rate'] < 95 or metrics['p95_duration_ms'] > 5000:
                logger.info(f"Breaking point found at {current_users} users")
                break
            
            current_users += step_size
        
        return {
            'breaking_point_users': current_users,
            'test_results': results
        }
    
    async def spike_test(
        self,
        normal_users: int = 100,
        spike_users: int = 1000,
        normal_duration: int = 60,
        spike_duration: int = 30
    ) -> Dict[str, Any]:
        """Perform a spike test"""
        # Normal load
        logger.info(f"Running normal load with {normal_users} users...")
        normal_result = await self.engine.run_load_test(
            duration_seconds=normal_duration,
            concurrent_users=normal_users
        )
        
        # Spike
        logger.info(f"Running spike with {spike_users} users...")
        spike_result = await self.engine.run_load_test(
            duration_seconds=spike_duration,
            concurrent_users=spike_users
        )
        
        # Recovery
        logger.info(f"Running recovery with {normal_users} users...")
        recovery_result = await self.engine.run_load_test(
            duration_seconds=normal_duration,
            concurrent_users=normal_users
        )
        
        return {
            'normal': normal_result,
            'spike': spike_result,
            'recovery': recovery_result,
            'recovery_time_seconds': self._calculate_recovery_time(
                normal_result['metrics'],
                recovery_result['metrics']
            )
        }
    
    def _calculate_recovery_time(
        self,
        baseline: Dict[str, Any],
        recovery: Dict[str, Any]
    ) -> float:
        """Calculate recovery time after spike"""
        baseline_p95 = baseline['p95_duration_ms']
        spike_p95 = recovery['p95_duration_ms']
        
        # Recovery is when we're within 20% of baseline
        threshold = baseline_p95 * 1.2
        
        if spike_p95 <= threshold:
            return 0
        
        # Estimate recovery time (simplified)
        return spike_p95 / baseline_p95


class PerformanceBenchmark:
    """Performance benchmarking"""
    
    def __init__(self):
        self.baselines: Dict[str, Dict[str, Any]] = {}
    
    def set_baseline(self, test_name: str, metrics: Dict[str, Any]):
        """Set performance baseline"""
        self.baselines[test_name] = {
            'metrics': metrics,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def compare_to_baseline(
        self,
        test_name: str,
        current_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare current metrics to baseline"""
        if test_name not in self.baselines:
            return {'error': 'No baseline set'}
        
        baseline = self.baselines[test_name]['metrics']
        
        comparisons = {}
        
        for metric in ['avg_duration_ms', 'p95_duration_ms', 'p99_duration_ms']:
            if metric in baseline and metric in current_metrics:
                baseline_val = baseline[metric]
                current_val = current_metrics[metric]
                
                change_pct = ((current_val - baseline_val) / baseline_val) * 100
                
                comparisons[metric] = {
                    'baseline': baseline_val,
                    'current': current_val,
                    'change_percent': change_pct,
                    'status': 'improved' if change_pct < -10 else 'degraded' if change_pct > 10 else 'stable'
                }
        
        return comparisons


# Predefined test scenarios
API_TEST_SCENARIOS = [
    TestScenario(
        id='health_check',
        name='Health Check',
        endpoint='/api/v1/health',
        method='GET',
        weight=5
    ),
    TestScenario(
        id='get_projects',
        name='Get Projects',
        endpoint='/api/v1/projects',
        method='GET',
        weight=10
    ),
    TestScenario(
        id='get_project',
        name='Get Single Project',
        endpoint='/api/v1/projects/123',
        method='GET',
        weight=20
    ),
    TestScenario(
        id='create_task',
        name='Create Task',
        endpoint='/api/v1/tasks',
        method='POST',
        headers={'Content-Type': 'application/json'},
        body='{"title": "Test Task", "project_id": "123"}',
        weight=5
    ),
    TestScenario(
        id='search',
        name='Search',
        endpoint='/api/v1/search?q=test',
        method='GET',
        weight=3
    )
]


# Global load test engine
load_test_engine = LoadTestEngine()
