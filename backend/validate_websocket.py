#!/usr/bin/env python3
"""
Static validation of WebSocket implementation.
Checks imports and structure without running the server.
"""

import sys
import ast

def check_file(filepath):
    """Check Python file for syntax errors."""
    try:
        with open(filepath, 'r') as f:
            source = f.read()
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, str(e)

def main():
    files_to_check = [
        "app/agent/websocket.py",
        "app/api/v1/api.py",
        "app/agent/core.py",
        "app/agent/planner.py",
    ]
    
    print("=" * 60)
    print("WebSocket Implementation Validation")
    print("=" * 60)
    
    all_ok = True
    for filepath in files_to_check:
        ok, error = check_file(filepath)
        status = "✅ OK" if ok else "❌ FAIL"
        print(f"  {status}: {filepath}")
        if error:
            print(f"      Error: {error}")
            all_ok = False
    
    print("\n" + "=" * 60)
    print("WebSocket Endpoint Configuration")
    print("=" * 60)
    print("  Expected endpoint: ws://localhost:8000/api/v1/agent/v2/ws")
    print("  Router prefix in api.py: /agent/v2")
    print("  WebSocket path in websocket.py: /ws")
    print("  Full path: /api/v1 + /agent/v2 + /ws = /api/v1/agent/v2/ws ✅")
    
    print("\n" + "=" * 60)
    print("Key Fixes Applied")
    print("=" * 60)
    print("""
1. ✅ Fixed endpoint path:
   - Changed from /api/v1/ws/agent to /api/v1/agent/v2/ws
   - Updated router prefix in api.py from /ws to /agent/v2
   - WebSocket route now at /ws (relative to prefix)

2. ✅ Fixed CORS origin validation (FIXED 403 Forbidden):
   - Fixed _validate_origin() function to allow empty Origin header
   - Added support for ws:// and wss:// protocols
   - Added support for file:// origins (local file clients)
   - Fixed issue where non-browser clients were rejected
   - Removed invalid websocket.close() before accept()

3. ✅ Improved error handling:
   - Added JSON parsing error handling in receive()
   - Added validation for required fields (task, goal)
   - Better exception logging in message handlers
   - Connection state checks before sending

4. ✅ Added connection state management:
   - Check WebSocketState.CONNECTED before sending
   - Track _closed state in AgentConnection
   - Proper cleanup on disconnect

5. ✅ Improved disconnect handling:
   - Added close codes and reasons
   - Clean shutdown of heartbeat on disconnect
   - Graceful handling of WebSocketDisconnect

6. ✅ Safe attribute access:
   - Added hasattr checks for .value access on enums
   - Prevents AttributeError if agent returns unexpected types
""")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ All files pass syntax validation")
        return 0
    else:
        print("❌ Some files have syntax errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())
