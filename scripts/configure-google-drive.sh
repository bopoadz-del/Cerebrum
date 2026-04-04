#!/bin/bash
# Google Drive OAuth Configuration Helper
set -e

echo "=== Google Drive OAuth Configuration ==="
echo ""

# Check if GOOGLE_CLIENT_SECRET is set
if [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "❌ ERROR: GOOGLE_CLIENT_SECRET environment variable is not set!"
    echo ""
    echo "To fix this:"
    echo "1. Get your Client Secret from Google Cloud Console:"
    echo "   https://console.cloud.google.com/apis/credentials"
    echo "   (Download the JSON or copy the 'Client secret' value)"
    echo ""
    echo "2. Set the environment variable:"
    echo "   export GOOGLE_CLIENT_SECRET='your-actual-client-secret-here'"
    echo ""
    echo "3. Then run this script again:"
    echo "   ./scripts/configure-google-drive.sh"
    exit 1
fi

echo "✅ GOOGLE_CLIENT_SECRET is set"
echo ""

# Show current configuration
echo "=== Current Configuration ==="
echo "GOOGLE_REDIRECT_URI: $(grep GOOGLE_REDIRECT_URI docker-compose.yml | head -1 | cut -d'=' -f2)"
echo "GOOGLE_CLIENT_ID: $(grep GOOGLE_CLIENT_ID docker-compose.yml | head -1 | cut -d'=' -f2)"
echo "SECRET_KEY: (using existing default)"
echo ""

echo "=== Restarting backend with new configuration ==="
docker compose up -d --force-recreate backend

echo ""
echo "=== Verifying configuration inside container ==="
sleep 2
docker compose exec -T backend sh -c 'echo "GOOGLE_REDIRECT_URI=$GOOGLE_REDIRECT_URI"; echo "GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID"; echo "GOOGLE_CLIENT_SECRET is set: $(if [ -n "$GOOGLE_CLIENT_SECRET" ]; then echo "YES (length: ${#GOOGLE_CLIENT_SECRET})"; else echo "NO"; fi)"'

echo ""
echo "=== Testing OAuth URL Generation ==="
docker compose exec -T backend python - <<'PY'
import os
client_id = os.getenv("GOOGLE_CLIENT_ID")
redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

if not client_id:
    print("❌ GOOGLE_CLIENT_ID is missing!")
elif not client_secret:
    print("❌ GOOGLE_CLIENT_SECRET is missing!")
elif not redirect_uri:
    print("❌ GOOGLE_REDIRECT_URI is missing!")
else:
    print("✅ All Google OAuth environment variables are set")
    print(f"   Client ID: {client_id[:20]}...")
    print(f"   Redirect URI: {redirect_uri}")
    print(f"   Client Secret length: {len(client_secret)}")
PY

echo ""
echo "=== Instructions to complete OAuth setup ==="
echo ""
echo "1. Make sure your Google Cloud Console OAuth app has this redirect URI added:"
echo "   https://silver-couscous-7v45rj6qg6qvcwqxw-8000.app.github.dev/api/v1/connectors/google-drive/callback"
echo ""
echo "2. Get a fresh auth URL by running:"
echo "   docker compose exec -T backend python - <<'PY'"
echo "   import httpx"
echo "   BASE='http://127.0.0.1:8000'"
echo "   with httpx.Client(timeout=30) as c:"
echo "       token = c.post(f'{BASE}/api/v1/auth/login', json={'email': 'you@domain.com', 'password': 'YourStrongPass123!', 'mfa_code': None}).json()['access_token']"
echo "       r = c.get(f'{BASE}/api/v1/connectors/google-drive/auth/url', headers={'Authorization': f'Bearer {token}'})"
echo "       print(r.json()['auth_url'])"
echo "   PY"
echo ""
echo "3. Copy the URL and open it in an INCOGNITO browser window"
echo ""
echo "4. After authorizing, Google will redirect to your callback URL"
echo ""
