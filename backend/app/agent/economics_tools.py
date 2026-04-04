"""
Economics Tools for Cerebrum Agent

Provides fast access to:
- RSMeans mock data (135+ items)
- Construction formulas (20+ calculations)
- City cost indices
- Building type estimates
- Web search for external formula libraries
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.agent.web_search import brave_search_sync
from app.agent.response_schema import (
    format_error_response,
    format_success_response,
    ErrorCode,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Economics Data Access Layer
# =============================================================================

class EconomicsDataStore:
    """Fast in-memory access to economics data."""

    def __init__(self):
        self._data_loaded = False
        self._items_by_id: Dict[str, Dict] = {}
        self._items_by_category: Dict[str, List[Dict]] = {}
        self._formulas: Dict[str, Dict] = {}
        self._cities: Dict[str, Dict] = {}
        self._building_types: Dict[str, Dict] = {}
        self._csi_divisions: Dict[str, Dict] = {}
        self._load_data()

    def _load_data(self):
        """Load all economics data into memory for fast access."""
        try:
            from app.economics.mock_data import (
                CSI_DIVISIONS,
                RSMEANS_MOCK_ITEMS,
                INFRASTRUCTURE_ITEMS,
                ROADWORK_ITEMS,
                SITEWORK_ITEMS,
                CITY_COST_INDICES,
                BUILDING_TYPES,
                CONSTRUCTION_FORMULAS,
                get_all_items,
            )

            # Index all items by ID
            all_items = get_all_items()
            for item in all_items:
                self._items_by_id[item["id"]] = item
                cat = item.get("category", "Uncategorized")
                if cat not in self._items_by_category:
                    self._items_by_category[cat] = []
                self._items_by_category[cat].append(item)

            # Load formulas
            self._formulas = CONSTRUCTION_FORMULAS

            # Load cities
            self._cities = CITY_COST_INDICES

            # Load building types
            self._building_types = BUILDING_TYPES

            # Load CSI divisions
            self._csi_divisions = CSI_DIVISIONS

            self._data_loaded = True
            logger.info(f"Economics data loaded: {len(self._items_by_id)} items, {len(self._formulas)} formulas")

        except ImportError as e:
            logger.warning(f"Economics mock data not available: {e}")
            self._data_loaded = False

    def is_available(self) -> bool:
        return self._data_loaded

    def get_item(self, item_id: str) -> Optional[Dict]:
        """Get item by ID (O(1) lookup)."""
        return self._items_by_id.get(item_id)

    def search_items(self, query: str, category: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Search items by query string."""
        query_lower = query.lower()
        results = []

        for item_id, item in self._items_by_id.items():
            # Search in ID, description, and category
            if (query_lower in item_id.lower() or
                query_lower in item.get("description", "").lower() or
                query_lower in item.get("category", "").lower()):

                if category is None or item.get("category") == category:
                    results.append(item)

                if len(results) >= limit:
                    break

        return results

    def get_items_by_category(self, category: str) -> List[Dict]:
        """Get all items in a category."""
        return self._items_by_category.get(category, [])

    def get_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self._keys_by_category.keys())

    def get_formula(self, formula_id: str) -> Optional[Dict]:
        """Get formula by ID."""
        return self._formulas.get(formula_id)

    def search_formulas(self, query: str, category: Optional[str] = None) -> List[Dict]:
        """Search formulas by query."""
        query_lower = query.lower()
        results = []

        for formula_id, formula in self._formulas.items():
            if (query_lower in formula_id.lower() or
                query_lower in formula.get("name", "").lower() or
                query_lower in formula.get("description", "").lower()):

                if category is None or formula.get("category") == category:
                    results.append({"id": formula_id, **formula})

        return results

    def get_formulas_by_category(self, category: str) -> List[Dict]:
        """Get formulas by category."""
        return [
            {"id": k, **v}
            for k, v in self._formulas.items()
            if v.get("category") == category
        ]

    def get_formula_categories(self) -> List[str]:
        """Get all formula categories."""
        categories = set()
        for formula in self._formulas.values():
            categories.add(formula.get("category", "Other"))
        return sorted(list(categories))

    def get_city_index(self, city: str) -> Optional[Dict]:
        """Get city cost index."""
        # Try exact match first
        if city in self._cities:
            return {"city": city, **self._cities[city]}

        # Try case-insensitive
        city_lower = city.lower()
        for c, data in self._cities.items():
            if city_lower in c.lower():
                return {"city": c, **data}

        return None

    def get_building_type(self, type_code: str) -> Optional[Dict]:
        """Get building type info."""
        return self._building_types.get(type_code)

    def get_csi_division(self, code: str) -> Optional[Dict]:
        """Get CSI division info."""
        return self._csi_divisions.get(code)

    def list_csi_divisions(self) -> List[Dict]:
        """List all CSI divisions."""
        return [{"code": k, **v} for k, v in self._csi_divisions.items()]

    def get_stats(self) -> Dict:
        """Get data store statistics."""
        return {
            "items_count": len(self._items_by_id),
            "formulas_count": len(self._formulas),
            "cities_count": len(self._cities),
            "building_types_count": len(self._building_types),
            "csi_divisions_count": len(self._csi_divisions),
            "categories": list(self._items_by_category.keys()),
            "formula_categories": self.get_formula_categories(),
        }


# Global singleton instance
_data_store: Optional[EconomicsDataStore] = None

def get_economics_store() -> EconomicsDataStore:
    """Get the economics data store singleton."""
    global _data_store
    if _data_store is None:
        _data_store = EconomicsDataStore()
    return _data_store


# =============================================================================
# Agent Tools Implementation
# =============================================================================

def economics_search_items(query: str, category: Optional[str] = None, limit: int = 10) -> Dict:
    """
    Search RSMeans construction items.

    Args:
        query: Search term (e.g., "concrete", "pipe", "manhole")
        category: Optional category filter
        limit: Max results (default 10)

    Returns:
        Dict with results and metadata
    """
    store = get_economics_store()
    if not store.is_available():
        return format_error_response(
            message="Economics data not available",
            code=ErrorCode.DATA_UNAVAILABLE,
            suggestion="Check system configuration"
        )

    results = store.search_items(query, category, limit)

    return format_success_response(
        results={"items": results},
        metadata={
            "query": query,
            "category": category,
            "count": len(results),
        },
        suggestions=[
            f"Get item details with economics_get_item(item_id='{results[0]['id']}')" if results else "Try a different search term"
        ]
    )


def economics_get_item(item_id: str) -> Dict:
    """
    Get specific item details by ID.

    Args:
        item_id: RSMeans item ID (e.g., "033000-100")

    Returns:
        Item details or error
    """
    store = get_economics_store()
    if not store.is_available():
        return format_error_response(
            message="Economics data not available",
            code=ErrorCode.DATA_UNAVAILABLE
        )

    item = store.get_item(item_id)
    if not item:
        return format_error_response(
            message=f"Item '{item_id}' not found",
            code=ErrorCode.NOT_FOUND,
            suggestion="Try searching with economics_search_items(query='concrete') to find available items"
        )

    return format_success_response(
        results={"item": item},
        metadata={"item_id": item_id}
    )


def economics_list_categories() -> Dict:
    """List all available item categories."""
    store = get_economics_store()
    if not store.is_available():
        return format_error_response(
            message="Economics data not available",
            code=ErrorCode.DATA_UNAVAILABLE
        )

    categories = store.get_categories()
    return format_success_response(
        results={"categories": categories},
        metadata={"count": len(categories)}
    )


def economics_search_formulas(query: str, category: Optional[str] = None) -> Dict:
    """
    Search construction formulas.

    Args:
        query: Search term (e.g., "concrete", "beam", "runoff")
        category: Optional category filter (Concrete, Structural, Infrastructure, etc.)

    Returns:
        Matching formulas with descriptions
    """
    store = get_economics_store()
    if not store.is_available():
        return format_error_response(
            message="Economics data not available",
            code=ErrorCode.DATA_UNAVAILABLE
        )

    results = store.search_formulas(query, category)

    return format_success_response(
        results={"formulas": results},
        metadata={
            "query": query,
            "category": category,
            "count": len(results),
        },
        suggestions=[
            f"Get formula details with economics_get_formula(formula_id='{results[0]['id']}')" if results else "Try a different search term"
        ]
    )


def economics_get_formula(formula_id: str) -> Dict:
    """
    Get formula details and calculation info.

    Args:
        formula_id: Formula identifier (e.g., "concrete_volume_rect")

    Returns:
        Formula with inputs, formula string, description
    """
    store = get_economics_store()
    if not store.is_available():
        return format_error_response(
            message="Economics data not available",
            code=ErrorCode.DATA_UNAVAILABLE
        )

    formula = store.get_formula(formula_id)
    if not formula:
        return format_error_response(
            message=f"Formula '{formula_id}' not found",
            code=ErrorCode.NOT_FOUND,
            suggestion="Search formulas with economics_search_formulas(query='concrete')"
        )

    return format_success_response(
        results={"formula": {"id": formula_id, **formula}},
        metadata={"formula_id": formula_id}
    )


def economics_calculate(formula_id: str, inputs: Dict[str, float]) -> Dict:
    """
    Execute a construction formula calculation.

    Args:
        formula_id: Formula to use
        inputs: Dictionary of input values

    Returns:
        Calculation result
    """
    store = get_economics_store()
    if not store.is_available():
        return format_error_response(
            message="Economics data not available",
            code=ErrorCode.DATA_UNAVAILABLE
        )

    formula = store.get_formula(formula_id)
    if not formula:
        return format_error_response(
            message=f"Formula '{formula_id}' not found",
            code=ErrorCode.NOT_FOUND,
            suggestion="Search available formulas with economics_search_formulas(query='concrete')"
        )

    # Check all required inputs
    missing = [inp for inp in formula["inputs"] if inp not in inputs]
    if missing:
        return format_error_response(
            message=f"Missing required inputs: {', '.join(missing)}",
            code=ErrorCode.MISSING_REQUIRED_FIELD,
            details={
                "missing_inputs": missing,
                "required_inputs": formula["inputs"],
                "provided_inputs": list(inputs.keys()),
            },
            suggestion=f"Provide all required inputs: {', '.join(formula['inputs'])}"
        )

    # Calculate
    try:
        result = _evaluate_formula(formula["formula"], inputs)
        return format_success_response(
            results={
                "calculation": {
                    "formula_id": formula_id,
                    "formula_name": formula["name"],
                    "inputs": inputs,
                    "result": result,
                    "unit": formula["unit"],
                }
            },
            metadata={
                "formula_id": formula_id,
                "result_value": result,
                "unit": formula["unit"],
            }
        )
    except Exception as e:
        logger.error(f"Formula calculation error: {e}")
        return format_error_response(
            message=f"Calculation error: {str(e)}",
            code=ErrorCode.CALCULATION_ERROR,
            details={"formula": formula["formula"], "inputs": inputs}
        )


def _evaluate_formula(formula: str, inputs: Dict[str, float]) -> float:
    """Safely evaluate a mathematical formula."""
    import math

    # Replace variables with values
    expression = formula
    for key, value in inputs.items():
        expression = expression.replace(key, str(value))

    # Safe evaluation
    allowed_names = {
        "pi": math.pi,
        "sqrt": math.sqrt,
        "pow": pow,
    }

    # Replace ^ with **
    expression = expression.replace("^", "**")

    result = eval(expression, {"__builtins__": {}}, allowed_names)
    return round(result, 4)


def economics_get_city_index(city: str) -> Dict:
    """
    Get cost index for a specific city.

    Args:
        city: City name (e.g., "New York", "Riyadh", "Dubai")

    Returns:
        City cost index data
    """
    store = get_economics_store()
    if not store.is_available():
        return format_error_response(
            message="Economics data not available",
            code=ErrorCode.DATA_UNAVAILABLE
        )

    result = store.get_city_index(city)
    if not result:
        return format_error_response(
            message=f"City '{city}' not found",
            code=ErrorCode.NOT_FOUND,
            details={"available_regions": ["US", "Middle East", "Europe"]},
            suggestion="Try major cities like 'New York', 'Riyadh', or 'Dubai'"
        )

    return format_success_response(
        results={"city_data": result},
        metadata={"city": city}
    )


def economics_estimate_building(building_type: str, size_sf: float, city: str = "National Average") -> Dict:
    """
    Quick building cost estimate.

    Args:
        building_type: Building type code (use list_building_types to see options)
        size_sf: Building size in square feet
        city: City for location adjustment

    Returns:
        Cost estimate breakdown
    """
    store = get_economics_store()
    if not store.is_available():
        return format_error_response(
            message="Economics data not available",
            code=ErrorCode.DATA_UNAVAILABLE
        )

    type_data = store.get_building_type(building_type)
    if not type_data:
        types = list(store._building_types.keys())
        return format_error_response(
            message=f"Unknown building type '{building_type}'",
            code=ErrorCode.NOT_FOUND,
            details={"available_types": types[:20]},
            suggestion=f"Use one of: {', '.join(types[:5])}..."
        )

    base_cost = type_data["cost_per_sf"] * size_sf
    city_data = store.get_city_index(city)
    location_factor = city_data.get("index", 1.0) if city_data else 1.0
    adjusted_cost = base_cost * location_factor

    return format_success_response(
        results={
            "estimate": {
                "building_type": building_type,
                "size_sf": size_sf,
                "city": city,
                "base_cost_per_sf": type_data["cost_per_sf"],
                "location_factor": location_factor,
                "total_cost": round(adjusted_cost, 2),
                "currency": "USD",
            }
        },
        metadata={
            "building_type": building_type,
            "size_sf": size_sf,
            "city": city,
        },
        suggestions=[
            "Get detailed breakdown with economics_estimate_project(project_type='{}')".format(building_type),
        ]
    )


def economics_list_building_types() -> Dict:
    """List all available building types for estimates."""
    store = get_economics_store()
    if not store.is_available():
        return format_error_response(
            message="Economics data not available",
            code=ErrorCode.DATA_UNAVAILABLE
        )

    types = []
    for code, data in store._building_types.items():
        types.append({
            "code": code,
            "name": data["name"],
            "cost_per_sf": data["cost_per_sf"],
            "typical_size_sf": data["typical_size_sf"],
        })

    return format_success_response(
        results={"building_types": types},
        metadata={"count": len(types)},
        suggestions=[
            f"Estimate cost with economics_estimate_building(building_type='{types[0]['code']}', size_sf=5000)" if types else ""
        ]
    )


def economics_list_csi_divisions() -> Dict:
    """List all CSI MasterFormat divisions."""
    store = get_economics_store()
    if not store.is_available():
        return {"success": False, "error": "Economics data not available"}

    divisions = store.list_csi_divisions()
    return {
        "success": True,
        "divisions": divisions,
        "count": len(divisions),
    }


def economics_get_stats() -> Dict:
    """Get statistics about available economics data."""
    store = get_economics_store()
    if not store.is_available():
        return format_error_response(
            message="Economics data not available",
            code=ErrorCode.DATA_UNAVAILABLE
        )

    return format_success_response(
        results={"stats": store.get_stats()},
        metadata={"data_available": True}
    )


# =============================================================================
# Web Search for External Formula Libraries
# =============================================================================

def search_formula_libraries_online(query: str, limit: int = 5) -> Dict:
    """
    Search online for construction formula libraries and resources.

    Args:
        query: Search query (e.g., "concrete volume formula", "beam deflection calculation")
        limit: Number of results

    Returns:
        Search results with URLs and snippets
    """
    # Enhance query for construction/engineering resources
    enhanced_query = f"{query} construction engineering formula calculation"

    try:
        results = brave_search_sync(enhanced_query, count=limit)
        return format_success_response(
            results={"search_results": results.get("results", [])},
            metadata={
                "query": query,
                "count": len(results.get("results", [])),
            },
            suggestions=[
                "Try local formulas with economics_search_formulas(query='concrete')"
            ]
        )
    except Exception as e:
        logger.error(f"Online search failed: {e}")
        return format_error_response(
            message=f"Search failed: {str(e)}",
            code=ErrorCode.UNKNOWN_ERROR,
            suggestion="Check network connection and try again"
        )


def browse_rsmeans_online(query: str) -> Dict:
    """
    Search RSMeans online resources.

    Args:
        query: Search term for RSMeans data

    Returns:
        Online RSMeans resources
    """
    enhanced_query = f"RSMeans {query} cost data construction"

    try:
        results = brave_search_sync(enhanced_query, count=5)
        return format_success_response(
            results={"search_results": results.get("results", [])},
            metadata={
                "query": query,
                "count": len(results.get("results", [])),
                "note": "Results from web search. For local data, use economics_search_items()"
            },
            suggestions=[
                "Search local RSMeans data with economics_search_items(query='{}')".format(query)
            ]
        )
    except Exception as e:
        logger.error(f"RSMeans browse failed: {e}")
        return format_error_response(
            message=f"Search failed: {str(e)}",
            code=ErrorCode.UNKNOWN_ERROR
        )


def browse_engineering_formulas(topic: str) -> Dict:
    """
    Browse online engineering formula resources by topic.

    Args:
        topic: Topic name (e.g., "structural", "hydraulics", "concrete", "electrical")

    Returns:
        Formula resources and references
    """
    query = f"{topic} engineering formulas reference calculations"

    try:
        results = brave_search_sync(query, count=5)

        # Also suggest known resources
        resources = {
            "structural": [
                "https://www.engineeringtoolbox.com",
                "https://www.structuralbasics.com",
            ],
            "hydraulics": [
                "https://www.engineeringtoolbox.com/hydraulics-pneumatics_",
                "https://www.lmnoeng.com",
            ],
            "concrete": [
                "https://www.concrete.org",
                "https://www.engineeringtoolbox.com/concrete-properties_",
            ],
            "electrical": [
                "https://www.engineeringtoolbox.com/electrical_",
            ],
            "general": [
                "https://www.engineeringtoolbox.com",
                "https://www.sciencedirect.com/topics/engineering",
            ],
        }

        return {
            "success": True,
            "topic": topic,
            "search_results": results.get("results", []),
            "suggested_resources": resources.get(topic.lower(), resources["general"]),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}",
        }


# =============================================================================
# Tool Registry for Agent
# =============================================================================

ECONOMICS_TOOLS = {
    # Local data access (fast)
    "economics_search_items": economics_search_items,
    "economics_get_item": economics_get_item,
    "economics_list_categories": economics_list_categories,
    "economics_search_formulas": economics_search_formulas,
    "economics_get_formula": economics_get_formula,
    "economics_calculate": economics_calculate,
    "economics_get_city_index": economics_get_city_index,
    "economics_estimate_building": economics_estimate_building,
    "economics_list_building_types": economics_list_building_types,
    "economics_list_csi_divisions": economics_list_csi_divisions,
    "economics_get_stats": economics_get_stats,

    # Online browsing
    "search_formula_libraries_online": search_formula_libraries_online,
    "browse_rsmeans_online": browse_rsmeans_online,
    "browse_engineering_formulas": browse_engineering_formulas,
}


def get_economics_tools() -> Dict[str, Any]:
    """Get all economics tools for agent registration."""
    return ECONOMICS_TOOLS


__all__ = [
    "EconomicsDataStore",
    "get_economics_store",
    "ECONOMICS_TOOLS",
    "get_economics_tools",
]
