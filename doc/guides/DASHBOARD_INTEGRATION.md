# Guia de Integração - Dashboard Modernizado

## Como Integrar nos Seus Componentes

### 1. Importar Componentes

```javascript
// No seu componente Vue
import ModernDeviceList from '@/components/DeviceDashboard/ModernDeviceList.vue'
import DeviceDashboardModal from '@/components/DeviceDashboard/DeviceDashboardModal.vue'
```

### 2. Template Básico

```vue
<template>
  <div>
    <!-- Lista de Dispositivos -->
    <ModernDeviceList
      :devices="devices"
      @view-dashboard="openDashboard"
      @configure="openConfig"
    />

    <!-- Modal da Dashboard -->
    <DeviceDashboardModal
      :show="showDashboard"
      :device="selectedDevice"
      @close="showDashboard = false"
      @config-saved="handleConfigSaved"
    />
  </div>
</template>
```

### 3. Script Setup

```javascript
<script setup>
import { ref } from 'vue'

const devices = ref([])
const selectedDevice = ref(null)
const showDashboard = ref(false)

// Buscar dispositivos (exemplo)
const loadDevices = async () => {
  const response = await fetch('/api/v1/inventory/sites/1/devices/')
  const data = await response.json()
  devices.value = data.devices
}

// Abrir dashboard
const openDashboard = (device) => {
  selectedDevice.value = device
  showDashboard.value = true
}

// Configurar widget
const openConfig = (device) => {
  selectedDevice.value = device
  showDashboard.value = true
  // O modal detectará automaticamente que precisa abrir config
}

// Quando salvar configuração
const handleConfigSaved = (newConfig) => {
  console.log('Nova configuração salva:', newConfig)
  // Atualizar device local se necessário
}

onMounted(() => {
  loadDevices()
})
</script>
```

## Estrutura de Dados Esperada

### Device Object
```javascript
{
  id: 123,
  name: "SW-CORE-01",
  vendor: "Cisco",
  model: "Catalyst 9300",
  status: "online", // ou "offline"
  category: "backbone", // backbone|gpon|dwdm|access
  zabbix_hostid: "10084",
  dashboard_config: {
    layout: "grid",
    widgets: [
      { type: "gauge", metric: "cpu", title: "CPU", size: "small" }
    ]
  },
  metrics: {
    cpu: 45.2,
    memory: 67.8,
    uptime: 2592000
  },
  alert_count: 2
}
```

## API Endpoints Necessários

### 1. Listar Dispositivos de um Site
```
GET /api/v1/inventory/sites/<site_id>/devices/
```

Response:
```json
{
  "devices": [
    {
      "id": 123,
      "name": "SW-CORE-01",
      "vendor": "Cisco",
      "model": "Catalyst 9300",
      ...
    }
  ]
}
```

### 2. Buscar Métricas do Dispositivo
```
GET /api/v1/inventory/devices/<device_id>/dashboard-data/
```

Response: Veja doc/releases/DASHBOARD_MODERNIZATION.md

### 3. Salvar Configuração
```
POST /api/v1/inventory/devices/<device_id>/dashboard-config/
```

Body:
```json
{
  "layout": "grid",
  "widgets": [...]
}
```

## Exemplo Completo

Veja: `frontend/src/views/monitoring/SiteMonitoringView.vue`

Este exemplo mostra:
- ✅ Listagem de dispositivos com busca e filtros
- ✅ Estatísticas em tempo real (online, alertas)
- ✅ Abertura do dashboard ao clicar
- ✅ Auto-refresh a cada 30 segundos
- ✅ Loading de métricas em paralelo
- ✅ Tratamento de erros gracioso

## Customização

### Cores por Vendor

Edite em `ModernDeviceList.vue`:

```javascript
const getDeviceGradient = (vendor) => {
  const gradients = {
    'MeuVendor': 'linear-gradient(135deg, rgba(255, 0, 0, 0.2) 0%, rgba(255, 100, 100, 0.2) 100%)',
    // ...
  }
  return gradients[vendor] || 'default'
}
```

### Widgets Padrão

Edite em `DeviceDashboardModal.vue`:

```javascript
const getDefaultWidgets = () => {
  return [
    { id: 1, type: 'gauge', metric: 'cpu', title: 'CPU', size: 'small' },
    { id: 2, type: 'alerts', title: 'Alertas', size: 'medium' },
    // Adicione seus widgets aqui
  ]
}
```

### Criar Widget Personalizado

1. Crie arquivo em `components/DeviceDashboard/widgets/MeuWidget.vue`
2. Implemente props: `device`, `config`
3. Adicione auto-refresh se necessário
4. Registre em `DeviceDashboardModal.vue`:

```javascript
import MeuWidget from './widgets/MeuWidget.vue'

const getWidgetComponent = (type) => {
  const components = {
    // ...existentes
    'meu-widget': MeuWidget
  }
  return components[type]
}
```

5. Adicione opção em `DashboardConfigModal.vue`:

```javascript
const availableWidgets = [
  // ...existentes
  {
    type: 'meu-widget',
    name: 'Meu Widget',
    icon: '🎯',
    description: 'Descrição do widget',
    defaultConfig: {
      type: 'meu-widget',
      title: 'Título',
      size: 'medium'
    }
  }
]
```

## Troubleshooting

### Widgets não aparecem
- Verifique se `device.dashboard_config` existe
- Confirme que `device.id` está definido
- Abra console para ver erros de API

### Métricas sempre em 0
- Confirme `device.zabbix_hostid` configurado
- Verifique logs do backend para erros do Zabbix
- Teste API diretamente: `/api/v1/inventory/devices/123/dashboard-data/`

### Modal não abre
- Verifique `v-if` ou `:show` no template
- Confirme que `selectedDevice` não é null
- Cheque erros no console

### Configuração não salva
- Verifique CSRF token configurado
- Confirme permissões do usuário
- Veja resposta da API no Network tab

## Performance Tips

1. **Lazy Loading**: Carregue métricas só quando necessário
2. **Debounce Search**: Use debounce na busca para evitar chamadas excessivas
3. **Virtual Scrolling**: Para sites com 100+ devices, use virtual scroll
4. **Cache**: Implemente cache local para métricas com TTL de 30s

## Próximos Passos

1. Adicione WebSockets para updates em tempo real
2. Implemente export de dashboard em PDF
3. Crie templates de dashboard por tipo de device
4. Adicione drag & drop para reordenar widgets na grid

---

**Dúvidas?** Consulte `doc/releases/DASHBOARD_MODERNIZATION.md`
