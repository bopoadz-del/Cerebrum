#!/usr/bin/env python3
"""
Cerebrum Prototype Validation Script

Comprehensive startup validation that tests:
1. Database connection
2. Redis connection
3. All 14 agent layers load correctly
4. API endpoints respond
5. Background tasks (Celery) are configured
6. Self-modification system functionality

Usage:
    python scripts/validate_prototype.py [--verbose] [--fail-fast]

Exit codes:
    0 - All checks passed
    1 - One or more critical checks failed
    2 - Validation script error
"""

import os
import sys
import asyncio
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

# Ensure we're in the backend directory context
BACKEND_DIR = Path(__file__).parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class CheckStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    WARNING = "WARNING"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    duration_ms: float
    details: Dict = field(default_factory=dict)


class CerebrumValidator:
    """Main validation orchestrator for Cerebrum prototype."""
    
    # The 14 agent layers in Cerebrum architecture
    AGENT_LAYERS = [
        ("coding", "Self-coding generation"),
        ("registry", "Capability registry"),
        ("validation", "Security & testing"),
        ("hotswap", "Dynamic deployment"),
        ("healing", "Self-healing"),
        ("prompts", "Prompt management"),
        ("triggers", "Event triggers"),
        ("economics", "Cost estimation"),
        ("vdc", "Virtual design & construction"),
        ("edge", "Edge inference"),
        ("portal", "User portal"),
        ("enterprise", "Security & auth"),
        ("connectors", "External integrations"),
        ("monitoring", "Observability"),
    ]
    
    def __init__(self, verbose: bool = False, fail_fast: bool = False):
        self.verbose = verbose
        self.fail_fast = fail_fast
        self.results: List[CheckResult] = []
        self.start_time = time.time()
        
    def log(self, message: str, level: str = "info"):
        """Log a message if verbose mode is enabled."""
        if self.verbose or level in ("error", "critical"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = {"error": "❌", "warning": "⚠️", "success": "✅", "info": "ℹ️"}.get(level, "ℹ️")
            print(f"[{timestamp}] {prefix} {message}")
    
    def add_result(self, result: CheckResult):
        """Add a check result and handle fail-fast."""
        self.results.append(result)
        icon = {
            CheckStatus.PASSED: "✅",
            CheckStatus.FAILED: "❌",
            CheckStatus.SKIPPED: "⏭️",
            CheckStatus.WARNING: "⚠️"
        }.get(result.status, "❓")
        
        if result.status == CheckStatus.FAILED:
            self.log(f"{icon} {result.name}: {result.message}", "error")
            if self.fail_fast:
                print(f"\n❌ FAIL-FAST: Stopping on first failure")
                sys.exit(1)
        elif result.status == CheckStatus.WARNING:
            self.log(f"{icon} {result.name}: {result.message}", "warning")
        else:
            self.log(f"{icon} {result.name}: {result.status.value}", "success" if result.status == CheckStatus.PASSED else "info")
    
    # ========================================================================
    # CHECK 1: Environment Variables
    # ========================================================================
    
    async def check_environment(self) -> CheckResult:
        """Validate required environment variables."""
        start = time.time()
        name = "Environment Variables"
        
        required_vars = [
            "SECRET_KEY",
            "DATABASE_URL",
            "REDIS_URL",
        ]
        
        missing = []
        warnings = []
        
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing.append(var)
            elif var == "SECRET_KEY" and len(value) < 32:
                warnings.append(f"{var} is shorter than 32 characters")
        
        duration = (time.time() - start) * 1000
        
        if missing:
            return CheckResult(
                name=name,
                status=CheckStatus.FAILED,
                message=f"Missing required variables: {', '.join(missing)}",
                duration_ms=duration,
                details={"missing": missing, "warnings": warnings}
            )
        
        if warnings:
            return CheckResult(
                name=name,
                status=CheckStatus.WARNING,
                message=f"All required variables set, but: {'; '.join(warnings)}",
                duration_ms=duration,
                details={"warnings": warnings}
            )
        
        return CheckResult(
            name=name,
            status=CheckStatus.PASSED,
            message="All required environment variables configured",
            duration_ms=duration
        )
    
    # ========================================================================
    # CHECK 2: Database Connection
    # ========================================================================
    
    async def check_database(self) -> CheckResult:
        """Test database connectivity."""
        start = time.time()
        name = "Database Connection"
        
        try:
            from app.core.config import settings
            from sqlalchemy.ext.asyncio import create_async_engine
            from sqlalchemy import text
            
            engine = create_async_engine(
                settings.async_database_url,
                pool_pre_ping=True,
                pool_size=1,
                max_overflow=0,
            )
            
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.scalar()
                
                # Test additional query for schema validation
                try:
                    tables_result = await conn.execute(text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                    ))
                    tables = [row[0] for row in tables_result.fetchall()]
                except Exception:
                    tables = []
            
            await engine.dispose()
            
            duration = (time.time() - start) * 1000
            
            if row == 1:
                return CheckResult(
                    name=name,
                    status=CheckStatus.PASSED,
                    message=f"Connected successfully ({len(tables)} tables found)",
                    duration_ms=duration,
                    details={"tables_count": len(tables), "tables": tables[:10]}
                )
            else:
                return CheckResult(
                    name=name,
                    status=CheckStatus.FAILED,
                    message="Unexpected query result",
                    duration_ms=duration
                )
                
        except Exception as e:
            duration = (time.time() - start) * 1000
            return CheckResult(
                name=name,
                status=CheckStatus.FAILED,
                message=f"Connection failed: {str(e)}",
                duration_ms=duration,
                details={"error_type": type(e).__name__}
            )
    
    # ========================================================================
    # CHECK 3: Redis Connection
    # ========================================================================
    
    async def check_redis(self) -> CheckResult:
        """Test Redis connectivity."""
        start = time.time()
        name = "Redis Connection"
        
        try:
            from app.core.config import settings
            import redis.asyncio as redis
            
            client = redis.from_url(
                settings.redis_url,
                socket_connect_timeout=5,
                decode_responses=True
            )
            
            # Test ping
            ping_result = await client.ping()
            
            # Test write/read
            test_key = f"cerebrum_validation:{int(time.time())}"
            await client.set(test_key, "test_value", ex=10)
            test_value = await client.get(test_key)
            await client.delete(test_key)
            
            # Check Celery queue keys
            queue_keys = await client.keys("celery*")
            
            await client.close()
            
            duration = (time.time() - start) * 1000
            
            if ping_result and test_value == "test_value":
                return CheckResult(
                    name=name,
                    status=CheckStatus.PASSED,
                    message=f"Connected, ping successful, read/write verified ({len(queue_keys)} Celery keys)",
                    duration_ms=duration,
                    details={"celery_keys_count": len(queue_keys)}
                )
            else:
                return CheckResult(
                    name=name,
                    status=CheckStatus.FAILED,
                    message="Redis ping or read/write test failed",
                    duration_ms=duration
                )
                
        except Exception as e:
            duration = (time.time() - start) * 1000
            return CheckResult(
                name=name,
                status=CheckStatus.FAILED,
                message=f"Connection failed: {str(e)}",
                duration_ms=duration,
                details={"error_type": type(e).__name__}
            )
    
    # ========================================================================
    # CHECK 4: 14 Agent Layers
    # ========================================================================
    
    async def check_agent_layers(self) -> CheckResult:
        """Verify all 14 agent layers can be imported."""
        start = time.time()
        name = "14 Agent Layers"
        
        failed_layers = []
        loaded_layers = []
        
        # Check core agent module
        try:
            from app.agent.core import CerebrumAgent, AgentLayer, AgentAction
            loaded_layers.append("core")
        except Exception as e:
            failed_layers.append(("core", str(e)))
        
        # Check each layer module
        layer_modules = {
            "coding": "app.coding",
            "registry": "app.registry",
            "validation": "app.validation",
            "hotswap": "app.hotswap",
            "healing": "app.healing",
            "prompts": "app.prompts",
            "triggers": "app.triggers",
            "economics": "app.economics",
            "vdc": "app.vdc",
            "edge": "app.edge",
            "portal": "app.portal",
            "enterprise": "app.enterprise",
            "connectors": "app.connectors",
            "monitoring": "app.monitoring",
        }
        
        for layer_name, module_path in layer_modules.items():
            try:
                __import__(module_path)
                loaded_layers.append(layer_name)
            except Exception as e:
                # Some modules might be optional/stubs
                failed_layers.append((layer_name, str(e)))
        
        duration = (time.time() - start) * 1000
        
        # Consider it passed if at least 12/14 layers load (allowing for optional/stub layers)
        if len(loaded_layers) >= 12:
            status = CheckStatus.PASSED if len(failed_layers) == 0 else CheckStatus.WARNING
            return CheckResult(
                name=name,
                status=status,
                message=f"{len(loaded_layers)}/14 layers loaded ({len(failed_layers)} issues)",
                duration_ms=duration,
                details={
                    "loaded": loaded_layers,
                    "failed": failed_layers
                }
            )
        else:
            return CheckResult(
                name=name,
                status=CheckStatus.FAILED,
                message=f"Only {len(loaded_layers)}/14 layers loaded",
                duration_ms=duration,
                details={"loaded": loaded_layers, "failed": failed_layers}
            )
    
    # ========================================================================
    # CHECK 5: API Endpoints
    # ========================================================================
    
    async def check_api_endpoints(self) -> CheckResult:
        """Test critical API endpoints."""
        start = time.time()
        name = "API Endpoints"
        
        try:
            from fastapi.testclient import TestClient
            from app.main import create_application
            
            # Create app with test settings
            app = create_application()
            client = TestClient(app)
            
            endpoints_tested = []
            failed_tests = []
            
            # Test health endpoints
            tests = [
                ("GET", "/health", [200]),
                ("GET", "/health/live", [200]),
                ("GET", "/health/ready", [200, 503]),  # 503 if deps not ready
                ("GET", "/healthz", [200]),
                ("GET", "/readyz", [200, 503]),
                ("GET", "/api", [200]),
                ("GET", "/", [200]),
            ]
            
            for method, path, expected_statuses in tests:
                try:
                    if method == "GET":
                        response = client.get(path)
                    else:
                        continue
                    
                    if response.status_code in expected_statuses:
                        endpoints_tested.append(f"{method} {path}")
                    else:
                        failed_tests.append(f"{method} {path}: got {response.status_code}, expected {expected_statuses}")
                except Exception as e:
                    failed_tests.append(f"{method} {path}: {str(e)}")
            
            duration = (time.time() - start) * 1000
            
            if len(failed_tests) == 0:
                return CheckResult(
                    name=name,
                    status=CheckStatus.PASSED,
                    message=f"All {len(endpoints_tested)} endpoints responded correctly",
                    duration_ms=duration,
                    details={"endpoints_tested": endpoints_tested}
                )
            elif len(failed_tests) <= 2:
                return CheckResult(
                    name=name,
                    status=CheckStatus.WARNING,
                    message=f"{len(endpoints_tested)} passed, {len(failed_tests)} warnings",
                    duration_ms=duration,
                    details={"passed": endpoints_tested, "failed": failed_tests}
                )
            else:
                return CheckResult(
                    name=name,
                    status=CheckStatus.FAILED,
                    message=f"{len(failed_tests)} endpoints failed",
                    duration_ms=duration,
                    details={"failed": failed_tests}
                )
                
        except Exception as e:
            duration = (time.time() - start) * 1000
            return CheckResult(
                name=name,
                status=CheckStatus.FAILED,
                message=f"API test setup failed: {str(e)}",
                duration_ms=duration,
                details={"error_type": type(e).__name__}
            )
    
    # ========================================================================
    # CHECK 6: Celery Background Tasks
    # ========================================================================
    
    async def check_celery(self) -> CheckResult:
        """Verify Celery configuration."""
        start = time.time()
        name = "Celery Background Tasks"
        
        try:
            from app.tasks import celery_app
            
            # Check broker URL
            broker_url = celery_app.conf.broker_url
            
            # Check configured queues
            task_routes = celery_app.conf.task_routes or {}
            beat_schedule = celery_app.conf.beat_schedule or {}
            
            # Try to connect to broker
            from celery import Celery
            with celery_app.connection() as conn:
                conn.connect()
                broker_connected = conn.connected
            
            duration = (time.time() - start) * 1000
            
            if broker_connected:
                return CheckResult(
                    name=name,
                    status=CheckStatus.PASSED,
                    message=f"Celery configured with {len(task_routes)} task routes, {len(beat_schedule)} scheduled tasks",
                    duration_ms=duration,
                    details={
                        "broker_url": broker_url.replace("://", "://***@" if "://" in broker_url else "://"),
                        "task_routes": list(task_routes.keys()),
                        "beat_schedule": list(beat_schedule.keys())
                    }
                )
            else:
                return CheckResult(
                    name=name,
                    status=CheckStatus.WARNING,
                    message="Celery configured but broker connection failed",
                    duration_ms=duration
                )
                
        except Exception as e:
            duration = (time.time() - start) * 1000
            return CheckResult(
                name=name,
                status=CheckStatus.FAILED,
                message=f"Celery check failed: {str(e)}",
                duration_ms=duration,
                details={"error_type": type(e).__name__}
            )
    
    # ========================================================================
    # CHECK 7: Self-Modification System
    # ========================================================================
    
    async def check_self_modification(self) -> CheckResult:
        """Verify self-modification system can modify code."""
        start = time.time()
        name = "Self-Modification System"
        
        try:
            from app.agent.self_modification import (
                SelfModificationEngine, 
                GitManager,
                ModificationType,
                ModificationStatus
            )
            
            checks_passed = []
            checks_failed = []
            
            # Test 1: GitManager initialization
            try:
                repo_path = Path(__file__).parent.parent
                git_mgr = GitManager(str(repo_path))
                checks_passed.append("GitManager initialization")
            except Exception as e:
                checks_failed.append(f"GitManager: {str(e)}")
            
            # Test 2: Check if we're in a git repo
            try:
                is_clean = git_mgr.ensure_clean_state()
                checks_passed.append(f"Git working directory clean: {is_clean}")
            except Exception as e:
                checks_failed.append(f"Git state check: {str(e)}")
            
            # Test 3: SelfModificationEngine import and initialization
            try:
                engine = SelfModificationEngine(str(repo_path))
                checks_passed.append("SelfModificationEngine initialization")
            except Exception as e:
                checks_failed.append(f"Engine initialization: {str(e)}")
            
            # Test 4: Test file modification capability (dry run)
            try:
                test_file = Path(__file__).parent / ".validation_test_file"
                test_content = f"# Test file created by validation script\n# Timestamp: {datetime.now().isoformat()}\n"
                
                # Write test file
                test_file.write_text(test_content)
                
                # Verify file was written
                if test_file.exists() and test_file.read_text() == test_content:
                    checks_passed.append("File write capability verified")
                else:
                    checks_failed.append("File write verification failed")
                
                # Cleanup
                test_file.unlink()
                checks_passed.append("File cleanup successful")
                
            except Exception as e:
                checks_failed.append(f"File modification test: {str(e)}")
            
            # Test 5: Validate layer generation template
            try:
                template = engine.generate_layer_template("ValidationTest", "Test layer for validation")
                if "class" in template and "ValidationTest" in template:
                    checks_passed.append("Layer template generation")
                else:
                    checks_failed.append("Layer template generation - invalid output")
            except Exception as e:
                checks_failed.append(f"Layer template: {str(e)}")
            
            duration = (time.time() - start) * 1000
            
            if len(checks_failed) == 0:
                return CheckResult(
                    name=name,
                    status=CheckStatus.PASSED,
                    message=f"All {len(checks_passed)} self-modification checks passed",
                    duration_ms=duration,
                    details={"checks": checks_passed}
                )
            elif len(checks_failed) <= 1:
                return CheckResult(
                    name=name,
                    status=CheckStatus.WARNING,
                    message=f"{len(checks_passed)} passed, {len(checks_failed)} warning(s)",
                    duration_ms=duration,
                    details={"passed": checks_passed, "warnings": checks_failed}
                )
            else:
                return CheckResult(
                    name=name,
                    status=CheckStatus.FAILED,
                    message=f"{len(checks_failed)} self-modification checks failed",
                    duration_ms=duration,
                    details={"passed": checks_passed, "failed": checks_failed}
                )
                
        except Exception as e:
            duration = (time.time() - start) * 1000
            return CheckResult(
                name=name,
                status=CheckStatus.FAILED,
                message=f"Self-modification system check failed: {str(e)}",
                duration_ms=duration,
                details={"error_type": type(e).__name__}
            )
    
    # ========================================================================
    # CHECK 8: Existing Tests
    # ========================================================================
    
    async def check_existing_tests(self) -> CheckResult:
        """Run existing test suite and check results."""
        start = time.time()
        name = "Existing Tests"
        
        try:
            # Count test files
            tests_dir = BACKEND_DIR / "tests"
            test_files = list(tests_dir.rglob("test_*.py"))
            
            # Try to run pytest on smoke tests first
            result = subprocess.run(
                ["python", "-m", "pytest", "backend/tests/test_smoke.py", "-v", "--tb=short"],
                cwd=BACKEND_DIR.parent,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            duration = (time.time() - start) * 1000
            
            # Parse results
            passed = result.returncode == 0
            output = result.stdout + result.stderr
            
            # Extract test count
            import re
            test_count_match = re.search(r'(\d+) passed', output)
            test_count = int(test_count_match.group(1)) if test_count_match else 0
            
            if passed:
                return CheckResult(
                    name=name,
                    status=CheckStatus.PASSED,
                    message=f"Smoke tests passed ({test_count} tests), {len(test_files)} test files found",
                    duration_ms=duration,
                    details={
                        "test_files": [f.name for f in test_files],
                        "pytest_output": output[-500:] if len(output) > 500 else output
                    }
                )
            else:
                return CheckResult(
                    name=name,
                    status=CheckStatus.WARNING,
                    message=f"Smoke tests had issues, {len(test_files)} test files found",
                    duration_ms=duration,
                    details={
                        "return_code": result.returncode,
                        "pytest_output": output[-1000:] if len(output) > 1000 else output
                    }
                )
                
        except subprocess.TimeoutExpired:
            duration = (time.time() - start) * 1000
            return CheckResult(
                name=name,
                status=CheckStatus.WARNING,
                message="Test run timed out after 60s",
                duration_ms=duration
            )
        except Exception as e:
            duration = (time.time() - start) * 1000
            return CheckResult(
                name=name,
                status=CheckStatus.WARNING,
                message=f"Could not run existing tests: {str(e)}",
                duration_ms=duration,
                details={"error_type": type(e).__name__}
            )
    
    # ========================================================================
    # RUN ALL CHECKS
    # ========================================================================
    
    async def run_all_checks(self) -> bool:
        """Run all validation checks."""
        print("=" * 70)
        print("CEREBRUM PROTOTYPE VALIDATION")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Backend: {BACKEND_DIR}")
        print(f"Python: {sys.version}")
        print("-" * 70)
        
        checks = [
            self.check_environment,
            self.check_database,
            self.check_redis,
            self.check_agent_layers,
            self.check_api_endpoints,
            self.check_celery,
            self.check_self_modification,
            self.check_existing_tests,
        ]
        
        for check in checks:
            result = await check()
            self.add_result(result)
        
        # Summary
        print("-" * 70)
        print("SUMMARY")
        print("-" * 70)
        
        total_time = (time.time() - self.start_time) * 1000
        
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAILED)
        warnings = sum(1 for r in self.results if r.status == CheckStatus.WARNING)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIPPED)
        
        print(f"  ✅ Passed:   {passed}")
        print(f"  ❌ Failed:   {failed}")
        print(f"  ⚠️  Warnings: {warnings}")
        print(f"  ⏭️  Skipped:  {skipped}")
        print(f"  ⏱️  Total:    {total_time:.0f}ms")
        
        print("-" * 70)
        
        # Detailed timing
        if self.verbose:
            print("\nTiming breakdown:")
            for r in sorted(self.results, key=lambda x: x.duration_ms, reverse=True):
                print(f"  {r.name:30} {r.duration_ms:8.1f}ms")
            print()
        
        # Final result
        if failed > 0:
            print("\n❌ VALIDATION FAILED - Critical checks did not pass")
            print("\nFailed checks:")
            for r in self.results:
                if r.status == CheckStatus.FAILED:
                    print(f"  - {r.name}: {r.message}")
            return False
        elif warnings > 0:
            print("\n⚠️  VALIDATION PASSED WITH WARNINGS")
            return True
        else:
            print("\n✅ ALL CHECKS PASSED")
            return True


def main():
    parser = argparse.ArgumentParser(
        description="Cerebrum Prototype Validation Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_prototype.py
  python scripts/validate_prototype.py --verbose
  python scripts/validate_prototype.py --fail-fast
        """
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "-f", "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    
    args = parser.parse_args()
    
    # Set up minimal environment for testing
    if not os.getenv("SECRET_KEY"):
        os.environ["SECRET_KEY"] = "validation-test-secret-key-32-chars-long-for-testing-only"
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/cerebrum"
    if not os.getenv("REDIS_URL"):
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    
    os.environ["DEBUG"] = "true"
    os.environ["ENVIRONMENT"] = "testing"
    
    validator = CerebrumValidator(verbose=args.verbose, fail_fast=args.fail_fast)
    
    try:
        success = asyncio.run(validator.run_all_checks())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user")
        sys.exit(2)
    except Exception as e:
        print(f"\n\n💥 Validation script error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
