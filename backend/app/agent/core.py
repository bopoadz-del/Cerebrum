"""
Cerebrum Agent - Autonomous AI Agent for Construction Intelligence

This agent integrates with the 14-layer Cerebrum architecture to:
- Move between layers (coding, registry, validation, healing, etc.)
- Use self-coding capabilities (Kimi Code)
- Read current and past conversations
- Generate, validate, and deploy code autonomously
"""

import json
import os
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AgentLayer(Enum):
    """The 14 layers of Cerebrum architecture the agent can navigate."""
    CODING = "coding"                    # Self-coding generation
    REGISTRY = "registry"                # Capability registry
    VALIDATION = "validation"            # Security & testing
    HOTSWAP = "hotswap"                  # Dynamic deployment
    HEALING = "healing"                  # Self-healing
    PROMPTS = "prompts"                  # Prompt management
    TRIGGERS = "triggers"                # Event triggers
    ECONOMICS = "economics"              # Cost estimation
    VDC = "vdc"                          # Virtual design
    EDGE = "edge"                        # Edge inference
    PORTAL = "portal"                    # User portal
    ENTERPRISE = "enterprise"            # Security/auth
    CONNECTORS = "connectors"            # External integrations
    MONITORING = "monitoring"            # Observability


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


@dataclass
class AgentContext:
    """Context for the agent's current operation."""
    session_id: str
    conversation_history: List[Dict] = field(default_factory=list)
    current_layer: AgentLayer = AgentLayer.CODING
    memory_references: List[str] = field(default_factory=list)
    generated_artifacts: List[str] = field(default_factory=list)
    workspace_path: str = "/root/.openclaw/workspace"


@dataclass
class AgentResult:
    """Result of an agent action."""
    success: bool
    action: AgentAction
    layer: AgentLayer
    data: Dict[str, Any]
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ConversationReader:
    """
    Reads current and past conversations from memory files.
    """
    
    def __init__(self, workspace_path: str = "/root/.openclaw/workspace"):
        self.workspace_path = Path(workspace_path)
        self.memory_path = self.workspace_path / "memory"
        
    def read_current_conversation(self, session_key: Optional[str] = None) -> List[Dict]:
        """
        Read the current conversation context.
        
        In production, this integrates with OpenClaw's session system.
        For now, reads from memory files.
        """
        # Look for recent memory files
        if not self.memory_path.exists():
            return []
            
        conversations = []
        
        # Read today's memory file if exists
        today_file = self.memory_path / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        if today_file.exists():
            content = today_file.read_text()
            conversations.append({
                "date": datetime.now().strftime('%Y-%m-%d'),
                "content": content,
                "source": str(today_file)
            })
        
        # Read yesterday's memory file
        from datetime import timedelta
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_file = self.memory_path / f"{yesterday}.md"
        if yesterday_file.exists():
            content = yesterday_file.read_text()
            conversations.append({
                "date": yesterday,
                "content": content,
                "source": str(yesterday_file)
            })
        
        return conversations
    
    def read_memory_md(self) -> Dict:
        """Read the main MEMORY.md file."""
        memory_file = self.workspace_path / "MEMORY.md"
        if memory_file.exists():
            return {
                "content": memory_file.read_text(),
                "source": str(memory_file),
                "last_modified": datetime.fromtimestamp(
                    memory_file.stat().st_mtime
                ).isoformat()
            }
        return {}
    
    def search_conversations(self, query: str, limit: int = 5) -> List[Dict]:
        """Search through all memory files for relevant conversations."""
        results = []
        
        if not self.memory_path.exists():
            return results
        
        # Search in memory files
        for memory_file in self.memory_path.glob("*.md"):
            content = memory_file.read_text()
            if query.lower() in content.lower():
                # Find context around the query
                idx = content.lower().find(query.lower())
                context_start = max(0, idx - 200)
                context_end = min(len(content), idx + 200)
                context = content[context_start:context_end]
                
                results.append({
                    "file": str(memory_file.name),
                    "context": context,
                    "match_count": content.lower().count(query.lower())
                })
        
        # Also search MEMORY.md
        memory_file = self.workspace_path / "MEMORY.md"
        if memory_file.exists():
            content = memory_file.read_text()
            if query.lower() in content.lower():
                results.append({
                    "file": "MEMORY.md",
                    "context": content[:500],
                    "match_count": content.lower().count(query.lower())
                })
        
        return sorted(results, key=lambda x: x["match_count"], reverse=True)[:limit]


class CerebrumAgent:
    """
    The main agent that navigates Cerebrum's 14 layers.
    
    Capabilities:
    - Self-coding using existing Kimi Code infrastructure
    - Layer navigation (move between coding, registry, validation, etc.)
    - Conversation reading and memory access
    - Autonomous task execution
    """
    
    def __init__(self, workspace_path: str = "/root/.openclaw/workspace"):
        self.workspace_path = Path(workspace_path)
        self.repo_path = self.workspace_path / "cerebrum-fix"
        self.context = AgentContext(
            session_id=f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            workspace_path=str(self.workspace_path)
        )
        self.conversation_reader = ConversationReader(str(self.workspace_path))
        
        # Layer handlers - will be initialized lazily
        self._layer_handlers: Dict[AgentLayer, Any] = {}
        self._coding_generator = None
        self._registry = None
        
        # Register available tools
        self.tools: Dict[str, Callable] = {
            "generate_endpoint": self._tool_generate_endpoint,
            "generate_component": self._tool_generate_component,
            "validate_code": self._tool_validate_code,
            "deploy_capability": self._tool_deploy_capability,
            "read_conversation": self._tool_read_conversation,
            "search_memory": self._tool_search_memory,
            "write_memory": self._tool_write_memory,
            "heal_error": self._tool_heal_error,
            "execute_sandbox": self._tool_execute_sandbox,
        }
    
    # ============ Layer Navigation ============
    
    def move_to_layer(self, layer: AgentLayer) -> AgentResult:
        """Move the agent to a specific layer."""
        old_layer = self.context.current_layer
        self.context.current_layer = layer
        
        return AgentResult(
            success=True,
            action=AgentAction.READ_MEMORY,
            layer=layer,
            data={"previous_layer": old_layer.value},
            message=f"Moved from {old_layer.value} to {layer.value}"
        )
    
    def get_current_layer(self) -> AgentLayer:
        """Get the current layer."""
        return self.context.current_layer
    
    # ============ Conversation & Memory Tools ============
    
    def _tool_read_conversation(self, days: int = 2) -> Dict:
        """Read recent conversations from memory files."""
        conversations = self.conversation_reader.read_current_conversation()
        memory = self.conversation_reader.read_memory_md()
        
        return {
            "recent_conversations": conversations,
            "memory_md": memory,
            "session_id": self.context.session_id
        }
    
    def _tool_search_memory(self, query: str, limit: int = 5) -> Dict:
        """Search through memory for specific information."""
        results = self.conversation_reader.search_conversations(query, limit)
        return {
            "query": query,
            "results": results,
            "total_matches": len(results)
        }
    
    def _tool_write_memory(self, content: str, memory_file: Optional[str] = None) -> Dict:
        """Write to MEMORY.md or a specific memory file."""
        try:
            if memory_file:
                file_path = self.workspace_path / "memory" / memory_file
            else:
                file_path = self.workspace_path / "MEMORY.md"
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Append with timestamp
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            entry = f"\n\n## Agent Entry [{timestamp}]\n\n{content}\n"
            
            with open(file_path, 'a') as f:
                f.write(entry)
            
            return {
                "success": True,
                "file": str(file_path),
                "timestamp": timestamp
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============ Code Generation Tools ============
    
    def _tool_generate_endpoint(self, 
                                 description: str, 
                                 model_name: str,
                                 fields: List[Dict],
                                 operations: List[str] = None) -> Dict:
        """Generate a FastAPI endpoint using the coding system."""
        try:
            # Import here to avoid circular dependencies
            from app.coding.generator import CodeGenerator
            
            generator = CodeGenerator()
            
            # Use existing generation system
            result = asyncio.run(generator.generate_endpoint(
                feature_description=description,
                model_name=model_name,
                fields=fields,
                operations=operations or ["create", "read", "update", "delete", "list"]
            ))
            
            return {
                "success": result.success,
                "code": result.code,
                "language": result.language,
                "metadata": result.metadata,
                "errors": result.errors
            }
        except Exception as e:
            logger.error(f"Endpoint generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _tool_generate_component(self,
                                  description: str,
                                  component_name: str,
                                  props: List[Dict] = None) -> Dict:
        """Generate a React component."""
        try:
            from app.coding.generator import CodeGenerator
            
            generator = CodeGenerator()
            result = asyncio.run(generator.generate_component(
                feature_description=description,
                component_name=component_name,
                props=props or []
            ))
            
            return {
                "success": result.success,
                "code": result.code,
                "language": result.language,
                "metadata": result.metadata
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============ Validation & Deployment Tools ============
    
    def _tool_validate_code(self, code: str, code_type: str = "python") -> Dict:
        """Validate code for security and syntax issues."""
        try:
            from app.validation.security_scan import SecurityScanner
            
            scanner = SecurityScanner()
            violations = scanner.scan_code(code)
            
            # Basic syntax check
            syntax_valid = True
            syntax_error = None
            if code_type == "python":
                try:
                    compile(code, '<string>', 'exec')
                except SyntaxError as e:
                    syntax_valid = False
                    syntax_error = str(e)
            
            return {
                "security_violations": violations,
                "syntax_valid": syntax_valid,
                "syntax_error": syntax_error,
                "passed": len(violations) == 0 and syntax_valid
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _tool_deploy_capability(self, 
                                 name: str,
                                 code: str,
                                 route_path: str,
                                 route_methods: List[str]) -> Dict:
        """Deploy a capability through the registry."""
        try:
            from app.registry.models import CapabilityCreate, CapabilityType
            from app.registry.crud import create_capability
            
            capability_data = CapabilityCreate(
                name=name,
                version="1.0.0",
                capability_type=CapabilityType.ENDPOINT,
                description=f"Auto-generated {name} endpoint",
                code_content=code,
                route_path=route_path,
                route_methods=route_methods
            )
            
            return {
                "success": True,
                "capability": capability_data.dict(),
                "message": f"Capability {name} ready for deployment"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _tool_heal_error(self, error_logs: str, capability_name: str) -> Dict:
        """Analyze error and suggest healing actions."""
        try:
            from app.healing.error_detection import ErrorDetector
            
            detector = ErrorDetector()
            incidents = asyncio.run(detector.scan_logs(error_logs))
            
            return {
                "incidents_detected": len(incidents),
                "incidents": [inc.dict() if hasattr(inc, 'dict') else str(inc) for inc in incidents],
                "suggested_actions": self._suggest_healing_actions(incidents)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _suggest_healing_actions(self, incidents: List) -> List[str]:
        """Suggest healing actions based on incidents."""
        actions = []
        for incident in incidents:
            if "ZeroDivisionError" in str(incident):
                actions.append("Add input validation to prevent division by zero")
            if "ConnectionError" in str(incident):
                actions.append("Implement retry logic with exponential backoff")
            if "KeyError" in str(incident):
                actions.append("Add null checks before accessing dictionary keys")
        return actions
    
    def _tool_execute_sandbox(self, code: str, timeout: int = 30) -> Dict:
        """Execute code in a sandboxed environment."""
        try:
            from app.validation.sandbox import DockerSandbox, SandboxConfig
            
            config = SandboxConfig(
                timeout_seconds=timeout,
                memory_limit_mb=512,
                network_disabled=True
            )
            
            sandbox = DockerSandbox(config)
            result = asyncio.run(sandbox.execute(code))
            
            return {
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "execution_time": result.execution_time
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============ Main Agent Loop ============
    
    async def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        """
        Main agent execution loop.
        
        Args:
            task: The task description
            context: Additional context
            
        Returns:
            AgentResult with the outcome
        """
        logger.info(f"Agent running task: {task}")
        
        # Step 1: Read conversation context
        conversation = self._tool_read_conversation()
        self.context.conversation_history.append({
            "task": task,
            "timestamp": datetime.now().isoformat()
        })
        
        # Step 2: Determine which layer and tool to use
        layer, tool_name, params = self._parse_task(task)
        
        # Step 3: Move to appropriate layer
        self.move_to_layer(layer)
        
        # Step 4: Execute the tool
        if tool_name in self.tools:
            try:
                result = self.tools[tool_name](**params)
                return AgentResult(
                    success=result.get("success", True),
                    action=self._get_action_from_tool(tool_name),
                    layer=layer,
                    data=result,
                    message=f"Executed {tool_name} successfully"
                )
            except Exception as e:
                return AgentResult(
                    success=False,
                    action=self._get_action_from_tool(tool_name),
                    layer=layer,
                    data={"error": str(e)},
                    message=f"Failed to execute {tool_name}: {str(e)}"
                )
        else:
            return AgentResult(
                success=False,
                action=AgentAction.READ_CONVERSATION,
                layer=layer,
                data={},
                message=f"Unknown tool: {tool_name}"
            )
    
    def _parse_task(self, task: str) -> Tuple[AgentLayer, str, Dict]:
        """Parse a natural language task into layer, tool, and parameters."""
        task_lower = task.lower()
        
        # Check for code generation tasks
        if any(word in task_lower for word in ["generate", "create", "build", "write"]):
            if "endpoint" in task_lower or "api" in task_lower:
                return AgentLayer.CODING, "generate_endpoint", {
                    "description": task,
                    "model_name": self._extract_model_name(task) or "Item",
                    "fields": self._extract_fields(task) or [
                        {"name": "id", "type": "int", "required": True},
                        {"name": "name", "type": "str", "required": True}
                    ]
                }
            elif "component" in task_lower or "react" in task_lower:
                return AgentLayer.CODING, "generate_component", {
                    "description": task,
                    "component_name": self._extract_component_name(task) or "MyComponent"
                }
        
        # Check for validation tasks
        if any(word in task_lower for word in ["validate", "check", "scan"]):
            return AgentLayer.VALIDATION, "validate_code", {
                "code": task,  # Assume task contains code
                "code_type": "python"
            }
        
        # Check for memory/conversation tasks
        if any(word in task_lower for word in ["remember", "recall", "search", "find"]):
            if "conversation" in task_lower:
                return AgentLayer.REGISTRY, "read_conversation", {"days": 2}
            else:
                query = task_lower.replace("search", "").replace("find", "").strip()
                return AgentLayer.REGISTRY, "search_memory", {"query": query}
        
        # Check for healing tasks
        if any(word in task_lower for word in ["heal", "fix", "repair", "error"]):
            return AgentLayer.HEALING, "heal_error", {
                "error_logs": task,
                "capability_name": "unknown"
            }
        
        # Default: read conversation
        return AgentLayer.REGISTRY, "read_conversation", {}
    
    def _extract_model_name(self, task: str) -> Optional[str]:
        """Extract model name from task description."""
        # Look for patterns like "for User" or "User model"
        patterns = [
            r"for\s+(\w+)",
            r"(\w+)\s+model",
            r"(\w+)\s+endpoint"
        ]
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
        return None
    
    def _extract_component_name(self, task: str) -> Optional[str]:
        """Extract component name from task description."""
        patterns = [
            r"component\s+called\s+(\w+)",
            r"named\s+(\w+)",
            r"(\w+)\s+component"
        ]
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_fields(self, task: str) -> Optional[List[Dict]]:
        """Extract field definitions from task description."""
        # This is a simplified extraction - could be enhanced with LLM
        fields = []
        
        # Look for field patterns like "name (str), age (int)"
        field_pattern = r"(\w+)\s*\(\s*(\w+)\s*\)"
        matches = re.findall(field_pattern, task)
        
        for name, type_str in matches:
            fields.append({
                "name": name,
                "type": type_str,
                "required": True
            })
        
        return fields if fields else None
    
    def _get_action_from_tool(self, tool_name: str) -> AgentAction:
        """Map tool name to action enum."""
        mapping = {
            "generate_endpoint": AgentAction.GENERATE_CODE,
            "generate_component": AgentAction.GENERATE_CODE,
            "validate_code": AgentAction.VALIDATE_CODE,
            "deploy_capability": AgentAction.DEPLOY_CODE,
            "read_conversation": AgentAction.READ_CONVERSATION,
            "search_memory": AgentAction.READ_MEMORY,
            "write_memory": AgentAction.WRITE_MEMORY,
            "heal_error": AgentAction.HEAL_ERROR,
            "execute_sandbox": AgentAction.EXECUTE_SANDBOX,
        }
        return mapping.get(tool_name, AgentAction.READ_CONVERSATION)
    
    # ============ Utility Methods ============
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return list(self.tools.keys())
    
    def get_layer_status(self) -> Dict:
        """Get current layer status."""
        return {
            "current_layer": self.context.current_layer.value,
            "session_id": self.context.session_id,
            "available_tools": len(self.tools),
            "conversation_entries": len(self.context.conversation_history),
            "generated_artifacts": self.context.generated_artifacts
        }


# Singleton instance
_agent_instance: Optional[CerebrumAgent] = None


def get_agent() -> CerebrumAgent:
    """Get or create the singleton agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CerebrumAgent()
    return _agent_instance


def reset_agent():
    """Reset the agent instance (useful for testing)."""
    global _agent_instance
    _agent_instance = None
