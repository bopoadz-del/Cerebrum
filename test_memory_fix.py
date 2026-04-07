#!/usr/bin/env python3
"""Test script for conversation history memory fix - standalone."""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/cerebrum-fix/backend')

import re
from typing import Dict, List, Optional, Any


def extract_context_from_history(task: str, conversation_history: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Extract relevant context from conversation history to answer follow-up questions."""
    if not conversation_history or len(conversation_history) < 2:
        return {}
    
    context = {}
    task_lower = task.lower()
    
    # Look for references to previous calculations
    reference_patterns = [
        r'(?:that|the|this|those|these)\s+(\d+m?\s*x\s*\d+m?)\s+foundation',
        r'(?:that|the|this|those|these)\s+(\d+m?\s*x\s*\d+m?)\s+slab',
        r'(?:that|the|this|those|these)\s+(\d+m?\s*x\s*\d+m?)\s+area',
        r'(?:that|the|this|those|these)\s+dimensions?',
        r'(?:that|the|this|those|these)\s+calculation',
        r'(?:it|that|this)\s+is?\s+(\d+m?\s*x\s*\d+m?)',
        r'what\s+about\s+(\d+m?\s*x\s*\d+m?)',
    ]
    
    # Check if task contains reference patterns (indicating a follow-up question)
    is_follow_up = any(re.search(pattern, task_lower) for pattern in reference_patterns)
    is_follow_up = is_follow_up or any(word in task_lower for word in [
        'that foundation', 'that slab', 'those dimensions', 'the dimensions', 
        'the calculation', 'previous', 'earlier', 'we calculated', 'we discussed',
        'what about', 'how about', 'and for', 'also', 'too', 'about it'
    ])
    
    if not is_follow_up:
        return context
    
    # Search through conversation history for dimensions and calculations
    for msg in reversed(conversation_history):
        content = msg.get('content', '')
        role = msg.get('role', '')
        content_lower = content.lower()
        
        # Look for concrete/steel calculations in assistant responses
        if role == 'assistant':
            # Check for calculation output markers (Dimensions section with length/width/depth)
            has_dimensions_section = ('length' in content_lower and 'width' in content_lower) or \
                                     ('dimensions' in content_lower and 'volume' in content_lower)
            
            if has_dimensions_section:
                context['has_previous_calculation'] = True
                context['assistant_calculation_content'] = content
                
                # Extract dimensions - handle "10 m" format with space
                # Look for pattern: number followed by optional space and 'm' or 'meters'
                all_dims = re.findall(r'(\d+\.?\d*)\s*(?:m|meters?)', content_lower)
                if len(all_dims) >= 2:
                    context['previous_length'] = all_dims[0]
                    context['previous_width'] = all_dims[1]
                    if len(all_dims) >= 3:
                        context['previous_depth'] = all_dims[2]
                break
    
    return context


def test_extract_context():
    """Test context extraction from conversation history."""
    print("🧪 Testing context extraction...\n")
    
    # Test case 1: Follow-up about "the foundation we calculated"
    assistant_response = """📐 **Concrete Volume Calculation**

**Dimensions:**
• Length: 10 m
• Width: 8 m
• Depth: 0.5 m

**Volume:**
• **40.00 cubic meters** (m³)
• 1412.60 cubic feet
• 52.32 cubic yards

**Estimated Cost:**
• $6,278 - $7,848 (@ $120-150/yd³)"""
    
    conversation_history = [
        {"role": "user", "content": "Calculate concrete for 10m x 8m x 0.5m", "timestamp": "2024-01-01T10:00:00Z"},
        {"role": "assistant", "content": assistant_response, "timestamp": "2024-01-01T10:00:01Z"},
        {"role": "user", "content": "What about the steel for that foundation?", "timestamp": "2024-01-01T10:01:00Z"}
    ]
    
    task = "What about the steel for that foundation?"
    context = extract_context_from_history(task, conversation_history)
    
    print(f"Task: {task}")
    print(f"Extracted context: {context}")
    print(f"Has previous calculation: {context.get('has_previous_calculation', False)}")
    
    # Debug: print regex match
    content_lower = assistant_response.lower()
    all_dims = re.findall(r'(\d+\.?\d*)\s*(?:m|meters?)', content_lower)
    print(f"Regex found dimensions: {all_dims}")
    print(f"Has length: {'length' in content_lower}")
    print(f"Has width: {'width' in content_lower}")
    print()
    
    assert context.get('has_previous_calculation') == True, "Should detect previous calculation"
    assert context.get('previous_length') == '10', f"Expected length '10', got {context.get('previous_length')}"
    assert context.get('previous_width') == '8', f"Expected width '8', got {context.get('previous_width')}"
    assert context.get('previous_depth') == '0.5', f"Expected depth '0.5', got {context.get('previous_depth')}"
    
    print("✅ Test 1 passed: Context extraction works!\n")


def test_no_follow_up():
    """Test that non-follow-up queries don't extract context."""
    print("🧪 Testing non-follow-up query...\n")
    
    conversation_history = [
        {"role": "user", "content": "Calculate concrete for 10m x 8m x 0.5m", "timestamp": "2024-01-01T10:00:00Z"},
        {"role": "assistant", "content": "Calculated 40 cubic meters", "timestamp": "2024-01-01T10:00:01Z"},
    ]
    
    # This is a fresh query, not a follow-up
    task = "Calculate concrete for 5m x 4m x 0.3m"
    context = extract_context_from_history(task, conversation_history)
    
    print(f"Task: {task}")
    print(f"Extracted context: {context}")
    print()
    
    assert context == {}, "Should not extract context for non-follow-up"
    
    print("✅ Test 2 passed: Non-follow-up queries don't extract context!\n")


def test_various_follow_up_patterns():
    """Test various follow-up patterns."""
    print("🧪 Testing various follow-up patterns...\n")
    
    conversation_history = [
        {"role": "user", "content": "Calculate concrete for 10m x 8m x 0.5m", "timestamp": "2024-01-01T10:00:00Z"},
        {"role": "assistant", "content": """📐 **Concrete Volume Calculation**

**Dimensions:**
• Length: 10 m
• Width: 8 m
• Depth: 0.5 m""", "timestamp": "2024-01-01T10:00:01Z"},
    ]
    
    follow_up_patterns = [
        "What's the cost for that foundation?",
        "How about that slab?",
        "What about the dimensions we discussed?",
        "Calculate steel for that foundation",
        "What about earlier calculation?",
        "Tell me more about it",  # Will be lowercased in function
    ]
    
    for task in follow_up_patterns:
        context = extract_context_from_history(task, conversation_history)
        assert context.get('has_previous_calculation') == True, f"Should detect follow-up for: {task}"
        print(f"✅ '{task[:40]}...' - correctly detected as follow-up")
    
    print("\n✅ Test 3 passed: Various follow-up patterns work!\n")


def test_empty_history():
    """Test with empty or None history."""
    print("🧪 Testing empty history...\n")
    
    task = "What about that foundation?"
    
    # Test with None
    context = extract_context_from_history(task, None)
    assert context == {}, "Should return empty dict for None history"
    
    # Test with empty list
    context = extract_context_from_history(task, [])
    assert context == {}, "Should return empty dict for empty history"
    
    # Test with only one message
    context = extract_context_from_history(task, [{"role": "user", "content": "hello"}])
    assert context == {}, "Should return empty dict for single message"
    
    print("✅ Test 4 passed: Empty history handled correctly!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("CONVERSATION MEMORY FIX - TEST SUITE")
    print("=" * 60)
    print()
    
    try:
        test_extract_context()
        test_no_follow_up()
        test_various_follow_up_patterns()
        test_empty_history()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Summary:")
        print("- Conversation history is being extracted correctly")
        print("- Follow-up questions are detected using various patterns")
        print("- Previous dimensions are extracted from assistant responses")
        print("- Empty history is handled gracefully")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
