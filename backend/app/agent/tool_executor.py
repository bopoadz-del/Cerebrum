"""
Enhanced Tool Executor with Local LLM
Phase 4.2: Intelligent tool execution and result interpretation
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import traceback

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger(__name__)


class ToolResultStatus(Enum):
    """Status of tool execution."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    RETRY = "retry"


@dataclass
class ToolResult:
    """Result of tool execution."""
    tool_name: str
    status: ToolResultStatus
    data: Any = None
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "status": self.status.value,
            "data": self.data,
            "error_message": self.error_message,
            "execution_time": self.execution_time,
            "metadata": self.metadata
        }


@dataclass
class ToolContext:
    """Context for tool execution."""
    conversation_history: List[Dict] = field(default_factory=list)
    memory_search_results: List[Dict] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    session_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_history": self.conversation_history,
            "memory_search_results": self.memory_search_results,
            "user_preferences": self.user_preferences,
            "session_data": self.session_data
        }


class ToolExecutor:
    """
    Execute tools with error handling, retries, and result interpretation.
    """
    
    def __init__(self, tools: Dict[str, Callable]):
        self.tools = tools
        self.execution_history: List[ToolResult] = []
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Optional[ToolContext] = None
    ) -> ToolResult:
        """
        Execute a tool with error handling and retries.
        
        Args:
            tool_name: Name of the tool to execute
            params: Tool parameters
            context: Execution context
        
        Returns:
            ToolResult with status and data
        """
        import time
        start_time = time.time()
        
        tool_func = self.tools.get(tool_name)
        if not tool_func:
            return ToolResult(
                tool_name=tool_name,
                status=ToolResultStatus.ERROR,
                error_message=f"Tool '{tool_name}' not found",
                execution_time=time.time() - start_time
            )
        
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                # Execute tool
                if asyncio.iscoroutinefunction(tool_func):
                    result = await tool_func(**params)
                else:
                    result = tool_func(**params)
                
                execution_time = time.time() - start_time
                
                tool_result = ToolResult(
                    tool_name=tool_name,
                    status=ToolResultStatus.SUCCESS,
                    data=result,
                    execution_time=execution_time,
                    metadata={"retries": retries}
                )
                
                self.execution_history.append(tool_result)
                return tool_result
                
            except Exception as e:
                last_error = e
                retries += 1
                
                if retries <= self.max_retries:
                    logger.warning(f"Tool {tool_name} failed (attempt {retries}), retrying...: {e}")
                    await asyncio.sleep(self.retry_delay * retries)
                else:
                    logger.error(f"Tool {tool_name} failed after {self.max_retries} retries: {e}")
        
        # All retries exhausted
        execution_time = time.time() - start_time
        
        tool_result = ToolResult(
            tool_name=tool_name,
            status=ToolResultStatus.ERROR,
            error_message=str(last_error),
            execution_time=execution_time,
            metadata={
                "retries": retries,
                "traceback": traceback.format_exc()
            }
        )
        
        self.execution_history.append(tool_result)
        return tool_result
    
    async def execute_batch(
        self,
        tool_calls: List[Dict[str, Any]],
        context: Optional[ToolContext] = None
    ) -> List[ToolResult]:
        """
        Execute multiple tools in parallel.
        
        Args:
            tool_calls: List of {"tool": name, "params": {}}
            context: Execution context
        
        Returns:
            List of ToolResults
        """
        tasks = [
            self.execute(call["tool"], call.get("params", {}), context)
            for call in tool_calls
        ]
        
        return await asyncio.gather(*tasks)


class LLMResultInterpreter:
    """
    Use local LLM to interpret tool results and suggest next actions.
    """
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    
    INTERPRETATION_PROMPT = """You are analyzing tool execution results for a construction management AI.

Tool Executed: {tool_name}
Parameters: {params}
Result Status: {status}
Result Data: {data}
Error (if any): {error}

Task Context:
{context}

Provide analysis in JSON format:
{{
  "success": true/false,
  "key_findings": ["finding 1", "finding 2"],
  "data_quality": "high/medium/low",
  "suggested_actions": ["action 1", "action 2"],
  "confidence": 0.0_to_1.0,
  "explanation": "brief explanation of what was accomplished"
}}"""

    def __init__(self, model: str = "gemma3:270m"):
        self.model = model
    
    async def interpret_result(
        self,
        result: ToolResult,
        params: Dict[str, Any],
        context: Optional[ToolContext] = None
    ) -> Dict[str, Any]:
        """
        Interpret a tool result using LLM.
        
        Args:
            result: The tool execution result
            params: Original parameters
            context: Execution context
        
        Returns:
            Interpretation with findings and suggestions
        """
        if not AIOHTTP_AVAILABLE:
            return {"error": "aiohttp not available"}
        
        try:
            context_str = json.dumps(context.to_dict() if context else {}, indent=2, default=str)[:1000]
            
            prompt = self.INTERPRETATION_PROMPT.format(
                tool_name=result.tool_name,
                params=json.dumps(params),
                status=result.status.value,
                data=json.dumps(result.data, default=str)[:2000],
                error=result.error_message or "None",
                context=context_str
            )
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.2,
                    "format": "json"
                }
                
                async with session.post(self.OLLAMA_API_URL, json=payload) as resp:
                    if resp.status == 200:
                        llm_result = await resp.json()
                        interpretation = json.loads(llm_result.get("response", "{}"))
                        return interpretation
                    else:
                        return {"error": f"Ollama API error: {resp.status}"}
                        
        except Exception as e:
            logger.error(f"Result interpretation failed: {e}")
            return {"error": str(e)}


class SmartToolSelector:
    """
    Use LLM to select the best tool for a task.
    """
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    
    SELECTION_PROMPT = """Select the best tool for this task.

Available Tools:
{tools}

Task: {task}
Context: {context}

Respond with ONLY this JSON:
{{
  "selected_tool": "tool_name",
  "confidence": 0.0_to_1.0,
  "reasoning": "why this tool was selected",
  "suggested_params": {{"param1": "value1"}}
}}"""

    def __init__(self, model: str = "gemma3:270m"):
        self.model = model
    
    async def select_tool(
        self,
        task: str,
        available_tools: Dict[str, str],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Select the best tool for a task.
        
        Args:
            task: Description of what needs to be done
            available_tools: Dict of tool_name -> description
            context: Additional context
        
        Returns:
            Selection result with tool name and parameters
        """
        if not AIOHTTP_AVAILABLE:
            return {"error": "aiohttp not available"}
        
        try:
            tools_str = json.dumps(available_tools, indent=2)
            
            prompt = self.SELECTION_PROMPT.format(
                tools=tools_str,
                task=task,
                context=context or "None"
            )
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,
                    "format": "json"
                }
                
                async with session.post(self.OLLAMA_API_URL, json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        selection = json.loads(result.get("response", "{}"))
                        return selection
                    else:
                        return {"error": f"Ollama API error: {resp.status}"}
                        
        except Exception as e:
            logger.error(f"Tool selection failed: {e}")
            return {"error": str(e)}


class EnhancedToolExecutor:
    """
    Enhanced tool executor combining execution, interpretation, and selection.
    """
    
    def __init__(self, tools: Dict[str, Callable], model: str = "gemma3:270m"):
        self.executor = ToolExecutor(tools)
        self.interpreter = LLMResultInterpreter(model)
        self.selector = SmartToolSelector(model)
        self.tools = tools
    
    async def execute_with_interpretation(
        self,
        tool_name: str,
        params: Dict[str, Any],
        context: Optional[ToolContext] = None
    ) -> Dict[str, Any]:
        """
        Execute tool and interpret results.
        
        Args:
            tool_name: Tool to execute
            params: Tool parameters
            context: Execution context
        
        Returns:
            Combined result with execution and interpretation
        """
        # Execute
        result = await self.executor.execute(tool_name, params, context)
        
        # Interpret
        interpretation = await self.interpreter.interpret_result(result, params, context)
        
        return {
            "execution": result.to_dict(),
            "interpretation": interpretation,
            "tool_name": tool_name,
            "params": params
        }
    
    async def smart_execute(
        self,
        task: str,
        context: Optional[ToolContext] = None
    ) -> Dict[str, Any]:
        """
        Select and execute the best tool for a task.
        
        Args:
            task: Natural language task description
            context: Execution context
        
        Returns:
            Full execution result with interpretation
        """
        # Build tool descriptions
        tool_descriptions = {}
        for name, func in self.tools.items():
            tool_descriptions[name] = func.__doc__ or name
        
        # Select tool
        selection = await self.selector.select_tool(task, tool_descriptions)
        
        if "error" in selection:
            return {"error": selection["error"], "task": task}
        
        tool_name = selection.get("selected_tool")
        params = selection.get("suggested_params", {})
        
        if not tool_name or tool_name not in self.tools:
            return {"error": f"Invalid tool selected: {tool_name}", "task": task}
        
        # Execute with interpretation
        return await self.execute_with_interpretation(tool_name, params, context)


# Convenience functions
async def execute_tool(
    tool_name: str,
    params: Dict[str, Any],
    tools: Dict[str, Callable]
) -> ToolResult:
    """Execute a single tool."""
    executor = ToolExecutor(tools)
    return await executor.execute(tool_name, params)


async def smart_execute(
    task: str,
    tools: Dict[str, Callable],
    model: str = "gemma3:270m"
) -> Dict[str, Any]:
    """Smart tool selection and execution."""
    executor = EnhancedToolExecutor(tools, model)
    return await executor.smart_execute(task)
