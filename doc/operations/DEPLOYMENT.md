# Production Deployment Guide - MapsProveFiber

**Version**: v2.0.0  
**Last Updated**: 2025-11-07  
**Owner**: DevOps Team

---

## 📖 Overview

This guide covers complete production deployment for **MapsProveFiber**, including:
- Infrastructure requirements and service layout
- Pre-deployment validation and checklist
- Step-by-step deployment procedures
- Health checks and monitoring
- Rollback procedures
- Post-deployment validation

---

## 🏗️ Service Layout

| Service | Port | Description |
|---------|------|-------------|
| **web** | 8000 | Django with Gunicorn + Uvicorn |
| **celery** | - | Celery worker for async tasks |
| **beat** | - | Celery beat scheduler |
| **redis** | 6379 | Cache and message broker |
| **db** | 3306 | MariaDB or MySQL |

---

## 🔴 Critical: Redis High Availability

Development runs a single Redis instance, which becomes a **single point of failure** in production. Use one of the following approaches for high availability.

### Option A: Managed Redis (Preferred)
Use a cloud managed service with replication:
- AWS ElastiCache
- Google Cloud Memorystore
- Azure Cache for Redis

```bash
REDIS_URL=redis://prod-cluster.example.cache.amazonaws.com:6379/0
```

### Option B: Redis Sentinel
Deploy a three-node Sentinel cluster (one primary, two replicas):

```bash
REDIS_USE_SENTINEL=true
REDIS_SENTINELS=sentinel1:26379,sentinel2:26379,sentinel3:26379
REDIS_MASTER_NAME=mymaster
REDIS_PASSWORD=your-secure-password
```

See [`../reference/REDIS_HIGH_AVAILABILITY.md`](../reference/REDIS_HIGH_AVAILABILITY.md) for detailed guidance.

---

## 📋 Pre-Deployment Checklist

### 1. Code Quality & Testing

- [ ] **Full Test Suite Passing**
  ```bash
  pytest -q
  # Expected: 199 passed in ~120s
  ```
  - [ ] All tests passing (no failures/errors)
  - [ ] Coverage maintained at >80%

- [ ] **Smoke Test Validation**
  ```bash
  python scripts/smoke_test_phase4.py
  # Expected: 6/6 tests passed
  ```
  - [ ] Legacy imports removed
  - [ ] Modular imports working
  - [ ] Database connectivity OK
  - [ ] Health endpoints responding
  - [ ] API endpoints accessible
  - [ ] Cache degrading gracefully

- [ ] **System Check Clean**
  ```bash
  python manage.py check --deploy
  # Expected: 0 errors (security warnings acceptable in dev)
  ```
  - [ ] No structural errors
  - [ ] No URL configuration warnings
  - [ ] No model/migration conflicts

- [ ] **Migration Validation**
  ```bash
  python scripts/validate_migration_staging.py
  # Expected: 14/14 checks passing
  ```
  - [ ] Migrations applied successfully
  - [ ] ContentTypes updated correctly
  - [ ] Model tables exist
  - [ ] CRUD operations working

---

### 2. Code Review & Documentation

- [ ] **Breaking Changes Documented**
  - [ ] `BREAKING_CHANGES_v2.0.0.md` reviewed
  - [ ] Migration guide accurate
  - [ ] Rollback procedures documented
  - [ ] Impact assessment complete

- [ ] **API Documentation Updated**
  - [ ] `API_DOCUMENTATION.md` reflects v2.0.0 changes
  - [ ] Legacy endpoints marked as removed
  - [ ] New endpoints documented
  - [ ] Examples tested and verified

- [ ] **Code Review Completed**
  - [ ] All `zabbix_api` imports removed from codebase
  - [ ] No hardcoded `/zabbix_api/` URLs in code
  - [ ] Frontend using `/api/v1/inventory/*` exclusively
  - [ ] Tests updated to new structure

---

### 3. Database & Backup

- [ ] **Production Backup Created**
  ```bash
  # Full database backup
  python manage.py dumpdata > backup_pre_v2_$(date +%Y%m%d_%H%M%S).json
  
  # Or MySQL dump
  mysqldump -u root -p mapsprovefib > backup_pre_v2_$(date +%Y%m%d_%H%M%S).sql
  ```
  - [ ] Backup file created successfully
  - [ ] Backup file verified (non-empty, valid format)
  - [ ] Backup stored in secure location
  - [ ] Backup retention policy applied (keep for 30 days)

- [ ] **Migration Dependencies Verified**
  ```bash
  python manage.py showmigrations
  ```
  - [ ] All current migrations applied
  - [ ] No pending migrations blocking deployment
  - [ ] `inventory.0003` ready to apply
  - [ ] `routes_builder.0001` present (dependency)

---

### 4. Infrastructure Readiness

- [ ] **Environment Variables**
  - [ ] `DJANGO_SETTINGS_MODULE` set correctly
  - [ ] `SECRET_KEY` configured (production-grade, 50+ chars)
  - [ ] `ALLOWED_HOSTS` includes production domain
  - [ ] `DEBUG=False` in production
  - [ ] `ENABLE_DIAGNOSTIC_ENDPOINTS` set appropriately
  - [ ] Database credentials secured
  - [ ] Redis credentials configured (if applicable)
  - [ ] Zabbix API credentials validated
  - [ ] `CSRF_TRUSTED_ORIGINS` includes production domain
  - [ ] `SECURE_SSL_REDIRECT=true` (HTTPS enforced)

- [ ] **Service Health**
  - [ ] Django app server running
  - [ ] Celery workers active
  - [ ] Celery beat running
  - [ ] Redis available (or degradation handled)
  - [ ] MySQL/MariaDB healthy
  - [ ] Nginx/reverse proxy configured

- [ ] **Monitoring & Alerting**
  - [ ] Prometheus metrics endpoint accessible (`/metrics/`)
  - [ ] Grafana dashboards updated for v2.0.0
  - [ ] Alert rules configured for critical failures
  - [ ] Log aggregation active (Sentry, CloudWatch, etc.)
  - [ ] Health check monitors configured

---

## 🚀 Deployment Steps

### Phase 1: Pre-Deploy Validation (T-1 hour)

**Duration**: 15 minutes  
**Owner**: DevOps

1. **Announce Maintenance Window**
   - [ ] Notify stakeholders via email/Slack
   - [ ] Update status page (if applicable)
   - [ ] Set deployment start time

2. **Final Smoke Test in Staging**
   ```bash
   # In staging environment
   python scripts/smoke_test_phase4.py
   pytest -q
   ```
   - [ ] All tests passing in staging
   - [ ] No errors in staging logs

3. **Create Deployment Tag**
   ```bash
   git tag -a v2.0.0 -m "Release v2.0.0 - Modular Architecture"
   git push origin v2.0.0
   ```
   - [ ] Tag created
   - [ ] Tag pushed to remote

---

### Phase 2: Database Migration (T-0)

**Duration**: 5 minutes (zero downtime)  
**Owner**: DevOps

1. **Enable Maintenance Mode** (optional)
   ```bash
   # Optional: set maintenance flag
   touch /var/www/mapsprovefib/MAINTENANCE_MODE
   ```
   - [ ] Maintenance mode enabled (if required)

2. **Apply Migration**
   ```bash
   python manage.py migrate inventory 0003_route_models_relocation
   ```
   - [ ] Migration applied successfully
   - [ ] No errors in output
   - [ ] Time taken: _____ seconds

3. **Validate ContentTypes**
   ```bash
   python manage.py shell -c "
   from django.contrib.contenttypes.models import ContentType
   ct = ContentType.objects.get(app_label='inventory', model='route')
   print(f'✅ Route ContentType: {ct}')
   assert ct.app_label == 'inventory'
   "
   ```
   - [ ] ContentType verification passed

---

### Phase 3: Code Deployment (T+5 min)

**Duration**: 10 minutes  
**Owner**: DevOps

1. **Pull Latest Code**
   ```bash
   cd /var/www/mapsprovefib
   git fetch origin
   git checkout v2.0.0
   ```
   - [ ] Code deployed to production directory

2. **Install Dependencies**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```
   - [ ] Dependencies installed
   - [ ] No version conflicts

3. **Collect Static Files**
   ```bash
   python manage.py collectstatic --noinput
   ```
   - [ ] Static files collected
   - [ ] No missing files

4. **Restart Services**
   ```bash
   # Docker Compose method
   docker compose -f docker-compose.prod.yml up -d --build
   docker compose -f docker-compose.prod.yml ps
   
   # Or systemd method
   sudo systemctl restart mapsprovefib
   sudo systemctl restart celery-worker
   sudo systemctl restart celery-beat
   sudo systemctl reload nginx
   ```
   - [ ] Django restarted successfully
   - [ ] Celery workers restarted
   - [ ] Celery beat restarted
   - [ ] Nginx reloaded (if applicable)

---

### Phase 4: Post-Deploy Validation (T+15 min)

**Duration**: 15 minutes  
**Owner**: DevOps + QA

1. **Health Checks**
   ```bash
   curl -f http://production-domain.com/health/ || echo "FAIL"
   curl -f http://production-domain.com/health/ready/ || echo "FAIL"
   curl -f http://production-domain.com/health/live/ || echo "FAIL"
   ```
   - [ ] `/health/` returns 200 OK
   - [ ] `/health/ready/` returns 200 OK
   - [ ] `/health/live/` returns 200 OK

   Expected response:
   ```json
   {
     "status": "healthy",
     "database": "ok",
     "redis": "ok",
     "celery": "ok"
   }
   ```

2. **API Endpoint Validation**
   ```bash
   curl -f http://production-domain.com/api/v1/inventory/sites/ || echo "FAIL"
   curl -f http://production-domain.com/api/v1/inventory/devices/ || echo "FAIL"
   curl -f http://production-domain.com/api/v1/inventory/fibers/oper-status/ || echo "FAIL"
   ```
   - [ ] `/api/v1/inventory/sites/` accessible
   - [ ] `/api/v1/inventory/devices/` accessible
   - [ ] `/api/v1/inventory/fibers/oper-status/` accessible

3. **Prometheus Metrics**
   ```bash
   curl -f http://production-domain.com/metrics/ | grep "django_"
   ```
   - [ ] Metrics endpoint returning data
   - [ ] Custom `static_version` metric present
   - [ ] Zabbix client metrics present

4. **Critical User Flows**
   - [ ] Dashboard loads (visual check)
   - [ ] Device list displays correctly
   - [ ] Create new route workflow functional
   - [ ] Fiber status updates in real-time
   - [ ] Maps rendering correctly

5. **Log Inspection**
   ```bash
   # Docker logs
   docker compose -f docker-compose.prod.yml logs --tail=100 web | grep ERROR
   docker compose -f docker-compose.prod.yml logs --tail=100 celery | grep ERROR
   
   # Or systemd logs
   tail -n 500 /var/log/mapsprovefib/django.log | grep ERROR
   tail -n 500 /var/log/mapsprovefib/celery.log | grep ERROR
   ```
   - [ ] No critical errors in Django logs
   - [ ] No critical errors in Celery logs
   - [ ] No `ModuleNotFoundError: zabbix_api` errors

---

### Phase 5: Monitoring & Sign-off (T+30 min)

**Duration**: 30 minutes  
**Owner**: DevOps + Engineering Lead

1. **Performance Baseline**
   - [ ] Response times comparable to pre-deployment
   - [ ] No significant increase in error rate
   - [ ] Database query performance unchanged
   - [ ] Celery task throughput normal

2. **Disable Maintenance Mode**
   ```bash
   rm /var/www/mapsprovefib/MAINTENANCE_MODE
   ```
   - [ ] Maintenance mode disabled

3. **Stakeholder Communication**
   - [ ] Email sent confirming successful deployment
   - [ ] Status page updated (deployed successfully)
   - [ ] Known issues documented (if any)

4. **Deployment Sign-off**
   - [ ] DevOps Lead approval: ________________
   - [ ] Engineering Lead approval: ________________
   - [ ] Deployment timestamp: ________________

---

## 🔄 Rollback Procedures

**Trigger Conditions**:
- Critical errors preventing application startup
- Database corruption detected
- >50% increase in error rate
- Critical user flows broken (dashboard, device list, route creation)

### Emergency Rollback (< 15 minutes)

1. **Revert Code**
   ```bash
   cd /var/www/mapsprovefib
   git checkout v1.x.x  # Previous stable tag
   
   # Docker method
   docker compose -f docker-compose.prod.yml down
   git checkout v1.x.x
   docker compose -f docker-compose.prod.yml up -d --build
   ```

2. **Restore Database** (if migration applied)
   ```bash
   # Option A: Rollback migration
   python manage.py migrate inventory 0002
   
   # Option B: Restore from backup (if data corruption)
   # Docker method
   docker compose -f docker-compose.prod.yml exec -T db sh -c \
     'mysql -u root -p$MYSQL_ROOT_PASSWORD mapsprovefib < /backups/backup_pre_v2_TIMESTAMP.sql'
   
   # Or direct MySQL
   mysql -u root -p mapsprovefib < backup_pre_v2_TIMESTAMP.sql
   ```

3. **Restart Services**
   ```bash
   # Docker method
   docker compose -f docker-compose.prod.yml restart
   
   # Systemd method
   sudo systemctl restart mapsprovefib
   sudo systemctl restart celery-worker
   sudo systemctl restart celery-beat
   ```

4. **Validate Rollback**
   ```bash
   curl -f http://production-domain.com/health/
   ```

5. **Notify Stakeholders**
   - [ ] Email sent explaining rollback reason
   - [ ] Incident postmortem scheduled

---

## 🔧 Backup and Recovery

### Database Backup

```bash
# Docker Compose method
docker compose -f docker-compose.prod.yml exec db sh -c \
  'mysqldump -u root -p$MYSQL_ROOT_PASSWORD mapspro_db > /backups/db_$(date +%Y%m%d_%H%M%S).sql'

# Restore
docker compose -f docker-compose.prod.yml exec -T db sh -c \
  'mysql -u root -p$MYSQL_ROOT_PASSWORD mapspro_db < /backups/db_20250127_120000.sql'
```

### Redis Backup (RDB persistence)

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli BGSAVE
docker cp redis:/data/dump.rdb ./backups/redis_$(date +%Y%m%d_%H%M%S).rdb
```

---

## 📊 Monitoring

### Container Logs

```bash
# Follow all logs
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs --tail=100 celery
```

### Health Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health/` | Overall status | `200 OK` with JSON |
| `/health/ready/` | Ready for traffic | `200 OK` |
| `/health/live/` | Process alive | `200 OK` |
| `/metrics/` | Prometheus metrics | `200 OK` with text |

### Prometheus Metrics

```bash
curl http://localhost:8000/metrics/
```

Track metrics such as:
- `django_http_requests_latency_seconds`
- `django_db_query_duration_seconds`
- `celery_task_total`
- `redis_connected_clients`

---

## 🔍 Troubleshooting

### Service Won't Start

```bash
docker compose -f docker-compose.prod.yml logs <service-name>
docker compose -f docker-compose.prod.yml ps
docker inspect <container-id>
```

### Database Connectivity

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py dbshell
docker compose -f docker-compose.prod.yml exec db mysql -u root -p -e "SHOW DATABASES;"
```

### Redis Connectivity

```bash
docker compose -f docker-compose.prod.yml exec redis redis-cli PING
docker compose -f docker-compose.prod.yml exec redis redis-cli INFO
```

### Celery Tasks Idle

```bash
docker compose -f docker-compose.prod.yml logs celery
docker compose -f docker-compose.prod.yml exec celery celery -A core inspect active
docker compose -f docker-compose.prod.yml logs beat
```

### Quick Fix Table

| Issue | Remedy |
|-------|--------|
| Database container fails to start | Inspect volumes or `.env` credentials |
| Celery stopped | `docker compose restart celery beat` |
| Health endpoint returns 503 | Validate Redis and database status |
| Static assets missing | `python manage.py collectstatic --noinput` |

---

## 📊 Success Criteria

### Deployment Successful If:

- ✅ All 199 tests passing post-deployment
- ✅ Health checks returning 200 OK
- ✅ No increase in error rate (< 0.1% errors)
- ✅ Response times within ±10% of baseline
- ✅ Critical user flows functional
- ✅ No `ModuleNotFoundError` in logs
- ✅ Prometheus metrics reporting correctly
- ✅ Celery tasks processing normally
- ✅ Zero customer-reported issues in first 24h

### Red Flags (Trigger Rollback):

- 🚨 Health checks failing
- 🚨 Error rate > 1%
- 🚨 Response times > 2x baseline
- 🚨 Dashboard not loading
- 🚨 Database connection errors
- 🚨 Migration failures
- 🚨 Critical Celery tasks failing

---

## 📞 Incident Response

### Escalation Path

1. **Level 1**: DevOps on-call  
   - Monitor logs, health checks, metrics
   - Attempt automated recovery
   - Escalate if not resolved in 10 minutes

2. **Level 2**: Engineering Lead  
   - Review application-level issues
   - Coordinate with DevOps on rollback decision
   - Escalate if architectural issue suspected

3. **Level 3**: CTO / Incident Commander  
   - Major outage affecting critical business functions
   - Data integrity concerns
   - Rollback not resolving issue

### Contact Information

| Role | Name | Contact |
|------|------|---------|
| DevOps Lead | TBD | TBD |
| Engineering Lead | Don Jonhn | TBD |
| Database Admin | TBD | TBD |
| CTO | TBD | TBD |

---

## 📝 Post-Deployment Tasks

### Within 24 Hours

- [ ] **Monitor Error Rates**
  - Check Sentry/CloudWatch for anomalies
  - Compare to pre-deployment baseline
  - Investigate any new error patterns

- [ ] **Performance Review**
  - Analyze Prometheus metrics
  - Compare database query times
  - Identify any regressions

- [ ] **User Feedback**
  - Monitor support tickets
  - Check user-reported issues
  - Collect feedback on new functionality

### Within 1 Week

- [ ] **Postmortem Document** (if issues occurred)
  - Timeline of events
  - Root cause analysis
  - Corrective actions
  - Preventive measures

- [ ] **Update Runbooks**
  - Document any deployment quirks
  - Update rollback procedures if needed
  - Refine health check thresholds

- [ ] **Cleanup Tasks**
  - Remove `routes_builder` app (if migration dependency resolved)
  - Archive old backups (retain 30 days)
  - Update deployment documentation

---

## 📚 Additional Resources

- [`../reference/REDIS_HIGH_AVAILABILITY.md`](../reference/REDIS_HIGH_AVAILABILITY.md)
- [`../architecture/OVERVIEW.md`](../architecture/OVERVIEW.md)
- [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md)
- [`MIGRATION_PRODUCTION_GUIDE.md`](./MIGRATION_PRODUCTION_GUIDE.md)

---

**MapsProveFiber** - Production Deployment Guide  
**Version**: v2.0.0 | **Last Updated**: 2025-11-07
