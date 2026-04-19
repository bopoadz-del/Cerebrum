"""
Cerebrum Agent - Autonomous AI Agent for Construction Intelligence
REAL LLM VERSION - No template responses
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

from app.llm.client import LLMClient
from app.economics.pricing_engine import get_pricing_engine

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


async def call_llm(messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
    """Call REAL DeepSeek LLM - no templates."""
    try:
        client = LLMClient()
        response = await client.chat(
            messages=[{"role": m["role"], "content": m["content"]} for m in messages],
            temperature=temperature,
            max_tokens=2048
        )
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return f"I encountered an error processing your request: {str(e)}"


class ConversationReader:
    """Reads current and past conversations from memory files."""
    
    def __init__(self, workspace_path: str = "/root/.openclaw/workspace"):
        self.workspace_path = Path(workspace_path)
        self.memory_path = self.workspace_path / "memory"
        
    def read_current_conversation(self, session_key: Optional[str] = None) -> List[Dict]:
        """Read the current conversation context."""
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


class CerebrumAgent:
    """The main agent that navigates Cerebrum's 14 layers."""
    
    def __init__(self, workspace_path: str = "/root/.openclaw/workspace"):
        self.workspace_path = Path(workspace_path)
        self.repo_path = self.workspace_path / "cerebrum-fix"
        self.context = AgentContext(
            session_id=f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            workspace_path=str(self.workspace_path)
        )
        self.conversation_reader = ConversationReader(str(self.workspace_path))
        
        self.tools: Dict[str, Callable] = {
            "generate_endpoint": self._tool_generate_endpoint,
            "validate_code": self._tool_validate_code,
            "heal_error": self._tool_heal_error,
            "execute_sandbox": self._tool_execute_sandbox,
        }
    
    def move_to_layer(self, layer: AgentLayer) -> AgentResult:
        """Move the agent to a specific layer."""
        old_layer = self.context.current_layer
        self.context.current_layer = layer
        
        return AgentResult(
            success=True,
            action=AgentAction.READ_MEMORY,
            layer=layer,
            data={"previous_layer": old_layer.value, "current_layer": layer.value},
            message=f"Moved from {old_layer.value} to {layer.value}"
        )
    
    def _tool_generate_endpoint(self, description: str, model_name: str, fields: List[Dict], operations: List[str] = None) -> Dict:
        """Generate a FastAPI endpoint."""
        try:
            from app.coding.generator import CodeGenerator
            generator = CodeGenerator()
            result = asyncio.run(generator.generate_endpoint(
                feature_description=description,
                model_name=model_name,
                fields=fields,
                operations=operations or ["create", "read", "update", "delete", "list"]
            ))
            return {"success": result.success, "code": result.code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _tool_validate_code(self, code: str, code_type: str = "python") -> Dict:
        """Validate code for security and syntax issues."""
        try:
            from app.validation.security_scan import SecurityScanner
            scanner = SecurityScanner()
            scan_result = scanner.scan(code, language=code_type)
            return {"passed": scan_result.passed, "issues": len(scan_result.issues)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _tool_heal_error(self, error_logs: str, capability_name: str) -> Dict:
        """Analyze error and suggest healing actions."""
        return {"success": True, "incidents": 0}  # Stub for now
    
    def _tool_execute_sandbox(self, code: str, timeout: int = 30) -> Dict:
        """Execute code in a sandboxed environment."""
        return {"success": False, "error": "Sandbox not configured"}
    
    async def run(self, task: str, context: Optional[Dict] = None) -> AgentResult:
        """Main agent execution loop - uses REAL LLM."""
        logger.info(f"Agent running task: {task}")
        
        # ALL responses go through LLM - no templates
        system_prompt = """You are Cerebrum AI Agent, an autonomous construction intelligence assistant with access to 14 specialized layers:

CODING - Self-coding generation
REGISTRY - Capability registry  
VALIDATION - Security & testing
HOTSWAP - Dynamic deployment
HEALING - Self-healing
PROMPTS - Prompt management
TRIGGERS - Event triggers
ECONOMICS - Cost estimation (RSMeans data)
VDC - Virtual design & construction (BIM)
EDGE - Edge inference
PORTAL - User portal
ENTERPRISE - Security/auth
CONNECTORS - External integrations
MONITORING - Observability

You have access to real RSMeans construction cost data and can help with code generation, cost estimation, document analysis, and construction workflows. Be helpful, concise, and professional."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        
        # Call REAL LLM
        llm_response = await call_llm(messages)
        
        return AgentResult(
            success=True,
            action=AgentAction.READ_CONVERSATION,
            layer=self.context.current_layer,
            data={"query": task},
            message=llm_response
        )

# Singleton instance
_agent_instance: Optional[CerebrumAgent] = None

def get_agent() -> CerebrumAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = CerebrumAgent()
    return _agent_instance
