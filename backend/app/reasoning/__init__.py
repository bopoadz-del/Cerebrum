"""
Heavy Reasoning Engine Module

SymPy-based merger for BOQ + Specs + Drawings.
Based on the Vietnam Doc architecture.
"""

from app.reasoning.engine import HeavyReasoningEngine, RiskLevel, VarianceResult, ComplianceCheck
from app.reasoning.integrations import IntegrationsEngine, MergedProjectData, MergedQuantityItem, MergedMaterialSpec
from app.reasoning.recommendations import RecommendationEngine, Recommendation, ActionType

__all__ = [
    "HeavyReasoningEngine",
    "RiskLevel",
    "VarianceResult",
    "ComplianceCheck",
    "IntegrationsEngine",
    "MergedProjectData",
    "MergedQuantityItem",
    "MergedMaterialSpec",
    "RecommendationEngine",
    "Recommendation",
    "ActionType",
]
