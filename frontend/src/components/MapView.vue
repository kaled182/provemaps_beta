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
        :key="marker.id"
        :options="{
          position: marker.position,
          title: marker.title || marker.siteName,
          label: marker.label,
          clickable: true
        }"
        @click="() => handleSiteMarkerClick(marker)"
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
          <div class="info-window-header">
            <h4>{{ selectedSegment.properties?.name || `Cabo #${selectedSegment.id}` }}</h4>
            <button @click="closeInfoWindow" class="close-button" aria-label="Fechar">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
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
        <div v-html="deviceInfoHtml"></div>
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
    <div v-if="showLegend" class="map-legend" :class="{ 'legend-collapsed': legendCollapsed }" :style="{ left: legendLeftPosition }">
      <div class="legend-header">
        <h4 v-if="!legendCollapsed">Legenda</h4>
        <button @click="toggleLegendCollapse" class="legend-toggle-btn" :title="legendCollapsed ? 'Expandir legenda' : 'Colapsar legenda'">
          <svg v-if="legendCollapsed" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>
      <div v-if="!legendCollapsed" class="legend-content">
        <div class="legend-item" v-for="(color, status) in legendItems" :key="status">
          <span class="legend-color" :style="{ background: color }"></span>
          <span class="legend-label">{{ status }}</span>
        </div>
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
import { useInventoryStore } from '@/stores/inventory';
import { storeToRefs } from 'pinia';
import { colorForStatus, SEGMENT_STATUS_COLORS } from '@/constants/segmentStatusColors';
import { debounce } from '@/utils/debounce';
import MapControls from '@/components/Map/MapControls.vue';

const props = defineProps({
  sidebarCollapsed: {
    type: Boolean,
    default: false
  },
  sidebarPosition: {
    type: String,
    default: 'left'
  },
  uiStore: {
    type: Object,
    default: null
  }
});

const mapStore = useMapStore();
const inventoryStore = useInventoryStore();
const { focusedItem } = storeToRefs(mapStore);
const { sites } = storeToRefs(inventoryStore);

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
const legendCollapsed = ref(false);

// Legend position based on sidebar state
const legendLeftPosition = computed(() => {
  // Menu lateral esquerdo
  const navMenuWidth = props.uiStore?.isNavMenuOpen ? 280 : 60;
  
  // Se sidebar (Status dos Hosts) está à esquerda
  if (props.sidebarPosition === 'left') {
    if (props.sidebarCollapsed) {
      return `${navMenuWidth + 35}px`; // nav + 15px sidebar colapsado + 20px margin
    }
    return `${navMenuWidth + 370}px`; // nav + 350px sidebar + 20px margin
  }
  
  // Sidebar à direita, legenda só respeita menu esquerdo
  return `${navMenuWidth + 20}px`;
});

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

function toggleLegendCollapse() {
  legendCollapsed.value = !legendCollapsed.value;
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

function buildSiteMarker(site) {
  if (!site || typeof site !== 'object') {
    return null;
  }

  const lat = Number(site.latitude ?? site.lat);
  const lng = Number(site.longitude ?? site.lng);

  if (Number.isNaN(lat) || Number.isNaN(lng)) {
    return null;
  }

  const deviceCount = Number(site.device_count ?? 0);

  const siteName = site.name || site.display_name || `Site #${site.id}`;
  const baseTitle = deviceCount === 1
    ? `${siteName} • 1 dispositivo`
    : `${siteName} • ${deviceCount} dispositivos`;

  return {
    id: `site-${site.id}`,
    siteId: site.id,
    name: siteName,
    siteName,
    siteCity: site.city || '',
    title: baseTitle,
    position: { lat, lng },
    raw: site,
    isSiteOnly: deviceCount === 0,
    deviceCount,
  };
}

function refreshSiteMarkers(siteList) {
  const byCoordinate = new Map();

  (siteList || []).forEach((site) => {
    const marker = buildSiteMarker(site);
    if (!marker) {
      return;
    }

    const { lat, lng } = marker.position;
    const key = `${lat.toFixed(6)}|${lng.toFixed(6)}`;
    const existing = byCoordinate.get(key);

    if (!existing) {
      byCoordinate.set(key, marker);
      return;
    }

    const existingCount = existing.deviceCount ?? 0;
    const candidateCount = marker.deviceCount ?? 0;

    // Prefer markers that actually have devices, breaking ties by higher count
    if (candidateCount > existingCount) {
      byCoordinate.set(key, marker);
    }
  });

  const markers = Array.from(byCoordinate.values()).sort(
    (a, b) => (b.deviceCount ?? 0) - (a.deviceCount ?? 0),
  );

  deviceMarkers.value = markers;

  if (markers.length) {
    setTimeout(() => {
      fitBoundsToAllObjects();
    }, 300);
  }
}

function buildDeviceMarker(site, device) {
  if (!device || !site) {
    console.warn('[buildDeviceMarker] Missing device or site');
    return null;
  }

  const lat = Number(site.latitude ?? site.lat);
  const lng = Number(site.longitude ?? site.lng);
  
  if (Number.isNaN(lat) || Number.isNaN(lng)) {
    console.warn('[buildDeviceMarker] Invalid coordinates - lat:', lat, 'lng:', lng);
    return null;
  }

  const marker = {
    id: device.id,
    hostid: device.hostid || device.host_id || null, // Preservar hostid se existir
    name: device.name || `Device #${device.id}`,
    siteName: site?.name || site?.site_name || 'Site desconhecido',
    siteCity: site?.city || site?.city_name || '',
    title: site?.name || site?.site_name || device.name,
    position: { lat, lng },
    icon: device.icon_url || device.device_icon_url || null,
    raw: device,
    isSiteOnly: Boolean(device.isSiteOnly),
  };
  
  return marker;
}

function getMarkerIcon(marker) {
  if (!marker?.icon) return undefined;
  if (typeof window !== 'undefined' && window.google?.maps?.Size) {
    return { url: marker.icon, scaledSize: new google.maps.Size(24, 24) };
  }
  return { url: marker.icon };
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

async function handleSiteMarkerClick(marker) {
  const site = marker?.raw;
  if (!site) {
    return;
  }

  try {
    const { mode, site: siteMeta, device } = await inventoryStore.selectSite(site);

    if (mode === 'single' && siteMeta && device) {
      const resolvedSite = {
        ...site,
        ...siteMeta,
        latitude: siteMeta.latitude ?? site.latitude,
        longitude: siteMeta.longitude ?? site.longitude,
      };

      const markerPayload = buildDeviceMarker(resolvedSite, device);
      if (markerPayload) {
        showDeviceInfo(markerPayload);
      }
    }
  } catch (err) {
    console.error('[MapView] Failed to handle site marker click', err);
  }
}

function buildDeviceInfoHtml(device, ports) {
  const siteLine = `${device.siteName}${device.siteCity ? ` - ${device.siteCity}` : ''}`;
  
  // Filtrar apenas portas em uso (que têm valores de optical ou status diferente de disponível)
  const portsInUse = Array.isArray(ports) ? ports.filter(port => {
    const hasOpticalData = port?.optical?.rx_dbm !== null || port?.optical?.tx_dbm !== null;
    const isInUse = port?.status && port.status.toLowerCase() !== 'available';
    return hasOpticalData || isInUse;
  }) : [];

  const formatOptical = (dbm) => {
    if (dbm === null || dbm === undefined) return 'N/A';
    const val = Number(dbm);
    if (Number.isNaN(val)) return 'N/A';
    const formatted = val.toFixed(2);
    const colorClass = val >= -15 ? 'good' : val >= -25 ? 'warning' : 'critical';
    return `<span class="optical-value ${colorClass}">${formatted} dBm</span>`;
  };

  const getPortDisplayName = (port) => {
    // Se houver notes, tentar extrair o nome da porta
    if (port.notes) {
      // Remover "Status Operacional da Porta " do início
      const cleanName = port.notes.replace(/^Status Operacional da Porta\s+/i, '').trim();
      if (cleanName) {
        return cleanName;
      }
    }
    // Fallback para o nome original
    return port.name || port.port || `Porta ${port.id}`;
  };

  let portsSection = '';
  if (portsInUse.length > 0) {
    portsSection = portsInUse.map(port => `
      <div class="port-section">
        <div class="port-header">${getPortDisplayName(port)}</div>
        <div class="optical-levels">
          <div class="level-row">
            <span>RX:</span>
            <span>${formatOptical(port?.optical?.rx_dbm)}</span>
          </div>
          <div class="level-row">
            <span>TX:</span>
            <span>${formatOptical(port?.optical?.tx_dbm)}</span>
          </div>
        </div>
      </div>
    `).join('');
  }

  return `
    <div class="fiber-info-window">
      <div class="info-window-header">
        <h4>${device.name}</h4>
        <button onclick="window.closeDeviceInfoWindow()" class="close-button">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>
      <div class="cable-details">
        <div class="info-row">
          <span class="info-label">Site:</span>
          <span class="info-value">${siteLine}</span>
        </div>
        
        <div class="collapsible-section">
          <button onclick="window.toggleDeviceInfo(event)" class="collapse-toggle">
            <svg class="collapse-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 9l-7 7-7-7"/>
            </svg>
            <span>Informações do Dispositivo</span>
          </button>
          <div class="collapsible-content">
            <div class="info-row">
              <span class="info-label">Tipo:</span>
              <span class="info-value">${device.raw?.device_type || device.raw?.type || 'N/A'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">IP:</span>
              <span class="info-value">${device.primary_ip || '-'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Uptime:</span>
              <span class="info-value">${device.uptime_value || '-'}</span>
            </div>
            <div class="info-row">
              <span class="info-label">CPU:</span>
              <span class="info-value">${device.cpu_value || '-'}</span>
            </div>
          </div>
        </div>
        
        ${portsInUse.length > 0 ? `
          <div class="ports-container">
            <div class="port-header" style="border-bottom: none; padding-bottom: 0; margin-bottom: 12px;">Portas em Uso:</div>
            <div class="ports-scroll">
              ${portsSection}
            </div>
          </div>
        ` : '<div style="margin-top: 12px; color: var(--text-tertiary); font-size: 12px; text-align: center;">Nenhuma porta em uso</div>'}
      </div>
    </div>
  `;
}

function closeDeviceInfo() {
  selectedDevice.value = null;
  deviceInfoWindowPosition.value = null;
  deviceInfoHtml.value = '';
  deviceInfoError.value = null;
}

function toggleDeviceInfo(event) {
  const button = event.currentTarget;
  const content = button.nextElementSibling;
  const icon = button.querySelector('.collapse-icon');
  
  if (content.style.maxHeight && content.style.maxHeight !== '0px') {
    // Collapse
    content.style.maxHeight = '0px';
    button.classList.remove('expanded');
  } else {
    // Expand
    content.style.maxHeight = content.scrollHeight + 'px';
    button.classList.add('expanded');
  }
}

// Expor função globalmente para o botão de fechar
if (typeof window !== 'undefined') {
  window.closeDeviceInfoWindow = closeDeviceInfo;
  window.toggleDeviceInfo = toggleDeviceInfo;
}

async function showDeviceInfo(marker) {
  selectedDevice.value = marker;
  deviceInfoWindowPosition.value = marker.position;
  deviceInfoLoading.value = true;
  deviceInfoError.value = null;
  deviceInfoHtml.value = `
    <div class="fiber-info-window">
      <div class="loading-spinner">Carregando informações do dispositivo...</div>
    </div>
  `;

  if (marker.isSiteOnly) {
    deviceInfoHtml.value = `
      <div class="fiber-info-window">
        <div class="info-window-header">
          <h4>${marker.name}</h4>
          <button onclick="window.closeDeviceInfoWindow()" class="close-button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="cable-details">
          <div class="info-row">
            <span class="info-label">Site:</span>
            <span class="info-value">${marker.siteName}</span>
          </div>
          ${marker.siteCity ? `
            <div class="info-row">
              <span class="info-label">Cidade:</span>
              <span class="info-value">${marker.siteCity}</span>
            </div>
          ` : ''}
          <div style="margin-top: 12px; color: var(--text-tertiary); font-size: 12px; text-align: center;">
            Nenhum dispositivo cadastrado neste local.
          </div>
        </div>
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
    let deviceData = { ...marker };
    if (response.ok) {
      const data = await response.json();
      ports = Array.isArray(data?.ports) ? data.ports : [];
      // Incluir dados do device do retorno da API
      if (data?.primary_ip) {
        deviceData.primary_ip = data.primary_ip;
      }
      if (data?.uptime_value) {
        deviceData.uptime_value = data.uptime_value;
      }
      if (data?.cpu_value) {
        deviceData.cpu_value = data.cpu_value;
      }
    } else {
      throw new Error(`HTTP ${response.status}`);
    }

    deviceInfoHtml.value = buildDeviceInfoHtml(deviceData, ports);
  } catch (err) {
    deviceInfoError.value = err.message;
    deviceInfoHtml.value = `
      <div class="fiber-info-window">
        <div class="info-window-header">
          <h4>${marker.name}</h4>
          <button onclick="window.closeDeviceInfoWindow()" class="close-button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div class="cable-details">
          <div class="error-message">
            Falha ao carregar detalhes: ${err.message}
          </div>
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
  inventoryStore.fetchSites();
  loadFiberSegments();
});

// Watch deviceMarkers to debug
watch(sites, (newSites) => {
  refreshSiteMarkers(newSites);
}, { deep: true, immediate: true });

watch(deviceMarkers, (newMarkers) => {
  console.debug('[MapView] deviceMarkers mudou:', newMarkers.length);
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
watch(focusedItem, async (newItem) => {
  if (!newItem || !mapRef.value?.map) {
    return;
  }

  const map = mapRef.value.map;
  const lat = Number(newItem.latitude);
  const lng = Number(newItem.longitude);

  if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
    map.panTo({ lat, lng });
    const currentZoom = map.getZoom();
    if (currentZoom < 14) {
      map.setZoom(14);
    }
  }

  try {
    if (newItem.device && newItem.site) {
      const marker = buildDeviceMarker(newItem.site, newItem.device);
      if (marker) {
        showDeviceInfo(marker);
      }
      return;
    }

    if (newItem.openModal) {
      const siteId = Number(
        newItem.site_id ?? newItem.siteId ?? newItem.site?.id ?? null,
      );

      if (!siteId) {
        return;
      }

      const { site, devices } = await inventoryStore.fetchSiteDevices(siteId);
      if (!site || !Array.isArray(devices) || devices.length === 0) {
        return;
      }

      const targetId = Number(newItem.id ?? newItem.device_id ?? 0);
      const targetHost = String(newItem.hostid ?? newItem.host_id ?? '') || null;

      const matchedDevice = devices.find((device) => {
        if (targetId && device.id === targetId) {
          return true;
        }
        if (targetHost && device.zabbix_hostid) {
          return String(device.zabbix_hostid) === targetHost;
        }
        return false;
      });

      if (matchedDevice) {
        const resolvedSite = {
          ...site,
          latitude: site.latitude ?? lat,
          longitude: site.longitude ?? lng,
        };
        const marker = buildDeviceMarker(resolvedSite, matchedDevice);
        if (marker) {
          showDeviceInfo(marker);
        }
      }
    }
  } catch (err) {
    console.error('[MapView] Failed to focus on item', err);
  } finally {
    setTimeout(() => {
      mapStore.clearFocus();
    }, 3000);
  }
});
</script>

<style>
/* Global styles for Google Maps InfoWindow - não scoped para afetar elementos do Google Maps */
.gm-style .gm-style-iw-c {
  background: linear-gradient(195deg, var(--menu-bg-start) 0%, var(--menu-bg-end) 100%) !important;
  border-radius: 8px !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important;
  padding: 0 !important;
  max-width: 420px !important;
  border: 1px solid var(--border-primary) !important;
}

.gm-style .gm-style-iw-d {
  overflow: hidden !important;
  max-height: none !important;
  background: transparent !important;
}

.gm-style .gm-style-iw-t::after {
  background: linear-gradient(195deg, var(--menu-bg-start) 0%, var(--menu-bg-end) 100%) !important;
  box-shadow: -2px 2px 4px 0 rgba(0, 0, 0, 0.2) !important;
}

/* Botão de fechar padrão do Google Maps - esconder */
.gm-style-iw-chr {
  display: none !important;
}

.gm-ui-hover-effect {
  display: none !important;
}

/* Estilos para conteúdo HTML injetado via v-html nos InfoWindows */
.fiber-info-window {
  padding: 0 !important;
  min-width: 280px;
  max-width: 380px;
  background: transparent !important;
  color: var(--text-secondary);
}

.info-window-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 12px 8px 12px;
  border-bottom: 1px solid var(--border-primary);
  gap: 8px;
}

.info-window-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
  line-height: 1.4;
}

.close-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: var(--surface-muted);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
  flex-shrink: 0;
}

.close-button:hover {
  background: var(--surface-highlight);
  color: var(--text-primary);
}

.close-button svg {
  width: 16px;
  height: 16px;
}

.cable-details {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.collapsible-section {
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  overflow: hidden;
  background: var(--bg-secondary);
}

.collapse-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.collapse-toggle:hover {
  background: var(--surface-highlight);
}

.collapse-icon {
  width: 16px;
  height: 16px;
  transition: transform 0.2s;
}

.collapse-toggle.expanded .collapse-icon {
  transform: rotate(180deg);
}

.collapsible-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease;
  padding: 0 12px;
}

.collapsible-content .info-row {
  margin-bottom: 8px;
}

.collapsible-content .info-row:last-child {
  margin-bottom: 12px;
}

.info-row {
  display: grid;
  grid-template-columns: minmax(80px, auto) 1fr;
  gap: 12px;
  margin-bottom: 4px;
  font-size: 13px;
  align-items: baseline;
  line-height: 1.4;
}

.info-label {
  color: var(--text-tertiary);
  font-weight: 600;
  white-space: nowrap;
}

.info-value {
  color: var(--text-primary);
  font-weight: 600;
  text-align: right;
  word-break: break-word;
}

.ports-container {
  margin-top: 12px;
}

.ports-scroll {
  max-height: 300px;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge */
}

.ports-scroll::-webkit-scrollbar {
  display: none; /* Chrome/Safari/Opera */
}

.port-section {
  background: var(--bg-secondary);
  border-radius: 6px;
  padding: 10px;
  border: 1px solid var(--border-primary);
  margin-bottom: 8px;
}

.port-section:last-child {
  margin-bottom: 0;
}

.port-header {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border-primary);
  line-height: 1.4;
}

.optical-levels {
  margin-top: 6px;
  padding: 6px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  border: 1px solid var(--border-primary);
}

.level-row {
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 8px;
  margin-bottom: 2px;
  font-size: 12px;
  align-items: baseline;
  line-height: 1.4;
}

.level-row span:first-child {
  color: var(--text-tertiary);
  font-weight: 600;
  white-space: nowrap;
}

.level-row .optical-value {
  font-weight: 600;
  text-align: right;
}

.level-row .optical-value.good {
  color: var(--status-online);
}

.level-row .optical-value.warning {
  color: var(--status-warning);
}

.level-row .optical-value.critical {
  color: var(--status-offline);
}

.loading-spinner {
  padding: 24px 16px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 13px;
  line-height: 1.4;
}

.error-message {
  padding: 12px;
  margin: 12px;
  background: var(--danger-soft-bg);
  color: var(--accent-danger);
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.4;
}
</style>

<style scoped>
.map-wrapper { position: relative; }
.status { position:absolute; top:8px; left:8px; background:var(--surface-card); padding:4px 8px; font-size:12px; border:1px solid var(--border-primary); color:var(--text-primary); }
.error { position:absolute; top:32px; left:8px; background:var(--danger-soft-bg); color:var(--accent-danger); padding:4px 8px; font-size:12px; border:1px solid var(--accent-danger); }
.missing-key { padding:16px; color:var(--accent-danger); }

.map-legend {
  position: fixed;
  bottom: 20px;
  background: linear-gradient(195deg, var(--menu-bg-start) 0%, var(--menu-bg-end) 100%);
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: var(--shadow-md);
  border: 1px solid var(--border-primary);
  min-width: 150px;
  max-width: 200px;
  z-index: 1050;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
  transition: left 0.3s ease, width 0.3s ease, padding 0.3s ease;
}

.map-legend.legend-collapsed {
  min-width: 40px;
  max-width: 40px;
  padding: 8px;
}

/* Ajustar posição quando há navbar/header */
@supports (top: env(safe-area-inset-top)) {
  .map-legend {
    bottom: max(20px, env(safe-area-inset-bottom));
  }
}

/* Scrollbar customizada para a legenda */
.map-legend::-webkit-scrollbar {
  width: 4px;
}

.map-legend::-webkit-scrollbar-track {
  background: var(--scrollbar-track);
  border-radius: 4px;
}

.map-legend::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 4px;
}

.map-legend::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}

.legend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.legend-collapsed .legend-header {
  margin-bottom: 0;
  justify-content: center;
}

.legend-header h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.legend-toggle-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  transition: color 0.2s;
  flex-shrink: 0;
}

.legend-toggle-btn:hover {
  color: var(--text-primary);
}

.legend-toggle-btn svg {
  width: 16px;
  height: 16px;
}

.legend-content {
  display: flex;
  flex-direction: column;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-color {
  width: 20px;
  height: 3px;
  border-radius: 2px;
}

.legend-label {
  color: var(--text-secondary);
}

.info-value.status-operational {
  color: var(--status-online);
}

.info-value.status-degraded {
  color: var(--status-warning);
}

.info-value.status-down {
  color: var(--status-offline);
}

.info-value.status-maintenance {
  color: var(--accent-info);
}

.info-value.status-unknown {
  color: var(--text-tertiary);
}

.signal-good {
  color: var(--status-online);
  font-weight: 600;
}

.signal-warning {
  color: var(--status-warning);
  font-weight: 600;
}

.signal-bad {
  color: var(--status-offline);
  font-weight: 600;
}

.signal-unknown {
  color: var(--status-unknown);
}

.no-data {
  margin-top: 6px;
  padding: 4px;
  background: var(--warning-soft-bg);
  color: var(--warning-soft-text);
  border-radius: 3px;
  font-size: 10px;
  text-align: center;
}

.action-buttons {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.chart-button {
  flex: 1;
  padding: 6px 10px;
  background: var(--accent-info);
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.chart-button:hover {
  background: var(--accent-info-dark);
}

.chart-button:active {
  background: var(--accent-info-dark);
  filter: brightness(0.9);
}

.simple-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>

