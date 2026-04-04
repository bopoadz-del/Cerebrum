"""
Model explainability with SHAP and LIME integration.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import uuid
import json


class ExplanationMethod(Enum):
    """Supported explanation methods."""
    SHAP = "shap"
    LIME = "lime"
    INTEGRATED_GRADIENTS = "integrated_gradients"
    ATTENTION = "attention"
    FEATURE_IMPORTANCE = "feature_importance"


@dataclass
class FeatureContribution:
    """Contribution of a single feature."""
    feature_name: str
    value: float
    contribution: float
    base_value: float
    description: str = ""


@dataclass
class Explanation:
    """Model explanation for a prediction."""
    explanation_id: str
    model_name: str
    model_version: str
    input_data: Dict[str, Any]
    prediction: Any
    method: ExplanationMethod
    feature_contributions: List[FeatureContribution]
    base_value: float
    predicted_value: float
    confidence: Optional[float] = None
    visualization_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class GlobalExplanation:
    """Global model explanation."""
    model_name: str
    model_version: str
    method: ExplanationMethod
    feature_importance: Dict[str, float]
    feature_interactions: List[Dict[str, Any]]
    summary_statistics: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


class ExplainabilityEngine:
    """Generate explanations for ML model predictions."""
    
    def __init__(self):
        self._explainers: Dict[str, Any] = {}
        self._explanation_cache: Dict[str, Explanation] = {}
    
    async def initialize_explainer(
        self,
        model_name: str,
        model_version: str,
        method: ExplanationMethod,
        model: Any,
        background_data: Optional[Any] = None
    ):
        """Initialize an explainer for a model."""
        
        key = f"{model_name}:{model_version}:{method.value}"
        
        if method == ExplanationMethod.SHAP:
            try:
                import shap
                explainer = shap.Explainer(model, background_data)
                self._explainers[key] = explainer
            except ImportError:
                raise RuntimeError("SHAP not installed")
        
        elif method == ExplanationMethod.LIME:
            try:
                from lime import lime_tabular
                explainer = lime_tabular.LimeTabularExplainer(background_data)
                self._explainers[key] = explainer
            except ImportError:
                raise RuntimeError("LIME not installed")
        
        elif method == ExplanationMethod.FEATURE_IMPORTANCE:
            # Built-in feature importance
            self._explainers[key] = {"type": "feature_importance", "model": model}
    
    async def explain_prediction(
        self,
        model_name: str,
        model_version: str,
        input_data: Dict[str, Any],
        prediction: Any,
        method: ExplanationMethod = ExplanationMethod.SHAP,
        num_features: int = 10
    ) -> Explanation:
        """Generate explanation for a single prediction."""
        
        key = f"{model_name}:{model_version}:{method.value}"
        explainer = self._explainers.get(key)
        
        if not explainer:
            raise ValueError(f"Explainer not initialized for {key}")
        
        explanation_id = str(uuid.uuid4())
        
        if method == ExplanationMethod.SHAP:
            contributions = await self._explain_with_shap(
                explainer, input_data, num_features
            )
        elif method == ExplanationMethod.LIME:
            contributions = await self._explain_with_lime(
                explainer, input_data, num_features
            )
        elif method == ExplanationMethod.FEATURE_IMPORTANCE:
            contributions = await self._explain_with_feature_importance(
                explainer, input_data, num_features
            )
        else:
            contributions = []
        
        # Calculate base and predicted values
        base_value = sum(c.base_value for c in contributions) / len(contributions) if contributions else 0
        predicted_value = base_value + sum(c.contribution for c in contributions)
        
        explanation = Explanation(
            explanation_id=explanation_id,
            model_name=model_name,
            model_version=model_version,
            input_data=input_data,
            prediction=prediction,
            method=method,
            feature_contributions=contributions,
            base_value=base_value,
            predicted_value=predicted_value,
            visualization_data=self._generate_visualization_data(contributions)
        )
        
        self._explanation_cache[explanation_id] = explanation
        
        return explanation
    
    async def _explain_with_shap(
        self,
        explainer: Any,
        input_data: Dict[str, Any],
        num_features: int
    ) -> List[FeatureContribution]:
        """Generate SHAP explanation."""
        
        # Convert input to array format
        input_array = [[v for v in input_data.values()]]
        
        # Get SHAP values
        shap_values = explainer(input_array)
        
        contributions = []
        feature_names = list(input_data.keys())
        
        for i, (name, value) in enumerate(input_data.items()):
            if i < len(shap_values.values[0]):
                contributions.append(FeatureContribution(
                    feature_name=name,
                    value=value if isinstance(value, (int, float)) else 0,
                    contribution=float(shap_values.values[0][i]),
                    base_value=float(shap_values.base_values[0]) if hasattr(shap_values, 'base_values') else 0,
                    description=f"SHAP value for {name}"
                ))
        
        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)
        
        return contributions[:num_features]
    
    async def _explain_with_lime(
        self,
        explainer: Any,
        input_data: Dict[str, Any],
        num_features: int
    ) -> List[FeatureContribution]:
        """Generate LIME explanation."""
        
        input_array = [v for v in input_data.values()]
        
        # Generate explanation
        exp = explainer.explain_instance(
            input_array,
            lambda x: [[0.5] for _ in x],  # Placeholder prediction function
            num_features=num_features
        )
        
        contributions = []
        for feature_name, weight in exp.as_list():
            contributions.append(FeatureContribution(
                feature_name=str(feature_name),
                value=0,  # LIME doesn't provide original values
                contribution=float(weight),
                base_value=0.5,
                description=f"LIME weight for {feature_name}"
            ))
        
        return contributions
    
    async def _explain_with_feature_importance(
        self,
        explainer: Dict[str, Any],
        input_data: Dict[str, Any],
        num_features: int
    ) -> List[FeatureContribution]:
        """Generate explanation using built-in feature importance."""
        
        model = explainer["model"]
        
        # Get feature importance
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
        elif hasattr(model, 'coef_'):
            importances = abs(model.coef_[0])
        else:
            importances = [1.0 / len(input_data)] * len(input_data)
        
        contributions = []
        for i, (name, value) in enumerate(input_data.items()):
            if i < len(importances):
                contributions.append(FeatureContribution(
                    feature_name=name,
                    value=value if isinstance(value, (int, float)) else 0,
                    contribution=float(importances[i]),
                    base_value=0.5,
                    description=f"Feature importance for {name}"
                ))
        
        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)
        
        return contributions[:num_features]
    
    def _generate_visualization_data(
        self,
        contributions: List[FeatureContribution]
    ) -> Dict[str, Any]:
        """Generate data for visualization."""
        
        return {
            "waterfall": {
                "labels": [c.feature_name for c in contributions],
                "values": [c.contribution for c in contributions],
                "base_value": contributions[0].base_value if contributions else 0
            },
            "bar_chart": {
                "labels": [c.feature_name for c in contributions],
                "values": [abs(c.contribution) for c in contributions]
            },
            "force_plot": {
                "features": [
                    {
                        "name": c.feature_name,
                        "value": c.value,
                        "contribution": c.contribution
                    }
                    for c in contributions
                ]
            }
        }
    
    async def explain_global(
        self,
        model_name: str,
        model_version: str,
        dataset: Any,
        method: ExplanationMethod = ExplanationMethod.SHAP
    ) -> GlobalExplanation:
        """Generate global model explanation."""
        
        key = f"{model_name}:{model_version}:{method.value}"
        explainer = self._explainers.get(key)
        
        if not explainer:
            raise ValueError(f"Explainer not initialized for {key}")
        
        # Calculate global feature importance
        if method == ExplanationMethod.SHAP:
            import shap
            shap_values = explainer(dataset)
            
            feature_importance = {
                f"feature_{i}": float(abs(shap_values.values[:, i]).mean())
                for i in range(shap_values.values.shape[1])
            }
        else:
            feature_importance = {}
        
        # Calculate summary statistics
        summary_stats = {
            "num_samples": len(dataset) if hasattr(dataset, '__len__') else 0,
            "feature_count": len(feature_importance),
            "top_feature": max(feature_importance.items(), key=lambda x: x[1])[0]
            if feature_importance else None
        }
        
        return GlobalExplanation(
            model_name=model_name,
            model_version=model_version,
            method=method,
            feature_importance=feature_importance,
            feature_interactions=[],  # Placeholder
            summary_statistics=summary_stats
        )
    
    async def get_explanation(self, explanation_id: str) -> Optional[Explanation]:
        """Retrieve a cached explanation."""
        return self._explanation_cache.get(explanation_id)
    
    async def compare_explanations(
        self,
        explanation_ids: List[str]
    ) -> Dict[str, Any]:
        """Compare multiple explanations."""
        
        explanations = [
            self._explanation_cache.get(eid)
            for eid in explanation_ids
        ]
        explanations = [e for e in explanations if e]
        
        if not explanations:
            return {"error": "No valid explanations found"}
        
        # Compare feature contributions
        feature_comparison = {}
        for exp in explanations:
            for contrib in exp.feature_contributions:
                if contrib.feature_name not in feature_comparison:
                    feature_comparison[contrib.feature_name] = []
                feature_comparison[contrib.feature_name].append(contrib.contribution)
        
        return {
            "explanations_compared": len(explanations),
            "feature_comparison": {
                name: {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values)
                }
                for name, values in feature_comparison.items()
            },
            "prediction_variance": max(
                e.predicted_value for e in explanations
            ) - min(e.predicted_value for e in explanations)
        }
