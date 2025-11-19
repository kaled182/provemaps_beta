# Phase 7 - Monitoring Setup Guide
# Prometheus + Grafana for Spatial Radius Search

**Phase**: 7 (Spatial Radius Search)  
**Day**: 7 (Production Deployment - Monitoring)  
**Rollout Status**: Phase 1 (10%)  
**Last Updated**: November 19, 2025

---

## 📋 Quick Start

### Prerequisites

- ✅ Phase 1 deployed (commit f35f6ea)
- ✅ Docker Compose running (5/5 containers healthy)
- ✅ Prometheus installed (or use Docker)
- ✅ Grafana installed (or use Docker)

### Files Created

```
docker/
├── prometheus/
│   └── alerts/
│       └── radius_search.yml          # Alert rules (16 alerts)
└── grafana/
    └── dashboards/
        └── phase7_radius_search.json  # Dashboard JSON (8 panels)
```

---

## 🚀 Option 1: Docker Compose Setup (Recommended)

### Step 1: Add Prometheus + Grafana to docker-compose.yml

Edit `docker/docker-compose.yml` and add:

```yaml
services:
  # ... existing services (web, postgres, redis, celery, beat) ...

  prometheus:
    image: prom/prometheus:latest
    container_name: docker-prometheus-1
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./prometheus/alerts:/etc/prometheus/alerts:ro
      - prometheus_data:/prometheus
    restart: unless-stopped
    networks:
      - default

  grafana:
    image: grafana/grafana:latest
    container_name: docker-grafana-1
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3000:3000"
    volumes:
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro
      - grafana_data:/var/lib/grafana
    restart: unless-stopped
    depends_on:
      - prometheus
    networks:
      - default

volumes:
  prometheus_data:
  grafana_data:
```

### Step 2: Create Prometheus Configuration

Create `docker/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'provemaps-phase7'
    environment: 'development'

# Load alert rules
rule_files:
  - '/etc/prometheus/alerts/*.yml'

# Scrape configurations
scrape_configs:
  # Django application metrics
  - job_name: 'django'
    static_configs:
      - targets: ['web:8000']
    metrics_path: '/metrics/'
    scrape_interval: 30s

  # Redis metrics (requires redis_exporter)
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    scrape_interval: 30s

  # PostgreSQL metrics (requires postgres_exporter)
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
    scrape_interval: 30s

  # Celery metrics (via Django /metrics/)
  - job_name: 'celery'
    static_configs:
      - targets: ['web:8000']
    metrics_path: '/metrics/'
    scrape_interval: 30s
    relabel_configs:
      - source_labels: [__name__]
        regex: 'celery_.*'
        action: keep
```

### Step 3: Create Grafana Datasource Provisioning

Create `docker/grafana/datasources/prometheus.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "30s"
      httpMethod: POST
```

### Step 4: Create Grafana Dashboard Provisioning

Create `docker/grafana/dashboards/dashboard.yml`:

```yaml
apiVersion: 1

providers:
  - name: 'Phase 7 Dashboards'
    orgId: 1
    folder: 'Production'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
      foldersFromFilesStructure: true
```

### Step 5: Start Monitoring Stack

```powershell
cd docker
docker compose up -d prometheus grafana
```

### Step 6: Verify Setup

```powershell
# Check Prometheus
Invoke-WebRequest -Uri "http://localhost:9090/targets" -UseBasicParsing

# Check Grafana
Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing

# Check metrics endpoint
Invoke-WebRequest -Uri "http://localhost:8000/metrics/" -UseBasicParsing
```

### Step 7: Access Dashboards

1. **Prometheus UI**: http://localhost:9090
   - Check `/targets` to verify Django scraping
   - Check `/alerts` to see radius_search alerts

2. **Grafana UI**: http://localhost:3000
   - Login: `admin` / `admin`
   - Navigate to Dashboards → Production → Phase 7 - Spatial Radius Search Monitoring

---

## 🛠️ Option 2: Standalone Prometheus/Grafana

### Prometheus Setup

1. **Download Prometheus**: https://prometheus.io/download/

2. **Copy alert rules**:
   ```powershell
   Copy-Item docker/prometheus/alerts/radius_search.yml -Destination C:/prometheus/alerts/
   ```

3. **Create prometheus.yml** (see Option 1 Step 2)

4. **Start Prometheus**:
   ```powershell
   cd C:/prometheus
   ./prometheus.exe --config.file=prometheus.yml
   ```

5. **Verify**: http://localhost:9090

### Grafana Setup

1. **Download Grafana**: https://grafana.com/grafana/download

2. **Start Grafana**:
   ```powershell
   cd C:/grafana/bin
   ./grafana-server.exe
   ```

3. **Access**: http://localhost:3000 (admin/admin)

4. **Add Prometheus datasource**:
   - Configuration → Data Sources → Add data source
   - Type: Prometheus
   - URL: http://localhost:9090
   - Save & Test

5. **Import dashboard**:
   - Dashboards → Import
   - Upload JSON file: `docker/grafana/dashboards/phase7_radius_search.json`
   - Select Prometheus datasource
   - Import

---

## 📊 Dashboard Panels Explained

### Panel 1: Cache Hit Rate (Gauge)
- **Metric**: `(fresh + stale) / (miss + fresh + stale) * 100`
- **Target**: > 70% (green)
- **Thresholds**: Red < 30%, Orange 30-50%, Yellow 50-70%, Green > 70%
- **What it shows**: Percentage of requests served from cache vs database

### Panel 2: API Latency (Graph)
- **Metrics**: p50, p95, p99 percentiles
- **Target**: p95 < 200ms
- **Thresholds**: Yellow > 200ms, Red > 500ms
- **What it shows**: API response time distribution over time

### Panel 3: API Request Rate (Stacked Area)
- **Metric**: `rate(django_http_requests_total[5m])`
- **Split by**: Status code (2xx green, 5xx red)
- **What it shows**: Request volume and error rate

### Panel 4: Celery Task Rate (Graph)
- **Metrics**: Success (green), Failed (red)
- **Target**: 0 failures
- **What it shows**: Async cache refresh task health

### Panel 5: Redis Memory (Graph)
- **Metric**: `redis_memory_used_bytes`
- **Target**: < 1GB
- **Thresholds**: Yellow > 1GB, Red > 2GB
- **What it shows**: Cache memory consumption

### Panel 6: Cache Operations Distribution (Donut)
- **Metrics**: MISS (red), FRESH (green), STALE (yellow)
- **What it shows**: Cache behavior breakdown

### Panel 7: Cache Latency (Graph)
- **Metric**: p95 latency for GET/SET/INVALIDATE operations
- **Target**: < 10ms
- **What it shows**: Redis performance

### Panel 8: Result Count (Bar Chart)
- **Metric**: Number of sites found per query
- **What it shows**: Query result size distribution

---

## 🚨 Alert Rules Summary

### Critical Alerts (16 total)

| Alert | Threshold | Duration | Action |
|-------|-----------|----------|--------|
| **RadiusSearchHighErrorRate** | > 1% | 5m | Immediate rollback |
| **RadiusSearchHighLatency** | p95 > 500ms | 10m | Investigate DB/cache |
| **RadiusSearchCacheDown** | 100% misses | 15m | Check Redis |
| **RadiusCacheRefreshTaskFailing** | Any failures | 5m | Check Celery logs |
| **RedisMemoryExhaustion** | > 2GB | 5m | Review TTL settings |

### Warning Alerts

| Alert | Threshold | Duration | Action |
|-------|-----------|----------|--------|
| **RadiusSearchLowCacheHitRate** | < 50% | 30m | Monitor, check patterns |
| **RadiusSearchElevatedLatency** | p95 > 200ms | 15m | Check cache hit rate |
| **RadiusSearchHighStaleRate** | > 20% stale | 20m | Review fresh TTL |
| **RadiusSearchCacheSlowness** | p95 > 50ms | 10m | Check Redis CPU |
| **RadiusCacheRefreshBacklog** | Queue > 100 | 10m | Scale Celery workers |
| **RadiusSearchDatabaseSlowness** | p95 > 100ms | 10m | Verify GiST index |

### Info Alerts

| Alert | Threshold | Duration | Note |
|-------|-----------|----------|------|
| **RadiusSearchCacheWarming** | < 30% hit rate | 5m | Normal during warmup |
| **RadiusSearchLowAdoption** | < 0.01 req/s | 2h | Feature underutilized |

---

## 🔍 Monitoring Checklist (24h Phase 1)

### Every 6 Hours

- [ ] Check Grafana dashboard for anomalies
- [ ] Review Prometheus active alerts
- [ ] Check Django logs: `docker compose logs web --tail 100 | Select-String "ERROR|CRITICAL"`
- [ ] Check Celery logs: `docker compose logs celery --tail 100 | Select-String "ERROR|FAILED"`
- [ ] Verify cache hit rate > 30% (warmup) or > 70% (after 2h)
- [ ] Confirm p95 latency < 200ms
- [ ] Check Redis memory < 1GB

### Daily

- [ ] Export Grafana screenshots for documentation
- [ ] Review alert history (any false positives?)
- [ ] Check user feedback (support tickets, Slack)
- [ ] Document any incidents in `doc/troubleshooting/INCIDENTS.md`
- [ ] Update deployment plan with observations

### End of Phase 1 (24h)

- [ ] Generate monitoring summary report
- [ ] Compare metrics against targets (success criteria)
- [ ] Decision: Proceed to Phase 2 (25%) or rollback
- [ ] Update stakeholders on deployment status

---

## 📈 Success Criteria (Phase 1 - 24h)

| Metric | Target | Status | Notes |
|--------|--------|--------|-------|
| **Error Rate** | < 0.1% | ⏰ | Monitor via `RadiusSearchHighErrorRate` alert |
| **API p95 Latency** | < 200ms | ⏰ | Monitor via Grafana Panel 2 |
| **Cache Hit Rate** | > 50% | ⏰ | After 2h warmup, target 70% |
| **Celery Task Success** | 100% | ⏰ | Monitor via Panel 4 (red line = 0) |
| **Redis Memory** | < 1GB | ⏰ | Monitor via Panel 5 |
| **User Complaints** | 0 | ⏰ | Check support channels |

If **ALL metrics pass** after 24h → **Proceed to Phase 2 (25%)**  
If **ANY metric fails** → **Investigate and consider rollback**

---

## 🛑 Troubleshooting

### Alert Firing: RadiusSearchHighErrorRate

**Symptoms**: Error rate > 1%, Prometheus alert critical

**Investigation**:
```powershell
# Check Django logs
docker compose logs web --tail 500 | Select-String "ERROR|CRITICAL|Exception"

# Check recent requests
Invoke-WebRequest -Uri "http://localhost:8000/metrics/" | Select-String "radius.*5.."
```

**Possible Causes**:
- Database connection issues
- Cache connection issues
- Invalid coordinates in requests
- Code bug (check recent commits)

**Remediation**:
1. If > 5% error rate: **Immediate rollback** (`VUE_DASHBOARD_ROLLOUT_PERCENTAGE=0`)
2. If 1-5%: Investigate root cause, fix, redeploy
3. Update incident report

### Alert Firing: RadiusSearchCacheDown

**Symptoms**: 100% cache misses, all requests hitting DB

**Investigation**:
```powershell
# Check Redis connection
docker compose exec web python -c "from django.core.cache import cache; print(cache.get('test'))"

# Check Redis status
docker compose exec redis redis-cli PING

# Check SWR settings
docker compose exec web env | Select-String "SWR"
```

**Possible Causes**:
- Redis container down
- `SWR_ENABLED=false`
- Cache key mismatch after deployment
- Redis maxmemory-policy evicting all keys

**Remediation**:
1. Restart Redis: `docker compose restart redis`
2. Verify settings: `SWR_ENABLED=true`, `SWR_FRESH_TTL=30`, `SWR_STALE_TTL=60`
3. Check Redis config: `docker compose exec redis redis-cli CONFIG GET maxmemory-policy`
4. If unresolved: Rollback deployment

### Dashboard Shows No Data

**Symptoms**: Grafana panels empty, "No data"

**Investigation**:
```powershell
# Check Prometheus targets
Invoke-WebRequest -Uri "http://localhost:9090/targets"

# Check Django metrics endpoint
Invoke-WebRequest -Uri "http://localhost:8000/metrics/" | Select-String "radius_search"
```

**Possible Causes**:
- Prometheus not scraping Django app
- Metrics not being exported (django-prometheus not installed)
- Incorrect datasource configuration in Grafana

**Remediation**:
1. Verify `/metrics/` endpoint accessible: `curl http://localhost:8000/metrics/`
2. Check Prometheus targets: Should show `web:8000` as UP
3. Verify datasource in Grafana: Configuration → Data Sources → Prometheus → Test
4. Check metric names: `radius_search_cache_hits_total`, `django_http_request_duration_seconds_bucket`

---

## 📚 References

### Documentation

- **Deployment Plan**: `doc/operations/PHASE7_DEPLOYMENT_PLAN.md`
- **Performance Report**: `doc/reports/phases/PHASE7_DAY6_PERFORMANCE.md`
- **Cache Architecture**: `doc/architecture/SWR_CACHE.md`

### External Resources

- Prometheus Alerting Best Practices: https://prometheus.io/docs/practices/alerting/
- Grafana Dashboard Best Practices: https://grafana.com/docs/grafana/latest/dashboards/
- django-prometheus Documentation: https://github.com/korfuri/django-prometheus

### Metrics Endpoints

- Django metrics: http://localhost:8000/metrics/
- Prometheus UI: http://localhost:9090
- Grafana UI: http://localhost:3000

---

## ✅ Next Steps

After monitoring setup complete:

1. **Start 24h monitoring period** (Phase 1 observation)
2. **Review metrics every 6h** (use checklist above)
3. **Document observations** in deployment log
4. **Decision point** (after 24h):
   - If stable → **Phase 2 (25% rollout)**
   - If issues → **Investigate and fix** or **rollback**

**Monitoring Status**: 🟡 IN PROGRESS  
**Next Review**: +6h  
**Phase 1 End**: +24h (November 20, 2025 ~01:00 UTC)

---

**Document Version**: 1.0  
**Last Updated**: November 19, 2025  
**Author**: GitHub Copilot (Phase 7 Day 7)
