# Cerebrum Backend API Audit Report

**Generated:** 2026-04-02  
**Scope:** `backend/app/` directory  
**Total Python Files:** 354

---

## Executive Summary

| Category | Count |
|----------|-------|
| Total API Routes | ~463 |
| HTTP Routers (APIRouter) | 50+ |
| WebSocket Endpoints | 3 |
| Files with External API Calls (httpx/requests) | ~40 |
| Hardcoded Localhost References | 30+ |

---

## 1. API Route Structure

### 1.1 Router Hierarchy

```
/api/v1/                          # Main API prefix
├── /auth/*                       # Authentication (auth.py)
├── /admin/*                      # Admin endpoints (admin.py)
├── /chat/*                       # Chat completions (chat.py)
├── /dejavu/*                     # Database introspection (dejavu.py)
├── /formulas/*                   # Economic formulas (formulas.py)
├── /sessions/*                   # Session management (sessions.py)
├── /connectors/*                 # External connectors (connectors.py)
├── /users/*                      # User management (stub_users.py)
├── /projects/*                   # Project management (stub_projects.py)
├── /registry/*                   # Component registry (stub_registry.py)
├── /coding/*                     # Code generation (stub_coding.py)
├── /quality/*                    # Quality inspections (stub_quality.py)
├── /bim/*                        # BIM operations (bim.py)
├── /economics/*                  # Economic calculations (economics.py)
├── /vdc/*                        # VDC operations (vdc.py)
├── /integrations/*               # Third-party integrations (integrations.py)
├── /warehouse/*                  # Data warehouse (warehouse.py)
├── /ml/*                         # ML operations (ml.py)
├── /edge/*                       # Edge computing (edge.py)
├── /enterprise/*                 # Enterprise features (enterprise.py)
├── /portal/*                     # Subcontractor portal (portal.py)
├── /documents/*                  # Document AI (documents.py)
├── /iot/*                        # IoT devices (iot.py)
├── /safety/*                     # Safety analysis (safety.py)
├── /state/*                      # State store (state.py)
├── /voice/*                      # Voice/realtime (voice.py)
├── /agent/*                      # Agent v1 endpoints
├── /agent/v2/*                   # Enhanced agent endpoints
├── /agent/self-mod/*             # Self-modification endpoints
├── /agent/enhance/*              # Enhancement endpoints
├── /agent/web-search/*           # Web search endpoints
├── /health/*                     # Health checks
├── /api/docs                     # Swagger UI (debug only)
└── /api/openapi.json             # OpenAPI spec (debug only)
```

### 1.2 Route Distribution by File

| File | Route Count |
|------|-------------|
| `api/v1/endpoints/vdc.py` | 33 |
| `api/v1/endpoints/portal.py` | 32 |
| `agent/enhanced_endpoints.py` | 32 |
| `agent/endpoints.py` | 28 |
| `api/v1/endpoints/economics.py` | 24 |
| `api/v1/endpoints/enterprise.py` | 23 |
| `api/v1/endpoints/ml.py` | 22 |
| `api/v1/endpoints/edge.py` | 22 |
| `api/v1/endpoints/documents.py` | 19 |
| `api/v1/endpoints/connectors.py` | 19 |

---

## 2. Complete Route Inventory

### 2.1 Registry Routes (`registry/endpoints.py`)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/v1/capabilities` | Create capability |
| GET | `/api/v1/capabilities` | List capabilities |
| GET | `/api/v1/capabilities/{id}` | Get capability |
| PUT | `/api/v1/capabilities/{id}` | Update capability |
| DELETE | `/api/v1/capabilities/{id}` | Delete capability |
| POST | `/api/v1/capabilities/{id}/deploy` | Deploy capability |
| POST | `/api/v1/capabilities/{id}/rollback` | Rollback capability |
| GET | `/api/v1/capabilities/{id}/dependencies` | Get dependencies |
| GET | `/api/v1/capabilities/{id}/dependents` | Get dependents |
| GET | `/api/v1/capabilities/stats/overview` | Statistics |
| POST | `/api/v1/capabilities/{id}/validate` | Validate capability |

### 2.2 Agent Routes (`agent/endpoints.py`)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/agent/execute` | Execute agent task |
| GET | `/agent/status` | Agent status |
| GET | `/agent/layers` | List layers |
| GET | `/agent/tools` | List tools |
| POST | `/agent/layer/move` | Move layer |
| POST | `/agent/conversation/read` | Read conversation |
| POST | `/agent/memory/search` | Search memory |
| POST | `/agent/memory/write` | Write memory |
| POST | `/agent/code/generate` | Generate code |
| POST | `/agent/code/validate` | Validate code |
| POST | `/agent/heal/analyze` | Analyze healing |
| POST | `/agent/sandbox/execute` | Execute in sandbox |
| GET | `/agent/reasoning/config` | Get reasoning config |
| POST | `/agent/reasoning/config` | Set reasoning config |
| GET | `/agent/reasoning/history` | Reasoning history |
| POST | `/agent/reasoning/clear` | Clear reasoning |
| **WS** | `/agent/ws` | **WebSocket for real-time agent** |
| POST | `/agent/plan/create` | Create plan |
| POST | `/agent/plan/execute/{id}` | Execute plan |
| POST | `/agent/plan/run` | Run plan |
| GET | `/agent/plan/{id}` | Get plan |
| GET | `/agent/plans` | List plans |
| POST | `/agent/schedule/create` | Create scheduled task |
| GET | `/agent/schedule/tasks` | List scheduled tasks |
| POST | `/agent/schedule/{id}/enable` | Enable task |
| POST | `/agent/schedule/{id}/disable` | Disable task |
| DELETE | `/agent/schedule/{id}` | Delete task |
| POST | `/agent/schedule/{id}/run` | Run task now |

### 2.3 Enhanced Agent Routes (`agent/enhanced_endpoints.py`)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/agent/v2/execute` | Enhanced execute |
| GET | `/agent/v2/status/enhanced` | Enhanced status |
| POST | `/agent/v2/conversation/query` | Query conversation |
| POST | `/agent/v2/memory/semantic-search` | Semantic search |
| GET | `/agent/v2/memory/search` | Search memory |
| POST | `/agent/v2/memory/write` | Write memory |
| GET | `/agent/v2/memory/insights` | Memory insights |
| GET | `/agent/v2/memory/entry/{id}` | Get memory entry |
| POST | `/agent/v2/layer/navigate` | Navigate layers |
| GET | `/agent/v2/layer/current` | Current layer |
| GET | `/agent/v2/layer/list` | List layers |
| GET | `/agent/v2/layer/info/{name}` | Layer info |
| POST | `/agent/v2/layer/suggest` | Suggest layer |
| GET | `/agent/v2/layer/transitions` | Layer transitions |
| GET | `/agent/v2/tools` | List tools |
| POST | `/agent/v2/tool/{name}/execute` | Execute tool |
| GET | `/agent/v2/economics/stats` | Economic stats |
| GET | `/agent/v2/economics/search/items` | Search items |
| GET | `/agent/v2/economics/items/{id}` | Get item |
| GET | `/agent/v2/economics/formulas` | List formulas |
| GET | `/agent/v2/economics/formulas/{id}` | Get formula |
| POST | `/agent/v2/economics/calculate` | Calculate |
| GET | `/agent/v2/economics/building-types` | Building types |
| POST | `/agent/v2/economics/estimate` | Create estimate |
| GET | `/agent/v2/economics/city-index` | City index |
| GET | `/agent/v2/economics/csi-divisions` | CSI divisions |
| GET | `/agent/v2/economics/browse/formulas` | Browse formulas |
| GET | `/agent/v2/economics/browse/topic/{topic}` | Browse by topic |
| GET | `/agent/v2/economics/browse/rsmeans` | RSMeans browse |
| GET | `/agent/v2/memory/working/{session}/{task}` | Working memory |
| POST | `/agent/v2/memory/working/checkpoint` | Checkpoint memory |
| DELETE | `/agent/v2/memory/working/{session}/{task}` | Delete working memory |

### 2.4 Self-Modification Routes (`agent/self_modification_endpoints.py`)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/agent/self-mod/layers/create` | Create layer |
| GET | `/agent/self-mod/layers/pending` | Pending layers |
| POST | `/agent/self-mod/code/modify` | Modify code |
| POST | `/agent/self-mod/code/refactor` | Refactor code |
| POST | `/agent/self-mod/modifications/{id}/approve` | Approve modification |
| POST | `/agent/self-mod/modifications/{id}/reject` | Reject modification |
| POST | `/agent/self-mod/modifications/{id}/apply` | Apply modification |
| POST | `/agent/self-mod/modifications/{id}/rollback` | Rollback modification |
| GET | `/agent/self-mod/status` | System status |
| GET | `/agent/self-mod/modifications/{id}` | Get modification |
| GET | `/agent/self-mod/history` | Modification history |
| POST | `/agent/self-mod/validate` | Validate changes |
| POST | `/agent/self-mod/autonomous/execute` | Autonomous execution |

### 2.5 Voice Routes (`api/v1/endpoints/voice.py`)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/voice/realtime/health` | Realtime health |
| **WS** | `/voice/realtime` | **WebSocket for OpenAI Realtime** |
| GET | `/voice/realtime/sessions` | List sessions |
| POST | `/voice/realtime/sessions/{id}/interrupt` | Interrupt session |

### 2.6 Edge Routes (`api/v1/endpoints/edge.py`)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/edge/devices` | Register device |
| GET | `/edge/devices` | List devices |
| GET | `/edge/devices/{id}` | Get device |
| PUT | `/edge/devices/{id}` | Update device |
| DELETE | `/edge/devices/{id}` | Delete device |
| POST | `/edge/devices/{id}/deploy` | Deploy to device |
| POST | `/edge/inference` | Run inference |
| GET | `/edge/inference/{id}` | Get inference status |
| POST | `/edge/sync` | Sync models |
| GET | `/edge/sync/status` | Sync status |
| **WS** | `/edge/ws/{device_id}` | **WebSocket for edge devices** |
| POST | `/edge/telemetry` | Submit telemetry |
| GET | `/edge/telemetry/{device_id}` | Get telemetry |
| POST | `/edge/federate` | Federated learning |
| GET | `/edge/federate/status` | Federate status |
| POST | `/edge/offload` | Task offload |
| GET | `/edge/offload/{task_id}` | Offload status |
| POST | `/edge/batch` | Batch inference |
| GET | `/edge/batch/{batch_id}` | Batch status |
| POST | `/edge/optimize` | Optimize model |
| GET | `/edge/optimize/{job_id}` | Optimization status |
| GET | `/edge/metrics` | Edge metrics |
| POST | `/edge/alert` | Create alert |
| GET | `/edge/alerts` | List alerts |

### 2.7 VDC Routes (`api/v1/endpoints/vdc.py`) - Sample

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/vdc/federated-models` | Create model |
| GET | `/vdc/federated-models/{id}` | Get model |
| GET | `/vdc/federated-models/{id}/statistics` | Model stats |
| POST | `/vdc/federated-models/{id}/export/{format}` | Export model |
| POST | `/vdc/clash-detection/run` | Run clash detection |
| GET | `/vdc/clash-detection/results/{id}` | Get results |
| GET | `/vdc/clash-detection/clashes/{id}` | Get clash |
| PATCH | `/vdc/clash-detection/clashes/{id}/resolve` | Resolve clash |
| PATCH | `/vdc/clash-detection/clashes/{id}/ignore` | Ignore clash |
| POST | `/vdc/schedule-4d` | Create 4D schedule |
| POST | `/vdc/schedule-4d/{id}/simulate` | Simulate schedule |
| POST | `/vdc/cost-5d` | Create 5D cost model |
| GET | `/vdc/cost-5d/{id}/heatmap` | Cost heatmap |
| POST | `/vdc/upload/ifc` | Upload IFC |
| POST | `/vdc/upload/bcf` | Upload BCF |

---

## 3. External API Calls

### 3.1 Files with HTTP Client Usage

| File | Library | External Services |
|------|---------|-------------------|
| `agent/web_search.py` | httpx | Brave Search API |
| `agent/enhanced_core.py` | httpx | **Internal APIs (relative URLs)** |
| `core/vault.py` | httpx | HashiCorp Vault |
| `warehouse/nl_queries.py` | httpx | OpenAI |
| `warehouse/etl_pipeline.py` | httpx | External data sources |
| `voice/realtime_proxy.py` | websockets | OpenAI Realtime API |
| `enterprise/custom_integrations.py` | requests | Webhook endpoints |
| `enterprise/scim.py` | requests | SCIM providers |
| `enterprise/sso_oidc.py` | requests | OIDC providers (Google, Microsoft, Okta) |
| `enterprise/sso_saml.py` | requests | SAML IdPs |
| `integrations/crm.py` | requests | Salesforce, HubSpot |
| `integrations/esignature.py` | requests | DocuSign |
| `integrations/slack.py` | requests | Slack API |
| `integrations/microsoft_365.py` | requests | Microsoft Graph |
| `integrations/erp.py` | requests | QuickBooks |
| `integrations/procore.py` | requests | Procore API |
| `integrations/accounting.py` | requests | QuickBooks, Xero |
| `integrations/file_storage.py` | requests | Box, Dropbox |
| `economics/pricing_engine.py` | - | RSMeans API |

### 3.2 External Service URLs

```python
# AI/ML Services
https://api.openai.com/v1/realtime          # OpenAI Realtime API (WebSocket)
https://api.search.brave.com/res/v1/web/search  # Brave Search

# Enterprise/Identity
https://accounts.google.com/.well-known/openid-configuration
https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration
https://{okta_domain}.okta.com
https://login.salesforce.com/services/oauth2/token
https://api.hubapi.com

# Integrations
https://account-d.docusign.com              # DocuSign OAuth
https://demo.docusign.net/restapi           # DocuSign API
https://slack.com/api
https://graph.microsoft.com/v1.0
https://quickbooks.api.intuit.com
https://api.procore.com
https://api.xero.com/api.xro/2.0
https://api.box.com/2.0
https://api.dropboxapi.com/2
https://api.rsmeans.com/v1

# Cloud Storage
https://{bucket}.s3.amazonaws.com
```

---

## 4. Internal API Calls (Using Relative URLs)

### 4.1 Problematic Relative URL Usage

**File:** `agent/enhanced_core.py`

| Line | URL Pattern | Issue |
|------|-------------|-------|
| 2246 | `httpx.get("/api/v1/documents/files")` | **Relative URL - requires base URL** |
| 2345 | `httpx.get(f"/api/v1/documents/upload/chat/{file_id}")` | **Relative URL** |
| 2361 | `httpx.post("/api/v1/documents/ocr")` | **Relative URL** |
| 2413 | `httpx.get(f"/api/v1/documents/upload/chat/{file_id}")` | **Relative URL** |
| 2429 | `httpx.post("/api/v1/documents/classify")` | **Relative URL** |
| 2473 | `httpx.get("/api/v1/documents/files")` | **Relative URL** |

**Issue:** These calls use relative URLs without a base URL configuration. They require either:
1. A configured base URL from environment variables
2. Proper httpx client initialization with base_url
3. Discovery from service registry

---

## 5. WebSocket Endpoints

| Route | File | Description |
|-------|------|-------------|
| `/agent/ws` | `agent/endpoints.py` | Real-time agent interaction |
| `/voice/realtime` | `api/v1/endpoints/voice.py` | OpenAI Realtime API proxy |
| `/edge/ws/{device_id}` | `api/v1/endpoints/edge.py` | Edge device communication |

### 5.1 WebSocket Implementation Details

**Agent WebSocket** (`agent/websocket.py`):
- CORS origins include extensive localhost/127.0.0.1 entries
- Supports 50+ simultaneous connections
- Message buffering for reliability

**Voice Realtime** (`voice/realtime_proxy.py`):
- Proxies to OpenAI Realtime API
- WebSocket URL: `wss://api.openai.com/v1/realtime`
- Handles bidirectional audio streaming

---

## 6. Hardcoded Localhost/127.0.0.1 References

### 6.1 CORS Origins (`agent/websocket.py:483-515`)

```python
# HTTP Origins
http://localhost
http://localhost:3000
http://localhost:8000
http://localhost:8080
http://127.0.0.1
http://127.0.0.1:3000
http://127.0.0.1:8000
http://127.0.0.1:8080
https://localhost
https://localhost:3000
https://localhost:8000
https://localhost:8080
https://127.0.0.1
https://127.0.0.1:3000
https://127.0.0.1:8000
https://127.0.0.1:8080

# WebSocket Origins
ws://localhost
ws://localhost:3000
ws://localhost:8000
ws://localhost:8080
ws://127.0.0.1
ws://127.0.0.1:3000
ws://127.0.0.1:8000
ws://127.0.0.1:8080
wss://localhost
wss://localhost:3000
wss://localhost:8000
wss://localhost:8080
wss://127.0.0.1
wss://127.0.0.1:3000
wss://127.0.0.1:8000
wss://127.0.0.1:8080
```

### 6.2 Default Configuration Values

| File | Variable | Default Value |
|------|----------|---------------|
| `core/config.py:101` | Database URL | `postgresql+asyncpg://user:pass@localhost/cerebrum` |
| `core/config.py:104` | DB_HOST | `localhost` |
| `core/config.py:131` | REDIS_HOST | `localhost` |
| `core/config.py:146` | VAULT_ADDR | `http://localhost:8200` |
| `core/config.py:159` | CORS Origins | `http://localhost:3000,...` |
| `core/config.py:268` | FRONTEND_URL | `http://localhost:3000` |
| `core/cors.py:7-8` | CORS Origins | `http://localhost:3000, http://localhost:5173` |
| `tasks.py:21` | REDIS_URL | `redis://localhost:6379/0` |
| `core/database/redis_sentinel.py:21` | SENTINEL_HOSTS | `localhost:26379` |
| `main.py:204` | Allowed Hosts | `localhost, 127.0.0.1` |
| `vdc/revit_link.py:97` | Revit Host | `localhost:8080` |
| `ml/jupyter.py:62` | Jupyter URL | `http://localhost:8888` |

### 6.3 Security Implications

**High Risk:**
- Production should never use default localhost configurations
- CORS origins allow all localhost ports (security vs convenience trade-off)
- Default database credentials in connection string

**Recommendations:**
1. Move all defaults to environment variables
2. Remove localhost from production CORS
3. Use service discovery for internal communication
4. Implement strict configuration validation

---

## 7. Router Registration Summary

### 7.1 Main Application (`main.py`)

```python
app.include_router(health_router, tags=["health"])
app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1", tags=["health"])
```

### 7.2 API v1 Router (`api/v1/api.py`)

```python
api_v1_router.include_router(auth.router)                    # /auth
api_v1_router.include_router(admin.router)                   # /admin
api_v1_router.include_router(chat.router)                    # /chat
api_v1_router.include_router(dejavu.router)                  # /dejavu
api_v1_router.include_router(formulas.router)                # /formulas
api_v1_router.include_router(sessions.router)                # /sessions
api_v1_router.include_router(connectors.router)              # /connectors
api_v1_router.include_router(users, prefix="/users")         # /users
api_v1_router.include_router(projects, prefix="/projects")   # /projects
api_v1_router.include_router(registry, prefix="/registry")   # /registry
api_v1_router.include_router(coding, prefix="/coding")       # /coding
api_v1_router.include_router(quality, prefix="/quality")     # /quality
api_v1_router.include_router(bim.router)                     # /bim
api_v1_router.include_router(economics.router)               # /economics
api_v1_router.include_router(vdc.router)                     # /vdc
api_v1_router.include_router(integrations.router)            # /integrations
api_v1_router.include_router(warehouse.router, prefix="/warehouse")
api_v1_router.include_router(ml.router)                      # /ml
api_v1_router.include_router(edge.router)                    # /edge
api_v1_router.include_router(enterprise.router)              # /enterprise
api_v1_router.include_router(portal.router)                  # /portal
api_v1_router.include_router(documents.router)               # /documents
api_v1_router.include_router(iot.router, prefix="/iot")      # /iot
api_v1_router.include_router(safety.router)                  # /safety
api_v1_router.include_router(state.router)                   # /state
api_v1_router.include_router(voice_router.router, prefix="/voice")

# Agent routers
api_v1_router.include_router(agent_router, prefix="/agent")
api_v1_router.include_router(enhanced_agent_router, prefix="/agent/v2")
api_v1_router.include_router(self_mod_router, prefix="/agent/self-mod")
api_v1_router.include_router(enhancement_router, prefix="/agent/enhance")
api_v1_router.include_router(web_search_router, prefix="/agent/web-search")
api_v1_router.include_router(websocket_router, prefix="/agent/v2")
```

---

## 8. Critical Findings

### 8.1 Internal API Call Issues

**Problem:** `agent/enhanced_core.py` uses relative URLs for internal API calls without proper base URL configuration.

```python
# Lines 2246, 2345, 2361, 2413, 2429, 2473
response = httpx.get("/api/v1/documents/files", timeout=10.0)
```

**Fix Required:**
```python
import httpx
from app.core.config import settings

# Option 1: Use base_url in client
async with httpx.AsyncClient(base_url=settings.API_BASE_URL) as client:
    response = await client.get("/api/v1/documents/files")

# Option 2: Use full URL
response = await httpx.get(f"{settings.API_BASE_URL}/api/v1/documents/files")
```

### 8.2 CORS Configuration

**File:** `agent/websocket.py:483-515`

Extensive localhost/127.0.0.1 entries in production CORS configuration could be a security risk.

**Recommendation:** Use environment-specific CORS origins:
```python
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://cerebrum-frontend.onrender.com"
).split(",")
```

### 8.3 Default Database Credentials

**File:** `core/config.py:101`

```python
default="postgresql+asyncpg://user:pass@localhost/cerebrum"
```

**Risk:** Default credentials in code.

**Fix:** Require environment variable:
```python
DATABASE_URL: str = Field(
    default=None,
    description="Database URL (required)"
)
```

### 8.4 External Service Dependencies

| Service | Usage | Fallback |
|---------|-------|----------|
| OpenAI Realtime | Voice features | None - graceful degradation needed |
| Brave Search | Web search | None |
| Redis | Caching, tasks | In-memory fallback |
| Vault | Secrets | Environment variables |
| PostgreSQL | Primary database | Read-only replica |

---

## 9. Recommendations

### Immediate Actions

1. **Fix relative URL calls** in `agent/enhanced_core.py` - Add base URL configuration
2. **Audit CORS origins** - Remove localhost from production builds
3. **Remove default credentials** - Make database URL required
4. **Add service discovery** - For internal API communication

### Architecture Improvements

1. **API Gateway Pattern** - Consolidate internal routing
2. **Service Mesh** - For inter-service communication
3. **Circuit Breakers** - For external API calls
4. **Health Check Aggregation** - For all dependencies

### Monitoring

1. Track external API latency and failures
2. Monitor WebSocket connection counts
3. Alert on internal API call failures
4. Log all service-to-service communication

---

## Appendix A: Complete File List with Routes

See individual file comments for full route documentation.

### Router Files (50 total)

```
agent/endpoints.py
agent/web_search_endpoints.py
agent/enhancement_endpoints.py
agent/self_modification_endpoints.py
agent/enhanced_endpoints.py
agent/self_modification.py
agent/websocket.py
agent/coding_tools.py

registry/endpoints.py
registry/main.py

validation/endpoints.py
hotswap/endpoints.py
hotswap/route_registration.py
prompts/endpoints.py
healing/endpoints.py
coding/endpoints.py

api/health.py
api/v1/api.py
api/v1/endpoints/chat.py
api/v1/endpoints/formulas.py
api/v1/endpoints/bim.py
api/v1/endpoints/dejavu.py
api/v1/endpoints/vdc.py
api/v1/endpoints/documents.py
api/v1/endpoints/auth.py
api/v1/endpoints/stub_registry.py
api/v1/endpoints/stub_quality.py
api/v1/endpoints/stub_coding.py
api/v1/endpoints/stub_projects.py
api/v1/endpoints/connectors.py
api/v1/endpoints/voice.py
api/v1/endpoints/ml.py
api/v1/endpoints/stub_users.py
api/v1/endpoints/state.py
api/v1/endpoints/enterprise.py
api/v1/endpoints/warehouse.py
api/v1/endpoints/iot.py
api/v1/endpoints/portal.py
api/v1/endpoints/edge.py
api/v1/endpoints/economics.py
api/v1/endpoints/safety.py
api/v1/endpoints/sessions.py
api/v1/endpoints/integrations.py
api/v1/endpoints/admin.py

monitoring/health_deep.py

core/rate_limit.py (example only)
core/deps.py (example only)
```

---

*End of Report*
