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
    # INFRASTRUCTURE & SITE WORK (Division 31-33)
    # ============================================
    # MANHOLES & CATCH BASINS
    "330101-100": {
        "rsmeans_id": "330101-100",
        "description": "Manhole, precast concrete, 4' diameter, 8' deep, complete",
        "unit": "EA",
        "material_cost": 1850.00,
        "labor_cost": 950.00,
        "equipment_cost": 285.00,
        "total_cost": 3085.00,
        "category": "Manholes",
        "csi_division": "33",
        "infrastructure_type": "storm_sanitary"
    },
    "330101-200": {
        "rsmeans_id": "330101-200",
        "description": "Manhole, precast concrete, 5' diameter, 10' deep, complete",
        "unit": "EA",
        "material_cost": 2850.00,
        "labor_cost": 1250.00,
        "equipment_cost": 385.00,
        "total_cost": 4485.00,
        "category": "Manholes",
        "csi_division": "33",
        "infrastructure_type": "storm_sanitary"
    },
    "330101-300": {
        "rsmeans_id": "330101-300",
        "description": "Manhole, precast concrete, 6' diameter, 12' deep, complete",
        "unit": "EA",
        "material_cost": 3850.00,
        "labor_cost": 1650.00,
        "equipment_cost": 485.00,
        "total_cost": 5985.00,
        "category": "Manholes",
        "csi_division": "33",
        "infrastructure_type": "storm_sanitary"
    },
    "330101-400": {
        "rsmeans_id": "330101-400",
        "description": "Drop manhole, precast, 5' diameter, 15' deep with drop connection",
        "unit": "EA",
        "material_cost": 4850.00,
        "labor_cost": 2250.00,
        "equipment_cost": 650.00,
        "total_cost": 7750.00,
        "category": "Manholes",
        "csi_division": "33",
        "infrastructure_type": "storm_sanitary"
    },
    "330102-100": {
        "rsmeans_id": "330102-100",
        "description": "Catch basin, precast concrete, 2' x 2' x 4' deep",
        "unit": "EA",
        "material_cost": 485.00,
        "labor_cost": 285.00,
        "equipment_cost": 85.00,
        "total_cost": 855.00,
        "category": "Catch Basins",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330102-200": {
        "rsmeans_id": "330102-200",
        "description": "Catch basin, precast concrete, 3' x 3' x 6' deep",
        "unit": "EA",
        "material_cost": 850.00,
        "labor_cost": 450.00,
        "equipment_cost": 125.00,
        "total_cost": 1425.00,
        "category": "Catch Basins",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330103-100": {
        "rsmeans_id": "330103-100",
        "description": "Manhole cover and frame, cast iron, medium duty",
        "unit": "SET",
        "material_cost": 285.00,
        "labor_cost": 125.00,
        "equipment_cost": 25.00,
        "total_cost": 435.00,
        "category": "Manhole Covers",
        "csi_division": "33",
        "infrastructure_type": "storm_sanitary"
    },
    "330103-200": {
        "rsmeans_id": "330103-200",
        "description": "Manhole cover and frame, cast iron, heavy duty (H-20 loading)",
        "unit": "SET",
        "material_cost": 425.00,
        "labor_cost": 145.00,
        "equipment_cost": 35.00,
        "total_cost": 605.00,
        "category": "Manhole Covers",
        "csi_division": "33",
        "infrastructure_type": "storm_sanitary"
    },
    "330104-100": {
        "rsmeans_id": "330104-100",
        "description": "Storm drain grate, cast iron, 12\" x 24\"",
        "unit": "EA",
        "material_cost": 125.00,
        "labor_cost": 65.00,
        "equipment_cost": 15.00,
        "total_cost": 205.00,
        "category": "Drain Grates",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    
    # SANITARY SEWER PIPE
    "330201-100": {
        "rsmeans_id": "330201-100",
        "description": "PVC pipe, sanitary sewer, SDR-35, 4\" diameter",
        "unit": "LF",
        "material_cost": 4.25,
        "labor_cost": 8.50,
        "equipment_cost": 1.25,
        "total_cost": 14.00,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330201-200": {
        "rsmeans_id": "330201-200",
        "description": "PVC pipe, sanitary sewer, SDR-35, 6\" diameter",
        "unit": "LF",
        "material_cost": 6.50,
        "labor_cost": 10.25,
        "equipment_cost": 1.75,
        "total_cost": 18.50,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330201-300": {
        "rsmeans_id": "330201-300",
        "description": "PVC pipe, sanitary sewer, SDR-35, 8\" diameter",
        "unit": "LF",
        "material_cost": 9.85,
        "labor_cost": 12.50,
        "equipment_cost": 2.15,
        "total_cost": 24.50,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330201-400": {
        "rsmeans_id": "330201-400",
        "description": "PVC pipe, sanitary sewer, SDR-35, 10\" diameter",
        "unit": "LF",
        "material_cost": 14.50,
        "labor_cost": 15.00,
        "equipment_cost": 2.50,
        "total_cost": 32.00,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330201-500": {
        "rsmeans_id": "330201-500",
        "description": "PVC pipe, sanitary sewer, SDR-35, 12\" diameter",
        "unit": "LF",
        "material_cost": 18.50,
        "labor_cost": 18.50,
        "equipment_cost": 3.00,
        "total_cost": 40.00,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330202-100": {
        "rsmeans_id": "330202-100",
        "description": "Ductile iron pipe, sanitary sewer, CL 52, 8\"",
        "unit": "LF",
        "material_cost": 28.50,
        "labor_cost": 18.50,
        "equipment_cost": 3.00,
        "total_cost": 50.00,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330202-200": {
        "rsmeans_id": "330202-200",
        "description": "Ductile iron pipe, sanitary sewer, CL 52, 12\"",
        "unit": "LF",
        "material_cost": 48.50,
        "labor_cost": 22.50,
        "equipment_cost": 4.00,
        "total_cost": 75.00,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330202-300": {
        "rsmeans_id": "330202-300",
        "description": "Ductile iron pipe, sanitary sewer, CL 52, 15\"",
        "unit": "LF",
        "material_cost": 65.00,
        "labor_cost": 28.50,
        "equipment_cost": 4.50,
        "total_cost": 98.00,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330203-100": {
        "rsmeans_id": "330203-100",
        "description": "Concrete pipe, sanitary sewer, Class III, 15\"",
        "unit": "LF",
        "material_cost": 35.00,
        "labor_cost": 15.00,
        "equipment_cost": 3.50,
        "total_cost": 53.50,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330203-200": {
        "rsmeans_id": "330203-200",
        "description": "Concrete pipe, sanitary sewer, Class III, 18\"",
        "unit": "LF",
        "material_cost": 45.00,
        "labor_cost": 18.50,
        "equipment_cost": 4.00,
        "total_cost": 67.50,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330203-300": {
        "rsmeans_id": "330203-300",
        "description": "Concrete pipe, sanitary sewer, Class III, 24\"",
        "unit": "LF",
        "material_cost": 65.00,
        "labor_cost": 25.00,
        "equipment_cost": 5.00,
        "total_cost": 95.00,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330203-400": {
        "rsmeans_id": "330203-400",
        "description": "Concrete pipe, sanitary sewer, Class IV, 30\"",
        "unit": "LF",
        "material_cost": 85.00,
        "labor_cost": 32.50,
        "equipment_cost": 6.50,
        "total_cost": 124.00,
        "category": "Sanitary Sewer Pipe",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    "330204-100": {
        "rsmeans_id": "330204-100",
        "description": "Sewer service lateral, PVC, 4\", with connection",
        "unit": "EA",
        "material_cost": 125.00,
        "labor_cost": 285.00,
        "equipment_cost": 65.00,
        "total_cost": 475.00,
        "category": "Service Laterals",
        "csi_division": "33",
        "infrastructure_type": "sanitary"
    },
    
    # STORM DRAINAGE PIPE
    "330301-100": {
        "rsmeans_id": "330301-100",
        "description": "Corrugated metal pipe (CMP), storm, 12\" diameter",
        "unit": "LF",
        "material_cost": 8.50,
        "labor_cost": 6.50,
        "equipment_cost": 1.00,
        "total_cost": 16.00,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330301-200": {
        "rsmeans_id": "330301-200",
        "description": "Corrugated metal pipe (CMP), storm, 18\" diameter",
        "unit": "LF",
        "material_cost": 12.50,
        "labor_cost": 8.50,
        "equipment_cost": 1.50,
        "total_cost": 22.50,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330301-300": {
        "rsmeans_id": "330301-300",
        "description": "Corrugated metal pipe (CMP), storm, 24\" diameter",
        "unit": "LF",
        "material_cost": 18.50,
        "labor_cost": 11.50,
        "equipment_cost": 2.00,
        "total_cost": 32.00,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330301-400": {
        "rsmeans_id": "330301-400",
        "description": "Corrugated metal pipe (CMP), storm, 36\" diameter",
        "unit": "LF",
        "material_cost": 32.50,
        "labor_cost": 18.50,
        "equipment_cost": 3.00,
        "total_cost": 54.00,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330301-500": {
        "rsmeans_id": "330301-500",
        "description": "Corrugated metal pipe (CMP), storm, 48\" diameter",
        "unit": "LF",
        "material_cost": 48.50,
        "labor_cost": 25.00,
        "equipment_cost": 4.50,
        "total_cost": 78.00,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330302-100": {
        "rsmeans_id": "330302-100",
        "description": "Reinforced concrete pipe (RCP), storm, 12\"",
        "unit": "LF",
        "material_cost": 22.50,
        "labor_cost": 12.50,
        "equipment_cost": 2.50,
        "total_cost": 37.50,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330302-200": {
        "rsmeans_id": "330302-200",
        "description": "Reinforced concrete pipe (RCP), storm, 18\"",
        "unit": "LF",
        "material_cost": 32.50,
        "labor_cost": 15.00,
        "equipment_cost": 3.00,
        "total_cost": 50.50,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330302-300": {
        "rsmeans_id": "330302-300",
        "description": "Reinforced concrete pipe (RCP), storm, 24\"",
        "unit": "LF",
        "material_cost": 45.00,
        "labor_cost": 18.50,
        "equipment_cost": 3.50,
        "total_cost": 67.00,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330302-400": {
        "rsmeans_id": "330302-400",
        "description": "Reinforced concrete pipe (RCP), storm, 36\"",
        "unit": "LF",
        "material_cost": 75.00,
        "labor_cost": 28.50,
        "equipment_cost": 5.50,
        "total_cost": 109.00,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330302-500": {
        "rsmeans_id": "330302-500",
        "description": "Reinforced concrete pipe (RCP), storm, 48\"",
        "unit": "LF",
        "material_cost": 112.50,
        "labor_cost": 38.50,
        "equipment_cost": 7.00,
        "total_cost": 158.00,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330302-600": {
        "rsmeans_id": "330302-600",
        "description": "Reinforced concrete pipe (RCP), storm, 60\"",
        "unit": "LF",
        "material_cost": 165.00,
        "labor_cost": 52.50,
        "equipment_cost": 9.50,
        "total_cost": 227.00,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330303-100": {
        "rsmeans_id": "330303-100",
        "description": "HDPE pipe, storm, corrugated, 12\"",
        "unit": "LF",
        "material_cost": 12.50,
        "labor_cost": 8.50,
        "equipment_cost": 1.50,
        "total_cost": 22.50,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330303-200": {
        "rsmeans_id": "330303-200",
        "description": "HDPE pipe, storm, corrugated, 24\"",
        "unit": "LF",
        "material_cost": 28.50,
        "labor_cost": 12.50,
        "equipment_cost": 2.50,
        "total_cost": 43.50,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    "330303-300": {
        "rsmeans_id": "330303-300",
        "description": "HDPE pipe, storm, corrugated, 36\"",
        "unit": "LF",
        "material_cost": 52.50,
        "labor_cost": 18.50,
        "equipment_cost": 4.00,
        "total_cost": 75.00,
        "category": "Storm Drainage",
        "csi_division": "33",
        "infrastructure_type": "storm"
    },
    
    # POTABLE WATER DISTRIBUTION
    "330401-100": {
        "rsmeans_id": "330401-100",
        "description": "PVC pipe, water main, C900, 6\" diameter",
        "unit": "LF",
        "material_cost": 12.50,
        "labor_cost": 15.00,
        "equipment_cost": 2.50,
        "total_cost": 30.00,
        "category": "Potable Water",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330401-200": {
        "rsmeans_id": "330401-200",
        "description": "PVC pipe, water main, C900, 8\" diameter",
        "unit": "LF",
        "material_cost": 18.50,
        "labor_cost": 18.50,
        "equipment_cost": 3.00,
        "total_cost": 40.00,
        "category": "Potable Water",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330401-300": {
        "rsmeans_id": "330401-300",
        "description": "PVC pipe, water main, C900, 12\" diameter",
        "unit": "LF",
        "material_cost": 32.50,
        "labor_cost": 22.50,
        "equipment_cost": 4.00,
        "total_cost": 59.00,
        "category": "Potable Water",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330402-100": {
        "rsmeans_id": "330402-100",
        "description": "Ductile iron pipe, water, CL 350, 6\"",
        "unit": "LF",
        "material_cost": 28.50,
        "labor_cost": 18.50,
        "equipment_cost": 3.00,
        "total_cost": 50.00,
        "category": "Potable Water",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330402-200": {
        "rsmeans_id": "330402-200",
        "description": "Ductile iron pipe, water, CL 350, 8\"",
        "unit": "LF",
        "material_cost": 38.50,
        "labor_cost": 22.50,
        "equipment_cost": 3.50,
        "total_cost": 64.50,
        "category": "Potable Water",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330402-300": {
        "rsmeans_id": "330402-300",
        "description": "Ductile iron pipe, water, CL 350, 12\"",
        "unit": "LF",
        "material_cost": 65.00,
        "labor_cost": 32.50,
        "equipment_cost": 4.50,
        "total_cost": 102.00,
        "category": "Potable Water",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330403-100": {
        "rsmeans_id": "330403-100",
        "description": "Gate valve, resilient wedge, 6\"",
        "unit": "EA",
        "material_cost": 485.00,
        "labor_cost": 185.00,
        "equipment_cost": 35.00,
        "total_cost": 705.00,
        "category": "Water Valves",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330403-200": {
        "rsmeans_id": "330403-200",
        "description": "Gate valve, resilient wedge, 8\"",
        "unit": "EA",
        "material_cost": 785.00,
        "labor_cost": 225.00,
        "equipment_cost": 45.00,
        "total_cost": 1055.00,
        "category": "Water Valves",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330403-300": {
        "rsmeans_id": "330403-300",
        "description": "Gate valve, resilient wedge, 12\"",
        "unit": "EA",
        "material_cost": 1250.00,
        "labor_cost": 285.00,
        "equipment_cost": 55.00,
        "total_cost": 1590.00,
        "category": "Water Valves",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330404-100": {
        "rsmeans_id": "330404-100",
        "description": "Fire hydrant, dry barrel, complete with valve",
        "unit": "EA",
        "material_cost": 1850.00,
        "labor_cost": 850.00,
        "equipment_cost": 125.00,
        "total_cost": 2825.00,
        "category": "Fire Hydrants",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330405-100": {
        "rsmeans_id": "330405-100",
        "description": "Water meter, compound, 2\"",
        "unit": "EA",
        "material_cost": 850.00,
        "labor_cost": 325.00,
        "equipment_cost": 45.00,
        "total_cost": 1220.00,
        "category": "Water Meters",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    "330405-200": {
        "rsmeans_id": "330405-200",
        "description": "Water service line, copper, 1\", with meter box",
        "unit": "EA",
        "material_cost": 485.00,
        "labor_cost": 385.00,
        "equipment_cost": 65.00,
        "total_cost": 935.00,
        "category": "Service Lines",
        "csi_division": "33",
        "infrastructure_type": "water"
    },
    
    # IRRIGATION SYSTEMS
    "328401-100": {
        "rsmeans_id": "328401-100",
        "description": "PVC pipe, irrigation, Schedule 40, 1\"",
        "unit": "LF",
        "material_cost": 1.85,
        "labor_cost": 2.25,
        "equipment_cost": 0.40,
        "total_cost": 4.50,
        "category": "Irrigation",
        "csi_division": "32",
        "infrastructure_type": "irrigation"
    },
    "328401-200": {
        "rsmeans_id": "328401-200",
        "description": "PVC pipe, irrigation, Schedule 40, 2\"",
        "unit": "LF",
        "material_cost": 3.25,
        "labor_cost": 2.85,
        "equipment_cost": 0.40,
        "total_cost": 6.50,
        "category": "Irrigation",
        "csi_division": "32",
        "infrastructure_type": "irrigation"
    },
    "328402-100": {
        "rsmeans_id": "328402-100",
        "description": "Sprinkler head, rotary gear drive, adjustable",
        "unit": "EA",
        "material_cost": 18.50,
        "labor_cost": 12.50,
        "equipment_cost": 2.00,
        "total_cost": 33.00,
        "category": "Irrigation",
        "csi_division": "32",
        "infrastructure_type": "irrigation"
    },
    "328402-200": {
        "rsmeans_id": "328402-200",
        "description": "Sprinkler head, pop-up spray, 4\"",
        "unit": "EA",
        "material_cost": 8.50,
        "labor_cost": 8.50,
        "equipment_cost": 1.50,
        "total_cost": 18.50,
        "category": "Irrigation",
        "csi_division": "32",
        "infrastructure_type": "irrigation"
    },
    "328403-100": {
        "rsmeans_id": "328403-100",
        "description": "Irrigation control valve, electric, 1\"",
        "unit": "EA",
        "material_cost": 65.00,
        "labor_cost": 45.00,
        "equipment_cost": 5.00,
        "total_cost": 115.00,
        "category": "Irrigation",
        "csi_division": "32",
        "infrastructure_type": "irrigation"
    },
    "328404-100": {
        "rsmeans_id": "328404-100",
        "description": "Irrigation controller, 12-station, weather-based",
        "unit": "EA",
        "material_cost": 285.00,
        "labor_cost": 125.00,
        "equipment_cost": 15.00,
        "total_cost": 425.00,
        "category": "Irrigation",
        "csi_division": "32",
        "infrastructure_type": "irrigation"
    },
    "328404-200": {
        "rsmeans_id": "328404-200",
        "description": "Irrigation controller, 24-station, smart WiFi",
        "unit": "EA",
        "material_cost": 485.00,
        "labor_cost": 165.00,
        "equipment_cost": 25.00,
        "total_cost": 675.00,
        "category": "Irrigation",
        "csi_division": "32",
        "infrastructure_type": "irrigation"
    },
    "328405-100": {
        "rsmeans_id": "328405-100",
        "description": "Drip irrigation, emitter line, 0.5 GPH, 100' roll",
        "unit": "ROLL",
        "material_cost": 28.50,
        "labor_cost": 18.50,
        "equipment_cost": 3.00,
        "total_cost": 50.00,
        "category": "Irrigation",
        "csi_division": "32",
        "infrastructure_type": "irrigation"
    },
    "328406-100": {
        "rsmeans_id": "328406-100",
        "description": "Backflow preventer, reduced pressure zone (RPZ), 1\"",
        "unit": "EA",
        "material_cost": 285.00,
        "labor_cost": 125.00,
        "equipment_cost": 15.00,
        "total_cost": 425.00,
        "category": "Irrigation",
        "csi_division": "32",
        "infrastructure_type": "irrigation"
    },
    "328406-200": {
        "rsmeans_id": "328406-200",
        "description": "Backflow preventer, pressure vacuum breaker (PVB), 2\"",
        "unit": "EA",
        "material_cost": 185.00,
        "labor_cost": 95.00,
        "equipment_cost": 10.00,
        "total_cost": 290.00,
        "category": "Irrigation",
        "csi_division": "32",
        "infrastructure_type": "irrigation"
    },
    
    # ROADWORK & PAVING
    "321100-100": {
        "rsmeans_id": "321100-100",
        "description": "Asphalt paving, hot mix, 2\" compacted thickness",
        "unit": "SY",
        "material_cost": 18.50,
        "labor_cost": 6.50,
        "equipment_cost": 5.00,
        "total_cost": 30.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321100-200": {
        "rsmeans_id": "321100-200",
        "description": "Asphalt paving, hot mix, 3\" compacted thickness",
        "unit": "SY",
        "material_cost": 25.50,
        "labor_cost": 8.50,
        "equipment_cost": 6.50,
        "total_cost": 40.50,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321100-300": {
        "rsmeans_id": "321100-300",
        "description": "Asphalt paving, hot mix, 4\" compacted thickness",
        "unit": "SY",
        "material_cost": 32.50,
        "labor_cost": 10.50,
        "equipment_cost": 8.00,
        "total_cost": 51.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321100-400": {
        "rsmeans_id": "321100-400",
        "description": "Asphalt milling, 2\" depth",
        "unit": "SY",
        "material_cost": 2.50,
        "labor_cost": 3.50,
        "equipment_cost": 4.00,
        "total_cost": 10.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321200-100": {
        "rsmeans_id": "321200-100",
        "description": "Concrete paving, 6\" thick, includes reinforcement",
        "unit": "SY",
        "material_cost": 45.00,
        "labor_cost": 18.50,
        "equipment_cost": 6.50,
        "total_cost": 70.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321200-200": {
        "rsmeans_id": "321200-200",
        "description": "Concrete paving, 8\" thick, includes reinforcement",
        "unit": "SY",
        "material_cost": 58.50,
        "labor_cost": 22.50,
        "equipment_cost": 8.00,
        "total_cost": 89.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321300-100": {
        "rsmeans_id": "321300-100",
        "description": "Aggregate base course, 6\" compacted",
        "unit": "SY",
        "material_cost": 8.50,
        "labor_cost": 4.50,
        "equipment_cost": 2.00,
        "total_cost": 15.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321300-200": {
        "rsmeans_id": "321300-200",
        "description": "Aggregate base course, 12\" compacted",
        "unit": "SY",
        "material_cost": 15.50,
        "labor_cost": 7.50,
        "equipment_cost": 3.00,
        "total_cost": 26.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321400-100": {
        "rsmeans_id": "321400-100",
        "description": "Curb and gutter, concrete, 6\" x 18\"",
        "unit": "LF",
        "material_cost": 8.50,
        "labor_cost": 8.50,
        "equipment_cost": 2.00,
        "total_cost": 19.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321400-200": {
        "rsmeans_id": "321400-200",
        "description": "Curb and gutter, concrete, barrier type",
        "unit": "LF",
        "material_cost": 12.50,
        "labor_cost": 11.50,
        "equipment_cost": 3.00,
        "total_cost": 27.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321400-300": {
        "rsmeans_id": "321400-300",
        "description": "Sidewalk, concrete, 4\" thick, broom finish",
        "unit": "SF",
        "material_cost": 3.25,
        "labor_cost": 3.75,
        "equipment_cost": 1.00,
        "total_cost": 8.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321400-400": {
        "rsmeans_id": "321400-400",
        "description": "Sidewalk, concrete, 6\" thick, broom finish",
        "unit": "SF",
        "material_cost": 4.50,
        "labor_cost": 4.50,
        "equipment_cost": 1.50,
        "total_cost": 10.50,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321500-100": {
        "rsmeans_id": "321500-100",
        "description": "Pavement marking, thermoplastic, 4\" line",
        "unit": "LF",
        "material_cost": 0.35,
        "labor_cost": 0.85,
        "equipment_cost": 0.30,
        "total_cost": 1.50,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    "321500-200": {
        "rsmeans_id": "321500-200",
        "description": "Pavement marking, thermoplastic, crosswalk",
        "unit": "SF",
        "material_cost": 2.50,
        "labor_cost": 3.50,
        "equipment_cost": 1.00,
        "total_cost": 7.00,
        "category": "Roadwork",
        "csi_division": "32",
        "infrastructure_type": "road"
    },
    
    # SITE WORK & EARTHWORK
    "311000-100": {
        "rsmeans_id": "311000-100",
        "description": "Site clearing, light vegetation, per acre",
        "unit": "AC",
        "material_cost": 0.00,
        "labor_cost": 850.00,
        "equipment_cost": 450.00,
        "total_cost": 1300.00,
        "category": "Site Work",
        "csi_division": "31",
        "infrastructure_type": "sitework"
    },
    "311000-200": {
        "rsmeans_id": "311000-200",
        "description": "Site clearing, heavy vegetation/trees, per acre",
        "unit": "AC",
        "material_cost": 0.00,
        "labor_cost": 1250.00,
        "equipment_cost": 750.00,
        "total_cost": 2000.00,
        "category": "Site Work",
        "csi_division": "31",
        "infrastructure_type": "sitework"
    },
    "312300-100": {
        "rsmeans_id": "312300-100",
        "description": "Excavation, bulk, common earth, per CY",
        "unit": "CY",
        "material_cost": 0.00,
        "labor_cost": 8.50,
        "equipment_cost": 6.50,
        "total_cost": 15.00,
        "category": "Excavation",
        "csi_division": "31",
        "infrastructure_type": "sitework"
    },
    "312300-200": {
        "rsmeans_id": "312300-200",
        "description": "Excavation, trench, common earth, per CY",
        "unit": "CY",
        "material_cost": 0.00,
        "labor_cost": 12.50,
        "equipment_cost": 8.50,
        "total_cost": 21.00,
        "category": "Excavation",
        "csi_division": "31",
        "infrastructure_type": "sitework"
    },
    "312300-300": {
        "rsmeans_id": "312300-300",
        "description": "Rock excavation, unclassified, per CY",
        "unit": "CY",
        "material_cost": 0.00,
        "labor_cost": 35.00,
        "equipment_cost": 45.00,
        "total_cost": 80.00,
        "category": "Excavation",
        "csi_division": "31",
        "infrastructure_type": "sitework"
    },
    "312316-100": {
        "rsmeans_id": "312316-100",
        "description": "Backfill, compacted, imported granular",
        "unit": "CY",
        "material_cost": 25.00,
        "labor_cost": 12.50,
        "equipment_cost": 4.50,
        "total_cost": 42.00,
        "category": "Backfill",
        "csi_division": "31",
        "infrastructure_type": "sitework"
    },
    "312316-200": {
        "rsmeans_id": "312316-200",
        "description": "Backfill, flowable fill, CLSM",
        "unit": "CY",
        "material_cost": 65.00,
        "labor_cost": 15.00,
        "equipment_cost": 5.00,
        "total_cost": 85.00,
        "category": "Backfill",
        "csi_division": "31",
        "infrastructure_type": "sitework"
    },
    "313700-100": {
        "rsmeans_id": "313700-100",
        "description": "Riprap, dumped, 12\" stone",
        "unit": "TON",
        "material_cost": 28.50,
        "labor_cost": 12.50,
        "equipment_cost": 4.00,
        "total_cost": 45.00,
        "category": "Erosion Control",
        "csi_division": "31",
        "infrastructure_type": "sitework"
    },
    "313700-200": {
        "rsmeans_id": "313700-200",
        "description": "Geotextile fabric, woven, 8 oz",
        "unit": "SY",
        "material_cost": 1.25,
        "labor_cost": 0.75,
        "equipment_cost": 0.25,
        "total_cost": 2.25,
        "category": "Erosion Control",
        "csi_division": "31",
        "infrastructure_type": "sitework"
    },
    "313700-300": {
        "rsmeans_id": "313700-300",
        "description": "Silt fence, fabric with posts",
        "unit": "LF",
        "material_cost": 1.50,
        "labor_cost": 2.00,
        "equipment_cost": 0.50,
        "total_cost": 4.00,
        "category": "Erosion Control",
        "csi_division": "31",
        "infrastructure_type": "sitework"
    },
    
    # UTILITIES TRENCHING
    "330501-100": {
        "rsmeans_id": "330501-100",
        "description": "Trenching, sand bedding, 24\" wide x 36\" deep, per LF",
        "unit": "LF",
        "material_cost": 8.50,
        "labor_cost": 12.50,
        "equipment_cost": 4.00,
        "total_cost": 25.00,
        "category": "Trenching",
        "csi_division": "33",
        "infrastructure_type": "utilities"
    },
    "330501-200": {
        "rsmeans_id": "330501-200",
        "description": "Trenching, sand bedding, 36\" wide x 48\" deep, per LF",
        "unit": "LF",
        "material_cost": 18.50,
        "labor_cost": 22.50,
        "equipment_cost": 7.00,
        "total_cost": 48.00,
        "category": "Trenching",
        "csi_division": "33",
        "infrastructure_type": "utilities"
    },
    "330501-300": {
        "rsmeans_id": "330501-300",
        "description": "Pipe bedding sand, per CY placed",
        "unit": "CY",
        "material_cost": 35.00,
        "labor_cost": 15.00,
        "equipment_cost": 3.50,
        "total_cost": 53.50,
        "category": "Trenching",
        "csi_division": "33",
        "infrastructure_type": "utilities"
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
    "28": "Electronic Safety and Security",
    "31": "Earthwork",
    "32": "Exterior Improvements",
    "33": "Utilities"
}

# Infrastructure types for filtering
INFRASTRUCTURE_TYPES = {
    "storm": "Storm Drainage",
    "sanitary": "Sanitary Sewer",
    "water": "Potable Water",
    "irrigation": "Irrigation Systems",
    "road": "Roadway & Paving",
    "sitework": "Site Work & Earthwork",
    "utilities": "General Utilities"
}
