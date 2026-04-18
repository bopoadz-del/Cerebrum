"""
Integrations Module for Heavy Reasoning Engine

Merges data from 3 JSON sources:
- BOQ (Bill of Quantities)
- Specs (Specifications)
- Drawings

Provides unified data model for cross-source analysis.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class MergedQuantityItem:
    """A quantity item merged from multiple sources."""
    item_id: str
    description: str
    boq_quantity: Optional[float] = None
    boq_unit: Optional[str] = None
    drawing_quantity: Optional[float] = None
    drawing_unit: Optional[str] = None
    spec_quantity: Optional[float] = None
    spec_unit: Optional[str] = None
    reconciled_quantity: Optional[float] = None
    variance_notes: List[str] = field(default_factory=list)
    
    @property
    def has_variance(self) -> bool:
        """Check if there's a variance between sources."""
        quantities = [
            q for q in [self.boq_quantity, self.drawing_quantity, self.spec_quantity]
            if q is not None
        ]
        if len(quantities) < 2:
            return False
        return max(quantities) != min(quantities)
    
    @property
    def variance_percent(self) -> Optional[float]:
        """Calculate variance percentage if multiple sources available."""
        quantities = [
            q for q in [self.boq_quantity, self.drawing_quantity, self.spec_quantity]
            if q is not None
        ]
        if len(quantities) < 2:
            return None
        avg = sum(quantities) / len(quantities)
        max_var = max(abs(q - avg) for q in quantities)
        return max_var / avg if avg != 0 else 0


@dataclass
class MergedMaterialSpec:
    """Material specification merged from multiple sources."""
    material_type: str
    spec_grade: Optional[str] = None
    boq_grade: Optional[str] = None
    drawing_grade: Optional[str] = None
    actual_grade: Optional[str] = None
    spec_strength: Optional[float] = None
    actual_strength: Optional[float] = None
    strength_unit: str = "MPa"
    compliant: Optional[bool] = None
    issues: List[str] = field(default_factory=list)


@dataclass
class MergedProjectData:
    """Complete merged project data from all sources."""
    quantities: List[MergedQuantityItem] = field(default_factory=list)
    materials: List[MergedMaterialSpec] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    merge_stats: Dict[str, int] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)


class IntegrationsEngine:
    """
    Merges data from BOQ, Specifications, and Drawings.
    
    Handles:
    - Cross-referencing items by ID, description, or type
    - Unit conversion and normalization
    - Conflict detection and resolution
    - Data completeness tracking
    """
    
    def __init__(self):
        self.unit_conversions = {
            ("m", "mm"): 1000,
            ("mm", "m"): 0.001,
            ("m3", "liters"): 1000,
            ("liters", "m3"): 0.001,
            ("kg", "tonnes"): 0.001,
            ("tonnes", "kg"): 1000,
            ("m2", "sqft"): 10.764,
            ("sqft", "m2"): 0.0929,
        }
    
    def merge_json_sources(
        self,
        boq_json: Optional[Dict[str, Any]] = None,
        spec_json: Optional[Dict[str, Any]] = None,
        drawing_json: Optional[Dict[str, Any]] = None
    ) -> MergedProjectData:
        """
        Merge three JSON data sources into unified data model.
        
        Args:
            boq_json: Data from BOQ analysis
            spec_json: Data from Specifications analysis
            drawing_json: Data from Drawings analysis
        
        Returns:
            MergedProjectData with cross-referenced information
        """
        merged = MergedProjectData()
        
        # Extract quantities from each source
        boq_quantities = boq_json.get("quantities", []) if boq_json else []
        spec_quantities = spec_json.get("quantities", []) if spec_json else []
        drawing_quantities = drawing_json.get("quantities", []) if drawing_json else []
        
        # Merge quantities
        merged.quantities = self._merge_quantities(
            boq_quantities,
            spec_quantities,
            drawing_quantities
        )
        
        # Extract materials from each source
        boq_materials = self._extract_materials_from_boq(boq_json)
        spec_materials = self._extract_materials_from_specs(spec_json)
        drawing_materials = self._extract_materials_from_drawings(drawing_json)
        
        # Merge materials
        merged.materials = self._merge_materials(
            boq_materials,
            spec_materials,
            drawing_materials
        )
        
        # Calculate merge statistics
        merged.merge_stats = {
            "boq_items": len(boq_quantities),
            "spec_items": len(spec_quantities),
            "drawing_items": len(drawing_quantities),
            "merged_quantities": len(merged.quantities),
            "material_specs": len(merged.materials),
            "items_with_variance": sum(1 for q in merged.quantities if q.has_variance),
            "material_conflicts": sum(1 for m in merged.materials if not m.compliant),
        }
        
        # Detect conflicts
        merged.conflicts = self._detect_conflicts(merged)
        
        # Build metadata
        merged.metadata = {
            "sources": {
                "boq": boq_json is not None,
                "specs": spec_json is not None,
                "drawings": drawing_json is not None,
            },
            "merge_timestamp": None,  # Set by caller
            "completeness_score": self._calculate_completeness(merged),
        }
        
        return merged
    
    def _merge_quantities(
        self,
        boq_items: List[Dict],
        spec_items: List[Dict],
        drawing_items: List[Dict]
    ) -> List[MergedQuantityItem]:
        """Merge quantity items from multiple sources."""
        # Create index by ID
        by_id: Dict[str, MergedQuantityItem] = {}
        
        # Process BOQ items
        for item in boq_items:
            item_id = item.get("id", item.get("description", "unknown"))
            if item_id not in by_id:
                by_id[item_id] = MergedQuantityItem(
                    item_id=item_id,
                    description=item.get("description", ""),
                )
            by_id[item_id].boq_quantity = item.get("value")
            by_id[item_id].boq_unit = item.get("unit")
        
        # Process Spec items
        for item in spec_items:
            item_id = item.get("id", item.get("description", "unknown"))
            if item_id not in by_id:
                by_id[item_id] = MergedQuantityItem(
                    item_id=item_id,
                    description=item.get("description", ""),
                )
            by_id[item_id].spec_quantity = item.get("value")
            by_id[item_id].spec_unit = item.get("unit")
        
        # Process Drawing items
        for item in drawing_items:
            item_id = item.get("id", item.get("description", "unknown"))
            if item_id not in by_id:
                by_id[item_id] = MergedQuantityItem(
                    item_id=item_id,
                    description=item.get("description", ""),
                )
            by_id[item_id].drawing_quantity = item.get("value")
            by_id[item_id].drawing_unit = item.get("unit")
        
        # Reconcile quantities
        for item in by_id.values():
            item.reconciled_quantity = self._reconcile_quantity(item)
            if item.has_variance:
                item.variance_notes = self._generate_variance_notes(item)
        
        return list(by_id.values())
    
    def _reconcile_quantity(self, item: MergedQuantityItem) -> Optional[float]:
        """Reconcile quantity from multiple sources."""
        quantities = []
        
        for qty, unit in [
            (item.boq_quantity, item.boq_unit),
            (item.drawing_quantity, item.drawing_unit),
            (item.spec_quantity, item.spec_unit),
        ]:
            if qty is not None:
                # Convert to base unit if needed
                converted = self._convert_to_base_unit(qty, unit)
                quantities.append(converted)
        
        if not quantities:
            return None
        
        # Use average of available sources
        # (More sophisticated logic could weight by source reliability)
        return sum(quantities) / len(quantities)
    
    def _convert_to_base_unit(self, value: float, unit: Optional[str]) -> float:
        """Convert value to base unit."""
        if unit is None:
            return value
        
        # Normalize unit string
        unit_norm = unit.lower().strip()
        
        # For now, just return value (real implementation would do conversions)
        # This is where unit conversion logic would go
        return value
    
    def _generate_variance_notes(self, item: MergedQuantityItem) -> List[str]:
        """Generate notes about quantity variances."""
        notes = []
        
        sources = []
        if item.boq_quantity is not None:
            sources.append(("BOQ", item.boq_quantity))
        if item.drawing_quantity is not None:
            sources.append(("Drawing", item.drawing_quantity))
        if item.spec_quantity is not None:
            sources.append(("Spec", item.spec_quantity))
        
        if len(sources) >= 2:
            max_qty = max(s[1] for s in sources)
            min_qty = min(s[1] for s in sources)
            variance = (max_qty - min_qty) / min_qty * 100 if min_qty != 0 else 0
            
            notes.append(f"Variance of {variance:.1f}% between sources")
            
            # Identify the outlier
            avg = sum(s[1] for s in sources) / len(sources)
            for name, qty in sources:
                if abs(qty - avg) > avg * 0.1:  # More than 10% from average
                    if qty > avg:
                        notes.append(f"{name} quantity is {((qty/avg)-1)*100:.1f}% higher than average")
                    else:
                        notes.append(f"{name} quantity is {((avg/qty)-1)*100:.1f}% lower than average")
        
        return notes
    
    def _extract_materials_from_boq(
        self,
        boq_json: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Extract material information from BOQ data."""
        if not boq_json:
            return {}
        
        materials = {}
        for item in boq_json.get("quantities", []):
            material_type = item.get("material_type", item.get("type", "unknown"))
            materials[material_type] = {
                "grade": item.get("grade"),
                "strength": item.get("strength"),
                "quantity": item.get("value"),
                "source": "boq",
            }
        
        return materials
    
    def _extract_materials_from_specs(
        self,
        spec_json: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Extract material information from Specifications data."""
        if not spec_json:
            return {}
        
        materials = {}
        
        # Extract from performance criteria
        for criterion in spec_json.get("performance_criteria", []):
            crit_type = criterion.get("type", "general")
            materials[crit_type] = {
                "grade": criterion.get("value"),
                "strength": criterion.get("value") if crit_type == "strength" else None,
                "source": "spec",
            }
        
        # Extract from sections
        for section in spec_json.get("sections", []):
            part2 = section.get("part2_products", {})
            for product in part2.get("products", []):
                material_type = product.get("type", "unknown")
                materials[material_type] = {
                    "grade": product.get("grade"),
                    "specifications": product.get("specs", []),
                    "source": "spec",
                }
        
        return materials
    
    def _extract_materials_from_drawings(
        self,
        drawing_json: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Extract material information from Drawing data."""
        if not drawing_json:
            return {}
        
        materials = {}
        
        # Extract from specifications found on drawings
        for spec in drawing_json.get("specifications", []):
            key = spec.get("key", "unknown")
            materials[key] = {
                "grade": spec.get("value"),
                "source": "drawing",
            }
        
        return materials
    
    def _merge_materials(
        self,
        boq_materials: Dict[str, Dict],
        spec_materials: Dict[str, Dict],
        drawing_materials: Dict[str, Dict]
    ) -> List[MergedMaterialSpec]:
        """Merge material specifications from multiple sources."""
        all_types = set(boq_materials.keys()) | set(spec_materials.keys()) | set(drawing_materials.keys())
        
        merged = []
        for material_type in all_types:
            boq_data = boq_materials.get(material_type, {})
            spec_data = spec_materials.get(material_type, {})
            drawing_data = drawing_materials.get(material_type, {})
            
            # Extract grades
            spec_grade = spec_data.get("grade")
            boq_grade = boq_data.get("grade")
            drawing_grade = drawing_data.get("grade")
            
            # Determine actual grade (prefer BOQ as that's what's being ordered)
            actual_grade = boq_grade or drawing_grade
            
            # Check compliance
            compliant = True
            issues = []
            
            if spec_grade and actual_grade:
                if spec_grade != actual_grade:
                    compliant = False
                    issues.append(f"Grade mismatch: Spec={spec_grade}, Actual={actual_grade}")
            
            # Extract strength values
            spec_strength = None
            actual_strength = None
            
            if spec_data.get("strength"):
                try:
                    spec_strength = float(spec_data["strength"])
                except (ValueError, TypeError):
                    pass
            
            if boq_data.get("strength"):
                try:
                    actual_strength = float(boq_data["strength"])
                except (ValueError, TypeError):
                    pass
            
            merged.append(MergedMaterialSpec(
                material_type=material_type,
                spec_grade=spec_grade,
                boq_grade=boq_grade,
                drawing_grade=drawing_grade,
                actual_grade=actual_grade,
                spec_strength=spec_strength,
                actual_strength=actual_strength,
                compliant=compliant,
                issues=issues,
            ))
        
        return merged
    
    def _detect_conflicts(self, merged: MergedProjectData) -> List[Dict[str, Any]]:
        """Detect conflicts in merged data."""
        conflicts = []
        
        # Check quantity variances
        for qty in merged.quantities:
            if qty.has_variance and qty.variance_percent:
                if qty.variance_percent > 0.15:  # > 15% variance
                    conflicts.append({
                        "type": "quantity_variance_critical",
                        "item": qty.item_id,
                        "variance_percent": qty.variance_percent * 100,
                        "severity": "critical",
                        "sources": [s for s, v in [
                            ("BOQ", qty.boq_quantity),
                            ("Drawing", qty.drawing_quantity),
                            ("Spec", qty.spec_quantity),
                        ] if v is not None],
                    })
        
        # Check material compliance
        for mat in merged.materials:
            if not mat.compliant:
                conflicts.append({
                    "type": "material_non_compliance",
                    "material": mat.material_type,
                    "issues": mat.issues,
                    "severity": "critical",
                })
        
        return conflicts
    
    def _calculate_completeness(self, merged: MergedProjectData) -> float:
        """Calculate data completeness score."""
        total_items = len(merged.quantities)
        if total_items == 0:
            return 0.0
        
        # Count items with data from all three sources
        complete_items = sum(
            1 for q in merged.quantities
            if q.boq_quantity is not None and
               q.drawing_quantity is not None and
               q.spec_quantity is not None
        )
        
        return complete_items / total_items
    
    def export_to_reasoning_format(
        self,
        merged: MergedProjectData
    ) -> Dict[str, Any]:
        """Export merged data to format expected by reasoning engine."""
        return {
            "quantities": [
                {
                    "id": q.item_id,
                    "description": q.description,
                    "boq": q.boq_quantity,
                    "drawing": q.drawing_quantity,
                    "spec": q.spec_quantity,
                    "reconciled": q.reconciled_quantity,
                    "has_variance": q.has_variance,
                    "variance_percent": q.variance_percent,
                    "notes": q.variance_notes,
                }
                for q in merged.quantities
            ],
            "materials": [
                {
                    "type": m.material_type,
                    "spec_grade": m.spec_grade,
                    "actual_grade": m.actual_grade,
                    "spec_strength": m.spec_strength,
                    "actual_strength": m.actual_strength,
                    "compliant": m.compliant,
                    "issues": m.issues,
                }
                for m in merged.materials
            ],
            "conflicts": merged.conflicts,
            "stats": merged.merge_stats,
            "completeness": merged.metadata.get("completeness_score", 0),
        }
