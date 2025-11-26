# Implementação do Botão "Ver Detalhes" - Modo Readonly

## Status Atual
✅ Botão "Ver Detalhes" existe na aba **Sincronização (Pré)**  
⏳ Falta: Modo readonly no `DeviceEditModal.vue`

---

## 1. Adicionar Prop `readOnly` ao DeviceEditModal

**Arquivo**: `frontend/src/components/DeviceImport/DeviceEditModal.vue`

### 1.1 Adicionar prop no `<script setup>`:

```javascript
const props = defineProps({
  devices: { type: Array, default: () => [] },
  device: { type: Object, default: null },
  isNew: { type: Boolean, default: false },
  readOnly: { type: Boolean, default: false }, // ← NOVO
  availableGroups: { type: Array, default: () => [] },
  availableSites: { type: Array, default: () => [] }
});
```

### 1.2 Atualizar título do modal:

```javascript
const modalTitle = computed(() => {
  if (props.readOnly) return 'Detalhes do Dispositivo';
  return isBatch.value 
    ? `Importação em Lote (${activeDevices.value.length} itens)` 
    : (props.isNew ? 'Classificar e Importar Dispositivo' : 'Editar Configurações');
});
```

---

## 2. Adicionar Conteúdo Readonly no Template

**Substituir** a seção `<!-- Content -->` quando `readOnly === true`:

```vue
<!-- Content -->
<div v-if="readOnly" class="px-6 py-6 space-y-6">
  
  <!-- Status de Sincronia -->
  <div class="bg-green-50 dark:bg-green-900/20 border-l-4 border-green-400 p-4 rounded-r">
    <div class="flex">
      <div class="flex-shrink-0">
        <i class="fas fa-check-circle text-green-500 text-2xl"></i>
      </div>
      <div class="ml-3">
        <h4 class="text-sm font-bold text-green-800 dark:text-green-300">
          Dispositivo Importado e Sincronizado
        </h4>
        <p class="text-sm text-green-700 dark:text-green-400 mt-1">
          Este equipamento está vinculado ao Zabbix e sendo monitorado.
          <span class="font-mono bg-green-100 dark:bg-green-800 px-2 py-0.5 rounded ml-2">
            ID: {{ activeDevices[0]?.zabbix_id }}
          </span>
        </p>
      </div>
    </div>
  </div>

  <!-- Comparativo Lado a Lado -->
  <div class="grid grid-cols-2 gap-4">
    
    <!-- Dados Atuais (Sistema) -->
    <div class="p-4 bg-gray-50 dark:bg-gray-700/50 rounded border border-gray-200 dark:border-gray-600">
      <h4 class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-3 flex items-center">
        <i class="fas fa-database mr-2 text-indigo-500"></i>
        Dados no Sistema
      </h4>
      <div class="space-y-2">
        <div>
          <p class="text-xs text-gray-500 dark:text-gray-400">Nome</p>
          <p class="font-bold text-gray-900 dark:text-white">{{ formState.name }}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 dark:text-gray-400">IP de Gerência</p>
          <p class="text-sm text-gray-700 dark:text-gray-300 font-mono">{{ formState.ip_address }}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 dark:text-gray-400">Grupo</p>
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 dark:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300">
            {{ formState.group || 'Sem grupo' }}
          </span>
        </div>
        <div>
          <p class="text-xs text-gray-500 dark:text-gray-400">Categoria</p>
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" 
            :class="{
              'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300': formState.category === 'backbone',
              'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300': formState.category === 'gpon',
              'bg-purple-100 dark:bg-purple-900/50 text-purple-800 dark:text-purple-300': formState.category === 'dwdm'
            }">
            {{ formState.category.toUpperCase() }}
          </span>
        </div>
      </div>
    </div>
    
    <!-- Ações Rápidas -->
    <div class="flex flex-col justify-center items-center border-2 border-dashed border-gray-300 dark:border-gray-600 rounded p-4 space-y-3">
      <i class="fas fa-tools text-gray-300 dark:text-gray-600 text-4xl mb-2"></i>
      <p class="text-sm text-gray-600 dark:text-gray-400 text-center">Ações disponíveis</p>
      
      <button 
        @click="openDashboard" 
        class="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none transition-colors"
      >
        <i class="fas fa-chart-line mr-2"></i> Abrir Dashboard
      </button>
      
      <button 
        @click="enableEditMode" 
        class="w-full inline-flex justify-center items-center px-4 py-2 border border-indigo-300 dark:border-indigo-600 rounded-md shadow-sm text-sm font-medium text-indigo-700 dark:text-indigo-400 bg-white dark:bg-gray-700 hover:bg-indigo-50 dark:hover:bg-gray-600 focus:outline-none transition-colors"
      >
        <i class="fas fa-edit mr-2"></i> Editar Configurações
      </button>
      
      <button 
        v-if="activeDevices[0]?.zabbix_id"
        @click="showInterfacesModal = true" 
        class="w-full inline-flex justify-center items-center px-4 py-2 border border-blue-300 dark:border-blue-600 rounded-md shadow-sm text-sm font-medium text-blue-700 dark:text-blue-400 bg-white dark:bg-gray-700 hover:bg-blue-50 dark:hover:bg-gray-600 focus:outline-none transition-colors"
      >
        <i class="fas fa-network-wired mr-2"></i> Ver Interfaces
      </button>
    </div>
  </div>

  <!-- Canais de Alerta Ativos -->
  <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
    <h4 class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-3">
      Canais de Alerta Configurados
    </h4>
    <div class="flex items-center gap-4">
      <div v-if="formState.alerts.screen" class="flex items-center text-sm text-gray-700 dark:text-gray-300">
        <i class="fas fa-desktop text-indigo-500 mr-2"></i>
        Dashboard Map
      </div>
      <div v-if="formState.alerts.whatsapp" class="flex items-center text-sm text-gray-700 dark:text-gray-300">
        <i class="fab fa-whatsapp text-green-500 mr-2"></i>
        WhatsApp Ops
      </div>
      <div v-if="!formState.alerts.screen && !formState.alerts.whatsapp" class="text-sm text-gray-500 dark:text-gray-400 italic">
        Nenhum canal de alerta configurado
      </div>
    </div>
  </div>
</div>

<!-- Conteúdo Editável (Original) - Apenas quando NÃO estiver em modo readonly -->
<div v-else class="px-6 py-6 space-y-8">
  <!-- ... todo o conteúdo original do modal ... -->
</div>
```

---

## 3. Adicionar Funções no Script

```javascript
// Função para abrir dashboard do dispositivo
const openDashboard = () => {
  const deviceId = activeDevices.value[0]?.id;
  if (deviceId) {
    // Abre em nova aba
    window.open(`/monitoring/device/${deviceId}`, '_blank');
  }
};

// Função para sair do modo readonly e entrar em edição
const enableEditMode = () => {
  // Emite evento para reabrir o modal em modo edição
  emit('close');
  nextTick(() => {
    emit('edit', activeDevices.value[0]);
  });
};
```

---

## 4. Atualizar Footer do Modal (Modo Readonly)

```vue
<!-- Footer Actions -->
<div class="bg-gray-50 dark:bg-gray-800 px-4 py-3 sm:px-6 border-t border-gray-200 dark:border-gray-700">
  <div v-if="readOnly" class="flex justify-end">
    <button 
      @click="$emit('close')"
      type="button" 
      class="inline-flex justify-center items-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none transition-colors"
    >
      <i class="fas fa-times mr-2"></i>
      Fechar
    </button>
  </div>
  
  <!-- Footer original para modo de edição -->
  <div v-else class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
    <!-- ... conteúdo original ... -->
  </div>
</div>
```

---

## 5. Integrar com ImportPreviewTab

**Arquivo**: `frontend/src/components/DeviceImport/ImportPreviewTab.vue`

### Modificar o botão "Ver Detalhes":

```vue
<button 
  @click="viewDeviceDetails(host)" 
  class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300 text-sm hover:underline"
>
  Ver Detalhes
</button>
```

### Adicionar função no script:

```javascript
// State para modal de detalhes
const showDetailsModal = ref(false);
const selectedDeviceForDetails = ref(null);

// Função para abrir modal em modo readonly
const viewDeviceDetails = (host) => {
  if (host.is_imported) {
    selectedDeviceForDetails.value = host;
    showDetailsModal.value = true;
  }
};
```

### Adicionar modal no template:

```vue
<!-- Modal de Detalhes (Readonly) -->
<DeviceEditModal
  v-if="showDetailsModal"
  :device="selectedDeviceForDetails"
  :read-only="true"
  :available-groups="[]"
  :available-sites="[]"
  @close="showDetailsModal = false"
/>
```

---

## 6. Resultado Esperado

### Quando clicar em "Ver Detalhes":

✅ Modal abre em **modo leitura**  
✅ Mostra **status de sincronia** (verde = OK)  
✅ Exibe **dados atuais** do sistema  
✅ Botões de **ação rápida**:
- **Abrir Dashboard**: Nova aba com monitoramento
- **Editar Configurações**: Sai do readonly e permite edição
- **Ver Interfaces**: Abre modal de interfaces com dados do Zabbix

---

## 7. Próximas Melhorias (Roadmap)

### A. Regras de Auto-Associação
- Botão "Configurar Regras" na aba Sincronização
- Regex patterns: `OLT.*` → GPON + Grupo "Huawei"
- Salvar regras no backend (tabela `ImportRule`)

### B. Detecção de Drift (Mudanças)
- Comparar dados Zabbix vs Sistema
- Status "Desatualizado" (laranja) se houver diferenças
- Botão "Sincronizar Alterações" para atualizar

### C. Lista de Ignorados (Blacklist)
- Botão "Ignorar" na lista
- Salvar IDs no `localStorage` ou backend
- Filtrar na aba "Sincronização"

### D. Teste de Conectividade
- Ping assíncrono antes de importar
- Indicador visual: 🟢 (OK) | 🔴 (Unreachable)
- Backend: endpoint `/api/v1/inventory/ping/{ip}/`

---

## 8. Comandos para Deploy

```powershell
# Compilar frontend
cd D:\provemaps_beta\frontend
npm run build

# Rebuild Docker
cd D:\provemaps_beta\docker
docker compose down
docker compose build --no-cache web
docker compose up -d
```

---

**Autor**: GitHub Copilot  
**Data**: 2025-11-23  
**Versão**: 1.0
