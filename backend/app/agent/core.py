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
    reasoning_content: Optional[str] = field(default=None)
    """Step-by-step reasoning/thinking process (Kimi-style transparent AI reasoning)"""


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
        
        # Initialize planner for multi-step tasks
        self.planner = None  # Lazy init to avoid circular imports
        
        # Initialize scheduler for recurring tasks
        self.scheduler = None  # Lazy init
    
    def _get_planner(self):
        """Get or create the multi-step planner."""
        if self.planner is None:
            from app.agent.planner import MultiStepPlanner
            self.planner = MultiStepPlanner(self.tools)
        return self.planner
    
    def _get_scheduler(self):
        """Get or create the task scheduler."""
        if self.scheduler is None:
            from app.agent.scheduler import AgentScheduler
            self.scheduler = AgentScheduler(self)
        return self.scheduler
    
    # ============ Layer Navigation ============
    
    def move_to_layer(self, layer: AgentLayer) -> AgentResult:
        """Move the agent to a specific layer."""
        old_layer = self.context.current_layer
        self.context.current_layer = layer
        
        # Track layer in history for persistence
        self.context.conversation_history.append({
            "action": "layer_change",
            "from_layer": old_layer.value,
            "to_layer": layer.value,
            "timestamp": datetime.now().isoformat()
        })
        
        return AgentResult(
            success=True,
            action=AgentAction.READ_MEMORY,
            layer=layer,
            data={"previous_layer": old_layer.value, "current_layer": layer.value},
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
            scan_result = scanner.scan(code, language=code_type)
            
            # Convert SecurityIssue objects to dicts for JSON serialization
            violations = [
                {
                    "tool": issue.tool,
                    "rule_id": issue.rule_id,
                    "message": issue.message,
                    "severity": issue.severity.value,
                    "line": issue.line,
                    "column": issue.column,
                    "file": issue.file,
                    "code_snippet": issue.code_snippet,
                    "remediation": issue.remediation
                }
                for issue in scan_result.issues
            ]
            
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
                "passed": scan_result.passed and syntax_valid
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
    
    def _is_conversation_query(self, task: str) -> bool:
        """Check if the task is a conversational greeting/query."""
        conversation_keywords = ['hello', 'hi', 'hey', 'greetings', 'what can you do',
                                'who are you', 'help', 'what do you do', 'thanks', 'thank you']
        task_lower = task.lower().strip()
        
        # Check for conversation keywords
        if any(kw in task_lower for kw in conversation_keywords):
            return True
        
        # Check if input is too vague/short to be a meaningful task
        if len(task_lower) < 10 or task_lower in ['hi', 'hello', 'hey', 'help', 'ok', 'okay', 'test']:
            return True
        
        return False

    def _generate_conversation_response(self, task: str) -> str:
        """Generate a conversational response for greetings and general queries."""
        task_lower = task.lower()
        
        if any(g in task_lower for g in ['hello', 'hi', 'hey', 'greetings']):
            return """👋 Hello! I'm Cerebrum AI Agent, your autonomous construction intelligence assistant.

I'm currently operating with access to 14 specialized layers:

**🛠️ Development Layers:**
• Coding - Generate code, endpoints, components
• Registry - Manage capabilities and modules
• Validation - Code validation, security scans
• Hotswap - Deploy and hot-reload modules

**🏗️ Construction Layers:**
• Economics - RSMeans, cost estimation, BOQ generation
• VDC - BIM queries, clash detection, quantity extraction
• Portal - Project management, reporting

**🔧 Operations Layers:**
• Edge - Device management, model deployment
• Enterprise - Authentication, security audit
• Monitoring - Logging, metrics, alerts

**What would you like me to help you with today?** Try:
• "Generate an API endpoint for material tracking"
• "Calculate concrete costs for a foundation"
• "Query BIM model for wall quantities"
• Type `/agent help` for all commands"""

        if any(h in task_lower for h in ['what can you do', 'who are you', 'help', 'capabilities']):
            return """🧠 **I'm the Cerebrum AI Agent** — an autonomous assistant with self-modification capabilities.

**I can help you with:**

**💻 Code & Development:**
• Generate API endpoints, React components, data models
• Refactor and optimize existing code
• Run security scans and validate code
• Self-modify to add new features

**🏗️ Construction & Cost:**
• Query RSMeans for material costs
• Calculate project estimates
• Generate Bills of Quantities (BOQ)
• Run construction formulas

**📊 Document & BIM:**
• Analyze uploaded documents
• Query BIM models for quantities
• Check for design clashes
• Generate reports

**Try:** `/agent layers` to see all available layers and tools!

Or just tell me what you need — I'll route to the right layer automatically."""

        if any(t in task_lower for t in ['thanks', 'thank you']):
            return "You're welcome! 🎉 Let me know if you need anything else."
        
        return f"""I understand you're asking about: "{task}"

I'm Cerebrum AI Agent with access to 14 specialized layers for construction and development tasks.

**Try asking me to:**
• Generate code or APIs
• Calculate construction costs
• Analyze documents or BIM models
• Search through your conversation history

Type `/agent help` for all available commands, or just tell me what you need!"""

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
        
        # Step 1: Check if this is a conversational greeting/query
        if self._is_conversation_query(task):
            return AgentResult(
                success=True,
                action=AgentAction.READ_CONVERSATION,
                layer=AgentLayer.PORTAL,
                data={"type": "conversation", "query": task},
                message=self._generate_conversation_response(task)
            )
        
        # Step 2: Read conversation context
        conversation = self._tool_read_conversation()
        self.context.conversation_history.append({
            "task": task,
            "timestamp": datetime.now().isoformat()
        })
        
        # Step 3: Determine which layer and tool to use
        layer, tool_name, params = self._parse_task(task)
        
        # Step 4: Move to appropriate layer
        self.move_to_layer(layer)
        
        # Step 5: Execute the tool
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
        
        # Check for healing tasks
        if any(word in task_lower for word in ["heal", "fix", "repair", "error"]):
            return AgentLayer.HEALING, "heal_error", {
                "error_logs": task,
                "capability_name": "unknown"
            }
        
        # Check for cost/economics tasks
        if any(word in task_lower for word in ["cost", "price", "estimate", "calculate", "budget", "rsmeans"]):
            return AgentLayer.ECONOMICS, "search_memory", {"query": task}
        
        # Check for BIM/VDC tasks
        if any(word in task_lower for word in ["bim", "model", "clash", "quantity", "ifc", "vdc"]):
            return AgentLayer.VDC, "query_bim", {"query": task}
        
        # Default: search memory (not read_conversation - avoid loops)
        return AgentLayer.REGISTRY, "search_memory", {"query": task[:50]}
    
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
            "generated_artifacts": self.context.generated_artifacts,
            "layer_history": [entry for entry in self.context.conversation_history if entry.get("action") == "layer_change"][-10:]
        }
    
    # ============ Multi-Step Planning ============
    
    async def create_plan(self, goal: str, context: Optional[Dict] = None) -> Dict:
        """Create a multi-step execution plan."""
        planner = self._get_planner()
        plan = planner.create_plan(goal, context)
        return plan.to_dict()
    
    async def execute_plan(self, plan_id: str) -> Dict:
        """Execute a multi-step plan."""
        planner = self._get_planner()
        plan = await planner.execute_plan(plan_id, self)
        return plan.to_dict()
    
    async def run_with_plan(self, goal: str, context: Optional[Dict] = None) -> Dict:
        """Create and execute a plan in one call."""
        planner = self._get_planner()
        plan = planner.create_plan(goal, context)
        completed_plan = await planner.execute_plan(plan.id, self)
        return completed_plan.to_dict()
    
    # ============ Task Scheduling ============
    
    async def start_scheduler(self):
        """Start the task scheduler."""
        scheduler = self._get_scheduler()
        await scheduler.start()
    
    async def stop_scheduler(self):
        """Stop the task scheduler."""
        if self.scheduler:
            await self.scheduler.stop()
    
    def schedule_task(self, name: str, description: str, task_template: str,
                     schedule_type: str, schedule_config: Dict,
                     max_runs: Optional[int] = None) -> Dict:
        """Schedule a recurring task."""
        scheduler = self._get_scheduler()
        task = scheduler.create_task(
            name=name,
            description=description,
            task_template=task_template,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            max_runs=max_runs
        )
        return task.to_dict()
    
    def list_scheduled_tasks(self) -> List[Dict]:
        """List all scheduled tasks."""
        scheduler = self._get_scheduler()
        return scheduler.list_tasks()
    
    def cancel_scheduled_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        scheduler = self._get_scheduler()
        return scheduler.delete_task(task_id)
    
    # ============ Working Memory (Redis State Store) ============
    
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
        ttl_seconds: int = 3600  # 1 hour default
    ) -> bool:
        """
        Save agent working memory to Redis.
        
        This allows the agent to resume mid-task without repeating steps.
        """
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
            
            if success:
                logger.info(f"Saved working memory for task: {task_description[:50]}...")
            
            return success
            
        except Exception as e:
            logger.warning(f"Failed to save working memory: {e}")
            return False
    
    async def load_working_memory(self, task_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load agent working memory from Redis.
        
        Returns None if no working memory exists or it has expired.
        """
        try:
            from app.services.redis_state_store import RedisStateStore
            
            store = RedisStateStore()
            await store.connect()
            
            key = self._get_working_memory_key(task_id)
            memory_data = await store.get_session_data(key)
            
            await store.disconnect()
            
            if memory_data:
                # Restore layer state if available
                if "current_layer" in memory_data:
                    layer_name = memory_data["current_layer"]
                    try:
                        self.context.current_layer = AgentLayer(layer_name)
                    except ValueError:
                        pass  # Invalid layer name, ignore
                
                logger.info(f"Loaded working memory with {len(memory_data.get('steps_completed', []))} steps completed")
            
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
            # Set empty data with short TTL to effectively clear
            success = await store.set_session_data(key, {"status": "completed"}, 60)
            
            await store.disconnect()
            
            if success:
                logger.info(f"Cleared working memory for key: {key}")
            
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
        """
        Checkpoint progress during a multi-step task.
        
        Call this after completing each significant step.
        """
        # Load existing memory
        existing = await self.load_working_memory(task_id) or {}
        
        # Update with new progress
        steps_completed = existing.get("steps_completed", [])
        if step_name not in steps_completed:
            steps_completed.append(step_name)
        
        intermediate_results = existing.get("intermediate_results", {})
        intermediate_results[step_name] = step_result
        intermediate_results["last_checkpoint"] = datetime.now().isoformat()
        
        # Preserve original start time
        if "started_at" not in intermediate_results:
            intermediate_results["started_at"] = datetime.now().isoformat()
        
        return await self.save_working_memory(
            task_description=task_description,
            steps_completed=steps_completed,
            steps_remaining=remaining_steps,
            intermediate_results=intermediate_results,
            task_id=task_id
        )
    
    async def run_with_memory(
        self,
        task: str,
        steps: List[str],
        task_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> AgentResult:
        """
        Execute a multi-step task with working memory.
        
        Resumes from last checkpoint if available.
        """
        # Check for existing working memory
        memory = await self.load_working_memory(task_id)
        
        if memory:
            completed = memory.get("steps_completed", [])
            remaining = memory.get("steps_remaining", [])
            results = memory.get("intermediate_results", {})
            
            logger.info(f"Resuming task with {len(completed)} steps already completed")
            
            # Resume from where we left off
            for step in remaining[:]:
                try:
                    result = await self._execute_step(step, context)
                    results[step] = result
                    completed.append(step)
                    remaining.remove(step)
                    
                    # Checkpoint after each step
                    await self.checkpoint(step, result, task, remaining, task_id)
                    
                except Exception as e:
                    logger.error(f"Step failed: {step}, error: {e}")
                    return AgentResult(
                        success=False,
                        action=AgentAction.READ_CONVERSATION,
                        layer=self.context.current_layer,
                        data={"completed_steps": completed, "failed_step": step, "error": str(e)},
                        message=f"Task failed at step: {step}"
                    )
            
            # Clear working memory on success
            await self.clear_working_memory(task_id)
            
            return AgentResult(
                success=True,
                action=AgentAction.READ_CONVERSATION,
                layer=self.context.current_layer,
                data={"steps_completed": completed, "results": results},
                message=f"Task completed successfully (resumed from checkpoint)"
            )
        
        else:
            # Fresh start
            remaining = steps[:]
            completed = []
            results = {}
            
            for step in remaining[:]:
                try:
                    result = await self._execute_step(step, context)
                    results[step] = result
                    completed.append(step)
                    remaining.remove(step)
                    
                    # Checkpoint after each step
                    await self.checkpoint(step, result, task, remaining, task_id)
                    
                except Exception as e:
                    logger.error(f"Step failed: {step}, error: {e}")
                    return AgentResult(
                        success=False,
                        action=AgentAction.READ_CONVERSATION,
                        layer=self.context.current_layer,
                        data={"completed_steps": completed, "failed_step": step, "error": str(e)},
                        message=f"Task failed at step: {step}"
                    )
            
            # Clear working memory on success
            await self.clear_working_memory(task_id)
            
            return AgentResult(
                success=True,
                action=AgentAction.READ_CONVERSATION,
                layer=self.context.current_layer,
                data={"steps_completed": completed, "results": results},
                message=f"Task completed successfully"
            )
    
    async def _execute_step(self, step: str, context: Optional[Dict] = None) -> Any:
        """Execute a single step (override in subclasses for custom logic)."""
        # Default implementation uses the standard run method
        result = await self.run(step, context)
        return result.data if result.success else {"error": result.message}


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
