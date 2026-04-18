"""
Context Analyzer for Project-Aware Recommendations

Analyzes project context to extract relevant features for
context-aware recommendation generation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from app.core.logging import get_logger

logger = get_logger(__name__)


class ProjectType(str, Enum):
    """Types of construction projects."""
    CONCRETE = "concrete"
    STRUCTURAL = "structural"
    EARTHWORK = "earthwork"
    MASONRY = "masonry"
    STEEL = "steel"
    GENERAL = "general"
    INFRASTRUCTURE = "infrastructure"
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"


class WorkflowPhase(str, Enum):
    """Phases of construction workflow."""
    PLANNING = "planning"
    DESIGN = "design"
    COST_ESTIMATION = "cost_estimation"
    PRE_CONSTRUCTION = "pre_construction"
    CONSTRUCTION = "construction"
    QUALITY_CONTROL = "quality_control"
    COMPLETION = "completion"
    MAINTENANCE = "maintenance"


@dataclass
class ProjectContext:
    """Analyzed project context."""
    project_type: str = "general"
    workflow_phase: str = "general"
    tags: List[str] = field(default_factory=list)
    detected_elements: List[str] = field(default_factory=list)
    user_intent: str = ""
    location_context: Dict[str, Any] = field(default_factory=dict)
    project_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_type": self.project_type,
            "workflow_phase": self.workflow_phase,
            "tags": self.tags,
            "detected_elements": self.detected_elements,
            "user_intent": self.user_intent,
            "location_context": self.location_context,
            "project_metadata": self.project_metadata,
        }


class ContextAnalyzer:
    """
    Analyzes context data to extract meaningful features.
    
    Uses keyword matching, pattern recognition, and semantic
    analysis to understand the user's current context.
    """
    
    # Keywords for project type detection
    PROJECT_TYPE_KEYWORDS = {
        ProjectType.CONCRETE: [
            "concrete", "cement", "slab", "foundation", "pouring", 
            "curing", "formwork", "rebar", "reinforcement"
        ],
        ProjectType.STRUCTURAL: [
            "structural", "beam", "column", "frame", "load", "moment",
            "shear", "deflection", "analysis", "capacity"
        ],
        ProjectType.EARTHWORK: [
            "earthwork", "excavation", "fill", "cut", "grading", "soil",
            "compaction", "slope", "embankment", "trench"
        ],
        ProjectType.MASONRY: [
            "masonry", "brick", "block", "wall", "mortar", "stone"
        ],
        ProjectType.STEEL: [
            "steel", "welding", "connection", "truss", "frame", "metal"
        ],
        ProjectType.INFRASTRUCTURE: [
            "road", "bridge", "tunnel", "dam", "pipeline", "utility"
        ],
        ProjectType.RESIDENTIAL: [
            "house", "home", "residential", "apartment", "dwelling"
        ],
        ProjectType.COMMERCIAL: [
            "commercial", "office", "retail", "building", "high-rise"
        ],
    }
    
    # Keywords for workflow phase detection
    WORKFLOW_PHASE_KEYWORDS = {
        WorkflowPhase.PLANNING: [
            "plan", "schedule", "estimate", "budget", "feasibility"
        ],
        WorkflowPhase.DESIGN: [
            "design", "calculate", "specify", "drawing", "blueprint"
        ],
        WorkflowPhase.COST_ESTIMATION: [
            "cost", "price", "quote", "bid", "estimate", "budget", "material cost"
        ],
        WorkflowPhase.PRE_CONSTRUCTION: [
            "permits", "approvals", "site prep", "mobilization"
        ],
        WorkflowPhase.CONSTRUCTION: [
            "build", "construct", "install", "erect", "place", "pour"
        ],
        WorkflowPhase.QUALITY_CONTROL: [
            "test", "inspect", "quality", "check", "verify", "compliance"
        ],
        WorkflowPhase.COMPLETION: [
            "finish", "complete", "handover", "closeout", "punch list"
        ],
    }
    
    # Element detection patterns
    ELEMENT_PATTERNS = {
        "beam": ["beam", "girder", "joist", "lintel"],
        "column": ["column", "pillar", "post", "pier"],
        "slab": ["slab", "deck", "floor", "roof"],
        "foundation": ["foundation", "footing", "pile", "caisson"],
        "wall": ["wall", "partition", "shear wall", "retaining wall"],
        "rebar": ["rebar", "reinforcement", "steel bar", "mesh"],
        "formwork": ["formwork", "shuttering", "mold", "falsework"],
        "concrete": ["concrete", "cement", "pour", "placement"],
        "excavation": ["excavation", "trench", "cut", "dig"],
        "fill": ["fill", "backfill", "embankment", "raise"],
    }
    
    def __init__(self):
        self._project_type_cache: Dict[str, str] = {}
        self._phase_cache: Dict[str, str] = {}
    
    def analyze(self, context: Dict[str, Any]) -> ProjectContext:
        """
        Analyze context data and return structured project context.
        
        Args:
            context: Raw context data from user input, project data, etc.
            
        Returns:
            Structured ProjectContext
        """
        # Extract text fields for analysis
        text_to_analyze = self._extract_text(context)
        
        # Detect project type
        project_type = self._detect_project_type(text_to_analyze, context)
        
        # Detect workflow phase
        workflow_phase = self._detect_workflow_phase(text_to_analyze, context)
        
        # Extract tags
        tags = self._extract_tags(text_to_analyze, context)
        
        # Detect elements
        detected_elements = self._detect_elements(text_to_analyze)
        
        # Detect user intent
        user_intent = self._detect_intent(text_to_analyze)
        
        # Extract location context
        location_context = self._extract_location_context(context)
        
        # Extract project metadata
        project_metadata = self._extract_metadata(context)
        
        return ProjectContext(
            project_type=project_type,
            workflow_phase=workflow_phase,
            tags=tags,
            detected_elements=detected_elements,
            user_intent=user_intent,
            location_context=location_context,
            project_metadata=project_metadata,
        )
    
    def _extract_text(self, context: Dict[str, Any]) -> str:
        """Extract text from context for analysis."""
        text_parts = []
        
        # Common text fields to analyze
        text_fields = [
            "description", "name", "title", "query", "input", "message",
            "notes", "comments", "specifications", "scope", "details"
        ]
        
        for field in text_fields:
            if field in context and isinstance(context[field], str):
                text_parts.append(context[field])
        
        # Also check nested structures
        if "project" in context and isinstance(context["project"], dict):
            project = context["project"]
            for field in text_fields:
                if field in project and isinstance(project[field], str):
                    text_parts.append(project[field])
        
        return " ".join(text_parts).lower()
    
    def _detect_project_type(
        self,
        text: str,
        context: Dict[str, Any],
    ) -> str:
        """Detect project type from context."""
        # Check explicit project_type in context
        if "project_type" in context:
            return str(context["project_type"]).lower()
        
        if "project" in context and isinstance(context["project"], dict):
            if "type" in context["project"]:
                return str(context["project"]["type"]).lower()
        
        # Analyze text for keywords
        scores = {}
        for project_type, keywords in self.PROJECT_TYPE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[project_type.value] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return ProjectType.GENERAL.value
    
    def _detect_workflow_phase(
        self,
        text: str,
        context: Dict[str, Any],
    ) -> str:
        """Detect workflow phase from context."""
        # Check explicit phase in context
        if "phase" in context:
            return str(context["phase"]).lower()
        
        if "workflow_phase" in context:
            return str(context["workflow_phase"]).lower()
        
        if "status" in context:
            status = str(context["status"]).lower()
            if status in ["planning", "design", "estimation", "construction", "completed"]:
                return status
        
        # Analyze text for keywords
        scores = {}
        for phase, keywords in self.WORKFLOW_PHASE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                scores[phase.value] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return "general"
    
    def _extract_tags(
        self,
        text: str,
        context: Dict[str, Any],
    ) -> List[str]:
        """Extract relevant tags from context."""
        tags = set()
        
        # Get explicit tags
        if "tags" in context and isinstance(context["tags"], list):
            tags.update(str(t).lower() for t in context["tags"])
        
        # Detect from text
        all_keywords = []
        for keywords in self.PROJECT_TYPE_KEYWORDS.values():
            all_keywords.extend(keywords)
        for keywords in self.WORKFLOW_PHASE_KEYWORDS.values():
            all_keywords.extend(keywords)
        
        for keyword in all_keywords:
            if keyword in text:
                tags.add(keyword)
        
        return list(tags)
    
    def _detect_elements(self, text: str) -> List[str]:
        """Detect construction elements in text."""
        detected = []
        
        for element, patterns in self.ELEMENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in text:
                    detected.append(element)
                    break
        
        return detected
    
    def _detect_intent(self, text: str) -> str:
        """Detect user intent from text."""
        # Intent detection patterns
        intent_patterns = {
            "calculate": ["calculate", "compute", "determine", "find", "solve", "what is"],
            "estimate": ["estimate", "approximate", "predict", "forecast"],
            "check": ["check", "verify", "validate", "confirm", "inspect"],
            "compare": ["compare", "versus", "vs", "difference", "better"],
            "optimize": ["optimize", "improve", "reduce", "minimize", "maximize"],
            "learn": ["how", "explain", "what", "why", "teach", "show me"],
        }
        
        scores = {}
        for intent, patterns in intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in text)
            if score > 0:
                scores[intent] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return "general"
    
    def _extract_location_context(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract location-related context."""
        location = {}
        
        if "location" in context:
            location["primary"] = context["location"]
        
        if "region" in context:
            location["region"] = context["region"]
        
        if "country" in context:
            location["country"] = context["country"]
        
        if "climate" in context:
            location["climate"] = context["climate"]
        
        # Soil/ground conditions
        if "soil_type" in context:
            location["soil_type"] = context["soil_type"]
        
        if "ground_conditions" in context:
            location["ground_conditions"] = context["ground_conditions"]
        
        return location
    
    def _extract_metadata(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract project metadata."""
        metadata = {}
        
        # Numeric metadata
        numeric_fields = [
            "budget", "area", "volume", "height", "length", "width",
            "duration", "team_size", "complexity"
        ]
        
        for field in numeric_fields:
            if field in context:
                metadata[field] = context[field]
        
        # Categorical metadata
        categorical_fields = [
            "building_type", "construction_type", "design_standard",
            "safety_level", "quality_level"
        ]
        
        for field in categorical_fields:
            if field in context:
                metadata[field] = context[field]
        
        # Nested project metadata
        if "project" in context and isinstance(context["project"], dict):
            for field in numeric_fields + categorical_fields:
                if field in context["project"]:
                    metadata[field] = context["project"][field]
        
        return metadata
    
    def quick_analyze(self, text: str) -> ProjectContext:
        """Quick analysis from a single text string."""
        return self.analyze({"description": text})
    
    def get_suggested_tags(self, partial_tag: str) -> List[str]:
        """Get tag suggestions based on partial input."""
        partial = partial_tag.lower()
        suggestions = []
        
        all_tags = set()
        for keywords in self.PROJECT_TYPE_KEYWORDS.values():
            all_tags.update(keywords)
        for keywords in self.WORKFLOW_PHASE_KEYWORDS.values():
            all_tags.update(keywords)
        for elements in self.ELEMENT_PATTERNS.values():
            all_tags.update(elements)
        
        for tag in all_tags:
            if partial in tag or tag in partial:
                suggestions.append(tag)
        
        return sorted(suggestions)[:10]


# Global analyzer instance
_context_analyzer: Optional[ContextAnalyzer] = None


def get_context_analyzer() -> ContextAnalyzer:
    """Get or create global context analyzer."""
    global _context_analyzer
    
    if _context_analyzer is None:
        _context_analyzer = ContextAnalyzer()
    
    return _context_analyzer
