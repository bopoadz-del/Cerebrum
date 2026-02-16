"""
Formula API Endpoints

Provides REST API for:
- Listing available formulas
- Getting formula definitions
- Evaluating formulas with inputs
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.formula_runtime import (
    FormulaDefinition,
    evaluate_formula_by_id,
    get_formulas,
    get_formula_by_id,
)

router = APIRouter(prefix="/formulas", tags=["Formulas"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class FormulaInputSchema(BaseModel):
    """Formula input parameter schema."""
    name: str
    type: str = "float"
    unit: str = ""
    required: bool = True
    description: str = ""


class FormulaOutputSchema(BaseModel):
    """Formula output parameter schema."""
    name: str
    type: str = "float"
    unit: str = ""


class FormulaDefinitionSchema(BaseModel):
    """Formula definition response schema."""
    id: str
    name: str
    domain: str
    description: str
    inputs: List[FormulaInputSchema]
    outputs: List[FormulaOutputSchema]
    references: List[str] = []
    tags: List[str] = []
    version: str = "1.0.0"


class FormulaListResponse(BaseModel):
    """Response for listing formulas."""
    formulas: List[FormulaDefinitionSchema]
    total: int
    domains: List[str]


class FormulaEvalRequest(BaseModel):
    """Request to evaluate a formula."""
    formula_id: str = Field(..., description="ID of the formula to evaluate")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Input values")


class FormulaEvalResponse(BaseModel):
    """Response from formula evaluation."""
    formula_id: str
    success: bool
    output_values: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =============================================================================
# API Endpoints
# =============================================================================

@router.get(
    "",
    response_model=FormulaListResponse,
    summary="List all formulas",
    description="Get a list of all available formulas with their metadata.",
)
async def list_formulas(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
) -> FormulaListResponse:
    """
    List all available formulas.
    
    Optionally filter by domain or tag.
    """
    formulas = get_formulas()
    
    # Apply filters
    if domain:
        formulas = [f for f in formulas if f.domain == domain]
    if tag:
        formulas = [f for f in formulas if tag in f.tags]
    
    # Get unique domains
    domains = sorted(set(f.domain for f in formulas))
    
    return FormulaListResponse(
        formulas=[_to_schema(f) for f in formulas],
        total=len(formulas),
        domains=domains,
    )


@router.get(
    "/{formula_id}",
    response_model=FormulaDefinitionSchema,
    summary="Get formula by ID",
    description="Get detailed information about a specific formula.",
)
async def get_formula(formula_id: str) -> FormulaDefinitionSchema:
    """
    Get a specific formula by its ID.
    """
    formula = get_formula_by_id(formula_id)
    
    if formula is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Formula not found: {formula_id}",
        )
    
    return _to_schema(formula)


@router.post(
    "/eval",
    response_model=FormulaEvalResponse,
    summary="Evaluate a formula",
    description="Evaluate a formula with the provided input values.",
)
async def evaluate_formula(request: FormulaEvalRequest) -> FormulaEvalResponse:
    """
    Evaluate a formula with input values.
    
    Example:
    ```json
    {
        "formula_id": "concrete_volume",
        "inputs": {
            "length": 10.0,
            "width": 5.0,
            "height": 0.3
        }
    }
    ```
    """
    result = evaluate_formula_by_id(request.formula_id, request.inputs)
    
    if "error" in result and result.get("output_values") is None:
        return FormulaEvalResponse(
            formula_id=request.formula_id,
            success=False,
            error=result["error"],
        )
    
    return FormulaEvalResponse(
        formula_id=request.formula_id,
        success=True,
        output_values=result.get("output_values"),
        error=result.get("error"),
    )


@router.post(
    "/{formula_id}/eval",
    response_model=FormulaEvalResponse,
    summary="Evaluate formula by ID (path)",
    description="Evaluate a specific formula using its ID in the path.",
)
async def evaluate_formula_by_path(
    formula_id: str,
    inputs: Dict[str, Any],
) -> FormulaEvalResponse:
    """
    Evaluate a specific formula by ID with input values.
    
    Example:
    ```json
    {
        "length": 10.0,
        "width": 5.0,
        "height": 0.3
    }
    ```
    """
    # Verify formula exists
    formula = get_formula_by_id(formula_id)
    if formula is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Formula not found: {formula_id}",
        )
    
    result = evaluate_formula_by_id(formula_id, inputs)
    
    if "error" in result and result.get("output_values") is None:
        return FormulaEvalResponse(
            formula_id=formula_id,
            success=False,
            error=result["error"],
        )
    
    return FormulaEvalResponse(
        formula_id=formula_id,
        success=True,
        output_values=result.get("output_values"),
        error=result.get("error"),
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _to_schema(formula: FormulaDefinition) -> FormulaDefinitionSchema:
    """Convert FormulaDefinition to Pydantic schema."""
    return FormulaDefinitionSchema(
        id=formula.id,
        name=formula.name,
        domain=formula.domain,
        description=formula.description,
        inputs=[
            FormulaInputSchema(
                name=inp.name,
                type=inp.type,
                unit=inp.unit,
                required=inp.required,
                description=inp.description,
            )
            for inp in formula.inputs
        ],
        outputs=[
            FormulaOutputSchema(
                name=out.name,
                type=out.type,
                unit=out.unit,
            )
            for out in formula.outputs
        ],
        references=formula.references,
        tags=formula.tags,
        version=formula.version,
    )
