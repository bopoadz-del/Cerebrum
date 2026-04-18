"""
Formula Executor Service

Provides secure, sandboxed formula execution with:
- Natural language to formula translation
- Docker-based isolated execution
- Construction-specific formulas (concrete, rebar, cost)
- Credibility scoring for results
- Comprehensive audit logging
"""

import uuid
import json
import logging
import re
import math
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.core.logging import get_logger
from app.monitoring.metrics import FormulaMetrics

logger = get_logger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class FormulaType(str, Enum):
    """Types of formulas supported."""
    CONCRETE = "concrete"
    REBAR = "rebar"
    COST = "cost"
    STRUCTURAL = "structural"
    MASONRY = "masonry"
    EARTHWORK = "earthwork"
    STEEL = "steel"
    GENERAL = "general"


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SECURITY_VIOLATION = "security_violation"


class CredibilityLevel(str, Enum):
    """Credibility levels for formula results."""
    HIGH = "high"      # > 0.8 - Verified formula, all inputs validated
    MEDIUM = "medium"  # 0.5 - 0.8 - Standard formula, typical inputs
    LOW = "low"        # 0.3 - 0.5 - Estimation, incomplete data
    UNCERTAIN = "uncertain"  # < 0.3 - High uncertainty, needs review


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FormulaInput:
    """Input parameter for formula execution."""
    name: str
    value: Any
    unit: str = ""
    source: str = "user"  # user, calculated, external
    confidence: float = 1.0  # 0.0 - 1.0


@dataclass
class FormulaOutput:
    """Output from formula execution."""
    name: str
    value: Any
    unit: str = ""
    formula_used: str = ""


@dataclass
class CredibilityScore:
    """Credibility assessment for formula results."""
    score: float  # 0.0 - 1.0
    level: CredibilityLevel
    factors: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 3),
            "level": self.level.value,
            "factors": self.factors
        }


@dataclass
class ExecutionResult:
    """Complete formula execution result."""
    execution_id: str
    formula_id: str
    formula_type: FormulaType
    status: ExecutionStatus
    inputs: List[FormulaInput]
    outputs: List[FormulaOutput]
    credibility: CredibilityScore
    execution_time_ms: float
    timestamp: datetime
    error_message: Optional[str] = None
    audit_log_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "formula_id": self.formula_id,
            "formula_type": self.formula_type.value,
            "status": self.status.value,
            "inputs": [
                {"name": i.name, "value": i.value, "unit": i.unit, "confidence": i.confidence}
                for i in self.inputs
            ],
            "outputs": [
                {"name": o.name, "value": o.value, "unit": o.unit, "formula_used": o.formula_used}
                for o in self.outputs
            ],
            "credibility": self.credibility.to_dict(),
            "execution_time_ms": round(self.execution_time_ms, 2),
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
            "audit_log_id": self.audit_log_id
        }


@dataclass
class FormulaTemplate:
    """Template for construction formulas."""
    id: str
    name: str
    formula_type: FormulaType
    description: str
    expression: str
    required_inputs: List[Dict[str, Any]]
    output_unit: str
    references: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


# =============================================================================
# Construction Formula Library
# =============================================================================

CONSTRUCTION_FORMULAS: Dict[str, FormulaTemplate] = {
    # Concrete Formulas
    "concrete_volume": FormulaTemplate(
        id="concrete_volume",
        name="Concrete Volume",
        formula_type=FormulaType.CONCRETE,
        description="Calculate volume of concrete for slabs, footings, walls",
        expression="length * width * depth",
        required_inputs=[
            {"name": "length", "type": "float", "unit": "m", "required": True},
            {"name": "width", "type": "float", "unit": "m", "required": True},
            {"name": "depth", "type": "float", "unit": "m", "required": True},
        ],
        output_unit="m³",
        references=["ACI 318", "ASTM C94"],
        tags=["concrete", "volume", "slab", "footing"]
    ),
    
    "concrete_volume_cylinder": FormulaTemplate(
        id="concrete_volume_cylinder",
        name="Concrete Volume - Cylinder",
        formula_type=FormulaType.CONCRETE,
        description="Calculate volume of cylindrical concrete (columns, piers)",
        expression="math.pi * (diameter / 2) ** 2 * height",
        required_inputs=[
            {"name": "diameter", "type": "float", "unit": "m", "required": True},
            {"name": "height", "type": "float", "unit": "m", "required": True},
        ],
        output_unit="m³",
        references=["ACI 318"],
        tags=["concrete", "volume", "column", "pier"]
    ),
    
    # Rebar Formulas
    "rebar_weight": FormulaTemplate(
        id="rebar_weight",
        name="Rebar Weight",
        formula_type=FormulaType.REBAR,
        description="Calculate weight of reinforcing steel",
        expression="length * weight_per_meter",
        required_inputs=[
            {"name": "length", "type": "float", "unit": "m", "required": True},
            {"name": "weight_per_meter", "type": "float", "unit": "kg/m", "required": True},
        ],
        output_unit="kg",
        references=["ASTM A615", "BS 4449"],
        tags=["rebar", "steel", "weight"]
    ),
    
    "rebar_weight_from_diameter": FormulaTemplate(
        id="rebar_weight_from_diameter",
        name="Rebar Weight from Diameter",
        formula_type=FormulaType.REBAR,
        description="Calculate rebar weight using standard diameter (mm)",
        expression="length * (diameter ** 2) / 162.162",
        required_inputs=[
            {"name": "length", "type": "float", "unit": "m", "required": True},
            {"name": "diameter", "type": "float", "unit": "mm", "required": True},
        ],
        output_unit="kg",
        references=["ASTM A615"],
        tags=["rebar", "steel", "weight", "standard"]
    ),
    
    "rebar_lap_length": FormulaTemplate(
        id="rebar_lap_length",
        name="Rebar Lap Length",
        formula_type=FormulaType.REBAR,
        description="Calculate lap splice length for rebar",
        expression="40 * diameter",
        required_inputs=[
            {"name": "diameter", "type": "float", "unit": "mm", "required": True},
        ],
        output_unit="mm",
        references=["ACI 318-19, Section 25.5"],
        tags=["rebar", "lap", "splice", "connection"]
    ),
    
    # Cost Formulas
    "concrete_cost": FormulaTemplate(
        id="concrete_cost",
        name="Concrete Material Cost",
        formula_type=FormulaType.COST,
        description="Calculate concrete material cost",
        expression="volume * cost_per_cubic_meter",
        required_inputs=[
            {"name": "volume", "type": "float", "unit": "m³", "required": True},
            {"name": "cost_per_cubic_meter", "type": "float", "unit": "USD/m³", "required": True, "default": 150},
        ],
        output_unit="USD",
        references=["RSMeans", "Local market rates"],
        tags=["cost", "concrete", "material"]
    ),
    
    "rebar_cost": FormulaTemplate(
        id="rebar_cost",
        name="Rebar Material Cost",
        formula_type=FormulaType.COST,
        description="Calculate rebar material cost",
        expression="weight * cost_per_kg",
        required_inputs=[
            {"name": "weight", "type": "float", "unit": "kg", "required": True},
            {"name": "cost_per_kg", "type": "float", "unit": "USD/kg", "required": True, "default": 1.2},
        ],
        output_unit="USD",
        references=["RSMeans"],
        tags=["cost", "rebar", "steel", "material"]
    ),
    
    # Structural Formulas
    "beam_moment": FormulaTemplate(
        id="beam_moment_simple",
        name="Simple Beam Maximum Moment",
        formula_type=FormulaType.STRUCTURAL,
        description="Calculate maximum bending moment for simple beam with uniform load",
        expression="(load * span ** 2) / 8",
        required_inputs=[
            {"name": "load", "type": "float", "unit": "kN/m", "required": True},
            {"name": "span", "type": "float", "unit": "m", "required": True},
        ],
        output_unit="kN·m",
        references=["AISC Steel Construction Manual"],
        tags=["structural", "beam", "moment", " bending"]
    ),
    
    "column_axial_load": FormulaTemplate(
        id="column_axial_load",
        name="Column Axial Load Capacity",
        formula_type=FormulaType.STRUCTURAL,
        description="Calculate axial load capacity of concrete column",
        expression="0.85 * concrete_strength * (area - steel_area) + steel_yield * steel_area",
        required_inputs=[
            {"name": "concrete_strength", "type": "float", "unit": "MPa", "required": True},
            {"name": "area", "type": "float", "unit": "mm²", "required": True},
            {"name": "steel_area", "type": "float", "unit": "mm²", "required": True},
            {"name": "steel_yield", "type": "float", "unit": "MPa", "required": True, "default": 400},
        ],
        output_unit="N",
        references=["ACI 318-19, Chapter 22"],
        tags=["structural", "column", "axial", "capacity"]
    ),
    
    # Masonry Formulas
    "brick_quantity": FormulaTemplate(
        id="brick_quantity",
        name="Brick Quantity Estimation",
        formula_type=FormulaType.MASONRY,
        description="Calculate number of bricks for wall",
        expression="(wall_area * bricks_per_m2) * waste_factor",
        required_inputs=[
            {"name": "wall_area", "type": "float", "unit": "m²", "required": True},
            {"name": "bricks_per_m2", "type": "float", "unit": "bricks/m²", "required": True, "default": 60},
            {"name": "waste_factor", "type": "float", "unit": "ratio", "required": True, "default": 1.05},
        ],
        output_unit="bricks",
        references=["Standard construction practice"],
        tags=["masonry", "brick", "quantity", "wall"]
    ),
    
    "mortar_volume": FormulaTemplate(
        id="mortar_volume",
        name="Mortar Volume for Brickwork",
        formula_type=FormulaType.MASONRY,
        description="Calculate mortar volume required for brick wall",
        expression="wall_area * mortar_thickness * 1.3",
        required_inputs=[
            {"name": "wall_area", "type": "float", "unit": "m²", "required": True},
            {"name": "mortar_thickness", "type": "float", "unit": "m", "required": True, "default": 0.012},
        ],
        output_unit="m³",
        references=["Standard construction practice"],
        tags=["masonry", "mortar", "volume"]
    ),
    
    # Earthwork Formulas
    "excavation_volume": FormulaTemplate(
        id="excavation_volume",
        name="Excavation Volume",
        formula_type=FormulaType.EARTHWORK,
        description="Calculate excavation volume with side slopes",
        expression="((top_length + bottom_length) / 2) * ((top_width + bottom_width) / 2) * depth",
        required_inputs=[
            {"name": "top_length", "type": "float", "unit": "m", "required": True},
            {"name": "top_width", "type": "float", "unit": "m", "required": True},
            {"name": "bottom_length", "type": "float", "unit": "m", "required": True},
            {"name": "bottom_width", "type": "float", "unit": "m", "required": True},
            {"name": "depth", "type": "float", "unit": "m", "required": True},
        ],
        output_unit="m³",
        references=["Construction estimating standards"],
        tags=["earthwork", "excavation", "volume"]
    ),
    
    "fill_volume": FormulaTemplate(
        id="fill_volume",
        name="Fill/Backfill Volume",
        formula_type=FormulaType.EARTHWORK,
        description="Calculate fill material volume with compaction factor",
        expression="area * depth * compaction_factor",
        required_inputs=[
            {"name": "area", "type": "float", "unit": "m²", "required": True},
            {"name": "depth", "type": "float", "unit": "m", "required": True},
            {"name": "compaction_factor", "type": "float", "unit": "ratio", "required": True, "default": 1.15},
        ],
        output_unit="m³",
        references=["Geotechnical standards"],
        tags=["earthwork", "fill", "backfill", "compaction"]
    ),
}


# =============================================================================
# Natural Language Formula Parser
# =============================================================================

class FormulaParser:
    """Parse natural language into formula execution requests."""
    
    # Keywords for formula type detection
    KEYWORD_PATTERNS = {
        FormulaType.CONCRETE: [
            r'concrete', r'cement', r'slab', r'footing', r'foundation', r'column',
            r'beam', r'pier', r'pour', r'cubic', r'm³', r'cubic\s+meter',
            r'cy', r'cubic\s+yard', r'ready.mix', r'grade\s+beam'
        ],
        FormulaType.REBAR: [
            r'rebar', r'reinforcing', r'steel\s+bar', r'reinforcement',
            r'deformed\s+bar', r'lap\s+length', r'splice', r'dowel',
            r'reinforcing\s+steel', r'fy\s*[=]?\s*\d+', r'grade\s*60'
        ],
        FormulaType.COST: [
            r'cost', r'price', r'budget', r'estimate', r'\$', r'usd',
            r'material\s+cost', r'total\s+cost', r'how\s+much', r'pricing'
        ],
        FormulaType.STRUCTURAL: [
            r'moment', r'shear', r'load', r'capacity', r'stress', r'strain',
            r'deflection', r'bending', r'axial', r'compression', r'tension',
            r'beam\s+design', r'column\s+design', r'foundation\s+design'
        ],
        FormulaType.MASONRY: [
            r'brick', r'block', r'masonry', r'mortar', r'wall\s+construction',
            r'cmu', r'concrete\s+masonry', r'brickwork', r'blockwork'
        ],
        FormulaType.EARTHWORK: [
            r'excavation', r'fill', r'backfill', r'cut', r'embankment',
            r'grading', r'earth', r'soil', r'compaction', r'trench'
        ],
        FormulaType.STEEL: [
            r'structural\s+steel', r'wf', r'wide\s+flange', r'i.beam',
            r'steel\s+beam', r'steel\s+column', r'w\s*\d+', r'hp\s*\d+'
        ],
    }
    
    # Dimension extraction patterns
    DIMENSION_PATTERNS = [
        # Metric: 10m x 8m x 0.5m or 10 m x 8 m x 0.5 m
        r'(\d+\.?\d*)\s*m?\s*[x×]\s*(\d+\.?\d*)\s*m?\s*[x×]\s*(\d+\.?\d*)\s*m?',
        # Imperial: 10ft x 8ft x 0.5ft
        r'(\d+\.?\d*)\s*(?:ft|feet|\')\s*[x×]\s*(\d+\.?\d*)\s*(?:ft|feet|\')\s*[x×]\s*(\d+\.?\d*)\s*(?:ft|feet|\'|in|inches|\")?',
        # Mixed: 10' x 8' x 6"
        r'(\d+\.?\d*)\s*\'\s*[x×]\s*(\d+\.?\d*)\s*\'\s*[x×]\s*(\d+\.?\d*)\s*\"',
    ]
    
    @classmethod
    def detect_formula_type(cls, text: str) -> Optional[FormulaType]:
        """Detect formula type from natural language text."""
        text_lower = text.lower()
        
        scores = {}
        for formula_type, patterns in cls.KEYWORD_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[formula_type] = score
        
        if not scores:
            return None
        
        return max(scores, key=scores.get)
    
    @classmethod
    def extract_dimensions(cls, text: str) -> Dict[str, float]:
        """Extract dimensions (length, width, height/depth) from text."""
        text_lower = text.lower()
        
        for pattern in cls.DIMENSION_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    dim1 = float(match.group(1))
                    dim2 = float(match.group(2))
                    dim3 = float(match.group(3))
                    
                    # Detect unit from context
                    is_metric = any(unit in text_lower for unit in ['m ', 'meter', 'mtr', 'metre', 'm³'])
                    is_imperial = any(unit in text_lower for unit in ["'", 'ft', 'feet', 'inch', 'yd', 'yard'])
                    
                    if is_imperial and not is_metric:
                        # Convert imperial to metric for standardization
                        dim1 *= 0.3048  # feet to meters
                        dim2 *= 0.3048
                        dim3 *= 0.3048
                    
                    return {
                        "length": dim1,
                        "width": dim2,
                        "depth": dim3,
                        "unit": "m" if (is_metric or not is_imperial) else "ft"
                    }
                except (ValueError, IndexError):
                    continue
        
        return {}
    
    @classmethod
    def extract_numeric_value(cls, text: str, keywords: List[str]) -> Optional[float]:
        """Extract numeric value associated with keywords."""
        text_lower = text.lower()
        
        for keyword in keywords:
            # Pattern: keyword followed by number
            pattern = rf'{keyword}\s*(?:of|is|was|equals|=|:)?\s*(\d+\.?\d*)'
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    @classmethod
    def parse_formula_request(cls, text: str) -> Dict[str, Any]:
        """Parse natural language into formula execution request."""
        formula_type = cls.detect_formula_type(text)
        dimensions = cls.extract_dimensions(text)
        
        result = {
            "original_text": text,
            "formula_type": formula_type.value if formula_type else None,
            "detected_inputs": dimensions,
            "confidence": 0.0,
            "suggested_formulas": []
        }
        
        # Find suggested formulas
        if formula_type:
            suggested = [
                f for f in CONSTRUCTION_FORMULAS.values()
                if f.formula_type == formula_type
            ]
            result["suggested_formulas"] = [f.id for f in suggested]
            
            # Calculate confidence based on input completeness
            if dimensions:
                if len(dimensions) >= 3:  # length, width, depth
                    result["confidence"] = 0.8
                else:
                    result["confidence"] = 0.5
            else:
                result["confidence"] = 0.3
        
        return result


# =============================================================================
# Credibility Scoring
# =============================================================================

class CredibilityScorer:
    """Calculate credibility scores for formula execution results."""
    
    @staticmethod
    def calculate_score(
        formula: FormulaTemplate,
        inputs: List[FormulaInput],
        execution_time_ms: float,
        has_errors: bool
    ) -> CredibilityScore:
        """
        Calculate credibility score based on multiple factors.
        
        Factors:
        - Input data quality (completeness, source reliability)
        - Formula reliability (standard vs custom)
        - Execution performance
        - Error presence
        """
        factors = []
        score = 1.0
        
        # Factor 1: Input completeness
        required_inputs = {inp["name"] for inp in formula.required_inputs}
        provided_inputs = {inp.name for inp in inputs}
        missing_inputs = required_inputs - provided_inputs
        
        if missing_inputs:
            completeness_score = len(provided_inputs) / len(required_inputs)
            score *= completeness_score
            factors.append({
                "factor": "input_completeness",
                "weight": 0.3,
                "score": completeness_score,
                "details": f"Missing inputs: {missing_inputs}"
            })
        else:
            factors.append({
                "factor": "input_completeness",
                "weight": 0.3,
                "score": 1.0,
                "details": "All required inputs provided"
            })
        
        # Factor 2: Input source confidence
        source_scores = [inp.confidence for inp in inputs]
        avg_source_confidence = sum(source_scores) / len(source_scores) if source_scores else 0.5
        score *= (0.7 + 0.3 * avg_source_confidence)  # Weight: 30%
        factors.append({
            "factor": "input_source_confidence",
            "weight": 0.2,
            "score": avg_source_confidence,
            "details": f"Average confidence: {avg_source_confidence:.2f}"
        })
        
        # Factor 3: Formula standardization
        if formula.references:
            # Has industry standard references (ACI, ASTM, etc.)
            standard_score = 0.9
        else:
            standard_score = 0.6
        score *= (0.8 + 0.2 * standard_score)  # Weight: 20%
        factors.append({
            "factor": "formula_standardization",
            "weight": 0.2,
            "score": standard_score,
            "details": f"References: {formula.references}" if formula.references else "No standard references"
        })
        
        # Factor 4: Execution quality
        if has_errors:
            score *= 0.3
            factors.append({
                "factor": "execution_quality",
                "weight": 0.2,
                "score": 0.0,
                "details": "Execution completed with errors"
            })
        elif execution_time_ms > 5000:  # > 5 seconds
            score *= 0.8
            factors.append({
                "factor": "execution_quality",
                "weight": 0.2,
                "score": 0.8,
                "details": "Slow execution (>5s)"
            })
        else:
            factors.append({
                "factor": "execution_quality",
                "weight": 0.1,
                "score": 1.0,
                "details": "Normal execution"
            })
        
        # Determine level
        if score > 0.8:
            level = CredibilityLevel.HIGH
        elif score > 0.5:
            level = CredibilityLevel.MEDIUM
        elif score > 0.3:
            level = CredibilityLevel.LOW
        else:
            level = CredibilityLevel.UNCERTAIN
        
        return CredibilityScore(score=score, level=level, factors=factors)


# =============================================================================
# Formula Executor Service
# =============================================================================

class FormulaExecutorService:
    """
    Main service for executing construction formulas securely.
    
    Features:
    - Natural language formula parsing
    - Sandboxed code execution
    - Credibility scoring
    - Comprehensive audit logging
    """
    
    def __init__(self, sandbox_client=None, audit_logger=None):
        self.sandbox = sandbox_client
        self.audit_logger = audit_logger
        self.parser = FormulaParser()
        self.scorer = CredibilityScorer()
    
    async def execute_formula(
        self,
        formula_id: str,
        inputs: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        source: str = "api"
    ) -> ExecutionResult:
        """
        Execute a formula by ID with given inputs.
        
        Args:
            formula_id: The formula template ID
            inputs: Input values dictionary
            user_id: User executing the formula (for audit)
            request_id: Request correlation ID
            source: Source of request (api, chat, agent)
        
        Returns:
            ExecutionResult with outputs and credibility score
        """
        start_time = datetime.utcnow()
        execution_id = str(uuid.uuid4())
        
        # Get formula template
        formula = CONSTRUCTION_FORMULAS.get(formula_id)
        if not formula:
            return ExecutionResult(
                execution_id=execution_id,
                formula_id=formula_id,
                formula_type=FormulaType.GENERAL,
                status=ExecutionStatus.ERROR,
                inputs=[],
                outputs=[],
                credibility=CredibilityScore(0.0, CredibilityLevel.UNCERTAIN),
                execution_time_ms=0.0,
                timestamp=start_time,
                error_message=f"Formula not found: {formula_id}"
            )
        
        # Validate and prepare inputs
        formula_inputs = []
        for inp_def in formula.required_inputs:
            inp_name = inp_def["name"]
            inp_value = inputs.get(inp_name)
            
            if inp_value is None and "default" in inp_def:
                inp_value = inp_def["default"]
            
            if inp_value is not None:
                formula_inputs.append(FormulaInput(
                    name=inp_name,
                    value=float(inp_value) if isinstance(inp_value, (int, float, str)) else inp_value,
                    unit=inp_def.get("unit", ""),
                    source="user",
                    confidence=1.0 if inputs.get(inp_name) is not None else 0.5  # Lower confidence for defaults
                ))
        
        # Prepare execution environment
        exec_inputs = {inp.name: inp.value for inp in formula_inputs}
        exec_inputs["math"] = math  # Provide math module
        
        # Execute formula (in sandbox if available, else local)
        try:
            if self.sandbox:
                # Use Docker sandbox for execution
                code = self._generate_formula_code(formula, exec_inputs)
                sandbox_result = await self.sandbox.execute_python(
                    code=code,
                    timeout=30,
                    context=exec_inputs
                )
                
                if sandbox_result.success:
                    output_value = sandbox_result.result
                    status = ExecutionStatus.SUCCESS
                    error_msg = None
                else:
                    output_value = None
                    status = ExecutionStatus.ERROR
                    error_msg = sandbox_result.error
            else:
                # Local execution (for development/testing)
                output_value = eval(formula.expression, {"__builtins__": {}}, exec_inputs)
                status = ExecutionStatus.SUCCESS
                error_msg = None
            
        except Exception as e:
            output_value = None
            status = ExecutionStatus.ERROR
            error_msg = str(e)
            logger.error(f"Formula execution failed: {formula_id} error={e}")
        
        execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Prepare outputs
        outputs = []
        if status == ExecutionStatus.SUCCESS:
            outputs.append(FormulaOutput(
                name="result",
                value=output_value,
                unit=formula.output_unit,
                formula_used=formula.expression
            ))
        
        # Calculate credibility score
        credibility = self.scorer.calculate_score(
            formula=formula,
            inputs=formula_inputs,
            execution_time_ms=execution_time_ms,
            has_errors=status != ExecutionStatus.SUCCESS
        )
        
        # Create result
        result = ExecutionResult(
            execution_id=execution_id,
            formula_id=formula_id,
            formula_type=formula.formula_type,
            status=status,
            inputs=formula_inputs,
            outputs=outputs,
            credibility=credibility,
            execution_time_ms=execution_time_ms,
            timestamp=start_time,
            error_message=error_msg
        )
        
        # Audit logging
        if self.audit_logger:
            audit_id = await self.audit_logger.log_formula_execution(
                execution_id=execution_id,
                user_id=user_id,
                formula_id=formula_id,
                inputs={inp.name: inp.value for inp in formula_inputs},
                outputs={out.name: out.value for out in outputs},
                credibility_score=credibility.score,
                status=status.value,
                error_message=error_msg,
                source=source,
                request_id=request_id
            )
            result.audit_log_id = audit_id
        
        # Record metrics
        FormulaMetrics.record_execution(
            domain=formula.formula_type.value,
            formula_id=formula_id,
            success=status == ExecutionStatus.SUCCESS,
            duration=execution_time_ms / 1000
        )
        
        return result
    
    async def execute_natural_language(
        self,
        text: str,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute formula from natural language description.
        
        Args:
            text: Natural language formula description
            user_id: User making the request
            request_id: Request correlation ID
        
        Returns:
            ExecutionResult
        """
        # Parse the request
        parsed = self.parser.parse_formula_request(text)
        
        formula_type_str = parsed.get("formula_type")
        if not formula_type_str:
            return ExecutionResult(
                execution_id=str(uuid.uuid4()),
                formula_id="unknown",
                formula_type=FormulaType.GENERAL,
                status=ExecutionStatus.ERROR,
                inputs=[],
                outputs=[],
                credibility=CredibilityScore(0.0, CredibilityLevel.UNCERTAIN),
                execution_time_ms=0.0,
                timestamp=datetime.utcnow(),
                error_message="Could not determine formula type from input"
            )
        
        formula_type = FormulaType(formula_type_str)
        
        # Get suggested formulas
        suggested_ids = parsed.get("suggested_formulas", [])
        if not suggested_ids:
            return ExecutionResult(
                execution_id=str(uuid.uuid4()),
                formula_id="unknown",
                formula_type=formula_type,
                status=ExecutionStatus.ERROR,
                inputs=[],
                outputs=[],
                credibility=CredibilityScore(0.1, CredibilityLevel.UNCERTAIN),
                execution_time_ms=0.0,
                timestamp=datetime.utcnow(),
                error_message=f"No formulas available for type: {formula_type.value}"
            )
        
        # Use first suggested formula
        formula_id = suggested_ids[0]
        inputs = parsed.get("detected_inputs", {})
        
        # Execute
        return await self.execute_formula(
            formula_id=formula_id,
            inputs=inputs,
            user_id=user_id,
            request_id=request_id,
            source="natural_language"
        )
    
    def _generate_formula_code(self, formula: FormulaTemplate, inputs: Dict[str, Any]) -> str:
        """Generate Python code for sandbox execution."""
        input_lines = "\n".join([f"{k} = {repr(v)}" for k, v in inputs.items()])
        
        code = f"""
import math

# Inputs
{input_lines}

# Formula calculation
result = {formula.expression}

# Output result
print(f"RESULT: {{result}}")
"""
        return code
    
    def get_available_formulas(
        self,
        formula_type: Optional[FormulaType] = None,
        tags: Optional[List[str]] = None
    ) -> List[FormulaTemplate]:
        """
        Get available formulas, optionally filtered.
        
        Args:
            formula_type: Filter by formula type
            tags: Filter by tags (must have all)
        
        Returns:
            List of FormulaTemplate
        """
        formulas = list(CONSTRUCTION_FORMULAS.values())
        
        if formula_type:
            formulas = [f for f in formulas if f.formula_type == formula_type]
        
        if tags:
            formulas = [f for f in formulas if all(tag in f.tags for tag in tags)]
        
        return formulas
    
    def get_formula(self, formula_id: str) -> Optional[FormulaTemplate]:
        """Get a specific formula by ID."""
        return CONSTRUCTION_FORMULAS.get(formula_id)


# =============================================================================
# Singleton Instance
# =============================================================================

_formula_executor: Optional[FormulaExecutorService] = None


def get_formula_executor(
    sandbox_client=None,
    audit_logger=None
) -> FormulaExecutorService:
    """Get or create formula executor service singleton."""
    global _formula_executor
    if _formula_executor is None:
        _formula_executor = FormulaExecutorService(
            sandbox_client=sandbox_client,
            audit_logger=audit_logger
        )
    return _formula_executor


def reset_formula_executor():
    """Reset the formula executor singleton (for testing)."""
    global _formula_executor
    _formula_executor = None
