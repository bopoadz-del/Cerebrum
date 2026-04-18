"""
Personalization and User Behavior Tracking

Tracks user interactions, preferences, and behavior patterns to
enable personalized recommendations and collaborative filtering.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.recommendations.models import (
    UserBehavior,
    UserSimilarity,
    get_db,
)

logger = get_logger(__name__)


@dataclass
class UserProfile:
    """User preference and behavior profile."""
    user_id: uuid.UUID
    template_usage: Dict[str, int] = field(default_factory=dict)
    category_preferences: Dict[str, float] = field(default_factory=dict)
    tag_preferences: Dict[str, float] = field(default_factory=dict)
    recently_shown: List[str] = field(default_factory=list)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_frequent_templates(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most frequently used templates."""
        sorted_usage = sorted(
            self.template_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_usage[:limit]
    
    def get_favorite_categories(self, limit: int = 5) -> List[Tuple[str, float]]:
        """Get preferred categories."""
        sorted_prefs = sorted(
            self.category_preferences.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_prefs[:limit]
    
    def get_activity_patterns(self) -> Dict[str, Any]:
        """Analyze user activity patterns."""
        if not self.interaction_history:
            return {"total_interactions": 0}
        
        # Time-based analysis
        hourly_distribution = defaultdict(int)
        daily_distribution = defaultdict(int)
        
        for interaction in self.interaction_history:
            timestamp = interaction.get("timestamp")
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                hourly_distribution[timestamp.hour] += 1
                daily_distribution[timestamp.weekday()] += 1
        
        # Interaction type distribution
        type_distribution = defaultdict(int)
        for interaction in self.interaction_history:
            type_distribution[interaction.get("type", "unknown")] += 1
        
        return {
            "total_interactions": len(self.interaction_history),
            "hourly_distribution": dict(hourly_distribution),
            "daily_distribution": dict(daily_distribution),
            "type_distribution": dict(type_distribution),
            "peak_hour": max(hourly_distribution, key=hourly_distribution.get) if hourly_distribution else None,
            "peak_day": max(daily_distribution, key=daily_distribution.get) if daily_distribution else None,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": str(self.user_id),
            "template_usage": self.template_usage,
            "category_preferences": self.category_preferences,
            "tag_preferences": self.tag_preferences,
            "recently_shown": self.recently_shown,
            "activity_patterns": self.get_activity_patterns(),
        }


class UserBehaviorTracker:
    """
    Tracks and analyzes user behavior for personalization.
    
    Features:
    - Interaction tracking (views, uses, ratings)
    - Preference inference from behavior
    - Similar user identification (collaborative filtering)
    - Activity pattern analysis
    """
    
    def __init__(self):
        self._profile_cache: Dict[uuid.UUID, UserProfile] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_timestamp: Dict[uuid.UUID, datetime] = {}
    
    async def record_interaction(
        self,
        user_id: uuid.UUID,
        item_id: str,
        interaction_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a user interaction.
        
        Args:
            user_id: User identifier
            item_id: Item that was interacted with (template, formula, etc.)
            interaction_type: Type of interaction (view, use, rate, dismiss)
            metadata: Additional interaction data
        """
        metadata = metadata or {}
        
        # Store in database
        db = next(get_db())
        try:
            behavior = UserBehavior(
                id=uuid.uuid4(),
                user_id=user_id,
                item_id=item_id,
                item_type=metadata.get("item_type", "template"),
                interaction_type=interaction_type,
                context=metadata.get("context", {}),
                duration_ms=metadata.get("duration_ms"),
                rating=metadata.get("rating"),
            )
            db.add(behavior)
            db.commit()
            
            logger.debug(
                f"Recorded interaction: {interaction_type} on {item_id} by {user_id}"
            )
        except Exception as e:
            logger.error(f"Failed to record interaction: {e}")
            db.rollback()
        finally:
            db.close()
        
        # Invalidate cache
        if user_id in self._profile_cache:
            del self._profile_cache[user_id]
        
        # If this is a template usage, update usage count
        if interaction_type in ["used", "accepted"] and "template_id" in item_id:
            await self._update_template_usage(item_id, user_id)
    
    async def _update_template_usage(
        self,
        item_id: str,
        user_id: uuid.UUID,
    ) -> None:
        """Update template usage statistics."""
        # Extract template ID from recommendation ID
        template_id = None
        if ":" in item_id:
            parts = item_id.split(":")
            if len(parts) >= 2:
                template_id = parts[-1]
        else:
            template_id = item_id
        
        if not template_id:
            return
        
        # Update in database would go here
        # For now, just log it
        logger.debug(f"Template {template_id} used by {user_id}")
    
    async def get_user_profile(self, user_id: uuid.UUID) -> UserProfile:
        """
        Get user behavior profile.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserProfile with aggregated behavior data
        """
        # Check cache
        if user_id in self._profile_cache:
            cache_time = self._cache_timestamp.get(user_id)
            if cache_time and datetime.utcnow() - cache_time < self._cache_ttl:
                return self._profile_cache[user_id]
        
        # Build profile from database
        profile = await self._build_profile_from_db(user_id)
        
        # Update cache
        self._profile_cache[user_id] = profile
        self._cache_timestamp[user_id] = datetime.utcnow()
        
        return profile
    
    async def _build_profile_from_db(self, user_id: uuid.UUID) -> UserProfile:
        """Build user profile from database records."""
        db = next(get_db())
        try:
            # Get recent interactions
            behaviors = db.query(UserBehavior).filter(
                UserBehavior.user_id == user_id
            ).order_by(UserBehavior.created_at.desc()).limit(1000).all()
            
            # Aggregate data
            template_usage: Dict[str, int] = defaultdict(int)
            category_prefs: Dict[str, List[float]] = defaultdict(list)
            tag_prefs: Dict[str, List[float]] = defaultdict(list)
            recently_shown: List[str] = []
            interaction_history: List[Dict[str, Any]] = []
            
            for behavior in behaviors:
                # Template usage
                if behavior.item_type == "template":
                    if behavior.interaction_type in ["used", "accepted"]:
                        template_usage[behavior.item_id] += 2
                    elif behavior.interaction_type == "viewed":
                        template_usage[behavior.item_id] += 1
                    elif behavior.interaction_type == "rejected":
                        template_usage[behavior.item_id] -= 1
                
                # Context-based preferences
                context = behavior.context or {}
                if "category" in context:
                    weight = 1.0
                    if behavior.interaction_type in ["used", "accepted"]:
                        weight = 2.0
                    elif behavior.interaction_type == "rejected":
                        weight = -0.5
                    category_prefs[context["category"]].append(weight)
                
                if "tags" in context:
                    for tag in context["tags"]:
                        weight = 1.0
                        if behavior.interaction_type in ["used", "accepted"]:
                            weight = 2.0
                        tag_prefs[tag].append(weight)
                
                # Recently shown
                if behavior.interaction_type == "shown":
                    recently_shown.append(behavior.item_id)
                
                # History
                interaction_history.append({
                    "type": behavior.interaction_type,
                    "item_id": behavior.item_id,
                    "timestamp": behavior.created_at.isoformat() if behavior.created_at else None,
                    "context": context,
                })
            
            # Calculate averages
            category_preferences = {
                cat: sum(weights) / len(weights)
                for cat, weights in category_prefs.items()
            }
            
            tag_preferences = {
                tag: sum(weights) / len(weights)
                for tag, weights in tag_prefs.items()
            }
            
            # Keep only recent shown items (last 50)
            recently_shown = recently_shown[:50]
            
            return UserProfile(
                user_id=user_id,
                template_usage=dict(template_usage),
                category_preferences=category_preferences,
                tag_preferences=tag_preferences,
                recently_shown=recently_shown,
                interaction_history=interaction_history,
            )
        
        except Exception as e:
            logger.error(f"Failed to build profile for {user_id}: {e}")
            return UserProfile(user_id=user_id)
        finally:
            db.close()
    
    async def get_similar_users(
        self,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Find users similar to the given user.
        
        Uses collaborative filtering based on template usage patterns.
        
        Args:
            user_id: User to find similar users for
            limit: Maximum number of similar users
            
        Returns:
            List of (user_id, similarity_score) tuples
        """
        # Get user's profile
        user_profile = await self.get_user_profile(user_id)
        
        if not user_profile.template_usage:
            return []
        
        # Get similar users from database
        db = next(get_db())
        try:
            # Find users with similar template usage
            similar_users = db.query(UserSimilarity).filter(
                UserSimilarity.user_id == user_id
            ).order_by(UserSimilarity.similarity_score.desc()).limit(limit).all()
            
            if similar_users:
                return [
                    (s.similar_user_id, s.similarity_score)
                    for s in similar_users
                ]
            
            # If no pre-calculated similarities, calculate on-the-fly
            # Get all users who used any of the same templates
            template_ids = list(user_profile.template_usage.keys())
            
            other_users = db.query(UserBehavior.user_id).filter(
                UserBehavior.item_id.in_(template_ids),
                UserBehavior.user_id != user_id,
                UserBehavior.interaction_type.in_(["used", "accepted"])
            ).distinct().all()
            
            similarities = []
            for (other_user_id,) in other_users:
                other_profile = await self.get_user_profile(other_user_id)
                similarity = self._calculate_similarity(user_profile, other_profile)
                if similarity > 0.1:  # Minimum threshold
                    similarities.append((other_user_id, similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities[:limit]
        
        except Exception as e:
            logger.error(f"Failed to get similar users for {user_id}: {e}")
            return []
        finally:
            db.close()
    
    def _calculate_similarity(
        self,
        profile1: UserProfile,
        profile2: UserProfile,
    ) -> float:
        """
        Calculate similarity between two user profiles.
        
        Uses Jaccard similarity for template usage and
        cosine similarity for category/tag preferences.
        """
        # Template usage similarity (Jaccard)
        templates1 = set(profile1.template_usage.keys())
        templates2 = set(profile2.template_usage.keys())
        
        if not templates1 or not templates2:
            template_similarity = 0.0
        else:
            intersection = len(templates1 & templates2)
            union = len(templates1 | templates2)
            template_similarity = intersection / union if union > 0 else 0.0
        
        # Category preference similarity (cosine-like)
        cat_similarity = self._preference_similarity(
            profile1.category_preferences,
            profile2.category_preferences,
        )
        
        # Tag preference similarity
        tag_similarity = self._preference_similarity(
            profile1.tag_preferences,
            profile2.tag_preferences,
        )
        
        # Weighted combination
        return (
            template_similarity * 0.5 +
            cat_similarity * 0.3 +
            tag_similarity * 0.2
        )
    
    def _preference_similarity(
        self,
        prefs1: Dict[str, float],
        prefs2: Dict[str, float],
    ) -> float:
        """Calculate similarity between preference dictionaries."""
        all_keys = set(prefs1.keys()) | set(prefs2.keys())
        
        if not all_keys:
            return 0.0
        
        # Simple correlation
        matches = 0
        total_diff = 0.0
        
        for key in all_keys:
            v1 = prefs1.get(key, 0)
            v2 = prefs2.get(key, 0)
            
            if v1 != 0 or v2 != 0:
                matches += 1
                total_diff += abs(v1 - v2)
        
        if matches == 0:
            return 0.0
        
        # Normalize: less difference = higher similarity
        avg_diff = total_diff / matches
        return max(0, 1 - (avg_diff / 2))
    
    async def get_trending_items(
        self,
        item_type: str = "template",
        limit: int = 10,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Get trending items based on recent usage.
        
        Args:
            item_type: Type of item to analyze
            limit: Maximum number of items
            days: Lookback period in days
            
        Returns:
            List of trending items with usage statistics
        """
        from_date = datetime.utcnow() - timedelta(days=days)
        
        db = next(get_db())
        try:
            # Get recent interactions
            behaviors = db.query(UserBehavior).filter(
                UserBehavior.item_type == item_type,
                UserBehavior.created_at >= from_date,
                UserBehavior.interaction_type.in_(["used", "accepted"])
            ).all()
            
            # Count usage
            item_counts: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
                "count": 0,
                "unique_users": set(),
            })
            
            for behavior in behaviors:
                item_counts[behavior.item_id]["count"] += 1
                item_counts[behavior.item_id]["unique_users"].add(behavior.user_id)
            
            # Calculate trending score
            trending = []
            for item_id, data in item_counts.items():
                # Score = usage count + unique user bonus
                score = data["count"] + len(data["unique_users"]) * 0.5
                trending.append({
                    "item_id": item_id,
                    "usage_count": data["count"],
                    "unique_users": len(data["unique_users"]),
                    "trending_score": score,
                })
            
            # Sort by trending score
            trending.sort(key=lambda x: x["trending_score"], reverse=True)
            
            return trending[:limit]
        
        except Exception as e:
            logger.error(f"Failed to get trending items: {e}")
            return []
        finally:
            db.close()
    
    async def calculate_all_similarities(self) -> int:
        """
        Batch calculate user similarities.
        
        This should be run periodically (e.g., daily) to update
        the similarity matrix for collaborative filtering.
        
        Returns:
            Number of similarity pairs calculated
        """
        db = next(get_db())
        calculated = 0
        
        try:
            # Get all active users
            user_ids = db.query(UserBehavior.user_id).distinct().all()
            user_ids = [uid for (uid,) in user_ids]
            
            # Calculate similarities for each pair
            for i, user_id in enumerate(user_ids):
                user_profile = await self.get_user_profile(user_id)
                
                for other_id in user_ids[i+1:]:
                    other_profile = await self.get_user_profile(other_id)
                    
                    similarity = self._calculate_similarity(user_profile, other_profile)
                    
                    if similarity > 0.1:
                        # Store both directions
                        for uid1, uid2 in [(user_id, other_id), (other_id, user_id)]:
                            existing = db.query(UserSimilarity).filter(
                                UserSimilarity.user_id == uid1,
                                UserSimilarity.similar_user_id == uid2
                            ).first()
                            
                            if existing:
                                existing.similarity_score = similarity
                                existing.updated_at = datetime.utcnow()
                            else:
                                similarity_record = UserSimilarity(
                                    id=uuid.uuid4(),
                                    user_id=uid1,
                                    similar_user_id=uid2,
                                    similarity_score=similarity,
                                )
                                db.add(similarity_record)
                            
                            calculated += 1
                
                if i % 100 == 0:
                    db.commit()
            
            db.commit()
            logger.info(f"Calculated {calculated} user similarity pairs")
            return calculated
        
        except Exception as e:
            logger.error(f"Failed to calculate similarities: {e}")
            db.rollback()
            return 0
        finally:
            db.close()


# Global tracker instance
_behavior_tracker: Optional[UserBehaviorTracker] = None


async def get_behavior_tracker() -> UserBehaviorTracker:
    """Get or create global behavior tracker."""
    global _behavior_tracker
    
    if _behavior_tracker is None:
        _behavior_tracker = UserBehaviorTracker()
    
    return _behavior_tracker
