"""
Intelligent Workflow for Smart Orchestrator

Chains multiple actions together for complex goals.
Based on the Vietnam Doc architecture for action chaining.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from app.orchestrator.action_map import ACTION_MAP
from app.orchestrator.session_memory import SessionMemory
from app.containers import ConstructionBlock


class WorkflowState(Enum):
    """States for workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    """A single step in a workflow chain."""
    action: str
    params: Dict[str, Any]
    depends_on: Optional[str] = None
    output_key: Optional[str] = None
    condition: Optional[str] = None  # Conditional execution


@dataclass
class WorkflowDefinition:
    """Definition of a workflow with multiple steps."""
    name: str
    description: str
    steps: List[WorkflowStep]
    input_requirements: List[str] = field(default_factory=list)
    final_output: Optional[str] = None


class IntelligentWorkflow:
    """
    Intelligent workflow engine for chaining construction actions.
    
    Key capabilities:
    - Chain multiple actions for complex goals
    - Pass outputs from one action to the next
    - Conditional execution based on previous results
    - Accumulate results across the workflow
    """
    
    # Predefined workflow patterns
    WORKFLOWS: Dict[str, WorkflowDefinition] = {
        "full_qto": WorkflowDefinition(
            name="full_qto",
            description="Complete quantity takeoff with cost and carbon analysis",
            steps=[
                WorkflowStep(
                    action="process_document",
                    params={},
                    output_key="document_data"
                ),
                WorkflowStep(
                    action="extract_quantities",
                    params={},
                    depends_on="document_data",
                    output_key="quantities"
                ),
                WorkflowStep(
                    action="carbon_footprint_calculator",
                    params={},
                    depends_on="quantities",
                    output_key="carbon"
                ),
            ],
            input_requirements=["file_path"],
            final_output="complete_qto_report"
        ),
        
        "change_order_full": WorkflowDefinition(
            name="change_order_full",
            description="Complete change order impact analysis",
            steps=[
                WorkflowStep(
                    action="change_order_impact",
                    params={},
                    output_key="co_impact"
                ),
                WorkflowStep(
                    action="rfi_generator",
                    params={},
                    condition="co_impact.requires_clarification",
                    output_key="rfi"
                ),
                WorkflowStep(
                    action="variation_order_manager",
                    params={},
                    depends_on="co_impact",
                    output_key="vo"
                ),
            ],
            input_requirements=["description"],
            final_output="co_package"
        ),
        
        "document_compliance_check": WorkflowDefinition(
            name="document_compliance_check",
            description="Full document compliance and risk check",
            steps=[
                WorkflowStep(
                    action="process_specification_full",
                    params={},
                    output_key="specs"
                ),
                WorkflowStep(
                    action="process_drawing",
                    params={},
                    output_key="drawings"
                ),
                WorkflowStep(
                    action="risk_register_auto_populate",
                    params={},
                    depends_on="specs",
                    output_key="risks"
                ),
                WorkflowStep(
                    action="submittal_log_generator",
                    params={},
                    depends_on="specs",
                    output_key="submittals"
                ),
            ],
            input_requirements=["spec_file", "drawing_files"],
            final_output="compliance_package"
        ),
        
        "project_risk_assessment": WorkflowDefinition(
            name="project_risk_assessment",
            description="Comprehensive project risk assessment",
            steps=[
                WorkflowStep(
                    action="risk_register_auto_populate",
                    params={},
                    output_key="risks"
                ),
                WorkflowStep(
                    action="parse_primavera_schedule",
                    params={},
                    output_key="schedule"
                ),
                WorkflowStep(
                    action="process_contract",
                    params={},
                    output_key="contract"
                ),
            ],
            input_requirements=["drawings", "schedule_file", "contract_file"],
            final_output="risk_report"
        ),
        
        "bim_coordination": WorkflowDefinition(
            name="bim_coordination",
            description="Complete BIM coordination workflow",
            steps=[
                WorkflowStep(
                    action="bim_clash_detection",
                    params={},
                    output_key="clashes"
                ),
                WorkflowStep(
                    action="rfi_generator",
                    params={},
                    condition="clashes.has_critical",
                    output_key="coordination_rfis"
                ),
                WorkflowStep(
                    action="digital_twin_sync",
                    params={},
                    output_key="twin_update"
                ),
            ],
            input_requirements=["ifc_file"],
            final_output="coordination_report"
        ),
        
        "monthly_progress": WorkflowDefinition(
            name="monthly_progress",
            description="Monthly progress reporting workflow",
            steps=[
                WorkflowStep(
                    action="parse_primavera_schedule",
                    params={},
                    output_key="schedule"
                ),
                WorkflowStep(
                    action="payment_certificate",
                    params={},
                    depends_on="schedule",
                    output_key="payment"
                ),
                WorkflowStep(
                    action="cash_flow_forecast",
                    params={},
                    depends_on="payment",
                    output_key="cashflow"
                ),
                WorkflowStep(
                    action="daily_site_report",
                    params={},
                    output_key="site_report"
                ),
            ],
            input_requirements=["schedule_file", "boq"],
            final_output="monthly_package"
        ),
        
        "procurement_planning": WorkflowDefinition(
            name="procurement_planning",
            description="Complete procurement planning workflow",
            steps=[
                WorkflowStep(
                    action="extract_quantities",
                    params={},
                    output_key="quantities"
                ),
                WorkflowStep(
                    action="procurement_list_generator",
                    params={},
                    depends_on="quantities",
                    output_key="procurement_list"
                ),
                WorkflowStep(
                    action="procurement_optimizer",
                    params={},
                    depends_on="procurement_list",
                    output_key="optimized_procurement"
                ),
                WorkflowStep(
                    action="cash_flow_forecast",
                    params={},
                    depends_on="optimized_procurement",
                    output_key="cashflow"
                ),
            ],
            input_requirements=["boq", "schedule_file"],
            final_output="procurement_plan"
        ),
        
        "handover_package": WorkflowDefinition(
            name="handover_package",
            description="Complete project handover documentation",
            steps=[
                WorkflowStep(
                    action="as_built_deviation_report",
                    params={},
                    output_key="deviations"
                ),
                WorkflowStep(
                    action="commissioning_checklist",
                    params={},
                    output_key="commissioning"
                ),
                WorkflowStep(
                    action="warranty_maintenance_schedule",
                    params={},
                    output_key="warranty"
                ),
                WorkflowStep(
                    action="om_manual_generator",
                    params={},
                    depends_on="commissioning",
                    output_key="om_manual"
                ),
            ],
            input_requirements=["as_built_files", "spec_file"],
            final_output="handover_package"
        ),
    }
    
    def __init__(
        self,
        session_memory: Optional[SessionMemory] = None,
        construction_block: Optional[ConstructionBlock] = None
    ):
        self.session_memory = session_memory or SessionMemory()
        self.construction_block = construction_block or ConstructionBlock()
    
    def get_workflow(self, name: str) -> Optional[WorkflowDefinition]:
        """Get a predefined workflow by name."""
        return self.WORKFLOWS.get(name)
    
    def list_workflows(self) -> List[Dict[str, str]]:
        """List all available predefined workflows."""
        return [
            {
                "name": wf.name,
                "description": wf.description,
                "steps": len(wf.steps),
                "inputs": wf.input_requirements,
            }
            for wf in self.WORKFLOWS.values()
        ]
    
    def build_workflow(
        self,
        user_goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[WorkflowDefinition]:
        """
        Build a custom workflow from user goal.
        
        Uses keyword matching and context to determine appropriate
        action sequence.
        """
        context = context or {}
        goal_lower = user_goal.lower()
        
        # Check for predefined workflow matches
        for workflow_name, workflow in self.WORKFLOWS.items():
            if workflow_name in goal_lower or workflow.name in goal_lower:
                return workflow
        
        # Build custom workflow from goal analysis
        steps = self._analyze_goal_for_steps(goal_lower, context)
        
        if not steps:
            return None
        
        return WorkflowDefinition(
            name="custom_workflow",
            description=f"Custom workflow for: {user_goal}",
            steps=steps,
            input_requirements=list(context.keys()),
        )
    
    def _analyze_goal_for_steps(
        self,
        goal: str,
        context: Dict[str, Any]
    ) -> List[WorkflowStep]:
        """Analyze user goal to determine workflow steps."""
        steps = []
        
        # Common patterns for workflow building
        patterns = [
            # QTO patterns
            (r'(?:extract|get|do)\s+(?:quantities?|qto|takeoff)', "extract_quantities"),
            (r'(?:calculate|compute)\s+(?:cost|price|value)', "extract_quantities"),
            
            # Document processing
            (r'(?:process|analyze|read)\s+(?:document|file|pdf)', "process_document"),
            (r'(?:process|analyze)\s+(?:the\s+)?spec(?:s|ification)?', "process_specification_full"),
            (r'(?:process|analyze)\s+(?:the\s+)?drawing', "process_drawing"),
            (r'(?:analyze|review)\s+(?:the\s+)?contract', "process_contract"),
            
            # Scheduling
            (r'(?:analyze|parse)\s+(?:the\s+)?schedule', "parse_primavera_schedule"),
            (r'(?:delay|forensic)\s+analysis', "forensic_delay_analysis"),
            (r'(?:resource|manpower)\s+(?:histogram|loading)', "resource_histogram"),
            
            # Financial
            (r'(?:generate|create)\s+(?:payment|ipc)', "payment_certificate"),
            (r'(?:cash\s+flow|cashflow)\s+(?:forecast|projection)', "cash_flow_forecast"),
            (r'(?:build|create)\s+(?:a\s+)?claim', "claims_builder"),
            (r'(?:variation|vo)\s+(?:management|register)', "variation_order_manager"),
            
            # Communication
            (r'(?:generate|create|draft)\s+(?:an\s+)?rfi', "rfi_generator"),
            (r'(?:generate|create)\s+submittal\s+(?:log|register)', "submittal_log_generator"),
            
            # Compliance
            (r'(?:safety|hse)\s+(?:audit|inspection)', "safety_compliance_audit"),
            (r'(?:quality|qa|qc)\s+(?:check|inspection)', "qa_qc_inspection"),
            (r'(?:commissioning|handover)\s+(?:checklist|plan)', "commissioning_checklist"),
            (r'(?:warranty|maintenance)\s+schedule', "warranty_maintenance_schedule"),
            
            # Carbon
            (r'(?:carbon|co2)\s+(?:footprint|calculation)', "carbon_footprint_calculator"),
            (r'(?:esg|sustainability)\s+report', "esg_sustainability_report"),
            
            # Risk
            (r'(?:risk|hazard)\s+(?:register|assessment)', "risk_register_auto_populate"),
            
            # BIM
            (r'(?:bim\s+)?clash\s+detection', "bim_clash_detection"),
            (r'(?:digital\s+twin|twin)\s+(?:sync|update)', "digital_twin_sync"),
            
            # Reporting
            (r'(?:daily\s+site|dsr)\s+report', "daily_site_report"),
            (r'(?:as[-\s]?built|asbuilt)\s+(?:report|comparison)', "as_built_deviation_report"),
            (r'(?:o[&+]m|om)\s+manual', "om_manual_generator"),
            
            # VE
            (r'(?:value\s+engineering|ve|optimization)', "value_engineering"),
            (r'(?:bid|tender)\s+(?:comparison|analysis)', "tender_bid_analysis"),
            
            # Procurement
            (r'(?:procurement|material)\s+(?:schedule|plan)', "procurement_list_generator"),
            (r'optimize\s+(?:procurement|materials|ordering)', "procurement_optimizer"),
        ]
        
        for pattern, action in patterns:
            if re.search(pattern, goal, re.IGNORECASE):
                # Check if step already exists
                if not any(s.action == action for s in steps):
                    steps.append(WorkflowStep(action=action, params={}))
        
        return steps
    
    async def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        initial_params: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow with the given parameters.
        
        Args:
            workflow: The workflow definition to execute
            initial_params: Initial parameters for the workflow
            session_id: Optional session ID for context tracking
        
        Returns:
            Dict with workflow results and accumulated data
        """
        results = {
            "workflow_name": workflow.name,
            "status": WorkflowState.PENDING.value,
            "steps_completed": 0,
            "total_steps": len(workflow.steps),
            "step_results": [],
            "accumulated_data": {},
            "errors": [],
        }
        
        if session_id:
            self.session_memory.set_workflow_state(
                session_id, 
                WorkflowState.RUNNING.value,
                [],
                {"workflow": workflow.name}
            )
        
        accumulated_data = {}
        
        for i, step in enumerate(workflow.steps):
            try:
                # Build params for this step
                step_params = self._build_step_params(
                    step, 
                    initial_params, 
                    accumulated_data
                )
                
                # Check condition
                if step.condition and not self._evaluate_condition(
                    step.condition, 
                    accumulated_data
                ):
                    results["step_results"].append({
                        "step": i + 1,
                        "action": step.action,
                        "status": "skipped",
                        "reason": f"Condition not met: {step.condition}",
                    })
                    continue
                
                # Execute the action
                action_method = getattr(self.construction_block, step.action, None)
                if not action_method:
                    raise ValueError(f"Unknown action: {step.action}")
                
                step_result = await action_method(
                    {"input_data": step_params},
                    step_params
                )
                
                # Store result
                if step.output_key:
                    accumulated_data[step.output_key] = step_result
                
                results["step_results"].append({
                    "step": i + 1,
                    "action": step.action,
                    "status": "completed",
                    "result": step_result,
                })
                
                results["steps_completed"] = i + 1
                
                # Update session memory
                if session_id:
                    self.session_memory.add_to_workflow_chain(
                        session_id,
                        step.action,
                        step_result
                    )
                
            except Exception as e:
                error_msg = f"Step {i + 1} ({step.action}) failed: {str(e)}"
                results["errors"].append(error_msg)
                results["step_results"].append({
                    "step": i + 1,
                    "action": step.action,
                    "status": "failed",
                    "error": str(e),
                })
                
                # Stop workflow on error
                results["status"] = WorkflowState.FAILED.value
                
                if session_id:
                    self.session_memory.set_workflow_state(
                        session_id,
                        WorkflowState.FAILED.value,
                        results["step_results"],
                        {"errors": results["errors"]}
                    )
                
                return results
        
        # Workflow completed successfully
        results["status"] = WorkflowState.COMPLETED.value
        results["accumulated_data"] = accumulated_data
        
        if workflow.final_output and accumulated_data:
            results["final_output"] = accumulated_data.get(workflow.final_output)
        
        if session_id:
            self.session_memory.set_workflow_state(
                session_id,
                WorkflowState.COMPLETED.value,
                [s.action for s in workflow.steps],
                accumulated_data
            )
        
        return results
    
    def _build_step_params(
        self,
        step: WorkflowStep,
        initial_params: Dict[str, Any],
        accumulated_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build parameters for a workflow step."""
        params = {}
        
        # Start with initial params
        params.update(initial_params)
        
        # Add step-specific params
        params.update(step.params)
        
        # Add dependency data if specified
        if step.depends_on and step.depends_on in accumulated_data:
            dep_data = accumulated_data[step.depends_on]
            # Map dependency data to appropriate input keys
            if isinstance(dep_data, dict):
                # Try to intelligently map outputs to inputs
                for key, value in dep_data.items():
                    if key not in params:
                        params[key] = value
        
        return params
    
    def _evaluate_condition(
        self,
        condition: str,
        accumulated_data: Dict[str, Any]
    ) -> bool:
        """Evaluate a conditional expression against accumulated data."""
        # Simple condition evaluation
        # Format: "key.subkey" or "key.subkey == value"
        
        parts = condition.split('.')
        data = accumulated_data
        
        for part in parts:
            if isinstance(data, dict):
                data = data.get(part)
                if data is None:
                    return False
            else:
                return False
        
        # If we got here, the key path exists
        # Check for specific conditions
        if isinstance(data, bool):
            return data
        if isinstance(data, (int, float)):
            return data > 0
        if isinstance(data, (list, dict)):
            return len(data) > 0
        
        return bool(data)
    
    def get_workflow_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a running workflow."""
        state = self.session_memory.get_workflow_state(session_id)
        if not state:
            return None
        
        return {
            "state": state["state"],
            "completed_actions": state["chain"],
            "data_keys": list(state["data"].keys()),
        }
