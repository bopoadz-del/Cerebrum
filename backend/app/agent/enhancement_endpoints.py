"""
Code Enhancement API Endpoints

Allows the agent to analyze and improve its own code.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging

from app.agent.code_enhancement import (
    CodeAnalyzer, CodeEnhancer, EnhancementManager,
    EnhancementType, enhance_code_file
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ Request/Response Models ============

class AnalyzeFileRequest(BaseModel):
    file_path: str = Field(..., description="Path to file relative to repo root")


class EnhanceFileRequest(BaseModel):
    file_path: str = Field(..., description="Path to file to enhance")
    enhancement_types: List[str] = Field(
        default_factory=list,
        description="Types of enhancements to apply (error_handling, documentation, type_hints, refactor)"
    )
    preview_only: bool = Field(default=True, description="If True, show diff but don't apply")


class ApplyEnhancementRequest(BaseModel):
    file_path: str = Field(..., description="Path to file")
    enhancement_type: str = Field(..., description="Type of enhancement to apply")
    approver: str = Field(default="agent", description="Who approved the enhancement")


class EnhancementPreviewResponse(BaseModel):
    file: str
    enhancement_type: str
    issues_addressed: int
    changes_made: List[Dict[str, Any]]
    diff: str
    ready_to_apply: bool


# ============ ANALYSIS ENDPOINTS ============

@router.post("/analyze")
async def analyze_file(request: AnalyzeFileRequest):
    """
    Analyze a file for improvement opportunities.
    
    Returns:
    - List of issues found (with severity, line numbers, suggestions)
    - Code metrics (LOC, function count, docstring coverage)
    - Recommended enhancement plans
    """
    try:
        manager = EnhancementManager("/root/.openclaw/workspace/cerebrum-fix")
        analysis = manager.get_file_analysis(request.file_path)
        
        return {
            "file": analysis["file"],
            "summary": {
                "total_issues": len(analysis["issues"]),
                "critical": analysis["issue_count_by_severity"].get("critical", 0),
                "warnings": analysis["issue_count_by_severity"].get("warning", 0),
                "info": analysis["issue_count_by_severity"].get("info", 0),
                "enhancement_opportunities": len(analysis["enhancement_plans"])
            },
            "metrics": analysis["metrics"],
            "issues": analysis["issues"],
            "recommended_enhancements": analysis["enhancement_plans"]
        }
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan")
async def scan_repository(
    file_pattern: str = Query(default="**/*.py", description="Glob pattern for files to scan")
):
    """
    Scan the entire repository for improvement opportunities.
    
    Returns a prioritized list of files that could benefit from enhancement.
    """
    try:
        manager = EnhancementManager("/root/.openclaw/workspace/cerebrum-fix")
        plans = manager.scan_for_improvements(file_pattern)
        
        # Group by file
        by_file: Dict[str, Dict] = {}
        for plan in plans:
            file_path = plan.target_file
            if file_path not in by_file:
                by_file[file_path] = {
                    "file": file_path,
                    "plans": [],
                    "total_issues": 0
                }
            by_file[file_path]["plans"].append({
                "type": plan.enhancement_type.value,
                "description": plan.description,
                "issues_count": len(plan.issues_found),
                "estimated_impact": plan.estimated_impact
            })
            by_file[file_path]["total_issues"] += len(plan.issues_found)
        
        # Sort by total issues
        sorted_files = sorted(
            by_file.values(),
            key=lambda x: x["total_issues"],
            reverse=True
        )
        
        return {
            "files_scanned": len(sorted_files),
            "files_with_issues": len([f for f in sorted_files if f["total_issues"] > 0]),
            "prioritized_files": sorted_files[:20]  # Top 20
        }
    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ ENHANCEMENT ENDPOINTS ============

@router.post("/preview", response_model=EnhancementPreviewResponse)
async def preview_enhancement(request: EnhanceFileRequest):
    """
    Preview an enhancement without applying it.
    
    Shows:
    - What issues will be addressed
    - What changes will be made
    - Diff between original and enhanced code
    """
    try:
        result = enhance_code_file(
            file_path=request.file_path,
            enhancement_types=request.enhancement_types or None,
            repo_path="/root/.openclaw/workspace/cerebrum-fix"
        )
        
        if result.get("status") == "no_improvements_needed":
            return {
                "file": request.file_path,
                "enhancement_type": "none",
                "issues_addressed": 0,
                "changes_made": [],
                "diff": "# No improvements needed",
                "ready_to_apply": False
            }
        
        return EnhancementPreviewResponse(
            file=result["file"],
            enhancement_type=result["enhancement_type"],
            issues_addressed=result["issues_addressed"],
            changes_made=result["changes_made"],
            diff=result["diff"],
            ready_to_apply=result["ready_to_apply"]
        )
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply")
async def apply_enhancement(request: ApplyEnhancementRequest):
    """
    Apply an enhancement to a file.
    
    This will:
    1. Create a git checkpoint
    2. Apply the enhancement
    3. Validate the changes
    4. Commit if successful
    5. Rollback if validation fails
    """
    try:
        from app.agent.self_modification import get_modification_engine, CodeChange
        
        # First generate the enhancement
        result = enhance_code_file(
            file_path=request.file_path,
            enhancement_types=[request.enhancement_type],
            repo_path="/root/.openclaw/workspace/cerebrum-fix"
        )
        
        if result.get("status") != "enhancement_ready":
            raise HTTPException(
                status_code=400,
                detail=f"Enhancement not ready: {result.get('error', 'Unknown error')}"
            )
        
        # Create modification request
        engine = get_modification_engine()
        
        change = CodeChange(
            file_path=request.file_path,
            original_content=result.get("original_content", ""),
            new_content=result.get("enhanced_content", ""),
            change_type="modify",
            description=f"Code enhancement: {result['enhancement_type']} ({result['issues_addressed']} issues addressed)",
            line_numbers=None
        )
        
        # Create the modification request
        from app.agent.self_modification import ModificationRequest, ModificationType
        
        mod_request = ModificationRequest(
            id=engine._generate_request_id(),
            timestamp=__import__('datetime').datetime.now().isoformat(),
            type=ModificationType.MODIFY_CODE,
            description=f"Enhance {request.file_path}: {result['enhancement_type']}",
            changes=[change],
            metadata={
                "enhancement_type": result['enhancement_type'],
                "issues_addressed": result['issues_addressed'],
                "changes_made": result['changes_made']
            }
        )
        
        engine.pending_requests[mod_request.id] = mod_request
        
        # Auto-approve and apply
        engine.approve_request(mod_request.id, request.approver)
        apply_result = engine.apply_modification(mod_request.id)
        
        return {
            "success": apply_result.get("success"),
            "file": request.file_path,
            "enhancement_type": result["enhancement_type"],
            "issues_addressed": result["issues_addressed"],
            "modification_id": mod_request.id,
            "result": apply_result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Apply enhancement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ AUTONOMOUS ENHANCEMENT ============

@router.post("/autonomous")
async def autonomous_enhancement(
    target: str = Query(..., description="What to enhance (e.g., 'error handling', 'documentation')"),
    scope: str = Query(default="backend/app/agent", description="Directory scope to scan")
):
    """
    Autonomously find and enhance code based on a target goal.
    
    Example targets:
    - "error handling" - Find and fix bare except clauses
    - "documentation" - Add missing docstrings
    - "type hints" - Add type annotations
    - "performance" - Optimize slow code
    
    The agent will:
    1. Scan the scope for relevant issues
    2. Generate enhancements
    3. Apply them with git tracking
    """
    try:
        manager = EnhancementManager("/root/.openclaw/workspace/cerebrum-fix")
        
        # Map target to enhancement type
        target_lower = target.lower()
        type_mapping = {
            "error": EnhancementType.ERROR_HANDLING,
            "except": EnhancementType.ERROR_HANDLING,
            "doc": EnhancementType.DOCUMENTATION,
            "type": EnhancementType.TYPE_HINTS,
            "hint": EnhancementType.TYPE_HINTS,
            "refactor": EnhancementType.REFACTOR,
            "perf": EnhancementType.PERFORMANCE
        }
        
        enhancement_type = None
        for key, val in type_mapping.items():
            if key in target_lower:
                enhancement_type = val
                break
        
        if not enhancement_type:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown enhancement target: {target}. Try: error handling, documentation, type hints, refactor"
            )
        
        # Scan for files with this type of issue
        all_plans = manager.scan_for_improvements(f"{scope}/**/*.py")
        relevant_plans = [p for p in all_plans if p.enhancement_type == enhancement_type]
        
        if not relevant_plans:
            return {
                "target": target,
                "scope": scope,
                "status": "no_issues_found",
                "message": f"No {target} issues found in {scope}"
            }
        
        # Apply the first plan
        plan = relevant_plans[0]
        result = await apply_enhancement(ApplyEnhancementRequest(
            file_path=plan.target_file,
            enhancement_type=enhancement_type.value,
            approver="autonomous_agent"
        ))
        
        return {
            "target": target,
            "scope": scope,
            "status": "enhanced",
            "file_enhanced": plan.target_file,
            "issues_addressed": len(plan.issues_found),
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Autonomous enhancement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ UTILITY ENDPOINTS ============

@router.get("/issues/types")
async def list_issue_types():
    """List all types of issues the analyzer can detect."""
    return {
        "issue_types": [
            {
                "type": "bare_except",
                "severity": "warning",
                "description": "Bare except clause catches SystemExit and KeyboardInterrupt",
                "fixable": True
            },
            {
                "type": "mutable_default",
                "severity": "critical",
                "description": "Mutable default argument causes shared state bugs",
                "fixable": True
            },
            {
                "type": "missing_docstring",
                "severity": "info",
                "description": "Function lacks documentation",
                "fixable": True
            },
            {
                "type": "no_type_hints",
                "severity": "info",
                "description": "Function missing type annotations",
                "fixable": True
            },
            {
                "type": "long_function",
                "severity": "warning",
                "description": "Function exceeds 50 lines",
                "fixable": False  # Requires manual refactoring
            },
            {
                "type": "high_complexity",
                "severity": "warning",
                "description": "Function has high cyclomatic complexity",
                "fixable": False
            },
            {
                "type": "hardcoded_string",
                "severity": "critical",
                "description": "Potential hardcoded secret detected",
                "fixable": False  # Requires manual review
            }
        ]
    }


@router.get("/metrics/{file_path:path}")
async def get_file_metrics(file_path: str):
    """Get code quality metrics for a specific file."""
    try:
        manager = EnhancementManager("/root/.openclaw/workspace/cerebrum-fix")
        analysis = manager.get_file_analysis(file_path)
        
        return {
            "file": file_path,
            "metrics": analysis["metrics"],
            "health_score": _calculate_health_score(analysis)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_health_score(analysis: Dict) -> int:
    """Calculate a 0-100 health score for the file."""
    score = 100
    
    # Deduct for issues
    severity_weights = {"critical": 20, "warning": 10, "info": 2}
    for severity, count in analysis.get("issue_count_by_severity", {}).items():
        score -= count * severity_weights.get(severity, 5)
    
    # Bonus for good documentation
    metrics = analysis.get("metrics", {})
    doc_coverage = metrics.get("docstring_coverage", 0)
    score += int(doc_coverage / 10)  # Up to +10 points
    
    return max(0, min(100, score))
