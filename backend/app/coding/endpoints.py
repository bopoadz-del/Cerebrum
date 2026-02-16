"""
Code Generation Endpoints

FastAPI endpoints for AI-powered code generation.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .generator import CodeGenerator, GenerationResult
from .prompts import PromptLibrary
from ..registry.models import CapabilityCreate, CapabilityType
from ..registry.crud import CapabilityCRUD
from ..database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/generate", tags=["code-generation"])


# ============ Request/Response Models ============

class GenerateRequest(BaseModel):
    """Request for code generation."""
    request: str = Field(..., min_length=5, description="Natural language request")
    capability_type: CapabilityType = CapabilityType.API_ENDPOINT
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    author: str = Field(..., description="Author of the request")


class GenerateResponse(BaseModel):
    """Response from code generation."""
    success: bool
    capability_id: Optional[str] = None
    code: Optional[str] = None
    language: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = 0
    message: str = ""


class RefineRequest(BaseModel):
    """Request for code refinement."""
    capability_id: str
    feedback: str = Field(..., min_length=5)


class ExplainRequest(BaseModel):
    """Request for code explanation."""
    code: str = Field(..., min_length=10)


class ExplainResponse(BaseModel):
    """Response with code explanation."""
    success: bool
    explanation: str = ""
    key_components: list = Field(default_factory=list)
    security_considerations: list = Field(default_factory=list)


# ============ Endpoints ============

@router.post("", response_model=GenerateResponse)
async def generate_code(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    save_to_registry: bool = True,
    db: Session = Depends(get_db)
):
    """
    Generate code from a natural language request.
    
    Example:
    ```json
    {
        "request": "Add a drywall quantity calculator",
        "capability_type": "api_endpoint",
        "author": "user@example.com"
    }
    ```
    """
    generator = CodeGenerator()
    
    # Generate code
    result = await generator.generate_from_request(
        request=request.request,
        context=request.context
    )
    
    if not result.success:
        return GenerateResponse(
            success=False,
            message=f"Generation failed: {', '.join(result.errors)}"
        )
    
    capability_id = None
    
    # Save to registry if requested
    if save_to_registry:
        crud = CapabilityCRUD(db)
        
        # Create capability record
        capability_data = CapabilityCreate(
            name=request.request[:50],  # Use request as name (truncated)
            version="1.0.0",
            capability_type=request.capability_type,
            description=request.request,
            author=request.author
        )
        
        db_capability = crud.create(
            data=capability_data,
            code_content=result.code
        )
        capability_id = db_capability.id
    
    return GenerateResponse(
        success=True,
        capability_id=capability_id,
        code=result.code,
        language=result.language,
        metadata=result.metadata,
        tokens_used=result.tokens_used,
        message="Code generated successfully"
    )


@router.post("/refine", response_model=GenerateResponse)
async def refine_code(
    request: RefineRequest,
    db: Session = Depends(get_db)
):
    """
    Refine existing generated code based on feedback.
    """
    crud = CapabilityCRUD(db)
    
    # Get existing capability
    capability = crud.get_by_id(request.capability_id)
    if not capability:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if not capability.code_content:
        raise HTTPException(status_code=400, detail="No code content to refine")
    
    # Generate refinement prompt
    prompt = PromptLibrary.get_refinement_prompt(
        original_request=capability.description or "",
        generated_code=capability.code_content,
        feedback=request.feedback
    )
    
    # Generate refined code
    generator = CodeGenerator()
    result = await generator.generate_custom(
        prompt=prompt,
        language=result.language if 'result' in dir() else "python"
    )
    
    if not result.success:
        return GenerateResponse(
            success=False,
            message=f"Refinement failed: {', '.join(result.errors)}"
        )
    
    # Update capability with new code
    from ..registry.models import CapabilityUpdate
    crud.update(
        capability.id,
        CapabilityUpdate(code_content=result.code)
    )
    
    return GenerateResponse(
        success=True,
        capability_id=capability.id,
        code=result.code,
        language=result.language,
        metadata=result.metadata,
        tokens_used=result.tokens_used,
        message="Code refined successfully"
    )


@router.post("/explain", response_model=ExplainResponse)
async def explain_code(request: ExplainRequest):
    """
    Explain generated code.
    """
    prompt = PromptLibrary.get_explanation_prompt(request.code)
    
    generator = CodeGenerator()
    result = await generator.generate_custom(prompt=prompt, language="text")
    
    if not result.success:
        return ExplainResponse(
            success=False,
            explanation=f"Explanation failed: {', '.join(result.errors)}"
        )
    
    # Parse explanation sections
    explanation = result.code or ""
    
    # Extract sections (simplified parsing)
    key_components = []
    security_considerations = []
    
    if "Key components" in explanation or "Key Components" in explanation:
        # Extract bullet points
        lines = explanation.split("\n")
        in_components = False
        for line in lines:
            if "Key component" in line or "Key Component" in line:
                in_components = True
                continue
            if in_components and line.strip().startswith("-"):
                key_components.append(line.strip()[1:].strip())
            elif in_components and line.strip() and not line.strip().startswith("-"):
                in_components = False
    
    return ExplainResponse(
        success=True,
        explanation=explanation,
        key_components=key_components,
        security_considerations=security_considerations
    )


@router.get("/templates/{template_type}")
async def get_template(template_type: str):
    """
    Get code template for a specific type.
    
    Types: fastapi, react, database, migration
    """
    from .templates import TemplateEngine
    
    engine = TemplateEngine()
    
    templates = {
        "fastapi": engine.FASTAPI_ROUTER_TEMPLATE,
        "react": engine.REACT_COMPONENT_TEMPLATE,
        "database": engine.SQLALCHEMY_MODEL_TEMPLATE,
        "migration": engine.ALEMBIC_MIGRATION_TEMPLATE
    }
    
    template = templates.get(template_type)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template type '{template_type}' not found")
    
    return {
        "success": True,
        "template_type": template_type,
        "template": template.source if hasattr(template, 'source') else str(template)
    }


@router.post("/validate-syntax")
async def validate_syntax(code: str, language: str = "python"):
    """
    Validate code syntax without executing.
    """
    import ast
    
    errors = []
    
    if language == "python":
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
    elif language == "typescript" or language == "javascript":
        # Would need TypeScript compiler for full validation
        # Simplified check for common issues
        if "import" in code and "from" not in code and "require" not in code:
            errors.append("Potential import syntax issue")
    
    return {
        "success": len(errors) == 0,
        "valid": len(errors) == 0,
        "errors": errors,
        "language": language
    }
