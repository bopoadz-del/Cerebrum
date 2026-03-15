"""
Cerebrum Agent Multi-Step Planner

Enables the agent to break complex tasks into executable steps
and execute them with context awareness and error recovery.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Status of a plan step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PlanStatus(Enum):
    """Status of the overall plan."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    id: str
    description: str
    tool: str
    params: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "tool": self.tool,
            "params": self.params,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retries": self.retries,
            "max_retries": self.max_retries
        }


@dataclass
class ExecutionPlan:
    """A multi-step execution plan."""
    id: str
    goal: str
    steps: List[PlanStep]
    status: PlanStatus = PlanStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_step_index: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "context": self.context,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "current_step_index": self.current_step_index,
            "progress": self.get_progress()
        }
    
    def get_progress(self) -> Dict:
        """Get execution progress statistics."""
        total = len(self.steps)
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in self.steps if s.status == StepStatus.FAILED)
        running = sum(1 for s in self.steps if s.status == StepStatus.RUNNING)
        pending = sum(1 for s in self.steps if s.status == StepStatus.PENDING)
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "pending": pending,
            "percent": (completed / total * 100) if total > 0 else 0
        }
    
    def get_next_executable_step(self) -> Optional[PlanStep]:
        """Get the next step that can be executed (dependencies satisfied)."""
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            deps_satisfied = all(
                any(s.id == dep and s.status == StepStatus.COMPLETED for s in self.steps)
                for dep in step.depends_on
            )
            
            if deps_satisfied:
                return step
        
        return None
    
    def is_complete(self) -> bool:
        """Check if all steps are completed or failed."""
        return all(s.status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED) 
                   for s in self.steps)


class MultiStepPlanner:
    """
    Multi-step planner for complex agent tasks.
    
    Breaks down complex goals into executable steps with:
    - Dependency management
    - Error recovery and retries
    - Progress tracking
    - Context passing between steps
    """
    
    def __init__(self, agent_tools: Dict[str, Callable]):
        self.tools = agent_tools
        self.active_plans: Dict[str, ExecutionPlan] = {}
        self.plan_history: List[str] = []
    
    def create_plan(self, goal: str, context: Optional[Dict] = None) -> ExecutionPlan:
        """
        Create an execution plan from a goal.
        
        In a full implementation, this would use an LLM to break down
        the goal into steps. For now, uses rule-based parsing.
        """
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.active_plans)}"
        
        steps = self._parse_goal_into_steps(goal, context or {})
        
        plan = ExecutionPlan(
            id=plan_id,
            goal=goal,
            steps=steps,
            context=context or {}
        )
        
        self.active_plans[plan_id] = plan
        self.plan_history.append(plan_id)
        
        logger.info(f"Created plan {plan_id} with {len(steps)} steps")
        return plan
    
    def _parse_goal_into_steps(self, goal: str, context: Dict) -> List[PlanStep]:
        """Parse a goal into execution steps."""
        goal_lower = goal.lower()
        steps = []
        
        # Pattern: Generate and deploy endpoint
        if "generate" in goal_lower and "endpoint" in goal_lower and "deploy" in goal_lower:
            model_name = self._extract_model_name(goal) or "Item"
            fields = self._extract_fields(goal) or [{"name": "id", "type": "int"}]
            
            steps = [
                PlanStep(
                    id="step_1",
                    description=f"Generate endpoint code for {model_name}",
                    tool="generate_endpoint",
                    params={
                        "description": goal,
                        "model_name": model_name,
                        "fields": fields
                    }
                ),
                PlanStep(
                    id="step_2",
                    description="Validate generated code",
                    tool="validate_code",
                    params={"code": "{{step_1.result.code}}", "code_type": "python"},
                    depends_on=["step_1"]
                ),
                PlanStep(
                    id="step_3",
                    description="Deploy validated endpoint",
                    tool="deploy_capability",
                    params={
                        "name": f"{model_name.lower()}_endpoint",
                        "code": "{{step_1.result.code}}",
                        "route_path": f"/api/{model_name.lower()}",
                        "route_methods": ["GET", "POST", "PUT", "DELETE"]
                    },
                    depends_on=["step_2"]
                )
            ]
        
        # Pattern: Analyze and fix errors
        elif any(word in goal_lower for word in ["fix", "heal", "repair"]):
            steps = [
                PlanStep(
                    id="step_1",
                    description="Read error logs and analyze",
                    tool="read_conversation",
                    params={"days": 1}
                ),
                PlanStep(
                    id="step_2",
                    description="Analyze errors and suggest fixes",
                    tool="heal_error",
                    params={
                        "error_logs": "{{context.error_logs}}",
                        "capability_name": "{{context.capability_name}}"
                    },
                    depends_on=["step_1"]
                ),
                PlanStep(
                    id="step_3",
                    description="Write healing actions to memory",
                    tool="write_memory",
                    params={
                        "content": "Healing plan: {{step_2.result.suggested_actions}}"
                    },
                    depends_on=["step_2"]
                )
            ]
        
        # Pattern: Search and summarize
        elif any(word in goal_lower for word in ["search", "find", "summarize"]):
            query = goal_lower.replace("search", "").replace("find", "").strip()
            steps = [
                PlanStep(
                    id="step_1",
                    description=f"Search for: {query}",
                    tool="search_memory",
                    params={"query": query, "limit": 10}
                ),
                PlanStep(
                    id="step_2",
                    description="Write findings to memory",
                    tool="write_memory",
                    params={
                        "content": "Search results for '{{step_1.params.query}}': {{step_1.result.results}}"
                    },
                    depends_on=["step_1"]
                )
            ]
        
        # Default: Single step
        else:
            steps = [
                PlanStep(
                    id="step_1",
                    description=goal,
                    tool="execute_task",
                    params={"task": goal}
                )
            ]
        
        return steps
    
    def _extract_model_name(self, goal: str) -> Optional[str]:
        """Extract model name from goal."""
        import re
        patterns = [
            r"for\s+(\w+)",
            r"(\w+)\s+model",
            r"(\w+)\s+endpoint"
        ]
        for pattern in patterns:
            match = re.search(pattern, goal, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
        return None
    
    def _extract_fields(self, goal: str) -> Optional[List[Dict]]:
        """Extract field definitions from goal."""
        import re
        fields = []
        field_pattern = r"(\w+)\s*\(\s*(\w+)\s*\)"
        matches = re.findall(field_pattern, goal)
        
        for name, type_str in matches:
            fields.append({
                "name": name,
                "type": type_str,
                "required": True
            })
        
        return fields if fields else None
    
    async def execute_plan(self, plan_id: str, agent) -> ExecutionPlan:
        """
        Execute a plan step by step.
        
        Args:
            plan_id: The plan ID to execute
            agent: The CerebrumAgent instance
        
        Returns:
            The completed (or failed) plan
        """
        plan = self.active_plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        plan.status = PlanStatus.RUNNING
        plan.started_at = datetime.now().isoformat()
        
        logger.info(f"Starting execution of plan {plan_id}")
        
        while not plan.is_complete():
            step = plan.get_next_executable_step()
            
            if not step:
                # No executable steps but not complete - possible deadlock
                if any(s.status == StepStatus.FAILED for s in plan.steps):
                    plan.status = PlanStatus.FAILED
                break
            
            await self._execute_step(step, plan, agent)
            
            # Brief pause between steps
            await asyncio.sleep(0.1)
        
        plan.completed_at = datetime.now().isoformat()
        
        if all(s.status == StepStatus.COMPLETED for s in plan.steps):
            plan.status = PlanStatus.COMPLETED
            logger.info(f"Plan {plan_id} completed successfully")
        elif plan.status != PlanStatus.FAILED:
            plan.status = PlanStatus.FAILED
            logger.error(f"Plan {plan_id} failed")
        
        return plan
    
    async def _execute_step(self, step: PlanStep, plan: ExecutionPlan, agent):
        """Execute a single plan step."""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()
        
        logger.info(f"Executing step {step.id}: {step.description}")
        
        try:
            # Resolve template variables in params
            params = self._resolve_params(step.params, plan)
            
            # Get the tool function
            tool_func = self.tools.get(step.tool)
            if not tool_func:
                raise ValueError(f"Unknown tool: {step.tool}")
            
            # Execute the tool
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**params)
            else:
                result = tool_func(**params)
            
            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now().isoformat()
            
            logger.info(f"Step {step.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Step {step.id} failed: {e}")
            step.error = str(e)
            step.retries += 1
            
            if step.retries < step.max_retries:
                step.status = StepStatus.PENDING
                logger.info(f"Retrying step {step.id} (attempt {step.retries + 1})")
            else:
                step.status = StepStatus.FAILED
    
    def _resolve_params(self, params: Dict, plan: ExecutionPlan) -> Dict:
        """Resolve template variables in parameters."""
        resolved = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                # Replace {{step_X.result...}} with actual values
                if "{{" in value and "}}" in value:
                    value = self._resolve_template(value, plan)
                resolved[key] = value
            else:
                resolved[key] = value
        
        return resolved
    
    def _resolve_template(self, template: str, plan: ExecutionPlan) -> str:
        """Resolve template variables like {{step_1.result.code}}."""
        import re
        
        pattern = r"\{\{(\w+)\.?([^}]*)\}\}"
        matches = re.findall(pattern, template)
        
        result = template
        for step_ref, path in matches:
            if step_ref == "context":
                # Get from plan context
                value = plan.context.get(path, "")
            else:
                # Get from step result
                step = next((s for s in plan.steps if s.id == step_ref), None)
                if step and step.result:
                    value = step.result
                    # Navigate path if provided
                    if path:
                        for key in path.split("."):
                            if isinstance(value, dict):
                                value = value.get(key, "")
                            else:
                                value = str(value)
                                break
                else:
                    value = ""
            
            result = result.replace(f"{{{{{step_ref}.{path}}}}}", str(value))
        
        return result
    
    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Get a plan by ID."""
        return self.active_plans.get(plan_id)
    
    def list_plans(self) -> List[Dict]:
        """List all plans with their status."""
        return [p.to_dict() for p in self.active_plans.values()]
    
    def cancel_plan(self, plan_id: str) -> bool:
        """Cancel a running plan."""
        plan = self.active_plans.get(plan_id)
        if plan and plan.status == PlanStatus.RUNNING:
            plan.status = PlanStatus.PAUSED
            return True
        return False
    
    def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan."""
        if plan_id in self.active_plans:
            del self.active_plans[plan_id]
            return True
        return False
