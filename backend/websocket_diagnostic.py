#!/usr/bin/env python3
"""
WebSocket Diagnostic Tool for Render Deployment
Run this on Render to check WebSocket availability
"""
import sys
sys.path.insert(0, '/app')

print("=" * 60)
print("WebSocket Diagnostic Report")
print("=" * 60)

# Check 1: websockets library
print("\n[1] Checking websockets library...")
try:
    import websockets
    print(f"    ✅ websockets installed: {websockets.__version__}")
except ImportError as e:
    print(f"    ❌ websockets not installed: {e}")

# Check 2: FastAPI WebSocket support
print("\n[2] Checking FastAPI WebSocket support...")
try:
    from fastapi import WebSocket
    print("    ✅ FastAPI WebSocket available")
except ImportError as e:
    print(f"    ❌ FastAPI WebSocket not available: {e}")

# Check 3: Import websocket router
print("\n[3] Checking websocket router import...")
try:
    from app.agent.websocket import websocket_router
    print(f"    ✅ websocket_router imported")
    print(f"    Routes: {websocket_router.routes}")
except Exception as e:
    print(f"    ❌ Failed to import websocket_router: {e}")
    import traceback
    traceback.print_exc()

# Check 4: Check api.py WEBSOCKET_AVAILABLE flag
print("\n[4] Checking WEBSOCKET_AVAILABLE flag in api.py...")
try:
    from app.api.v1.api import WEBSOCKET_AVAILABLE
    print(f"    WEBSOCKET_AVAILABLE = {WEBSOCKET_AVAILABLE}")
except Exception as e:
    print(f"    ❌ Failed to check: {e}")

# Check 5: Check all routes in main app
print("\n[5] Checking registered routes...")
try:
    from app.main import app
    ws_routes = [r for r in app.routes if 'WebSocket' in str(type(r))]
    if ws_routes:
        for r in ws_routes:
            print(f"    ✅ WebSocket route: {r.path}")
    else:
        print("    ❌ No WebSocket routes found")
except Exception as e:
    print(f"    ❌ Failed to check routes: {e}")

# Check 6: Environment check
print("\n[6] Environment variables...")
import os
relevant_vars = ['ENVIRONMENT', 'DEBUG', 'WEB_CONCURRENCY', 'PORT']
for var in relevant_vars:
    val = os.environ.get(var, '<not set>')
    print(f"    {var} = {val}")

print("\n" + "=" * 60)
print("End of Diagnostic Report")
print("=" * 60)
