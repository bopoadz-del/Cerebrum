"""
Scientific Computing Service for Cerebrum

Wraps SymPy, Pint, CoolProp, QuantLib, NumPy/SciPy for formula execution.
Provides unified interface for mathematical, physical, and financial calculations.
"""

import logging
from typing import Any, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy import ndarray

import sympy as sp
from sympy import Symbol, Eq, solve, simplify, diff, integrate

from pint import UnitRegistry

from CoolProp.CoolProp import PropsSI

import QuantLib as ql

logger = logging.getLogger(__name__)

# Initialize unit registry
ureg = UnitRegistry()


class CalculationType(str, Enum):
    """Types of scientific calculations supported."""
    SYMBOLIC_MATH = "symbolic_math"
    UNIT_CONVERSION = "unit_conversion"
    THERMODYNAMIC = "thermodynamic"
    FINANCIAL = "financial"
    NUMERICAL = "numerical"
    OPTIMIZATION = "optimization"


@dataclass
class CalculationResult:
    """Result of a scientific calculation."""
    value: Any
    units: Optional[str] = None
    calculation_type: CalculationType
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


class ScientificComputingService:
    """
    Unified service for scientific computing in Cerebrum.
    Wraps SymPy, Pint, CoolProp, QuantLib, NumPy/SciPy.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ureg = UnitRegistry()
    
    # =========================================================================
    # SymPy - Symbolic Mathematics
    # =========================================================================
    
    def solve_equation(self, equation: str, variables: Dict[str, float] = None) -> CalculationResult:
        """
        Solve a symbolic equation using SymPy.
        
        Args:
            equation: Equation as string (e.g., "x**2 - 4 = 0")
            variables: Dict of known variable values
            
        Returns:
            CalculationResult with solution
        """
        try:
            # Parse equation
            if '=' in equation:
                left, right = equation.split('=')
                expr = sp.sympify(left.strip()) - sp.sympify(right.strip())
            else:
                expr = sp.sympify(equation)
            
            # Find symbols
            symbols = list(expr.free_symbols)
            
            if not symbols:
                return CalculationResult(
                    value=float(expr.evalf()),
                    calculation_type=CalculationType.SYMBOLIC_MATH,
                    success=True
                )
            
            # Solve
            solutions = solve(expr, symbols)
            
            # Convert to float if possible
            if isinstance(solutions, list):
                numeric_solutions = [float(s.evalf()) if hasattr(s, 'evalf') else s for s in solutions]
            else:
                numeric_solutions = float(solutions.evalf()) if hasattr(solutions, 'evalf') else solutions
            
            return CalculationResult(
                value=numeric_solutions,
                calculation_type=CalculationType.SYMBOLIC_MATH,
                success=True,
                metadata={"symbols": [str(s) for s in symbols]}
            )
            
        except Exception as e:
            self.logger.error(f"Equation solving error: {e}")
            return CalculationResult(
                value=None,
                calculation_type=CalculationType.SYMBOLIC_MATH,
                success=False,
                error_message=str(e)
            )
    
    def differentiate(self, expression: str, variable: str, order: int = 1) -> CalculationResult:
        """Differentiate an expression with respect to a variable."""
        try:
            expr = sp.sympify(expression)
            var = Symbol(variable)
            
            result = expr
            for _ in range(order):
                result = diff(result, var)
            
            return CalculationResult(
                value=str(simplify(result)),
                calculation_type=CalculationType.SYMBOLIC_MATH,
                success=True,
                metadata={"order": order}
            )
        except Exception as e:
            return CalculationResult(
                value=None,
                calculation_type=CalculationType.SYMBOLIC_MATH,
                success=False,
                error_message=str(e)
            )
    
    def integrate_expr(self, expression: str, variable: str, 
                       limits: Optional[Tuple[float, float]] = None) -> CalculationResult:
        """Integrate an expression."""
        try:
            expr = sp.sympify(expression)
            var = Symbol(variable)
            
            if limits:
                result = integrate(expr, (var, limits[0], limits[1]))
            else:
                result = integrate(expr, var)
            
            return CalculationResult(
                value=str(result),
                calculation_type=CalculationType.SYMBOLIC_MATH,
                success=True,
                metadata={"definite": limits is not None}
            )
        except Exception as e:
            return CalculationResult(
                value=None,
                calculation_type=CalculationType.SYMBOLIC_MATH,
                success=False,
                error_message=str(e)
            )
    
    # =========================================================================
    # Pint - Unit Conversion
    # =========================================================================
    
    def convert_units(self, value: float, from_unit: str, to_unit: str) -> CalculationResult:
        """
        Convert between units using Pint.
        
        Args:
            value: Numeric value
            from_unit: Source unit (e.g., "meters", "kg")
            to_unit: Target unit (e.g., "feet", "lbs")
            
        Returns:
            CalculationResult with converted value
        """
        try:
            quantity = value * self.ureg(from_unit)
            converted = quantity.to(to_unit)
            
            return CalculationResult(
                value=converted.magnitude,
                units=str(converted.units),
                calculation_type=CalculationType.UNIT_CONVERSION,
                success=True,
                metadata={"original_unit": from_unit, "target_unit": to_unit}
            )
        except Exception as e:
            self.logger.error(f"Unit conversion error: {e}")
            return CalculationResult(
                value=None,
                calculation_type=CalculationType.UNIT_CONVERSION,
                success=False,
                error_message=str(e)
            )
    
    def validate_unit(self, unit_string: str) -> bool:
        """Check if a unit string is valid."""
        try:
            self.ureg(unit_string)
            return True
        except:
            return False
    
    # =========================================================================
    # CoolProp - Thermodynamic Properties
    # =========================================================================
    
    def get_thermodynamic_property(self, fluid: str, property_name: str, 
                                   temperature: Optional[float] = None,
                                   pressure: Optional[float] = None,
                                   **kwargs) -> CalculationResult:
        """
        Get thermodynamic property using CoolProp.
        
        Args:
            fluid: Fluid name (e.g., "Water", "Air", "R134a")
            property_name: Property to get (e.g., "D", "H", "S", "C")
            temperature: Temperature in K
            pressure: Pressure in Pa
            
        Returns:
            CalculationResult with property value
        """
        try:
            # Build input pairs
            inputs = []
            if temperature is not None:
                inputs.extend(['T', temperature])
            if pressure is not None:
                inputs.extend(['P', pressure])
            
            for key, val in kwargs.items():
                inputs.extend([key.upper(), val])
            
            if len(inputs) < 4:
                raise ValueError("Need at least 2 input properties")
            
            result = PropsSI(property_name, *inputs, fluid)
            
            property_units = {
                'D': 'kg/m^3',      # Density
                'H': 'J/kg',        # Enthalpy
                'S': 'J/kg/K',      # Entropy
                'C': 'J/kg/K',      # Heat capacity
                'V': 'Pa·s',        # Viscosity
                'L': 'W/m/K',       # Thermal conductivity
            }
            
            return CalculationResult(
                value=result,
                units=property_units.get(property_name, 'SI'),
                calculation_type=CalculationType.THERMODYNAMIC,
                success=True,
                metadata={"fluid": fluid, "property": property_name}
            )
            
        except Exception as e:
            self.logger.error(f"Thermodynamic calculation error: {e}")
            return CalculationResult(
                value=None,
                calculation_type=CalculationType.THERMODYNAMIC,
                success=False,
                error_message=str(e)
            )
    
    # =========================================================================
    # QuantLib - Financial Calculations
    # =========================================================================
    
    def calculate_present_value(self, cashflows: list, discount_rate: float) -> CalculationResult:
        """
        Calculate present value of cash flows using QuantLib.
        
        Args:
            cashflows: List of (amount, year) tuples
            discount_rate: Annual discount rate (e.g., 0.05 for 5%)
            
        Returns:
            CalculationResult with present value
        """
        try:
            today = ql.Date.todaysDate()
            ql.Settings.instance().evaluationDate = today
            
            # Create cash flows
            ql_cashflows = []
            for amount, year in cashflows:
                payment_date = today + int(year * 365)
                ql_cashflows.append(ql.SimpleCashFlow(amount, payment_date))
            
            # Discount curve
            rate = ql.InterestRate(discount_rate, ql.Actual365Fixed(), ql.Continuous, ql.Annual)
            
            # Calculate PV
            pv = sum([cf.amount() * rate.discountFactor(today, cf.date()) for cf in ql_cashflows])
            
            return CalculationResult(
                value=pv,
                units="currency",
                calculation_type=CalculationType.FINANCIAL,
                success=True,
                metadata={"cashflows": len(cashflows), "discount_rate": discount_rate}
            )
            
        except Exception as e:
            self.logger.error(f"Financial calculation error: {e}")
            return CalculationResult(
                value=None,
                calculation_type=CalculationType.FINANCIAL,
                success=False,
                error_message=str(e)
            )
    
    # =========================================================================
    # NumPy/SciPy - Numerical Computing
    # =========================================================================
    
    def numerical_analysis(self, data: list, analysis_type: str = "basic") -> CalculationResult:
        """
        Perform numerical analysis using NumPy/SciPy.
        
        Args:
            data: List of numeric values
            analysis_type: Type of analysis (basic, stats, fft, interpolate)
            
        Returns:
            CalculationResult with analysis results
        """
        try:
            arr = np.array(data)
            
            if analysis_type == "basic":
                result = {
                    "mean": float(np.mean(arr)),
                    "std": float(np.std(arr)),
                    "min": float(np.min(arr)),
                    "max": float(np.max(arr)),
                    "sum": float(np.sum(arr))
                }
            elif analysis_type == "stats":
                from scipy import stats
                result = {
                    "mean": float(np.mean(arr)),
                    "median": float(np.median(arr)),
                    "mode": float(stats.mode(arr, keepdims=True).mode[0]),
                    "variance": float(np.var(arr)),
                    "skewness": float(stats.skew(arr)),
                    "kurtosis": float(stats.kurtosis(arr))
                }
            else:
                result = {"data": arr.tolist()}
            
            return CalculationResult(
                value=result,
                calculation_type=CalculationType.NUMERICAL,
                success=True,
                metadata={"analysis_type": analysis_type, "data_points": len(data)}
            )
            
        except Exception as e:
            self.logger.error(f"Numerical analysis error: {e}")
            return CalculationResult(
                value=None,
                calculation_type=CalculationType.NUMERICAL,
                success=False,
                error_message=str(e)
            )
    
    def optimize_function(self, func_str: str, bounds: list, method: str = "L-BFGS-B") -> CalculationResult:
        """
        Optimize a function using SciPy.
        
        Args:
            func_str: Function as string (e.g., "x**2 + 2*x + 1")
            bounds: List of (min, max) tuples for each variable
            method: Optimization method
            
        Returns:
            CalculationResult with optimization results
        """
        try:
            from scipy.optimize import minimize
            
            # Create lambda from string (SECURITY: only in sandbox)
            x = Symbol('x')
            expr = sp.sympify(func_str)
            func = sp.lambdify(x, expr, 'numpy')
            
            def objective(x_vec):
                return func(x_vec[0])
            
            x0 = [(b[0] + b[1]) / 2 for b in bounds]
            
            result = minimize(objective, x0, method=method, bounds=bounds)
            
            return CalculationResult(
                value={
                    "minimum": float(result.fun),
                    "location": result.x.tolist(),
                    "success": result.success
                },
                calculation_type=CalculationType.OPTIMIZATION,
                success=result.success,
                metadata={"iterations": result.nit, "method": method}
            )
            
        except Exception as e:
            self.logger.error(f"Optimization error: {e}")
            return CalculationResult(
                value=None,
                calculation_type=CalculationType.OPTIMIZATION,
                success=False,
                error_message=str(e)
            )


# Singleton instance
_scientific_service: Optional[ScientificComputingService] = None


def get_scientific_service() -> ScientificComputingService:
    """Get or create singleton instance of scientific computing service."""
    global _scientific_service
    if _scientific_service is None:
        _scientific_service = ScientificComputingService()
    return _scientific_service
