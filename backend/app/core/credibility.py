"""
Credibility System - 5-Tier Formula Source Ranking

Governs trust levels for formula sources and deployment autonomy.
Integrates with the validation pipeline to determine deployment workflow.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


class CredibilityTier(int, Enum):
    """
    5-Tier Credibility System
    
    Higher tier = more trust = more deployment autonomy
    """
    UNKNOWN = 5           # Tier 5: Unverified/Anonymous
    COMMUNITY = 4         # Tier 4: Open-source/Community
    PRACTITIONER = 3      # Tier 3: Certified domain experts
    INSTITUTIONAL = 2     # Tier 2: Government/Universities/Industry bodies
    VERIFIED_SCIENTIFIC = 1  # Tier 1: Peer-reviewed/Standards


@dataclass
class SourceCredibility:
    """Credibility profile for a formula source."""
    source_id: str
    source_name: str
    source_type: str
    tier: CredibilityTier
    verification_date: Optional[datetime] = None
    credentials: List[str] = None
    reputation_score: float = 0.0  # 0.0 to 1.0
    formulas_submitted: int = 0
    formulas_accepted: int = 0
    
    def __post_init__(self):
        if self.credentials is None:
            self.credentials = []


class CredibilitySystem:
    """
    5-Tier Credibility System
    
    Maps source types to credibility tiers and determines deployment workflow.
    """
    
    # Source type to tier mapping
    SOURCE_TYPE_TIERS = {
        # Tier 1: Verified Scientific
        "peer_reviewed_journal": CredibilityTier.VERIFIED_SCIENTIFIC,
        "iso_standard": CredibilityTier.VERIFIED_SCIENTIFIC,
        "iec_standard": CredibilityTier.VERIFIED_SCIENTIFIC,
        "ieee_standard": CredibilityTier.VERIFIED_SCIENTIFIC,
        "acm_publication": CredibilityTier.VERIFIED_SCIENTIFIC,
        "nature_publication": CredibilityTier.VERIFIED_SCIENTIFIC,
        "science_publication": CredibilityTier.VERIFIED_SCIENTIFIC,
        
        # Tier 2: Institutional
        "government_agency": CredibilityTier.INSTITUTIONAL,
        "university_lab": CredibilityTier.INSTITUTIONAL,
        "research_institute": CredibilityTier.INSTITUTIONAL,
        "industry_body": CredibilityTier.INSTITUTIONAL,
        "ashrae": CredibilityTier.INSTITUTIONAL,
        "astm": CredibilityTier.INSTITUTIONAL,
        "ansi": CredibilityTier.INSTITUTIONAL,
        "bsi": CredibilityTier.INSTITUTIONAL,
        "din": CredibilityTier.INSTITUTIONAL,
        
        # Tier 3: Practitioner
        "certified_engineer": CredibilityTier.PRACTITIONER,
        "professional_engineer": CredibilityTier.PRACTITIONER,
        "domain_expert": CredibilityTier.PRACTITIONER,
        "platform_verified": CredibilityTier.PRACTITIONER,
        
        # Tier 4: Community
        "open_source": CredibilityTier.COMMUNITY,
        "github_repo": CredibilityTier.COMMUNITY,
        "community_contribution": CredibilityTier.COMMUNITY,
        "third_party": CredibilityTier.COMMUNITY,
        
        # Tier 5: Unknown (default)
        "unknown": CredibilityTier.UNKNOWN,
        "anonymous": CredibilityTier.UNKNOWN,
        "unverified": CredibilityTier.UNKNOWN,
        "scraped": CredibilityTier.UNKNOWN,
    }
    
    # Tier configuration
    TIER_CONFIG = {
        CredibilityTier.VERIFIED_SCIENTIFIC: {
            "label": "Verified Scientific",
            "description": "Peer-reviewed journals, ISO/IEC/IEEE standards",
            "auto_deploy": True,
            "requires_review": False,
            "audit_log_required": True,
            "escalation_required": False,
            "approval_chain": ["system"],
        },
        CredibilityTier.INSTITUTIONAL: {
            "label": "Institutional",
            "description": "Government agencies, university labs, industry bodies (ASHRAE, ASTM)",
            "auto_deploy": True,
            "requires_review": False,
            "audit_log_required": True,
            "escalation_required": False,
            "approval_chain": ["system"],
        },
        CredibilityTier.PRACTITIONER: {
            "label": "Practitioner",
            "description": "Certified engineers, domain experts, platform verified users",
            "auto_deploy": True,
            "requires_review": True,  # Flagged for review but can deploy
            "audit_log_required": True,
            "escalation_required": False,
            "approval_chain": ["system", "moderator"],
        },
        CredibilityTier.COMMUNITY: {
            "label": "Community",
            "description": "Open-source contributions, unverified third parties",
            "auto_deploy": False,
            "requires_review": True,
            "audit_log_required": True,
            "escalation_required": False,
            "approval_chain": ["human_reviewer", "moderator"],
        },
        CredibilityTier.UNKNOWN: {
            "label": "Unknown / Unverified",
            "description": "Anonymous submissions, scraped formulas, unverified sources",
            "auto_deploy": False,
            "requires_review": True,
            "audit_log_required": True,
            "escalation_required": True,
            "approval_chain": ["security_review", "senior_moderator", "admin"],
        },
    }
    
    def __init__(self):
        self._source_cache: Dict[str, SourceCredibility] = {}
    
    def get_tier(self, source_type: str) -> CredibilityTier:
        """
        Get credibility tier for a source type.
        
        Args:
            source_type: Type of source (e.g., "peer_reviewed_journal", "open_source")
            
        Returns:
            CredibilityTier enum value
        """
        return self.SOURCE_TYPE_TIERS.get(source_type.lower(), CredibilityTier.UNKNOWN)
    
    def get_tier_config(self, tier: CredibilityTier) -> Dict[str, Any]:
        """Get configuration for a specific tier."""
        return self.TIER_CONFIG.get(tier, self.TIER_CONFIG[CredibilityTier.UNKNOWN])
    
    def can_auto_deploy(self, tier: CredibilityTier, validation_passed: bool = True) -> bool:
        """
        Determine if a formula can auto-deploy based on tier and validation.
        
        Args:
            tier: Credibility tier of the source
            validation_passed: Whether all validation stages passed
            
        Returns:
            True if auto-deployment is allowed
        """
        if not validation_passed:
            return False
        
        config = self.get_tier_config(tier)
        return config.get("auto_deploy", False)
    
    def get_required_approval(self, tier: CredibilityTier, validation_passed: bool = True) -> str:
        """
        Get the approval requirement for a tier.
        
        Args:
            tier: Credibility tier
            validation_passed: Whether validation passed
            
        Returns:
            Description of approval requirement
        """
        config = self.get_tier_config(tier)
        
        if not validation_passed:
            return "Validation failed - deployment blocked until all stages pass"
        
        if config["auto_deploy"] and not config["requires_review"]:
            return "Auto-deploy enabled (no human review required)"
        elif config["auto_deploy"] and config["requires_review"]:
            return "Auto-deploy with audit flag (review recommended)"
        else:
            return f"Human approval required via: {' → '.join(config['approval_chain'])}"
    
    def get_approval_chain(self, tier: CredibilityTier) -> List[str]:
        """Get the approval chain for a tier."""
        config = self.get_tier_config(tier)
        return config.get("approval_chain", ["admin"])
    
    def calculate_reputation(self, source: SourceCredibility) -> float:
        """
        Calculate reputation score based on formula history.
        
        Formula: accepted / submitted * tier_weight
        """
        if source.formulas_submitted == 0:
            return 0.0
        
        acceptance_rate = source.formulas_accepted / source.formulas_submitted
        tier_weight = 1.0 / source.tier.value  # Higher tier = higher weight
        
        return min(1.0, acceptance_rate * tier_weight * (1 + source.tier.value * 0.1))
    
    def upgrade_tier(self, source: SourceCredibility) -> Optional[CredibilityTier]:
        """
        Determine if a source should be upgraded based on performance.
        
        Uses reinforcement learning feedback - if a lower tier consistently
        outperforms higher tier benchmarks, upgrade their credibility.
        """
        reputation = self.calculate_reputation(source)
        
        # Upgrade logic
        if source.tier == CredibilityTier.UNKNOWN and reputation > 0.7:
            return CredibilityTier.COMMUNITY
        elif source.tier == CredibilityTier.COMMUNITY and reputation > 0.8:
            return CredibilityTier.PRACTITIONER
        elif source.tier == CredibilityTier.PRACTITIONER and reputation > 0.9:
            return CredibilityTier.INSTITUTIONAL
        
        return None  # No upgrade
    
    def get_deployment_decision(self, source_type: str, validation_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get complete deployment decision for a formula.
        
        Args:
            source_type: Type of formula source
            validation_report: Output from FormulaValidationPipeline
            
        Returns:
            Complete deployment decision with action, approval chain, and rationale
        """
        tier = self.get_tier(source_type)
        config = self.get_tier_config(tier)
        validation_passed = validation_report.get("can_deploy", False)
        
        auto_deploy = self.can_auto_deploy(tier, validation_passed)
        approval_required = not auto_deploy or (config["requires_review"] and validation_passed)
        
        decision = {
            "can_deploy": validation_passed,
            "auto_deploy": auto_deploy,
            "approval_required": approval_required,
            "escalation_required": config["escalation_required"],
            "tier": {
                "level": tier.value,
                "label": config["label"],
                "description": config["description"],
            },
            "approval_chain": self.get_approval_chain(tier) if approval_required else [],
            "rationale": self._generate_rationale(tier, validation_passed, config),
            "audit_log_required": config["audit_log_required"],
        }
        
        return decision
    
    def _generate_rationale(self, tier: CredibilityTier, validation_passed: bool, config: Dict) -> str:
        """Generate human-readable rationale for deployment decision."""
        if not validation_passed:
            return f"Formula failed validation. Fix issues before deployment."
        
        if tier == CredibilityTier.VERIFIED_SCIENTIFIC:
            return "Peer-reviewed source with full validation - auto-deploy enabled"
        elif tier == CredibilityTier.INSTITUTIONAL:
            return "Institutional source with full validation - auto-deploy with audit"
        elif tier == CredibilityTier.PRACTITIONER:
            return "Verified practitioner - auto-deploy with recommendation for spot-check review"
        elif tier == CredibilityTier.COMMUNITY:
            return "Community contribution requires human review before deployment"
        else:
            return "Unverified source requires security review and senior approval"
    
    def list_tiers(self) -> List[Dict[str, Any]]:
        """List all tiers with their configurations."""
        return [
            {
                "tier": tier.value,
                "label": config["label"],
                "description": config["description"],
                "auto_deploy": config["auto_deploy"],
                "requires_review": config["requires_review"],
            }
            for tier, config in self.TIER_CONFIG.items()
        ]


# Singleton instance
_credibility_system = None

def get_credibility_system() -> CredibilitySystem:
    """Get or create the credibility system singleton."""
    global _credibility_system
    if _credibility_system is None:
        _credibility_system = CredibilitySystem()
    return _credibility_system


def get_deployment_decision(source_type: str, validation_report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to get deployment decision.
    
    Args:
        source_type: Type of formula source
        validation_report: Validation report from pipeline
        
    Returns:
        Deployment decision dict
    """
    system = get_credibility_system()
    return system.get_deployment_decision(source_type, validation_report)
