"""
RSMeans API Integration for Construction Cost Pricing
Fetches and manages construction cost data from RSMeans.
"""

import json
import asyncio
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
import aiohttp

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


@dataclass
class CostItem:
    """RSMeans cost item."""
    rsmeans_id: str
    description: str
    unit: str
    crew: Optional[str] = None
    
    # Costs
    material_cost: Decimal = Decimal('0')
    labor_cost: Decimal = Decimal('0')
    equipment_cost: Decimal = Decimal('0')
    
    # Totals
    total_cost: Decimal = field(init=False)
    
    # Metadata
    city_cost_index: Optional[float] = None
    zip_code: Optional[str] = None
    year: int = 2024
    quarter: int = 1
    
    def __post_init__(self):
        self.total_cost = self.material_cost + self.labor_cost + self.equipment_cost
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rsmeans_id": self.rsmeans_id,
            "description": self.description,
            "unit": self.unit,
            "crew": self.crew,
            "material_cost": float(self.material_cost),
            "labor_cost": float(self.labor_cost),
            "equipment_cost": float(self.equipment_cost),
            "total_cost": float(self.total_cost),
            "city_cost_index": self.city_cost_index,
            "zip_code": self.zip_code,
            "year": self.year,
            "quarter": self.quarter
        }


@dataclass
class LocationFactor:
    """Location cost factor for a city/region."""
    city: str
    state: str
    zip_code: Optional[str]
    cost_index: float
    material_index: float
    labor_index: float
    equipment_index: float
    
    def apply_to_cost(self, base_cost: Decimal, cost_type: str = "total") -> Decimal:
        """Apply location factor to base cost."""
        factors = {
            "total": self.cost_index,
            "material": self.material_index,
            "labor": self.labor_index,
            "equipment": self.equipment_index
        }
        factor = factors.get(cost_type, self.cost_index)
        return base_cost * Decimal(str(factor / 100))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "cost_index": self.cost_index,
            "material_index": self.material_index,
            "labor_index": self.labor_index,
            "equipment_index": self.equipment_index
        }


class RSMeansAPI:
    """
    RSMeans API client for construction cost data.
    Supports cost lookups, location factors, and crew rates.
    """
    
    BASE_URL = "https://api.rsmeans.com/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.RSMEANS_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self.session
    
    async def get_cost_item(
        self,
        rsmeans_id: str,
        zip_code: Optional[str] = None,
        year: int = 2024,
        quarter: int = 1
    ) -> Optional[CostItem]:
        """
        Get cost item by RSMeans ID.
        
        Args:
            rsmeans_id: RSMeans cost item ID
            zip_code: Optional ZIP code for location adjustment
            year: Cost data year
            quarter: Cost data quarter
        
        Returns:
            CostItem or None if not found
        """
        cache_key = f"{rsmeans_id}_{zip_code}_{year}_{quarter}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            session = await self._get_session()
            
            params = {
                "year": year,
                "quarter": quarter
            }
            if zip_code:
                params["zipCode"] = zip_code
            
            url = f"{self.BASE_URL}/costs/{rsmeans_id}"
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    cost_item = CostItem(
                        rsmeans_id=data.get("id"),
                        description=data.get("description", ""),
                        unit=data.get("unit", "ea"),
                        crew=data.get("crew"),
                        material_cost=Decimal(str(data.get("materialCost", 0))),
                        labor_cost=Decimal(str(data.get("laborCost", 0))),
                        equipment_cost=Decimal(str(data.get("equipmentCost", 0))),
                        city_cost_index=data.get("cityCostIndex"),
                        zip_code=zip_code,
                        year=year,
                        quarter=quarter
                    )
                    
                    self._cache[cache_key] = cost_item
                    return cost_item
                    
                elif response.status == 404:
                    logger.warning(f"Cost item {rsmeans_id} not found")
                    return None
                else:
                    logger.error(f"RSMeans API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get cost item: {e}")
            return None
    
    async def search_cost_items(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[CostItem]:
        """
        Search for cost items.
        
        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results
        
        Returns:
            List of matching CostItems
        """
        try:
            session = await self._get_session()
            
            params = {
                "q": query,
                "limit": limit
            }
            if category:
                params["category"] = category
            
            url = f"{self.BASE_URL}/costs/search"
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    results = []
                    for item in data.get("results", []):
                        cost_item = CostItem(
                            rsmeans_id=item.get("id"),
                            description=item.get("description", ""),
                            unit=item.get("unit", "ea"),
                            material_cost=Decimal(str(item.get("materialCost", 0))),
                            labor_cost=Decimal(str(item.get("laborCost", 0))),
                            equipment_cost=Decimal(str(item.get("equipmentCost", 0)))
                        )
                        results.append(cost_item)
                    
                    return results
                else:
                    logger.error(f"RSMeans search error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to search cost items: {e}")
            return []
    
    async def get_location_factor(
        self,
        zip_code: str
    ) -> Optional[LocationFactor]:
        """
        Get location cost factor for ZIP code.
        
        Args:
            zip_code: ZIP code
        
        Returns:
            LocationFactor or None
        """
        cache_key = f"loc_{zip_code}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            session = await self._get_session()
            
            url = f"{self.BASE_URL}/location-factors/{zip_code}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    factor = LocationFactor(
                        city=data.get("city", ""),
                        state=data.get("state", ""),
                        zip_code=zip_code,
                        cost_index=data.get("costIndex", 100),
                        material_index=data.get("materialIndex", 100),
                        labor_index=data.get("laborIndex", 100),
                        equipment_index=data.get("equipmentIndex", 100)
                    )
                    
                    self._cache[cache_key] = factor
                    return factor
                    
                else:
                    logger.warning(f"Location factor for {zip_code} not found")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get location factor: {e}")
            return None
    
    async def get_crew_rates(
        self,
        crew_code: str,
        zip_code: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get crew labor rates.
        
        Args:
            crew_code: Crew code (e.g., 'C1', 'C2')
            zip_code: Optional ZIP code for location adjustment
        
        Returns:
            Crew rate data or None
        """
        try:
            session = await self._get_session()
            
            params = {}
            if zip_code:
                params["zipCode"] = zip_code
            
            url = f"{self.BASE_URL}/crews/{crew_code}"
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get crew rates: {e}")
            return None
    
    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()


class PricingEngine:
    """
    Construction pricing engine using RSMeans data.
    Calculates costs with location adjustments, markups, and contingencies.
    """
    
    def __init__(self):
        self.rsmeans = RSMeansAPI()
        self._overhead_markup: Decimal = Decimal('0.10')  # 10%
        self._profit_markup: Decimal = Decimal('0.05')  # 5%
        self._contingency: Decimal = Decimal('0.05')  # 5%
    
    async def calculate_item_cost(
        self,
        rsmeans_id: str,
        quantity: Decimal,
        zip_code: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate total cost for a cost item.
        
        Args:
            rsmeans_id: RSMeans cost item ID
            quantity: Quantity
            zip_code: Optional ZIP code for location adjustment
            options: Additional options (markups, etc.)
        
        Returns:
            Cost breakdown dictionary
        """
        # Get base cost item
        cost_item = await self.rsmeans.get_cost_item(rsmeans_id, zip_code)
        
        if not cost_item:
            return {"error": f"Cost item {rsmeans_id} not found"}
        
        # Get location factor
        location_factor = None
        if zip_code:
            location_factor = await self.rsmeans.get_location_factor(zip_code)
        
        # Apply location adjustment
        if location_factor:
            material_cost = location_factor.apply_to_cost(cost_item.material_cost, "material")
            labor_cost = location_factor.apply_to_cost(cost_item.labor_cost, "labor")
            equipment_cost = location_factor.apply_to_cost(cost_item.equipment_cost, "equipment")
        else:
            material_cost = cost_item.material_cost
            labor_cost = cost_item.labor_cost
            equipment_cost = cost_item.equipment_cost
        
        # Calculate base cost
        base_cost = (material_cost + labor_cost + equipment_cost) * quantity
        
        # Apply markups
        options = options or {}
        overhead = options.get('overhead', self._overhead_markup)
        profit = options.get('profit', self._profit_markup)
        contingency = options.get('contingency', self._contingency)
        
        overhead_amount = base_cost * overhead
        profit_amount = base_cost * profit
        contingency_amount = base_cost * contingency
        
        total_cost = base_cost + overhead_amount + profit_amount + contingency_amount
        
        return {
            "rsmeans_id": rsmeans_id,
            "description": cost_item.description,
            "unit": cost_item.unit,
            "quantity": float(quantity),
            "zip_code": zip_code,
            "location_factor": location_factor.to_dict() if location_factor else None,
            "cost_breakdown": {
                "material": float(material_cost * quantity),
                "labor": float(labor_cost * quantity),
                "equipment": float(equipment_cost * quantity),
                "base_total": float(base_cost)
            },
            "markups": {
                "overhead": float(overhead_amount),
                "profit": float(profit_amount),
                "contingency": float(contingency_amount)
            },
            "total_cost": float(total_cost),
            "unit_price": float(total_cost / quantity) if quantity > 0 else 0
        }
    
    async def calculate_takeoff_costs(
        self,
        takeoff_items: List[Dict[str, Any]],
        zip_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate costs for quantity takeoff items.
        
        Args:
            takeoff_items: List of takeoff items with rsmeans_id and quantity
            zip_code: Optional ZIP code
        
        Returns:
            Summary of all costs
        """
        results = []
        total_material = Decimal('0')
        total_labor = Decimal('0')
        total_equipment = Decimal('0')
        total_cost = Decimal('0')
        
        for item in takeoff_items:
            rsmeans_id = item.get('rsmeans_id')
            quantity = Decimal(str(item.get('quantity', 0)))
            
            if rsmeans_id and quantity > 0:
                result = await self.calculate_item_cost(rsmeans_id, quantity, zip_code)
                
                if 'error' not in result:
                    results.append(result)
                    
                    breakdown = result.get('cost_breakdown', {})
                    total_material += Decimal(str(breakdown.get('material', 0)))
                    total_labor += Decimal(str(breakdown.get('labor', 0)))
                    total_equipment += Decimal(str(breakdown.get('equipment', 0)))
                    total_cost += Decimal(str(result.get('total_cost', 0)))
        
        return {
            "items": results,
            "summary": {
                "item_count": len(results),
                "total_material": float(total_material),
                "total_labor": float(total_labor),
                "total_equipment": float(total_equipment),
                "total_cost": float(total_cost)
            }
        }
    
    def set_markup_rates(
        self,
        overhead: Optional[Decimal] = None,
        profit: Optional[Decimal] = None,
        contingency: Optional[Decimal] = None
    ) -> None:
        """Set default markup rates."""
        if overhead is not None:
            self._overhead_markup = overhead
        if profit is not None:
            self._profit_markup = profit
        if contingency is not None:
            self._contingency = contingency
    
    async def close(self):
        """Cleanup resources."""
        await self.rsmeans.close()


# Singleton instance
pricing_engine = PricingEngine()


async def get_pricing_engine() -> PricingEngine:
    """Get pricing engine instance."""
    return pricing_engine
