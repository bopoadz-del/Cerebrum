"""Coding API Endpoints

Code generation and analysis tools — powered by DeepSeek LLM.
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    SQL = "sql"
    BASH = "bash"
    YAML = "yaml"
    JSON = "json"


class CodeGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    language: Language = Language.PYTHON
    context: Optional[str] = None
    framework: Optional[str] = None


class CodeAnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: Language = Language.PYTHON
    check_security: bool = True
    check_performance: bool = True


class CodeRefactorRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: Language = Language.PYTHON
    instructions: Optional[str] = None


class CodeResponse(BaseModel):
    id: str
    language: str
    code: str
    explanation: Optional[str] = None
    created_at: datetime


class CodeAnalysisResponse(BaseModel):
    id: str
    language: str
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    complexity_score: int
    security_issues: List[str]
    created_at: datetime


async def _call_llm(prompt: str) -> str:
    """Call the LLM client for code generation."""
    try:
        from app.llm.client import LLMClient
        client = LLMClient()
        response = await client.complete(prompt)
        return response
    except Exception as e:
        logger.warning("LLM unavailable, returning placeholder", error=str(e))
        return f"# Generated code placeholder\n# Prompt: {prompt[:100]}\npass"


@router.post("/generate", response_model=CodeResponse, status_code=status.HTTP_201_CREATED)
async def generate_code(data: CodeGenerateRequest):
    """Generate code from a natural language prompt using DeepSeek AI."""
    context_str = f"\nContext:\n{data.context}" if data.context else ""
    framework_str = f"\nFramework: {data.framework}" if data.framework else ""
    prompt = (
        f"Generate {data.language.value} code for the following task:{framework_str}{context_str}\n\n"
        f"Task: {data.prompt}\n\n"
        f"Return only the code with brief inline comments. No markdown fences."
    )
    code = await _call_llm(prompt)
    logger.info("Code generated", language=data.language.value)
    return CodeResponse(
        id=str(uuid.uuid4()),
        language=data.language.value,
        code=code,
        explanation=f"Generated {data.language.value} code for: {data.prompt[:80]}",
        created_at=datetime.utcnow(),
    )


@router.post("/analyze", response_model=CodeAnalysisResponse)
async def analyze_code(data: CodeAnalyzeRequest):
    """Analyze code for issues, security problems, and improvements."""
    checks = []
    if data.check_security:
        checks.append("security vulnerabilities (SQL injection, XSS, hardcoded secrets)")
    if data.check_performance:
        checks.append("performance issues (N+1 queries, blocking calls, memory leaks)")

    prompt = (
        f"Analyze this {data.language.value} code for: {', '.join(checks)}.\n"
        f"Return JSON with keys: issues (list of {{type, line, message}}), "
        f"suggestions (list of strings), complexity_score (1-10), security_issues (list of strings).\n\n"
        f"Code:\n{data.code[:3000]}"
    )
    raw = await _call_llm(prompt)

    # Try to parse LLM JSON response, fallback to empty analysis
    try:
        import json, re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        parsed = json.loads(match.group()) if match else {}
    except Exception:
        parsed = {}

    return CodeAnalysisResponse(
        id=str(uuid.uuid4()),
        language=data.language.value,
        issues=parsed.get("issues", []),
        suggestions=parsed.get("suggestions", ["Review code manually"]),
        complexity_score=parsed.get("complexity_score", 5),
        security_issues=parsed.get("security_issues", []),
        created_at=datetime.utcnow(),
    )


@router.post("/refactor", response_model=CodeResponse)
async def refactor_code(data: CodeRefactorRequest):
    """Refactor code with optional instructions."""
    instructions = data.instructions or "improve readability, add type hints, follow best practices"
    prompt = (
        f"Refactor this {data.language.value} code. Instructions: {instructions}\n\n"
        f"Return only the refactored code, no explanations.\n\nCode:\n{data.code[:3000]}"
    )
    code = await _call_llm(prompt)
    return CodeResponse(
        id=str(uuid.uuid4()),
        language=data.language.value,
        code=code,
        explanation=f"Refactored: {instructions[:80]}",
        created_at=datetime.utcnow(),
    )


@router.post("/explain")
async def explain_code(data: CodeAnalyzeRequest):
    """Explain what a piece of code does in plain English."""
    prompt = (
        f"Explain this {data.language.value} code in plain English. "
        f"Be concise but thorough. Use bullet points.\n\nCode:\n{data.code[:3000]}"
    )
    explanation = await _call_llm(prompt)
    return {
        "id": str(uuid.uuid4()),
        "language": data.language.value,
        "explanation": explanation,
        "created_at": datetime.utcnow().isoformat(),
    }


@router.get("/languages")
async def list_languages():
    """List supported programming languages."""
    return {
        "languages": [{"id": lang.value, "name": lang.value.capitalize()} for lang in Language]
    }
