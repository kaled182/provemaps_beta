# Plano de Refatoração - Componentes Gigantes

**Status**: 🟡 Planejamento  
**Início**: 26/01/2026  
**Responsável**: Equipe Dev  
**Prioridade**: ALTA

---

## 📊 Diagnóstico Atual

### Arquivos Críticos (> 2000 linhas)

| Arquivo | Linhas | Tamanho | Problemas Identificados |
|---------|--------|---------|------------------------|
| `ConfigurationPage.vue` | 3854 | 185KB | Múltiplos gateways misturados, lógica duplicada |
| `SiteDetailsModal.vue` | 2757 | 74KB | 4 responsabilidades (info, fibras, devices, câmeras) |
| `CustomMapViewer.vue` | 2251 | 70KB | Lógica de mapa + interações + modals entrelaçados |
| `MapView.vue` | 1943 | 55KB | Gerenciamento de estado complexo, múltiplas camadas |
| `FiberCableDetailModal.vue` | 1888 | 51KB | Lógica de portas + segmentos + ações misturadas |

### Riscos Identificados

🔴 **Alto Risco**
- Dificuldade de manutenção (mudanças em cascata)
- Bugs difíceis de rastrear
- Tempo de build aumentado
- Code review complexo
- Conflitos de merge frequentes

🟡 **Médio Risco**
- Performance degradada (componentes pesados)
- Reusabilidade limitada
- Testes impossíveis de escrever

---

## 🎯 Estratégia Geral

### Princípios da Refatoração

1. **Incremental**: Nunca quebrar produção
2. **Testável**: Cada mudança deve ser testada isoladamente
3. **Reversível**: Manter código antigo até confirmação
4. **Documentada**: Registrar todas as mudanças
5. **Comunicada**: Avisar equipe sobre refatorações em andamento

### Padrões a Seguir

**Composables** (Lógica Reutilizável)
```javascript
// composables/useSiteData.js
export function useSiteData(siteId) {
  const site = ref(null)
  const loading = ref(false)
  const error = ref(null)
  
  async function fetchSite() {
    loading.value = true
    error.value = null
    try {
      site.value = await api.get(`/api/v1/sites/${siteId}/`)
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }
  
  return { site, loading, error, fetchSite }
}
```

**Sub-componentes** (UI Modular)
```vue
<!-- components/Site/SiteCamerasTab.vue -->
<template>
  <div class="cameras-tab">
    <CameraPlayer 
      v-for="camera in cameras" 
      :key="camera.id"
      :camera="camera"
    />
  </div>
</template>

<script setup>
import { useSiteCameras } from '@/composables/useSiteCameras'

const props = defineProps(['siteId'])
const { cameras, startStreams } = useSiteCameras(props.siteId)

onMounted(() => startStreams())
</script>
```

---

## 📅 Fase 1: SiteDetailsModal.vue (Semana 1-2)

### Objetivo
Reduzir de **2757 → 600 linhas** extraindo responsabilidades

### Arquitetura Alvo

```
frontend/src/
├── components/
│   ├── SiteDetailsModal.vue (orchestrator - 600 linhas)
│   └── Site/
│       ├── SiteInfoTab.vue (informações básicas - 150 linhas)
│       ├── SiteFibersTab.vue (lista fibras - 200 linhas)
│       ├── SiteDevicesTab.vue (lista dispositivos - 200 linhas)
│       ├── SiteCamerasTab.vue (câmeras + mosaico - 250 linhas)
│       └── SiteCameraPlayer.vue (player individual - 100 linhas)
├── composables/
│   ├── useSiteData.js (fetch site info - 80 linhas)
│   ├── useSiteFibers.js (lógica fibras - 100 linhas)
│   ├── useSiteDevices.js (lógica devices - 100 linhas)
│   └── useSiteCameras.js (lógica câmeras/mosaicos - 200 linhas)
└── stores/
    └── siteModal.js (Pinia store - estado global - 150 linhas)
```

### Passo 1.1: Criar Composables (2 dias)

**Arquivo**: `frontend/src/composables/useSiteCameras.js`

```javascript
import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'

export function useSiteCameras(siteId) {
  const api = useApi()
  
  // Estado
  const mosaics = ref([])
  const currentMosaic = ref(null)
  const mosaicCameras = ref([])
  const loading = ref(false)
  const error = ref(null)
  
  // Computed
  const hasCameras = computed(() => mosaicCameras.value.length > 0)
  
  // Métodos
  async function fetchMosaics() {
    if (!siteId.value) return
    loading.value = true
    try {
      const response = await api.get(`/setup_app/video/api/mosaics/?site_id=${siteId.value}`)
      mosaics.value = response.results || []
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }
  
  async function loadMosaic(mosaicId) {
    const mosaic = await api.get(`/setup_app/video/api/mosaics/${mosaicId}/`)
    currentMosaic.value = mosaic
    
    // Enriquecer câmeras
    const cameraIds = mosaic.cameras.map(c => c.id)
    const camerasData = await Promise.all(
      cameraIds.map(id => api.get(`/setup_app/video/api/cameras/${id}/`).catch(() => null))
    )
    
    mosaicCameras.value = mosaic.cameras.map((cam, idx) => ({
      ...cam,
      ...(camerasData[idx] || {}),
      playback_url: null
    }))
  }
  
  async function startStreams() {
    const promises = mosaicCameras.value
      .filter(cam => cam.id)
      .map(async (camera) => {
        try {
          const response = await api.post(
            `/setup_app/api/gateways/${camera.id}/video/preview/start/`
          )
          if (response?.success && response.playback_url) {
            camera.playback_url = response.playback_proxy_url || response.playback_url
            return { success: true, camera }
          }
        } catch (error) {
          console.error(`Erro ao iniciar stream: ${camera.name}`, error)
          return { success: false, camera }
        }
      })
    
    await Promise.all(promises)
  }
  
  async function stopStreams() {
    const promises = mosaicCameras.value
      .filter(cam => cam.id)
      .map(camera => 
        api.post(`/setup_app/api/gateways/${camera.id}/video/preview/stop/`)
          .catch(e => console.warn(`Falha ao parar stream: ${camera.name}`, e))
      )
    
    await Promise.all(promises)
    mosaicCameras.value = []
    currentMosaic.value = null
  }
  
  return {
    // Estado
    mosaics,
    currentMosaic,
    mosaicCameras,
    loading,
    error,
    
    // Computed
    hasCameras,
    
    // Métodos
    fetchMosaics,
    loadMosaic,
    startStreams,
    stopStreams
  }
}
```

**✅ Checklist de Testes - useSiteCameras.js**
- [ ] Teste: `fetchMosaics()` retorna lista de mosaicos
- [ ] Teste: `loadMosaic()` enriquece câmeras com dados da API
- [ ] Teste: `startStreams()` processa em paralelo
- [ ] Teste: `stopStreams()` limpa estado corretamente
- [ ] Teste: `hasCameras` retorna `true` quando há câmeras
- [ ] Teste: Erro na API é capturado em `error.value`

### Passo 1.2: Criar SiteCamerasTab.vue (1 dia)

**Arquivo**: `frontend/src/components/Site/SiteCamerasTab.vue`

```vue
<template>
  <div class="site-cameras-tab">
    <!-- Lista de Mosaicos -->
    <div v-if="!currentMosaic" class="mosaic-list">
      <h3>Mosaicos Disponíveis</h3>
      <button 
        v-for="mosaic in mosaics" 
        :key="mosaic.id"
        @click="openMosaic(mosaic.id)"
        class="mosaic-card"
      >
        {{ mosaic.name }}
      </button>
    </div>
    
    <!-- Viewer do Mosaico -->
    <div v-else class="mosaic-viewer">
      <div class="mosaic-header">
        <h3>{{ currentMosaic.name }}</h3>
        <button @click="closeMosaic">Voltar</button>
      </div>
      
      <div class="cameras-grid">
        <CameraPlayer 
          v-for="camera in mosaicCameras"
          :key="camera.id"
          :camera="camera"
          :autoplay="true"
          :muted="true"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useSiteCameras } from '@/composables/useSiteCameras'
import CameraPlayer from '@/components/Video/CameraPlayer.vue'

const props = defineProps({
  siteId: { type: Number, required: true }
})

const {
  mosaics,
  currentMosaic,
  mosaicCameras,
  loading,
  fetchMosaics,
  loadMosaic,
  startStreams,
  stopStreams
} = useSiteCameras(props.siteId)

async function openMosaic(mosaicId) {
  await loadMosaic(mosaicId)
  await startStreams()
}

function closeMosaic() {
  stopStreams()
}

onMounted(() => {
  fetchMosaics()
})
</script>
```

**✅ Checklist de Testes - SiteCamerasTab.vue**
- [ ] Teste: Componente renderiza lista de mosaicos
- [ ] Teste: Clicar em mosaico carrega câmeras
- [ ] Teste: CameraPlayer recebe props corretos
- [ ] Teste: Botão "Voltar" limpa estado
- [ ] Teste: Streams são iniciados ao abrir mosaico
- [ ] Teste: Streams são parados ao fechar

### Passo 1.3: Integrar no SiteDetailsModal.vue (1 dia)

**Arquivo**: `frontend/src/components/SiteDetailsModal.vue` (versão refatorada)

```vue
<template>
  <Teleport to="body">
    <div v-if="show" class="modal-overlay" @click.self="close">
      <div class="modal-content">
        <!-- Tabs -->
        <div class="tabs">
          <button @click="activeTab = 'info'">Informações</button>
          <button @click="activeTab = 'fibers'">Fibras</button>
          <button @click="activeTab = 'devices'">Dispositivos</button>
          <button @click="activeTab = 'cameras'">Câmeras</button>
        </div>
        
        <!-- Tab Content -->
        <SiteInfoTab v-if="activeTab === 'info'" :site-id="siteId" />
        <SiteFibersTab v-if="activeTab === 'fibers'" :site-id="siteId" />
        <SiteDevicesTab v-if="activeTab === 'devices'" :site-id="siteId" />
        <SiteCamerasTab v-if="activeTab === 'cameras'" :site-id="siteId" />
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import SiteInfoTab from './Site/SiteInfoTab.vue'
import SiteFibersTab from './Site/SiteFibersTab.vue'
import SiteDevicesTab from './Site/SiteDevicesTab.vue'
import SiteCamerasTab from './Site/SiteCamerasTab.vue'

const props = defineProps({
  siteId: { type: Number, required: true }
})

const emit = defineEmits(['close'])

const show = ref(false)
const activeTab = ref('info')

function open() {
  show.value = true
}

function close() {
  show.value = false
  emit('close')
}

defineExpose({ open, close })
</script>
```

**✅ Checklist de Testes - SiteDetailsModal.vue Refatorado**
- [ ] Teste E2E: Modal abre corretamente
- [ ] Teste E2E: Navegação entre tabs funciona
- [ ] Teste E2E: Tab de câmeras carrega mosaicos
- [ ] Teste E2E: Fechar modal limpa estado
- [ ] Teste Regressão: Todas funções antigas funcionam
- [ ] Teste Performance: Tempo de renderização < 500ms

### Passo 1.4: Validação e Rollback (1 dia)

**Critérios de Sucesso**
- ✅ Todas tabs funcionam corretamente
- ✅ Câmeras carregam sem erros
- ✅ Performance igual ou melhor
- ✅ Zero regressões em funcionalidades existentes
- ✅ Code review aprovado
- ✅ Testes automatizados passando

**Plano de Rollback**
1. Manter `SiteDetailsModal.vue.backup` com código original
2. Feature flag `REFACTORED_SITE_MODAL=false` em desenvolvimento
3. Se bugs críticos aparecerem, reverter commit específico
4. Monitorar por 3 dias em staging antes de produção

---

## 📅 Fase 2: ConfigurationPage.vue (Semana 3-4)

### Objetivo
Reduzir de **3854 → 800 linhas** separando gateways

### Arquitetura Alvo

```
frontend/src/
├── views/
│   └── ConfigurationPage.vue (layout - 300 linhas)
├── components/
│   └── Gateway/
│       ├── GatewaySelector.vue (escolher tipo - 100 linhas)
│       ├── GatewaySMS.vue (200 linhas)
│       ├── GatewayWhatsApp.vue (250 linhas)
│       ├── GatewayTelegram.vue (200 linhas)
│       ├── GatewayVideo.vue (300 linhas)
│       │   └── VideoPreviewPanel.vue (150 linhas)
│       └── GatewaySMTP.vue (200 linhas)
└── composables/
    ├── useGatewayConfig.js (lógica comum - 150 linhas)
    └── useVideoPreview.js (específico vídeo - 200 linhas)
```

### Passo 2.1: Extrair useVideoPreview.js (1 dia)

**Arquivo**: `frontend/src/composables/useVideoPreview.js`

```javascript
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export function useVideoPreview(gatewayId) {
  const api = useApi()
  
  const videoPreview = ref({
    url: '',
    loading: false,
    status: 'idle',
    error: ''
  })
  
  async function startPreview() {
    if (!gatewayId.value) return
    
    videoPreview.value.loading = true
    videoPreview.value.status = 'loading'
    videoPreview.value.error = ''
    
    try {
      const response = await api.post(
        `/setup_app/api/gateways/${gatewayId.value}/video/preview/start/`
      )
      
      if (!response?.success) {
        videoPreview.value.status = 'error'
        videoPreview.value.error = response?.message || 'Falha ao iniciar'
        return
      }
      
      const playbackUrl = response.playback_proxy_url || response.playback_url
      
      if (!playbackUrl) {
        videoPreview.value.status = 'error'
        videoPreview.value.error = 'Backend não retornou URL'
        return
      }
      
      videoPreview.value.url = playbackUrl
      videoPreview.value.status = 'ready'
      
    } catch (error) {
      videoPreview.value.status = 'error'
      videoPreview.value.error = error.message
    } finally {
      videoPreview.value.loading = false
    }
  }
  
  async function stopPreview() {
    if (!gatewayId.value) return
    
    try {
      await api.post(
        `/setup_app/api/gateways/${gatewayId.value}/video/preview/stop/`
      )
    } catch (error) {
      console.warn('Erro ao parar preview:', error)
    } finally {
      videoPreview.value.url = ''
      videoPreview.value.status = 'idle'
    }
  }
  
  return {
    videoPreview,
    startPreview,
    stopPreview
  }
}
```

**✅ Checklist de Testes - useVideoPreview.js**
- [ ] Teste: `startPreview()` chama API corretamente
- [ ] Teste: `playback_proxy_url` tem prioridade sobre `playback_url`
- [ ] Teste: Erros da API são capturados em `error`
- [ ] Teste: `stopPreview()` limpa estado
- [ ] Teste: Estados (`idle`, `loading`, `ready`, `error`) funcionam

### Passo 2.2: Criar GatewayVideo.vue (2 dias)

**Arquivo**: `frontend/src/components/Gateway/GatewayVideo.vue`

```vue
<template>
  <div class="gateway-video">
    <h3>Gateway de Vídeo</h3>
    
    <!-- Formulário -->
    <form @submit.prevent="saveGateway">
      <input v-model="form.name" placeholder="Nome" />
      <select v-model="form.config.stream_type">
        <option value="rtmp">RTMP</option>
        <option value="rtsp">RTSP</option>
      </select>
      <input v-model="form.config.stream_url" placeholder="URL do Stream" />
      
      <button type="submit">Salvar</button>
    </form>
    
    <!-- Pré-visualização -->
    <VideoPreviewPanel 
      v-if="form.id"
      :gateway-id="form.id"
      :stream-url="form.config.stream_url"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import VideoPreviewPanel from './VideoPreviewPanel.vue'

const props = defineProps({
  gateway: { type: Object, default: null }
})

const emit = defineEmits(['saved'])

const api = useApi()
const form = ref({
  id: props.gateway?.id || null,
  name: props.gateway?.name || '',
  config: {
    stream_type: props.gateway?.config?.stream_type || 'rtmp',
    stream_url: props.gateway?.config?.stream_url || ''
  }
})

async function saveGateway() {
  const response = await api.post('/setup_app/api/gateways/', form.value)
  form.value.id = response.id
  emit('saved', response)
}
</script>
```

**✅ Checklist de Testes - GatewayVideo.vue**
- [ ] Teste: Formulário renderiza corretamente
- [ ] Teste: Salvar gateway cria/atualiza no backend
- [ ] Teste: VideoPreviewPanel recebe props corretos
- [ ] Teste: Emit 'saved' dispara ao salvar
- [ ] Teste: Validação de campos obrigatórios

### Passo 2.3: Integrar em ConfigurationPage.vue (1 dia)

**Arquivo**: `frontend/src/views/ConfigurationPage.vue` (refatorado)

```vue
<template>
  <div class="configuration-page">
    <h1>Configurações</h1>
    
    <!-- Seletor de Gateway -->
    <GatewaySelector v-model="activeGateway" />
    
    <!-- Gateway Components -->
    <component 
      :is="gatewayComponents[activeGateway]"
      :gateway="currentGateway"
      @saved="handleSaved"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import GatewaySelector from '@/components/Gateway/GatewaySelector.vue'
import GatewaySMS from '@/components/Gateway/GatewaySMS.vue'
import GatewayWhatsApp from '@/components/Gateway/GatewayWhatsApp.vue'
import GatewayTelegram from '@/components/Gateway/GatewayTelegram.vue'
import GatewayVideo from '@/components/Gateway/GatewayVideo.vue'
import GatewaySMTP from '@/components/Gateway/GatewaySMTP.vue'

const activeGateway = ref('video')
const currentGateway = ref(null)

const gatewayComponents = {
  sms: GatewaySMS,
  whatsapp: GatewayWhatsApp,
  telegram: GatewayTelegram,
  video: GatewayVideo,
  smtp: GatewaySMTP
}

function handleSaved(gateway) {
  currentGateway.value = gateway
}
</script>
```

**✅ Checklist de Testes - ConfigurationPage.vue Refatorado**
- [ ] Teste E2E: Troca entre tipos de gateway funciona
- [ ] Teste E2E: Salvar gateway persiste dados
- [ ] Teste E2E: Pré-visualização de vídeo funciona
- [ ] Teste Regressão: SMS/WhatsApp/Telegram/SMTP funcionam
- [ ] Teste Performance: Lazy loading de componentes

---

## 📅 Fase 3: MapView.vue + CustomMapViewer.vue (Semana 5-6)

### Objetivo
Reduzir `MapView.vue` (1943 → 800 linhas) + `CustomMapViewer.vue` (2251 → 900 linhas)

### Arquitetura Alvo

```
frontend/src/
├── views/
│   ├── MapView.vue (orchestrator - 800 linhas)
│   └── CustomMapViewer.vue (orchestrator - 900 linhas)
├── components/Map/
│   ├── MapControls.vue (zoom, layers - 150 linhas)
│   ├── MapLegend.vue (100 linhas)
│   ├── MapMarkerCluster.vue (200 linhas)
│   ├── MapSiteMarker.vue (150 linhas)
│   └── MapRoutePolyline.vue (150 linhas)
└── composables/
    ├── useMapData.js (fetch sites/devices/cables - 200 linhas)
    ├── useMapLayers.js (gerenciar camadas - 150 linhas)
    └── useMapInteractions.js (clicks, hovers - 200 linhas)
```

### Passo 3.1: Criar useMapData.js (2 dias)

**Arquivo**: `frontend/src/composables/useMapData.js`

```javascript
import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'

export function useMapData() {
  const api = useApi()
  
  // Estado
  const sites = ref([])
  const devices = ref([])
  const cables = ref([])
  const loading = ref(false)
  
  // Computed
  const sitesWithDevices = computed(() => {
    return sites.value.filter(site => 
      devices.value.some(dev => dev.site_id === site.id)
    )
  })
  
  const cablesGeoJSON = computed(() => ({
    type: 'FeatureCollection',
    features: cables.value.map(cable => ({
      type: 'Feature',
      geometry: cable.geometry,
      properties: { id: cable.id, name: cable.name, status: cable.status }
    }))
  }))
  
  // Métodos
  async function fetchAll() {
    loading.value = true
    try {
      const [sitesRes, devicesRes, cablesRes] = await Promise.all([
        api.get('/api/v1/sites/'),
        api.get('/api/v1/devices/'),
        api.get('/api/v1/cables/')
      ])
      
      sites.value = sitesRes.results || []
      devices.value = devicesRes.results || []
      cables.value = cablesRes.results || []
    } catch (error) {
      console.error('Erro ao carregar dados do mapa:', error)
    } finally {
      loading.value = false
    }
  }
  
  async function refreshSites() {
    const response = await api.get('/api/v1/sites/')
    sites.value = response.results || []
  }
  
  return {
    sites,
    devices,
    cables,
    loading,
    sitesWithDevices,
    cablesGeoJSON,
    fetchAll,
    refreshSites
  }
}
```

**✅ Checklist de Testes - useMapData.js**
- [ ] Teste: `fetchAll()` carrega dados em paralelo
- [ ] Teste: `sitesWithDevices` filtra corretamente
- [ ] Teste: `cablesGeoJSON` converte para GeoJSON válido
- [ ] Teste: `refreshSites()` atualiza lista
- [ ] Teste: Loading state funciona

### Passo 3.2: Criar MapControls.vue (1 dia)

**Arquivo**: `frontend/src/components/Map/MapControls.vue`

```vue
<template>
  <div class="map-controls">
    <!-- Zoom -->
    <button @click="$emit('zoom-in')" title="Zoom In">+</button>
    <button @click="$emit('zoom-out')" title="Zoom Out">-</button>
    
    <!-- Layers -->
    <div class="layers-toggle">
      <label>
        <input type="checkbox" v-model="layers.sites" @change="updateLayers" />
        Sites
      </label>
      <label>
        <input type="checkbox" v-model="layers.cables" @change="updateLayers" />
        Cabos
      </label>
      <label>
        <input type="checkbox" v-model="layers.devices" @change="updateLayers" />
        Dispositivos
      </label>
    </div>
    
    <!-- Search -->
    <input 
      v-model="searchQuery"
      @input="$emit('search', searchQuery)"
      placeholder="Buscar..."
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['zoom-in', 'zoom-out', 'layers-changed', 'search'])

const layers = ref({
  sites: true,
  cables: true,
  devices: true
})

const searchQuery = ref('')

function updateLayers() {
  emit('layers-changed', layers.value)
}
</script>
```

**✅ Checklist de Testes - MapControls.vue**
- [ ] Teste: Botões de zoom emitem eventos
- [ ] Teste: Checkboxes de layers funcionam
- [ ] Teste: Busca emite valor correto
- [ ] Teste: Estado inicial é correto

---

## 🧪 Protocolo de Testes

### Testes Unitários (Composables)

Usar **Vitest** para testar lógica isolada:

```javascript
// composables/__tests__/useSiteCameras.spec.js
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useSiteCameras } from '../useSiteCameras'

describe('useSiteCameras', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })
  
  it('fetchMosaics retorna lista de mosaicos', async () => {
    const { fetchMosaics, mosaics } = useSiteCameras(ref(1))
    
    await fetchMosaics()
    
    expect(mosaics.value).toHaveLength(2)
    expect(mosaics.value[0]).toHaveProperty('name')
  })
  
  it('startStreams processa em paralelo', async () => {
    const { mosaicCameras, startStreams } = useSiteCameras(ref(1))
    mosaicCameras.value = [
      { id: 1, name: 'Cam1' },
      { id: 2, name: 'Cam2' }
    ]
    
    await startStreams()
    
    expect(mosaicCameras.value[0].playback_url).toBeDefined()
    expect(mosaicCameras.value[1].playback_url).toBeDefined()
  })
})
```

**Rodar testes:**
```bash
npm run test:unit
```

### Testes de Componente (Vue Test Utils)

```javascript
// components/Site/__tests__/SiteCamerasTab.spec.js
import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import SiteCamerasTab from '../SiteCamerasTab.vue'

describe('SiteCamerasTab', () => {
  it('renderiza lista de mosaicos', () => {
    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 1 }
    })
    
    expect(wrapper.find('.mosaic-list').exists()).toBe(true)
  })
  
  it('abre mosaico ao clicar', async () => {
    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 1 }
    })
    
    await wrapper.find('.mosaic-card').trigger('click')
    
    expect(wrapper.find('.mosaic-viewer').exists()).toBe(true)
  })
})
```

### Testes E2E (Playwright)

```javascript
// e2e/siteDetailsModal.spec.js
import { test, expect } from '@playwright/test'

test('Modal de site - Tab de câmeras', async ({ page }) => {
  await page.goto('http://localhost:8000/monitoring/backbone/map/default')
  
  // Abrir site
  await page.click('.site-marker[data-site-id="1"]')
  
  // Esperar modal abrir
  await expect(page.locator('.site-details-modal')).toBeVisible()
  
  // Navegar para tab de câmeras
  await page.click('button:has-text("Câmeras")')
  
  // Verificar mosaicos
  await expect(page.locator('.mosaic-card')).toHaveCount(2)
  
  // Abrir mosaico
  await page.click('.mosaic-card:first-child')
  
  // Verificar câmeras carregando
  await expect(page.locator('.camera-player')).toHaveCount(4)
  
  // Aguardar streams
  await page.waitForTimeout(2000)
  
  // Verificar vídeos ativos
  const videos = page.locator('video')
  await expect(videos).toHaveCount(4)
  
  // Fechar modal
  await page.click('.modal-close')
  await expect(page.locator('.site-details-modal')).not.toBeVisible()
})
```

**Rodar E2E:**
```bash
npm run test:e2e
```

### Testes de Regressão Visual (Percy/Chromatic)

```javascript
// visual-regression/siteModal.spec.js
import { test } from '@playwright/test'
import percySnapshot from '@percy/playwright'

test('Site modal - visual regression', async ({ page }) => {
  await page.goto('http://localhost:8000/monitoring/backbone/map/default')
  await page.click('.site-marker[data-site-id="1"]')
  await page.waitForSelector('.site-details-modal')
  
  // Screenshot do modal
  await percySnapshot(page, 'Site Modal - Info Tab')
  
  // Tab de câmeras
  await page.click('button:has-text("Câmeras")')
  await percySnapshot(page, 'Site Modal - Cameras Tab')
})
```

---

## 📋 Checklist Completa de Validação

### Antes de Iniciar Refatoração
- [ ] Code freeze comunicado à equipe
- [ ] Branch `refactor/site-modal` criada
- [ ] Backup do código original feito
- [ ] Ambiente de staging preparado
- [ ] Testes E2E existentes rodando

### Durante Refatoração
- [ ] Commits pequenos e incrementais
- [ ] Testes unitários escritos para cada composable
- [ ] Code review em cada pull request
- [ ] Feature flag ativada para testar incrementalmente
- [ ] Documentação atualizada

### Antes de Merge
- [ ] ✅ Todos testes unitários passando (100% coverage de composables)
- [ ] ✅ Todos testes de componente passando
- [ ] ✅ Testes E2E passando sem regressões
- [ ] ✅ Build de produção sem erros
- [ ] ✅ Performance igual ou melhor (Lighthouse > 90)
- [ ] ✅ Code review aprovado por 2+ desenvolvedores
- [ ] ✅ QA manual aprovado
- [ ] ✅ Documentação completa

### Após Deploy em Staging
- [ ] Testar todas funcionalidades manualmente
- [ ] Monitorar logs por 24h
- [ ] Verificar métricas de performance
- [ ] Coletar feedback da equipe
- [ ] Zero bugs críticos encontrados

### Antes de Produção
- [ ] Aprovação final do tech lead
- [ ] Plano de rollback documentado
- [ ] Comunicação aos usuários (se necessário)
- [ ] Deploy em horário de baixo tráfego

---

## 🚨 Plano de Rollback

### Gatilhos de Rollback

**Rollback Imediato**
- Erro crítico que impede uso do sistema
- Performance degradada > 50%
- Perda de dados

**Rollback Planejado**
- 3+ bugs médios em 24h
- Feedback negativo da equipe
- Testes E2E falhando em produção

### Procedimento de Rollback

1. **Reverter commit**
   ```bash
   git revert <commit-hash>
   git push origin main
   ```

2. **Desativar feature flag**
   ```javascript
   // .env
   VITE_REFACTORED_SITE_MODAL=false
   ```

3. **Deploy da versão anterior**
   ```bash
   npm run build
   docker compose restart web
   ```

4. **Comunicar equipe**
   - Slack: #dev-updates
   - Criar post-mortem

5. **Análise de causa raiz**
   - O que falhou?
   - Por que não foi detectado?
   - Como prevenir?

---

## 📊 Métricas de Sucesso

### Quantitativas

| Métrica | Antes | Meta | Atual |
|---------|-------|------|-------|
| Linhas SiteDetailsModal.vue | 2757 | <600 | - |
| Linhas ConfigurationPage.vue | 3854 | <800 | - |
| Tempo de build | 8s | <6s | - |
| Tempo renderização modal | 800ms | <500ms | - |
| Coverage testes | 45% | >80% | - |
| Lighthouse Performance | 85 | >90 | - |

### Qualitativas

- [ ] Código mais fácil de entender
- [ ] Onboarding de novos devs mais rápido
- [ ] Code review mais eficiente
- [ ] Bugs mais fáceis de debugar
- [ ] Features mais rápidas de implementar

---

## 📝 Próximos Passos

### Semana 1-2: SiteDetailsModal
- Dia 1-2: Criar composables
- Dia 3-4: Criar componentes tabs
- Dia 5: Integração
- Dia 6-7: Testes e validação

### Semana 3-4: ConfigurationPage
- Dia 1-2: Extrair useVideoPreview
- Dia 3-5: Criar componentes de gateway
- Dia 6-7: Testes e validação

### Semana 5-6: MapView
- Dia 1-3: Criar composables de mapa
- Dia 4-6: Criar componentes de controles
- Dia 7: Testes e validação

### Após Fase 1
- Retrospectiva da equipe
- Ajustar processo se necessário
- Documentar aprendizados
- Decidir se continua para Fase 2

---

## 🔗 Recursos

### Documentação
- [Vue 3 Composition API](https://vuejs.org/guide/extras/composition-api-faq.html)
- [Pinia](https://pinia.vuejs.org/)
- [Vue Test Utils](https://test-utils.vuejs.org/)
- [Vitest](https://vitest.dev/)
- [Playwright](https://playwright.dev/)

### Ferramentas
- ESLint + Prettier para code style
- Husky para pre-commit hooks
- Conventional Commits para mensagens
- SonarQube para análise de qualidade

### Comunicação
- Slack: #dev-refactoring
- Daily standups: 9h30
- Code review: GitHub Pull Requests
- Documentação: Notion + GitHub Wiki

---

**Última atualização**: 26/01/2026  
**Próxima revisão**: Após Fase 1
