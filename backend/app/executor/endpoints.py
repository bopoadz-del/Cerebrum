"""
Formula Executor API Endpoints

REST API for:
- Executing formulas by ID
- Natural language formula execution
- Listing available formulas
- Execution history and audit
- Sandbox health checks
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.core.security import get_current_user, get_current_user_optional
from app.models.user import User
from app.core.logging import get_logger

from app.executor.executor_service import (
    FormulaExecutorService,
    FormulaTemplate,
    ExecutionResult,
    get_formula_executor,
    reset_formula_executor,
    FormulaType,
    CONSTRUCTION_FORMULAS,
)
from app.executor.sandbox import (
    DockerSandbox,
    SandboxConfig,
    get_sandbox,
    execute_code_safely,
)
from app.executor.models import (
    FormulaExecutionLog,
    FormulaAuditLogger,
    get_formula_audit_logger,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/executor", tags=["Formula Executor"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class FormulaInputSchema(BaseModel):
    """Input parameter for formula execution."""
    name: str
    value: Any
    unit: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class FormulaOutputSchema(BaseModel):
    """Output from formula execution."""
    name: str
    value: Any
    unit: str = ""
    formula_used: str = ""


class CredibilitySchema(BaseModel):
    """Credibility score details."""
    score: float = Field(..., ge=0.0, le=1.0)
    level: str  # high, medium, low, uncertain
    factors: List[Dict[str, Any]] = []


class FormulaExecuteRequest(BaseModel):
    """Request to execute a formula by ID."""
    formula_id: str = Field(..., description="ID of the formula to execute")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Input values")
    timeout: int = Field(default=30, ge=1, le=300, description="Execution timeout (seconds)")


class FormulaExecuteResponse(BaseModel):
    """Response from formula execution."""
    execution_id: str
    formula_id: str
    formula_type: str
    status: str  # success, error, timeout, security_violation
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    credibility: CredibilitySchema
    execution_time_ms: float
    timestamp: str
    error_message: Optional[str] = None
    audit_log_id: Optional[str] = None


class NaturalLanguageExecuteRequest(BaseModel):
    """Request to execute formula from natural language."""
    text: str = Field(..., min_length=1, max_length=5000, description="Natural language description")
    auto_select: bool = Field(default=True, description="Automatically select best formula")


class NaturalLanguageExecuteResponse(BaseModel):
    """Response from natural language formula execution."""
    execution_id: str
    parsed: Dict[str, Any]  # Parsing results
    result: Optional[FormulaExecuteResponse] = None
    error: Optional[str] = None


class FormulaListItem(BaseModel):
    """Formula item in list response."""
    id: str
    name: str
    formula_type: str
    description: str
    required_inputs: List[Dict[str, Any]]
    output_unit: str
    references: List[str]
    tags: List[str]


class FormulaListResponse(BaseModel):
    """Response listing available formulas."""
    formulas: List[FormulaListItem]
    total: int
    types: List[str]


class FormulaDetailResponse(BaseModel):
    """Detailed formula information."""
    id: str
    name: str
    formula_type: str
    description: str
    expression: str
    required_inputs: List[Dict[str, Any]]
    output_unit: str
    references: List[str]
    tags: List[str]
    example: Optional[Dict[str, Any]] = None


class SandboxExecuteRequest(BaseModel):
    """Request to execute arbitrary Python code in sandbox."""
    code: str = Field(..., min_length=1, max_length=10000, description="Python code to execute")
    context: Dict[str, Any] = Field(default_factory=dict, description="Variables to inject")
    timeout: int = Field(default=30, ge=1, le=300)


class SandboxExecuteResponse(BaseModel):
    """Response from sandbox code execution."""
    success: bool
    status: str
    result: Optional[Any] = None
    output: str = ""
    error: Optional[str] = None
    execution_time_ms: float
    timeout_reached: bool = False
    security_violations: List[str] = []


class ExecutionHistoryItem(BaseModel):
    """Item in execution history."""
    execution_id: str
    formula_id: str
    formula_type: str
    formula_name: Optional[str]
    status: str
    credibility_score: float
    execution_time_ms: float
    executed_at: str
    source: str


class ExecutionHistoryResponse(BaseModel):
    """Response for execution history."""
    executions: List[ExecutionHistoryItem]
    total: int
    page: int
    page_size: int


class ExecutionStatsResponse(BaseModel):
    """Execution statistics response."""
    total_executions: int
    successful: int
    failed: int
    success_rate: float
    average_credibility: float
    average_execution_time_ms: float
    by_formula_type: Dict[str, int]


class SandboxHealthResponse(BaseModel):
    """Sandbox health check response."""
    docker_available: bool
    image_available: bool
    can_execute: bool
    last_check: str


# =============================================================================
# Dependency Injection
# =============================================================================

async def get_executor(
    db: AsyncSession = Depends(get_async_session)
) -> FormulaExecutorService:
    """Get formula executor service with dependencies."""
    audit_logger = get_formula_audit_logger()
    
    # Try to get sandbox
    try:
        sandbox = await get_sandbox()
    except Exception as e:
        logger.warning(f"Sandbox not available: {e}")
        sandbox = None
    
    return get_formula_executor(sandbox_client=sandbox, audit_logger=audit_logger)


# =============================================================================
# API Endpoints
# =============================================================================

@router.get(
    "/formulas",
    response_model=FormulaListResponse,
    summary="List available formulas",
    description="Get a list of all available construction formulas with metadata.",
)
async def list_formulas(
    formula_type: Optional[str] = Query(None, description="Filter by formula type (concrete, rebar, cost, etc.)"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    executor: FormulaExecutorService = Depends(get_executor),
) -> FormulaListResponse:
    """
    List all available construction formulas.
    
    Optionally filter by formula type or tag.
    """
    # Convert string to enum if provided
    type_filter = None
    if formula_type:
        try:
            type_filter = FormulaType(formula_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid formula type: {formula_type}. Valid types: {[t.value for t in FormulaType]}"
            )
    
    tags_filter = [tag] if tag else None
    
    formulas = executor.get_available_formulas(
        formula_type=type_filter,
        tags=tags_filter
    )
    
    # Get unique types
    all_types = sorted(set(f.formula_type.value for f in CONSTRUCTION_FORMULAS.values()))
    
    return FormulaListResponse(
        formulas=[
            FormulaListItem(
                id=f.id,
                name=f.name,
                formula_type=f.formula_type.value,
                description=f.description,
                required_inputs=f.required_inputs,
                output_unit=f.output_unit,
                references=f.references,
                tags=f.tags,
            )
            for f in formulas
        ],
        total=len(formulas),
        types=all_types,
    )


@router.get(
    "/formulas/{formula_id}",
    response_model=FormulaDetailResponse,
    summary="Get formula details",
    description="Get detailed information about a specific formula including example usage.",
)
async def get_formula_details(
    formula_id: str,
    executor: FormulaExecutorService = Depends(get_executor),
) -> FormulaDetailResponse:
    """
    Get detailed information about a specific formula.
    """
    formula = executor.get_formula(formula_id)
    
    if not formula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Formula not found: {formula_id}"
        )
    
    # Generate example
    example_inputs = {}
    for inp in formula.required_inputs:
        if "default" in inp:
            example_inputs[inp["name"]] = inp["default"]
        elif inp["type"] == "float":
            example_inputs[inp["name"]] = 1.0
        else:
            example_inputs[inp["name"]] = "example"
    
    example = {
        "inputs": example_inputs,
        "description": f"Calculate {formula.name.lower()} using provided dimensions"
    }
    
    return FormulaDetailResponse(
        id=formula.id,
        name=formula.name,
        formula_type=formula.formula_type.value,
        description=formula.description,
        expression=formula.expression,
        required_inputs=formula.required_inputs,
        output_unit=formula.output_unit,
        references=formula.references,
        tags=formula.tags,
        example=example,
    )


@router.post(
    "/execute",
    response_model=FormulaExecuteResponse,
    summary="Execute formula by ID",
    description="Execute a construction formula with the provided input values.",
    status_code=status.HTTP_200_OK,
)
async def execute_formula(
    request: FormulaExecuteRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user_optional),
    executor: FormulaExecutorService = Depends(get_executor),
    http_request: Request = None,
) -> FormulaExecuteResponse:
    """
    Execute a formula by ID with provided inputs.
    
    Example:
    ```json
    {
        "formula_id": "concrete_volume",
        "inputs": {
            "length": 10.0,
            "width": 5.0,
            "depth": 0.3
        }
    }
    ```
    
    Returns execution result with credibility score and audit trail ID.
    """
    try:
        # Generate request ID for tracing
        request_id = str(getattr(http_request, 'state', {}).get('request_id', '')) if http_request else None
        
        # Execute formula
        result = await executor.execute_formula(
            formula_id=request.formula_id,
            inputs=request.inputs,
            user_id=str(current_user.id) if current_user else None,
            request_id=request_id,
            source="api"
        )
        
        # Convert to response model
        return FormulaExecuteResponse(
            execution_id=result.execution_id,
            formula_id=result.formula_id,
            formula_type=result.formula_type.value,
            status=result.status.value,
            inputs=[
                {"name": inp.name, "value": inp.value, "unit": inp.unit, "confidence": inp.confidence}
                for inp in result.inputs
            ],
            outputs=[
                {"name": out.name, "value": out.value, "unit": out.unit, "formula_used": out.formula_used}
                for out in result.outputs
            ],
            credibility=CredibilitySchema(
                score=result.credibility.score,
                level=result.credibility.level.value,
                factors=result.credibility.factors,
            ),
            execution_time_ms=result.execution_time_ms,
            timestamp=result.timestamp.isoformat(),
            error_message=result.error_message,
            audit_log_id=result.audit_log_id,
        )
        
    except Exception as e:
        logger.error(f"Formula execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Formula execution failed: {str(e)}"
        )


@router.post(
    "/execute/natural-language",
    response_model=NaturalLanguageExecuteResponse,
    summary="Execute from natural language",
    description="Parse natural language and execute appropriate formula.",
)
async def execute_natural_language(
    request: NaturalLanguageExecuteRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    executor: FormulaExecutorService = Depends(get_executor),
    http_request: Request = None,
) -> NaturalLanguageExecuteResponse:
    """
    Execute formula from natural language description.
    
    Example:
    ```json
    {
        "text": "Calculate concrete volume for 10m x 5m x 0.3m slab"
    }
    ```
    
    The system will:
    1. Parse the text to detect formula type
    2. Extract dimensions and parameters
    3. Select appropriate formula
    4. Execute and return results with credibility
    """
    try:
        # Parse the request
        parsed = executor.parser.parse_formula_request(request.text)
        
        if not parsed.get("formula_type"):
            return NaturalLanguageExecuteResponse(
                execution_id=str(__import__('uuid').uuid4()),
                parsed=parsed,
                error="Could not determine formula type from input. Try to be more specific (e.g., 'concrete volume', 'rebar weight')."
            )
        
        # Generate request ID
        request_id = str(getattr(http_request, 'state', {}).get('request_id', '')) if http_request else None
        
        # Execute
        result = await executor.execute_natural_language(
            text=request.text,
            user_id=str(current_user.id) if current_user else None,
            request_id=request_id
        )
        
        # Convert to response
        return NaturalLanguageExecuteResponse(
            execution_id=result.execution_id,
            parsed=parsed,
            result=FormulaExecuteResponse(
                execution_id=result.execution_id,
                formula_id=result.formula_id,
                formula_type=result.formula_type.value,
                status=result.status.value,
                inputs=[
                    {"name": inp.name, "value": inp.value, "unit": inp.unit, "confidence": inp.confidence}
                    for inp in result.inputs
                ],
                outputs=[
                    {"name": out.name, "value": out.value, "unit": out.unit, "formula_used": out.formula_used}
                    for out in result.outputs
                ],
                credibility=CredibilitySchema(
                    score=result.credibility.score,
                    level=result.credibility.level.value,
                    factors=result.credibility.factors,
                ),
                execution_time_ms=result.execution_time_ms,
                timestamp=result.timestamp.isoformat(),
                error_message=result.error_message,
                audit_log_id=result.audit_log_id,
            ) if result else None,
            error=result.error_message if result and result.error_message else None,
        )
        
    except Exception as e:
        logger.error(f"Natural language execution failed: {e}", exc_info=True)
        return NaturalLanguageExecuteResponse(
            execution_id=str(__import__('uuid').uuid4()),
            parsed={},
            error=f"Execution failed: {str(e)}"
        )


@router.post(
    "/sandbox/execute",
    response_model=SandboxExecuteResponse,
    summary="Execute code in sandbox",
    description="Execute arbitrary Python code in isolated sandbox environment.",
)
async def execute_sandbox_code(
    request: SandboxExecuteRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> SandboxExecuteResponse:
    """
    Execute Python code safely in a sandboxed environment.
    
    Security features:
    - Code security scanning
    - Restricted imports
    - Resource limits (CPU, memory)
    - Timeout enforcement
    - No network access (by default)
    
    Allowed libraries: math, numpy, pandas, matplotlib, scipy
    
    Example:
    ```json
    {
        "code": "import math\nresult = math.pi * (5 ** 2)",
        "timeout": 30
    }
    ```
    """
    try:
        result = await execute_code_safely(
            code=request.code,
            context=request.context,
            timeout=request.timeout
        )
        
        return SandboxExecuteResponse(
            success=result.success,
            status=result.status.value,
            result=result.result,
            output=result.output,
            error=result.error,
            execution_time_ms=result.execution_time_ms,
            timeout_reached=result.timeout_reached,
            security_violations=result.security_violations,
        )
        
    except Exception as e:
        logger.error(f"Sandbox execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sandbox execution failed: {str(e)}"
        )


@router.get(
    "/history",
    response_model=ExecutionHistoryResponse,
    summary="Get execution history",
    description="Get history of formula executions for current user.",
)
async def get_execution_history(
    formula_type: Optional[str] = Query(None, description="Filter by formula type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> ExecutionHistoryResponse:
    """
    Get execution history for the current user.
    
    Shows formulas you've executed with results and credibility scores.
    """
    audit_logger = get_formula_audit_logger()
    
    entries = await audit_logger.get_execution_history(
        user_id=current_user.id,
        formula_type=formula_type,
        status=status,
        limit=limit,
        offset=offset,
        db_session=db
    )
    
    # Get total count
    from sqlalchemy import func, select
    count_query = select(func.count()).select_from(FormulaExecutionLog)
    count_query = count_query.where(FormulaExecutionLog.user_id == current_user.id)
    if formula_type:
        count_query = count_query.where(FormulaExecutionLog.formula_type == formula_type)
    if status:
        count_query = count_query.where(FormulaExecutionLog.status == status)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return ExecutionHistoryResponse(
        executions=[
            ExecutionHistoryItem(
                execution_id=entry.execution_id,
                formula_id=entry.formula_id,
                formula_type=entry.formula_type,
                formula_name=entry.formula_name,
                status=entry.status,
                credibility_score=entry.credibility_score,
                execution_time_ms=entry.execution_time_ms,
                executed_at=entry.executed_at.isoformat() if entry.executed_at else "",
                source=entry.source,
            )
            for entry in entries
        ],
        total=total,
        page=offset // limit + 1,
        page_size=limit,
    )


@router.get(
    "/stats",
    response_model=ExecutionStatsResponse,
    summary="Get execution statistics",
    description="Get aggregate statistics about formula executions.",
)
async def get_execution_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
) -> ExecutionStatsResponse:
    """
    Get execution statistics for the current user.
    
    Shows aggregate metrics like success rate, average credibility, etc.
    """
    audit_logger = get_formula_audit_logger()
    
    from datetime import timedelta
    start_date = datetime.utcnow() - timedelta(days=days)
    
    stats = await audit_logger.get_execution_stats(
        user_id=current_user.id,
        start_date=start_date,
        db_session=db
    )
    
    return ExecutionStatsResponse(**stats)


@router.get(
    "/sandbox/health",
    response_model=SandboxHealthResponse,
    summary="Sandbox health check",
    description="Check sandbox environment health and availability.",
)
async def check_sandbox_health() -> SandboxHealthResponse:
    """
    Check if the sandbox execution environment is healthy.
    
    Returns Docker availability and image status.
    """
    try:
        sandbox = DockerSandbox()
        docker_available = sandbox.is_docker_available()
        
        image_available = False
        if docker_available:
            image_available = await sandbox.validate_image()
        
        return SandboxHealthResponse(
            docker_available=docker_available,
            image_available=image_available,
            can_execute=docker_available or True,  # Can always fall back to local
            last_check=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Sandbox health check failed: {e}")
        return SandboxHealthResponse(
            docker_available=False,
            image_available=False,
            can_execute=True,  # Fallback available
            last_check=datetime.utcnow().isoformat(),
        )


@router.post(
    "/sandbox/rebuild",
    response_model=Dict[str, Any],
    summary="Rebuild sandbox image",
    description="Rebuild the Docker sandbox image. Admin only.",
)
async def rebuild_sandbox_image(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Rebuild the Docker sandbox image.
    
    Requires admin privileges.
    """
    # Check admin (simplified - would check actual admin role)
    if not getattr(current_user, 'is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    try:
        sandbox = DockerSandbox()
        success = await sandbox.build_image()
        
        if success:
            return {
                "success": True,
                "message": "Sandbox image rebuilt successfully",
                "image_name": sandbox.image_name,
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to build sandbox image"
            )
            
    except Exception as e:
        logger.error(f"Sandbox rebuild failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rebuild failed: {str(e)}"
        )
