/**
 * Serviço para buscar dados de cabos de fibra óptica
 */

import { useApi } from '@/composables/useApi'

const { get } = useApi()

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
 * Busca histórico óptico completo de um cabo (origem + destino)
 * Retorna dados separados por porta com informações de dispositivo
 */
export async function getCableOpticalHistory(cableId, hours = 24) {
  try {
    console.log(`[FiberService] Buscando histórico completo do cabo ${cableId}`)
    
    // Primeiro buscar informações do cabo para obter port_ids e device info
    const cableStatus = await getCableOpticalStatus(cableId)
    if (!cableStatus || !cableStatus.origin_port_id || !cableStatus.destination_port_id) {
      console.warn('[FiberService] Cabo não possui portas configuradas')
      return null
    }
    
    // Buscar histórico de ambas as portas em paralelo
    const [originHistory, destHistory] = await Promise.all([
      getPortOpticalHistory(cableStatus.origin_port_id, hours),
      getPortOpticalHistory(cableStatus.destination_port_id, hours)
    ])
    
    // Processar dados separadamente para cada porta
    const formatPortData = (historyArray) => {
      if (!historyArray || historyArray.length === 0) return null

      // Garantir ordenação por timestamp e alinhar as séries por tempo
      const sorted = [...historyArray].sort((a, b) => {
        const ta = new Date(a.timestamp).getTime()
        const tb = new Date(b.timestamp).getTime()
        return ta - tb
      })

      const labels = []
      const rxData = []
      const txData = []

      // Forward-fill: mantém último valor conhecido quando o ponto vier como null
      // Evita que uma das linhas termine antes da outra
      let lastRx = null
      let lastTx = null

      sorted.forEach(point => {
        const date = new Date(point.timestamp)
        labels.push(date.toLocaleTimeString('pt-BR', {
          hour: '2-digit',
          minute: '2-digit',
          day: '2-digit',
          month: '2-digit'
        }))

        const rx = point.rx_power
        const tx = point.tx_power

        // RX: só começa a preencher após primeiro valor válido; depois faz forward-fill
        if (rx !== null && rx !== undefined && !Number.isNaN(rx)) {
          lastRx = rx
          rxData.push(rx)
        } else {
          rxData.push(lastRx)
        }

        // TX: mesma lógica do RX
        if (tx !== null && tx !== undefined && !Number.isNaN(tx)) {
          lastTx = tx
          txData.push(tx)
        } else {
          txData.push(lastTx)
        }
      })

      return { labels, rxData, txData }
    }
    
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
    
    return {
      origin: formatPortData(originHistory),
      destination: formatPortData(destHistory),
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
    // TODO: Verificar se existe endpoint específico para alarmes de cabo
    // Por enquanto retorna array vazio
    return []
  } catch (error) {
    console.error('[FiberService] Erro ao buscar alarmes:', error)
    return []
  }
}
