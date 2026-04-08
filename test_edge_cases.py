#!/usr/bin/env python3
"""Edge case testing for Cerebrum chat endpoints"""

import requests
import json

BASE_URL = "http://localhost:8000"
AGENT_URL = f"{BASE_URL}/api/v1/agent/v2"
CHAT_URL = f"{BASE_URL}/api/v1/chat"

def test_case(name, method, url, payload, checks):
    """Run a test case and verify checks"""
    try:
        if method == "POST":
            resp = requests.post(url, json=payload, timeout=30)
        else:
            resp = requests.get(url, timeout=30)
        
        if resp.status_code != 200:
            print(f"✗ {name}: HTTP {resp.status_code}")
            return False
        
        data = resp.json()
        
        # Get message content
        if "choices" in data:
            message = data["choices"][0].get("message", {}).get("content", "").lower()
        else:
            message = data.get("message", "").lower()
        
        # Run checks
        passed = True
        for check_name, check_func in checks.items():
            if not check_func(message, data):
                print(f"✗ {name}: Failed check '{check_name}'")
                print(f"  Message: {message[:150]}...")
                passed = False
                break
        
        if passed:
            print(f"✓ {name}")
        return passed
    except Exception as e:
        print(f"✗ {name}: {e}")
        return False

def main():
    print("=== EDGE CASE TESTING ===\n")
    
    results = []
    
    # Edge Case 1: Empty context
    results.append(test_case(
        "Agent: Empty context",
        "POST", f"{AGENT_URL}/execute",
        {"task": "Hello", "context": {}},
        {"has_greeting": lambda m, d: any(w in m for w in ["hello", "hi", "hey"])}
    ))
    
    # Edge Case 2: Very long query
    results.append(test_case(
        "Agent: Long query",
        "POST", f"{AGENT_URL}/execute",
        {"task": "I need to calculate the cost for a very large warehouse building that is approximately 50000 square feet in size and located in a major metropolitan area with high labor costs", "context": {}},
        {"has_response": lambda m, d: len(m) > 10}
    ))
    
    # Edge Case 3: Special characters
    results.append(test_case(
        "Agent: Special chars",
        "POST", f"{AGENT_URL}/execute",
        {"task": "Cost for 5,000 sq.ft. office-building (high-rise) @ NYC?", "context": {}},
        {"has_response": lambda m, d: len(m) > 10}
    ))
    
    # Edge Case 4: Normal chat with history
    results.append(test_case(
        "Normal: With history",
        "POST", f"{CHAT_URL}/completions",
        {
            "model": "cerebrum-default",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "What can you do?"}
            ]
        },
        {"has_capabilities": lambda m, d: any(w in m for w in ["help", "cost", "construction"])}
    ))
    
    # Edge Case 5: Normal chat - just numbers
    results.append(test_case(
        "Normal: Just numbers",
        "POST", f"{CHAT_URL}/completions",
        {
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "5000 sq ft"}]
        },
        {"has_response": lambda m, d: len(m) > 10}
    ))
    
    # Edge Case 6: Agent - unclear query
    results.append(test_case(
        "Agent: Unclear query",
        "POST", f"{AGENT_URL}/execute",
        {"task": "???", "context": {}},
        {"has_response": lambda m, d: len(m) > 10}
    ))
    
    # Edge Case 7: Agent - memory search
    results.append(test_case(
        "Agent: Memory search",
        "POST", f"{AGENT_URL}/execute",
        {"task": "What did we discuss earlier?", "context": {}, "use_memory": True},
        {"has_response": lambda m, d: len(m) > 10}
    ))
    
    # Edge Case 8: Different building types
    results.append(test_case(
        "Agent: Hospital estimate",
        "POST", f"{AGENT_URL}/execute",
        {"task": "Estimate hospital 20000 sq ft", "context": {}},
        {"has_hospital": lambda m, d: "hospital" in m or "estimate" in m or "cost" in m}
    ))
    
    # Summary
    print(f"\n=== SUMMARY ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} ({passed/total*100:.0f}%)")
    
    return passed == total

if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
