#!/usr/bin/env python3
"""
Comprehensive Cerebrum Chat Testing Script
Tests both Agent Chat and Normal Chat endpoints
"""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
AGENT_URL = f"{BASE_URL}/api/v1/agent/v2"
CHAT_URL = f"{BASE_URL}/api/v1/chat"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

results = {
    "agent_chat": {"passed": 0, "failed": 0, "tests": []},
    "normal_chat": {"passed": 0, "failed": 0, "tests": []}
}

def log_pass(test_name, details=""):
    print(f"{Colors.GREEN}✓ PASS{Colors.END}: {test_name}")
    if details:
        print(f"  {details}")

def log_fail(test_name, error, response=None):
    print(f"{Colors.RED}✗ FAIL{Colors.END}: {test_name}")
    print(f"  Error: {error}")
    if response:
        print(f"  Response: {response}")

def log_info(msg):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")

def test_agent_chat_hello():
    """Test 1: Agent Chat - Hello greeting"""
    test_name = "Agent Chat: Hello"
    try:
        resp = requests.post(f"{AGENT_URL}/execute", json={
            "task": "Hello",
            "context": {},
            "use_memory": True
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("message", "").lower()
        
        # Check for friendly greeting
        has_greeting = any(word in message for word in ["hello", "hi", "hey", "greetings", "welcome"])
        has_cerebrum = "cerebrum" in message
        
        if has_greeting or has_cerebrum:
            log_pass(test_name, f"Response: {data.get('message', '')[:100]}...")
            results["agent_chat"]["passed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, "No greeting found", data)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "No greeting"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["agent_chat"]["failed"] += 1
        results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

def test_agent_chat_office_building():
    """Test 2: Agent Chat - Office building 5000 sq ft"""
    test_name = "Agent Chat: Office building 5000 sq ft"
    try:
        resp = requests.post(f"{AGENT_URL}/execute", json={
            "task": "Calculate cost for office building 5000 sq ft",
            "context": {},
            "use_memory": True
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("message", "").lower()
        layer = data.get("layer", "").lower()
        
        # Should suggest office-low/high or be in economics layer
        has_office = "office" in message
        has_suggestion = any(term in message for term in ["office-low", "office-high", "suggest", "estimate"])
        is_economics = layer == "economics"
        
        if has_office and (has_suggestion or is_economics):
            log_pass(test_name, f"Layer: {layer}, Response: {data.get('message', '')[:100]}...")
            results["agent_chat"]["passed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, f"Expected office suggestion, got layer={layer}", data)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "No office suggestion"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["agent_chat"]["failed"] += 1
        results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

def test_agent_chat_warehouse():
    """Test 3: Agent Chat - Warehouse 10000 sq ft should calculate $950,000"""
    test_name = "Agent Chat: Warehouse 10000 sq ft"
    try:
        resp = requests.post(f"{AGENT_URL}/execute", json={
            "task": "Calculate cost for warehouse 10000 sq ft",
            "context": {},
            "use_memory": True
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("message", "").lower()
        
        # Check for cost calculation
        has_cost = any(term in message for term in ["$", "cost", "price", "estimate"])
        has_warehouse = "warehouse" in message
        
        # Look for a number near 950,000 or 950
        import re
        numbers = re.findall(r'[\d,]+', data.get("message", ""))
        has_estimate = any("950" in n or "1,000,000" in n or "1000000" in n for n in numbers)
        
        if has_cost and has_warehouse:
            log_pass(test_name, f"Has cost info: {has_estimate}, Response: {data.get('message', '')[:100]}...")
            results["agent_chat"]["passed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, f"Missing cost or warehouse info", data)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "Missing info"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["agent_chat"]["failed"] += 1
        results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

def test_agent_chat_office_low():
    """Test 4: Agent Chat - Office-low 3000 sq ft should calculate $675,000"""
    test_name = "Agent Chat: Office-low 3000 sq ft"
    try:
        resp = requests.post(f"{AGENT_URL}/execute", json={
            "task": "Calculate cost for office-low 3000 sq ft",
            "context": {},
            "use_memory": True
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("message", "")
        message_lower = message.lower()
        
        # Check for cost calculation
        has_cost = any(term in message_lower for term in ["$", "cost", "price", "estimate"])
        has_office = "office" in message_lower
        
        # Look for numbers near 675,000
        import re
        numbers = re.findall(r'[\d,]+', message)
        has_estimate = any("675" in n or "700,000" in n for n in numbers)
        
        if has_cost and has_office:
            log_pass(test_name, f"Has cost: {has_estimate}, Response: {message[:100]}...")
            results["agent_chat"]["passed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, f"Missing cost or office info", data)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "Missing info"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["agent_chat"]["failed"] += 1
        results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

def test_agent_chat_what_is_cerebrum():
    """Test 5: Agent Chat - What is Cerebrum should search memory"""
    test_name = "Agent Chat: What is Cerebrum"
    try:
        resp = requests.post(f"{AGENT_URL}/execute", json={
            "task": "What is Cerebrum",
            "context": {},
            "use_memory": True
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("message", "").lower()
        
        # Should mention Cerebrum and construction/AI
        has_cerebrum = "cerebrum" in message
        has_construction = "construction" in message
        has_ai = "ai" in message or "intelligence" in message or "assistant" in message
        
        if has_cerebrum and (has_construction or has_ai):
            log_pass(test_name, f"Response: {data.get('message', '')[:100]}...")
            results["agent_chat"]["passed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, f"Missing Cerebrum/Construction/AI info", data)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "Missing info"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["agent_chat"]["failed"] += 1
        results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

def test_agent_chat_capabilities():
    """Test 6: Agent Chat - What can you do should list capabilities"""
    test_name = "Agent Chat: What can you do"
    try:
        resp = requests.post(f"{AGENT_URL}/execute", json={
            "task": "What can you do",
            "context": {},
            "use_memory": True
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("message", "").lower()
        
        # Should list capabilities
        has_capabilities = any(term in message for term in [
            "help", "cost", "estimate", "document", "code", "bim", "construction"
        ])
        
        if has_capabilities:
            log_pass(test_name, f"Response: {data.get('message', '')[:100]}...")
            results["agent_chat"]["passed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, f"No capabilities listed", data)
            results["agent_chat"]["failed"] += 1
            results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "No capabilities"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["agent_chat"]["failed"] += 1
        results["agent_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

# ==================== NORMAL CHAT TESTS ====================

def test_normal_chat_hello():
    """Test 1: Normal Chat - Hello greeting"""
    test_name = "Normal Chat: Hello"
    try:
        resp = requests.post(f"{CHAT_URL}/completions", json={
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["normal_chat"]["failed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("choices", [{}])[0].get("message", {}).get("content", "").lower()
        
        # Check for greeting
        has_greeting = any(word in message for word in ["hello", "hi", "hey", "greetings", "welcome"])
        has_cerebrum = "cerebrum" in message
        
        if has_greeting or has_cerebrum:
            log_pass(test_name, f"Response: {message[:100]}...")
            results["normal_chat"]["passed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, "No greeting found", data)
            results["normal_chat"]["failed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "No greeting"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["normal_chat"]["failed"] += 1
        results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

def test_normal_chat_concrete():
    """Test 2: Normal Chat - Calculate 50 cubic meters of concrete"""
    test_name = "Normal Chat: 50 cubic meters concrete"
    try:
        resp = requests.post(f"{CHAT_URL}/completions", json={
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Calculate 50 cubic meters of concrete"}],
            "temperature": 0.7
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["normal_chat"]["failed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        message_lower = message.lower()
        
        # Should give cost info, not formula error
        has_cost = any(term in message_lower for term in ["$", "cost", "price", "estimate"])
        has_concrete = "concrete" in message_lower
        has_formula_error = "formula" in message_lower and "error" in message_lower
        
        if has_cost and has_concrete and not has_formula_error:
            log_pass(test_name, f"Response: {message[:100]}...")
            results["normal_chat"]["passed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, f"Formula error or missing info", data)
            results["normal_chat"]["failed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "Formula error"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["normal_chat"]["failed"] += 1
        results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

def test_normal_chat_steel_beams():
    """Test 3: Normal Chat - What is the cost of steel beams"""
    test_name = "Normal Chat: Cost of steel beams"
    try:
        resp = requests.post(f"{CHAT_URL}/completions", json={
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "What is the cost of steel beams"}],
            "temperature": 0.7
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["normal_chat"]["failed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        message_lower = message.lower()
        
        # Should search RSMeans or give cost info
        has_cost = any(term in message_lower for term in ["$", "cost", "price", "rsmeans"])
        has_steel = "steel" in message_lower
        
        if has_cost or has_steel:
            log_pass(test_name, f"Response: {message[:100]}...")
            results["normal_chat"]["passed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, f"Missing steel/cost info", data)
            results["normal_chat"]["failed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "Missing info"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["normal_chat"]["failed"] += 1
        results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

def test_normal_chat_office_estimate():
    """Test 4: Normal Chat - Estimate office building 5000 sq ft"""
    test_name = "Normal Chat: Estimate office 5000 sq ft"
    try:
        resp = requests.post(f"{CHAT_URL}/completions", json={
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "Estimate office building 5000 sq ft"}],
            "temperature": 0.7
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["normal_chat"]["failed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        message_lower = message.lower()
        
        # Should give cost estimate
        has_cost = any(term in message_lower for term in ["$", "cost", "price", "estimate"])
        has_office = "office" in message_lower
        
        if has_cost and has_office:
            log_pass(test_name, f"Response: {message[:100]}...")
            results["normal_chat"]["passed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, f"Missing cost or office info", data)
            results["normal_chat"]["failed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "Missing info"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["normal_chat"]["failed"] += 1
        results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

def test_normal_chat_capabilities():
    """Test 5: Normal Chat - What can you do should list capabilities"""
    test_name = "Normal Chat: What can you do"
    try:
        resp = requests.post(f"{CHAT_URL}/completions", json={
            "model": "cerebrum-default",
            "messages": [{"role": "user", "content": "What can you do"}],
            "temperature": 0.7
        }, timeout=30)
        
        if resp.status_code != 200:
            log_fail(test_name, f"HTTP {resp.status_code}", resp.text)
            results["normal_chat"]["failed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": f"HTTP {resp.status_code}"})
            return False
            
        data = resp.json()
        message = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        message_lower = message.lower()
        
        # Should list capabilities
        has_capabilities = any(term in message_lower for term in [
            "help", "cost", "estimate", "document", "code", "bim", "construction"
        ])
        
        if has_capabilities:
            log_pass(test_name, f"Response: {message[:100]}...")
            results["normal_chat"]["passed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "passed"})
            return True
        else:
            log_fail(test_name, f"No capabilities listed", data)
            results["normal_chat"]["failed"] += 1
            results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": "No capabilities"})
            return False
    except Exception as e:
        log_fail(test_name, str(e))
        results["normal_chat"]["failed"] += 1
        results["normal_chat"]["tests"].append({"name": test_name, "status": "failed", "error": str(e)})
        return False

def run_all_tests():
    """Run all tests and print summary"""
    print("\n" + "="*70)
    print(f"{Colors.BLUE}CEREBRUM COMPREHENSIVE CHAT TESTING{Colors.END}")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print("="*70 + "\n")
    
    # Agent Chat Tests
    print(f"\n{Colors.YELLOW}AGENT CHAT TESTS (/api/v1/agent/v2/execute){Colors.END}")
    print("-"*70)
    test_agent_chat_hello()
    test_agent_chat_office_building()
    test_agent_chat_warehouse()
    test_agent_chat_office_low()
    test_agent_chat_what_is_cerebrum()
    test_agent_chat_capabilities()
    
    # Normal Chat Tests
    print(f"\n{Colors.YELLOW}NORMAL CHAT TESTS (/api/v1/chat/completions){Colors.END}")
    print("-"*70)
    test_normal_chat_hello()
    test_normal_chat_concrete()
    test_normal_chat_steel_beams()
    test_normal_chat_office_estimate()
    test_normal_chat_capabilities()
    
    # Summary
    print("\n" + "="*70)
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.END}")
    print("="*70)
    
    agent_total = results["agent_chat"]["passed"] + results["agent_chat"]["failed"]
    agent_pass_rate = (results["agent_chat"]["passed"] / agent_total * 100) if agent_total > 0 else 0
    
    normal_total = results["normal_chat"]["passed"] + results["normal_chat"]["failed"]
    normal_pass_rate = (results["normal_chat"]["passed"] / normal_total * 100) if normal_total > 0 else 0
    
    total_passed = results["agent_chat"]["passed"] + results["normal_chat"]["passed"]
    total_failed = results["agent_chat"]["failed"] + results["normal_chat"]["failed"]
    total_tests = total_passed + total_failed
    overall_pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nAgent Chat:  {results['agent_chat']['passed']}/{agent_total} passed ({agent_pass_rate:.1f}%)")
    print(f"Normal Chat: {results['normal_chat']['passed']}/{normal_total} passed ({normal_pass_rate:.1f}%)")
    print(f"\n{Colors.GREEN if overall_pass_rate == 100 else Colors.YELLOW if overall_pass_rate >= 70 else Colors.RED}Overall:     {total_passed}/{total_tests} passed ({overall_pass_rate:.1f}%){Colors.END}")
    
    # Failed tests details
    if total_failed > 0:
        print(f"\n{Colors.RED}FAILED TESTS:{Colors.END}")
        for test in results["agent_chat"]["tests"]:
            if test["status"] == "failed":
                print(f"  - [Agent] {test['name']}: {test.get('error', 'Unknown')}")
        for test in results["normal_chat"]["tests"]:
            if test["status"] == "failed":
                print(f"  - [Normal] {test['name']}: {test.get('error', 'Unknown')}")
    
    print("\n" + "="*70)
    
    return overall_pass_rate == 100

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
