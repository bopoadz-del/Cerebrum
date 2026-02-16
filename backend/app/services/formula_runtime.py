"""
Formula Runtime Service

Provides safe evaluation of mathematical formulas with:
- JSON-based formula library loading
- Lazy loading with caching
- Restricted eval environment (no open/import/exec)
- Input validation and error handling
"""

from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# =============================================================================
# Formula Definition Models
# =============================================================================

@dataclass
class FormulaInput:
    """Input parameter definition for a formula."""
    name: str
    type: str = "float"
    unit: str = ""
    required: bool = True
    description: str = ""
    default: Optional[Any] = None


@dataclass
class FormulaOutput:
    """Output parameter definition for a formula."""
    name: str
    type: str = "float"
    unit: str = ""


@dataclass
class FormulaDefinition:
    """Complete formula definition with metadata."""
    id: str
    name: str
    domain: str
    description: str
    formula_expression: str
    inputs: List[FormulaInput] = field(default_factory=list)
    outputs: List[FormulaOutput] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FormulaDefinition:
        """Create FormulaDefinition from dictionary."""
        inputs = [
            FormulaInput(**inp) if isinstance(inp, dict) else inp
            for inp in data.get("inputs", [])
        ]
        outputs = [
            FormulaOutput(**out) if isinstance(out, dict) else out
            for out in data.get("outputs", [])
        ]
        
        return cls(
            id=data["id"],
            name=data["name"],
            domain=data.get("domain", "general"),
            description=data.get("description", ""),
            formula_expression=data["formula_expression"],
            inputs=inputs,
            outputs=outputs,
            references=data.get("references", []),
            tags=data.get("tags", []),
            version=data.get("version", "1.0.0"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excludes expression for security if needed)."""
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "inputs": [
                {
                    "name": inp.name,
                    "type": inp.type,
                    "unit": inp.unit,
                    "required": inp.required,
                    "description": inp.description,
                }
                for inp in self.inputs
            ],
            "outputs": [
                {"name": out.name, "type": out.type, "unit": out.unit}
                for out in self.outputs
            ],
            "references": self.references,
            "tags": self.tags,
            "version": self.version,
        }


# =============================================================================
# Formula Library
# =============================================================================

class FormulaLibrary:
    """In-memory cache of loaded formulas."""
    
    _instance: Optional[FormulaLibrary] = None
    _formulas: Dict[str, FormulaDefinition] = {}
    _loaded: bool = False
    
    def __new__(cls) -> FormulaLibrary:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get(self, formula_id: str) -> Optional[FormulaDefinition]:
        """Get a formula by ID."""
        return self._formulas.get(formula_id)
    
    def get_all(self) -> List[FormulaDefinition]:
        """Get all loaded formulas."""
        return list(self._formulas.values())
    
    def get_by_domain(self, domain: str) -> List[FormulaDefinition]:
        """Get formulas filtered by domain."""
        return [f for f in self._formulas.values() if f.domain == domain]
    
    def set_formulas(self, formulas: List[FormulaDefinition]) -> None:
        """Set the formula cache."""
        self._formulas = {f.id: f for f in formulas}
        self._loaded = True
    
    def clear(self) -> None:
        """Clear the formula cache."""
        self._formulas.clear()
        self._loaded = False
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded


# =============================================================================
# Safe Evaluator
# =============================================================================

# Restricted builtins for formula evaluation
SAFE_BUILTINS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
    "enumerate": enumerate,
    "len": len,
    "range": range,
}

# Math module functions and constants
SAFE_MATH = {
    name: getattr(math, name)
    for name in dir(math)
    if not name.startswith("_")
}


def create_safe_env(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Create a safe evaluation environment."""
    env = {}
    # Add safe builtins
    env.update(SAFE_BUILTINS)
    # Add math functions and constants
    env.update(SAFE_MATH)
    # Add user inputs
    env.update(inputs)
    return env


def eval_formula(
    formula_expression: str,
    inputs: Dict[str, Any],
    formula_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Safely evaluate a formula expression.
    
    Args:
        formula_expression: The formula as a Python expression string
        inputs: Dictionary of input values
        formula_id: Optional formula ID for error reporting
        
    Returns:
        Dictionary with either:
        - {"output_values": {"result": value}, "formula_id": id}
        - {"error": "...", "formula_id": id}
    """
    # Security: Check for dangerous patterns
    dangerous_patterns = ["__import__", "import", "open", "exec", "eval", "compile", 
                         "__builtins__", "__globals__", "__class__", "__base__",
                         "os.", "sys.", "subprocess", "file", "write", "read"]
    
    expr_lower = formula_expression.lower()
    for pattern in dangerous_patterns:
        if pattern in expr_lower:
            logger.warning(f"Blocked dangerous pattern '{pattern}' in formula: {formula_id}")
            return {
                "error": f"Security violation: '{pattern}' is not allowed",
                "formula_id": formula_id,
            }
    
    # Create safe environment
    safe_env = create_safe_env(inputs)
    
    try:
        # Evaluate the expression
        result = eval(formula_expression, {"__builtins__": {}}, safe_env)
        
        return {
            "output_values": {"result": result},
            "formula_id": formula_id,
        }
    except NameError as e:
        logger.warning(f"Formula evaluation name error: formula={formula_id} error={e}")
        return {
            "error": f"Unknown variable or function: {e}",
            "formula_id": formula_id,
        }
    except ZeroDivisionError:
        logger.warning(f"Formula evaluation division by zero: formula={formula_id}")
        return {
            "error": "Division by zero",
            "formula_id": formula_id,
        }
    except Exception as e:
        logger.error(f"Formula evaluation error: formula={formula_id} error={e}")
        return {
            "error": f"Evaluation error: {type(e).__name__}: {e}",
            "formula_id": formula_id,
        }


# =============================================================================
# Formula Loader
# =============================================================================

def _get_default_formulas_path() -> Path:
    """Get the default path to the formulas JSON file."""
    # Path relative to the backend/app directory
    # In Docker: /app/app/services/ -> /app/data/formulas/
    backend_dir = Path(__file__).parent.parent.parent  # app -> backend
    return backend_dir / "data" / "formulas" / "initial_library.json"


def _load_formulas_from_file(file_path: Union[str, Path]) -> List[FormulaDefinition]:
    """
    Load formulas from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        List of FormulaDefinition objects
    """
    path = Path(file_path)
    
    if not path.exists():
        logger.error(f"Formula library file not found: {path}")
        return []
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        formulas_data = data.get("formulas", [])
        formulas = [FormulaDefinition.from_dict(f) for f in formulas_data]
        
        logger.info(f"Loaded {len(formulas)} formulas from {path}")
        return formulas
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in formula library: {path} error={e}")
        return []
    except Exception as e:
        logger.error(f"Failed to load formula library: {path} error={e}")
        return []


def get_formulas(
    settings_path: Optional[str] = None,
    force_reload: bool = False,
) -> List[FormulaDefinition]:
    """
    Get all formulas, loading from file if not already cached.
    
    Args:
        settings_path: Optional path to formulas JSON file
        force_reload: If True, reload from file even if cached
        
    Returns:
        List of FormulaDefinition objects
    """
    library = FormulaLibrary()
    
    if library.is_loaded and not force_reload:
        return library.get_all()
    
    # Determine file path
    if settings_path:
        file_path = Path(settings_path)
    else:
        # Check environment variable
        env_path = os.getenv("INITIAL_FORMULAS_PATH")
        if env_path:
            file_path = Path(env_path)
        else:
            file_path = _get_default_formulas_path()
    
    # Load formulas
    formulas = _load_formulas_from_file(file_path)
    library.set_formulas(formulas)
    
    return formulas


def get_formula_by_id(formula_id: str) -> Optional[FormulaDefinition]:
    """Get a single formula by ID (loads library if needed)."""
    library = FormulaLibrary()
    if not library.is_loaded:
        get_formulas()
    return library.get(formula_id)


def clear_formula_cache() -> None:
    """Clear the formula cache (useful for testing)."""
    FormulaLibrary().clear()


# =============================================================================
# Convenience Functions
# =============================================================================

def evaluate_formula_by_id(
    formula_id: str,
    inputs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate a formula by its ID with the given inputs.
    
    Args:
        formula_id: The formula ID
        inputs: Dictionary of input values
        
    Returns:
        Evaluation result dictionary
    """
    formula = get_formula_by_id(formula_id)
    
    if formula is None:
        return {
            "error": f"Formula not found: {formula_id}",
            "formula_id": formula_id,
        }
    
    # Validate required inputs
    for inp in formula.inputs:
        if inp.required and inp.name not in inputs:
            return {
                "error": f"Missing required input: {inp.name}",
                "formula_id": formula_id,
            }
    
    return eval_formula(formula.formula_expression, inputs, formula_id)
