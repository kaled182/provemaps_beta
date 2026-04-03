# Sincronização de Grupos do Zabbix - Solução Implementada

## ⚠️ Problema Identificado

O parâmetro `selectGroups` na chamada `host.get` da API do Zabbix **não retorna** os grupos dos hosts em algumas versões/configurações do Zabbix.

**Comportamento observado:**
```python
# Esta chamada NÃO retorna o campo "groups"
zabbix_request("host.get", {
    "hostids": ["10669"],
    "selectGroups": ["groupid", "name"]
})

# Retorna apenas:
{
    "hostid": "10669",
    "name": "Device Name"
    # ❌ Campo "groups" AUSENTE!
}
```

**Causas possíveis:**
- Versão do Zabbix incompatível com `selectGroups`
- Usuário API em modo READ_ONLY
- Restrições de permissão na API
- Bug em versões específicas do Zabbix

---

## ✅ Solução Implementada: Busca Reversa (Reverse Lookup)

Ao invés de buscar grupos por host (`host.get` com `selectGroups`), implementamos **busca reversa**: buscamos hosts por grupo (`host.get` com `groupids`).

## ✅ Mudanças Aplicadas (Backend)

### 1. Comando `sync_zabbix_inventory` Atualizado

**Arquivo**: `backend/inventory/management/commands/sync_zabbix_inventory.py`

**Mudanças**:
- ✅ Importa automaticamente todos os grupos do Zabbix antes de sincronizar hosts
- ✅ **Sincronização em BATCH** depois de processar todos os hosts (otimizado)
- ✅ Usa função `sync_all_device_groups()` com reverse lookup
- ✅ Adiciona estatística de `groups_synced` no resumo
- ✅ Log detalhado de associações criadas

**Workflow:**
1. Importar grupos do Zabbix (`import_device_groups_from_zabbix()`)
2. Sincronizar todos os hosts (devices, ports)
3. **Batch sync de grupos** (`sync_all_device_groups()`) ← NOVO OTIMIZADO!

**Uso**:
```bash
# Importar todos os hosts com grupos
docker compose -f docker/docker-compose.yml exec web python manage.py sync_zabbix_inventory

# Limitar quantidade de hosts
docker compose -f docker/docker-compose.yml exec web python manage.py sync_zabbix_inventory --limit 50

# Modo verbose (mostra grupos associados)
docker compose -f docker/docker-compose.yml exec web python manage.py sync_zabbix_inventory --verbose
```

### 2. Endpoint `/api/v1/inventory/zabbix/lookup/hosts/grouped/` Melhorado

**Arquivo**: `backend/inventory/api/zabbix_lookup.py`

**Mudanças**:
- ✅ Retorna hosts agrupados por grupo do Zabbix
- ✅ Cada host inclui lista de seus grupos no campo `groups: []`
- ✅ Marca corretamente `is_imported: true/false` baseado no banco
- ✅ Detecta drift (diferenças entre Zabbix e banco)
- ✅ Previne duplicação de hosts no mesmo grupo

**Estrutura de resposta**:
```json
{
  "data": [
    {
      "zabbix_group_id": "22",
      "name": "Switch Huawei",
      "hosts": [
        {
          "zabbix_id": "10723",
          "name": "Huawei - Switch Elagro",
          "ip": "192.168.1.1",
          "status": "online",
          "is_imported": false,
          "has_drift": false,
          "drift_fields": [],
          "groups": ["Switch Huawei", "Network"]
        }
      ]
    },
    {
      "zabbix_group_id": "25",
      "name": "ZTE",
      "hosts": [...]
    }
  ],
  "count": 8
}
```

### 3. Serviço de Sincronização de Grupos (OTIMIZADO)

**Arquivo**: `backend/inventory/services/device_groups.py`

**Funções**:
- `import_device_groups_from_zabbix()` — Importa todos os grupos do Zabbix
- `sync_all_device_groups()` — **NOVA** Sincroniza grupos de TODOS os devices em batch usando reverse lookup  
- `sync_device_groups_for_device(device)` — Sincroniza grupos de UM device (usa reverse lookup para compatibilidade)

**Abordagem: Reverse Lookup (Busca Reversa)**

```python
def sync_all_device_groups() -> dict[str, int]:
    """
    Busca hosts POR GRUPO ao invés de grupos POR HOST.
    
    Mais eficiente: 14 chamadas (1 por grupo) ao invés de 40+ (1 por host).
    """
    # 1. Buscar todos os grupos
    all_groups = zabbix_request("hostgroup.get", {...})
    
    # 2. Para cada grupo, buscar hosts que pertencem a ele
    for group in all_groups:
        # Busca reversa - hosts por grupo
        hosts = zabbix_request("host.get", {
            "groupids": [group["groupid"]]  # ✅ FUNCIONA!
        })
        
        # Associar cada host ao grupo
        for host in hosts:
            device = Device.objects.get(zabbix_hostid=host["hostid"])
            device.groups.add(device_group)
    
    return {"synced": count, "failed": 0}
```

**Por que funciona:**
- ❌ `host.get` com `selectGroups` → NÃO retorna grupos
- ✅ `host.get` com `groupids` → FUNCIONA perfeitamente

**Performance:**
- **Antes**: N chamadas (uma por device) = 40 chamadas para 40 devices
- **Agora**: M chamadas (uma por grupo) = 14 chamadas para 14 grupos  
- **Ganho**: ~65% menos chamadas API



### 4. Scripts de Diagnóstico e Teste

**Arquivo**: `backend/scripts/sync_groups_workaround.py`

Remove todos os devices e portas do banco, mantendo os grupos para nova importação.

**Arquivo**: `backend/scripts/diagnose_zabbix_host_groups.py`

Diagnóstico completo da API do Zabbix:
- Testa `host.get` com e sem `selectGroups`
- Verifica busca reversa (hosts por grupo)
- Identifica problemas de permissão
- Mostra informações do usuário API

**Arquivo**: `backend/scripts/check_device_groups.py`

Verifica grupos associados a devices no banco de dados.

---

## 🧪 Resultados de Testes

### Teste com 10 Hosts

```bash
$ docker compose exec web python manage.py sync_zabbix_inventory --limit 10 --verbose

======================================================================
Zabbix Inventory Sync
======================================================================
Importing device groups from Zabbix...
[OK] Groups: 0 created, 14 updated

Fetching hosts from Zabbix API...
[OK] Found 10 host(s) in Zabbix

[1/10] Processing: Huawei - Switch Elagro
  [OK] Created device
    -> Created port

[2/10] Processing: Ubiquiti - Switch JBS STA  
  [OK] Created device
    -> Created port

... (8 mais) ...

Syncing device groups (batch operation)...
INFO Starting optimized group sync for all devices...
DEBUG Associated Huawei - Switch Santana Marajo with Switch Huawei
DEBUG Associated Huawei - Switch Elagro with Switch Huawei
DEBUG Associated Mikrotik - CCR Escritorio STA with Mikrotik
DEBUG Associated Ubiquiti - Switch JBS STA with Switch Ubiquiti
DEBUG Associated Ubiquiti - Switch Escritorio STA with Switch Ubiquiti
DEBUG Associated ZTE - OLT MANDI C610 with ZTE
DEBUG Associated ZTE - OLT CONFRESA C600 - 01 with ZTE
DEBUG Associated ZTE - OLT CONFRESA C600 - 02 with ZTE
DEBUG Associated VSOL - OLT EPON ELAGRO with VSOLUTION
DEBUG Associated VSOL - OLT EPON FURACAO with VSOLUTION

[OK] Synced 10 device-group associations

======================================================================
Sync Summary
======================================================================
Mode: COMMITTED
Duration: 9.45s
Sites created: 0
Sites updated: 2
Devices created: 10
Devices updated: 0
Ports created: 10
Ports updated: 0
Device groups synced: 10  ← ✅ SUCESSO!

Sync completed successfully!
```

### Verificação no Banco de Dados

```bash
$ docker compose exec web python scripts/check_device_groups.py

Total de grupos: 14
Dispositivos com grupos: 10
Dispositivos SEM grupos: 0

VSOL - OLT EPON FURACAO:
  - VSOLUTION

Ubiquiti - Switch JBS STA:
  - Switch Ubiquiti  

Mikrotik - CCR Escritorio STA:
  - Mikrotik

Huawei - Switch Santana Marajo:
  - Switch Huawei

... (mais 6 devices) ...
```

**✅ Resultado: 100% dos dispositivos importados com grupos corretos!**

---

### 4. Script de Limpeza

**Arquivo**: `backend/scripts/clear_devices.py`

Remove todos os devices e portas do banco, mantendo os grupos para nova importação.

---

## 🔄 Próximos Passos - Frontend

### Melhoria Necessária: Importação Automática de Grupos

O frontend precisa ser atualizado para suportar a importação e associação automática de grupos do Zabbix.

### Localização Provável

Baseado na estrutura do projeto, o modal de importação deve estar em:
- `frontend/src/components/` (componentes de importação)
- `frontend/src/views/` (views de gerenciamento de devices)

### Funcionalidades a Implementar

#### 1. Visualização de Grupos no Modal de Importação

**Antes** (atual):
```
[ ] Host 1 (192.168.1.1)
[ ] Host 2 (192.168.1.2)
```

**Depois** (melhorado):
```
📂 Switch Huawei
  [ ] Huawei - Switch Elagro (192.168.1.1)
  [ ] Huawei - Switch Santana (192.168.1.2)

📂 ZTE
  [ ] ZTE - OLT CONFRESA (192.168.2.1)
  [ ] ZTE - OLT MANDI (192.168.2.2)

📂 VSOLUTION
  [ ] VSOL - OLT EPON FURACAO (192.168.3.1)
```

#### 2. Seleção em Massa por Grupo

Adicionar checkbox no nome do grupo para selecionar/desmarcar todos os hosts do grupo:

```
[x] 📂 Switch Huawei (2 hosts)
    [x] Huawei - Switch Elagro (192.168.1.1)
    [x] Huawei - Switch Santana (192.168.1.2)
```

#### 3. Badge de Grupos em Cada Host

Mostrar visualmente a quais grupos cada host pertence:

```
[ ] Huawei - Switch Elagro (192.168.1.1)
    🏷️ Switch Huawei  🏷️ Network
```

#### 4. Filtro por Grupo

Adicionar filtro dropdown para exibir apenas hosts de grupos selecionados:

```
[Filtrar por grupo ▼]
  [ ] Todos
  [x] Switch Huawei
  [ ] ZTE
  [ ] VSOLUTION
```

#### 5. Importação com Preservação de Grupos

Ao importar, o frontend deve:
1. Chamar o endpoint de importação normalmente
2. O backend automaticamente associa os grupos (já implementado)
3. Mostrar confirmação com grupos associados:

```
✅ Importados 10 dispositivos
   - 3 em "Switch Huawei"
   - 4 em "ZTE"
   - 2 em "VSOLUTION"
   - 1 em "Network"
```

### Código de Exemplo (Vue 3)

```vue
<template>
  <div class="import-modal">
    <!-- Filtro por grupo -->
    <div class="group-filter">
      <select v-model="selectedGroupFilter" @change="filterByGroup">
        <option value="">Todos os grupos</option>
        <option v-for="group in availableGroups" :key="group.zabbix_group_id" :value="group.zabbix_group_id">
          {{ group.name }} ({{ group.hosts.length }})
        </option>
      </select>
    </div>

    <!-- Lista agrupada de hosts -->
    <div v-for="group in filteredGroups" :key="group.zabbix_group_id" class="group-section">
      <div class="group-header">
        <input 
          type="checkbox" 
          :checked="isGroupSelected(group)"
          @change="toggleGroup(group)"
        />
        <span class="group-icon">📂</span>
        <strong>{{ group.name }}</strong>
        <span class="group-count">({{ group.hosts.length }} hosts)</span>
      </div>

      <div class="group-hosts">
        <div v-for="host in group.hosts" :key="host.zabbix_id" class="host-item">
          <input 
            type="checkbox" 
            :value="host.zabbix_id"
            v-model="selectedHosts"
            :disabled="host.is_imported"
          />
          <span class="host-name">{{ host.name }}</span>
          <span class="host-ip">({{ host.ip }})</span>
          
          <!-- Badge de status -->
          <span v-if="host.is_imported" class="badge badge-success">Importado</span>
          <span v-else-if="host.has_drift" class="badge badge-warning">Mudanças detectadas</span>
          
          <!-- Badges de grupos -->
          <div class="host-groups">
            <span v-for="groupName in host.groups" :key="groupName" class="badge badge-group">
              🏷️ {{ groupName }}
            </span>
          </div>

          <!-- Drift info -->
          <div v-if="host.has_drift" class="drift-info">
            <small>Diferenças: {{ host.drift_fields.join(', ') }}</small>
          </div>
        </div>
      </div>
    </div>

    <!-- Botão de importar -->
    <div class="modal-actions">
      <button @click="importSelected" :disabled="selectedHosts.length === 0">
        Importar {{ selectedHosts.length }} dispositivo(s)
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useApi } from '@/composables/useApi'

const api = useApi()
const groups = ref([])
const selectedHosts = ref([])
const selectedGroupFilter = ref('')

// Buscar hosts agrupados do backend
onMounted(async () => {
  const response = await api.get('/api/v1/inventory/zabbix/lookup/hosts/grouped/')
  groups.value = response.data.data
})

// Filtrar grupos
const filteredGroups = computed(() => {
  if (!selectedGroupFilter.value) return groups.value
  return groups.value.filter(g => g.zabbix_group_id === selectedGroupFilter.value)
})

// Grupos disponíveis para filtro
const availableGroups = computed(() => groups.value)

// Verificar se grupo inteiro está selecionado
const isGroupSelected = (group) => {
  return group.hosts.every(h => selectedHosts.value.includes(h.zabbix_id))
}

// Toggle grupo inteiro
const toggleGroup = (group) => {
  const allSelected = isGroupSelected(group)
  if (allSelected) {
    // Desmarcar todos
    group.hosts.forEach(h => {
      const idx = selectedHosts.value.indexOf(h.zabbix_id)
      if (idx > -1) selectedHosts.value.splice(idx, 1)
    })
  } else {
    // Marcar todos (exceto já importados)
    group.hosts.forEach(h => {
      if (!h.is_imported && !selectedHosts.value.includes(h.zabbix_id)) {
        selectedHosts.value.push(h.zabbix_id)
      }
    })
  }
}

// Importar selecionados
const importSelected = async () => {
  try {
    const response = await api.post('/api/v1/inventory/devices/import/', {
      host_ids: selectedHosts.value,
      sync_groups: true  // Flag para sincronizar grupos automaticamente
    })
    
    // Mostrar resumo
    alert(`✅ ${response.data.imported_count} dispositivos importados com sucesso!`)
    
    // Recarregar lista
    const updated = await api.get('/api/v1/inventory/zabbix/lookup/hosts/grouped/')
    groups.value = updated.data.data
    selectedHosts.value = []
  } catch (error) {
    console.error('Erro ao importar:', error)
    alert('Erro ao importar dispositivos')
  }
}
</script>

<style scoped>
.group-section {
  margin-bottom: 1.5rem;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.group-header {
  background: #f5f5f5;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  cursor: pointer;
}

.group-hosts {
  padding: 8px 16px;
}

.host-item {
  padding: 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid #f0f0f0;
}

.host-item:last-child {
  border-bottom: none;
}

.host-groups {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-left: auto;
}

.badge-group {
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
}

.badge-success {
  background: #4caf50;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
}

.badge-warning {
  background: #ff9800;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
}

.drift-info {
  width: 100%;
  padding: 4px 0;
  color: #ff9800;
  font-size: 0.85rem;
}
</style>
```

---

## 📝 Checklist de Implementação Frontend

- [ ] Buscar componente/view de importação de devices
- [ ] Atualizar chamada API para usar `/api/v1/inventory/zabbix/lookup/hosts/grouped/`
- [ ] Adicionar estrutura de grupos colapsáveis/expansíveis
- [ ] Implementar checkbox de grupo para seleção em massa
- [ ] Adicionar badges de grupos em cada host
- [ ] Implementar filtro por grupo
- [ ] Adicionar indicador de `is_imported` e `has_drift`
- [ ] Passar flag `sync_groups: true` na importação
- [ ] Mostrar resumo de grupos após importação
- [ ] Adicionar testes para o componente

---

## 🧪 Teste Pós-Implementação

### 1. Limpar banco e reimportar
```bash
docker compose -f docker/docker-compose.yml exec web python scripts/clear_devices.py
docker compose -f docker/docker-compose.yml exec web python manage.py sync_zabbix_inventory --verbose
```

### 2. Verificar grupos no banco
```bash
docker compose -f docker/docker-compose.yml exec web python scripts/check_device_groups.py
```

### 3. Testar endpoint na web
- Acessar interface de importação
- Verificar se hosts estão agrupados corretamente
- Selecionar grupo inteiro e importar
- Confirmar que grupos foram associados aos devices

---

## 📌 Observações Importantes

1. **Grupos no Zabbix**: Os hosts DEVEM estar associados a grupos no Zabbix para que a sincronização funcione
2. **Sincronização automática**: O comando `sync_zabbix_inventory` agora sincroniza grupos automaticamente
3. **Drift detection**: O endpoint detecta quando há diferenças entre Zabbix e banco (nome, IP, grupos)
4. **Performance**: A consulta agrupa hosts no backend para reduzir carga no frontend

---

**Data da implementação**: 4 de março de 2026
**Status**: ✅ Backend completo | 🔄 Frontend pendente
