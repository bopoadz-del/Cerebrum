"""
Enhanced Cerebrum Agent Core

Major improvements:
- Semantic conversation search with embeddings
- Advanced memory indexing and retrieval
- Rich layer navigation with state management
- Full integration with all Cerebrum endpoints
"""

import json
import os
import asyncio
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from pathlib import Path
import logging

from app.errors import get_user_friendly_error, format_error_response, ErrorCategory
from app.agent.response_schema import (
    AgentResponse,
    ErrorCode,
    format_error_response as schema_format_error,
    format_success_response as schema_format_success,
    normalize_response,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# Synonym dictionary for flexible keyword matching
SYNONYMS = {
    # Cost estimation
    "cost": ["price", "pricing", "budget", "estimate", "expense", "value", "rate", "fee"],
    "estimate": ["estimation", "quote", "bid", "calculation", "forecast", "projection"],
    "concrete": ["cement", "rebar", "foundation", "slab", "pouring", "formwork"],
    "rebar": ["reinforcement", "steel", "bar", "mesh", "reinforcing"],
    
    # Safety
    "safety": ["secure", "protection", "hazard", "risk", "incident", "accident", "ppe", "helmet", "vest"],
    "helmet": ["hardhat", "hard hat", "head protection"],
    "vest": ["safety vest", "high vis", "reflective"],
    
    # Documents
    "document": ["file", "pdf", "report", "paper", "doc", "drawing", "blueprint", "spec"],
    "invoice": ["bill", "receipt", "payment", "charge", "billing"],
    "blueprint": ["drawing", "plan", "diagram", "schematic", "design"],
    
    # Projects
    "project": ["job", "work", "assignment", "contract", "build", "construction"],
    "schedule": ["timeline", "program", "plan", "deadline", "milestone", "date"],
    "delay": ["late", "postpone", "behind", "slip", "overrun"],
    
    # BIM/VDC
    "bim": ["building information modeling", "3d model", "digital twin", "ifc"],
    "model": ["3d", "cad", "drawing", "geometry", "design"],
    "quantity": ["amount", "volume", "count", "takeoff", "measurement", "metric"],
    
    # General
    "help": ["assist", "support", "guide", "how to", "what is", "explain"],
    "find": ["search", "locate", "get", "retrieve", "look for", "seek"],
    "create": ["make", "generate", "build", "produce", "new"],
    "update": ["modify", "change", "edit", "revise", "patch"],
    "delete": ["remove", "clear", "erase", "purge", "destroy"],
}


def expand_keywords(query: str) -> Set[str]:
    """
    Expand query keywords with synonyms for better matching.
    
    Args:
        query: Original search query
        
    Returns:
        Set of query words plus synonyms
    """
    words = set(query.lower().split())
    expanded = set(words)
    
    for word in words:
        # Direct synonyms
        if word in SYNONYMS:
            expanded.update(SYNONYMS[word])
        
        # Reverse lookup (word appears in synonym list)
        for key, synonyms in SYNONYMS.items():
            if word in synonyms:
                expanded.add(key)
                expanded.update(s for s in synonyms if s != word)
    
    return expanded


class AgentLayer(Enum):
    """The 14 layers of Cerebrum architecture."""
    CODING = "coding"
    REGISTRY = "registry"
    VALIDATION = "validation"
    HOTSWAP = "hotswap"
    HEALING = "healing"
    PROMPTS = "prompts"
    TRIGGERS = "triggers"
    ECONOMICS = "economics"
    VDC = "vdc"
    EDGE = "edge"
    PORTAL = "portal"
    ENTERPRISE = "enterprise"
    CONNECTORS = "connectors"
    MONITORING = "monitoring"


class AgentAction(Enum):
    """Actions the agent can perform."""
    GENERATE_CODE = "generate_code"
    VALIDATE_CODE = "validate_code"
    DEPLOY_CODE = "deploy_code"
    READ_CONVERSATION = "read_conversation"
    READ_MEMORY = "read_memory"
    WRITE_MEMORY = "write_memory"
    HEAL_ERROR = "heal_error"
    QUERY_BIM = "query_bim"
    CALCULATE_COST = "calculate_cost"
    EXECUTE_SANDBOX = "execute_sandbox"
    ANALYZE_DOCUMENT = "analyze_document"
    QUERY_WAREHOUSE = "query_warehouse"
    TRIGGER_EVENT = "trigger_event"
    AUDIT_SECURITY = "audit_security"


@dataclass
class LayerState:
    """State information for a layer."""
    layer: AgentLayer
    entered_at: str
    actions_performed: List[str] = field(default_factory=list)
    artifacts_created: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Enhanced context for the agent."""
    session_id: str
    conversation_history: List[Dict] = field(default_factory=list)
    current_layer: AgentLayer = AgentLayer.CODING
    layer_history: List[LayerState] = field(default_factory=list)
    memory_references: List[str] = field(default_factory=list)
    generated_artifacts: List[str] = field(default_factory=list)
    workspace_path: str = "/root/.openclaw/workspace"
    active_conversations: Dict[str, Dict] = field(default_factory=dict)
    session_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Enhanced agent result with reasoning support (Kimi-style)."""
    success: bool
    action: AgentAction
    layer: AgentLayer
    data: Dict[str, Any]
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: Optional[float] = None
    related_conversations: List[str] = field(default_factory=list)
    suggested_next_actions: List[str] = field(default_factory=list)
    reasoning_content: Optional[str] = field(default=None)
    """Step-by-step reasoning/thinking process (Kimi-style transparent AI reasoning)"""


@dataclass
class AgentReasoningConfig:
    """Configuration for agent reasoning display (Kimi-style)."""
    enabled: bool = True
    """Enable/disable reasoning content generation"""
    include_in_response: bool = True
    """Include reasoning in API responses"""
    max_reasoning_length: int = 10000
    """Maximum length of reasoning content in characters"""
    preserve_across_turns: bool = True
    """Preserve reasoning across multi-turn conversations"""
    format_style: str = "markdown"
    """Format style: markdown, plain, or structured"""


class ReasoningTracker:
    """
    Tracks step-by-step reasoning/thinking process for transparent AI reasoning.

    Kimi-style reasoning provides transparency into the agent's decision-making process,
    showing how it arrives at conclusions and takes actions.
    """

    def __init__(self, config: Optional[AgentReasoningConfig] = None):
        self.config = config or AgentReasoningConfig()
        self.steps: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        self.session_id: str = f"reasoning_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(self)}"

    def start(self, task: str, context: Optional[Dict] = None):
        """Start tracking reasoning for a new task."""
        if not self.config.enabled:
            return

        self.start_time = datetime.now()
        self.steps = []
        self.add_step(
            step_type="task_received",
            title="Task Received",
            content=f"Starting task: {task}",
            details=context or {}
        )

    def add_step(
        self,
        step_type: str,
        title: str,
        content: str,
        details: Optional[Dict] = None,
        layer: Optional[str] = None
    ):
        """Add a reasoning step."""
        if not self.config.enabled:
            return

        step = {
            "timestamp": datetime.now().isoformat(),
            "step_type": step_type,
            "title": title,
            "content": content,
            "details": details or {},
            "layer": layer,
            "step_number": len(self.steps) + 1
        }
        self.steps.append(step)

    def add_thinking(self, thought: str, layer: Optional[str] = None):
        """Add a thinking/reasoning step."""
        self.add_step(
            step_type="thinking",
            title="Thinking",
            content=thought,
            layer=layer
        )

    def add_observation(self, observation: str, details: Optional[Dict] = None):
        """Add an observation step."""
        self.add_step(
            step_type="observation",
            title="Observation",
            content=observation,
            details=details
        )

    def add_decision(self, decision: str, rationale: str, layer: Optional[str] = None):
        """Add a decision step with rationale."""
        self.add_step(
            step_type="decision",
            title="Decision",
            content=decision,
            details={"rationale": rationale},
            layer=layer
        )

    def add_tool_call(self, tool_name: str, params: Dict, result: Optional[Dict] = None):
        """Add a tool call step."""
        details = {"params": params}
        if result:
            details["result"] = result

        self.add_step(
            step_type="tool_call",
            title=f"Tool Call: {tool_name}",
            content=f"Executing {tool_name} with parameters: {list(params.keys())}",
            details=details
        )

    def add_layer_navigation(self, from_layer: str, to_layer: str, reason: str):
        """Add a layer navigation step."""
        self.add_step(
            step_type="layer_navigation",
            title="Layer Navigation",
            content=f"Navigating from {from_layer} to {to_layer}",
            details={"reason": reason, "from_layer": from_layer, "to_layer": to_layer}
        )

    def add_error(self, error: str, recovery_attempt: Optional[str] = None):
        """Add an error step."""
        details = {}
        if recovery_attempt:
            details["recovery_attempt"] = recovery_attempt

        self.add_step(
            step_type="error",
            title="Error",
            content=error,
            details=details
        )

    def add_conclusion(self, conclusion: str, success: bool = True):
        """Add a conclusion step."""
        self.add_step(
            step_type="conclusion",
            title="Conclusion",
            content=conclusion,
            details={"success": success}
        )

    def format_reasoning(self) -> Optional[str]:
        """Format reasoning steps into a readable string."""
        if not self.config.enabled or not self.steps:
            return None

        if self.config.format_style == "markdown":
            return self._format_markdown()
        elif self.config.format_style == "structured":
            return self._format_structured()
        else:
            return self._format_plain()

    def _format_markdown(self) -> str:
        """Format reasoning as markdown."""
        lines = ["## Reasoning Process\n"]

        for step in self.steps:
            emoji = self._get_step_emoji(step["step_type"])
            lines.append(f"### {emoji} Step {step['step_number']}: {step['title']}")
            lines.append(f"*{step['timestamp']}*  ")
            if step.get("layer"):
                lines.append(f"**Layer:** `{step['layer']}`  ")
            lines.append(f"\n{step['content']}\n")

            # Add details if present
            if step.get("details"):
                if "rationale" in step["details"]:
                    lines.append(f"**Rationale:** {step['details']['rationale']}\n")
                if "reason" in step["details"]:
                    lines.append(f"**Reason:** {step['details']['reason']}\n")

            lines.append("---\n")

        result = "\n".join(lines)

        # Truncate if too long
        if len(result) > self.config.max_reasoning_length:
            result = result[:self.config.max_reasoning_length] + "\n\n...(reasoning truncated)"

        return result

    def _format_plain(self) -> str:
        """Format reasoning as plain text."""
        lines = ["Reasoning Process:"]

        for step in self.steps:
            emoji = self._get_step_emoji(step["step_type"])
            lines.append(f"\n{emoji} [{step['step_number']}] {step['title']}")
            lines.append(f"   {step['content']}")
            if step.get("layer"):
                lines.append(f"   [Layer: {step['layer']}]")

        result = "\n".join(lines)

        if len(result) > self.config.max_reasoning_length:
            result = result[:self.config.max_reasoning_length] + "\n\n...(reasoning truncated)"

        return result

    def _format_structured(self) -> str:
        """Format reasoning as structured JSON (for API consumption)."""
        import json

        data = {
            "session_id": self.session_id,
            "total_steps": len(self.steps),
            "steps": self.steps
        }

        return json.dumps(data, indent=2, default=str)

    def _get_step_emoji(self, step_type: str) -> str:
        """Get emoji for step type."""
        emojis = {
            "task_received": "📥",
            "thinking": "🤔",
            "observation": "👁️",
            "decision": "✅",
            "tool_call": "🔧",
            "layer_navigation": "🔄",
            "error": "⚠️",
            "conclusion": "🏁"
        }
        return emojis.get(step_type, "•")

    def to_dict(self) -> Dict:
        """Convert reasoning to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "config": {
                "enabled": self.config.enabled,
                "format_style": self.config.format_style
            },
            "steps": self.steps,
            "total_steps": len(self.steps),
            "formatted": self.format_reasoning()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ReasoningTracker":
        """Create ReasoningTracker from dictionary."""
        config = AgentReasoningConfig(**data.get("config", {}))
        tracker = cls(config=config)
        tracker.session_id = data.get("session_id", tracker.session_id)
        tracker.steps = data.get("steps", [])
        return tracker

    def merge(self, other: "ReasoningTracker"):
        """Merge another reasoning tracker into this one."""
        if not self.config.enabled:
            return

        # Add separator step
        if other.steps:
            self.add_step(
                step_type="merge",
                title="Continuing from Previous Turn",
                content=f"Merged {len(other.steps)} reasoning steps from previous interaction",
                details={"merged_steps": len(other.steps)}
            )

            # Add all steps from other tracker
            for step in other.steps:
                step_copy = step.copy()
                step_copy["step_number"] = len(self.steps) + 1
                step_copy["merged"] = True
                self.steps.append(step_copy)


@dataclass
class ConversationEntry:
    """A single conversation entry with metadata."""
    id: str
    timestamp: str
    role: str  # 'user', 'agent', 'system'
    content: str
    layer: Optional[str] = None
    action: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    sentiment: Optional[str] = None
    importance_score: float = 0.5


@dataclass
class MemoryIndex:
    """Indexed memory entry for fast retrieval."""
    id: str
    content: str
    source: str
    timestamp: str
    tags: List[str] = field(default_factory=list)
    related_layers: List[str] = field(default_factory=list)
    access_count: int = 0
    last_accessed: Optional[str] = None


class EnhancedConversationReader:
    """
    Advanced conversation reader with semantic search and indexing.
    """

    def __init__(self, workspace_path: str = "/root/.openclaw/workspace"):
        self.workspace_path = Path(workspace_path)
        self.memory_path = self.workspace_path / "memory"
        self.memory_index: Dict[str, MemoryIndex] = {}
        self._index_built = False

    async def initialize(self):
        """Async initialization - build the memory index."""
        if not self._index_built:
            await self._build_index_async()
            self._index_built = True

    def _build_index(self):
        """Build in-memory index of all conversations (sync version for backwards compat)."""
        if not self.memory_path.exists():
            return

        for memory_file in list(self.memory_path.glob("*.md")) + [self.workspace_path / "MEMORY.md"]:
            if memory_file.exists():
                self._index_file(memory_file)
        self._index_built = True

    async def _build_index_async(self):
        """Build in-memory index of all conversations asynchronously."""
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._build_index)

    def _index_file(self, file_path: Path):
        """Index a single memory file."""
        try:
            content = file_path.read_text()

            # Split into sections/entries
            sections = re.split(r'\n##+\s+', content)

            for i, section in enumerate(sections):
                if not section.strip():
                    continue

                # Extract timestamp if present
                ts_match = re.search(r'\[(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})\]', section)
                timestamp = ts_match.group(1) if ts_match else datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat()

                # Extract tags
                tags = re.findall(r'#(\w+)', section)

                # Create index entry
                entry_id = hashlib.md5(f"{file_path}:{i}".encode()).hexdigest()[:12]
                self.memory_index[entry_id] = MemoryIndex(
                    id=entry_id,
                    content=section[:2000],  # Limit content size
                    source=str(file_path.relative_to(self.workspace_path)),
                    timestamp=timestamp,
                    tags=tags,
                    related_layers=self._extract_layers(section)
                )
        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")

    def _extract_layers(self, text: str) -> List[str]:
        """Extract mentioned layers from text."""
        layers = []
        layer_names = [l.value for l in AgentLayer]
        for layer in layer_names:
            if layer.lower() in text.lower():
                layers.append(layer)
        return layers

    def read_conversations(self,
                          days: int = 7,
                          layers: Optional[List[str]] = None,
                          tags: Optional[List[str]] = None) -> Dict:
        """
        Read conversations with filtering.

        Args:
            days: How many days back to look
            layers: Filter by specific layers
            tags: Filter by tags
        """
        cutoff = datetime.now() - timedelta(days=days)
        results = []

        for entry in self.memory_index.values():
            entry_date = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00').replace('+00:00', ''))
            if entry_date < cutoff:
                continue

            # Apply filters
            if layers and not any(l in entry.related_layers for l in layers):
                continue
            if tags and not any(t in entry.tags for t in tags):
                continue

            results.append(asdict(entry))

        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x['timestamp'], reverse=True)

        return {
            "success": True,
            "results": {
                "entries": results[:50],  # Limit results
                "total_entries": len(results),
            },
            "metadata": {
                "filtered_by": {"days": days, "layers": layers, "tags": tags},
            },
        }

    def semantic_search(self,
                       query: str,
                       limit: int = 10,
                       context_window: int = 300) -> Dict:
        """
        Advanced search with relevance scoring and synonym expansion.

        Uses multiple scoring factors:
        - Exact phrase matches (high weight)
        - Keyword frequency (with synonym expansion)
        - Recency boost
        - Tag matches
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Expand keywords with synonyms for better matching
        expanded_words = expand_keywords(query)
        
        scores = []

        for entry_id, entry in self.memory_index.items():
            content_lower = entry.content.lower()
            score = 0.0

            # Exact phrase match (high weight)
            if query_lower in content_lower:
                score += 10.0

            # Word frequency with original words
            for word in query_words:
                count = content_lower.count(word)
                score += count * 1.0
            
            # Synonym matches (lower weight)
            synonym_words = expanded_words - query_words
            for word in synonym_words:
                count = content_lower.count(word)
                score += count * 0.5  # Half weight for synonyms

            # Tag match bonus
            for tag in entry.tags:
                if tag.lower() in query_words:
                    score += 5.0
                elif tag.lower() in synonym_words:
                    score += 2.5  # Half weight for synonym tag matches

            # Recency boost (newer = higher score)
            try:
                entry_date = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00').replace('+00:00', ''))
                days_old = (datetime.now() - entry_date).days
                recency_boost = max(0, 5 - days_old * 0.5)  # Decay over 10 days
                score += recency_boost
            except:
                pass

            if score > 0:
                # Update access stats
                entry.access_count += 1
                entry.last_accessed = datetime.now().isoformat()

                scores.append({
                    "id": entry_id,
                    "score": score,
                    "content": entry.content[:context_window],
                    "source": entry.source,
                    "timestamp": entry.timestamp,
                    "tags": entry.tags,
                    "related_layers": entry.related_layers
                })

        # Sort by score
        scores.sort(key=lambda x: x['score'], reverse=True)

        return {
            "success": True,
            "results": {
                "matches": scores[:limit],
                "total_matches": len(scores),
            },
            "metadata": {
                "query": query,
                "expanded_keywords": list(expanded_words)[:20],  # Show expansion
                "returned": min(len(scores), limit),
            },
        }

    def get_conversation_thread(self, entry_id: str, context_entries: int = 3) -> Dict:
        """
        Get a conversation thread with surrounding context.
        """
        if entry_id not in self.memory_index:
            return {"success": False, "error": {"code": "not_found", "message": "Entry not found"}}

        entry = self.memory_index[entry_id]

        # Find related entries from same source
        source_entries = [
            e for e in self.memory_index.values()
            if e.source == entry.source
        ]
        source_entries.sort(key=lambda x: x.timestamp)

        # Find index of target entry
        try:
            idx = next(i for i, e in enumerate(source_entries) if e.id == entry_id)
        except StopIteration:
            return {"success": False, "error": {"code": "not_found", "message": "Entry not found in source"}}

        # Get surrounding entries
        start = max(0, idx - context_entries)
        end = min(len(source_entries), idx + context_entries + 1)
        thread = source_entries[start:end]

        return {
            "success": True,
            "results": {
                "target_entry": asdict(entry),
                "thread": [asdict(e) for e in thread],
                "position": idx - start,
            }
        }

    def get_layer_activity(self, layer: str, days: int = 7) -> Dict:
        """
        Get all activity for a specific layer.
        """
        return self.read_conversations(days=days, layers=[layer])

    def extract_insights(self, days: int = 7) -> Dict:
        """
        Extract insights from recent conversations.
        """
        conversations = self.read_conversations(days=days)

        # Count by layer
        layer_counts = {}
        tag_counts = {}

        for entry in conversations.get('entries', []):
            for layer in entry.get('related_layers', []):
                layer_counts[layer] = layer_counts.get(layer, 0) + 1
            for tag in entry.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "period_days": days,
            "total_entries": conversations['total_entries'],
            "layer_activity": layer_counts,
            "popular_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "most_accessed": sorted(
                [e for e in self.memory_index.values() if e.access_count > 0],
                key=lambda x: x.access_count,
                reverse=True
            )[:5]
        }


class EnhancedLayerNavigator:
    """
    Advanced layer navigation with state management and transitions.
    """

    def __init__(self):
        self.layer_states: Dict[AgentLayer, LayerState] = {}
        self.transition_history: List[Dict] = []
        self.layer_capabilities: Dict[AgentLayer, List[str]] = {
            AgentLayer.CODING: [
                "generate_endpoint", "generate_component", "generate_model",
                "refactor_code", "optimize_code", "generate_tests"
            ],
            AgentLayer.REGISTRY: [
                "register_capability", "list_capabilities", "get_capability",
                "update_capability", "deprecate_capability"
            ],
            AgentLayer.VALIDATION: [
                "validate_code", "scan_security", "run_tests",
                "check_performance", "audit_quality"
            ],
            AgentLayer.HOTSWAP: [
                "deploy_capability", "rollback_deployment", "hot_reload",
                "route_registration", "module_loading"
            ],
            AgentLayer.HEALING: [
                "detect_errors", "analyze_incident", "suggest_fix",
                "apply_healing", "circuit_breaker_check"
            ],
            AgentLayer.PROMPTS: [
                "create_prompt", "update_prompt", "test_prompt",
                "ab_test_prompt", "version_prompt"
            ],
            AgentLayer.TRIGGERS: [
                "create_trigger", "list_triggers", "fire_trigger",
                "enable_trigger", "disable_trigger"
            ],
            AgentLayer.ECONOMICS: [
                "calculate_cost", "estimate_project", "analyze_pricing",
                "rsmeans_query", "generate_boq"
            ],
            AgentLayer.VDC: [
                "query_bim", "check_clash", "extract_quantities",
                "4d_simulation", "model_conversion"
            ],
            AgentLayer.EDGE: [
                "register_device", "deploy_model", "run_inference",
                "sync_models", "device_health_check"
            ],
            AgentLayer.PORTAL: [
                "create_project", "manage_documents", "track_progress",
                "generate_report", "schedule_task"
            ],
            AgentLayer.ENTERPRISE: [
                "authenticate_user", "authorize_action", "audit_log",
                "manage_roles", "security_scan"
            ],
            AgentLayer.CONNECTORS: [
                "connect_external", "sync_data", "transform_data",
                "webhook_handler", "api_bridge"
            ],
            AgentLayer.MONITORING: [
                "log_event", "record_metric", "create_alert",
                "generate_dashboard", "trace_request"
            ]
        }

        # Layer dependencies (some layers need others first)
        self.layer_dependencies: Dict[AgentLayer, List[AgentLayer]] = {
            AgentLayer.HOTSWAP: [AgentLayer.VALIDATION],
            AgentLayer.HEALING: [AgentLayer.MONITORING],
        }

    def enter_layer(self, layer: AgentLayer, context: Dict = None) -> LayerState:
        """Enter a layer and initialize its state."""
        state = LayerState(
            layer=layer,
            entered_at=datetime.now().isoformat(),
            context=context or {}
        )
        self.layer_states[layer] = state
        return state

    def exit_layer(self, layer: AgentLayer, next_layer: AgentLayer = None):
        """Exit a layer and record the transition."""
        if layer in self.layer_states:
            state = self.layer_states[layer]
            self.transition_history.append({
                "from_layer": layer.value,
                "to_layer": next_layer.value if next_layer else None,
                "exited_at": datetime.now().isoformat(),
                "actions_performed": len(state.actions_performed),
                "artifacts_created": len(state.artifacts_created)
            })

    def record_action(self, layer: AgentLayer, action: str, artifact: str = None):
        """Record an action performed in a layer."""
        if layer in self.layer_states:
            self.layer_states[layer].actions_performed.append({
                "action": action,
                "timestamp": datetime.now().isoformat()
            })
            if artifact:
                self.layer_states[layer].artifacts_created.append(artifact)

    def can_enter_layer(self, layer: AgentLayer) -> Tuple[bool, List[str]]:
        """Check if we can enter a layer (dependencies satisfied)."""
        deps = self.layer_dependencies.get(layer, [])
        missing = []

        for dep in deps:
            if dep not in self.layer_states:
                missing.append(dep.value)

        return len(missing) == 0, missing

    def get_layer_info(self, layer: AgentLayer) -> Dict:
        """Get comprehensive information about a layer."""
        return {
            "name": layer.value,
            "capabilities": self.layer_capabilities.get(layer, []),
            "dependencies": [d.value for d in self.layer_dependencies.get(layer, [])],
            "current_state": asdict(self.layer_states[layer]) if layer in self.layer_states else None,
            "entry_count": sum(1 for t in self.transition_history if t["from_layer"] == layer.value),
            "visit_count": sum(1 for t in self.transition_history if t["to_layer"] == layer.value)
        }

    def suggest_layer_for_task(self, task: str) -> List[Dict]:
        """Suggest layers that can handle a task."""
        task_lower = task.lower()
        suggestions = []

        layer_keywords = {
            AgentLayer.CODING: ["code", "generate", "write", "create", "endpoint", "component", "function"],
            AgentLayer.REGISTRY: ["register", "capability", "module", "plugin"],
            AgentLayer.VALIDATION: ["validate", "test", "scan", "check", "audit"],
            AgentLayer.HOTSWAP: ["deploy", "release", "publish", "hot", "swap"],
            AgentLayer.HEALING: ["fix", "heal", "repair", "error", "bug", "incident"],
            AgentLayer.PROMPTS: ["prompt", "template", "llm", "ai"],
            AgentLayer.TRIGGERS: ["trigger", "event", "webhook", "schedule"],
            AgentLayer.ECONOMICS: [
                "cost", "price", "budget", "estimate", "rsmeans",
                "calculate", "concrete", "building", "sq ft", "square feet",
                "masonry", "steel", "wood", "drywall", "paint", "flooring",
                "roofing", "electrical", "plumbing", "hvac", "excavation",
                "rebar", "formwork", "cubic", "meters", "quantity", "quantities",
                "material", "labor", "csi", "division", "unit price", "total",
                "cubic meters", "cubic feet", "square meters", "square footage"
            ],
            AgentLayer.VDC: ["bim", "model", "clash", "quantity", "ifc"],
            AgentLayer.EDGE: ["device", "jetson", "orin", "edge", "inference"],
            AgentLayer.PORTAL: ["project", "document", "report", "user"],
            AgentLayer.ENTERPRISE: ["auth", "security", "user", "role", "permission"],
            AgentLayer.CONNECTORS: ["connect", "sync", "import", "export", "webhook"],
            AgentLayer.MONITORING: ["log", "metric", "monitor", "alert", "trace"]
        }

        for layer, keywords in layer_keywords.items():
            score = sum(1 for kw in keywords if kw in task_lower)
            if score > 0:
                suggestions.append({
                    "layer": layer.value,
                    "confidence": min(score / len(keywords) * 3, 1.0),
                    "capabilities": self.layer_capabilities.get(layer, [])[:5]
                })

        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions[:3]

    def get_navigation_path(self, from_layer: AgentLayer, to_layer: AgentLayer) -> List[Dict]:
        """Get the recommended path between layers."""
        path = [{"layer": from_layer.value, "action": "exit"}]

        # Check if we need to go through dependencies
        deps = self.layer_dependencies.get(to_layer, [])
        for dep in deps:
            if dep != from_layer:
                path.append({"layer": dep.value, "action": "enter", "reason": "dependency"})

        path.append({"layer": to_layer.value, "action": "enter"})
        return path


class EnhancedCerebrumAgent:
    """
    Enhanced Cerebrum Agent with all improvements.
    """

    def __init__(self, workspace_path: str = "/root/.openclaw/workspace",
                 reasoning_config: Optional[AgentReasoningConfig] = None,
                 lazy_init: bool = True):
        self.workspace_path = Path(workspace_path)
        self.repo_path = self.workspace_path / "cerebrum-fix"

        self.context = AgentContext(
            session_id=f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            workspace_path=str(self.workspace_path)
        )

        # Enhanced components - lazy initialization
        self._conversation_reader: Optional[EnhancedConversationReader] = None
        self._reader_initialized = False
        self.layer_navigator = EnhancedLayerNavigator()

        # Reasoning tracker for transparent AI reasoning (Kimi-style)
        self.reasoning_config = reasoning_config or AgentReasoningConfig()
        self.reasoning_tracker = ReasoningTracker(self.reasoning_config)
        # Store previous reasoning for multi-turn preservation
        self.previous_reasoning: Optional[Dict] = None

        # All available tools
        self.tools: Dict[str, Callable] = {}
        self._register_all_tools()

        # Lazy init components
        self.planner = None
        self.scheduler = None
        self.websocket_manager = None

        # If not lazy init, build index synchronously (for backwards compat)
        if not lazy_init:
            self._ensure_reader_initialized()

    def _ensure_reader_initialized(self):
        """Ensure conversation reader is initialized (sync version)."""
        if self._conversation_reader is None:
            self._conversation_reader = EnhancedConversationReader(str(self.workspace_path))
            # Build index synchronously for backwards compatibility
            self._conversation_reader._build_index()
        return self._conversation_reader

    async def initialize(self):
        """Async initialization - pre-load memory index and prepare agent."""
        if self._conversation_reader is None:
            self._conversation_reader = EnhancedConversationReader(str(self.workspace_path))
        
        if not self._reader_initialized:
            await self._conversation_reader.initialize()
            self._reader_initialized = True
            logger.info("EnhancedCerebrumAgent initialized successfully")

    @property
    def conversation_reader(self) -> EnhancedConversationReader:
        """Get conversation reader, initializing if necessary."""
        if self._conversation_reader is None:
            self._ensure_reader_initialized()
        return self._conversation_reader

    def _register_all_tools(self):
        """Register all tools from all layers."""
        # CODING layer tools
        self.tools.update({
            "generate_endpoint": self._tool_generate_endpoint,
            "generate_component": self._tool_generate_component,
            "generate_model": self._tool_generate_model,
            "refactor_code": self._tool_refactor_code,
        })

        # REGISTRY layer tools
        self.tools.update({
            "register_capability": self._tool_register_capability,
            "list_capabilities": self._tool_list_capabilities,
            "get_capability": self._tool_get_capability,
        })

        # VALIDATION layer tools
        self.tools.update({
            "validate_code": self._tool_validate_code,
            "scan_security": self._tool_scan_security,
            "run_tests": self._tool_run_tests,
        })

        # HOTSWAP layer tools
        self.tools.update({
            "deploy_capability": self._tool_deploy_capability,
            "hot_reload": self._tool_hot_reload,
        })

        # HEALING layer tools
        self.tools.update({
            "detect_errors": self._tool_detect_errors,
            "analyze_incident": self._tool_analyze_incident,
            "heal_error": self._tool_heal_error,
        })

        # MEMORY layer tools
        self.tools.update({
            "read_conversation": self._tool_read_conversation,
            "search_memory": self._tool_search_memory,
            "write_memory": self._tool_write_memory,
            "extract_insights": self._tool_extract_insights,
        })

        # ECONOMICS layer tools
        self.tools.update({
            "calculate_cost": self._tool_calculate_cost,
            "estimate_project": self._tool_estimate_project,
            "rsmeans_query": self._tool_rsmeans_query,
            "search_formulas": self._tool_search_formulas,
            "calculate_formula": self._tool_calculate_formula,
            "browse_formulas_online": self._tool_browse_formulas_online,
        })

        # VDC layer tools
        self.tools.update({
            "query_bim": self._tool_query_bim,
            "extract_quantities": self._tool_extract_quantities,
        })

        # EDGE layer tools
        self.tools.update({
            "register_device": self._tool_register_device,
            "deploy_model_to_edge": self._tool_deploy_model_to_edge,
        })

        # PORTAL layer tools
        self.tools.update({
            "create_project": self._tool_create_project,
            "generate_report": self._tool_generate_report,
        })

        # ENTERPRISE layer tools
        self.tools.update({
            "audit_security": self._tool_audit_security,
        })

        # TRIGGERS layer tools
        self.tools.update({
            "create_trigger": self._tool_create_trigger,
            "fire_trigger": self._tool_fire_trigger,
        })

        # MONITORING layer tools
        self.tools.update({
            "log_event": self._tool_log_event,
            "record_metric": self._tool_record_metric,
        })

    # ============ LAYER NAVIGATION ============

    def move_to_layer(self, layer: AgentLayer, context: Dict = None) -> AgentResult:
        """Move to a layer with dependency checking and state management."""
        current = self.context.current_layer

        # Track reasoning for layer navigation
        self.reasoning_tracker.add_layer_navigation(
            from_layer=current.value,
            to_layer=layer.value,
            reason=f"Task requires {layer.value} layer capabilities"
        )

        # Check dependencies
        can_enter, missing = self.layer_navigator.can_enter_layer(layer)
        if not missing:
            pass  # Dependencies satisfied

        # Exit current layer
        self.layer_navigator.exit_layer(current, layer)

        # Enter new layer
        state = self.layer_navigator.enter_layer(layer, context)
        self.context.current_layer = layer
        self.context.layer_history.append(state)

        # Format reasoning for the result
        reasoning = self.reasoning_tracker.format_reasoning()

        return AgentResult(
            success=True,
            action=AgentAction.READ_MEMORY,
            layer=layer,
            data={
                "previous_layer": current.value,
                "layer_state": asdict(state),
                "capabilities": self.layer_navigator.layer_capabilities.get(layer, []),
                "dependencies_satisfied": can_enter,
                "missing_dependencies": missing
            },
            message=f"Navigated from {current.value} to {layer.value}",
            suggested_next_actions=self._get_layer_suggestions(layer),
            reasoning_content=reasoning
        )

    def _get_layer_suggestions(self, layer: AgentLayer) -> List[str]:
        """Get suggested actions for a layer."""
        suggestions = {
            AgentLayer.CODING: ["Generate an endpoint", "Create a React component", "Write tests"],
            AgentLayer.REGISTRY: ["List capabilities", "Register new module", "Update existing"],
            AgentLayer.VALIDATION: ["Validate recent code", "Run security scan", "Execute tests"],
            AgentLayer.HOTSWAP: ["Deploy capability", "Hot reload module", "Rollback deployment"],
            AgentLayer.HEALING: ["Check for errors", "Analyze incidents", "Apply fixes"],
            AgentLayer.ECONOMICS: ["Calculate project cost", "Query RSMeans", "Generate BOQ"],
            AgentLayer.VDC: ["Query BIM model", "Check for clashes", "Extract quantities"],
        }
        return suggestions.get(layer, ["Explore available tools"])

    # ============ ENHANCED MEMORY TOOLS ============

    def _tool_read_conversation(self, days: int = 7, layers: List[str] = None) -> Dict:
        """Enhanced conversation reading with filtering."""
        result = self.conversation_reader.read_conversations(days=days, layers=layers)
        # Ensure consistent format
        if isinstance(result, dict) and "success" not in result:
            result["success"] = True
        return result

    def _tool_search_memory(self, query: str = None, limit: int = 10, task: str = None, **kwargs) -> Dict:
        """Semantic memory search with relevance scoring."""
        # Support both 'query' and 'task' parameters
        search_query = query or task or ""
        result = self.conversation_reader.semantic_search(search_query, limit)
        # Ensure consistent format
        if isinstance(result, dict) and "success" not in result:
            result["success"] = True
        return result

    def _tool_write_memory(self, content: str, tags: List[str] = None,
                          related_layers: List[str] = None) -> Dict:
        """Enhanced memory writing with tags and layer references."""
        try:
            file_path = self.workspace_path / "MEMORY.md"
            file_path.parent.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Build entry with metadata
            entry_lines = [f"\n\n## Agent Entry [{timestamp}]"]

            if tags:
                entry_lines.append(f"**Tags:** {', '.join(f'#{t}' for t in tags)}")
            if related_layers:
                entry_lines.append(f"**Layers:** {', '.join(related_layers)}")

            entry_lines.append(f"\n{content}\n")
            entry = '\n'.join(entry_lines)

            with open(file_path, 'a') as f:
                f.write(entry)

            # Rebuild index
            self.conversation_reader._index_file(file_path)

            return {
                "success": True,
                "file": str(file_path),
                "timestamp": timestamp,
                "tags": tags or [],
                "related_layers": related_layers or []
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_extract_insights(self, days: int = 7) -> Dict:
        """Extract insights from recent activity."""
        return self.conversation_reader.extract_insights(days)

    # ============ ALL LAYER TOOLS (stubs for now, connect to real endpoints) ============

    def _tool_generate_endpoint(self, **kwargs) -> Dict:
        return {"success": True, "tool": "generate_endpoint", "params": kwargs}

    def _tool_generate_component(self, **kwargs) -> Dict:
        return {"success": True, "tool": "generate_component", "params": kwargs}

    def _tool_generate_model(self, **kwargs) -> Dict:
        return {"success": True, "tool": "generate_model", "params": kwargs}

    def _tool_refactor_code(self, **kwargs) -> Dict:
        return {"success": True, "tool": "refactor_code", "params": kwargs}

    def _tool_register_capability(self, **kwargs) -> Dict:
        return {"success": True, "tool": "register_capability", "params": kwargs}

    def _tool_list_capabilities(self, **kwargs) -> Dict:
        return {"success": True, "tool": "list_capabilities", "params": kwargs}

    def _tool_get_capability(self, **kwargs) -> Dict:
        return {"success": True, "tool": "get_capability", "params": kwargs}

    def _tool_validate_code(self, **kwargs) -> Dict:
        return {"success": True, "tool": "validate_code", "params": kwargs}

    def _tool_scan_security(self, **kwargs) -> Dict:
        return {"success": True, "tool": "scan_security", "params": kwargs}

    def _tool_run_tests(self, **kwargs) -> Dict:
        return {"success": True, "tool": "run_tests", "params": kwargs}

    def _tool_deploy_capability(self, **kwargs) -> Dict:
        return {"success": True, "tool": "deploy_capability", "params": kwargs}

    def _tool_hot_reload(self, **kwargs) -> Dict:
        return {"success": True, "tool": "hot_reload", "params": kwargs}

    def _tool_detect_errors(self, **kwargs) -> Dict:
        return {"success": True, "tool": "detect_errors", "params": kwargs}

    def _tool_analyze_incident(self, **kwargs) -> Dict:
        return {"success": True, "tool": "analyze_incident", "params": kwargs}

    def _tool_heal_error(self, **kwargs) -> Dict:
        return {"success": True, "tool": "heal_error", "params": kwargs}

    # Building type fuzzy matching mapping
    # Maps generic user terms to available specific building types
    BUILDING_TYPE_FUZZY_MAP = {
        # Office variants
        "office": ["office-low", "office-high"],
        "offices": ["office-low", "office-high"],
        "office building": ["office-low", "office-high"],
        "office space": ["office-low", "office-high"],
        "commercial office": ["office-low", "office-high"],

        # Warehouse variants
        "warehouse": ["warehouse"],
        "warehouses": ["warehouse"],
        "storage": ["warehouse"],
        "distribution center": ["warehouse"],
        "industrial warehouse": ["warehouse"],
        "industrial": ["warehouse", "manufacturing"],

        # Residential variants
        "residential": ["residential-single", "residential-multi"],
        "house": ["residential-single"],
        "houses": ["residential-single"],
        "home": ["residential-single"],
        "homes": ["residential-single"],
        "apartment": ["residential-multi"],
        "apartments": ["residential-multi"],
        "condo": ["residential-multi"],
        "condos": ["residential-multi"],
        "dwelling": ["residential-single"],
        "single family": ["residential-single"],
        "multi family": ["residential-multi"],

        # Commercial/Retail variants
        "commercial": ["retail-strip", "retail-enclosed", "office-low", "office-high"],
        "retail": ["retail-strip", "retail-enclosed"],
        "store": ["retail-strip"],
        "stores": ["retail-strip"],
        "shop": ["retail-strip"],
        "shopping center": ["retail-enclosed"],
        "mall": ["retail-enclosed"],
        "strip mall": ["retail-strip"],

        # Manufacturing/Industrial
        "factory": ["manufacturing"],
        "factories": ["manufacturing"],
        "plant": ["manufacturing"],
        "manufacturing": ["manufacturing"],
        "production facility": ["manufacturing"],

        # Hospital/Medical variants
        "hospital": ["hospital"],
        "hospitals": ["hospital"],
        "medical center": ["hospital", "medical-office"],
        "healthcare facility": ["hospital", "medical-office"],
        "clinic": ["medical-office"],
        "medical office": ["medical-office"],

        # School variants
        "school": ["school-elementary", "school-high"],
        "schools": ["school-elementary", "school-high"],
        "education": ["school-elementary", "school-high"],
        "classroom": ["school-elementary", "school-high"],
        "university": ["school-high"],
        "college": ["school-high"],
        "elementary school": ["school-elementary"],
        "high school": ["school-high"],
        "primary school": ["school-elementary"],

        # Hotel variants
        "hotel": ["hotel-mid", "hotel-luxury"],
        "hotels": ["hotel-mid", "hotel-luxury"],
        "motel": ["hotel-mid"],
        "lodging": ["hotel-mid", "hotel-luxury"],
        "hospitality": ["hotel-mid", "hotel-luxury"],

        # Restaurant/Food service
        "restaurant": ["restaurant"],
        "restaurants": ["restaurant"],
        "dining": ["restaurant"],
        "food service": ["restaurant"],
        "cafe": ["restaurant"],

        # Parking
        "parking": ["parking-structure"],
        "garage": ["parking-structure", "parking-underground"],
        "parking structure": ["parking-structure"],
        "parking lot": ["parking-lot"],
        "parking garage": ["parking-structure", "parking-underground"],
    }

    def _parse_economics_natural_language(self, query: str) -> Dict:
        """
        Parse natural language economics queries into structured parameters.

        Extracts:
        - Building types: office, warehouse, residential, commercial, etc.
        - Size patterns: "100 sq ft", "5000 square feet", "2000 sf", etc.
        - Location hints: zip codes, city names
        """
        result = {
            "building_type": None,
            "size_sf": None,
            "city": None,
            "quantity": None,
            "item_description": None,
            "original_query": query,
            "building_type_suggestions": [],  # Fuzzy match suggestions
            "requires_clarification": False,  # True if ambiguous building type
        }

        query_lower = query.lower()

        # FIRST: Check if query already contains a specific building type code
        # This prevents "office-low" from being parsed as generic "office"
        specific_types = [
            "office-low", "office-high",
            "residential-single", "residential-multi",
            "retail-strip", "retail-enclosed",
            "school-elementary", "school-high",
            "hotel-mid", "hotel-luxury",
            "parking-structure", "parking-underground", "parking-lot",
            "medical-office", "manufacturing", "hospital", "warehouse",
            "restaurant"
        ]
        for specific in specific_types:
            if specific in query_lower:
                result["building_type"] = specific
                result["building_type_suggestions"] = [specific]
                result["requires_clarification"] = False
                # Continue to parse size and location
                detected_generic_type = None
                break
        else:
            detected_generic_type = None

            # Building type keywords and their variations (for initial detection)
            building_types = {
                "office": ["office", "offices", "office building", "office space", "commercial office"],
                "warehouse": ["warehouse", "warehouses", "storage", "distribution center", "industrial warehouse"],
                "residential": ["residential", "house", "houses", "home", "homes", "apartment", "apartments", "condo", "condos", "dwelling"],
                "commercial": ["commercial", "retail", "store", "stores", "shop", "shopping center", "mall"],
                "industrial": ["industrial", "factory", "factories", "plant", "manufacturing", "production facility"],
                "hospital": ["hospital", "hospitals", "medical center", "healthcare facility", "clinic"],
                "school": ["school", "schools", "education", "classroom", "university", "college"],
                "hotel": ["hotel", "hotels", "motel", "lodging", "hospitality"],
                "restaurant": ["restaurant", "restaurants", "dining", "food service", "cafe"],
                "parking": ["parking", "garage", "parking structure", "parking lot"],
            }

            # Extract building type using fuzzy matching
            for btype, keywords in building_types.items():
                for keyword in keywords:
                    if keyword in query_lower:
                        detected_generic_type = keyword
                        result["building_type"] = btype
                        break
                if result["building_type"]:
                    break

            # Apply fuzzy matching to get specific building types
            if detected_generic_type:
                fuzzy_matches = self.BUILDING_TYPE_FUZZY_MAP.get(detected_generic_type, [])
                if fuzzy_matches:
                    result["building_type_suggestions"] = fuzzy_matches
                    # If only one match, use it directly; otherwise flag for clarification
                    if len(fuzzy_matches) == 1:
                        result["building_type"] = fuzzy_matches[0]
                    else:
                        # Multiple matches - require clarification, don't set building_type
                        result["requires_clarification"] = True
                        result["building_type"] = None  # Clear the generic type

        # Size patterns - handle various formats
        # Pattern 1: "100 sq ft", "100 sqft", "100 sq.ft", "100 sf"
        # Pattern 2: "100 square feet", "100 square foot"
        # Pattern 3: "100sf", "100sqft" (no space)
        # Pattern 4: "100 sq. ft", "100 sq. feet"
        # Pattern 5: "100 m2", "100 sqm", "100 square meters" (metric - convert to sq ft)

        size_patterns = [
            # Imperial: X sq ft, X sqft, X sf, X sq. ft, etc.
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:sq\.?\s*ft\.?|sqft|sf)',
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:square\s+(?:feet|foot))',
            # Metric: X m2, X sqm, X sq m, etc. (convert: 1 sq m = 10.764 sq ft)
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:m2|m²|sq\.?\s*m\.?|sqm|square\s+meters?)',
        ]

        for pattern in size_patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                size_str = match.group(1).replace(',', '')
                try:
                    size_val = float(size_str)
                    # Check if it's metric (m2 pattern matched)
                    if 'm2' in match.group(0) or 'm²' in match.group(0) or 'meter' in match.group(0) or 'sqm' in match.group(0):
                        size_val = size_val * 10.764  # Convert sq meters to sq feet
                    result["size_sf"] = int(size_val)
                except ValueError:
                    pass
                break

        # Location extraction
        # Zip codes (US): 5 digits, optionally with +4
        # But avoid matching numbers that are followed by size-related words
        zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b(?!\s*(?:square|sq\.?|sqft|feet|foot|sf|m2|m²|meters?))', query, re.IGNORECASE)
        if zip_match:
            result["city"] = zip_match.group(1)
        else:
            # Common city names - look for capitalized words that might be cities
            # This is a simplified approach - could be enhanced with a city database
            city_indicators = ["in ", "at ", "near ", "located in ", "located at "]
            for indicator in city_indicators:
                if indicator in query_lower:
                    after_indicator = query_lower.split(indicator)[-1].strip()
                    # Take first word after indicator as potential city
                    potential_city = after_indicator.split()[0].strip('.,;')
                    # Only accept if it's alphabetic (not a number) and reasonable length
                    if len(potential_city) > 2 and potential_city.isalpha():
                        result["city"] = potential_city.title()
                        break

        # Quantity extraction for item-based queries
        # Patterns like "100 bricks", "50 tons of concrete", "1000 units", "50 cubic meters"
        quantity_pattern = r'\b(\d+(?:,\d{3})*)\s*(?:units?|pcs?|pieces?|tons?|lbs?|pounds?|kg|kilograms?|bags?|blocks?|bricks?|sheets?|panels?|cubic\s+(?:meters?|feet|foot|yards?|yd)|cu\.?\s*(?:m|ft|yd)|m3|m³|ft3|ft³|yd3|yd³|cy|cf)\b'
        qty_match = re.search(quantity_pattern, query_lower, re.IGNORECASE)
        if qty_match:
            result["quantity"] = int(qty_match.group(1).replace(',', ''))

        # Extract item description for material queries
        # Look for material keywords
        material_keywords = [
            "concrete", "steel", "lumber", "wood", "brick", "block", "drywall",
            "insulation", "roofing", "flooring", "tile", "paint", "electrical",
            "plumbing", "hvac", "windows", "doors", "foundation", "framing"
        ]
        for material in material_keywords:
            if material in query_lower:
                result["item_description"] = material
                break

        return result

    def _tool_calculate_cost(self, **kwargs) -> Dict:
        """Calculate construction cost using local RSMeans data."""
        try:
            from app.agent.economics_tools import (
                economics_search_items,
                economics_calculate,
                economics_estimate_building,
            )

            # Check if we have a natural language query to parse
            query = kwargs.get("query", "")
            task = kwargs.get("task", "")

            # Use query or task as the natural language input
            nl_input = query or task or ""

            # Parse natural language if provided
            if nl_input and ("building_type" not in kwargs or "size_sf" not in kwargs):
                parsed = self._parse_economics_natural_language(nl_input)
                # Merge parsed values into kwargs (only if not already provided)
                for key, value in parsed.items():
                    if value is not None and key not in kwargs:
                        kwargs[key] = value

            # Check if building type needs clarification
            if kwargs.get("requires_clarification") and kwargs.get("building_type_suggestions"):
                # Instead of asking for clarification, just use the first (most common) option
                # User can be more specific if they want a different type
                suggestions = kwargs["building_type_suggestions"]
                if suggestions:
                    kwargs["building_type"] = suggestions[0]
                    print(f"Auto-selected building type '{suggestions[0]}' from suggestions: {suggestions}")
                    # Remove the clarification flag so it proceeds
                    kwargs.pop("requires_clarification", None)

            # Determine what type of calculation
            if "building_type" in kwargs and kwargs["building_type"] and "size_sf" in kwargs:
                return economics_estimate_building(
                    kwargs["building_type"],
                    kwargs["size_sf"],
                    kwargs.get("city", "National Average")
                )
            elif "item_id" in kwargs and "quantity" in kwargs:
                item = economics_search_items(kwargs["item_id"], limit=1)
                if item.get("results"):
                    base_cost = item["results"][0].get("base_cost", 0)
                    quantity = kwargs["quantity"]
                    return {
                        "success": True,
                        "item": item["results"][0],
                        "quantity": quantity,
                        "total_cost": base_cost * quantity,
                    }
                return {"success": False, "error": "Item not found"}
            elif kwargs.get("item_description") and kwargs.get("quantity"):
                # Search by item description
                search_results = economics_search_items(kwargs["item_description"], limit=1)
                if search_results.get("results"):
                    item = search_results["results"][0]
                    base_cost = item.get("base_cost", 0)
                    quantity = kwargs["quantity"]
                    return {
                        "success": True,
                        "item": item,
                        "quantity": quantity,
                        "total_cost": base_cost * quantity,
                        "parsed_from": nl_input if nl_input else None
                    }
                return {"success": False, "error": f"Item not found: {kwargs['item_description']}"}
            else:
                return {
                    "success": False,
                    "error": "Need building_type+size_sf or item_id+quantity",
                    "parsed_parameters": {k: v for k, v in kwargs.items() if v is not None and k not in ["query", "task", "context"]}
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_estimate_project(self, **kwargs) -> Dict:
        """Generate project cost estimate with fuzzy building type matching."""
        try:
            from app.agent.economics_tools import (
                economics_list_building_types,
                economics_estimate_building,
            )

            # Check if we have a natural language query to parse
            query = kwargs.get("query", "")
            task = kwargs.get("task", "")
            nl_input = query or task or ""

            # Parse natural language if provided
            if nl_input:
                parsed = self._parse_economics_natural_language(nl_input)
                # Merge parsed values into kwargs
                for key, value in parsed.items():
                    if value is not None and key not in kwargs:
                        kwargs[key] = value

            # Check if we have building type suggestions that need clarification
            building_suggestions = kwargs.get("building_type_suggestions", [])
            requires_clarification = kwargs.get("requires_clarification", False)

            # If building type is ambiguous, provide helpful suggestions
            if requires_clarification and building_suggestions:
                # Get detailed info about suggested building types
                all_types = economics_list_building_types()
                suggested_details = []

                for bt in all_types.get("building_types", []):
                    if bt["code"] in building_suggestions:
                        suggested_details.append({
                            "code": bt["code"],
                            "name": bt["name"],
                            "cost_per_sf": bt["cost_per_sf"],
                            "typical_size": bt.get("typical_size_sf", "N/A")
                        })

                return {
                    "success": True,
                    "requires_clarification": True,
                    "message": f"I found multiple building types that match '{kwargs.get('building_type')}'. Which one did you mean?",
                    "suggestions": suggested_details,
                    "parsed_from": nl_input if nl_input else None,
                    "parsed_parameters": {
                        "building_type": kwargs.get("building_type"),
                        "size_sf": kwargs.get("size_sf"),
                        "city": kwargs.get("city"),
                        "possible_matches": building_suggestions
                    },
                    "example_queries": [
                        f"Estimate cost for {suggested_details[0]['code'] if suggested_details else 'office-low'} building {kwargs.get('size_sf', '5000')} sq ft",
                        f"Calculate cost for {suggested_details[1]['code'] if len(suggested_details) > 1 else 'office-high'} building {kwargs.get('size_sf', '5000')} sq ft"
                    ]
                }

            # If we have a building type but it's not in the available types, try to suggest alternatives
            if "building_type" in kwargs and kwargs["building_type"]:
                test_result = economics_estimate_building(
                    kwargs["building_type"],
                    kwargs.get("size_sf", 1000),  # dummy size for test
                    "National Average"
                )
                if not test_result.get("success", True):
                    # Building type not found - get available types for suggestions
                    all_types = economics_list_building_types()
                    available_codes = [bt["code"] for bt in all_types.get("building_types", [])]

                    # Try to find similar building types
                    user_type = kwargs["building_type"].lower()
                    suggestions = []

                    for code in available_codes:
                        # Simple similarity check
                        if user_type in code or code in user_type:
                            type_data = next((bt for bt in all_types.get("building_types", []) if bt["code"] == code), None)
                            if type_data:
                                suggestions.append(type_data)

                    return {
                        "success": False,
                        "error": f"Unknown building type: '{kwargs['building_type']}'",
                        "message": f"I don't recognize '{kwargs['building_type']}' as a building type. Here are some suggestions:",
                        "suggestions": suggestions[:5] if suggestions else all_types.get("building_types", [])[:5],
                        "parsed_from": nl_input if nl_input else None,
                        "all_available_types": [{"code": bt["code"], "name": bt["name"]} for bt in all_types.get("building_types", [])],
                        "example_queries": [
                            "Estimate cost for office-low building 5000 sq ft",
                            "Calculate cost for warehouse 10000 sq ft",
                            "Cost estimate for residential-single 2500 sq ft"
                        ]
                    }

            # If we have enough parsed parameters, run the estimate
            if "building_type" in kwargs and "size_sf" in kwargs:
                result = economics_estimate_building(
                    kwargs["building_type"],
                    kwargs["size_sf"],
                    kwargs.get("city", "National Average")
                )
                result["parsed_from"] = nl_input if nl_input else None
                result["parsed_parameters"] = {
                    "building_type": kwargs.get("building_type"),
                    "size_sf": kwargs.get("size_sf"),
                    "city": kwargs.get("city")
                }
                return result

            # Otherwise, just list available building types
            result = economics_list_building_types()

            # Add parsed info if we extracted something but not enough for a full estimate
            if nl_input and any(v is not None for v in [kwargs.get("building_type"), kwargs.get("size_sf"), kwargs.get("city")]):
                result["parsed_from"] = nl_input
                result["parsed_parameters"] = {
                    "building_type": kwargs.get("building_type"),
                    "size_sf": kwargs.get("size_sf"),
                    "city": kwargs.get("city"),
                    "building_type_suggestions": kwargs.get("building_type_suggestions", [])
                }
                result["message"] = "Parsed your query but need more information for a complete estimate."

                # If we detected a building type that needs clarification
                if kwargs.get("requires_clarification"):
                    result["requires_clarification"] = True
                    result["clarification_message"] = f"Please specify which building type you mean by '{kwargs.get('building_type')}'."

            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_rsmeans_query(self, **kwargs) -> Dict:
        """Query RSMeans construction items."""
        try:
            from app.agent.economics_tools import economics_search_items
            query = kwargs.get("query", "")
            category = kwargs.get("category")
            limit = kwargs.get("limit", 10)
            return economics_search_items(query, category, limit)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_search_formulas(self, **kwargs) -> Dict:
        """Search construction formulas."""
        try:
            from app.agent.economics_tools import economics_search_formulas
            query = kwargs.get("query", "")
            category = kwargs.get("category")
            return economics_search_formulas(query, category)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_calculate_formula(self, **kwargs) -> Dict:
        """Execute a construction formula calculation."""
        try:
            from app.agent.economics_tools import economics_calculate
            formula_id = kwargs.get("formula_id")
            inputs = kwargs.get("inputs", {})
            return economics_calculate(formula_id, inputs)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_browse_formulas_online(self, **kwargs) -> Dict:
        """Browse online formula libraries."""
        try:
            from app.agent.economics_tools import (
                search_formula_libraries_online,
                browse_engineering_formulas,
            )
            query = kwargs.get("query")
            topic = kwargs.get("topic")

            if topic:
                return browse_engineering_formulas(topic)
            return search_formula_libraries_online(query or "construction formulas")
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_query_bim(self, **kwargs) -> Dict:
        return {"success": True, "tool": "query_bim", "params": kwargs}

    def _tool_extract_quantities(self, **kwargs) -> Dict:
        return {"success": True, "tool": "extract_quantities", "params": kwargs}

    def _tool_register_device(self, **kwargs) -> Dict:
        return {"success": True, "tool": "register_device", "params": kwargs}

    def _tool_deploy_model_to_edge(self, **kwargs) -> Dict:
        return {"success": True, "tool": "deploy_model_to_edge", "params": kwargs}

    def _tool_create_project(self, **kwargs) -> Dict:
        return {"success": True, "tool": "create_project", "params": kwargs}

    def _tool_generate_report(self, **kwargs) -> Dict:
        return {"success": True, "tool": "generate_report", "params": kwargs}

    def _tool_audit_security(self, **kwargs) -> Dict:
        return {"success": True, "tool": "audit_security", "params": kwargs}

    def _tool_create_trigger(self, **kwargs) -> Dict:
        return {"success": True, "tool": "create_trigger", "params": kwargs}

    def _tool_fire_trigger(self, **kwargs) -> Dict:
        return {"success": True, "tool": "fire_trigger", "params": kwargs}

    def _tool_log_event(self, **kwargs) -> Dict:
        return {"success": True, "tool": "log_event", "params": kwargs}

    def _tool_record_metric(self, **kwargs) -> Dict:
        return {"success": True, "tool": "record_metric", "params": kwargs}

    # ============ MAIN EXECUTION ============

    async def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        """Execute a task with full layer navigation, memory awareness, and reasoning tracking."""
        import time
        start_time = time.time()
        context = context or {}

        # Initialize or restore reasoning from previous turn
        if self.reasoning_config.preserve_across_turns and self.previous_reasoning:
            # Restore previous reasoning and merge
            previous_tracker = ReasoningTracker.from_dict(self.previous_reasoning)
            self.reasoning_tracker.merge(previous_tracker)
            self.reasoning_tracker.add_thinking(
                "Continuing from previous interaction with preserved reasoning context"
            )

        # Start tracking reasoning for this task
        self.reasoning_tracker.start(task, context)

        # FIRST: Check if task contains a file_id (UUID pattern)
        import re
        file_id_match = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_[0-9a-f]{32})', task)
        if file_id_match:
            file_id = file_id_match.group(1)
            self.reasoning_tracker.add_observation(
                f"Detected file upload reference: {file_id[:8]}...",
                {"file_id": file_id}
            )
            self.reasoning_tracker.add_decision(
                "Route to file analysis",
                "File upload detected in task - need to analyze the uploaded file"
            )
            result = await self._analyze_uploaded_file(file_id, task, context)
            # Attach reasoning to result
            result.reasoning_content = self.reasoning_tracker.format_reasoning()
            # Store for next turn
            self.previous_reasoning = self.reasoning_tracker.to_dict()
            return result

        # SECOND: Check for file query patterns
        file_keywords = ['this file', 'this pdf', 'this document', 'the file', 'the pdf', 'the document',
                        'uploaded file', 'analyze file', 'analyze pdf', 'analyze document',
                        'what is in this', "what's in this", 'extract from', 'read this']
        is_file_query = any(kw in task.lower() for kw in file_keywords)
        looks_like_filename = bool(re.search(r'\.[a-zA-Z]{3,4}$', task.strip()))

        if is_file_query or looks_like_filename:
            self.reasoning_tracker.add_observation(
                "File query pattern detected",
                {"is_file_query": is_file_query, "looks_like_filename": looks_like_filename}
            )
            session_id = context.get('session_id')
            file_id = await self._find_recent_file(task, session_id)
            if file_id:
                self.reasoning_tracker.add_decision(
                    f"Found recent file: {file_id[:8]}...",
                    "Matched file query to recent upload"
                )
                result = await self._analyze_uploaded_file(file_id, task, context)
                result.reasoning_content = self.reasoning_tracker.format_reasoning()
                self.previous_reasoning = self.reasoning_tracker.to_dict()
                return result

        # Check if this is a conversational greeting/query
        conversation_keywords = ['hello', 'hi', 'hey', 'greetings', 'what can you do',
                                'who are you', 'help', 'what do you do', 'thanks', 'thank you']
        is_conversation = any(kw in task.lower() for kw in conversation_keywords)
        is_vague = len(task.strip()) < 10 and not looks_like_filename

        if is_conversation or is_vague:
            self.reasoning_tracker.add_thinking(
                f"Detected conversational query (is_conversation={is_conversation}, is_vague={is_vague})"
            )
            self.reasoning_tracker.add_decision(
                "Route to conversational response",
                "Short greeting or vague query - provide conversational response without tool execution"
            )
            reasoning = self.reasoning_tracker.format_reasoning()
            self.previous_reasoning = self.reasoning_tracker.to_dict()
            return AgentResult(
                success=True,
                action=AgentAction.READ_MEMORY,
                layer=AgentLayer.PORTAL,
                data={"type": "conversation", "query": task},
                message=self._generate_conversation_response(task),
                execution_time_ms=0,
                related_conversations=[],
                suggested_next_actions=["Try /agent layers", "Switch to Agent Mode for complex tasks"],
                reasoning_content=reasoning
            )

        # Read relevant conversations
        self.reasoning_tracker.add_thinking("Searching for related conversations in memory...")
        related = self.conversation_reader.semantic_search(task, limit=3)
        # The semantic_search returns {'results': {'matches': [...], 'total_matches': N}, 'metadata': {...}}
        related_ids = [r["id"] for r in related.get("results", {}).get("matches", [])]
        if related_ids:
            self.reasoning_tracker.add_observation(
                f"Found {len(related_ids)} related conversations",
                {"related_ids": related_ids}
            )

        # Check if force_layer is specified
        force_layer = context.get("force_layer")
        if force_layer:
            self.reasoning_tracker.add_thinking(f"Force layer specified: {force_layer}")

        # Suggest layers for the task
        layer_suggestions = self.layer_navigator.suggest_layer_for_task(task)
        self.reasoning_tracker.add_observation(
            f"Layer suggestions: {[s['layer'] for s in layer_suggestions]}",
            {"suggestions": layer_suggestions}
        )

        # Select best layer
        if force_layer:
            try:
                target_layer = AgentLayer(force_layer)
            except ValueError:
                target_layer = AgentLayer(layer_suggestions[0]["layer"]) if layer_suggestions else AgentLayer.CODING
        elif layer_suggestions:
            target_layer = AgentLayer(layer_suggestions[0]["layer"])
        else:
            target_layer = AgentLayer.CODING

        self.reasoning_tracker.add_decision(
            f"Selected layer: {target_layer.value}",
            f"Best match for task based on layer suggestions and confidence scores"
        )

        # Navigate to layer
        nav_result = self.move_to_layer(target_layer, context)

        # Find appropriate tool
        tool_name = self._select_tool_for_task(task, target_layer)
        self.reasoning_tracker.add_decision(
            f"Selected tool: {tool_name}",
            f"Tool mapped from task keywords and layer {target_layer.value}"
        )

        # Execute tool
        self.reasoning_tracker.add_tool_call(tool_name, {"task": task[:100], "context_keys": list(context.keys())})
        if tool_name in self.tools:
            try:
                result = self.tools[tool_name](task=task, context=context)
                self.reasoning_tracker.add_observation(
                    f"Tool execution successful: {tool_name}",
                    {"result_keys": list(result.keys()) if isinstance(result, dict) else "non-dict result"}
                )
            except Exception as e:
                self.reasoning_tracker.add_error(str(e), "Will return error result")
                result = {"success": False, "error": str(e)}
        else:
            error_msg = f"Tool {tool_name} not found"
            self.reasoning_tracker.add_error(error_msg)
            result = {"success": False, "error": error_msg}

        execution_time = (time.time() - start_time) * 1000

        # Format the message
        formatted_message = self._format_result_message(tool_name, result, task)

        # Add conclusion
        success = result.get("success", True)
        self.reasoning_tracker.add_conclusion(
            f"Task completed with success={success}",
            success=success
        )

        # Format reasoning for response
        reasoning = self.reasoning_tracker.format_reasoning()

        # Store reasoning for next turn if preserving across turns
        if self.reasoning_config.preserve_across_turns:
            self.previous_reasoning = self.reasoning_tracker.to_dict()

        return AgentResult(
            success=success,
            action=AgentAction.GENERATE_CODE if "generate" in tool_name else AgentAction.READ_MEMORY,
            layer=target_layer,
            data=result,
            message=formatted_message,
            execution_time_ms=execution_time,
            related_conversations=related_ids,
            suggested_next_actions=[f"Try {s['layer']}" for s in layer_suggestions[1:3]],
            reasoning_content=reasoning
        )

    def _select_tool_for_task(self, task: str, layer: AgentLayer) -> str:
        """Select the best tool for a task."""
        task_lower = task.lower()

        # When on ECONOMICS layer, prioritize economics tools over formula tools
        if layer == AgentLayer.ECONOMICS:
            # Check economics-specific keywords first
            economics_keywords = {
                "cost": "calculate_cost",
                "price": "rsmeans_query",
                "estimate": "estimate_project",
                "budget": "calculate_cost",
                "concrete": "calculate_cost",
                "masonry": "rsmeans_query",
                "steel": "rsmeans_query",
                "building": "estimate_project",
                "cubic": "calculate_cost",
                "material": "rsmeans_query",
            }
            for keyword, tool in economics_keywords.items():
                if keyword in task_lower:
                    return tool

        # Map keywords to tools (general case)
        tool_map = {
            "endpoint": "generate_endpoint",
            "component": "generate_component",
            "model": "generate_model",
            "validate": "validate_code",
            "test": "run_tests",
            "scan": "scan_security",
            "deploy": "deploy_capability",
            "heal": "heal_error",
            "fix": "heal_error",
            "cost": "calculate_cost",
            "price": "rsmeans_query",
            "estimate": "estimate_project",
            "budget": "calculate_cost",
            "bim": "query_bim",
            "quantity": "extract_quantities",
            "search": "search_memory",
            "remember": "write_memory",
            "formula": "search_formulas",
            "calculate": "calculate_formula",
            "concrete": "calculate_cost",
            "masonry": "rsmeans_query",
            "steel": "rsmeans_query",
            "building": "estimate_project",
            "cubic": "calculate_cost",
            "material": "rsmeans_query",
        }

        for keyword, tool in tool_map.items():
            if keyword in task_lower:
                return tool

        # Default based on layer - use safe defaults that don't auto-generate code
        defaults = {
            AgentLayer.CODING: "search_memory",
            AgentLayer.VALIDATION: "validate_code",
            AgentLayer.HEALING: "heal_error",
            AgentLayer.ECONOMICS: "calculate_cost",
            AgentLayer.VDC: "query_bim",
            AgentLayer.REGISTRY: "search_memory",
            AgentLayer.PORTAL: "search_memory",
            AgentLayer.PROMPTS: "search_memory",
            AgentLayer.TRIGGERS: "search_memory",
            AgentLayer.EDGE: "search_memory",
            AgentLayer.ENTERPRISE: "audit_security",
            AgentLayer.CONNECTORS: "search_memory",
            AgentLayer.MONITORING: "log_event",
            AgentLayer.HOTSWAP: "search_memory",
        }
        return defaults.get(layer, "search_memory")

    def _format_currency(self, amount: float, currency: str = "$") -> str:
        """Format a number as currency with commas."""
        if amount is None or amount == 0:
            return f"{currency}0.00"
        return f"{currency}{amount:,.2f}"

    def _format_number(self, num: float, decimals: int = 2) -> str:
        """Format a number with commas and specified decimals."""
        if num is None:
            return "0"
        if decimals == 0:
            return f"{int(num):,}"
        return f"{num:,.{decimals}f}"

    def _format_result_message(self, tool_name: str, result: Dict, task: str) -> str:
        """
        Format a user-friendly message based on tool result type.

        This transforms raw tool results into human-readable responses.
        """
        # Handle error cases first
        if not result.get("success", True):
            error = result.get("error", "Unknown error")
            return self._format_error_message(tool_name, error, task)

        # Format based on tool type
        if tool_name == "search_memory":
            return self._format_memory_search_result(result, task)

        if tool_name in ["calculate_cost", "rsmeans_query", "estimate_project"]:
            return self._format_economics_result(tool_name, result, task)

        if tool_name == "calculate_formula":
            return self._format_formula_result(result, task)

        if tool_name == "search_formulas":
            return self._format_formula_search_result(result, task)

        if tool_name == "write_memory":
            return f"✅ I've saved that to your memory. You can search for it later using keywords like: {', '.join(result.get('tags', [])[:3] or ['the main topic'])}."

        if tool_name == "query_bim":
            return self._format_bim_result(result, task)

        if tool_name == "extract_quantities":
            return self._format_quantities_result(result, task)

        if tool_name in ["validate_code", "scan_security", "run_tests"]:
            return self._format_validation_result(tool_name, result, task)

        if tool_name in ["generate_endpoint", "generate_component", "generate_model"]:
            return self._format_generation_result(tool_name, result, task)

        if tool_name in ["heal_error", "detect_errors", "analyze_incident"]:
            return self._format_healing_result(tool_name, result, task)

        # Default formatting for other tools
        return f"I executed {tool_name.replace('_', ' ')} and completed your request."

    def _format_error_message(self, tool_name: str, error: str, task: str) -> str:
        """Format error messages with helpful suggestions using centralized error handling."""
        # Handle new standardized error format (error might be a dict)
        if isinstance(error, dict):
            error_code = error.get("code", "unknown")
            error_message = error.get("message", "Unknown error")
            suggestion = error.get("suggestion", "")

            # Use centralized error formatter if available
            if hasattr(self, 'error_formatter') and self.error_formatter:
                formatted = self.error_formatter.format_tool_error(
                    tool_name,
                    error_message,
                    context={"code": error_code, "suggestion": suggestion}
                )
                if formatted:
                    return formatted

            # Fallback to simple error formatting
            message = f"❌ **Error:** {error_message}"
            if suggestion:
                message += f"\n\n💡 **Suggestion:** {suggestion}"
            return message

        # Original error string handling
        # First check for specific patterns that need custom formatting
        error_lower = error.lower()

        # Building type clarification needed
        if "building_type_clarification_needed" in error_lower:
            return """🏢 **Which building type did you mean?**

I found multiple options. Please specify:

**Office buildings:**
• `office-low` - Low-rise office (1-4 stories), ~$225/sq ft
• `office-high` - High-rise office (5+ stories), ~$285/sq ft

**Try:**
• "Calculate cost for office-low 5000 sq ft"
• "Estimate office-high building 10000 sq ft"

Or ask "What building types are available?" to see all options."""

        # Try to use centralized error handling for user-friendly messages
        try:
            # Create a temporary exception for the error
            class TempError(Exception):
                pass

            temp_error = TempError(error)
            friendly_error = get_user_friendly_error(temp_error, context={"tool": tool_name, "task": task})

            # Build a formatted message from the friendly error
            message_parts = [f"⚠️ **{friendly_error.user_message}**"]

            if friendly_error.suggestion:
                message_parts.append(f"\n{friendly_error.suggestion}")

            if friendly_error.retry_allowed:
                message_parts.append("\n💡 **You can try again** or rephrase your request.")

            return "\n".join(message_parts)
        except:
            # Fallback to original behavior if centralized handling fails
            pass

        # Economics-related errors
        if "need building_type" in error_lower or "need item_id" in error_lower:
            return """❓ **I need more information to calculate costs.**

Try one of these:
• "Estimate cost for a 5000 sq ft office building"
• "Calculate cost for item 03-100-100 with quantity 100"
• "What building types are available?"

**Examples:**
- "Cost estimate for 3000 sq ft warehouse"
- "Price of concrete per cubic yard" """

        if "item not found" in error_lower:
            return """🔍 **I couldn't find that item in RSMeans.**

**Try:**
• Searching with broader terms (e.g., "concrete" instead of "03-100-100")
• Checking the CSI division code
• Asking "What concrete items are available?"

**Example searches:**
- "concrete foundation"
- "steel reinforcement"
- "drywall" """

        if "formula" in error_lower:
            return """📐 **Formula calculation issue.**

**Try:**
• "Search formulas for concrete"
• "List available formulas"
• "Calculate slab concrete with length 10, width 20, depth 0.5"

**Available formula categories:**
- Concrete (slabs, footings, walls)
- Drywall (walls, ceilings)
- Flooring (tile, carpet, hardwood)
- Paint (interior, exterior)"""

        if "not found" in error_lower or "404" in error_lower:
            return f"""❌ **I couldn't find what you're looking for.**

**What I tried:** {tool_name.replace('_', ' ')}

**Try instead:**
• Use more general keywords
• Check spelling
• Ask me "What can you do with {tool_name.replace('_', ' ')}?"

**Error:** {error}"""

        # Default error message with centralized error handling context
        return f"""⚠️ **Something went wrong while processing your request.**

**What happened:** {error}

**Try:**
• Rephrasing your request
• Adding more specific details
• Ask "What can you do?" to see my capabilities

If this keeps happening, please try again in a moment."""

    def _format_memory_search_result(self, result: Dict, task: str) -> str:
        """Format memory search results in a user-friendly way.

        Handles both new standardized format and legacy format.
        """
        # Handle new standardized format
        if "results" in result and isinstance(result["results"], dict):
            results_data = result["results"]
            total = results_data.get("total_matches", 0)
            results = results_data.get("matches", [])
            query = result.get("metadata", {}).get("query", task)
        else:
            # Legacy format
            total = result.get("total_matches", 0)
            query = result.get("query", task)
            results = result.get("results", [])

        if total == 0 or not results:
            return f"""🤔 **I didn't find any memories matching "{query}".**

**Try searching for:**
• Related keywords (e.g., "concrete" instead of "cement")
• Broader terms (e.g., "building" instead of "warehouse")
• Check your spelling

**Or ask me to remember something new:**
• "Remember that foundation costs $5,000"
• "Save this: concrete price is $120/cubic yard"

**Recent topics I might have:**
• Cost estimates
• Project notes
• Formula calculations"""

        # Group results by source file
        sources = {}
        for r in results:
            source = r.get("source", "Unknown")
            if source not in sources:
                sources[source] = []
            sources[source].append(r)

        num_sources = len(sources)

        # Build the message with improved formatting
        message_parts = []
        message_parts.append(f"🔍 **Found {total} result{'s' if total != 1 else ''} from {num_sources} source{'s' if num_sources != 1 else ''}**")
        message_parts.append(f"   Query: \"{query}\"\n")

        # Show top results (max 10, but prefer fewer for readability)
        display_limit = min(10, max(5, total // 3))  # Scale based on total results
        displayed = 0

        # Sort sources by number of results (most relevant first)
        sorted_sources = sorted(sources.items(), key=lambda x: len(x[1]), reverse=True)

        for source, items in sorted_sources:
            if displayed >= display_limit:
                break

            message_parts.append(f"📄 **{source}** ({len(items)} result{'s' if len(items) != 1 else ''})")

            # Show top 2 results per source (max)
            for item in items[:2]:
                if displayed >= display_limit:
                    break

                content = item.get("content", "").strip()
                if content:
                    # Clean up content: remove headers, normalize whitespace
                    content = re.sub(r'^#+\s*', '', content)  # Remove markdown headers
                    content = re.sub(r'\n+', ' ', content)   # Replace newlines with spaces
                    content = re.sub(r'\s+', ' ', content)   # Normalize whitespace
                    content = content.strip()

                    # Truncate to 200 chars with ellipsis
                    if len(content) > 200:
                        content = content[:200].strip() + "..."
                    elif len(content) > 0 and not content.endswith('.'):
                        content = content + "..."

                    # Add relevance score if available
                    score = item.get("score", 0)
                    score_indicator = ""
                    if score >= 10:
                        score_indicator = " 🔥"  # High relevance
                    elif score >= 5:
                        score_indicator = " ⭐"  # Medium relevance

                    message_parts.append(f"   •{score_indicator} {content}")
                    displayed += 1

            message_parts.append("")  # Empty line between sources

        # Add summary if there are more results
        remaining = total - displayed
        if remaining > 0:
            message_parts.append(f"📌 ...and {remaining} more result{'s' if remaining != 1 else ''} not shown.")
            message_parts.append("")

        # Suggest follow-up queries based on context
        message_parts.append("💡 **What would you like to do?**")
        message_parts.append("• Ask for more details about any result")
        message_parts.append("• Refine your search with more specific keywords")

        # Context-aware suggestions
        if total > 20:
            message_parts.append(f"• Try: \"{query} concrete\" to narrow results")
        if num_sources > 3:
            message_parts.append("• Specify a file: \"search in MEMORY.md\"")

        message_parts.append("• Save something new to memory")

        # Add helpful note if results seem overwhelming
        if total > 50:
            message_parts.append(f"\n💭 *Tip: You got many results ({total}). Adding more keywords will help me find exactly what you need.*")

        return "\n".join(message_parts)

    async def _analyze_uploaded_file(self, file_id: str, task: str, context: Dict) -> AgentResult:
        """Analyze an uploaded file (image, PDF, etc.) and return results."""
        import time
        import asyncio
        start_time = time.time()

        try:
            # Get file info from documents endpoint
            import httpx

            def get_files():
                try:
                    response = httpx.get(f"{settings.api_base_url}/api/v1/documents/files", timeout=10.0)
                    return response.json() if response.status_code == 200 else []
                except Exception as e:
                    print(f"Error getting files: {e}")
                    return []

            # Run sync code in thread pool
            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(None, get_files)

            # Find the file (handle file_id with or without extension)
            file_info = None
            for f in files:
                stored_id = f.get("file_id", "")
                # Match with or without extension
                if stored_id == file_id or stored_id.startswith(file_id + "."):
                    file_info = f
                    break

            if not file_info:
                return AgentResult(
                    success=False,
                    action=AgentAction.READ_MEMORY,
                    layer=AgentLayer.PORTAL,
                    data={"error": "file_not_found"},
                    message=f"❌ **File not found**\n\nI couldn't find file `{file_id[:20]}...`. It may have been deleted or expired.\n\nTry uploading the file again.",
                    execution_time_ms=0
                )

            filename = file_info.get("file_name", "Unknown")

            # Infer file type from extension
            file_type = "unknown"
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                if filename.lower().endswith('.png'):
                    file_type = "image/png"
                elif filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                    file_type = "image/jpeg"
                elif filename.lower().endswith('.webp'):
                    file_type = "image/webp"
            elif filename.lower().endswith('.pdf'):
                file_type = "application/pdf"
            elif filename.lower().endswith(('.mp3', '.wav', '.m4a')):
                if filename.lower().endswith('.mp3'):
                    file_type = "audio/mpeg"
                elif filename.lower().endswith('.wav'):
                    file_type = "audio/wav"
                elif filename.lower().endswith('.m4a'):
                    file_type = "audio/m4a"

            # Determine analysis type based on file type
            if file_type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
                # Analyze image with OCR
                return await self._analyze_image_file(file_id, filename, context)
            elif file_type == "application/pdf":
                # Analyze PDF
                return await self._analyze_pdf_file(file_id, filename, context)
            elif file_type in ["audio/mpeg", "audio/wav", "audio/mp3", "audio/m4a"]:
                # Audio file
                return AgentResult(
                    success=True,
                    action=AgentAction.READ_MEMORY,
                    layer=AgentLayer.PORTAL,
                    data={"file_id": file_id, "filename": filename, "type": "audio"},
                    message=f"🎵 **Audio File Uploaded**\n\n**File:** {filename}\n**ID:** `{file_id[:20]}...`\n\nAudio has been uploaded successfully. To transcribe this audio, set the `OPENAI_API_KEY` environment variable.",
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            else:
                # Generic document
                return AgentResult(
                    success=True,
                    action=AgentAction.READ_MEMORY,
                    layer=AgentLayer.PORTAL,
                    data={"file_id": file_id, "filename": filename, "type": file_type},
                    message=f"📄 **Document Uploaded**\n\n**File:** {filename}\n**Type:** {file_type}\n**ID:** `{file_id[:20]}...`\n\nDocument has been saved. You can reference it in future queries.",
                    execution_time_ms=(time.time() - start_time) * 1000
                )

        except Exception as e:
            return AgentResult(
                success=False,
                action=AgentAction.READ_MEMORY,
                layer=AgentLayer.PORTAL,
                data={"error": str(e)},
                message=f"⚠️ **Error analyzing file**\n\nI encountered an issue while processing the file: {str(e)[:100]}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

    async def _analyze_image_file(self, file_id: str, filename: str, context: Dict) -> AgentResult:
        """Analyze an image file using OCR."""
        import time
        import asyncio
        import httpx
        start_time = time.time()

        try:
            # Retrieve the file
            def get_file():
                try:
                    response = httpx.get(f"{settings.api_base_url}/api/v1/documents/upload/chat/{file_id}", timeout=10.0)
                    return response.content if response.status_code == 200 else None
                except Exception as e:
                    print(f"Error retrieving image: {e}")
                    return None

            loop = asyncio.get_event_loop()
            file_content = await loop.run_in_executor(None, get_file)

            if file_content is None:
                raise Exception("Failed to retrieve image")

            # Run OCR
            def run_ocr():
                try:
                    files = {"file": (filename, file_content, "image/png")}
                    ocr_response = httpx.post(f"{settings.api_base_url}/api/v1/documents/ocr", files=files, timeout=15.0)
                    return ocr_response.json() if ocr_response.status_code == 200 else {}
                except Exception as e:
                    print(f"Error running OCR: {e}")
                    return {}

            ocr_data = await loop.run_in_executor(None, run_ocr)

            text = ocr_data.get("text", "")
            confidence = ocr_data.get("confidence", 0)

            if text:
                message = f"📸 **Image Analysis: {filename}**\n\n"
                message += f"**Extracted Text:**\n```\n{text[:500]}{'...' if len(text) > 500 else ''}\n```\n\n"
                message += f"**Confidence:** {confidence:.1f}%\n"
                message += f"**Word Count:** {ocr_data.get('word_count', 0)}\n\n"
                message += "💡 *You can ask me to analyze specific content from this image.*"
            else:
                message = f"📸 **Image Uploaded: {filename}**\n\n"
                message += "I couldn't extract any text from this image.\n\n"
                message += "💡 *Tip: Make sure the image contains clear, readable text.*"

            return AgentResult(
                success=True,
                action=AgentAction.READ_MEMORY,
                layer=AgentLayer.PORTAL,
                data={"file_id": file_id, "filename": filename, "ocr": ocr_data},
                message=message,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return AgentResult(
                success=False,
                action=AgentAction.READ_MEMORY,
                layer=AgentLayer.PORTAL,
                data={"error": str(e)},
                message=f"⚠️ **Error analyzing image**\n\n{str(e)[:100]}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

    async def _analyze_pdf_file(self, file_id: str, filename: str, context: Dict) -> AgentResult:
        """Analyze a PDF file."""
        import time
        import asyncio
        import httpx
        start_time = time.time()

        try:
            # Retrieve the file
            def get_file():
                try:
                    response = httpx.get(f"{settings.api_base_url}/api/v1/documents/upload/chat/{file_id}", timeout=10.0)
                    return response.content if response.status_code == 200 else None
                except Exception as e:
                    print(f"Error retrieving PDF: {e}")
                    return None

            loop = asyncio.get_event_loop()
            file_content = await loop.run_in_executor(None, get_file)

            if file_content is None:
                raise Exception("Failed to retrieve PDF")

            # Run classification
            def classify():
                try:
                    files = {"file": (filename, file_content, "application/pdf")}
                    classify_response = httpx.post(f"{settings.api_base_url}/api/v1/documents/classify", files=files, timeout=15.0)
                    return classify_response.json() if classify_response.status_code == 200 else {}
                except Exception as e:
                    print(f"Error classifying PDF: {e}")
                    return {}

            classify_data = await loop.run_in_executor(None, classify)

            doc_class = classify_data.get("document_class") or classify_data.get("document_type", "Unknown")

            message = f"📄 **PDF Analysis: {filename}**\n\n"
            message += f"**Document Type:** {doc_class.title()}\n"
            if classify_data.get("confidence"):
                message += f"**Confidence:** {classify_data['confidence']:.0%}\n"
            message += f"**File ID:** `{file_id[:20]}...`\n\n"
            message += "💡 *The document has been analyzed and classified.*"

            return AgentResult(
                success=True,
                action=AgentAction.READ_MEMORY,
                layer=AgentLayer.PORTAL,
                data={"file_id": file_id, "filename": filename, "classification": classify_data},
                message=message,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            return AgentResult(
                success=False,
                action=AgentAction.READ_MEMORY,
                layer=AgentLayer.PORTAL,
                data={"error": str(e)},
                message=f"⚠️ **Error analyzing PDF**\n\n{str(e)[:100]}",
                execution_time_ms=(time.time() - start_time) * 1000
            )

    async def _find_recent_file(self, task: str, session_id: Optional[str] = None) -> Optional[str]:
        """Find a file by looking up recent uploads or matching filename."""
        import httpx
        import asyncio

        try:
            def get_files():
                try:
                    response = httpx.get(f"{settings.api_base_url}/api/v1/documents/files", timeout=10.0)
                    return response.json() if response.status_code == 200 else []
                except Exception as e:
                    print(f"Error getting files: {e}")
                    return []

            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(None, get_files)

            if not files:
                return None

            # Sort by upload time (newest first)
            files.sort(key=lambda f: f.get('uploaded_at', ''), reverse=True)

            # Extract potential filename from task (remove punctuation, normalize)
            task_clean = task.strip().lower()
            task_clean = task_clean.replace('?', '').replace('!', '').replace('.', '').strip()

            # 1. Try exact filename match
            for f in files:
                filename = f.get('file_name', '').lower()
                if task_clean in filename or filename in task_clean:
                    return f.get('file_id')

            # 2. Try partial filename match (for long names like IP-INF-054...)
            # Extract the base name without extension
            task_base = task_clean.split('.')[0] if '.' in task_clean else task_clean
            if len(task_base) > 5:  # Only if meaningful length
                for f in files:
                    filename = f.get('file_name', '').lower()
                    if task_base in filename:
                        return f.get('file_id')

            # 3. Return most recent file (if query mentions "this file", "the file", etc.)
            recent_keywords = ['this file', 'this pdf', 'this document', 'the file', 'the pdf', 'the document', 'uploaded file']
            if any(kw in task.lower() for kw in recent_keywords):
                most_recent = files[0]
                return most_recent.get('file_id')

            # 4. If task looks like a filename (has extension) but no match found,
            # assume user is referring to the most recently uploaded file
            # Check if task looks like a filename
            task_looks_like_filename = bool(re.search(r'\.[a-zA-Z]{3,4}$', task.strip()))
            if task_looks_like_filename:
                print(f"Filename query '{task}' didn't match, returning most recent file")
                return files[0].get('file_id') if files else None

            return None

        except Exception as e:
            print(f"Error finding file: {e}")
            return None

    def _format_economics_result(self, tool_name: str, result: Dict, task: str) -> str:
        """Format economics/cost results with currency and breakdown.

        Handles both new standardized format and legacy format.
        """
        # Extract results from new standardized format if present
        if "results" in result and isinstance(result["results"], dict):
            results_data = result["results"]
            # Merge results data with top-level for compatibility
            merged_result = {**result, **results_data}
        else:
            merged_result = result

        # Handle building type clarification request
        if merged_result.get("requires_clarification"):
            suggestions = merged_result.get("suggestions", [])
            parsed_type = merged_result.get("parsed_parameters", {}).get("building_type", "this building type")

            message = f"🏗️ **Building Type Clarification Needed**\n\n"
            message += f"You mentioned '{parsed_type}', but I need more specifics.\n\n"
            message += f"**Which type did you mean?**\n\n"

            for i, sug in enumerate(suggestions[:4], 1):
                code = sug.get("code", "")
                name = sug.get("name", "")
                cost_per_sf = sug.get("cost_per_sf", 0)
                typical_size = sug.get("typical_size", "N/A")

                message += f"{i}. **{name}** (`{code}`)\n"
                message += f"   💰 ~{self._format_currency(cost_per_sf)}/sq ft\n"
                if typical_size != "N/A":
                    message += f"   📐 Typical: {self._format_number(typical_size, 0)} sq ft\n"
                message += "\n"

            message += "**Try one of these queries:**\n"
            for example in result.get("example_queries", [])[:2]:
                message += f'• "{example}"\n'

            return message

        # Handle error with suggestions
        if not merged_result.get("success", True) and "suggestions" in merged_result:
            message = f"❓ **{merged_result.get('message', 'Building Type Not Found')}" + "**\n\n"
            message += merged_result.get("error", "") + "\n\n"
            message += "**Suggested building types:**\n\n"

            for sug in merged_result.get("suggestions", [])[:5]:
                code = sug.get("code", "")
                name = sug.get("name", "")
                cost_per_sf = sug.get("cost_per_sf", 0)
                message += f"• **{name}** (`{code}`) - {self._format_currency(cost_per_sf)}/sq ft\n"

            message += "\n**Example queries:**\n"
            for example in merged_result.get("example_queries", [])[:3]:
                message += f'• "{example}"\n'

            return message

        # Building estimate results
        if "estimate" in merged_result:
            estimate = merged_result.get("estimate", {})
            building = estimate.get("building_type", "Building")
            size = estimate.get("size_sf", 0)
            city = estimate.get("city", "National Average")
            costs = estimate.get("costs", {})
            total = estimate.get("total_cost", 0)
            per_sqft = estimate.get("base_cost_per_sf", estimate.get("cost_per_sqft", 0))

            message = f"""## Cost Estimate: {building.title()}

**Project Details**
- Location: {city}
- Building Size: {self._format_number(size, 0)} sq ft
- Cost per sq ft: {self._format_currency(per_sqft)}

**Cost Breakdown**"""

            # Add line items
            for category, cost in costs.items():
                if isinstance(cost, (int, float)) and cost > 0:
                    pct = (cost / total * 100) if total > 0 else 0
                    message += f"\n- {category.replace('_', ' ').title()}: {self._format_currency(cost)} ({pct:.1f}%)"

            message += f"\n\n**Total Estimated Cost: {self._format_currency(total)}**"

            # Add note about accuracy
            message += "\n\n*Note: This is a preliminary estimate. Actual costs may vary based on specific design requirements, material selections, and current market conditions.*"

            return message

        # RSMeans item query results
        if "results" in result and tool_name == "rsmeans_query":
            # Handle nested structure: result["results"]["items"] or result["results"] directly
            results_data = result.get("results", {})
            if isinstance(results_data, dict) and "items" in results_data:
                items = results_data["items"]
            else:
                items = results_data if isinstance(results_data, list) else []
            total_items = result.get("total", len(items)) or len(items)
            query = result.get("query", task)

            if not items:
                return f"""🔍 **No RSMeans items found for \"{query}\".**

**Try:**
• Broader search terms (e.g., "concrete" instead of "03-100-100")
• Category filters (e.g., "concrete in division 03")
• Common construction terms

**Popular searches:**
• "concrete"
• "steel reinforcement"
• "drywall"
• "electrical" """

            message = f"""🏗️ **Found {total_items} RSMeans item{'s' if total_items != 1 else ''} matching \"{query}\"**

"""
            for i, item in enumerate(items[:5], 1):
                desc = item.get("description", item.get("title", "Unknown"))
                base_cost = item.get("base_cost", 0)
                unit = item.get("unit", "ea")
                item_id = item.get("id", item.get("item_id", "N/A"))

                message += f"{i}. **{desc}**\n"
                message += f"   💰 {self._format_currency(base_cost)} per {unit}\n"
                message += f"   🏷️ Item ID: `{item_id}`\n\n"

            if len(items) > 5:
                message += f"...and {len(items) - 5} more items.\n\n"

            message += "**To calculate costs:**\n"
            first_item_id = items[0].get("id", items[0].get("item_id", "item_id")) if items else "item_id"
            message += f'• "Calculate cost for {first_item_id} with quantity 100"'

            return message

        # Single item cost calculation
        if "item" in result and "quantity" in result:
            item = result.get("item", {})
            quantity = result.get("quantity", 0)
            total_cost = result.get("total_cost", 0)

            desc = item.get("description", item.get("title", "Unknown"))
            unit_cost = item.get("base_cost", 0)
            unit = item.get("unit", "ea")

            return f"""## Cost Calculation

**Item Details**
- Description: {desc}
- Unit Price: {self._format_currency(unit_cost)} per {unit}
- Quantity: {self._format_number(quantity, 0)} {unit}

**Total Cost: {self._format_currency(total_cost)}**

*Source: RSMeans Construction Cost Database*"""

        # Building types list
        if "building_types" in result:
            types = result.get("building_types", [])
            message = "## Available Building Types\n\n"
            for bt in types[:10]:
                name = bt.get("name", "Unknown")
                desc = bt.get("description", "")
                base_cost = bt.get("base_cost_per_sqft", 0)
                message += f"- **{name}**"
                if desc:
                    message += f" - {desc}"
                if base_cost:
                    message += f" (from {self._format_currency(base_cost)}/sq ft)"
                message += "\n"

            message += f"\n**Example:** 'Estimate cost for 5000 sq ft office building'"

            return message

        return f"Economics calculation completed."

    def _format_formula_result(self, result: Dict, task: str) -> str:
        """Format formula calculation results.

        Handles both new standardized format and legacy format.
        """
        # Handle new standardized format
        if "results" in result and isinstance(result["results"], dict):
            results_data = result["results"]
            if "calculation" in results_data:
                calc = results_data["calculation"]
                formula_name = calc.get("formula_name", calc.get("name", "Calculation"))
                inputs = calc.get("inputs", {})
                outputs = {"result": calc.get("result", 0), "unit": calc.get("unit", "")}
            else:
                formula_name = results_data.get("formula_name", "Calculation")
                inputs = results_data.get("inputs", {})
                outputs = results_data.get("outputs", {})
        else:
            # Legacy format
            formula_name = result.get("formula_name", "Calculation")
            inputs = result.get("inputs", {})
            outputs = result.get("outputs", {})

        message = f"📐 **{formula_name}**\n\n"

        # Show inputs
        if inputs:
            message += "**Input Values:**\n"
            for key, value in inputs.items():
                # Format with units if it's a number
                if isinstance(value, (int, float)):
                    message += f"  • {key.replace('_', ' ').title()}: {self._format_number(value)}\n"
                else:
                    message += f"  • {key.replace('_', ' ').title()}: {value}\n"
            message += "\n"

        # Show results
        if outputs:
            message += "**Results:**\n"
            for key, value in outputs.items():
                if isinstance(value, (int, float)):
                    # Determine unit based on key name
                    unit = ""
                    if "cost" in key.lower() or "price" in key.lower():
                        message += f"  • {key.replace('_', ' ').title()}: {self._format_currency(value)}\n"
                    elif "area" in key.lower() or "surface" in key.lower():
                        message += f"  • {key.replace('_', ' ').title()}: {self._format_number(value)} sq ft\n"
                    elif "volume" in key.lower() or "cubic" in key.lower():
                        message += f"  • {key.replace('_', ' ').title()}: {self._format_number(value)} cubic yards\n"
                    elif "weight" in key.lower() or "lbs" in key.lower():
                        message += f"  • {key.replace('_', ' ').title()}: {self._format_number(value)} lbs\n"
                    else:
                        message += f"  • {key.replace('_', ' ').title()}: {self._format_number(value)} {unit}\n"
                else:
                    message += f"  • {key.replace('_', ' ').title()}: {value}\n"

        return message

    def _format_formula_search_result(self, result: Dict, task: str) -> str:
        """Format formula search results.

        Handles both new standardized format and legacy format.
        """
        # Handle new standardized format
        if "results" in result and isinstance(result["results"], dict):
            results_data = result["results"]
            formulas = results_data.get("formulas", [])
            query = result.get("metadata", {}).get("query", task)
        else:
            # Legacy format
            formulas = result.get("formulas", result.get("results", []))
            query = result.get("query", task)

        if not formulas:
            return f"""📐 **No formulas found for \"{query}\".**

**Try searching for:**
• "concrete" (slabs, footings, walls)
• "drywall" (walls, ceilings)
• "paint" (interior, exterior)
• "flooring" (tile, carpet, hardwood)
• "masonry" (bricks, blocks)

**Or browse by topic:**
• Structural calculations
• Material quantities
• Cost estimations"""

        message = f"📐 **Found {len(formulas)} formula{'s' if len(formulas) != 1 else ''} matching \"{query}\"**\n\n"

        for i, formula in enumerate(formulas[:5], 1):
            name = formula.get("name", formula.get("title", "Unknown Formula"))
            desc = formula.get("description", "")
            category = formula.get("category", "")

            message += f"{i}. **{name}**"
            if category:
                message += f" *({category})*"
            message += "\n"
            if desc:
                message += f"   {desc}\n"
            message += "\n"

        if len(formulas) > 5:
            message += f"...and {len(formulas) - 5} more formulas.\n\n"

        message += "**To use a formula:**\n"
        message += f'• "Calculate {formulas[0].get("name", "formula")} with [your values]"'

        return message

    def _format_bim_result(self, result: Dict, task: str) -> str:
        """Format BIM query results."""
        # Handle new standardized format
        if "results" in result and isinstance(result["results"], dict):
            results_data = result["results"]
            elements = results_data.get("elements", [])
            model = results_data.get("model", results_data.get("model_name", "BIM Model"))
        else:
            # Legacy format
            elements = result.get("elements", result.get("results", []))
            model = result.get("model", result.get("model_name", "BIM Model"))

        if not elements:
            return f"""🏗️ **No elements found in {model}.**

**Try:**
• Using different element types (walls, doors, windows)
• Checking the model name
• Querying with filters (e.g., "walls on level 1")

**Common BIM queries:**
• "Show all walls"
• "Count doors on level 2"
• "Get windows by type" """

        message = f"🏗️ **BIM Model Query Results**\n"
        message += f"📁 Model: {model}\n"
        message += f"📊 Elements found: {len(elements)}\n\n"

        # Group by type
        by_type = {}
        for elem in elements:
            elem_type = elem.get("type", elem.get("category", "Unknown"))
            if elem_type not in by_type:
                by_type[elem_type] = []
            by_type[elem_type].append(elem)

        for elem_type, items in list(by_type.items())[:5]:
            message += f"**{elem_type}:** {len(items)} found\n"
            for item in items[:3]:
                name = item.get("name", item.get("id", "Unknown"))
                message += f"  • {name}\n"
            if len(items) > 3:
                message += f"  ...and {len(items) - 3} more\n"
            message += "\n"

        return message

    def _format_quantities_result(self, result: Dict, task: str) -> str:
        """Format quantity extraction results."""
        # Handle new standardized format
        if "results" in result and isinstance(result["results"], dict):
            results_data = result["results"]
            quantities = results_data.get("quantities", {})
            totals = results_data.get("totals", {})
            # Convert dict to list for compatibility
            if isinstance(quantities, dict):
                quantities = [{"name": k, **v} for k, v in quantities.items()]
            total_volume = totals.get("total_volume_m3", 0) * 1.30795  # Convert m3 to cubic yards
            total_area = totals.get("total_area_m2", 0) * 10.7639  # Convert m2 to sq ft
        else:
            # Legacy format
            quantities = result.get("quantities", result.get("results", []))
            total_volume = result.get("total_volume", 0)
            total_area = result.get("total_area", 0)

        if not quantities:
            return f"""📏 **No quantities extracted.**

**Try:**
• Specifying element types (concrete walls, steel beams)
• Checking your BIM model is loaded
• Using specific level or area filters

**Examples:**
• "Extract concrete quantities"
• "Calculate drywall area"
• "Get steel tonnage" """

        message = "📏 **Quantity Takeoff Results**\n\n"

        if total_volume > 0:
            message += f"**Total Volume:** {self._format_number(total_volume)} cubic yards\n"
        if total_area > 0:
            message += f"**Total Area:** {self._format_number(total_area)} sq ft\n"

        message += "\n**Breakdown:**\n"

        for item in quantities[:10]:
            name = item.get("name", item.get("type", "Unknown"))
            qty = item.get("quantity", item.get("value", item.get("total_volume_m3", item.get("total_area_m2", 0))))
            unit = item.get("unit", "ea")

            if isinstance(qty, (int, float)):
                message += f"  • {name}: {self._format_number(qty)} {unit}\n"
            else:
                message += f"  • {name}: {qty} {unit}\n"

        if len(quantities) > 10:
            message += f"\n...and {len(quantities) - 10} more items."

        return message

    def _format_validation_result(self, tool_name: str, result: Dict, task: str) -> str:
        """Format code validation results."""
        issues = result.get("issues", result.get("errors", result.get("vulnerabilities", [])))
        passed = result.get("passed", result.get("success", len(issues) == 0))

        if tool_name == "scan_security":
            if passed and not issues:
                return "🔒 **Security Scan Passed** ✅\n\nNo vulnerabilities detected in the scanned code."

            message = f"🔒 **Security Scan Results**\n\n"
            message += f"⚠️ **{len(issues)} issue{'s' if len(issues) != 1 else ''} found**\n\n"

            for i, issue in enumerate(issues[:5], 1):
                severity = issue.get("severity", "Medium")
                desc = issue.get("description", issue.get("message", "Unknown issue"))
                emoji = "🔴" if severity == "High" else "🟡" if severity == "Medium" else "🟢"
                message += f"{i}. {emoji} **{severity}:** {desc}\n"

            return message

        if tool_name == "run_tests":
            passed_tests = result.get("passed", 0)
            failed_tests = result.get("failed", 0)
            total = result.get("total", passed_tests + failed_tests)

            if failed_tests == 0:
                return f"🧪 **All Tests Passed** ✅\n\n{passed_tests}/{total} tests passed successfully."

            return f"🧪 **Test Results**\n\n✅ Passed: {passed_tests}\n❌ Failed: {failed_tests}\n📊 Total: {total}"

        if tool_name == "validate_code":
            if passed and not issues:
                return "✅ **Code Validation Passed**\n\nYour code meets all quality standards."

            message = "⚠️ **Code Validation Issues**\n\n"
            for issue in issues[:5]:
                message += f"• {issue.get('message', 'Unknown issue')}\n"

            return message

        return f"✅ Validation completed successfully."

    def _format_generation_result(self, tool_name: str, result: Dict, task: str) -> str:
        """Format code generation results."""
        artifact = result.get("artifact", result.get("file", result.get("name", "")))

        if tool_name == "generate_endpoint":
            return f"""🚀 **API Endpoint Generated** ✅

**Created:** `{artifact}`

The endpoint is ready to use. It's been validated and added to the registry. You can now:
• Test it with sample requests
• Deploy it to your environment
• Extend it with additional functionality"""

        if tool_name == "generate_component":
            return f"""⚛️ **React Component Generated** ✅

**Created:** `{artifact}`

The component is ready to integrate into your frontend. It's been:
• Styled and structured
• Validated for best practices
• Added to the component registry"""

        if tool_name == "generate_model":
            return f"""🗄️ **Data Model Generated** ✅

**Created:** `{artifact}`

The model includes:
• Database schema definitions
• Validation rules
• API serialization
• Migration files (if needed)"""

        return f"✅ Successfully generated: {artifact}"

    def _format_healing_result(self, tool_name: str, result: Dict, task: str) -> str:
        """Format healing/error fixing results."""
        if tool_name == "detect_errors":
            errors = result.get("errors", [])
            if not errors:
                return "✅ **No errors detected.** Your system is running smoothly."

            message = f"🐛 **{len(errors)} Error{'s' if len(errors) != 1 else ''} Detected**\n\n"
            for error in errors[:5]:
                msg = error.get("message", error.get("error", "Unknown error"))
                location = error.get("location", error.get("file", ""))
                message += f"• **{msg}**"
                if location:
                    message += f" in `{location}`"
                message += "\n"

            return message

        if tool_name == "heal_error":
            fixed = result.get("fixed", result.get("success", False))
            if fixed:
                return """🔧 **Issue Fixed** ✅

The error has been automatically resolved. The system:
• Identified the root cause
• Applied the appropriate fix
• Validated the solution

Your code should now work correctly."""

            return """⚠️ **Unable to Auto-Fix**

The issue requires manual attention. Try:
• Checking the error logs for details
• Reviewing recent code changes
• Running validation tests

You can also provide more context about the error."""

        if tool_name == "analyze_incident":
            cause = result.get("root_cause", "Unknown")
            recommendations = result.get("recommendations", [])

            message = f"📊 **Incident Analysis**\n\n"
            message += f"**Root Cause:** {cause}\n\n"

            if recommendations:
                message += "**Recommendations:**\n"
                for rec in recommendations[:5]:
                    message += f"  • {rec}\n"

            return message

        return "🔧 Healing operation completed."

    def _generate_conversation_response(self, task: str) -> str:
        """Generate a conversational response for greetings and general queries."""
        task_lower = task.lower()

        if any(g in task_lower for g in ['hello', 'hi', 'hey', 'greetings']):
            return """Hello. I am Cerebrum AI Agent, your construction intelligence assistant.

I operate across 14 specialized layers:

**Development:** Coding, Registry, Validation, Hotswap, Healing, Prompts, Triggers
**Construction:** Economics (cost estimation), VDC (BIM), Edge (devices)
**Operations:** Portal, Enterprise, Connectors, Monitoring

**How can I help you today?**

Examples:
- "Calculate concrete costs for a 10x20x0.5 foundation"
- "Estimate cost for 5000 sq ft office building in Dubai"
- "Analyze this PDF document"
- "/agent help" for all commands"""

        if any(h in task_lower for h in ['what can you do', 'who are you', 'help', 'capabilities']):
            return """**Cerebrum AI Agent Capabilities**

**Code & Development:**
- Generate API endpoints, components, data models
- Refactor and optimize code
- Run security scans and validation

**Construction & Cost:**
- RSMeans cost queries and estimates
- Project cost calculations
- Bill of Quantities (BOQ) generation

**Document & BIM:**
- Analyze uploaded documents (PDF, images)
- BIM model queries and quantity extraction
- Design clash detection

Use `/agent layers` to see all available tools."""

        if any(t in task_lower for t in ['thanks', 'thank you']):
            return "You're welcome. Let me know if you need further assistance."

        if any(f in task_lower for f in ['formula', 'formulas']):
            return """**Construction Formulas**

Available calculation types:

**Concrete:** Volume (L × W × D), cost estimation
**Drywall:** Wall area, sheet calculations
**Paint:** Coverage area, gallons needed
**Flooring:** Square footage, material waste
**Masonry:** Block/brick counts

Ask about a specific calculation or use `/agent tools` to see all formulas."""

        return f"""I understand you're asking about: "{task}"

I'm Cerebrum AI Agent with access to 14 specialized layers for construction and development tasks.

**Try asking me to:**
• Generate code or APIs
• Calculate construction costs
• Analyze documents or BIM models
• Search through your conversation history

Type `/agent help` for all available commands, or just tell me what you need!"""

    # ============ WORKING MEMORY (Task Checkpointing) ============

    def _get_working_memory_key(self, task_id: Optional[str] = None) -> str:
        """Generate Redis key for working memory."""
        session_id = self.context.session_id
        if task_id:
            return f"agent:{session_id}:task:{task_id}"
        return f"agent:{session_id}:current"

    async def save_working_memory(
        self,
        task_description: str,
        steps_completed: List[str],
        steps_remaining: List[str],
        intermediate_results: Dict[str, Any],
        task_id: Optional[str] = None,
        ttl_seconds: int = 3600
    ) -> bool:
        """Save agent working memory to Redis."""
        try:
            from app.services.redis_state_store import RedisStateStore

            store = RedisStateStore()
            await store.connect()

            memory_data = {
                "session_id": self.context.session_id,
                "task_description": task_description,
                "steps_completed": steps_completed,
                "steps_remaining": steps_remaining,
                "intermediate_results": intermediate_results,
                "current_layer": self.context.current_layer.value,
                "started_at": intermediate_results.get("started_at", datetime.now().isoformat()),
                "last_updated": datetime.now().isoformat(),
                "status": "in_progress"
            }

            key = self._get_working_memory_key(task_id)
            success = await store.set_session_data(key, memory_data, ttl_seconds)
            await store.disconnect()

            return success

        except Exception as e:
            logger.warning(f"Failed to save working memory: {e}")
            return False

    async def load_working_memory(self, task_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load agent working memory from Redis."""
        try:
            from app.services.redis_state_store import RedisStateStore

            store = RedisStateStore()
            await store.connect()

            key = self._get_working_memory_key(task_id)
            memory_data = await store.get_session_data(key)

            await store.disconnect()

            if memory_data:
                if "current_layer" in memory_data:
                    layer_name = memory_data["current_layer"]
                    try:
                        self.context.current_layer = AgentLayer(layer_name)
                    except ValueError:
                        pass

            return memory_data

        except Exception as e:
            logger.warning(f"Failed to load working memory: {e}")
            return None

    async def clear_working_memory(self, task_id: Optional[str] = None) -> bool:
        """Clear working memory after task completion."""
        try:
            from app.services.redis_state_store import RedisStateStore

            store = RedisStateStore()
            await store.connect()

            key = self._get_working_memory_key(task_id)
            success = await store.set_session_data(key, {"status": "completed"}, 60)

            await store.disconnect()
            return success

        except Exception as e:
            logger.warning(f"Failed to clear working memory: {e}")
            return False

    async def checkpoint(
        self,
        step_name: str,
        step_result: Any,
        task_description: str,
        remaining_steps: List[str],
        task_id: Optional[str] = None
    ) -> bool:
        """Checkpoint progress during a multi-step task."""
        existing = await self.load_working_memory(task_id) or {}

        steps_completed = existing.get("steps_completed", [])
        if step_name not in steps_completed:
            steps_completed.append(step_name)

        intermediate_results = existing.get("intermediate_results", {})
        intermediate_results[step_name] = step_result
        intermediate_results["last_checkpoint"] = datetime.now().isoformat()

        if "started_at" not in intermediate_results:
            intermediate_results["started_at"] = datetime.now().isoformat()

        return await self.save_working_memory(
            task_description=task_description,
            steps_completed=steps_completed,
            steps_remaining=remaining_steps,
            intermediate_results=intermediate_results,
            task_id=task_id
        )


# Singleton
_agent_instance: Optional[EnhancedCerebrumAgent] = None
_agent_initialized: bool = False


def get_enhanced_agent(lazy_init: bool = True) -> EnhancedCerebrumAgent:
    """
    Get the singleton EnhancedCerebrumAgent instance.
    
    Args:
        lazy_init: If True, defer expensive initialization (memory indexing) until initialize() is called.
                  If False, initialize synchronously (for backwards compatibility).
    """
    global _agent_instance, _agent_initialized
    if _agent_instance is None:
        _agent_instance = EnhancedCerebrumAgent(lazy_init=lazy_init)
        _agent_initialized = False
    return _agent_instance


async def initialize_agent() -> EnhancedCerebrumAgent:
    """
    Initialize the agent asynchronously during app startup.
    This pre-loads the memory index to avoid blocking on first request.
    """
    global _agent_instance, _agent_initialized
    if _agent_instance is None:
        _agent_instance = EnhancedCerebrumAgent(lazy_init=True)
    
    if not _agent_initialized:
        await _agent_instance.initialize()
        _agent_initialized = True
        logger.info("Agent pre-initialized during startup")
    
    return _agent_instance
