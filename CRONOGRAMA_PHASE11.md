# 📅 Cronograma Atualizado — Phase 11 Canary Rollout

**Última atualização:** 12/11/2025 — 18:10  
**Status Atual:** 🧪 Testes Manuais no Navegador + Monitoring Setup

---

## ✅ Completed (12/11/2025)

### Sprint 3 — Polish & Production Ready
- [x] **Performance Optimization**
  - Virtual scroll (useVirtualScroll, VirtualList.vue)
  - Lazy load MapView (defineAsyncComponent)
  - Throttle WebSocket (300ms)
  - Memoization (dashboard store)

- [x] **Backend Integration**
  - Status real dos segmentos (_serialize_route_segment)
  - Status mapping: active→operational, planned→maintenance, etc.
  - mapStore consumindo status do backend

- [x] **Deploy Preparation**
  - Feature flags implementadas (USE_VUE_DASHBOARD, VUE_DASHBOARD_ROLLOUT_PERCENTAGE)
  - Canary routing (hash-based session)
  - Documentação completa (5 documentos, 1500+ linhas)
  - Docker services atualizados

- [x] **Testing**
  - 44 unit tests (100% passing)
  - 10+ E2E scenarios
  - Build production: 96.08 kB (37.74 kB gzip)

- [x] **Infrastructure Setup**
  - Docker compose atualizado com feature flags
  - Static files collected
  - Services restarted (web, celery, beat)
  - Credenciais criadas (admin/admin123)

---

## 🔄 In Progress (12/11/2025 — 18:10)

### Phase 1: Testes Manuais + Monitoring Setup

#### A. Testes no Navegador (AGORA) — ⏱️ 30-60 min
**Objetivo:** Validar Vue dashboard funcionando corretamente

**Checklist Essencial:**
```
URL: http://localhost:8000/maps_view/dashboard
Login: admin / admin123

Testes Críticos:
□ Dashboard carrega sem erros (F12 console)
□ Header mostra "MapsProve Dashboard"
□ WebSocket conecta (status verde)
□ Host cards renderizam (ou empty state se sem dados)
□ Map carrega (mesmo sem API key Google)
□ Controls respondem (fit bounds, toggle legend)
□ Mobile responsive (resize para 375px)
```

**Documentação:** `TESTE_NAVEGADOR.md` (checklist completo)

**Outputs Esperados:**
- ✅ Todos os testes críticos passam → Seguir para Monitoring
- ⚠️ Bugs menores → Fix e re-test
- ❌ Bugs críticos → Investigar e corrigir

---

#### B. Configurar Monitoring (DEPOIS DOS TESTES) — ⏱️ 15 min
**Objetivo:** Setup scripts de monitoring para 24h

1. **Ajustar Canary para 10%**
   ```powershell
   # Editar docker/docker-compose.yml
   VUE_DASHBOARD_ROLLOUT_PERCENTAGE: "10"
   
   # Restart
   docker compose -f docker/docker-compose.yml restart web
   ```

2. **Iniciar Monitoring**
   ```powershell
   # Ver: doc/operations/MONITORING_COMMANDS_PHASE1.md
   # Health check inicial
   docker compose -f docker/docker-compose.yml ps
   
   # Verificar distribuição canary (10% Vue, 90% Legacy)
   # Testar 10 sessões diferentes (incognito)
   ```

3. **Agendar Health Checks**
   - Próximos checks: 22:00, 02:00, 06:00, 10:00, 14:00 (13/11)
   - Usar script em `MONITORING_COMMANDS_PHASE1.md`

---

## 📅 Próximas Etapas (Timeline)

### 🕐 Hoje à Noite (12/11/2025 — 22:00)
**Health Check #1**
```powershell
# Run health check script
# Ver: MONITORING_COMMANDS_PHASE1.md
# Expected: Services UP, Error rate <1%, Response time <3s
```

---

### 🌙 Overnight (13/11/2025 — 02:00, 06:00)
**Health Checks #2 e #3**
- Monitor error logs
- Check resource usage (CPU, RAM)
- Verify WebSocket stability

---

### 🌅 Amanhã Manhã (13/11/2025 — 10:00)
**Health Check #4**
- 16h de monitoring completado
- Review trends (errors, performance, resources)
- Preliminary assessment

---

### 🕐 Amanhã Tarde (13/11/2025 — 14:00)
**Health Check #5**
- 20h de monitoring
- Final data collection before checkpoint

---

### ✅ Checkpoint 24h (13/11/2025 — 17:50)
**Decision Point: Phase 2 ou Rollback**

**Métricas a Avaliar:**
| Métrica | Target | Status |
|---------|--------|--------|
| Error Rate | <1% | _____ |
| Load Time P95 | <3000ms | _____ |
| WebSocket Uptime | >99% | _____ |
| CPU Usage (web) | <50% | _____ |
| Memory (web) | <512MB | _____ |
| Canary Distribution | ~10% Vue | _____ |

**Ações:**
- [ ] Fill `SMOKE_TEST_REPORT_PHASE1.md`
- [ ] Review all health check logs
- [ ] Assess user feedback (if any)
- [ ] **GO Decision:**
  - ✅ All metrics green → Proceed to Phase 2 (25%)
  - ⚠️ Some issues → Investigate, fix, extend monitoring
  - ❌ Critical issues → Rollback to 0%

---

### 📅 Fase 2: Canary 25% (15/11/2025 — Se Phase 1 OK)
**Timeline:** 48h monitoring

**Setup:**
```powershell
# Update rollout
VUE_DASHBOARD_ROLLOUT_PERCENTAGE: "25"
docker compose restart web

# Monitor for 48h (15/11 18:00 → 17/11 18:00)
```

**Health Checks:**
- A cada 6h: 00:00, 06:00, 12:00, 18:00
- Same metrics as Phase 1
- Broader user exposure (25%)

**Checkpoint:** 17/11/2025 18:00
- Decision: Phase 3 (50%) OR Hold OR Rollback

---

### 📅 Fase 3: Canary 50% (18/11/2025 — Se Phase 2 OK)
**Timeline:** 72h monitoring

**Setup:**
```powershell
VUE_DASHBOARD_ROLLOUT_PERCENTAGE: "50"
docker compose restart web
```

**Health Checks:**
- A cada 8h durante 3 dias
- User feedback collection (majority now on Vue)
- Performance under higher load

**Checkpoint:** 21/11/2025 18:00
- Decision: Phase 4 (100%) OR Hold

---

### 📅 Fase 4: Full Rollout 100% (22/11/2025 — Se Phase 3 OK)
**Timeline:** 1 semana monitoring

**Setup:**
```powershell
VUE_DASHBOARD_ROLLOUT_PERCENTAGE: "100"
docker compose restart web
```

**Monitoring:**
- Daily health checks por 7 dias
- Full production load
- Final validation antes de deprecar legacy

**Checkpoint:** 29/11/2025
- Decision: Deprecate Legacy Dashboard

---

### 📅 Legacy Deprecation (Dezembro 2025)
**Timeline:** 1 mês após 100% rollout

**Ações:**
1. Mark `dashboard.js` as deprecated (01/12)
2. Add deprecation warning in code (01/12)
3. Update documentation (01/12)
4. Remove legacy code (29/12)
5. Close Phase 11 (31/12)

---

## 🎯 Milestones

| Milestone | Data Target | Status |
|-----------|-------------|--------|
| Sprint 3 Complete | 12/11/2025 | ✅ |
| Deploy Staging | 12/11/2025 | ✅ |
| Testes Manuais | 12/11/2025 18:00 | 🔄 |
| Phase 1 (10%) Start | 12/11/2025 18:30 | ⏳ |
| Phase 1 Checkpoint | 13/11/2025 17:50 | ⏳ |
| Phase 2 (25%) Start | 15/11/2025 | ⏳ |
| Phase 2 Checkpoint | 17/11/2025 | ⏳ |
| Phase 3 (50%) Start | 18/11/2025 | ⏳ |
| Phase 3 Checkpoint | 21/11/2025 | ⏳ |
| Phase 4 (100%) Start | 22/11/2025 | ⏳ |
| Phase 4 Checkpoint | 29/11/2025 | ⏳ |
| Legacy Deprecation | 29/12/2025 | ⏳ |
| Phase 11 Complete | 31/12/2025 | ⏳ |

---

## 📊 KPIs to Track

### Technical Metrics
- **Error Rate:** <1% (critical)
- **Load Time P95:** <3000ms (critical)
- **WebSocket Uptime:** >99% (critical)
- **CPU Usage:** <50% sustained (important)
- **Memory Usage:** <512MB sustained (important)
- **Build Size:** <100KB main.js (achieved: 96.08KB ✅)

### Business Metrics
- **User Satisfaction:** No critical complaints
- **Rollback Events:** 0 (target)
- **Deployment Time:** <10 min per phase
- **Test Coverage:** >80% (achieved: 44 tests ✅)

---

## 🚨 Rollback Triggers

**Immediate Rollback if:**
- Error rate >5% sustained
- Load time P95 >5s sustained
- WebSocket disconnect rate >10%
- Critical bug (data corruption, security)
- Service crashes

**Rollback Procedure:**
```powershell
# Quick rollback <5 min
VUE_DASHBOARD_ROLLOUT_PERCENTAGE: "0"
docker compose restart web

# Full rollback <15 min
USE_VUE_DASHBOARD: "False"
docker compose restart
docker compose exec redis redis-cli FLUSHALL
```

---

## 📝 Action Items (Immediate)

### Agora (18:10 → 19:00):
1. [ ] **Testar no navegador** (TESTE_NAVEGADOR.md)
   - Abrir http://localhost:8000/maps_view/dashboard
   - Login: admin / admin123
   - Executar checklist essencial
   - Registrar screenshots/issues

2. [ ] **Ajustar para Canary 10%** (se testes OK)
   - Edit docker-compose.yml
   - Restart web service
   - Verify canary distribution

3. [ ] **First Health Check** (22:00)
   - Run monitoring script
   - Log metrics
   - Check for issues

### Próximas 24h:
4. [ ] Health checks: 02:00, 06:00, 10:00, 14:00
5. [ ] Collect performance data
6. [ ] Monitor error logs
7. [ ] Test canary distribution (multiple sessions)

### Checkpoint (13/11 17:50):
8. [ ] Review 24h metrics
9. [ ] Fill smoke test report
10. [ ] GO/NO-GO decision for Phase 2

---

## 🎉 Success Criteria

**Phase 1 Successful if:**
- ✅ All smoke tests pass
- ✅ Error rate <1% for 24h
- ✅ Load time P95 <3s consistently
- ✅ WebSocket uptime >99%
- ✅ No critical bugs reported
- ✅ Resources stable (CPU <50%, RAM <512MB)
- ✅ Canary distribution working (~10% Vue)

**Ready for Phase 2 when:**
- All success criteria met
- Team confident in stability
- Monitoring data shows no red flags

---

**Status:** 🧪 Testes Manuais em Andamento  
**Próxima Ação:** Executar checklist em TESTE_NAVEGADOR.md  
**Próximo Checkpoint:** 13/11/2025 17:50 (24h review)  
**Última atualização:** 12/11/2025 — 18:10
