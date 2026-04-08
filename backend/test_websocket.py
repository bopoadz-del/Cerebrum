#!/usr/bin/env python3
"""
WebSocket Test Client for Cerebrum Agent
Tests connection, messaging, and error handling.
"""

import asyncio
import json
import sys
import websockets

# WebSocket endpoint
WS_URL = "ws://localhost:8000/api/v1/agent/v2/ws"


async def test_basic_connection():
    """Test basic WebSocket connection."""
    print("\n=== Test 1: Basic Connection ===")
    try:
        async with websockets.connect(WS_URL) as ws:
            # Receive welcome message
            welcome = await ws.recv()
            data = json.loads(welcome)
            print(f"✅ Connected! Welcome message: {data.get('type')}")
            print(f"   Client ID: {data.get('client_id')}")
            print(f"   Message: {data.get('message')}")
            
            # Send ping
            await ws.send(json.dumps({"type": "ping"}))
            pong = await asyncio.wait_for(ws.recv(), timeout=5.0)
            pong_data = json.loads(pong)
            print(f"✅ Ping/Pong works: {pong_data.get('type')}")
            
        print("✅ Connection closed gracefully")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_task_execution():
    """Test task execution via WebSocket."""
    print("\n=== Test 2: Task Execution ===")
    try:
        async with websockets.connect(WS_URL) as ws:
            # Receive welcome
            welcome = await ws.recv()
            print(f"   Received: {json.loads(welcome).get('type')}")
            
            # Send a simple task
            task_msg = {
                "type": "task",
                "task": "Hello, are you there?",
                "context": {"test": True}
            }
            await ws.send(json.dumps(task_msg))
            
            # Wait for task_started
            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            data = json.loads(response)
            print(f"✅ Task response: {data.get('type')}")
            
            if data.get('type') == 'task_started':
                # Wait for completion
                response = await asyncio.wait_for(ws.recv(), timeout=30.0)
                data = json.loads(response)
                print(f"✅ Task completed: {data.get('type')}")
                print(f"   Success: {data.get('success')}")
                print(f"   Message: {data.get('message', 'N/A')[:100]}...")
            
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_invalid_json():
    """Test handling of invalid JSON."""
    print("\n=== Test 3: Invalid JSON Handling ===")
    try:
        async with websockets.connect(WS_URL) as ws:
            # Receive welcome
            welcome = await ws.recv()
            print(f"   Received: {json.loads(welcome).get('type')}")
            
            # Send invalid JSON
            await ws.send("this is not valid json {{{")
            
            # Should receive error
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)
            
            if data.get('type') == 'error':
                print(f"✅ Error handled correctly: {data.get('message', 'N/A')[:80]}")
                return True
            else:
                print(f"❌ Expected error, got: {data.get('type')}")
                return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_missing_task_field():
    """Test task without required field."""
    print("\n=== Test 4: Missing Task Field ===")
    try:
        async with websockets.connect(WS_URL) as ws:
            # Receive welcome
            welcome = await ws.recv()
            print(f"   Received: {json.loads(welcome).get('type')}")
            
            # Send task without 'task' field
            await ws.send(json.dumps({"type": "task", "context": {}}))
            
            # Should receive error
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)
            
            if data.get('type') == 'error':
                print(f"✅ Validation works: {data.get('message')}")
                return True
            else:
                print(f"❌ Expected error, got: {data.get('type')}")
                return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_heartbeat():
    """Test heartbeat reception."""
    print("\n=== Test 5: Heartbeat Reception ===")
    try:
        async with websockets.connect(WS_URL) as ws:
            # Receive welcome
            welcome = await ws.recv()
            print(f"   Received: {json.loads(welcome).get('type')}")
            
            # Wait for heartbeat (sent every 30s, but we timeout after 5s for testing)
            # Just verify we can stay connected for a few seconds
            await asyncio.sleep(2)
            
            # Send ping to verify still connected
            await ws.send(json.dumps({"type": "ping"}))
            pong = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(pong)
            
            if data.get('type') == 'pong':
                print(f"✅ Connection stable after 2 seconds")
                return True
            else:
                print(f"❌ Unexpected response: {data.get('type')}")
                return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_unknown_message_type():
    """Test unknown message type handling."""
    print("\n=== Test 6: Unknown Message Type ===")
    try:
        async with websockets.connect(WS_URL) as ws:
            # Receive welcome
            welcome = await ws.recv()
            print(f"   Received: {json.loads(welcome).get('type')}")
            
            # Send unknown type
            await ws.send(json.dumps({"type": "unknown_type_xyz"}))
            
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)
            
            if data.get('type') == 'error' and 'unknown' in data.get('message', '').lower():
                print(f"✅ Unknown type handled: {data.get('message')}")
                return True
            else:
                print(f"❌ Expected unknown type error, got: {data}")
                return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Cerebrum WebSocket Test Suite")
    print(f"Endpoint: {WS_URL}")
    print("=" * 60)
    
    results = []
    
    # Run tests
    tests = [
        test_basic_connection,
        test_invalid_json,
        test_unknown_message_type,
        test_missing_task_field,
        test_heartbeat,
        test_task_execution,
    ]
    
    for test in tests:
        try:
            result = await test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append((test.__name__, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
