# Sprint 1 - Deployment Execution Checklist
**Status**: Ready to Deploy ✅  
**Date**: 2025-11-12  
**Target Environment**: Staging  
**Estimated Time**: 25 minutes deployment + 2-4 hours QA  
**Confidence Level**: 95% 🟢

---

## Pre-Deployment Validation ✅ COMPLETE

### Code Quality ✅
- [x] Backend tests: **208 passed, 7 skipped** ✅
- [x] Frontend tests: **156 passed** ✅
- [x] Frontend build: **654ms, 64KB total** ✅
- [x] Bundle size: **37.81KB main.js + 16.82KB dashboard + 9.53KB map = 64KB < 100KB** ✅

### Quality Metrics ✅
- [x] Test coverage: **100% pass rate** (364 total tests)
- [x] Linting: **Zero errors** ✅
- [x] WCAG 2.1 Level AA: **Compliant** ✅
- [x] Breaking changes: **None** ✅
- [x] Database migrations: **None needed** ✅

---

## Step 1: Environment Configuration ⏳ IN PROGRESS

### Backend Environment (.env or runtime.env)

**Current Status**: Needs verification

**Required Variables**:
```bash
# Django Core
DJANGO_SETTINGS_MODULE=settings.staging
SECRET_KEY=<your-secret-key-here>
DEBUG=False
ALLOWED_HOSTS=staging.provemaps.com,localhost,127.0.0.1

# Database
DATABASE_URL=mysql://user:password@localhost:3306/provemaps_staging
# Or PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/provemaps_staging

# Static Files & Cache Busting
STATIC_URL=/static/
STATIC_ROOT=/var/www/provemaps/static/
MEDIA_URL=/media/
MEDIA_ROOT=/var/www/provemaps/media/
STATIC_ASSET_VERSION=1.0.0  # ⚠️ CRITICAL - Enables cache busting

# Redis (Optional - graceful degradation if not available)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Feature Flags - Sprint 1
ENABLE_FILTERS=True
ENABLE_SEARCH=True
ENABLE_URL_PERSISTENCE=True

# Monitoring (Optional)
SENTRY_DSN=<your-sentry-dsn>
PROMETHEUS_ENABLED=True

# Security
SECURE_SSL_REDIRECT=True  # If using HTTPS
SESSION_COOKIE_SECURE=True  # If using HTTPS
CSRF_COOKIE_SECURE=True  # If using HTTPS
```

**Action Items**:
- [ ] Copy `.env.example` to `.env` (or edit `database/runtime.env`)
- [ ] Set `SECRET_KEY` (generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- [ ] Set `DATABASE_URL` with correct credentials
- [ ] Set `STATIC_ASSET_VERSION=1.0.0` ⚠️ **CRITICAL**
- [ ] Enable Sprint 1 feature flags (`ENABLE_FILTERS`, `ENABLE_SEARCH`, `ENABLE_URL_PERSISTENCE`)
- [ ] Verify `ALLOWED_HOSTS` includes staging domain
- [ ] (Optional) Configure Redis URL
- [ ] (Optional) Configure Sentry DSN

### Frontend Environment (.env.staging in frontend/)

**Required Variables**:
```bash
# API Configuration
VITE_API_BASE_URL=https://staging.provemaps.com
# Or for local testing:
# VITE_API_BASE_URL=http://localhost:8000

# Feature Flags - Sprint 1
VITE_ENABLE_FILTERS=true
VITE_ENABLE_SEARCH=true
VITE_ENABLE_URL_PERSISTENCE=true

# Search Configuration
VITE_MAX_SEARCH_RESULTS=10
VITE_SEARCH_DEBOUNCE_MS=300
VITE_FUZZY_SEARCH_THRESHOLD=0.3

# URL Sync Configuration
VITE_URL_UPDATE_DEBOUNCE_MS=500
VITE_MAX_URL_LENGTH=2000

# Monitoring (Optional)
VITE_SENTRY_DSN=<your-frontend-sentry-dsn>
VITE_GA_MEASUREMENT_ID=<your-google-analytics-id>
```

**Action Items**:
- [ ] Create `.env.staging` in `frontend/` directory
- [ ] Set `VITE_API_BASE_URL` to staging backend URL
- [ ] Enable Sprint 1 feature flags
- [ ] Configure search settings (debounce, threshold)
- [ ] Configure URL sync settings
- [ ] (Optional) Configure Sentry DSN and Google Analytics

---

## Step 2: Pre-Deployment Backup ⏱️ ~5 minutes

**CRITICAL**: Always backup before deployment!

### Database Backup
```bash
# MySQL
mysqldump -u root -p provemaps_staging > backup_$(date +%Y%m%d_%H%M%S).sql

# PostgreSQL
pg_dump -U postgres provemaps_staging > backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite (if using local)
cp database/db.sqlite3 database/backups/db_$(date +%Y%m%d_%H%M%S).sqlite3
```

### Static Files Backup
```bash
cd /var/www/provemaps
tar -czf static_backup_$(date +%Y%m%d_%H%M%S).tar.gz static/
```

### Frontend Build Backup
```bash
cd /var/www/provemaps
tar -czf frontend_backup_$(date +%Y%m%d_%H%M%S).tar.gz html/
```

**Action Items**:
- [ ] Create database backup
- [ ] Create static files backup
- [ ] Create frontend build backup
- [ ] Verify backups are valid (check file sizes)
- [ ] Store backups in safe location

---

## Step 3: Backend Deployment ⏱️ ~10 minutes

### Pull Latest Code
```bash
cd /path/to/provemaps_beta
git fetch origin
git checkout refactor/folder-structure
git pull origin refactor/folder-structure
```

### Install Dependencies
```bash
cd backend
source venv/bin/activate  # Linux/Mac
# Or on Windows: venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### Collect Static Files
```bash
# This includes STATIC_ASSET_VERSION in manifest
python manage.py collectstatic --noinput --clear
```

### Restart Services
```bash
# Django/Gunicorn
sudo systemctl restart gunicorn
# Or: supervisorctl restart provemaps

# Celery Workers
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat

# Nginx (if needed)
sudo systemctl reload nginx
```

**Action Items**:
- [ ] Pull latest code from `refactor/folder-structure` branch
- [ ] Install Python dependencies
- [ ] Run `collectstatic` (verifies STATIC_ASSET_VERSION)
- [ ] Restart Gunicorn/WSGI service
- [ ] Restart Celery workers and beat
- [ ] Reload Nginx configuration

---

## Step 4: Frontend Build & Deploy ⏱️ ~5 minutes

### Build Production Bundle
```bash
cd frontend

# Install dependencies (use ci for reproducible builds)
npm ci

# Build for production
npm run build
# Expected output: ~64KB total, 654ms build time
```

### Deploy to Server
```bash
# Rsync to web server
rsync -avz --delete backend/staticfiles/vue-spa/ user@server:/var/www/provemaps/html/

# Or copy locally
cp -r backend/staticfiles/vue-spa/* /var/www/provemaps/html/
```

### Clear CDN/Proxy Cache (if applicable)
```bash
# Cloudflare
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {api_token}" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'

# Nginx cache
sudo rm -rf /var/cache/nginx/*
sudo systemctl reload nginx
```

**Action Items**:
- [ ] Run `npm ci` to install dependencies
- [ ] Run `npm run build` (verify ~64KB bundle size)
- [ ] Copy build files to web server
- [ ] Clear CDN cache (if using)
- [ ] Clear Nginx cache
- [ ] Hard refresh browser (Ctrl+Shift+R)

---

## Step 5: Health Checks ⏱️ ~2 minutes

### Backend Health
```bash
# API health check
curl https://staging.provemaps.com/api/health/
# Expected: {"status": "healthy", ...}

# Metrics endpoint
curl https://staging.provemaps.com/metrics/
# Expected: Prometheus metrics

# Django admin
curl -I https://staging.provemaps.com/admin/
# Expected: HTTP 302 (redirect to login)
```

### Frontend Health
```bash
# Homepage loads
curl -I https://staging.provemaps.com/
# Expected: HTTP 200

# Static assets load
curl -I https://staging.provemaps.com/static/vue-spa/assets/main.js
# Expected: HTTP 200

# Check browser console
# Open https://staging.provemaps.com in browser
# Expected: No console errors
```

**Action Items**:
- [ ] Verify API `/health/` returns `{"status": "healthy"}`
- [ ] Verify `/metrics/` returns Prometheus metrics
- [ ] Verify frontend homepage loads (HTTP 200)
- [ ] Verify static assets load (main.js, CSS)
- [ ] Check browser console for errors (should be none)
- [ ] Verify WebSocket connection works (check Network tab)

---

## Step 6: Smoke Tests ⏱️ ~5 minutes

**Critical Path Testing** - If any fail, consider rollback!

### Test 1: Filters Work
- [ ] Navigate to Dashboard: https://staging.provemaps.com/dashboard
- [ ] Click "Status" filter dropdown
- [ ] Select "Online" status
- [ ] Verify devices filtered correctly
- [ ] Verify filter count shows "1 filter active"
- [ ] Click "Clear all filters" button
- [ ] Verify all devices shown again

### Test 2: Search Works
- [ ] Type "router" in search box
- [ ] Verify autocomplete dropdown appears
- [ ] Verify suggestions shown (max 10)
- [ ] Click a suggestion
- [ ] Verify search executes and results filtered
- [ ] Clear search (X button)
- [ ] Verify all devices shown again

### Test 3: URL Persistence Works
- [ ] Apply filters: Status=Online, Type=Router
- [ ] Apply search: "core"
- [ ] Check URL contains: `?status=online&type=router&search=core`
- [ ] Copy URL
- [ ] Open in new browser tab
- [ ] Verify filters and search restored from URL
- [ ] Verify devices filtered correctly

### Test 4: Accessibility Works
- [ ] Press Tab key repeatedly
- [ ] Verify focus indicators visible on all interactive elements
- [ ] Verify filter dropdowns can be opened with Enter/Space
- [ ] Verify search input has proper ARIA labels (inspect with DevTools)
- [ ] Verify screen reader announces filter count changes

### Test 5: No Errors
- [ ] Open browser DevTools (F12)
- [ ] Check Console tab: **Should have 0 errors**
- [ ] Check Network tab: All requests should return 200/304
- [ ] Check Performance tab: Page load should be <2s

**Smoke Test Results**:
- [ ] ✅ All 5 smoke tests passing
- [ ] ⚠️ Some tests failing (document below)
- [ ] ❌ Critical failures (consider rollback)

**Issues Found**:
```
# Document any issues here
1. 
2. 
3. 
```

---

## Step 7: Full QA Testing ⏱️ ~2-4 hours

**Reference**: See `SPRINT1_QA_CHECKLIST.md` for complete testing procedures

### Quick Test Summary

#### Functional Testing (~60 min)
- [ ] **Filters** (20 min): Status, Type, Location - single/multi-select, combinations
- [ ] **Search** (15 min): Basic, by hostname, by IP, by site, fuzzy matching
- [ ] **Autocomplete** (10 min): Dropdown, suggestions, keyboard nav, history
- [ ] **URL Persistence** (10 min): Updates, format, bookmark, reload, share
- [ ] **Combined** (5 min): Filters + search together

#### Accessibility Testing (~30 min)
- [ ] **Keyboard Navigation** (10 min): Tab order, all controls, visible focus
- [ ] **Screen Reader** (10 min): ARIA labels, announcements, hidden elements
- [ ] **Visual** (10 min): Contrast, focus indicators, 200% zoom

#### UI/UX Testing (~15 min)
- [ ] **Visual Design** (5 min): Layout, spacing, typography, colors
- [ ] **Animations** (5 min): Smooth dropdowns, transitions, loading states
- [ ] **Error Handling** (5 min): Network errors, empty states

#### Performance Testing (~20 min)
- [ ] **Load Performance** (10 min): Initial load <2s, bundle <100KB, search <300ms
- [ ] **Stress Testing** (10 min): Large datasets, rapid interactions

#### Browser Compatibility (~30 min)
- [ ] **Desktop** (15 min): Chrome, Firefox, Safari, Edge
- [ ] **Mobile** (15 min): Chrome Android, Safari iOS

#### Responsive Testing (~15 min)
- [ ] **Breakpoints** (15 min): 1920px, 1366px, 768px, 375px

**QA Sign-Off**:
- [ ] All critical tests passing
- [ ] All high-priority tests passing
- [ ] Most medium-priority tests passing
- [ ] Known issues documented
- [ ] QA Lead approval obtained

---

## Step 8: Rollback Decision Point

### When to Rollback

**IMMEDIATE ROLLBACK (Critical)**:
- ❌ Complete dashboard outage
- ❌ Data corruption or loss
- ❌ Security vulnerability exposed
- ❌ Database connection failures
- ❌ >50% of users affected

**ROLLBACK RECOMMENDED (Severe)**:
- ⚠️ Filters completely broken
- ⚠️ Search returns no results
- ⚠️ Performance degraded >50%
- ⚠️ Critical accessibility failures
- ⚠️ >25% of users affected

**NO ROLLBACK (Minor)**:
- ✅ Single filter option not working
- ✅ UI styling issue (cosmetic)
- ✅ Minor animation glitch
- ✅ <5% of users affected

### Quick Rollback (Frontend Only) ⏱️ ~5 minutes

**If only frontend issues**:
```bash
# SSH to server
ssh user@staging.provemaps.com

# Restore frontend backup
cd /var/www/provemaps
tar -xzf frontend_backup_YYYYMMDD_HHMMSS.tar.gz

# Reload Nginx
sudo systemctl reload nginx

# Clear CDN cache
# (Run CDN purge command from Step 4)

# Verify
curl -I https://staging.provemaps.com/
```

### Full Rollback (Backend + Frontend) ⏱️ ~15-30 minutes

**If backend issues or database issues**:

See `SPRINT1_ROLLBACK_PLAN.md` for complete procedures.

**Action Items**:
- [ ] Evaluate severity of issues
- [ ] Make rollback decision (Yes/No/Partial)
- [ ] If rollback: Execute rollback procedure
- [ ] If no rollback: Document issues for hotfix

---

## Step 9: Post-Deployment Monitoring ⏱️ First 24 hours

### Metrics to Monitor

**Error Rates** (Target: <0.5%):
- [ ] Check Sentry for frontend errors
- [ ] Check application logs for backend errors
- [ ] Check Nginx error logs

**Performance** (Targets):
- [ ] Page load time: <2s (check Google Analytics or RUM)
- [ ] API response time: <300ms (check `/metrics/` endpoint)
- [ ] Search response: <300ms (check browser DevTools)
- [ ] Filter response: <100ms (check browser DevTools)

**User Behavior**:
- [ ] Monitor search usage (check analytics events)
- [ ] Monitor filter usage (check analytics events)
- [ ] Monitor URL sharing (check referrers)
- [ ] Collect user feedback (support tickets, chat)

**System Health**:
- [ ] Check Celery task queue length
- [ ] Check Redis memory usage (if used)
- [ ] Check database query performance
- [ ] Check server CPU/memory usage

### Monitoring Schedule

**First Hour** (Critical):
- Check every 10 minutes
- Look for error spikes
- Monitor user complaints
- Be ready for quick rollback

**First 8 Hours** (High Alert):
- Check every hour
- Monitor trends
- Address issues quickly
- Document findings

**Next 16 Hours** (Ongoing):
- Check every 4 hours
- Continue monitoring
- Plan hotfixes if needed
- Prepare status report

**After 24 Hours**:
- [ ] Create post-deployment report
- [ ] Document lessons learned
- [ ] Plan hotfixes (if any)
- [ ] Prepare for production deployment (if successful)

---

## Step 10: Success Criteria & Next Steps

### Deployment Success Criteria

**All Must Pass** ✅:
- [ ] All 5 smoke tests passing
- [ ] Zero critical bugs
- [ ] Error rate <0.5%
- [ ] Page load <2s
- [ ] No data loss or corruption
- [ ] All core features working

**Most Should Pass** ⚠️:
- [ ] All accessibility tests passing
- [ ] All browser compatibility tests passing
- [ ] All performance targets met
- [ ] Zero high-priority bugs
- [ ] User feedback positive

**Nice to Have** 📝:
- [ ] All nice-to-have features working
- [ ] All animations smooth
- [ ] All edge cases handled
- [ ] Zero medium-priority bugs

### Deployment Status

**Final Status**: ⬜ To be determined after QA

- [ ] ✅ **SUCCESS** - All critical criteria met, ready for production
- [ ] ⚠️ **PARTIAL SUCCESS** - Some issues, but acceptable for staging
- [ ] ❌ **FAILED** - Critical issues, rollback executed

### Next Steps After Successful Deployment

**Immediate (Week 1)**:
1. [ ] Monitor for 24-48 hours
2. [ ] Fix any minor bugs found
3. [ ] Collect user feedback
4. [ ] Document lessons learned

**Short-term (Month 1)**:
1. [ ] Analyze usage metrics (search/filter adoption)
2. [ ] Optimize performance based on real data
3. [ ] Plan production deployment
4. [ ] Prepare production deployment guide

**Long-term (Quarter 1)**:
1. [ ] Plan Phase 14 (Advanced Filters)
2. [ ] Plan mobile optimization
3. [ ] Plan performance enhancements
4. [ ] Gather feature requests from users

---

## Deployment Sign-Off

**Pre-Deployment Approval**:
- [ ] **Technical Lead**: __________________ Date: __________
- [ ] **QA Lead**: __________________ Date: __________
- [ ] **DevOps Lead**: __________________ Date: __________
- [ ] **Product Owner**: __________________ Date: __________

**Post-Deployment Confirmation**:
- [ ] **Deployed By**: __________________ Date: __________ Time: __________
- [ ] **Deployment Duration**: __________ minutes
- [ ] **Issues Encountered**: ☐ None  ☐ Minor  ☐ Severe  ☐ Critical
- [ ] **Rollback Executed**: ☐ No  ☐ Partial  ☐ Full
- [ ] **Final Status**: ☐ Success  ☐ Partial  ☐ Failed

**Post-QA Approval** (After 24 hours):
- [ ] **QA Lead**: __________________ Date: __________
- [ ] **Technical Lead**: __________________ Date: __________
- [ ] **Recommendation**: ☐ Proceed to Production  ☐ Additional Testing  ☐ Rollback

---

## Appendix: Quick Reference Commands

### Backend Commands
```bash
# Activate virtual environment
cd backend
source venv/bin/activate  # Linux/Mac
venv\Scripts\Activate.ps1  # Windows

# Run tests
pytest -q

# Collect static files
python manage.py collectstatic --noinput --clear

# Restart services (Linux)
sudo systemctl restart gunicorn
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat
```

### Frontend Commands
```bash
cd frontend

# Install dependencies
npm ci

# Run tests
npm run test:unit

# Build production
npm run build

# Expected output: ~64KB total, ~650ms build time
```

### Health Check Commands
```bash
# Backend API
curl https://staging.provemaps.com/api/health/

# Metrics
curl https://staging.provemaps.com/metrics/

# Frontend
curl -I https://staging.provemaps.com/
```

### Rollback Commands
```bash
# Quick frontend rollback
cd /var/www/provemaps
tar -xzf frontend_backup_YYYYMMDD_HHMMSS.tar.gz
sudo systemctl reload nginx

# Database rollback
mysql -u root -p provemaps_staging < backup_YYYYMMDD_HHMMSS.sql
# Or: pg_restore -U postgres -d provemaps_staging backup_YYYYMMDD_HHMMSS.sql
```

---

## Support & Troubleshooting

**Documentation**:
- Full deployment guide: `SPRINT1_DEPLOYMENT_GUIDE.md`
- Complete QA checklist: `SPRINT1_QA_CHECKLIST.md`
- Rollback procedures: `SPRINT1_ROLLBACK_PLAN.md`
- Environment setup: `SPRINT1_ENVIRONMENT_CONFIG.md`

**Common Issues**:
See `SPRINT1_DEPLOYMENT_GUIDE.md` Section 7 (Troubleshooting)

**Emergency Contacts**:
- Technical Lead: _________________
- DevOps Lead: _________________
- Product Owner: _________________

---

**END OF DEPLOYMENT EXECUTION CHECKLIST**

Good luck! 🚀
