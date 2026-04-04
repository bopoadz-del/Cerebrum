"""
Feature store using Feast for feature management.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json


class FeatureType(Enum):
    """Supported feature types."""
    FLOAT = "float"
    INT = "int"
    STRING = "string"
    BOOL = "bool"
    TIMESTAMP = "timestamp"
    ARRAY = "array"
    EMBEDDING = "embedding"


class FeatureSourceType(Enum):
    """Feature data sources."""
    BATCH = "batch"
    STREAM = "stream"
    REQUEST = "request"


@dataclass
class FeatureDefinition:
    """Definition of a feature."""
    name: str
    type: FeatureType
    description: str
    entity: str
    source: FeatureSourceType
    transformation: Optional[str] = None
    default_value: Any = None
    tags: List[str] = field(default_factory=list)
    owner: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FeatureView:
    """Collection of related features."""
    name: str
    entities: List[str]
    features: List[FeatureDefinition]
    ttl: timedelta = field(default_factory=lambda: timedelta(days=7))
    online: bool = True
    batch_source: Optional[str] = None
    stream_source: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    owner: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FeatureValue:
    """Feature value with timestamp."""
    feature_name: str
    entity_key: str
    value: Any
    event_timestamp: datetime
    created_timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeatureStore:
    """Central feature store for ML features."""
    
    def __init__(self, feast_repo_path: Optional[str] = None):
        self.feast_repo_path = feast_repo_path
        self._feature_views: Dict[str, FeatureView] = {}
        self._features: Dict[str, FeatureDefinition] = {}
        self._online_store: Dict[str, Dict[str, FeatureValue]] = {}
        self._offline_store: List[FeatureValue] = []
        self._entity_keys: Dict[str, List[str]] = {}
    
    async def register_feature_view(
        self,
        name: str,
        entities: List[str],
        features: List[Dict[str, Any]],
        ttl_days: int = 7,
        online: bool = True,
        batch_source: Optional[str] = None,
        owner: str = ""
    ) -> FeatureView:
        """Register a new feature view."""
        
        # Create feature definitions
        feature_defs = []
        for feat_data in features:
            feature = FeatureDefinition(
                name=feat_data["name"],
                type=FeatureType(feat_data["type"]),
                description=feat_data.get("description", ""),
                entity=entities[0],  # Primary entity
                source=FeatureSourceType(feat_data.get("source", "batch")),
                transformation=feat_data.get("transformation"),
                default_value=feat_data.get("default_value"),
                tags=feat_data.get("tags", []),
                owner=owner
            )
            feature_defs.append(feature)
            self._features[feat_data["name"]] = feature
        
        # Create feature view
        feature_view = FeatureView(
            name=name,
            entities=entities,
            features=feature_defs,
            ttl=timedelta(days=ttl_days),
            online=online,
            batch_source=batch_source,
            owner=owner
        )
        
        self._feature_views[name] = feature_view
        
        # Initialize entity keys
        for entity in entities:
            if entity not in self._entity_keys:
                self._entity_keys[entity] = []
        
        return feature_view
    
    async def ingest_features(
        self,
        feature_view_name: str,
        data: List[Dict[str, Any]],
        entity_key_column: str = "entity_key"
    ) -> int:
        """Ingest feature data into the store."""
        
        feature_view = self._feature_views.get(feature_view_name)
        if not feature_view:
            raise ValueError(f"Feature view {feature_view_name} not found")
        
        ingested_count = 0
        
        for row in data:
            entity_key = row.get(entity_key_column)
            if not entity_key:
                continue
            
            event_timestamp = row.get("event_timestamp", datetime.utcnow())
            if isinstance(event_timestamp, str):
                event_timestamp = datetime.fromisoformat(event_timestamp)
            
            for feature in feature_view.features:
                if feature.name in row:
                    feature_value = FeatureValue(
                        feature_name=feature.name,
                        entity_key=entity_key,
                        value=row[feature.name],
                        event_timestamp=event_timestamp
                    )
                    
                    # Store in online store
                    if feature_view.online:
                        if entity_key not in self._online_store:
                            self._online_store[entity_key] = {}
                        self._online_store[entity_key][feature.name] = feature_value
                    
                    # Store in offline store
                    self._offline_store.append(feature_value)
                    ingested_count += 1
            
            # Track entity key
            if entity_key not in self._entity_keys.get(feature_view.entities[0], []):
                self._entity_keys[feature_view.entities[0]].append(entity_key)
        
        return ingested_count
    
    async def get_online_features(
        self,
        feature_refs: List[str],
        entity_rows: List[Dict[str, Any]]
    ) -> Dict[str, List[Any]]:
        """Get features for online serving."""
        
        results = {ref: [] for ref in feature_refs}
        
        for entity_row in entity_rows:
            entity_key = entity_row.get("entity_key")
            if not entity_key:
                continue
            
            entity_features = self._online_store.get(entity_key, {})
            
            for ref in feature_refs:
                # Parse feature reference (feature_view:feature_name)
                if ":" in ref:
                    _, feature_name = ref.split(":")
                else:
                    feature_name = ref
                
                feature_value = entity_features.get(feature_name)
                if feature_value:
                    results[ref].append(feature_value.value)
                else:
                    # Use default value
                    feature_def = self._features.get(feature_name)
                    results[ref].append(
                        feature_def.default_value if feature_def else None
                    )
        
        return results
    
    async def get_historical_features(
        self,
        feature_refs: List[str],
        entity_df: List[Dict[str, Any]],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get historical features for training."""
        
        results = []
        
        # Filter by date range
        filtered_store = self._offline_store
        if start_date:
            filtered_store = [
                fv for fv in filtered_store
                if fv.event_timestamp >= start_date
            ]
        if end_date:
            filtered_store = [
                fv for fv in filtered_store
                if fv.event_timestamp <= end_date
            ]
        
        # Group by entity and timestamp
        for entity_row in entity_df:
            entity_key = entity_row.get("entity_key")
            timestamp = entity_row.get("timestamp", datetime.utcnow())
            
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            row_result = {"entity_key": entity_key, "timestamp": timestamp}
            
            # Get latest features before timestamp
            for ref in feature_refs:
                if ":" in ref:
                    _, feature_name = ref.split(":")
                else:
                    feature_name = ref
                
                # Find most recent value before timestamp
                matching_values = [
                    fv for fv in filtered_store
                    if fv.entity_key == entity_key
                    and fv.feature_name == feature_name
                    and fv.event_timestamp <= timestamp
                ]
                
                if matching_values:
                    latest = max(matching_values, key=lambda x: x.event_timestamp)
                    row_result[feature_name] = latest.value
                else:
                    feature_def = self._features.get(feature_name)
                    row_result[feature_name] = (
                        feature_def.default_value if feature_def else None
                    )
            
            results.append(row_result)
        
        return results
    
    async def materialize(
        self,
        feature_view_name: str,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """Materialize features from offline to online store."""
        
        feature_view = self._feature_views.get(feature_view_name)
        if not feature_view:
            raise ValueError(f"Feature view {feature_view_name} not found")
        
        if not feature_view.online:
            return 0
        
        # Get features in date range
        features_to_materialize = [
            fv for fv in self._offline_store
            if fv.event_timestamp >= start_date
            and fv.event_timestamp <= end_date
            and fv.feature_name in [f.name for f in feature_view.features]
        ]
        
        # Update online store
        materialized_count = 0
        for fv in features_to_materialize:
            if fv.entity_key not in self._online_store:
                self._online_store[fv.entity_key] = {}
            
            # Only update if newer
            existing = self._online_store[fv.entity_key].get(fv.feature_name)
            if not existing or fv.event_timestamp > existing.event_timestamp:
                self._online_store[fv.entity_key][fv.feature_name] = fv
                materialized_count += 1
        
        return materialized_count
    
    async def list_feature_views(self) -> List[Dict[str, Any]]:
        """List all registered feature views."""
        
        return [
            {
                "name": fv.name,
                "entities": fv.entities,
                "feature_count": len(fv.features),
                "online": fv.online,
                "ttl_days": fv.ttl.days,
                "owner": fv.owner,
                "created_at": fv.created_at.isoformat()
            }
            for fv in self._feature_views.values()
        ]
    
    async def get_feature_statistics(
        self,
        feature_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get statistics for a feature."""
        
        # Filter values
        values = [
            fv.value for fv in self._offline_store
            if fv.feature_name == feature_name
        ]
        
        if start_date:
            values = [
                fv.value for fv in self._offline_store
                if fv.feature_name == feature_name
                and fv.event_timestamp >= start_date
            ]
        
        if end_date:
            values = [
                fv.value for fv in self._offline_store
                if fv.feature_name == feature_name
                and fv.event_timestamp <= end_date
            ]
        
        if not values:
            return {"feature_name": feature_name, "count": 0}
        
        # Calculate statistics based on type
        feature_def = self._features.get(feature_name)
        
        if feature_def and feature_def.type in [FeatureType.FLOAT, FeatureType.INT]:
            numeric_values = [float(v) for v in values if v is not None]
            return {
                "feature_name": feature_name,
                "count": len(values),
                "null_count": len(values) - len(numeric_values),
                "mean": sum(numeric_values) / len(numeric_values) if numeric_values else 0,
                "min": min(numeric_values) if numeric_values else None,
                "max": max(numeric_values) if numeric_values else None
            }
        else:
            return {
                "feature_name": feature_name,
                "count": len(values),
                "unique_values": len(set(values)),
                "most_common": max(set(values), key=values.count) if values else None
            }
    
    async def delete_feature_view(self, name: str) -> bool:
        """Delete a feature view and its data."""
        
        if name not in self._feature_views:
            return False
        
        feature_view = self._feature_views[name]
        
        # Remove features
        for feature in feature_view.features:
            if feature.name in self._features:
                del self._features[feature.name]
        
        # Remove from stores
        for entity_key in list(self._online_store.keys()):
            for feature in feature_view.features:
                if feature.name in self._online_store[entity_key]:
                    del self._online_store[entity_key][feature.name]
        
        self._offline_store = [
            fv for fv in self._offline_store
            if fv.feature_name not in [f.name for f in feature_view.features]
        ]
        
        del self._feature_views[name]
        
        return True
