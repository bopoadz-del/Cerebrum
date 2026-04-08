"""
Intent Router for Natural Language Construction Queries
Deterministic keyword+regex router for fast responses without agent calls.
"""

import re
from typing import Optional, Dict, Any, Tuple

# RSMeans cost data (simplified for demo)
COST_DATA = {
    "concrete": {"unit": "yd³", "low": 120, "high": 150, "national": 135},
    "rebar": {"unit": "lb", "low": 0.80, "high": 1.20, "national": 1.00},
    "structural_steel": {"unit": "ton", "low": 2500, "high": 4000, "national": 3200},
    "lumber": {"unit": "board_ft", "low": 0.50, "high": 1.50, "national": 0.85},
    "drywall": {"unit": "sq_ft", "low": 1.50, "high": 2.50, "national": 2.00},
    "roofing": {"unit": "sq_ft", "low": 3.50, "high": 6.00, "national": 4.75},
    "flooring": {"unit": "sq_ft", "low": 3.00, "high": 12.00, "national": 7.50},
    "paint": {"unit": "sq_ft", "low": 2.00, "high": 5.00, "national": 3.50},
}

# Building type costs per sq ft
BUILDING_COSTS = {
    "office": {"low": 150, "high": 300, "national": 225},
    "warehouse": {"low": 80, "high": 150, "national": 115},
    "retail": {"low": 120, "high": 250, "national": 185},
    "hotel": {"low": 200, "high": 400, "national": 300},
    "hospital": {"low": 400, "high": 800, "national": 600},
    "school": {"low": 180, "high": 350, "national": 265},
    "apartment": {"low": 140, "high": 280, "national": 210},
}


def parse_dimensions(message: str) -> Optional[Tuple[float, float, float]]:
    """Parse dimensions like '10m x 5m x 0.5m' or '10 x 5 x 0.5'"""
    # Match patterns like: 10m x 5m x 0.5m, 10 x 5 x 0.5, 10.5m x 5.2m x 0.3m
    pattern = r'(\d+(?:\.\d+)?)\s*(?:m|meter|meters)?\s*[x,]\s*(\d+(?:\.\d+)?)\s*(?:m|meter|meters)?\s*[x,]\s*(\d+(?:\.\d+)?)\s*(?:m|meter|meters)?'
    match = re.search(pattern, message.lower())
    if match:
        length = float(match.group(1))
        width = float(match.group(2))
        depth = float(match.group(3))
        return (length, width, depth)
    return None


def parse_area(message: str) -> Optional[float]:
    """Parse area like '5000 sq ft' or '500 m2'"""
    # Match sq ft patterns
    sqft_pattern = r'(\d+(?:,\d+)*)\s*(?:sq\s*ft|sf|sqft|square\s*feet)'
    match = re.search(sqft_pattern, message.lower())
    if match:
        return float(match.group(1).replace(',', ''))
    
    # Match m2 patterns
    m2_pattern = r'(\d+(?:,\d+)*)\s*(?:m2|m²|sq\s*m|square\s*meters)'
    match = re.search(m2_pattern, message.lower())
    if match:
        # Convert m2 to sq ft
        m2 = float(match.group(1).replace(',', ''))
        return m2 * 10.764  # m2 to sq ft
    
    return None


def calculate_concrete_volume(length_m: float, width_m: float, depth_m: float) -> Dict[str, Any]:
    """Calculate concrete volume and cost."""
    volume_m3 = length_m * width_m * depth_m
    volume_yd3 = volume_m3 * 1.308  # Convert m3 to cubic yards
    
    cost_data = COST_DATA["concrete"]
    cost_low = volume_yd3 * cost_data["low"]
    cost_high = volume_yd3 * cost_data["high"]
    cost_national = volume_yd3 * cost_data["national"]
    
    return {
        "volume_m3": round(volume_m3, 2),
        "volume_yd3": round(volume_yd3, 2),
        "cost_low": round(cost_low, 2),
        "cost_high": round(cost_high, 2),
        "cost_estimate": round(cost_national, 2),
    }


def estimate_building_cost(area_sqft: float, building_type: str) -> Optional[Dict[str, Any]]:
    """Estimate building cost based on type and area."""
    building_type = building_type.lower()
    if building_type not in BUILDING_COSTS:
        return None
    
    costs = BUILDING_COSTS[building_type]
    low_total = area_sqft * costs["low"]
    high_total = area_sqft * costs["high"]
    national_total = area_sqft * costs["national"]
    
    return {
        "building_type": building_type,
        "area_sqft": round(area_sqft, 0),
        "cost_per_sqft_low": costs["low"],
        "cost_per_sqft_high": costs["high"],
        "total_cost_low": round(low_total, 0),
        "total_cost_high": round(high_total, 0),
        "total_cost_estimate": round(national_total, 0),
    }


def route_intent(message: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Route natural language message to appropriate handler.
    
    Returns:
        (response_text, metadata)
    """
    message_lower = message.lower()
    
    # 1. Concrete calculation
    if any(word in message_lower for word in ["concrete", "cement", "foundation", "slab"]):
        if any(word in message_lower for word in ["calculate", "volume", "how much", "cubic", "m3", "yd3"]):
            dims = parse_dimensions(message)
            if dims:
                result = calculate_concrete_volume(*dims)
                response = f"""🏗️ **Concrete Calculation**

**Dimensions:** {dims[0]}m × {dims[1]}m × {dims[2]}m

**Volume:**
• {result['volume_m3']} m³
• {result['volume_yd3']} yd³

**Estimated Cost (RSMeans 2024):**
• Low: ${result['cost_low']:,.2f}
• High: ${result['cost_high']:,.2f}
• **Typical: ${result['cost_estimate']:,.2f}**

_Note: Costs are for concrete material only. Labor, forms, and reinforcement additional._"""
                return response, {"intent": "concrete_calculation", "result": result}
    
    # 2. Building cost estimation
    if any(word in message_lower for word in ["estimate", "cost", "price", "budget"]):
        area = parse_area(message)
        
        # Detect building type
        building_type = None
        for btype in BUILDING_COSTS.keys():
            if btype in message_lower:
                building_type = btype
                break
        
        if area and building_type:
            result = estimate_building_cost(area, building_type)
            if result:
                response = f"""💰 **Building Cost Estimate**

**Project:** {area:,.0f} sq ft {building_type.title()}

**Cost per sq ft:**
• Low: ${result['cost_per_sqft_low']}/sq ft
• High: ${result['cost_per_sqft_high']}/sq ft

**Total Project Cost:**
• Low: ${result['total_cost_low']:,.0f}
• High: ${result['total_cost_high']:,.0f}
• **Typical: ${result['total_cost_estimate']:,.0f}**

_Note: Costs are construction only (not including land, soft costs, or FF&E). Location adjustments may apply._"""
                return response, {"intent": "building_estimate", "result": result}
    
    # 3. Material cost lookup
    for material, data in COST_DATA.items():
        if material.replace("_", " ") in message_lower or material in message_lower:
            if any(word in message_lower for word in ["cost", "price", "how much"]):
                response = f"""📊 **{material.replace('_', ' ').title()} Cost** (RSMeans 2024)

• Low: ${data['low']}/{data['unit']}
• High: ${data['high']}/{data['unit']}
• **National Average: ${data['national']}/{data['unit']}**

_Note: Prices are material costs only. Labor, equipment, and location factors additional._"""
                return response, {"intent": "material_cost", "material": material}
    
    # 4. Formulas
    if any(word in message_lower for word in ["formula", "equation", "calculation method"]):
        if "beam" in message_lower or "moment" in message_lower:
            response = """📐 **Beam Moment Formula**

**Simple Support, Uniform Load:**
M = wL²/8

Where:
• M = Maximum moment (lb-ft or N-m)
• w = Uniform load (lb/ft or N/m)
• L = Span length (ft or m)

**Cantilever, Uniform Load:**
M = wL²/2

**Simple Support, Point Load at Center:**
M = PL/4

Where P = Point load (lb or N)"""
            return response, {"intent": "formula", "topic": "beam_moment"}
        
        if "concrete" in message_lower or "volume" in message_lower:
            response = """📐 **Concrete Volume Formula**

**Volume = Length × Width × Depth**

Units:
• Metric: m × m × m = m³
• Imperial: ft × ft × ft = ft³

**Conversions:**
• 1 m³ = 1.308 yd³
• 1 yd³ = 27 ft³
• 1 m³ = 35.315 ft³

**Common Concrete Densities:**
• Normal weight: 2,400 kg/m³ (150 lb/ft³)
• Lightweight: 1,800 kg/m³ (112 lb/ft³)"""
            return response, {"intent": "formula", "topic": "concrete_volume"}
    
    # No match
    return None, None


def generate_intent_response(message: str) -> Optional[str]:
    """Generate a response if intent is recognized, otherwise return None."""
    response, _ = route_intent(message)
    return response
