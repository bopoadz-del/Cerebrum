#!/usr/bin/env python3
"""Test script for enhanced response formatting in Cerebrum."""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/cerebrum-fix/backend')

from app.agent.enhanced_core import EnhancedCerebrumAgent

def test_formatting():
    """Test the new formatting methods."""
    agent = EnhancedCerebrumAgent()
    
    print("=" * 60)
    print("TESTING ENHANCED RESPONSE FORMATTING")
    print("=" * 60)
    
    # Test 1: Memory search with 0 results
    print("\n1. MEMORY SEARCH - 0 RESULTS")
    print("-" * 40)
    result = {
        "query": "unicorn material costs",
        "total_matches": 0,
        "results": []
    }
    message = agent._format_memory_search_result(result, "unicorn material costs")
    print(message)
    
    # Test 2: Memory search with results
    print("\n2. MEMORY SEARCH - WITH RESULTS")
    print("-" * 40)
    result = {
        "query": "concrete costs",
        "total_matches": 3,
        "results": [
            {
                "id": "abc123",
                "content": "Foundation concrete cost was $125 per cubic yard for the warehouse project in Riyadh.",
                "source": "memory/2024-01-15.md",
                "timestamp": "2024-01-15T10:30:00",
                "tags": ["costs", "concrete", "warehouse"],
                "related_layers": ["economics"]
            },
            {
                "id": "def456", 
                "content": "Structural concrete for office building: 500 cubic yards at $130/cy.",
                "source": "memory/2024-02-20.md",
                "timestamp": "2024-02-20T14:15:00",
                "tags": ["concrete", "office"],
                "related_layers": ["economics", "vdc"]
            }
        ]
    }
    message = agent._format_memory_search_result(result, "concrete costs")
    print(message)
    
    # Test 3: Economics - Building Estimate
    print("\n3. ECONOMICS - BUILDING ESTIMATE")
    print("-" * 40)
    result = {
        "building_type": "warehouse",
        "size_sf": 5000,
        "city": "Riyadh",
        "costs": {
            "materials": 125000,
            "labor": 87500,
            "equipment": 25000,
            "overhead": 37500
        },
        "total_cost": 275000,
        "cost_per_sqft": 55.00
    }
    message = agent._format_economics_result("estimate_project", result, "warehouse cost")
    print(message)
    
    # Test 4: Economics - RSMeans Item Results
    print("\n4. ECONOMICS - RSMEANS ITEMS")
    print("-" * 40)
    result = {
        "query": "concrete",
        "total": 15,
        "results": [
            {
                "description": "Concrete, 3000 PSI, per cubic yard",
                "base_cost": 125.50,
                "unit": "cy",
                "item_id": "03-30-10-1000"
            },
            {
                "description": "Concrete, 4000 PSI, per cubic yard",
                "base_cost": 138.75,
                "unit": "cy",
                "item_id": "03-30-10-1100"
            },
            {
                "description": "Reinforcing steel, #4, per lb",
                "base_cost": 0.85,
                "unit": "lb",
                "item_id": "03-20-10-1000"
            }
        ]
    }
    message = agent._format_economics_result("rsmeans_query", result, "concrete")
    print(message)
    
    # Test 5: Economics - Cost Calculation
    print("\n5. ECONOMICS - COST CALCULATION")
    print("-" * 40)
    result = {
        "item": {
            "description": "Concrete, 3000 PSI, per cubic yard",
            "base_cost": 125.50,
            "unit": "cy"
        },
        "quantity": 50,
        "total_cost": 6275.00
    }
    message = agent._format_economics_result("calculate_cost", result, "50 cubic yards concrete")
    print(message)
    
    # Test 6: Error Message
    print("\n6. ERROR MESSAGE")
    print("-" * 40)
    message = agent._format_error_message("calculate_cost", "Need building_type+size_sf or item_id+quantity", "calculate cost")
    print(message)
    
    # Test 7: Formula Search Results
    print("\n7. FORMULA SEARCH RESULTS")
    print("-" * 40)
    result = {
        "query": "concrete slab",
        "formulas": [
            {"name": "Concrete Slab Volume", "description": "Calculate cubic yards for a concrete slab", "category": "Concrete"},
            {"name": "Slab Reinforcement", "description": "Calculate rebar needed for slab", "category": "Concrete"}
        ]
    }
    message = agent._format_formula_search_result(result, "concrete slab")
    print(message)
    
    # Test 8: Code Generation Result
    print("\n8. CODE GENERATION RESULT")
    print("-" * 40)
    result = {"artifact": "api/endpoints/material_tracking.py", "success": True}
    message = agent._format_generation_result("generate_endpoint", result, "create material tracking endpoint")
    print(message)
    
    # Test 9: Validation Result - Success
    print("\n9. VALIDATION - SUCCESS")
    print("-" * 40)
    result = {"success": True, "passed": True, "issues": []}
    message = agent._format_validation_result("scan_security", result, "scan code")
    print(message)
    
    # Test 10: Validation Result - With Issues
    print("\n10. VALIDATION - WITH ISSUES")
    print("-" * 40)
    result = {
        "success": True,
        "passed": False,
        "vulnerabilities": [
            {"severity": "High", "description": "SQL injection vulnerability in user input"},
            {"severity": "Medium", "description": "Missing input validation on API endpoint"}
        ]
    }
    message = agent._format_validation_result("scan_security", result, "scan code")
    print(message)
    
    print("\n" + "=" * 60)
    print("ALL FORMATTING TESTS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_formatting()
