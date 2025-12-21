# OAuth Setup Instructions

## Current Status

The Gmail API OAuth setup is **INCOMPLETE** due to Google Cloud Console restrictions:
- ✅ OAuth consent screen configured
- ✅ Test user added (vincidphysio@gmail.com)
- ✅ OAuth Desktop client created
- ❌ **Client credentials NOT downloadable** (Google Cloud policy change)
- ❌ Refresh token generation PENDING

## Problem

Google Cloud Console no longer allows downloading OAuth client secrets after creation. The secret is masked as `****Bx7L`.

## Solution Options

### Option 1: Manual OAuth Flow (RECOMMENDED)

Since we cannot download the desktop client credentials, we'll manually generate a refresh token:

1. **Get Client Info from Google Cloud Console:**
   - Client ID: `67627505170-5dtavfobn1k87b3cs89if6538a7chbbd.apps.googleusercontent.com`
   - Client Secret: Contact @vincidphysio to add a new secret and capture it immediately

2. **Generate Authorization URL:**
```
https://accounts.google.com/o/oauth2/v2/auth?client_id=67627505170-5dtavfobn1k87b3cs89if6538a7chbbd.apps.googleusercontent.com&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/gmail.readonly+https://www.googleapis.com/auth/spreadsheets&access_type=offline&prompt=consent
```
*Note: The `urn:ietf:wg:oauth:2.0:oob` redirect URI is deprecated. If it fails, you may need to use a local server or a different flow.*

3. **Visit the URL** and authorize access
4. **Copy the authorization code** from the response
5. **Exchange for refresh token** using:
```bash
curl -X POST https://oauth2.googleapis.com/token \
  -d code=YOUR_AUTH_CODE \
  -d client_id=67627505170-5dtavfobn1k87b3cs89if6538a7chbbd.apps.googleusercontent.com \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d redirect_uri=urn:ietf:wg:oauth:2.0:oob \
  -d grant_type=authorization_code
```

6. **Add secrets to GitHub Actions:**
   - `OAUTH_CLIENT_ID`: 67627505170-5dtavfobn1k87b3cs89if6538a7chbbd.apps.googleusercontent.com
   - `OAUTH_CLIENT_SECRET`: (from step 1)
   - `OAUTH_REFRESH_TOKEN`: (from step 5)

### Option 2: Use Service Account (ALTERNATIVE)

Service accounts don't work with personal Gmail. Skip this option.

## Next Steps

1. **USER ACTION REQUIRED:** Add a new client secret in Google Cloud Console
2. Generate refresh token using Option 1
3. Add OAuth secrets to GitHub Actions
4. Update `gmail_sync.py` to use OAuth instead of service account
5. Test GitHub Actions workflow

## Resources

- [Google OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Gmail API Scopes](https://developers.google.com/gmail/api/auth/scopes)
