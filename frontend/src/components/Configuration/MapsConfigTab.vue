<template>
  <div class="space-y-6">
    <!-- Provider Selection -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Provedor de Mapas</h3>
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <button
          v-for="provider in mapProviders"
          :key="provider.id"
          @click="selectedProvider = provider.id"
          class="relative p-4 border-2 rounded-lg transition-all hover:shadow-md"
          :class="selectedProvider === provider.id 
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' 
            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-full flex items-center justify-center" 
                   :style="{ backgroundColor: provider.color + '20', color: provider.color }">
                <component :is="provider.icon" class="w-4 h-4" />
              </div>
              <h4 class="font-semibold text-gray-900 dark:text-white">{{ provider.name }}</h4>
            </div>
            <div v-if="selectedProvider === provider.id" class="w-5 h-5 rounded-full bg-primary-500 flex items-center justify-center">
              <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
            </div>
          </div>
          <p class="text-xs text-gray-500 dark:text-gray-400">{{ provider.description }}</p>
        </button>
      </div>
    </div>

    <!-- Google Maps Configuration -->
    <div v-if="selectedProvider === 'google'" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex items-center gap-2 mb-4">
        <GoogleMapsIcon class="w-5 h-5 text-[#4285F4]" />
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Google Maps</h3>
      </div>
      
      <div class="space-y-4">
        <div>
          <label class="label-custom">API Key *</label>
          <input 
            v-model="config.google.api_key" 
            type="text" 
            class="input-custom font-mono text-xs" 
            placeholder="AIzaSy..."
            required
          />
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Obtenha sua chave em <a href="https://console.cloud.google.com" target="_blank" class="text-primary-600 hover:underline">Google Cloud Console</a>
          </p>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label-custom">Zoom Padrão</label>
            <input 
              v-model.number="config.google.default_zoom" 
              type="number" 
              min="1"
              max="20"
              class="input-custom" 
              placeholder="12"
            />
          </div>

          <div>
            <label class="label-custom">Tipo de Mapa</label>
            <select v-model="config.google.map_type" class="input-custom">
              <option value="roadmap">Roadmap (Ruas)</option>
              <option value="terrain">Terrain (Relevo - Recomendado)</option>
              <option value="satellite">Satellite (Satélite)</option>
              <option value="hybrid">Hybrid (Satélite + Ruas)</option>
            </select>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Terrain oferece visualização clara com relevo e sem linhas de grid
            </p>
          </div>
        </div>

        <div>
          <label class="label-custom">Estilos de Mapa (JSON)</label>
          <textarea 
            v-model="config.google.styles" 
            class="input-custom font-mono text-xs" 
            rows="4"
            placeholder='[{"featureType": "all", "stylers": [{"saturation": -100}]}]'
          ></textarea>
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Personalize em <a href="https://mapstyle.withgoogle.com" target="_blank" class="text-primary-600 hover:underline">Map Styling Wizard</a>
          </p>
        </div>

        <div class="space-y-2">
          <div class="flex items-center">
            <input 
              v-model="config.google.enable_street_view" 
              type="checkbox" 
              id="enable-street-view"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label for="enable-street-view" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Habilitar Street View
            </label>
          </div>

          <div class="flex items-center">
            <input 
              v-model="config.google.enable_traffic" 
              type="checkbox" 
              id="enable-traffic"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label for="enable-traffic" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Mostrar tráfego em tempo real
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Mapbox Configuration -->
    <div v-else-if="selectedProvider === 'mapbox'" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex items-center gap-2 mb-4">
        <MapboxIcon class="w-5 h-5 text-[#000000] dark:text-white" />
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Mapbox</h3>
      </div>
      
      <div class="space-y-4">
        <div>
          <label class="label-custom">Access Token *</label>
          <input 
            v-model="config.mapbox.access_token" 
            type="text" 
            class="input-custom font-mono text-xs" 
            placeholder="pk.eyJ1..."
            required
          />
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Obtenha seu token em <a href="https://account.mapbox.com" target="_blank" class="text-primary-600 hover:underline">Mapbox Account</a>
          </p>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label-custom">Zoom Padrão</label>
            <input 
              v-model.number="config.mapbox.default_zoom" 
              type="number" 
              min="1"
              max="22"
              class="input-custom" 
              placeholder="12"
            />
          </div>

          <div>
            <label class="label-custom">Estilo de Mapa</label>
            <select v-model="config.mapbox.style" class="input-custom">
              <option value="mapbox://styles/mapbox/streets-v12">Streets</option>
              <option value="mapbox://styles/mapbox/outdoors-v12">Outdoors</option>
              <option value="mapbox://styles/mapbox/light-v11">Light</option>
              <option value="mapbox://styles/mapbox/dark-v11">Dark</option>
              <option value="mapbox://styles/mapbox/satellite-v9">Satellite</option>
              <option value="mapbox://styles/mapbox/satellite-streets-v12">Satellite Streets</option>
            </select>
          </div>
        </div>

        <div>
          <label class="label-custom">Estilo Customizado (URL)</label>
          <input 
            v-model="config.mapbox.custom_style" 
            type="text" 
            class="input-custom font-mono text-xs" 
            placeholder="mapbox://styles/username/style-id"
          />
        </div>

        <div class="flex items-center">
          <input 
            v-model="config.mapbox.enable_3d" 
            type="checkbox" 
            id="enable-3d"
            class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
          />
          <label for="enable-3d" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
            Habilitar visualização 3D de edifícios
          </label>
        </div>
      </div>
    </div>

    <!-- Esri/ArcGIS Configuration -->
    <div v-else-if="selectedProvider === 'esri'" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex items-center gap-2 mb-4">
        <EsriIcon class="w-5 h-5 text-[#007AC2]" />
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Esri ArcGIS</h3>
      </div>
      
      <div class="space-y-4">
        <div>
          <label class="label-custom">API Key</label>
          <input 
            v-model="config.esri.api_key" 
            type="text" 
            class="input-custom font-mono text-xs" 
            placeholder="AAPK..."
          />
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Opcional. Obtenha em <a href="https://developers.arcgis.com" target="_blank" class="text-primary-600 hover:underline">ArcGIS Developers</a>
          </p>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label-custom">Zoom Padrão</label>
            <input 
              v-model.number="config.esri.default_zoom" 
              type="number" 
              min="1"
              max="19"
              class="input-custom" 
              placeholder="12"
            />
          </div>

          <div>
            <label class="label-custom">Basemap</label>
            <select v-model="config.esri.basemap" class="input-custom">
              <option value="streets">Streets</option>
              <option value="topo">Topographic</option>
              <option value="satellite">Satellite</option>
              <option value="hybrid">Hybrid</option>
              <option value="terrain">Terrain</option>
              <option value="oceans">Oceans</option>
              <option value="gray">Gray Canvas</option>
              <option value="dark-gray">Dark Gray Canvas</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Common Settings -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Configurações Gerais</h3>
      
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label-custom">Latitude Inicial</label>
            <input 
              v-model.number="config.common.default_lat" 
              type="number" 
              step="0.000001"
              class="input-custom" 
              placeholder="-15.7801"
            />
          </div>

          <div>
            <label class="label-custom">Longitude Inicial</label>
            <input 
              v-model.number="config.common.default_lng" 
              type="number" 
              step="0.000001"
              class="input-custom" 
              placeholder="-47.9292"
            />
          </div>
        </div>

        <div>
          <label class="label-custom">Idioma do Mapa</label>
          <select v-model="config.common.language" class="input-custom">
            <option value="pt-BR">Português (Brasil)</option>
            <option value="en">English</option>
            <option value="es">Español</option>
            <option value="fr">Français</option>
          </select>
        </div>

        <div>
          <label class="label-custom">Tema do Mapa</label>
          <select v-model="config.common.theme" class="input-custom">
            <option value="light">Claro</option>
            <option value="dark">Escuro</option>
            <option value="auto">Automático (seguir sistema)</option>
          </select>
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Define a aparência do mapa (cores claras ou escuras)
          </p>
        </div>

        <div class="space-y-2">
          <div class="flex items-center">
            <input 
              v-model="config.common.enable_clustering" 
              type="checkbox" 
              id="enable-clustering"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label for="enable-clustering" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Agrupar marcadores próximos (clustering)
            </label>
          </div>

          <div class="flex items-center">
            <input 
              v-model="config.common.enable_drawing_tools" 
              type="checkbox" 
              id="enable-drawing"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label for="enable-drawing" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Ferramentas de desenho (polígonos, linhas)
            </label>
          </div>

          <div class="flex items-center">
            <input 
              v-model="config.common.enable_fullscreen" 
              type="checkbox" 
              id="enable-fullscreen"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label for="enable-fullscreen" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Botão de tela cheia
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex justify-end gap-3">
      <button @click="handleReset" class="btn-secondary">
        Resetar
      </button>
      <button @click="handleSave" :disabled="saving" class="btn-primary">
        <svg v-if="saving" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Salvar Configurações
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, h, computed, watch } from 'vue'
import { useNotification } from '@/composables/useNotification'
import { useSystemConfig } from '@/composables/useSystemConfig'

// Simple icon components
const GoogleMapsIcon = (props) => h('svg', { ...props, fill: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { d: 'M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z' })
])

const MapboxIcon = (props) => h('svg', { ...props, fill: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { d: 'M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.6 0 12 0zm0 22c-5.5 0-10-4.5-10-10S6.5 2 12 2s10 4.5 10 10-4.5 10-10 10z' })
])

const EsriIcon = (props) => h('svg', { ...props, fill: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { d: 'M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z' })
])

// Composables
const { notify } = useNotification()
const { configForm, loadSystemConfig, saveSystemConfig, loading } = useSystemConfig()

// Local state
const selectedProvider = ref('google')
const saving = ref(false)

// Map local reactive config to configForm
const config = reactive({
  google: {
    api_key: computed({
      get: () => configForm.value.GOOGLE_MAPS_API_KEY,
      set: (val) => configForm.value.GOOGLE_MAPS_API_KEY = val
    }),
    default_zoom: computed({
      get: () => parseInt(configForm.value.MAP_DEFAULT_ZOOM) || 12,
      set: (val) => configForm.value.MAP_DEFAULT_ZOOM = String(val)
    }),
    map_type: computed({
      get: () => configForm.value.MAP_TYPE,
      set: (val) => configForm.value.MAP_TYPE = val
    }),
    styles: computed({
      get: () => configForm.value.MAP_STYLES,
      set: (val) => configForm.value.MAP_STYLES = val
    }),
    enable_street_view: computed({
      get: () => configForm.value.ENABLE_STREET_VIEW,
      set: (val) => configForm.value.ENABLE_STREET_VIEW = val
    }),
    enable_traffic: computed({
      get: () => configForm.value.ENABLE_TRAFFIC,
      set: (val) => configForm.value.ENABLE_TRAFFIC = val
    }),
  },
  mapbox: {
    access_token: computed({
      get: () => configForm.value.MAPBOX_TOKEN,
      set: (val) => configForm.value.MAPBOX_TOKEN = val
    }),
    default_zoom: computed({
      get: () => parseInt(configForm.value.MAP_DEFAULT_ZOOM) || 12,
      set: (val) => configForm.value.MAP_DEFAULT_ZOOM = String(val)
    }),
    style: computed({
      get: () => configForm.value.MAPBOX_STYLE,
      set: (val) => configForm.value.MAPBOX_STYLE = val
    }),
    custom_style: computed({
      get: () => configForm.value.MAPBOX_CUSTOM_STYLE,
      set: (val) => configForm.value.MAPBOX_CUSTOM_STYLE = val
    }),
    enable_3d: computed({
      get: () => configForm.value.MAPBOX_ENABLE_3D,
      set: (val) => configForm.value.MAPBOX_ENABLE_3D = val
    }),
  },
  esri: {
    api_key: computed({
      get: () => configForm.value.ESRI_API_KEY,
      set: (val) => configForm.value.ESRI_API_KEY = val
    }),
    default_zoom: computed({
      get: () => parseInt(configForm.value.MAP_DEFAULT_ZOOM) || 12,
      set: (val) => configForm.value.MAP_DEFAULT_ZOOM = String(val)
    }),
    basemap: computed({
      get: () => configForm.value.ESRI_BASEMAP,
      set: (val) => configForm.value.ESRI_BASEMAP = val
    }),
  },
  common: {
    default_lat: computed({
      get: () => { const v = parseFloat(configForm.value.MAP_DEFAULT_LAT); return isNaN(v) ? -15.7801 : v },
      set: (val) => configForm.value.MAP_DEFAULT_LAT = String(val)
    }),
    default_lng: computed({
      get: () => { const v = parseFloat(configForm.value.MAP_DEFAULT_LNG); return isNaN(v) ? -47.9292 : v },
      set: (val) => configForm.value.MAP_DEFAULT_LNG = String(val)
    }),
    language: computed({
      get: () => configForm.value.MAP_LANGUAGE,
      set: (val) => configForm.value.MAP_LANGUAGE = val
    }),
    theme: computed({
      get: () => configForm.value.MAP_THEME || 'light',
      set: (val) => configForm.value.MAP_THEME = val
    }),
    enable_clustering: computed({
      get: () => configForm.value.ENABLE_MAP_CLUSTERING,
      set: (val) => configForm.value.ENABLE_MAP_CLUSTERING = val
    }),
    enable_drawing_tools: computed({
      get: () => configForm.value.ENABLE_DRAWING_TOOLS,
      set: (val) => configForm.value.ENABLE_DRAWING_TOOLS = val
    }),
    enable_fullscreen: computed({
      get: () => configForm.value.ENABLE_FULLSCREEN,
      set: (val) => configForm.value.ENABLE_FULLSCREEN = val
    }),
  },
})

// Watch for provider changes in configForm
watch(() => configForm.value.MAP_PROVIDER, (newVal) => {
  if (newVal) selectedProvider.value = newVal
}, { immediate: true })

watch(selectedProvider, (newVal) => {
  configForm.value.MAP_PROVIDER = newVal
})

const mapProviders = [
  {
    id: 'google',
    name: 'Google Maps',
    description: 'Cobertura global com Street View e dados de tráfego',
    icon: GoogleMapsIcon,
    color: '#4285F4',
  },
  {
    id: 'mapbox',
    name: 'Mapbox',
    description: 'Mapas customizáveis com visualização 3D',
    icon: MapboxIcon,
    color: '#000000',
  },
  {
    id: 'esri',
    name: 'Esri ArcGIS',
    description: 'Análises geoespaciais avançadas',
    icon: EsriIcon,
    color: '#007AC2',
  },
]

// Methods
const handleSave = async () => {
  saving.value = true
  try {
    await saveSystemConfig()
    notify('Configurações de mapas salvas com sucesso!', 'success')
  } catch (error) {
    notify('Erro ao salvar configurações de mapas', 'error')
    console.error('[MapsConfigTab] Save error:', error)
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  if (confirm('Resetar configurações de mapas para os valores padrão?')) {
    configForm.value.MAP_PROVIDER = 'google'
    configForm.value.GOOGLE_MAPS_API_KEY = ''
    configForm.value.MAP_DEFAULT_ZOOM = '12'
    configForm.value.MAP_DEFAULT_LAT = '-15.7801'
    configForm.value.MAP_DEFAULT_LNG = '-47.9292'
    configForm.value.MAP_TYPE = 'roadmap'
    configForm.value.MAP_STYLES = ''
    configForm.value.ENABLE_STREET_VIEW = true
    configForm.value.ENABLE_TRAFFIC = false
    configForm.value.MAPBOX_TOKEN = ''
    configForm.value.MAPBOX_STYLE = 'mapbox://styles/mapbox/streets-v12'
    configForm.value.MAPBOX_CUSTOM_STYLE = ''
    configForm.value.MAPBOX_ENABLE_3D = false
    configForm.value.ESRI_API_KEY = ''
    configForm.value.ESRI_BASEMAP = 'streets'
    configForm.value.MAP_LANGUAGE = 'pt-BR'
    configForm.value.ENABLE_MAP_CLUSTERING = true
    configForm.value.ENABLE_DRAWING_TOOLS = true
    configForm.value.ENABLE_FULLSCREEN = true
  }
}

// Lifecycle
onMounted(async () => {
  await loadSystemConfig()
})
</script>

<style scoped>
.label-custom {
  @apply block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5;
}

.input-custom {
  @apply w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-colors;
}

.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}

.btn-secondary {
  @apply inline-flex items-center justify-center rounded-md bg-white dark:bg-gray-800 px-4 py-2 text-sm font-semibold text-gray-900 dark:text-gray-200 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200;
}
</style>
