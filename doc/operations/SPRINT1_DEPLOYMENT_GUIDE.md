# Sprint 1 Deployment Guide
## Filters & Search System - Staging Deployment

**Version:** 1.0.0  
**Date:** November 12, 2025  
**Target Environment:** Staging  
**Features:** Multi-select filters, fuzzy search, autocomplete, URL persistence, accessibility

---

## 📋 Pre-Deployment Checklist

### Code Quality ✅
- [x] All 156 frontend tests passing
- [x] All backend tests passing
- [x] Zero linting errors
- [x] Zero TypeScript errors
- [x] Bundle size within limits (<50KB)

### Documentation ✅
- [x] User documentation complete
- [x] API documentation updated
- [x] Deployment guide created
- [x] Rollback plan documented

### Dependencies ✅
- [x] fuse.js@7.0.0 added to package.json
- [x] @vueuse/core@11.0.0 added to package.json
- [x] No breaking dependency changes
- [x] All dependencies audit clean

---

## 🔧 Environment Requirements

### Frontend
- Node.js: >= 18.0.0
- npm: >= 9.0.0
- Vite: 5.x
- Vue: 3.x

### Backend
- Python: 3.11+
- Django: 5.0+
- PostgreSQL/MySQL: Any version
- Redis: Optional (graceful degradation)

### Environment Variables

#### Required
```bash
# Backend (.env)
DJANGO_SETTINGS_MODULE=settings.staging
SECRET_KEY=<your-secret-key>
DATABASE_URL=<your-database-url>
ALLOWED_HOSTS=staging.provemaps.com

# Feature Flags (optional, defaults to True)
ENABLE_FILTERS=True
ENABLE_SEARCH=True
ENABLE_URL_PERSISTENCE=True

# Static Files
STATIC_URL=/static/
STATIC_ROOT=/var/www/provemaps/static/
STATIC_ASSET_VERSION=1.0.0  # For cache busting
```

#### Frontend (.env.staging)
```bash
VITE_API_BASE_URL=https://staging-api.provemaps.com
VITE_ENABLE_FILTERS=true
VITE_ENABLE_SEARCH=true
VITE_MAX_SEARCH_RESULTS=10
VITE_SEARCH_DEBOUNCE_MS=300
VITE_URL_UPDATE_DEBOUNCE_MS=500
```

#### Optional (Performance)
```bash
# Redis for caching (backend)
REDIS_URL=redis://localhost:6379/0
CHANNEL_LAYER_URL=redis://localhost:6379/1

# Bundle optimization (frontend)
VITE_BUILD_SOURCEMAP=false
VITE_BUILD_MINIFY=true
```

---

## 🚀 Deployment Steps

### 1. Backup Current State

```bash
# Database backup
python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json

# Static files backup
tar -czf static_backup_$(date +%Y%m%d_%H%M%S).tar.gz staticfiles/

# Frontend build backup
tar -czf frontend_backup_$(date +%Y%m%d_%H%M%S).tar.gz frontend/dist/
```

### 2. Pull Latest Code

```bash
# Checkout deployment branch
git fetch origin
git checkout refactor/folder-structure
git pull origin refactor/folder-structure

# Verify commit hash
git log -1 --oneline
# Should show: Sprint 1 complete - Filters & Search System
```

### 3. Backend Deployment

```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\Activate.ps1  # Windows

# Install/update dependencies
pip install -r requirements.txt

# Run migrations (should be none for Sprint 1)
python manage.py migrate --check
python manage.py migrate

# Collect static files with new STATIC_ASSET_VERSION
python manage.py collectstatic --noinput --clear

# Run tests to verify
pytest -q
python manage.py test

# Restart services
sudo systemctl restart gunicorn
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat
```

### 4. Frontend Deployment

```bash
cd frontend

# Install dependencies
npm ci  # Use ci for production (faster, more reliable)

# Build for staging
npm run build

# Verify build output
ls -lh dist/
# Should see index.html, assets/, static/

# Copy to web server
rsync -avz --delete dist/ /var/www/provemaps/frontend/

# Or deploy to CDN/S3
# aws s3 sync dist/ s3://provemaps-staging/frontend/ --delete
```

### 5. Verify Static Asset Version

```bash
# Check static files have version query params
grep -r "STATIC_ASSET_VERSION" frontend/dist/index.html
# Should see: ?v=1.0.0 on static asset URLs

# Verify in browser DevTools Network tab
# All static files should have ?v=1.0.0
```

### 6. Clear CDN/Cache

```bash
# Clear CloudFlare cache (if using)
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'

# Clear Nginx cache (if using)
sudo rm -rf /var/cache/nginx/*
sudo systemctl reload nginx

# Clear browser cache (manual)
# Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
```

### 7. Health Checks

```bash
# Backend health
curl https://staging-api.provemaps.com/health/
# Expected: {"status": "healthy", "version": "1.0.0"}

# Frontend health
curl https://staging.provemaps.com/
# Expected: 200 OK with HTML

# API endpoints
curl https://staging-api.provemaps.com/api/v1/maps/dashboard/cached/
# Expected: Dashboard data with filters

# WebSocket (if using)
wscat -c wss://staging.provemaps.com/ws/dashboard/status/
# Expected: Connection established
```

---

## 🧪 Post-Deployment Validation

### Automated Tests

```bash
# Frontend E2E tests (if available)
npm run test:e2e

# Backend smoke tests
python manage.py test --tag=smoke

# API integration tests
python manage.py test maps_view.tests
python manage.py test inventory.tests
```

### Manual Testing (See QA Checklist)

1. **Filters:**
   - [ ] Can select multiple statuses
   - [ ] Can select multiple types
   - [ ] Can select multiple locations
   - [ ] Filter count updates correctly
   - [ ] Clear all works
   - [ ] Clear individual filters works

2. **Search:**
   - [ ] Search finds devices by name
   - [ ] Search finds devices by IP
   - [ ] Search finds devices by site
   - [ ] Fuzzy matching works (typos)
   - [ ] Autocomplete shows suggestions
   - [ ] Search history persists

3. **URL Persistence:**
   - [ ] URL updates when filters change
   - [ ] URL updates when search query changes
   - [ ] Bookmark works (reload with URL)
   - [ ] Share URL works (copy/paste)
   - [ ] Back/forward buttons work

4. **Accessibility:**
   - [ ] Tab navigation works
   - [ ] Screen reader announces changes
   - [ ] Keyboard shortcuts work
   - [ ] Focus indicators visible
   - [ ] ARIA labels present

5. **Performance:**
   - [ ] Search responds in <300ms
   - [ ] Filter applies in <100ms
   - [ ] No console errors
   - [ ] No memory leaks
   - [ ] Bundle size acceptable

---

## 🔄 Rollback Procedures

### If Deployment Fails

#### Quick Rollback (Frontend Only)
```bash
# Restore previous frontend build
cd /var/www/provemaps/frontend/
tar -xzf /path/to/frontend_backup_TIMESTAMP.tar.gz

# Clear cache
sudo systemctl reload nginx
```

#### Full Rollback (Backend + Frontend)
```bash
# 1. Checkout previous commit
git log --oneline -5  # Find previous commit
git checkout PREVIOUS_COMMIT_HASH

# 2. Restore database (if migrations were run)
python manage.py migrate inventory 0042  # Replace with previous migration

# 3. Restore static files
tar -xzf /path/to/static_backup_TIMESTAMP.tar.gz -C staticfiles/

# 4. Rebuild frontend
cd frontend
npm ci
npm run build

# 5. Restart services
sudo systemctl restart gunicorn celery-worker celery-beat nginx
```

### Verify Rollback
```bash
# Check services
sudo systemctl status gunicorn
sudo systemctl status celery-worker
sudo systemctl status nginx

# Check health endpoints
curl https://staging-api.provemaps.com/health/
curl https://staging.provemaps.com/

# Verify version
# Should show previous version number
```

---

## 📊 Monitoring

### Metrics to Watch

#### Performance
- Page load time (target: <2s)
- Time to Interactive (target: <3s)
- Search response time (target: <300ms)
- Filter response time (target: <100ms)

#### Errors
- JavaScript errors (target: <0.1%)
- API errors (target: <0.5%)
- Failed requests (target: <1%)
- Console warnings (target: 0)

#### Usage
- Search queries per user
- Filter combinations used
- URL shares/bookmarks
- Keyboard navigation usage

### Monitoring Tools

```bash
# Sentry (error tracking)
# Configure in frontend/src/main.js
import * as Sentry from "@sentry/vue";
Sentry.init({
  dsn: "YOUR_SENTRY_DSN",
  environment: "staging",
});

# Google Analytics (usage tracking)
# Configure in frontend/index.html
gtag('config', 'GA_MEASUREMENT_ID');

# Performance monitoring
# Use Lighthouse CI or similar
npm run lighthouse
```

---

## 🐛 Troubleshooting

### Issue: Filters not working

**Symptoms:** Dropdowns don't show, filters don't apply

**Diagnosis:**
```bash
# Check browser console
# Look for: "filtersStore is undefined"

# Check Pinia store loaded
# DevTools > Vue > Pinia
```

**Solution:**
```bash
# Verify stores imported in main.js
grep -n "createPinia" frontend/src/main.js

# Clear browser cache and reload
# Hard refresh: Ctrl+Shift+R
```

---

### Issue: Search not working

**Symptoms:** Search input doesn't respond, no suggestions

**Diagnosis:**
```bash
# Check fuse.js loaded
npm list fuse.js
# Should show: fuse.js@7.0.0

# Check console errors
# Look for: "Fuse is not defined"
```

**Solution:**
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Rebuild
npm run build
```

---

### Issue: URL persistence not working

**Symptoms:** URL doesn't update, refresh loses filters

**Diagnosis:**
```bash
# Check Vue Router configured
grep -n "createRouter" frontend/src/main.js

# Check useUrlSync initialized
grep -n "useUrlSync" frontend/src/components/Dashboard/DashboardView.vue
```

**Solution:**
```bash
# Verify DashboardView.vue has:
# const router = useRouter()
# const route = useRoute()
# useUrlSync(filtersStore, router, route)

# Check browser supports history API
# window.history.pushState should exist
```

---

### Issue: Accessibility features missing

**Symptoms:** Screen reader doesn't announce, keyboard nav broken

**Diagnosis:**
```bash
# Check ARIA attributes in HTML
curl https://staging.provemaps.com/ | grep -i "aria-"

# Run accessibility audit
npm run lighthouse -- --only-categories=accessibility
```

**Solution:**
```bash
# Verify components have ARIA attributes
grep -r "aria-label" frontend/src/components/

# Check CSS not hiding focus
grep -r "outline: none" frontend/src/ --exclude-dir=node_modules
```

---

### Issue: Performance degradation

**Symptoms:** Slow search, slow filtering, high memory usage

**Diagnosis:**
```bash
# Check bundle size
npm run build
ls -lh dist/assets/*.js

# Profile in DevTools
# Performance tab > Record > Perform action > Stop
```

**Solution:**
```bash
# Verify debouncing in place
grep -n "useDebounceFn" frontend/src/components/search/SearchInput.vue

# Check for memory leaks
# DevTools > Memory > Take heap snapshot > Compare
```

---

## 📞 Support Contacts

- **DevOps Lead:** devops@provemaps.com
- **Backend Lead:** backend@provemaps.com
- **Frontend Lead:** frontend@provemaps.com
- **QA Lead:** qa@provemaps.com
- **Emergency:** +1-555-URGENT

---

## 📚 Additional Resources

- [Sprint 1 Complete Summary](../roadmap/SPRINT1_COMPLETE_SUMMARY.md)
- [QA Testing Checklist](./SPRINT1_QA_CHECKLIST.md)
- [Rollback Plan](./SPRINT1_ROLLBACK_PLAN.md)
- [User Documentation](../guides/FILTERS_AND_SEARCH.md)
- [API Documentation](../api/FILTERS_API.md)

---

**Deployment Prepared By:** AI Assistant  
**Approved By:** _____________  
**Deployed By:** _____________  
**Deployment Date:** _____________  
**Deployment Time:** _____________  
**Deployment Duration:** _____________  
**Status:** ✅ Success / ❌ Failed / ⏸️ Rolled Back
