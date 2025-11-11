# Roadmap: Preparação para Vue 3 (Próximas Fases)

## 🎯 Contexto

Seguindo as recomendações estratégicas do usuário após análise do código, este roadmap detalha os próximos passos ANTES de migrar o frontend para Vue 3.

> **Princípio:** "Se você simplesmente conectar o Vue 3 nas APIs lentas atuais, ele continuará lento."

## ✅ Fases Concluídas

### Phase 8: Celery Background Processing (Cable Status)
- **Status:** ✅ Implementado e em produção
- **Commit:** `5cafda6`
- **Benefício:** API `/api/v1/inventory/fibers/oper-status/` passou de 40s → <100ms
- **Padrão:** Cache Redis (120s TTL) + WebSocket push updates

### Phase 9: Async Optical Levels (Port RX/TX)
- **Status:** ✅ Implementado
- **Commit:** `89d0ac0`
- **Benefício:** API `/api/v1/fibers/<id>/cached-status/` = 0 Zabbix calls (DB read only)
- **Padrão:** Persistência em modelo (Port.last_rx_power / last_tx_power)

## 🚧 Phase 9.1: Completar Migração Assíncrona (Estimativa: 2-3 dias)

### Objetivo
Eliminar **100% das chamadas síncronas ao Zabbix** em todas as funções de `inventory/usecases/fibers.py`.

### Tarefas

#### 1. Migrar `update_cable_oper_status()` para DB-backed
**Arquivo:** `backend/inventory/usecases/fibers.py`

**Antes:**
```python
def update_cable_oper_status(cable_id: int) -> Dict[str, Any]:
    # Chamadas SÍNCRONAS ao Zabbix:
    status_origin, raw_origin, meta_origin = get_oper_status_from_port(origin_port)
    status_dest, raw_dest, meta_dest = get_oper_status_from_port(dest_port)
    origin_optical = fetch_port_optical_snapshot(origin_port)  # LENTO
    dest_optical = fetch_port_optical_snapshot(dest_port)      # LENTO
```

**Depois:**
```python
def update_cable_oper_status(cable_id: int) -> Dict[str, Any]:
    cable = FiberCable.objects.select_related("origin_port", "destination_port").get(id=cable_id)
    
    # Leitura dos campos já populados pelo Celery (Phase 9)
    origin_optical = {
        "rx_dbm": cable.origin_port.last_rx_power,
        "tx_dbm": cable.origin_port.last_tx_power,
        "last_check": cable.origin_port.last_optical_check,
    }
    dest_optical = {
        "rx_dbm": cable.destination_port.last_rx_power,
        "tx_dbm": cable.destination_port.last_tx_power,
        "last_check": cable.destination_port.last_optical_check,
    }
    
    # Status também cacheado (Phase 8)
    cache_key = f"cable:oper_status:{cable_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Fallback para cálculo sob demanda (raro)
    ...
```

**Migration necessária:**
- Adicionar `FiberCable.last_status_check` (DateTimeField)
- Adicionar `FiberCable.last_status_origin` (CharField)
- Adicionar `FiberCable.last_status_dest` (CharField)

#### 2. Persistir Status no Modelo (eliminar dependência Redis)

**Modificar tarefa:** `backend/inventory/tasks.py → refresh_cables_oper_status()`

```python
@shared_task(name="inventory.tasks.refresh_cables_oper_status")
def refresh_cables_oper_status(self: Any) -> dict[str, Any]:
    for cable in cables:
        status_data = fiber_uc.update_cable_oper_status(cable.id)
        
        # NOVO: Persistir no banco (eliminar Redis)
        cable.last_status_origin = status_data["origin_status"]
        cable.last_status_dest = status_data["destination_status"]
        cable.last_status_check = timezone.now()
        cable.save(update_fields=[
            "status",
            "last_status_origin",
            "last_status_dest",
            "last_status_check",
        ])
        
        # Manter cache Redis opcional (para backward compatibility)
        cache.set(f"cable:oper_status:{cable.id}", status_data, timeout=120)
```

**Vantagem:** Banco vira fonte primária, Redis vira camada opcional de aceleração.

#### 3. Refatorar `compute_live_status()` → Task Celery

**Arquivo atual:** `backend/inventory/usecases/fibers.py`

**Problema:** Função chamada por API REST faz queries Zabbix em tempo real.

**Solução:**
```python
# backend/inventory/tasks.py
@shared_task(name="inventory.tasks.refresh_fiber_live_status")
def refresh_fiber_live_status() -> dict[str, Any]:
    """
    Calcula status "live" de todos os cabos e persiste no modelo.
    Similar ao refresh_cables_oper_status, mas com lógica "live".
    """
    cables = FiberCable.objects.select_related("origin_port", "destination_port").all()
    
    for cable in cables:
        live_status = _compute_live_status_internal(cable)
        
        # Persistir resultado
        cable.last_live_status = live_status.status
        cable.last_live_check = timezone.now()
        cable.save(update_fields=["last_live_status", "last_live_check"])
```

**Agendar no beat:**
```python
# backend/core/celery.py
beat_schedule = {
    # ...
    "refresh-fiber-live-status": {
        "task": "inventory.tasks.refresh_fiber_live_status",
        "schedule": 120.0,  # 2 minutos (mesmo intervalo cable status)
        "options": {"queue": "zabbix"},
    },
}
```

#### 4. Criar API "cached-live-status"

```python
# backend/inventory/api/fibers.py
@require_GET
@api_login_required
def api_fiber_cached_live_status(request: HttpRequest, cable_id: int) -> JsonResponse:
    cable = FiberCable.objects.get(id=cable_id)
    
    return JsonResponse({
        "cable_id": cable.id,
        "live_status": cable.last_live_status,
        "last_check": cable.last_live_check,
    })
```

### Checklist Phase 9.1

- [ ] Adicionar campos `FiberCable.last_status_*` (migration)
- [ ] Adicionar campos `FiberCable.last_live_*` (migration)
- [ ] Modificar `refresh_cables_oper_status` para persistir no DB
- [ ] Criar task `refresh_fiber_live_status`
- [ ] Agendar task no Celery Beat
- [ ] Criar endpoint `cached-live-status`
- [ ] Atualizar testes (cobertura 100%)
- [ ] Validar em staging (0 queries Zabbix nas APIs REST)

**Estimativa:** 2-3 dias de desenvolvimento + 1 dia de testes.

---

## 🗺️ Phase 10: Migração PostGIS (Estimativa: 1-2 semanas)

### Objetivo
Resolver o **próximo grande gargalo de performance do mapa** antes de migrar o frontend para Vue 3.

### Problema Atual

**JSONField para coordenadas:**
```python
# backend/inventory/models_routes.py
class RouteSegment(models.Model):
    path_coordinates = models.JSONField(
        blank=True,
        null=True,
        help_text='Array of {"lat": float, "lng": float} points.',
    )
```

**Consequências:**
- ❌ MySQL não consegue filtrar cabos por área visível (BBox)
- ❌ Frontend tem que carregar **TODOS** os cabos e filtrar no JavaScript
- ❌ Não escala para >1000 segmentos (mapa congela)

### Solução: PostGIS

**Vantagens:**
- ✅ Filtros espaciais nativos (`path__bboverlaps`, `path__intersects`)
- ✅ Backend retorna apenas segmentos visíveis no mapa atual
- ✅ Escalável para 10k+ segmentos (query <100ms)
- ✅ Suporta cálculo de distâncias, interseções, buffers (futuro)

### Tarefas

#### 10.1: Infraestrutura

1. **Provisionar PostgreSQL + PostGIS**
   - Docker Compose:
     ```yaml
     services:
       postgres:
         image: postgis/postgis:16-3.4
         environment:
           POSTGRES_DB: mapsprovefiber
           POSTGRES_USER: provemaps
           POSTGRES_PASSWORD: ${DB_PASSWORD}
         volumes:
           - pg_data:/var/lib/postgresql/data
     ```

2. **Migrar dados MySQL → PostgreSQL**
   - Usar `pg_dump` / `mysqldump` ou Django management command
   - Validar integridade (contagem de registros, FKs)

#### 10.2: Código

1. **Atualizar settings**
   ```python
   # backend/settings/base.py
   INSTALLED_APPS = [
       "django.contrib.gis",  # ADICIONAR
       # ...
   ]
   
   DATABASES = {
       "default": {
           "ENGINE": "django.contrib.gis.db.backends.postgis",
           "NAME": os.getenv("DB_NAME", "mapsprovefiber"),
           "USER": os.getenv("DB_USER", "provemaps"),
           # ...
       }
   }
   ```

2. **Transformar modelos**
   ```python
   # backend/inventory/models_routes.py
   from django.contrib.gis.db import models as gis_models
   
   class RouteSegment(models.Model):
       # ANTES: path_coordinates = models.JSONField(...)
       # DEPOIS:
       path = gis_models.LineStringField(
           srid=4326,  # WGS84 (padrão GPS)
           blank=True,
           null=True,
           help_text="Trajeto geográfico do segmento.",
       )
   ```

3. **Criar migration de transformação**
   ```python
   # Converter JSON → LineString
   from django.contrib.gis.geos import LineString
   
   def convert_json_to_linestring(apps, schema_editor):
       RouteSegment = apps.get_model("inventory", "RouteSegment")
       
       for segment in RouteSegment.objects.all():
           coords = segment.path_coordinates  # [{"lat": ..., "lng": ...}, ...]
           if coords:
               points = [(pt["lng"], pt["lat"]) for pt in coords]
               segment.path = LineString(points, srid=4326)
               segment.save(update_fields=["path"])
   ```

#### 10.3: API com Filtro BBox

```python
# backend/inventory/viewsets.py (DRF)
from django.contrib.gis.geos import Polygon
from rest_framework import viewsets

class RouteSegmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RouteSegment.objects.all()
    serializer_class = RouteSegmentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Exemplo: /api/segments/?bbox=-49.2,-16.6,-49.1,-16.5
        bbox_param = self.request.query_params.get('bbox')
        if bbox_param:
            try:
                xmin, ymin, xmax, ymax = map(float, bbox_param.split(','))
                bbox_polygon = Polygon.from_bbox((xmin, ymin, xmax, ymax))
                
                # MÁGICA DO POSTGIS: filtro espacial no banco!
                queryset = queryset.filter(path__bboverlaps=bbox_polygon)
            except (ValueError, TypeError):
                pass
        
        return queryset
```

**Performance:**
- **Antes:** Carregar 5000 segmentos (5MB JSON) → frontend filtra no JavaScript
- **Depois:** Carregar 50 segmentos visíveis (50KB JSON) → PostgreSQL filtra na query

### Checklist Phase 10

- [ ] Provisionar PostgreSQL + PostGIS (Docker/staging)
- [ ] Atualizar `settings/base.py` (ENGINE + gis)
- [ ] Transformar `RouteSegment.path_coordinates` → `path` (LineStringField)
- [ ] Criar migration de conversão de dados (JSON → LineString)
- [ ] Testar queries espaciais (bboverlaps, distance, etc.)
- [ ] Implementar API com filtro `bbox`
- [ ] Validar performance (query <100ms para BBox)
- [ ] Migrar dados de produção (backup + conversão)
- [ ] Deploy staging → produção

**Estimativa:** 1-2 semanas (incluindo testes de carga e validação).

---

## 🎨 Phase 11: Frontend Vue 3 + Pinia (Estimativa: 3-4 semanas)

### Objetivo
Migrar frontend de `dashboard.js` (JavaScript monolítico) para **Vue 3 + Pinia**, consumindo as APIs rápidas criadas nas Phases 8-10.

### Pré-requisitos

✅ **Phase 9.1 concluída:** Todas as APIs retornam dados do banco (zero Zabbix síncrono)  
✅ **Phase 10 concluída:** PostGIS filtra segmentos por BBox (mapa escalável)

### Estrutura

```
frontend/
├── src/
│   ├── stores/
│   │   ├── inventory.js       # Estado de sites, devices, cables
│   │   ├── dashboard.js       # Estado de status, métricas
│   │   └── map.js             # Estado do mapa (bounds, zoom, segmentos)
│   ├── components/
│   │   ├── MapView.vue        # Google Maps wrapper
│   │   ├── CableList.vue      # Lista de cabos (sidebar)
│   │   └── OpticalStatus.vue  # Widget de sinal RX/TX
│   ├── composables/
│   │   ├── useWebSocket.js    # WebSocket Channels connection
│   │   └── useCableStatus.js  # Lógica de status de cabos
│   └── main.js
```

### Implementação

#### 11.1: Store Pinia (Inventory)

```javascript
// frontend/src/stores/inventory.js
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useInventoryStore = defineStore('inventory', () => {
  // State
  const sites = ref([]);
  const cables = ref({});  // Map<cableId, cable>
  const segments = ref({}); // Map<segmentId, segment>
  const loading = ref({ sites: false, cables: false, segments: false });
  const error = ref(null);
  
  // Actions
  
  /**
   * Busca sites (estático, cache longo)
   */
  async function fetchSites() {
    loading.value.sites = true;
    try {
      const response = await fetch('/api/v1/inventory/sites/');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      sites.value = await response.json();
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value.sites = false;
    }
  }
  
  /**
   * Busca segmentos visíveis no mapa (PostGIS BBox)
   */
  async function fetchSegmentsInView(mapBounds) {
    loading.value.segments = true;
    
    // Converte Google Maps bounds → "lng_min,lat_min,lng_max,lat_max"
    const bbox = [
      mapBounds.getSouthWest().lng(),
      mapBounds.getSouthWest().lat(),
      mapBounds.getNorthEast().lng(),
      mapBounds.getNorthEast().lat(),
    ].join(',');
    
    try {
      const response = await fetch(`/api/segments/?bbox=${bbox}`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const newSegments = await response.json();
      
      // Atualiza apenas segmentos visíveis (merge incremental)
      for (const segment of newSegments) {
        segments.value[segment.id] = segment;
      }
      
    } catch (err) {
      error.value = err.message;
    } finally {
      loading.value.segments = false;
    }
  }
  
  /**
   * Busca status óptico cacheado de um cabo (Phase 9 API)
   */
  async function fetchCableOpticalStatus(cableId) {
    try {
      const response = await fetch(`/api/v1/fibers/${cableId}/cached-status/`);
      if (!response.ok) return;
      
      const data = await response.json();
      
      // Atualiza estado
      if (cables.value[cableId]) {
        cables.value[cableId].optical = data;
      }
      
    } catch (err) {
      console.warn(`Failed to fetch optical status for cable ${cableId}`, err);
    }
  }
  
  /**
   * Atualiza status de cabos via WebSocket (Phase 8 push)
   */
  function applyCableStatusBatch(updates) {
    for (const update of updates) {
      if (cables.value[update.cable_id]) {
        cables.value[update.cable_id].status = update.status;
        cables.value[update.cable_id].origin_optical = update.origin_optical;
        cables.value[update.cable_id].destination_optical = update.destination_optical;
      }
    }
  }
  
  return {
    sites,
    cables,
    segments,
    loading,
    error,
    fetchSites,
    fetchSegmentsInView,
    fetchCableOpticalStatus,
    applyCableStatusBatch,
  };
});
```

#### 11.2: Composable WebSocket

```javascript
// frontend/src/composables/useWebSocket.js
import { ref, onMounted, onUnmounted } from 'vue';
import { useInventoryStore } from '@/stores/inventory';

export function useWebSocket() {
  const ws = ref(null);
  const connected = ref(false);
  const inventoryStore = useInventoryStore();
  
  function connect() {
    const wsUrl = `ws://${window.location.host}/ws/dashboard/status/`;
    ws.value = new WebSocket(wsUrl);
    
    ws.value.onopen = () => {
      connected.value = true;
      console.log('[WS] Conectado ao dashboard status');
    };
    
    ws.value.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      
      if (msg.type === 'cable_status') {
        // Atualiza estado via Pinia action
        inventoryStore.applyCableStatusBatch(msg.cables);
      }
    };
    
    ws.value.onclose = () => {
      connected.value = false;
      console.log('[WS] Desconectado, reconectando em 5s...');
      setTimeout(connect, 5000);
    };
  }
  
  function disconnect() {
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
  }
  
  onMounted(connect);
  onUnmounted(disconnect);
  
  return {
    connected,
  };
}
```

#### 11.3: Componente MapView

```vue
<!-- frontend/src/components/MapView.vue -->
<template>
  <div id="map" style="width: 100%; height: 600px;"></div>
</template>

<script setup>
import { onMounted, watch } from 'vue';
import { useInventoryStore } from '@/stores/inventory';

const inventoryStore = useInventoryStore();

let map = null;
let polylines = {}; // Map<segmentId, google.maps.Polyline>

onMounted(() => {
  // Inicializa Google Maps
  map = new google.maps.Map(document.getElementById('map'), {
    center: { lat: -15.7942, lng: -47.8822 },
    zoom: 10,
  });
  
  // Listener: quando usuário move o mapa
  map.addListener('idle', () => {
    const bounds = map.getBounds();
    inventoryStore.fetchSegmentsInView(bounds);
  });
});

// Reativo: quando segmentos mudam, atualiza polylines
watch(
  () => inventoryStore.segments,
  (newSegments) => {
    for (const [id, segment] of Object.entries(newSegments)) {
      if (!polylines[id]) {
        // Criar nova polyline
        const path = segment.path.coordinates.map(([lng, lat]) => ({ lat, lng }));
        polylines[id] = new google.maps.Polyline({
          path,
          map,
          strokeColor: getColorByStatus(segment.status),
          strokeWeight: 3,
        });
      } else {
        // Atualizar cor (status mudou via WebSocket)
        polylines[id].setOptions({
          strokeColor: getColorByStatus(segment.status),
        });
      }
    }
  },
  { deep: true }
);

function getColorByStatus(status) {
  const colors = {
    up: '#00FF00',
    down: '#FF0000',
    degraded: '#FFA500',
    unknown: '#808080',
  };
  return colors[status] || '#808080';
}
</script>
```

### Benefícios Phase 11

✅ **Performance:** Apenas segmentos visíveis carregados (PostGIS BBox)  
✅ **Reatividade:** Vue 3 atualiza DOM automaticamente (sem manipulação manual)  
✅ **Estado unificado:** Pinia centraliza dados (elimina variáveis globais)  
✅ **Tempo real:** WebSocket atualiza mapa sem polling HTTP  
✅ **Manutenibilidade:** Componentes Vue vs. 2000 linhas de `dashboard.js`

### Checklist Phase 11

- [ ] Configurar Vite + Vue 3 (já existente em `frontend/`)
- [ ] Implementar stores Pinia (inventory, dashboard, map)
- [ ] Criar composables (useWebSocket, useCableStatus)
- [ ] Componente MapView.vue (Google Maps wrapper)
- [ ] Componente CableList.vue (lista lateral)
- [ ] Componente OpticalStatus.vue (widget RX/TX)
- [ ] Integrar WebSocket (consumer do Phase 8)
- [ ] Testes E2E (Cypress/Playwright)
- [ ] Migração gradual (feature flags: `USE_VUE_DASHBOARD`)
- [ ] Deploy staging → produção

**Estimativa:** 3-4 semanas (desenvolvimento + testes).

---

## 📊 Cronograma Geral

| Phase | Descrição | Duração | Status |
|-------|-----------|---------|--------|
| 8 | Cable Status Celery | 3 dias | ✅ Concluído |
| 9 | Async Optical Levels | 2 dias | ✅ Concluído |
| 9.1 | Completar Migração Assíncrona | 2-3 dias | 🚧 Próximo |
| 10 | Migração PostGIS | 1-2 semanas | 📅 Planejado |
| 11 | Frontend Vue 3 + Pinia | 3-4 semanas | 📅 Planejado |

**Total estimado:** **6-7 semanas** para completar toda a migração.

---

## 🎯 Critérios de Sucesso

### Performance

- [ ] Todas as APIs REST respondem em <100ms (p95)
- [ ] Zero chamadas síncronas ao Zabbix durante requisições web
- [ ] Mapa carrega <100 segmentos independente do zoom (PostGIS BBox)
- [ ] WebSocket latência <50ms para atualizações

### Arquitetura

- [ ] Banco de dados = fonte da verdade (não Redis)
- [ ] Celery Beat atualiza cache a cada 2-5 minutos
- [ ] APIs REST são "burras" (apenas leem do banco)
- [ ] Frontend Vue 3 consome APIs rápidas (sem lógica de negócio)

### Qualidade

- [ ] Cobertura de testes >90%
- [ ] Zero regressões em funcionalidades existentes
- [ ] Documentação completa (ADRs, README, guias)
- [ ] Observabilidade (métricas Prometheus, logs estruturados)

---

## 📚 Referências

- [Phase 8 Documentation](./PHASE8_CABLE_STATUS_CELERY.md)
- [Phase 9 Documentation](./PHASE9_ASYNC_OPTICAL_LEVELS.md)
- [Copilot Instructions](./.github/copilot-instructions.md)
- [Django GeoDjango](https://docs.djangoproject.com/en/5.0/ref/contrib/gis/)
- [PostGIS Documentation](https://postgis.net/documentation/)
- [Vue 3 + Pinia Guide](https://pinia.vuejs.org/)

---

**Última atualização:** 2025-11-11  
**Responsável:** Equipe MapsProveFiber  
**Status:** Phase 9.1 em planejamento
