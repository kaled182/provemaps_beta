<template>
  <div class="map-wrapper">
    <GoogleMap
      v-if="apiKey"
      ref="mapRef"
      :api-key="apiKey"
      :center="center"
      :zoom="zoom"
      @idle="onIdle"
      style="width:100%;height:100vh"
    >
      <!-- Polylines desenhadas via Google Maps API nativa em drawNativePolylines() -->
      
      <Marker
        v-for="marker in deviceMarkers"
        :key="`device-${marker.id}`"
        :options="{
          position: marker.position,
          title: marker.name,
          clickable: true
        }"
        @click="() => showDeviceInfo(marker)"
      />
      
      <!-- InfoWindow for selected segment/fiber cable -->
      <InfoWindow
        v-if="selectedSegment"
        :options="{ 
          position: infoWindowPosition,
          pixelOffset: { width: 0, height: -10 }
        }"
        @closeclick="closeInfoWindow"
      >
        <div class="fiber-info-window">
          <h4>{{ selectedSegment.properties?.name || `Cabo #${selectedSegment.id}` }}</h4>
          
          <!-- Loading state -->
          <div v-if="fiberInfoLoading" class="loading-spinner">
            Carregando detalhes...
          </div>
          
          <!-- Error state -->
          <div v-else-if="fiberInfoData?.error" class="error-message">
            Erro ao carregar detalhes
          </div>
          
          <!-- Cable details -->
          <div v-else-if="fiberInfoData?.cable" class="cable-details">
            <!-- Status -->
            <div class="info-row">
              <span class="info-label">Status:</span>
              <span class="info-value" :class="`status-${getSegmentStatus(selectedSegment)}`">
                {{ getSegmentStatusLabel(selectedSegment) }}
              </span>
            </div>
            
            <!-- Length -->
            <div class="info-row" v-if="fiberInfoData.cable.length_km">
              <span class="info-label">Comprimento:</span>
              <span class="info-value">{{ fiberInfoData.cable.length_km }} km</span>
            </div>
            
            <!-- Origin -->
            <div class="port-section">
              <div class="port-header">📍 Origem</div>
              <div class="port-info">
                <div><strong>{{ fiberInfoData.cable.origin?.device || 'N/A' }}</strong></div>
                <div class="port-name">{{ fiberInfoData.cable.origin?.port || 'N/A' }}</div>
                <div v-if="fiberInfoData.originPort?.optical" class="optical-levels">
                  <div class="level-row">
                    <span>RX:</span>
                    <span :class="getSignalClass(fiberInfoData.originPort.optical.rx_dbm)">
                      {{ formatOptical(fiberInfoData.originPort.optical.rx_dbm) }}
                    </span>
                  </div>
                  <div class="level-row">
                    <span>TX:</span>
                    <span :class="getSignalClass(fiberInfoData.originPort.optical.tx_dbm)">
                      {{ formatOptical(fiberInfoData.originPort.optical.tx_dbm) }}
                    </span>
                  </div>
                </div>
                <div v-else class="no-data">Sem dados de sinal</div>
              </div>
            </div>
            
            <!-- Destination -->
            <div class="port-section">
              <div class="port-header">🎯 Destino</div>
              <div class="port-info">
                <div><strong>{{ fiberInfoData.cable.destination?.device || 'N/A' }}</strong></div>
                <div class="port-name">{{ fiberInfoData.cable.destination?.port || 'N/A' }}</div>
                <div v-if="fiberInfoData.destPort?.optical" class="optical-levels">
                  <div class="level-row">
                    <span>RX:</span>
                    <span :class="getSignalClass(fiberInfoData.destPort.optical.rx_dbm)">
                      {{ formatOptical(fiberInfoData.destPort.optical.rx_dbm) }}
                    </span>
                  </div>
                  <div class="level-row">
                    <span>TX:</span>
                    <span :class="getSignalClass(fiberInfoData.destPort.optical.tx_dbm)">
                      {{ formatOptical(fiberInfoData.destPort.optical.tx_dbm) }}
                    </span>
                  </div>
                </div>
                <div v-else class="no-data">Sem dados de sinal</div>
              </div>
            </div>
            
            <!-- Action buttons -->
            <div class="action-buttons">
              <button 
                v-if="fiberInfoData.originPort?.optical"
                @click="showPortChart(fiberInfoData.cable.origin.port_id, 'origin')"
                class="chart-button"
              >
                📊 Gráfico Origem
              </button>
              <button 
                v-if="fiberInfoData.destPort?.optical"
                @click="showPortChart(fiberInfoData.cable.destination.port_id, 'destination')"
                class="chart-button"
              >
                📊 Gráfico Destino
              </button>
            </div>
          </div>
          
          <!-- Fallback for non-fiber segments -->
          <div v-else class="simple-info">
            <div class="info-row">
              <span class="info-label">Status:</span>
              <span class="info-value" :class="`status-${getSegmentStatus(selectedSegment)}`">
                {{ getSegmentStatusLabel(selectedSegment) }}
              </span>
            </div>
            <div class="info-row" v-if="selectedSegment.properties?.length">
              <span class="info-label">Comprimento:</span>
              <span class="info-value">{{ selectedSegment.properties.length }} km</span>
            </div>
          </div>
        </div>
      </InfoWindow>

      <InfoWindow
        v-if="selectedDevice && deviceInfoWindowPosition"
        :options="{
          position: deviceInfoWindowPosition,
          pixelOffset: { width: 0, height: -10 }
        }"
        @closeclick="closeDeviceInfo"
      >
        <div class="info-window-content" v-html="deviceInfoHtml"></div>
      </InfoWindow>
    </GoogleMap>
    <div v-else class="missing-key">Google Maps API key não configurada.</div>
    
    <!-- Map Controls -->
    <MapControls 
      v-if="apiKey" 
      @fit-bounds="fitBounds"
      @toggle-legend="toggleLegend"
    />
    
    <!-- Status Legend -->
    <div v-if="showLegend" class="map-legend">
      <h4>Legenda</h4>
      <div class="legend-item" v-for="(color, status) in legendItems" :key="status">
        <span class="legend-color" :style="{ background: color }"></span>
        <span class="legend-label">{{ status }}</span>
      </div>
    </div>
    
    <div class="status" v-if="loading">Carregando segmentos...</div>
    <div class="error" v-if="error">Erro: {{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { GoogleMap, InfoWindow, Marker } from 'vue3-google-map';
import { useMapStore } from '@/stores/map';
import { storeToRefs } from 'pinia';
import { colorForStatus, SEGMENT_STATUS_COLORS } from '@/constants/segmentStatusColors';
import { debounce } from '@/utils/debounce';
import MapControls from '@/components/Map/MapControls.vue';

const mapStore = useMapStore();
const { focusedItem } = storeToRefs(mapStore);

const runtimeKey = typeof document !== 'undefined'
  ? document.querySelector('meta[name="google-maps-api-key"]')?.getAttribute('content')
  : '';

const apiKey = runtimeKey || import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';
const center = ref({ lat: -15.7801, lng: -47.9292 }); // Brasília
const zoom = ref(12);
const mapRef = ref(null);

const loading = computed(() => mapStore.loading);
const error = computed(() => mapStore.error);
const segmentList = computed(() => Array.from(mapStore.segments.values()));

const fiberSegments = ref([]);
const combinedSegments = computed(() => [
  ...fiberSegments.value,
  ...segmentList.value,
]);

const deviceMarkers = ref([]);
const selectedDevice = ref(null);
const deviceInfoWindowPosition = ref(null);
const deviceInfoHtml = ref('');
const deviceInfoLoading = ref(false);
const deviceInfoError = ref(null);

// Fiber cable info state
const selectedFiberCable = ref(null);
const fiberInfoLoading = ref(false);
const fiberInfoData = ref(null);

// InfoWindow state
const selectedSegment = ref(null);
const infoWindowPosition = ref(null);
const showLegend = ref(true);

const legendItems = computed(() => ({
  'Operacional': SEGMENT_STATUS_COLORS.operational,
  'Degradado': SEGMENT_STATUS_COLORS.degraded,
  'Fora': SEGMENT_STATUS_COLORS.down,
  'Manutenção': SEGMENT_STATUS_COLORS.maintenance,
  'Desconhecido': SEGMENT_STATUS_COLORS.unknown,
}));

// Debounce & duplicate-bbox suppression
const DEBOUNCE_MS = 300;
const lastBoundsStr = ref(null);
function bboxToString(b) {
  return `${b.lng_min},${b.lat_min},${b.lng_max},${b.lat_max}`;
}

const debouncedFetch = debounce((bbox) => {
  mapStore.fetchSegmentsByBbox(bbox);
  lastBoundsStr.value = bboxToString(bbox);
  
  // Prune segments outside viewport after fetch completes
  // Small delay to ensure fetch completes first
  setTimeout(() => mapStore.pruneOutside(bbox), 500);
}, DEBOUNCE_MS);

function resolveMapInstance(eventPayload) {
  if (eventPayload && typeof eventPayload.getBounds === 'function') {
    return eventPayload;
  }
  if (eventPayload?.map && typeof eventPayload.map.getBounds === 'function') {
    return eventPayload.map;
  }
  if (eventPayload?.target?.$mapObject) {
    return eventPayload.target.$mapObject;
  }
  return mapRef.value?.map || null;
}

function onIdle(eventPayload) {
  const map = resolveMapInstance(eventPayload);
  if (!map) return;
  const bounds = map.getBounds();
  if (!bounds) return;
  const ne = bounds.getNorthEast();
  const sw = bounds.getSouthWest();
  const bbox = {
    lng_min: sw.lng(),
    lat_min: sw.lat(),
    lng_max: ne.lng(),
    lat_max: ne.lat(),
  };
  const bboxStr = bboxToString(bbox);
  if (bboxStr === lastBoundsStr.value) {
    return; // Skip identical viewport
  }
  debouncedFetch(bbox);
}

function getSegmentColor(feature) {
  const status = feature?.properties?.status || feature?.status || 'unknown';
  return colorForStatus(status);
}

function getSegmentStatus(feature) {
  return feature?.properties?.status || feature?.status || 'unknown';
}

function getSegmentStatusLabel(feature) {
  const statusMap = {
    operational: 'Operacional',
    degraded: 'Degradado',
    down: 'Fora',
    maintenance: 'Manutenção',
    unknown: 'Desconhecido',
  };
  const status = getSegmentStatus(feature);
  return statusMap[status] || 'Desconhecido';
}

function showSegmentInfo(feature) {
  selectedSegment.value = feature;
  // Calculate center of polyline for InfoWindow position
  const coords = feature.geometry.coordinates;
  if (coords && coords.length > 0) {
    const midIndex = Math.floor(coords.length / 2);
    const [lng, lat] = coords[midIndex];
    infoWindowPosition.value = { lat, lng };
  }
  
  // Se for um fiber cable (id começa com 'fiber-'), buscar detalhes
  if (feature.id && feature.id.toString().startsWith('fiber-')) {
    const cableId = feature.id.replace('fiber-', '');
    loadFiberCableDetails(cableId);
  }
}

async function loadFiberCableDetails(cableId) {
  fiberInfoLoading.value = true;
  fiberInfoData.value = null;
  
  try {
    // Buscar detalhes do cabo
    const response = await fetch(`/api/v1/inventory/fibers/${cableId}/`, {
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    const cableData = await response.json();
    console.log('[loadFiberCableDetails] Cable data:', cableData);
    
    // Buscar níveis de sinal das portas
    const portPromises = [];
    
    if (cableData.origin?.port_id) {
      portPromises.push(
        fetch(`/api/v1/inventory/ports/${cableData.origin.port_id}/optical/`, {
          credentials: 'include',
        }).then(r => r.ok ? r.json() : null)
      );
    } else {
      portPromises.push(Promise.resolve(null));
    }
    
    if (cableData.destination?.port_id) {
      portPromises.push(
        fetch(`/api/v1/inventory/ports/${cableData.destination.port_id}/optical/`, {
          credentials: 'include',
        }).then(r => r.ok ? r.json() : null)
      );
    } else {
      portPromises.push(Promise.resolve(null));
    }
    
    const [originPortData, destPortData] = await Promise.all(portPromises);
    
    fiberInfoData.value = {
      cable: cableData,
      originPort: originPortData,
      destPort: destPortData,
    };
    
    console.log('[loadFiberCableDetails] Complete data:', fiberInfoData.value);
  } catch (err) {
    console.error('[loadFiberCableDetails] Error:', err);
    fiberInfoData.value = { error: err.message };
  } finally {
    fiberInfoLoading.value = false;
  }
}

function closeInfoWindow() {
  selectedSegment.value = null;
  infoWindowPosition.value = null;
  fiberInfoData.value = null;
  fiberInfoLoading.value = false;
}

function formatOptical(dbm) {
  if (dbm === null || dbm === undefined) return 'N/A';
  const val = Number(dbm);
  if (Number.isNaN(val)) return 'N/A';
  return `${val.toFixed(2)} dBm`;
}

function getSignalClass(dbm) {
  if (dbm === null || dbm === undefined) return 'signal-unknown';
  const val = Number(dbm);
  if (Number.isNaN(val)) return 'signal-unknown';
  
  // Typical optical signal levels:
  // Good: > -15 dBm
  // Warning: -15 to -25 dBm
  // Bad: < -25 dBm
  if (val > -15) return 'signal-good';
  if (val > -25) return 'signal-warning';
  return 'signal-bad';
}

function showPortChart(portId, portType) {
  console.log('[showPortChart] Port ID:', portId, 'Type:', portType);
  // TODO: Implementar modal/página de gráficos
  alert(`Gráfico da porta ${portType} (ID: ${portId}) - Em desenvolvimento`);
}

function fitBounds() {
  fitBoundsToAllObjects();
}

function toggleLegend() {
  showLegend.value = !showLegend.value;
}

function normalizeFiberStatus(status) {
  if (!status) return 'unknown';
  const normalized = String(status).toLowerCase();
  if (['up', 'operational', 'online'].includes(normalized)) return 'operational';
  if (['down', 'offline', 'out', 'unavailable', 'fora'].includes(normalized)) return 'down';
  if (['degraded', 'warning', 'alert', 'alerta'].includes(normalized)) return 'degraded';
  if (['maintenance', 'manutenção'].includes(normalized)) return 'maintenance';
  return 'unknown';
}

function mapFiberToFeature(fiber) {
  console.log('[mapFiberToFeature] Input fiber:', fiber);
  if (!fiber) return null;

  let path = [];
  if (Array.isArray(fiber.path) && fiber.path.length) {
    console.log('[mapFiberToFeature] fiber.path recebido, comprimento:', fiber.path.length);
    console.log('[mapFiberToFeature] Primeiro ponto:', fiber.path[0]);
    path = fiber.path
      .map(point => {
        const lat = Number(point.lat);
        const lng = Number(point.lng);
        return { lat, lng };
      })
      .filter(coord => !Number.isNaN(coord.lat) && !Number.isNaN(coord.lng));
    console.log('[mapFiberToFeature] Path após processamento, comprimento:', path.length);
    console.log('[mapFiberToFeature] Primeiro ponto processado:', path[0]);
  } else if (fiber.origin && fiber.destination) {
    console.log('[mapFiberToFeature] Usando origin/destination fallback');
    const originLat = Number(fiber.origin.lat);
    const originLng = Number(fiber.origin.lng);
    const destLat = Number(fiber.destination.lat);
    const destLng = Number(fiber.destination.lng);
    if (!Number.isNaN(originLat) && !Number.isNaN(originLng) && !Number.isNaN(destLat) && !Number.isNaN(destLng)) {
      path = [
        { lat: originLat, lng: originLng },
        { lat: destLat, lng: destLng },
      ];
    }
  }

  if (!path.length) {
    console.warn('[mapFiberToFeature] Path vazio, retornando null');
    return null;
  }

  const coordinates = path.map(({ lat, lng }) => [lng, lat]);
  console.log('[mapFiberToFeature] Coordinates GeoJSON, comprimento:', coordinates.length);
  console.log('[mapFiberToFeature] Primeiro coordinate:', coordinates[0]);

  const feature = {
    id: `fiber-${fiber.id}`,
    type: 'Feature',
    geometry: {
      type: 'LineString',
      coordinates,
    },
    properties: {
      name: fiber.name || fiber.code || `Fibra #${fiber.id}`,
      status: normalizeFiberStatus(fiber.status),
      length: fiber.length_km || fiber.length || null,
      fiber_count: fiber.fiber_count || fiber.fibers_count || fiber.fiber_total || null,
    },
  };
  
  console.log('[mapFiberToFeature] Feature final:', feature);
  console.log('[mapFiberToFeature] Feature.geometry.coordinates comprimento:', feature.geometry.coordinates.length);
  return feature;
}

async function loadFiberSegments() {
  try {
    const response = await fetch('/api/v1/inventory/fibers/', {
      credentials: 'include',
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    console.log('[loadFiberSegments] API response:', data);
    
    const items = Array.isArray(data?.fibers)
      ? data.fibers
      : Array.isArray(data?.cables)
        ? data.cables
        : Array.isArray(data)
          ? data
          : [];

    console.log('[loadFiberSegments] Items extraídos:', items);
    console.log('[loadFiberSegments] Primeiro item:', items[0]);

    fiberSegments.value = items
      .map(mapFiberToFeature)
      .filter(Boolean);
    
    console.log('[loadFiberSegments] Fiber segments processados:', fiberSegments.value);
  } catch (err) {
    console.error('[MapView] Failed to load fiber network', err);
  }
}

function buildDeviceMarker(site, device) {
  console.log('[buildDeviceMarker] site:', site, 'device:', device);
  if (!device || !site) {
    console.warn('[buildDeviceMarker] Missing device or site');
    return null;
  }

  const lat = Number(site.latitude ?? site.lat);
  const lng = Number(site.longitude ?? site.lng);
  console.log('[buildDeviceMarker] lat:', lat, 'lng:', lng);
  
  if (Number.isNaN(lat) || Number.isNaN(lng)) {
    console.warn('[buildDeviceMarker] Invalid coordinates - lat:', lat, 'lng:', lng);
    return null;
  }

  const marker = {
    id: device.id,
    name: device.name || `Device #${device.id}`,
    siteName: site?.name || site?.site_name || 'Site desconhecido',
    siteCity: site?.city || site?.city_name || '',
    position: { lat, lng },
    icon: device.icon_url || device.device_icon_url || null,
    raw: device,
    isSiteOnly: Boolean(device.isSiteOnly),
  };
  
  console.log('[buildDeviceMarker] Marker criado:', marker);
  return marker;
}

function getMarkerIcon(marker) {
  if (!marker?.icon) return undefined;
  if (typeof window !== 'undefined' && window.google?.maps?.Size) {
    return { url: marker.icon, scaledSize: new google.maps.Size(24, 24) };
  }
  return { url: marker.icon };
}

function extractResults(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.results)) return payload.results;
  if (Array.isArray(payload?.sites)) return payload.sites;
  if (Array.isArray(payload?.devices)) return payload.devices;
  return [];
}

// Função para ajustar bounds incluindo markers E polylines
function fitBoundsToAllObjects() {
  if (!mapRef.value?.map || !window.google?.maps) {
    console.warn('[fitBoundsToAllObjects] Mapa não disponível');
    return;
  }

  const bounds = new window.google.maps.LatLngBounds();
  let hasObjects = false;

  // Incluir todos os markers
  deviceMarkers.value.forEach(marker => {
    bounds.extend(marker.position);
    hasObjects = true;
  });

  // Incluir todas as polylines
  combinedSegments.value.forEach(feature => {
    if (feature.geometry?.coordinates) {
      feature.geometry.coordinates.forEach(([lng, lat]) => {
        bounds.extend({ lat, lng });
        hasObjects = true;
      });
    }
  });

  if (hasObjects) {
    console.log('[fitBoundsToAllObjects] Aplicando bounds para', deviceMarkers.value.length, 'markers e', combinedSegments.value.length, 'segmentos');
    mapRef.value.map.fitBounds(bounds);
  } else {
    console.warn('[fitBoundsToAllObjects] Nenhum objeto para ajustar bounds');
  }
}

async function loadSitesAndDevices() {
  try {
    console.log('[MapView] Iniciando carregamento de sites e devices...');
    const [sitesResponse, devicesResponse] = await Promise.all([
      fetch('/api/v1/sites/', { credentials: 'include' }),
      fetch('/api/v1/devices/', { credentials: 'include' }),
    ]);

    console.log('[MapView] Sites response status:', sitesResponse.status);
    console.log('[MapView] Devices response status:', devicesResponse.status);

    if (!sitesResponse.ok) {
      throw new Error(`Sites HTTP ${sitesResponse.status}`);
    }
    const sitesPayload = await sitesResponse.json();
    const siteList = extractResults(sitesPayload);
    console.log('[MapView] Sites carregados:', siteList.length, siteList);

    const devices = devicesResponse.ok ? extractResults(await devicesResponse.json()) : [];
    console.log('[MapView] Devices carregados:', devices.length, devices);

    const siteById = new Map();
    siteList.forEach(site => {
      siteById.set(site.id, site);
    });

    const markers = devices
      .map(device => buildDeviceMarker(siteById.get(device.site), device))
      .filter(Boolean);

    console.log('[MapView] Marcadores criados de devices:', markers.length);

    // Fallback: if no devices returned, surface site markers when coordinates exist
    if (!markers.length) {
      console.log('[MapView] Nenhum device, criando marcadores de sites...');
      siteList.forEach(site => {
        const marker = buildDeviceMarker(site, {
          id: `site-${site.id}`,
          name: site.name || `Site #${site.id}`,
          isSiteOnly: true,
        });
        if (marker) {
          markers.push(marker);
        }
      });
      console.log('[MapView] Marcadores de sites criados:', markers.length);
    }

    deviceMarkers.value = markers;
    console.log('[MapView] Total de marcadores definidos:', deviceMarkers.value.length);

    // Aguardar um pouco para garantir que tudo carregou, então ajustar bounds
    setTimeout(() => {
      fitBoundsToAllObjects();
    }, 800);
  } catch (err) {
    console.error('[MapView] Failed to load sites/devices', err);
  }
}

function buildDeviceInfoHtml(device, ports) {
  const siteLine = `${device.siteName}${device.siteCity ? ` - ${device.siteCity}` : ''}`;
  let portsSection = '';

  if (Array.isArray(ports) && ports.length) {
    const formatOptical = (dbm) => {
      if (dbm === null || dbm === undefined) return 'N/A';
      const val = Number(dbm);
      if (Number.isNaN(val)) return 'N/A';
      return `${val.toFixed(2)} dBm`;
    };

    portsSection = `
      <div style="margin-top:12px;">
        <strong>Portas:</strong>
        <ul style="padding-left:16px; margin:8px 0; font-size:12px;">
          ${ports
            .map(port => `
              <li>
                <strong>${port.name || port.port || `Porta ${port.id}`}</strong>
                <div>RX: ${formatOptical(port?.optical?.rx_dbm)} | TX: ${formatOptical(port?.optical?.tx_dbm)}</div>
              </li>`)
            .join('')}
        </ul>
      </div>
    `;
  }

  return `
    <div style="min-width:220px;font-size:13px;">
      <h4 style="margin:0 0 4px 0;font-size:14px;">${device.name}</h4>
      <div><strong>Site:</strong> ${siteLine}</div>
      <div><strong>Tipo:</strong> ${device.raw?.device_type || device.raw?.type || 'N/A'}</div>
      <div><strong>IP:</strong> ${device.raw?.primary_ip || '-'}</div>
      ${portsSection}
    </div>
  `;
}

function closeDeviceInfo() {
  selectedDevice.value = null;
  deviceInfoWindowPosition.value = null;
  deviceInfoHtml.value = '';
  deviceInfoError.value = null;
}

async function showDeviceInfo(marker) {
  selectedDevice.value = marker;
  deviceInfoWindowPosition.value = marker.position;
  deviceInfoLoading.value = true;
  deviceInfoError.value = null;
  deviceInfoHtml.value = '<div>Carregando...</div>';

  if (marker.isSiteOnly) {
    deviceInfoHtml.value = `
      <div style="min-width:200px;">
        <strong>${marker.name}</strong>
        <div>${marker.siteName}</div>
        <div>${marker.siteCity || ''}</div>
        <div style="margin-top:8px;color:#6b7280;">Nenhum dispositivo cadastrado neste local.</div>
      </div>
    `;
    deviceInfoLoading.value = false;
    return;
  }

  try {
    const response = await fetch(`/api/v1/inventory/devices/${marker.id}/ports/optical/`, {
      credentials: 'include',
    });

    let ports = [];
    if (response.ok) {
      const data = await response.json();
      ports = Array.isArray(data?.ports) ? data.ports : [];
    } else {
      throw new Error(`HTTP ${response.status}`);
    }

    deviceInfoHtml.value = buildDeviceInfoHtml(marker, ports);
  } catch (err) {
    deviceInfoError.value = err.message;
    deviceInfoHtml.value = `
      <div style="min-width:200px;">
        <strong>${marker.name}</strong>
        <div style="color:#dc2626; margin-top:8px;">
          Falha ao carregar detalhes: ${err.message}
        </div>
      </div>
    `;
  } finally {
    deviceInfoLoading.value = false;
  }
}

// Store polylines criadas diretamente com Google Maps API
const nativePolylines = ref([]);

// Função para desenhar polylines nativamente
function drawNativePolylines() {
  // Limpar polylines antigas
  nativePolylines.value.forEach(p => p.setMap(null));
  nativePolylines.value = [];
  
  const map = mapRef.value?.map;
  if (!map || typeof google === 'undefined') {
    console.warn('[drawNativePolylines] Map ou Google Maps API não disponível');
    return;
  }
  
  console.log('[drawNativePolylines] Desenhando', combinedSegments.value.length, 'segmentos');
  
  combinedSegments.value.forEach(feature => {
    if (!feature.geometry?.coordinates?.length) {
      console.warn('[drawNativePolylines] Feature sem coordinates:', feature.id);
      return;
    }
    
    const path = feature.geometry.coordinates.map(([lng, lat]) => ({ lat, lng }));
    console.log('[drawNativePolylines] Criando polyline', feature.id, 'com', path.length, 'pontos');
    
    const polyline = new google.maps.Polyline({
      path: path,
      strokeColor: getSegmentColor(feature),
      strokeWeight: 3,
      strokeOpacity: 0.8,
      map: map,
      clickable: true
    });
    
    polyline.addListener('click', () => {
      console.log('[Polyline] Clicked:', feature.id);
      showSegmentInfo(feature);
    });
    
    nativePolylines.value.push(polyline);
  });
  
  console.log('[drawNativePolylines] Total de polylines criadas:', nativePolylines.value.length);
  
  // Ajustar bounds após desenhar polylines
  setTimeout(() => {
    fitBoundsToAllObjects();
  }, 200);
}

onMounted(() => {
  loadSitesAndDevices();
  loadFiberSegments();
});

// Watch deviceMarkers to debug
watch(deviceMarkers, (newMarkers) => {
  console.log('[MapView] deviceMarkers mudou:', newMarkers.length, newMarkers);
}, { deep: true });

// Watch combinedSegments e redesenhar polylines quando mudar
watch(combinedSegments, () => {
  console.log('[MapView] combinedSegments mudou:', combinedSegments.value.length);
  // Aguardar o mapa estar pronto
  setTimeout(() => {
    drawNativePolylines();
  }, 500);
}, { deep: true });

// Watch mapRef para desenhar quando o mapa carregar
watch(mapRef, (newMap) => {
  if (newMap?.map) {
    console.log('[MapView] Map ref disponível, aguardando idle...');
    google.maps.event.addListenerOnce(newMap.map, 'idle', () => {
      console.log('[MapView] Map idle, desenhando polylines');
      drawNativePolylines();
    });
  }
});

// --- NOVO WATCHER ---
// Observa mudanças no 'focusedItem' da store
watch(focusedItem, (newItem) => {
  if (newItem && mapRef.value?.map) {
    const map = mapRef.value.map;
    const newCenter = {
      lat: parseFloat(newItem.latitude),
      lng: parseFloat(newItem.longitude),
    };
    
    // Anima o movimento do mapa para o item focado
    map.panTo(newCenter);
    
    // Ajusta o zoom se estiver muito distante
    const currentZoom = map.getZoom();
    if (currentZoom < 14) {
      map.setZoom(14);
    }
    
    // Limpa o foco após 3 segundos (opcional)
    setTimeout(() => {
      mapStore.clearFocus();
    }, 3000);
  }
});
</script>

<style scoped>
.map-wrapper { position: relative; }
.status { position:absolute; top:8px; left:8px; background:#fff; padding:4px 8px; font-size:12px; border:1px solid #ccc; }
.error { position:absolute; top:32px; left:8px; background:#ffecec; color:#b00; padding:4px 8px; font-size:12px; border:1px solid #e99; }
.missing-key { padding:16px; color:#b00; }

.map-legend {
  position: absolute;
  bottom: 24px;
  left: 12px;
  background: #fff;
  padding: 12px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  min-width: 150px;
  z-index: 1000;
}

.map-legend h4 {
  margin: 0 0 8px 0;
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}

.legend-color {
  width: 20px;
  height: 3px;
  border-radius: 2px;
}

.legend-label {
  color: #374151;
}

.info-window-content {
  padding: 8px;
  min-width: 200px;
}

.info-window-content h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 12px;
}

.info-label {
  color: #6b7280;
  font-weight: 500;
}

.info-value {
  color: #111827;
  font-weight: 600;
}

.info-value.status-operational {
  color: #10b981;
}

.info-value.status-degraded {
  color: #f59e0b;
}

.info-value.status-down {
  color: #ef4444;
}

.info-value.status-maintenance {
  color: #3b82f6;
}

.info-value.status-unknown {
  color: #6b7280;
}

/* Fiber cable info window styles */
.fiber-info-window {
  padding: 8px;
  min-width: 280px;
  max-width: 350px;
}

.fiber-info-window h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  border-bottom: 2px solid #e5e7eb;
  padding-bottom: 6px;
}

.fiber-info-window .port-info > div > strong {
  color: #1f2937;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 3px;
  display: inline-block;
}

.loading-spinner {
  padding: 16px;
  text-align: center;
  color: #6b7280;
  font-size: 12px;
}

.error-message {
  padding: 8px;
  background: #fef2f2;
  color: #dc2626;
  border-radius: 4px;
  font-size: 12px;
}

.cable-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.port-section {
  background: #f9fafb;
  border-radius: 6px;
  padding: 10px;
  border: 1px solid #e5e7eb;
}

.port-header {
  font-weight: 600;
  font-size: 12px;
  color: #374151;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e5e7eb;
}

.port-info {
  font-size: 12px;
}

.port-info > div {
  margin-bottom: 3px;
}

.port-info > div > strong {
  color: #1e40af;
  background: #dbeafe;
  padding: 3px 8px;
  border-radius: 4px;
  display: inline-block;
  font-size: 12px;
}

.port-name {
  color: #6b7280;
  font-size: 11px;
}

.optical-levels {
  margin-top: 6px;
  padding: 6px;
  background: white;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}

.level-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 2px;
  font-size: 11px;
}

.level-row span:first-child {
  color: #6b7280;
  font-weight: 500;
}

.signal-good {
  color: #10b981;
  font-weight: 600;
}

.signal-warning {
  color: #f59e0b;
  font-weight: 600;
}

.signal-bad {
  color: #ef4444;
  font-weight: 600;
}

.signal-unknown {
  color: #9ca3af;
}

.no-data {
  margin-top: 6px;
  padding: 4px;
  background: #fef3c7;
  color: #92400e;
  border-radius: 3px;
  font-size: 10px;
  text-align: center;
}

.action-buttons {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
}

.chart-button {
  flex: 1;
  padding: 6px 10px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.chart-button:hover {
  background: #2563eb;
}

.chart-button:active {
  background: #1d4ed8;
}

.simple-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>

