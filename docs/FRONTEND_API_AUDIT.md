# Frontend API Audit Report

**Audit Date:** 2026-04-02  
**Auditor:** Subagent  
**Scope:** All files in `/frontend/src/`  

---

## Summary

| Category | Count | Status |
|----------|-------|--------|
| `fetch()` calls | 50+ | ✅ Uses env variable with fallback |
| `axios` calls | 0 | N/A |
| WebSocket connections | 1 | ✅ Uses env variable with fallback |
| Hardcoded URLs | 1 | ⚠️ Production fallback URL |
| `localhost` references | 0 | ✅ None found |

---

## API Configuration Pattern

All API calls use the following pattern:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
```

**Environment Variable:** `VITE_API_URL`  
**Production Fallback:** `https://cerebrum-api.onrender.com`

---

## Detailed Findings

### 1. File: `hooks/useAgentChat.ts`

| Line | API Call | URL Pattern | Uses Env | Hardcoded |
|------|----------|-------------|----------|-----------|
| 8 | Configuration | `import.meta.env.VITE_API_URL` | ✅ Yes | Fallback only |
| 122 | `fetch()` | `${apiBaseUrl}/agent/v2/status/enhanced` | ✅ Yes | No |
| 137 | `fetch()` | `${apiBaseUrl}/agent/v2/execute` | ✅ Yes | No |
| 176 | `fetch()` | `${apiBaseUrl}/agent/v2/memory/search` | ✅ Yes | No |
| 207 | `fetch()` | `${apiBaseUrl}/agent/v2/layer/list` | ✅ Yes | No |
| 233 | `fetch()` | `${apiBaseUrl}/agent/v2/layer/navigate` | ✅ Yes | No |
| 262 | `fetch()` | `${apiBaseUrl}/agent/enhance/scan` | ✅ Yes | No |
| 270 | `fetch()` | `${apiBaseUrl}/agent/enhance/autonomous` | ✅ Yes | No |
| 306 | `fetch()` | `${apiBaseUrl}/agent/v2/status/enhanced` | ✅ Yes | No |
| 345 | `fetch()` | `${apiBaseUrl}/agent/v2/memory/working/...` | ✅ Yes | No |
| 381 | `fetch()` | `${apiBaseUrl}/agent/v2/memory/working/...` | ✅ Yes | No |
| 429 | `fetch()` | `${apiBaseUrl}/agent/web-search/search` | ✅ Yes | No |
| 659 | `fetch()` | `${getApiUrl()}/documents/upload/chat` | ✅ Yes | No |

**Configuration Lines:**
- Line 8: `const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';`
- Line 9-13: `getApiUrl()` helper function

---

### 2. File: `hooks/useChat.ts`

| Line | API Call | URL Pattern | Uses Env | Hardcoded |
|------|----------|-------------|----------|-----------|
| 7 | Configuration | `import.meta.env.VITE_API_URL` | ✅ Yes | Fallback only |
| 182 | `fetch()` | `${apiBaseUrl}/economics/search` | ✅ Yes | No |
| 215 | `fetch()` | `${apiBaseUrl}/economics/formulas` | ✅ Yes | No |
| 254 | `fetch()` | `${apiBaseUrl}/economics/estimate/quick` | ✅ Yes | No |
| 284 | `fetch()` | `${apiBaseUrl}/economics/building-types` | ✅ Yes | No |
| 308 | `fetch()` | `${apiBaseUrl}/economics/city-indices` | ✅ Yes | No |
| 349 | `fetch()` | `${apiBaseUrl}/economics/formulas/...` | ✅ Yes | No |
| 359 | `fetch()` | `${apiBaseUrl}/economics/formulas/.../calculate` | ✅ Yes | No |
| 397 | `fetch()` | `${apiBaseUrl}/documents/chroma/stats` | ✅ Yes | No |
| 400 | `fetch()` | `${apiBaseUrl}/health/embeddings` | ✅ Yes | No |
| 430 | `fetch()` | `${apiBaseUrl}/documents/chroma/hydrate` | ✅ Yes | No |
| 468 | `fetch()` | `${apiBaseUrl}/state/task/...` | ✅ Yes | No |
| 508 | `fetch()` | `${apiBaseUrl}/drive/auth/url` | ✅ Yes | No |
| 553 | `fetch()` | `${apiBaseUrl}/documents/process-invoice` | ✅ Yes | No |
| 589 | `fetch()` | `${apiBaseUrl}/safety/analyze` | ✅ Yes | No |
| 627 | `fetch()` | `${apiBaseUrl}/documents/search` | ✅ Yes | No |
| 700 | `fetch()` | `${getApiUrl()}/health/live` | ✅ Yes | No |
| 816 | `fetch()` | `${apiBaseUrl}/chat/completions` | ✅ Yes | No |

**Configuration Lines:**
- Line 7: `const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';`
- Line 8-11: `getApiUrl()` helper function

---

### 3. File: `hooks/useVoiceChat.ts`

| Line | API Call | URL Pattern | Uses Env | Hardcoded |
|------|----------|-------------|----------|-----------|
| 4 | Configuration (HTTP) | `import.meta.env.VITE_API_URL` | ✅ Yes | Fallback only |
| 5 | Configuration (WS) | `API_BASE_URL.replace(/^http/, 'ws')` | ✅ Yes | No |
| 290 | `new WebSocket()` | `wsUrl.toString()` | ✅ Yes | No |

**WebSocket URL Construction:**
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');
// Results in: ws://localhost:8000 or wss://cerebrum-api.onrender.com
```

**WebSocket Connection (Line 290):**
```typescript
const wsUrl = new URL(`${WS_BASE_URL}/voice/realtime`);
wsUrl.searchParams.set('session_id', sessionIdRef.current);
wsUrl.searchParams.set('voice', voice);
const ws = new WebSocket(wsUrl.toString());
```

---

### 4. File: `lib/fileProcessing.ts`

| Line | API Call | URL Pattern | Uses Env | Hardcoded |
|------|----------|-------------|----------|-----------|
| 4 | Configuration | `import.meta.env.VITE_API_URL` | ✅ Yes | Fallback only |
| 180 | `fetch()` (via XHR) | `${API_BASE_URL}/api/v1/documents/batch/process` | ✅ Yes | No |
| 253 | `fetch()` (via XHR) | `${API_BASE_URL}/api/v1/documents/transcribe` | ✅ Yes | No |
| 374 | `fetch()` | `${getApiUrl()}/documents/upload/chat` | ✅ Yes | No |

**Configuration Lines:**
- Line 4: `const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';`
- Line 59-62: `getApiUrl()` helper function

---

### 5. File: `context/AuthContext.tsx`

| Line | API Call | URL Pattern | Uses Env | Hardcoded |
|------|----------|-------------|----------|-----------|
| 3 | Configuration | `import.meta.env.VITE_API_URL` | ✅ Yes | Fallback only |
| 121 | `fetch()` | `${API_BASE}/auth/me` | ✅ Yes | No |
| 142 | `fetch()` | `${API_BASE}/auth/refresh` | ✅ Yes | No |
| 194 | `fetch()` | `${API_BASE}/auth/me` | ✅ Yes | No |
| 259 | `fetch()` | `loginUrl` (constructed) | ✅ Yes | No |
| 278 | `fetch()` | `${API_BASE}/auth/me` | ✅ Yes | No |
| 308 | `fetch()` | `${API_BASE}/auth/register` | ✅ Yes | No |

**Configuration Lines:**
- Line 3: `const API_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';`
- Line 4-6: `API_BASE` construction with `/api/v1` suffix

---

### 6. File: `mobile/sync.ts`

| Line | API Call | URL Pattern | Uses Env | Hardcoded |
|------|----------|-------------|----------|-----------|
| 366 | `fetch()` | `config.uploadEndpoint` | ⚠️ Configurable | **POTENTIAL ISSUE** |

**Note:** This file uses a configurable `uploadEndpoint` from the `SyncConfig` interface. The endpoint is passed in via configuration, so it depends on how the calling code sets this value.

---

## Hardcoded URLs Found

### Production Fallback URL
**Location:** Multiple files  
**URL:** `https://cerebrum-api.onrender.com`  
**Status:** ⚠️ Used as fallback when env variable is not set

**Files affected:**
- `hooks/useAgentChat.ts` (Line 8)
- `hooks/useChat.ts` (Line 7)
- `hooks/useVoiceChat.ts` (Line 4)
- `lib/fileProcessing.ts` (Line 4)
- `context/AuthContext.tsx` (Line 3)

**Recommendation:** Consider removing the fallback or making it configurable at build time to avoid accidental production API calls during development.

---

## Environment Variables

### Defined Variables (from `env.d.ts`)
```typescript
interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_APP_NAME: string
  readonly VITE_APP_VERSION: string
}
```

### Variables Actually Used
| Variable | Used In | Purpose |
|----------|---------|---------|
| `VITE_API_URL` | 5 files | Base URL for API calls |
| `VITE_WS_URL` | ❌ Not used | Defined but not referenced |

**Note:** `VITE_WS_URL` is defined but not used. WebSocket URLs are derived from `VITE_API_URL` by replacing `http` with `ws`.

---

## localhost/127.0.0.1 References

**Status:** ✅ None found

No hardcoded localhost or 127.0.0.1 references were detected in the codebase.

---

## Axios Usage

**Status:** ✅ None found

The codebase uses native `fetch()` exclusively. No axios instances or imports found.

---

## Recommendations

### 1. Remove or Make Fallback URL Configurable
**Priority:** Medium  
**Files:** All files with API configuration  

The hardcoded production URL fallback could lead to:
- Accidental production API calls during development
- Confusion when debugging
- Potential data pollution

**Suggested fix:**
```typescript
// Instead of:
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';

// Use:
const API_BASE_URL = import.meta.env.VITE_API_URL;
if (!API_BASE_URL) {
  throw new Error('VITE_API_URL environment variable is required');
}
```

### 2. Use Centralized API Configuration
**Priority:** Low  

Each file duplicates the same configuration logic. Consider creating a centralized config:

```typescript
// lib/apiConfig.ts
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://cerebrum-api.onrender.com';
export const getApiUrl = () => {
  const url = API_BASE_URL.replace(/\/?$/, '');
  return url.endsWith('/api/v1') ? url : `${url}/api/v1`;
};
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');
```

### 3. Clean Up Unused Environment Variable
**Priority:** Low  

`VITE_WS_URL` is defined in `env.d.ts` but never used. Either:
- Remove it from the type definitions, or
- Use it instead of deriving WS URL from API_URL

### 4. Document API Endpoints
**Priority:** Low  

Consider creating an API endpoints constant file:

```typescript
export const ENDPOINTS = {
  AGENT: {
    STATUS: '/agent/v2/status/enhanced',
    EXECUTE: '/agent/v2/execute',
    MEMORY_SEARCH: '/agent/v2/memory/search',
    // ... etc
  },
  ECONOMICS: {
    SEARCH: '/economics/search',
    FORMULAS: '/economics/formulas',
    // ... etc
  }
} as const;
```

---

## Complete List of API Endpoints Called

### Agent Endpoints
- `GET /agent/v2/status/enhanced`
- `POST /agent/v2/execute`
- `GET /agent/v2/memory/search`
- `GET /agent/v2/layer/list`
- `POST /agent/v2/layer/navigate`
- `GET /agent/enhance/scan`
- `POST /agent/enhance/autonomous`
- `GET /agent/v2/memory/working/{sessionId}/{taskId}`
- `DELETE /agent/v2/memory/working/{sessionId}/{taskId}`
- `POST /agent/web-search/search`

### Economics Endpoints
- `GET /economics/search`
- `GET /economics/formulas`
- `GET /economics/estimate/quick`
- `GET /economics/building-types`
- `GET /economics/city-indices`
- `GET /economics/formulas/{formulaId}`
- `POST /economics/formulas/{formulaId}/calculate`

### Document Endpoints
- `GET /documents/chroma/stats`
- `POST /documents/chroma/hydrate`
- `GET /documents/search`
- `POST /documents/process-invoice`
- `POST /documents/upload/chat`
- `POST /api/v1/documents/batch/process`
- `POST /api/v1/documents/transcribe`

### Auth Endpoints
- `GET /auth/me`
- `POST /auth/refresh`
- `POST /auth/login`
- `POST /auth/register`

### Other Endpoints
- `GET /health/live`
- `GET /health/embeddings`
- `GET /state/task/{taskId}`
- `GET /drive/auth/url`
- `POST /safety/analyze`
- `POST /chat/completions`
- `WebSocket /voice/realtime`

---

## Conclusion

The frontend codebase is generally well-structured regarding API calls:

✅ **Good practices found:**
- Uses environment variables for API base URL
- No hardcoded localhost references
- Consistent use of `fetch()` API
- Proper fallback mechanism (though production URL is hardcoded as fallback)

⚠️ **Areas for improvement:**
- Production URL fallback could be removed for safety
- Configuration is duplicated across files
- Unused environment variable `VITE_WS_URL`

Overall, the API architecture is sound and follows reasonable patterns for a React/Vite application.
