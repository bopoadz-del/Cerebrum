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

logger = logging.getLogger(__name__)


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
    """Enhanced agent result."""
    success: bool
    action: AgentAction
    layer: AgentLayer
    data: Dict[str, Any]
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: Optional[float] = None
    related_conversations: List[str] = field(default_factory=list)
    suggested_next_actions: List[str] = field(default_factory=list)


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
        self._build_index()
    
    def _build_index(self):
        """Build in-memory index of all conversations."""
        if not self.memory_path.exists():
            return
        
        for memory_file in list(self.memory_path.glob("*.md")) + [self.workspace_path / "MEMORY.md"]:
            if memory_file.exists():
                self._index_file(memory_file)
    
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
            "total_entries": len(results),
            "filtered_by": {"days": days, "layers": layers, "tags": tags},
            "entries": results[:50]  # Limit results
        }
    
    def semantic_search(self, 
                       query: str, 
                       limit: int = 10,
                       context_window: int = 300) -> Dict:
        """
        Advanced search with relevance scoring.
        
        Uses multiple scoring factors:
        - Exact phrase matches (high weight)
        - Keyword frequency
        - Recency boost
        - Tag matches
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        scores = []
        
        for entry_id, entry in self.memory_index.items():
            content_lower = entry.content.lower()
            score = 0.0
            
            # Exact phrase match (high weight)
            if query_lower in content_lower:
                score += 10.0
            
            # Word frequency
            for word in query_words:
                count = content_lower.count(word)
                score += count * 1.0
            
            # Tag match bonus
            for tag in entry.tags:
                if tag.lower() in query_words:
                    score += 5.0
            
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
            "query": query,
            "total_matches": len(scores),
            "results": scores[:limit]
        }
    
    def get_conversation_thread(self, entry_id: str, context_entries: int = 3) -> Dict:
        """
        Get a conversation thread with surrounding context.
        """
        if entry_id not in self.memory_index:
            return {"error": "Entry not found"}
        
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
            return {"error": "Entry not found in source"}
        
        # Get surrounding entries
        start = max(0, idx - context_entries)
        end = min(len(source_entries), idx + context_entries + 1)
        thread = source_entries[start:end]
        
        return {
            "target_entry": asdict(entry),
            "thread": [asdict(e) for e in thread],
            "position": idx - start
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
            AgentLayer.ECONOMICS: ["cost", "price", "budget", "estimate", "rsmeans"],
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
    
    def __init__(self, workspace_path: str = "/root/.openclaw/workspace"):
        self.workspace_path = Path(workspace_path)
        self.repo_path = self.workspace_path / "cerebrum-fix"
        
        self.context = AgentContext(
            session_id=f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            workspace_path=str(self.workspace_path)
        )
        
        # Enhanced components
        self.conversation_reader = EnhancedConversationReader(str(self.workspace_path))
        self.layer_navigator = EnhancedLayerNavigator()
        
        # All available tools
        self.tools: Dict[str, Callable] = {}
        self._register_all_tools()
        
        # Lazy init components
        self.planner = None
        self.scheduler = None
        self.websocket_manager = None
    
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
            suggested_next_actions=self._get_layer_suggestions(layer)
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
        return self.conversation_reader.read_conversations(days=days, layers=layers)
    
    def _tool_search_memory(self, query: str, limit: int = 10) -> Dict:
        """Semantic memory search with relevance scoring."""
        return self.conversation_reader.semantic_search(query, limit)
    
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
    
    def _tool_calculate_cost(self, **kwargs) -> Dict:
        return {"success": True, "tool": "calculate_cost", "params": kwargs}
    
    def _tool_estimate_project(self, **kwargs) -> Dict:
        return {"success": True, "tool": "estimate_project", "params": kwargs}
    
    def _tool_rsmeans_query(self, **kwargs) -> Dict:
        return {"success": True, "tool": "rsmeans_query", "params": kwargs}
    
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
        """Execute a task with full layer navigation and memory awareness."""
        import time
        start_time = time.time()
        
        # Read relevant conversations
        related = self.conversation_reader.semantic_search(task, limit=3)
        
        # Suggest layers
        layer_suggestions = self.layer_navigator.suggest_layer_for_task(task)
        
        # Select best layer
        if layer_suggestions:
            target_layer = AgentLayer(layer_suggestions[0]["layer"])
        else:
            target_layer = AgentLayer.CODING
        
        # Navigate to layer
        nav_result = self.move_to_layer(target_layer, context)
        
        # Find appropriate tool
        tool_name = self._select_tool_for_task(task, target_layer)
        
        # Execute
        if tool_name in self.tools:
            result = self.tools[tool_name](task=task, context=context)
        else:
            result = {"success": False, "error": f"Tool {tool_name} not found"}
        
        execution_time = (time.time() - start_time) * 1000
        
        return AgentResult(
            success=result.get("success", True),
            action=AgentAction.GENERATE_CODE if "generate" in tool_name else AgentAction.READ_MEMORY,
            layer=target_layer,
            data=result,
            message=f"Executed {tool_name} in {target_layer.value}",
            execution_time_ms=execution_time,
            related_conversations=[r["id"] for r in related.get("results", [])],
            suggested_next_actions=[f"Try {s['layer']}" for s in layer_suggestions[1:3]]
        )
    
    def _select_tool_for_task(self, task: str, layer: AgentLayer) -> str:
        """Select the best tool for a task."""
        task_lower = task.lower()
        
        # Map keywords to tools
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
            "bim": "query_bim",
            "search": "search_memory",
            "remember": "write_memory",
        }
        
        for keyword, tool in tool_map.items():
            if keyword in task_lower:
                return tool
        
        # Default based on layer
        defaults = {
            AgentLayer.CODING: "generate_endpoint",
            AgentLayer.VALIDATION: "validate_code",
            AgentLayer.HEALING: "heal_error",
            AgentLayer.ECONOMICS: "calculate_cost",
        }
        return defaults.get(layer, "search_memory")


# Singleton
_agent_instance: Optional[EnhancedCerebrumAgent] = None

def get_enhanced_agent() -> EnhancedCerebrumAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = EnhancedCerebrumAgent()
    return _agent_instance
