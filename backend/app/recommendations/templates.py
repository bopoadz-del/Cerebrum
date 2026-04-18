"""
Formula Templates for Construction Domain

Pre-defined templates for common construction calculations:
- Concrete calculations
- Rebar estimation
- Cost estimation
- Structural analysis
- Earthwork calculations
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TemplateInput:
    """Input parameter for a formula template."""
    name: str
    type: str = "float"
    unit: str = ""
    required: bool = True
    description: str = ""
    default_value: Optional[Any] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class TemplateOutput:
    """Output parameter for a formula template."""
    name: str
    type: str = "float"
    unit: str = ""
    description: str = ""


@dataclass
class FormulaTemplate:
    """Formula template definition."""
    id: str
    name: str
    description: str
    category: str
    formula: str
    inputs: List[TemplateInput]
    outputs: List[TemplateOutput]
    tags: List[str] = field(default_factory=list)
    required_elements: List[str] = field(default_factory=list)
    usage_count: int = 0
    version: str = "1.0.0"
    references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "formula": self.formula,
            "inputs": [
                {
                    "name": inp.name,
                    "type": inp.type,
                    "unit": inp.unit,
                    "required": inp.required,
                    "description": inp.description,
                    "default_value": inp.default_value,
                    "min_value": inp.min_value,
                    "max_value": inp.max_value,
                }
                for inp in self.inputs
            ],
            "outputs": [
                {
                    "name": out.name,
                    "type": out.type,
                    "unit": out.unit,
                    "description": out.description,
                }
                for out in self.outputs
            ],
            "tags": self.tags,
            "required_elements": self.required_elements,
            "usage_count": self.usage_count,
            "version": self.version,
            "references": self.references,
        }


class TemplateManager:
    """
    Manager for formula templates.
    
    Loads, stores, and retrieves formula templates for construction calculations.
    Supports category-based organization and tag-based filtering.
    """
    
    def __init__(self, templates_path: Optional[str] = None):
        self.templates: Dict[str, FormulaTemplate] = {}
        self.templates_by_category: Dict[str, List[str]] = {}
        self.templates_by_tag: Dict[str, List[str]] = {}
        
        # Default path for templates
        if templates_path is None:
            backend_dir = Path(__file__).parent.parent.parent
            self.templates_path = backend_dir.parent / "data" / "templates" / "formula_templates.json"
        else:
            self.templates_path = Path(templates_path)
    
    async def load_templates(self) -> None:
        """Load templates from JSON file."""
        try:
            if self.templates_path.exists():
                with open(self.templates_path, "r") as f:
                    data = json.load(f)
                
                for template_data in data.get("templates", []):
                    template = self._parse_template(template_data)
                    self._add_template(template)
                
                logger.info(f"Loaded {len(self.templates)} templates")
            else:
                logger.warning(f"Templates file not found: {self.templates_path}")
                # Load default templates
                self._load_default_templates()
        except Exception as e:
            logger.error(f"Failed to load templates: {e}")
            self._load_default_templates()
    
    def _parse_template(self, data: Dict[str, Any]) -> FormulaTemplate:
        """Parse template from dictionary."""
        inputs = [
            TemplateInput(
                name=inp["name"],
                type=inp.get("type", "float"),
                unit=inp.get("unit", ""),
                required=inp.get("required", True),
                description=inp.get("description", ""),
                default_value=inp.get("default_value"),
                min_value=inp.get("min_value"),
                max_value=inp.get("max_value"),
            )
            for inp in data.get("inputs", [])
        ]
        
        outputs = [
            TemplateOutput(
                name=out["name"],
                type=out.get("type", "float"),
                unit=out.get("unit", ""),
                description=out.get("description", ""),
            )
            for out in data.get("outputs", [])
        ]
        
        return FormulaTemplate(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            category=data.get("category", "general"),
            formula=data.get("formula", ""),
            inputs=inputs,
            outputs=outputs,
            tags=data.get("tags", []),
            required_elements=data.get("required_elements", []),
            usage_count=data.get("usage_count", 0),
            version=data.get("version", "1.0.0"),
            references=data.get("references", []),
        )
    
    def _add_template(self, template: FormulaTemplate) -> None:
        """Add template to indexes."""
        self.templates[template.id] = template
        
        # Index by category
        if template.category not in self.templates_by_category:
            self.templates_by_category[template.category] = []
        self.templates_by_category[template.category].append(template.id)
        
        # Index by tag
        for tag in template.tags:
            if tag not in self.templates_by_tag:
                self.templates_by_tag[tag] = []
            self.templates_by_tag[tag].append(template.id)
    
    def get_template(self, template_id: str) -> Optional[FormulaTemplate]:
        """Get template by ID."""
        return self.templates.get(template_id)
    
    def get_templates_by_category(self, category: str) -> List[FormulaTemplate]:
        """Get all templates in a category."""
        template_ids = self.templates_by_category.get(category, [])
        return [self.templates[tid] for tid in template_ids if tid in self.templates]
    
    def get_templates_by_tag(self, tag: str) -> List[FormulaTemplate]:
        """Get all templates with a specific tag."""
        template_ids = self.templates_by_tag.get(tag, [])
        return [self.templates[tid] for tid in template_ids if tid in self.templates]
    
    def get_templates_for_context(
        self,
        project_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[FormulaTemplate]:
        """Get templates relevant to the given context."""
        candidates = set()
        
        # By project type (category)
        if project_type:
            category_templates = self.templates_by_category.get(project_type, [])
            candidates.update(category_templates)
        
        # By tags
        if tags:
            for tag in tags:
                tag_templates = self.templates_by_tag.get(tag, [])
                candidates.update(tag_templates)
        
        # If no context, return all templates
        if not candidates:
            return list(self.templates.values())
        
        return [self.templates[tid] for tid in candidates if tid in self.templates]
    
    def search_templates(self, query: str) -> List[FormulaTemplate]:
        """Search templates by name, description, or tags."""
        query = query.lower()
        results = []
        
        for template in self.templates.values():
            if (
                query in template.name.lower()
                or query in template.description.lower()
                or any(query in tag.lower() for tag in template.tags)
            ):
                results.append(template)
        
        return results
    
    def increment_usage(self, template_id: str) -> None:
        """Increment usage count for a template."""
        if template_id in self.templates:
            self.templates[template_id].usage_count += 1
    
    def get_all_templates(self) -> List[FormulaTemplate]:
        """Get all templates."""
        return list(self.templates.values())
    
    def get_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self.templates_by_category.keys())
    
    def get_tags(self) -> List[str]:
        """Get all available tags."""
        return list(self.templates_by_tag.keys())
    
    def _load_default_templates(self) -> None:
        """Load built-in default templates."""
        logger.info("Loading default templates")
        
        # Concrete Volume
        self._add_template(FormulaTemplate(
            id="concrete_volume_basic",
            name="Concrete Volume",
            description="Calculate volume of concrete for rectangular elements",
            category="concrete",
            formula="length * width * height",
            inputs=[
                TemplateInput("length", "float", "m", True, "Element length"),
                TemplateInput("width", "float", "m", True, "Element width"),
                TemplateInput("height", "float", "m", True, "Element height/thickness"),
            ],
            outputs=[
                TemplateOutput("volume", "float", "m³", "Total concrete volume"),
            ],
            tags=["concrete", "volume", "basic", "rectangular"],
            references=["ACI 318"],
        ))
        
        # Concrete Volume (Cylindrical)
        self._add_template(FormulaTemplate(
            id="concrete_volume_cylinder",
            name="Concrete Volume (Cylindrical)",
            description="Calculate concrete volume for cylindrical elements like columns",
            category="concrete",
            formula="pi * (diameter / 2) ** 2 * height",
            inputs=[
                TemplateInput("diameter", "float", "m", True, "Column diameter"),
                TemplateInput("height", "float", "m", True, "Column height"),
            ],
            outputs=[
                TemplateOutput("volume", "float", "m³", "Total concrete volume"),
            ],
            tags=["concrete", "volume", "cylinder", "column"],
            references=["ACI 318"],
        ))
        
        # Rebar Weight
        self._add_template(FormulaTemplate(
            id="rebar_weight_basic",
            name="Rebar Weight",
            description="Calculate total weight of reinforcing steel",
            category="rebar",
            formula="(count * length * weight_per_meter) / 1000",
            inputs=[
                TemplateInput("count", "int", "pcs", True, "Number of rebars"),
                TemplateInput("length", "float", "m", True, "Length of each rebar"),
                TemplateInput("weight_per_meter", "float", "kg/m", True, "Weight per meter for bar size"),
            ],
            outputs=[
                TemplateOutput("total_weight", "float", "ton", "Total rebar weight"),
            ],
            tags=["rebar", "steel", "weight", "estimation"],
            references=["ASTM A615"],
        ))
        
        # Rebar Estimation by Area
        self._add_template(FormulaTemplate(
            id="rebar_by_area",
            name="Rebar Estimation (Area Based)",
            description="Estimate rebar required based on concrete area and typical ratios",
            category="rebar",
            formula="(concrete_area * rebar_ratio * steel_density) / 1000",
            inputs=[
                TemplateInput("concrete_area", "float", "m²", True, "Concrete surface area"),
                TemplateInput("rebar_ratio", "float", "kg/m²", True, "Rebar ratio (typically 80-150 kg/m²)"),
                TemplateInput("steel_density", "float", "kg/m³", False, "Steel density", 7850),
            ],
            outputs=[
                TemplateOutput("estimated_weight", "float", "ton", "Estimated rebar weight"),
            ],
            tags=["rebar", "estimation", "area", "ratio"],
            references=["Typical construction ratios"],
        ))
        
        # Cost Estimation (Material)
        self._add_template(FormulaTemplate(
            id="material_cost_basic",
            name="Material Cost Estimation",
            description="Calculate material costs based on quantities and unit prices",
            category="cost_estimation",
            formula="sum(quantity * unit_price for each material)",
            inputs=[
                TemplateInput("quantities", "array", "various", True, "Material quantities"),
                TemplateInput("unit_prices", "array", "currency", True, "Unit prices per material"),
                TemplateInput("wastage_factor", "float", "%", False, "Wastage percentage", 0.05, 0.0, 0.3),
            ],
            outputs=[
                TemplateOutput("total_cost", "float", "currency", "Total material cost"),
                TemplateOutput("cost_with_wastage", "float", "currency", "Cost including wastage"),
            ],
            tags=["cost", "estimation", "material", "budget"],
            references=["Standard estimating practices"],
        ))
        
        # Labor Cost Estimation
        self._add_template(FormulaTemplate(
            id="labor_cost_basic",
            name="Labor Cost Estimation",
            description="Estimate labor costs based on productivity rates",
            category="cost_estimation",
            formula="(work_quantity / productivity_rate) * hourly_rate",
            inputs=[
                TemplateInput("work_quantity", "float", "various", True, "Quantity of work"),
                TemplateInput("productivity_rate", "float", "unit/hr", True, "Worker productivity rate"),
                TemplateInput("hourly_rate", "float", "currency/hr", True, "Labor hourly rate"),
                TemplateInput("crew_size", "int", "workers", False, "Number of workers", 1, 1),
            ],
            outputs=[
                TemplateOutput("labor_hours", "float", "hours", "Total labor hours"),
                TemplateOutput("labor_cost", "float", "currency", "Total labor cost"),
            ],
            tags=["cost", "labor", "estimation", "productivity"],
            references=["RS Means", "Craftsman"],
        ))
        
        # Beam Moment
        self._add_template(FormulaTemplate(
            id="beam_moment_simple",
            name="Simple Beam Moment (Point Load)",
            description="Calculate maximum moment in simply supported beam with point load",
            category="structural_analysis",
            formula="(load * span) / 4",
            inputs=[
                TemplateInput("load", "float", "kN", True, "Point load at midspan"),
                TemplateInput("span", "float", "m", True, "Beam span length"),
            ],
            outputs=[
                TemplateOutput("max_moment", "float", "kN-m", "Maximum bending moment"),
            ],
            tags=["structural", "beam", "moment", "analysis"],
            references=["Structural Analysis - Hibbeler"],
        ))
        
        # Beam Deflection
        self._add_template(FormulaTemplate(
            id="beam_deflection_uniform",
            name="Beam Deflection (Uniform Load)",
            description="Calculate maximum deflection for simply supported beam with uniform load",
            category="structural_analysis",
            formula="(5 * load * span ** 4) / (384 * E * I)",
            inputs=[
                TemplateInput("load", "float", "kN/m", True, "Uniform distributed load"),
                TemplateInput("span", "float", "m", True, "Beam span"),
                TemplateInput("E", "float", "kPa", True, "Modulus of elasticity"),
                TemplateInput("I", "float", "m⁴", True, "Moment of inertia"),
            ],
            outputs=[
                TemplateOutput("deflection", "float", "m", "Maximum deflection at midspan"),
                TemplateOutput("deflection_mm", "float", "mm", "Deflection in millimeters"),
            ],
            tags=["structural", "beam", "deflection", "serviceability"],
            references=["Structural Analysis - Hibbeler"],
        ))
        
        # Column Axial Capacity
        self._add_template(FormulaTemplate(
            id="column_axial_capacity",
            name="Column Axial Capacity",
            description="Estimate concrete column axial load capacity",
            category="structural_analysis",
            formula="0.8 * (0.85 * f_c * (A_g - A_st) + f_y * A_st)",
            inputs=[
                TemplateInput("f_c", "float", "MPa", True, "Concrete compressive strength"),
                TemplateInput("f_y", "float", "MPa", True, "Steel yield strength"),
                TemplateInput("A_g", "float", "mm²", True, "Gross area of column"),
                TemplateInput("A_st", "float", "mm²", True, "Area of steel reinforcement"),
            ],
            outputs=[
                TemplateOutput("axial_capacity", "float", "kN", "Maximum axial load capacity"),
            ],
            tags=["structural", "column", "capacity", "concrete"],
            references=["ACI 318-19 Eq. (22.4.2.2)"],
        ))
        
        # Excavation Volume
        self._add_template(FormulaTemplate(
            id="excavation_volume_basic",
            name="Excavation Volume",
            description="Calculate volume of earth to be excavated",
            category="earthwork",
            formula="length * width * depth",
            inputs=[
                TemplateInput("length", "float", "m", True, "Excavation length"),
                TemplateInput("width", "float", "m", True, "Excavation width"),
                TemplateInput("depth", "float", "m", True, "Excavation depth"),
                TemplateInput("bulking_factor", "float", "ratio", False, "Soil bulking factor", 1.25, 1.0, 1.5),
            ],
            outputs=[
                TemplateOutput("bank_volume", "float", "m³", "In-situ (bank) volume"),
                TemplateOutput("loose_volume", "float", "m³", "Loose volume after excavation"),
            ],
            tags=["earthwork", "excavation", "volume", "soil"],
            references=["Earthwork Construction Principles"],
        ))
        
        # Cut and Fill
        self._add_template(FormulaTemplate(
            id="cut_fill_balance",
            name="Cut and Fill Balance",
            description="Calculate net earthwork (cut vs fill)",
            category="earthwork",
            formula="(cut_volume * shrinkage_factor) - fill_volume",
            inputs=[
                TemplateInput("cut_volume", "float", "m³", True, "Volume of material to be cut"),
                TemplateInput("fill_volume", "float", "m³", True, "Volume of fill required"),
                TemplateInput("shrinkage_factor", "float", "ratio", False, "Material shrinkage factor", 0.9, 0.7, 1.0),
            ],
            outputs=[
                TemplateOutput("net_volume", "float", "m³", "Net volume (positive=excess, negative=needed)"),
                TemplateOutput("haul_distance_estimate", "float", "m", "Estimated haul distance"),
            ],
            tags=["earthwork", "cut", "fill", "balance", "grading"],
            references=["Heavy Construction Methods"],
        ))
        
        # Slope Stability (Factor of Safety)
        self._add_template(FormulaTemplate(
            id="slope_fos_simple",
            name="Slope Factor of Safety (Infinite Slope)",
            description="Calculate factor of safety for infinite slope with seepage",
            category="earthwork",
            formula="(c + (gamma * z * cos(beta)**2 - gamma_w * h_w * cos(beta)**2) * tan(phi)) / (gamma * z * sin(beta) * cos(beta))",
            inputs=[
                TemplateInput("c", "float", "kPa", True, "Soil cohesion"),
                TemplateInput("phi", "float", "degrees", True, "Friction angle"),
                TemplateInput("gamma", "float", "kN/m³", True, "Soil unit weight"),
                TemplateInput("gamma_w", "float", "kN/m³", False, "Water unit weight", 9.81),
                TemplateInput("z", "float", "m", True, "Depth of failure surface"),
                TemplateInput("beta", "float", "degrees", True, "Slope angle"),
                TemplateInput("h_w", "float", "m", False, "Height of water table above failure surface", 0),
            ],
            outputs=[
                TemplateOutput("factor_of_safety", "float", "ratio", "Factor of safety against sliding"),
            ],
            tags=["earthwork", "slope", "stability", "geotechnical"],
            references=["Principles of Geotechnical Engineering - Das"],
        ))
        
        logger.info(f"Loaded {len(self.templates)} default templates")
