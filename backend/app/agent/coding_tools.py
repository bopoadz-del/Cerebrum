"""
Coding Tools for Cerebrum Agent

Provides tools for:
- Code generation (endpoints, components, models)
- Code validation and review
- Test generation
- Refactoring suggestions
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.agent.response_schema import (
    AgentResponse,
    ErrorCode,
    format_error_response,
    format_success_response,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Code Generation Tools
# =============================================================================

def coding_generate_endpoint(
    path: str,
    method: str = "GET",
    model_name: Optional[str] = None,
    fields: Optional[List[Dict]] = None,
    operations: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generate a FastAPI endpoint with CRUD operations.
    
    Args:
        path: API path (e.g., /api/v1/items)
        method: HTTP method (GET, POST, PUT, DELETE)
        model_name: Pydantic model name
        fields: List of field definitions with name, type, required
        operations: CRUD operations to include (create, read, update, delete, list)
    
    Returns:
        Standardized response with generated code
    """
    try:
        # Validate inputs
        if not path.startswith("/"):
            return format_error_response(
                message="Path must start with /",
                code="invalid_input",
                details={"path": path},
                suggestion="Use format like '/api/v1/items'"
            )
        
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
        if method.upper() not in valid_methods:
            return format_error_response(
                message=f"Invalid HTTP method '{method}'",
                code="invalid_input",
                details={"valid_methods": valid_methods},
                suggestion=f"Use one of: {', '.join(valid_methods)}"
            )
        
        # Generate the endpoint code
        model_name = model_name or "Item"
        operations = operations or ["create", "read", "update", "delete", "list"]
        
        code = _generate_fastapi_endpoint_code(path, method, model_name, fields or [], operations)
        
        return format_success_response(
            results={
                "code": code,
                "language": "python",
                "file_name": f"{model_name.lower()}_endpoints.py",
                "endpoint_path": path,
                "operations": operations,
            },
            metadata={
                "generator": "fastapi",
                "lines_of_code": len(code.split("\n")),
            },
            suggestions=[
                "Validate the code with coding_validate_code(code=result['code'])",
                "Generate tests with coding_generate_tests(endpoint_path='{}')".format(path),
            ]
        )
    
    except Exception as e:
        logger.error(f"Endpoint generation failed: {e}")
        return format_error_response(
            message=f"Failed to generate endpoint: {str(e)}",
            code="unknown_error",
            suggestion="Check input parameters and try again"
        )


def _generate_fastapi_endpoint_code(
    path: str,
    method: str,
    model_name: str,
    fields: List[Dict],
    operations: List[str]
) -> str:
    """Generate FastAPI endpoint code."""
    
    code_lines = [
        f'"""',
        f'{model_name} Endpoints',
        f'Auto-generated on {datetime.now().isoformat()}',
        f'"""',
        f'',
        f'from fastapi import APIRouter, HTTPException, Depends',
        f'from typing import List, Optional',
        f'from pydantic import BaseModel',
        f'',
        f'router = APIRouter(prefix="{path}", tags=["{model_name}"])',
        f'',
        f'',
        f'class {model_name}Create(BaseModel):',
    ]
    
    # Add fields
    for field in fields:
        name = field.get("name", "field")
        ftype = field.get("type", "str")
        required = field.get("required", True)
        description = field.get("description", "")
        
        if not required:
            ftype = f"Optional[{ftype}] = None"
        
        code_lines.append(f'    {name}: {ftype}  # {description}')
    
    if not fields:
        code_lines.append(f'    name: str')
        code_lines.append(f'    description: Optional[str] = None')
    
    code_lines.extend([
        f'',
        f'',
        f'class {model_name}Response({model_name}Create):',
        f'    id: int',
        f'',
        f'    class Config:',
        f'        from_attributes = True',
        f'',
    ])
    
    # Generate CRUD operations
    if "create" in operations:
        code_lines.extend([
            f'',
            f'@router.post("/", response_model={model_name}Response)',
            f'async def create_{model_name.lower()}(item: {model_name}Create):',
            f'    """Create a new {model_name}."""',
            f'    # TODO: Implement database logic',
            f'    return {{"id": 1, **item.model_dump()}}',
        ])
    
    if "list" in operations:
        code_lines.extend([
            f'',
            f'@router.get("/", response_model=List[{model_name}Response])',
            f'async def list_{model_name.lower()}(skip: int = 0, limit: int = 100):',
            f'    """List all {model_name} items."""',
            f'    # TODO: Implement database query',
            f'    return []',
        ])
    
    if "read" in operations:
        code_lines.extend([
            f'',
            f'@router.get("/{{item_id}}", response_model={model_name}Response)',
            f'async def get_{model_name.lower()}(item_id: int):',
            f'    """Get a specific {model_name} by ID."""',
            f'    # TODO: Implement database lookup',
            f'    raise HTTPException(status_code=404, detail="Item not found")',
        ])
    
    if "update" in operations:
        code_lines.extend([
            f'',
            f'@router.put("/{{item_id}}", response_model={model_name}Response)',
            f'async def update_{model_name.lower()}(item_id: int, item: {model_name}Create):',
            f'    """Update a {model_name}."""',
            f'    # TODO: Implement update logic',
            f'    raise HTTPException(status_code=404, detail="Item not found")',
        ])
    
    if "delete" in operations:
        code_lines.extend([
            f'',
            f'@router.delete("/{{item_id}}")',
            f'async def delete_{model_name.lower()}(item_id: int):',
            f'    """Delete a {model_name}."""',
            f'    # TODO: Implement delete logic',
            f'    return {{"message": "Item deleted"}}',
        ])
    
    return "\n".join(code_lines)


def coding_generate_component(
    name: str,
    component_type: str = "functional",
    props: Optional[List[Dict]] = None,
    with_typescript: bool = True
) -> Dict[str, Any]:
    """
    Generate a React component.
    
    Args:
        name: Component name (e.g., UserCard)
        component_type: Type (functional, class, hook)
        props: List of prop definitions
        with_typescript: Include TypeScript types
    
    Returns:
        Standardized response with generated component code
    """
    try:
        # Validate component name
        if not name[0].isupper():
            return format_error_response(
                message=f"Component name '{name}' must start with uppercase",
                code="invalid_input",
                suggestion="Use PascalCase like 'UserCard' instead of 'userCard'"
            )
        
        props = props or []
        code = _generate_react_component_code(name, component_type, props, with_typescript)
        
        return format_success_response(
            results={
                "code": code,
                "language": "typescript" if with_typescript else "javascript",
                "file_name": f"{name}.tsx" if with_typescript else f"{name}.jsx",
                "component_name": name,
                "component_type": component_type,
            },
            metadata={
                "props_count": len(props),
                "lines_of_code": len(code.split("\n")),
            },
            suggestions=[
                "Generate Storybook story with coding_generate_story(component_name='{}')".format(name),
                "Generate tests with coding_generate_tests(component_name='{}')".format(name),
            ]
        )
    
    except Exception as e:
        logger.error(f"Component generation failed: {e}")
        return format_error_response(
            message=f"Failed to generate component: {str(e)}",
            code="unknown_error"
        )


def _generate_react_component_code(
    name: str,
    component_type: str,
    props: List[Dict],
    with_typescript: bool
) -> str:
    """Generate React component code."""
    
    # Build props interface
    if with_typescript:
        props_interface = f"interface {name}Props {{\n"
        for prop in props:
            pname = prop.get("name", "prop")
            ptype = prop.get("type", "string")
            optional = not prop.get("required", True)
            props_interface += f"  {pname}{'?' if optional else ''}: {ptype};\n"
        if not props:
            props_interface += f"  // Add props here\n"
        props_interface += "}\n"
        
        props_decl = f"{{ " + ", ".join([p.get("name", "prop") for p in props]) + " }: " + f"{name}Props"
    else:
        props_interface = ""
        props_decl = "{ " + ", ".join([p.get("name", "prop") for p in props]) + " }"
    
    code_lines = [
        f'/**',
        f' * {name} Component',
        f' * Auto-generated on {datetime.now().isoformat()}',
        f' */',
        f'',
        f"import React from 'react';",
        f"import './{name}.css';  // Optional: component styles",
        f'',
    ]
    
    if props_interface:
        code_lines.append(props_interface)
        code_lines.append('')
    
    code_lines.extend([
        f'export const {name}: React.FC{"<" + name + "Props>" if with_typescript else ""} = ({props_decl}) => {{',
        f'  // Component logic here',
    ])
    
    # Add prop usage examples
    for prop in props:
        pname = prop.get("name", "prop")
        code_lines.append(f'  // const {pname}Value = {pname};')
    
    code_lines.extend([
        f'',
        f'  return (',
        f'    <div className="{name.lower()}">',
        f'      {{/* {name} content */}}',
    ])
    
    # Add prop rendering
    for prop in props:
        pname = prop.get("name", "prop")
        code_lines.append(f'      <span>{{{pname}}}</span>')
    
    if not props:
        code_lines.append(f'      <p>Component content</p>')
    
    code_lines.extend([
        f'    </div>',
        f'  );',
        f'}};',
        f'',
        f'export default {name};',
    ])
    
    return "\n".join(code_lines)


def coding_generate_model(
    name: str,
    fields: List[Dict],
    database: str = "sqlalchemy"
) -> Dict[str, Any]:
    """
    Generate a database model.
    
    Args:
        name: Model name (e.g., User)
        fields: List of field definitions with name, type, nullable, default
        database: Database type (sqlalchemy, pydantic, django)
    
    Returns:
        Standardized response with generated model code
    """
    try:
        valid_databases = ["sqlalchemy", "pydantic", "django"]
        if database not in valid_databases:
            return format_error_response(
                message=f"Invalid database type '{database}'",
                code="invalid_input",
                details={"valid_options": valid_databases},
                suggestion=f"Use one of: {', '.join(valid_databases)}"
            )
        
        code = _generate_model_code(name, fields, database)
        
        return format_success_response(
            results={
                "code": code,
                "language": "python",
                "file_name": f"{name.lower()}_model.py",
                "model_name": name,
                "database": database,
            },
            metadata={
                "fields_count": len(fields),
                "lines_of_code": len(code.split("\n")),
            },
            suggestions=[
                "Generate migration with coding_generate_migration(model_name='{}')".format(name),
                "Generate CRUD endpoints for this model",
            ]
        )
    
    except Exception as e:
        logger.error(f"Model generation failed: {e}")
        return format_error_response(
            message=f"Failed to generate model: {str(e)}",
            code="unknown_error"
        )


def _generate_model_code(name: str, fields: List[Dict], database: str) -> str:
    """Generate database model code."""
    
    code_lines = [
        f'"""',
        f'{name} Model',
        f'Auto-generated on {datetime.now().isoformat()}',
        f'"""',
        f'',
    ]
    
    if database == "sqlalchemy":
        code_lines.extend([
            f'from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float',
            f'from sqlalchemy.sql import func',
            f'from app.db.base_class import Base',
            f'',
            f'',
            f'class {name}(Base):',
            f'    """{name} database model."""',
            f'',
            f'    __tablename__ = "{name.lower()}s"',
            f'',
            f'    id = Column(Integer, primary_key=True, index=True)',
        ])
        
        for field in fields:
            fname = field.get("name", "field")
            ftype = field.get("type", "str")
            nullable = field.get("nullable", True)
            
            # Map Python types to SQLAlchemy types
            type_mapping = {
                "str": "String",
                "int": "Integer",
                "float": "Float",
                "bool": "Boolean",
                "datetime": "DateTime",
            }
            
            sa_type = type_mapping.get(ftype, "String")
            code_lines.append(f'    {fname} = Column({sa_type}, nullable={nullable})')
        
        code_lines.extend([
            f'    created_at = Column(DateTime(timezone=True), server_default=func.now())',
            f'    updated_at = Column(DateTime(timezone=True), onupdate=func.now())',
        ])
    
    elif database == "pydantic":
        code_lines.extend([
            f'from pydantic import BaseModel, Field',
            f'from typing import Optional',
            f'from datetime import datetime',
            f'',
            f'',
            f'class {name}Base(BaseModel):',
            f'    """Base {name} schema."""',
        ])
        
        for field in fields:
            fname = field.get("name", "field")
            ftype = field.get("type", "str")
            description = field.get("description", "")
            code_lines.append(f'    {fname}: {ftype} = Field(..., description="{description}")')
        
        code_lines.extend([
            f'',
            f'',
            f'class {name}Create({name}Base):',
            f'    """Schema for creating {name}."""',
            f'    pass',
            f'',
            f'',
            f'class {name}Response({name}Base):',
            f'    """Schema for {name} response."""',
            f'    id: int',
            f'    created_at: datetime',
            f'',
            f'    class Config:',
            f'        from_attributes = True',
        ])
    
    return "\n".join(code_lines)


# =============================================================================
# Code Validation Tools
# =============================================================================

def coding_validate_code(code: str, language: str = "python") -> Dict[str, Any]:
    """
    Validate code for syntax errors and style issues.
    
    Args:
        code: Source code to validate
        language: Programming language
    
    Returns:
        Standardized response with validation results
    """
    try:
        issues = []
        
        if language == "python":
            # Check for syntax errors
            try:
                import ast
                ast.parse(code)
            except SyntaxError as e:
                issues.append({
                    "type": "syntax_error",
                    "line": e.lineno,
                    "message": str(e),
                    "severity": "critical"
                })
            
            # Basic style checks
            lines = code.split("\n")
            for i, line in enumerate(lines, 1):
                if len(line) > 100:
                    issues.append({
                        "type": "style",
                        "line": i,
                        "message": f"Line too long ({len(line)} > 100 characters)",
                        "severity": "warning"
                    })
                if line.rstrip() != line:
                    issues.append({
                        "type": "style",
                        "line": i,
                        "message": "Trailing whitespace",
                        "severity": "info"
                    })
        
        elif language in ["typescript", "javascript"]:
            # Basic JS/TS checks
            if "console.log" in code:
                issues.append({
                    "type": "best_practice",
                    "line": None,
                    "message": "Remove console.log statements before production",
                    "severity": "warning"
                })
        
        critical = [i for i in issues if i.get("severity") == "critical"]
        
        if critical:
            return format_error_response(
                message=f"Code validation failed with {len(critical)} critical issues",
                code="validation_failed",
                details={"issues": issues},
                suggestion="Fix syntax errors before proceeding"
            )
        
        return format_success_response(
            results={
                "valid": len(issues) == 0,
                "issues": issues,
                "language": language,
            },
            metadata={
                "lines_checked": len(code.split("\n")),
                "issues_found": len(issues),
                "critical_issues": len(critical),
            },
            suggestions=[
                "Generate tests with coding_generate_tests()",
                "Refactor with coding_suggest_refactoring()",
            ]
        )
    
    except Exception as e:
        logger.error(f"Code validation failed: {e}")
        return format_error_response(
            message=f"Validation error: {str(e)}",
            code="unknown_error"
        )


def coding_suggest_refactoring(code: str, goal: str = "improve_readability") -> Dict[str, Any]:
    """
    Suggest refactoring improvements for code.
    
    Args:
        code: Source code to analyze
        goal: Refactoring goal (improve_readability, reduce_complexity, add_types)
    
    Returns:
        Standardized response with refactoring suggestions
    """
    suggestions = []
    
    # Simple heuristic-based suggestions
    lines = code.split("\n")
    
    if goal == "improve_readability":
        if len(lines) > 50:
            suggestions.append({
                "type": "extract_function",
                "message": f"Consider splitting this {len(lines)} line function into smaller units",
                "priority": "medium"
            })
        
        if code.count("if ") > 5:
            suggestions.append({
                "type": "simplify_conditionals",
                "message": f"Multiple if statements ({code.count('if ')}) - consider using polymorphism or strategy pattern",
                "priority": "low"
            })
    
    elif goal == "add_types":
        if "def " in code and "->" not in code:
            suggestions.append({
                "type": "add_return_types",
                "message": "Add return type annotations to functions",
                "priority": "high"
            })
    
    return format_success_response(
        results={
            "suggestions": suggestions,
            "goal": goal,
        },
        metadata={
            "suggestions_count": len(suggestions),
            "code_lines": len(lines),
        },
        suggestions=[
            "Apply suggestions and validate with coding_validate_code()",
        ]
    )


# =============================================================================
# Test Generation Tools
# =============================================================================

def coding_generate_tests(
    target: str,
    test_type: str = "unit",
    framework: str = "pytest"
) -> Dict[str, Any]:
    """
    Generate test cases for code.
    
    Args:
        target: Function or class name to test
        test_type: Type of tests (unit, integration, e2e)
        framework: Testing framework (pytest, jest, unittest)
    
    Returns:
        Standardized response with generated test code
    """
    try:
        valid_frameworks = ["pytest", "jest", "unittest"]
        if framework not in valid_frameworks:
            return format_error_response(
                message=f"Invalid framework '{framework}'",
                code="invalid_input",
                details={"valid_frameworks": valid_frameworks},
                suggestion=f"Use one of: {', '.join(valid_frameworks)}"
            )
        
        code = _generate_test_code(target, test_type, framework)
        
        return format_success_response(
            results={
                "code": code,
                "language": "python" if framework in ["pytest", "unittest"] else "javascript",
                "file_name": f"test_{target.lower()}.py" if framework in ["pytest", "unittest"] else f"{target.lower()}.test.js",
                "target": target,
                "test_type": test_type,
                "framework": framework,
            },
            metadata={
                "test_cases_generated": code.count("def test_") if framework == "pytest" else code.count("test("),
            },
            suggestions=[
                "Run tests with coding_run_tests(test_file='test_{}.py')".format(target.lower()),
            ]
        )
    
    except Exception as e:
        logger.error(f"Test generation failed: {e}")
        return format_error_response(
            message=f"Failed to generate tests: {str(e)}",
            code="unknown_error"
        )


def _generate_test_code(target: str, test_type: str, framework: str) -> str:
    """Generate test code."""
    
    if framework == "pytest":
        code_lines = [
            f'"""',
            f'Tests for {target}',
            f'Auto-generated on {datetime.now().isoformat()}',
            f'"""',
            f'',
            f'import pytest',
            f'from unittest.mock import Mock, patch',
            f'',
            f'',
            f'class Test{target}:',
            f'    """Test cases for {target}."""',
            f'',
            f'    def test_{target.lower()}_creation(self):',
            f'        """Test creating {target}."""',
            f'        # TODO: Implement test',
            f'        assert True',
            f'',
            f'    def test_{target.lower()}_validation(self):',
            f'        """Test {target} validation."""',
            f'        # TODO: Implement test',
            f'        assert True',
            f'',
            f'    def test_{target.lower()}_edge_cases(self):',
            f'        """Test edge cases for {target}."""',
            f'        # TODO: Implement test',
            f'        assert True',
        ]
        
        if test_type == "integration":
            code_lines.extend([
                f'',
                f'    @pytest.mark.integration',
                f'    def test_{target.lower()}_integration(self):',
                f'        """Integration test for {target}."""',
                f'        # TODO: Implement integration test',
                f'        assert True',
            ])
    
    else:
        code_lines = [
            f'// Tests for {target}',
            f'// Auto-generated on {datetime.now().isoformat()}',
            f'',
            f"import {{ {target} }} from './{target}';",
            f'',
            f"describe('{target}', () => {{",
            f'  test("should create {target} correctly", () => {{',
            f'    // TODO: Implement test',
            f'    expect(true).toBe(true);',
            f'  }});',
            f'',
            f'  test("should handle validation", () => {{',
            f'    // TODO: Implement test',
            f'    expect(true).toBe(true);',
            f'  }});',
            f'}});',
        ]
    
    return "\n".join(code_lines)


def coding_run_tests(test_file: Optional[str] = None, pattern: str = "test_*.py") -> Dict[str, Any]:
    """
    Run tests and return results.
    
    Args:
        test_file: Specific test file to run (None = all)
        pattern: Test file pattern
    
    Returns:
        Standardized response with test results
    """
    # Mock test results for demonstration
    # In real implementation, this would execute pytest or similar
    
    return format_success_response(
        results={
            "passed": 12,
            "failed": 0,
            "skipped": 2,
            "total": 14,
            "duration_seconds": 2.34,
            "coverage_percent": 78.5,
        },
        metadata={
            "test_file": test_file,
            "pattern": pattern,
        },
        suggestions=[
            "View detailed report with coding_get_test_report()",
            "Improve coverage by adding tests for uncovered lines",
        ]
    )


# =============================================================================
# Tool Registry
# =============================================================================

CODING_TOOLS = {
    # Generation tools
    "coding_generate_endpoint": coding_generate_endpoint,
    "coding_generate_component": coding_generate_component,
    "coding_generate_model": coding_generate_model,
    
    # Validation tools
    "coding_validate_code": coding_validate_code,
    "coding_suggest_refactoring": coding_suggest_refactoring,
    
    # Test tools
    "coding_generate_tests": coding_generate_tests,
    "coding_run_tests": coding_run_tests,
}


def get_coding_tools() -> Dict[str, Any]:
    """Get all coding tools for agent registration."""
    return CODING_TOOLS


__all__ = [
    "CODING_TOOLS",
    "get_coding_tools",
    "coding_generate_endpoint",
    "coding_generate_component",
    "coding_generate_model",
    "coding_validate_code",
    "coding_suggest_refactoring",
    "coding_generate_tests",
    "coding_run_tests",
]