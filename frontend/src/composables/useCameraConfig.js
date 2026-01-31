/**
 * Composable para gerenciamento de configurações de câmeras e streaming
 * 
 * Responsabilidades:
 * - Gerenciar configurações globais de câmeras
 * - Helpers para stream URLs e formatos
 * - Validação de URLs de streaming
 * - Configurações de qualidade e codecs
 * - Presets de configuração de câmeras
 * 
 * @module useCameraConfig
 */

import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

/**
 * Composable para gerenciamento de configurações de câmeras
 * @returns {Object} Objetos e funções para gerenciar configurações de câmeras
 */
export function useCameraConfig() {
  const api = useApi()
  const notify = useNotification()

  // Estado
  const loading = ref(false)
  const error = ref(null)
  
  // Configurações globais de câmeras
  const cameraSettings = ref({
    default_stream_type: 'rtmp',
    default_resolution: '1080p',
    default_fps: 30,
    default_codec: 'h264',
    enable_hardware_acceleration: true,
    max_concurrent_streams: 10,
    stream_timeout_seconds: 30,
    reconnect_attempts: 3,
    reconnect_delay_ms: 2000,
  })

  // Presets de câmeras populares
  const cameraPresets = ref([
    {
      id: 'hikvision',
      name: 'Hikvision',
      manufacturer: 'Hikvision',
      default_port: 554,
      url_template: 'rtsp://{username}:{password}@{ip}:{port}/Streaming/Channels/101',
      supported_formats: ['rtsp', 'rtmp'],
    },
    {
      id: 'dahua',
      name: 'Dahua',
      manufacturer: 'Dahua',
      default_port: 554,
      url_template: 'rtsp://{username}:{password}@{ip}:{port}/cam/realmonitor?channel=1&subtype=0',
      supported_formats: ['rtsp', 'rtmp'],
    },
    {
      id: 'intelbras',
      name: 'Intelbras',
      manufacturer: 'Intelbras',
      default_port: 554,
      url_template: 'rtsp://{username}:{password}@{ip}:{port}/cam/realmonitor?channel=1&subtype=0',
      supported_formats: ['rtsp'],
    },
    {
      id: 'axis',
      name: 'Axis',
      manufacturer: 'Axis Communications',
      default_port: 554,
      url_template: 'rtsp://{username}:{password}@{ip}:{port}/axis-media/media.amp',
      supported_formats: ['rtsp', 'http'],
    },
    {
      id: 'generic_rtsp',
      name: 'RTSP Genérico',
      manufacturer: 'Generic',
      default_port: 554,
      url_template: 'rtsp://{username}:{password}@{ip}:{port}/stream',
      supported_formats: ['rtsp'],
    },
  ])

  // Stream types suportados
  const streamTypes = [
    { value: 'rtsp', label: 'RTSP', description: 'Real Time Streaming Protocol' },
    { value: 'rtmp', label: 'RTMP', description: 'Real Time Messaging Protocol' },
    { value: 'hls', label: 'HLS', description: 'HTTP Live Streaming' },
    { value: 'webrtc', label: 'WebRTC', description: 'Web Real-Time Communication' },
    { value: 'http', label: 'HTTP', description: 'HTTP Progressive Download' },
  ]

  // Resoluções suportadas
  const resolutions = [
    { value: '4k', label: '4K (3840x2160)', width: 3840, height: 2160 },
    { value: '1080p', label: 'Full HD (1920x1080)', width: 1920, height: 1080 },
    { value: '720p', label: 'HD (1280x720)', width: 1280, height: 720 },
    { value: '480p', label: 'SD (854x480)', width: 854, height: 480 },
    { value: '360p', label: 'Low (640x360)', width: 640, height: 360 },
  ]

  // Codecs suportados
  const codecs = [
    { value: 'h264', label: 'H.264 (AVC)', description: 'Mais compatível' },
    { value: 'h265', label: 'H.265 (HEVC)', description: 'Melhor compressão' },
    { value: 'vp8', label: 'VP8', description: 'Google WebM' },
    { value: 'vp9', label: 'VP9', description: 'Google WebM v2' },
    { value: 'av1', label: 'AV1', description: 'Codec moderno' },
  ]

  // Computed
  const hasPresets = computed(() => cameraPresets.value.length > 0)

  // Métodos

  /**
   * Carrega configurações globais de câmeras
   * @returns {Promise<void>}
   */
  const loadCameraSettings = async () => {
    try {
      loading.value = true
      error.value = null
      
      const res = await api.get('/setup_app/api/camera-settings/')
      
      if (res.success !== false && res.settings) {
        cameraSettings.value = { ...cameraSettings.value, ...res.settings }
      }
    } catch (e) {
      error.value = e.message || 'Erro ao carregar configurações'
      console.error('[useCameraConfig] Error loading settings:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * Salva configurações globais de câmeras
   * @param {Object} settings - Novas configurações
   * @returns {Promise<boolean>} true se salvou com sucesso
   */
  const saveCameraSettings = async (settings) => {
    try {
      loading.value = true
      error.value = null
      
      const payload = settings || cameraSettings.value
      
      const res = await api.post('/setup_app/api/camera-settings/', payload)
      
      if (res.success !== false) {
        notify.success('Câmeras', res.message || 'Configurações salvas.')
        cameraSettings.value = { ...cameraSettings.value, ...payload }
        return true
      } else {
        notify.error('Câmeras', res.message || 'Erro ao salvar.')
        return false
      }
    } catch (e) {
      error.value = e.message || 'Erro ao salvar configurações'
      notify.error('Câmeras', e.message || 'Erro ao salvar configurações.')
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Valida URL de streaming
   * @param {string} url - URL a validar
   * @returns {Object} { valid: boolean, type?: string, error?: string }
   */
  const validateStreamUrl = (url) => {
    if (!url || typeof url !== 'string') {
      return { valid: false, error: 'URL vazia ou inválida' }
    }

    const trimmed = url.trim()
    
    // RTSP
    if (trimmed.startsWith('rtsp://')) {
      return { valid: true, type: 'rtsp' }
    }
    
    // RTMP
    if (trimmed.startsWith('rtmp://') || trimmed.startsWith('rtmps://')) {
      return { valid: true, type: 'rtmp' }
    }
    
    // HLS
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      if (trimmed.endsWith('.m3u8')) {
        return { valid: true, type: 'hls' }
      }
      return { valid: true, type: 'http' }
    }
    
    // WebRTC
    if (trimmed.startsWith('webrtc://')) {
      return { valid: true, type: 'webrtc' }
    }

    return { valid: false, error: 'Protocolo não suportado (use rtsp://, rtmp://, http://, https://, webrtc://)' }
  }

  /**
   * Gera URL de stream a partir de preset
   * @param {string} presetId - ID do preset
   * @param {Object} params - Parâmetros { ip, port, username, password }
   * @returns {string} URL gerada
   */
  const generateStreamUrlFromPreset = (presetId, params) => {
    const preset = cameraPresets.value.find(p => p.id === presetId)
    if (!preset) {
      return ''
    }

    let url = preset.url_template
    
    // Substituir placeholders
    url = url.replace('{ip}', params.ip || '')
    url = url.replace('{port}', params.port || preset.default_port)
    url = url.replace('{username}', params.username || 'admin')
    url = url.replace('{password}', params.password || '')
    
    return url
  }

  /**
   * Busca preset por ID
   * @param {string} presetId - ID do preset
   * @returns {Object|null} Preset encontrado ou null
   */
  const getPresetById = (presetId) => {
    return cameraPresets.value.find(p => p.id === presetId) || null
  }

  /**
   * Busca presets por fabricante
   * @param {string} manufacturer - Nome do fabricante
   * @returns {Array} Lista de presets
   */
  const getPresetsByManufacturer = (manufacturer) => {
    return cameraPresets.value.filter(p => 
      p.manufacturer.toLowerCase().includes(manufacturer.toLowerCase())
    )
  }

  /**
   * Detecta tipo de stream a partir da URL
   * @param {string} url - URL do stream
   * @returns {string} Tipo detectado (rtsp, rtmp, hls, http, webrtc, unknown)
   */
  const detectStreamType = (url) => {
    const validation = validateStreamUrl(url)
    return validation.type || 'unknown'
  }

  /**
   * Extrai informações de URL RTSP
   * @param {string} rtspUrl - URL RTSP
   * @returns {Object} { ip, port, username, password, path }
   */
  const parseRtspUrl = (rtspUrl) => {
    try {
      const url = new URL(rtspUrl)
      return {
        protocol: url.protocol.replace(':', ''),
        ip: url.hostname,
        port: url.port || '554',
        username: url.username || '',
        password: url.password || '',
        path: url.pathname + url.search,
      }
    } catch (e) {
      return {
        protocol: '',
        ip: '',
        port: '554',
        username: '',
        password: '',
        path: '',
        error: 'URL inválida',
      }
    }
  }

  /**
   * Testa conectividade com stream
   * @param {string} streamUrl - URL do stream
   * @param {Object} options - Opções de teste { timeout, type }
   * @returns {Promise<Object>} Resultado do teste
   */
  const testStreamConnection = async (streamUrl, options = {}) => {
    try {
      loading.value = true
      error.value = null
      
      const payload = {
        stream_url: streamUrl,
        timeout: options.timeout || cameraSettings.value.stream_timeout_seconds,
        stream_type: options.type || detectStreamType(streamUrl),
      }
      
      const res = await api.post('/setup_app/api/test-stream/', payload)
      
      if (res.success) {
        notify.success('Stream', res.message || 'Conexão bem-sucedida!')
        return { success: true, ...res }
      } else {
        notify.error('Stream', res.message || 'Falha na conexão.')
        return { success: false, error: res.message }
      }
    } catch (e) {
      error.value = e.message || 'Erro ao testar stream'
      notify.error('Stream', e.message || 'Erro ao testar stream.')
      return { success: false, error: e.message }
    } finally {
      loading.value = false
    }
  }

  /**
   * Valida credenciais de câmera
   * @param {Object} credentials - { ip, username, password, port }
   * @returns {Object} { valid: boolean, errors: Array }
   */
  const validateCameraCredentials = (credentials) => {
    const errors = []
    
    if (!credentials.ip || !/^[\d.]+$/.test(credentials.ip)) {
      errors.push('IP inválido')
    }
    
    if (!credentials.username) {
      errors.push('Username obrigatório')
    }
    
    if (!credentials.password) {
      errors.push('Password obrigatório')
    }
    
    const port = parseInt(credentials.port)
    if (!port || port < 1 || port > 65535) {
      errors.push('Porta inválida (1-65535)')
    }
    
    return {
      valid: errors.length === 0,
      errors,
    }
  }

  /**
   * Cria configuração padrão de câmera
   * @param {Object} overrides - Valores a sobrescrever
   * @returns {Object} Configuração padrão
   */
  const createDefaultCameraConfig = (overrides = {}) => {
    return {
      stream_type: cameraSettings.value.default_stream_type,
      resolution: cameraSettings.value.default_resolution,
      fps: cameraSettings.value.default_fps,
      codec: cameraSettings.value.default_codec,
      enable_audio: false,
      enable_recording: false,
      retention_days: 7,
      ...overrides,
    }
  }

  /**
   * Normaliza URL de stream (adiciona protocolo se necessário)
   * @param {string} url - URL a normalizar
   * @param {string} defaultProtocol - Protocolo padrão (rtsp)
   * @returns {string} URL normalizada
   */
  const normalizeStreamUrl = (url, defaultProtocol = 'rtsp') => {
    if (!url) return ''
    
    const trimmed = url.trim()
    
    // Já tem protocolo
    if (/^[a-z]+:\/\//i.test(trimmed)) {
      return trimmed
    }
    
    // Adicionar protocolo padrão
    return `${defaultProtocol}://${trimmed}`
  }

  /**
   * Limpa erros
   */
  const clearError = () => {
    error.value = null
  }

  // Retorno do composable
  return {
    // Estado
    loading,
    error,
    cameraSettings,
    cameraPresets,
    streamTypes,
    resolutions,
    codecs,
    
    // Computed
    hasPresets,
    
    // Métodos
    loadCameraSettings,
    saveCameraSettings,
    validateStreamUrl,
    generateStreamUrlFromPreset,
    testStreamConnection,
    detectStreamType,
    parseRtspUrl,
    validateCameraCredentials,
    createDefaultCameraConfig,
    normalizeStreamUrl,
    
    // Utilitários
    getPresetById,
    getPresetsByManufacturer,
    clearError,
  }
}
