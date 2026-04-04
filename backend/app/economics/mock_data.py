"""
Enhanced RSMeans Mock Data for Cerebrum
50+ construction items with CSI MasterFormat divisions
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal


# ============================================================================
# CSI MasterFormat Divisions Reference
# ============================================================================

CSI_DIVISIONS = {
    "03": {"name": "Concrete", "description": "Concrete and reinforcing"},
    "04": {"name": "Masonry", "description": "Masonry units and assemblies"},
    "05": {"name": "Metals", "description": "Structural and architectural metals"},
    "06": {"name": "Wood, Plastics, Composites", "description": "Wood and engineered materials"},
    "07": {"name": "Thermal and Moisture Protection", "description": "Insulation and roofing"},
    "08": {"name": "Openings", "description": "Doors, windows, and hardware"},
    "09": {"name": "Finishes", "description": "Interior finishes"},
    "10": {"name": "Specialties", "description": "Specialty products"},
    "11": {"name": "Equipment", "description": "Installed equipment"},
    "12": {"name": "Furnishings", "description": "Furniture and fixtures"},
    "13": {"name": "Special Construction", "description": "Special construction"},
    "14": {"name": "Conveying Equipment", "description": "Elevators and lifts"},
    "21": {"name": "Fire Suppression", "description": "Sprinklers and fire protection"},
    "22": {"name": "Plumbing", "description": "Plumbing systems"},
    "23": {"name": "Heating, Ventilation, Air Conditioning", "description": "HVAC systems"},
    "26": {"name": "Electrical", "description": "Electrical systems"},
    "31": {"name": "Earthwork", "description": "Excavation and fill"},
    "32": {"name": "Exterior Improvements", "description": "Paving and landscaping"},
    "33": {"name": "Utilities", "description": "Utility infrastructure"},
}


# ============================================================================
# Construction Cost Items by CSI Division
# ============================================================================

RSMEANS_MOCK_ITEMS: Dict[str, List[Dict[str, Any]]] = {
    # Division 03 - Concrete
    "03": [
        {"id": "033000-100", "description": "Ready-mix concrete, 3000 psi", "unit": "CY", "base_cost": 135.0, "category": "Concrete"},
        {"id": "033000-200", "description": "Ready-mix concrete, 4000 psi", "unit": "CY", "base_cost": 152.0, "category": "Concrete"},
        {"id": "032100-100", "description": "Reinforcing steel, Grade 60, #4 bars", "unit": "LB", "base_cost": 1.25, "category": "Reinforcing"},
        {"id": "032100-200", "description": "Reinforcing steel, Grade 60, #6 bars", "unit": "LB", "base_cost": 1.20, "category": "Reinforcing"},
        {"id": "033500-100", "description": "Concrete finishing, broom finish", "unit": "SF", "base_cost": 1.85, "category": "Finishing"},
        {"id": "033500-200", "description": "Concrete finishing, trowel finish", "unit": "SF", "base_cost": 2.45, "category": "Finishing"},
    ],
    
    # Division 04 - Masonry
    "04": [
        {"id": "042000-100", "description": "Concrete masonry units, 8\" standard", "unit": "EA", "base_cost": 3.25, "category": "Block"},
        {"id": "042200-100", "description": "Concrete masonry units, 8\" reinforced", "unit": "EA", "base_cost": 4.15, "category": "Block"},
        {"id": "042113-100", "description": "Brick veneer, standard modular", "unit": "SF", "base_cost": 18.50, "category": "Brick"},
    ],
    
    # Division 05 - Metals
    "05": [
        {"id": "051200-100", "description": "Structural steel, wide flange beams", "unit": "LB", "base_cost": 2.85, "category": "Structural Steel"},
        {"id": "053100-100", "description": "Steel decking, 20 gauge composite", "unit": "SF", "base_cost": 4.25, "category": "Decking"},
        {"id": "055000-100", "description": "Metal fabrications, miscellaneous", "unit": "LB", "base_cost": 3.50, "category": "Fabrication"},
    ],
    
    # Division 06 - Wood, Plastics, Composites
    "06": [
        {"id": "061100-100", "description": "Wood framing, 2x4 Douglas Fir", "unit": "LF", "base_cost": 2.15, "category": "Framing"},
        {"id": "061100-200", "description": "Wood framing, 2x6 Douglas Fir", "unit": "LF", "base_cost": 3.25, "category": "Framing"},
        {"id": "061753-100", "description": "Engineered wood, I-joists 11-7/8\"", "unit": "LF", "base_cost": 5.85, "category": "Engineered"},
        {"id": "064116-100", "description": "Cabinetry, base cabinets", "unit": "LF", "base_cost": 285.0, "category": "Cabinetry"},
    ],
    
    # Division 07 - Thermal and Moisture Protection
    "07": [
        {"id": "072100-100", "description": "Thermal insulation, batt R-19", "unit": "SF", "base_cost": 1.45, "category": "Insulation"},
        {"id": "072100-200", "description": "Thermal insulation, rigid board R-10", "unit": "SF", "base_cost": 2.85, "category": "Insulation"},
        {"id": "075100-100", "description": "Built-up roofing, 3-ply system", "unit": "SF", "base_cost": 8.50, "category": "Roofing"},
        {"id": "076200-100", "description": "Sheet metal flashing", "unit": "SF", "base_cost": 18.75, "category": "Flashing"},
    ],
    
    # Division 08 - Openings
    "08": [
        {"id": "081113-100", "description": "Hollow metal door, 3'0\" x 7'0\"", "unit": "EA", "base_cost": 485.0, "category": "Doors"},
        {"id": "081113-200", "description": "Hollow metal door frame, standard", "unit": "EA", "base_cost": 225.0, "category": "Frames"},
        {"id": "087100-100", "description": "Door hardware, standard lockset", "unit": "EA", "base_cost": 165.0, "category": "Hardware"},
        {"id": "087100-200", "description": "Door hardware, panic exit device", "unit": "EA", "base_cost": 385.0, "category": "Hardware"},
        {"id": "085113-100", "description": "Aluminum window, single hung 3' x 5'", "unit": "EA", "base_cost": 685.0, "category": "Windows"},
    ],
    
    # Division 09 - Finishes
    "09": [
        {"id": "092900-100", "description": "Gypsum wallboard, 1/2\" standard", "unit": "SF", "base_cost": 2.35, "category": "Drywall"},
        {"id": "093000-100", "description": "Ceramic tile, floor 12\" x 12\"", "unit": "SF", "base_cost": 12.50, "category": "Tile"},
        {"id": "096800-100", "description": "Carpet tile, modular 24\" x 24\"", "unit": "SF", "base_cost": 8.75, "category": "Flooring"},
        {"id": "096500-100", "description": "Resilient flooring, VCT 12\" x 12\"", "unit": "SF", "base_cost": 5.25, "category": "Flooring"},
        {"id": "099100-100", "description": "Interior paint, latex wall", "unit": "SF", "base_cost": 1.15, "category": "Paint"},
        {"id": "099100-200", "description": "Interior paint, latex ceiling", "unit": "SF", "base_cost": 0.95, "category": "Paint"},
    ],
    
    # Division 10 - Specialties
    "10": [
        {"id": "101100-100", "description": "Visual display board, marker type", "unit": "EA", "base_cost": 385.0, "category": "Specialties"},
        {"id": "102113-100", "description": "Toilet partitions, plastic laminate", "unit": "EA", "base_cost": 485.0, "category": "Specialties"},
    ],
    
    # Division 11 - Equipment
    "11": [
        {"id": "113100-100", "description": "Residential kitchen exhaust hood", "unit": "EA", "base_cost": 685.0, "category": "Equipment"},
        {"id": "114000-100", "description": "Residential appliances, package", "unit": "LS", "base_cost": 4250.0, "category": "Equipment"},
    ],
    
    # Division 12 - Furnishings
    "12": [
        {"id": "123600-100", "description": "Countertops, laminate", "unit": "SF", "base_cost": 42.50, "category": "Furnishings"},
    ],
    
    # Division 21 - Fire Suppression
    "21": [
        {"id": "211000-100", "description": "Fire sprinkler heads, pendant", "unit": "EA", "base_cost": 85.0, "category": "Fire Protection"},
        {"id": "211000-200", "description": "Fire sprinkler system piping", "unit": "LF", "base_cost": 12.50, "category": "Fire Protection"},
    ],
    
    # Division 22 - Plumbing
    "22": [
        {"id": "221100-100", "description": "Water closet, flush valve type", "unit": "EA", "base_cost": 485.0, "category": "Plumbing"},
        {"id": "224000-100", "description": "Domestic water heater, 50 gallon", "unit": "EA", "base_cost": 1250.0, "category": "Plumbing"},
    ],
    
    # Division 23 - HVAC
    "23": [
        {"id": "233600-100", "description": "Air handling unit, 2 ton split", "unit": "EA", "base_cost": 2850.0, "category": "HVAC"},
        {"id": "238100-100", "description": "Ductwork, galvanized steel", "unit": "LB", "base_cost": 4.85, "category": "HVAC"},
    ],
    
    # Division 26 - Electrical
    "26": [
        {"id": "262000-100", "description": "Panelboard, 200A 42-circuit", "unit": "EA", "base_cost": 1850.0, "category": "Electrical"},
        {"id": "262816-100", "description": "Receptacles, duplex 120V", "unit": "EA", "base_cost": 85.0, "category": "Electrical"},
    ],
}


# ============================================================================
# Infrastructure Mock Data (CSI Division 33 - Utilities)
# ============================================================================

INFRASTRUCTURE_ITEMS: Dict[str, List[Dict[str, Any]]] = {
    # Division 33 - Utilities - Manholes & Drainage Structures
    "33-manholes": [
        {"id": "330101-100", "description": "Precast concrete manhole, 4' dia x 8' deep", "unit": "EA", "base_cost": 3085.0, "category": "Manholes"},
        {"id": "330101-200", "description": "Precast concrete manhole, 5' dia x 10' deep", "unit": "EA", "base_cost": 4485.0, "category": "Manholes"},
        {"id": "330101-300", "description": "Precast concrete manhole, 6' dia x 12' deep", "unit": "EA", "base_cost": 5985.0, "category": "Manholes"},
        {"id": "330101-400", "description": "Drop manhole with connection", "unit": "EA", "base_cost": 7750.0, "category": "Manholes"},
        {"id": "330102-100", "description": "Catch basin 2' x 2' x 4'", "unit": "EA", "base_cost": 855.0, "category": "Catch Basins"},
        {"id": "330102-200", "description": "Catch basin 3' x 3' x 6'", "unit": "EA", "base_cost": 1425.0, "category": "Catch Basins"},
        {"id": "330103-100", "description": "Manhole cover, standard duty", "unit": "SET", "base_cost": 425.0, "category": "Accessories"},
        {"id": "330103-200", "description": "Manhole cover, heavy duty (H-20)", "unit": "SET", "base_cost": 605.0, "category": "Accessories"},
    ],
    
    # Division 33 - Sanitary Sewer Pipe
    "33-sanitary": [
        {"id": "331000-100", "description": "PVC sewer pipe SDR-35, 4\"", "unit": "LF", "base_cost": 12.50, "category": "Sanitary"},
        {"id": "331000-200", "description": "PVC sewer pipe SDR-35, 6\"", "unit": "LF", "base_cost": 18.75, "category": "Sanitary"},
        {"id": "331000-300", "description": "PVC sewer pipe SDR-35, 8\"", "unit": "LF", "base_cost": 28.50, "category": "Sanitary"},
        {"id": "331000-400", "description": "PVC sewer pipe SDR-35, 10\"", "unit": "LF", "base_cost": 42.00, "category": "Sanitary"},
        {"id": "331000-500", "description": "PVC sewer pipe SDR-35, 12\"", "unit": "LF", "base_cost": 58.50, "category": "Sanitary"},
        {"id": "331100-100", "description": "Ductile iron pipe CL 52, 8\"", "unit": "LF", "base_cost": 65.00, "category": "Sanitary"},
        {"id": "331100-200", "description": "Ductile iron pipe CL 52, 12\"", "unit": "LF", "base_cost": 115.00, "category": "Sanitary"},
        {"id": "331100-300", "description": "Ductile iron pipe CL 52, 15\"", "unit": "LF", "base_cost": 165.00, "category": "Sanitary"},
        {"id": "331200-100", "description": "Concrete pipe Class III, 15\"", "unit": "LF", "base_cost": 85.00, "category": "Sanitary"},
        {"id": "331200-200", "description": "Concrete pipe Class IV, 18\"", "unit": "LF", "base_cost": 125.00, "category": "Sanitary"},
        {"id": "331200-300", "description": "Concrete pipe Class IV, 24\"", "unit": "LF", "base_cost": 215.00, "category": "Sanitary"},
        {"id": "331300-100", "description": "Service lateral with connection", "unit": "EA", "base_cost": 1850.0, "category": "Sanitary"},
    ],
    
    # Division 33 - Storm Drainage Pipe
    "33-storm": [
        {"id": "332000-100", "description": "CMP pipe, 12\" gauge 16", "unit": "LF", "base_cost": 28.50, "category": "Storm"},
        {"id": "332000-200", "description": "CMP pipe, 18\" gauge 14", "unit": "LF", "base_cost": 48.50, "category": "Storm"},
        {"id": "332000-300", "description": "CMP pipe, 24\" gauge 12", "unit": "LF", "base_cost": 78.50, "category": "Storm"},
        {"id": "332000-400", "description": "CMP pipe, 36\" gauge 10", "unit": "LF", "base_cost": 165.00, "category": "Storm"},
        {"id": "332000-500", "description": "CMP pipe, 48\" gauge 8", "unit": "LF", "base_cost": 285.00, "category": "Storm"},
        {"id": "332100-100", "description": "RCP Class III, 12\"", "unit": "LF", "base_cost": 65.00, "category": "Storm"},
        {"id": "332100-200", "description": "RCP Class IV, 15\"", "unit": "LF", "base_cost": 95.00, "category": "Storm"},
        {"id": "332100-300", "description": "RCP Class IV, 18\"", "unit": "LF", "base_cost": 135.00, "category": "Storm"},
        {"id": "332100-400", "description": "RCP Class V, 24\"", "unit": "LF", "base_cost": 225.00, "category": "Storm"},
        {"id": "332100-500", "description": "RCP Class V, 30\"", "unit": "LF", "base_cost": 325.00, "category": "Storm"},
        {"id": "332100-600", "description": "RCP Class V, 36\"", "unit": "LF", "base_cost": 485.00, "category": "Storm"},
        {"id": "332100-700", "description": "RCP Class V, 48\"", "unit": "LF", "base_cost": 785.00, "category": "Storm"},
        {"id": "332100-800", "description": "RCP Class V, 60\"", "unit": "LF", "base_cost": 1250.00, "category": "Storm"},
        {"id": "332200-100", "description": "HDPE corrugated pipe, 12\"", "unit": "LF", "base_cost": 18.50, "category": "Storm"},
        {"id": "332200-200", "description": "HDPE corrugated pipe, 24\"", "unit": "LF", "base_cost": 58.50, "category": "Storm"},
        {"id": "332200-300", "description": "HDPE corrugated pipe, 36\"", "unit": "LF", "base_cost": 125.00, "category": "Storm"},
    ],
    
    # Division 33 - Potable Water
    "33-water": [
        {"id": "333100-100", "description": "PVC C900 pipe, 6\"", "unit": "LF", "base_cost": 28.50, "category": "Water"},
        {"id": "333100-200", "description": "PVC C900 pipe, 8\"", "unit": "LF", "base_cost": 45.00, "category": "Water"},
        {"id": "333100-300", "description": "PVC C900 pipe, 12\"", "unit": "LF", "base_cost": 95.00, "category": "Water"},
        {"id": "333200-100", "description": "Ductile iron pipe CL 350, 6\"", "unit": "LF", "base_cost": 58.50, "category": "Water"},
        {"id": "333200-200", "description": "Ductile iron pipe CL 350, 8\"", "unit": "LF", "base_cost": 88.50, "category": "Water"},
        {"id": "333200-300", "description": "Ductile iron pipe CL 350, 12\"", "unit": "LF", "base_cost": 185.00, "category": "Water"},
        {"id": "333300-100", "description": "Gate valve, 6\"", "unit": "EA", "base_cost": 1850.0, "category": "Water"},
        {"id": "333300-200", "description": "Gate valve, 8\"", "unit": "EA", "base_cost": 2850.0, "category": "Water"},
        {"id": "333300-300", "description": "Gate valve, 12\"", "unit": "EA", "base_cost": 5850.0, "category": "Water"},
        {"id": "333400-100", "description": "Fire hydrant, complete", "unit": "EA", "base_cost": 4850.0, "category": "Water"},
        {"id": "333500-100", "description": "Water meter, 5/8\" x 3/4\"", "unit": "EA", "base_cost": 485.0, "category": "Water"},
        {"id": "333500-200", "description": "Water meter, 1\"", "unit": "EA", "base_cost": 785.0, "category": "Water"},
        {"id": "333600-100", "description": "Water service line, copper 1\"", "unit": "LF", "base_cost": 35.50, "category": "Water"},
        {"id": "333600-200", "description": "Water service line, copper 2\"", "unit": "LF", "base_cost": 65.00, "category": "Water"},
    ],
    
    # Division 33 - Irrigation
    "33-irrigation": [
        {"id": "334100-100", "description": "PVC Schedule 40 pipe, 1\"", "unit": "LF", "base_cost": 4.50, "category": "Irrigation"},
        {"id": "334100-200", "description": "PVC Schedule 40 pipe, 2\"", "unit": "LF", "base_cost": 12.50, "category": "Irrigation"},
        {"id": "334200-100", "description": "Rotary sprinkler head, commercial", "unit": "EA", "base_cost": 65.00, "category": "Irrigation"},
        {"id": "334200-200", "description": "Spray head, fixed", "unit": "EA", "base_cost": 28.50, "category": "Irrigation"},
        {"id": "334300-100", "description": "Control valve, 1\" electric", "unit": "EA", "base_cost": 185.0, "category": "Irrigation"},
        {"id": "334400-100", "description": "Irrigation controller, 8-station", "unit": "EA", "base_cost": 485.0, "category": "Irrigation"},
        {"id": "334500-100", "description": "Drip emitter line, 1/2\"", "unit": "LF", "base_cost": 2.85, "category": "Irrigation"},
        {"id": "334600-100", "description": "Backflow preventer, 1\"", "unit": "EA", "base_cost": 685.0, "category": "Irrigation"},
        {"id": "334600-200", "description": "Backflow preventer, 2\"", "unit": "EA", "base_cost": 1250.0, "category": "Irrigation"},
        {"id": "334700-100", "description": "Quick coupling valve", "unit": "EA", "base_cost": 85.0, "category": "Irrigation"},
    ],
}


# ============================================================================
# Roadwork Items (CSI Division 32)
# ============================================================================

ROADWORK_ITEMS: List[Dict[str, Any]] = [
    {"id": "321100-100", "description": "Hot mix asphalt, 2\" thickness", "unit": "SY", "base_cost": 18.50, "category": "Paving"},
    {"id": "321100-200", "description": "Hot mix asphalt, 3\" thickness", "unit": "SY", "base_cost": 26.50, "category": "Paving"},
    {"id": "321100-300", "description": "Hot mix asphalt, 4\" thickness", "unit": "SY", "base_cost": 34.50, "category": "Paving"},
    {"id": "321200-100", "description": "Concrete paving, 6\" thickness", "unit": "SY", "base_cost": 58.50, "category": "Paving"},
    {"id": "321200-200", "description": "Concrete paving, 8\" thickness", "unit": "SY", "base_cost": 72.50, "category": "Paving"},
    {"id": "321300-100", "description": "Aggregate base course, 6\"", "unit": "SY", "base_cost": 12.50, "category": "Base"},
    {"id": "321300-200", "description": "Aggregate base course, 12\"", "unit": "SY", "base_cost": 22.50, "category": "Base"},
    {"id": "321400-100", "description": "Curb & gutter, integral concrete", "unit": "LF", "base_cost": 28.50, "category": "Curbs"},
    {"id": "321400-200", "description": "Curb & gutter, barrier type", "unit": "LF", "base_cost": 35.50, "category": "Curbs"},
    {"id": "321600-100", "description": "Concrete sidewalk, 4\" thick", "unit": "SF", "base_cost": 8.50, "category": "Walks"},
    {"id": "321600-200", "description": "Concrete sidewalk, 6\" thick", "unit": "SF", "base_cost": 12.50, "category": "Walks"},
    {"id": "321800-100", "description": "Pavement marking, thermoplastic", "unit": "LF", "base_cost": 4.50, "category": "Marking"},
    {"id": "321800-200", "description": "Pavement marking, paint", "unit": "LF", "base_cost": 1.85, "category": "Marking"},
    {"id": "321900-100", "description": "Parking bumpers, precast concrete", "unit": "EA", "base_cost": 125.0, "category": "Parking"},
]


# ============================================================================
# Site Work Items (CSI Division 31)
# ============================================================================

SITEWORK_ITEMS: List[Dict[str, Any]] = [
    {"id": "311000-100", "description": "Site clearing, light vegetation", "unit": "AC", "base_cost": 2850.0, "category": "Site Clearing"},
    {"id": "311000-200", "description": "Site clearing, heavy vegetation", "unit": "AC", "base_cost": 4850.0, "category": "Site Clearing"},
    {"id": "312300-100", "description": "Excavation, bulk common", "unit": "CY", "base_cost": 12.50, "category": "Excavation"},
    {"id": "312300-200", "description": "Excavation, trench common", "unit": "CY", "base_cost": 18.50, "category": "Excavation"},
    {"id": "312300-300", "description": "Excavation, rock (blasting)", "unit": "CY", "base_cost": 85.00, "category": "Excavation"},
    {"id": "312316-100", "description": "Backfill, compacted", "unit": "CY", "base_cost": 18.50, "category": "Earthwork"},
    {"id": "312500-100", "description": "Riprap, dumped", "unit": "CY", "base_cost": 125.00, "category": "Erosion Control"},
    {"id": "312500-200", "description": "Riprap, hand placed", "unit": "CY", "base_cost": 185.00, "category": "Erosion Control"},
    {"id": "312600-100", "description": "Geotextile fabric", "unit": "SY", "base_cost": 4.50, "category": "Erosion Control"},
    {"id": "312700-100", "description": "Silt fence", "unit": "LF", "base_cost": 8.50, "category": "Erosion Control"},
]


# ============================================================================
# City Cost Indices
# ============================================================================

CITY_COST_INDICES: Dict[str, Dict[str, float]] = {
    # United States
    "New York, NY": {"index": 1.42, "region": "Northeast"},
    "San Francisco, CA": {"index": 1.55, "region": "West"},
    "Los Angeles, CA": {"index": 1.38, "region": "West"},
    "Chicago, IL": {"index": 1.25, "region": "Midwest"},
    "Houston, TX": {"index": 0.95, "region": "South"},
    "Dallas, TX": {"index": 0.98, "region": "South"},
    "Atlanta, GA": {"index": 0.92, "region": "South"},
    "Seattle, WA": {"index": 1.28, "region": "West"},
    "Boston, MA": {"index": 1.35, "region": "Northeast"},
    "Denver, CO": {"index": 1.05, "region": "West"},
    "Phoenix, AZ": {"index": 0.88, "region": "West"},
    "Philadelphia, PA": {"index": 1.18, "region": "Northeast"},
    "Miami, FL": {"index": 0.98, "region": "South"},
    "Washington, DC": {"index": 1.15, "region": "Northeast"},
    "Austin, TX": {"index": 0.92, "region": "South"},
    "San Diego, CA": {"index": 1.32, "region": "West"},
    "Portland, OR": {"index": 1.12, "region": "West"},
    "Minneapolis, MN": {"index": 1.08, "region": "Midwest"},
    "Detroit, MI": {"index": 1.02, "region": "Midwest"},
    "Tampa, FL": {"index": 0.88, "region": "South"},
    "Las Vegas, NV": {"index": 0.95, "region": "West"},
    "Nashville, TN": {"index": 0.88, "region": "South"},
    "Charlotte, NC": {"index": 0.90, "region": "South"},
    "Columbus, OH": {"index": 0.95, "region": "Midwest"},
    "Kansas City, MO": {"index": 0.92, "region": "Midwest"},
    "Indianapolis, IN": {"index": 0.90, "region": "Midwest"},
    "Salt Lake City, UT": {"index": 1.02, "region": "West"},
    "National Average": {"index": 1.00, "region": "National"},
    
    # Middle East
    "Riyadh, Saudi Arabia": {"index": 0.88, "region": "Middle East"},
    "Jeddah, Saudi Arabia": {"index": 0.85, "region": "Middle East"},
    "Dubai, UAE": {"index": 0.92, "region": "Middle East"},
    "Abu Dhabi, UAE": {"index": 0.95, "region": "Middle East"},
    "Doha, Qatar": {"index": 1.05, "region": "Middle East"},
    "Kuwait City, Kuwait": {"index": 0.98, "region": "Middle East"},
    
    # Europe
    "London, UK": {"index": 1.48, "region": "Europe"},
    "Paris, France": {"index": 1.35, "region": "Europe"},
    "Berlin, Germany": {"index": 1.22, "region": "Europe"},
    "Amsterdam, Netherlands": {"index": 1.38, "region": "Europe"},
}


# ============================================================================
# Building Types for Quick Estimates
# ============================================================================

BUILDING_TYPES: Dict[str, Dict[str, Any]] = {
    "residential-single": {
        "name": "Single Family Residential",
        "cost_per_sf": 185.0,
        "description": "Single family detached home",
        "typical_size_sf": 2500,
    },
    "residential-multi": {
        "name": "Multi-Family Residential",
        "cost_per_sf": 165.0,
        "description": "Apartments or condominiums",
        "typical_size_sf": 85000,
    },
    "office-low": {
        "name": "Office Building (Low Rise)",
        "cost_per_sf": 225.0,
        "description": "1-4 story office building",
        "typical_size_sf": 75000,
    },
    "office-high": {
        "name": "Office Building (High Rise)",
        "cost_per_sf": 285.0,
        "description": "5+ story office building",
        "typical_size_sf": 250000,
    },
    "retail-strip": {
        "name": "Retail (Strip Mall)",
        "cost_per_sf": 145.0,
        "description": "Single story retail strip",
        "typical_size_sf": 25000,
    },
    "retail-enclosed": {
        "name": "Retail (Enclosed Mall)",
        "cost_per_sf": 185.0,
        "description": "Enclosed shopping mall",
        "typical_size_sf": 350000,
    },
    "warehouse": {
        "name": "Warehouse/Distribution",
        "cost_per_sf": 95.0,
        "description": "Industrial warehouse",
        "typical_size_sf": 150000,
    },
    "manufacturing": {
        "name": "Manufacturing Plant",
        "cost_per_sf": 145.0,
        "description": "Light manufacturing facility",
        "typical_size_sf": 100000,
    },
    "school-elementary": {
        "name": "Elementary School",
        "cost_per_sf": 245.0,
        "description": "K-5 school building",
        "typical_size_sf": 65000,
    },
    "school-high": {
        "name": "High School",
        "cost_per_sf": 265.0,
        "description": "9-12 school building",
        "typical_size_sf": 185000,
    },
    "hospital": {
        "name": "Hospital",
        "cost_per_sf": 585.0,
        "description": "General acute care hospital",
        "typical_size_sf": 250000,
    },
    "medical-office": {
        "name": "Medical Office",
        "cost_per_sf": 285.0,
        "description": "Outpatient medical facility",
        "typical_size_sf": 35000,
    },
    "hotel-mid": {
        "name": "Hotel (Midscale)",
        "cost_per_sf": 195.0,
        "description": "3-star hotel",
        "typical_size_sf": 85000,
    },
    "hotel-luxury": {
        "name": "Hotel (Luxury)",
        "cost_per_sf": 385.0,
        "description": "4-5 star hotel",
        "typical_size_sf": 350000,
    },
    "parking-structure": {
        "name": "Parking Structure",
        "cost_per_sf": 65.0,
        "description": "Multi-level parking garage",
        "typical_size_sf": 125000,
    },
}


# ============================================================================
# Construction Formulas (20+ calculations)
# ============================================================================

CONSTRUCTION_FORMULAS: Dict[str, Dict[str, Any]] = {
    # Concrete Formulas
    "concrete_volume_rect": {
        "name": "Concrete Volume (Rectangular)",
        "category": "Concrete",
        "formula": "length * width * depth / 27",  # CY
        "inputs": ["length", "width", "depth"],
        "unit": "CY",
        "description": "Calculate concrete volume for rectangular slab/pour",
    },
    "concrete_volume_cyl": {
        "name": "Concrete Volume (Cylindrical)",
        "category": "Concrete",
        "formula": "pi * (diameter/2)^2 * depth / 27",
        "inputs": ["diameter", "depth"],
        "unit": "CY",
        "description": "Calculate concrete volume for cylindrical columns/caissons",
    },
    "rebar_weight": {
        "name": "Rebar Weight",
        "category": "Concrete",
        "formula": "length * weight_per_foot",
        "inputs": ["length", "weight_per_foot"],
        "unit": "LB",
        "description": "Calculate rebar weight for given length",
    },
    
    # Structural Formulas
    "beam_moment_uniform": {
        "name": "Beam Moment (Uniform Load)",
        "category": "Structural",
        "formula": "(w * l^2) / 8",
        "inputs": ["w", "l"],
        "unit": "ft-lb",
        "description": "Maximum moment for simply supported beam with uniform load",
    },
    "beam_moment_point": {
        "name": "Beam Moment (Point Load)",
        "category": "Structural",
        "formula": "(p * l) / 4",
        "inputs": ["p", "l"],
        "unit": "ft-lb",
        "description": "Maximum moment for simply supported beam with center point load",
    },
    "beam_deflection": {
        "name": "Beam Deflection",
        "category": "Structural",
        "formula": "(5 * w * l^4) / (384 * e * i)",
        "inputs": ["w", "l", "e", "i"],
        "unit": "in",
        "description": "Maximum deflection for uniformly loaded beam",
    },
    "column_capacity": {
        "name": "Column Capacity",
        "category": "Structural",
        "formula": "fc * area",
        "inputs": ["fc", "area"],
        "unit": "LB",
        "description": "Axial load capacity of concrete column",
    },
    "safety_factor": {
        "name": "Safety Factor",
        "category": "Structural",
        "formula": "ultimate_strength / working_load",
        "inputs": ["ultimate_strength", "working_load"],
        "unit": "ratio",
        "description": "Calculate structural safety factor",
    },
    
    # Cost Estimation
    "unit_cost_calc": {
        "name": "Unit Cost Calculation",
        "category": "Cost",
        "formula": "material_cost + labor_cost + equipment_cost",
        "inputs": ["material_cost", "labor_cost", "equipment_cost"],
        "unit": "$/unit",
        "description": "Total unit cost from components",
    },
    "markup_calc": {
        "name": "Markup (Overhead + Profit)",
        "category": "Cost",
        "formula": "direct_cost * (1 + overhead_pct + profit_pct)",
        "inputs": ["direct_cost", "overhead_pct", "profit_pct"],
        "unit": "$",
        "description": "Apply overhead and profit markup to direct costs",
    },
    
    # Financial
    "roi_calc": {
        "name": "Return on Investment (ROI)",
        "category": "Financial",
        "formula": "(gain - cost) / cost * 100",
        "inputs": ["gain", "cost"],
        "unit": "%",
        "description": "Calculate ROI percentage",
    },
    "npv_calc": {
        "name": "Net Present Value",
        "category": "Financial",
        "formula": "sum(cash_flow / (1 + rate)^period)",
        "inputs": ["cash_flows", "discount_rate"],
        "unit": "$",
        "description": "Calculate NPV for cash flow series",
    },
    
    # Construction
    "wall_framing": {
        "name": "Wall Framing (Studs)",
        "category": "Construction",
        "formula": "(length / spacing) + 1",
        "inputs": ["length", "spacing"],
        "unit": "EA",
        "description": "Calculate number of studs for wall",
    },
    "paint_coverage": {
        "name": "Paint Coverage",
        "category": "Construction",
        "formula": "area / coverage_per_gallon",
        "inputs": ["area", "coverage_per_gallon"],
        "unit": "gallons",
        "description": "Calculate paint quantity needed",
    },
    "excavation_volume": {
        "name": "Excavation Volume",
        "category": "Construction",
        "formula": "length * width * depth",
        "inputs": ["length", "width", "depth"],
        "unit": "CY",
        "description": "Calculate excavation volume",
    },
    "roofing_area": {
        "name": "Roofing Area (Gable)",
        "category": "Construction",
        "formula": "2 * (length/2) * sqrt((width/2)^2 + height^2)",
        "inputs": ["length", "width", "height"],
        "unit": "SF",
        "description": "Calculate gable roof surface area",
    },
    
    # Infrastructure Formulas (NEW)
    "manhole_volume": {
        "name": "Manhole Concrete Volume",
        "category": "Infrastructure",
        "formula": "pi * r^2 * depth",
        "inputs": ["diameter", "depth"],
        "unit": "CF",
        "description": "Calculate concrete volume for precast manhole",
    },
    "pipe_trench_volume": {
        "name": "Pipe Trench Excavation",
        "category": "Infrastructure",
        "formula": "(width + 2*depth*slope) * depth * length",
        "inputs": ["width", "depth", "length", "slope"],
        "unit": "CY",
        "description": "Calculate trench excavation volume with slopes",
    },
    "pipe_friction_loss": {
        "name": "Pipe Friction Loss (Hazen-Williams)",
        "category": "Infrastructure",
        "formula": "10.67 * l * (q/c)^1.852 / d^4.87",
        "inputs": ["length", "flow", "diameter", "c_factor"],
        "unit": "ft",
        "description": "Calculate head loss in pipe using Hazen-Williams",
    },
    "storm_runoff_rational": {
        "name": "Storm Runoff (Rational Method)",
        "category": "Infrastructure",
        "formula": "c * i * a",
        "inputs": ["runoff_coeff", "intensity", "area"],
        "unit": "cfs",
        "description": "Peak runoff using Rational Method",
    },
    "manning_equation": {
        "name": "Manning Equation (Open Channel)",
        "category": "Infrastructure",
        "formula": "(1.486/n) * area * r^0.67 * s^0.5",
        "inputs": ["n", "area", "hydraulic_radius", "slope"],
        "unit": "cfs",
        "description": "Calculate open channel flow capacity",
    },
    "circular_pipe_capacity": {
        "name": "Circular Pipe Capacity",
        "category": "Infrastructure",
        "formula": "(1.486/n) * (pi*d^2/4) * (d/4)^0.67 * s^0.5",
        "inputs": ["n", "diameter", "slope"],
        "unit": "cfs",
        "description": "Full-flow pipe capacity using Manning",
    },
    "asphalt_tonnage": {
        "name": "Asphalt Tonnage",
        "category": "Infrastructure",
        "formula": "area * thickness * density / 2000",
        "inputs": ["area", "thickness", "density"],
        "unit": "tons",
        "description": "Calculate hot mix asphalt tonnage needed",
    },
    "road_base_course": {
        "name": "Road Base Course Volume",
        "category": "Infrastructure",
        "formula": "area * thickness / 12 / 27",
        "inputs": ["area", "thickness"],
        "unit": "CY",
        "description": "Calculate aggregate base course volume",
    },
    "detention_volume": {
        "name": "Detention Pond Volume",
        "category": "Infrastructure",
        "formula": "runoff_volume - allowable_discharge * duration",
        "inputs": ["runoff_volume", "allowable_discharge", "duration"],
        "unit": "CF",
        "description": "Stormwater detention pond sizing",
    },
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_all_items() -> List[Dict[str, Any]]:
    """Get all construction items from all categories."""
    all_items = []
    
    # Add division items
    for division, items in RSMEANS_MOCK_ITEMS.items():
        for item in items:
            item_copy = item.copy()
            item_copy["division"] = division
            item_copy["division_name"] = CSI_DIVISIONS.get(division, {}).get("name", "Unknown")
            all_items.append(item_copy)
    
    # Add infrastructure items
    for category, items in INFRASTRUCTURE_ITEMS.items():
        for item in items:
            item_copy = item.copy()
            item_copy["category"] = "Infrastructure"
            item_copy["subcategory"] = category
            all_items.append(item_copy)
    
    # Add roadwork items
    for item in ROADWORK_ITEMS:
        item_copy = item.copy()
        item_copy["category"] = "Roadwork"
        all_items.append(item_copy)
    
    # Add sitework items
    for item in SITEWORK_ITEMS:
        item_copy = item.copy()
        item_copy["category"] = "Sitework"
        all_items.append(item_copy)
    
    return all_items


def get_items_by_division(division: str) -> List[Dict[str, Any]]:
    """Get items by CSI division code."""
    return RSMEANS_MOCK_ITEMS.get(division, [])


def get_item_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific item by ID."""
    for division, items in RSMEANS_MOCK_ITEMS.items():
        for item in items:
            if item["id"] == item_id:
                result = item.copy()
                result["division"] = division
                return result
    return None


def apply_location_factor(cost: float, city: str) -> float:
    """Apply city cost index to base cost."""
    city_data = CITY_COST_INDICES.get(city)
    if city_data:
        return cost * city_data["index"]
    return cost


def estimate_building_cost(building_type: str, size_sf: float, city: str = "National Average") -> Dict[str, Any]:
    """Quick building cost estimate."""
    type_data = BUILDING_TYPES.get(building_type)
    if not type_data:
        return {"error": f"Unknown building type: {building_type}"}
    
    base_cost = type_data["cost_per_sf"] * size_sf
    location_factor = CITY_COST_INDICES.get(city, {}).get("index", 1.0)
    adjusted_cost = base_cost * location_factor
    
    return {
        "building_type": type_data["name"],
        "size_sf": size_sf,
        "city": city,
        "base_cost_per_sf": type_data["cost_per_sf"],
        "location_factor": location_factor,
        "total_cost": round(adjusted_cost, 2),
        "description": type_data["description"],
    }


# Export all data for easy importing
__all__ = [
    "CSI_DIVISIONS",
    "RSMEANS_MOCK_ITEMS",
    "INFRASTRUCTURE_ITEMS",
    "ROADWORK_ITEMS",
    "SITEWORK_ITEMS",
    "CITY_COST_INDICES",
    "BUILDING_TYPES",
    "CONSTRUCTION_FORMULAS",
    "get_all_items",
    "get_items_by_division",
    "get_item_by_id",
    "apply_location_factor",
    "estimate_building_cost",
]
