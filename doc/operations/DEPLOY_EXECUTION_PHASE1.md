# Deploy Staging - Phase 1 Execution Checklist

**Data:** 12/11/2025  
**Fase:** Canary Rollout Phase 1 (10%)  
**Status:** 🔄 EM PROGRESSO

---

## ✅ Configuração Completa

### 1. Feature Flags Habilitadas
```bash
# database/runtime.env
USE_VUE_DASHBOARD="True"
VUE_DASHBOARD_ROLLOUT_PERCENTAGE="10"
```

### 2. Backend Configurado
```python
# backend/settings/base.py
USE_VUE_DASHBOARD = os.getenv("USE_VUE_DASHBOARD", "false").lower() == "true"
VUE_DASHBOARD_ROLLOUT_PERCENTAGE = int(
    os.getenv("VUE_DASHBOARD_ROLLOUT_PERCENTAGE", "0")
)
```

### 3. Canary Routing Implementado
```python
# backend/maps_view/views.py
def dashboard_view(request):
    # Hash-based user assignment for consistent rollout
    # 10% of users → Vue dashboard (spa.html)
    # 90% of users → Legacy dashboard (dashboard.html)
```

### 4. Frontend Build
```
✓ built in 534ms
main.js: 96.08 kB (37.74 kB gzip)
```

---

## 📋 Próximos Passos (Manual)

### Passo 1: Verificar Serviços Docker
```powershell
# Check all services running
cd d:\provemaps_beta
docker compose -f docker/docker-compose.yml ps

# Expected services: web, celery, beat, redis, postgres
```

### Passo 2: Coletar Static Files
```powershell
cd d:\provemaps_beta\backend
python manage.py collectstatic --noinput

# Verify Vue SPA files copied
ls ../backend/staticfiles/vue-spa/
# Should see: index.html, assets/main.js, assets/*.css
```

### Passo 3: Reload Django Config
```powershell
# Option A: Restart web service (preferred)
docker compose -f docker/docker-compose.yml restart web

# Option B: Reload in Python shell
docker compose -f docker/docker-compose.yml exec web python manage.py shell
>>> from setup_app.services.runtime_settings import reload_config
>>> reload_config()
>>> exit()
```

### Passo 4: Restart Celery Workers
```powershell
docker compose -f docker/docker-compose.yml restart celery beat
```

### Passo 5: Verificar Serviços
```powershell
# Health check
curl http://localhost:8000/health/ready/

# Check dashboard endpoint
curl -I http://localhost:8000/maps_view/dashboard

# Verify static assets
curl -I http://localhost:8000/static/vue-spa/assets/main.js
```

---

## 🧪 Executar Smoke Tests

### Abrir Navegador e Testar:

1. **Dashboard Load (10% chance Vue, 90% legacy):**
   ```
   http://localhost:8000/maps_view/dashboard
   ```
   - Refresh várias vezes para testar diferentes sessões
   - ~10% should see Vue dashboard (h1: "MapsProve Dashboard")
   - ~90% should see legacy (Django template)

2. **Forçar Vue Dashboard (test mode):**
   - Limpar cookies/session
   - Refresh até pegar bucket <10
   - Ou temporariamente: `VUE_DASHBOARD_ROLLOUT_PERCENTAGE="100"`

3. **Console Verification:**
   - F12 → Console
   - Should see: `[VUE_DASHBOARD] Canary Rollout Active: 10%`
   - No errors

4. **WebSocket Connection:**
   - F12 → Network → WS tab
   - Should see: `ws://localhost:8000/ws/dashboard/status/`
   - Status 101 (Switching Protocols)
   - Frames showing JSON messages

5. **Host Cards Rendering:**
   - StatusChart with distribution
   - Host cards with metrics
   - Status badges colored correctly

6. **Map Integration:**
   - Google Maps loads
   - Segments render on viewport change
   - Click segment → InfoWindow

---

## 📊 Monitoring Commands

### Check Error Logs
```powershell
# Web service logs
docker compose -f docker/docker-compose.yml logs -f web | Select-String -Pattern "error|exception|traceback" -Context 2

# Celery logs
docker compose -f docker/docker-compose.yml logs -f celery | Select-String -Pattern "error" -Context 1
```

### Check WebSocket Activity
```powershell
docker compose -f docker/docker-compose.yml logs web | Select-String -Pattern "websocket|channels" | Select-Object -Last 20
```

### Resource Usage
```powershell
docker stats --no-stream

# Expected:
# web: < 50% CPU, < 512 MB
# celery: < 30% CPU, < 256 MB
# redis: < 10% CPU, < 128 MB
```

### Performance Metrics
```powershell
# Check response times
Measure-Command { curl http://localhost:8000/maps_view/dashboard }

# Target: < 3 seconds
```

---

## 🚨 Rollback (Se Necessário)

### Quick Rollback (<5 min)
```powershell
# 1. Disable canary (back to 0%)
# Edit database/runtime.env:
VUE_DASHBOARD_ROLLOUT_PERCENTAGE="0"

# 2. Restart web
docker compose -f docker/docker-compose.yml restart web

# 3. Verify all users see legacy
curl http://localhost:8000/maps_view/dashboard | Select-String "dashboard.html|legacy"
```

### Full Rollback (<15 min)
```powershell
# 1. Disable feature flag completely
# Edit database/runtime.env:
USE_VUE_DASHBOARD="False"

# 2. Restart all services
docker compose -f docker/docker-compose.yml restart

# 3. Clear cache
docker compose -f docker/docker-compose.yml exec redis redis-cli FLUSHALL
```

---

## ✅ Success Criteria (24h monitoring)

### Metrics to Track:
- [ ] **Error Rate:** < 1%
  ```powershell
  docker compose logs web | Select-String "error" | Measure-Object
  ```

- [ ] **Load Time P95:** < 3s
  - Use browser DevTools Performance tab
  - Measure 10 page loads, calculate P95

- [ ] **WebSocket Uptime:** > 99%
  ```powershell
  docker compose logs web | Select-String "websocket.*connected|disconnected"
  ```

- [ ] **CPU/Memory:** Stable
  ```powershell
  docker stats --no-stream | Select-Object -First 5
  ```

- [ ] **No Critical Bugs:** Console errors, data corruption, crashes

---

## 📝 Report Template

After 24h monitoring, fill SMOKE_TEST_REPORT_PHASE1.md:

```markdown
## Phase 1 Results (10%)

**Metrics:**
- Error Rate: _____ % (target <1%)
- Load Time P95: _____ ms (target <3000ms)
- WebSocket Uptime: _____ % (target >99%)
- User Reports: _____ issues

**Decision:**
- [ ] ✅ Proceed to Phase 2 (25%)
- [ ] ⏸️ Hold - needs fixes
- [ ] ❌ Rollback

**Notes:**
_____
```

---

## 🎯 Next Phase

If successful after 24h:
1. Update `VUE_DASHBOARD_ROLLOUT_PERCENTAGE="25"`
2. Restart web service
3. Monitor for another 48h
4. Repeat for 50% → 100%

---

**Status:** Configuração completa, pronto para execução manual de deploy e smoke tests.

**Última atualização:** 12/11/2025 — 17:55
