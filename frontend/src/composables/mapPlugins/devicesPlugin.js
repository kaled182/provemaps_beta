/**
 * Plugin de Markers de Dispositivos - Para visualização de sites/devices
 * 
 * Gerencia markers de dispositivos no mapa com ícones customizados,
 * InfoWindows e agrupamento (clustering).
 */

export default function createDevicesPlugin(context, options = {}) {
  const { map, google } = context;
  const {
    onDeviceClick = null,
    enableClustering = false,
    customIcon = null
  } = options;

  // Estado interno
  const markers = new Map();
  const infoWindow = new google.maps.InfoWindow();
  let markerClusterer = null;

  /**
   * Desenha ou atualiza markers de dispositivos
   * @param {Array} devices - Array de devices com { id, latitude, longitude, ... }
   */
  function drawDevices(devices) {
    if (!Array.isArray(devices)) {
      console.warn('[DevicesPlugin] Expected array, got:', typeof devices);
      return;
    }

    // Remove markers antigos
    const currentIds = new Set(devices.map(d => d.id));
    for (const [id, marker] of markers) {
      if (!currentIds.has(id)) {
        marker.setMap(null);
        markers.delete(id);
      }
    }

    // Adiciona ou atualiza markers
    const newMarkers = [];
    devices.forEach(device => {
      const lat = parseFloat(device.latitude);
      const lng = parseFloat(device.longitude);

      if (isNaN(lat) || isNaN(lng)) {
        console.warn('[DevicesPlugin] Invalid coordinates for device:', device.id);
        return;
      }

      const position = { lat, lng };
      const existing = markers.get(device.id);

      if (existing) {
        // Atualiza posição
        existing.setPosition(position);
      } else {
        // Cria novo marker
        const markerOptions = {
          position,
          map,
          title: device.name || device.siteName || `Device ${device.id}`,
          clickable: true
        };

        // Ícone customizado
        if (customIcon) {
          markerOptions.icon = typeof customIcon === 'function'
            ? customIcon(device)
            : customIcon;
        } else {
          // Ícone padrão baseado no status
          markerOptions.icon = getDefaultIcon(device.status);
        }

        const marker = new google.maps.Marker(markerOptions);

        // Event listeners
        if (onDeviceClick) {
          marker.addListener('click', () => {
            onDeviceClick(device, marker);
          });
        }

        // Armazena device data no marker
        marker.deviceData = device;
        markers.set(device.id, marker);
        newMarkers.push(marker);
      }
    });

    // Clustering se habilitado
    if (enableClustering && window.markerClusterer) {
      if (!markerClusterer) {
        markerClusterer = new window.markerClusterer.MarkerClusterer({
          map,
          markers: Array.from(markers.values())
        });
      } else {
        markerClusterer.clearMarkers();
        markerClusterer.addMarkers(Array.from(markers.values()));
      }
    }

    console.log(`[DevicesPlugin] Drew ${devices.length} device markers`);
  }

  /**
   * Retorna ícone padrão baseado no status
   * @param {string} status - Status do device
   * @returns {Object}
   */
  function getDefaultIcon(status) {
    const colors = {
      ok: '#10b981',      // green
      warning: '#f59e0b', // amber
      critical: '#ef4444', // red
      unknown: '#6b7280'  // gray
    };

    const color = colors[status] || colors.unknown;

    return {
      path: google.maps.SymbolPath.CIRCLE,
      fillColor: color,
      fillOpacity: 0.9,
      strokeColor: '#ffffff',
      strokeWeight: 2,
      scale: 8
    };
  }

  /**
   * Exibe InfoWindow para um device
   * @param {Object} device - Device data
   * @param {google.maps.Marker} marker - Marker associado
   */
  function showDeviceInfo(device, marker) {
    const content = `
      <div style="padding: 12px; min-width: 200px;">
        <h4 style="margin: 0 0 8px 0; color: #1f2937;">${device.name || device.siteName}</h4>
        ${device.status ? `<p style="margin: 4px 0;"><strong>Status:</strong> <span style="color: ${getStatusColor(device.status)}">${device.status}</span></p>` : ''}
        ${device.type ? `<p style="margin: 4px 0;"><strong>Type:</strong> ${device.type}</p>` : ''}
        ${device.ip ? `<p style="margin: 4px 0;"><strong>IP:</strong> ${device.ip}</p>` : ''}
      </div>
    `;
    infoWindow.setContent(content);
    infoWindow.open(map, marker);
  }

  /**
   * Retorna cor para status
   */
  function getStatusColor(status) {
    const colors = {
      ok: '#10b981',
      warning: '#f59e0b',
      critical: '#ef4444',
      unknown: '#6b7280'
    };
    return colors[status] || colors.unknown;
  }

  /**
   * Foca em um device específico
   * @param {string|number} deviceId - ID do device
   * @param {number} zoom - Nível de zoom (opcional)
   */
  function focusDevice(deviceId, zoom = 16) {
    const marker = markers.get(deviceId);
    if (!marker) {
      console.warn('[DevicesPlugin] Device not found:', deviceId);
      return;
    }

    map.panTo(marker.getPosition());
    if (zoom) {
      map.setZoom(zoom);
    }
    showDeviceInfo(marker.deviceData, marker);
  }

  /**
   * Ajusta o mapa para mostrar todos os devices
   */
  function fitBounds() {
    if (markers.size === 0) return;

    const bounds = new google.maps.LatLngBounds();
    for (const marker of markers.values()) {
      bounds.extend(marker.getPosition());
    }
    map.fitBounds(bounds);
  }

  /**
   * Limpa todos os markers
   */
  function clearDevices() {
    for (const marker of markers.values()) {
      marker.setMap(null);
    }
    markers.clear();
    infoWindow.close();

    if (markerClusterer) {
      markerClusterer.clearMarkers();
    }
  }

  /**
   * Cleanup do plugin
   */
  function cleanup() {
    clearDevices();
    if (markerClusterer) {
      markerClusterer.setMap(null);
      markerClusterer = null;
    }
  }

  return {
    drawDevices,
    showDeviceInfo,
    focusDevice,
    fitBounds,
    clearDevices,
    cleanup,
    // Getters
    get count() {
      return markers.size;
    },
    get allMarkers() {
      return Array.from(markers.values());
    }
  };
}
