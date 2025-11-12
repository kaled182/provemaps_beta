# Phase 12 — Performance & Observability

**Status:** 🚀 Starting Now  
**Duration:** 1-2 weeks (2 sprints)  
**Goal:** Build solid technical foundation before scaling features  
**Prerequisites:** ✅ Phase 11 Complete (Vue 3 Dashboard deployed at 10%)

---

## 🎯 Objectives

1. **Redis Caching** — Reduce database load by 60-80%
2. **Query Optimization** — Fix N+1 queries, add indexes
3. **APM Integration** — Real-time error tracking and performance monitoring
4. **Grafana Dashboards** — Visual operational metrics
5. **Load Testing** — Validate performance improvements

---

## 📋 Sprint 1: Core Performance (Week 1)

### Task 1: Redis Caching Infrastructure (2 days)

**Goal:** Implement comprehensive caching strategy

#### 1.1 Configure Django Cache Backend
```python
# backend/settings/base.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'mapsprove',
        'TIMEOUT': 300,  # 5 minutes default
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/2'),
        'TIMEOUT': 86400,  # 24 hours
    },
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
```

#### 1.2 Cache Dashboard Data
```python
# backend/maps_view/services.py
from django.core.cache import cache

def get_dashboard_data_cached(force_refresh=False):
    """Get dashboard data with caching."""
    cache_key = 'dashboard:main:v1'
    
    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
    
    # Existing logic from get_dashboard_cached()
    data = get_dashboard_data()
    
    cache.set(cache_key, data, timeout=60)  # 1 minute
    return data
```

#### 1.3 Cache Zabbix Responses
```python
# backend/integrations/zabbix/zabbix_service.py

# Already implemented! Just verify timeouts:
CACHE_KEY_HOST_STATUS = 'zabbix:host_status:{host_id}'
CACHE_TIMEOUT_HOST_STATUS = 120  # 2 minutes

# Add cache warming task
@shared_task
def warm_zabbix_cache():
    """Pre-populate cache with Zabbix data."""
    hosts = get_all_hosts()
    for host in hosts:
        get_host_status(host.hostid)  # Populates cache
```

#### 1.4 Cache Route Segments (BBox)
```python
# backend/inventory/services.py
from django.core.cache import cache

def get_segments_in_bbox_cached(bbox: tuple, status_filter: str = None):
    """Get segments with spatial caching."""
    # Round bbox to reduce cache key variance
    rounded_bbox = tuple(round(coord, 2) for coord in bbox)
    cache_key = f'segments:bbox:{rounded_bbox}:{status_filter}'
    
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    segments = get_segments_in_bbox(bbox, status_filter)
    cache.set(cache_key, segments, timeout=300)  # 5 minutes
    
    return segments
```

**Deliverables:**
- [ ] Redis configured in Django settings
- [ ] Dashboard data cached (1min TTL)
- [ ] Zabbix responses cached (2min TTL)
- [ ] BBox segments cached (5min TTL)
- [ ] Cache invalidation on data updates

---

### Task 2: Query Optimization (2 days)

**Goal:** Eliminate N+1 queries, add database indexes

#### 2.1 Install Django Debug Toolbar
```bash
pip install django-debug-toolbar
```

```python
# backend/settings/dev.py
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']
```

#### 2.2 Analyze Current Queries
**Dashboard View:**
```python
# Before optimization (example):
# SELECT * FROM inventory_device;  # 50 queries (N+1)
# SELECT * FROM inventory_site WHERE id = 1;
# SELECT * FROM inventory_site WHERE id = 2;
# ...

# After optimization:
devices = Device.objects.select_related('site', 'device_type').all()
```

**Common N+1 Problems:**
- `inventory/views.py` → Device list with Sites
- `maps_view/services.py` → Hosts with Devices
- `monitoring/usecases.py` → Devices with Zabbix status

#### 2.3 Add Indexes
```python
# backend/inventory/models.py

class Device(models.Model):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['site', 'status']),  # Common filter
            models.Index(fields=['device_type', 'status']),
            models.Index(fields=['created_at']),  # Recent devices
        ]

class RouteSegment(models.Model):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['route', 'sequence']),  # Route ordering
            models.Index(fields=['status']),  # Status filtering
            # GiST index for spatial queries (already exists via GeoDjango)
        ]
```

```bash
# Generate migration
python manage.py makemigrations --name add_performance_indexes

# Apply
python manage.py migrate
```

#### 2.4 Optimize Critical Views
```python
# backend/maps_view/services.py

def get_devices_with_zabbix():
    """Optimized version with select_related."""
    devices = Device.objects.select_related(
        'site',
        'device_type',
    ).prefetch_related(
        'ports',
        'ports__fiber_cables',
    ).filter(
        status__in=['active', 'maintenance']
    ).only(
        'id', 'name', 'status',
        'site__name', 'site__location',
        'device_type__name',
    )
    
    # Batch fetch Zabbix data
    zabbix_statuses = get_zabbix_statuses_batch([d.id for d in devices])
    
    # Combine in memory (avoid N+1)
    for device in devices:
        device.zabbix_status = zabbix_statuses.get(device.id)
    
    return devices
```

**Deliverables:**
- [ ] Django Debug Toolbar installed
- [ ] N+1 queries identified (>5 cases)
- [ ] select_related/prefetch_related added
- [ ] Database indexes created (migration)
- [ ] Query count reduced by 50%+

---

### Task 3: Sentry APM Integration (1 day)

**Goal:** Real-time error tracking and performance monitoring

#### 3.1 Install Sentry SDK
```bash
pip install sentry-sdk[django]
```

#### 3.2 Configure Sentry
```python
# backend/settings/base.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

SENTRY_DSN = os.getenv('SENTRY_DSN', None)

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% profiling
        send_default_pii=False,
        environment=os.getenv('ENVIRONMENT', 'development'),
        release=f"mapsprove@{os.getenv('GIT_COMMIT', 'dev')}",
    )
```

#### 3.3 Add Custom Spans
```python
# backend/maps_view/services.py
from sentry_sdk import start_transaction, start_span

def get_dashboard_data():
    with start_transaction(op="dashboard", name="get_dashboard_data"):
        with start_span(op="db.query", description="fetch devices"):
            devices = Device.objects.all()
        
        with start_span(op="zabbix.api", description="fetch statuses"):
            statuses = get_zabbix_statuses_batch(device_ids)
        
        with start_span(op="transform", description="combine data"):
            result = combine_devices_and_statuses(devices, statuses)
        
        return result
```

#### 3.4 Error Tracking Examples
```python
# Automatic error capture (already works with Sentry)
try:
    result = risky_operation()
except Exception as e:
    # Sentry captures automatically
    raise

# Manual context enrichment
from sentry_sdk import set_context, set_tag

set_tag("feature", "dashboard")
set_context("request_info", {
    "bbox": str(bbox),
    "filter": status_filter,
})
```

**Deliverables:**
- [ ] Sentry SDK installed
- [ ] DSN configured in .env
- [ ] Custom transactions for dashboard, API, Celery
- [ ] Error tracking active
- [ ] Performance profiling enabled (10%)

---

## 📋 Sprint 2: Advanced Observability (Week 2 - Optional)

### Task 4: Grafana Dashboards (2 days)

**Goal:** Visual dashboards for Prometheus metrics

#### 4.1 Grafana Setup (Docker)
```yaml
# docker/docker-compose.yml
services:
  grafana:
    image: grafana/grafana:10.2.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_INSTALL_PLUGINS=redis-datasource
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      - prometheus

  prometheus:
    image: prom/prometheus:v2.45.0
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

volumes:
  grafana-data:
  prometheus-data:
```

#### 4.2 Prometheus Config
```yaml
# docker/prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'django'
    static_configs:
      - targets: ['web:8000']
    metrics_path: '/metrics/'
```

#### 4.3 Grafana Dashboards
Create 5 dashboards:

1. **Application Overview**
   - Request rate (req/s)
   - Response time P50/P95/P99
   - Error rate (%)
   - Active users

2. **Database Performance**
   - Query execution time
   - Connection pool usage
   - Cache hit ratio
   - Slow queries (>1s)

3. **Zabbix Integration**
   - API call rate
   - API errors
   - Circuit breaker state
   - Cache hit/miss ratio

4. **Celery Workers**
   - Task queue length
   - Task execution time
   - Failed tasks
   - Worker uptime

5. **Infrastructure**
   - CPU usage (%)
   - Memory usage (MB)
   - Redis memory
   - Database connections

**Deliverables:**
- [ ] Grafana running in Docker
- [ ] Prometheus scraping Django metrics
- [ ] 5 dashboards created
- [ ] Alerts configured (email/Slack)

---

### Task 5: Load Testing (1 day)

**Goal:** Validate performance improvements under load

#### 5.1 Install Locust
```bash
pip install locust
```

#### 5.2 Load Test Scenarios
```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        """Login before tests."""
        self.client.post("/accounts/login/", {
            "username": "testuser",
            "password": "testpass123",
        })
    
    @task(3)
    def view_dashboard(self):
        """Main dashboard view."""
        self.client.get("/maps_view/dashboard")
    
    @task(2)
    def fetch_dashboard_api(self):
        """Dashboard API endpoint."""
        self.client.get("/api/v1/dashboard/")
    
    @task(1)
    def fetch_segments(self):
        """BBox segments API."""
        bbox = "-48.5,-27.5,-48.3,-27.3"
        self.client.get(f"/api/v1/inventory/segments/?bbox={bbox}")
```

#### 5.3 Run Load Tests
```bash
# Start Locust
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Open browser: http://localhost:8089
# Configure:
# - Number of users: 100
# - Spawn rate: 10/s
# - Duration: 5 minutes
```

#### 5.4 Performance Targets
| Metric | Before | Target | After |
|--------|--------|--------|-------|
| Requests/sec | 50 | 200+ | _____ |
| Avg Response Time | 800ms | <300ms | _____ |
| P95 Response Time | 2000ms | <500ms | _____ |
| Error Rate | 2% | <0.5% | _____ |
| Database Queries | 150/req | <20/req | _____ |

**Deliverables:**
- [ ] Locust tests created (3 scenarios)
- [ ] Baseline performance measured
- [ ] Load test report generated
- [ ] Performance targets met

---

### Task 6: Database Optimization (1 day)

**Goal:** Advanced database tuning

#### 6.1 Analyze Slow Queries
```sql
-- PostgreSQL slow query log
ALTER DATABASE mapsprove SET log_min_duration_statement = 100;

-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;
```

#### 6.2 Add Composite Indexes
```python
# backend/inventory/migrations/0XXX_composite_indexes.py
from django.db import migrations, models

class Migration(migrations.Migration):
    operations = [
        migrations.AddIndex(
            model_name='device',
            index=models.Index(
                fields=['site', 'status', 'device_type'],
                name='device_site_status_type_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='routesegment',
            index=models.Index(
                fields=['route', 'sequence', 'status'],
                name='segment_route_seq_status_idx'
            ),
        ),
    ]
```

#### 6.3 Partial Indexes (PostgreSQL)
```python
# Only index active devices
migrations.RunSQL(
    sql="CREATE INDEX device_active_idx ON inventory_device (site_id) WHERE status = 'active';",
    reverse_sql="DROP INDEX IF EXISTS device_active_idx;",
)
```

#### 6.4 Materialized View for Dashboard
```sql
-- Cache heavy aggregations
CREATE MATERIALIZED VIEW dashboard_summary AS
SELECT
    s.id AS site_id,
    s.name AS site_name,
    COUNT(d.id) AS device_count,
    COUNT(d.id) FILTER (WHERE d.status = 'active') AS active_devices,
    COUNT(p.id) AS port_count
FROM inventory_site s
LEFT JOIN inventory_device d ON d.site_id = s.id
LEFT JOIN inventory_port p ON p.device_id = d.id
GROUP BY s.id, s.name;

-- Refresh periodically (Celery task)
REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard_summary;
```

**Deliverables:**
- [ ] Slow queries identified (>100ms)
- [ ] Composite indexes added
- [ ] Partial indexes for common filters
- [ ] Materialized view created (optional)
- [ ] Query performance improved 3x+

---

## 🎯 Success Criteria (End of Sprint 2)

### Performance Metrics
- [ ] Dashboard load time: <500ms (from ~1500ms)
- [ ] API response time P95: <300ms (from ~800ms)
- [ ] Cache hit ratio: >80%
- [ ] Database queries per request: <20 (from ~150)
- [ ] Concurrent users supported: 200+ (from ~50)

### Observability
- [ ] Sentry tracking 100% of errors
- [ ] Grafana dashboards operational
- [ ] Alerts configured for critical metrics
- [ ] Load testing validates improvements

### Code Quality
- [ ] No N+1 queries in critical paths
- [ ] All expensive queries cached
- [ ] Database indexes for common queries
- [ ] Performance regression tests

---

## 📦 Deliverables

### Sprint 1 (Week 1)
1. ✅ Redis caching infrastructure
2. ✅ Query optimization (N+1 fixes)
3. ✅ Sentry APM integration
4. ✅ Performance baseline established

### Sprint 2 (Week 2 - Optional)
5. ✅ Grafana dashboards (5 dashboards)
6. ✅ Load testing with Locust
7. ✅ Database optimization (indexes, materialized views)
8. ✅ Performance targets validated

---

## 🔄 Next Phase

After Phase 12 completion → **Phase 13: Dashboard Features**
- Advanced filters
- Search/autocomplete
- Drill-down modals
- Export reports
- Push notifications

**Estimated Start:** ~2 weeks from now  
**Duration:** 2-3 weeks  
**Prerequisites:** ✅ Phase 12 performance improvements

---

**Created:** 12/11/2025  
**Status:** 🚀 Ready to Start  
**Owner:** Development Team  
**Priority:** High (Foundation for scaling)
