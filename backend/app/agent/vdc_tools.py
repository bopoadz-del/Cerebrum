"""
VDC (Virtual Design and Construction) Tools for Cerebrum Agent

Provides tools for:
- BIM model querying
- Clash detection
- Quantity extraction
- 4D/5D simulation
- Model coordination
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.agent.response_schema import (
    AgentResponse,
    ErrorCode,
    format_error_response,
    format_success_response,
)

logger = logging.getLogger(__name__)


# =============================================================================
# VDC Data Store
# =============================================================================

class VDCDataStore:
    """In-memory store for VDC data and model references."""
    
    def __init__(self):
        self._models: Dict[str, Dict] = {}
        self._clashes: Dict[str, Dict] = {}
        self._quantities: Dict[str, Dict] = {}
        self._loaded = False
        self._load_mock_data()
    
    def _load_mock_data(self):
        """Load mock VDC data for demonstration."""
        self._models = {
            "model_001": {
                "id": "model_001",
                "name": "Architectural_Model_v2.ifc",
                "discipline": "architectural",
                "version": "2.0",
                "uploaded_at": datetime.now().isoformat(),
                "element_count": 1523,
                "file_size_mb": 45.2,
            },
            "model_002": {
                "id": "model_002",
                "name": "Structural_Model_v1.ifc",
                "discipline": "structural",
                "version": "1.0",
                "uploaded_at": datetime.now().isoformat(),
                "element_count": 892,
                "file_size_mb": 28.7,
            },
            "model_003": {
                "id": "model_003",
                "name": "MEP_Model_v3.ifc",
                "discipline": "mep",
                "version": "3.0",
                "uploaded_at": datetime.now().isoformat(),
                "element_count": 2156,
                "file_size_mb": 62.3,
            },
        }
        
        self._clashes = {
            "clash_001": {
                "id": "clash_001",
                "type": "hard_clash",
                "severity": "high",
                "status": "active",
                "element_a": {"id": "elem_123", "name": "HVAC_Duct_01", "discipline": "mep"},
                "element_b": {"id": "elem_456", "name": "Beam_L3_45", "discipline": "structural"},
                "intersection_volume": 0.45,
                "grid_location": "C-4",
                "level": "Level 3",
                "detected_at": datetime.now().isoformat(),
            },
            "clash_002": {
                "id": "clash_002",
                "type": "clearance",
                "severity": "medium",
                "status": "active",
                "element_a": {"id": "elem_789", "name": "Pipe_Sprinkler_23", "discipline": "mep"},
                "element_b": {"id": "elem_101", "name": "Ceiling_Grid_L2", "discipline": "architectural"},
                "clearance_required": 0.3,
                "clearance_actual": 0.15,
                "grid_location": "B-7",
                "level": "Level 2",
                "detected_at": datetime.now().isoformat(),
            },
        }
        
        self._quantities = {
            "concrete_walls": {
                "category": "concrete",
                "element_type": "wall",
                "total_volume_m3": 245.5,
                "total_area_m2": 1850.0,
                "element_count": 45,
            },
            "structural_steel": {
                "category": "steel",
                "element_type": "beam",
                "total_weight_kg": 15230.5,
                "total_length_m": 2450.0,
                "element_count": 156,
            },
            "drywall": {
                "category": "drywall",
                "element_type": "wall",
                "total_area_m2": 3200.0,
                "sheet_count_4x8": 1075,
                "element_count": 89,
            },
        }
        
        self._loaded = True
    
    def is_available(self) -> bool:
        return self._loaded
    
    def get_model(self, model_id: str) -> Optional[Dict]:
        """Get model by ID."""
        return self._models.get(model_id)
    
    def list_models(self, discipline: Optional[str] = None) -> List[Dict]:
        """List all models, optionally filtered by discipline."""
        models = list(self._models.values())
        if discipline:
            models = [m for m in models if m.get("discipline") == discipline]
        return models
    
    def get_clash(self, clash_id: str) -> Optional[Dict]:
        """Get clash by ID."""
        return self._clashes.get(clash_id)
    
    def list_clashes(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        discipline: Optional[str] = None
    ) -> List[Dict]:
        """List clashes with optional filtering."""
        clashes = list(self._clashes.values())
        
        if status:
            clashes = [c for c in clashes if c.get("status") == status]
        if severity:
            clashes = [c for c in clashes if c.get("severity") == severity]
        if discipline:
            clashes = [
                c for c in clashes
                if c.get("element_a", {}).get("discipline") == discipline
                or c.get("element_b", {}).get("discipline") == discipline
            ]
        
        return clashes
    
    def get_quantities(self, category: Optional[str] = None) -> Dict[str, Dict]:
        """Get quantity data by category."""
        if category:
            return {
                k: v for k, v in self._quantities.items()
                if v.get("category") == category
            }
        return self._quantities


# Global singleton instance
_vdc_store: Optional[VDCDataStore] = None

def get_vdc_store() -> VDCDataStore:
    """Get the VDC data store singleton."""
    global _vdc_store
    if _vdc_store is None:
        _vdc_store = VDCDataStore()
    return _vdc_store


# =============================================================================
# Model Tools
# =============================================================================

def vdc_list_models(discipline: Optional[str] = None) -> Dict[str, Any]:
    """
    List available BIM models.
    
    Args:
        discipline: Optional filter by discipline (architectural, structural, mep)
    
    Returns:
        Standardized response with list of models
    """
    store = get_vdc_store()
    if not store.is_available():
        return format_error_response(
            message="VDC data store is not available",
            code="data_unavailable",
            suggestion="Check system configuration and try again"
        )
    
    models = store.list_models(discipline)
    
    return format_success_response(
        results={"models": models},
        metadata={
            "count": len(models),
            "discipline_filter": discipline,
        },
        suggestions=[
            f"Query model details with vdc_get_model(model_id='{m['id']}')" 
            for m in models[:3]
        ]
    )


def vdc_get_model(model_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific BIM model.
    
    Args:
        model_id: Unique identifier for the model
    
    Returns:
        Standardized response with model details
    """
    store = get_vdc_store()
    if not store.is_available():
        return format_error_response(
            message="VDC data store is not available",
            code="data_unavailable"
        )
    
    model = store.get_model(model_id)
    if not model:
        available = [m["id"] for m in store.list_models()]
        return format_error_response(
            message=f"Model '{model_id}' not found",
            code="resource_not_found",
            details={"requested_id": model_id, "available_ids": available[:10]},
            suggestion=f"Use vdc_list_models() to see available models. Similar IDs: {[a for a in available if model_id[:3] in a][:3]}"
        )
    
    return format_success_response(
        results={"model": model},
        metadata={"model_id": model_id},
        suggestions=[
            "vdc_query_elements(model_id='{}', element_type='wall')".format(model_id),
            "vdc_extract_quantities(model_id='{}')".format(model_id),
        ]
    )


def vdc_query_elements(
    model_id: str,
    element_type: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Query elements from a BIM model.
    
    Args:
        model_id: Model to query
        element_type: Filter by element type (wall, door, window, beam, etc.)
        level: Filter by building level
        limit: Maximum number of elements to return
    
    Returns:
        Standardized response with matching elements
    """
    store = get_vdc_store()
    if not store.is_available():
        return format_error_response(
            message="VDC data store is not available",
            code="data_unavailable"
        )
    
    # Verify model exists
    model = store.get_model(model_id)
    if not model:
        return format_error_response(
            message=f"Model '{model_id}' not found",
            code="resource_not_found",
            suggestion="Use vdc_list_models() to see available models"
        )
    
    # Generate mock elements based on filters
    elements = _generate_mock_elements(model_id, element_type, level, limit)
    
    return format_success_response(
        results={"elements": elements},
        metadata={
            "model_id": model_id,
            "element_type_filter": element_type,
            "level_filter": level,
            "count": len(elements),
            "limit": limit,
        },
        suggestions=[
            f"Extract quantities with vdc_extract_quantities(model_id='{model_id}')",
            f"Check for clashes with vdc_detect_clashes(model_id='{model_id}')",
        ]
    )


def _generate_mock_elements(
    model_id: str,
    element_type: Optional[str],
    level: Optional[str],
    limit: int
) -> List[Dict]:
    """Generate mock BIM elements for demonstration."""
    import random
    
    element_types = ["wall", "door", "window", "beam", "column", "floor", "ceiling"] if not element_type else [element_type]
    levels = ["Level 1", "Level 2", "Level 3", "Roof"] if not level else [level]
    
    elements = []
    for i in range(min(limit, 20)):
        etype = random.choice(element_types)
        lvl = random.choice(levels)
        elements.append({
            "id": f"elem_{model_id}_{i:04d}",
            "type": etype,
            "name": f"{etype.capitalize()}_{lvl.replace(' ', '')}_{i+1:03d}",
            "level": lvl,
            "properties": {
                "length": round(random.uniform(1.0, 10.0), 2),
                "width": round(random.uniform(0.1, 1.0), 2),
                "height": round(random.uniform(2.0, 4.0), 2),
            }
        })
    
    return elements


# =============================================================================
# Clash Detection Tools
# =============================================================================

def vdc_detect_clashes(
    model_ids: Optional[List[str]] = None,
    clash_type: Optional[str] = None,
    severity: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect clashes between BIM models.
    
    Args:
        model_ids: List of model IDs to check (None = all models)
        clash_type: Filter by type (hard_clash, clearance, soft_clash)
        severity: Filter by severity (critical, high, medium, low)
    
    Returns:
        Standardized response with detected clashes
    """
    store = get_vdc_store()
    if not store.is_available():
        return format_error_response(
            message="VDC data store is not available",
            code="data_unavailable"
        )
    
    clashes = store.list_clashes(
        status="active",
        severity=severity,
    )
    
    if clash_type:
        clashes = [c for c in clashes if c.get("type") == clash_type]
    
    # Calculate summary statistics
    severity_counts = {}
    type_counts = {}
    for clash in clashes:
        sev = clash.get("severity", "unknown")
        typ = clash.get("type", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        type_counts[typ] = type_counts.get(typ, 0) + 1
    
    return format_success_response(
        results={
            "clashes": clashes,
            "summary": {
                "total": len(clashes),
                "by_severity": severity_counts,
                "by_type": type_counts,
            }
        },
        metadata={
            "model_ids": model_ids,
            "clash_type_filter": clash_type,
            "severity_filter": severity,
        },
        suggestions=[
            f"Get clash details with vdc_get_clash(clash_id='{clashes[0]['id']}')" if clashes else "No clashes to review",
            "Export clash report with vdc_export_clash_report(format='bcf')",
        ]
    )


def vdc_get_clash(clash_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific clash.
    
    Args:
        clash_id: Unique clash identifier
    
    Returns:
        Standardized response with clash details
    """
    store = get_vdc_store()
    if not store.is_available():
        return format_error_response(
            message="VDC data store is not available",
            code="data_unavailable"
        )
    
    clash = store.get_clash(clash_id)
    if not clash:
        available = list(store._clashes.keys())
        return format_error_response(
            message=f"Clash '{clash_id}' not found",
            code="resource_not_found",
            details={"requested_id": clash_id, "available_ids": available},
            suggestion="Use vdc_detect_clashes() to find active clashes"
        )
    
    return format_success_response(
        results={"clash": clash},
        metadata={"clash_id": clash_id},
        suggestions=[
            "Update status with vdc_update_clash_status(clash_id='{}', status='resolved')".format(clash_id),
            "Assign clash with vdc_assign_clash(clash_id='{}', assignee='user@example.com')".format(clash_id),
        ]
    )


def vdc_update_clash_status(clash_id: str, status: str, resolution_notes: Optional[str] = None) -> Dict[str, Any]:
    """
    Update the status of a clash.
    
    Args:
        clash_id: Clash to update
        status: New status (active, resolved, ignored)
        resolution_notes: Optional notes about resolution
    
    Returns:
        Standardized response with updated clash
    """
    store = get_vdc_store()
    if not store.is_available():
        return format_error_response(
            message="VDC data store is not available",
            code="data_unavailable"
        )
    
    clash = store.get_clash(clash_id)
    if not clash:
        return format_error_response(
            message=f"Clash '{clash_id}' not found",
            code="resource_not_found"
        )
    
    # Update the clash (in memory only for mock)
    clash["status"] = status
    clash["updated_at"] = datetime.now().isoformat()
    if resolution_notes:
        clash["resolution_notes"] = resolution_notes
    
    return format_success_response(
        results={"clash": clash},
        metadata={"clash_id": clash_id, "new_status": status},
        suggestions=["Check all clashes with vdc_detect_clashes()"]
    )


# =============================================================================
# Quantity Extraction Tools
# =============================================================================

def vdc_extract_quantities(
    model_id: Optional[str] = None,
    category: Optional[str] = None,
    element_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract quantities from BIM models.
    
    Args:
        model_id: Specific model to extract from (None = all models)
        category: Filter by category (concrete, steel, drywall, etc.)
        element_type: Filter by element type
    
    Returns:
        Standardized response with quantity data
    """
    store = get_vdc_store()
    if not store.is_available():
        return format_error_response(
            message="VDC data store is not available",
            code="data_unavailable"
        )
    
    quantities = store.get_quantities(category)
    
    # Calculate totals
    total_volume = sum(q.get("total_volume_m3", 0) for q in quantities.values())
    total_area = sum(q.get("total_area_m2", 0) for q in quantities.values())
    total_weight = sum(q.get("total_weight_kg", 0) for q in quantities.values())
    total_elements = sum(q.get("element_count", 0) for q in quantities.values())
    
    return format_success_response(
        results={
            "quantities": quantities,
            "totals": {
                "total_volume_m3": round(total_volume, 2),
                "total_area_m2": round(total_area, 2),
                "total_weight_kg": round(total_weight, 2),
                "total_elements": total_elements,
            }
        },
        metadata={
            "model_id": model_id,
            "category_filter": category,
            "element_type_filter": element_type,
        },
        suggestions=[
            "Get cost estimate with economics_estimate_project()",
            "Export to Excel with vdc_export_quantities(format='excel')",
        ]
    )


def vdc_export_quantities(format: str = "excel", model_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Export quantity data to various formats.
    
    Args:
        format: Export format (excel, csv, json, bcf)
        model_id: Optional specific model to export
    
    Returns:
        Standardized response with export details
    """
    store = get_vdc_store()
    if not store.is_available():
        return format_error_response(
            message="VDC data store is not available",
            code="data_unavailable"
        )
    
    valid_formats = ["excel", "csv", "json", "bcf"]
    if format not in valid_formats:
        return format_error_response(
            message=f"Invalid export format '{format}'",
            code="invalid_format",
            details={"valid_formats": valid_formats},
            suggestion=f"Use one of: {', '.join(valid_formats)}"
        )
    
    quantities = store.get_quantities()
    
    # Simulate export
    export_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    return format_success_response(
        results={
            "export_id": export_id,
            "format": format,
            "download_url": f"/api/v1/vdc/exports/{export_id}.{format}",
            "record_count": len(quantities),
        },
        metadata={
            "model_id": model_id,
            "export_format": format,
        },
        suggestions=["Download the file from the provided URL"]
    )


# =============================================================================
# Coordination Tools
# =============================================================================

def vdc_create_coordination_issue(
    title: str,
    description: str,
    assigned_to: Optional[str] = None,
    priority: str = "medium"
) -> Dict[str, Any]:
    """
    Create a new coordination issue.
    
    Args:
        title: Issue title
        description: Detailed description
        assigned_to: Email or user ID to assign
        priority: Priority level (low, medium, high, critical)
    
    Returns:
        Standardized response with created issue
    """
    issue_id = f"issue_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(title) % 10000}"
    
    issue = {
        "id": issue_id,
        "title": title,
        "description": description,
        "status": "open",
        "priority": priority,
        "assigned_to": assigned_to,
        "created_at": datetime.now().isoformat(),
    }
    
    return format_success_response(
        results={"issue": issue},
        metadata={"issue_id": issue_id},
        suggestions=[
            f"Track issue status with vdc_get_issue(issue_id='{issue_id}')",
            "List all issues with vdc_list_issues()",
        ]
    )


def vdc_get_coordination_status() -> Dict[str, Any]:
    """
    Get overall coordination status across all models.
    
    Returns:
        Standardized response with coordination dashboard data
    """
    store = get_vdc_store()
    if not store.is_available():
        return format_error_response(
            message="VDC data store is not available",
            code="data_unavailable"
        )
    
    clashes = store.list_clashes()
    models = store.list_models()
    
    active_clashes = [c for c in clashes if c.get("status") == "active"]
    critical_clashes = [c for c in active_clashes if c.get("severity") == "critical"]
    high_clashes = [c for c in active_clashes if c.get("severity") == "high"]
    
    return format_success_response(
        results={
            "status": "needs_attention" if critical_clashes else "ok",
            "models": {
                "total": len(models),
                "list": [{"id": m["id"], "name": m["name"], "discipline": m["discipline"]} for m in models]
            },
            "clashes": {
                "total": len(clashes),
                "active": len(active_clashes),
                "critical": len(critical_clashes),
                "high": len(high_clashes),
            },
        },
        metadata={"timestamp": datetime.now().isoformat()},
        suggestions=[
            "Review critical clashes with vdc_detect_clashes(severity='critical')",
            "Generate coordination report with vdc_export_coordination_report()",
        ]
    )


# =============================================================================
# Tool Registry
# =============================================================================

VDC_TOOLS = {
    # Model tools
    "vdc_list_models": vdc_list_models,
    "vdc_get_model": vdc_get_model,
    "vdc_query_elements": vdc_query_elements,
    
    # Clash detection tools
    "vdc_detect_clashes": vdc_detect_clashes,
    "vdc_get_clash": vdc_get_clash,
    "vdc_update_clash_status": vdc_update_clash_status,
    
    # Quantity tools
    "vdc_extract_quantities": vdc_extract_quantities,
    "vdc_export_quantities": vdc_export_quantities,
    
    # Coordination tools
    "vdc_create_coordination_issue": vdc_create_coordination_issue,
    "vdc_get_coordination_status": vdc_get_coordination_status,
}


def get_vdc_tools() -> Dict[str, Any]:
    """Get all VDC tools for agent registration."""
    return VDC_TOOLS


__all__ = [
    "VDCDataStore",
    "get_vdc_store",
    "VDC_TOOLS",
    "get_vdc_tools",
    "vdc_list_models",
    "vdc_get_model",
    "vdc_query_elements",
    "vdc_detect_clashes",
    "vdc_get_clash",
    "vdc_extract_quantities",
    "vdc_export_quantities",
]