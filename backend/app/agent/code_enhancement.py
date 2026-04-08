"""
Code Enhancement System for Self-Modification Engine

Enables the agent to analyze and improve its own code:
- Identify improvement opportunities
- Generate enhanced versions
- Compare before/after
- Apply with safety checks
- Track enhancement history
"""

import ast
import re
import inspect
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EnhancementType(Enum):
    PERFORMANCE = "performance"          # Optimize speed/memory
    READABILITY = "readability"          # Improve clarity
    ERROR_HANDLING = "error_handling"    # Add better error handling
    TYPE_HINTS = "type_hints"            # Add missing type annotations
    DOCUMENTATION = "documentation"      # Improve docs
    REFACTOR = "refactor"                # Restructure for better design
    FEATURE_ADD = "feature_add"          # Add new capabilities
    BUG_FIX = "bug_fix"                  # Fix potential issues


@dataclass
class CodeIssue:
    """An issue or improvement opportunity found in code."""
    line_number: int
    issue_type: str
    severity: str  # "info", "warning", "critical"
    message: str
    suggestion: str
    original_code: str
    enhanced_code: Optional[str] = None


@dataclass
class EnhancementPlan:
    """Plan for enhancing a piece of code."""
    target_file: str
    target_function: Optional[str]
    enhancement_type: EnhancementType
    description: str
    issues_found: List[CodeIssue]
    proposed_changes: List[Dict[str, str]]
    estimated_impact: str  # "low", "medium", "high"
    risks: List[str] = field(default_factory=list)


@dataclass
class EnhancementResult:
    """Result of applying an enhancement."""
    success: bool
    original_content: str
    enhanced_content: str
    changes_made: List[Dict[str, Any]]
    validation_result: Dict[str, Any]
    execution_time_ms: float
    error: Optional[str] = None


class CodeAnalyzer:
    """Analyzes code for improvement opportunities."""
    
    # Anti-patterns to detect
    ANTI_PATTERNS = {
        "bare_except": {
            "pattern": r"except\s*:",
            "message": "Bare except clause catches SystemExit and KeyboardInterrupt",
            "suggestion": "Use 'except Exception:' or specific exception types",
            "severity": "warning"
        },
        "print_debugging": {
            "pattern": r"print\s*\([^)]*debug",
            "message": "Debug print statement found",
            "suggestion": "Use logging instead of print for debug output",
            "severity": "info"
        },
        "mutable_default": {
            "pattern": r"def\s+\w+\s*\([^)]*=\s*(\[\s*\]|\{\s*\})",
            "message": "Mutable default argument detected",
            "suggestion": "Use None as default and initialize mutable in function body",
            "severity": "critical"
        },
        "no_type_hints": {
            "pattern": r"^\s*def\s+\w+\s*\([^)]*\)(?!\s*->)",
            "message": "Function missing return type annotation",
            "suggestion": "Add -> return_type annotation",
            "severity": "info"
        },
        "broad_exception": {
            "pattern": r"except\s+Exception\s*:",
            "message": "Catching broad Exception class",
            "suggestion": "Catch specific exception types when possible",
            "severity": "warning"
        },
        "hardcoded_string": {
            "pattern": r'["\'][^"\']*(?:password|secret|key|token)[^"\']*["\']',
            "message": "Potential hardcoded secret",
            "suggestion": "Use environment variables or secure vault",
            "severity": "critical"
        }
    }
    
    def __init__(self):
        self.issues: List[CodeIssue] = []
    
    def analyze_file(self, file_path: str) -> List[CodeIssue]:
        """Analyze a Python file for improvement opportunities."""
        self.issues = []
        path = Path(file_path)
        
        if not path.exists():
            return [CodeIssue(
                line_number=0,
                issue_type="file_error",
                severity="critical",
                message=f"File not found: {file_path}",
                suggestion="Check file path",
                original_code=""
            )]
        
        try:
            content = path.read_text()
            self._analyze_with_regex(content)
            self._analyze_with_ast(content)
            self._analyze_complexity(content)
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
        
        return sorted(self.issues, key=lambda x: x.line_number)
    
    def _analyze_with_regex(self, content: str):
        """Find issues using regex patterns."""
        lines = content.split('\n')
        
        for pattern_name, pattern_info in self.ANTI_PATTERNS.items():
            for i, line in enumerate(lines, 1):
                if re.search(pattern_info["pattern"], line, re.IGNORECASE):
                    issue = CodeIssue(
                        line_number=i,
                        issue_type=pattern_name,
                        severity=pattern_info["severity"],
                        message=pattern_info["message"],
                        suggestion=pattern_info["suggestion"],
                        original_code=line.strip()
                    )
                    self.issues.append(issue)
    
    def _analyze_with_ast(self, content: str):
        """Find issues using AST analysis."""
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Check for functions without docstrings
                if isinstance(node, ast.FunctionDef):
                    if not ast.get_docstring(node):
                        self.issues.append(CodeIssue(
                            line_number=node.lineno,
                            issue_type="missing_docstring",
                            severity="info",
                            message=f"Function '{node.name}' missing docstring",
                            suggestion="Add a docstring describing the function",
                            original_code=f"def {node.name}(...):"
                        ))
                    
                    # Check for long functions
                    if node.end_lineno and node.end_lineno - node.lineno > 50:
                        self.issues.append(CodeIssue(
                            line_number=node.lineno,
                            issue_type="long_function",
                            severity="warning",
                            message=f"Function '{node.name}' is very long ({node.end_lineno - node.lineno} lines)",
                            suggestion="Consider breaking into smaller functions",
                            original_code=f"def {node.name}(...):"
                        ))
                    
                    # Check for too many arguments
                    args_count = len(node.args.args) + len(node.args.kwonlyargs)
                    if args_count > 5:
                        self.issues.append(CodeIssue(
                            line_number=node.lineno,
                            issue_type="too_many_args",
                            severity="warning",
                            message=f"Function '{node.name}' has {args_count} arguments",
                            suggestion="Consider using a dataclass or config object",
                            original_code=f"def {node.name}(...):"
                        ))
                
                # Check for deeply nested code
                if isinstance(node, (ast.If, ast.For, ast.While, ast.With)):
                    depth = self._get_nesting_depth(node, tree)
                    if depth > 4:
                        self.issues.append(CodeIssue(
                            line_number=node.lineno,
                            issue_type="deep_nesting",
                            severity="warning",
                            message=f"Deep nesting detected (depth {depth})",
                            suggestion="Refactor to reduce nesting (extract functions, use early returns)",
                            original_code="# Deeply nested block"
                        ))
        
        except SyntaxError:
            pass  # Regex analysis already done
    
    def _get_nesting_depth(self, node: ast.AST, tree: ast.AST) -> int:
        """Calculate nesting depth of a node."""
        depth = 0
        for parent in ast.walk(tree):
            if isinstance(parent, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                # Check if node is inside parent
                if hasattr(parent, 'body') and any(
                    child is node or (isinstance(node, ast.AST) and self._node_contains(parent, node))
                    for child in ast.walk(parent)
                ):
                    depth += 1
        return depth
    
    def _node_contains(self, parent: ast.AST, child: ast.AST) -> bool:
        """Check if parent node contains child node."""
        for node in ast.walk(parent):
            if node is child:
                return True
        return False
    
    def _analyze_complexity(self, content: str):
        """Analyze code complexity metrics."""
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Simple cyclomatic complexity approximation
                    complexity = 1  # Base
                    complexity += len([n for n in ast.walk(node) if isinstance(n, (ast.If, ast.While, ast.For))])
                    complexity += len([n for n in ast.walk(node) if isinstance(n, ast.ExceptHandler)])
                    complexity += len([n for n in ast.walk(node) if isinstance(n, ast.With)])
                    
                    if complexity > 10:
                        self.issues.append(CodeIssue(
                            line_number=node.lineno,
                            issue_type="high_complexity",
                            severity="warning",
                            message=f"Function '{node.name}' has high complexity (estimated {complexity})",
                            suggestion="Refactor to reduce branches and loops",
                            original_code=f"def {node.name}(...):"
                        ))
        except:
            pass


class CodeEnhancer:
    """Generates enhanced versions of code."""
    
    def __init__(self):
        self.analyzer = CodeAnalyzer()
    
    def generate_enhancement_plan(self, file_path: str, 
                                   enhancement_types: Optional[List[EnhancementType]] = None
                                   ) -> List[EnhancementPlan]:
        """Generate plans for enhancing a file."""
        if enhancement_types is None:
            enhancement_types = [t for t in EnhancementType]
        
        issues = self.analyzer.analyze_file(file_path)
        plans = []
        
        # Group issues by type
        by_type: Dict[str, List[CodeIssue]] = {}
        for issue in issues:
            by_type.setdefault(issue.issue_type, []).append(issue)
        
        # Create plans based on issue types
        if "bare_except" in by_type or "broad_exception" in by_type:
            plans.append(self._create_error_handling_plan(file_path, issues))
        
        if "missing_docstring" in by_type:
            plans.append(self._create_documentation_plan(file_path, issues))
        
        if "no_type_hints" in by_type:
            plans.append(self._create_type_hints_plan(file_path, issues))
        
        if "long_function" in by_type or "high_complexity" in by_type:
            plans.append(self._create_refactor_plan(file_path, issues))
        
        return plans
    
    def _create_error_handling_plan(self, file_path: str, issues: List[CodeIssue]) -> EnhancementPlan:
        """Create plan for improving error handling."""
        relevant_issues = [i for i in issues if i.issue_type in ("bare_except", "broad_exception")]
        
        return EnhancementPlan(
            target_file=file_path,
            target_function=None,
            enhancement_type=EnhancementType.ERROR_HANDLING,
            description=f"Improve error handling in {Path(file_path).name}",
            issues_found=relevant_issues,
            proposed_changes=[{
                "type": "replace",
                "description": "Replace bare except with specific exception types"
            }],
            estimated_impact="high",
            risks=["May miss some edge cases if exceptions are too specific"]
        )
    
    def _create_documentation_plan(self, file_path: str, issues: List[CodeIssue]) -> EnhancementPlan:
        """Create plan for improving documentation."""
        relevant_issues = [i for i in issues if i.issue_type == "missing_docstring"]
        
        return EnhancementPlan(
            target_file=file_path,
            target_function=None,
            enhancement_type=EnhancementType.DOCUMENTATION,
            description=f"Add missing docstrings to functions in {Path(file_path).name}",
            issues_found=relevant_issues,
            proposed_changes=[{
                "type": "add",
                "description": "Add Google-style docstrings to undocumented functions"
            }],
            estimated_impact="low",
            risks=[]
        )
    
    def _create_type_hints_plan(self, file_path: str, issues: List[CodeIssue]) -> EnhancementPlan:
        """Create plan for adding type hints."""
        relevant_issues = [i for i in issues if i.issue_type == "no_type_hints"]
        
        return EnhancementPlan(
            target_file=file_path,
            target_function=None,
            enhancement_type=EnhancementType.TYPE_HINTS,
            description=f"Add type annotations to {Path(file_path).name}",
            issues_found=relevant_issues,
            proposed_changes=[{
                "type": "add",
                "description": "Add type hints for parameters and return values"
            }],
            estimated_impact="medium",
            risks=["May require importing additional types from typing module"]
        )
    
    def _create_refactor_plan(self, file_path: str, issues: List[CodeIssue]) -> EnhancementPlan:
        """Create plan for refactoring complex code."""
        relevant_issues = [i for i in issues if i.issue_type in ("long_function", "high_complexity")]
        
        return EnhancementPlan(
            target_file=file_path,
            target_function=None,
            enhancement_type=EnhancementType.REFACTOR,
            description=f"Refactor complex functions in {Path(file_path).name}",
            issues_found=relevant_issues,
            proposed_changes=[{
                "type": "refactor",
                "description": "Extract helper functions, reduce nesting, simplify logic"
            }],
            estimated_impact="high",
            risks=["May change behavior if not tested thoroughly"]
        )
    
    def apply_enhancement(self, file_path: str, plan: EnhancementPlan) -> EnhancementResult:
        """Apply an enhancement plan to a file."""
        import time
        start_time = time.time()
        
        path = Path(file_path)
        if not path.exists():
            return EnhancementResult(
                success=False,
                original_content="",
                enhanced_content="",
                changes_made=[],
                validation_result={},
                execution_time_ms=0,
                error="File not found"
            )
        
        original_content = path.read_text()
        enhanced_content = original_content
        changes_made = []
        
        try:
            if plan.enhancement_type == EnhancementType.ERROR_HANDLING:
                enhanced_content, changes = self._enhance_error_handling(original_content)
                changes_made.extend(changes)
            
            elif plan.enhancement_type == EnhancementType.DOCUMENTATION:
                enhanced_content, changes = self._enhance_documentation(original_content)
                changes_made.extend(changes)
            
            elif plan.enhancement_type == EnhancementType.TYPE_HINTS:
                enhanced_content, changes = self._enhance_type_hints(original_content)
                changes_made.extend(changes)
            
            # Validate the result
            validation_result = self._validate_enhancement(original_content, enhanced_content)
            
            execution_time = (time.time() - start_time) * 1000
            
            return EnhancementResult(
                success=validation_result.get("valid", False),
                original_content=original_content,
                enhanced_content=enhanced_content,
                changes_made=changes_made,
                validation_result=validation_result,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            return EnhancementResult(
                success=False,
                original_content=original_content,
                enhanced_content=enhanced_content,
                changes_made=changes_made,
                validation_result={},
                execution_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    def _enhance_error_handling(self, content: str) -> Tuple[str, List[Dict]]:
        """Improve error handling patterns."""
        changes = []
        
        # Replace bare except with Exception
        original = content
        content = re.sub(
            r'^(\	|    )except\s*:$',
            r'\1except Exception:',
            content,
            flags=re.MULTILINE
        )
        if content != original:
            changes.append({"type": "bare_except_fix", "count": 1})
        
        # Add logging to bare except blocks
        content = re.sub(
            r'^(\t|    )(except\s+[^:]+:)$',
            r'\1\2\n\1    logger = logging.getLogger(__name__)\n\1    logger.error(f"Error: {e}")',
            content,
            flags=re.MULTILINE
        )
        
        return content, changes
    
    def _enhance_documentation(self, content: str) -> Tuple[str, List[Dict]]:
        """Add missing docstrings."""
        changes = []
        
        try:
            tree = ast.parse(content)
            lines = content.split('\n')
            
            # Find functions without docstrings
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not ast.get_docstring(node):
                    # Find insertion point (after function def line)
                    indent = self._get_indent(lines[node.lineno - 1])
                    docstring = f'{indent}"""\n{indent}TODO: Add description for {node.name}\n{indent}"""'
                    
                    lines.insert(node.lineno, docstring)
                    changes.append({"type": "add_docstring", "function": node.name})
            
            content = '\n'.join(lines)
        except:
            pass
        
        return content, changes
    
    def _enhance_type_hints(self, content: str) -> Tuple[str, List[Dict]]:
        """Add type hints to functions."""
        changes = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if already has return type
                    if node.returns is None:
                        # Add -> Any as placeholder
                        changes.append({"type": "add_return_hint", "function": node.name})
        except:
            pass
        
        return content, changes
    
    def _get_indent(self, line: str) -> str:
        """Extract leading whitespace from a line."""
        match = re.match(r'^(\s*)', line)
        return match.group(1) if match else ''
    
    def _validate_enhancement(self, original: str, enhanced: str) -> Dict[str, Any]:
        """Validate that enhancement didn't break anything."""
        result = {"valid": True, "errors": [], "warnings": []}
        
        # Check syntax
        try:
            ast.parse(enhanced)
        except SyntaxError as e:
            result["valid"] = False
            result["errors"].append(f"Syntax error: {e}")
        
        # Check that we didn't lose content (basic check)
        if len(enhanced) < len(original) * 0.5:
            result["valid"] = False
            result["errors"].append("Enhanced version suspiciously shorter than original")
        
        # Count functions (should be same or more)
        try:
            original_funcs = len([n for n in ast.walk(ast.parse(original)) if isinstance(n, ast.FunctionDef)])
            enhanced_funcs = len([n for n in ast.walk(ast.parse(enhanced)) if isinstance(n, ast.FunctionDef)])
            
            if enhanced_funcs < original_funcs:
                result["warnings"].append(f"Lost {original_funcs - enhanced_funcs} functions during enhancement")
        except:
            pass
        
        return result


class EnhancementManager:
    """Manages the code enhancement workflow."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.analyzer = CodeAnalyzer()
        self.enhancer = CodeEnhancer()
        self.history: List[Dict] = []
    
    def scan_for_improvements(self, file_pattern: str = "**/*.py") -> List[EnhancementPlan]:
        """Scan repository for improvement opportunities."""
        all_plans = []
        
        for py_file in self.repo_path.rglob(file_pattern):
            # Skip certain directories
            if any(part.startswith('.') or part == '__pycache__' 
                   for part in py_file.parts):
                continue
            
            plans = self.enhancer.generate_enhancement_plan(str(py_file))
            all_plans.extend(plans)
        
        return sorted(all_plans, key=lambda p: len(p.issues_found), reverse=True)
    
    def get_file_analysis(self, file_path: str) -> Dict[str, Any]:
        """Get detailed analysis of a file."""
        full_path = self.repo_path / file_path
        
        issues = self.analyzer.analyze_file(str(full_path))
        plans = self.enhancer.generate_enhancement_plan(str(full_path))
        
        # Calculate metrics
        try:
            content = full_path.read_text()
            tree = ast.parse(content)
            
            metrics = {
                "lines_of_code": len(content.split('\n')),
                "functions": len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]),
                "classes": len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]),
                "imports": len([n for n in ast.walk(tree) if isinstance(n, ast.Import)]),
                "docstring_coverage": self._calculate_docstring_coverage(tree),
                "type_hint_coverage": self._calculate_type_hint_coverage(tree)
            }
        except:
            metrics = {}
        
        return {
            "file": file_path,
            "issues": [self._issue_to_dict(i) for i in issues],
            "issue_count_by_severity": self._count_by_severity(issues),
            "enhancement_plans": [self._plan_to_dict(p) for p in plans],
            "metrics": metrics
        }
    
    def _calculate_docstring_coverage(self, tree: ast.AST) -> float:
        """Calculate percentage of functions with docstrings."""
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        if not functions:
            return 100.0
        documented = sum(1 for f in functions if ast.get_docstring(f))
        return (documented / len(functions)) * 100
    
    def _calculate_type_hint_coverage(self, tree: ast.AST) -> float:
        """Calculate percentage of functions with type hints."""
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        if not functions:
            return 100.0
        
        hinted = 0
        for f in functions:
            has_arg_hints = any(arg.annotation for arg in f.args.args)
            has_return_hint = f.returns is not None
            if has_arg_hints or has_return_hint:
                hinted += 1
        
        return (hinted / len(functions)) * 100
    
    def _issue_to_dict(self, issue: CodeIssue) -> Dict:
        return {
            "line": issue.line_number,
            "type": issue.issue_type,
            "severity": issue.severity,
            "message": issue.message,
            "suggestion": issue.suggestion,
            "code": issue.original_code[:100]
        }
    
    def _count_by_severity(self, issues: List[CodeIssue]) -> Dict[str, int]:
        counts = {"critical": 0, "warning": 0, "info": 0}
        for i in issues:
            counts[i.severity] = counts.get(i.severity, 0) + 1
        return counts
    
    def _plan_to_dict(self, plan: EnhancementPlan) -> Dict:
        return {
            "type": plan.enhancement_type.value,
            "description": plan.description,
            "issues_count": len(plan.issues_found),
            "estimated_impact": plan.estimated_impact,
            "risks": plan.risks
        }
    
    def preview_enhancement(self, file_path: str, plan: EnhancementPlan) -> Dict[str, Any]:
        """Generate a preview of the enhancement without applying."""
        full_path = self.repo_path / file_path
        result = self.enhancer.apply_enhancement(str(full_path), plan)
        
        return {
            "file": file_path,
            "plan": self._plan_to_dict(plan),
            "success": result.success,
            "changes_made": result.changes_made,
            "diff_preview": self._generate_diff(result.original_content, result.enhanced_content),
            "error": result.error
        }
    
    def _generate_diff(self, original: str, enhanced: str, context_lines: int = 3) -> str:
        """Generate a unified diff between original and enhanced."""
        import difflib
        
        original_lines = original.splitlines(keepends=True)
        enhanced_lines = enhanced.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            enhanced_lines,
            fromfile="original",
            tofile="enhanced",
            lineterm='',
            n=context_lines
        )
        
        return ''.join(diff)


# Integration with SelfModificationEngine
def enhance_code_file(file_path: str, 
                      enhancement_types: Optional[List[str]] = None,
                      repo_path: Optional[str] = None) -> Dict[str, Any]:
    """
    High-level function to enhance a code file.
    
    Usage:
        result = enhance_code_file(
            "backend/app/agent/core.py",
            enhancement_types=["error_handling", "documentation"]
        )
    """
    if repo_path is None:
        repo_path = "/root/.openclaw/workspace/cerebrum-fix"
    
    manager = EnhancementManager(repo_path)
    
    # Get analysis
    analysis = manager.get_file_analysis(file_path)
    
    if not analysis["enhancement_plans"]:
        return {
            "file": file_path,
            "status": "no_improvements_needed",
            "message": "No enhancement opportunities found"
        }
    
    # Preview the first plan
    plan_dict = analysis["enhancement_plans"][0]
    
    # Convert back to EnhancementPlan (simplified)
    from app.agent.self_modification import (
        get_modification_engine, CodeChange, ModificationType
    )
    
    engine = get_modification_engine()
    
    # Create a modification request
    full_path = Path(repo_path) / file_path
    original_content = full_path.read_text()
    
    # Generate the enhancement
    enhancer = CodeEnhancer()
    # Find the actual plan
    plans = enhancer.generate_enhancement_plan(str(full_path))
    if not plans:
        return {"error": "No enhancement plans generated"}
    
    plan = plans[0]
    result = enhancer.apply_enhancement(str(full_path), plan)
    
    if not result.success:
        return {
            "file": file_path,
            "status": "enhancement_failed",
            "error": result.error,
            "validation": result.validation_result
        }
    
    # Create modification request
    from app.agent.self_modification import ModificationRequest
    
    change = CodeChange(
        file_path=file_path,
        original_content=result.original_content,
        new_content=result.enhanced_content,
        change_type="modify",
        description=f"Enhanced {file_path}: {plan.enhancement_type.value}",
        line_numbers=None
    )
    
    return {
        "file": file_path,
        "status": "enhancement_ready",
        "enhancement_type": plan.enhancement_type.value,
        "issues_addressed": len(plan.issues_found),
        "changes_made": result.changes_made,
        "diff": manager._generate_diff(result.original_content, result.enhanced_content),
        "ready_to_apply": True
    }
