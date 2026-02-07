/**
 * Composable para gerenciamento de seleção de itens no mapa
 * Gerencia seleção de devices, cables, cameras e racks
 * Suporta seleção individual, por site e seleção total
 */
import { ref, computed } from 'vue'

export function useMapSelection() {
  // Estado de seleção
  const selectedItems = ref({
    devices: [],
    cables: [],
    cameras: [],
    racks: []
  })
  
  // Sites expandidos (para UI do painel)
  const expandedSites = ref(new Set())
  const expandedCameraSites = ref(new Set())
  
  // Sites selecionados (checkbox do site inteiro)
  const selectedSites = ref(new Set())
  const selectedCameraSites = ref(new Set())
  
  /**
   * Alterna expansão de um site no painel de devices
   */
  const toggleSiteExpansion = (siteId) => {
    if (expandedSites.value.has(siteId)) {
      expandedSites.value.delete(siteId)
    } else {
      expandedSites.value.add(siteId)
    }
  }
  
  /**
   * Verifica se um site está expandido
   */
  const isSiteExpanded = (siteId) => {
    return expandedSites.value.has(siteId)
  }
  
  /**
   * Alterna seleção de todos os devices de um site
   */
  const toggleSite = (siteId, devices) => {
    const deviceIds = devices.map(d => d.id)
    const allSelected = deviceIds.every(id => selectedItems.value.devices.includes(id))
    
    console.log(`[toggleSite] Site ${siteId}, deviceIds:`, deviceIds)
    console.log(`[toggleSite] allSelected:`, allSelected)
    console.log(`[toggleSite] selectedItems.devices ANTES:`, selectedItems.value.devices)
    
    if (allSelected) {
      // Desmarcar todos os devices do site
      selectedItems.value.devices = selectedItems.value.devices.filter(
        id => !deviceIds.includes(id)
      )
      selectedSites.value.delete(siteId)
      console.log(`[toggleSite] DESMARCANDO site ${siteId}`)
    } else {
      // Marcar todos os devices do site
      deviceIds.forEach(id => {
        if (!selectedItems.value.devices.includes(id)) {
          selectedItems.value.devices.push(id)
        }
      })
      selectedSites.value.add(siteId)
      console.log(`[toggleSite] MARCANDO site ${siteId}`)
    }
    
    console.log(`[toggleSite] selectedItems.devices DEPOIS:`, selectedItems.value.devices)
  }
  
  /**
   * Verifica se um site está completamente selecionado
   */
  const isSiteSelected = (siteId, devices) => {
    const deviceIds = devices.map(d => d.id)
    return deviceIds.length > 0 && deviceIds.every(id => selectedItems.value.devices.includes(id))
  }
  
  /**
   * Verifica se um site está parcialmente selecionado
   */
  const isSitePartiallySelected = (siteId, devices) => {
    const deviceIds = devices.map(d => d.id)
    const selectedCount = deviceIds.filter(id => selectedItems.value.devices.includes(id)).length
    return selectedCount > 0 && selectedCount < deviceIds.length
  }
  
  /**
   * Retorna resumo de status dos devices de um site
   */
  const getSiteStatusSummary = (devices) => {
    const statusCount = {
      online: 0,
      warning: 0,
      critical: 0,
      offline: 0
    }
    
    devices.forEach(device => {
      if (statusCount.hasOwnProperty(device.status)) {
        statusCount[device.status]++
      }
    })
    
    return statusCount
  }
  
  // ========== Funções específicas para câmeras ==========
  
  /**
   * Alterna expansão de um site de câmeras no painel
   */
  const toggleCameraSiteExpansion = (siteName) => {
    if (expandedCameraSites.value.has(siteName)) {
      expandedCameraSites.value.delete(siteName)
    } else {
      expandedCameraSites.value.add(siteName)
    }
  }
  
  /**
   * Verifica se um site de câmeras está expandido
   */
  const isCameraSiteExpanded = (siteName) => {
    return expandedCameraSites.value.has(siteName)
  }
  
  /**
   * Alterna seleção de todas as câmeras de um site
   */
  const toggleCameraSite = (siteName, cameras) => {
    const cameraIds = cameras.map(c => c.id)
    const allSelected = cameraIds.every(id => selectedItems.value.cameras.includes(id))
    
    if (allSelected) {
      selectedItems.value.cameras = selectedItems.value.cameras.filter(
        id => !cameraIds.includes(id)
      )
      selectedCameraSites.value.delete(siteName)
    } else {
      cameraIds.forEach(id => {
        if (!selectedItems.value.cameras.includes(id)) {
          selectedItems.value.cameras.push(id)
        }
      })
      selectedCameraSites.value.add(siteName)
    }
  }
  
  /**
   * Verifica se um site de câmeras está completamente selecionado
   */
  const isCameraSiteSelected = (siteName, cameras) => {
    const cameraIds = cameras.map(c => c.id)
    return cameraIds.length > 0 && cameraIds.every(id => selectedItems.value.cameras.includes(id))
  }
  
  /**
   * Verifica se um site de câmeras está parcialmente selecionado
   */
  const isCameraSitePartiallySelected = (siteName, cameras) => {
    const cameraIds = cameras.map(c => c.id)
    const selectedCount = cameraIds.filter(id => selectedItems.value.cameras.includes(id)).length
    return selectedCount > 0 && selectedCount < cameraIds.length
  }
  
  /**
   * Retorna resumo de status das câmeras de um site
   */
  const getCameraSiteStatusSummary = (cameras) => {
    const statusCount = {
      online: 0,
      offline: 0
    }
    
    cameras.forEach(camera => {
      const status = String(camera.status || 'offline').toLowerCase()
      if (status === 'online' || status === 'active' || status === 'streaming') {
        statusCount.online++
      } else {
        statusCount.offline++
      }
    })
    
    return statusCount
  }
  
  // ========== Funções gerais de seleção ==========
  
  /**
   * Alterna seleção de um item individual
   */
  const toggleItem = (itemId, category) => {
    const index = selectedItems.value[category].indexOf(itemId)
    
    if (index > -1) {
      // Desmarcar
      selectedItems.value[category].splice(index, 1)
      console.log(`[useMapSelection] Item ${itemId} desmarcado da categoria ${category}`)
      return false // Retorna false para indicar que foi desmarcado
    } else {
      // Marcar
      selectedItems.value[category].push(itemId)
      console.log(`[useMapSelection] Item ${itemId} marcado na categoria ${category}`)
      return true // Retorna true para indicar que foi marcado
    }
  }
  
  /**
   * Seleciona todos os itens de uma categoria
   */
  const selectAll = (category, availableItems) => {
    const allIds = availableItems.map(item => item.id)
    selectedItems.value[category] = [...allIds]
    console.log(`[useMapSelection] Todos os ${allIds.length} items selecionados na categoria ${category}`)
  }
  
  /**
   * Limpa todas as seleções
   */
  const clearAllSelections = () => {
    selectedItems.value = {
      devices: [],
      cables: [],
      cameras: [],
      racks: []
    }
    selectedSites.value.clear()
    selectedCameraSites.value.clear()
    console.log('[useMapSelection] Todas as seleções limpas')
  }
  
  /**
   * Verifica se um item está selecionado
   */
  const isItemSelected = (itemId, category) => {
    return selectedItems.value[category].includes(itemId)
  }
  
  /**
   * Retorna contagem de itens selecionados por categoria
   */
  const getSelectionCount = computed(() => ({
    devices: selectedItems.value.devices.length,
    cables: selectedItems.value.cables.length,
    cameras: selectedItems.value.cameras.length,
    racks: selectedItems.value.racks.length,
    total: selectedItems.value.devices.length + 
           selectedItems.value.cables.length + 
           selectedItems.value.cameras.length + 
           selectedItems.value.racks.length
  }))
  
  return {
    // Estado
    selectedItems,
    expandedSites,
    expandedCameraSites,
    selectedSites,
    selectedCameraSites,
    
    // Funções de expansão de sites
    toggleSiteExpansion,
    isSiteExpanded,
    
    // Funções de seleção de sites (devices)
    toggleSite,
    isSiteSelected,
    isSitePartiallySelected,
    getSiteStatusSummary,
    
    // Funções de expansão de sites de câmeras
    toggleCameraSiteExpansion,
    isCameraSiteExpanded,
    
    // Funções de seleção de sites (cameras)
    toggleCameraSite,
    isCameraSiteSelected,
    isCameraSitePartiallySelected,
    getCameraSiteStatusSummary,
    
    // Funções gerais
    toggleItem,
    selectAll,
    clearAllSelections,
    isItemSelected,
    getSelectionCount
  }
}
