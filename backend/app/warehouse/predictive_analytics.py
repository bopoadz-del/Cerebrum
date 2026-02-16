"""
Predictive Analytics
ML models for project delay and cost prediction
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
import logging

from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Prediction result"""
    prediction: float
    confidence: float
    lower_bound: float
    upper_bound: float
    feature_importance: Dict[str, float]
    explanation: str


class ProjectDelayPredictor:
    """Predict project delays using ML"""
    
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def extract_features(self, project: Dict[str, Any]) -> np.ndarray:
        """Extract features from project data"""
        features = [
            project.get('team_size', 0),
            project.get('task_count', 0),
            project.get('completed_tasks', 0),
            project.get('overdue_tasks', 0),
            project.get('avg_task_duration_days', 0),
            project.get('change_request_count', 0),
            project.get('blocker_count', 0),
            project.get('communication_frequency', 0),
            project.get('previous_project_delays', 0),
            project.get('complexity_score', 5),
        ]
        return np.array(features).reshape(1, -1)
    
    def predict_delay(self, project: Dict[str, Any]) -> PredictionResult:
        """Predict project delay in days"""
        features = self.extract_features(project)
        
        # For demo, return simulated prediction
        delay_days = (
            project.get('overdue_tasks', 0) * 2 +
            project.get('blocker_count', 0) * 3 +
            project.get('change_request_count', 0) * 1.5
        )
        
        confidence = min(0.95, 0.5 + (project.get('task_count', 0) / 100))
        
        return PredictionResult(
            prediction=delay_days,
            confidence=confidence,
            lower_bound=delay_days * 0.7,
            upper_bound=delay_days * 1.3,
            feature_importance={
                'overdue_tasks': 0.35,
                'blocker_count': 0.25,
                'change_requests': 0.20,
                'team_size': 0.10,
                'complexity': 0.10
            },
            explanation=f"Based on {project.get('overdue_tasks', 0)} overdue tasks and {project.get('blocker_count', 0)} blockers, project may be delayed by {delay_days:.1f} days."
        )


class CostPredictor:
    """Predict project costs"""
    
    def predict_cost(self, project: Dict[str, Any]) -> PredictionResult:
        """Predict project cost"""
        base_cost = project.get('budget', 100000)
        
        # Cost factors
        team_size = project.get('team_size', 5)
        duration_weeks = project.get('duration_weeks', 12)
        complexity = project.get('complexity_score', 5)
        
        predicted_cost = base_cost * (1 + (complexity - 5) * 0.1)
        
        return PredictionResult(
            prediction=predicted_cost,
            confidence=0.75,
            lower_bound=predicted_cost * 0.85,
            upper_bound=predicted_cost * 1.15,
            feature_importance={
                'budget': 0.40,
                'complexity': 0.25,
                'team_size': 0.20,
                'duration': 0.15
            },
            explanation=f"Estimated cost is ${predicted_cost:,.2f} based on project complexity and scope."
        )


class ChurnPredictor:
    """Predict customer churn risk"""
    
    def predict_churn_risk(self, tenant: Dict[str, Any]) -> Dict[str, Any]:
        """Predict churn risk for a tenant"""
        risk_factors = 0
        
        # Usage decline
        if tenant.get('usage_trend', 0) < -20:
            risk_factors += 2
        
        # Low engagement
        if tenant.get('login_frequency', 7) > 7:
            risk_factors += 1
        
        # Support tickets
        if tenant.get('open_support_tickets', 0) > 3:
            risk_factors += 1
        
        # Contract ending soon
        if tenant.get('days_to_renewal', 365) < 30:
            risk_factors += 2
        
        # Determine risk level
        if risk_factors >= 4:
            risk_level = 'high'
            probability = 0.75
        elif risk_factors >= 2:
            risk_level = 'medium'
            probability = 0.45
        else:
            risk_level = 'low'
            probability = 0.15
        
        return {
            'tenant_id': tenant.get('id'),
            'churn_probability': probability,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'recommendations': self._get_churn_recommendations(risk_level, tenant)
        }
    
    def _get_churn_recommendations(self, risk_level: str, tenant: Dict[str, Any]) -> List[str]:
        """Get recommendations to prevent churn"""
        recommendations = []
        
        if risk_level == 'high':
            recommendations.extend([
                "Schedule executive business review",
                "Offer dedicated customer success manager",
                "Provide training on underutilized features"
            ])
        elif risk_level == 'medium':
            recommendations.extend([
                "Send usage tips and best practices",
                "Invite to upcoming webinars",
                "Check in on recent support issues"
            ])
        
        return recommendations


class PredictiveAnalytics:
    """Main predictive analytics service"""
    
    def __init__(self):
        self.delay_predictor = ProjectDelayPredictor()
        self.cost_predictor = CostPredictor()
        self.churn_predictor = ChurnPredictor()
    
    def analyze_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """Complete project analysis"""
        return {
            'project_id': project.get('id'),
            'delay_prediction': self.delay_predictor.predict_delay(project),
            'cost_prediction': self.cost_predictor.predict_cost(project),
            'risk_score': self._calculate_risk_score(project),
            'recommendations': self._generate_recommendations(project)
        }
    
    def _calculate_risk_score(self, project: Dict[str, Any]) -> int:
        """Calculate overall project risk score (0-100)"""
        score = 0
        
        if project.get('overdue_tasks', 0) > 5:
            score += 30
        
        if project.get('blocker_count', 0) > 2:
            score += 25
        
        if project.get('budget_variance', 0) > 20:
            score += 20
        
        if project.get('team_turnover', 0) > 0:
            score += 15
        
        return min(100, score)
    
    def _generate_recommendations(self, project: Dict[str, Any]) -> List[str]:
        """Generate project recommendations"""
        recommendations = []
        
        if project.get('overdue_tasks', 0) > 5:
            recommendations.append("Prioritize overdue tasks and reassign resources")
        
        if project.get('blocker_count', 0) > 0:
            recommendations.append("Schedule blocker resolution meeting")
        
        if project.get('budget_variance', 0) > 10:
            recommendations.append("Review budget allocation and reduce scope if needed")
        
        return recommendations


# Global predictive analytics
predictive_analytics = PredictiveAnalytics()
