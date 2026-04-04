"""
Validation Pipeline Orchestration

Coordinates sandbox execution, security scanning, and test generation.
"""
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from .sandbox import DockerSandbox, SandboxResult
from .security_scan import SecurityScanner, SecurityScanResult
from .integration_test import TestGenerator, TestGenerationResult, TestRunner

logger = logging.getLogger(__name__)


class ValidationStage(str, Enum):
    """Stages in the validation pipeline."""
    SYNTAX_CHECK = "syntax_check"
    SECURITY_SCAN = "security_scan"
    SANDBOX_EXECUTION = "sandbox_execution"
    TEST_GENERATION = "test_generation"
    TEST_EXECUTION = "test_execution"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ValidationResult:
    """Complete validation result."""
    capability_id: str
    success: bool
    stage: ValidationStage
    syntax_valid: bool
    security_passed: bool
    sandbox_passed: bool
    tests_passed: bool
    
    syntax_errors: List[str] = field(default_factory=list)
    security_issues: List[Dict] = field(default_factory=list)
    sandbox_result: Optional[SandboxResult] = None
    test_result: Optional[TestGenerationResult] = None
    test_execution: Optional[Dict] = None
    
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "capability_id": self.capability_id,
            "success": self.success,
            "stage": self.stage.value,
            "syntax_valid": self.syntax_valid,
            "security_passed": self.security_passed,
            "sandbox_passed": self.sandbox_passed,
            "tests_passed": self.tests_passed,
            "syntax_errors": self.syntax_errors,
            "security_issues": self.security_issues,
            "sandbox_result": {
                "success": self.sandbox_result.success if self.sandbox_result else None,
                "exit_code": self.sandbox_result.exit_code if self.sandbox_result else None,
                "execution_time_ms": self.sandbox_result.execution_time_ms if self.sandbox_result else None
            },
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms
        }


class ValidationPipeline:
    """
    Orchestrates the complete validation pipeline.
    
    Pipeline stages:
    1. Syntax check
    2. Security scan (Bandit, Semgrep, ESLint)
    3. Sandbox execution
    4. Test generation
    5. Test execution
    """
    
    def __init__(self):
        self.sandbox = DockerSandbox()
        self.security_scanner = SecurityScanner()
        self.test_generator = TestGenerator()
        self.test_runner = TestRunner()
    
    async def validate(
        self,
        capability_id: str,
        code: str,
        language: str = "python",
        run_tests: bool = True,
        skip_sandbox: bool = False
    ) -> ValidationResult:
        """
        Run complete validation pipeline.
        
        Args:
            capability_id: ID of the capability being validated
            code: Code to validate
            language: Programming language
            run_tests: Whether to generate and run tests
            skip_sandbox: Skip sandbox execution (for faster validation)
        
        Returns:
            ValidationResult with complete results
        """
        start_time = datetime.utcnow()
        
        result = ValidationResult(
            capability_id=capability_id,
            success=False,
            stage=ValidationStage.SYNTAX_CHECK,
            syntax_valid=False,
            security_passed=False,
            sandbox_passed=False,
            tests_passed=False
        )
        
        try:
            # Stage 1: Syntax Check
            logger.info(f"[{capability_id}] Stage 1: Syntax check")
            syntax_errors = self.sandbox.validate_syntax(code, language)
            result.syntax_errors = syntax_errors
            result.syntax_valid = len(syntax_errors) == 0
            
            if not result.syntax_valid:
                result.stage = ValidationStage.FAILED
                logger.error(f"[{capability_id}] Syntax check failed")
                return self._finalize_result(result, start_time)
            
            # Stage 2: Security Scan
            logger.info(f"[{capability_id}] Stage 2: Security scan")
            result.stage = ValidationStage.SECURITY_SCAN
            security_result = self.security_scanner.scan(code, language)
            result.security_issues = [
                {
                    "tool": issue.tool,
                    "rule_id": issue.rule_id,
                    "message": issue.message,
                    "severity": issue.severity.value,
                    "line": issue.line
                }
                for issue in security_result.issues
            ]
            result.security_passed = security_result.passed
            
            if not result.security_passed:
                logger.warning(f"[{capability_id}] Security scan found issues")
                # Continue but mark as warning
            
            # Stage 3: Sandbox Execution
            if not skip_sandbox:
                logger.info(f"[{capability_id}] Stage 3: Sandbox execution")
                result.stage = ValidationStage.SANDBOX_EXECUTION
                sandbox_result = self.sandbox.execute_python(code)
                result.sandbox_result = sandbox_result
                result.sandbox_passed = sandbox_result.success
                
                if not result.sandbox_passed:
                    result.stage = ValidationStage.FAILED
                    logger.error(f"[{capability_id}] Sandbox execution failed")
                    return self._finalize_result(result, start_time)
            else:
                result.sandbox_passed = True
            
            # Stage 4: Test Generation
            if run_tests:
                logger.info(f"[{capability_id}] Stage 4: Test generation")
                result.stage = ValidationStage.TEST_GENERATION
                test_result = self.test_generator.generate_from_code(code, language)
                result.test_result = test_result
                
                if not test_result.success:
                    logger.warning(f"[{capability_id}] Test generation failed")
                    result.tests_passed = False
                else:
                    # Stage 5: Test Execution
                    logger.info(f"[{capability_id}] Stage 5: Test execution")
                    result.stage = ValidationStage.TEST_EXECUTION
                    test_execution = self.test_runner.run_tests(test_result.test_code)
                    result.test_execution = test_execution
                    result.tests_passed = test_execution.get("passed", False)
            
            # Mark as successful
            result.success = (
                result.syntax_valid and 
                result.security_passed and 
                result.sandbox_passed and
                (not run_tests or result.tests_passed)
            )
            result.stage = ValidationStage.COMPLETED if result.success else ValidationStage.FAILED
            
            return self._finalize_result(result, start_time)
        
        except Exception as e:
            logger.error(f"[{capability_id}] Validation error: {e}")
            result.stage = ValidationStage.FAILED
            return self._finalize_result(result, start_time)
    
    def _finalize_result(
        self, 
        result: ValidationResult, 
        start_time: datetime
    ) -> ValidationResult:
        """Finalize validation result with timing."""
        result.completed_at = datetime.utcnow()
        result.duration_ms = (result.completed_at - start_time).total_seconds() * 1000
        return result
    
    async def validate_batch(
        self,
        capabilities: List[Dict[str, str]]
    ) -> List[ValidationResult]:
        """
        Validate multiple capabilities in parallel.
        
        Args:
            capabilities: List of dicts with 'id', 'code', 'language'
        
        Returns:
            List of ValidationResults
        """
        tasks = [
            self.validate(
                capability_id=c["id"],
                code=c["code"],
                language=c.get("language", "python")
            )
            for c in capabilities
        ]
        
        return await asyncio.gather(*tasks)
    
    def quick_validate(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Quick validation (syntax + security only).
        
        Returns:
            Quick validation results
        """
        # Syntax check
        syntax_errors = self.sandbox.validate_syntax(code, language)
        
        # Security scan
        security_result = self.security_scanner.scan(code, language)
        
        return {
            "valid": len(syntax_errors) == 0 and security_result.passed,
            "syntax_valid": len(syntax_errors) == 0,
            "syntax_errors": syntax_errors,
            "security_passed": security_result.passed,
            "security_issues_count": len(security_result.issues),
            "security_summary": security_result.summary
        }


# Singleton instance
validation_pipeline = ValidationPipeline()
