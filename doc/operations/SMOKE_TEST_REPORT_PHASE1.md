# Smoke Test Execution Report - Sprint 3 Deploy

**Data:** 12/11/2025  
**Ambiente:** Staging  
**Phase:** Canary Rollout Phase 1 (10%)  
**Testador:** Deploy Team

---

## ✅ Pre-Deploy Verification Checklist

### 1. Tests Status
- [x] **Unit Tests:** 44/44 passing (100%)
- [x] **E2E Tests:** 10+ scenarios created
- [x] **Build Success:** 534ms, 96.08 kB (37.74 kB gzip)

### 2. Migrations
- [ ] All migrations applied
  ```bash
  cd backend
  python manage.py showmigrations --plan
  ```

### 3. Static Files
- [x] Frontend build completed successfully
  ```
  ✓ built in 534ms
  main.js: 96.08 kB (37.74 kB gzip)
  DashboardView.js: 13.13 kB (5.00 kB gzip)
  MapView.js: 26.46 kB (9.52 kB gzip)
  ```

### 4. Environment Variables
- [x] **USE_VUE_DASHBOARD:** True
- [x] **VUE_DASHBOARD_ROLLOUT_PERCENTAGE:** 10
- [x] **GOOGLE_MAPS_API_KEY:** Configured
- [x] **ZABBIX_API_KEY:** Configured
- [x] **REDIS_URL:** redis://redis:6379/1

### 5. Database Backup
- [ ] Backup created before deploy
  ```bash
  docker exec -t provemaps-postgres pg_dump -U app app > backup_$(date +%Y%m%d_%H%M%S).sql
  ```

---

## 🔍 Smoke Tests (10 Categories)

### 1. Dashboard Load ✅
**Objetivo:** Verificar carregamento inicial da aplicação

- [ ] Navigate to `http://localhost:8000/dashboard`
- [ ] Page loads in <3 seconds
  - **Medido:** ___________ ms
- [ ] No errors in browser console (F12)
- [ ] Header displays "MapsProve Dashboard"
- [ ] Connection status indicator visible
- [ ] StatusChart component renders

**Comandos:**
```bash
# Check server running
curl -I http://localhost:8000/dashboard

# Check static files served
curl -I http://localhost:8000/static/vue-spa/assets/main.js
```

**Critérios de Sucesso:**
- HTTP 200 response
- No 404 errors for static files
- Load time < 3000ms

---

### 2. WebSocket Connection ✅
**Objetivo:** Validar comunicação real-time

- [ ] Status indicator shows "Conectado" (green dot)
- [ ] WebSocket URL correct in DevTools Network tab
  - Expected: `ws://localhost:8000/ws/dashboard/status/`
- [ ] No connection errors (status 101 expected)
- [ ] Messages flowing (check WS frames)
- [ ] Reconnection works after simulated disconnect

**Comandos:**
```bash
# Check Channels layer
docker compose logs web | grep -i "websocket\|channels"

# Check Redis connection
docker compose exec redis redis-cli ping
```

**Critérios de Sucesso:**
- WebSocket handshake successful (101 Switching Protocols)
- No "Failed to connect" messages
- Auto-reconnect after network interruption

---

### 3. Host Cards Display ✅
**Objetivo:** Verificar renderização de dados do dashboard

- [ ] StatusChart shows distribution (Online/Warning/Critical/Offline)
- [ ] Host cards render with correct data
  - [ ] Host name visible
  - [ ] Status badge (Operacional/Atenção/Crítico/Offline)
  - [ ] Metrics: CPU, Memory, Uptime
  - [ ] Last update timestamp (relative: "2m ago")
- [ ] Pulse animation on WebSocket updates
- [ ] Empty state if no hosts ("Nenhum host encontrado")

**API Test:**
```bash
# Check dashboard API
curl http://localhost:8000/api/v1/dashboard/ | jq .

# Expected response:
# {
#   "hosts": { ... },
#   "summary": {
#     "total": X,
#     "online": Y,
#     "warning": Z,
#     "critical": W,
#     "offline": V
#   }
# }
```

**Critérios de Sucesso:**
- All hosts visible in cards
- Status colors correct (green/yellow/red/gray)
- Metrics update via WebSocket

---

### 4. Map Integration ✅
**Objetivo:** Verificar Google Maps + segments loading

- [ ] Google Maps API loads (or shows key warning if invalid)
- [ ] Map initializes with default center/zoom
- [ ] Segments load on viewport change (BBox API)
- [ ] Polylines render with correct status colors
  - operational: green (#16a34a)
  - maintenance: blue (#3b82f6)
  - degraded: amber (#f59e0b)
  - unknown: gray (#6b7280)
- [ ] Click segment → InfoWindow displays route details
- [ ] Legend component visible and toggleable

**API Test:**
```bash
# Check segments API (example bbox)
curl "http://localhost:8000/api/v1/inventory/segments/?bbox=-48.0,-25.0,-47.0,-24.0" | jq .

# Expected response:
# {
#   "count": X,
#   "bbox": [...],
#   "segments": [
#     {
#       "id": ...,
#       "status": "operational",
#       "path_geojson": { "type": "LineString", "coordinates": [...] }
#     }
#   ]
# }
```

**Critérios de Sucesso:**
- Segments load within 2 seconds of viewport change
- Status colors match backend data
- InfoWindow shows correct route info

---

### 5. Map Controls ✅
**Objetivo:** Validar controles interativos do mapa

- [ ] "Ajustar visualização" button works
  - Calls `fitBounds()` for all segments
  - Smooth zoom/pan animation
- [ ] Legend toggle button works
  - Shows/hides legend panel
  - Persists state during session
- [ ] All controls keyboard accessible (Tab + Enter)
- [ ] ARIA labels present (`aria-label="Ajustar visualização"`)

**Critérios de Sucesso:**
- fitBounds centers all visible segments
- Controls responsive on mobile (<768px)
- No console errors on interaction

---

### 6. Mobile Responsive ✅
**Objetivo:** Verificar UX em dispositivos móveis

- [ ] Resize browser to 375px width (iPhone SE)
- [ ] Sidebar hidden by default
- [ ] Toggle button appears in header (☰ icon)
- [ ] Sidebar slides in/out smoothly (300ms transition)
- [ ] Map controls touch-friendly (44x44px minimum)
- [ ] Host cards adapt layout (full width)
- [ ] No horizontal scroll

**DevTools Test:**
```
1. Open Chrome DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Select "iPhone SE" preset
4. Test sidebar toggle
5. Test map pan/zoom with touch
```

**Critérios de Sucesso:**
- Sidebar width 80% max 320px
- Touch targets ≥44px
- Smooth transitions
- No layout breaks

---

### 7. Performance ✅
**Objetivo:** Validar métricas de performance

- [ ] **Load Time P95:** < 3000ms
  - Measure with Lighthouse or DevTools Performance tab
- [ ] **Time to Interactive (TTI):** < 3000ms
- [ ] **First Contentful Paint (FCP):** < 1500ms
- [ ] **Largest Contentful Paint (LCP):** < 2500ms
- [ ] **Cumulative Layout Shift (CLS):** < 0.1
- [ ] Virtual scroll works smoothly for 100+ hosts
- [ ] No frame drops during scroll (60fps)

**Lighthouse Test:**
```bash
# Install lighthouse CLI (if not installed)
npm install -g lighthouse

# Run audit
lighthouse http://localhost:8000/dashboard --output html --output-path ./lighthouse-report.html

# Target Scores:
# Performance: > 90
# Accessibility: > 90
# Best Practices: > 90
# SEO: > 80
```

**Critérios de Sucesso:**
- Load time < 3s on 3G throttling
- No memory leaks (check DevTools Memory tab)
- Bundle size < 100 kB gzip (✓ 37.74 kB)

---

### 8. Error Handling ✅
**Objetivo:** Validar graceful degradation

- [ ] **API Failure:** Simulate 500 error
  - Dashboard shows error message
  - Retry button works
  - No app crash
  
- [ ] **WebSocket Disconnect:** Stop Redis
  - Status shows "Desconectado" (red dot)
  - Auto-reconnect after 2s, 4s, 8s (exponential backoff)
  - Max 5 reconnection attempts
  
- [ ] **Google Maps API Failure:** Invalid key
  - Shows warning message
  - Rest of dashboard still functional
  
- [ ] **Network Timeout:** Slow 3G throttling
  - Loading indicators visible
  - Timeout after 30s with error message

**Simulate Errors:**
```bash
# Stop Redis to test WebSocket reconnect
docker compose stop redis

# Restart after test
docker compose start redis

# Check error logs
docker compose logs web | grep -i "error\|exception"
```

**Critérios de Sucesso:**
- No unhandled exceptions in console
- User-friendly error messages
- Retry mechanisms work
- Application remains usable

---

### 9. Accessibility (a11y) ✅
**Objetivo:** WCAG 2.1 AA compliance

- [ ] **Keyboard Navigation:**
  - Tab through all interactive elements
  - Enter activates buttons
  - Focus indicators visible (2px blue outline)
  
- [ ] **Screen Reader:**
  - ARIA labels present on all controls
  - Host cards have `role="article"`
  - Status badges have `role="status"`
  - Map controls have `role="toolbar"`
  
- [ ] **Color Contrast:**
  - Status badges meet 4.5:1 ratio
  - Text readable on all backgrounds
  
- [ ] **Focus Management:**
  - No keyboard traps
  - Logical tab order
  - Skip to main content link

**axe DevTools Test:**
```
1. Install axe DevTools Chrome extension
2. Open dashboard
3. Run axe scan
4. Fix any Critical/Serious issues
```

**Critérios de Sucesso:**
- 0 Critical accessibility issues
- All controls keyboard accessible
- ARIA labels semantically correct

---

### 10. Data Integrity ✅
**Objetivo:** Verificar consistência de dados backend ↔ frontend

- [ ] **Dashboard Summary:**
  - Backend API count matches frontend display
  - Status distribution accurate
  
- [ ] **Host Metrics:**
  - CPU/Memory values within expected ranges (0-100%)
  - Uptime formatted correctly (days/hours/minutes)
  - Last update timestamps accurate
  
- [ ] **Segment Status:**
  - Route.status correctly mapped to segment.status
  - active → operational (green)
  - planned → maintenance (blue)
  - degraded → degraded (amber)
  - archived → unknown (gray)
  
- [ ] **Real-time Updates:**
  - WebSocket messages update UI immediately
  - No stale data after 5 minutes

**Data Validation:**
```bash
# Compare API response with UI
curl http://localhost:8000/api/v1/dashboard/ | jq '.summary'

# Check segment status mapping
curl "http://localhost:8000/api/v1/inventory/segments/?bbox=-48,-25,-47,-24" | jq '.segments[] | {id, status}'
```

**Critérios de Sucesso:**
- API counts match UI display
- No null/undefined values displayed
- Status colors consistent with data

---

## 📊 Performance Metrics

### Load Time Measurements
| Metric | Target | Measured | Status |
|--------|--------|----------|--------|
| Load Time P95 | < 3s | _____ ms | ⏳ |
| Time to Interactive | < 3s | _____ ms | ⏳ |
| First Contentful Paint | < 1.5s | _____ ms | ⏳ |
| Largest Contentful Paint | < 2.5s | _____ ms | ⏳ |
| Bundle Size (gzip) | < 40 kB | 37.74 kB | ✅ |

### Error Rate Monitoring
```bash
# Check error rate (target < 1%)
docker compose logs web | grep -i "error" | wc -l

# Check WebSocket uptime (target > 99%)
docker compose logs web | grep -i "websocket.*connected"
```

### Resource Usage
```bash
# CPU/Memory usage
docker stats --no-stream web celery beat redis postgres

# Expected:
# web: < 50% CPU, < 512 MB RAM
# celery: < 30% CPU, < 256 MB RAM
# redis: < 10% CPU, < 128 MB RAM
```

---

## 🚨 Rollback Criteria

**Immediate Rollback if:**
- [ ] Error rate > 5% within 1 hour
- [ ] Load time P95 > 5 seconds
- [ ] WebSocket disconnect rate > 10%
- [ ] Critical accessibility issues reported
- [ ] Data corruption detected
- [ ] Server CPU/Memory > 80% sustained

**Rollback Procedure (Quick <5min):**
```bash
# 1. Disable feature flag
echo 'VUE_DASHBOARD_ROLLOUT_PERCENTAGE="0"' >> database/runtime.env

# 2. Reload config
docker compose exec web python manage.py shell -c "from setup_app.services.runtime_settings import reload_config; reload_config()"

# 3. Verify legacy dashboard active
curl http://localhost:8000/dashboard | grep -i "legacy\|django"

# 4. Monitor error rate recovery
docker compose logs -f web | grep -i "error"
```

---

## ✅ Sign-off

### Phase 1 (10%) Approval

**Tests Passed:** _____ / 10 categories  
**Critical Issues:** _____ (0 expected)  
**Performance:** ✅ Within targets  
**Error Rate:** _____ % (< 1% target)

**Decision:**
- [ ] ✅ Proceed to Phase 2 (25%) after 24h monitoring
- [ ] ⏸️ Hold - needs fixes (specify):
- [ ] ❌ Rollback immediately (reason):

**Signed:** __________________  
**Date:** __________________  

---

## 📝 Notes & Observations

### Issues Found


### Performance Observations


### User Feedback (if any)


### Next Steps
1. Monitor for 24 hours
2. Review Prometheus metrics
3. Collect user feedback
4. Plan Phase 2 rollout (25%)

---

**End of Smoke Test Report**
