"""
5D BIM - Cost Integration with Heatmaps
Links 3D model elements to cost data for 5D cost visualization.
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import uuid
import json
import logging

from .federated_models import ModelElement, FederatedModel, BoundingBox, Point3D

logger = logging.getLogger(__name__)


class CostCategory(str, Enum):
    """Cost categories for 5D BIM."""
    MATERIALS = "materials"
    LABOR = "labor"
    EQUIPMENT = "equipment"
    SUBCONTRACTOR = "subcontractor"
    OVERHEAD = "overhead"
    CONTINGENCY = "contingency"
    PERMIT = "permit"
    INSURANCE = "insurance"


class CostStatus(str, Enum):
    """Cost status for budget tracking."""
    ESTIMATED = "estimated"
    APPROVED = "approved"
    COMMITTED = "committed"
    INVOICED = "invoiced"
    PAID = "paid"
    VARIANCE = "variance"


@dataclass
class CostItem:
    """Represents a cost item linked to model elements."""
    id: str
    name: str
    category: CostCategory
    element_ids: List[str]
    unit_cost: float
    quantity: float
    unit_of_measure: str
    total_cost: float = 0.0
    status: CostStatus = CostStatus.ESTIMATED
    budget_amount: float = 0.0
    actual_amount: float = 0.0
    variance: float = 0.0
    vendor: Optional[str] = None
    trade: Optional[str] = None
    wbs_code: str = ""
    notes: str = ""
    
    def __post_init__(self):
        self.total_cost = self.unit_cost * self.quantity
        self.variance = self.actual_amount - self.budget_amount
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category.value,
            'unit_cost': self.unit_cost,
            'quantity': self.quantity,
            'unit_of_measure': self.unit_of_measure,
            'total_cost': self.total_cost,
            'status': self.status.value,
            'budget_amount': self.budget_amount,
            'actual_amount': self.actual_amount,
            'variance': self.variance,
            'vendor': self.vendor,
            'trade': self.trade,
            'wbs_code': self.wbs_code
        }


@dataclass
class Cost5D:
    """5D cost model linked to BIM."""
    id: str
    name: str
    project_id: str
    federated_model_id: str
    cost_items: List[CostItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    currency: str = "USD"
    base_date: date = field(default_factory=date.today)
    
    @property
    def total_budget(self) -> float:
        return sum(item.budget_amount for item in self.cost_items)
    
    @property
    def total_actual(self) -> float:
        return sum(item.actual_amount for item in self.cost_items)
    
    @property
    def total_variance(self) -> float:
        return self.total_actual - self.total_budget
    
    @property
    def variance_percentage(self) -> float:
        if self.total_budget == 0:
            return 0.0
        return (self.total_variance / self.total_budget) * 100
    
    @property
    def cost_by_category(self) -> Dict[str, float]:
        """Get costs grouped by category."""
        by_category = {}
        for item in self.cost_items:
            cat = item.category.value
            if cat not in by_category:
                by_category[cat] = {'budget': 0, 'actual': 0}
            by_category[cat]['budget'] += item.budget_amount
            by_category[cat]['actual'] += item.actual_amount
        return by_category
    
    @property
    def cost_by_trade(self) -> Dict[str, float]:
        """Get costs grouped by trade."""
        by_trade = {}
        for item in self.cost_items:
            trade = item.trade or "Unassigned"
            if trade not in by_trade:
                by_trade[trade] = {'budget': 0, 'actual': 0}
            by_trade[trade]['budget'] += item.budget_amount
            by_trade[trade]['actual'] += item.actual_amount
        return by_trade
    
    def get_cost_for_element(self, element_id: str) -> float:
        """Get total cost for a specific element."""
        return sum(
            item.total_cost 
            for item in self.cost_items 
            if element_id in item.element_ids
        )
    
    def get_elements_by_cost_range(self, min_cost: float, 
                                   max_cost: float) -> List[str]:
        """Get element IDs within a cost range."""
        element_costs = {}
        for item in self.cost_items:
            for elem_id in item.element_ids:
                if elem_id not in element_costs:
                    element_costs[elem_id] = 0
                element_costs[elem_id] += item.unit_cost * (item.quantity / len(item.element_ids))
        
        return [
            elem_id for elem_id, cost in element_costs.items()
            if min_cost <= cost <= max_cost
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'project_id': self.project_id,
            'federated_model_id': self.federated_model_id,
            'total_budget': self.total_budget,
            'total_actual': self.total_actual,
            'total_variance': self.total_variance,
            'variance_percentage': self.variance_percentage,
            'currency': self.currency,
            'cost_by_category': self.cost_by_category,
            'cost_by_trade': self.cost_by_trade,
            'cost_items_count': len(self.cost_items)
        }


@dataclass
class CostHeatmapPoint:
    """Point in a cost heatmap."""
    position: Point3D
    cost_density: float  # cost per unit volume
    total_cost: float
    element_count: int
    color_value: float  # 0-1 for color mapping


class CostHeatmapGenerator:
    """Generates cost heatmaps for 5D visualization."""
    
    def __init__(self, cost_model: Cost5D, federated_model: FederatedModel):
        self.cost_model = cost_model
        self.federated_model = federated_model
    
    def generate_heatmap(self, 
                        resolution: float = 1.0,
                        cost_type: str = "total") -> List[CostHeatmapPoint]:
        """Generate cost heatmap data."""
        heatmap_points = []
        
        # Get overall bounding box
        bbox = self.federated_model.overall_bounding_box
        if not bbox:
            return heatmap_points
        
        # Create grid
        dims = bbox.dimensions
        nx = max(1, int(dims[0] / resolution))
        ny = max(1, int(dims[1] / resolution))
        nz = max(1, int(dims[2] / resolution))
        
        for i in range(nx):
            for j in range(ny):
                for k in range(nz):
                    # Calculate grid cell center
                    x = bbox.min_point.x + (i + 0.5) * resolution
                    y = bbox.min_point.y + (j + 0.5) * resolution
                    z = bbox.min_point.z + (k + 0.5) * resolution
                    center = Point3D(x, y, z)
                    
                    # Find elements in this cell
                    cell_bbox = BoundingBox(
                        Point3D(x - resolution/2, y - resolution/2, z - resolution/2),
                        Point3D(x + resolution/2, y + resolution/2, z + resolution/2)
                    )
                    
                    elements_in_cell = self._get_elements_in_cell(cell_bbox)
                    
                    if elements_in_cell:
                        total_cost = sum(
                            self.cost_model.get_cost_for_element(e.id)
                            for e in elements_in_cell
                        )
                        cell_volume = resolution ** 3
                        cost_density = total_cost / cell_volume if cell_volume > 0 else 0
                        
                        heatmap_points.append(CostHeatmapPoint(
                            position=center,
                            cost_density=cost_density,
                            total_cost=total_cost,
                            element_count=len(elements_in_cell),
                            color_value=0.0  # Will be calculated
                        ))
        
        # Normalize color values
        if heatmap_points:
            max_density = max(p.cost_density for p in heatmap_points)
            for point in heatmap_points:
                point.color_value = point.cost_density / max_density if max_density > 0 else 0
        
        return heatmap_points
    
    def _get_elements_in_cell(self, cell_bbox: BoundingBox) -> List[ModelElement]:
        """Get elements that intersect with a grid cell."""
        elements = []
        for element in self.federated_model.get_all_elements():
            if element.bounding_box.intersects(cell_bbox):
                elements.append(element)
        return elements
    
    def generate_trade_heatmap(self, trade: str,
                              resolution: float = 1.0) -> List[CostHeatmapPoint]:
        """Generate heatmap for a specific trade."""
        # Filter cost items by trade
        trade_items = [
            item for item in self.cost_model.cost_items
            if item.trade == trade
        ]
        
        # Generate heatmap using only trade items
        heatmap_points = []
        
        for item in trade_items:
            for element_id in item.element_ids:
                element = self._get_element_by_id(element_id)
                if element:
                    center = element.bounding_box.center
                    heatmap_points.append(CostHeatmapPoint(
                        position=center,
                        cost_density=item.unit_cost,
                        total_cost=item.total_cost / len(item.element_ids),
                        element_count=1,
                        color_value=0.0
                    ))
        
        # Normalize
        if heatmap_points:
            max_cost = max(p.total_cost for p in heatmap_points)
            for point in heatmap_points:
                point.color_value = point.total_cost / max_cost if max_cost > 0 else 0
        
        return heatmap_points
    
    def _get_element_by_id(self, element_id: str) -> Optional[ModelElement]:
        """Get element by ID."""
        for element in self.federated_model.get_all_elements():
            if element.id == element_id:
                return element
        return None
    
    def get_color_for_value(self, value: float, 
                           color_scheme: str = "red_green") -> str:
        """Get color for heatmap value (0-1)."""
        if color_scheme == "red_green":
            # Red (high cost) to Green (low cost)
            r = int(255 * value)
            g = int(255 * (1 - value))
            b = 0
        elif color_scheme == "blue_yellow_red":
            # Blue to Yellow to Red
            if value < 0.5:
                r = int(255 * value * 2)
                g = int(255 * value * 2)
                b = int(255 * (1 - value * 2))
            else:
                r = 255
                g = int(255 * (1 - (value - 0.5) * 2))
                b = 0
        else:
            # Grayscale
            v = int(255 * value)
            r = g = b = v
        
        return f"#{r:02x}{g:02x}{b:02x}"


class Cost5DEngine:
    """Engine for 5D cost management."""
    
    def __init__(self):
        self.cost_models: Dict[str, Cost5D] = {}
    
    def create_cost_model(self, name: str, project_id: str,
                         federated_model_id: str,
                         currency: str = "USD") -> Cost5D:
        """Create a new 5D cost model."""
        cost_model = Cost5D(
            id=str(uuid.uuid4()),
            name=name,
            project_id=project_id,
            federated_model_id=federated_model_id,
            currency=currency
        )
        self.cost_models[cost_model.id] = cost_model
        logger.info(f"Created 5D cost model: {name}")
        return cost_model
    
    def add_cost_item(self, cost_model_id: str, cost_item: CostItem) -> bool:
        """Add a cost item to the model."""
        cost_model = self.cost_models.get(cost_model_id)
        if not cost_model:
            return False
        
        cost_model.cost_items.append(cost_item)
        cost_model.updated_at = datetime.utcnow()
        return True
    
    def update_actual_cost(self, cost_model_id: str, cost_item_id: str,
                          actual_amount: float) -> bool:
        """Update actual cost for a cost item."""
        cost_model = self.cost_models.get(cost_model_id)
        if not cost_model:
            return False
        
        for item in cost_model.cost_items:
            if item.id == cost_item_id:
                item.actual_amount = actual_amount
                item.variance = actual_amount - item.budget_amount
                item.status = CostStatus.PAID if actual_amount > 0 else item.status
                cost_model.updated_at = datetime.utcnow()
                return True
        
        return False
    
    def generate_budget_report(self, cost_model_id: str) -> Dict[str, Any]:
        """Generate budget vs actual report."""
        cost_model = self.cost_models.get(cost_model_id)
        if not cost_model:
            return {}
        
        return {
            'model_id': cost_model_id,
            'name': cost_model.name,
            'currency': cost_model.currency,
            'summary': {
                'total_budget': cost_model.total_budget,
                'total_actual': cost_model.total_actual,
                'total_variance': cost_model.total_variance,
                'variance_percentage': cost_model.variance_percentage
            },
            'by_category': cost_model.cost_by_category,
            'by_trade': cost_model.cost_by_trade,
            'variance_items': [
                item.to_dict() 
                for item in cost_model.cost_items 
                if abs(item.variance) > 0
            ]
        }
    
    def generate_heatmap(self, cost_model_id: str,
                        federated_model: FederatedModel,
                        resolution: float = 1.0) -> List[Dict[str, Any]]:
        """Generate cost heatmap for visualization."""
        cost_model = self.cost_models.get(cost_model_id)
        if not cost_model:
            return []
        
        generator = CostHeatmapGenerator(cost_model, federated_model)
        heatmap = generator.generate_heatmap(resolution)
        
        return [
            {
                'x': p.position.x,
                'y': p.position.y,
                'z': p.position.z,
                'cost_density': p.cost_density,
                'total_cost': p.total_cost,
                'color_value': p.color_value,
                'color': generator.get_color_for_value(p.color_value)
            }
            for p in heatmap
        ]
    
    def export_to_excel(self, cost_model_id: str) -> bytes:
        """Export cost model to Excel format."""
        cost_model = self.cost_models.get(cost_model_id)
        if not cost_model:
            return b""
        
        # Placeholder - would use openpyxl
        lines = [
            "ID,Name,Category,WBS Code,Unit Cost,Quantity,UOM,Total Cost,Budget,Actual,Variance,Trade,Vendor"
        ]
        
        for item in cost_model.cost_items:
            lines.append(
                f'"{item.id}","{item.name}","{item.category.value}","{item.wbs_code}",'
                f'{item.unit_cost},{item.quantity},"{item.unit_of_measure}",'
                f'{item.total_cost},{item.budget_amount},{item.actual_amount},'
                f'{item.variance},"{item.trade or ""}","{item.vendor or ""}"'
            )
        
        return '\n'.join(lines).encode('utf-8')


# Convenience functions
def create_sample_cost_model(project_id: str,
                             federated_model_id: str) -> Cost5D:
    """Create a sample 5D cost model for testing."""
    engine = Cost5DEngine()
    cost_model = engine.create_cost_model("Sample Cost Model", 
                                         project_id, federated_model_id)
    
    # Add sample cost items
    sample_items = [
        CostItem(
            id=str(uuid.uuid4()),
            name="Concrete Foundation",
            category=CostCategory.MATERIALS,
            element_ids=["elem-1", "elem-2"],
            unit_cost=150.0,
            quantity=500.0,
            unit_of_measure="m3",
            budget_amount=75000.0,
            trade="Concrete",
            wbs_code="1.1.1"
        ),
        CostItem(
            id=str(uuid.uuid4()),
            name="Structural Steel",
            category=CostCategory.MATERIALS,
            element_ids=["elem-3", "elem-4", "elem-5"],
            unit_cost=2500.0,
            quantity=100.0,
            unit_of_measure="ton",
            budget_amount=250000.0,
            trade="Steel",
            wbs_code="2.1.1"
        ),
        CostItem(
            id=str(uuid.uuid4()),
            name="MEP Rough-in",
            category=CostCategory.LABOR,
            element_ids=["elem-6", "elem-7"],
            unit_cost=75.0,
            quantity=1000.0,
            unit_of_measure="hr",
            budget_amount=75000.0,
            trade="MEP",
            wbs_code="3.1.1"
        ),
    ]
    
    for item in sample_items:
        engine.add_cost_item(cost_model.id, item)
    
    return cost_model
