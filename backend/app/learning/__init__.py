"""
Learning Engine Service for Cerebrum

ML-based learning system for:
- Tier promotion/demotion logic (5-tier credibility system)
- Coefficient auto-tuning based on formula performance
- Feedback loop from formula execution results
- Model performance tracking and scoring
- Reinforcement learning for formula suggestions
"""

from .engine import LearningEngine, get_learning_engine
from .tier_manager import TierManager, get_tier_manager
from .coefficient_tuner import CoefficientTuner, get_coefficient_tuner
from .models import (
    LearningModel,
    FormulaPerformance,
    TierHistory,
    CoefficientAdjustment,
    FeedbackLoop,
    ReinforcementEpisode,
)

__all__ = [
    "LearningEngine",
    "get_learning_engine",
    "TierManager",
    "get_tier_manager",
    "CoefficientTuner",
    "get_coefficient_tuner",
    "LearningModel",
    "FormulaPerformance",
    "TierHistory",
    "CoefficientAdjustment",
    "FeedbackLoop",
    "ReinforcementEpisode",
]
