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
      <Polyline
        v-for="feature in combinedSegments"
        :key="feature.id"
        :path="feature.geometry.coordinates.map(([lng,lat]) => ({ lat, lng }))"
        :options="{ 
          strokeColor: getSegmentColor(feature), 
          strokeWeight: 2,
          clickable: true
        }"
        @click="() => showSegmentInfo(feature)"
      />

      <Marker
        v-for="marker in deviceMarkers"
        :key="`device-${marker.id}`"
        :position="marker.position"
        :icon="getMarkerIcon(marker)"
        @click="() => showDeviceInfo(marker)"
      />
      
      <!-- InfoWindow for selected segment -->
      <InfoWindow
        v-if="selectedSegment"
        :options="{ 
          position: infoWindowPosition,
          pixelOffset: { width: 0, height: -10 }
        }"
        @closeclick="closeInfoWindow"
      >
        <div class="info-window-content">
          <h4>{{ selectedSegment.properties?.name || `Segmento #${selectedSegment.id}` }}</h4>
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
          <div class="info-row" v-if="selectedSegment.properties?.fiber_count">
            <span class="info-label">Fibras:</span>
            <span class="info-value">{{ selectedSegment.properties.fiber_count }}</span>
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
import { ref, computed, onMounted } from 'vue';
import { GoogleMap, Polyline, InfoWindow, Marker } from 'vue3-google-map';
import { useMapStore } from '@/stores/map';
import { colorForStatus, SEGMENT_STATUS_COLORS } from '@/constants/segmentStatusColors';
import { debounce } from '@/utils/debounce';
import MapControls from '@/components/Map/MapControls.vue';

const mapStore = useMapStore();

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
}

function closeInfoWindow() {
  selectedSegment.value = null;
  infoWindowPosition.value = null;
}

function fitBounds() {
  const map = mapRef.value?.map;
  if (!map) return;

  const bounds = new google.maps.LatLngBounds();
  let hasGeometry = false;

  combinedSegments.value.forEach(feature => {
    const coords = feature.geometry?.coordinates;
    if (coords && Array.isArray(coords)) {
      coords.forEach(([lng, lat]) => {
        bounds.extend({ lat, lng });
        hasGeometry = true;
      });
    }
  });

  deviceMarkers.value.forEach(marker => {
    bounds.extend(marker.position);
    hasGeometry = true;
  });

  if (!hasGeometry) {
    console.warn('No geometry available to fit bounds');
    return;
  }

  map.fitBounds(bounds, {
    top: 20,
    right: 20,
    bottom: 20,
    left: 20,
  });
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
  if (!fiber) return null;

  let path = [];
  if (Array.isArray(fiber.path) && fiber.path.length) {
    path = fiber.path
      .map(point => ({ lat: Number(point.lat), lng: Number(point.lng) }))
      .filter(coord => !Number.isNaN(coord.lat) && !Number.isNaN(coord.lng));
  } else if (fiber.origin && fiber.destination) {
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

  if (!path.length) return null;

  const coordinates = path.map(({ lat, lng }) => [lng, lat]);

  return {
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
}

async function loadFiberSegments() {
  try {
    const response = await fetch('/api/v1/inventory/fibers/', {
      credentials: 'include',
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    const items = Array.isArray(data?.fibers)
      ? data.fibers
      : Array.isArray(data?.cables)
        ? data.cables
        : Array.isArray(data)
          ? data
          : [];

    fiberSegments.value = items
      .map(mapFiberToFeature)
      .filter(Boolean);
  } catch (err) {
    console.error('[MapView] Failed to load fiber network', err);
  }
}

function buildDeviceMarker(site, device) {
  if (!device || !site) return null;

  const lat = Number(site.latitude ?? site.lat);
  const lng = Number(site.longitude ?? site.lng);
  if (Number.isNaN(lat) || Number.isNaN(lng)) return null;

  return {
    id: device.id,
    name: device.name || `Device #${device.id}`,
    siteName: site?.name || site?.site_name || 'Site desconhecido',
    siteCity: site?.city || site?.city_name || '',
    position: { lat, lng },
    icon: device.icon_url || device.device_icon_url || null,
    raw: device,
    isSiteOnly: Boolean(device.isSiteOnly),
  };
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

async function loadSitesAndDevices() {
  try {
    const [sitesResponse, devicesResponse] = await Promise.all([
      fetch('/api/v1/sites/', { credentials: 'include' }),
      fetch('/api/v1/devices/', { credentials: 'include' }),
    ]);

    if (!sitesResponse.ok) {
      throw new Error(`Sites HTTP ${sitesResponse.status}`);
    }
    const sitesPayload = await sitesResponse.json();
    const siteList = extractResults(sitesPayload);

    const devices = devicesResponse.ok ? extractResults(await devicesResponse.json()) : [];

    const siteById = new Map();
    siteList.forEach(site => {
      siteById.set(site.id, site);
    });

    const markers = devices
      .map(device => buildDeviceMarker(siteById.get(device.site), device))
      .filter(Boolean);

    // Fallback: if no devices returned, surface site markers when coordinates exist
    if (!markers.length) {
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
    }

    deviceMarkers.value = markers;

    if (markers.length === 1) {
      center.value = { ...markers[0].position };
    } else if (markers.length > 1 && mapRef.value?.map && window.google?.maps) {
      const bounds = new google.maps.LatLngBounds();
      markers.forEach(marker => bounds.extend(marker.position));
      mapRef.value.map.fitBounds(bounds);
    }
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

onMounted(() => {
  loadSitesAndDevices();
  loadFiberSegments();
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
</style>
