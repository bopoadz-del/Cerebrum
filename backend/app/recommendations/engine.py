"""
Recommendation Engine - Main orchestrator for formula and workflow recommendations.

Combines template-based recommendations, symbolic rules, context awareness,
personalization, and collaborative filtering.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.core.logging import get_logger
from app.recommendations.templates import TemplateManager, FormulaTemplate
from app.recommendations.rules import RuleEngine, RuleCondition, RuleAction
from app.recommendations.context import ContextAnalyzer, ProjectContext
from app.recommendations.personalization import UserBehaviorTracker, UserProfile
from app.recommendations.models import (
    Recommendation,
    UserBehavior,
    RecommendationFeedback,
    get_db,
)

logger = get_logger(__name__)


class RecommendationType(str, Enum):
    """Types of recommendations."""
    FORMULA = "formula"
    WORKFLOW = "workflow"
    TEMPLATE = "template"
    SHORTCUT = "shortcut"


class RecommendationPriority(int, Enum):
    """Priority levels for recommendations."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


@dataclass
class RecommendationResult:
    """Result of a recommendation request."""
    id: str
    type: RecommendationType
    title: str
    description: str
    content: Dict[str, Any]
    priority: RecommendationPriority
    confidence: float
    reason: str
    context_match: float
    usage_count: int
    tags: List[str]


class RecommendationEngine:
    """
    Main recommendation engine for Cerebrum.
    
    Combines multiple recommendation strategies:
    1. Template-based: Pre-defined formula templates for construction domains
    2. Rule-based: Symbolic rules for contextual suggestions
    3. Context-aware: Recommendations based on current project context
    4. Personalization: Based on user's history and preferences
    5. Collaborative: Based on similar users' behaviors
    """
    
    def __init__(self):
        self.template_manager = TemplateManager()
        self.rule_engine = RuleEngine()
        self.context_analyzer = ContextAnalyzer()
        self.behavior_tracker = UserBehaviorTracker()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize all recommendation components."""
        if self._initialized:
            return
        
        logger.info("Initializing recommendation engine...")
        
        # Load templates
        await self.template_manager.load_templates()
        
        # Initialize rule engine with default rules
        self._setup_default_rules()
        
        self._initialized = True
        logger.info("Recommendation engine initialized")
    
    def _setup_default_rules(self) -> None:
        """Set up default recommendation rules."""
        # Rule: Concrete project -> suggest concrete formulas
        self.rule_engine.add_rule(
            name="concrete_project_formulas",
            conditions=[
                RuleCondition(
                    field="project_type",
                    operator="equals",
                    value="concrete"
                )
            ],
            actions=[
                RuleAction(
                    type="boost_category",
                    params={"category": "concrete", "boost": 2.0}
                )
            ],
            priority=RecommendationPriority.HIGH,
        )
        
        # Rule: Structural project -> suggest structural formulas
        self.rule_engine.add_rule(
            name="structural_project_formulas",
            conditions=[
                RuleCondition(
                    field="project_type",
                    operator="equals",
                    value="structural"
                )
            ],
            actions=[
                RuleAction(
                    type="boost_category",
                    params={"category": "structural_analysis", "boost": 2.0}
                )
            ],
            priority=RecommendationPriority.HIGH,
        )
        
        # Rule: Earthwork project -> suggest earthwork formulas
        self.rule_engine.add_rule(
            name="earthwork_project_formulas",
            conditions=[
                RuleCondition(
                    field="project_type",
                    operator="equals",
                    value="earthwork"
                )
            ],
            actions=[
                RuleAction(
                    type="boost_category",
                    params={"category": "earthwork", "boost": 2.0}
                )
            ],
            priority=RecommendationPriority.HIGH,
        )
        
        # Rule: High rebar usage -> suggest rebar estimation
        self.rule_engine.add_rule(
            name="rebar_usage_suggestion",
            conditions=[
                RuleCondition(
                    field="elements",
                    operator="contains",
                    value="rebar"
                )
            ],
            actions=[
                RuleAction(
                    type="suggest_template",
                    params={"template_id": "rebar_estimation_basic"}
                )
            ],
            priority=RecommendationPriority.MEDIUM,
        )
        
        # Rule: Cost estimation phase
        self.rule_engine.add_rule(
            name="cost_estimation_phase",
            conditions=[
                RuleCondition(
                    field="workflow_phase",
                    operator="equals",
                    value="cost_estimation"
                )
            ],
            actions=[
                RuleAction(
                    type="boost_category",
                    params={"category": "cost_estimation", "boost": 3.0}
                )
            ],
            priority=RecommendationPriority.CRITICAL,
        )
    
    async def get_recommendations(
        self,
        user_id: uuid.UUID,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        recommendation_type: Optional[RecommendationType] = None,
    ) -> List[RecommendationResult]:
        """
        Get personalized recommendations for a user.
        
        Args:
            user_id: User identifier
            context: Current project/workflow context
            limit: Maximum number of recommendations
            recommendation_type: Filter by recommendation type
            
        Returns:
            List of recommendation results sorted by relevance
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info(f"Getting recommendations for user {user_id}")
        
        # Analyze context
        project_context = self.context_analyzer.analyze(context or {})
        
        # Get user profile
        user_profile = await self.behavior_tracker.get_user_profile(user_id)
        
        # Collect candidates from different sources
        candidates = []
        
        # 1. Template-based recommendations
        template_candidates = await self._get_template_recommendations(
            project_context, user_profile
        )
        candidates.extend(template_candidates)
        
        # 2. Rule-based recommendations
        rule_candidates = self._get_rule_recommendations(
            project_context, user_profile
        )
        candidates.extend(rule_candidates)
        
        # 3. Personalized recommendations
        personalized_candidates = await self._get_personalized_recommendations(
            user_id, user_profile, project_context
        )
        candidates.extend(personalized_candidates)
        
        # 4. Collaborative filtering
        collaborative_candidates = await self._get_collaborative_recommendations(
            user_id, project_context
        )
        candidates.extend(collaborative_candidates)
        
        # Score and rank candidates
        scored_candidates = self._score_candidates(
            candidates, project_context, user_profile
        )
        
        # Apply diversity filter to avoid similar recommendations
        diverse_results = self._apply_diversity(scored_candidates, limit)
        
        # Track that recommendations were shown
        await self._track_recommendation_shown(user_id, diverse_results)
        
        return diverse_results
    
    async def _get_template_recommendations(
        self,
        context: ProjectContext,
        user_profile: UserProfile,
    ) -> List[RecommendationResult]:
        """Get recommendations from formula templates."""
        candidates = []
        
        # Get templates matching the context
        templates = self.template_manager.get_templates_for_context(
            project_type=context.project_type,
            tags=context.tags,
        )
        
        for template in templates:
            # Calculate context match score
            match_score = self._calculate_template_match(template, context)
            
            if match_score > 0.3:  # Minimum threshold
                candidates.append(RecommendationResult(
                    id=f"template:{template.id}",
                    type=RecommendationType.FORMULA,
                    title=template.name,
                    description=template.description,
                    content={
                        "template_id": template.id,
                        "formula": template.formula,
                        "inputs": template.inputs,
                        "outputs": template.outputs,
                        "category": template.category,
                    },
                    priority=RecommendationPriority.MEDIUM,
                    confidence=match_score,
                    reason=f"Matches {context.project_type} project context",
                    context_match=match_score,
                    usage_count=template.usage_count,
                    tags=template.tags,
                ))
        
        return candidates
    
    def _get_rule_recommendations(
        self,
        context: ProjectContext,
        user_profile: UserProfile,
    ) -> List[RecommendationResult]:
        """Get recommendations from rule engine."""
        candidates = []
        
        # Evaluate rules against context
        triggered_actions = self.rule_engine.evaluate({
            "project_type": context.project_type,
            "workflow_phase": context.workflow_phase,
            "elements": context.detected_elements,
            "tags": context.tags,
        })
        
        for action in triggered_actions:
            if action.type == "suggest_template":
                template_id = action.params.get("template_id")
                template = self.template_manager.get_template(template_id)
                
                if template:
                    candidates.append(RecommendationResult(
                        id=f"rule:{action.rule_name}:{template_id}",
                        type=RecommendationType.FORMULA,
                        title=template.name,
                        description=template.description,
                        content={
                            "template_id": template.id,
                            "formula": template.formula,
                            "inputs": template.inputs,
                            "outputs": template.outputs,
                            "triggered_by_rule": action.rule_name,
                        },
                        priority=action.priority,
                        confidence=0.85,
                        reason=f"Suggested by rule: {action.rule_name}",
                        context_match=0.9,
                        usage_count=template.usage_count,
                        tags=template.tags + ["rule-based"],
                    ))
        
        return candidates
    
    async def _get_personalized_recommendations(
        self,
        user_id: uuid.UUID,
        user_profile: UserProfile,
        context: ProjectContext,
    ) -> List[RecommendationResult]:
        """Get personalized recommendations based on user history."""
        candidates = []
        
        # Get user's frequently used templates
        frequent_templates = user_profile.get_frequent_templates(limit=5)
        
        for template_id, frequency in frequent_templates:
            template = self.template_manager.get_template(template_id)
            
            if template and template_id not in [c.content.get("template_id") for c in candidates]:
                # Boost score based on user familiarity
                confidence = min(0.5 + (frequency * 0.1), 0.95)
                
                candidates.append(RecommendationResult(
                    id=f"personalized:{template_id}",
                    type=RecommendationType.FORMULA,
                    title=f"{template.name} (Your Favorite)",
                    description=template.description,
                    content={
                        "template_id": template.id,
                        "formula": template.formula,
                        "inputs": template.inputs,
                        "outputs": template.outputs,
                        "frequency_of_use": frequency,
                    },
                    priority=RecommendationPriority.MEDIUM,
                    confidence=confidence,
                    reason=f"You've used this {frequency} times",
                    context_match=0.7,
                    usage_count=template.usage_count,
                    tags=template.tags + ["personalized"],
                ))
        
        return candidates
    
    async def _get_collaborative_recommendations(
        self,
        user_id: uuid.UUID,
        context: ProjectContext,
    ) -> List[RecommendationResult]:
        """Get recommendations based on similar users."""
        candidates = []
        
        # Find similar users
        similar_users = await self.behavior_tracker.get_similar_users(user_id, limit=5)
        
        # Aggregate their frequently used templates
        template_scores: Dict[str, Tuple[int, float]] = {}
        
        for similar_user_id, similarity_score in similar_users:
            similar_profile = await self.behavior_tracker.get_user_profile(similar_user_id)
            
            for template_id, frequency in similar_profile.get_frequent_templates(limit=3):
                if template_id not in template_scores:
                    template_scores[template_id] = (0, 0.0)
                
                count, score = template_scores[template_id]
                template_scores[template_id] = (
                    count + frequency,
                    score + (similarity_score * frequency),
                )
        
        # Create recommendations from aggregated scores
        for template_id, (count, total_score) in template_scores.items():
            template = self.template_manager.get_template(template_id)
            
            if template and count >= 2:  # Minimum usage threshold
                confidence = min(total_score / count, 0.9)
                
                candidates.append(RecommendationResult(
                    id=f"collaborative:{template_id}",
                    type=RecommendationType.FORMULA,
                    title=f"{template.name} (Trending)",
                    description=template.description,
                    content={
                        "template_id": template.id,
                        "formula": template.formula,
                        "inputs": template.inputs,
                        "outputs": template.outputs,
                        "similar_users_count": count,
                    },
                    priority=RecommendationPriority.LOW,
                    confidence=confidence,
                    reason=f"Popular among {count} similar users",
                    context_match=0.6,
                    usage_count=template.usage_count,
                    tags=template.tags + ["trending"],
                ))
        
        return candidates
    
    def _calculate_template_match(
        self,
        template: FormulaTemplate,
        context: ProjectContext,
    ) -> float:
        """Calculate how well a template matches the context."""
        scores = []
        
        # Category match
        if template.category == context.project_type:
            scores.append(1.0)
        elif template.category in context.tags:
            scores.append(0.8)
        
        # Tag overlap
        if template.tags and context.tags:
            overlap = len(set(template.tags) & set(context.tags))
            tag_score = overlap / max(len(template.tags), len(context.tags))
            scores.append(tag_score)
        
        # Element match
        if template.required_elements:
            matching_elements = len(
                set(template.required_elements) & set(context.detected_elements)
            )
            element_score = matching_elements / len(template.required_elements)
            scores.append(element_score)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _score_candidates(
        self,
        candidates: List[RecommendationResult],
        context: ProjectContext,
        user_profile: UserProfile,
    ) -> List[RecommendationResult]:
        """Score and sort candidate recommendations."""
        scored = []
        
        for candidate in candidates:
            # Base score from confidence
            score = candidate.confidence
            
            # Boost based on priority
            priority_boost = (6 - candidate.priority.value) * 0.1
            score += priority_boost
            
            # Boost based on popularity
            popularity_boost = min(candidate.usage_count / 100, 0.2)
            score += popularity_boost
            
            # Penalize recently shown items
            if candidate.id in user_profile.recently_shown:
                score *= 0.5
            
            # Create new result with final score
            scored.append(RecommendationResult(
                id=candidate.id,
                type=candidate.type,
                title=candidate.title,
                description=candidate.description,
                content=candidate.content,
                priority=candidate.priority,
                confidence=score,
                reason=candidate.reason,
                context_match=candidate.context_match,
                usage_count=candidate.usage_count,
                tags=candidate.tags,
            ))
        
        # Sort by confidence (descending)
        return sorted(scored, key=lambda x: x.confidence, reverse=True)
    
    def _apply_diversity(
        self,
        candidates: List[RecommendationResult],
        limit: int,
    ) -> List[RecommendationResult]:
        """Apply diversity filter to avoid too similar recommendations."""
        selected = []
        used_categories = set()
        used_template_ids = set()
        
        for candidate in candidates:
            template_id = candidate.content.get("template_id")
            category = candidate.content.get("category", "general")
            
            # Skip if same template already selected
            if template_id and template_id in used_template_ids:
                continue
            
            # Skip if too many from same category (max 3 per category)
            category_count = sum(
                1 for s in selected 
                if s.content.get("category") == category
            )
            if category_count >= 3:
                continue
            
            selected.append(candidate)
            if template_id:
                used_template_ids.add(template_id)
            used_categories.add(category)
            
            if len(selected) >= limit:
                break
        
        return selected
    
    async def record_feedback(
        self,
        user_id: uuid.UUID,
        recommendation_id: str,
        feedback_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record user feedback on a recommendation.
        
        Args:
            user_id: User identifier
            recommendation_id: ID of the recommendation
            feedback_type: Type of feedback (accepted, rejected, ignored)
            metadata: Additional feedback metadata
        """
        # Track in behavior tracker
        await self.behavior_tracker.record_interaction(
            user_id=user_id,
            item_id=recommendation_id,
            interaction_type=feedback_type,
            metadata=metadata or {},
        )
        
        # Store in database
        db = next(get_db())
        try:
            feedback = RecommendationFeedback(
                id=uuid.uuid4(),
                user_id=user_id,
                recommendation_id=recommendation_id,
                feedback_type=feedback_type,
                metadata=metadata or {},
            )
            db.add(feedback)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _track_recommendation_shown(
        self,
        user_id: uuid.UUID,
        recommendations: List[RecommendationResult],
    ) -> None:
        """Track that recommendations were shown to user."""
        for rec in recommendations:
            await self.behavior_tracker.record_interaction(
                user_id=user_id,
                item_id=rec.id,
                interaction_type="shown",
            )
    
    async def get_trending_templates(
        self,
        limit: int = 10,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Get trending templates based on recent usage."""
        return await self.behavior_tracker.get_trending_items(
            item_type="template",
            limit=limit,
            days=days,
        )
    
    async def get_user_preferences(
        self,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Get user preference insights."""
        profile = await self.behavior_tracker.get_user_profile(user_id)
        
        return {
            "favorite_categories": profile.get_favorite_categories(),
            "favorite_templates": profile.get_frequent_templates(limit=10),
            "activity_patterns": profile.get_activity_patterns(),
            "similar_users_count": len(
                await self.behavior_tracker.get_similar_users(user_id, limit=1)
            ),
        }


# Global engine instance
_recommendation_engine: Optional[RecommendationEngine] = None


async def get_recommendation_engine() -> RecommendationEngine:
    """Get or create the global recommendation engine."""
    global _recommendation_engine
    
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
        await _recommendation_engine.initialize()
    
    return _recommendation_engine
