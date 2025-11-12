# Deploy Staging - Sprint 3

## Feature Flag Canary Rollout Strategy

### 1. Configuração da Feature Flag

**Arquivo:** `backend/settings/base.py`

```python
# Vue 3 Dashboard Feature Flag (Phase 11)
USE_VUE_DASHBOARD = env.bool('USE_VUE_DASHBOARD', default=False)
VUE_DASHBOARD_ROLLOUT_PERCENTAGE = env.int('VUE_DASHBOARD_ROLLOUT_PERCENTAGE', default=0)
```

### 2. Rollout Gradual

#### Fase 0: Preparação (0%)
```bash
# .env configuration
USE_VUE_DASHBOARD=True
VUE_DASHBOARD_ROLLOUT_PERCENTAGE=0
```

**Ações:**
- ✅ Build de produção validado (94.34 kB, 532ms)
- ✅ Testes unitários passando (30/30)
- ✅ Testes E2E criados (10+ scenarios)
- ✅ Backup do banco de dados
- ✅ Docker services atualizados

#### Fase 1: Internal Testing (10%)
```bash
VUE_DASHBOARD_ROLLOUT_PERCENTAGE=10
```

**Critérios de Sucesso:**
- [ ] Desenvolvedores validam funcionalidades principais
- [ ] WebSocket conecta corretamente
- [ ] Segments carregam no mapa (BBox API)
- [ ] Dashboard cards exibem hosts
- [ ] Sem erros JavaScript no console
- [ ] Performance aceitável (<3s load time)

**Rollback se:**
- Erros críticos no console
- WebSocket falha constantemente
- Timeout > 5s no carregamento

#### Fase 2: Limited Rollout (25%)
```bash
VUE_DASHBOARD_ROLLOUT_PERCENTAGE=25
```

**Critérios de Sucesso:**
- [ ] Usuários beta reportam UX positiva
- [ ] Sem erros 500 nos logs do backend
- [ ] CPU/Memória estáveis no Docker
- [ ] Redis handles WebSocket load
- [ ] Mobile responsive funcionando

**Rollback se:**
- > 5% de usuários reportam bugs críticos
- Overhead de performance > 20%

#### Fase 3: Majority Rollout (50%)
```bash
VUE_DASHBOARD_ROLLOUT_PERCENTAGE=50
```

**Critérios de Sucesso:**
- [ ] Métricas Prometheus normais
- [ ] Latência P95 < 500ms (dashboard API)
- [ ] Taxa de erro < 1%
- [ ] Feedback positivo de usuários

#### Fase 4: Full Rollout (100%)
```bash
VUE_DASHBOARD_ROLLOUT_PERCENTAGE=100
```

**Critérios de Sucesso:**
- [ ] Todos usuários migrados
- [ ] Legacy dashboard deprecado
- [ ] Documentação atualizada
- [ ] Treinamento concluído

---

## Checklist de Smoke Tests Staging

### Pre-Deploy
- [ ] `npm run test:unit` — 30/30 passando
- [ ] `npm run build` — Build sem erros
- [ ] `docker compose ps` — Todos services healthy
- [ ] `make health` — Backend health check OK
- [ ] Backup DB criado: `make backup-db`

### Deploy Process
1. **Build Frontend**
   ```bash
   cd frontend
   npm run build
   # Output em backend/staticfiles/vue-spa/
   ```

2. **Collect Static Files**
   ```bash
   cd backend
   python manage.py collectstatic --noinput
   ```

3. **Restart Services**
   ```bash
   docker compose -f docker/docker-compose.yml restart web celery beat
   ```

4. **Verify Services**
   ```bash
   docker compose ps
   curl http://localhost:8000/health/ready/
   ```

### Post-Deploy Smoke Tests

#### 1. Dashboard Load
- [ ] Navigate to `/dashboard`
- [ ] Page loads in <3 seconds
- [ ] No errors in browser console
- [ ] Header displays "MapsProve Dashboard"
- [ ] Connection status indicator visible

#### 2. WebSocket Connection
- [ ] Status indicator shows "Conectado" (green)
- [ ] WebSocket URL correct: `ws://localhost:8000/ws/dashboard/status/`
- [ ] No connection errors in network tab
- [ ] Reconnection works after simulated disconnect

#### 3. Host Cards
- [ ] StatusChart renders with distribution
- [ ] Host cards display with correct status badges
- [ ] Metrics (CPU, Memory, Uptime) visible
- [ ] Timestamp shows relative time ("2m ago")
- [ ] Pulse animation on updates

#### 4. Map Integration
- [ ] Google Maps loads (or shows API key warning)
- [ ] Segments load on viewport change
- [ ] Polylines render with correct colors
- [ ] Click segment → InfoWindow displays
- [ ] Legend toggles on/off

#### 5. Map Controls
- [ ] Fit bounds button centers all segments
- [ ] Legend toggle works
- [ ] Fullscreen mode activates (F11)
- [ ] All controls keyboard accessible (Tab + Enter)

#### 6. Mobile Responsive
- [ ] Resize to 375px width
- [ ] Sidebar toggle button appears
- [ ] Sidebar slides in/out smoothly
- [ ] Touch controls work (tap, swipe)
- [ ] No horizontal scroll

#### 7. Performance
- [ ] Dashboard loads <3s (check Network tab)
- [ ] Virtual scroll works with 50+ hosts
- [ ] No memory leaks after 5min usage
- [ ] Smooth 60fps scrolling
- [ ] CPU usage <30% idle

#### 8. Error Handling
- [ ] Simulate API failure (block /api/*)
- [ ] Error boundary shows fallback UI
- [ ] Retry button re-fetches data
- [ ] No crashes, graceful degradation

#### 9. Accessibility
- [ ] Screen reader reads status badges
- [ ] Tab navigation cycles through controls
- [ ] Enter key activates buttons
- [ ] Focus indicators visible
- [ ] ARIA labels present (inspect elements)

#### 10. Data Integrity
- [ ] Segment status matches route status (active → operational)
- [ ] Real-time updates reflect in cards
- [ ] Bbox filtering returns correct segments
- [ ] No duplicate segments in map

---

## Nginx Configuration (Production)

**Arquivo:** `/etc/nginx/sites-available/provemaps`

```nginx
server {
    listen 80;
    server_name mapsprove.example.com;

    # Static files
    location /static/ {
        alias /var/www/provemaps/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Vue SPA
    location /vue-spa/ {
        alias /var/www/provemaps/staticfiles/vue-spa/;
        try_files $uri $uri/ /vue-spa/index.html;
        expires 7d;
        add_header Cache-Control "public";
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django admin
    location /admin/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }

    # Feature flag routing
    location /dashboard {
        # Check feature flag cookie/header
        # If enabled, serve Vue app
        # Else, proxy to legacy Django view
        
        if ($cookie_use_vue_dashboard = "1") {
            rewrite ^/dashboard$ /vue-spa/index.html last;
        }
        
        proxy_pass http://localhost:8000;
    }
}
```

---

## Monitoring & Alerts

### Prometheus Metrics
```yaml
# Alert rules for Vue dashboard
groups:
  - name: vue_dashboard
    rules:
      - alert: DashboardHighErrorRate
        expr: rate(http_requests_total{path="/dashboard",status=~"5.."}[5m]) > 0.05
        annotations:
          summary: "Dashboard error rate > 5%"
      
      - alert: WebSocketDisconnects
        expr: rate(websocket_disconnects_total[5m]) > 10
        annotations:
          summary: "High WebSocket disconnect rate"
      
      - alert: SlowDashboardLoad
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket{path="/dashboard"}) > 3
        annotations:
          summary: "Dashboard P95 load time > 3s"
```

### Logs to Monitor
```bash
# Django logs
tail -f backend/logs/django.log | grep -E "dashboard|websocket"

# Celery logs
tail -f backend/logs/celery.log

# Nginx access logs
tail -f /var/log/nginx/access.log | grep dashboard
```

---

## Rollback Procedure

### Quick Rollback (< 5 min)
```bash
# 1. Disable feature flag
export VUE_DASHBOARD_ROLLOUT_PERCENTAGE=0

# 2. Restart services
docker compose restart web celery beat

# 3. Verify legacy dashboard
curl http://localhost:8000/dashboard | grep "Legacy Dashboard"
```

### Full Rollback (< 15 min)
```bash
# 1. Checkout previous commit
git checkout <previous-stable-commit>

# 2. Rebuild frontend (if needed)
cd frontend && npm run build

# 3. Collect static
cd backend && python manage.py collectstatic --noinput

# 4. Restart all services
docker compose down && docker compose up -d

# 5. Verify
make health && make smoke-test
```

---

## Post-Deploy Tasks

- [ ] Update CHANGELOG.md com Sprint 3 features
- [ ] Tag release: `git tag v1.3.0-sprint3`
- [ ] Update Confluence/Wiki documentation
- [ ] Notify team in Slack #releases
- [ ] Schedule retrospective meeting
- [ ] Archive Sprint 3 Jira tickets

---

## Success Criteria Summary

| Metric | Target | Atual |
|--------|--------|-------|
| Load Time (P95) | <3s | TBD |
| Error Rate | <1% | TBD |
| Test Coverage | >80% | 30/30 unit tests |
| Bundle Size | <100kB gzip | 36.98 kB ✅ |
| Mobile Score (Lighthouse) | >90 | TBD |
| Accessibility Score | >90 | TBD |
| WebSocket Uptime | >99% | TBD |

---

**Última atualização:** Sprint 3 — Parte 2  
**Responsável:** DevOps Team  
**Aprovação:** Tech Lead + Product Owner
