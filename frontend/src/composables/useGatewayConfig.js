/**
 * Composable para gerenciamento de gateways de comunicação
 * 
 * Responsabilidades:
 * - Gerenciar CRUD de gateways (SMS, WhatsApp, Telegram, SMTP, Vídeo)
 * - Teste de conexão/envio de mensagens
 * - Gerenciar estado de QR code do WhatsApp
 * - Preview de vídeo
 * 
 * @module useGatewayConfig
 */

import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

/**
 * Composable para gerenciamento de gateways
 * @returns {Object} Objetos e funções para gerenciar gateways
 */
export function useGatewayConfig() {
  const api = useApi()
  const notify = useNotification()

  // Estado
  const loading = ref(false)
  const error = ref(null)
  const gateways = ref([])
  const activeGatewayType = ref('sms') // sms, whatsapp, telegram, smtp, video

  // Estados de teste
  const testingConnection = ref(false)
  const testResult = ref(null)

  // Computed - Gateways por tipo
  const smsGateways = computed(() => 
    gateways.value.filter(g => g.gateway_type === 'sms')
  )
  
  const whatsappGateways = computed(() => 
    gateways.value.filter(g => g.gateway_type === 'whatsapp')
  )
  
  const telegramGateways = computed(() => 
    gateways.value.filter(g => g.gateway_type === 'telegram')
  )
  
  const smtpGateways = computed(() => 
    gateways.value.filter(g => g.gateway_type === 'smtp')
  )
  
  const videoGateways = computed(() => 
    gateways.value.filter(g => g.gateway_type === 'video')
  )

  const hasGateways = computed(() => gateways.value.length > 0)
  
  const gatewayCount = computed(() => ({
    sms: smsGateways.value.length,
    whatsapp: whatsappGateways.value.length,
    telegram: telegramGateways.value.length,
    smtp: smtpGateways.value.length,
    video: videoGateways.value.length,
    total: gateways.value.length,
  }))

  // Métodos

  /**
   * Carrega todos os gateways da API
   * @returns {Promise<void>}
   */
  const loadGateways = async () => {
    try {
      loading.value = true
      error.value = null
      
      const res = await api.get('/setup_app/api/gateways/')
      
      console.log('[useGatewayConfig] API Response:', res)
      
      if (res.success) {
        gateways.value = res.gateways || []
        console.log('[useGatewayConfig] Gateways loaded:', gateways.value.length, gateways.value)
        
        // Enriquecer gateways WhatsApp com status de conexão
        await enrichWhatsAppConnectionStatus()
      }
    } catch (e) {
      console.error('[useGatewayConfig] Error loading gateways:', e)
      error.value = e.message || 'Erro ao carregar gateways'
      notify.error('Gateways', e.message || 'Erro ao carregar gateways.')
    } finally {
      loading.value = false
    }
  }

  /**
   * Enriquece gateways WhatsApp com status de conexão em tempo real
   * @returns {Promise<void>}
   */
  const enrichWhatsAppConnectionStatus = async () => {
    const whatsAppGws = gateways.value.filter(g => g.gateway_type === 'whatsapp')
    
    if (whatsAppGws.length === 0) return
    
    console.log('[useGatewayConfig] Enriching WhatsApp gateways with connection status...')
    
    // Buscar status de todos os gateways WhatsApp em paralelo
    const statusPromises = whatsAppGws.map(async (gateway) => {
      try {
        const qrServiceUrl = gateway.config?.qr_service_url || ''
        const result = await checkWhatsappQRStatus(gateway.id, qrServiceUrl)
        
        if (result) {
          return {
            id: gateway.id,
            connection_status: result.qr_status || result.status || 'disconnected',
            last_connection: result.updated_at || null
          }
        }
      } catch (error) {
        console.error(`[useGatewayConfig] Error checking status for gateway ${gateway.id}:`, error)
        return {
          id: gateway.id,
          connection_status: 'error',
          last_connection: null
        }
      }
    })
    
    const statuses = await Promise.all(statusPromises)
    
    // Atualizar gateways com os status
    gateways.value = gateways.value.map(gateway => {
      if (gateway.gateway_type !== 'whatsapp') return gateway
      
      const statusInfo = statuses.find(s => s && s.id === gateway.id)
      if (statusInfo) {
        return {
          ...gateway,
          connection_status: statusInfo.connection_status,
          last_connection: statusInfo.last_connection
        }
      }
      
      return gateway
    })
    
    console.log('[useGatewayConfig] WhatsApp gateways enriched with connection status')
  }

  /**
   * Salva gateway (criar ou atualizar)
   * @param {Object} gatewayData - Dados do gateway
   * @param {string} gatewayData.id - ID (se atualização)
   * @param {string} gatewayData.name - Nome do gateway
   * @param {string} gatewayData.gateway_type - Tipo (sms, whatsapp, etc)
   * @param {string} gatewayData.provider - Provider
   * @param {number} gatewayData.priority - Prioridade
   * @param {boolean} gatewayData.enabled - Ativo/Inativo
   * @param {Object} gatewayData.config - Configurações específicas
   * @returns {Promise<Object|null>} Gateway salvo ou null
   */
  const saveGateway = async (gatewayData) => {
    try {
      loading.value = true
      error.value = null
      
      const payload = {
        id: gatewayData.id,
        name: gatewayData.name,
        gateway_type: gatewayData.gateway_type,
        provider: gatewayData.provider,
        priority: gatewayData.priority,
        enabled: gatewayData.enabled,
        config: gatewayData.config,
      }

      let res
      if (payload.id) {
        res = await api.patch(`/setup_app/api/gateways/${payload.id}/`, payload)
      } else {
        res = await api.post('/setup_app/api/gateways/', payload)
      }

      if (res.success) {
        notify.success('Gateways', res.message || 'Gateway salvo.')
        await loadGateways()
        return res.gateway || payload
      } else {
        notify.error('Gateways', res.message || 'Erro ao salvar gateway.')
        return null
      }
    } catch (e) {
      error.value = e.message || 'Erro ao salvar gateway'
      notify.error('Gateways', e.message || 'Erro ao salvar gateway.')
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Deleta gateway
   * @param {string|number} gatewayId - ID do gateway
   * @returns {Promise<boolean>} true se deletou com sucesso
   */
  const deleteGateway = async (gatewayId) => {
    try {
      loading.value = true
      error.value = null
      
      const res = await api.delete(`/setup_app/api/gateways/${gatewayId}/`)
      
      if (res.success) {
        notify.success('Gateways', res.message || 'Gateway removido.')
        await loadGateways()
        return true
      } else {
        notify.error('Gateways', res.message || 'Erro ao remover gateway.')
        return false
      }
    } catch (e) {
      error.value = e.message || 'Erro ao remover gateway'
      notify.error('Gateways', e.message || 'Erro ao remover gateway.')
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Testa gateway específico
   * @param {string} gatewayType - Tipo do gateway
   * @param {Object} config - Configurações para teste
   * @returns {Promise<boolean>} true se teste passou
   */
  const testGateway = async (gatewayType, config) => {
    try {
      testingConnection.value = true
      testResult.value = null
      
      let endpoint = ''
      let payload = {}
      
      switch (gatewayType) {
        case 'sms':
          endpoint = '/setup_app/api/test-sms/'
          payload = {
            provider: config.provider,
            username: config.username,
            password: config.password,
            api_token: config.api_token,
            api_url: config.api_url,
            sender_id: config.sender_id,
            test_recipient: config.test_recipient,
            test_message: config.test_message,
          }
          break
        case 'smtp':
          endpoint = '/setup_app/api/test-smtp/'
          payload = {
            smtp_host: config.host,
            smtp_port: config.port,
            smtp_security: config.security,
            smtp_user: config.user,
            smtp_password: config.password,
            smtp_auth_mode: config.auth_mode,
            smtp_from_email: config.from_email,
            smtp_test_recipient: config.test_recipient,
          }
          break
        default:
          notify.warning('Teste', `Teste não implementado para ${gatewayType}`)
          return false
      }
      
      const res = await api.post(endpoint, payload)
      
      if (res.success) {
        notify.success(gatewayType.toUpperCase(), res.message || 'Teste bem-sucedido!')
        testResult.value = { success: true, message: res.message }
        return true
      } else {
        notify.error(gatewayType.toUpperCase(), res.message || 'Teste falhou')
        testResult.value = { success: false, message: res.message }
        return false
      }
    } catch (e) {
      const message = e.message || `Erro ao testar ${gatewayType}`
      notify.error(gatewayType.toUpperCase(), message)
      testResult.value = { success: false, message }
      return false
    } finally {
      testingConnection.value = false
    }
  }

  /**
   * Gera QR code para WhatsApp
   * @param {string|number} gatewayId - ID do gateway WhatsApp
   * @param {string} qrServiceUrl - URL do serviço de QR
   * @returns {Promise<Object|null>} Dados do QR ou null
   */
  const generateWhatsappQR = async (gatewayId, qrServiceUrl) => {
    try {
      loading.value = true
      
      console.log('[useGatewayConfig] generateWhatsappQR called with:', { gatewayId, qrServiceUrl })
      
      const res = await api.post(
        `/setup_app/api/gateways/${gatewayId}/whatsapp/qr/`,
        { qr_service_url: qrServiceUrl }
      )
      
      console.log('[useGatewayConfig] API response:', res)
      
      if (res.success) {
        notify.success('WhatsApp', res.message || 'QR gerado.')
        const result = {
          qr_status: res.qr_status,
          qr_image_url: res.qr_image_url,
          qr_code: res.qr_code,
        }
        console.log('[useGatewayConfig] Returning:', result)
        return result
      } else {
        notify.error('WhatsApp', res.message || 'Erro ao gerar QR.')
        return null
      }
    } catch (e) {
      console.error('[useGatewayConfig] Error generating QR:', e)
      notify.error('WhatsApp', e.message || 'Erro ao gerar QR.')
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Consulta status do QR code WhatsApp
   * @param {string|number} gatewayId - ID do gateway WhatsApp
   * @param {string} qrServiceUrl - URL do serviço de QR
   * @returns {Promise<Object|null>} Status do QR ou null
   */
  const checkWhatsappQRStatus = async (gatewayId, qrServiceUrl) => {
    try {
      const res = await api.get(
        `/setup_app/api/gateways/${gatewayId}/whatsapp/qr/status/`,
        { qr_service_url: qrServiceUrl }
      )
      
      if (res.success) {
        return {
          qr_status: res.qr_status,
          qr_image_url: res.qr_image_url,
          last_disconnect_reason: res.last_disconnect_reason,
          last_disconnect_message: res.last_disconnect_message,
        }
      }
      return null
    } catch (e) {
      console.error('[useGatewayConfig] Error checking WhatsApp QR status:', e)
      return null
    }
  }

  /**
   * Desconecta sessão WhatsApp QR
   * @param {string|number} gatewayId - ID do gateway WhatsApp
   * @param {string} qrServiceUrl - URL do serviço de QR
   * @returns {Promise<boolean>} true se desconectou
   */
  const disconnectWhatsappQR = async (gatewayId, qrServiceUrl) => {
    try {
      const res = await api.post(
        `/setup_app/api/gateways/${gatewayId}/whatsapp/qr/disconnect/`,
        { qr_service_url: qrServiceUrl }
      )
      
      if (res.success) {
        notify.success('WhatsApp', res.message || 'Desconectado.')
        await loadGateways() // Reload to update status
        return true
      } else {
        notify.error('WhatsApp', res.message || 'Erro ao desconectar.')
        return false
      }
    } catch (e) {
      notify.error('WhatsApp', e.message || 'Erro ao desconectar.')
      return false
    }
  }

  /**
   * Reseta sessão WhatsApp QR (limpa dados e desconecta)
   * @param {string|number} gatewayId - ID do gateway WhatsApp
   * @param {string} qrServiceUrl - URL do serviço de QR
   * @returns {Promise<boolean>} true se resetou
   */
  const resetWhatsappQR = async (gatewayId, qrServiceUrl) => {
    try {
      const res = await api.post(
        `/setup_app/api/gateways/${gatewayId}/whatsapp/qr/reset/`,
        { qr_service_url: qrServiceUrl }
      )
      
      if (res.success) {
        notify.success('WhatsApp', res.message || 'Sessão resetada.')
        await loadGateways() // Reload to update status
        return true
      } else {
        notify.error('WhatsApp', res.message || 'Erro ao resetar.')
        return false
      }
    } catch (e) {
      notify.error('WhatsApp', e.message || 'Erro ao resetar.')
      return false
    }
  }

  /**
   * Testa envio de mensagem WhatsApp
   * @param {string|number} gatewayId - ID do gateway
   * @param {string} recipient - Número do destinatário (formato: +5561999999999)
   * @param {string} message - Mensagem a enviar
   * @param {string} qrServiceUrl - URL do serviço QR (opcional)
   * @returns {Object|null} Resultado do teste
   */
  const testWhatsappMessage = async (gatewayId, recipient, message, qrServiceUrl = '') => {
    try {
      console.log('[useGatewayConfig] Testing WhatsApp message:', { gatewayId, recipient })
      
      // Usar endpoint Django que age como proxy para o serviço WhatsApp
      const res = await api.post(
        `/setup_app/api/gateways/${gatewayId}/whatsapp/qr/test-message/`,
        {
          recipient,
          message,
          qr_service_url: qrServiceUrl,
        }
      )
      
      console.log('[useGatewayConfig] Test message result:', res)
      
      if (res.success) {
        notify.success('WhatsApp', res.message || 'Mensagem enviada com sucesso!')
        return res
      } else {
        notify.error('WhatsApp', res.message || 'Erro ao enviar mensagem.')
        return null
      }
    } catch (e) {
      console.error('[useGatewayConfig] Test message error:', e)
      notify.error('WhatsApp', e.message || 'Erro ao enviar mensagem.')
      return null
    }
  }

  /**
   * Busca gateway por ID
   * @param {string|number} gatewayId - ID do gateway
   * @returns {Object|null} Gateway encontrado ou null
   */
  const getGatewayById = (gatewayId) => {
    return gateways.value.find(g => g.id === gatewayId) || null
  }

  /**
   * Busca gateways por tipo
   * @param {string} type - Tipo do gateway
   * @returns {Array} Lista de gateways do tipo
   */
  const getGatewaysByType = (type) => {
    return gateways.value.filter(g => g.gateway_type === type)
  }

  /**
   * Limpa estados de teste
   */
  const clearTestResults = () => {
    testResult.value = null
  }

  // Retorno do composable
  return {
    // Estado
    loading,
    error,
    gateways,
    activeGatewayType,
    testingConnection,
    testResult,
    
    // Computed
    smsGateways,
    whatsappGateways,
    telegramGateways,
    smtpGateways,
    videoGateways,
    hasGateways,
    gatewayCount,
    
    // Métodos
    loadGateways,
    saveGateway,
    deleteGateway,
    testGateway,
    generateWhatsappQR,
    checkWhatsappQRStatus,
    disconnectWhatsappQR,
    resetWhatsappQR,
    testWhatsappMessage,
    getGatewayById,
    getGatewaysByType,
    clearTestResults,
  }
}
