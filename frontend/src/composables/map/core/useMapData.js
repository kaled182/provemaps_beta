/**
 * Composable para carregamento e transformação de dados do inventário
 * Integra APIs de devices, sites, cables, cameras e Zabbix
 * Normaliza status e mapeia coordenadas geográficas
 */
import { ref } from 'vue'

export function useMapData() {
  // Estado dos itens disponíveis
  const availableItems = ref({
    devices: [],
    cables: [],
    cameras: [],
    racks: []
  })
  
  // Mapa de sites para lookup de coordenadas
  const sitesMap = ref(new Map())
  
  /**
   * Normaliza status do Zabbix para formato UI
   * @param {string} availability - Availability do Zabbix ("1"=online, "2"=offline, "0"=unknown)
   * @returns {string} Status normalizado
   */
  const normalizeZabbixStatus = (availability) => {
    const availStr = String(availability || '0')
    
    switch (availStr) {
      case '1':
        return 'online'
      case '2':
        return 'offline'
      default:
        return 'unknown'
    }
  }
  
  /**
   * Normaliza status do cabo para formato UI
   * Backend: "up", "down", "degraded", "unknown"
   * UI: "online", "offline", "warning", "critical", "unknown"
   */
  const normalizeCableStatus = (status) => {
    const statusStr = (status || 'unknown').toLowerCase()
    
    switch (statusStr) {
      case 'up':
      case 'operational':
      case 'online':
      case 'ok':
      case 'normal':
        return 'online'
      case 'down':
      case 'unavailable':
      case 'offline':
        return 'offline'
      case 'degraded':
      case 'warning':
      case 'alert':
        return 'warning'
      case 'critical':
        return 'critical'
      default:
        return 'unknown'
    }
  }

  const STATUS_SEVERITY = {
    offline: 4,
    critical: 3,
    warning: 2,
    online: 1,
    unknown: 0
  }

  const pickMoreSevereStatus = (primary, secondary) => {
    const base = STATUS_SEVERITY[primary] ?? 0
    const candidate = STATUS_SEVERITY[secondary] ?? 0
    return candidate > base ? secondary : primary
  }
  
  /**
   * Normaliza status da câmera para formato UI
   */
  const normalizeCameraStatus = (status) => {
    const statusStr = (status || 'offline').toLowerCase()
    
    if (['online', 'active', 'streaming'].includes(statusStr)) {
      return 'online'
    }
    
    return 'offline'
  }
  
  /**
   * Carrega sites e cria mapa de lookup
   */
  const loadSites = async () => {
    try {
      const response = await fetch('/api/v1/sites/?page_size=500', {
        credentials: 'include'
      })
      
      if (!response.ok) {
        throw new Error(`Erro ao carregar sites: ${response.status}`)
      }
      
      const data = await response.json()
      const sites = Array.isArray(data) ? data : (data.results || [])
      
      console.log(`[useMapData] ${sites.length} sites carregados`)
      
      // Criar mapa de sites por ID
      sitesMap.value.clear()
      sites.forEach(site => {
        if (site.id) {
          sitesMap.value.set(String(site.id), site)
        }
      })
      
      console.log(`[useMapData] ${sitesMap.value.size} sites no mapa de lookup`)
      
      return sites
    } catch (error) {
      console.error('[useMapData] Erro ao carregar sites:', error)
      return []
    }
  }
  
  /**
   * Carrega status dos hosts do Zabbix
   */
  const loadZabbixStatus = async () => {
    try {
      const response = await fetch('/maps_view/api/dashboard/data/', {
        credentials: 'include'
      })
      
      if (!response.ok) {
        throw new Error(`Erro ao carregar status do Zabbix: ${response.status}`)
      }
      
      const data = await response.json()
      const hosts = data.hosts_status || data.hosts || []
      
      console.log(`[useMapData] ${hosts.length} hosts do Zabbix carregados`)
      
      // Criar mapa de status com múltiplas estratégias de lookup
      const statusMap = new Map()
      
      hosts.forEach(host => {
        const status = normalizeZabbixStatus(host.availability || host.available)
        
        // Estratégia 1: Por device_id ou id
        const deviceId = host.device_id || host.id
        if (deviceId) {
          statusMap.set(String(deviceId), status)
        }
        
        // Estratégia 2: Por nome (normalizado)
        if (host.name) {
          statusMap.set(String(host.name).toLowerCase(), status)
        }
        if (host.display_name) {
          statusMap.set(String(host.display_name).toLowerCase(), status)
        }
        
        // Estratégia 3: Por zabbix_hostid
        const zabbixId = host.zabbix_hostid || host.hostid
        if (zabbixId) {
          statusMap.set(`zabbix_${zabbixId}`, status)
        }
      })
      
      console.log(`[useMapData] ${statusMap.size} entradas no statusMap`)
      
      return statusMap
    } catch (error) {
      console.error('[useMapData] Erro ao carregar status do Zabbix:', error)
      return new Map()
    }
  }
  
  /**
   * Busca status de um device usando múltiplas estratégias
   */
  const getDeviceStatus = (device, statusMap) => {
    let status = null
    
    // Estratégia 1: Por device.id
    status = statusMap.get(String(device.id))
    
    // Estratégia 2: Por device.name (normalizado)
    if (!status && device.name) {
      status = statusMap.get(String(device.name).toLowerCase())
    }
    
    // Estratégia 3: Por zabbix_hostid
    if (!status && device.zabbix_hostid) {
      status = statusMap.get(`zabbix_${device.zabbix_hostid}`)
    }
    
    // Fallback: offline se não encontrado
    return status || 'offline'
  }
  
  /**
   * Carrega devices do inventário e enriquece com dados de sites e Zabbix
   */
  const loadDevices = async (statusMap) => {
    try {
      const response = await fetch('/api/v1/devices/?page_size=1000', {
        credentials: 'include'
      })
      
      if (!response.ok) {
        throw new Error(`Erro ao carregar devices: ${response.status}`)
      }
      
      const data = await response.json()
      const devices = Array.isArray(data) ? data : (data.results || [])
      
      console.log(`[useMapData] ${devices.length} devices carregados`)
      
      // Processar devices com localização do site
      const devicesWithLocation = []
      
      devices.forEach(device => {
        if (!device) return
        
        // Pegar site
        const site = sitesMap.value.get(String(device.site))
        if (!site) {
          console.warn(`[useMapData] Site ${device.site} não encontrado para device ${device.name}`)
          return
        }
        
        const lat = parseFloat(site.latitude)
        const lng = parseFloat(site.longitude)
        
        // Validar coordenadas
        if (isNaN(lat) || isNaN(lng)) return
        
        // Pegar status do Zabbix
        const status = getDeviceStatus(device, statusMap)
        
        devicesWithLocation.push({
          id: device.id,
          name: device.name || `Device ${device.id}`,
          type: device.device_type || 'device',
          lat: lat,
          lng: lng,
          status: status,
          ip: device.primary_ip4 || device.ip_address || 'N/A',
          location: site.city || site.location || 'N/A',
          site: device.site,
          site_id: device.site,
          site_name: site.name || site.display_name,
          device_type: device.device_type,
          serial_number: device.serial_number
        })
      })
      
      availableItems.value.devices = devicesWithLocation
      
      console.log(`[useMapData] ${devicesWithLocation.length} devices com localização processados`)
      
      // Resumo de status
      const statusSummary = devicesWithLocation.reduce((acc, device) => {
        acc[device.status] = (acc[device.status] || 0) + 1
        return acc
      }, {})
      
      console.log('[useMapData] Resumo de status dos devices:', statusSummary)
      
      return devicesWithLocation
    } catch (error) {
      console.error('[useMapData] Erro ao carregar devices:', error)
      availableItems.value.devices = []
      return []
    }
  }
  
  /**
   * Carrega cabos de fibra com rotas
   */
  const loadCables = async () => {
    try {
      const response = await fetch('/api/v1/fiber-cables/', {
        credentials: 'include'
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('[useMapData] Erro HTTP ao carregar cabos:', response.status, errorText)
        throw new Error(`Erro ao carregar cabos: ${response.status}`)
      }
      
      const data = await response.json()
      const cables = Array.isArray(data) ? data : (data.results || [])
      
      console.log(`[useMapData] ${cables.length} cabos carregados`)
      console.log('[useMapData] Primeiros 2 cabos:', cables.slice(0, 2).map(c => ({ id: c.id, name: c.name, coords: c.path_coordinates?.length || 0 })))
      
      // Processar cabos
      availableItems.value.cables = cables.map(cable => {
        const pathCoords = cable.path_coordinates || []
        const backendStatus = normalizeCableStatus(cable.status)
        const opticalStatus = normalizeCableStatus(cable.optical_status)

        // Optical data should drive map coloring when available.
        let uiStatus = opticalStatus !== 'unknown' ? opticalStatus : backendStatus
        if (uiStatus === 'online' && backendStatus === 'offline') {
          uiStatus = backendStatus
        }
        if (uiStatus === 'online' && backendStatus === 'critical') {
          uiStatus = backendStatus
        }
        
        return {
          id: cable.id,
          name: cable.name,
          status: uiStatus,
          original_status: cable.status,
          optical_status: opticalStatus,
          optical_summary: cable.optical_summary || null,
          description: cable.description || '',
          path_coordinates: pathCoords,
          site_a_name: cable.site_a_name,
          site_b_name: cable.site_b_name,
          length_km: cable.length_km,
          is_connected: cable.is_connected,
          connection_status: cable.connection_status
        }
      })
      
      // Resumo de status
      const statusSummary = availableItems.value.cables.reduce((acc, cable) => {
        acc[cable.status] = (acc[cable.status] || 0) + 1
        return acc
      }, {})
      
      console.log('[useMapData] Resumo de status dos cabos:', statusSummary)
      
      return availableItems.value.cables
    } catch (error) {
      console.error('[useMapData] Erro ao carregar cabos:', error)
      availableItems.value.cables = []
      return []
    }
  }
  
  /**
   * Carrega câmeras
   */
  const loadCameras = async () => {
    try {
      const response = await fetch('/api/v1/cameras/', {
        credentials: 'include'
      })
      
      if (!response.ok) {
        throw new Error(`Erro ao carregar câmeras: ${response.status}`)
      }
      
      const data = await response.json()
      const cameras = Array.isArray(data) ? data : (data.results || [])
      
      console.log(`[useMapData] ${cameras.length} câmeras carregadas`)
      
      availableItems.value.cameras = cameras.map(camera => {
        const status = normalizeCameraStatus(camera.status || camera.stream_status)
        
        return {
          id: camera.id,
          name: camera.display_name || camera.name || `Câmera ${camera.id}`,
          status: status,
          description: camera.description || '',
          site_name: camera.site_name,
          lat: camera.latitude || null,
          lng: camera.longitude || null
        }
      })
      
      console.log(`[useMapData] ${availableItems.value.cameras.length} câmeras processadas`)
      
      return availableItems.value.cameras
    } catch (error) {
      console.error('[useMapData] Erro ao carregar câmeras:', error)
      availableItems.value.cameras = []
      return []
    }
  }
  
  /**
   * Carrega todo o inventário (sites, devices, cables, cameras)
   */
  const loadInventoryItems = async () => {
    try {
      console.log('[useMapData] Iniciando carregamento do inventário...')
      
      // 1. Carregar sites primeiro (necessário para coordenadas)
      await loadSites()
      
      // 2. Carregar status do Zabbix
      const statusMap = await loadZabbixStatus()
      
      // 3. Carregar devices com coordenadas e status
      await loadDevices(statusMap)
      
      // 4. Carregar cabos
      await loadCables()
      
      // 5. Carregar câmeras
      await loadCameras()
      
      // 6. Racks (placeholder)
      availableItems.value.racks = []
      
      console.log('[useMapData] Inventário completo:', {
        devices: availableItems.value.devices.length,
        cables: availableItems.value.cables.length,
        cameras: availableItems.value.cameras.length,
        racks: availableItems.value.racks.length
      })
      
      return availableItems.value
    } catch (error) {
      console.error('[useMapData] Erro ao carregar inventário:', error)
      throw error
    }
  }
  
  /**
   * Limpa todos os dados
   */
  const clearAllData = () => {
    availableItems.value = {
      devices: [],
      cables: [],
      cameras: [],
      racks: []
    }
    sitesMap.value.clear()
    console.log('[useMapData] Todos os dados limpos')
  }
  
  return {
    // Estado
    availableItems,
    sitesMap,
    
    // Funções de carregamento
    loadInventoryItems,
    loadSites,
    loadZabbixStatus,
    loadDevices,
    loadCables,
    loadCameras,
    
    // Funções de normalização
    normalizeZabbixStatus,
    normalizeCableStatus,
    normalizeCameraStatus,
    getDeviceStatus,
    
    // Utilitários
    clearAllData
  }
}
