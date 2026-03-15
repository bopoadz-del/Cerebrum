# Enhanced RSMeans Mock Data for Cerebrum
# Comprehensive construction cost database (demo values)

MOCK_RSMEANS_DATA = {
    # ============================================
    # CONCRETE WORK (Division 03)
    # ============================================
    "031011-010": {
        "rsmeans_id": "031011-010",
        "description": "Concrete, 3000 psi, ready mix (includes delivery)",
        "unit": "CY",
        "material_cost": 125.50,
        "labor_cost": 45.00,
        "equipment_cost": 15.00,
        "total_cost": 185.50,
        "category": "Concrete",
        "csi_division": "03",
        "location_factors": {"urban": 1.15, "suburban": 1.0, "rural": 0.95}
    },
    "031011-020": {
        "rsmeans_id": "031011-020",
        "description": "Concrete, 4000 psi, ready mix (high strength)",
        "unit": "CY",
        "material_cost": 145.00,
        "labor_cost": 48.00,
        "equipment_cost": 16.00,
        "total_cost": 209.00,
        "category": "Concrete",
        "csi_division": "03"
    },
    "032111-100": {
        "rsmeans_id": "032111-100",
        "description": "Reinforcing steel, grade 60, #4 bar (1/2\")",
        "unit": "LB",
        "material_cost": 1.15,
        "labor_cost": 0.85,
        "equipment_cost": 0.10,
        "total_cost": 2.10,
        "category": "Rebar",
        "csi_division": "03"
    },
    "032111-200": {
        "rsmeans_id": "032111-200",
        "description": "Reinforcing steel, grade 60, #6 bar (3/4\")",
        "unit": "LB",
        "material_cost": 1.10,
        "labor_cost": 0.80,
        "equipment_cost": 0.10,
        "total_cost": 2.00,
        "category": "Rebar",
        "csi_division": "03"
    },
    "033053-100": {
        "rsmeans_id": "033053-100",
        "description": "Concrete finishing, broom finish",
        "unit": "SF",
        "material_cost": 0.25,
        "labor_cost": 1.85,
        "equipment_cost": 0.40,
        "total_cost": 2.50,
        "category": "Concrete Finishing",
        "csi_division": "03"
    },
    "033053-200": {
        "rsmeans_id": "033053-200",
        "description": "Concrete finishing, steel trowel finish",
        "unit": "SF",
        "material_cost": 0.30,
        "labor_cost": 2.15,
        "equipment_cost": 0.45,
        "total_cost": 2.90,
        "category": "Concrete Finishing",
        "csi_division": "03"
    },
    
    # ============================================
    # MASONRY (Division 04)
    # ============================================
    "042200-100": {
        "rsmeans_id": "042200-100",
        "description": "Concrete block, 8\" standard, lightweight",
        "unit": "SF",
        "material_cost": 4.25,
        "labor_cost": 8.50,
        "equipment_cost": 0.75,
        "total_cost": 13.50,
        "category": "Masonry",
        "csi_division": "04"
    },
    "042200-200": {
        "rsmeans_id": "042200-200",
        "description": "Concrete block, 8\" reinforced, grouted",
        "unit": "SF",
        "material_cost": 6.50,
        "labor_cost": 11.00,
        "equipment_cost": 1.00,
        "total_cost": 18.50,
        "category": "Masonry",
        "csi_division": "04"
    },
    "048100-100": {
        "rsmeans_id": "048100-100",
        "description": "Brick veneer, modular, running bond",
        "unit": "SF",
        "material_cost": 8.50,
        "labor_cost": 18.00,
        "equipment_cost": 1.50,
        "total_cost": 28.00,
        "category": "Masonry",
        "csi_division": "04"
    },
    
    # ============================================
    # METALS (Division 05)
    # ============================================
    "051200-100": {
        "rsmeans_id": "051200-100",
        "description": "Structural steel, wide flange beams, shop fabricated",
        "unit": "LB",
        "material_cost": 1.65,
        "labor_cost": 1.25,
        "equipment_cost": 0.35,
        "total_cost": 3.25,
        "category": "Structural Steel",
        "csi_division": "05"
    },
    "051200-200": {
        "rsmeans_id": "051200-200",
        "description": "Structural steel, columns, shop fabricated",
        "unit": "LB",
        "material_cost": 1.75,
        "labor_cost": 1.35,
        "equipment_cost": 0.40,
        "total_cost": 3.50,
        "category": "Structural Steel",
        "csi_division": "05"
    },
    "055100-100": {
        "rsmeans_id": "055100-100",
        "description": "Metal decking, 20 gauge, galvanized",
        "unit": "SF",
        "material_cost": 3.25,
        "labor_cost": 2.75,
        "equipment_cost": 0.50,
        "total_cost": 6.50,
        "category": "Metal Decking",
        "csi_division": "05"
    },
    
    # ============================================
    # WOOD & PLASTICS (Division 06)
    # ============================================
    "061000-100": {
        "rsmeans_id": "061000-100",
        "description": "Rough carpentry, framing lumber, 2x4 studs",
        "unit": "BF",
        "material_cost": 0.85,
        "labor_cost": 0.65,
        "equipment_cost": 0.10,
        "total_cost": 1.60,
        "category": "Rough Carpentry",
        "csi_division": "06"
    },
    "061000-200": {
        "rsmeans_id": "061000-200",
        "description": "Rough carpentry, framing lumber, 2x6 studs",
        "unit": "BF",
        "material_cost": 0.90,
        "labor_cost": 0.70,
        "equipment_cost": 0.10,
        "total_cost": 1.70,
        "category": "Rough Carpentry",
        "csi_division": "06"
    },
    "061753-100": {
        "rsmeans_id": "061753-100",
        "description": "Engineered wood, I-joists, 11-7/8\" depth",
        "unit": "LF",
        "material_cost": 4.85,
        "labor_cost": 2.15,
        "equipment_cost": 0.50,
        "total_cost": 7.50,
        "category": "Engineered Wood",
        "csi_division": "06"
    },
    "064100-100": {
        "rsmeans_id": "064100-100",
        "description": "Architectural woodwork, custom cabinets",
        "unit": "SF",
        "material_cost": 85.00,
        "labor_cost": 65.00,
        "equipment_cost": 5.00,
        "total_cost": 155.00,
        "category": "Finish Carpentry",
        "csi_division": "06"
    },
    
    # ============================================
    # THERMAL & MOISTURE (Division 07)
    # ============================================
    "072100-100": {
        "rsmeans_id": "072100-100",
        "description": "Thermal insulation, batt, R-13 walls",
        "unit": "SF",
        "material_cost": 0.85,
        "labor_cost": 1.15,
        "equipment_cost": 0.10,
        "total_cost": 2.10,
        "category": "Insulation",
        "csi_division": "07"
    },
    "072100-200": {
        "rsmeans_id": "072100-200",
        "description": "Thermal insulation, batt, R-30 ceilings",
        "unit": "SF",
        "material_cost": 1.25,
        "labor_cost": 1.50,
        "equipment_cost": 0.15,
        "total_cost": 2.90,
        "category": "Insulation",
        "csi_division": "07"
    },
    "075300-100": {
        "rsmeans_id": "075300-100",
        "description": "Roofing, TPO membrane, 60 mil, mechanically attached",
        "unit": "SF",
        "material_cost": 3.25,
        "labor_cost": 2.50,
        "equipment_cost": 0.75,
        "total_cost": 6.50,
        "category": "Roofing",
        "csi_division": "07"
    },
    "076200-100": {
        "rsmeans_id": "076200-100",
        "description": "Sheet metal flashing, galvanized steel, 26 gauge",
        "unit": "SF",
        "material_cost": 8.50,
        "labor_cost": 12.00,
        "equipment_cost": 1.50,
        "total_cost": 22.00,
        "category": "Flashing",
        "csi_division": "07"
    },
    
    # ============================================
    # DOORS & WINDOWS (Division 08)
    # ============================================
    "081113-100": {
        "rsmeans_id": "081113-100",
        "description": "Steel door, hollow metal, 3'0\" x 7'0\", standard duty",
        "unit": "EA",
        "material_cost": 285.00,
        "labor_cost": 125.00,
        "equipment_cost": 15.00,
        "total_cost": 425.00,
        "category": "Doors",
        "csi_division": "08"
    },
    "081113-200": {
        "rsmeans_id": "081113-200",
        "description": "Steel door, hollow metal, 3'0\" x 7'0\", heavy duty",
        "unit": "EA",
        "material_cost": 385.00,
        "labor_cost": 145.00,
        "equipment_cost": 20.00,
        "total_cost": 550.00,
        "category": "Doors",
        "csi_division": "08"
    },
    "087111-100": {
        "rsmeans_id": "087111-100",
        "description": "Door hardware, standard office set (lock, closer, stops)",
        "unit": "SET",
        "material_cost": 185.00,
        "labor_cost": 95.00,
        "equipment_cost": 5.00,
        "total_cost": 285.00,
        "category": "Door Hardware",
        "csi_division": "08"
    },
    "085000-100": {
        "rsmeans_id": "085000-100",
        "description": "Aluminum window, fixed, 4' x 5', double pane",
        "unit": "EA",
        "material_cost": 425.00,
        "labor_cost": 185.00,
        "equipment_cost": 25.00,
        "total_cost": 635.00,
        "category": "Windows",
        "csi_division": "08"
    },
    "085000-200": {
        "rsmeans_id": "085000-200",
        "description": "Aluminum window, operable, 4' x 5', double pane",
        "unit": "EA",
        "material_cost": 575.00,
        "labor_cost": 225.00,
        "equipment_cost": 30.00,
        "total_cost": 830.00,
        "category": "Windows",
        "csi_division": "08"
    },
    
    # ============================================
    # FINISHES (Division 09)
    # ============================================
    "092216-100": {
        "rsmeans_id": "092216-100",
        "description": "Drywall, 5/8\" gypsum board, Type X (fire rated)",
        "unit": "SF",
        "material_cost": 0.65,
        "labor_cost": 1.20,
        "equipment_cost": 0.10,
        "total_cost": 1.95,
        "category": "Drywall",
        "csi_division": "09"
    },
    "092216-200": {
        "rsmeans_id": "092216-200",
        "description": "Drywall, 1/2\" gypsum board, standard",
        "unit": "SF",
        "material_cost": 0.45,
        "labor_cost": 1.00,
        "equipment_cost": 0.08,
        "total_cost": 1.53,
        "category": "Drywall",
        "csi_division": "09"
    },
    "093000-100": {
        "rsmeans_id": "093000-100",
        "description": "Ceramic tile, wall, 6\" x 6\", standard grade",
        "unit": "SF",
        "material_cost": 4.50,
        "labor_cost": 12.00,
        "equipment_cost": 0.75,
        "total_cost": 17.25,
        "category": "Tile",
        "csi_division": "09"
    },
    "096800-100": {
        "rsmeans_id": "096800-100",
        "description": "Carpet, broadloom, commercial grade, 26 oz",
        "unit": "SY",
        "material_cost": 28.50,
        "labor_cost": 8.50,
        "equipment_cost": 1.50,
        "total_cost": 38.50,
        "category": "Flooring",
        "csi_division": "09"
    },
    "096800-200": {
        "rsmeans_id": "096800-200",
        "description": "VCT tile, 12\" x 12\", standard grade",
        "unit": "SF",
        "material_cost": 2.25,
        "labor_cost": 4.50,
        "equipment_cost": 0.50,
        "total_cost": 7.25,
        "category": "Flooring",
        "csi_division": "09"
    },
    "099100-100": {
        "rsmeans_id": "099100-100",
        "description": "Painting, interior, latex, 2 coats, walls",
        "unit": "SF",
        "material_cost": 0.35,
        "labor_cost": 0.85,
        "equipment_cost": 0.10,
        "total_cost": 1.30,
        "category": "Painting",
        "csi_division": "09"
    },
    "099100-200": {
        "rsmeans_id": "099100-200",
        "description": "Painting, exterior, latex, 2 coats",
        "unit": "SF",
        "material_cost": 0.45,
        "labor_cost": 1.25,
        "equipment_cost": 0.15,
        "total_cost": 1.85,
        "category": "Painting",
        "csi_division": "09"
    },
    
    # ============================================
    # SPECIALTIES (Division 10)
    # ============================================
    "101400-100": {
        "rsmeans_id": "101400-100",
        "description": "Signage, ADA compliant, room identification",
        "unit": "EA",
        "material_cost": 45.00,
        "labor_cost": 35.00,
        "equipment_cost": 2.50,
        "total_cost": 82.50,
        "category": "Signage",
        "csi_division": "10"
    },
    "108100-100": {
        "rsmeans_id": "108100-100",
        "description": "Toilet accessories, complete set (paper, soap, mirror)",
        "unit": "SET",
        "material_cost": 185.00,
        "labor_cost": 125.00,
        "equipment_cost": 5.00,
        "total_cost": 315.00,
        "category": "Accessories",
        "csi_division": "10"
    },
    
    # ============================================
    # EQUIPMENT (Division 11)
    # ============================================
    "113100-100": {
        "rsmeans_id": "113100-100",
        "description": "Residential kitchen cabinets, base, per linear foot",
        "unit": "LF",
        "material_cost": 125.00,
        "labor_cost": 65.00,
        "equipment_cost": 5.00,
        "total_cost": 195.00,
        "category": "Cabinetry",
        "csi_division": "11"
    },
    
    # ============================================
    # FURNISHINGS (Division 12)
    # ============================================
    "124800-100": {
        "rsmeans_id": "124800-100",
        "description": "Window blinds, horizontal, 2\", vinyl",
        "unit": "EA",
        "material_cost": 85.00,
        "labor_cost": 45.00,
        "equipment_cost": 2.50,
        "total_cost": 132.50,
        "category": "Window Treatments",
        "csi_division": "12"
    },
    
    # ============================================
    # SPECIAL CONSTRUCTION (Division 13)
    # ============================================
    "131100-100": {
        "rsmeans_id": "131100-100",
        "description": "Swimming pool, concrete, 20' x 40', basic",
        "unit": "EA",
        "material_cost": 45000.00,
        "labor_cost": 28500.00,
        "equipment_cost": 8500.00,
        "total_cost": 82000.00,
        "category": "Special Construction",
        "csi_division": "13"
    },
    
    # ============================================
    # CONVEYING SYSTEMS (Division 14)
    # ============================================
    "142100-100": {
        "rsmeans_id": "142100-100",
        "description": "Elevator, passenger, 2500 lb, 3-stop",
        "unit": "EA",
        "material_cost": 85000.00,
        "labor_cost": 25000.00,
        "equipment_cost": 8500.00,
        "total_cost": 118500.00,
        "category": "Elevators",
        "csi_division": "14"
    },
    
    # ============================================
    # FIRE SUPPRESSION (Division 21)
    # ============================================
    "211000-100": {
        "rsmeans_id": "211000-100",
        "description": "Fire sprinkler system, wet pipe, light hazard",
        "unit": "SF",
        "material_cost": 2.85,
        "labor_cost": 3.15,
        "equipment_cost": 0.50,
        "total_cost": 6.50,
        "category": "Fire Protection",
        "csi_division": "21"
    },
    
    # ============================================
    # PLUMBING (Division 22)
    # ============================================
    "220500-100": {
        "rsmeans_id": "220500-100",
        "description": "Plumbing fixtures, water closet, floor mounted",
        "unit": "EA",
        "material_cost": 285.00,
        "labor_cost": 185.00,
        "equipment_cost": 15.00,
        "total_cost": 485.00,
        "category": "Plumbing",
        "csi_division": "22"
    },
    "220500-200": {
        "rsmeans_id": "220500-200",
        "description": "Plumbing fixtures, lavatory, wall hung",
        "unit": "EA",
        "material_cost": 225.00,
        "labor_cost": 165.00,
        "equipment_cost": 12.50,
        "total_cost": 402.50,
        "category": "Plumbing",
        "csi_division": "22"
    },
    
    # ============================================
    # HVAC (Division 23)
    # ============================================
    "238100-100": {
        "rsmeans_id": "238100-100",
        "description": "Air conditioning, split system, 2 ton",
        "unit": "EA",
        "material_cost": 1850.00,
        "labor_cost": 1250.00,
        "equipment_cost": 125.00,
        "total_cost": 3225.00,
        "category": "HVAC",
        "csi_division": "23"
    },
    "238100-200": {
        "rsmeans_id": "238100-200",
        "description": "Air conditioning, split system, 5 ton",
        "unit": "EA",
        "material_cost": 2850.00,
        "labor_cost": 1850.00,
        "equipment_cost": 185.00,
        "total_cost": 4885.00,
        "category": "HVAC",
        "csi_division": "23"
    },
    "238239-100": {
        "rsmeans_id": "238239-100",
        "description": "Ductwork, galvanized, low pressure, 24 gauge",
        "unit": "LB",
        "material_cost": 2.85,
        "labor_cost": 3.25,
        "equipment_cost": 0.40,
        "total_cost": 6.50,
        "category": "HVAC",
        "csi_division": "23"
    },
    
    # ============================================
    # ELECTRICAL (Division 26)
    # ============================================
    "260500-100": {
        "rsmeans_id": "260500-100",
        "description": "Electrical service, 200A panel, residential",
        "unit": "EA",
        "material_cost": 850.00,
        "labor_cost": 650.00,
        "equipment_cost": 50.00,
        "total_cost": 1550.00,
        "category": "Electrical",
        "csi_division": "26"
    },
    "262000-100": {
        "rsmeans_id": "262000-100",
        "description": "Electrical rough-in, standard outlet",
        "unit": "EA",
        "material_cost": 12.50,
        "labor_cost": 65.00,
        "equipment_cost": 2.50,
        "total_cost": 80.00,
        "category": "Electrical",
        "csi_division": "26"
    },
    "265100-100": {
        "rsmeans_id": "265100-100",
        "description": "Interior lighting, LED panel, 2x4",
        "unit": "EA",
        "material_cost": 125.00,
        "labor_cost": 85.00,
        "equipment_cost": 5.00,
        "total_cost": 215.00,
        "category": "Electrical",
        "csi_division": "26"
    }
}

# City cost indices for location adjustments
MOCK_CITY_INDEX = {
    # Major US Cities
    "10001": {"city": "New York", "state": "NY", "index": 135.5, "region": "Northeast"},
    "90210": {"city": "Los Angeles", "state": "CA", "index": 128.3, "region": "West"},
    "60601": {"city": "Chicago", "state": "IL", "index": 118.7, "region": "Midwest"},
    "77001": {"city": "Houston", "state": "TX", "index": 98.4, "region": "South"},
    "85001": {"city": "Phoenix", "state": "AZ", "index": 102.1, "region": "West"},
    "19101": {"city": "Philadelphia", "state": "PA", "index": 115.2, "region": "Northeast"},
    "78205": {"city": "San Antonio", "state": "TX", "index": 95.8, "region": "South"},
    "92101": {"city": "San Diego", "state": "CA", "index": 125.5, "region": "West"},
    "75201": {"city": "Dallas", "state": "TX", "index": 101.5, "region": "South"},
    "95113": {"city": "San Jose", "state": "CA", "index": 142.8, "region": "West"},
    "98101": {"city": "Seattle", "state": "WA", "index": 118.5, "region": "West"},
    "30303": {"city": "Atlanta", "state": "GA", "index": 104.2, "region": "South"},
    "80202": {"city": "Denver", "state": "CO", "index": 108.5, "region": "West"},
    "20001": {"city": "Washington DC", "state": "DC", "index": 112.5, "region": "Northeast"},
    "33101": {"city": "Miami", "state": "FL", "index": 108.8, "region": "South"},
    "55401": {"city": "Minneapolis", "state": "MN", "index": 110.5, "region": "Midwest"},
    "97201": {"city": "Portland", "state": "OR", "index": 115.8, "region": "West"},
    "64101": {"city": "Kansas City", "state": "MO", "index": 102.5, "region": "Midwest"},
    "44101": {"city": "Cleveland", "state": "OH", "index": 108.2, "region": "Midwest"},
    "38103": {"city": "Memphis", "state": "TN", "index": 96.5, "region": "South"},
    "18101": {"city": "Allentown", "state": "PA", "index": 112.5, "region": "Northeast"},
    "53201": {"city": "Milwaukee", "state": "WI", "index": 106.8, "region": "Midwest"},
    "72201": {"city": "Little Rock", "state": "AR", "index": 95.2, "region": "South"},
    "83701": {"city": "Boise", "state": "ID", "index": 101.8, "region": "West"},
    "87501": {"city": "Santa Fe", "state": "NM", "index": 98.5, "region": "West"},
    "17101": {"city": "Harrisburg", "state": "PA", "index": 106.5, "region": "Northeast"},
    "29201": {"city": "Columbia", "state": "SC", "index": 97.8, "region": "South"},
    "23510": {"city": "Norfolk", "state": "VA", "index": 99.5, "region": "South"},
    "65801": {"city": "Springfield", "state": "MO", "index": 94.5, "region": "Midwest"},
    "79101": {"city": "Amarillo", "state": "TX", "index": 92.8, "region": "South"},
    
    # International (base 100)
    "Riyadh": {"city": "Riyadh", "state": "Saudi Arabia", "index": 98.5, "region": "International"},
    "Dubai": {"city": "Dubai", "state": "UAE", "index": 95.2, "region": "International"},
    "London": {"city": "London", "state": "UK", "index": 142.5, "region": "International"},
    "Toronto": {"city": "Toronto", "state": "Canada", "index": 108.5, "region": "International"},
    "Sydney": {"city": "Sydney", "state": "Australia", "index": 125.8, "region": "International"}
}

# Building type costs for quick estimates (per sq ft)
BUILDING_TYPE_COSTS = {
    "office": {"base_cost": 175.0, "description": "Office building, standard finish"},
    "retail": {"base_cost": 145.0, "description": "Retail store, open plan"},
    "warehouse": {"base_cost": 85.0, "description": "Warehouse, shell only"},
    "apartment": {"base_cost": 195.0, "description": "Multi-family residential"},
    "hospital": {"base_cost": 450.0, "description": "Hospital, fully equipped"},
    "school": {"base_cost": 220.0, "description": "K-12 school building"},
    "industrial": {"base_cost": 125.0, "description": "Light industrial/manufacturing"},
    "hotel": {"base_cost": 285.0, "description": "Hotel, mid-scale"},
    "restaurant": {"base_cost": 245.0, "description": "Restaurant, full service"},
    "parking": {"base_cost": 65.0, "description": "Parking structure, above grade"},
    "residential_custom": {"base_cost": 285.0, "description": "Custom single family home"},
    "residential_tract": {"base_cost": 145.0, "description": "Tract housing, production built"}
}

# CSI MasterFormat divisions for categorization
CSI_DIVISIONS = {
    "01": "General Requirements",
    "02": "Existing Conditions",
    "03": "Concrete",
    "04": "Masonry",
    "05": "Metals",
    "06": "Wood, Plastics, Composites",
    "07": "Thermal and Moisture Protection",
    "08": "Openings",
    "09": "Finishes",
    "10": "Specialties",
    "11": "Equipment",
    "12": "Furnishings",
    "13": "Special Construction",
    "14": "Conveying Equipment",
    "21": "Fire Suppression",
    "22": "Plumbing",
    "23": "Heating, Ventilating, and Air Conditioning",
    "25": "Integrated Automation",
    "26": "Electrical",
    "27": "Communications",
    "28": "Electronic Safety and Security"
}
