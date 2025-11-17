# 🚀 Guia Rápido - Sistema Unificado de Mapas

## ⚡ TL;DR

**Problema:** Código de mapa duplicado em múltiplos componentes.  
**Solução:** Um único sistema com plugins modulares.  
**Resultado:** Cada contexto carrega apenas as ferramentas necessárias.

---

## 📦 O que foi criado?

### 1. Core System
| Arquivo | Descrição |
|---------|-----------|
| `composables/useMapService.js` | Gerencia Google Maps + carrega plugins |
| `components/Map/UnifiedMapView.vue` | Componente wrapper reutilizável |

### 2. Plugins Disponíveis
| Plugin | Uso | Funcionalidades |
|--------|-----|-----------------|
| `segments` | Monitoring | Desenha polylines de fibra coloridas por status |
| `devices` | Monitoring | Markers de devices com clustering opcional |
| `drawing` | Network Design | Ferramentas de desenho interativo de rotas |
| `contextMenu` | Network Design | Menu de contexto (right-click) customizável |

### 3. Documentação
| Arquivo | Conteúdo |
|---------|----------|
| `Map/README.md` | Documentação completa com exemplos |
| `Map/ARCHITECTURE.md` | Diagramas e decisões arquiteturais |
| `Map/USAGE_EXAMPLES.vue` | Exemplos de código funcionais |

### 4. Testes
| Arquivo | Tipo | Cobertura |
|---------|------|-----------|
| `tests/unit/useMapService.spec.js` | Unit | Core service + plugins |
| `tests/e2e/map-loading.spec.js` | E2E | Carregamento do mapa |

---

## 🎯 Como Usar - 3 Passos

### Passo 1: Escolha o Modo
```javascript
mode: 'monitoring'  // Dashboard/visualização
mode: 'design'      // Network design/desenho
mode: 'analysis'    // Análise de rede
```

### Passo 2: Selecione Plugins
```javascript
// Monitoring
:plugins="['segments', 'devices']"

// Network Design
:plugins="['drawing', 'contextMenu', 'segments']"

// Custom
:plugins="['segments']" // Apenas o necessário
```

### Passo 3: Configure Opções
```javascript
:plugin-options="{
  segments: { onSegmentClick: handleClick },
  devices: { enableClustering: true }
}"
```

---

## 💡 Exemplos Práticos

### Monitoring (Dashboard)
```vue
<template>
  <UnifiedMapView
    mode="monitoring"
    :plugins="['segments', 'devices']"
    @map-ready="loadData"
  />
</template>

<script setup>
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';

function loadData(map) {
  // Carregar e desenhar dados
}
</script>
```

### Network Design
```vue
<template>
  <UnifiedMapView
    ref="mapRef"
    mode="design"
    :plugins="['drawing', 'contextMenu']"
  >
    <template #controls>
      <button @click="startDrawing">✏️ Desenhar</button>
      <button @click="savePath">💾 Salvar</button>
    </template>
  </UnifiedMapView>
</template>

<script setup>
const mapRef = ref(null);

function startDrawing() {
  const plugin = mapRef.value.getPlugin('drawing');
  plugin.startDrawing();
}

function savePath() {
  const plugin = mapRef.value.getPlugin('drawing');
  const coords = plugin.getPathCoordinates();
  const distance = plugin.getDistanceKm();
  // Salvar no backend...
}
</script>
```

### Plugins Dinâmicos
```vue
<template>
  <div>
    <label><input type="checkbox" v-model="showSegments" /> Segmentos</label>
    <label><input type="checkbox" v-model="showDevices" /> Devices</label>
    
    <UnifiedMapView :plugins="activePlugins" />
  </div>
</template>

<script setup>
const showSegments = ref(true);
const showDevices = ref(true);

const activePlugins = computed(() => {
  const plugins = [];
  if (showSegments.value) plugins.push('segments');
  if (showDevices.value) plugins.push('devices');
  return plugins;
});
</script>
```

---

## 🔌 API Rápida dos Plugins

### Segments Plugin
```javascript
const plugin = mapRef.value.getPlugin('segments');

plugin.drawSegments([...]);  // Desenhar segmentos
plugin.clearSegments();      // Limpar
plugin.fitBounds();          // Ajustar zoom
console.log(plugin.count);   // Quantidade
```

### Devices Plugin
```javascript
const plugin = mapRef.value.getPlugin('devices');

plugin.drawDevices([...]);      // Desenhar devices
plugin.focusDevice(id, zoom);   // Focar em device
plugin.clearDevices();          // Limpar
console.log(plugin.allMarkers); // Array de markers
```

### Drawing Plugin
```javascript
const plugin = mapRef.value.getPlugin('drawing');

plugin.startDrawing();              // Iniciar desenho
plugin.stopDrawing();               // Parar desenho
plugin.addPoint({ lat, lng });      // Adicionar ponto
plugin.getPathCoordinates();        // Obter coordenadas
plugin.getDistanceKm();             // Distância em km
plugin.clearPath();                 // Limpar tudo
console.log(plugin.pointCount);     // Quantidade de pontos
console.log(plugin.isDrawing);      // true/false
```

### Context Menu Plugin
```javascript
const plugin = mapRef.value.getPlugin('contextMenu');

plugin.addMenuItem({
  id: 'action',
  label: '🎯 Ação',
  action: (data) => { /* ... */ }
});

plugin.removeMenuItem('action');
console.log(plugin.currentPosition); // LatLng do clique
```

---

## 📋 Checklist de Migração

### Para Dashboard/Monitoring
- [ ] Substituir `MapView.vue` por `UnifiedMapView`
- [ ] Usar `mode="monitoring"`
- [ ] Adicionar plugins: `['segments', 'devices']`
- [ ] Migrar handlers para `plugin-options`
- [ ] Testar carregamento de dados

### Para Network Design
- [ ] Substituir código de desenho manual
- [ ] Usar `mode="design"`
- [ ] Adicionar plugins: `['drawing', 'contextMenu']`
- [ ] Migrar toolbar para slot `#controls`
- [ ] Conectar eventos de save/load

---

## ⚠️ Pontos de Atenção

### 1. Inicialização
```javascript
// ❌ Usar plugin antes de map-ready
function loadData() {
  const plugin = mapRef.value.getPlugin('segments'); // undefined!
}

// ✅ Esperar map-ready
@map-ready="loadData"
function loadData() {
  const plugin = mapRef.value.getPlugin('segments'); // OK!
}
```

### 2. Cleanup
```javascript
// ✅ Cleanup automático no onUnmounted
// Mas pode fazer manual se necessário
onBeforeRouteLeave(() => {
  mapRef.value?.cleanup();
});
```

### 3. Performance
```javascript
// ❌ Carregar tudo sempre
:plugins="['segments', 'devices', 'drawing', 'contextMenu']"

// ✅ Carregar apenas o necessário
:plugins="mode === 'monitoring' ? ['segments', 'devices'] : ['drawing']"
```

---

## 🆘 Troubleshooting

### Problema: Mapa não carrega
```javascript
// Verificar console:
// - "Google Maps API failed to load" → Checar API key
// - "Map not initialized" → Aguardar @map-ready
// - Container não encontrado → Verificar ref
```

### Problema: Plugin não encontrado
```javascript
// Erro: Plugin "myPlugin" not found
// Solução: Registrar plugin primeiro

import { registerMapPlugin } from '@/composables/useMapService';
import createMyPlugin from './myPlugin';

registerMapPlugin('myPlugin', createMyPlugin);
```

### Problema: Dados não aparecem
```javascript
// Verificar ordem de execução:
@map-ready="onMapReady"      // 1. Mapa pronto
@plugin-loaded="onPluginLoaded" // 2. Plugin carregado
// Só então carregar dados:
function onPluginLoaded(name) {
  if (name === 'segments') {
    loadSegments();
  }
}
```

---

## 📚 Próximos Passos

1. **Ler Documentação Completa:** `Map/README.md`
2. **Ver Exemplos:** `Map/USAGE_EXAMPLES.vue`
3. **Entender Arquitetura:** `Map/ARCHITECTURE.md`
4. **Criar Plugin Customizado:** Seguir template em README
5. **Executar Testes:** `npm run test:unit` e `npm run test:e2e`

---

## 🤔 FAQ

**Q: Posso usar multiple plugins do mesmo tipo?**  
A: Não, cada plugin é singleton por mapa. Se precisar de múltiplos, crie instâncias de mapa diferentes.

**Q: Como passar dados entre plugins?**  
A: Via estado compartilhado (stores Pinia) ou eventos do componente pai.

**Q: Performance com muitos segmentos?**  
A: Use clustering no `devicesPlugin` e considere virtualização para grandes datasets.

**Q: Como debugar problemas?**  
A: Console logs estão em `[MapService]`, `[PluginName]` - filtrar por prefix.

**Q: Posso usar sem Vue Router?**  
A: Sim! UnifiedMapView é standalone, funciona em qualquer contexto Vue 3.

---

## 📞 Suporte

- **Documentação:** `frontend/src/components/Map/README.md`
- **Exemplos:** `frontend/src/components/Map/USAGE_EXAMPLES.vue`
- **Testes:** `frontend/tests/unit/useMapService.spec.js`
- **Issues:** Reportar no repositório do projeto

---

**Happy Mapping! 🗺️✨**
