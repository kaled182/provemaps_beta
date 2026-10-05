/**
 * Serviço para buscar dados de cabos de fibra óptica
 */

import { useApi } from '@/composables/useApi'
import { formatOpticalSeries } from '@/utils/opticalSeries'

const { get, post, patch, delete: del } = useApi()

/**
 * Busca status óptico em cache de um cabo
 */
export async function getCableOpticalStatus(cableId) {
  try {
    console.log('[FiberService] Buscando status óptico para cabo', cableId)
    const response = await get(`/api/v1/inventory/fibers/${cableId}/cached-status/`)
    console.log('[FiberService] Status óptico recebido:', response)
    return response
  } catch (error) {
    console.error('[FiberService] Erro ao buscar status óptico:', error)
    return null
  }
}

/**
 * Busca histórico óptico de uma porta do Zabbix
 */
export async function getPortOpticalHistory(portId, hours = 24) {
  try {
    console.log(`[FiberService] Buscando histórico óptico da porta ${portId} (${hours}h)`)
    const response = await get(`/api/v1/ports/${portId}/optical_history/?hours=${hours}`)
    console.log(`[FiberService] Histórico recebido:`, response)
    return response
  } catch (error) {
    console.error('[FiberService] Erro ao buscar histórico óptico:', error)
    return null
  }
}

/**
 * Busca histórico óptico completo de um cabo (origem + destino) em uma única requisição.
 * O backend paraleliza todas as chamadas ao Zabbix server-side.
 */
export async function getCableOpticalHistory(cableId, hours = 24) {
  try {
    console.log(`[FiberService] Buscando histórico completo do cabo ${cableId}`)

    const response = await get(`/api/v1/fiber-cables/${cableId}/optical-history/?hours=${hours}`)
    if (!response || (!response.origin_history?.length && !response.destination_history?.length)) {
      console.warn('[FiberService] Sem dados ópticos disponíveis')
      return null
    }

    // Adaptar resposta para o formato esperado pelo modal
    const cableStatus = response
    const originHistory = response.origin_history || []
    const destHistory = response.destination_history || []

    const extractThresholds = (opticalInfo) => {
      const parseValue = (value) => {
        if (value === null || value === undefined) {
          return null
        }
        const numeric = Number(value)
        return Number.isFinite(numeric) ? numeric : null
      }

      return {
        warning: parseValue(opticalInfo?.warning_threshold ?? opticalInfo?.warningThreshold),
        critical: parseValue(opticalInfo?.critical_threshold ?? opticalInfo?.criticalThreshold)
      }
    }
    
    // EV-0010: sem forward-fill — um ponto sem valor é um buraco no gráfico.
    const formatPortData = (historyArray, thresholds) => formatOpticalSeries(historyArray, thresholds)
    
    const calculatePortStats = (historyArray) => {
      if (!historyArray || historyArray.length === 0) {
        return { avgRx: 0, avgTx: 0, minRx: 0, maxRx: 0, minTx: 0, maxTx: 0 }
      }
      
      const rxValues = historyArray.map(p => p.rx_power).filter(v => v !== null && v !== undefined)
      const txValues = historyArray.map(p => p.tx_power).filter(v => v !== null && v !== undefined)
      
      return {
        avgRx: rxValues.length > 0 ? rxValues.reduce((a, b) => a + b, 0) / rxValues.length : 0,
        minRx: rxValues.length > 0 ? Math.min(...rxValues) : 0,
        maxRx: rxValues.length > 0 ? Math.max(...rxValues) : 0,
        avgTx: txValues.length > 0 ? txValues.reduce((a, b) => a + b, 0) / txValues.length : 0,
        minTx: txValues.length > 0 ? Math.min(...txValues) : 0,
        maxTx: txValues.length > 0 ? Math.max(...txValues) : 0
      }
    }
    
    const originThresholds = extractThresholds(cableStatus.origin_optical)
    const destinationThresholds = extractThresholds(cableStatus.destination_optical)

    return {
      origin: formatPortData(originHistory, originThresholds),
      destination: formatPortData(destHistory, destinationThresholds),
      portInfo: {
        origin: {
          device: cableStatus.origin_optical?.device_name || 'Dispositivo Origem',
          port: cableStatus.origin_optical?.port_name || 'Porta não identificada'
        },
        destination: {
          device: cableStatus.destination_optical?.device_name || 'Dispositivo Destino',
          port: cableStatus.destination_optical?.port_name || 'Porta não identificada'
        }
      },
      stats: {
        origin: calculatePortStats(originHistory),
        destination: calculatePortStats(destHistory)
      },
      thresholds: {
        origin: originThresholds,
        destination: destinationThresholds
      }
    }
  } catch (error) {
    console.error('[FiberService] Erro ao buscar histórico do cabo:', error)
    return null
  }
}

/**
 * Busca detalhes completos de um cabo
 */
export async function getCableDetails(cableId) {
  try {
    const response = await get(`/api/v1/fiber-cables/${cableId}/`)
    return response
  } catch (error) {
    console.error('[FiberService] Erro ao buscar detalhes do cabo:', error)
    return null
  }
}

/**
 * Busca alarmes de um cabo (se houver endpoint)
 */
export async function getCableAlarms(cableId) {
  try {
    if (!cableId) {
      return []
    }

    const response = await get(`/api/v1/fiber-cables/${cableId}/alarms/`)

    if (!response) {
      return []
    }

    if (Array.isArray(response)) {
      return response
    }

    if (Array.isArray(response?.results)) {
      return response.results
    }

    if (Array.isArray(response?.data)) {
      return response.data
    }

    if (Array.isArray(response?.alarms)) {
      return response.alarms
    }

    return []
  } catch (error) {
    if (error?.response?.status === 404) {
      console.warn('[FiberService] Endpoint de alarmes não disponível para este cabo, retornando lista vazia')
      return []
    }
    console.error('[FiberService] Erro ao buscar alarmes:', error)
    return []
  }
}

export async function createCableAlarm(cableId, payload) {
  if (!cableId) {
    throw new Error('Cabo inválido para salvar alarme')
  }

  try {
    const response = await post(`/api/v1/fiber-cables/${cableId}/alarms/`, payload)
    return response
  } catch (error) {
    console.error('[FiberService] Erro ao criar configuração de alarme:', error)
    throw error
  }
}

export async function deleteCableAlarm(cableId, alarmId) {
  try {
    await del(`/api/v1/fiber-cables/${cableId}/alarms/${alarmId}/`)
  } catch (error) {
    console.error('[FiberService] Erro ao excluir configuração de alarme:', error)
    throw error
  }
}

export async function updateCableAlarm(cableId, alarmId, payload) {
  try {
    const response = await patch(`/api/v1/fiber-cables/${cableId}/alarms/${alarmId}/`, payload)
    return response
  } catch (error) {
    console.error('[FiberService] Erro ao atualizar configuração de alarme:', error)
    throw error
  }
}

/**
 * Histórico de notificações de alarme do cabo (últimos N envios).
 * Inclui automáticos (Celery dispatcher) e manuais (botão Enviar Teste).
 */
export async function getCableAlarmNotifications(cableId, limit = 50) {
  try {
    const response = await get(`/api/v1/fiber-cables/${cableId}/alarm-notifications/?limit=${limit}`)
    return response
  } catch (error) {
    console.error('[FiberService] Erro ao carregar histórico de notificações:', error)
    throw error
  }
}

/**
 * Envia mensagem de TESTE real para os destinatários da config.
 * Útil para validar que o gateway WhatsApp + telefones funcionam.
 * Retorna { ok, sent, total, results, message }.
 */
export async function testCableAlarm(cableId, alarmId) {
  try {
    const response = await post(`/api/v1/fiber-cables/${cableId}/alarms/${alarmId}/test/`, {})
    return response
  } catch (error) {
    console.error('[FiberService] Erro ao enviar alarme de teste:', error)
    throw error
  }
}

/**
 * Silencia (snooze) ou retoma notificações automáticas de uma config.
 * - hours > 0  → silencia por N horas a partir de agora
 * - hours = 0 ou null → remove o snooze
 */
export async function snoozeCableAlarm(cableId, alarmId, hours) {
  try {
    const response = await post(`/api/v1/fiber-cables/${cableId}/alarms/${alarmId}/snooze/`, { hours })
    return response
  } catch (error) {
    console.error('[FiberService] Erro ao alterar snooze do alarme:', error)
    throw error
  }
}

/**
 * Busca histórico de tráfego de rede (IN/OUT) de ambas as portas do cabo.
 * O backend paraleliza as chamadas ao Zabbix server-side.
 */
export async function getCableTrafficHistory(cableId, hours = 24) {
  try {
    const response = await get(`/api/v1/fiber-cables/${cableId}/traffic-history/?hours=${hours}`)
    return response || null
  } catch (error) {
    console.error('[FiberService] Erro ao buscar tráfego do cabo:', error)
    return null
  }
}
