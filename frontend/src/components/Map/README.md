# 🗺️ Sistema Unificado de Mapas - Arquitetura de Plugins

Sistema modular para Google Maps que permite reutilizar o mesmo componente base em diferentes contextos (monitoramento, network design, análise) carregando apenas as ferramentas necessárias via plugins.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Plugins Disponíveis](#plugins-disponíveis)
- [Como Usar](#como-usar)
- [Exemplos](#exemplos)
- [Criar Novos Plugins](#criar-novos-plugins)

---

## 🎯 Visão Geral

### Problema Anterior
Antes, tínhamos múltiplos componentes de mapa duplicando lógica:
- `MapView.vue` - Para dashboard/monitoring
- `NetworkDesignView.vue` - Para design de rotas
- Cada um com sua própria inicialização, gerenciamento de API, etc.

### Solução Atual
Um único sistema com:
- **`useMapService`** - Composable base que gerencia o Google Maps
- **Sistema de Plugins** - Carrega apenas ferramentas necessárias
- **`UnifiedMapView`** - Componente wrapper reutilizável

### Benefícios
✅ **DRY** - Sem duplicação de código
✅ **Modular** - Plugins independentes e testáveis
✅ **Performático** - Carrega apenas o necessário
✅ **Extensível** - Fácil adicionar novos plugins
✅ **Manutenível** - Mudanças em um lugar só

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────┐
│           UnifiedMapView.vue                    │
│  (Componente wrapper reutilizável)              │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│         useMapService.js                        │
│  (Composable - gerencia Google Maps)            │
│  - Inicialização do mapa                        │
│  - Carregamento de plugins                      │
│  - Lifecycle management                         │
└────────────┬────────────────────────────────────┘
             │
             ├──► Plugin Registry (global)
             │
             ▼
┌─────────────────────────────────────────────────┐
│              Plugins                            │
├─────────────────────────────────────────────────┤
│  segments       - Polylines de fibra            │
│  devices        - Markers de devices            │
│  drawing        - Ferramentas de desenho        │
│  contextMenu    - Menu right-click              │
│  [custom]       - Seus plugins customizados     │
└─────────────────────────────────────────────────┘
```

### Fluxo de Execução

```
1. Componente usa <UnifiedMapView mode="monitoring" :plugins="['segments', 'devices']" />
                        ↓
2. UnifiedMapView.vue inicializa useMapService({ mode: 'monitoring' })
                        ↓
3. useMapService.initMap() cria instância do Google Maps
                        ↓
4. useMapService.loadPlugin('segments', options) carrega plugin
                        ↓
5. Plugin é instanciado com contexto { map, google, mode }
                        ↓
6. Plugin retorna API pública (drawSegments, clearSegments, etc.)
                        ↓
7. Componente usa plugin via mapRef.getPlugin('segments')
```

---

## 🧩 Plugins Disponíveis

### 1. `segments` - Visualização de Segmentos de Fibra

**Uso:** Monitoring, Dashboard

**Funcionalidades:**
- Desenha polylines de cabos de fibra
- Cores baseadas em status (ok, warning, critical)
- Click/hover handlers
- InfoWindow com detalhes
- Fit bounds automático

**API:**
```javascript
const segmentsPlugin = mapRef.getPlugin('segments');

// Desenhar segmentos
segmentsPlugin.drawSegments([
  { id: 1, status: 'ok', geometry: { coordinates: [[lng, lat], ...] } },
  { id: 2, status: 'warning', path: [{ lat, lng }, ...] }
]);

// Limpar
segmentsPlugin.clearSegments();

// Ajustar zoom
segmentsPlugin.fitBounds();

// Contador
console.log(segmentsPlugin.count); // 2
```

**Opções:**
```javascript
{
  onSegmentClick: (segment, event) => { /* ... */ },
  onSegmentHover: (segment, event, isHover) => { /* ... */ }
}
```

---

### 2. `devices` - Markers de Dispositivos

**Uso:** Monitoring, Dashboard, Analysis

**Funcionalidades:**
- Markers customizados por tipo/status
- Clustering opcional (agrupa markers próximos)
- InfoWindow com detalhes do device
- Focus em device específico

**API:**
```javascript
const devicesPlugin = mapRef.getPlugin('devices');

// Desenhar devices
devicesPlugin.drawDevices([
  { id: 1, latitude: -15.78, longitude: -47.92, name: 'Router A', status: 'ok' },
  { id: 2, latitude: -15.79, longitude: -47.93, name: 'Switch B', status: 'warning' }
]);

// Focar em device
devicesPlugin.focusDevice(1, 16); // deviceId, zoom

// Limpar
devicesPlugin.clearDevices();

// Markers
console.log(devicesPlugin.allMarkers); // Array de google.maps.Marker
```

**Opções:**
```javascript
{
  onDeviceClick: (device, marker) => { /* ... */ },
  enableClustering: true,
  customIcon: (device) => ({
    url: `/icons/${device.type}.png`,
    scaledSize: { width: 32, height: 32 }
  })
}
```

---

### 3. `drawing` - Ferramentas de Desenho

**Uso:** Network Design, Route Planning

**Funcionalidades:**
- Click para adicionar pontos
- Markers arrastáveis
- Polyline dinâmica
- Cálculo de distância em tempo real
- Right-click para remover ponto

**API:**
```javascript
const drawingPlugin = mapRef.getPlugin('drawing');

// Iniciar desenho
drawingPlugin.startDrawing();

// Parar desenho
drawingPlugin.stopDrawing();

// Adicionar ponto programaticamente
drawingPlugin.addPoint({ lat: -15.78, lng: -47.92 });

// Remover ponto
drawingPlugin.removePoint(0); // índice

// Obter path
const coords = drawingPlugin.getPathCoordinates();
// [{ lat, lng }, { lat, lng }, ...]

// Distância
const distanceMeters = drawingPlugin.getDistance();
const distanceKm = drawingPlugin.getDistanceKm();

// Definir path completo
drawingPlugin.setPath([{ lat: -15.78, lng: -47.92 }, ...]);

// Limpar
drawingPlugin.clearPath();

// Estado
console.log(drawingPlugin.isDrawing); // true/false
console.log(drawingPlugin.pointCount); // 3
```

**Opções:**
```javascript
{
  editable: true,
  onPathChange: (coordinates, distance) => {
    console.log(`Path: ${coordinates.length} pontos, ${distance}m`);
  },
  onMarkerAdded: (index, position) => { /* ... */ },
  onMarkerMoved: (index, position) => { /* ... */ },
  onMarkerRemoved: (index) => { /* ... */ }
}
```

---

### 4. `contextMenu` - Menu de Contexto

**Uso:** Network Design, Advanced Tools

**Funcionalidades:**
- Right-click no mapa abre menu
- Items customizáveis
- Callbacks de ação
- Auto-posicionamento (não sai da tela)

**API:**
```javascript
const menuPlugin = mapRef.getPlugin('contextMenu');

// Adicionar item
menuPlugin.addMenuItem({
  id: 'my-action',
  label: '🎯 Minha Ação',
  action: ({ latLng, position }) => {
    console.log('Clicou em', latLng);
  }
});

// Remover item
menuPlugin.removeMenuItem('my-action');

// Posição atual do clique
console.log(menuPlugin.currentPosition); // google.maps.LatLng
```

**Opções:**
```javascript
{
  menuItems: [
    { id: 'save', label: '💾 Salvar', action: (data) => { /* ... */ } },
    { separator: true },
    { id: 'delete', label: '🗑️ Deletar', action: (data) => { /* ... */ } }
  ],
  onItemClick: (itemId, data) => {
    console.log(`Item ${itemId} clicado`, data);
  }
}
```

---

## 🚀 Como Usar

### 1. Básico - Monitoring

```vue
<template>
  <UnifiedMapView
    mode="monitoring"
    :plugins="['segments', 'devices']"
    :plugin-options="pluginOptions"
    @map-ready="onMapReady"
  />
</template>

<script setup>
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';

const pluginOptions = {
  segments: {
    onSegmentClick: (segment) => console.log(segment)
  },
  devices: {
    enableClustering: true
  }
};

function onMapReady(map) {
  console.log('Mapa pronto!', map);
}
</script>
```

### 2. Network Design

```vue
<template>
  <UnifiedMapView
    ref="mapRef"
    mode="design"
    :plugins="['drawing', 'contextMenu', 'segments']"
    :plugin-options="pluginOptions"
    @plugin-loaded="onPluginLoaded"
  >
    <template #controls>
      <button @click="startDrawing">✏️ Desenhar</button>
      <button @click="savePath">💾 Salvar</button>
    </template>
  </UnifiedMapView>
</template>

<script setup>
import { ref } from 'vue';
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';

const mapRef = ref(null);

const pluginOptions = {
  drawing: {
    onPathChange: (coords, distance) => {
      console.log(`${coords.length} pontos, ${distance / 1000} km`);
    }
  },
  contextMenu: {
    menuItems: [
      { id: 'save', label: '💾 Salvar Rota', action: savePath },
      { id: 'clear', label: '🗑️ Limpar', action: clearPath }
    ]
  }
};

function onPluginLoaded(pluginName) {
  console.log(`Plugin ${pluginName} carregado`);
}

function startDrawing() {
  const plugin = mapRef.value.getPlugin('drawing');
  plugin.startDrawing();
}

function savePath() {
  const plugin = mapRef.value.getPlugin('drawing');
  const coords = plugin.getPathCoordinates();
  // Salvar no backend...
}

function clearPath() {
  const plugin = mapRef.value.getPlugin('drawing');
  plugin.clearPath();
}
</script>
```

### 3. Plugins Dinâmicos

```vue
<template>
  <div>
    <!-- Controles -->
    <label>
      <input type="checkbox" v-model="showSegments" />
      Mostrar Segmentos
    </label>
    <label>
      <input type="checkbox" v-model="showDevices" />
      Mostrar Devices
    </label>

    <!-- Mapa com plugins dinâmicos -->
    <UnifiedMapView
      mode="monitoring"
      :plugins="activePlugins"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';

const showSegments = ref(true);
const showDevices = ref(true);

// Plugins são carregados/removidos automaticamente
const activePlugins = computed(() => {
  const plugins = [];
  if (showSegments.value) plugins.push('segments');
  if (showDevices.value) plugins.push('devices');
  return plugins;
});
</script>
```

---

## 🛠️ Criar Novos Plugins

### Template Base

```javascript
// composables/mapPlugins/myPlugin.js

export default function createMyPlugin(context, options = {}) {
  const { map, google, mode } = context;
  const { option1, onEvent } = options;

  // Estado interno do plugin
  let internalState = null;

  /**
   * Inicialização (opcional)
   */
  function init() {
    console.log('[MyPlugin] Initializing');
    // Setup listeners, etc.
  }

  /**
   * Método público 1
   */
  function publicMethod1(arg) {
    // Implementação
  }

  /**
   * Método público 2
   */
  function publicMethod2(arg) {
    // Implementação
  }

  /**
   * Cleanup obrigatório
   */
  function cleanup() {
    console.log('[MyPlugin] Cleaning up');
    // Remover listeners, limpar estado, etc.
  }

  // Auto-init se necessário
  init();

  // API pública do plugin
  return {
    publicMethod1,
    publicMethod2,
    cleanup,
    // Getters
    get someProperty() {
      return internalState;
    }
  };
}
```

### Registrar Plugin

```javascript
// composables/mapPlugins/index.js

import { registerMapPlugin } from '@/composables/useMapService';
import createMyPlugin from './myPlugin';

registerMapPlugin('myPlugin', createMyPlugin);
```

### Usar Plugin

```vue
<UnifiedMapView
  :plugins="['myPlugin']"
  :plugin-options="{
    myPlugin: {
      option1: 'value',
      onEvent: (data) => console.log(data)
    }
  }"
/>
```

---

## 📁 Estrutura de Arquivos

```
frontend/src/
├── composables/
│   ├── useMapService.js          # Composable base
│   └── mapPlugins/
│       ├── index.js              # Registry de plugins
│       ├── segmentsPlugin.js     # Plugin de segmentos
│       ├── devicesPlugin.js      # Plugin de devices
│       ├── drawingPlugin.js      # Plugin de desenho
│       └── contextMenuPlugin.js  # Plugin de menu
│
└── components/
    └── Map/
        ├── UnifiedMapView.vue    # Componente wrapper
        └── USAGE_EXAMPLES.vue    # Exemplos de uso
```

---

## 🧪 Testes

### Testar Plugin Isoladamente

```javascript
// tests/mapPlugins/segmentsPlugin.spec.js

import { describe, it, expect, vi } from 'vitest';
import createSegmentsPlugin from '@/composables/mapPlugins/segmentsPlugin';

describe('SegmentsPlugin', () => {
  it('should draw segments', () => {
    const mockMap = {};
    const mockGoogle = {
      maps: {
        Polyline: vi.fn(),
        InfoWindow: vi.fn()
      }
    };

    const plugin = createSegmentsPlugin(
      { map: mockMap, google: mockGoogle },
      {}
    );

    plugin.drawSegments([
      { id: 1, status: 'ok', path: [{ lat: 0, lng: 0 }] }
    ]);

    expect(plugin.count).toBe(1);
  });
});
```

---

## 🎓 Melhores Práticas

### 1. Escolha os Plugins Certos

```javascript
// ❌ Não carregar tudo sempre
:plugins="['segments', 'devices', 'drawing', 'contextMenu']"

// ✅ Carregar apenas o necessário
:plugins="mode === 'monitoring' ? ['segments', 'devices'] : ['drawing']"
```

### 2. Use Opções para Customizar

```javascript
// ✅ Opções específicas por contexto
const pluginOptions = computed(() => ({
  devices: {
    enableClustering: deviceCount.value > 100,
    customIcon: isDarkMode.value ? darkIcon : lightIcon
  }
}));
```

### 3. Cleanup Automático

```javascript
// ✅ Plugins são limpos automaticamente no onUnmounted
// Mas você pode fazer cleanup manual se necessário
onBeforeRouteLeave(() => {
  mapRef.value?.cleanup();
});
```

### 4. Error Handling

```vue
<UnifiedMapView
  @error="handleMapError"
>
```

```javascript
function handleMapError(error) {
  console.error('Map error:', error);
  // Mostrar mensagem ao usuário
}
```

---

## 📚 Referências

- [Google Maps JavaScript API](https://developers.google.com/maps/documentation/javascript)
- [Vue 3 Composables](https://vuejs.org/guide/reusability/composables.html)
- [Plugin Architecture Pattern](https://medium.com/js-dojo/plugin-architecture-in-javascript)

---

## 🤝 Contribuindo

Para adicionar um novo plugin:

1. Crie arquivo em `composables/mapPlugins/meuPlugin.js`
2. Siga o template base
3. Registre em `mapPlugins/index.js`
4. Adicione testes em `tests/mapPlugins/`
5. Documente no README
6. Adicione exemplo de uso em `USAGE_EXAMPLES.vue`

---

## 📝 Changelog

### v1.0.0 (2025-11-17)
- ✨ Sistema unificado de mapas
- ✨ 4 plugins iniciais (segments, devices, drawing, contextMenu)
- 📚 Documentação completa
- 🧪 Testes E2E

---

**Autor:** Maps Prove Fiber Team
**Licença:** Proprietário
