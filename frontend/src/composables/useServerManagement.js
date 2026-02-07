/**
 * Composable para gerenciamento de servidores de monitoramento
 * 
 * Responsabilidades:
 * - Gerenciar CRUD de servidores de monitoramento (Zabbix, Prometheus, etc)
 * - Validar configurações de servidor
 * - Gerenciar extra_config (JSON)
 * - Controlar estado ativo/inativo de servidores
 * 
 * @module useServerManagement
 */

import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

/**
 * Composable para gerenciamento de servidores de monitoramento
 * @returns {Object} Objetos e funções para gerenciar servidores
 */
export function useServerManagement() {
  const api = useApi()
  const notify = useNotification()

  // Estado
  const loading = ref(false)
  const error = ref(null)
  const servers = ref([])

  // Computed
  const hasServers = computed(() => servers.value.length > 0)
  
  const activeServers = computed(() => 
    servers.value.filter(s => s.is_active)
  )
  
  const inactiveServers = computed(() => 
    servers.value.filter(s => !s.is_active)
  )

  const serverCount = computed(() => ({
    total: servers.value.length,
    active: activeServers.value.length,
    inactive: inactiveServers.value.length,
  }))

  const serversByType = computed(() => {
    const types = {}
    servers.value.forEach(server => {
      const type = server.server_type || 'unknown'
      if (!types[type]) {
        types[type] = []
      }
      types[type].push(server)
    })
    return types
  })

  // Métodos

  /**
   * Carrega todos os servidores da API
   * @returns {Promise<void>}
   */
  const loadServers = async () => {
    try {
      loading.value = true
      error.value = null
      
      console.log('[useServerManagement] Loading servers from API...')
      const res = await api.get('/setup_app/api/monitoring-servers/')
      console.log('[useServerManagement] API response:', res)
      
      if (res.success !== false) {
        servers.value = res.servers || []
        console.log('[useServerManagement] Servers loaded:', servers.value)
      } else {
        console.warn('[useServerManagement] Invalid response format:', res)
      }
    } catch (e) {
      error.value = e.message || 'Erro ao carregar servidores'
      console.error('[useServerManagement] Error loading servers:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * Salva servidor (criar ou atualizar)
   * @param {Object} serverData - Dados do servidor
   * @param {string} serverData.id - ID (se atualização)
   * @param {string} serverData.name - Nome do servidor
   * @param {string} serverData.server_type - Tipo (zabbix, prometheus, etc)
   * @param {string} serverData.url - URL da API
   * @param {string} serverData.auth_token - Token de autenticação
   * @param {boolean} serverData.is_active - Ativo/Inativo
   * @param {Object|string} serverData.extra_config - Configurações extras (JSON)
   * @returns {Promise<Object|null>} Servidor salvo ou null
   */
  const saveServer = async (serverData) => {
    try {
      loading.value = true
      error.value = null
      
      // Parse extra_config se for string
      let extraConfig = {}
      if (serverData.extra_config) {
        if (typeof serverData.extra_config === 'string') {
          try {
            extraConfig = JSON.parse(serverData.extra_config)
          } catch (e) {
            notify.error('Servidores', 'JSON inválido em extra_config.')
            return null
          }
        } else {
          extraConfig = serverData.extra_config
        }
      }
      
      // Também aceita extra_config_text (campo do formulário)
      if (serverData.extra_config_text && typeof serverData.extra_config_text === 'string') {
        try {
          extraConfig = JSON.parse(serverData.extra_config_text)
        } catch (e) {
          notify.error('Servidores', 'JSON inválido.')
          return null
        }
      }

      const payload = {
        name: serverData.name,
        server_type: serverData.server_type || 'zabbix',
        url: serverData.url,
        auth_token: serverData.auth_token || '',
        is_active: serverData.is_active ?? true,
        extra_config: extraConfig,
      }

      let res
      if (serverData.id) {
        res = await api.patch(`/setup_app/api/monitoring-servers/${serverData.id}/`, payload)
        notify.success('Servidores', res.message || 'Atualizado!')
      } else {
        res = await api.post('/setup_app/api/monitoring-servers/', payload)
        notify.success('Servidores', res.message || 'Criado!')
      }

      if (res.success !== false) {
        await loadServers()
        return res.server || payload
      } else {
        notify.error('Servidores', res.message || 'Erro ao salvar servidor.')
        return null
      }
    } catch (e) {
      error.value = e.message || 'Erro ao salvar servidor'
      notify.error('Servidores', e.message || 'Erro ao salvar servidor.')
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Deleta servidor
   * @param {string|number} serverId - ID do servidor
   * @param {boolean} confirm - Se deve confirmar antes de deletar (padrão: true)
   * @returns {Promise<boolean>} true se deletou com sucesso
   */
  const deleteServer = async (serverId, confirm = true) => {
    if (confirm && !window.confirm('Remover servidor de monitoramento?')) {
      return false
    }
    
    try {
      loading.value = true
      error.value = null
      
      const res = await api.delete(`/setup_app/api/monitoring-servers/${serverId}/`)
      
      if (res.success !== false) {
        notify.success('Servidores', res.message || 'Removido.')
        await loadServers()
        return true
      } else {
        notify.error('Servidores', res.message || 'Erro ao remover.')
        return false
      }
    } catch (e) {
      error.value = e.message || 'Erro ao remover servidor'
      notify.error('Servidores', e.message || 'Erro ao remover.')
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Testa conexão com servidor
   * @param {Object} serverData - Dados do servidor para testar
   * @returns {Promise<Object|null>} Resultado do teste ou null
   */
  const testServerConnection = async (serverData) => {
    try {
      loading.value = true
      error.value = null
      
      const payload = {
        server_type: serverData.server_type,
        url: serverData.url,
        auth_token: serverData.auth_token,
        extra_config: typeof serverData.extra_config === 'string' 
          ? JSON.parse(serverData.extra_config) 
          : serverData.extra_config,
      }
      
      const res = await api.post('/setup_app/api/monitoring-servers/test/', payload)
      
      if (res.success) {
        notify.success('Teste', res.message || 'Conexão bem-sucedida!')
        return res
      } else {
        notify.error('Teste', res.message || 'Falha na conexão.')
        return null
      }
    } catch (e) {
      error.value = e.message || 'Erro ao testar conexão'
      notify.error('Teste', e.message || 'Erro ao testar conexão.')
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Ativa/desativa servidor
   * @param {string|number} serverId - ID do servidor
   * @param {boolean} isActive - Novo estado
   * @returns {Promise<boolean>} true se alterou com sucesso
   */
  const toggleServerStatus = async (serverId, isActive) => {
    const server = servers.value.find(s => s.id === serverId)
    if (!server) {
      notify.error('Servidores', 'Servidor não encontrado.')
      return false
    }
    
    return await saveServer({
      ...server,
      is_active: isActive,
    })
  }

  /**
   * Busca servidor por ID
   * @param {string|number} serverId - ID do servidor
   * @returns {Object|null} Servidor encontrado ou null
   */
  const getServerById = (serverId) => {
    return servers.value.find(s => s.id === serverId) || null
  }

  /**
   * Busca servidores por tipo
   * @param {string} type - Tipo do servidor (zabbix, prometheus, etc)
   * @returns {Array} Lista de servidores do tipo
   */
  const getServersByType = (type) => {
    return servers.value.filter(s => s.server_type === type)
  }

  /**
   * Valida extra_config JSON
   * @param {string} jsonString - String JSON a validar
   * @returns {Object} { valid: boolean, error?: string, parsed?: Object }
   */
  const validateExtraConfig = (jsonString) => {
    if (!jsonString || jsonString.trim() === '') {
      return { valid: true, parsed: {} }
    }
    
    try {
      const parsed = JSON.parse(jsonString)
      return { valid: true, parsed }
    } catch (e) {
      return { valid: false, error: e.message }
    }
  }

  /**
   * Cria objeto de formulário vazio para novo servidor
   * @param {Object} defaults - Valores padrão opcionais
   * @returns {Object} Formulário de servidor
   */
  const createEmptyServerForm = (defaults = {}) => {
    return {
      name: defaults.name || '',
      server_type: defaults.server_type || 'zabbix',
      url: defaults.url || '',
      auth_token: defaults.auth_token || '',
      is_active: defaults.is_active ?? true,
      extra_config_text: defaults.extra_config_text || '{}',
    }
  }

  /**
   * Converte servidor para objeto de formulário
   * @param {Object} server - Servidor a converter
   * @returns {Object} Formulário de servidor
   */
  const serverToForm = (server) => {
    if (!server) return createEmptyServerForm()
    
    return {
      id: server.id,
      name: server.name || '',
      server_type: server.server_type || 'zabbix',
      url: server.url || '',
      auth_token: '', // Não preencher token por segurança
      is_active: server.is_active ?? true,
      extra_config_text: JSON.stringify(server.extra_config || {}, null, 2),
    }
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
    servers,
    
    // Computed
    hasServers,
    activeServers,
    inactiveServers,
    serverCount,
    serversByType,
    
    // Métodos CRUD
    loadServers,
    saveServer,
    deleteServer,
    testServerConnection,
    toggleServerStatus,
    
    // Utilitários
    getServerById,
    getServersByType,
    validateExtraConfig,
    createEmptyServerForm,
    serverToForm,
    clearError,
  }
}
