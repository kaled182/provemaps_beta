# Sentry APM - Quick Implementation Guide

**Status:** ✅ Sentry SDK installed (2.44.0)  
**Status:** ✅ Settings already configured  
**Time:** ~30 minutes to activate and test

---

## ✅ Already Done

1. **Sentry SDK installed:** `sentry-sdk==2.44.0`
2. **Settings configured:** `backend/settings/base.py` lines 503-530
3. **Integrations ready:** Django + Celery

---

## 🔧 Steps to Activate

### Step 1: Get Sentry DSN (Free Account)

1. Go to https://sentry.io/signup/
2. Create free account (50k events/month free)
3. Create new project "MapsProveFiber" (Django)
4. Copy DSN (looks like: `https://xxxxx@o1234567.ingest.us.sentry.io/9876543`)

### Step 2: Add DSN to Environment

**Option A: Docker (.env file)**
```bash
# Add to docker/.env or docker-compose.yml
SENTRY_DSN=https://xxxxx@o1234567.ingest.us.sentry.io/9876543
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions
SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10% profiling
```

**Option B: Test locally (database/runtime.env)**
```bash
# Add to database/runtime.env
SENTRY_DSN="https://xxxxx@o1234567.ingest.us.sentry.io/9876543"
SENTRY_ENVIRONMENT="development"
SENTRY_TRACES_SAMPLE_RATE="0.1"
```

### Step 3: Restart Services

```powershell
# Restart web container
docker compose -f docker/docker-compose.yml restart web

# Check if Sentry initialized (logs)
docker compose -f docker/docker-compose.yml logs web | Select-String "sentry"
```

### Step 4: Test Error Tracking

**Create test view:**
```python
# backend/core/views.py
def test_sentry_error(request):
    """Test endpoint to verify Sentry error tracking."""
    division_by_zero = 1 / 0  # Intentional error
    return HttpResponse("This won't execute")
```

**Add URL:**
```python
# backend/core/urls.py
urlpatterns = [
    # ... existing patterns ...
    path('test-sentry-error/', core_views.test_sentry_error),  # Only in dev!
]
```

**Trigger error:**
```
http://localhost:8000/test-sentry-error/
```

**Check Sentry dashboard:**
- Go to sentry.io → Your Project
- Should see ZeroDivisionError captured
- Stack trace, request context, user info

---

## 📊 Custom Transaction Spans (Optional but Recommended)

### Dashboard View with Spans

```python
# backend/maps_view/views.py
from sentry_sdk import start_transaction, start_span

def dashboard_view(request):
    with start_transaction(op="http.server", name="dashboard_view"):
        # Existing rollout logic...
        
        with start_span(op="db.query", description="get_runtime_settings"):
            google_maps_key = get_google_maps_api_key(request)
        
        with start_span(op="template.render", description="render_dashboard"):
            return render(request, template_name, context)
```

### API with Spans

```python
# backend/maps_view/services.py
from sentry_sdk import start_span

def get_dashboard_cached(use_fresh=False):
    with start_span(op="cache.get", description="dashboard_swr_cache"):
        cached = cache.get(cache_key)
    
    if cached is None:
        with start_span(op="zabbix.api", description="fetch_hosts_status"):
            data = get_devices_with_zabbix()
        
        with start_span(op="cache.set", description="dashboard_swr_cache"):
            cache.set(cache_key, data, timeout=SWR_FRESH_TTL)
    
    return data
```

### Celery Task Tracking

```python
# backend/maps_view/tasks.py
from sentry_sdk import start_transaction

@shared_task
def refresh_dashboard_cache_task():
    with start_transaction(op="task", name="refresh_dashboard_cache"):
        get_dashboard_cached(use_fresh=True)
```

---

## 🎯 What Sentry Provides

### Error Tracking
- **Automatic capture:** All unhandled exceptions
- **Context enrichment:** Request headers, user, environment
- **Breadcrumbs:** User actions leading to error
- **Grouping:** Similar errors grouped together
- **Alerts:** Email/Slack when errors spike

### Performance Monitoring
- **Transaction tracking:** Dashboard load time, API response time
- **Custom spans:** Database queries, cache hits, Zabbix calls
- **Profiling:** Function-level performance (10% sample)
- **Trends:** Performance degradation over time
- **Distributed tracing:** Track requests across services

### Release Tracking
```python
# In settings/base.py (already configured!)
release=f"mapsprove@{os.getenv('GIT_COMMIT', 'dev')}"
```

Set `GIT_COMMIT` env var to track errors by version:
```bash
GIT_COMMIT=$(git rev-parse --short HEAD)
```

---

## 📈 Expected Metrics (After Activation)

### Error Rate
- **Target:** <1% of requests
- **Alert if:** >5% in 5 minutes
- **Dashboard:** Sentry Issues tab

### Performance
- **Dashboard load:** P95 <500ms
- **API response:** P95 <300ms
- **Dashboard:** Sentry Performance tab

### Custom Metrics (Examples)
```python
from sentry_sdk import set_measurement

set_measurement("dashboard_cache_hit_rate", 0.85, "ratio")  # 85%
set_measurement("zabbix_api_latency", 250, "millisecond")
```

---

## ✅ Verification Checklist

- [ ] Sentry account created (free tier)
- [ ] DSN added to environment variables
- [ ] Web container restarted
- [ ] Sentry initialization logged (check `docker logs`)
- [ ] Test error triggered and captured in Sentry dashboard
- [ ] Custom transaction spans added (optional)
- [ ] Release tracking configured with GIT_COMMIT
- [ ] Alerts configured (email/Slack)

---

## 🚀 After Sentry is Active

**Mark complete and proceed to Phase 13:**
- [ ] Sentry APM integration complete (1 day)
- → **Phase 13: Dashboard Features - Sprint 1** (filters, search)

**Benefits:**
- ✅ Real-time error alerts
- ✅ Performance regression detection
- ✅ User impact visibility
- ✅ Production-ready observability

---

**Time Estimate:** 30 minutes (with free Sentry account)  
**Complexity:** Low (mostly configuration)  
**Impact:** High (essential for production)

**Next:** Get Sentry DSN and add to environment → restart → test!
