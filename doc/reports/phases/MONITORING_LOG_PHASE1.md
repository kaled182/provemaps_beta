# ✅ Canary 10% Ativado — Monitoring Log

**Data de Início:** 12/11/2025 — 18:15  
**Configuração:** 10% rollout (hash-based session)  
**Duração Planejada:** 24 horas  
**Checkpoint:** 13/11/2025 — 17:50

---

## 🎯 Configuração Atual

### Feature Flags
```env
USE_VUE_DASHBOARD="True"
VUE_DASHBOARD_ROLLOUT_PERCENTAGE="10"
```

### Distribuição Esperada
- **Vue Dashboard:** ~10% dos usuários (sessão hash <10)
- **Legacy Dashboard:** ~90% dos usuários (sessão hash ≥10)

### Comportamento
- Determinístico: Mesma sessão sempre vê mesma versão
- Sem flip-flop entre requests
- Baseado em MD5 hash do session ID

---

## 📊 Health Check #0 — Baseline (18:15)

### Services Status
```
✅ web:      UP (healthy)
✅ celery:   UP (healthy)
✅ beat:     UP (healthy)
✅ redis:    UP (healthy)
✅ postgres: UP (healthy)
```

### Initial Metrics
- **Dashboard Endpoint:** 200 OK ✅
- **Vue SPA Assets:** 96,078 bytes ✅
- **Settings Loaded:** USE_VUE_DASHBOARD=True, ROLLOUT=10 ✅
- **Services:** All healthy ✅

### Canary Distribution Test
**Objetivo:** Verificar se ~10% das sessões recebem Vue

**Método de Teste:**
```powershell
# Testar 20 sessões diferentes (modo incognito)
# Contar quantas recebem Vue vs Legacy
# Esperado: ~2 Vue, ~18 Legacy (10% ±5%)
```

**Resultado:** ⏳ A testar manualmente

---

## 📝 Monitoring Schedule (Next 24h)

| Check # | Horário | Status | Notes |
|---------|---------|--------|-------|
| #0 | 12/11 18:15 | ✅ | Baseline - Canary ativado |
| #1 | 12/11 22:00 | ⏳ | First 4h check |
| #2 | 13/11 02:00 | ⏳ | Overnight check |
| #3 | 13/11 06:00 | ⏳ | Morning check |
| #4 | 13/11 10:00 | ⏳ | Mid-day check |
| #5 | 13/11 14:00 | ⏳ | Afternoon check |
| **CHECKPOINT** | **13/11 17:50** | ⏳ | **24h Decision Point** |

---

## 🔍 Health Check Template

### Commands to Run Each Check
```powershell
# 1. Services Status
docker compose -f docker/docker-compose.yml ps

# 2. Error Count (last 4h)
docker compose -f docker/docker-compose.yml logs --since 4h web | Select-String "error|exception" | Measure-Object

# 3. WebSocket Activity
docker compose -f docker/docker-compose.yml logs --since 4h web | Select-String "websocket.*connected|failed" | Select-Object -Last 5

# 4. Resource Usage
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 5. Response Time
Measure-Command { Invoke-WebRequest -Uri http://localhost:8000/maps_view/dashboard -UseBasicParsing }
```

### Metrics to Log
- **Error Count:** _____ (target <10 per 4h)
- **Response Time:** _____ ms (target <3000ms)
- **CPU (web):** _____ % (target <50%)
- **Memory (web):** _____ MB (target <512MB)
- **WebSocket Status:** Connected/Failed ratio

---

## 📊 Health Check #1 — 22:00 (12/11/2025)

### Services Status
```
□ web:      
□ celery:   
□ beat:     
□ redis:    
□ postgres: 
```

### Metrics (Last 4h: 18:15-22:00)
- **Error Count:** _____ errors
- **WebSocket Connections:** _____ success, _____ failed
- **Response Time:** _____ ms
- **CPU (web):** _____ %
- **Memory (web):** _____ MB

### Issues Found
- 

### Actions Taken
- 

---

## 📊 Health Check #2 — 02:00 (13/11/2025)

### Services Status
```
□ web:      
□ celery:   
□ beat:     
□ redis:    
□ postgres: 
```

### Metrics (Last 4h: 22:00-02:00)
- **Error Count:** _____ errors
- **WebSocket Connections:** _____ success, _____ failed
- **Response Time:** _____ ms
- **CPU (web):** _____ %
- **Memory (web):** _____ MB

### Issues Found
- 

### Actions Taken
- 

---

## 📊 Health Check #3 — 06:00 (13/11/2025)

### Services Status
```
□ web:      
□ celery:   
□ beat:     
□ redis:    
□ postgres: 
```

### Metrics (Last 4h: 02:00-06:00)
- **Error Count:** _____ errors
- **WebSocket Connections:** _____ success, _____ failed
- **Response Time:** _____ ms
- **CPU (web):** _____ %
- **Memory (web):** _____ MB

### Issues Found
- 

### Actions Taken
- 

---

## 📊 Health Check #4 — 10:00 (13/11/2025)

### Services Status
```
□ web:      
□ celery:   
□ beat:     
□ redis:    
□ postgres: 
```

### Metrics (Last 4h: 06:00-10:00)
- **Error Count:** _____ errors
- **WebSocket Connections:** _____ success, _____ failed
- **Response Time:** _____ ms
- **CPU (web):** _____ %
- **Memory (web):** _____ MB

### Issues Found
- 

### Actions Taken
- 

---

## 📊 Health Check #5 — 14:00 (13/11/2025)

### Services Status
```
□ web:      
□ celery:   
□ beat:     
□ redis:    
□ postgres: 
```

### Metrics (Last 4h: 10:00-14:00)
- **Error Count:** _____ errors
- **WebSocket Connections:** _____ success, _____ failed
- **Response Time:** _____ ms
- **CPU (web):** _____ %
- **Memory (web):** _____ MB

### Issues Found
- 

### Actions Taken
- 

---

## ✅ Checkpoint 24h — 17:50 (13/11/2025)

### Aggregate Metrics (24h)
- **Total Errors:** _____ (target <240 = 1% de ~24,000 requests/day)
- **Avg Response Time:** _____ ms (target <3000ms)
- **Max CPU:** _____ % (target <50%)
- **Max Memory:** _____ MB (target <512MB)
- **WebSocket Uptime:** _____ % (target >99%)

### Canary Distribution Validation
**Tested Sessions:** _____ total
- Vue Dashboard: _____ (~10% expected)
- Legacy Dashboard: _____ (~90% expected)
- Distribution Accurate: [ ] Yes [ ] No

### Issues Summary
**Critical Issues:** _____ (0 expected)
**Major Issues:** _____ (0 expected)
**Minor Issues:** _____ (acceptable if <3)

### User Feedback
- 

---

## 🎯 GO/NO-GO Decision

### Success Criteria
- [ ] Error rate <1% ✅
- [ ] Load time P95 <3000ms ✅
- [ ] WebSocket uptime >99% ✅
- [ ] CPU usage <50% sustained ✅
- [ ] Memory usage <512MB sustained ✅
- [ ] Canary distribution ~10% ✅
- [ ] Zero critical bugs ✅

### Decision
- [ ] ✅ **GO to Phase 2 (25%)** — All criteria met
- [ ] ⏸️ **HOLD** — Needs investigation/fixes (specify):
- [ ] ❌ **ROLLBACK to 0%** — Critical issues (specify):

### Reasoning
_____

### Next Steps
_____

---

## 📝 Notes & Observations

### What Went Well
- 

### Issues Encountered
- 

### Improvements Needed
- 

### Lessons Learned
- 

---

## 🚀 Phase 2 Planning (If GO)

### Timeline
- **Start:** 15/11/2025 18:00
- **Rollout:** 25%
- **Duration:** 48 hours
- **Checkpoint:** 17/11/2025 18:00

### Preparation
- [ ] Update docker-compose.yml: `VUE_DASHBOARD_ROLLOUT_PERCENTAGE="25"`
- [ ] Restart web service
- [ ] Verify settings loaded
- [ ] Start monitoring (6h intervals)

---

**Monitoring Started:** 12/11/2025 — 18:15  
**Next Check:** 12/11/2025 — 22:00  
**Status:** 🟢 Active Monitoring  
**Última atualização:** 12/11/2025 — 18:15
