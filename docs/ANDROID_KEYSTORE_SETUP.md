# Android Keystore Setup Guide

This guide covers how to set up keystores for signing Android APKs, from debug builds to production releases.

---

## Quick Start: Debug Builds

Debug builds use an automatically generated debug keystore. The CI workflow generates one if it doesn't exist.

**No setup required** - Just push to main and download the APK from GitHub Actions.

---

## Production Keystore Setup

For production releases, you need a proper signing keystore. Follow these steps:

### 1. Generate Production Keystore

Run this command on your local machine (keep the file secure):

```bash
keytool -genkey -v \
  -keystore cerebrum-release.keystore \
  -alias cerebrum \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -dname "CN=Your Name,O=Your Organization,C=US"
```

You'll be prompted for passwords. **Save these securely** - you'll need them for GitHub secrets.

### 2. Convert Keystore to Base64

For storing in GitHub secrets, convert the keystore to base64:

```bash
base64 -i cerebrum-release.keystore | pbcopy  # macOS
base64 -i cerebrum-release.keystore -w 0 | xclip -selection clipboard  # Linux
base64 -i cerebrum-release.keystore -w 0  # Output to terminal, then copy
```

### 3. Add GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `ANDROID_KEYSTORE_BASE64` | Base64-encoded keystore file | `LS0tLS1...` |
| `ANDROID_KEYSTORE_PASSWORD` | Keystore password | `your-keystore-pass` |
| `ANDROID_KEY_ALIAS` | Key alias from keystore | `cerebrum` |
| `ANDROID_KEY_PASSWORD` | Key password (if different) | `your-key-pass` |

### 4. Optional: Environment Variables

If your app needs API URLs:

| Secret Name | Description |
|-------------|-------------|
| `VITE_API_URL` | Backend API URL |
| `VITE_FRONTEND_URL` | Frontend URL |

---

## Keystore Management Best Practices

### 🔒 Security
- **Never commit** keystore files to git
- **Back up** your keystore file in a secure location (encrypted cloud, password manager)
- **Use strong passwords** for both keystore and key
- **Keep the alias** consistent across builds

### 📱 Google Play Store
If publishing to Play Store:
1. Use App Signing by Google Play (recommended)
2. Generate an upload keystore (same process as above)
3. Google will manage the signing key for distribution

### 🔄 Lost Keystore?
If you lose your keystore:
- **Cannot update existing app** on Play Store
- Must create new app listing with new package name
- This is why backups are critical!

---

## Local Building with Signing

To build locally with the release keystore:

1. Place `cerebrum-release.keystore` in `frontend/android/app/`

2. Create `frontend/android/keystore.properties`:
```properties
storeFile=release.keystore
storePassword=your-keystore-password
keyAlias=cerebrum
keyPassword=your-key-password
```

3. Build:
```bash
cd frontend/android
./gradlew assembleRelease
```

The signed APK will be at:
`frontend/android/app/build/outputs/apk/release/app-release.apk`

---

## Troubleshooting

### "Keystore file not found"
- Check the base64 encoding is correct
- Verify secret name matches exactly

### "Invalid keystore format"
- Ensure you uploaded base64, not raw binary
- Check the file wasn't corrupted during encoding

### "Password verification failed"
- Double-check password secrets match what you used to create the keystore
- Key password and keystore password may be different

### Build fails with signing error
- Verify all 4 signing secrets are set
- Check the key alias matches what you used when creating the keystore
