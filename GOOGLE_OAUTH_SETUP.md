# Google OAuth Setup for Render

## Environment Variables to Add in Render Dashboard

Go to: https://dashboard.render.com/ → Select `cerebrum-api` → Environment

Add these environment variables:

```bash
GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=https://cerebrum-api.onrender.com/api/v1/drive/auth/callback
FRONTEND_URL=https://cerebrum-frontend.onrender.com
```

**Note:** The actual Client ID and Secret have been provided separately. Set them in the Render dashboard, NOT in code.

## Google Cloud Console Configuration

1. Go to: https://console.cloud.google.com/apis/credentials
2. Select your project
3. Click on your OAuth 2.0 Client ID
4. Add these **Authorized Redirect URIs**:
   - `https://cerebrum-api.onrender.com/api/v1/drive/auth/callback`
   - `http://localhost:8000/api/v1/drive/auth/callback` (for local development)

5. Add these **Authorized JavaScript Origins**:
   - `https://cerebrum-frontend.onrender.com`
   - `http://localhost:3000` (for local development)

6. Enable Google Drive API:
   - Go to: https://console.cloud.google.com/apis/library
   - Search "Google Drive API"
   - Click "Enable"

## Test the Integration

After deployment, test with chat command:
```
/connect drive
```

You should see an OAuth popup for Google Drive authorization.
