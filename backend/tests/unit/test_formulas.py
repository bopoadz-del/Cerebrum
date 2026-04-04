"""
Unit Tests for Formula Runtime

Tests run without Postgres/Redis dependencies.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from app.services.formula_runtime import (
    FormulaDefinition,
    FormulaInput,
    FormulaLibrary,
    FormulaOutput,
    _load_formulas_from_file,
    clear_formula_cache,
    create_safe_env,
    eval_formula,
    evaluate_formula_by_id,
    get_formulas,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_formula_cache():
    """Reset formula cache before each test."""
    clear_formula_cache()
    yield
    clear_formula_cache()


@pytest.fixture
def sample_formulas_json():
    """Sample formulas JSON data."""
    return {
        "version": "1.0.0",
        "formulas": [
            {
                "id": "test_add",
                "name": "Test Addition",
                "domain": "test",
                "description": "Simple addition test",
                "formula_expression": "a + b",
                "inputs": [
                    {"name": "a", "type": "float", "required": True},
                    {"name": "b", "type": "float", "required": True},
                ],
                "outputs": [{"name": "result", "type": "float"}],
                "references": [],
                "tags": ["test"],
            },
            {
                "id": "test_math",
                "name": "Test Math Functions",
                "domain": "test",
                "description": "Tests math module access",
                "formula_expression": "sqrt(x) + pi",
                "inputs": [{"name": "x", "type": "float", "required": True}],
                "outputs": [{"name": "result", "type": "float"}],
                "references": [],
                "tags": ["test", "math"],
            },
        ],
    }


@pytest.fixture
def temp_formulas_file(sample_formulas_json):
    """Create a temporary formulas JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_formulas_json, f)
        path = f.name
    yield path
    os.unlink(path)


# =============================================================================
# Formula Loading Tests
# =============================================================================

class TestLoadFormulas:
    """Tests for loading formulas from JSON."""

    def test_load_formulas_from_json(self, temp_formulas_file):
        """Test loading formulas from a JSON file."""
        formulas = _load_formulas_from_file(temp_formulas_file)
        
        assert len(formulas) == 2
        assert isinstance(formulas[0], FormulaDefinition)
        assert formulas[0].id == "test_add"
        assert formulas[1].id == "test_math"

    def test_load_formulas_file_not_found(self):
        """Test handling of missing file."""
        formulas = _load_formulas_from_file("/nonexistent/path/formulas.json")
        assert formulas == []

    def test_load_formulas_invalid_json(self):
        """Test handling of invalid JSON."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            path = f.name
        
        try:
            formulas = _load_formulas_from_file(path)
            assert formulas == []
        finally:
            os.unlink(path)

    def test_formula_definition_from_dict(self):
        """Test creating FormulaDefinition from dictionary."""
        data = {
            "id": "test_formula",
            "name": "Test Formula",
            "domain": "test",
            "description": "A test formula",
            "formula_expression": "x * 2",
            "inputs": [
                {"name": "x", "type": "float", "unit": "m", "required": True}
            ],
            "outputs": [{"name": "result", "type": "float", "unit": "m"}],
            "references": ["Ref1"],
            "tags": ["test"],
        }
        
        formula = FormulaDefinition.from_dict(data)
        
        assert formula.id == "test_formula"
        assert formula.name == "Test Formula"
        assert formula.domain == "test"
        assert formula.formula_expression == "x * 2"
        assert len(formula.inputs) == 1
        assert formula.inputs[0].name == "x"
        assert formula.inputs[0].type == "float"
        assert formula.inputs[0].unit == "m"
        assert len(formula.outputs) == 1
        assert formula.references == ["Ref1"]
        assert formula.tags == ["test"]

    def test_formula_to_dict(self):
        """Test converting FormulaDefinition to dictionary."""
        formula = FormulaDefinition(
            id="test",
            name="Test",
            domain="test",
            description="Test formula",
            formula_expression="x + 1",
            inputs=[FormulaInput(name="x", type="float", required=True)],
            outputs=[FormulaOutput(name="result", type="float")],
        )
        
        data = formula.to_dict()
        
        assert data["id"] == "test"
        assert data["name"] == "Test"
        assert "formula_expression" not in data  # Excluded for security
        assert len(data["inputs"]) == 1


# =============================================================================
# Safe Evaluator Tests
# =============================================================================

class TestSafeEvaluator:
    """Tests for the safe formula evaluator."""

    def test_eval_formula_success(self):
        """Test successful formula evaluation."""
        result = eval_formula("a + b", {"a": 5, "b": 3})
        
        assert "error" not in result
        assert result["output_values"]["result"] == 8

    def test_eval_formula_with_math_functions(self):
        """Test formula with math module functions."""
        result = eval_formula("sqrt(16) + pi", {})
        
        assert "error" not in result
        assert abs(result["output_values"]["result"] - (4 + 3.14159)) < 0.001

    def test_eval_formula_error_missing_variable(self):
        """Test error handling for missing variable."""
        result = eval_formula("a + b", {"a": 5})  # b is missing
        
        assert "error" in result
        assert "Unknown variable" in result["error"]

    def test_eval_formula_error_division_by_zero(self):
        """Test error handling for division by zero."""
        result = eval_formula("1 / 0", {})
        
        assert "error" in result
        assert "Division by zero" in result["error"]

    def test_eval_disallows_builtins_import(self):
        """Test that __import__ is blocked."""
        result = eval_formula("__import__('os').system('ls')", {})
        
        assert "error" in result
        assert "Security violation" in result["error"]
        assert "__import__" in result["error"]

    def test_eval_disallows_open(self):
        """Test that open() is blocked."""
        result = eval_formula("open('/etc/passwd').read()", {})
        
        assert "error" in result
        assert "Security violation" in result["error"]

    def test_eval_disallows_exec(self):
        """Test that exec is blocked."""
        result = eval_formula("exec('print(1)')", {})
        
        assert "error" in result
        assert "Security violation" in result["error"]

    def test_eval_disallows_eval(self):
        """Test that nested eval is blocked."""
        result = eval_formula("eval('1+1')", {})
        
        assert "error" in result
        assert "Security violation" in result["error"]

    def test_eval_allows_safe_math(self):
        """Test that safe math operations work."""
        result = eval_formula("max(1, 5, 3) + min(10, 20)", {})
        
        assert "error" not in result
        assert result["output_values"]["result"] == 15

    def test_eval_allows_safe_builtins(self):
        """Test that safe builtins work."""
        result = eval_formula("abs(-5) + round(3.7) + pow(2, 3)", {})
        
        assert "error" not in result
        assert result["output_values"]["result"] == 5 + 4 + 8

    def test_eval_complex_expression(self):
        """Test more complex expressions."""
        result = eval_formula(
            "(length * width * height) + sum([1, 2, 3])",
            {"length": 2, "width": 3, "height": 4}
        )
        
        assert "error" not in result
        assert result["output_values"]["result"] == 24 + 6


# =============================================================================
# Formula Library Tests
# =============================================================================

class TestFormulaLibrary:
    """Tests for the formula library cache."""

    def test_lazy_loading(self, temp_formulas_file):
        """Test that formulas are loaded lazily and cached."""
        # First call should load from file
        formulas1 = get_formulas(settings_path=temp_formulas_file)
        assert len(formulas1) == 2
        
        # Second call should return cached
        formulas2 = get_formulas(settings_path=temp_formulas_file)
        assert len(formulas2) == 2
        
        # Verify it's the same data (from cache)
        library = FormulaLibrary()
        assert library.is_loaded

    def test_get_formula_by_id(self, temp_formulas_file):
        """Test retrieving a specific formula by ID."""
        get_formulas(settings_path=temp_formulas_file)
        
        formula = evaluate_formula_by_id("test_add", {"a": 1, "b": 2})
        assert formula["output_values"]["result"] == 3

    def test_get_formula_not_found(self):
        """Test handling of non-existent formula."""
        result = evaluate_formula_by_id("nonexistent", {})
        
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_force_reload(self, temp_formulas_file):
        """Test force_reload option."""
        get_formulas(settings_path=temp_formulas_file)
        
        # Modify the file
        with open(temp_formulas_file, "w") as f:
            json.dump({"version": "2.0.0", "formulas": []}, f)
        
        # Without force_reload, should return cached
        formulas1 = get_formulas(settings_path=temp_formulas_file)
        assert len(formulas1) == 2
        
        # With force_reload, should reload from file
        formulas2 = get_formulas(settings_path=temp_formulas_file, force_reload=True)
        assert len(formulas2) == 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestFormulaIntegration:
    """Integration tests for the complete formula system."""

    def test_full_evaluation_workflow(self, temp_formulas_file):
        """Test the complete evaluation workflow."""
        # Load formulas
        formulas = get_formulas(settings_path=temp_formulas_file)
        assert len(formulas) == 2
        
        # Evaluate a formula
        result = evaluate_formula_by_id("test_math", {"x": 9})
        
        assert "error" not in result or result.get("output_values") is not None
        expected = 3 + 3.14159  # sqrt(9) + pi
        assert abs(result["output_values"]["result"] - expected) < 0.001

    def test_missing_required_input(self, temp_formulas_file):
        """Test validation of required inputs."""
        get_formulas(settings_path=temp_formulas_file)
        
        # Missing 'b' input
        result = evaluate_formula_by_id("test_add", {"a": 5})
        
        assert "error" in result
        assert "Missing required input" in result["error"]

    def test_concrete_volume_example(self):
        """Test a realistic concrete volume calculation."""
        result = eval_formula(
            "length * width * height",
            {"length": 10.0, "width": 5.0, "height": 0.3}
        )
        
        assert "error" not in result
        assert result["output_values"]["result"] == 15.0  # 10 * 5 * 0.3
