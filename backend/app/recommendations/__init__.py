"""
Recommendation Engine package for Cerebrum.

Provides template-based formula recommendations, context-aware suggestions,
user behavior tracking, and collaborative filtering.
"""

from app.recommendations.engine import RecommendationEngine
from app.recommendations.templates import TemplateManager
from app.recommendations.rules import RuleEngine
from app.recommendations.context import ContextAnalyzer
from app.recommendations.personalization import UserBehaviorTracker

__all__ = [
    "RecommendationEngine",
    "TemplateManager",
    "RuleEngine",
    "ContextAnalyzer",
    "UserBehaviorTracker",
]
