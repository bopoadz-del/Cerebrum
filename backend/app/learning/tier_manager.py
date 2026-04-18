"""
Tier Manager - Promotion/Demotion Logic

Manages the 5-tier credibility system with intelligent promotion
and demotion decisions based on formula performance and learning signals.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.credibility import (
    CredibilitySystem,
    CredibilityTier,
    SourceCredibility,
    get_credibility_system,
)
from app.core.logging import get_logger
from app.learning.models import (
    TierHistory,
    FormulaPerformance,
    SourceReputation,
    TierChangeType,
)

logger = get_logger(__name__)


@dataclass
class TierDecision:
    """Decision result for tier change."""
    source_id: str
    current_tier: int
    proposed_tier: int
    change_type: TierChangeType
    confidence: float
    reason: str
    should_change: bool


class TierManager:
    """
    Manages tier promotion and demotion logic.
    
    Integrates with:
    - CredibilitySystem for tier definitions
    - FormulaPerformance for performance data
    - TierHistory for audit trail
    """
    
    # Tier thresholds (performance score required for promotion)
    PROMOTION_THRESHOLDS = {
        CredibilityTier.UNKNOWN: 0.65,      # To Community
        CredibilityTier.COMMUNITY: 0.75,    # To Practitioner
        CredibilityTier.PRACTITIONER: 0.85, # To Institutional
        CredibilityTier.INSTITUTIONAL: 0.92, # To Verified Scientific
        CredibilityTier.VERIFIED_SCIENTIFIC: 1.0, # Cannot promote further
    }
    
    # Demotion thresholds (performance score that triggers demotion)
    DEMOTION_THRESHOLDS = {
        CredibilityTier.VERIFIED_SCIENTIFIC: 0.80,
        CredibilityTier.INSTITUTIONAL: 0.70,
        CredibilityTier.PRACTITIONER: 0.60,
        CredibilityTier.COMMUNITY: 0.50,
        CredibilityTier.UNKNOWN: 0.0,  # Cannot demote further
    }
    
    # Minimum executions before tier evaluation
    MIN_EXECUTIONS_FOR_EVAL = 10
    
    # Minimum time in tier before promotion (days)
    MIN_TIME_IN_TIER_DAYS = {
        CredibilityTier.UNKNOWN: 7,
        CredibilityTier.COMMUNITY: 14,
        CredibilityTier.PRACTITIONER: 30,
        CredibilityTier.INSTITUTIONAL: 60,
        CredibilityTier.VERIFIED_SCIENTIFIC: 90,
    }
    
    def __init__(self, credibility_system: Optional[CredibilitySystem] = None):
        self.credibility_system = credibility_system or get_credibility_system()
        self._cache: Dict[str, SourceReputation] = {}
    
    async def evaluate_source(
        self,
        source_id: str,
        db_session: AsyncSession,
        force: bool = False
    ) -> TierDecision:
        """
        Evaluate a source for potential tier change.
        
        Args:
            source_id: The source to evaluate
            db_session: Database session
            force: Force evaluation even if minimum criteria not met
            
        Returns:
            TierDecision with recommendation
        """
        # Get source reputation
        reputation = await self._get_source_reputation(source_id, db_session)
        if not reputation:
            return TierDecision(
                source_id=source_id,
                current_tier=CredibilityTier.UNKNOWN.value,
                proposed_tier=CredibilityTier.UNKNOWN.value,
                change_type=TierChangeType.MAINTAINED,
                confidence=0.0,
                reason="Source not found in reputation system",
                should_change=False
            )
        
        current_tier = CredibilityTier(reputation.current_tier)
        
        # Check minimum criteria
        if not force and not self._meets_minimum_criteria(reputation):
            return TierDecision(
                source_id=source_id,
                current_tier=current_tier.value,
                proposed_tier=current_tier.value,
                change_type=TierChangeType.MAINTAINED,
                confidence=0.0,
                reason="Insufficient data for evaluation",
                should_change=False
            )
        
        # Calculate reputation score
        reputation_score = reputation.calculate_reputation()
        
        # Determine if promotion or demotion is warranted
        decision = self._evaluate_tier_change(
            source_id=source_id,
            reputation=reputation,
            current_tier=current_tier,
            score=reputation_score
        )
        
        return decision
    
    async def process_tier_change(
        self,
        decision: TierDecision,
        db_session: AsyncSession,
        triggered_by: str = "system"
    ) -> bool:
        """
        Process an approved tier change.
        
        Args:
            decision: TierDecision with change details
            db_session: Database session
            triggered_by: Who/what triggered the change
            
        Returns:
            True if change was successful
        """
        if not decision.should_change:
            return False
        
        try:
            # Get source reputation
            reputation = await self._get_source_reputation(decision.source_id, db_session)
            if not reputation:
                logger.warning(f"Source {decision.source_id} not found for tier change")
                return False
            
            # Create tier history record
            tier_history = TierHistory(
                source_id=decision.source_id,
                source_name=reputation.source_name,
                source_type=reputation.source_type,
                previous_tier=decision.current_tier,
                new_tier=decision.proposed_tier,
                change_type=decision.change_type,
                performance_score=reputation.avg_performance_score,
                formulas_submitted=reputation.formulas_submitted,
                formulas_accepted=reputation.formulas_accepted,
                change_reason=decision.reason,
                triggered_by=triggered_by,
                reputation_score=reputation.reputation_score,
                acceptance_rate=reputation.acceptance_rate,
            )
            
            db_session.add(tier_history)
            
            # Update source reputation
            reputation.current_tier = decision.proposed_tier
            reputation.tier_changes += 1
            reputation.last_tier_change = datetime.utcnow()
            reputation.tier_since = datetime.utcnow()
            
            await db_session.flush()
            
            logger.info(
                f"Tier change processed: {decision.source_id} "
                f"Tier {decision.current_tier} -> {decision.proposed_tier} "
                f"({decision.change_type.value})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process tier change: {e}")
            await db_session.rollback()
            return False
    
    async def batch_evaluate(
        self,
        db_session: AsyncSession,
        tier_filter: Optional[CredibilityTier] = None,
        limit: int = 100
    ) -> List[TierDecision]:
        """
        Batch evaluate sources for tier changes.
        
        Args:
            db_session: Database session
            tier_filter: Only evaluate sources in this tier
            limit: Maximum sources to evaluate
            
        Returns:
            List of TierDecisions
        """
        # Get sources to evaluate
        query = select(SourceReputation)
        
        if tier_filter:
            query = query.where(SourceReputation.current_tier == tier_filter.value)
        
        # Prioritize sources with recent activity
        query = query.where(
            SourceReputation.total_executions >= self.MIN_EXECUTIONS_FOR_EVAL
        ).order_by(desc(SourceReputation.total_executions))
        
        query = query.limit(limit)
        
        result = await db_session.execute(query)
        sources = result.scalars().all()
        
        # Evaluate each source
        decisions = []
        for source in sources:
            decision = await self.evaluate_source(source.source_id, db_session)
            decisions.append(decision)
        
        return decisions
    
    async def auto_promote_eligible(
        self,
        db_session: AsyncSession,
        confidence_threshold: float = 0.8
    ) -> List[TierDecision]:
        """
        Automatically promote sources that meet criteria.
        
        Args:
            db_session: Database session
            confidence_threshold: Minimum confidence to auto-promote
            
        Returns:
            List of successful promotions
        """
        decisions = await self.batch_evaluate(db_session)
        
        promotions = []
        for decision in decisions:
            if (decision.change_type == TierChangeType.PROMOTION and 
                decision.confidence >= confidence_threshold):
                
                success = await self.process_tier_change(
                    decision, db_session, triggered_by="system_auto"
                )
                
                if success:
                    promotions.append(decision)
        
        await db_session.commit()
        return promotions
    
    async def flag_for_review(
        self,
        source_id: str,
        reason: str,
        db_session: AsyncSession
    ) -> bool:
        """
        Flag a source for manual tier review.
        
        Args:
            source_id: Source to flag
            reason: Review reason
            db_session: Database session
            
        Returns:
            True if flagged successfully
        """
        reputation = await self._get_source_reputation(source_id, db_session)
        if not reputation:
            return False
        
        reputation.under_review = True
        reputation.review_reason = reason
        
        await db_session.flush()
        return True
    
    async def manual_tier_change(
        self,
        source_id: str,
        new_tier: int,
        reason: str,
        admin_id: str,
        db_session: AsyncSession
    ) -> Optional[TierHistory]:
        """
        Manual tier change by administrator.
        
        Args:
            source_id: Source to change
            new_tier: New tier level (1-5)
            reason: Change reason
            admin_id: Admin user ID
            db_session: Database session
            
        Returns:
            Created TierHistory record
        """
        reputation = await self._get_source_reputation(source_id, db_session)
        if not reputation:
            return None
        
        if not 1 <= new_tier <= 5:
            raise ValueError("Tier must be between 1 and 5")
        
        old_tier = reputation.current_tier
        
        # Determine change type
        if new_tier < old_tier:
            change_type = TierChangeType.PROMOTION
        elif new_tier > old_tier:
            change_type = TierChangeType.DEMOTION
        else:
            change_type = TierChangeType.MAINTAINED
        
        # Create history record
        tier_history = TierHistory(
            source_id=source_id,
            source_name=reputation.source_name,
            source_type=reputation.source_type,
            previous_tier=old_tier,
            new_tier=new_tier,
            change_type=TierChangeType.MANUAL_OVERRIDE,
            performance_score=reputation.avg_performance_score,
            formulas_submitted=reputation.formulas_submitted,
            formulas_accepted=reputation.formulas_accepted,
            change_reason=f"Manual override by {admin_id}: {reason}",
            triggered_by=f"admin:{admin_id}",
            reputation_score=reputation.reputation_score,
            acceptance_rate=reputation.acceptance_rate,
        )
        
        db_session.add(tier_history)
        
        # Update reputation
        reputation.current_tier = new_tier
        reputation.tier_changes += 1
        reputation.last_tier_change = datetime.utcnow()
        reputation.tier_since = datetime.utcnow()
        reputation.under_review = False
        reputation.review_reason = None
        
        await db_session.flush()
        return tier_history
    
    async def get_tier_history(
        self,
        source_id: str,
        db_session: AsyncSession,
        limit: int = 50
    ) -> List[TierHistory]:
        """
        Get tier change history for a source.
        
        Args:
            source_id: Source ID
            db_session: Database session
            limit: Maximum records to return
            
        Returns:
            List of TierHistory records
        """
        query = select(TierHistory).where(
            TierHistory.source_id == source_id
        ).order_by(desc(TierHistory.created_at)).limit(limit)
        
        result = await db_session.execute(query)
        return list(result.scalars().all())
    
    async def get_sources_by_tier(
        self,
        tier: CredibilityTier,
        db_session: AsyncSession,
        include_under_review: bool = False,
        limit: int = 100
    ) -> List[SourceReputation]:
        """
        Get all sources in a specific tier.
        
        Args:
            tier: Credibility tier
            db_session: Database session
            include_under_review: Include sources under review
            limit: Maximum sources to return
            
        Returns:
            List of SourceReputation records
        """
        query = select(SourceReputation).where(
            SourceReputation.current_tier == tier.value
        )
        
        if not include_under_review:
            query = query.where(SourceReputation.under_review == False)
        
        query = query.order_by(desc(SourceReputation.reputation_score)).limit(limit)
        
        result = await db_session.execute(query)
        return list(result.scalars().all())
    
    async def _get_source_reputation(
        self,
        source_id: str,
        db_session: AsyncSession
    ) -> Optional[SourceReputation]:
        """Get or create source reputation record."""
        # Check cache
        if source_id in self._cache:
            return self._cache[source_id]
        
        query = select(SourceReputation).where(SourceReputation.source_id == source_id)
        result = await db_session.execute(query)
        reputation = result.scalar_one_or_none()
        
        if reputation:
            self._cache[source_id] = reputation
        
        return reputation
    
    def _meets_minimum_criteria(self, reputation: SourceReputation) -> bool:
        """Check if source meets minimum criteria for tier evaluation."""
        # Minimum executions
        if reputation.total_executions < self.MIN_EXECUTIONS_FOR_EVAL:
            return False
        
        # Minimum time in current tier
        current_tier = CredibilityTier(reputation.current_tier)
        min_days = self.MIN_TIME_IN_TIER_DAYS.get(current_tier, 30)
        
        days_in_tier = (datetime.utcnow() - reputation.tier_since).days
        if days_in_tier < min_days:
            return False
        
        return True
    
    def _evaluate_tier_change(
        self,
        source_id: str,
        reputation: SourceReputation,
        current_tier: CredibilityTier,
        score: float
    ) -> TierDecision:
        """
        Evaluate whether tier change is warranted.
        
        Args:
            source_id: Source being evaluated
            reputation: Source reputation data
            current_tier: Current credibility tier
            score: Calculated reputation score
            
        Returns:
            TierDecision with recommendation
        """
        # Check promotion threshold
        promotion_threshold = self.PROMOTION_THRESHOLDS.get(current_tier, 1.0)
        demotion_threshold = self.DEMOTION_THRESHOLDS.get(current_tier, 0.0)
        
        # Determine if promotion is warranted
        if score >= promotion_threshold and current_tier != CredibilityTier.VERIFIED_SCIENTIFIC:
            next_tier = self._get_next_tier(current_tier)
            confidence = min(1.0, (score - promotion_threshold) / (1.0 - promotion_threshold))
            
            return TierDecision(
                source_id=source_id,
                current_tier=current_tier.value,
                proposed_tier=next_tier.value,
                change_type=TierChangeType.PROMOTION,
                confidence=confidence,
                reason=(
                    f"Performance score {score:.2f} exceeds promotion threshold "
                    f"({promotion_threshold:.2f}). Acceptance rate: {reputation.acceptance_rate:.2%}, "
                    f"Formulas accepted: {reputation.formulas_accepted}/{reputation.formulas_submitted}"
                ),
                should_change=True
            )
        
        # Determine if demotion is warranted
        elif score <= demotion_threshold and current_tier != CredibilityTier.UNKNOWN:
            prev_tier = self._get_previous_tier(current_tier)
            confidence = min(1.0, (demotion_threshold - score) / demotion_threshold)
            
            return TierDecision(
                source_id=source_id,
                current_tier=current_tier.value,
                proposed_tier=prev_tier.value,
                change_type=TierChangeType.DEMOTION,
                confidence=confidence,
                reason=(
                    f"Performance score {score:.2f} below demotion threshold "
                    f"({demotion_threshold:.2f}). Recent performance indicates quality degradation."
                ),
                should_change=True
            )
        
        # Maintain current tier
        return TierDecision(
            source_id=source_id,
            current_tier=current_tier.value,
            proposed_tier=current_tier.value,
            change_type=TierChangeType.MAINTAINED,
            confidence=0.5,
            reason=f"Performance score {score:.2f} within acceptable range for current tier",
            should_change=False
        )
    
    def _get_next_tier(self, current: CredibilityTier) -> CredibilityTier:
        """Get the next higher tier."""
        tier_order = [
            CredibilityTier.UNKNOWN,
            CredibilityTier.COMMUNITY,
            CredibilityTier.PRACTITIONER,
            CredibilityTier.INSTITUTIONAL,
            CredibilityTier.VERIFIED_SCIENTIFIC,
        ]
        
        current_idx = tier_order.index(current)
        if current_idx < len(tier_order) - 1:
            return tier_order[current_idx + 1]
        return current
    
    def _get_previous_tier(self, current: CredibilityTier) -> CredibilityTier:
        """Get the next lower tier."""
        tier_order = [
            CredibilityTier.UNKNOWN,
            CredibilityTier.COMMUNITY,
            CredibilityTier.PRACTITIONER,
            CredibilityTier.INSTITUTIONAL,
            CredibilityTier.VERIFIED_SCIENTIFIC,
        ]
        
        current_idx = tier_order.index(current)
        if current_idx > 0:
            return tier_order[current_idx - 1]
        return current
    
    async def get_tier_statistics(
        self,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Get statistics about tiers across the system.
        
        Args:
            db_session: Database session
            
        Returns:
            Statistics dictionary
        """
        from sqlalchemy import func
        
        # Count sources by tier
        query = select(
            SourceReputation.current_tier,
            func.count().label("count"),
            func.avg(SourceReputation.reputation_score).label("avg_score"),
            func.sum(SourceReputation.total_executions).label("total_executions"),
        ).group_by(SourceReputation.current_tier)
        
        result = await db_session.execute(query)
        
        tier_stats = {}
        for row in result.all():
            tier = CredibilityTier(row[0])
            tier_stats[tier.name] = {
                "tier_level": row[0],
                "source_count": row[1],
                "avg_reputation_score": round(row[2] or 0, 3),
                "total_executions": row[3] or 0,
            }
        
        # Recent tier changes
        changes_query = select(
            TierHistory.change_type,
            func.count().label("count")
        ).where(
            TierHistory.created_at >= datetime.utcnow() - timedelta(days=30)
        ).group_by(TierHistory.change_type)
        
        changes_result = await db_session.execute(changes_query)
        recent_changes = {row[0].value: row[1] for row in changes_result.all()}
        
        return {
            "tier_distribution": tier_stats,
            "recent_changes_30d": recent_changes,
            "total_sources": sum(s["source_count"] for s in tier_stats.values()),
            "total_executions": sum(s["total_executions"] for s in tier_stats.values()),
        }


# Singleton instance
_tier_manager: Optional[TierManager] = None


def get_tier_manager(
    credibility_system: Optional[CredibilitySystem] = None
) -> TierManager:
    """Get or create tier manager singleton."""
    global _tier_manager
    if _tier_manager is None:
        _tier_manager = TierManager(credibility_system=credibility_system)
    return _tier_manager
