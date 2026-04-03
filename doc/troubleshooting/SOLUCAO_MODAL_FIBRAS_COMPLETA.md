# Solução Completa: Modal de Edição de Fibras com Dados Pré-populados

## 📋 Problema Original

O modal de edição de fibras óticas não estava pré-populando os campos de site, device e porta quando o usuário clicava para editar um cabo existente. Os dropdowns apareciam vazios com "Selecione..." apesar do cabo ter origem e destino configurados.

## 🔍 Diagnóstico

### Problemas Identificados

1. **Backend - Serializers sem campos enriquecidos**
   - `PortSerializer` não retornava `device_id`, `site_id`
   - `FiberCableSerializer` não tinha campos de contexto (origin_device_id, origin_site_id, etc.)

2. **Backend - Endpoint de portas retornava HTML**
   - Frontend usava `/api/v1/inventory/devices/{id}/ports/` (retornava redirect HTML)
   - Endpoint correto era `/api/v1/ports/?device={id}` (JSON com paginação)

3. **Frontend - Modal não usava campos enriquecidos**
   - `FiberEditModal.vue` não mapeava `origin_device_id` → `device_a`
   - `fetchPorts()` chamava endpoint errado
   - Watch no `props.cable` não carregava dados cascading

4. **Frontend - Componente pai com fallback complexo**
   - `FiberCablesList.vue` tentava endpoint antigo (`/inventory/fibers/{id}/`) primeiro
   - Helper `mapFiberDetailToForm()` não usava campos enriquecidos do backend

## ✅ Solução Implementada

### 1. Backend - Enriquecimento dos Serializers

**Arquivo**: `backend/inventory/serializers.py`

```python
class PortSerializer(serializers.ModelSerializer):
    device_id = serializers.IntegerField(source="device.id", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)
    site_id = serializers.IntegerField(source="device.site.id", read_only=True)
    site_name = serializers.CharField(source="device.site.name", read_only=True)
    
    class Meta:
        model = Port
        fields = [
            "id", "name", "port_type", "description",
            "device_id", "device_name", "site_id", "site_name"
        ]
```

**Arquivo**: `backend/inventory/serializers.py`

```python
class FiberCableSerializer(serializers.ModelSerializer):
    # Campos enriquecidos de origem
    origin_device_id = serializers.IntegerField(
        source="origin_port.device.id", read_only=True
    )
    origin_device_name = serializers.CharField(
        source="origin_port.device.name", read_only=True
    )
    origin_port_name = serializers.CharField(
        source="origin_port.name", read_only=True
    )
    origin_site_id = serializers.IntegerField(
        source="origin_port.device.site.id", read_only=True
    )
    
    # Campos enriquecidos de destino
    destination_device_id = serializers.IntegerField(
        source="destination_port.device.id", read_only=True
    )
    destination_device_name = serializers.CharField(
        source="destination_port.device.name", read_only=True
    )
    destination_port_name = serializers.CharField(
        source="destination_port.name", read_only=True
    )
    destination_site_id = serializers.IntegerField(
        source="destination_port.device.site.id", read_only=True
    )
    
    class Meta:
        model = FiberCable
        fields = [
            "id", "name", "origin_port", "destination_port", "status",
            # Campos enriquecidos
            "origin_device_id", "origin_device_name", "origin_port_name",
            "origin_site_id", "destination_device_id", "destination_device_name",
            "destination_port_name", "destination_site_id"
        ]
```

### 2. Backend - Filtro de Portas por Device

**Arquivo**: `backend/inventory/viewsets.py`

```python
class PortViewSet(viewsets.ModelViewSet):
    queryset = Port.objects.all()
    serializer_class = PortSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related("device__site")
        device_id = self.request.query_params.get("device")
        if device_id:
            queryset = queryset.filter(device_id=device_id)
        return queryset
```

**Endpoint resultante**: `/api/v1/ports/?device=42` retorna portas do device 42 com campos enriquecidos.

### 3. Frontend - Correção do Modal

**Arquivo**: `frontend/src/components/Inventory/Fiber/FiberEditModal.vue`

#### 3.1. Endpoint correto para buscar portas

```javascript
const fetchPorts = async (deviceId, side) => {
  if (!deviceId) return;
  const targetList = side === 'a' ? portsA : portsB;
  targetList.value = [];
  
  try {
    const resp = await fetch(
      `/api/v1/ports/?device=${deviceId}&page_size=500`,
      {
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
      }
    );
    
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    
    const json = await resp.json();
    const ports = json.results || [];
    
    targetList.value = ports.map((p) => ({
      id: p.id,
      name: p.name,
      device_id: p.device_id,
      site_id: p.site_id,
    }));
  } catch (err) {
    console.error(`Erro ao carregar portas (device ${deviceId}):`, err);
  }
};
```

#### 3.2. Watch com mapeamento de campos enriquecidos

```javascript
watch(
  () => props.cable,
  async (newCable) => {
    if (newCable) {
      // Mapear campos enriquecidos do backend para estrutura do form
      form.value = {
        id: newCable.id || null,
        name: newCable.name || '',
        // Usar campos enriquecidos do serializer
        site_a: newCable.origin_site_id || newCable.site_a || '',
        device_a: newCable.origin_device_id || newCable.device_a || '',
        port_a: newCable.origin_port || newCable.port_a || '',
        site_b: newCable.destination_site_id || newCable.site_b || '',
        device_b: newCable.destination_device_id || newCable.device_b || '',
        port_b: newCable.destination_port || newCable.port_b || '',
        // Outros campos
        length: newCable.length || 0,
        status: newCable.status || 'planned',
        type: newCable.type || 'backbone',
        fiber_count: newCable.fiber_count || 12,
      };

      // Carregar devices e portas em cascata
      if (form.value.site_a) {
        await fetchDevices(form.value.site_a, 'a');
      }
      if (form.value.device_a) {
        await fetchPorts(form.value.device_a, 'a');
      }
      if (form.value.site_b) {
        await fetchDevices(form.value.site_b, 'b');
      }
      if (form.value.device_b) {
        await fetchPorts(form.value.device_b, 'b');
      }
    }
  },
  { immediate: true }
);
```

### 4. Frontend - Simplificação do Helper de Mapeamento

**Arquivo**: `frontend/src/components/Inventory/Fiber/mapFiberDetail.js`

```javascript
export function mapFiberDetailToForm({
  cable,
  detail,
  sites = [],
  originPortInfo = null,
  destPortInfo = null,
}) {
  const merged = { ...cable };
  
  // PRIORIDADE 1: Usar campos enriquecidos do backend
  merged.site_a = cable.origin_site_id || detail?.origin?.site_id || '';
  merged.site_b = cable.destination_site_id || detail?.destination?.site_id || '';
  merged.device_a = cable.origin_device_id || detail?.origin?.device_id || '';
  merged.device_b = cable.destination_device_id || detail?.destination?.device_id || '';
  merged.port_a = cable.origin_port || detail?.origin?.port_id || '';
  merged.port_b = cable.destination_port || detail?.destination?.port_id || '';

  // FALLBACK: Mapear por nome se campos enriquecidos não existirem
  if (!merged.site_a) {
    const originSiteName = detail?.origin?.site || cable.origin_site_name;
    merged.site_a = findSiteIdByName(sites, originSiteName);
  }
  if (!merged.site_b) {
    const destSiteName = detail?.destination?.site || cable.destination_site_name;
    merged.site_b = findSiteIdByName(sites, destSiteName);
  }

  // Metadados
  merged.length = detail?.length_km
    ? Number(detail.length_km) * 1000
    : cable.length_km
      ? Number(cable.length_km) * 1000
      : cable.length || 0;
  merged.status = normalizeStatus(detail?.status || cable.status || 'planned');
  merged.type = cable.type || 'backbone';
  merged.fiber_count = cable.fiber_count || 12;

  return merged;
}
```

### 5. Frontend - Simplificação do Componente Pai

**Arquivo**: `frontend/src/components/Inventory/FiberCablesList.vue`

```javascript
const handleEdit = async (cable) => {
  try {
    saving.value = true;
    if (!allSites.value.length) {
      await fetchSites().catch(() => ensureSitesFromCables());
    }

    // Buscar dados frescos do backend (com campos enriquecidos)
    const freshCable = await api.get(`/api/v1/fiber-cables/${cable.id}/`);
    console.debug('[FiberCables] Detalhe fibra com campos enriquecidos', freshCable);

    // Mapear para formato do modal
    const merged = mapFiberDetailToForm({
      cable: freshCable,
      detail: null,
      sites: allSites.value,
    });

    selectedCable.value = merged;
    showModal.value = true;
  } catch (err) {
    console.error('Erro ao carregar detalhes do cabo', err);
    alert(err?.message || 'Erro ao carregar cabo.');
  } finally {
    saving.value = false;
  }
};
```

## 🧪 Validação

### Script de Teste Automatizado

Criado `test_fiber_modal_data_flow.py` que valida:

1. Endpoint `/api/v1/fiber-cables/{id}/` retorna HTTP 200
2. Response é JSON válido
3. Campos básicos estão presentes (id, name, origin_port, destination_port, status)
4. Campos enriquecidos estão presentes (origin_device_id, origin_site_id, etc.)
5. Dados completos para cascading selects (site → device → port)

**Resultado do teste**:
```
✅ SUCESSO: Todos os campos necessários estão presentes!
   O modal deve popular os selects automaticamente.
```

### Exemplo de Resposta da API

```json
{
  "id": 38,
  "name": "24324",
  "origin_port": 345,
  "destination_port": 308,
  "status": "up",
  "origin_device_id": 42,
  "origin_device_name": "huawei - Switch Confresa",
  "origin_port_name": "XGigabitEthernet0/0/1",
  "origin_site_id": 41,
  "destination_device_id": 41,
  "destination_device_name": "Huawei - Switch Vila Rica",
  "destination_port_name": "XGigabitEthernet0/0/1",
  "destination_site_id": 57
}
```

## 📝 Checklist de Deploy

### Backend
- [x] Adicionar campos enriquecidos em `PortSerializer`
- [x] Adicionar campos enriquecidos em `FiberCableSerializer`
- [x] Implementar filtro `?device=X` em `PortViewSet`
- [x] Adicionar campos enriquecidos em `list_fiber_cables()` (legacy API)
- [x] Rebuild do container Docker (`docker compose build --no-cache web`)
- [x] Restart do container (`docker compose restart web`)

### Frontend
- [x] Corrigir endpoint em `fetchPorts()` de `FiberEditModal.vue`
- [x] Adicionar mapeamento de campos enriquecidos em `watch(props.cable)`
- [x] Atualizar `mapFiberDetailToForm()` para priorizar campos enriquecidos
- [x] Simplificar `handleEdit()` em `FiberCablesList.vue`
- [x] Build do frontend (`npm run build`)
- [x] Restart do container Django (para servir novos assets)

### Validação
- [x] Teste manual: Abrir modal de edição e verificar dropdowns pré-populados
- [x] Script automatizado: `python test_fiber_modal_data_flow.py`
- [x] Logs do navegador: Verificar `console.debug` mostrando dados mapeados

## 🎯 Fluxo de Dados Final

```
┌─────────────────────────────────────────────────────────────────┐
│ USUÁRIO CLICA EM "EDITAR CABO"                                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ FiberCablesList.vue::handleEdit(cable)                          │
│  1. Fetch: GET /api/v1/fiber-cables/38/                         │
│  2. Response com campos enriquecidos:                            │
│     {                                                            │
│       origin_site_id: 41,                                        │
│       origin_device_id: 42,                                      │
│       origin_port: 345,                                          │
│       destination_site_id: 57,                                   │
│       destination_device_id: 41,                                 │
│       destination_port: 308                                      │
│     }                                                            │
│  3. Mapeia via mapFiberDetailToForm():                          │
│     { site_a: 41, device_a: 42, port_a: 345, ... }              │
│  4. selectedCable.value = merged                                 │
│  5. showModal.value = true                                       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ FiberEditModal.vue::watch(props.cable)                          │
│  1. Recebe cable com: { site_a: 41, device_a: 42, ... }         │
│  2. Preenche form.value = { site_a: 41, device_a: 42, ... }     │
│  3. Cascading load:                                              │
│     - fetchDevices(site_a=41, 'a')                              │
│       → GET /api/v1/inventory/devices/select-options/           │
│       → devicesA.value = [{ id: 42, name: "Switch..." }, ...]   │
│     - fetchPorts(device_a=42, 'a')                              │
│       → GET /api/v1/ports/?device=42&page_size=500              │
│       → portsA.value = [{ id: 345, name: "XGig..." }, ...]      │
│  4. Repete para destino (site_b, device_b, port_b)              │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ RESULTADO: Modal com todos os selects pré-populados             │
│  - Site A: [✓] Selecionado                                      │
│  - Device A: [✓] Lista carregada + valor selecionado            │
│  - Port A: [✓] Lista carregada + valor selecionado              │
│  - Site B, Device B, Port B: [✓] Idem                           │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Troubleshooting

### Modal ainda mostra "Selecione..."

1. **Verificar backend**:
   ```bash
   python test_fiber_modal_data_flow.py
   ```
   Se falhar: serializers não têm campos enriquecidos

2. **Verificar console do navegador**:
   ```javascript
   // Deve aparecer:
   [FiberCables] Detalhe fibra com campos enriquecidos { origin_device_id: 42, ... }
   [FiberCables] Mapeado para modal { site_a: 41, device_a: 42, ... }
   ```
   Se não aparecer: frontend não foi rebuilded

3. **Verificar Network tab**:
   - Request: `GET /api/v1/fiber-cables/38/`
   - Response: Deve ter `origin_device_id`, `origin_site_id` no JSON
   - Se retornar HTML: endpoint errado ou sessão expirada

4. **Verificar watchers do Vue**:
   - No Vue DevTools, inspecionar `devicesA.value` e `portsA.value`
   - Devem estar populados após abrir o modal
   - Se vazios: `fetchDevices`/`fetchPorts` falharam

### Dropdowns carregam mas valor não fica selecionado

**Problema 1**: IDs dos campos não batem (ex: `form.device_a = 42` mas options têm strings `"42"`)

Solução: Garantir type consistency:
```javascript
// No fetchDevices
devicesA.value = devices.map((d) => ({
  id: Number(d.id),  // Force number
  name: d.name,
}));

// No form
device_a: Number(newCable.origin_device_id) || '',
```

**Problema 2**: Watches reativos resetando valores durante inicialização (CRÍTICO!)

Este era o problema principal! Os watches em `site_a`, `site_b`, `device_a`, `device_b` limpavam os valores assim que detectavam mudança, conflitando com o `watch(props.cable)` que tentava preencher o formulário.

Solução: Flag `isInitializing` para desabilitar watches reativos durante carregamento:
```javascript
const isInitializing = ref(false);

watch(
  () => props.cable,
  async (newCable) => {
    isInitializing.value = true; // Desabilita watches durante init
    
    if (newCable) {
      form.value = {
        site_a: newCable.origin_site_id,
        device_a: newCable.origin_device_id,
        port_a: newCable.origin_port,
        // ... etc
      };
      
      // Carregar cascading data
      await fetchDevices(form.value.site_a, 'a');
      await fetchPorts(form.value.device_a, 'a');
    }
    
    // Reativa watches após 100ms
    setTimeout(() => {
      isInitializing.value = false;
    }, 100);
  }
);

// Watches que resetam campos agora verificam flag
watch(
  () => form.value.site_a,
  async (siteId) => {
    if (isInitializing.value) return; // Ignora durante init!
    
    form.value.device_a = '';
    form.value.port_a = '';
    // ... reset cascading
  }
);
```

### Endpoint /api/v1/ports/?device=X retorna HTML

Problema: Middleware de autenticação redirecionando para login

Solução: Adicionar header `X-Requested-With` no fetch (já implementado):
```javascript
headers: {
  'X-Requested-With': 'XMLHttpRequest',
}
```

## 📚 Documentação Relacionada

- **Arquitetura**: `doc/architecture/MODULES.md` (inventário, serializers, viewsets)
- **API Reference**: `doc/api/ENDPOINTS.md` (endpoints de fiber-cables e ports)
- **Processos**: `doc/process/AGENTS.md` (padrões de coding agents)
- **Guia de Desenvolvimento**: `doc/guides/DEVELOPMENT.md` (setup Docker, frontend build)

## 🎉 Resultado Final

Modal de edição de fibras agora:
- ✅ Pré-popula todos os selects automaticamente
- ✅ Carrega devices e portas em cascata (site → device → port)
- ✅ Exibe nomes corretos nos dropdowns
- ✅ Mantém seleções do cabo original
- ✅ Funciona tanto para criar quanto editar
- ✅ Validado por script automatizado

---

**Data**: 2024-11-27  
**Versão**: 2.0.0  
**Autores**: AI Agent + Time de Desenvolvimento
