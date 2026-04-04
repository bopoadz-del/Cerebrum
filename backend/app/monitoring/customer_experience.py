"""
Customer Experience Metrics
NPS, CSAT, CES surveys and feedback collection
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class SurveyType(Enum):
    """Types of customer surveys"""
    NPS = 'nps'  # Net Promoter Score
    CSAT = 'csat'  # Customer Satisfaction
    CES = 'ces'  # Customer Effort Score
    CUSTOM = 'custom'


class SurveyTrigger(Enum):
    """Survey trigger events"""
    AFTER_SUPPORT = 'after_support'
    AFTER_PURCHASE = 'after_purchase'
    AFTER_ONBOARDING = 'after_onboarding'
    PERIODIC = 'periodic'
    MANUAL = 'manual'


@dataclass
class SurveyResponse:
    """Survey response"""
    id: str
    survey_type: SurveyType
    user_id: str
    tenant_id: Optional[str]
    score: int
    feedback: Optional[str]
    timestamp: datetime
    trigger: SurveyTrigger
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['survey_type'] = self.survey_type.value
        data['trigger'] = self.trigger.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class SurveyConfig:
    """Survey configuration"""
    id: str
    survey_type: SurveyType
    name: str
    question: str
    scale_min: int
    scale_max: int
    triggers: List[SurveyTrigger]
    enabled: bool = True
    throttle_days: int = 30


class NPSCalculator:
    """Calculate Net Promoter Score"""
    
    @staticmethod
    def calculate(responses: List[int]) -> Dict[str, Any]:
        """Calculate NPS from responses (0-10 scale)"""
        if not responses:
            return {'nps': 0, 'promoters': 0, 'passives': 0, 'detractors': 0}
        
        promoters = sum(1 for r in responses if r >= 9)
        passives = sum(1 for r in responses if 7 <= r <= 8)
        detractors = sum(1 for r in responses if r <= 6)
        total = len(responses)
        
        nps = ((promoters - detractors) / total) * 100
        
        return {
            'nps': round(nps, 2),
            'promoters': promoters,
            'promoter_percent': round(promoters / total * 100, 2),
            'passives': passives,
            'passive_percent': round(passives / total * 100, 2),
            'detractors': detractors,
            'detractor_percent': round(detractors / total * 100, 2),
            'total_responses': total
        }


class CSATCalculator:
    """Calculate Customer Satisfaction Score"""
    
    @staticmethod
    def calculate(responses: List[int]) -> Dict[str, Any]:
        """Calculate CSAT from responses (1-5 scale)"""
        if not responses:
            return {'csat': 0, 'satisfied': 0, 'neutral': 0, 'dissatisfied': 0}
        
        satisfied = sum(1 for r in responses if r >= 4)
        neutral = sum(1 for r in responses if r == 3)
        dissatisfied = sum(1 for r in responses if r <= 2)
        total = len(responses)
        
        csat = (satisfied / total) * 100
        
        return {
            'csat': round(csat, 2),
            'satisfied': satisfied,
            'satisfied_percent': round(satisfied / total * 100, 2),
            'neutral': neutral,
            'neutral_percent': round(neutral / total * 100, 2),
            'dissatisfied': dissatisfied,
            'dissatisfied_percent': round(dissatisfied / total * 100, 2),
            'total_responses': total
        }


class CESCalculator:
    """Calculate Customer Effort Score"""
    
    @staticmethod
    def calculate(responses: List[int]) -> Dict[str, Any]:
        """Calculate CES from responses (1-7 scale)"""
        if not responses:
            return {'ces': 0, 'low_effort': 0, 'medium_effort': 0, 'high_effort': 0}
        
        low_effort = sum(1 for r in responses if r <= 2)  # 1-2: Easy
        medium_effort = sum(1 for r in responses if 3 <= r <= 5)  # 3-5: Neutral
        high_effort = sum(1 for r in responses if r >= 6)  # 6-7: Difficult
        total = len(responses)
        
        avg_score = sum(responses) / total
        
        return {
            'ces': round(avg_score, 2),
            'low_effort': low_effort,
            'low_effort_percent': round(low_effort / total * 100, 2),
            'medium_effort': medium_effort,
            'medium_effort_percent': round(medium_effort / total * 100, 2),
            'high_effort': high_effort,
            'high_effort_percent': round(high_effort / total * 100, 2),
            'total_responses': total
        }


class CustomerExperienceManager:
    """Manage customer experience surveys and metrics"""
    
    def __init__(self):
        self.responses: List[SurveyResponse] = []
        self.configs: Dict[str, SurveyConfig] = {}
        self.max_responses = 10000
        self._load_default_configs()
    
    def _load_default_configs(self):
        """Load default survey configurations"""
        default_configs = [
            SurveyConfig(
                id='nps-default',
                survey_type=SurveyType.NPS,
                name='Net Promoter Score',
                question='How likely are you to recommend Cerebrum AI to a friend or colleague?',
                scale_min=0,
                scale_max=10,
                triggers=[SurveyTrigger.PERIODIC, SurveyTrigger.AFTER_ONBOARDING]
            ),
            SurveyConfig(
                id='csat-support',
                survey_type=SurveyType.CSAT,
                name='Support Satisfaction',
                question='How satisfied were you with the support you received?',
                scale_min=1,
                scale_max=5,
                triggers=[SurveyTrigger.AFTER_SUPPORT]
            ),
            SurveyConfig(
                id='ces-onboarding',
                survey_type=SurveyType.CES,
                name='Onboarding Effort',
                question='How easy was it to get started with Cerebrum AI?',
                scale_min=1,
                scale_max=7,
                triggers=[SurveyTrigger.AFTER_ONBOARDING]
            )
        ]
        
        for config in default_configs:
            self.configs[config.id] = config
    
    def submit_response(self, response: SurveyResponse) -> str:
        """Submit a survey response"""
        self.responses.append(response)
        
        # Trim old responses
        if len(self.responses) > self.max_responses:
            self.responses = self.responses[-self.max_responses:]
        
        logger.info(f"Received {response.survey_type.value} response from user {response.user_id}")
        
        return response.id
    
    def get_nps(self, days: int = 30, tenant_id: str = None) -> Dict[str, Any]:
        """Get NPS for a period"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        responses = [
            r for r in self.responses
            if r.survey_type == SurveyType.NPS
            and r.timestamp > cutoff
            and (tenant_id is None or r.tenant_id == tenant_id)
        ]
        
        scores = [r.score for r in responses]
        
        return NPSCalculator.calculate(scores)
    
    def get_csat(self, days: int = 30, tenant_id: str = None) -> Dict[str, Any]:
        """Get CSAT for a period"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        responses = [
            r for r in self.responses
            if r.survey_type == SurveyType.CSAT
            and r.timestamp > cutoff
            and (tenant_id is None or r.tenant_id == tenant_id)
        ]
        
        scores = [r.score for r in responses]
        
        return CSATCalculator.calculate(scores)
    
    def get_ces(self, days: int = 30, tenant_id: str = None) -> Dict[str, Any]:
        """Get CES for a period"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        responses = [
            r for r in self.responses
            if r.survey_type == SurveyType.CES
            and r.timestamp > cutoff
            and (tenant_id is None or r.tenant_id == tenant_id)
        ]
        
        scores = [r.score for r in responses]
        
        return CESCalculator.calculate(scores)
    
    def get_experience_summary(self, days: int = 30, tenant_id: str = None) -> Dict[str, Any]:
        """Get overall customer experience summary"""
        return {
            'period_days': days,
            'nps': self.get_nps(days, tenant_id),
            'csat': self.get_csat(days, tenant_id),
            'ces': self.get_ces(days, tenant_id),
            'total_responses': len([
                r for r in self.responses
                if r.timestamp > datetime.utcnow() - timedelta(days=days)
                and (tenant_id is None or r.tenant_id == tenant_id)
            ])
        }
    
    def get_trends(self, metric: str, days: int = 90) -> List[Dict[str, Any]]:
        """Get metric trends over time"""
        survey_type = SurveyType(metric.lower())
        
        trends = []
        
        for day_offset in range(days):
            day_end = datetime.utcnow() - timedelta(days=day_offset)
            day_start = day_end - timedelta(days=1)
            
            day_responses = [
                r for r in self.responses
                if r.survey_type == survey_type
                and day_start <= r.timestamp <= day_end
            ]
            
            if day_responses:
                scores = [r.score for r in day_responses]
                
                if survey_type == SurveyType.NPS:
                    value = NPSCalculator.calculate(scores)['nps']
                elif survey_type == SurveyType.CSAT:
                    value = CSATCalculator.calculate(scores)['csat']
                else:
                    value = CESCalculator.calculate(scores)['ces']
                
                trends.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'value': value,
                    'responses': len(day_responses)
                })
        
        return list(reversed(trends))
    
    def should_show_survey(self, user_id: str, survey_type: SurveyType) -> bool:
        """Check if survey should be shown to user"""
        # Find config for survey type
        config = None
        for c in self.configs.values():
            if c.survey_type == survey_type:
                config = c
                break
        
        if not config or not config.enabled:
            return False
        
        # Check throttle
        cutoff = datetime.utcnow() - timedelta(days=config.throttle_days)
        
        recent_responses = [
            r for r in self.responses
            if r.user_id == user_id
            and r.survey_type == survey_type
            and r.timestamp > cutoff
        ]
        
        return len(recent_responses) == 0
    
    def get_feedback_analysis(self, days: int = 30) -> Dict[str, Any]:
        """Analyze feedback text"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        feedback_texts = [
            r.feedback for r in self.responses
            if r.feedback
            and r.timestamp > cutoff
        ]
        
        if not feedback_texts:
            return {'total_feedback': 0, 'themes': []}
        
        # Simple keyword analysis (would use NLP in production)
        keywords = {
            'feature': ['feature', 'functionality', 'capability'],
            'support': ['support', 'help', 'service'],
            'price': ['price', 'cost', 'expensive', 'cheap'],
            'ease': ['easy', 'simple', 'difficult', 'hard'],
            'performance': ['fast', 'slow', 'performance', 'speed']
        }
        
        themes = {theme: 0 for theme in keywords}
        
        for text in feedback_texts:
            text_lower = text.lower()
            for theme, words in keywords.items():
                if any(word in text_lower for word in words):
                    themes[theme] += 1
        
        return {
            'total_feedback': len(feedback_texts),
            'themes': [
                {'theme': theme, 'mentions': count}
                for theme, count in sorted(themes.items(), key=lambda x: x[1], reverse=True)
                if count > 0
            ]
        }


# Global customer experience manager
cx_manager = CustomerExperienceManager()
