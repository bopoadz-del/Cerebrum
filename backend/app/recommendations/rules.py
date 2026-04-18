"""
Symbolic Rule Engine for Recommendations

Implements a rule-based system for generating contextual recommendations.
Rules consist of conditions and actions that are evaluated against context.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from app.core.logging import get_logger

logger = get_logger(__name__)


class ComparisonOperator(str, Enum):
    """Comparison operators for rule conditions."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    IN = "in"
    NOT_IN = "not_in"
    REGEX = "regex"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class ActionType(str, Enum):
    """Types of rule actions."""
    SUGGEST_TEMPLATE = "suggest_template"
    BOOST_CATEGORY = "boost_category"
    BOOST_TAG = "boost_tag"
    HIDE_CATEGORY = "hide_category"
    REQUIRE_INPUT = "require_input"
    SET_CONTEXT = "set_context"


@dataclass
class RuleCondition:
    """Condition for a rule to trigger."""
    field: str
    operator: str
    value: Any
    negate: bool = False
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against context."""
        context_value = self._get_nested_value(context, self.field)
        
        result = self._compare(context_value, self.operator, self.value)
        return not result if self.negate else result
    
    def _get_nested_value(self, context: Dict[str, Any], field: str) -> Any:
        """Get value from context, supporting nested fields with dot notation."""
        parts = field.split(".")
        value = context
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return value
    
    def _compare(self, context_value: Any, operator: str, target_value: Any) -> bool:
        """Compare context value with target value using operator."""
        op = ComparisonOperator(operator)
        
        if op == ComparisonOperator.EXISTS:
            return context_value is not None
        
        if op == ComparisonOperator.NOT_EXISTS:
            return context_value is None
        
        if context_value is None:
            return False
        
        if op == ComparisonOperator.EQUALS:
            return context_value == target_value
        
        if op == ComparisonOperator.NOT_EQUALS:
            return context_value != target_value
        
        if op == ComparisonOperator.CONTAINS:
            if isinstance(context_value, (list, tuple, set)):
                return target_value in context_value
            elif isinstance(context_value, str):
                return target_value in context_value
            elif isinstance(context_value, dict):
                return target_value in context_value.values()
            return False
        
        if op == ComparisonOperator.NOT_CONTAINS:
            if isinstance(context_value, (list, tuple, set)):
                return target_value not in context_value
            elif isinstance(context_value, str):
                return target_value not in context_value
            elif isinstance(context_value, dict):
                return target_value not in context_value.values()
            return True
        
        if op == ComparisonOperator.GREATER_THAN:
            try:
                return float(context_value) > float(target_value)
            except (ValueError, TypeError):
                return False
        
        if op == ComparisonOperator.LESS_THAN:
            try:
                return float(context_value) < float(target_value)
            except (ValueError, TypeError):
                return False
        
        if op == ComparisonOperator.GREATER_EQUAL:
            try:
                return float(context_value) >= float(target_value)
            except (ValueError, TypeError):
                return False
        
        if op == ComparisonOperator.LESS_EQUAL:
            try:
                return float(context_value) <= float(target_value)
            except (ValueError, TypeError):
                return False
        
        if op == ComparisonOperator.IN:
            if isinstance(target_value, (list, tuple, set)):
                return context_value in target_value
            return False
        
        if op == ComparisonOperator.NOT_IN:
            if isinstance(target_value, (list, tuple, set)):
                return context_value not in target_value
            return True
        
        if op == ComparisonOperator.REGEX:
            import re
            try:
                return bool(re.search(target_value, str(context_value)))
            except re.error:
                return False
        
        return False


@dataclass
class RuleAction:
    """Action to execute when rule conditions are met."""
    type: str
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 3  # 1=Critical, 2=High, 3=Medium, 4=Low, 5=Info
    rule_name: str = ""


@dataclass
class Rule:
    """Complete rule with conditions and actions."""
    name: str
    description: str
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    priority: int = 3
    enabled: bool = True
    category: str = "general"
    
    def evaluate(self, context: Dict[str, Any]) -> Optional[List[RuleAction]]:
        """Evaluate rule against context."""
        if not self.enabled:
            return None
        
        # Check if all conditions are met
        for condition in self.conditions:
            if not condition.evaluate(context):
                return None
        
        # All conditions met - return actions with rule metadata
        for action in self.actions:
            action.priority = self.priority
            action.rule_name = self.name
        
        logger.debug(f"Rule '{self.name}' triggered")
        return self.actions


class RuleEngine:
    """
    Rule engine for contextual recommendations.
    
    Manages and evaluates rules against context to generate
    recommendation actions. Supports rule categories, priorities,
    and complex condition logic.
    """
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.rules_by_category: Dict[str, List[str]] = {}
        self.custom_operators: Dict[str, Callable] = {}
    
    def add_rule(
        self,
        name: str,
        conditions: List[RuleCondition],
        actions: List[RuleAction],
        description: str = "",
        priority: int = 3,
        category: str = "general",
        enabled: bool = True,
    ) -> Rule:
        """Add a new rule to the engine."""
        rule = Rule(
            name=name,
            description=description,
            conditions=conditions,
            actions=actions,
            priority=priority,
            enabled=enabled,
            category=category,
        )
        
        self.rules[name] = rule
        
        # Index by category
        if category not in self.rules_by_category:
            self.rules_by_category[category] = []
        self.rules_by_category[category].append(name)
        
        logger.info(f"Added rule: {name} (category: {category})")
        return rule
    
    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name."""
        if name not in self.rules:
            return False
        
        rule = self.rules.pop(name)
        
        # Remove from category index
        if rule.category in self.rules_by_category:
            self.rules_by_category[rule.category].remove(name)
        
        logger.info(f"Removed rule: {name}")
        return True
    
    def enable_rule(self, name: str) -> bool:
        """Enable a rule."""
        if name in self.rules:
            self.rules[name].enabled = True
            logger.info(f"Enabled rule: {name}")
            return True
        return False
    
    def disable_rule(self, name: str) -> bool:
        """Disable a rule."""
        if name in self.rules:
            self.rules[name].enabled = False
            logger.info(f"Disabled rule: {name}")
            return True
        return False
    
    def evaluate(
        self,
        context: Dict[str, Any],
        category: Optional[str] = None,
    ) -> List[RuleAction]:
        """
        Evaluate rules against context.
        
        Args:
            context: Context data to evaluate against
            category: Optional category filter
            
        Returns:
            List of triggered actions sorted by priority
        """
        triggered_actions = []
        
        # Get rules to evaluate
        if category:
            rule_names = self.rules_by_category.get(category, [])
        else:
            rule_names = list(self.rules.keys())
        
        # Evaluate each rule
        for rule_name in rule_names:
            rule = self.rules.get(rule_name)
            if not rule:
                continue
            
            actions = rule.evaluate(context)
            if actions:
                triggered_actions.extend(actions)
        
        # Sort by priority (lower = higher priority)
        triggered_actions.sort(key=lambda a: a.priority)
        
        return triggered_actions
    
    def evaluate_single(
        self,
        rule_name: str,
        context: Dict[str, Any],
    ) -> Optional[List[RuleAction]]:
        """Evaluate a single rule by name."""
        if rule_name not in self.rules:
            return None
        
        return self.rules[rule_name].evaluate(context)
    
    def get_rules(self, category: Optional[str] = None) -> List[Rule]:
        """Get all rules or rules in a category."""
        if category:
            rule_names = self.rules_by_category.get(category, [])
            return [self.rules[name] for name in rule_names if name in self.rules]
        
        return list(self.rules.values())
    
    def get_rule(self, name: str) -> Optional[Rule]:
        """Get a specific rule by name."""
        return self.rules.get(name)
    
    def add_custom_operator(
        self,
        name: str,
        operator_func: Callable[[Any, Any], bool],
    ) -> None:
        """Add a custom comparison operator."""
        self.custom_operators[name] = operator_func
        logger.info(f"Added custom operator: {name}")
    
    def export_rules(self) -> List[Dict[str, Any]]:
        """Export all rules as dictionaries."""
        return [
            {
                "name": rule.name,
                "description": rule.description,
                "category": rule.category,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "conditions": [
                    {
                        "field": c.field,
                        "operator": c.operator,
                        "value": c.value,
                        "negate": c.negate,
                    }
                    for c in rule.conditions
                ],
                "actions": [
                    {
                        "type": a.type,
                        "params": a.params,
                    }
                    for a in rule.actions
                ],
            }
            for rule in self.rules.values()
        ]
    
    def import_rules(self, rules_data: List[Dict[str, Any]]) -> int:
        """Import rules from dictionaries."""
        imported = 0
        
        for data in rules_data:
            try:
                conditions = [
                    RuleCondition(
                        field=c["field"],
                        operator=c["operator"],
                        value=c["value"],
                        negate=c.get("negate", False),
                    )
                    for c in data.get("conditions", [])
                ]
                
                actions = [
                    RuleAction(
                        type=a["type"],
                        params=a.get("params", {}),
                    )
                    for a in data.get("actions", [])
                ]
                
                self.add_rule(
                    name=data["name"],
                    description=data.get("description", ""),
                    conditions=conditions,
                    actions=actions,
                    priority=data.get("priority", 3),
                    category=data.get("category", "general"),
                    enabled=data.get("enabled", True),
                )
                imported += 1
            except Exception as e:
                logger.error(f"Failed to import rule {data.get('name')}: {e}")
        
        logger.info(f"Imported {imported} rules")
        return imported


# Pre-defined rule templates for construction domain
CONSTRUCTION_RULE_TEMPLATES = {
    "concrete_project": {
        "description": "Boost concrete-related formulas for concrete projects",
        "conditions": [
            {"field": "project_type", "operator": "equals", "value": "concrete"}
        ],
        "actions": [
            {"type": "boost_category", "params": {"category": "concrete", "boost": 2.0}}
        ],
        "priority": 2,
    },
    "structural_project": {
        "description": "Boost structural formulas for structural projects",
        "conditions": [
            {"field": "project_type", "operator": "equals", "value": "structural"}
        ],
        "actions": [
            {"type": "boost_category", "params": {"category": "structural_analysis", "boost": 2.0}}
        ],
        "priority": 2,
    },
    "earthwork_project": {
        "description": "Boost earthwork formulas for earthwork projects",
        "conditions": [
            {"field": "project_type", "operator": "equals", "value": "earthwork"}
        ],
        "actions": [
            {"type": "boost_category", "params": {"category": "earthwork", "boost": 2.0}}
        ],
        "priority": 2,
    },
    "cost_phase": {
        "description": "Boost cost estimation during cost estimation phase",
        "conditions": [
            {"field": "workflow_phase", "operator": "equals", "value": "cost_estimation"}
        ],
        "actions": [
            {"type": "boost_category", "params": {"category": "cost_estimation", "boost": 3.0}}
        ],
        "priority": 1,
    },
    "rebar_elements": {
        "description": "Suggest rebar estimation when rebar elements detected",
        "conditions": [
            {"field": "elements", "operator": "contains", "value": "rebar"}
        ],
        "actions": [
            {"type": "suggest_template", "params": {"template_id": "rebar_weight_basic"}}
        ],
        "priority": 2,
    },
    "beam_elements": {
        "description": "Suggest beam formulas when beam elements detected",
        "conditions": [
            {"field": "elements", "operator": "contains", "value": "beam"}
        ],
        "actions": [
            {"type": "boost_tag", "params": {"tag": "beam", "boost": 2.0}}
        ],
        "priority": 3,
    },
    "column_elements": {
        "description": "Suggest column formulas when column elements detected",
        "conditions": [
            {"field": "elements", "operator": "contains", "value": "column"}
        ],
        "actions": [
            {"type": "boost_tag", "params": {"tag": "column", "boost": 2.0}}
        ],
        "priority": 3,
    },
    "excavation_context": {
        "description": "Suggest excavation formulas when excavation mentioned",
        "conditions": [
            {"field": "tags", "operator": "contains", "value": "excavation"}
        ],
        "actions": [
            {"type": "suggest_template", "params": {"template_id": "excavation_volume_basic"}}
        ],
        "priority": 2,
    },
    "high_budget": {
        "description": "Prioritize cost estimation for high-budget projects",
        "conditions": [
            {"field": "budget_tier", "operator": "equals", "value": "high"}
        ],
        "actions": [
            {"type": "boost_category", "params": {"category": "cost_estimation", "boost": 1.5}}
        ],
        "priority": 3,
    },
}


def get_rule_template(name: str) -> Optional[Dict[str, Any]]:
    """Get a predefined rule template."""
    return CONSTRUCTION_RULE_TEMPLATES.get(name)


def list_rule_templates() -> List[str]:
    """List available rule template names."""
    return list(CONSTRUCTION_RULE_TEMPLATES.keys())
