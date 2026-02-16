"""
Synthetic Transaction Testing
Automated end-to-end transaction testing
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

import aiohttp
import playwright.async_api as playwright

from app.core.config import settings

logger = logging.getLogger(__name__)


class SyntheticTestStatus(Enum):
    """Synthetic test status"""
    PASS = 'pass'
    FAIL = 'fail'
    WARNING = 'warning'
    SKIPPED = 'skipped'


@dataclass
class SyntheticStep:
    """Synthetic test step"""
    name: str
    action: str  # navigate, click, type, assert, wait
    target: str  # URL, selector, etc.
    value: Optional[str] = None
    timeout_seconds: int = 30
    expected_result: Optional[str] = None


@dataclass
class SyntheticTest:
    """Synthetic test definition"""
    id: str
    name: str
    description: str
    steps: List[SyntheticStep]
    frequency_minutes: int = 5
    enabled: bool = True
    alert_on_failure: bool = True
    regions: List[str] = field(default_factory=lambda: ['us-east-1'])


@dataclass
class StepResult:
    """Step execution result"""
    step_name: str
    status: SyntheticTestStatus
    duration_ms: float
    screenshot: Optional[str] = None
    error_message: Optional[str] = None
    actual_result: Optional[str] = None


@dataclass
class TestResult:
    """Test execution result"""
    test_id: str
    timestamp: datetime
    status: SyntheticTestStatus
    duration_ms: float
    step_results: List[StepResult]
    region: str
    error_count: int = 0


class SyntheticTestRunner:
    """Run synthetic tests using Playwright"""
    
    def __init__(self):
        self.tests: Dict[str, SyntheticTest] = {}
        self.results: Dict[str, List[TestResult]] = {}
        self._playwright: Optional[playwright.Playwright] = None
        self._browser: Optional[playwright.Browser] = None
        self._running = False
    
    async def initialize(self):
        """Initialize Playwright"""
        self._playwright = await playwright.async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._running = True
        
        logger.info("Synthetic test runner initialized")
    
    async def close(self):
        """Close Playwright"""
        self._running = False
        
        if self._browser:
            await self._browser.close()
        
        if self._playwright:
            await self._playwright.stop()
        
        logger.info("Synthetic test runner stopped")
    
    def add_test(self, test: SyntheticTest):
        """Add a synthetic test"""
        self.tests[test.id] = test
        
        if test.enabled:
            asyncio.create_task(self._schedule_test(test))
    
    async def _schedule_test(self, test: SyntheticTest):
        """Schedule test to run periodically"""
        while self._running and test.enabled:
            try:
                result = await self.run_test(test)
                
                # Store result
                if test.id not in self.results:
                    self.results[test.id] = []
                
                self.results[test.id].append(result)
                
                # Keep only last 100 results
                if len(self.results[test.id]) > 100:
                    self.results[test.id] = self.results[test.id][-100:]
                
                # Alert on failure
                if result.status == SyntheticTestStatus.FAIL and test.alert_on_failure:
                    await self._alert_failure(test, result)
                
            except Exception as e:
                logger.error(f"Error running synthetic test {test.id}: {e}")
            
            await asyncio.sleep(test.frequency_minutes * 60)
    
    async def run_test(self, test: SyntheticTest) -> TestResult:
        """Run a synthetic test"""
        start_time = time.time()
        step_results = []
        error_count = 0
        
        context = await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        try:
            for step in test.steps:
                step_start = time.time()
                
                try:
                    step_result = await self._execute_step(page, step)
                    step_results.append(step_result)
                    
                    if step_result.status == SyntheticTestStatus.FAIL:
                        error_count += 1
                
                except Exception as e:
                    step_results.append(StepResult(
                        step_name=step.name,
                        status=SyntheticTestStatus.FAIL,
                        duration_ms=(time.time() - step_start) * 1000,
                        error_message=str(e)
                    ))
                    error_count += 1
            
            # Determine overall status
            if error_count == 0:
                status = SyntheticTestStatus.PASS
            elif error_count == len(test.steps):
                status = SyntheticTestStatus.FAIL
            else:
                status = SyntheticTestStatus.WARNING
            
        finally:
            await context.close()
        
        duration_ms = (time.time() - start_time) * 1000
        
        return TestResult(
            test_id=test.id,
            timestamp=datetime.utcnow(),
            status=status,
            duration_ms=duration_ms,
            step_results=step_results,
            region='us-east-1',
            error_count=error_count
        )
    
    async def _execute_step(self, page: playwright.Page, step: SyntheticStep) -> StepResult:
        """Execute a test step"""
        start_time = time.time()
        
        try:
            if step.action == 'navigate':
                await page.goto(step.target, timeout=step.timeout_seconds * 1000)
            
            elif step.action == 'click':
                await page.click(step.target, timeout=step.timeout_seconds * 1000)
            
            elif step.action == 'type':
                await page.fill(step.target, step.value, timeout=step.timeout_seconds * 1000)
            
            elif step.action == 'wait':
                if step.target.startswith('//'):
                    await page.wait_for_selector(f'xpath={step.target}', timeout=step.timeout_seconds * 1000)
                else:
                    await page.wait_for_selector(step.target, timeout=step.timeout_seconds * 1000)
            
            elif step.action == 'assert':
                if step.target.startswith('text='):
                    text = step.target.replace('text=', '')
                    content = await page.content()
                    assert text in content, f"Expected text '{text}' not found"
                else:
                    element = await page.query_selector(step.target)
                    assert element is not None, f"Expected element '{step.target}' not found"
            
            duration_ms = (time.time() - start_time) * 1000
            
            return StepResult(
                step_name=step.name,
                status=SyntheticTestStatus.PASS,
                duration_ms=duration_ms
            )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Take screenshot on failure
            screenshot = None
            try:
                screenshot_bytes = await page.screenshot()
                import base64
                screenshot = base64.b64encode(screenshot_bytes).decode()
            except:
                pass
            
            return StepResult(
                step_name=step.name,
                status=SyntheticTestStatus.FAIL,
                duration_ms=duration_ms,
                screenshot=screenshot,
                error_message=str(e)
            )
    
    async def _alert_failure(self, test: SyntheticTest, result: TestResult):
        """Alert on test failure"""
        logger.warning(f"Synthetic test failed: {test.name}")
        # Would send alert via notification system
    
    def get_test_results(self, test_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get test results"""
        results = self.results.get(test_id, [])
        
        return [
            {
                'test_id': r.test_id,
                'timestamp': r.timestamp.isoformat(),
                'status': r.status.value,
                'duration_ms': r.duration_ms,
                'error_count': r.error_count,
                'step_results': [
                    {
                        'step_name': s.step_name,
                        'status': s.status.value,
                        'duration_ms': s.duration_ms,
                        'error_message': s.error_message
                    }
                    for s in r.step_results
                ]
            }
            for r in results[-limit:]
        ]
    
    def get_test_stats(self, test_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get test statistics"""
        if test_id not in self.results:
            return {}
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        results = [r for r in self.results[test_id] if r.timestamp > cutoff]
        
        if not results:
            return {}
        
        total = len(results)
        passed = sum(1 for r in results if r.status == SyntheticTestStatus.PASS)
        failed = sum(1 for r in results if r.status == SyntheticTestStatus.FAIL)
        
        return {
            'total_runs': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': (passed / total * 100) if total > 0 else 0,
            'avg_duration_ms': sum(r.duration_ms for r in results) / total,
            'uptime_percentage': (passed / total * 100) if total > 0 else 0
        }


# Predefined synthetic tests
PREDEFINED_TESTS = [
    SyntheticTest(
        id='login-flow',
        name='User Login Flow',
        description='Test complete user login flow',
        frequency_minutes=5,
        steps=[
            SyntheticStep(
                name='Navigate to login',
                action='navigate',
                target='https://app.cerebrum.ai/login'
            ),
            SyntheticStep(
                name='Enter email',
                action='type',
                target='input[name="email"]',
                value='test@example.com'
            ),
            SyntheticStep(
                name='Enter password',
                action='type',
                target='input[name="password"]',
                value='testpassword'
            ),
            SyntheticStep(
                name='Click login',
                action='click',
                target='button[type="submit"]'
            ),
            SyntheticStep(
                name='Wait for dashboard',
                action='wait',
                target='[data-testid="dashboard"]'
            ),
            SyntheticStep(
                name='Assert dashboard loaded',
                action='assert',
                target='text=Dashboard'
            )
        ]
    ),
    SyntheticTest(
        id='api-health',
        name='API Health Check',
        description='Test API endpoints',
        frequency_minutes=1,
        steps=[
            SyntheticStep(
                name='Check health endpoint',
                action='navigate',
                target='https://api.cerebrum.ai/health'
            ),
            SyntheticStep(
                name='Assert healthy response',
                action='assert',
                target='text=healthy'
            )
        ]
    )
]


# Global test runner
synthetic_test_runner = SyntheticTestRunner()
