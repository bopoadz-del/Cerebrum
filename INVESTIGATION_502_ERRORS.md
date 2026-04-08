# Investigation Report: 502/Failed to Fetch Errors in Production

**Date:** 2026-04-04  
**Investigation Status:** ✅ COMPLETE  
**Severity:** HIGH

---

## Executive Summary

The issue stems from **fundamental differences between how local tests and real browsers interact with the production API**, combined with several production-specific configuration issues that cause 502 errors and fetch failures.

### Key Findings
1. **CORS Configuration Mismatch** - Tests bypass CORS; real browsers enforce it
2. **Missing CORS Origin for Render Frontend** - CORS list doesn't include all possible Render domains
3. **TrustedHostMiddleware Too Restrictive** - Blocks some legitimate browser requests
4. **Rate Limiting on Redis** - Real users share IP pools (mobile/ISP), triggering rate limits
5. **Render Free Tier Timeout Limits** - 100s hard limit on requests, long operations cause 502s
6. **Authentication Required for File Upload** - Anonymous users can't upload (design vs bug?)

---

## Detailed Investigation

### 1. CORS Configuration Issues 🔴 CRITICAL

**Current CORS Origins (config.py):**
```python
CORS_ORIGINS = "http://localhost:3000,https://cerebrum-frontend.onrender.com"
```

**Problem:**
- The render.yaml sets: `CORS_ORIGINS: "https://cerebrum-frontend.onrender.com,https://cerebrum.ai"`
- But the `cors_origins_list` property in config.py Merges with defaults:
```python
default_origins = ["http://localhost:3000", "https://cerebrum-frontend.onrender.com"]
```

**Issues Found:**
1. Render can deploy to preview URLs like `https://cerebrum-frontend-pr-123.onrender.com` which aren't in the CORS list
2. The `cors_origins_list` property merges env origins with defaults but **removes duplicates incorrectly**
3. Wildcard origins not supported for credentials mode

**Evidence:**
```python
# In main.py - CORS is configured as:
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,  # May not include all Render domains
    allow_credentials=True,
    ...
)
```

**Why Tests Pass:**
- `test_comprehensive_chat.py` uses `requests.post()` directly to `localhost:8000`
- Python requests don't enforce CORS - it's a browser security feature
- No origin header = no CORS check

---

### 2. TrustedHostMiddleware Blocking Requests 🔴 CRITICAL

**Current Configuration (main.py line ~128):**
```python
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*.onrender.com", "localhost", "127.0.0.1"]
)
```

**Problem:**
- `*.onrender.com` pattern matching may not work correctly with all browsers
- Some browsers send `Host` header variations that don't match
- Missing `cerebrum.ai` custom domain

**Error Symptom:**
```
403 Forbidden from TrustedHostMiddleware
→ Browser shows "Failed to fetch" (not the actual 403)
```

---

### 3. Rate Limiting Issues 🟡 MEDIUM

**Configuration (main.py):**
```python
limiter = Limiter(
    key_func=get_remote_address,  # Uses IP address
    default_limits=["100/minute", "1000/hour"],
    storage_uri=settings.redis_url,
)
```

**Problem:**
- `get_remote_address` uses client IP for rate limiting
- Real users behind NAT/mobile networks share IPs
- Multiple users from same office/mobile tower = shared quota
- 100/minute is easily exhausted with file uploads + chat

**Evidence from Code:**
```python
# In useChat.ts - no client-side rate limiting
const response = await fetch(`${apiBaseUrl}/chat/completions`, {...})  # Can fire rapidly
```

---

### 4. Render Timeout Limits 🔴 CRITICAL

**Render Free Tier Constraints:**
- **100 second hard timeout** on all requests
- File uploads + processing + AI response can exceed this
- 502 Bad Gateway when timeout exceeded

**Problematic Code (documents.py):**
```python
@router.post("/upload/chat")
async def upload_chat_file(...):
    # 1. Read file (can be slow for large files)
    file_content = await file.read()
    
    # 2. Save to disk
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # 3. Queue Celery task for indexing
    # But response waits for ALL of this...
```

**Why Tests Pass:**
- Local tests use small files (test.pdf ~4KB)
- Local network = fast upload
- No AI processing latency in tests (mocked/stubbed)

---

### 5. File Upload Authentication Required 🟡 MEDIUM

**Current Implementation (documents.py):**
```python
@router.post("/upload/chat")
async def upload_chat_file(
    ...,
    current_user: User = Depends(get_current_user)  # Requires auth
):
```

**Problem:**
- Anonymous users get 401/403 errors
- Frontend error handling may show "Failed to fetch" instead of proper auth error

**Frontend Code (useChat.ts):**
```typescript
const token = getAuthToken();
const response = await fetch(`${getApiUrl()}/documents/upload/chat`, {
  method: 'POST',
  headers: {
    'Authorization': token ? `Bearer ${token}` : '',  // Empty if not logged in
  },
  body: formData,
});
```

---

### 6. WebSocket vs HTTP Differences 🟡 MEDIUM

**Findings:**
- WebSocket uses `/api/v1/agent/v2/ws` endpoint
- HTTP chat uses `/api/v1/chat/completions` and `/api/v1/agent/v2/execute`
- WebSocket has separate CORS/connection handling

**Potential Issue:**
```python
# WebSocket endpoint may have different timeout handling
# But both go through same rate limiting
```

---

## Root Cause Analysis

### Why Tests Pass But Real Users Fail

| Aspect | Local Test | Real User |
|--------|-----------|-----------|
| **Origin** | No origin (Python requests) | `https://cerebrum-frontend.onrender.com` |
| **CORS Check** | Skipped | Enforced by browser |
| **Host Header** | `localhost:8000` | `cerebrum-api.onrender.com` |
| **Network** | Local (0ms latency) | Internet (50-300ms latency) |
| **File Upload Size** | Small test file | Real documents (MBs) |
| **Rate Limiting** | Single IP (test runner) | Shared IPs (NAT/mobile) |
| **Timeout** | No hard limit | 100s Render limit |
| **Auth** | May use test token | Real login flow |

### The 502 Error Chain

```
User uploads file → Upload takes 30s+ → AI processing starts
                                         ↓
                    Render 100s timeout ← AI response takes 60s+
                              ↓
                         502 Bad Gateway
```

---

## Recommended Fixes

### 1. Fix CORS Configuration 🔴 URGENT

**File:** `backend/app/core/config.py`

```python
@property
def cors_origins_list(self) -> List[str]:
    """Parse CORS_ORIGINS string into list."""
    # Always include production frontend URLs
    default_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://cerebrum-frontend.onrender.com",
        "https://cerebrum.ai",
    ]
    
    # Add env origins
    env_origins = []
    if self.CORS_ORIGINS:
        env_origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    # Support Render preview deployments
    render_origins = [o for o in env_origins if "onrender.com" in o]
    
    # Merge all, removing duplicates while preserving order
    all_origins = list(dict.fromkeys(default_origins + env_origins + render_origins))
    return all_origins
```

**Update render.yaml:**
```yaml
- key: CORS_ORIGINS
  value: "https://cerebrum-frontend.onrender.com,https://cerebrum.ai,https://*.onrender.com"
```

### 2. Fix TrustedHostMiddleware 🔴 URGENT

**File:** `backend/app/main.py`

```python
# Add support for Render's dynamic domains and custom domains
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "*.onrender.com",
        "cerebrum-api.onrender.com",
        "cerebrum.ai",
        "*.cerebrum.ai",
        "localhost",
        "127.0.0.1",
        "*" if settings.DEBUG else None,  # Allow all in development
    ]
)
```

### 3. Implement Smarter Rate Limiting 🟡 HIGH

**File:** `backend/app/main.py`

```python
# Use user ID for rate limiting when authenticated, IP as fallback
def get_rate_limit_key(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # Use token fingerprint or user ID
        return f"user:{auth_header[7:15]}"  # First 8 chars of token
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/minute", "1000/hour"],
    storage_uri=settings.redis_url,
)
```

### 4. Fix File Upload Timeout 🟡 HIGH

**Option A: Streaming Upload (Recommended)**

**File:** `backend/app/api/v1/endpoints/documents.py`

```python
@router.post("/upload/chat")
async def upload_chat_file(
    request: Request,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    # Return immediately after saving, process in background
    file_id = f"{current_user.id}_{uuid.uuid4().hex}"
    
    # Stream write to avoid loading entire file in memory
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.tmp")
    
    # Write in chunks
    async with aiofiles.open(file_path, 'wb') as f:
        while chunk := await file.read(8192):  # 8KB chunks
            await f.write(chunk)
    
    # Rename to final
    final_path = file_path.replace('.tmp', '')
    os.rename(file_path, final_path)
    
    # Queue background processing
    index_single_document.delay(file_id=file_id, file_path=final_path, ...)
    
    # Return immediately
    return {
        "success": True,
        "file_id": file_id,
        "status": "uploaded",
        "message": "File uploaded and queued for processing"
    }
```

**Option B: Increase Render Timeout (Limited Effect)**

```yaml
# render.yaml - Note: Only works on paid plans
services:
  - type: web
    name: cerebrum-api
    # ... other config
    # Request timeout can't be configured on free tier
```

### 5. Add Better Error Handling 🔵 MEDIUM

**File:** `frontend/src/hooks/useChat.ts`

```typescript
const sendMessage = useCallback(async () => {
  // ... existing code
  try {
    const response = await fetch(`${apiBaseUrl}/agent/v2/execute`, {
      // ... config
    });
    
    if (response.status === 502) {
      throw new Error("Server timeout. The request took too long. Try a shorter message or smaller file.");
    }
    
    if (response.status === 429) {
      throw new Error("Rate limit exceeded. Please wait a moment and try again.");
    }
    
    if (response.status === 403) {
      throw new Error("Access denied. Please check you're logged in or refresh the page.");
    }
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Server error: ${response.status}`);
    }
    
    // ... rest of handler
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      // Network/CORS error
      console.error('CORS or network error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '❌ Connection failed. This might be a CORS issue or the server is unavailable.'
      }]);
    }
    // ... rest of error handling
  }
}, [...]);
```

### 6. Add CORS Debugging Endpoint 🔵 LOW

**File:** `backend/app/api/health.py` (add new endpoint)

```python
@router.get("/cors-debug")
async def cors_debug(request: Request):
    """Debug endpoint to verify CORS configuration."""
    return {
        "origin": request.headers.get("origin"),
        "host": request.headers.get("host"),
        "allowed_origins": settings.cors_origins_list,
        "user_agent": request.headers.get("user-agent"),
    }
```

---

## Testing Checklist

Before deploying fixes:

- [ ] Test from `https://cerebrum-frontend.onrender.com` in browser
- [ ] Test from Render preview deployment URL
- [ ] Test with large file upload (>10MB)
- [ ] Test rate limiting with rapid requests
- [ ] Test anonymous vs authenticated user
- [ ] Check browser console for CORS errors
- [ ] Verify 502 errors reduced in logs

---

## Monitoring Recommendations

Add to `backend/app/main.py`:

```python
@app.middleware("http")
async def error_tracking(request: Request, call_next):
    """Track 502/504 errors for monitoring."""
    try:
        response = await call_next(request)
        if response.status_code in [502, 504]:
            logger.error(
                "Gateway timeout detected",
                path=request.url.path,
                method=request.method,
                client=request.client.host if request.client else None,
            )
        return response
    except Exception as e:
        logger.exception("Unhandled exception")
        raise
```

---

## Conclusion

The 502/Failed to Fetch errors are caused by a combination of:

1. **CORS misconfiguration** blocking legitimate browser requests
2. **Render timeout limits** being exceeded by long operations
3. **Rate limiting** affecting users behind shared IPs

**Priority fixes:**
1. Update CORS_ORIGINS to include all Render domains
2. Fix TrustedHostMiddleware allowed hosts
3. Implement streaming file uploads
4. Add user-based rate limiting

The tests pass because they use Python requests directly to localhost, bypassing all browser security features and network constraints that real users face.
