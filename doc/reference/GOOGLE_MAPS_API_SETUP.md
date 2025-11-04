# Google Maps API Setup Guide

**Date:** 27 October 2025  
**Component:** routes_builder/fiber-route-builder/  
**Priority:** Critical (the map fails to load without this key)

---

## Executive Summary

The Fiber Route Builder depends on a valid Google Maps JavaScript API key. Without it you will observe:

```
Console error: "Google Maps API not loaded"
Empty map container (<div id="builderMap"> has no content)
TypeError: Cannot read properties of undefined (reading 'maps')
```

Current status: `GOOGLE_MAPS_API_KEY` missing, map features are unavailable.

---

## Obtain an API Key

### 1. Open Google Cloud Console
1. Navigate to https://console.cloud.google.com/
2. Sign in with a Google account (create one if necessary)

### 2. Create or select a project
1. Click "Select a project" at the top
2. Click "New Project"
3. Suggested name: `MapsProveFiber`
4. Click "Create" and wait for completion

### 3. Enable the Maps JavaScript API
1. In the left menu go to "APIs & Services" > "Library"
2. Search for "Maps JavaScript API"
3. Open the result and click "Enable"
4. Wait for activation (10-30 seconds)

### 4. Create credentials (API key)
1. Go to "APIs & Services" > "Credentials"
2. Click "+ Create Credentials" and choose "API key"
3. Copy the generated key (format similar to `AIzaSyC-ExampleKey123456789`)
4. Store the key securely

### 5. Restrict the key
Without restrictions, anyone who finds the key can incur charges.

**Application restrictions:**
- Development: choose "HTTP referrers" and add `http://localhost:8000/*` and `http://127.0.0.1:8000/*`
- Production: add your public domains, for example `https://example.com/*` and `https://*.example.com/*`

**API restrictions:**
1. Select "Restrict key"
2. Check only "Maps JavaScript API"
3. Save

---

## Configure the Project

### Option 1: Local `.env`
File: `.env.local`
```bash
GOOGLE_MAPS_API_KEY=AIzaSyC-ExampleKey123456789
```
Ensure `.env.local` is listed under `env_file` or loaded by Docker Compose.

### Option 2: Docker Compose environment
`docker-compose.yml`
```yaml
services:
  web:
    environment:
      - GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
```
Set the value in `.env` at the repository root:
```bash
GOOGLE_MAPS_API_KEY=AIzaSyC-ExampleKey123456789
```

### Option 3: Admin interface (dynamic configuration)
1. Visit http://localhost:8000/setup/
2. Sign in as an administrator
3. Locate the Google Maps API Key field
4. Paste the key and save

---

## Validate the Configuration

### 1. Check the setting inside the container
```powershell
docker compose exec web python -c "from django.conf import settings; import django; django.setup(); print('GOOGLE_MAPS_API_KEY:', settings.GOOGLE_MAPS_API_KEY or 'NOT SET')"
```
Expected output: the key value, not `NOT SET`.

### 2. Inspect the browser console
1. Open http://localhost:8000/routes/builder/fiber-route-builder/
2. Press F12 and check the Console tab
3. There should be no errors referencing `google.maps`

### 3. Inspect the rendered HTML
```powershell
curl -s http://localhost:8000/routes/builder/fiber-route-builder/ | Select-String "maps.googleapis.com"
```
The script tag must include the API key:
```html
<script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyC-ExampleKey123456789" async defer></script>
```

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
|---------|--------------|------------|
| `google is not defined` | Key missing or not loaded | Confirm the key in `.env`, restart the `web` container |
| `InvalidKeyMapError` | Key revoked or API disabled | Regenerate the key and ensure the API is enabled |
| `RefererNotAllowedMapError` | HTTP referrer restrictions block the request | Add `localhost` and production domains to the allowed referrers |
| Container reports `NOT SET` | Environment variable not injected | Verify `env_file` or `environment` blocks and restart Docker |

To restart the service:
```powershell
docker compose restart web
```

---

## Costs and Limits

Google provides 200 USD of free Maps Platform credit each month. The Maps JavaScript API costs 7 USD per 1000 dynamic map loads, so the free tier covers roughly 28,000 loads. Typical Fiber Route Builder usage is well below this limit.

Recommended: create a billing alert at 10 USD to receive email notifications if usage spikes.

---

## Security Guidelines

**Do:**
- Restrict API keys by HTTP referrer and enabled APIs
- Store keys in environment variables or the configuration UI
- Maintain separate keys for development, staging, and production

**Do not:**
- Commit keys to the repository
- Share keys through unsecured channels
- Leave keys unrestricted in production

---

## Quick Checklist

- [ ] Create a project in Google Cloud Console
- [ ] Enable Maps JavaScript API
- [ ] Generate an API key
- [ ] Apply HTTP referrer and API restrictions
- [ ] Add `GOOGLE_MAPS_API_KEY` to `.env` or the setup interface
- [ ] Restart the `web` container
- [ ] Confirm the map loads and no console errors appear

---

## Expected Result After Configuration

- Browser console contains no Google Maps errors
- The fiber route builder map renders tiles and responds to clicks
- Context menu actions (create, assign, reload) work as expected
- Container logs show no warnings about missing API keys

---

**Document generated automatically.** Refer to https://developers.google.com/maps/documentation for official guides.
