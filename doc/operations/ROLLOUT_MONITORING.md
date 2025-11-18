# 📊 Guia de Monitoramento - Rollout Vue Dashboard

**Data**: 18 de Novembro de 2025  
**Versão**: 1.0  
**Ambiente**: Docker Compose (Produção)

---

## 🎯 Objetivo

Monitorar o rollout gradual do dashboard Vue 3 em produção, garantindo:
- ✅ Zero erros críticos
- ✅ Performance dentro do esperado (<500ms)
- ✅ Usuários não reportam problemas
- ✅ Rollback rápido se necessário

---

## 🚀 Scripts de Rollout

### PowerShell (Windows)
```powershell
# Rollout 10%
.\scripts\rollout_vue.ps1 -Percentage 10

# Rollout 25%
.\scripts\rollout_vue.ps1 -Percentage 25

# Rollout 50%
.\scripts\rollout_vue.ps1 -Percentage 50

# Rollout 100%
.\scripts\rollout_vue.ps1 -Percentage 100

# Rollback (0%)
.\scripts\rollout_vue.ps1 -Percentage 0

# Com monitoramento estendido (60s)
.\scripts\rollout_vue.ps1 -Percentage 25 -MonitorTime 60
```

### Bash (Linux/macOS)
```bash
# Rollout 10%
./scripts/rollout_vue.sh 10

# Rollout 100%
./scripts/rollout_vue.sh 100

# Com monitoramento estendido (60s)
./scripts/rollout_vue.sh 25 60

# Rollback (0%)
./scripts/rollout_vue.sh 0
```

---

## 📋 Checklist de Rollout (por fase)

### Fase 1: Rollout 10% (4 horas de monitoramento)

**Pré-requisitos:**
- [ ] Todos os testes E2E passando (29/29)
- [ ] Docker containers saudáveis (4/4)
- [ ] Backup recente do banco de dados
- [ ] Time disponível para monitorar

**Execução:**
```powershell
.\scripts\rollout_vue.ps1 -Percentage 10
```

**Monitoramento (4 horas):**

1. **Logs em tempo real** (terminal 1):
   ```bash
   cd docker
   docker compose logs -f web
   ```

2. **Erros críticos** (terminal 2, verificar a cada 30 min):
   ```bash
   # PowerShell
   docker compose logs web --since 30m | Select-String -Pattern "ERROR|CRITICAL|Exception"
   
   # Bash
   docker compose logs web --since 30m | grep -E "ERROR|CRITICAL|Exception"
   ```

3. **Health checks** (verificar a cada 15 min):
   ```bash
   # PowerShell
   Invoke-WebRequest http://localhost:8000/ready
   Invoke-WebRequest http://localhost:8000/healthz
   
   # Bash
   curl http://localhost:8000/ready
   curl http://localhost:8000/healthz
   ```

4. **Performance dashboard** (testar 5-10 vezes):
   - Abrir: http://localhost:8000/monitoring/backbone/
   - Recarregar várias vezes
   - Alguns acessos mostrarão Vue (~10%), outros legacy
   - Verificar tempo de carregamento no DevTools (Network tab)
   - **Esperado**: <500ms para dashboard load

5. **Console JavaScript** (navegador):
   - Abrir DevTools (F12)
   - Tab "Console"
   - Verificar erros (vermelho) → **Esperado: 0 erros**
   - Verificar warnings (amarelo) → Máximo 2-3 warnings aceitáveis

**Critérios de sucesso (4h):**
- ✅ 0 erros `ERROR`/`CRITICAL` nos logs Django
- ✅ 0 erros no console JavaScript (amostra de 10+ acessos)
- ✅ Performance <500ms (média)
- ✅ Health checks retornam HTTP 200
- ✅ 0 reclamações de usuários

**Se critérios OK**: ✅ Avançar para **Fase 2 (25%)**  
**Se critérios FAIL**: ⚠️ **ROLLBACK** para 0%

---

### Fase 2: Rollout 25% (4 horas de monitoramento)

**Execução:**
```powershell
.\scripts\rollout_vue.ps1 -Percentage 25
```

**Monitoramento:** Mesmo processo da Fase 1

**Critérios de sucesso (4h):**
- ✅ Mesmos critérios da Fase 1

**Se critérios OK**: ✅ Avançar para **Fase 3 (50%)**  
**Se critérios FAIL**: ⚠️ **ROLLBACK** para 10% (ou 0%)

---

### Fase 3: Rollout 50% (6 horas de monitoramento)

**Execução:**
```powershell
.\scripts\rollout_vue.ps1 -Percentage 50
```

**Monitoramento:** Mesmo processo, com verificações a cada 45 min

**Critérios de sucesso (6h):**
- ✅ Mesmos critérios anteriores

**Se critérios OK**: ✅ Avançar para **Fase 4 (100%)**  
**Se critérios FAIL**: ⚠️ **ROLLBACK** para 25%

---

### Fase 4: Rollout 100% (24 horas de monitoramento)

**Execução:**
```powershell
.\scripts\rollout_vue.ps1 -Percentage 100
```

**Monitoramento estendido (24h):**
- Verificar logs a cada 2 horas
- Health checks a cada hora
- Performance spot checks (5x ao dia)

**Critérios de sucesso (24h):**
- ✅ Mesmos critérios anteriores
- ✅ Nenhuma regressão funcional reportada
- ✅ Métricas de uso normais

**Se critérios OK**: 🎉 **SUCESSO! Rollout completo**  
**Se critérios FAIL**: ⚠️ **ROLLBACK** para 50% e investigar

---

## 🔍 Comandos de Monitoramento Detalhado

### 1. Logs Django (Erros)

```bash
# PowerShell - Últimos 100 erros
docker compose logs web --tail=1000 | Select-String -Pattern "ERROR|CRITICAL" | Select-Object -First 100

# Bash - Últimos 100 erros
docker compose logs web --tail=1000 | grep -E "ERROR|CRITICAL" | head -n 100

# Filtrar por período (últimas 2 horas)
docker compose logs web --since 2h | grep ERROR
```

### 2. Health Checks Automatizados

```powershell
# PowerShell - Loop de health checks (verificar a cada 60s por 10 min)
1..10 | ForEach-Object {
    $status = (Invoke-WebRequest http://localhost:8000/ready -UseBasicParsing).StatusCode
    Write-Host "[$_/10] Health: $status - $(Get-Date)"
    Start-Sleep -Seconds 60
}
```

```bash
# Bash - Loop de health checks
for i in {1..10}; do
    status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ready)
    echo "[$i/10] Health: $status - $(date)"
    sleep 60
done
```

### 3. Performance Monitoring

```bash
# Tempo de resposta do dashboard API
time curl -s http://localhost:8000/maps_view/api/dashboard/data/ > /dev/null

# Múltiplas requisições para média
for i in {1..10}; do
    time curl -s http://localhost:8000/maps_view/api/dashboard/data/ > /dev/null
done
```

### 4. Verificar Percentual Ativo

```bash
# PowerShell
docker compose exec web env | Select-String VUE_DASHBOARD

# Bash
docker compose exec web env | grep VUE_DASHBOARD
```

**Output esperado:**
```
USE_VUE_DASHBOARD=true
VUE_DASHBOARD_ROLLOUT_PERCENTAGE=25  # (ou outro valor)
```

### 5. Logs em Tempo Real com Filtros

```bash
# Apenas logs do dashboard
docker compose logs -f web | grep -i dashboard

# Apenas erros e warnings
docker compose logs -f web | grep -E "ERROR|WARNING|CRITICAL"

# Apenas requisições HTTP
docker compose logs -f web | grep -E "GET|POST|PUT|DELETE"
```

### 6. Verificar Containers

```bash
# Status de todos os containers
docker compose ps

# Uso de recursos
docker stats --no-stream
```

**Output esperado:**
```
NAME                   STATUS        PORTS
docker-web-1          Up (healthy)  0.0.0.0:8000->8000/tcp
docker-postgres-1     Up (healthy)  0.0.0.0:5433->5432/tcp
docker-redis-1        Up (healthy)  0.0.0.0:6379->6379/tcp
docker-celery_worker-1 Up           -
```

---

## ⚠️ Procedimento de Rollback

### Rollback Rápido (Emergência)

```powershell
# PowerShell - Rollback para 0% (legacy 100%)
.\scripts\rollout_vue.ps1 -Percentage 0

# OU manualmente:
cd docker
docker compose restart web
```

### Rollback Gradual (Problema menor)

```powershell
# De 100% → 50%
.\scripts\rollout_vue.ps1 -Percentage 50

# De 50% → 25%
.\scripts\rollout_vue.ps1 -Percentage 25

# De 25% → 10%
.\scripts\rollout_vue.ps1 -Percentage 10
```

### Validar Rollback

```bash
# Verificar que rollback foi aplicado
docker compose exec web env | grep VUE_DASHBOARD

# Testar dashboard (deve mostrar legacy)
curl -I http://localhost:8000/monitoring/backbone/

# Monitorar logs por 5 minutos
docker compose logs -f web --tail=50
```

---

## 📊 Métricas de Sucesso

### KPIs por Fase

| Fase | Percentual | Duração Monitoramento | Erros Tolerados | Performance (p95) |
|------|------------|----------------------|-----------------|-------------------|
| 1    | 10%        | 4 horas              | 0               | <500ms            |
| 2    | 25%        | 4 horas              | 0               | <500ms            |
| 3    | 50%        | 6 horas              | 0               | <500ms            |
| 4    | 100%       | 24 horas             | 0               | <500ms            |

### Sinais de Alerta (RED FLAGS)

🚨 **ROLLBACK IMEDIATO** se:
- ❌ Erro `500 Internal Server Error` no dashboard
- ❌ Exceção `TypeError`, `AttributeError` nos logs
- ❌ Health check retorna `503` ou timeout
- ❌ Container web reiniciando continuamente (`docker compose ps`)
- ❌ Mais de 3 reclamações de usuários em 1 hora

⚠️ **INVESTIGAR** se:
- ⚠️ Warnings no console JavaScript (>5 por página)
- ⚠️ Performance >800ms (p95)
- ⚠️ Logs com `DeprecationWarning` relacionados a Vue/Django
- ⚠️ 1-2 reclamações de usuários

---

## 🎯 Checklist Pós-Rollout 100%

Após 24-48h com rollout 100% estável:

- [ ] Validar métricas finais (0 erros, performance OK)
- [ ] Documentar lições aprendidas
- [ ] Planejar remoção do código legacy:
  - [ ] Deletar `backend/static/dashboard.js` (~1.200 linhas)
  - [ ] Deletar `backend/static/traffic_chart.js` (~800 linhas)
  - [ ] Deletar `backend/maps_view/templates/dashboard.html`
  - [ ] Atualizar `views.py` (remover lógica de fallback)
  - [ ] Remover feature flags `USE_VUE_DASHBOARD`, `VUE_DASHBOARD_ROLLOUT_PERCENTAGE`
- [ ] Commit: `feat: Remove legacy dashboard (-2,000 lines)`
- [ ] Celebrar sucesso! 🎉

---

## 📞 Suporte

**Em caso de problemas:**

1. **Consultar logs**: `docker compose logs web`
2. **Verificar issues conhecidos**: `doc/reports/SPRINT_DAY1_*.md`
3. **Rollback se necessário**: `.\scripts\rollout_vue.ps1 -Percentage 0`
4. **Documentar problema**: Criar issue no GitHub

---

**Última atualização**: 18 de Novembro de 2025
