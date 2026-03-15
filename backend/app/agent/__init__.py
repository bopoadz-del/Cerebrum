"""
Cerebrum Agent Module

Autonomous AI agent for the Cerebrum construction intelligence platform.
Integrates with the 14-layer architecture for self-coding, healing, and task execution.
"""

from app.agent.core import CerebrumAgent, AgentLayer, AgentAction, AgentContext, AgentResult
from app.agent.core import get_agent, reset_agent
from app.agent.enhanced_core import (
    EnhancedCerebrumAgent, EnhancedConversationReader, EnhancedLayerNavigator,
    LayerState, ConversationEntry, MemoryIndex, get_enhanced_agent
)
from app.agent.planner import MultiStepPlanner, ExecutionPlan, PlanStep, PlanStatus, StepStatus
from app.agent.scheduler import AgentScheduler, ScheduledTask, ScheduleType, TaskStatus
from app.agent.websocket import AgentWebSocketManager, get_websocket_manager
from app.agent.self_modification import (
    SelfModificationEngine, GitManager, CodeSafetyChecker, LayerGenerator,
    ModificationRequest, CodeChange, GeneratedLayer, RollbackPoint,
    ModificationType, ModificationStatus, get_modification_engine
)
from app.agent.code_enhancement import (
    CodeAnalyzer, CodeEnhancer, EnhancementManager,
    EnhancementType, EnhancementPlan, EnhancementResult,
    CodeIssue, enhance_code_file
)

from app.agent.self_modification import (
    SelfModificationEngine, GitManager, CodeSafetyChecker, LayerGenerator,
    ModificationRequest, CodeChange, GeneratedLayer, RollbackPoint,
    ModificationType, ModificationStatus, get_modification_engine
)

__all__ = [
    "CerebrumAgent",
    "EnhancedCerebrumAgent",
    "EnhancedConversationReader",
    "EnhancedLayerNavigator",
    "SelfModificationEngine",
    "GitManager",
    "CodeSafetyChecker",
    "LayerGenerator",
    "ModificationRequest",
    "CodeChange",
    "GeneratedLayer",
    "RollbackPoint",
    "ModificationType",
    "ModificationStatus",
    "CodeAnalyzer",
    "CodeEnhancer",
    "EnhancementManager",
    "EnhancementType",
    "EnhancementPlan",
    "EnhancementResult",
    "CodeIssue",
    "enhance_code_file",
    "AgentLayer",
    "AgentAction",
    "AgentContext",
    "AgentResult",
    "LayerState",
    "ConversationEntry",
    "MemoryIndex",
    "get_agent",
    "reset_agent",
    "get_enhanced_agent",
    "get_modification_engine",
    "MultiStepPlanner",
    "ExecutionPlan",
    "PlanStep",
    "PlanStatus",
    "StepStatus",
    "AgentScheduler",
    "ScheduledTask",
    "ScheduleType",
    "TaskStatus",
    "AgentWebSocketManager",
    "get_websocket_manager",
]