# Environment Variables & Configuration Audit

**Project:** Cerebrum AI Platform  
**Audit Date:** 2026-04-02  
**Scope:** All environment variables in frontend, backend, deployment configs

---

## Executive Summary

| Category | Count |
|----------|-------|
| **Total Variables** | 90+ |
| **Required** | 3 (SECRET_KEY, DATABASE_URL, REDIS_URL) |
| **Optional** | 80+ |
| **Documented** | ~50 |
| **Undocumented** | ~40 |

**Critical Issues Found:**
1. **Missing Frontend .env.example** - No template for frontend environment variables
2. **Inconsistent naming** - Some vars use `API_BASE_URL` (config.py) while render.yaml uses different vars
3. **Undocumented feature flags** - Many feature flags lack documentation
4. **Security concern** - `AUTH_SLEEP_MODE` defaults to `true` (bypasses auth)

---

## 1. Frontend Environment Variables (Vite)

### Used in Code

| Variable | Files | Default | Required | Description |
|----------|-------|---------|----------|-------------|
| `VITE_API_URL` | `useAgentChat.ts:8`, `useVoiceChat.ts:4`, `useChat.ts:7`, `fileProcessing.ts:4` | `https://cerebrum-api.onrender.com` | ❌ Yes | Backend API URL |
| `VITE_WS_URL` | `env.d.ts:5` | - | ❌ No | WebSocket URL (defined but not used) |
| `VITE_APP_NAME` | `env.d.ts:6` | - | ❌ No | App name (defined but not used) |
| `VITE_APP_VERSION` | `env.d.ts:7` | - | ❌ No | App version (defined but not used) |

**Issues:**
- No `.env.example` file exists in frontend
- `VITE_WS_URL`, `VITE_APP_NAME`, `VITE_APP_VERSION` declared but never used
- Fallback hardcoded to Render URL in multiple places

**Files with hardcoded fallback:**
- `frontend/src/hooks/useAgentChat.ts:8`
- `frontend/src/hooks/useVoiceChat.ts:4`
- `frontend/src/hooks/useChat.ts:7`
- `frontend/src/lib/fileProcessing.ts:4`
- `frontend/src/context/AuthContext.tsx:4`

---

## 2. Backend Environment Variables

### 2.1 Core Application Settings (config.py)

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `APP_NAME` | `Cerebrum AI Platform` | config.py:35 | ❌ No | Application name |
| `APP_VERSION` | `1.0.0` | config.py:36 | ❌ No | Application version |
| `APP_DESCRIPTION` | `AI-powered knowledge...` | config.py:38 | ❌ No | App description |
| `DEBUG` | `false` | config.py:42 | ❌ No | Enable debug mode |
| `ENVIRONMENT` | `development` | config.py:44 | ❌ No | Environment enum |
| `HOST` | `0.0.0.0` | config.py:54 | ❌ No | Server host |
| `PORT` | `8000` | config.py:55 | ❌ No | Server port |
| `WORKERS` | `4` | config.py:56 | ❌ No | Worker processes |
| `RELOAD` | `false` | config.py:57 | ❌ No | Auto-reload |

### 2.2 Security Settings (CRITICAL)

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| **SECRET_KEY** | *(none)* | config.py:62 | ✅ **YES** | JWT signing key |
| `PASSWORD_PEPPER` | *(none)* | config.py:65 | ❌ No | Password hash pepper |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | config.py:68 | ❌ No | Token expiry |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `365` | config.py:72 | ❌ No | Refresh expiry |
| `JWT_ALGORITHM` | `HS256` | config.py:75 | ❌ No | JWT algorithm |
| `MFA_ISSUER_NAME` | `Cerebrum AI` | config.py:77 | ❌ No | TOTP issuer |

**Validation:**
- `SECRET_KEY` must be ≥32 characters (enforced in `config.py:303`)
- Missing SECRET_KEY causes app exit with `CRITICAL` log (main.py:69)

### 2.3 Database Settings (CRITICAL)

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| **DATABASE_URL** | *(none)* | config.py:85 | ✅ **YES** | Database connection |
| `DB_HOST` | `localhost` | config.py:90 | ❌ No | DB host (fallback) |
| `DB_PORT` | `5432` | config.py:91 | ❌ No | DB port (fallback) |
| `DB_NAME` | `cerebrum` | config.py:92 | ❌ No | DB name (fallback) |
| `DB_USER` | `user` | config.py:93 | ❌ No | DB user (fallback) |
| `DB_PASSWORD` | `pass` | config.py:94 | ❌ No | DB pass (fallback) |
| `USE_PGBOUNCER` | `false` | config.py:100 | ❌ No | Enable PgBouncer |
| `PGBOUNCER_HOST` | `null` | config.py:97 | ❌ No | PgBouncer host |
| `PGBOUNCER_PORT` | `6432` | config.py:100 | ❌ No | PgBouncer port |
| `TEST_DATABASE_URL` | `null` | config.py:318 | ❌ No | Test database URL |

**Validation:**
- Missing DATABASE_URL causes app exit with `CRITICAL` log (main.py:74)
- `alembic/env.py:27` uses `os.getenv("DATABASE_URL")` directly
- `alembic/env.py:96` uses `os.getenv("DATABASE_URL")` directly

### 2.4 Redis Settings (CRITICAL)

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| **REDIS_URL** | *(none)* | config.py:104 | ✅ **YES** | Redis connection URL |
| `REDIS_HOST` | `localhost` | config.py:110 | ❌ No | Redis host (fallback) |
| `REDIS_PORT` | `6379` | config.py:111 | ❌ No | Redis port (fallback) |
| `REDIS_PASSWORD` | `null` | config.py:113 | ❌ No | Redis password |
| `REDIS_DB_CACHE` | `0` | config.py:115 | ❌ No | Cache DB |
| `REDIS_DB_QUEUE` | `1` | config.py:116 | ❌ No | Queue DB |
| `REDIS_DB_SESSIONS` | `2` | config.py:117 | ❌ No | Sessions DB |
| `REDIS_DB_RATE_LIMIT` | `3` | config.py:118 | ❌ No | Rate limit DB |

**Validation:**
- Missing REDIS_URL causes app exit with `CRITICAL` log (main.py:74)

### 2.5 Redis Sentinel (High Availability)

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `REDIS_SENTINEL_HOSTS` | `localhost:26379` | redis_sentinel.py:21 | ❌ No | Sentinel hosts |
| `REDIS_SENTINEL_MASTER_NAME` | `mymaster` | redis_sentinel.py:22 | ❌ No | Master name |
| `REDIS_PASSWORD` | `null` | redis_sentinel.py:23 | ❌ No | Redis password |
| `REDIS_DB` | `0` | redis_sentinel.py:24 | ❌ No | Database number |
| `SENTINEL_SOCKET_TIMEOUT` | `5` | redis_sentinel.py:25 | ❌ No | Timeout (seconds) |

### 2.6 Vault Settings

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `VAULT_ENABLED` | `false` | config.py:125 | ❌ No | Enable Vault |
| `VAULT_ADDR` | `http://localhost:8200` | config.py:126 | ❌ No | Vault address |
| `VAULT_TOKEN` | `null` | config.py:127 | ❌ No | Vault token |
| `VAULT_ROLE_ID` | `null` | config.py:128 | ❌ No | AppRole ID |
| `VAULT_SECRET_ID` | `null` | config.py:129 | ❌ No | AppRole secret |
| `VAULT_MOUNT_POINT` | `secret` | config.py:130 | ❌ No | Mount point |
| `VAULT_DB_PATH` | `database/creds/app` | config.py:131 | ❌ No | DB creds path |
| `VAULT_ENCRYPTION_KEY` | *(auto-gen)* | pam.py:106 | ❌ No | PAM encryption |

### 2.7 CORS Settings

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `CORS_ORIGINS` | `http://localhost:3000,...` | config.py:140 | ✅ Prod | Allowed origins |
| `CORS_ALLOW_CREDENTIALS` | `true` | config.py:143 | ❌ No | Allow credentials |
| `CORS_ALLOW_METHODS` | `*` | config.py:145 | ❌ No | Allowed methods |
| `CORS_ALLOW_HEADERS` | `*` | config.py:148 | ❌ No | Allowed headers |

**Validation:**
- CORS_ORIGINS required in production (main.py:78)

### 2.8 Rate Limiting

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `RATE_LIMIT_ENABLED` | `true` | config.py:175 | ❌ No | Enable rate limiting |
| `RATE_LIMIT_DEFAULT` | `100/minute` | config.py:176 | ❌ No | Default limit |
| `RATE_LIMIT_LOGIN` | `5/minute` | config.py:177 | ❌ No | Login limit |
| `RATE_LIMIT_REGISTER` | `3/hour` | config.py:178 | ❌ No | Register limit |

### 2.9 Logging

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `LOG_LEVEL` | `INFO` | config.py:182 | ❌ No | Log level |
| `LOG_FORMAT` | `json` | config.py:183 | ❌ No | Log format |
| `LOG_FILE` | `null` | config.py:184 | ❌ No | Log file path |

### 2.10 Sentry

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `SENTRY_ENABLED` | `false` | config.py:190 | ❌ No | Enable Sentry |
| `SENTRY_DSN` | `null` | config.py:191 | ❌ No | Sentry DSN |
| `SENTRY_ENVIRONMENT` | `development` | config.py:192 | ❌ No | Environment |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.1` | config.py:193 | ❌ No | Sample rate |

### 2.11 AWS Settings

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `AWS_REGION` | `us-east-1` | config.py:197 | ❌ No | AWS region |
| `AWS_ACCESS_KEY_ID` | `null` | config.py:198 | ❌ No | Access key |
| `AWS_SECRET_ACCESS_KEY` | `null` | config.py:199 | ❌ No | Secret key |
| `S3_BUCKET_NAME` | `null` | config.py:201 | ❌ No | S3 bucket |
| `S3_AUDIT_PREFIX` | `audit-logs/` | config.py:203 | ❌ No | Audit prefix |
| `S3_BACKUP_PREFIX` | `backups/` | config.py:204 | ❌ No | Backup prefix |

### 2.12 API Keys & Integrations

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `RSMEANS_API_KEY` | `null` | config.py:210 | ❌ No | RSMeans API |
| `BRAVE_API_KEY` | `null` | config.py:216 | ❌ No | Brave Search |
| `OPENAI_API_KEY` | `null` | config.py:222 | ❌ No | OpenAI API |
| `MLFLOW_TRACKING_URI` | `null` | config.py:228 | ❌ No | MLflow URI |
| `LAYOUTLM_MODEL_PATH` | `null` | config.py:234 | ❌ No | LayoutLM model |
| `TESSERACT_CMD` | `null` | config.py:238 | ❌ No | Tesseract path |

### 2.13 Monitoring

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `SPLUNK_URL` | `null` | config.py:252 | ❌ No | Splunk URL |
| `SPLUNK_HEC_TOKEN` | `null` | config.py:256 | ❌ No | Splunk HEC token |
| `FLOWER_API_URL` | `http://localhost:5555/api` | flower_monitoring.py:18 | ❌ No | Flower API |
| `FLOWER_BASIC_AUTH` | `null` | flower_monitoring.py:19 | ❌ No | Flower auth |

### 2.14 Email Settings

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `SMTP_HOST` | `null` | config.py:273 | ❌ No | SMTP host |
| `SMTP_PORT` | `587` | config.py:274 | ❌ No | SMTP port |
| `SMTP_USER` | `null` | config.py:275 | ❌ No | SMTP user |
| `SMTP_PASSWORD` | `null` | config.py:276 | ❌ No | SMTP password |
| `SMTP_TLS` | `true` | config.py:277 | ❌ No | Use TLS |
| `EMAIL_FROM` | `noreply@cerebrum.ai` | config.py:278 | ❌ No | From address |

### 2.15 Encryption

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `ENCRYPTION_KEY` | `null` | config.py:283 | ❌ No | Field encryption |
| `ENCRYPTION_MASTER_KEY` | `null` | column_encryption.py:36 | ❌ No | Column encryption |

### 2.16 Feature Flags

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `FEATURE_MFA_ENABLED` | `true` | config.py:291 | ❌ No | Enable MFA |
| `FEATURE_AUDIT_LOGGING` | `true` | config.py:292 | ❌ No | Enable audit logs |
| `FEATURE_API_KEYS` | `true` | config.py:293 | ❌ No | Enable API keys |

### 2.17 Compatibility/Stub Settings

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `USE_STUB_CONNECTORS` | `true` | config.py:298 | ❌ No | Use stub connectors |
| `USE_STUB_ML` | `true` | config.py:302 | ❌ No | Use stub ML |
| `USE_STUB_NOTIFICATIONS` | `true` | config.py:306 | ❌ No | Use stub notifications |
| `STUB_FALLBACK_ENABLED` | `true` | config.py:310 | ❌ No | Enable fallback |

**Note:** Connector-specific stub flags follow pattern `USE_STUB_<SERVICE>` (e.g., `USE_STUB_PROCORE`)

### 2.18 Local Development

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `WATCH_LOCAL_FILES` | `false` | main.py:141 | ❌ No | Enable file watcher |
| `LOCAL_DATA_PATH` | `/data/diriyah_docs` | watcher.py:269 | ❌ No | Watch path |
| `AUTH_SLEEP_MODE` | `true` | deps.py:27 | ❌ No | **⚠️ Bypasses auth** |

**⚠️ CRITICAL:** `AUTH_SLEEP_MODE=true` bypasses all authentication!

### 2.19 ChromaDB / Vector Search

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `DISABLE_CHROMADB` | `false` | chroma_service.py:17 | ❌ No | Disable ChromaDB |
| `USE_ML_EMBEDDINGS` | `true` | chroma_service.py:53 | ❌ No | Use ML embeddings |
| `TRANSFORMERS_CACHE` | `/app/models` | chroma_service.py:55 | ❌ No | Model cache path |
| `CHROMA_DB_PATH` | `/data/chroma_store` | chroma_service.py:128 | ❌ No | ChromaDB path |
| `CHROMA_HOST` | `null` | chroma_service.py:138 | ❌ No | ChromaDB host |
| `CHROMA_PORT` | `8000` | chroma_service.py:139 | ❌ No | ChromaDB port |

### 2.20 Formulas

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `INITIAL_FORMULAS_PATH` | `null` | config.py:326 | ❌ No | Formulas JSON path |

### 2.21 Distributed Triggers

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `USE_DISTRIBUTED_TRIGGERS` | `true` | triggers/engine.py:24 | ❌ No | Distributed events |

### 2.22 Data Residency

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `GEOIP_DB_PATH` | `/usr/share/GeoIP/GeoLite2-City.mmdb` | data_residency.py:85 | ❌ No | GeoIP database |

### 2.23 Migration

| Variable | Default | Used In | Required | Description |
|----------|---------|---------|----------|-------------|
| `MIGRATION_LOCK_ID` | `987654321` | alembic/env.py:73 | ❌ No | Migration lock ID |

---

## 3. Variables Only in Deployment Configs

### Render (render.yaml)

| Variable | Set In | Notes |
|----------|--------|-------|
| `PUBLIC_BASE_URL` | render.yaml:42 | Not in config.py |
| `API_BASE_URL` | render.yaml:44 | Not in config.py |
| `PDP_ENABLED` | render.yaml:35 | Not in config.py |
| `BACKUP_DIR` | render.yaml:86 | Cron job only |
| `BACKUP_RETENTION_DAYS` | render.yaml:88 | Cron job only |

### Docker Compose

| Variable | Set In | Notes |
|----------|--------|-------|
| `GOOGLE_CLIENT_ID` | docker-compose.yml | Hardcoded in file |
| `GOOGLE_CLIENT_SECRET` | docker-compose.yml | From env |
| `GOOGLE_REDIRECT_URI` | docker-compose.yml | Hardcoded in file |

---

## 4. Current .env Files

### `/backend/.env` (Development)

```bash
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=cerebrum-development-secret-key-32chars-min-required
PASSWORD_PEPPER=dev-pepper-not-for-production
DATABASE_URL=sqlite+aiosqlite:///./cerebrum.db
REDIS_URL=redis://localhost:6379/0
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
S3_BUCKET=cerebrum-dev
TESSERACT_CMD=/usr/bin/tesseract
```

**Issues:**
- Uses SQLite (not PostgreSQL)
- AWS credentials are test values
- Missing many optional variables

### `/backend/app/core/.env_local`

```bash
TESSERACT_CMD=/usr/bin/tesseract
```

**Issues:**
- Only contains Tesseract path
- Unclear purpose (overrides?)

---

## 5. Missing Documentation

### Frontend Variables Not Documented

| Variable | Status |
|----------|--------|
| `VITE_API_URL` | ❌ No .env.example |
| `VITE_WS_URL` | ❌ Declared but unused |
| `VITE_APP_NAME` | ❌ Declared but unused |
| `VITE_APP_VERSION` | ❌ Declared but unused |

### Backend Variables Not in DEPLOY.md

| Variable | Category |
|----------|----------|
| `AUTH_SLEEP_MODE` | Security (⚠️ critical) |
| `WATCH_LOCAL_FILES` | Development |
| `LOCAL_DATA_PATH` | Development |
| `USE_STUB_*` | All stub flags |
| `CHROMA_*` | Vector DB |
| `DISABLE_CHROMADB` | Vector DB |
| `USE_ML_EMBEDDINGS` | ML |
| `TRANSFORMERS_CACHE` | ML |
| `INITIAL_FORMULAS_PATH` | Formulas |
| `MIGRATION_LOCK_ID` | Database |
| `GEOIP_DB_PATH` | Data residency |
| `VAULT_*` | Vault integration |
| `ENCRYPTION_MASTER_KEY` | Encryption |
| `FLOWER_*` | Monitoring |
| `SPLUNK_*` | Monitoring |
| `TEST_DATABASE_URL` | Testing |

### Variables Missing from config.py

| Variable | Found In | Issue |
|----------|----------|-------|
| `PUBLIC_BASE_URL` | render.yaml | Not used in code |
| `API_BASE_URL` | render.yaml | Not used in code |
| `PDP_ENABLED` | render.yaml | Not used in code |

---

## 6. Recommendations

### Critical (Fix Immediately)

1. **Create `frontend/.env.example`**
   ```bash
   VITE_API_URL=http://localhost:8000
   ```

2. **Document `AUTH_SLEEP_MODE`**
   - Add warning that it bypasses authentication
   - Default should be `false` in production templates

3. **Remove unused Vite env declarations**
   - Remove `VITE_WS_URL`, `VITE_APP_NAME`, `VITE_APP_VERSION` from `env.d.ts` or implement usage

### High Priority

4. **Standardize `API_BASE_URL` usage**
   - Either add to `config.py` or remove from render.yaml
   - Currently defined but not consumed

5. **Document all feature flags**
   - Add table to DEPLOY.md or create FEATURE_FLAGS.md

6. **Document ChromaDB/ML variables**
   - Required for vector search functionality

### Medium Priority

7. **Clean up .env files**
   - Remove `.env_local` or document its purpose
   - Update `.env` to use PostgreSQL for consistency

8. **Add missing env vars to DEPLOY.md**
   - All monitoring variables
   - All development variables
   - All security variables

9. **Create environment-specific templates**
   - `.env.development`
   - `.env.staging`
   - `.env.production.example`

---

## 7. Security Checklist

| Variable | Production Safe? | Notes |
|----------|------------------|-------|
| `SECRET_KEY` | ✅ Must be set | Enforced ≥32 chars |
| `DEBUG` | ✅ Must be `false` | Validated on startup |
| `AUTH_SLEEP_MODE` | ❌ **DANGER** | Defaults to `true`! |
| `USE_STUB_CONNECTORS` | ⚠️ Review | May be needed for some services |
| `CORS_ORIGINS` | ✅ Required | Enforced in production |
| `PASSWORD_PEPPER` | ✅ Should be set | Adds security layer |
| `ENCRYPTION_*` | ✅ Optional | Only if encryption used |
| `VAULT_*` | ✅ Optional | For enterprise use |

---

## 8. Files Using Environment Variables

### Frontend
```
frontend/src/env.d.ts
frontend/src/hooks/useAgentChat.ts
frontend/src/hooks/useVoiceChat.ts
frontend/src/hooks/useChat.ts
frontend/src/lib/fileProcessing.ts
frontend/src/context/AuthContext.tsx
```

### Backend (direct os.getenv)
```
backend/app/core/config.py          # Primary config
backend/app/api/deps.py             # AUTH_SLEEP_MODE
backend/app/main.py                 # WATCH_LOCAL_FILES
backend/app/tasks.py                # REDIS_URL
backend/app/triggers/engine.py      # USE_DISTRIBUTED_TRIGGERS
backend/app/coding/generator.py     # OPENAI_API_KEY
backend/app/healing/patch_generation.py  # OPENAI_API_KEY
backend/app/services/chroma_service.py   # CHROMA_*, USE_ML_EMBEDDINGS
backend/app/services/formula_runtime.py  # INITIAL_FORMULAS_PATH
backend/app/services/redis_state_store.py # REDIS_URL
backend/app/workers/celery_config.py     # REDIS_URL
backend/app/connectors/factory.py        # USE_STUB_*
backend/app/platform/local_filesystem/watcher.py  # WATCH_LOCAL_FILES, LOCAL_DATA_PATH
backend/app/core/database/redis_sentinel.py         # REDIS_SENTINEL_*
backend/app/core/security/column_encryption.py      # ENCRYPTION_MASTER_KEY
backend/app/core/security/pam.py                    # VAULT_ENCRYPTION_KEY
backend/app/core/security/data_residency.py         # GEOIP_DB_PATH
backend/app/core/monitoring/flower_monitoring.py    # FLOWER_*
backend/alembic/env.py                              # DATABASE_URL, MIGRATION_LOCK_ID
backend/tests/test_smoke.py                         # Test defaults
```

---

## 9. Current Values in Deployment

### Render Production
```yaml
DEBUG: false
ENVIRONMENT: production
USE_STUB_CONNECTORS: true
PDP_ENABLED: false
USE_ML_EMBEDDINGS: true
SENTRY_ENABLED: true
```

### Docker Compose Local
```yaml
DEBUG: true
USE_STUB_CONNECTORS: true
USE_STUB_ML: true
USE_STUB_NOTIFICATIONS: true
WATCH_LOCAL_FILES: true
```

---

## Appendix A: Quick Reference - Required Variables

For production deployment, these MUST be set:

```bash
# Required
SECRET_KEY=                # Min 32 chars
DATABASE_URL=              # PostgreSQL URL
REDIS_URL=                 # Redis URL

# Required in production
CORS_ORIGINS=              # Your frontend domain

# Highly recommended
PASSWORD_PEPPER=           # Random string
SENTRY_DSN=                # For error tracking
AWS_ACCESS_KEY_ID=         # If using S3
AWS_SECRET_ACCESS_KEY=     # If using S3
OPENAI_API_KEY=            # If using AI features
```

---

*End of Audit Report*
