# Fase 6: Reorganização Estrutural e Resolução de Débitos Técnicos

**Data:** 18 de Novembro de 2025  
**Projeto:** MapsProveFiber v2.0.0  
**Status:** Planejamento — Pós-Refatoração Modular (Fase 5 Concluída)  
**Responsável:** Equipe de Desenvolvimento

---

## 📋 Sumário Executivo

Este documento detalha o plano de ação da Fase 6, focado na reestruturação física do projeto e resolução de débitos técnicos identificados após a conclusão bem-sucedida da Fase 5 (Refatoração Modular).

**Objetivo Principal:** Separar responsabilidades físicas entre Backend, Frontend e Infraestrutura, eliminando código legado e otimizando o uso de recursos espaciais (PostGIS).

**Duração Estimada:** 5 dias úteis  
**Impacto:** Melhoria significativa em manutenibilidade, onboarding de desenvolvedores e performance de queries espaciais

---

## ⚠️ Débitos Técnicos Identificados

### PN-01: Padrão "Zombie App" (`routes_builder`) ⚰️

**Situação Atual:**
- App `routes_builder` permanece em `INSTALLED_APPS` apenas para preservar histórico de migrações
- Lógica migrada para `inventory.routes` e `inventory.models_routes` (Fase 5 - Nov 2025)
- Código morto polui o projeto e complica grafo de dependências

**Impacto:**
- Confusão para novos desenvolvedores
- Risco de uso acidental de código deprecated
- Overhead desnecessário em descoberta de apps Django

**Status:** 🔴 **CRÍTICO** — Resolução prioritária

---

### PN-02: Estrutura de Diretórios Mista 📁

**Situação Atual:**
- Backend (Django), Frontend (Vue), Docker e scripts misturados na raiz
- Dificulta separação de responsabilidades
- Complica pipelines CI/CD independentes

**Estrutura Atual (Problemática):**
```
/
├── backend/               # Django apps
├── frontend/              # Vue 3 SPA
├── docker/                # Infraestrutura
├── scripts/               # Utilitários
├── staticfiles/           # Assets compilados (conflito)
├── manage.py              # Raiz confusa
├── package.json           # Raiz confusa
└── ...
```

**Impacto:**
- Onboarding lento de desenvolvedores
- Build contexts de Docker complicados
- Dificuldade em estabelecer ownership de código

**Status:** 🟡 **MODERADO** — Impacta experiência do desenvolvedor

---

### PN-03: Uso Tímido do PostGIS 🗺️

**Situação Atual:**
- PostGIS 3.4 configurado desde Fase 10, mas subutilizado
- Lógica de proximidade/distância ainda ocorre em Python
- Queries espaciais não aproveitam índices GIST do PostgreSQL

**Exemplo de Problema:**
```python
# ❌ ANTES: Lento, não usa índice espacial
def get_nearby_devices(lat, lon, radius):
    devices = Device.objects.all()
    return [d for d in devices if haversine(lat, lon, d.lat, d.lon) <= radius]
```

**Impacto:**
- Performance degradada em datasets grandes (>10k devices)
- CPU desperdiçada em cálculos que o DB faz melhor
- Escalabilidade limitada

**Status:** 🟡 **MODERADO** — Performance crítica em produção

---

### PN-04: Interface Híbrida (Django Templates + Vue) 🔀

**Situação Atual:**
- Templates Django legados (`maps_view/templates/dashboard.html`)
- Vue 3 SPA moderno (`frontend/src/`)
- Canary rollout em 10% (configurado em `.env`)
- Duas pilhas de frontend para manter

**Impacto:**
- Duplicação de testes (E2E para ambas as versões)
- Overhead de manutenção em dois sistemas
- Complexidade no roteamento (Django vs Vue Router)

**Status:** 🟢 **BAIXO** — Migração gradual planejada, sem urgência

---

## 📅 Cronograma de Execução (5 Dias Úteis)

### 🗓️ Dia 1: Validação e Preparação Backend

**Objetivo:** Confirmar estado atual e preparar movimentação de arquivos Django

**Tarefas:**
- [ ] Executar `pytest --cov` para baseline de cobertura
- [ ] Verificar que produção rodou migrações da Fase 5
  ```bash
  docker compose exec web python manage.py showmigrations inventory
  ```
- [ ] Confirmar que `routes_builder` não tem referências ativas
  ```bash
  grep -r "routes_builder" backend/ --exclude-dir=migrations
  ```
- [ ] Documentar dependências atuais em `requirements.txt`

**Entregável:** Relatório de estado pré-reorganização

---

### 🗓️ Dia 2: Limpeza do Zombie App

**Objetivo:** Remover completamente `routes_builder` do projeto

**Procedimento:**

1. **Fake Migration para Histórico:**
   ```bash
   # Marcar migrações antigas como aplicadas sem executar
   docker compose exec web python manage.py migrate inventory --fake
   ```

2. **Remover de `INSTALLED_APPS`:**
   ```python
   # backend/settings/base.py
   INSTALLED_APPS = [
       # ...
       # "routes_builder",  # ❌ REMOVIDO - Migrado para inventory (Nov 2025)
   ]
   ```

3. **Deletar Código Morto:**
   ```bash
   rm -rf backend/routes_builder/
   git rm -r backend/routes_builder/
   git commit -m "chore: remove routes_builder zombie app (Phase 6)"
   ```

4. **Atualizar Documentação:**
   - [x] Atualizar `doc/architecture/MODULES.md`
   - [x] Atualizar `.github/copilot-instructions.md` (já feito)
   - [ ] Adicionar nota em `doc/releases/CHANGELOG.md`

**Validação:**
```bash
# Deve rodar sem erros
docker compose exec web python manage.py check
docker compose exec web pytest -q
```

**Entregável:** Commit com remoção completa do app

---

### 🗓️ Dia 3: Consolidação de Diretórios (Não Prioritário)

**⚠️ IMPORTANTE:** Baseado na análise do projeto, a estrutura atual **JÁ ESTÁ ORGANIZADA**:

```
/
├── backend/               # ✅ Django separado
├── frontend/              # ✅ Vue separado
├── docker/                # ✅ Infra separada
├── scripts/               # ✅ Scripts separados
└── doc/                   # ✅ Docs organizadas
```

**Ação Recomendada:** **SKIP** — Estrutura atual está adequada

**Ajustes Menores (Opcionais):**
- [ ] Mover `staticfiles/` para `backend/staticfiles/` (já está correto)
- [ ] Revisar `.dockerignore` e `.gitignore` para otimizar build contexts

---

### 🗓️ Dia 4: Otimização PostGIS

**Objetivo:** Refatorar queries críticas para aproveitar índices espaciais

**Queries Prioritárias:**

1. **Busca de Devices Próximos:**
   ```python
   # backend/inventory/usecases/spatial.py (NOVO ARQUIVO)
   
   from django.contrib.gis.measure import D
   from django.contrib.gis.geos import Point
   from inventory.models import Device
   
   def get_nearby_devices(lat: float, lon: float, radius_km: float):
       """
       Busca devices dentro de um raio usando índice espacial PostGIS.
       
       Performance: O(log n) com índice GIST vs O(n) em Python puro.
       """
       point = Point(lon, lat, srid=4326)
       return Device.objects.filter(
           location__distance_lte=(point, D(km=radius_km))
       ).select_related('site')
   ```

2. **BBox Viewport (já implementado em `inventory/api/spatial.py`):**
   - ✅ **JÁ CORRETO** — Usa `Polygon.from_bbox()` + filtro PostGIS
   - Apenas documentar padrão para equipe

3. **Adicionar Índice GIST:**
   ```python
   # backend/inventory/migrations/0012_add_gist_indexes.py
   
   from django.contrib.gis.db import models
   from django.db import migrations
   
   class Migration(migrations.Migration):
       dependencies = [
           ('inventory', '0011_populate_spatial_fields'),
       ]
       
       operations = [
           migrations.AddIndex(
               model_name='device',
               index=models.Index(fields=['location'], name='device_location_gist'),
           ),
           migrations.AddIndex(
               model_name='fibercable',
               index=models.Index(fields=['path'], name='cable_path_gist'),
           ),
       ]
   ```

**Testes de Performance:**
```bash
# Benchmark antes vs depois
docker compose exec web python manage.py shell
>>> from inventory.usecases.spatial import get_nearby_devices
>>> import time
>>> start = time.time()
>>> devices = get_nearby_devices(-15.7801, -47.9292, 10)
>>> print(f"Query time: {time.time() - start:.4f}s")
```

**Entregável:** Migração + testes unitários

---

### 🗓️ Dia 5: Aceleração Vue Rollout (Opcional)

**Objetivo:** Aumentar % de rollout do Vue Dashboard se métricas forem positivas

**Status Atual:**
- Canary em **10%** (configurado em `.env` e `database/runtime.env`)
- Lógica: `maps_view/views.py::dashboard_view()` via hash MD5 do session ID

**Critérios para Aumento:**
1. **Error Rate < 0.5%** (Sentry/logs)
2. **Page Load < 2s** (P95)
3. **Feedback Positivo** de usuários no bucket 10%

**Procedimento de Aumento para 25%:**

1. **Atualizar Configuração:**
   ```bash
   # .env
   VUE_DASHBOARD_ROLLOUT_PERCENTAGE=25
   
   # database/runtime.env
   VUE_DASHBOARD_ROLLOUT_PERCENTAGE="25"
   ```

2. **Restart Containers:**
   ```bash
   cd docker
   docker compose restart web
   ```

3. **Monitorar por 48h:**
   - Prometheus: `/metrics/` → Taxa de erros HTTP 500
   - Sentry: Erros JS do Vue vs Django templates
   - Logs: `docker compose logs -f web | grep ERROR`

**Rollback se Necessário:**
```bash
# Voltar para 10%
VUE_DASHBOARD_ROLLOUT_PERCENTAGE=10
docker compose restart web
```

**Entregável:** Relatório de métricas + decisão de rollout

---

## 🎯 Critérios de Sucesso

| Métrica | Valor Alvo | Medição |
|---------|------------|---------|
| **Cobertura de Testes** | ≥ 80% | `pytest --cov` |
| **Apps Zombie** | 0 | `grep routes_builder backend/` |
| **Query Spatial Performance** | < 100ms (P95) | Benchmark `get_nearby_devices` |
| **Build Time Docker** | < 5 min | GitHub Actions CI |
| **Onboarding Time** | < 2h (dev setup) | Feedback time-to-first-commit |

---

## 🚧 Riscos e Mitigações

### Risco 1: Remoção Prematura do `routes_builder`

**Probabilidade:** Baixa  
**Impacto:** Alto (quebra produção)

**Mitigação:**
- Confirmar em **TODOS** ambientes que migrações da Fase 5 foram aplicadas
- Manter backup do código por 30 dias antes de delete permanente
- Usar `git tag phase-5-complete` antes da remoção

### Risco 2: Performance Degradada com PostGIS

**Probabilidade:** Muito Baixa  
**Impacto:** Médio

**Mitigação:**
- Benchmark obrigatório antes/depois
- Rollback fácil: queries antigas ficam comentadas no código
- Monitorar `django_db_query_duration_seconds` no Prometheus

### Risco 3: Vue Rollout Causa Regressões

**Probabilidade:** Baixa  
**Impacto:** Médio

**Mitigação:**
- Rollout gradual: 10% → 25% → 50% → 100%
- Feature flag permite desabilitar instantaneamente
- Testes E2E obrigatórios antes de cada aumento

---

## 📚 Referências

- [Fase 5 Completion Report](../reports/phases/PHASE_5_COMPLETION_REPORT.md)
- [Architecture Modules](../architecture/MODULES.md)
- [Data Flow Patterns](../architecture/DATA_FLOW.md)
- [Copilot Instructions](../../.github/copilot-instructions.md)

---

## 📝 Notas de Implementação

### Ordem de Execução Recomendada

1. **Dia 1-2:** Remoção do `routes_builder` (CRÍTICO)
2. **Dia 4:** Otimização PostGIS (ALTO IMPACTO)
3. **Dia 3:** Skip (estrutura já organizada)
4. **Dia 5:** Vue rollout (BAIXA PRIORIDADE)

### Comandos Rápidos

```bash
# Validar estado atual
make test
docker compose exec web python manage.py check

# Remover zombie app
git rm -r backend/routes_builder/
git commit -m "chore: remove routes_builder (Phase 6)"

# Adicionar índices PostGIS
docker compose exec web python manage.py makemigrations inventory
docker compose exec web python manage.py migrate

# Aumentar Vue rollout
# Editar .env: VUE_DASHBOARD_ROLLOUT_PERCENTAGE=25
docker compose restart web
```

---

**Última Atualização:** 18 de Novembro de 2025  
**Próxima Revisão:** Após conclusão da Fase 6 (estimada para 25 Nov 2025)
