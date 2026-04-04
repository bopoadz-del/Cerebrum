# WebSocket 403 Forbidden Fix Summary

## Problem
WebSocket connections to `ws://localhost:8000/api/v1/agent/v2/ws` were returning **403 Forbidden** errors.

## Root Causes Identified

### 1. Empty Origin Header Rejection
The `_validate_origin()` function was rejecting connections from clients that don't send an Origin header (common for test scripts and non-browser clients).

**Before:**
```python
def _validate_origin(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin", "")
    # ... validation logic that didn't handle empty origin
    return False  # Would return False for empty origin
```

**After:**
```python
def _validate_origin(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin", "")
    
    # Allow non-browser clients that don't send Origin header
    if not origin:
        return True
    # ... rest of validation
```

### 2. Missing WebSocket Protocols
The allowed origins list only included `http://` and `https://` protocols, but WebSocket connections use `ws://` and `wss://`.

**Added:**
```python
allowed_origins.extend([
    # WebSocket origins (ws:// and wss://)
    "ws://localhost",
    "ws://localhost:3000",
    # ... etc
    "wss://localhost",
    "wss://localhost:3000",
    # ... etc
])
```

### 3. Invalid close() Before accept()
The code was calling `await websocket.close(code=1008, reason="Invalid origin")` before the connection was accepted. This is invalid - you cannot close a WebSocket before accepting it.

**Before:**
```python
if not _validate_origin(websocket):
    await websocket.close(code=1008, reason="Invalid origin")  # ❌ Invalid!
    return
```

**After:**
```python
if not _validate_origin(websocket):
    # Cannot close before accept - just return to reject the connection
    # The HTTP upgrade will fail with 403
    return  # ✅ Correct way to reject
```

## Changes Made

### File: `backend/app/agent/websocket.py`

1. **Updated `_validate_origin()` function:**
   - Added check for empty Origin header (allows non-browser clients)
   - Added support for `ws://` and `wss://` protocols
   - Added support for `file://` origins (local file clients)
   - Changed `allowed_origins.extend()` to use `list()` to avoid modifying original

2. **Fixed `agent_websocket()` function:**
   - Removed invalid `websocket.close()` call before `accept()`
   - Added comment explaining the rejection mechanism

## Testing

Created unit tests in `backend/test_websocket_unit.py` that verify:
- ✅ DEBUG mode allows all origins
- ✅ Empty Origin header is allowed (non-browser clients)
- ✅ Localhost origins (http/https/ws/wss) are allowed
- ✅ CORS origins from settings are allowed
- ✅ file:// origins are allowed
- ✅ Invalid origins are properly rejected

Run tests:
```bash
cd backend
python3 test_websocket_unit.py
```

## WebSocket Endpoint

The WebSocket endpoint is available at:
```
ws://localhost:8000/api/v1/agent/v2/ws
```

Router configuration:
- Main app: `/api/v1`
- Agent router: `/agent/v2`
- WebSocket route: `/ws`
- Full path: `/api/v1/agent/v2/ws`

## Additional Notes

- The `DEBUG=true` setting in `.env` will allow all origins
- In production (`DEBUG=false`), only configured CORS origins + localhost are allowed
- Non-browser clients that don't send Origin headers are now properly supported
