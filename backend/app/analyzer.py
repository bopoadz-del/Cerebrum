"""
Rule-Based Document Analyzer for Cerebrum AI

Provides outcome-first analysis of construction documents:
- Feature A: Quantity Takeoffs (dimensions, area, volume extraction)
- Feature B: Contract Risk Assessment (keyword-based risk flagging)

All measurements normalized to meters.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import Column, String, DateTime, JSON, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import get_sync_db_context

logger = logging.getLogger(__name__)
Base = declarative_base()


# =============================================================================
# Risk Assessment Configuration
# =============================================================================

RISK_KEYWORDS = {
    "Liquidated Damages": "red",
    "Force Majeure": "yellow",
    "Termination": "red",
    "Payment": "green",
    "Indemnification": "red",
    "Limitation of Liability": "yellow",
    "Warranty": "yellow",
    "Default": "red",
    "Delay": "yellow",
    "Penalty": "red",
    "Bond": "green",
    "Insurance": "green",
    "Arbitration": "yellow",
    "Governing Law": "green",
}

RISK_LEVELS = {
    "red": {"severity": 3, "label": "High Risk", "action_required": True},
    "yellow": {"severity": 2, "label": "Medium Risk", "action_required": True},
    "green": {"severity": 1, "label": "Low Risk", "action_required": False},
}


# =============================================================================
# Database Models
# =============================================================================

class DocumentAnalysis(Base):
    """SQLAlchemy model for storing document analysis results."""
    __tablename__ = "document_analyses"
    
    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False)  # 'takeoffs', 'risk', 'full'
    
    # Analysis results stored as JSON
    takeoffs = Column(JSON, default=dict)
    risk_assessment = Column(JSON, default=dict)
    raw_results = Column(JSON, default=dict)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    analyzed_by = Column(String(255), nullable=True)
    status = Column(String(50), default="completed")


# =============================================================================
# Data Classes for Analysis Results
# =============================================================================

@dataclass
class Dimension:
    """A dimension measurement (length, width, height)."""
    value: float
    unit: str
    value_meters: float
    original_text: str
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "value_meters": round(self.value_meters, 4),
            "original_text": self.original_text,
            "context": self.context[:200] if self.context else ""
        }


@dataclass
class Area:
    """An area measurement."""
    value: float
    unit: str
    value_sq_meters: float
    original_text: str
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "value_sq_meters": round(self.value_sq_meters, 4),
            "original_text": self.original_text,
            "context": self.context[:200] if self.context else ""
        }


@dataclass
class Volume:
    """Calculated volume from area × thickness."""
    area_value: float
    thickness_value: float
    unit: str
    value_cubic_meters: float
    calculation_method: str
    context: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "area_value": self.area_value,
            "thickness_value": self.thickness_value,
            "unit": self.unit,
            "value_cubic_meters": round(self.value_cubic_meters, 6),
            "calculation_method": self.calculation_method,
            "context": self.context[:200] if self.context else ""
        }


@dataclass
class TakeoffResult:
    """Complete takeoff analysis result."""
    dimensions: List[Dimension] = field(default_factory=list)
    areas: List[Area] = field(default_factory=list)
    volumes: List[Volume] = field(default_factory=list)
    total_area_sqm: float = 0.0
    total_volume_cum: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimensions": [d.to_dict() for d in self.dimensions],
            "areas": [a.to_dict() for a in self.areas],
            "volumes": [v.to_dict() for v in self.volumes],
            "total_area_sqm": round(self.total_area_sqm, 4),
            "total_volume_cum": round(self.total_volume_cum, 6),
            "count": {
                "dimensions": len(self.dimensions),
                "areas": len(self.areas),
                "volumes": len(self.volumes)
            }
        }


@dataclass
class RiskClause:
    """A flagged contract clause with risk assessment."""
    clause_text: str
    keywords_found: List[str]
    risk_level: str
    severity: int
    label: str
    action_required: bool
    location: str = ""  # paragraph or section reference
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "clause_text": self.clause_text[:500] if self.clause_text else "",
            "keywords_found": self.keywords_found,
            "risk_level": self.risk_level,
            "severity": self.severity,
            "label": self.label,
            "action_required": self.action_required,
            "location": self.location
        }


@dataclass
class RiskAssessment:
    """Complete contract risk assessment result."""
    clauses: List[RiskClause] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "clauses": [c.to_dict() for c in self.clauses],
            "summary": self._calculate_summary()
        }
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate risk summary statistics."""
        if not self.clauses:
            return {
                "total_clauses": 0,
                "risk_breakdown": {"red": 0, "yellow": 0, "green": 0},
                "highest_severity": 0,
                "requires_action": False
            }
        
        risk_counts = {"red": 0, "yellow": 0, "green": 0}
        max_severity = 0
        requires_action = False
        
        for clause in self.clauses:
            risk_counts[clause.risk_level] = risk_counts.get(clause.risk_level, 0) + 1
            max_severity = max(max_severity, clause.severity)
            if clause.action_required:
                requires_action = True
        
        return {
            "total_clauses": len(self.clauses),
            "risk_breakdown": risk_counts,
            "highest_severity": max_severity,
            "requires_action": requires_action
        }


@dataclass
class AnalysisResult:
    """Complete document analysis result."""
    document_id: str
    success: bool
    takeoffs: Optional[TakeoffResult] = None
    risk_assessment: Optional[RiskAssessment] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "success": self.success,
            "takeoffs": self.takeoffs.to_dict() if self.takeoffs else None,
            "risk_assessment": self.risk_assessment.to_dict() if self.risk_assessment else None,
            "error": self.error,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Return JSON string representation."""
        return json.dumps(self.to_dict(), indent=2, default=str)


# =============================================================================
# Unit Conversion Utilities
# =============================================================================

UNIT_CONVERSIONS = {
    # Length to meters
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "inch": 0.0254,
    "inches": 0.0254,
    '"': 0.0254,
    "ft": 0.3048,
    "feet": 0.3048,
    "foot": 0.3048,
    "'": 0.3048,
    "yd": 0.9144,
    "yard": 0.9144,
    "yards": 0.9144,
    # Area to square meters
    "m²": 1.0,
    "sqm": 1.0,
    "sq m": 1.0,
    "square meter": 1.0,
    "square meters": 1.0,
    "sq ft": 0.092903,
    "sqft": 0.092903,
    "square foot": 0.092903,
    "square feet": 0.092903,
    "ft²": 0.092903,
    "sq in": 0.00064516,
    "sqin": 0.00064516,
    "in²": 0.00064516,
    "acre": 4046.86,
    "acres": 4046.86,
    "ha": 10000.0,
    "hectare": 10000.0,
    "hectares": 10000.0,
}


def normalize_to_meters(value: float, unit: str) -> float:
    """Convert a measurement to meters."""
    unit_lower = unit.lower().strip()
    conversion = UNIT_CONVERSIONS.get(unit_lower)
    if conversion:
        return value * conversion
    # Try without trailing 's'
    if unit_lower.endswith('s'):
        conversion = UNIT_CONVERSIONS.get(unit_lower[:-1])
        if conversion:
            return value * conversion
    logger.warning(f"Unknown unit '{unit}', returning original value")
    return value


def normalize_area_to_sq_meters(value: float, unit: str) -> float:
    """Convert an area measurement to square meters."""
    unit_lower = unit.lower().strip()
    conversion = UNIT_CONVERSIONS.get(unit_lower)
    if conversion:
        return value * conversion
    # Try variations
    for key, conv in UNIT_CONVERSIONS.items():
        if key in unit_lower or unit_lower in key:
            return value * conv
    logger.warning(f"Unknown area unit '{unit}', returning original value")
    return value


# =============================================================================
# Regex Patterns
# =============================================================================

# Dimension pattern: captures numbers with optional decimals followed by units
DIMENSION_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(mm|cm|m|inch|inches|in|ft|feet|foot|yd|yards?|"|\')',
    re.IGNORECASE
)

# Area pattern: captures area measurements
AREA_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(m²|sqm|sq m|square meters?|sq ft|sqft|square feet|ft²|sq in|in²|acres?|ha|hectares?)',
    re.IGNORECASE
)

# Thickness keywords that might indicate a dimension is actually thickness
THICKNESS_KEYWORDS = [
    "thick", "thickness", "depth", "layer", "coating", "paint", "render",
    "plaster", "insulation", "slab", "pour", "bed", "mortar"
]

# Sentence splitter for clause extraction
SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+(?=[A-Z])|\n\n+')


# =============================================================================
# Analysis Functions
# =============================================================================

def extract_dimensions(text: str) -> List[Dimension]:
    """
    Extract dimension measurements from text.
    
    Regex: (\\d+(?:\\.\\d+)?)\\s*(mm|cm|m|inch|ft)
    """
    dimensions = []
    
    # Find all dimension matches with context
    for match in DIMENSION_PATTERN.finditer(text):
        value_str = match.group(1)
        unit = match.group(2)
        value = float(value_str)
        
        # Get surrounding context (100 chars before and after)
        start = max(0, match.start() - 100)
        end = min(len(text), match.end() + 100)
        context = text[start:end].strip()
        
        # Normalize to meters
        value_meters = normalize_to_meters(value, unit)
        
        dimension = Dimension(
            value=value,
            unit=unit,
            value_meters=value_meters,
            original_text=match.group(0),
            context=context
        )
        dimensions.append(dimension)
    
    logger.info(f"Extracted {len(dimensions)} dimensions")
    return dimensions


def extract_areas(text: str) -> List[Area]:
    """
    Extract area measurements from text.
    
    Regex: (\\d+(?:\\.\\d+)?)\\s*(m²|sqm|sq ft|sqm)
    """
    areas = []
    
    for match in AREA_PATTERN.finditer(text):
        value_str = match.group(1)
        unit = match.group(2)
        value = float(value_str)
        
        # Get surrounding context
        start = max(0, match.start() - 100)
        end = min(len(text), match.end() + 100)
        context = text[start:end].strip()
        
        # Normalize to square meters
        value_sq_meters = normalize_area_to_sq_meters(value, unit)
        
        area = Area(
            value=value,
            unit=unit,
            value_sq_meters=value_sq_meters,
            original_text=match.group(0),
            context=context
        )
        areas.append(area)
    
    logger.info(f"Extracted {len(areas)} areas")
    return areas


def calculate_volumes(areas: List[Area], dimensions: List[Dimension]) -> List[Volume]:
    """
    Calculate volumes from area × thickness.
    
    Attempts to match areas with likely thickness dimensions based on context.
    """
    volumes = []
    
    # Identify likely thickness dimensions
    thickness_dims = []
    for dim in dimensions:
        context_lower = dim.context.lower()
        if any(keyword in context_lower for keyword in THICKNESS_KEYWORDS):
            thickness_dims.append(dim)
    
    # If no explicit thickness found, use smallest dimension as fallback
    if not thickness_dims and dimensions:
        # Sort by value in meters and take smallest reasonable one (likely thickness)
        sorted_dims = sorted(dimensions, key=lambda d: d.value_meters)
        for dim in sorted_dims:
            # Only use if it's a small dimension (likely thickness, not length/width)
            if dim.value_meters < 1.0:  # Less than 1 meter
                thickness_dims.append(dim)
                break
    
    # Calculate volume for each area using available thickness
    if thickness_dims:
        # Use the first/most relevant thickness
        thickness = thickness_dims[0]
        
        for area in areas:
            volume_cubic_m = area.value_sq_meters * thickness.value_meters
            
            volume = Volume(
                area_value=area.value,
                thickness_value=thickness.value,
                unit=f"{area.unit} × {thickness.unit}",
                value_cubic_meters=volume_cubic_m,
                calculation_method=f"area({area.value_sq_meters:.4f} m²) × thickness({thickness.value_meters:.4f} m)",
                context=f"{area.context[:100]}... | Thickness: {thickness.original_text}"
            )
            volumes.append(volume)
    
    logger.info(f"Calculated {len(volumes)} volumes")
    return volumes


def perform_takeoff_analysis(text: str) -> TakeoffResult:
    """
    Perform complete quantity takeoff analysis.
    
    Extracts dimensions, areas, and calculates volumes.
    All measurements normalized to meters.
    """
    result = TakeoffResult()
    
    # Extract dimensions
    result.dimensions = extract_dimensions(text)
    
    # Extract areas
    result.areas = extract_areas(text)
    
    # Calculate volumes
    result.volumes = calculate_volumes(result.areas, result.dimensions)
    
    # Calculate totals
    result.total_area_sqm = sum(a.value_sq_meters for a in result.areas)
    result.total_volume_cum = sum(v.value_cubic_meters for v in result.volumes)
    
    return result


def extract_clauses(text: str) -> List[str]:
    """Split text into clauses/sentences for analysis."""
    # Split by sentence boundaries and newlines
    clauses = SENTENCE_PATTERN.split(text)
    # Filter out very short segments and clean
    clauses = [c.strip() for c in clauses if len(c.strip()) > 20]
    return clauses


def assess_clause_risk(clause: str, location: str = "") -> Optional[RiskClause]:
    """
    Assess a single clause for contract risks.
    
    Returns RiskClause if risks found, None otherwise.
    """
    clause_upper = clause.upper()
    found_keywords = []
    risk_levels = []
    
    for keyword, risk_level in RISK_KEYWORDS.items():
        if keyword.upper() in clause_upper:
            found_keywords.append(keyword)
            risk_levels.append(risk_level)
    
    if not found_keywords:
        return None
    
    # Determine highest risk level
    if "red" in risk_levels:
        final_risk = "red"
    elif "yellow" in risk_levels:
        final_risk = "yellow"
    else:
        final_risk = "green"
    
    risk_info = RISK_LEVELS[final_risk]
    
    return RiskClause(
        clause_text=clause,
        keywords_found=found_keywords,
        risk_level=final_risk,
        severity=risk_info["severity"],
        label=risk_info["label"],
        action_required=risk_info["action_required"],
        location=location
    )


def perform_risk_assessment(text: str) -> RiskAssessment:
    """
    Perform contract risk assessment.
    
    Flags sentences containing risk keywords and assigns risk levels.
    """
    result = RiskAssessment()
    
    # Extract clauses
    clauses = extract_clauses(text)
    
    # Analyze each clause
    for i, clause in enumerate(clauses):
        location = f"clause_{i + 1}"
        risk_clause = assess_clause_risk(clause, location)
        if risk_clause:
            result.clauses.append(risk_clause)
    
    # Also scan paragraphs for broader context
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
    for i, para in enumerate(paragraphs):
        # Check if paragraph contains multiple risk keywords
        para_upper = para.upper()
        para_keywords = [k for k in RISK_KEYWORDS.keys() if k.upper() in para_upper]
        
        if len(para_keywords) >= 2:
            # This paragraph has multiple risks - flag it
            risk_levels = [RISK_KEYWORDS[k] for k in para_keywords]
            if "red" in risk_levels:
                final_risk = "red"
            elif "yellow" in risk_levels:
                final_risk = "yellow"
            else:
                final_risk = "green"
            
            risk_info = RISK_LEVELS[final_risk]
            
            # Check if we already captured this as a clause
            already_captured = any(
                para[:100] in rc.clause_text or rc.clause_text in para
                for rc in result.clauses
            )
            
            if not already_captured:
                result.clauses.append(RiskClause(
                    clause_text=para[:500],
                    keywords_found=para_keywords,
                    risk_level=final_risk,
                    severity=risk_info["severity"],
                    label=f"{risk_info['label']} (Multi-clause paragraph)",
                    action_required=risk_info["action_required"],
                    location=f"paragraph_{i + 1}"
                ))
    
    logger.info(f"Found {len(result.clauses)} risk clauses")
    return result


# =============================================================================
# Main Analysis Function
# =============================================================================

def analyze_document(
    text: str,
    document_id: str = "",
    analysis_types: List[str] = None,
    save_to_db: bool = True
) -> Dict[str, Any]:
    """
    Analyze a document using rule-based extraction.
    
    Args:
        text: Extracted text from OCR
        document_id: Unique document identifier
        analysis_types: List of analysis types to perform ['takeoffs', 'risk', 'all']
        save_to_db: Whether to save results to database
        
    Returns:
        Structured JSON with analysis results
    """
    if analysis_types is None:
        analysis_types = ["all"]
    
    if not text or not text.strip():
        return {
            "document_id": document_id,
            "success": False,
            "error": "Empty text provided",
            "takeoffs": None,
            "risk_assessment": None,
            "metadata": {"timestamp": datetime.utcnow().isoformat()}
        }
    
    do_takeoffs = "all" in analysis_types or "takeoffs" in analysis_types
    do_risk = "all" in analysis_types or "risk" in analysis_types
    
    try:
        result = AnalysisResult(
            document_id=document_id,
            success=True,
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "text_length": len(text),
                "analysis_types": analysis_types
            }
        )
        
        # Feature A: Quantity Takeoffs
        if do_takeoffs:
            logger.info(f"Performing takeoff analysis for document {document_id}")
            result.takeoffs = perform_takeoff_analysis(text)
        
        # Feature B: Contract Risk Assessment
        if do_risk:
            logger.info(f"Performing risk assessment for document {document_id}")
            result.risk_assessment = perform_risk_assessment(text)
        
        # Save to database if requested
        if save_to_db and document_id:
            save_analysis_result(result)
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return {
            "document_id": document_id,
            "success": False,
            "error": str(e),
            "takeoffs": None,
            "risk_assessment": None,
            "metadata": {"timestamp": datetime.utcnow().isoformat()}
        }


def save_analysis_result(result: AnalysisResult) -> bool:
    """
    Save analysis result to SQLite database.
    
    Uses existing db connection from app.db.session.
    """
    try:
        from uuid import uuid4
        
        with get_sync_db_context() as db:
            analysis_record = DocumentAnalysis(
                id=str(uuid4()),
                document_id=result.document_id,
                analysis_type="full" if (result.takeoffs and result.risk_assessment) else 
                            ("takeoffs" if result.takeoffs else "risk"),
                takeoffs=result.takeoffs.to_dict() if result.takeoffs else None,
                risk_assessment=result.risk_assessment.to_dict() if result.risk_assessment else None,
                raw_results=result.to_dict(),
                status="completed" if result.success else "failed"
            )
            
            db.add(analysis_record)
            db.commit()
            
            logger.info(f"Saved analysis result for document {result.document_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to save analysis result: {e}", exc_info=True)
        return False


# =============================================================================
# Utility Functions
# =============================================================================

def get_analysis_by_document(document_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve analysis results for a specific document."""
    try:
        with get_sync_db_context() as db:
            from sqlalchemy import select
            stmt = select(DocumentAnalysis).where(DocumentAnalysis.document_id == document_id)
            result = db.execute(stmt).scalar_one_or_none()
            
            if result:
                return {
                    "id": result.id,
                    "document_id": result.document_id,
                    "analysis_type": result.analysis_type,
                    "takeoffs": result.takeoffs,
                    "risk_assessment": result.risk_assessment,
                    "created_at": result.created_at.isoformat() if result.created_at else None,
                    "status": result.status
                }
            return None
            
    except Exception as e:
        logger.error(f"Failed to retrieve analysis: {e}")
        return None


def format_takeoff_report(result: TakeoffResult) -> str:
    """Format takeoff results as a human-readable report."""
    lines = [
        "=" * 60,
        "QUANTITY TAKEOFF REPORT",
        "=" * 60,
        "",
        f"Dimensions Found: {len(result.dimensions)}",
        f"Areas Found: {len(result.areas)}",
        f"Volumes Calculated: {len(result.volumes)}",
        "",
        "TOTALS:",
        f"  Total Area: {result.total_area_sqm:.2f} m²",
        f"  Total Volume: {result.total_volume_cum:.3f} m³",
        "",
    ]
    
    if result.dimensions:
        lines.extend(["DIMENSIONS:", "-" * 40])
        for d in result.dimensions[:10]:  # Show first 10
            lines.append(f"  {d.original_text} = {d.value_meters:.4f} m")
        if len(result.dimensions) > 10:
            lines.append(f"  ... and {len(result.dimensions) - 10} more")
        lines.append("")
    
    if result.areas:
        lines.extend(["AREAS:", "-" * 40])
        for a in result.areas[:10]:
            lines.append(f"  {a.original_text} = {a.value_sq_meters:.2f} m²")
        if len(result.areas) > 10:
            lines.append(f"  ... and {len(result.areas) - 10} more")
        lines.append("")
    
    lines.append("=" * 60)
    return "\n".join(lines)


def format_risk_report(assessment: RiskAssessment) -> str:
    """Format risk assessment as a human-readable report."""
    summary = assessment._calculate_summary()
    
    lines = [
        "=" * 60,
        "CONTRACT RISK ASSESSMENT REPORT",
        "=" * 60,
        "",
        f"Total Clauses Analyzed: {summary['total_clauses']}",
        f"Risk Breakdown:",
        f"  🔴 High Risk (Red): {summary['risk_breakdown']['red']}",
        f"  🟡 Medium Risk (Yellow): {summary['risk_breakdown']['yellow']}",
        f"  🟢 Low Risk (Green): {summary['risk_breakdown']['green']}",
        "",
    ]
    
    if summary['requires_action']:
        lines.append("⚠️  ACTION REQUIRED: High-risk clauses detected")
        lines.append("")
    
    if assessment.clauses:
        lines.extend(["FLAGGED CLAUSES:", "-" * 40])
        for clause in assessment.clauses[:5]:  # Show first 5
            emoji = "🔴" if clause.risk_level == "red" else ("🟡" if clause.risk_level == "yellow" else "🟢")
            lines.append(f"{emoji} {clause.label}")
            lines.append(f"   Keywords: {', '.join(clause.keywords_found)}")
            text_preview = clause.clause_text[:100].replace('\n', ' ')
            lines.append(f"   Text: {text_preview}...")
            lines.append("")
    
    lines.append("=" * 60)
    return "\n".join(lines)


# =============================================================================
# Quick Test
# =============================================================================

if __name__ == "__main__":
    # Test with sample construction document text
    sample_text = """
    CONSTRUCTION SPECIFICATIONS
    
    Project: Commercial Building Extension
    
    Foundation:
    - Concrete slab thickness: 150 mm
    - Area: 450 sqm
    - Total volume required: 67.5 cubic meters
    
    Walls:
    - External wall length: 25.5 m
    - Wall height: 3.2 m
    - Wall thickness: 200 mm
    
    Flooring:
    - Ground floor area: 420 sqm
    - Screed thickness: 50 mm
    
    CONTRACT TERMS
    
    Payment terms: Net 30 days from invoice date.
    
    Liquidated Damages: Contractor shall pay $500 per day for delays 
    beyond the agreed completion date.
    
    Force Majeure: Neither party shall be liable for delays caused by 
    events beyond reasonable control including natural disasters, war, 
    or government actions.
    
    Termination: Owner may terminate this contract with 30 days written 
    notice. Upon Termination, Contractor shall be paid for work completed 
    to date.
    
    Indemnification: Contractor agrees to indemnify and hold harmless 
    Owner from all claims arising from Contractor's negligence.
    """
    
    print("Testing Rule-Based Document Analyzer")
    print("=" * 60)
    
    result = analyze_document(
        text=sample_text,
        document_id="test-doc-001",
        analysis_types=["all"],
        save_to_db=False
    )
    
    print("\nANALYSIS RESULT:")
    print(json.dumps(result, indent=2, default=str))
    
    if result.get("takeoffs"):
        print("\n" + format_takeoff_report(TakeoffResult(
            dimensions=[Dimension(**d) for d in result["takeoffs"]["dimensions"]],
            areas=[Area(**a) for a in result["takeoffs"]["areas"]],
            volumes=[Volume(**v) for v in result["takeoffs"]["volumes"]],
            total_area_sqm=result["takeoffs"]["total_area_sqm"],
            total_volume_cum=result["takeoffs"]["total_volume_cum"]
        )))
    
    if result.get("risk_assessment"):
        ra = result["risk_assessment"]
        risk_obj = RiskAssessment(
            clauses=[RiskClause(**c) for c in ra["clauses"]]
        )
        print("\n" + format_risk_report(risk_obj))
    
    print("\n✅ Test completed successfully!")
