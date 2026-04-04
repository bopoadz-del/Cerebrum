"""
Validation Pipeline Module

Coordinates sandbox execution, security scanning, and test generation.
"""

# Try to import docker-dependent modules, provide stubs if unavailable
try:
    from .sandbox import DockerSandbox, SandboxResult, SandboxManager
    from .security_scan import (
        SecurityScanner,
        SecurityScanResult,
        SecurityIssue,
        Severity,
        BanditScanner,
        SemgrepScanner,
        ESLintScanner
    )
    from .integration_test import (
        TestGenerator,
        TestGenerationResult,
        TestCase,
        TestRunner
    )
    from .pipeline import (
        ValidationPipeline,
        ValidationResult,
        ValidationStage,
        validation_pipeline
    )
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    # Define stub classes for when docker is unavailable
    class DockerSandbox:
        def __init__(self, *args, **kwargs):
            raise ImportError("Docker is not available. Install docker package to use sandbox features.")
    class SandboxResult:
        pass
    class SandboxManager:
        def __init__(self, *args, **kwargs):
            raise ImportError("Docker is not available. Install docker package to use sandbox features.")
    class SecurityScanner:
        pass
    class SecurityScanResult:
        pass
    class SecurityIssue:
        pass
    class Severity:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"
    class BanditScanner:
        pass
    class SemgrepScanner:
        pass
    class ESLintScanner:
        pass
    class TestGenerator:
        pass
    class TestGenerationResult:
        pass
    class TestCase:
        pass
    class TestRunner:
        pass
    class ValidationPipeline:
        pass
    class ValidationResult:
        pass
    class ValidationStage:
        pass
    validation_pipeline = None

__all__ = [
    # Sandbox
    "DockerSandbox",
    "SandboxResult",
    "SandboxManager",
    # Security Scan
    "SecurityScanner",
    "SecurityScanResult",
    "SecurityIssue",
    "Severity",
    "BanditScanner",
    "SemgrepScanner",
    "ESLintScanner",
    # Integration Test
    "TestGenerator",
    "TestGenerationResult",
    "TestCase",
    "TestRunner",
    # Pipeline
    "ValidationPipeline",
    "ValidationResult",
    "ValidationStage",
    "validation_pipeline"
]
