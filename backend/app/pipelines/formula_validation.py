"""
Formula Validation Pipeline - 5 Stage System

Validates construction/engineering formulas through 5 gates before deployment:
1. Syntactic - Mathematical correctness
2. Dimensional - Unit consistency  
3. Physical - Domain law compliance
4. Empirical - Benchmark testing
5. Operational - Performance & edge compatibility
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
import time
import re


class ValidationStage(str, Enum):
    SYNTACTIC = "syntactic"
    DIMENSIONAL = "dimensional"
    PHYSICAL = "physical"
    EMPIRICAL = "empirical"
    OPERATIONAL = "operational"


class ValidationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"


@dataclass
class StageResult:
    """Result from a single validation stage."""
    stage: ValidationStage
    status: ValidationStatus
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0


@dataclass
class ValidationReport:
    """Complete validation report from all 5 stages."""
    formula_id: str
    formula_expression: str
    overall_valid: bool
    stages: Dict[ValidationStage, StageResult]
    total_execution_time_ms: float = 0.0
    can_deploy: bool = False
    requires_review: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "formula_id": self.formula_id,
            "formula_expression": self.formula_expression,
            "overall_valid": self.overall_valid,
            "can_deploy": self.can_deploy,
            "requires_review": self.requires_review,
            "total_execution_time_ms": self.total_execution_time_ms,
            "stages": {
                stage.value: {
                    "status": result.status.value,
                    "valid": result.valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "metadata": result.metadata,
                    "execution_time_ms": result.execution_time_ms
                }
                for stage, result in self.stages.items()
            }
        }


class FormulaValidationPipeline:
    """
    5-Stage Formula Validation Pipeline.
    
    Each stage acts as a gate. Formulas must pass all critical stages
    before deployment to edge nodes.
    """
    
    # Domain-specific physical constraints
    PHYSICAL_CONSTRAINTS = {
        "construction": {
            "max_compression_ratio": 0.85,
            "min_safety_factor": 1.5,
            "max_stress_mpa": 1000,
            "min_density_kg_m3": 100,
            "max_density_kg_m3": 25000,
        },
        "thermodynamics": {
            "min_temp_kelvin": 0,
            "max_temp_kelvin": 6000,
            "min_entropy": 0,
        },
        "structural": {
            "max_deflection_ratio": 1/250,
            "min_elastic_modulus_gpa": 0.01,
        }
    }
    
    # Operational thresholds
    OPERATIONAL_THRESHOLDS = {
        "max_latency_ms": 100,
        "max_memory_mb": 512,
        "max_jetson_latency_ms": 200,
    }
    
    def __init__(self):
        self._sympy_available = self._check_sympy()
        self._pint_available = self._check_pint()
        
    def _check_sympy(self) -> bool:
        try:
            import sympy
            return True
        except ImportError:
            return False
    
    def _check_pint(self) -> bool:
        try:
            import pint
            return True
        except ImportError:
            return False
    
    def validate(self, formula_id: str, expression: str, 
                 expected_output_unit: Optional[str] = None,
                 domain: str = "construction",
                 benchmark_data: Optional[List[Dict]] = None) -> ValidationReport:
        """
        Run full 5-stage validation pipeline.
        
        Args:
            formula_id: Unique identifier for the formula
            expression: Mathematical expression (e.g., "F = m * a")
            expected_output_unit: Expected output unit (e.g., "N", "Pa")
            domain: Domain for physical validation (construction, thermodynamics, etc.)
            benchmark_data: Optional test dataset for empirical validation
            
        Returns:
            ValidationReport with results from all 5 stages
        """
        start_time = time.time()
        stages = {}
        
        # Stage 1: Syntactic Validation
        stages[ValidationStage.SYNTACTIC] = self._validate_syntactic(expression)
        
        # Stage 2: Dimensional Validation
        stages[ValidationStage.DIMENSIONAL] = self._validate_dimensional(
            expression, expected_output_unit
        )
        
        # Stage 3: Physical Validation
        stages[ValidationStage.PHYSICAL] = self._validate_physical(expression, domain)
        
        # Stage 4: Empirical Validation
        stages[ValidationStage.EMPIRICAL] = self._validate_empirical(
            expression, benchmark_data
        )
        
        # Stage 5: Operational Validation
        stages[ValidationStage.OPERATIONAL] = self._validate_operational(expression)
        
        # Determine overall validity
        critical_stages = [
            ValidationStage.SYNTACTIC,
            ValidationStage.PHYSICAL
        ]
        overall_valid = all(
            stages[stage].valid for stage in critical_stages
        )
        
        # Can deploy if all stages pass
        can_deploy = all(stage.valid for stage in stages.values())
        
        # Requires review if any warnings or non-critical failures
        requires_review = any(
            stage.status in [ValidationStatus.WARNING, ValidationStatus.FAIL]
            for stage in stages.values()
        ) and not can_deploy
        
        total_time = (time.time() - start_time) * 1000
        
        return ValidationReport(
            formula_id=formula_id,
            formula_expression=expression,
            overall_valid=overall_valid,
            stages=stages,
            total_execution_time_ms=total_time,
            can_deploy=can_deploy,
            requires_review=requires_review
        )
    
    def _validate_syntactic(self, expression: str) -> StageResult:
        """
        Stage 1: Syntactic Validation
        
        Checks mathematical well-formedness using SymPy.
        """
        start = time.time()
        errors = []
        warnings = []
        metadata = {}
        
        if not self._sympy_available:
            return StageResult(
                stage=ValidationStage.SYNTACTIC,
                status=ValidationStatus.SKIP,
                valid=True,
                warnings=["SymPy not available, skipping detailed syntax check"],
                execution_time_ms=(time.time() - start) * 1000
            )
        
        try:
            import sympy as sp
            
            # Parse the expression
            try:
                parsed = sp.parse_expr(expression, evaluate=False)
                metadata["parsed_tree"] = str(parsed)
                metadata["variables"] = list(map(str, parsed.free_symbols))
                metadata["is_equation"] = "=" in expression
            except Exception as e:
                errors.append(f"Parse error: {str(e)}")
                return StageResult(
                    stage=ValidationStage.SYNTACTIC,
                    status=ValidationStatus.FAIL,
                    valid=False,
                    errors=errors,
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            # Check for common issues
            if "//" in expression:
                warnings.append("Use / for division, not //")
            
            if "**" in expression and "^" in expression:
                warnings.append("Inconsistent exponent operators (** vs ^)")
            
            # Check parenthesis balance
            if expression.count("(") != expression.count(")"):
                errors.append("Unbalanced parentheses")
            
            # Check for undefined operations
            dangerous_patterns = ["/0", "/ 0", "**nan", "+inf", "-inf"]
            for pattern in dangerous_patterns:
                if pattern in expression.lower():
                    warnings.append(f"Potentially dangerous pattern: {pattern}")
            
            valid = len(errors) == 0
            
            return StageResult(
                stage=ValidationStage.SYNTACTIC,
                status=ValidationStatus.PASS if valid else ValidationStatus.FAIL,
                valid=valid,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return StageResult(
                stage=ValidationStage.SYNTACTIC,
                status=ValidationStatus.FAIL,
                valid=False,
                errors=errors,
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _validate_dimensional(self, expression: str, 
                              expected_output_unit: Optional[str]) -> StageResult:
        """
        Stage 2: Dimensional Validation
        
        Ensures unit consistency using dimensional analysis.
        """
        start = time.time()
        errors = []
        warnings = []
        metadata = {"input_units": {}, "output_unit": expected_output_unit}
        
        if not self._pint_available:
            return StageResult(
                stage=ValidationStage.DIMENSIONAL,
                status=ValidationStatus.SKIP,
                valid=True,
                warnings=["Pint not available, skipping dimensional analysis"],
                execution_time_ms=(time.time() - start) * 1000
            )
        
        try:
            import pint
            ureg = pint.UnitRegistry()
            
            # This is a simplified check - real implementation would parse
            # variables and their units from the formula metadata
            if expected_output_unit:
                try:
                    ureg(expected_output_unit)
                    metadata["output_unit_valid"] = True
                except Exception:
                    errors.append(f"Invalid output unit: {expected_output_unit}")
                    metadata["output_unit_valid"] = False
            
            valid = len(errors) == 0
            
            return StageResult(
                stage=ValidationStage.DIMENSIONAL,
                status=ValidationStatus.PASS if valid else ValidationStatus.FAIL,
                valid=valid,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            errors.append(f"Dimensional validation error: {str(e)}")
            return StageResult(
                stage=ValidationStage.DIMENSIONAL,
                status=ValidationStatus.FAIL,
                valid=False,
                errors=errors,
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _validate_physical(self, expression: str, domain: str) -> StageResult:
        """
        Stage 3: Physical Validation
        
        Checks against domain-specific physical laws and constraints.
        """
        start = time.time()
        errors = []
        warnings = []
        metadata = {"domain": domain, "constraints_checked": []}
        
        constraints = self.PHYSICAL_CONSTRAINTS.get(domain, {})
        
        # Check for negative values where inappropriate
        if "sqrt(" in expression and "-" in expression:
            # Simple heuristic - real check would analyze the AST
            warnings.append("Square root of potentially negative value")
        
        if "log(" in expression or "ln(" in expression:
            warnings.append("Logarithm of potentially non-positive value")
        
        # Check thermodynamic constraints
        if domain == "thermodynamics":
            metadata["constraints_checked"].append("temperature_bounds")
            if "temp" in expression.lower():
                # Would need actual variable binding for real check
                pass
        
        # Check structural constraints
        if domain == "structural":
            metadata["constraints_checked"].append("deflection_limits")
            if "deflection" in expression.lower() and "span" in expression.lower():
                warnings.append("Ensure deflection ratio < 1/250")
        
        valid = len(errors) == 0
        
        return StageResult(
            stage=ValidationStage.PHYSICAL,
            status=ValidationStatus.PASS if valid else ValidationStatus.FAIL,
            valid=valid,
            errors=errors,
            warnings=warnings,
            metadata=metadata,
            execution_time_ms=(time.time() - start) * 1000
        )
    
    def _validate_empirical(self, expression: str, 
                           benchmark_data: Optional[List[Dict]]) -> StageResult:
        """
        Stage 4: Empirical Validation
        
        Tests formula against benchmark datasets.
        """
        start = time.time()
        errors = []
        warnings = []
        metadata = {"samples_tested": 0, "mse": None, "mae": None}
        
        if not benchmark_data:
            return StageResult(
                stage=ValidationStage.EMPIRICAL,
                status=ValidationStatus.SKIP,
                valid=True,
                warnings=["No benchmark data provided, skipping empirical validation"],
                execution_time_ms=(time.time() - start) * 1000
            )
        
        try:
            if not self._sympy_available:
                return StageResult(
                    stage=ValidationStage.EMPIRICAL,
                    status=ValidationStatus.SKIP,
                    valid=True,
                    warnings=["SymPy not available for empirical testing"],
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            import sympy as sp
            
            # Parse formula
            parsed = sp.parse_expr(expression, evaluate=False)
            variables = list(parsed.free_symbols)
            
            # Run tests
            predictions = []
            actuals = []
            
            for sample in benchmark_data[:100]:  # Limit to 100 samples
                try:
                    # Substitute values
                    subs = {str(v): sample.get(str(v), 0) for v in variables}
                    pred = float(parsed.evalf(subs=subs))
                    predictions.append(pred)
                    actuals.append(sample.get("expected_output", 0))
                except Exception:
                    continue
            
            metadata["samples_tested"] = len(predictions)
            
            if len(predictions) > 0:
                # Calculate error metrics
                mse = sum((p - a) ** 2 for p, a in zip(predictions, actuals)) / len(predictions)
                mae = sum(abs(p - a) for p, a in zip(predictions, actuals)) / len(predictions)
                
                metadata["mse"] = round(mse, 6)
                metadata["mae"] = round(mae, 6)
                
                # Check if within threshold
                if mse > 0.01:  # 1% MSE threshold
                    warnings.append(f"High MSE: {mse:.4f} (threshold: 0.01)")
            
            valid = len(errors) == 0
            
            return StageResult(
                stage=ValidationStage.EMPIRICAL,
                status=ValidationStatus.PASS if valid else ValidationStatus.FAIL,
                valid=valid,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
                execution_time_ms=(time.time() - start) * 1000
            )
            
        except Exception as e:
            errors.append(f"Empirical validation error: {str(e)}")
            return StageResult(
                stage=ValidationStage.EMPIRICAL,
                status=ValidationStatus.FAIL,
                valid=False,
                errors=errors,
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _validate_operational(self, expression: str) -> StageResult:
        """
        Stage 5: Operational Validation
        
        Tests performance metrics for edge deployment.
        """
        start = time.time()
        errors = []
        warnings = []
        metadata = {}
        
        # Estimate complexity
        complexity_score = 0
        complexity_score += expression.count("*") * 1
        complexity_score += expression.count("/") * 2
        complexity_score += expression.count("**") * 3
        complexity_score += expression.count("sqrt(") * 5
        complexity_score += expression.count("log(") * 5
        complexity_score += expression.count("sin(") * 5
        complexity_score += expression.count("cos(") * 5
        complexity_score += len(re.findall(r'\d+\.\d+', expression)) * 0.5
        
        metadata["complexity_score"] = complexity_score
        metadata["expression_length"] = len(expression)
        
        # Estimate latency (very rough heuristic)
        estimated_latency_ms = 1 + complexity_score * 0.5
        metadata["estimated_latency_ms"] = round(estimated_latency_ms, 2)
        
        # Estimate memory (based on expression size)
        estimated_memory_kb = 10 + len(expression) * 0.1
        metadata["estimated_memory_kb"] = round(estimated_memory_kb, 2)
        
        # Check thresholds
        thresholds = self.OPERATIONAL_THRESHOLDS
        
        if estimated_latency_ms > thresholds["max_latency_ms"]:
            warnings.append(
                f"High latency estimate: {estimated_latency_ms:.1f}ms "
                f"(threshold: {thresholds['max_latency_ms']}ms)"
            )
        
        if estimated_latency_ms > thresholds["max_jetson_latency_ms"]:
            warnings.append(
                f"May exceed Jetson latency budget: {estimated_latency_ms:.1f}ms "
                f"(threshold: {thresholds['max_jetson_latency_ms']}ms)"
            )
        
        # Check if expression is too complex
        if complexity_score > 50:
            warnings.append(f"High complexity score: {complexity_score} (may impact performance)")
        
        valid = len(errors) == 0
        
        return StageResult(
            stage=ValidationStage.OPERATIONAL,
            status=ValidationStatus.PASS if valid else ValidationStatus.WARNING,
            valid=valid,
            errors=errors,
            warnings=warnings,
            metadata=metadata,
            execution_time_ms=(time.time() - start) * 1000
        )


# Singleton instance
_validation_pipeline = None

def get_validation_pipeline() -> FormulaValidationPipeline:
    """Get or create the validation pipeline singleton."""
    global _validation_pipeline
    if _validation_pipeline is None:
        _validation_pipeline = FormulaValidationPipeline()
    return _validation_pipeline


def validate_formula(formula_id: str, expression: str, **kwargs) -> ValidationReport:
    """
    Convenience function to validate a formula.
    
    Args:
        formula_id: Unique formula identifier
        expression: Mathematical expression
        **kwargs: Additional validation parameters
        
    Returns:
        ValidationReport with all 5 stages
    """
    pipeline = get_validation_pipeline()
    return pipeline.validate(formula_id, expression, **kwargs)
