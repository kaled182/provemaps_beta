# Fix: Celery/Beat Restart Loop - psutil Missing

**Data:** 18 de Novembro de 2025  
**Problema:** Containers `docker-celery-1` e `docker-beat-1` em loop de restart  
**Causa Raiz:** Cache de imagens Docker antigas sem psutil instalado  
**Status:** ✅ RESOLVIDO

---

## 🔴 Sintomas

```
docker-beat-1       Restarting (1) 21 seconds ago
docker-celery-1     Restarting (1) 20 seconds ago
```

**Logs mostravam:**
```python
File "/app/backend/core/views_metrics.py", line 3, in <module>
    import psutil
ModuleNotFoundError: No module named 'psutil'
```

---

## 🔍 Diagnóstico

1. **Verificação do requirements.txt:**
   - ✅ `psutil==6.1.1` estava presente na linha 47

2. **Problema identificado:**
   - Após rebuild de `docker-web`, os containers `celery` e `beat` continuavam usando **imagens antigas em cache**
   - Docker Compose não reconstruiu automaticamente todas as imagens que compartilham o mesmo Dockerfile

3. **Arquitetura do docker-compose.yml:**
   ```yaml
   web:
     build:
       context: ..
       dockerfile: docker/dockerfile
   
   celery:
     build:
       context: ..
       dockerfile: docker/dockerfile  # Mesma imagem base
   
   beat:
     build:
       context: ..
       dockerfile: docker/dockerfile  # Mesma imagem base
   ```

---

## ✅ Solução Aplicada

### Passo 1: Remover TODAS as imagens locais
```powershell
cd d:\provemaps_beta\docker
docker compose down --rmi all
```

**Resultado:**
```
✔ Image docker-beat:latest      Removed
✔ Image docker-web:latest       Removed
✔ Image docker-celery:latest    Removed
✔ Image redis:7-alpine          Removed
✔ Image postgis/postgis:16-3.4  Removed
```

### Passo 2: Rebuild completo SEM cache
```powershell
docker compose build --no-cache
```

**Tempo:** ~96 segundos  
**Resultado:** 3 imagens reconstruídas do zero (web, celery, beat)

### Passo 3: Subir containers com configuração
```powershell
$env:VUE_DASHBOARD_ROLLOUT_PERCENTAGE="100"
$env:USE_VUE_DASHBOARD="true"
docker compose up -d
```

### Passo 4: Validação
```powershell
# Verificar status
docker compose ps

# Confirmar psutil instalado
docker compose exec web python -c "import psutil; print('✓ psutil version:', psutil.__version__)"

# Health check
Invoke-WebRequest http://localhost:8000/ready

# Ver logs ativos
docker logs docker-celery-1 --tail=30
docker logs docker-beat-1 --tail=30
```

---

## 📊 Status Final - TODOS SAUDÁVEIS

```
NAME                STATUS
docker-beat-1       Up 2 minutes (healthy) ✅
docker-celery-1     Up 2 minutes (healthy) ✅
docker-postgres-1   Up 2 minutes (healthy) ✅
docker-redis-1      Up 2 minutes (healthy) ✅
docker-web-1        Up 2 minutes (healthy) ✅
```

**Validações:**
- ✅ `psutil version: 6.1.1` - Instalado corretamente
- ✅ Health Check: `HTTP 200 OK`
- ✅ Vue Dashboard: `VUE_DASHBOARD_ROLLOUT_PERCENTAGE=100`

---

## 🎯 Tarefas Celery Funcionando

**Celery Worker (docker-celery-1):**
```
✓ update_celery_metrics_task - succeeded
✓ refresh_dashboard_cache_task - 11 hosts, 14.28s
✓ refresh_cables_oper_status - 2 cables processed
✓ refresh_fiber_live_status - 2 cables processed
✓ refresh_fiber_list_cache - 2 cables cached
✓ enforce_rotation_policies_task - 0 rotations
✓ update_all_port_optical_levels - processing
```

**Celery Beat (docker-beat-1):**
```
✓ Scheduler: Sending due tasks every interval
✓ update-celery-metrics (30s interval)
✓ refresh-dashboard-cache
✓ refresh-fiber-list-cache
✓ refresh-cables-oper-status
✓ refresh-fiber-live-status
```

---

## 💡 Lições Aprendidas

### 1. Cache de Imagens Docker
- **Problema:** `docker compose build web` NÃO reconstrói automaticamente `celery` e `beat`
- **Motivo:** Cada serviço tem sua própria tag de imagem (`docker-web:latest`, `docker-celery:latest`)
- **Solução:** Sempre usar `docker compose build --no-cache` quando há mudanças em dependências

### 2. Quando Usar `--rmi all`
Use quando:
- Dependências Python mudaram (requirements.txt)
- Problemas de cache entre serviços que compartilham Dockerfile
- Migração de versões de sistema (ex: Python 3.11 → 3.12)

### 3. Verificação de Dependências
Sempre validar após rebuild:
```powershell
docker compose exec web python -c "import psutil"
docker compose exec celery python -c "import psutil"
docker compose exec beat python -c "import psutil"
```

---

## 🚨 Comandos de Emergência

### Se Celery/Beat continuarem em loop:

```powershell
# 1. Parar tudo e remover imagens
cd d:\provemaps_beta\docker
docker compose down --rmi all

# 2. Rebuild completo
docker compose build --no-cache

# 3. Subir com variáveis de ambiente
$env:VUE_DASHBOARD_ROLLOUT_PERCENTAGE="100"
$env:USE_VUE_DASHBOARD="true"
docker compose up -d

# 4. Monitorar logs em tempo real
docker compose logs -f celery
docker compose logs -f beat
```

### Validação Rápida:
```powershell
docker compose ps
docker compose exec web python -c "import psutil; print(psutil.__version__)"
Invoke-WebRequest http://localhost:8000/ready
```

---

## 📚 Referências

- **Dockerfile:** `docker/dockerfile` (multi-stage build)
- **Docker Compose:** `docker/docker-compose.yml`
- **Requirements:** `backend/requirements.txt` (linha 47: psutil==6.1.1)
- **Copilot Instructions:** `.github/copilot-instructions.md` (seção "Docker Compose")

---

## ✅ Conclusão

Problema resolvido completamente através de rebuild completo das imagens Docker. Sistema agora 100% operacional com:

- **0 erros** em Celery/Beat
- **5/5 containers** healthy
- **Vue Dashboard** em produção (100% rollout)
- **Tarefas assíncronas** executando normalmente

**Próximos passos:** Monitorar 24-48h para garantir estabilidade.
