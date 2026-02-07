/**
 * useSiteDevices.js
 * Composable para gerenciar dispositivos de um site
 * 
 * Funcionalidades:
 * - Fetch de dispositivos por site ID
 * - Computed properties para estatísticas (online, warning, critical, offline)
 * - Utilities para formatação (uptime, status class, icons, metrics)
 */

import { ref, computed } from 'vue'
import { get } from '@/composables/useApi'

export function useSiteDevices() {
  // ===== State =====
  const devices = ref([])
  const loading = ref(false)
  const error = ref(null)

  // ===== Computed Properties =====
  
  /**
   * Retorna se há dispositivos carregados
   */
  const hasDevices = computed(() => devices.value.length > 0)

  /**
   * Retorna quantidade total de dispositivos
   */
  const deviceCount = computed(() => devices.value.length)

  /**
   * Retorna estatísticas de dispositivos por status
   */
  const deviceStats = computed(() => {
    const stats = {
      online: 0,
      warning: 0,
      critical: 0,
      offline: 0
    }
    
    devices.value.forEach(device => {
      const status = device.status?.toLowerCase()
      if (status === 'online') stats.online++
      else if (status === 'warning' || status === 'atenção') stats.warning++
      else if (status === 'critical' || status === 'crítico') stats.critical++
      else stats.offline++
    })
    
    return stats
  })

  /**
   * Retorna quantidade de dispositivos online
   */
  const onlineDevices = computed(() => deviceStats.value.online)

  /**
   * Retorna quantidade de dispositivos com warning
   */
  const warningDevices = computed(() => deviceStats.value.warning)

  /**
   * Retorna quantidade de dispositivos critical
   */
  const criticalDevices = computed(() => deviceStats.value.critical)

  /**
   * Retorna quantidade de dispositivos offline
   */
  const offlineDevices = computed(() => deviceStats.value.offline)

  // ===== Methods =====

  /**
   * Fetch dispositivos para um site específico
   * @param {number} siteId - ID do site
   */
  const fetchDevices = async (siteId) => {
    if (!siteId) {
      console.warn('[useSiteDevices] siteId é obrigatório')
      devices.value = []
      return
    }

    loading.value = true
    error.value = null

    try {
      console.log('[useSiteDevices] Carregando dispositivos para site:', siteId)

      // Buscar todos os devices e filtrar pelo site ID
      const response = await get('/api/v1/devices/')
      
      console.log('[useSiteDevices] Resposta da API:', {
        count: response.count,
        totalResults: response.results?.length
      })

      // Filtrar devices pelo site ID
      const devicesData = response.results?.filter(device => device.site === siteId) || []
      
      console.log('[useSiteDevices] Devices encontrados:', devicesData.length)

      // Mapear dados para formato usado no componente
      devices.value = devicesData.map(device => ({
        id: device.id,
        name: device.name || 'Dispositivo sem nome',
        type: device.group_name || 'Dispositivo',
        status: 'offline', // Será atualizado por integração com Zabbix
        cpu: device.cpu_usage_manual_percent || 0,
        memory: device.memory_usage_manual_percent || 0,
        uptime: device.uptime || 0,
        ip: device.primary_ip || 'N/A',
        zabbixHostId: device.zabbix_hostid,
        cpuItemKey: device.cpu_usage_item_key,
        memoryItemKey: device.memory_usage_item_key,
        uptimeItemKey: device.uptime_item_key,
      }))
    } catch (err) {
      console.error('[useSiteDevices] Erro ao buscar dispositivos:', err)
      error.value = err.message || 'Erro ao carregar dispositivos'
      devices.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * Refresh devices (alias para fetchDevices)
   * @param {number} siteId - ID do site
   */
  const refreshDevices = async (siteId) => {
    await fetchDevices(siteId)
  }

  /**
   * Limpa devices do state
   */
  const clearDevices = () => {
    devices.value = []
    error.value = null
    loading.value = false
  }

  // ===== Utility Functions =====

  /**
   * Retorna classe CSS para status
   * @param {string} status - Status do dispositivo
   * @returns {string} Classe CSS
   */
  const getStatusClass = (status) => {
    return status?.toLowerCase() || 'offline'
  }

  /**
   * Retorna label traduzido para status
   * @param {string} status - Status do dispositivo
   * @returns {string} Label traduzido
   */
  const getStatusLabel = (status) => {
    const labels = {
      online: 'Online',
      warning: 'Atenção',
      critical: 'Crítico',
      offline: 'Offline'
    }
    return labels[status?.toLowerCase()] || 'Offline'
  }

  /**
   * Retorna ícone para tipo de dispositivo
   * @param {string} type - Tipo do dispositivo
   * @returns {string} Classe do ícone FontAwesome
   */
  const getDeviceIcon = (type) => {
    const icons = {
      router: 'fas fa-network-wired',
      switch: 'fas fa-code-branch',
      server: 'fas fa-server',
      firewall: 'fas fa-shield-alt',
      default: 'fas fa-server'
    }
    return icons[type?.toLowerCase()] || icons.default
  }

  /**
   * Retorna classe CSS para métrica (CPU/Memory)
   * @param {number} value - Valor da métrica (0-100)
   * @returns {string} Classe CSS (normal, warning, critical)
   */
  const getMetricClass = (value) => {
    if (value >= 90) return 'critical'
    if (value >= 70) return 'warning'
    return 'normal'
  }

  /**
   * Formata segundos de uptime para texto legível
   * @param {number} seconds - Segundos de uptime
   * @returns {string} Uptime formatado (ex: "5d 3h", "2h 30m", "45m")
   */
  const formatUptime = (seconds) => {
    if (!seconds || seconds === 0) return 'N/A'
    
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (days > 0) return `${days}d ${hours}h`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  /**
   * Retorna tooltip completo para um dispositivo
   * @param {Object} device - Objeto do dispositivo
   * @returns {string} Texto do tooltip
   */
  const getDeviceTooltip = (device) => {
    const parts = [
      `${device.name}`,
      `Status: ${getStatusLabel(device.status)}`,
      `IP: ${device.ip}`,
    ]
    
    if (device.uptime) {
      parts.push(`Uptime: ${formatUptime(device.uptime)}`)
    }
    
    if (device.cpuItemKey) {
      parts.push(`CPU Key: ${device.cpuItemKey}`)
    }
    
    if (device.uptimeItemKey) {
      parts.push(`Uptime Key: ${device.uptimeItemKey}`)
    }
    
    if (device.zabbixHostId) {
      parts.push(`Zabbix Host ID: ${device.zabbixHostId}`)
    }
    
    return parts.join('\n')
  }

  return {
    // State
    devices,
    loading,
    error,
    
    // Computed
    hasDevices,
    deviceCount,
    deviceStats,
    onlineDevices,
    warningDevices,
    criticalDevices,
    offlineDevices,
    
    // Methods
    fetchDevices,
    refreshDevices,
    clearDevices,
    
    // Utilities
    getStatusClass,
    getStatusLabel,
    getDeviceIcon,
    getMetricClass,
    formatUptime,
    getDeviceTooltip,
  }
}
