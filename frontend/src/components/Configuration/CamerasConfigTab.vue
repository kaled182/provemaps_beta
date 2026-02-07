<template>
  <div class="space-y-6">
    <!-- Camera Settings Form -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Configuração Global de Câmeras</h3>
      
      <div class="space-y-4">
        <!-- Stream Protocol -->
        <div>
          <label class="label-custom">Protocolo de Streaming Padrão</label>
          <select v-model="cameraConfig.default_protocol" class="input-custom">
            <option value="rtsp">RTSP (Real-Time Streaming Protocol)</option>
            <option value="rtmp">RTMP (Real-Time Messaging Protocol)</option>
            <option value="hls">HLS (HTTP Live Streaming)</option>
            <option value="http">HTTP/MJPEG</option>
            <option value="webrtc">WebRTC</option>
          </select>
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Protocolo usado por padrão ao adicionar novas câmeras
          </p>
        </div>

        <!-- Camera Manufacturer Preset -->
        <div>
          <label class="label-custom">Fabricante Padrão</label>
          <select v-model="selectedPreset" @change="applyPreset" class="input-custom">
            <option value="">Selecione um fabricante...</option>
            <option value="hikvision">Hikvision</option>
            <option value="dahua">Dahua</option>
            <option value="intelbras">Intelbras</option>
            <option value="axis">Axis Communications</option>
            <option value="generic">Genérico (ONVIF)</option>
          </select>
        </div>

        <!-- Stream URL Template -->
        <div>
          <label class="label-custom">Template de URL de Streaming</label>
          <input 
            v-model="cameraConfig.stream_url_template" 
            type="text" 
            class="input-custom font-mono text-xs" 
            placeholder="rtsp://{username}:{password}@{host}:{port}/Streaming/Channels/101"
          />
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Variáveis disponíveis: {username}, {password}, {host}, {port}, {channel}
          </p>
        </div>

        <!-- Credentials -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label-custom">Usuário Padrão</label>
            <input 
              v-model="cameraConfig.default_username" 
              type="text" 
              class="input-custom" 
              placeholder="admin"
              autocomplete="off"
            />
          </div>

          <div>
            <label class="label-custom">Senha Padrão</label>
            <input 
              v-model="cameraConfig.default_password" 
              type="password" 
              class="input-custom" 
              autocomplete="new-password"
            />
          </div>
        </div>

        <!-- Port Configuration -->
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label class="label-custom">Porta RTSP</label>
            <input 
              v-model.number="cameraConfig.rtsp_port" 
              type="number" 
              min="1"
              max="65535"
              class="input-custom" 
              placeholder="554"
            />
          </div>

          <div>
            <label class="label-custom">Porta HTTP</label>
            <input 
              v-model.number="cameraConfig.http_port" 
              type="number" 
              min="1"
              max="65535"
              class="input-custom" 
              placeholder="80"
            />
          </div>

          <div>
            <label class="label-custom">Porta ONVIF</label>
            <input 
              v-model.number="cameraConfig.onvif_port" 
              type="number" 
              min="1"
              max="65535"
              class="input-custom" 
              placeholder="8000"
            />
          </div>
        </div>

        <!-- Connection Settings -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label-custom">Timeout de Conexão (segundos)</label>
            <input 
              v-model.number="cameraConfig.connection_timeout" 
              type="number" 
              min="1"
              max="60"
              class="input-custom" 
              placeholder="10"
            />
          </div>

          <div>
            <label class="label-custom">Buffer de Streaming (KB)</label>
            <input 
              v-model.number="cameraConfig.stream_buffer_size" 
              type="number" 
              min="64"
              max="4096"
              class="input-custom" 
              placeholder="512"
            />
          </div>
        </div>

        <!-- Additional Options -->
        <div class="space-y-3">
          <div class="flex items-center">
            <input 
              v-model="cameraConfig.verify_ssl" 
              type="checkbox" 
              id="verify-ssl"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label for="verify-ssl" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Verificar certificados SSL/TLS
            </label>
          </div>

          <div class="flex items-center">
            <input 
              v-model="cameraConfig.auto_reconnect" 
              type="checkbox" 
              id="auto-reconnect"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label for="auto-reconnect" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Reconectar automaticamente em caso de falha
            </label>
          </div>

          <div class="flex items-center">
            <input 
              v-model="cameraConfig.enable_recording" 
              type="checkbox" 
              id="enable-recording"
              class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <label for="enable-recording" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
              Habilitar gravação local (DVR/NVR)
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Stream URL Tester -->
    <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Testar URL de Streaming</h3>
      
      <div class="space-y-4">
        <div>
          <label class="label-custom">URL de Teste</label>
          <input 
            v-model="testUrl" 
            type="text" 
            class="input-custom font-mono text-xs" 
            placeholder="rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101"
          />
        </div>

        <div class="flex gap-2">
          <button 
            @click="handleValidateUrl" 
            :disabled="!testUrl || validating"
            class="btn-secondary"
          >
            <svg v-if="validating" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Validar Formato
          </button>

          <button 
            @click="handleTestConnection" 
            :disabled="!testUrl || testing"
            class="btn-secondary"
          >
            <svg v-if="testing" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Testar Conexão
          </button>
        </div>

        <!-- Test Results -->
        <div v-if="urlValidation" class="p-3 rounded-md text-sm"
             :class="urlValidation.valid 
               ? 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400' 
               : 'bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400'">
          <p class="font-medium">{{ urlValidation.message }}</p>
          <ul v-if="urlValidation.details" class="mt-2 space-y-1 text-xs">
            <li v-for="(value, key) in urlValidation.details" :key="key">
              <span class="font-medium">{{ key }}:</span> {{ value }}
            </li>
          </ul>
        </div>

        <div v-if="connectionTest" class="p-3 rounded-md text-sm"
             :class="connectionTest.success 
               ? 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400' 
               : 'bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400'">
          <p class="font-medium">{{ connectionTest.message }}</p>
          <p v-if="connectionTest.latency" class="text-xs mt-1">
            Latência: {{ connectionTest.latency }}ms
          </p>
        </div>
      </div>
    </div>

    <!-- Preset Information -->
    <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 p-4">
      <h4 class="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2">ℹ️ Informações sobre Presets</h4>
      <div class="text-xs text-blue-700 dark:text-blue-400 space-y-1">
        <p><strong>Hikvision:</strong> rtsp://{username}:{password}@{host}:554/Streaming/Channels/{channel}01</p>
        <p><strong>Dahua:</strong> rtsp://{username}:{password}@{host}:554/cam/realmonitor?channel={channel}&subtype=0</p>
        <p><strong>Intelbras:</strong> rtsp://{username}:{password}@{host}:554/cam/realmonitor?channel=1&subtype=0</p>
        <p><strong>Axis:</strong> rtsp://{username}:{password}@{host}:554/axis-media/media.amp?streamprofile={channel}</p>
        <p><strong>Genérico (ONVIF):</strong> rtsp://{username}:{password}@{host}:554/onvif1</p>
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
import { ref, reactive, onMounted } from 'vue'
import { useCameraConfig } from '@/composables/useCameraConfig'

// Composable
const {
  cameraSettings,
  loading,
  loadCameraSettings,
  saveCameraSettings,
  validateStreamUrl,
  generateStreamUrlFromPreset,
  testStreamConnection,
  createDefaultCameraConfig,
} = useCameraConfig()

// Local state
const cameraConfig = reactive({ ...createDefaultCameraConfig() })
const selectedPreset = ref('')
const testUrl = ref('')
const validating = ref(false)
const testing = ref(false)
const saving = ref(false)
const urlValidation = ref(null)
const connectionTest = ref(null)

// Methods
const applyPreset = () => {
  if (selectedPreset.value) {
    const presetUrl = generateStreamUrlFromPreset(selectedPreset.value, {
      host: '192.168.1.100',
      channel: 1,
    })
    
    if (presetUrl) {
      cameraConfig.stream_url_template = presetUrl
      
      // Apply manufacturer-specific defaults
      const defaults = {
        hikvision: { rtsp_port: 554, http_port: 80, onvif_port: 8000 },
        dahua: { rtsp_port: 554, http_port: 80, onvif_port: 80 },
        intelbras: { rtsp_port: 554, http_port: 80, onvif_port: 8999 },
        axis: { rtsp_port: 554, http_port: 80, onvif_port: 80 },
        generic: { rtsp_port: 554, http_port: 80, onvif_port: 8080 },
      }
      
      const presetDefaults = defaults[selectedPreset.value]
      if (presetDefaults) {
        Object.assign(cameraConfig, presetDefaults)
      }
    }
  }
}

const handleValidateUrl = () => {
  validating.value = true
  urlValidation.value = null
  
  try {
    const result = validateStreamUrl(testUrl.value)
    urlValidation.value = result
  } finally {
    validating.value = false
  }
}

const handleTestConnection = async () => {
  testing.value = true
  connectionTest.value = null
  
  try {
    const result = await testStreamConnection(testUrl.value)
    connectionTest.value = result
  } finally {
    testing.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    await saveCameraSettings(cameraConfig)
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  if (confirm('Resetar configurações de câmeras para os valores padrão?')) {
    Object.assign(cameraConfig, createDefaultCameraConfig())
    selectedPreset.value = ''
    testUrl.value = ''
    urlValidation.value = null
    connectionTest.value = null
  }
}

// Lifecycle
onMounted(async () => {
  const settings = await loadCameraSettings()
  if (settings) {
    Object.assign(cameraConfig, settings)
  }
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
  @apply inline-flex items-center justify-center rounded-md bg-white dark:bg-gray-800 px-4 py-2 text-sm font-semibold text-gray-900 dark:text-gray-200 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}
</style>
