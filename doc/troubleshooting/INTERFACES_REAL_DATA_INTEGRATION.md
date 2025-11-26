# Integração de Dados Reais - Modal de Interfaces

**Data**: 2025-01-22  
**Componente**: Device Import System - Interfaces Viewer  
**Status**: ✅ Implementado

---

## Sumário Executivo

Substituição de dados mockados por integração real com banco de dados PostgreSQL para exibição de interfaces/portas de dispositivos importados do Zabbix.

---

## Problema Identificado

### Contexto
O modal de interfaces estava funcional, mas exibia apenas dados mockados (hardcoded) para demonstração:

```javascript
// ❌ ANTES - Mock data
interfacesData.value = [
  {
    name: 'ether1',
    description: 'WAN Principal',
    status: 'up',
    speed: '1 Gbps',
    rx_power: -15.2,
    tx_power: -3.5
  },
  // ... mais dados mockados
];
```

### Sintomas
- Interface mostrava sempre os mesmos dados independente do dispositivo
- Não refletia portas realmente cadastradas no banco
- Usuário não conseguia visualizar informações reais dos equipamentos

---

## Solução Implementada

### 1. Identificação de Endpoint Existente

**Descoberta**: Backend já tinha endpoint completo para listar portas:

```python
# backend/inventory/api/devices.py
@require_GET
@login_required
@handle_api_errors
def api_device_ports(request: HttpRequest, device_id: int) -> HttpResponse:
    try:
        payload = device_uc.get_device_ports(device_id)
    except InventoryNotFound as exc:
        return JsonResponse({"error": str(exc)}, status=404)
    return JsonResponse(payload)
```

**Rota Existente**:
```python
# backend/inventory/urls_api.py
path("devices/<int:device_id>/ports/", device_api.api_device_ports, name="device-ports"),
```

**Estrutura de Resposta**:
```json
{
  "ports": [
    {
      "id": 1,
      "name": "ether1",
      "device": "Router-01",
      "fiber_cable_id": null,
      "zabbix_item_key": "net.if.in[ether1]",
      "notes": "WAN Principal"
    }
  ]
}
```

### 2. Limpeza de Código Duplicado

**Ação**: Removido endpoint `api_device_ports_list` criado por engano

```python
# ❌ REMOVIDO - Endpoint duplicado desnecessário
@require_GET
@login_required
def api_device_ports_list(request, device_id):
    # ... código duplicado ...
```

**Motivo**: Funcionalidade já existe em `api_device_ports` usando arquitetura de usecases

### 3. Integração Frontend - DeviceImportManager.vue

**Antes** (Mock):
```javascript
// Simulação de dados
await new Promise(resolve => setTimeout(resolve, 800));
interfacesData.value = [
  { name: 'ether1', description: 'WAN Principal', status: 'up', ... },
  // ... hardcoded data
];
```

**Depois** (Real API):
```javascript
const fetchInterfaces = async (device) => {
  if (!device || !device.id) {
    interfacesData.value = [];
    return;
  }

  loadingInterfaces.value = true;

  try {
    console.log('[DeviceImportManager] Fetching interfaces for device:', device.id);
    
    // Chamada real à API
    const response = await api.get(`/api/v1/inventory/devices/${device.id}/ports/`);
    
    if (response.ports) {
      // Mapeia os dados da API para o formato esperado pelo template
      interfacesData.value = response.ports.map(port => ({
        id: port.id,
        name: port.name,
        description: port.notes || '',
        status: 'unknown', // TODO: Integrar com Zabbix
        speed: '',         // TODO: Integrar com Zabbix
        rx_power: null,    // TODO: Integrar com Zabbix
        tx_power: null,    // TODO: Integrar com Zabbix
        fiber_cable_id: port.fiber_cable_id,
        zabbix_item_key: port.zabbix_item_key
      }));
      
      console.log('[DeviceImportManager] Interfaces loaded:', interfacesData.value.length);
    } else {
      interfacesData.value = [];
    }
  } catch (error) {
    console.error('[DeviceImportManager] Error fetching interfaces:', error);
    notifyError('Erro', 'Não foi possível carregar as interfaces do dispositivo.');
    interfacesData.value = [];
  } finally {
    loadingInterfaces.value = false;
  }
};
```

### 4. Integração Frontend - DeviceEditModal.vue

Mesma atualização aplicada ao `fetchInterfaces` no DeviceEditModal.vue para garantir consistência entre os dois pontos de acesso ao modal de interfaces.

---

## Estrutura de Dados

### Modelo Port (PostgreSQL)

```python
# backend/inventory/models.py
class Port(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)
    zabbix_item_key = models.CharField(max_length=255, blank=True, null=True)
    rx_power_item_key = models.CharField(max_length=255, blank=True, null=True)
    tx_power_item_key = models.CharField(max_length=255, blank=True, null=True)
    # ... outros campos
```

### Resposta da API

```typescript
interface PortResponse {
  ports: Array<{
    id: number;
    name: string;
    device: string;
    fiber_cable_id: number | null;
    zabbix_item_key: string | null;
    notes: string | null;
  }>;
}
```

### Formato Frontend (Mapeado)

```typescript
interface InterfaceData {
  id: number;
  name: string;
  description: string;
  status: 'up' | 'down' | 'unknown';
  speed: string;
  rx_power: number | null;
  tx_power: number | null;
  fiber_cable_id: number | null;
  zabbix_item_key: string | null;
}
```

---

## Fluxo Completo

### User Journey

1. **Usuário clica "Interfaces"**
   - Origem: Tabela de inventário OU footer do modal de edição
   - Pré-condição: Dispositivo deve ter `zabbix_hostid` (foi importado)

2. **Modal abre com loading state**
   ```vue
   <div v-if="loadingInterfaces">
     <div class="animate-spin..."></div>
     <p>Carregando interfaces...</p>
   </div>
   ```

3. **Chamada à API**
   ```
   GET /api/v1/inventory/devices/{device_id}/ports/
   ```

4. **Backend processa**
   - Usecase: `inventory.usecases.devices.get_device_ports(device_id)`
   - Query: `Port.objects.filter(device=device).select_related("device")`
   - Inclui: Referências a cabos de fibra conectados

5. **Frontend renderiza**
   ```vue
   <div v-for="iface in interfacesData" :key="iface.id">
     <h4>{{ iface.name }}</h4>
     <p v-if="iface.description">{{ iface.description }}</p>
     
     <!-- Status visual (TODO: Integração Zabbix) -->
     <span v-if="iface.status === 'unknown'">Status Desconhecido</span>
     
     <!-- Níveis de potência (TODO: Integração Zabbix) -->
     <div v-if="iface.rx_power">
       RX Power: {{ iface.rx_power }} dBm
     </div>
   </div>
   ```

6. **Empty state**
   ```vue
   <div v-else-if="!interfacesData.length">
     <p>Nenhuma interface cadastrada para este dispositivo.</p>
   </div>
   ```

---

## Pontos de Acesso ao Modal

### 1. Tabela de Inventário (InventoryManagerTab.vue)

```vue
<button 
  v-if="device.zabbix_hostid"
  @click="$emit('view-interfaces', device)" 
  class="text-blue-600 bg-blue-50 px-3 py-1 rounded"
>
  <i class="fas fa-network-wired mr-1"></i> Interfaces
</button>
```

**Event flow**:
```
InventoryManagerTab → emit('view-interfaces', device)
  ↓
DeviceImportManager → openInterfacesModal(device)
  ↓
fetchInterfaces(device) → API call
```

### 2. Footer do Modal de Edição (DeviceEditModal.vue)

```vue
<button 
  v-if="!isBatch && activeDevices[0]?.zabbix_id"
  @click="showInterfacesModal = true"
  class="px-4 py-2 border border-blue-300 text-blue-700 bg-white rounded"
>
  <i class="fas fa-network-wired mr-2"></i> Ver Interfaces
</button>
```

**Event flow**:
```
DeviceEditModal → showInterfacesModal.value = true
  ↓
watch(showInterfacesModal) → fetchInterfaces()
  ↓
API call
```

---

## TODOs - Próximas Melhorias

### 1. Integração Zabbix para Status em Tempo Real

**Objetivo**: Substituir `status: 'unknown'` por dados reais do Zabbix

**Implementação Backend**:
```python
# backend/inventory/usecases/devices.py
def get_device_ports_with_zabbix_status(device_id: int) -> Dict[str, Any]:
    ports = Port.objects.filter(device_id=device_id)
    
    for port in ports:
        if port.zabbix_item_key:
            # Query Zabbix API para status da interface
            status = zabbix_get_interface_status(
                device.zabbix_hostid, 
                port.zabbix_item_key
            )
            port_data['status'] = 'up' if status == 1 else 'down'
```

**Campos Zabbix sugeridos**:
- `net.if.status[{IFNAME}]` → Status up/down
- `net.if.speed[{IFNAME}]` → Velocidade da interface
- `net.if.in[{IFNAME}]` / `net.if.out[{IFNAME}]` → Tráfego

### 2. Integração de Potência Óptica

**Objetivo**: Exibir RX/TX power para interfaces SFP/SFP+

**Modelo já preparado**:
```python
class Port(models.Model):
    rx_power_item_key = models.CharField(max_length=255, blank=True, null=True)
    tx_power_item_key = models.CharField(max_length=255, blank=True, null=True)
```

**Implementação**:
```python
if port.rx_power_item_key:
    rx_value = zabbix_get_item_last_value(
        device.zabbix_hostid, 
        port.rx_power_item_key
    )
    port_data['rx_power'] = float(rx_value) if rx_value else None
```

**Item keys Mikrotik típicos**:
- `sfp.rx.power[{IFNAME}]`
- `sfp.tx.power[{IFNAME}]`
- `dom.rx.power[{IFNAME}]` (DOM - Digital Optical Monitoring)

### 3. Cache de Dados Zabbix

**Problema**: Múltiplas queries ao Zabbix podem ser lentas

**Solução**: SWR cache pattern (já usado no dashboard)

```python
from maps_view.cache_swr import SWRCache

def get_device_ports_with_optical_cached(device_id: int):
    cache_key = f"device_ports_optical_{device_id}"
    cache = SWRCache(cache_key, fresh_ttl=30, stale_ttl=60)
    
    data = cache.get()
    if data is None:
        data = get_device_ports_with_zabbix_status(device_id)
        cache.set(data)
    
    return data
```

### 4. Indicadores Visuais de Saúde

**Frontend enhancements**:

```vue
<!-- Badge de status -->
<span 
  :class="{
    'bg-green-100 text-green-800': iface.status === 'up',
    'bg-red-100 text-red-800': iface.status === 'down',
    'bg-gray-100 text-gray-600': iface.status === 'unknown'
  }"
  class="px-2 py-1 rounded-full text-xs font-medium"
>
  {{ iface.status.toUpperCase() }}
</span>

<!-- Alerta de potência baixa -->
<div v-if="iface.rx_power && iface.rx_power < -25" class="text-orange-600">
  ⚠️ Sinal fraco (< -25 dBm)
</div>

<!-- Gráfico de potência -->
<div class="flex items-center gap-2">
  <span class="text-sm text-gray-600">RX:</span>
  <div class="flex-1 bg-gray-200 rounded-full h-2">
    <div 
      :style="{ width: `${calculatePowerPercentage(iface.rx_power)}%` }"
      :class="getPowerColorClass(iface.rx_power)"
      class="h-2 rounded-full"
    ></div>
  </div>
  <span class="text-sm font-mono">{{ iface.rx_power }} dBm</span>
</div>
```

### 5. Histórico de Potência Óptica

**Endpoint adicional**:
```
GET /api/v1/inventory/ports/{port_id}/optical-history/?hours=24
```

**Resposta**:
```json
{
  "port_id": 1,
  "port_name": "sfp-sfpplus1",
  "history": [
    {
      "timestamp": "2025-01-22T15:30:00Z",
      "rx_power": -15.2,
      "tx_power": -3.5
    },
    // ... mais pontos
  ]
}
```

**Frontend**: Gráfico de linha com Chart.js ou similar

---

## Testes Realizados

### ✅ Build Frontend
```bash
cd frontend
npm run build
# ✓ built in 1.82s
```

### ✅ Restart Docker
```bash
cd docker
docker compose restart web
# ✔ Container docker-web-1  Started
```

### ⏳ Testes End-to-End Pendentes

**Checklist**:
- [ ] Importar dispositivo do Zabbix
- [ ] Cadastrar portas manualmente (ou via migração)
- [ ] Clicar em "Interfaces" na tabela de inventário
- [ ] Verificar se modal carrega dados reais
- [ ] Testar empty state (dispositivo sem portas)
- [ ] Testar error state (API offline)
- [ ] Verificar console logs para debugging

**Query SQL para criar portas de teste**:
```sql
INSERT INTO inventory_port (device_id, name, notes, zabbix_item_key, created_at, updated_at)
VALUES
  (1, 'ether1', 'WAN Principal', 'net.if.in[ether1]', NOW(), NOW()),
  (1, 'ether2', 'LAN', 'net.if.in[ether2]', NOW(), NOW()),
  (1, 'sfp-sfpplus1', 'Fibra Óptica', 'net.if.in[sfp-sfpplus1]', NOW(), NOW());
```

---

## Arquivos Modificados

### Backend
- ✅ `backend/inventory/api/devices.py`
  - Removido: `api_device_ports_list` (duplicado)
  - Mantido: `api_device_ports` (existente, funcional)
  - Atualizado: `__all__` exports

### Frontend
- ✅ `frontend/src/components/DeviceImport/DeviceImportManager.vue`
  - Linha ~415: `fetchInterfaces` substituído por chamada real à API
  - Mapeamento: `response.ports` → `interfacesData.value`
  - Error handling: `notifyError` em caso de falha

- ✅ `frontend/src/components/DeviceImport/DeviceEditModal.vue`
  - Linha ~793: `fetchInterfaces` substituído por chamada real à API
  - Consistência: Mesmo padrão do DeviceImportManager

### Build
- ✅ `backend/staticfiles/vue-spa/`
  - Arquivos gerados por `npm run build`
  - Assets com hash para cache busting

---

## Benefícios

### Técnicos
- ✅ Remoção de código duplicado/desnecessário
- ✅ Arquitetura consistente (usecases + API views)
- ✅ Error handling robusto (try/catch + notificações)
- ✅ Logging adequado para debugging
- ✅ Type safety nas transformações de dados

### Funcionais
- ✅ Dados reais do banco de dados PostgreSQL
- ✅ Reflete estado atual das portas cadastradas
- ✅ Suporte a empty state (sem portas)
- ✅ Preparação para integração Zabbix (campos prontos)
- ✅ Escalabilidade (usa queries otimizadas com `select_related`)

### UX
- ✅ Loading state durante fetch
- ✅ Mensagens de erro amigáveis
- ✅ Console logs para debug
- ✅ Responsividade mantida

---

## Riscos Mitigados

### ❌ Risco: Endpoint duplicado causando confusão
**Mitigação**: Removido `api_device_ports_list`, mantido apenas `api_device_ports`

### ❌ Risco: Frontend e backend desalinhados
**Mitigação**: Mapeamento explícito de campos (`response.ports` → `interfacesData`)

### ❌ Risco: Crashes em caso de erro de API
**Mitigação**: Try/catch + fallback para array vazio + notificação ao usuário

### ❌ Risco: Dispositivos sem portas quebrarem UI
**Mitigação**: Empty state handled (`v-else-if="!interfacesData.length"`)

---

## Próximos Passos Recomendados

### Curto Prazo (Sprint Atual)
1. **Testar com dados reais**
   - Importar dispositivo
   - Cadastrar portas
   - Validar modal de interfaces

2. **Criar migração de portas Zabbix**
   - Script para popular Port table a partir de Zabbix API
   - `zabbix.host.interface.get` → `Port.objects.create()`

### Médio Prazo (Próximo Sprint)
3. **Integração Zabbix para status**
   - Implementar `get_device_ports_with_zabbix_status`
   - Adicionar endpoint `/api/v1/inventory/devices/{id}/ports/live/`
   - Frontend polling ou WebSocket para updates em tempo real

4. **Potência óptica**
   - Configurar item keys de RX/TX power no Zabbix
   - Atualizar Port model com chaves corretas
   - Implementar query de valores Zabbix

### Longo Prazo (Backlog)
5. **Dashboard de interfaces**
   - Visão agregada de todas as interfaces
   - Filtros por status, tipo, dispositivo
   - Alertas para interfaces down ou sinal fraco

6. **Histórico e métricas**
   - Gráficos de potência óptica ao longo do tempo
   - Tráfego de rede (in/out)
   - SLA tracking (uptime percentual)

---

## Conclusão

A integração de dados reais para o modal de interfaces foi concluída com sucesso, eliminando mock data e conectando diretamente ao banco PostgreSQL via endpoint existente. A implementação seguiu as melhores práticas do projeto (usecases, error handling, logging) e está preparada para melhorias futuras com integração Zabbix.

**Status Final**: ✅ **Produção-Ready** (após testes end-to-end com dados reais)

---

## Referências

### Código Relacionado
- Endpoint: `backend/inventory/api/devices.py::api_device_ports`
- Usecase: `backend/inventory/usecases/devices.py::get_device_ports`
- Route: `backend/inventory/urls_api.py` (linha ~20)
- Frontend: `frontend/src/components/DeviceImport/DeviceImportManager.vue`
- Frontend: `frontend/src/components/DeviceImport/DeviceEditModal.vue`

### Documentação
- Copilot Instructions: `.github/copilot-instructions.md`
- Architecture: `doc/architecture/MODULES.md`
- Data Flow: `doc/architecture/DATA_FLOW.md`

### Issues Relacionadas
- N/A (Feature request conversacional)

---

**Autor**: GitHub Copilot (Claude Sonnet 4.5)  
**Revisão**: Pendente  
**Versão**: 1.0
