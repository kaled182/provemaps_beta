# Monitoring Stack - Prometheus + Grafana

**Phase 7 Day 7** - Spatial Radius Search Production Monitoring

---

## 📂 Directory Structure

```
docker/
├── prometheus/
│   ├── prometheus.yml          # Prometheus configuration
│   └── alerts/
│       └── radius_search.yml   # Alert rules (16 alerts)
├── grafana/
│   ├── datasources/
│   │   └── prometheus.yml      # Prometheus datasource config
│   └── dashboards/
│       ├── dashboard.yml        # Dashboard provisioning config
│       └── phase7_radius_search.json  # Dashboard definition (8 panels)
└── docker-compose.yml           # Updated with Prometheus + Grafana services
```

---

## 🚀 Quick Start

### Option 1: Deploy Script (Recommended)

```powershell
# From project root
.\scripts\deploy_monitoring.ps1
```

This script will:
- ✅ Check Docker availability
- ✅ Start Prometheus + Grafana containers
- ✅ Wait for services to be healthy
- ✅ Verify Prometheus targets
- ✅ Display access URLs and next steps

### Option 2: Manual Deployment

```powershell
cd docker
docker compose up -d prometheus grafana

# Check status
docker compose ps

# View logs
docker compose logs -f prometheus grafana
```

---

## 📊 Access Points

| Service | URL | Credentials | Purpose |
|---------|-----|-------------|---------|
| **Prometheus** | http://localhost:9090 | None | Metrics storage, alerting |
| **Grafana** | http://localhost:3000 | admin/admin | Dashboards, visualization |
| **Django Metrics** | http://localhost:8000/metrics/ | None | Prometheus metrics endpoint |

---

## 🎯 Prometheus Configuration

**Scrape Targets** (`prometheus.yml`):
- `django` job: Scrapes Django app at `web:8000/metrics/` every 30s
- `prometheus` job: Self-monitoring

**Alert Rules** (`alerts/radius_search.yml`):
- **5 Critical alerts**: Error rate, latency, cache down, Celery failures, Redis memory
- **6 Warning alerts**: Low cache hit rate, elevated latency, stale rate, backlog
- **2 Info alerts**: Cache warming, low adoption

**Storage**:
- Retention: 30 days
- Volume: `prometheus_data` (persistent)

---

## 📈 Grafana Configuration

**Datasource** (auto-provisioned):
- Name: `Prometheus`
- URL: `http://prometheus:9090`
- Default: Yes

**Dashboard** (auto-provisioned):
- Name: `Phase 7 - Spatial Radius Search Monitoring`
- Folder: `Production`
- UID: `phase7-radius-search`
- Refresh: 30s
- Time range: Last 6 hours

**Panels** (8 total):
1. Cache Hit Rate (gauge)
2. API Latency - p50/p95/p99 (graph)
3. API Request Rate by Status (stacked area)
4. Celery Task Rate (graph)
5. Redis Memory Usage (graph)
6. Cache Operations Distribution (donut)
7. Cache Operation Latency (graph)
8. Radius Search Result Count (bar chart)

---

## 🔍 Verification Steps

### 1. Check Prometheus Targets

```powershell
# Web UI
Start-Process "http://localhost:9090/targets"

# API
Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets" | 
  ConvertTo-Json -Depth 5
```

**Expected**: `django` target should show `UP` status

### 2. Verify Alert Rules

```powershell
# Web UI
Start-Process "http://localhost:9090/rules"

# API
Invoke-RestMethod -Uri "http://localhost:9090/api/v1/rules" | 
  ConvertTo-Json -Depth 5
```

**Expected**: 16 rules loaded from `radius_search.yml`

### 3. Check Metrics Availability

```powershell
# Query cache hit rate
Invoke-WebRequest -Uri "http://localhost:9090/api/v1/query?query=radius_search_cache_hits_total" -UseBasicParsing

# Check Django metrics endpoint
Invoke-WebRequest -Uri "http://localhost:8000/metrics/" | 
  Select-String "radius_search"
```

**Expected**: Metrics should be available (may take 30s for first scrape)

### 4. Access Grafana Dashboard

```powershell
# Open Grafana
Start-Process "http://localhost:3000"

# Login: admin/admin
# Navigate: Dashboards → Production → Phase 7 - Spatial Radius Search Monitoring
```

**Expected**: Dashboard should load with 8 panels (may show "No data" initially)

---

## 🛠️ Troubleshooting

### Prometheus Not Scraping Django

**Symptoms**: No data in Grafana, Prometheus target shows `DOWN`

**Solutions**:
```powershell
# Check Django metrics endpoint
Invoke-WebRequest -Uri "http://localhost:8000/metrics/" -UseBasicParsing

# Check network connectivity
docker compose exec prometheus wget -O- http://web:8000/metrics/

# Restart Prometheus
docker compose restart prometheus
```

### Grafana Dashboard Not Auto-Provisioned

**Symptoms**: Dashboard not found in Grafana UI

**Solutions**:
```powershell
# Check provisioning logs
docker compose logs grafana | Select-String "provision"

# Manually import dashboard
# 1. Login to Grafana
# 2. Dashboards → Import
# 3. Upload: docker/grafana/dashboards/phase7_radius_search.json
# 4. Select datasource: Prometheus
# 5. Import
```

### Prometheus Alerts Not Loading

**Symptoms**: No rules in Prometheus UI

**Solutions**:
```powershell
# Check alert file syntax
docker compose exec prometheus promtool check rules /etc/prometheus/alerts/radius_search.yml

# Reload Prometheus config
Invoke-WebRequest -Uri "http://localhost:9090/-/reload" -Method POST

# Restart Prometheus
docker compose restart prometheus
```

### Metrics Show "No Data"

**Symptoms**: Grafana panels empty

**Possible Causes**:
- Prometheus not scraping Django (check targets)
- No traffic to radius search API yet (expected if just deployed)
- Time range too far in past (adjust to "Last 15 minutes")

**Solutions**:
- Generate test traffic: Access http://localhost:8000/api/v1/inventory/sites/radius?lat=-15.7942&lng=-47.8825&radius_km=10
- Wait 30s for next scrape
- Check Prometheus query: http://localhost:9090/graph?g0.expr=radius_search_cache_hits_total

---

## 📚 Documentation

- **Setup Guide**: `doc/operations/MONITORING_SETUP.md`
- **Deployment Plan**: `doc/operations/PHASE7_DEPLOYMENT_PLAN.md`
- **Performance Report**: `doc/reports/phases/PHASE7_DAY6_PERFORMANCE.md`

---

## 🔧 Maintenance

### Update Alert Rules

1. Edit `docker/prometheus/alerts/radius_search.yml`
2. Validate syntax:
   ```powershell
   docker compose exec prometheus promtool check rules /etc/prometheus/alerts/radius_search.yml
   ```
3. Reload Prometheus:
   ```powershell
   Invoke-WebRequest -Uri "http://localhost:9090/-/reload" -Method POST
   ```

### Update Dashboard

1. Edit `docker/grafana/dashboards/phase7_radius_search.json`
2. Restart Grafana:
   ```powershell
   docker compose restart grafana
   ```
3. Or manually import via Grafana UI

### Backup Prometheus Data

```powershell
# Create snapshot
docker run --rm -v docker_prometheus_data:/data -v ${PWD}:/backup alpine tar czf /backup/prometheus-backup-$(Get-Date -Format "yyyyMMdd-HHmmss").tar.gz /data

# Restore from snapshot
docker run --rm -v docker_prometheus_data:/data -v ${PWD}:/backup alpine tar xzf /backup/prometheus-backup-YYYYMMDD-HHMMSS.tar.gz
```

---

## 🎯 Monitoring Checklist (Phase 1 - 24h)

**Every 6 hours**:
- [ ] Check Grafana dashboard for anomalies
- [ ] Review Prometheus active alerts: http://localhost:9090/alerts
- [ ] Verify cache hit rate > 30% (warmup) or > 70% (after 2h)
- [ ] Confirm p95 latency < 200ms
- [ ] Check Redis memory < 1GB
- [ ] Review Django logs: `docker compose logs web --tail 100 | Select-String "ERROR"`
- [ ] Review Celery logs: `docker compose logs celery --tail 100 | Select-String "FAILED"`

**After 24h**:
- [ ] Generate monitoring summary report
- [ ] Export Grafana screenshots for documentation
- [ ] Decision: Proceed to Phase 2 (25%) or rollback
- [ ] Update stakeholders

---

## 📊 Expected Metrics (Healthy State)

| Metric | Target | Panel |
|--------|--------|-------|
| **Cache Hit Rate** | > 70% | Panel 1 (Gauge) |
| **API p95 Latency** | < 200ms | Panel 2 (Graph) |
| **Error Rate** | < 0.1% | Panel 3 (Area) |
| **Celery Failures** | 0 | Panel 4 (Graph) |
| **Redis Memory** | < 1GB | Panel 5 (Graph) |
| **Cache GET Latency** | < 10ms | Panel 7 (Graph) |

---

## 🚨 Alert Thresholds

### Critical (Immediate Action Required)

- **RadiusSearchHighErrorRate**: > 1% for 5m → Rollback deployment
- **RadiusSearchHighLatency**: p95 > 500ms for 10m → Investigate DB/cache
- **RadiusSearchCacheDown**: 100% misses for 15m → Check Redis
- **RadiusCacheRefreshTaskFailing**: Any failures → Check Celery logs
- **RedisMemoryExhaustion**: > 2GB → Review TTL settings

### Warning (Monitor Closely)

- **RadiusSearchLowCacheHitRate**: < 50% for 30m → May need TTL adjustment
- **RadiusSearchElevatedLatency**: p95 > 200ms for 15m → Acceptable but degraded
- **RadiusSearchHighStaleRate**: > 20% stale for 20m → Check fresh TTL
- **RadiusSearchCacheSlowness**: p95 > 50ms for 10m → Redis performance issue
- **RadiusCacheRefreshBacklog**: Queue > 100 for 10m → Scale Celery workers

---

## 🔗 Quick Links

- Prometheus UI: http://localhost:9090
- Prometheus Targets: http://localhost:9090/targets
- Prometheus Alerts: http://localhost:9090/alerts
- Prometheus Rules: http://localhost:9090/rules
- Grafana UI: http://localhost:3000
- Django Metrics: http://localhost:8000/metrics/

---

**Status**: ✅ Ready for Phase 1 (10% rollout) monitoring  
**Last Updated**: November 19, 2025  
**Version**: 1.0
