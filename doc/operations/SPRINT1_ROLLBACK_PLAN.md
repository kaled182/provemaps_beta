# Sprint 1 Rollback Plan
## Filters & Search System - Emergency Recovery

**Version:** 1.0.0  
**Last Updated:** November 12, 2025  
**Purpose:** Emergency procedures to revert Sprint 1 deployment if critical issues arise

---

## 🚨 When to Rollback

### Critical Issues (Immediate Rollback Required)
- [ ] Complete site outage (500 errors, white screen)
- [ ] Data corruption or loss
- [ ] Security vulnerability exposed
- [ ] Cannot load dashboard at all
- [ ] Database errors affecting other features

### Severe Issues (Rollback Recommended)
- [ ] Filters completely broken for all users
- [ ] Search crashes browser consistently
- [ ] Performance degradation >50% (page load >4s)
- [ ] Accessibility completely broken (WCAG violations)
- [ ] Multiple user reports of critical bugs

### Minor Issues (Rollback NOT Recommended)
- [ ] Single filter option not working
- [ ] Search autocomplete intermittent
- [ ] UI styling issues
- [ ] Performance degradation <20%
- [ ] Single browser compatibility issue

**Decision Maker:** Product Owner or Technical Lead

---

## ⚡ Quick Rollback (Frontend Only)

**Use When:** Frontend issue, backend working fine  
**Duration:** ~5 minutes  
**Downtime:** Minimal (refresh required)

### Steps

```bash
# 1. SSH to web server
ssh user@staging.provemaps.com

# 2. Navigate to frontend directory
cd /var/www/provemaps/frontend/

# 3. List available backups
ls -lh /var/www/provemaps/backups/frontend/
# Example: frontend_backup_20251112_100000.tar.gz

# 4. Extract previous backup (dry-run first)
tar -tzf /var/www/provemaps/backups/frontend/frontend_backup_TIMESTAMP.tar.gz | head -20

# 5. Extract to temporary location
mkdir -p /tmp/frontend_rollback
tar -xzf /var/www/provemaps/backups/frontend/frontend_backup_TIMESTAMP.tar.gz -C /tmp/frontend_rollback/

# 6. Stop serving current version (optional, reduces issues)
sudo systemctl stop nginx

# 7. Backup current (broken) version
mv dist dist_broken_$(date +%Y%m%d_%H%M%S)

# 8. Restore previous version
mv /tmp/frontend_rollback/dist ./

# 9. Restart web server
sudo systemctl start nginx
sudo systemctl reload nginx

# 10. Clear CDN cache
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'

# 11. Verify rollback
curl -I https://staging.provemaps.com/
# Should return 200 OK

# 12. Test in browser
# Hard refresh: Ctrl+Shift+R
# Check filters/search removed or previous version working
```

### Verification

- [ ] Site loads without errors
- [ ] Previous version visible (check version number in footer/about)
- [ ] No console errors
- [ ] Basic navigation works
- [ ] Users can access dashboard

---

## 🔄 Full Rollback (Backend + Frontend)

**Use When:** Backend migration issue, data corruption, or full stack problem  
**Duration:** ~15-30 minutes  
**Downtime:** 10-15 minutes

### Pre-Rollback Checklist

- [ ] Notify users of upcoming downtime (email, banner)
- [ ] Set up maintenance page
- [ ] Stop Celery workers to prevent background tasks
- [ ] Backup current state (even if broken) for forensic analysis

### Steps

#### 1. Enable Maintenance Mode

```bash
# Create maintenance page
cat > /var/www/provemaps/frontend/maintenance.html <<EOF
<!DOCTYPE html>
<html>
<head>
  <title>Maintenance - ProveMapsFiber</title>
  <style>
    body { font-family: sans-serif; text-align: center; padding: 50px; }
    h1 { color: #333; }
    p { color: #666; }
  </style>
</head>
<body>
  <h1>🔧 Maintenance in Progress</h1>
  <p>We're rolling back a recent update. The site will be back online shortly.</p>
  <p>Expected downtime: 15 minutes</p>
  <p>Contact: support@provemaps.com</p>
</body>
</html>
EOF

# Configure Nginx to serve maintenance page
sudo nano /etc/nginx/sites-available/provemaps

# Add before location blocks:
# if (-f /var/www/provemaps/frontend/maintenance.html) {
#   return 503;
# }
# error_page 503 @maintenance;
# location @maintenance {
#   root /var/www/provemaps/frontend;
#   rewrite ^(.*)$ /maintenance.html break;
# }

sudo systemctl reload nginx
```

#### 2. Stop Services

```bash
# Stop background workers
sudo systemctl stop celery-worker
sudo systemctl stop celery-beat

# Stop web server (optional, maintenance page already served)
# sudo systemctl stop gunicorn
```

#### 3. Rollback Database

```bash
cd /path/to/backend

# Activate virtual environment
source venv/bin/activate

# Check current migration state
python manage.py showmigrations

# Identify Sprint 1 migrations (should be none, but check)
python manage.py showmigrations inventory | grep '\[X\]'

# If migrations were added, rollback to previous
# Example: python manage.py migrate inventory 0042
# Replace 0042 with the migration before Sprint 1

# Verify no data loss
python manage.py shell
>>> from inventory.models import Site, Device
>>> Site.objects.count()  # Should match pre-Sprint 1 count
>>> Device.objects.count()  # Should match pre-Sprint 1 count
>>> exit()
```

#### 4. Rollback Code

```bash
# Navigate to project root
cd /path/to/provemaps_beta

# Check current commit
git log -1 --oneline
# Example: abc1234 Sprint 1 complete - Filters & Search System

# Find commit before Sprint 1
git log --oneline -10
# Example: def5678 Phase 12 complete

# Checkout previous commit (detached HEAD state)
git checkout def5678

# Or checkout previous tag
git tag -l
git checkout tags/v0.9.0

# Verify correct code
git log -1 --oneline
```

#### 5. Restore Backend Dependencies

```bash
cd backend

# Reinstall dependencies from previous version
pip install -r requirements.txt

# Verify no Sprint 1 dependencies
pip list | grep -i fuse
# Should NOT show fuse.js in Python packages

# Collect static files
python manage.py collectstatic --noinput --clear
```

#### 6. Restore Frontend

```bash
cd frontend

# Reinstall dependencies (previous package-lock.json)
npm ci

# Verify no Sprint 1 dependencies
npm list fuse.js
# Should show error: "extraneous: fuse.js" or not found

# Rebuild frontend
npm run build

# Deploy to web server
rsync -avz --delete dist/ /var/www/provemaps/frontend/
```

#### 7. Restore Database from Backup (if data corrupted)

```bash
# List available backups
ls -lh /var/www/provemaps/backups/database/

# Identify pre-Sprint 1 backup
# Example: backup_20251112_095500.json

# Restore database (CAUTION: overwrites current data)
cd backend
python manage.py flush --noinput  # Clear all data
python manage.py loaddata /var/www/provemaps/backups/database/backup_20251112_095500.json

# Verify data restored
python manage.py shell
>>> from inventory.models import Device
>>> Device.objects.count()  # Check count
>>> exit()
```

#### 8. Restart Services

```bash
# Start web server
sudo systemctl start gunicorn
sudo systemctl status gunicorn

# Start background workers
sudo systemctl start celery-worker
sudo systemctl start celery-beat

# Verify services running
sudo systemctl status gunicorn celery-worker celery-beat
```

#### 9. Disable Maintenance Mode

```bash
# Remove maintenance page
rm /var/www/provemaps/frontend/maintenance.html

# Or remove Nginx maintenance config
sudo nano /etc/nginx/sites-available/provemaps
# Comment out maintenance block

sudo systemctl reload nginx
```

#### 10. Clear Caches

```bash
# Clear Redis cache
redis-cli FLUSHALL

# Clear Nginx cache
sudo rm -rf /var/cache/nginx/*
sudo systemctl reload nginx

# Clear CDN cache
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/purge_cache" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

### Verification

- [ ] Site loads without errors
- [ ] Dashboard accessible
- [ ] No Sprint 1 features visible (filters, search)
- [ ] Previous version features work
- [ ] No console errors
- [ ] No API errors
- [ ] Database queries working
- [ ] Background tasks running

---

## 🧪 Post-Rollback Testing

### Automated Tests

```bash
# Backend tests
cd backend
python manage.py test --tag=smoke

# Frontend tests (if applicable)
cd frontend
npm run test:e2e -- --spec "tests/e2e/smoke.spec.js"
```

### Manual Tests

- [ ] **Homepage:** Loads without errors
- [ ] **Login:** User can authenticate
- [ ] **Dashboard:** Shows devices (no filters/search)
- [ ] **Device Detail:** Device pages work
- [ ] **Map View:** Map displays correctly
- [ ] **Navigation:** All menu items work

### Performance Tests

- [ ] Page load time <2s (vs pre-Sprint 1 baseline)
- [ ] No memory leaks
- [ ] No console errors
- [ ] API response times normal

---

## 📊 Monitoring Post-Rollback

### Metrics to Track (First 2 Hours)

- **Error Rate:** Should drop to <0.5% (pre-Sprint 1 level)
- **Page Load Time:** Should return to <2s
- **API Response Time:** Should return to <200ms
- **User Sessions:** Monitor for drop-off (users might refresh)
- **Console Errors:** Should be minimal/zero

### Alerts to Set

```bash
# Sentry alert for increased error rate
# Alert if error rate > 1% for 5 minutes

# Performance alert
# Alert if page load > 3s for 10 minutes

# Uptime alert
# Alert if site down for >1 minute
```

---

## 📝 Incident Report

### Template

```
INCIDENT REPORT: Sprint 1 Rollback

Date: _______________
Time Started: _______________
Time Resolved: _______________
Duration: _______________

TRIGGER
What caused the rollback?
- [ ] Critical bug: ______________
- [ ] Performance issue: ______________
- [ ] Data corruption: ______________
- [ ] Other: ______________

IMPACT
- Users affected: _______________
- Downtime: _______________
- Data loss: Yes / No
- Features lost: Filters, Search, URL Persistence, Accessibility

ROLLBACK TYPE
- [ ] Quick Rollback (Frontend only)
- [ ] Full Rollback (Backend + Frontend)
- [ ] Database Rollback

TIMELINE
1. [HH:MM] Issue detected
2. [HH:MM] Decision to rollback made
3. [HH:MM] Maintenance mode enabled
4. [HH:MM] Services stopped
5. [HH:MM] Code/DB rolled back
6. [HH:MM] Services restarted
7. [HH:MM] Verification complete
8. [HH:MM] Maintenance mode disabled
9. [HH:MM] Incident closed

ROOT CAUSE
______________________________________________
______________________________________________

LESSONS LEARNED
1. ______________________________________________
2. ______________________________________________
3. ______________________________________________

PREVENTION MEASURES
1. ______________________________________________
2. ______________________________________________
3. ______________________________________________

FOLLOW-UP ACTIONS
- [ ] Fix identified bugs
- [ ] Add missing tests
- [ ] Update deployment procedures
- [ ] Schedule Sprint 1 re-deployment

SIGN-OFF
Incident Manager: _____________
Technical Lead: _____________
Product Owner: _____________
```

---

## 🔮 Prevention for Next Deployment

### Pre-Deployment

- [ ] Run full test suite (backend + frontend)
- [ ] Test in staging for 24+ hours
- [ ] Load test with expected traffic
- [ ] Run accessibility audit
- [ ] Code review by 2+ developers
- [ ] QA sign-off required

### Deployment

- [ ] Deploy during low-traffic window (e.g., 2 AM)
- [ ] Have rollback plan ready
- [ ] Monitor dashboards open
- [ ] Team on standby for 2 hours post-deployment
- [ ] Gradual rollout (e.g., 10% → 50% → 100%)

### Post-Deployment

- [ ] Monitor error rates for 24 hours
- [ ] Check performance metrics
- [ ] Gather user feedback
- [ ] Fix any minor issues quickly
- [ ] Document lessons learned

---

## 📞 Emergency Contacts

### Rollback Decision Chain

1. **On-Call Engineer** → Assess severity
2. **Technical Lead** → Approve rollback if critical/severe
3. **Product Owner** → Inform of decision (async if off-hours)

### Team Contacts

- **DevOps Lead:** devops@provemaps.com / +1-555-DEV-OPS
- **Backend Lead:** backend@provemaps.com / +1-555-BACKEND
- **Frontend Lead:** frontend@provemaps.com / +1-555-FRONTEND
- **Database Admin:** dba@provemaps.com / +1-555-DBA-HELP
- **Emergency Hotline:** +1-555-URGENT

### Escalation

- **Severity 1 (Critical):** Notify all leads immediately
- **Severity 2 (Severe):** Notify technical lead + on-call
- **Severity 3 (Minor):** On-call can handle, inform leads next business day

---

## 📚 Related Documents

- [Deployment Guide](./SPRINT1_DEPLOYMENT_GUIDE.md)
- [QA Checklist](./SPRINT1_QA_CHECKLIST.md)
- [Sprint 1 Complete Summary](../roadmap/SPRINT1_COMPLETE_SUMMARY.md)
- [Incident Response Playbook](./INCIDENT_RESPONSE.md)

---

**Prepared By:** AI Assistant  
**Reviewed By:** _____________  
**Approved By:** _____________  
**Last Tested:** _____________  
**Next Review:** _____________
