#!/usr/bin/env python3
"""Test script to verify economics query routing logic."""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/cerebrum-fix/backend')

# Test the pattern detection from chat.py
ECONOMICS_KEYWORDS = [
    'cost', 'price', 'budget', 'estimate', 'concrete', 'building', 'sq ft',
    'square feet', 'square foot', 'cubic', 'meters', 'masonry', 'steel', 'wood',
    'drywall', 'paint', 'flooring', 'roofing', 'electrical', 'plumbing', 'hvac',
    'excavation', 'rebar', 'formwork', 'quantity', 'quantities', 'material',
    'labor', 'rsmeans', 'csi', 'division', 'unit price', 'cubic meters',
    'cubic feet', 'square meters', 'square footage'
]


def is_economics_query(message: str) -> bool:
    """Check if the message is an economics/construction cost query."""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in ECONOMICS_KEYWORDS)


# Test cases
test_cases = [
    ("Calculate 50 cubic meters of concrete", True),
    ("What is the cost of steel per ton?", True),
    ("Estimate a 5000 sq ft office building", True),
    ("Price of drywall per sheet", True),
    ("Building budget for warehouse", True),
    ("Hello, how are you?", False),
    ("What can you do?", False),
    ("Help me with formulas", False),
    ("Who are you?", False),
]

print("Testing economics query detection:")
print("=" * 60)

all_passed = True
for query, expected in test_cases:
    result = is_economics_query(query)
    status = "✓ PASS" if result == expected else "✗ FAIL"
    if result != expected:
        all_passed = False
    print(f"{status} | Query: '{query[:50]}...' | Expected: {expected}, Got: {result}")

print("=" * 60)
if all_passed:
    print("All tests passed!")
else:
    print("Some tests failed!")

# Now test the quantity extraction from enhanced_core.py
print("\n\nTesting quantity extraction:")
print("=" * 60)

import re

quantity_pattern = r'\b(\d+(?:,\d{3})*)\s*(?:units?|pcs?|pieces?|tons?|lbs?|pounds?|kg|kilograms?|bags?|blocks?|bricks?|sheets?|panels?|cubic\s+(?:meters?|feet|foot|yards?|yd)|cu\.?\s*(?:m|ft|yd)|m3|m³|ft3|ft³|yd3|yd³|cy|cf)\b'

quantity_tests = [
    ("Calculate 50 cubic meters of concrete", "50"),
    ("100 cubic feet of concrete", "100"),
    ("200 cf of concrete", "200"),
    ("300 cubic yards", "300"),
    ("400 cy of dirt", "400"),
    ("I need 500 bricks", "500"),
    ("1000 sheets of drywall", "1000"),
    ("10 tons of steel", "10"),
    ("25 kg of nails", "25"),
]

for query, expected_qty in quantity_tests:
    match = re.search(quantity_pattern, query.lower(), re.IGNORECASE)
    if match:
        qty = match.group(1).replace(',', '')
        status = "✓ PASS" if qty == expected_qty else "✗ FAIL"
        if qty != expected_qty:
            all_passed = False
        print(f"{status} | Query: '{query[:50]}' | Expected qty: {expected_qty}, Got: {qty}")
    else:
        print(f"✗ FAIL | Query: '{query[:50]}' | Expected qty: {expected_qty}, Got: None")
        all_passed = False

print("=" * 60)
if all_passed:
    print("All tests passed!")
    sys.exit(0)
else:
    print("Some tests failed!")
    sys.exit(1)
