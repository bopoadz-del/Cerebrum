"""
Enhanced Task Planner with Local LLM Integration
Phase 4.1: Intelligent task decomposition using Ollama
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from app.agent.planner import MultiStepPlanner, ExecutionPlan, PlanStep, StepStatus, PlanStatus

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

logger = logging.getLogger(__name__)


class LocalLLMPlanner:
    """
    Task planner using local LLM (Ollama) for intelligent task decomposition.
    Enhances the base planner with AI-powered step generation.
    """
    
    OLLAMA_API_URL = "http://localhost:11434/api/generate"
    
    PLANNING_PROMPT = """You are a task planning expert for a construction management AI system.

Break down the following goal into a sequence of executable steps.
Each step should use one of these tools:
- search_memory: Search past conversations and documents
- read_document: Read a specific document
- classify_document: Classify document type
- extract_data: Extract structured data from documents
- generate_report: Generate analysis report
- write_memory: Save findings to memory
- notify_user: Send notification to user
- execute_code: Execute Python code for analysis
- query_database: Query project database
- analyze_costs: Perform cost analysis

Goal: {goal}

Available Context:
{context}

Respond with ONLY a JSON array of steps:
[
  {{
    "id": "step_1",
    "description": "What this step does",
    "tool": "tool_name",
    "params": {{"param1": "value1"}},
    "depends_on": []
  }},
  {{
    "id": "step_2",
    "description": "Next step description",
    "tool": "tool_name",
    "params": {{"param1": "{{step_1.result.value}}"}},
    "depends_on": ["step_1"]
  }}
]

Rules:
- Use depends_on to create sequential dependencies
- Use {{step_X.result.key}} syntax to reference previous step results
- Keep steps atomic and specific
- Maximum 10 steps for complex tasks"""

    def __init__(self, model: str = "gemma3:270m"):
        self.model = model
        self.base_planner = None  # Will be set with tools
    
    def set_tools(self, tools: Dict[str, Callable]):
        """Set available tools for the planner."""
        self.base_planner = MultiStepPlanner(tools)
    
    async def _call_llm(self, prompt: str, temperature: float = 0.2) -> str:
        """Call local LLM via Ollama API."""
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp required for LLM planning")
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": temperature,
                    "format": "json"
                }
                
                async with session.post(self.OLLAMA_API_URL, json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("response", "")
                    else:
                        logger.error(f"Ollama API error: {resp.status}")
                        return ""
                        
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""
    
    async def create_plan_with_llm(
        self,
        goal: str,
        context: Optional[Dict] = None
    ) -> Optional[ExecutionPlan]:
        """
        Create an execution plan using LLM for task decomposition.
        
        Args:
            goal: The high-level goal to achieve
            context: Additional context for planning
        
        Returns:
            ExecutionPlan or None if LLM fails
        """
        if not self.base_planner:
            raise RuntimeError("Tools not set - call set_tools() first")
        
        # Build context string
        context_str = json.dumps(context or {}, indent=2, default=str)
        
        prompt = self.PLANNING_PROMPT.format(
            goal=goal,
            context=context_str
        )
        
        try:
            response = await self._call_llm(prompt)
            steps_data = json.loads(response)
            
            if not isinstance(steps_data, list):
                logger.error("LLM response is not a list of steps")
                return None
            
            # Convert to PlanStep objects
            steps = []
            for step_data in steps_data:
                step = PlanStep(
                    id=step_data.get("id", f"step_{len(steps)+1}"),
                    description=step_data.get("description", "Unknown step"),
                    tool=step_data.get("tool", "execute_task"),
                    params=step_data.get("params", {}),
                    depends_on=step_data.get("depends_on", [])
                )
                steps.append(step)
            
            # Create plan using base planner
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(goal) % 10000}"
            
            plan = ExecutionPlan(
                id=plan_id,
                goal=goal,
                steps=steps,
                context=context or {}
            )
            
            # Register with base planner
            self.base_planner.active_plans[plan_id] = plan
            self.base_planner.plan_history.append(plan_id)
            
            logger.info(f"Created LLM plan {plan_id} with {len(steps)} steps")
            return plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM planning failed: {e}")
            return None
    
    async def create_plan(
        self,
        goal: str,
        context: Optional[Dict] = None,
        use_llm: bool = True
    ) -> ExecutionPlan:
        """
        Create a plan using LLM or fallback to rule-based.
        
        Args:
            goal: The goal to achieve
            context: Planning context
            use_llm: Whether to try LLM first
        
        Returns:
            ExecutionPlan
        """
        if use_llm and self.base_planner:
            try:
                plan = await self.create_plan_with_llm(goal, context)
                if plan:
                    return plan
            except Exception as e:
                logger.warning(f"LLM planning failed, using fallback: {e}")
        
        # Fallback to rule-based
        if self.base_planner:
            return self.base_planner.create_plan(goal, context)
        
        raise RuntimeError("No planner available")
    
    async def execute_plan(self, plan_id: str, agent) -> ExecutionPlan:
        """Execute a plan using the base planner."""
        if not self.base_planner:
            raise RuntimeError("Tools not set")
        return await self.base_planner.execute_plan(plan_id, agent)
    
    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get a plan by ID."""
        if self.base_planner:
            return self.base_planner.get_plan(plan_id)
        return None
    
    def list_plans(self) -> List[Dict]:
        """List all plans."""
        if self.base_planner:
            return self.base_planner.list_plans()
        return []


# Common planning patterns for construction domain
CONSTRUCTION_PATTERNS = {
    "analyze_safety": {
        "description": "Analyze safety trends from reports",
        "steps": [
            {"tool": "search_memory", "params": {"query": "safety incident report"}},
            {"tool": "classify_document", "params": {"document_type": "safety_report"}},
            {"tool": "extract_data", "params": {"fields": ["date", "incident_type", "severity"]}},
            {"tool": "generate_report", "params": {"report_type": "safety_trends"}},
            {"tool": "write_memory", "params": {"tags": ["safety", "analysis"]}}
        ]
    },
    "process_invoice": {
        "description": "Process and validate invoice",
        "steps": [
            {"tool": "classify_document", "params": {"expected_type": "invoice"}},
            {"tool": "extract_data", "params": {"fields": ["vendor", "amount", "date", "line_items"]}},
            {"tool": "query_database", "params": {"check": "purchase_order_match"}},
            {"tool": "write_memory", "params": {"tags": ["invoice", "financial"]}}
        ]
    },
    "review_contract": {
        "description": "Review contract for key terms",
        "steps": [
            {"tool": "classify_document", "params": {"expected_type": "contract"}},
            {"tool": "extract_data", "params": {"fields": ["parties", "value", "dates", "key_clauses"]}},
            {"tool": "analyze_costs", "params": {"analysis_type": "contract_value"}},
            {"tool": "write_memory", "params": {"tags": ["contract", "legal"]}}
        ]
    }
}


class PatternBasedPlanner:
    """
    Fallback planner using predefined patterns for common tasks.
    """
    
    def __init__(self, tools: Dict[str, Callable]):
        self.tools = tools
        self.patterns = CONSTRUCTION_PATTERNS
    
    def create_plan(self, goal: str, context: Optional[Dict] = None) -> ExecutionPlan:
        """Create a plan using pattern matching."""
        goal_lower = goal.lower()
        
        # Find matching pattern
        matched_pattern = None
        for pattern_name, pattern in self.patterns.items():
            if any(keyword in goal_lower for keyword in pattern_name.split("_")):
                matched_pattern = pattern
                break
        
        # Build steps from pattern or generic
        if matched_pattern:
            steps = [
                PlanStep(
                    id=f"step_{i+1}",
                    description=step.get("description", f"Execute {step['tool']}"),
                    tool=step["tool"],
                    params=step.get("params", {}),
                    depends_on=[f"step_{i}"] if i > 0 else []
                )
                for i, step in enumerate(matched_pattern["steps"])
            ]
        else:
            # Generic single-step plan
            steps = [PlanStep(
                id="step_1",
                description=goal,
                tool="execute_task",
                params={"task": goal}
            )]
        
        plan_id = f"plan_pattern_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return ExecutionPlan(
            id=plan_id,
            goal=goal,
            steps=steps,
            context=context or {}
        )


# Unified planner that combines all approaches
class EnhancedPlanner:
    """
    Enhanced planner combining LLM, pattern-based, and rule-based planning.
    """
    
    def __init__(self, tools: Dict[str, Callable], model: str = "gemma3:270m"):
        self.llm_planner = LocalLLMPlanner(model)
        self.llm_planner.set_tools(tools)
        self.pattern_planner = PatternBasedPlanner(tools)
        self.tools = tools
    
    async def create_plan(
        self,
        goal: str,
        context: Optional[Dict] = None,
        strategy: str = "auto"
    ) -> ExecutionPlan:
        """
        Create plan using specified strategy.
        
        Args:
            goal: The goal to achieve
            context: Planning context
            strategy: "llm", "pattern", "auto" (tries LLM first, falls back to pattern)
        """
        if strategy == "llm":
            return await self.llm_planner.create_plan(goal, context, use_llm=True)
        elif strategy == "pattern":
            return self.pattern_planner.create_plan(goal, context)
        else:  # auto
            # Try LLM first
            try:
                plan = await self.llm_planner.create_plan_with_llm(goal, context)
                if plan:
                    return plan
            except Exception as e:
                logger.warning(f"LLM planning failed: {e}")
            
            # Fallback to pattern
            return self.pattern_planner.create_plan(goal, context)
    
    async def execute_plan(self, plan_id: str, agent) -> ExecutionPlan:
        """Execute a plan."""
        return await self.llm_planner.execute_plan(plan_id, agent)
    
    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get a plan by ID."""
        return self.llm_planner.get_plan(plan_id)
    
    def list_plans(self) -> List[Dict]:
        """List all plans."""
        return self.llm_planner.list_plans()


# Convenience function
async def create_plan(
    goal: str,
    tools: Dict[str, Callable],
    context: Optional[Dict] = None,
    use_llm: bool = True
) -> ExecutionPlan:
    """
    Create a plan for the given goal.
    
    Args:
        goal: The goal to achieve
        tools: Available tools
        context: Planning context
        use_llm: Whether to use LLM for planning
    
    Returns:
        ExecutionPlan
    """
    planner = EnhancedPlanner(tools)
    return await planner.create_plan(goal, context, strategy="llm" if use_llm else "pattern")
