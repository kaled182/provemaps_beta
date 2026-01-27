import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'

/**
 * Composable para gerenciar cabos de fibra ótica de um site
 * 
 * @returns {Object} Estado e métodos para gerenciar fibras
 * 
 * @example
 * ```js
 * const { 
 *   fibers, 
 *   fiberCount,
 *   hasFibers,
 *   fetchFibers, 
 *   refreshFibers,
 *   loading,
 *   error
 * } = useSiteFibers()
 * 
 * await fetchFibers(siteId)
 * ```
 */
export function useSiteFibers() {
  const api = useApi()
  
  // Estado reativo
  const fibers = ref([])
  const loading = ref(false)
  const error = ref(null)
  
  // Computed properties
  const hasFibers = computed(() => fibers.value.length > 0)
  const fiberCount = computed(() => fibers.value.length)
  
  // Estatísticas úteis
  const connectedFibers = computed(() => 
    fibers.value.filter(f => f.connection_status !== 'floating')
  )
  
  const activeFibers = computed(() => 
    fibers.value.filter(f => f.status === 'up' || f.status === 'active')
  )
  
  const totalLength = computed(() => {
    return fibers.value.reduce((sum, fiber) => {
      const length = fiber.length_km || 0
      return sum + parseFloat(length)
    }, 0)
  })
  
  /**
   * Busca lista de cabos de fibra conectados ao site
   * 
   * @param {number} siteId - ID do site
   * @returns {Promise<void>}
   */
  async function fetchFibers(siteId) {
    if (!siteId) {
      console.warn('[useSiteFibers] siteId não fornecido')
      return
    }
    
    loading.value = true
    error.value = null
    
    try {
      const response = await api.get(`/api/v1/sites/${siteId}/fiber_cables/`)
      
      if (response && response.fibers) {
        fibers.value = response.fibers
        console.log(`[useSiteFibers] ${response.fiber_count} fibras carregadas para site ${siteId}`)
      } else {
        fibers.value = []
      }
    } catch (err) {
      console.error('[useSiteFibers] Erro ao buscar fibras:', err)
      error.value = err
      fibers.value = []
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Atualiza lista de fibras (alias para fetchFibers)
   * 
   * @param {number} siteId - ID do site
   * @returns {Promise<void>}
   */
  async function refreshFibers(siteId) {
    return fetchFibers(siteId)
  }
  
  /**
   * Limpa estado de fibras (útil ao fechar modal)
   * 
   * @returns {void}
   */
  function clearFibers() {
    fibers.value = []
    error.value = null
    loading.value = false
  }
  
  /**
   * Formata comprimento do cabo (m ou km)
   * 
   * @param {number} lengthKm - Comprimento em km
   * @returns {string} String formatada
   */
  function formatLength(lengthKm) {
    if (!lengthKm || lengthKm === 0) return '-'
    
    const km = parseFloat(lengthKm)
    
    if (km < 1) {
      return `${(km * 1000).toFixed(0)} m`
    }
    
    return `${km.toFixed(2)} km`
  }
  
  /**
   * Retorna classe CSS baseada no status do cabo
   * 
   * @param {string} status - Status do cabo (up, down, degraded, unknown)
   * @returns {string} Nome da classe CSS
   */
  function getStatusClass(status) {
    const statusMap = {
      'up': 'status-up',
      'active': 'status-up',
      'down': 'status-down',
      'degraded': 'status-degraded',
      'planned': 'status-planned',
      'unknown': 'status-unknown'
    }
    
    return statusMap[status] || 'status-unknown'
  }
  
  /**
   * Retorna label traduzido para o status
   * 
   * @param {string} status - Status do cabo
   * @returns {string} Label em português
   */
  function getStatusLabel(status) {
    const labelMap = {
      'up': 'Ativo',
      'active': 'Ativo',
      'down': 'Inativo',
      'degraded': 'Degradado',
      'planned': 'Planejado',
      'unknown': 'Desconhecido'
    }
    
    return labelMap[status] || 'Desconhecido'
  }
  
  /**
   * Retorna label para connection_status
   * 
   * @param {string} connectionStatus - Status da conexão (floating, logical, physical)
   * @returns {string} Label em português
   */
  function getConnectionLabel(connectionStatus) {
    const labelMap = {
      'floating': 'Não Conectado',
      'logical': 'Conexão Lógica',
      'physical': 'Conexão Física'
    }
    
    return labelMap[connectionStatus] || 'Indefinido'
  }
  
  return {
    // Estado
    fibers,
    loading,
    error,
    
    // Computed
    hasFibers,
    fiberCount,
    connectedFibers,
    activeFibers,
    totalLength,
    
    // Métodos
    fetchFibers,
    refreshFibers,
    clearFibers,
    
    // Utilitários
    formatLength,
    getStatusClass,
    getStatusLabel,
    getConnectionLabel
  }
}
