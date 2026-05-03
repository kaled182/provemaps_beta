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

  // Árvore de pastas de cabos
  const foldersTree = ref([])

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
   * Busca status de um device usando múltiplas estratégias.
   *
   * Fallback é 'unknown' (não 'offline'): quando o device não tem zabbix_hostid
   * ou o Zabbix não retorna dados, NÃO afirmamos que está offline. O pin do mapa
   * trata 'unknown' como online presumido (verde). Só vira cinza quando o
   * Zabbix confirma availability='2' (offline real).
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

    // Fallback presumido-online — evita pintar de cinza um device saudável
    // só porque o Zabbix está inconclusivo.
    return status || 'unknown'
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
      applyDisplayStatus(availableItems.value.devices)

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
          connection_status: cable.connection_status,
          origin_device_id: cable.origin_device_id || null,
          destination_device_id: cable.destination_device_id || null,
          folder_id: cable.folder_id ?? null,
          folder_name: cable.folder_name ?? null,
          responsible_id: cable.responsible_id ?? null,
          responsible_name: cable.responsible_name ?? null,
          responsible_email: cable.responsible_email ?? null,
          responsible_phone: cable.responsible_phone ?? null,
          responsible_user_id: cable.responsible_user_id ?? null,
          responsible_user_name: cable.responsible_user_name ?? null,
          // Cable type & group
          cable_type_id: cable.cable_type_id ?? null,
          cable_type_name: cable.cable_type_name ?? null,
          cable_group_id: cable.cable_group_id ?? null,
          cable_group_name: cable.cable_group_name ?? null,
          cable_group_attenuation: cable.cable_group_attenuation ?? null,
          fiber_count: cable.fiber_count ?? null,
          // Port/device info
          origin_device_name: cable.origin_device_name ?? null,
          origin_port_name: cable.origin_port_name ?? null,
          destination_device_name: cable.destination_device_name ?? null,
          destination_port_name: cable.destination_port_name ?? null,
          // Extra
          notes: cable.notes ?? '',
          last_status_update: cable.last_status_update ?? null,
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
   * Carrega árvore de pastas de cabos
   */
  const loadFolderTree = async () => {
    try {
      const response = await fetch('/api/v1/inventory/cable-folders/', {
        credentials: 'include'
      })
      if (!response.ok) throw new Error(`Erro ao carregar pastas: ${response.status}`)
      const data = await response.json()
      foldersTree.value = data.tree || []
      console.log(`[useMapData] ${foldersTree.value.length} pastas raiz carregadas`)
      return foldersTree.value
    } catch (error) {
      console.error('[useMapData] Erro ao carregar pastas:', error)
      foldersTree.value = []
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
   * Calcula o `displayStatus` de cada device com base no agregado do site:
   *  - device.status === 'offline' E o site tem outro device 'online'
   *      → displayStatus = 'warning' (amarelo: site parcialmente afetado)
   *  - device.status === 'offline' E TODOS do site offline
   *      → displayStatus = 'offline' (cinza: queda total)
   *  - caso contrário → displayStatus = status
   *
   * Idempotente: pode ser chamado a cada polling. Muta o array in-place.
   */
  const applyDisplayStatus = (devices) => {
    if (!Array.isArray(devices) || devices.length === 0) return
    const bySite = new Map()
    devices.forEach((d) => {
      const sid = String(d.site || d.site_id || '')
      if (!sid) return
      if (!bySite.has(sid)) bySite.set(sid, [])
      bySite.get(sid).push(d)
    })
    devices.forEach((d) => {
      if (d.status !== 'offline') {
        d.displayStatus = d.status
        return
      }
      const sid = String(d.site || d.site_id || '')
      const siblings = bySite.get(sid) || []
      // 'unknown' é presumido online — entra no cômputo de "tem irmão saudável"
      const hasHealthy = siblings.some((s) => s.status === 'online' || s.status === 'unknown')
      d.displayStatus = hasHealthy ? 'warning' : 'offline'
    })
  }

  /**
   * Hidrata o estado a partir da resposta do bootstrap agregado.
   * Aplica a mesma normalização que os loaders individuais.
   */
  const _hydrateFromBootstrap = (payload) => {
    // 1. Sites → sitesMap (lookup por ID)
    sitesMap.value.clear()
    const sites = payload.sites || []
    sites.forEach(site => {
      if (site.id) sitesMap.value.set(String(site.id), site)
    })

    // 2. Zabbix status → statusMap multi-estratégia
    const statusMap = new Map()
    const hosts = payload.zabbix?.hosts_status || payload.zabbix?.hosts || []
    hosts.forEach(host => {
      const status = normalizeZabbixStatus(host.availability || host.available)
      const deviceId = host.device_id || host.id
      if (deviceId) statusMap.set(String(deviceId), status)
      if (host.name) statusMap.set(String(host.name).toLowerCase(), status)
      if (host.display_name) statusMap.set(String(host.display_name).toLowerCase(), status)
      const zabbixId = host.zabbix_hostid || host.hostid
      if (zabbixId) statusMap.set(`zabbix_${zabbixId}`, status)
    })

    // 3. Devices com coordenadas + status
    const devicesWithLocation = []
    ;(payload.devices || []).forEach(device => {
      const site = sitesMap.value.get(String(device.site))
      if (!site) return
      const lat = parseFloat(site.latitude)
      const lng = parseFloat(site.longitude)
      if (isNaN(lat) || isNaN(lng)) return

      const status = getDeviceStatus(device, statusMap)
      devicesWithLocation.push({
        id: device.id,
        name: device.name || `Device ${device.id}`,
        type: device.device_type || 'device',
        lat, lng, status,
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
    applyDisplayStatus(availableItems.value.devices)

    // 4. Cabos (mesma normalização do loadCables)
    availableItems.value.cables = (payload.cables || []).map(cable => {
      const backendStatus = normalizeCableStatus(cable.status)
      const opticalStatus = normalizeCableStatus(cable.optical_status)
      let uiStatus = opticalStatus !== 'unknown' ? opticalStatus : backendStatus
      if (uiStatus === 'online' && backendStatus === 'offline') uiStatus = backendStatus
      if (uiStatus === 'online' && backendStatus === 'critical') uiStatus = backendStatus

      return {
        id: cable.id,
        name: cable.name,
        status: uiStatus,
        original_status: cable.status,
        optical_status: opticalStatus,
        optical_summary: cable.optical_summary || null,
        description: cable.description || '',
        path_coordinates: cable.path_coordinates || [],
        site_a_name: cable.site_a_name,
        site_b_name: cable.site_b_name,
        length_km: cable.length_km,
        is_connected: cable.is_connected,
        connection_status: cable.connection_status,
        origin_device_id: cable.origin_device_id || null,
        destination_device_id: cable.destination_device_id || null,
        folder_id: cable.folder_id ?? null,
        folder_name: cable.folder_name ?? null,
        responsible_id: cable.responsible_id ?? null,
        responsible_name: cable.responsible_name ?? null,
        responsible_email: cable.responsible_email ?? null,
        responsible_phone: cable.responsible_phone ?? null,
        responsible_user_id: cable.responsible_user_id ?? null,
        responsible_user_name: cable.responsible_user_name ?? null,
        cable_type_id: cable.cable_type_id ?? null,
        cable_type_name: cable.cable_type_name ?? null,
        cable_group_id: cable.cable_group_id ?? null,
        cable_group_name: cable.cable_group_name ?? null,
        cable_group_attenuation: cable.cable_group_attenuation ?? null,
        fiber_count: cable.fiber_count ?? null,
        origin_device_name: cable.origin_device_name ?? null,
        origin_port_name: cable.origin_port_name ?? null,
        destination_device_name: cable.destination_device_name ?? null,
        destination_port_name: cable.destination_port_name ?? null,
        notes: cable.notes ?? '',
        last_status_update: cable.last_status_update ?? null,
      }
    })

    // 5. Folders tree
    foldersTree.value = payload.folders?.tree || []

    // 6. Câmeras (mesma normalização)
    availableItems.value.cameras = (payload.cameras || []).map(camera => ({
      id: camera.id,
      name: camera.display_name || camera.name || `Câmera ${camera.id}`,
      status: normalizeCameraStatus(camera.status || camera.stream_status),
      description: camera.description || '',
      site_name: camera.site_name,
      lat: camera.latitude || null,
      lng: camera.longitude || null
    }))

    availableItems.value.racks = []
  }

  /**
   * Carrega todo o inventário em uma única chamada agregada (bootstrap).
   * Fallback para os 6 endpoints individuais (em paralelo) se o bootstrap falhar.
   *
   * Bootstrap: GET /maps_view/api/backbone/init/
   *   → { sites, devices, cables, folders, cameras, zabbix }
   */
  const loadInventoryItems = async () => {
    const t0 = performance.now()

    // Tenta o endpoint agregado primeiro
    try {
      const res = await fetch('/maps_view/api/backbone/init/', { credentials: 'include' })
      if (res.ok) {
        const payload = await res.json()
        _hydrateFromBootstrap(payload)
        const elapsed = Math.round(performance.now() - t0)
        console.log(`[useMapData] Bootstrap completo em ${elapsed}ms:`, {
          devices: availableItems.value.devices.length,
          cables: availableItems.value.cables.length,
          cameras: availableItems.value.cameras.length,
        })
        return availableItems.value
      }
      console.warn(`[useMapData] Bootstrap retornou ${res.status}, caindo para fallback paralelo`)
    } catch (error) {
      console.warn('[useMapData] Bootstrap indisponível, fallback para 6 endpoints:', error)
    }

    // Fallback: estratégia paralela com endpoints individuais
    try {
      const [, statusMap] = await Promise.all([loadSites(), loadZabbixStatus()])
      await Promise.all([
        loadDevices(statusMap),
        loadCables(),
        loadFolderTree(),
        loadCameras()
      ])
      availableItems.value.racks = []
      const elapsed = Math.round(performance.now() - t0)
      console.log(`[useMapData] Fallback completo em ${elapsed}ms`)
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
    foldersTree,

    // Funções de carregamento
    loadInventoryItems,
    loadSites,
    loadZabbixStatus,
    loadDevices,
    loadCables,
    loadFolderTree,
    loadCameras,
    
    // Funções de normalização
    normalizeZabbixStatus,
    normalizeCableStatus,
    normalizeCameraStatus,
    getDeviceStatus,

    // Status agregado por site (offline + irmão online → warning)
    applyDisplayStatus,

    // Utilitários
    clearAllData
  }
}
