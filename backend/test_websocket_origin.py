#!/usr/bin/env python3
"""
WebSocket Connection Test with Origin Header
Tests that the WebSocket endpoint accepts connections properly.
"""

import asyncio
import json
import sys

# Test with websockets library
try:
    import websockets
except ImportError:
    print("Installing websockets library...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets", "-q"])
    import websockets


WS_URL = "ws://localhost:8000/api/v1/agent/v2/ws"


async def test_with_origin(origin: str = None):
    """Test WebSocket connection with specific origin header."""
    extra_headers = {}
    if origin:
        extra_headers["Origin"] = origin
        print(f"\n=== Testing with Origin: {origin} ===")
    else:
        print(f"\n=== Testing without Origin header ===")
    
    try:
        async with websockets.connect(WS_URL, extra_headers=extra_headers) as ws:
            # Receive welcome message
            welcome = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(welcome)
            print(f"✅ Connected! Message type: {data.get('type')}")
            print(f"   Client ID: {data.get('client_id')}")
            
            # Send ping
            await ws.send(json.dumps({"type": "ping"}))
            pong = await asyncio.wait_for(ws.recv(), timeout=5.0)
            pong_data = json.loads(pong)
            print(f"✅ Ping/Pong: {pong_data.get('type')}")
            
        print("✅ Connection closed gracefully")
        return True
        
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection rejected with status: {e.status_code}")
        if e.status_code == 403:
            print("   This is the 403 Forbidden error we're investigating!")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("WebSocket Origin Header Test")
    print(f"Endpoint: {WS_URL}")
    print("=" * 60)
    
    results = []
    
    # Test 1: No origin header (common for test scripts)
    results.append(("No Origin", await test_with_origin(None)))
    
    # Test 2: Localhost origin
    results.append(("http://localhost:3000", await test_with_origin("http://localhost:3000")))
    
    # Test 3: Localhost:8000 origin
    results.append(("http://localhost:8000", await test_with_origin("http://localhost:8000")))
    
    # Test 4: Invalid origin (should fail in production, but pass in DEBUG mode)
    results.append(("http://evil.com", await test_with_origin("http://evil.com")))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    return passed == len(results)


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted")
        sys.exit(1)
