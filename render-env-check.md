# Render Environment Variables Check

## Service: cerebrum-api (srv-d69j8av5r7bs73f9au40)

**API Key Status:** Valid (can list services)

**Permission Issue:** The API key cannot retrieve environment variables via the API endpoint. This is expected - Render API keys typically don't expose sensitive env var values for security reasons.

## Manual Check Required

You need to verify the following env vars are set in Render Dashboard:

### Required for Google Drive:
- [ ] `GOOGLE_CLIENT_ID` - OAuth 2.0 Client ID
- [ ] `GOOGLE_CLIENT_SECRET` - OAuth 2.0 Client Secret

### Already Configured in render.yaml:
- ✅ `GOOGLE_REDIRECT_URI` = `https://cerebrum-api.onrender.com/api/v1/connectors/google-drive/callback`

### Other Critical Vars:
- ✅ `DATABASE_URL` - From PostgreSQL
- ✅ `REDIS_URL` - From Redis
- ✅ `SECRET_KEY` - Auto-generated
- ✅ `USE_STUB_CONNECTORS` = `false` (just pushed)

## How to Check/Set:

1. Go to: https://dashboard.render.com/web/srv-d69j8av5r7bs73f9au40/env-vars
2. Look for GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
3. If missing, add them from: https://console.cloud.google.com/apis/credentials

## Get Google OAuth Credentials:

1. Visit: https://console.cloud.google.com/apis/credentials
2. Select project: `cerebrum-30d9c`
3. Click on your OAuth 2.0 Client ID
4. Copy Client ID and Client Secret
5. Paste into Render dashboard

**Cannot verify automatically due to API permissions. Please check manually.**
