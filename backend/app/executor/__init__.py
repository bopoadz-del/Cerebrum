"""
Formula Executor Module

Provides secure, sandboxed formula execution for construction calculations.

Components:
- executor_service: Main formula execution logic with credibility scoring
- sandbox: Docker-based isolated code execution
- models: Database models for audit logging
- endpoints: FastAPI REST API endpoints

Usage:
    from app.executor import get_formula_executor
    
    executor = get_formula_executor()
    result = await executor.execute_formula(
        formula_id="concrete_volume",
        inputs={"length": 10, "width": 5, "depth": 0.3}
    )
"""

from app.executor.executor_service import (
    FormulaExecutorService,
    FormulaTemplate,
    FormulaInput,
    FormulaOutput,
    ExecutionResult,
    ExecutionStatus,
    FormulaType,
    CredibilityScore,
    CredibilityLevel,
    get_formula_executor,
    reset_formula_executor,
    CONSTRUCTION_FORMULAS,
    FormulaParser,
    CredibilityScorer,
)

from app.executor.sandbox import (
    DockerSandbox,
    ProcessSandbox,
    SandboxResult,
    SandboxConfig,
    SandboxStatus,
    SecurityScanner,
    get_sandbox,
    execute_code_safely,
)

from app.executor.models import (
    FormulaExecutionLog,
    FormulaAuditLogger,
    get_formula_audit_logger,
)

__all__ = [
    # Service classes
    "FormulaExecutorService",
    "FormulaTemplate",
    "FormulaInput",
    "FormulaOutput",
    "ExecutionResult",
    "ExecutionStatus",
    "FormulaType",
    "CredibilityScore",
    "CredibilityLevel",
    "FormulaParser",
    "CredibilityScorer",
    
    # Sandbox classes
    "DockerSandbox",
    "ProcessSandbox",
    "SandboxResult",
    "SandboxConfig",
    "SandboxStatus",
    "SecurityScanner",
    
    # Model classes
    "FormulaExecutionLog",
    "FormulaAuditLogger",
    
    # Functions
    "get_formula_executor",
    "reset_formula_executor",
    "get_sandbox",
    "execute_code_safely",
    "get_formula_audit_logger",
    
    # Constants
    "CONSTRUCTION_FORMULAS",
]
