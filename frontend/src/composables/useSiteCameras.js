import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'

/**
 * Composable para gerenciar câmeras e mosaicos de um site
 * 
 * @returns {Object} Estado e métodos para gerenciar câmeras
 * 
 * @example
 * ```js
 * const { 
 *   mosaics, 
 *   cameras, 
 *   fetchMosaics, 
 *   loadMosaic, 
 *   startStreams 
 * } = useSiteCameras()
 * 
 * await fetchMosaics(siteId)
 * await loadMosaic(mosaics.value[0].id, siteId)
 * await startStreams()
 * ```
 */
export function useSiteCameras() {
  const api = useApi()
  
  // Estado reativo
  const mosaics = ref([])
  const cameras = ref([])
  const currentMosaic = ref(null)
  const loading = ref(false)
  const error = ref(null)
  
  // Computed
  const hasCameras = computed(() => cameras.value.length > 0)
  
  /**
   * Busca lista de mosaicos filtrados por site_id
   * 
   * @param {number} siteId - ID do site
   * @returns {Promise<void>}
   */
  async function fetchMosaics(siteId) {
    loading.value = true
    error.value = null
    
    try {
      const response = await api.get('/setup_app/video/api/mosaics/')
      
      if (response && response.success) {
        const allMosaics = response.mosaics || response.results || []
        mosaics.value = allMosaics.filter(m => m.site_id === siteId)
      } else {
        mosaics.value = []
      }
    } catch (err) {
      console.error('[useSiteCameras] Erro ao buscar mosaicos:', err)
      error.value = err
      mosaics.value = []
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Carrega detalhes de um mosaico e enriquece câmeras com dados da API
   * 
   * @param {number} mosaicId - ID do mosaico
   * @param {number} siteId - ID do site (usado para buscar câmeras)
   * @returns {Promise<void>}
   */
  async function loadMosaic(mosaicId, siteId) {
    loading.value = true
    error.value = null
    
    try {
      // 1. Buscar detalhes do mosaico
      const mosaicResponse = await api.get(`/setup_app/video/api/mosaics/${mosaicId}/`)
      
      if (!mosaicResponse || !mosaicResponse.success) {
        throw new Error('Falha ao carregar mosaico')
      }
      
      currentMosaic.value = mosaicResponse.mosaic || mosaicResponse.data
      const camerasFromMosaic = currentMosaic.value.cameras || []
      
      console.log(`[useSiteCameras] Mosaico: ${currentMosaic.value.name} - Câmeras: ${camerasFromMosaic.length}`)
      
      // 2. Tentar enriquecer câmeras com dados completos da API
      try {
        const camerasResponse = await api.get(`/api/v1/cameras/?site=${siteId}`)
        const camerasWithWhep = camerasResponse.results || []
        
        cameras.value = camerasFromMosaic.map((mosaicCam, idx) => {
          // Se o item for número/string, criar objeto base
          if (typeof mosaicCam === 'number' || typeof mosaicCam === 'string') {
            const camId = Number(mosaicCam)
            const fullCam = camerasWithWhep.find(c => Number(c.id) === camId)
            const obj = fullCam ? { ...fullCam } : { id: camId, name: `Camera ${camId}` }
            
            // Derivar WHEP URL se não existir
            if (!obj.whep_url && obj.playback_url) {
              obj.whep_url = deriveWhepUrl(obj.playback_url)
            }
            
            assignConnectionKey(obj, `mosaic-${mosaicId}-${idx}`)
            return obj
          }
          
          // Se for objeto, fazer merge com dados da API
          const camId = mosaicCam.id ?? mosaicCam.camera_id ?? mosaicCam.pk ?? mosaicCam.camera?.id ?? idx
          const fullCam = camerasWithWhep.find(c => Number(c.id) === Number(camId) || c.name === mosaicCam.name)
          const merged = fullCam ? { ...fullCam, ...mosaicCam, id: Number(camId) } : { ...mosaicCam, id: Number(camId) }
          
          if (!merged.whep_url && merged.playback_url) {
            merged.whep_url = deriveWhepUrl(merged.playback_url)
          }
          
          assignConnectionKey(merged, `mosaic-${mosaicId}-${idx}`)
          return merged
        })
        
      } catch (cameraError) {
        // Fallback: construir objetos básicos a partir dos IDs
        console.warn('[useSiteCameras] Erro ao buscar câmeras, usando fallback:', cameraError)
        
        cameras.value = camerasFromMosaic.map((mosaicCam, idx) => {
          const base = typeof mosaicCam === 'number' || typeof mosaicCam === 'string'
            ? { id: Number(mosaicCam), name: `Camera ${mosaicCam}` }
            : { ...mosaicCam, id: mosaicCam.id ?? idx }
          
          return assignConnectionKey(base, `mosaic-${mosaicId}-${idx}`)
        })
      }
      
    } catch (err) {
      console.error('[useSiteCameras] Erro ao carregar mosaico:', err)
      error.value = err
      cameras.value = []
      currentMosaic.value = null
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Inicia streams de todas as câmeras em paralelo (Promise.all)
   * Usa playback_proxy_url prioritariamente, fallback para playback_url
   * 
   * @returns {Promise<void>}
   */
  async function startStreams() {
    const startTime = performance.now()
    console.log(`[useSiteCameras] 🚀 Iniciando ${cameras.value.length} streams em paralelo...`)
    
    const validCameras = cameras.value.filter(cam => cam.id)
    
    const promises = validCameras.map(async (camera) => {
      const camStartTime = performance.now()
      
      try {
        const startUrl = `/setup_app/api/gateways/${camera.id}/video/preview/start/`
        
        // Timeout de 8 segundos
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 8000)
        
        const response = await api.post(startUrl, {}, { signal: controller.signal })
        clearTimeout(timeoutId)
        
        const apiTime = performance.now() - camStartTime
        
        if (response && response.success && response.playback_url) {
          // Priorizar playback_proxy_url
          camera.playback_url = response.playback_proxy_url || response.playback_url
          console.log(`[useSiteCameras] ✅ ${camera.name} - API: ${apiTime.toFixed(0)}ms`)
          return { success: true, camera, apiTime }
        } else {
          console.error(`[useSiteCameras] ❌ Falha: ${camera.name} - API: ${apiTime.toFixed(0)}ms`, response)
          return { success: false, camera, apiTime }
        }
      } catch (err) {
        const apiTime = performance.now() - camStartTime
        
        if (err.name === 'AbortError') {
          console.error(`[useSiteCameras] ⏱️ Timeout: ${camera.name} - 8000ms`)
        } else {
          console.error(`[useSiteCameras] ❌ Erro: ${camera.name} - API: ${apiTime.toFixed(0)}ms`, err)
        }
        
        return { success: false, camera, apiTime, error: err }
      }
    })
    
    const results = await Promise.all(promises)
    const totalTime = performance.now() - startTime
    const successCount = results.filter(r => r.success).length
    const avgApiTime = results.reduce((sum, r) => sum + (r.apiTime || 0), 0) / results.length
    
    console.log(
      `[useSiteCameras] ⏱️ Total: ${totalTime.toFixed(0)}ms | ` +
      `API média: ${avgApiTime.toFixed(0)}ms | ` +
      `Sucesso: ${successCount}/${validCameras.length}`
    )
  }
  
  /**
   * Para streams de todas as câmeras e limpa estado
   * 
   * @returns {Promise<void>}
   */
  async function stopStreams() {
    console.log('[useSiteCameras] Parando streams...')
    
    for (const camera of cameras.value) {
      if (!camera.gateway_id) continue
      
      try {
        const stopUrl = `/setup_app/api/gateways/${camera.gateway_id}/video/preview/stop/`
        await api.post(stopUrl, { camera_id: camera.id })
        console.log(`[useSiteCameras] Stream parado: ${camera.name}`)
      } catch (err) {
        console.error(`[useSiteCameras] Erro ao parar stream ${camera.name}:`, err)
      }
    }
    
    // Limpar estado
    cameras.value = []
    currentMosaic.value = null
  }
  
  /**
   * Derivar WHEP URL a partir de playback_url HLS
   * Exemplo: http://localhost:8082/hls/live/gateway_123/index.m3u8
   *       -> http://localhost:8082/whep/live/gateway_123
   * 
   * @param {string} playbackUrl - URL HLS
   * @returns {string|null} WHEP URL derivado ou null
   */
  function deriveWhepUrl(playbackUrl) {
    if (!playbackUrl || typeof playbackUrl !== 'string') return null
    
    try {
      const match = playbackUrl.match(/\/hls\/(live\/[^\/]+)/)
      if (match) {
        return playbackUrl.replace(/\/hls\/(live\/[^\/]+).*/, '/whep/$1')
      }
    } catch (err) {
      console.warn('[useSiteCameras] Erro ao derivar WHEP URL:', err)
    }
    
    return null
  }
  
  /**
   * Atribui connectionKey único para câmera (usado em WebRTC)
   * 
   * @param {Object} camera - Objeto da câmera
   * @param {string} key - Chave de conexão
   * @returns {Object} Câmera com connectionKey
   */
  function assignConnectionKey(camera, key) {
    camera.connectionKey = key
    return camera
  }
  
  return {
    // Estado
    mosaics,
    cameras,
    currentMosaic,
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
