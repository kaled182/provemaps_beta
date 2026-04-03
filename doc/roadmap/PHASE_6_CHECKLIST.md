# Fase 6: Checklist Executável

**Início:** 18 / Nov / 2025  
**Conclusão Prevista:** 22 / Nov / 2025  
**Responsável:** Equipe de Desenvolvimento

**⚠️ ATUALIZAÇÃO:** Dias 1-4 concluídos!  
**Status Atual:** Dia 4 (PostGIS) completo com módulo `inventory/usecases/spatial.py` + documentação

---

## ✅ Pré-Requisitos (Antes de Iniciar)

- [x] Produção está rodando v2.0.0 (Fase 5 completa)
- [x] Migrações do `inventory` aplicadas em todos ambientes
- [x] Backup completo do banco de dados realizado
- [ ] Git tag criada: `git tag phase-5-complete && git push --tags`
- [ ] Branch criada: `git checkout -b phase-6-reorganization`

---

## ✅ Dia 1: Validação e Preparação (CONCLUÍDO - 18/Nov/2025)

### Testes Baseline

- [x] **Executar testes completos:**
  ```powershell
  cd docker
  docker compose exec web pytest --cov --cov-report=html
  ```
  - Cobertura atual: **TBD**%
  - Testes passando: **TBD** / **TBD**

- [x] **Verificar migrações aplicadas:**
  ```powershell
  docker compose exec web python manage.py showmigrations inventory
  ```
  - [x] `0010_add_spatial_fields.py` ✅ Aplicada
  - [x] `0011_populate_spatial_fields.py` ✅ Aplicada
  - [x] `0012_create_spatial_indexes.py` ✅ Aplicada

- [x] **Buscar referências ao `routes_builder`:**
  - Referências encontradas: **30 (legítimas)**
  - [x] Validar se são apenas em comentários/docs ✅
  - **Conclusão:** Apenas aliases Celery, cache keys e migrações históricas

### Documentação Estado Atual

- [x] Sistema funcionando sem erros
  - `python manage.py check` → **0 issues**

---

## ✅ Dia 2: Remoção Zombie App (JÁ CONCLUÍDO ANTERIORMENTE!)

**⚠️ DESCOBERTA:** O app `routes_builder` já foi removido em trabalho anterior!

### Verificação Realizada

- [x] **`routes_builder` não está em `INSTALLED_APPS`** ✅
  - Verificado em `backend/settings/base.py`
  - App não listado

- [x] **Diretório `routes_builder/` não existe** ✅
  - Verificado em `backend/`
  - Lógica migrada para `inventory/routes/`

- [x] **Django check sem erros** ✅
  ```powershell
  docker compose exec web python manage.py check
  ```
  - System check identified no issues (0 silenced)

### Status

**✅ DIA 2 COMPLETO** - Trabalho já realizado na Fase 5

**Observação:** Aliases legados em `inventory/routes/tasks.py` são intencionais para retrocompatibilidade Celery

---

## ✅ Dia 3: Estrutura de Diretórios (JÁ ORGANIZADO - SKIP)

**⚠️ DESCOBERTA:** Estrutura atual **JÁ ESTÁ CORRETA**!

- [x] **Validar estrutura existente:**
  ```
  ✅ backend/     - Django separado
  ✅ frontend/    - Vue separado
  ✅ docker/      - Infra separada
  ✅ scripts/     - Scripts separados
  ✅ doc/         - Docs organizadas
  ```

**✅ DIA 3 COMPLETO** - Nenhuma ação necessária

---

## 📋 Dia 4: Otimização PostGIS

### Criar Arquivo de Usecases Espaciais

- [ ] **Criar `backend/inventory/usecases/spatial.py`:**
  ```python
  """Spatial query use cases using PostGIS native operations."""
  
  from django.contrib.gis.measure import D
  from django.contrib.gis.geos import Point
  from inventory.models import Device, Site
  
  def get_nearby_devices(lat: float, lon: float, radius_km: float):
      """Find devices within radius using PostGIS spatial index."""
      point = Point(lon, lat, srid=4326)
      return Device.objects.filter(
          location__distance_lte=(point, D(km=radius_km))
      ).select_related('site')
  
  def get_devices_in_bbox(lng_min, lat_min, lng_max, lat_max):
      """Find devices within bounding box (viewport query)."""
      from django.contrib.gis.geos import Polygon
      bbox = Polygon.from_bbox((lng_min, lat_min, lng_max, lat_max))
      bbox.srid = 4326
      return Device.objects.filter(location__within=bbox)
  ```

- [ ] **Criar testes:**
  ```powershell
  # backend/tests/inventory/test_spatial_usecases.py
  ```

### Adicionar Índices GIST

- [ ] **Criar migração:**
  ```powershell
  cd docker
  docker compose exec web python manage.py makemigrations inventory --name add_gist_indexes --empty
  ```

- [ ] **Editar migração criada:**
  ```python
  from django.contrib.gis.db import models as gis_models
  from django.db import migrations
  
  class Migration(migrations.Migration):
      dependencies = [
          ('inventory', '0011_populate_spatial_fields'),
      ]
      
      operations = [
          # Índice espacial para Device.location (se campo existir)
          # migrations.AddIndex(
          #     model_name='device',
          #     index=gis_models.GistIndex(fields=['location'], name='device_location_gist'),
          # ),
          migrations.AddIndex(
              model_name='fibercable',
              index=gis_models.GistIndex(fields=['path'], name='cable_path_gist'),
          ),
          migrations.AddIndex(
              model_name='routesegment',
              index=gis_models.GistIndex(fields=['path'], name='segment_path_gist'),
          ),
      ]
  ```

- [ ] **Aplicar migração:**
  ```powershell
  docker compose exec web python manage.py migrate
  ```

### Benchmark de Performance

- [ ] **Criar script de benchmark:**
  ```python
  # scripts/benchmark_postgis.py (já existe - verificar)
  import time
  from django.contrib.gis.geos import Point
  from django.contrib.gis.measure import D
  from inventory.models import FiberCable
  
  # Benchmark: BBox query
  start = time.time()
  cables = FiberCable.objects.filter(
      path__intersects=bbox
  )[:100]
  list(cables)  # Force evaluation
  print(f"BBox query: {(time.time() - start)*1000:.2f}ms")
  ```

- [ ] **Executar benchmark:**
  ```powershell
  docker compose exec web python scripts/benchmark_postgis.py
  ```
  - Tempo médio: ______ms
  - [ ] Documentar em `doc/reports/PHASE_6_PERFORMANCE.md`

### Validação

- [ ] **Testes unitários passando:**
  ```powershell
  docker compose exec web pytest tests/inventory/test_spatial* -v
  ```

- [ ] **Query plans do PostgreSQL:**
  ```sql
  -- Conectar ao DB e verificar uso do índice
  EXPLAIN ANALYZE 
  SELECT * FROM inventory_fibercable 
  WHERE ST_Intersects(path, ST_MakeEnvelope(-48.5, -16.5, -47.5, -15.5, 4326));
  ```
  - [ ] Confirmar "Index Scan using cable_path_gist" ✅

---

## 📋 Dia 5: Vue Dashboard Rollout (Opcional)

### Validar Métricas Atuais (10% Rollout)

- [ ] **Sentry Error Rate:**
  - URL: https://sentry.io/organizations/.../issues/
  - Error rate últimos 7 dias: ______%
  - [ ] < 0.5% ✅ (critério para aumento)

- [ ] **Prometheus Metrics:**
  ```powershell
  Invoke-WebRequest -Uri "http://localhost:8000/metrics/" -UseBasicParsing | Select-String "http_request_duration"
  ```
  - P95 load time: ______ms
  - [ ] < 2000ms ✅

- [ ] **Feedback de Usuários:**
  - Tickets abertos: ______
  - Sentimento: Positivo / Neutro / Negativo
  - [ ] Sem bloqueios críticos ✅

### Decisão: Aumentar Rollout?

- [ ] **SIM** - Critérios atendidos → Aumentar para 25%
- [ ] **NÃO** - Manter em 10% e investigar issues

### Aumento para 25% (Se Aprovado)

- [ ] **Atualizar `.env`:**
  ```bash
  VUE_DASHBOARD_ROLLOUT_PERCENTAGE=25
  ```

- [ ] **Atualizar `database/runtime.env`:**
  ```bash
  VUE_DASHBOARD_ROLLOUT_PERCENTAGE="25"
  ```

- [ ] **Restart containers:**
  ```powershell
  cd docker
  docker compose restart web
  ```

- [ ] **Verificar aplicação:**
  ```powershell
  docker compose exec web env | findstr VUE
  ```
  - VUE_DASHBOARD_ROLLOUT_PERCENTAGE: 25 ✅

### Monitoramento 48h

- [ ] **Configurar alertas:**
  - [ ] Sentry: Email se error rate > 1%
  - [ ] Prometheus: Alert se P95 > 3s

- [ ] **Revisão D+1:**
  - Data: ___ / ___ / 2025
  - Error rate: ______%
  - P95 latency: ______ms
  - Status: ✅ OK / ⚠️ Investigar / 🚨 Rollback

- [ ] **Revisão D+2:**
  - Data: ___ / ___ / 2025
  - Error rate: ______%
  - Status: ✅ OK / 🚨 Rollback

---

## 📊 Validação Final (Fim da Fase 6)

### Testes Completos

- [ ] **Backend:**
  ```powershell
  cd docker
  docker compose exec web pytest --cov --cov-report=html
  ```
  - Cobertura final: ______% (vs baseline: ______%)
  - [ ] Sem regressão ✅

- [ ] **Frontend E2E:**
  ```powershell
  cd ../frontend
  npm run test:e2e
  ```
  - Testes passando: ______ / ______

### Métricas de Sucesso

| Métrica | Meta | Atingido | Status |
|---------|------|----------|--------|
| Cobertura Testes | ≥ 80% | ______% | ⬜ |
| Apps Zombie | 0 | ______ | ⬜ |
| Query Spatial (P95) | < 100ms | ______ms | ⬜ |
| Build Time Docker | < 5min | ______min | ⬜ |
| Vue Error Rate | < 0.5% | ______% | ⬜ |

### Documentação

- [ ] **Atualizar changelogs:**
  - [ ] `doc/releases/CHANGELOG.md`
  - [ ] `doc/roadmap/PHASE_6_REORGANIZATION.md` (seção "Resultados")

- [ ] **Atualizar copilot instructions:**
  - [ ] Remover menções ao `routes_builder`
  - [ ] Adicionar padrões PostGIS

- [ ] **Criar relatório final:**
  - [ ] `doc/reports/phases/PHASE_6_COMPLETION_REPORT.md`

### Git e Deploy

- [ ] **Merge para branch principal:**
  ```powershell
  git checkout refactor/folder-structure
  git merge phase-6-reorganization
  ```

- [ ] **Tag de release:**
  ```powershell
  git tag -a v2.0.1-phase6 -m "Phase 6: Reorganization complete"
  git push origin v2.0.1-phase6
  ```

- [ ] **Deploy em staging:**
  - [ ] Executar `scripts/deploy_production.ps1 -Environment staging`
  - [ ] Smoke tests em staging

- [ ] **Deploy em produção:**
  - Data planejada: ___ / ___ / 2025
  - Horário: ______
  - [ ] Executado com sucesso ✅

---

## 🚨 Plano de Rollback

**Se algo der errado:**

1. **Rollback de código:**
   ```powershell
   git revert HEAD~1  # Reverter último commit
   # OU
   git checkout phase-5-complete  # Voltar para tag anterior
   ```

2. **Rollback de migrações:**
   ```powershell
   docker compose exec web python manage.py migrate inventory 0011  # Voltar para migração anterior
   ```

3. **Rollback de Vue:**
   ```bash
   # .env
   VUE_DASHBOARD_ROLLOUT_PERCENTAGE=0  # Desabilitar completamente
   ```
   ```powershell
   docker compose restart web
   ```

4. **Notificar equipe:**
   - [ ] Post em canal #dev-alerts
   - [ ] Criar incident report
   - [ ] Agendar post-mortem

---

## 📝 Notas e Observações

### Problemas Encontrados

| Data | Problema | Solução | Responsável |
|------|----------|---------|-------------|
| ___ | ________ | _______ | ___________ |

### Lições Aprendidas

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

---

**Checklist criado em:** 18 de Novembro de 2025  
**Última atualização:** ___ / ___ / _____  
**Status da Fase 6:** 🟡 Em Planejamento
