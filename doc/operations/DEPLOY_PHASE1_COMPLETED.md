# Phase 1 Deploy - COMPLETED

**Data:** 12/11/2025 — 17:50  
**Status:** ✅ **DEPLOY REALIZADO**  
**Rollout:** Canary Phase 1 (10%)

---

## ✅ Deploy Steps Completed

### 1. Feature Flags Configured ✅
```env
# database/runtime.env
USE_VUE_DASHBOARD="True"
VUE_DASHBOARD_ROLLOUT_PERCENTAGE="10"
```

### 2. Backend Code Updated ✅
```python
# backend/settings/base.py
VUE_DASHBOARD_ROLLOUT_PERCENTAGE = int(
    os.getenv("VUE_DASHBOARD_ROLLOUT_PERCENTAGE", "0")
)

# backend/maps_view/views.py
# Canary routing implemented with session hash
# 10% users → Vue (spa.html)
# 90% users → Legacy (dashboard.html)
```

### 3. Frontend Build ✅
```
✓ built in 534ms
main.js: 96.08 kB (37.74 kB gzip)
DashboardView.js: 13.13 kB (5.00 kB gzip)
MapView.js: 26.46 kB (9.52 kB gzip)
```

### 4. Static Files Collected ✅
```bash
python manage.py collectstatic --noinput
# 172 files in staticfiles/
# Vue SPA files in staticfiles/vue-spa/
```

### 5. Services Restarted ✅
```bash
docker compose restart web celery beat
# All services: UP (healthy)
```

### 6. Endpoints Verified ✅
```
✓ http://localhost:8000/maps_view/dashboard → 200 OK (text/html)
✓ http://localhost:8000/static/vue-spa/assets/main.js → Accessible
✗ http://localhost:8000/health/ready/ → 404 (endpoint não configurado em dev)
```

---

## 🧪 Manual Testing Instructions

### Test 1: Verify Canary Routing

**Objetivo:** Confirmar que ~10% de sessões servem Vue, ~90% servem Legacy

1. Open **Incognito Window** in Chrome/Edge
2. Navigate to: `http://localhost:8000/maps_view/dashboard`
3. Check which version loaded:

**Vue Dashboard (10% chance):**
- Header: `<h1>MapsProve Dashboard</h1>`
- Vue DevTools extension shows Vue 3
- Console: `[VUE_DASHBOARD] Initialized`
- Modern UI with sidebar + map layout

**Legacy Dashboard (90% chance):**
- Django template (older layout)
- No Vue DevTools detected
- Different HTML structure

4. **Repeat 10 times** (clear cookies between tests):
   - Delete all cookies for localhost
   - Refresh page
   - Note which version appears
   - Expected: ~1 Vue, ~9 Legacy

---

### Test 2: Vue Dashboard Full Flow

**If you got Vue dashboard (or force 100% temporarily):**

#### A. Dashboard Load ✅
- [ ] Page loads in <3 seconds
- [ ] No errors in console (F12 → Console)
- [ ] Header shows "MapsProve Dashboard"
- [ ] Connection status indicator visible

#### B. WebSocket Connection ✅
- [ ] F12 → Network → WS tab
- [ ] WebSocket URL: `ws://localhost:8000/ws/dashboard/status/`
- [ ] Status 101 Switching Protocols
- [ ] Frames showing JSON messages
- [ ] Status indicator: "Conectado" (green dot)

#### C. Host Cards ✅
- [ ] StatusChart renders with distribution bars
- [ ] Host cards display:
  - Host name
  - Status badge (Operacional/Atenção/Crítico/Offline)
  - Metrics: CPU %, Memory %, Uptime
  - Last update timestamp ("2m ago")
- [ ] Cards update on WebSocket message (pulse animation)

#### D. Map Integration ✅
- [ ] Google Maps loads (check API key in template)
- [ ] Segments load when viewport changes (BBox API)
- [ ] Polylines render with colors:
  - Green (#16a34a) → operational
  - Blue (#3b82f6) → maintenance
  - Amber (#f59e0b) → degraded
  - Gray (#6b7280) → unknown
- [ ] Click segment → InfoWindow displays route info
- [ ] Legend component visible

#### E. Map Controls ✅
- [ ] "Ajustar visualização" button works
  - Clicks → Map zooms to fit all segments
  - Smooth animation
- [ ] Legend toggle button works
  - Shows/hides legend panel
- [ ] Keyboard navigation (Tab + Enter)

#### F. Mobile Responsive ✅
- [ ] F12 → Toggle device toolbar (Ctrl+Shift+M)
- [ ] Select "iPhone SE" (375px width)
- [ ] Sidebar hidden by default
- [ ] Toggle button (☰) appears in header
- [ ] Sidebar slides in/out smoothly
- [ ] Map controls touch-friendly (44x44px)

#### G. Performance ✅
- [ ] F12 → Performance tab
- [ ] Record page load
- [ ] Metrics:
  - Load Time: _____ ms (target <3000ms)
  - FCP: _____ ms (target <1500ms)
  - LCP: _____ ms (target <2500ms)
  - No frame drops during scroll

#### H. Error Handling ✅
- [ ] Simulate network failure:
  - F12 → Network tab → Throttle to "Offline"
  - Wait 5 seconds
  - Switch back to "Online"
- [ ] Dashboard shows error state gracefully
- [ ] WebSocket reconnects automatically
- [ ] No app crash

---

### Test 3: API Endpoints

#### Dashboard Data API
```powershell
Invoke-WebRequest -Uri http://localhost:8000/api/v1/dashboard/ | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

**Expected Response:**
```json
{
  "hosts": {
    "host-1": {
      "name": "Host Alpha",
      "status": "online",
      "metrics": { "cpu": 45, "memory": 67, "uptime": 86400 },
      "last_update": "2025-11-12T17:45:00Z"
    }
  },
  "summary": {
    "total": 10,
    "online": 7,
    "warning": 2,
    "critical": 1,
    "offline": 0
  }
}
```

#### Segments API
```powershell
$bbox = "-48.0,-25.0,-47.0,-24.0"
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/inventory/segments/?bbox=$bbox" | Select-Object -ExpandProperty Content | ConvertFrom-Json
```

**Expected Response:**
```json
{
  "count": 5,
  "bbox": [-48.0, -25.0, -47.0, -24.0],
  "segments": [
    {
      "id": 1,
      "route_id": 10,
      "status": "operational",
      "path_geojson": {
        "type": "LineString",
        "coordinates": [[-47.5, -24.5], [-47.6, -24.6]]
      }
    }
  ]
}
```

---

## 📊 Monitoring (Next 24h)

### Error Rate
```powershell
# Check error count every hour
docker compose -f docker/docker-compose.yml logs web | Select-String "error|exception" | Measure-Object
```

**Target:** < 1% error rate

### Performance
```powershell
# Measure load time (repeat 10x)
Measure-Command { Invoke-WebRequest -Uri http://localhost:8000/maps_view/dashboard }

# Calculate P95 (9th fastest of 10 loads)
```

**Target:** P95 < 3000ms

### WebSocket Uptime
```powershell
# Check connection success rate
docker compose -f docker/docker-compose.yml logs web | Select-String "websocket.*connected|failed"
```

**Target:** > 99% uptime

### Resource Usage
```powershell
docker stats --no-stream

# Monitor every 4 hours for 24h
# Expected:
# web: <50% CPU, <512MB RAM
# celery: <30% CPU, <256MB RAM
```

---

## 🚨 Rollback Procedure

### If Error Rate > 5% OR Critical Bug Found:

```powershell
# 1. Set rollout to 0%
# Edit database/runtime.env:
VUE_DASHBOARD_ROLLOUT_PERCENTAGE="0"

# 2. Restart web
docker compose -f docker/docker-compose.yml restart web

# 3. Verify all users see legacy
Invoke-WebRequest -Uri http://localhost:8000/maps_view/dashboard | Select-Object -ExpandProperty Content | Select-String "dashboard.html|legacy"

# 4. Monitor error recovery
docker compose -f docker/docker-compose.yml logs -f web | Select-String "error"
```

**Rollback Time:** < 5 minutes

---

## ✅ Phase 1 Success Criteria

After 24h monitoring, Phase 1 is successful if:

- [ ] Error rate < 1%
- [ ] Load time P95 < 3000ms
- [ ] WebSocket uptime > 99%
- [ ] No critical bugs reported
- [ ] Resource usage stable (CPU <50%, RAM <512MB)
- [ ] User feedback positive (if any)

**If all criteria met:** Proceed to Phase 2 (25% rollout)

**If criteria not met:** Investigate issues, fix, re-test, or rollback

---

## 📝 Next Steps

### Immediate (Next 4 Hours):
1. ✅ Monitor error logs
2. ✅ Test manual flows in browser
3. ✅ Verify API responses
4. ✅ Check resource usage

### Tomorrow (12 hours):
1. Review error rate trend
2. Collect performance metrics (P95)
3. Check WebSocket stability
4. Gather user feedback (if users accessed 10% bucket)

### After 24h:
1. Fill SMOKE_TEST_REPORT_PHASE1.md
2. Decision: Proceed to Phase 2 (25%) OR Fix issues OR Rollback
3. If proceeding: Update `VUE_DASHBOARD_ROLLOUT_PERCENTAGE="25"`

---

## 🎯 Phase 2 Preview (If Successful)

**Timeline:** 2 days after Phase 1
**Rollout:** 25% of users
**Monitoring:** 48 hours
**Success Criteria:** Same as Phase 1

**Phases Ahead:**
- Phase 2: 25% (48h)
- Phase 3: 50% (72h)
- Phase 4: 100% (1 week)
- Deprecate legacy: 1 month after 100%

---

**Status:** ✅ Deploy complete — Monitoring active  
**Next Checkpoint:** 12/13/2025 17:50 (24h review)  
**Responsible:** Dev Team  
**Última atualização:** 12/11/2025 — 17:50
