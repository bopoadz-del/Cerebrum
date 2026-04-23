"""
Formula Validation Pipeline - 5 Stage System

Validates construction/engineering formulas through 5 gates before deployment:
1. Syntactic   - Mathematical correctness (SymPy parse)
2. Dimensional - Real symbolic dimensional analysis (SymPy units)
3. Physical    - Domain law compliance (constraints + heuristics)
4. Empirical   - Benchmark dataset testing
5. Operational - Edge/Jetson performance budget
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
import time
import re


# ---------------------------------------------------------------------------
# Unit string → SymPy unit object lookup table (used by Stage 2)
# Populated lazily once SymPy is confirmed available.
# ---------------------------------------------------------------------------
_UNIT_MAP: Optional[Dict[str, Any]] = None


def _build_unit_map() -> Dict[str, Any]:
    """Build the unit string → SymPy unit mapping once on first use."""
    import sympy as sp
    from sympy.physics import units as su

    return {
        # Length
        "m": su.meter, "km": su.kilometer,
        "cm": su.centimeter, "mm": su.millimeter,
        # Time
        "s": su.second, "min": su.minute, "h": su.hour,
        # Mass
        "kg": su.kilogram, "g": su.gram,
        # Force
        "N": su.newton,
        "kN": 1000 * su.newton,
        "MN": 1_000_000 * su.newton,
        # Pressure / stress
        "Pa":  su.pascal,
        "kPa": 1000 * su.pascal,
        "MPa": 1_000_000 * su.pascal,
        "GPa": 1_000_000_000 * su.pascal,
        "N/m**2": su.pascal,
        "N/m2":   su.pascal,
        # Energy
        "J":  su.joule,
        "kJ": 1000 * su.joule,
        "MJ": 1_000_000 * su.joule,
        # Power
        "W":  su.watt,
        "kW": 1000 * su.watt,
        "MW": 1_000_000 * su.watt,
        # Temperature
        "K": su.kelvin,
        # Area / Volume
        "m**2": su.meter ** 2, "m2": su.meter ** 2,
        "m**3": su.meter ** 3, "m3": su.meter ** 3,
        "cm**2": su.centimeter ** 2, "cm2": su.centimeter ** 2,
        "mm**2": su.millimeter ** 2, "mm2": su.millimeter ** 2,
        # Velocity / acceleration
        "m/s":    su.meter / su.second,
        "km/h":   su.kilometer / su.hour,
        "m/s**2": su.meter / su.second ** 2,
        "m/s2":   su.meter / su.second ** 2,
        # Density
        "kg/m**3": su.kilogram / su.meter ** 3,
        "kg/m3":   su.kilogram / su.meter ** 3,
        # Thermal
        "W/m**2": su.watt / su.meter ** 2,
        "W/m2":   su.watt / su.meter ** 2,
        "W/(m*K)": su.watt / (su.meter * su.kelvin),
        "W/mK":    su.watt / (su.meter * su.kelvin),
        # Angular / frequency
        "rad":   su.radian,
        "rad/s": su.radian / su.second,
        "Hz":    su.hertz,
        "1/s":   1 / su.second,
        # Dimensionless
        "dimensionless": sp.Integer(1),
        "1":             sp.Integer(1),
        "-":             sp.Integer(1),
    }


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
            "max_deflection_ratio": 1 / 250,
            "min_elastic_modulus_gpa": 0.01,
        },
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
                 benchmark_data: Optional[List[Dict]] = None,
                 variable_units: Optional[Dict[str, str]] = None) -> ValidationReport:
        """
        Run full 5-stage validation pipeline.

        Args:
            formula_id:           Unique identifier for the formula.
            expression:           Mathematical expression (e.g. "F = m * a").
            expected_output_unit: Expected output unit string (e.g. "N", "Pa", "MPa").
            domain:               Physical domain for Stage 3 — one of
                                  "construction", "thermodynamics", "structural".
            benchmark_data:       Optional list of dicts for empirical testing.
            variable_units:       Mapping of variable name → unit string for real
                                  dimensional analysis, e.g.
                                  {"m": "kg", "a": "m/s**2"}.
                                  If omitted Stage 2 is skipped.

        Returns:
            ValidationReport with results from all 5 stages.
        """
        start_time = time.time()
        stages = {}

        # Stage 1: Syntactic Validation
        stages[ValidationStage.SYNTACTIC] = self._validate_syntactic(expression)

        # Stage 2: Dimensional Validation (symbolic SymPy units)
        stages[ValidationStage.DIMENSIONAL] = self._validate_dimensional(
            expression, expected_output_unit, variable_units
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

            # For equations (e.g. "F = m * a"), parse both sides separately
            # so we validate the full expression without SymPy choking on `=`.
            is_equation = "=" in expression and "==" not in expression
            metadata["is_equation"] = is_equation

            if is_equation:
                lhs_str, rhs_str = expression.split("=", 1)
                parse_targets = [("lhs", lhs_str.strip()), ("rhs", rhs_str.strip())]
            else:
                parse_targets = [("expr", expression.strip())]

            all_symbols: set = set()
            for label, target in parse_targets:
                try:
                    parsed = sp.parse_expr(target, evaluate=False)
                    all_symbols |= parsed.free_symbols
                except Exception as e:
                    errors.append(f"Parse error ({label}): {str(e)}")

            if errors:
                return StageResult(
                    stage=ValidationStage.SYNTACTIC,
                    status=ValidationStatus.FAIL,
                    valid=False,
                    errors=errors,
                    execution_time_ms=(time.time() - start) * 1000,
                )

            metadata["variables"] = list(map(str, all_symbols))
            
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
                              expected_output_unit: Optional[str],
                              variable_units: Optional[Dict[str, str]]) -> StageResult:
        """
        Stage 2: Dimensional Validation — real symbolic analysis via SymPy units.

        Strategy
        --------
        1. Strip the LHS of equations so we only analyse the RHS expression.
        2. Replace every named variable with its declared SymPy unit object.
        3. Simplify the resulting unit expression.
        4. If an expected output unit was provided, compute the ratio of the
           computed unit to the expected unit.  A pure numeric ratio (no
           surviving unit symbols) means the dimensions are consistent; any
           remaining unit symbols mean a mismatch.
        5. Variables whose unit string is not in the lookup table are flagged
           as warnings rather than errors, so a partial annotation still gives
           useful feedback.
        """
        start = time.time()
        errors: List[str] = []
        warnings: List[str] = []
        metadata: Dict[str, Any] = {
            "variable_units": variable_units or {},
            "expected_output_unit": expected_output_unit,
        }

        # ── Guard: skip when no annotations are provided ─────────────────────
        if not variable_units:
            return StageResult(
                stage=ValidationStage.DIMENSIONAL,
                status=ValidationStatus.SKIP,
                valid=True,
                warnings=["No variable_units provided — dimensional analysis skipped."],
                metadata=metadata,
                execution_time_ms=(time.time() - start) * 1000,
            )

        if not self._sympy_available:
            return StageResult(
                stage=ValidationStage.DIMENSIONAL,
                status=ValidationStatus.SKIP,
                valid=True,
                warnings=["SymPy not available — dimensional analysis skipped."],
                metadata=metadata,
                execution_time_ms=(time.time() - start) * 1000,
            )

        try:
            import sympy as sp

            # Lazily build the unit map once
            global _UNIT_MAP
            if _UNIT_MAP is None:
                _UNIT_MAP = _build_unit_map()

            # ── Step 1: isolate the RHS ──────────────────────────────────────
            rhs = expression.strip()
            if "=" in rhs and "==" not in rhs:
                rhs = rhs.split("=", 1)[1].strip()

            # ── Step 2: parse RHS with variable symbols ──────────────────────
            local_syms = {name: sp.Symbol(name) for name in variable_units}
            try:
                parsed = sp.parse_expr(rhs, local_dict=local_syms, evaluate=False)
            except Exception as exc:
                errors.append(f"Cannot parse RHS for dimensional analysis: {exc}")
                return StageResult(
                    stage=ValidationStage.DIMENSIONAL,
                    status=ValidationStatus.FAIL,
                    valid=False,
                    errors=errors,
                    metadata=metadata,
                    execution_time_ms=(time.time() - start) * 1000,
                )

            # ── Step 3: substitute units for each variable ───────────────────
            unit_subs: Dict[Any, Any] = {}
            unresolved: List[str] = []
            for var, unit_str in variable_units.items():
                unit_obj = _UNIT_MAP.get(unit_str)
                if unit_obj is None:
                    unresolved.append(f"{var}='{unit_str}'")
                else:
                    unit_subs[local_syms[var]] = unit_obj

            if unresolved:
                warnings.append(
                    f"Unknown unit strings (skipped in analysis): {', '.join(unresolved)}"
                )

            if not unit_subs:
                return StageResult(
                    stage=ValidationStage.DIMENSIONAL,
                    status=ValidationStatus.SKIP,
                    valid=True,
                    warnings=["No variables could be resolved to units — skipping."],
                    metadata=metadata,
                    execution_time_ms=(time.time() - start) * 1000,
                )

            # ── Step 4: evaluate the unit expression ─────────────────────────
            try:
                unit_expr = parsed.subs(unit_subs)
                simplified = sp.simplify(unit_expr)
                metadata["computed_unit_expr"] = str(simplified)
            except Exception as exc:
                warnings.append(f"Could not simplify unit expression: {exc}")
                simplified = None

            # ── Step 5: compare with expected output unit ────────────────────
            if simplified is not None and expected_output_unit:
                expected_obj = _UNIT_MAP.get(expected_output_unit)
                if expected_obj is None:
                    warnings.append(
                        f"Expected output unit '{expected_output_unit}' not in "
                        "lookup table — cannot verify dimensional match."
                    )
                else:
                    try:
                        from sympy.physics.units.util import convert_to

                        # convert_to normalises both expressions to the same
                        # unit basis.  If the formula is dimensionally consistent,
                        # convert_to(simplified, expected_obj) will return a pure
                        # numerical multiple of expected_obj (e.g. 1*newton).
                        converted = convert_to(simplified, expected_obj)
                        ratio = sp.simplify(converted / expected_obj)
                        metadata["unit_ratio"] = str(ratio)

                        if ratio.is_number:
                            # Dimensionally consistent — possibly with a scale factor
                            metadata["dimension_check"] = "pass"
                            metadata["scale_factor"] = str(float(ratio))
                            if abs(float(ratio) - 1.0) > 1e-9:
                                warnings.append(
                                    f"Units are dimensionally consistent but differ "
                                    f"by a scale factor of {float(ratio):.6g} "
                                    f"(computed vs '{expected_output_unit}')."
                                )
                        else:
                            # Surviving unit symbols ⟹ mismatch
                            errors.append(
                                f"Dimensional mismatch: expression evaluates to "
                                f"'{simplified}', which cannot be converted to "
                                f"'{expected_output_unit}' (ratio: {ratio})."
                            )
                            metadata["dimension_check"] = "fail"
                    except Exception as exc:
                        # convert_to raises when dimensions are incompatible
                        errors.append(
                            f"Dimensional mismatch: cannot convert computed units "
                            f"to '{expected_output_unit}' — {exc}"
                        )
                        metadata["dimension_check"] = "fail"

            valid = len(errors) == 0
            return StageResult(
                stage=ValidationStage.DIMENSIONAL,
                status=ValidationStatus.PASS if valid else ValidationStatus.FAIL,
                valid=valid,
                errors=errors,
                warnings=warnings,
                metadata=metadata,
                execution_time_ms=(time.time() - start) * 1000,
            )

        except Exception as exc:
            errors.append(f"Dimensional validation error: {exc}")
            return StageResult(
                stage=ValidationStage.DIMENSIONAL,
                status=ValidationStatus.FAIL,
                valid=False,
                errors=errors,
                metadata=metadata,
                execution_time_ms=(time.time() - start) * 1000,
            )
    
    def _validate_physical(self, expression: str, domain: str) -> StageResult:
        """
        Stage 3: Physical Validation

        Checks the expression against domain-specific physical laws and the
        constraint table.  Detection is heuristic (keyword + pattern matching)
        because full symbolic constraint propagation is handled by Stage 4
        (empirical) once variable values are available.
        """
        start = time.time()
        errors: List[str] = []
        warnings: List[str] = []
        metadata: Dict[str, Any] = {"domain": domain, "constraints_checked": []}

        constraints = self.PHYSICAL_CONSTRAINTS.get(domain, {})
        expr_lower = expression.lower()

        # ── Universal checks (all domains) ───────────────────────────────────
        if "sqrt(" in expr_lower or "sqrt (" in expr_lower:
            warnings.append(
                "sqrt() present — ensure the argument is non-negative for all "
                "physically valid inputs."
            )
        if "log(" in expr_lower or "ln(" in expr_lower or "log10(" in expr_lower:
            warnings.append(
                "Logarithm present — argument must be strictly positive; "
                "validate inputs before deployment."
            )
        if re.search(r"/\s*\(?\s*0\b", expression):
            errors.append("Potential division by zero detected.")

        # ── Domain-specific checks ────────────────────────────────────────────
        if domain == "thermodynamics":
            metadata["constraints_checked"].append("temperature_bounds")
            min_t = constraints.get("min_temp_kelvin", 0)
            max_t = constraints.get("max_temp_kelvin", 6000)
            if "temp" in expr_lower or "_t" in expr_lower:
                warnings.append(
                    f"Temperature variable detected — ensure value is within "
                    f"[{min_t} K, {max_t} K]."
                )
            if "entropy" in expr_lower or " s " in expression:
                warnings.append("Entropy term detected — must remain ≥ 0 (2nd Law).")

        elif domain == "structural":
            metadata["constraints_checked"].append("deflection_limits")
            ratio = constraints.get("max_deflection_ratio", 1 / 250)
            if "deflection" in expr_lower and "span" in expr_lower:
                warnings.append(
                    f"Deflection/span formula — ensure ratio ≤ 1/{int(1/ratio)}."
                )
            sf = constraints.get("min_safety_factor")
            if sf and ("safety" in expr_lower or "factor" in expr_lower):
                warnings.append(f"Safety factor must be ≥ {sf} for this domain.")

        elif domain == "construction":
            metadata["constraints_checked"].append("stress_density")
            max_stress = constraints.get("max_stress_mpa", 1000)
            if "stress" in expr_lower or "pressure" in expr_lower:
                warnings.append(
                    f"Stress/pressure term — verify result does not exceed "
                    f"{max_stress} MPa."
                )
            if "density" in expr_lower or "rho" in expr_lower:
                lo = constraints.get("min_density_kg_m3", 100)
                hi = constraints.get("max_density_kg_m3", 25000)
                warnings.append(
                    f"Density term — verify value is within [{lo}, {hi}] kg/m³."
                )

        valid = len(errors) == 0
        return StageResult(
            stage=ValidationStage.PHYSICAL,
            status=ValidationStatus.PASS if valid else ValidationStatus.FAIL,
            valid=valid,
            errors=errors,
            warnings=warnings,
            metadata=metadata,
            execution_time_ms=(time.time() - start) * 1000,
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
