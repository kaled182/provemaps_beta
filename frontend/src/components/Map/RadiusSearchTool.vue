<!--
  RadiusSearchTool - Phase 7 Day 4
  
  Componente de busca por raio geodésico usando PostGIS ST_DWithin.
  Features:
  - Click no mapa para definir centro de busca
  - Slider para ajustar raio (1-100km)
  - Exibição de círculo visual no mapa
  - Marcadores coloridos para sites encontrados
  - Tooltips com distância de cada site
  - Integração com API /api/v1/inventory/sites/radius
-->

<template>
  <div class="radius-search-tool">
    <!-- Control Panel -->
    <div class="search-panel" :class="{ collapsed: isPanelCollapsed }">
      <div class="panel-header">
        <h3>🔍 Busca por Raio</h3>
        <button 
          @click="togglePanel" 
          class="toggle-button"
          :title="isPanelCollapsed ? 'Expandir' : 'Recolher'"
        >
          {{ isPanelCollapsed ? '▼' : '▲' }}
        </button>
      </div>
      
      <div v-if="!isPanelCollapsed" class="panel-content">
        <!-- Instructions -->
        <div v-if="!searchCenter" class="instructions">
          <p>📍 Clique no mapa para definir o ponto central da busca</p>
        </div>
        
        <!-- Search Center Display -->
        <div v-else class="center-info">
          <div class="info-row">
            <span class="label">Centro:</span>
            <span class="value">
              {{ searchCenter.lat.toFixed(6) }}, {{ searchCenter.lng.toFixed(6) }}
            </span>
            <button @click="clearSearch" class="clear-button" title="Limpar busca">
              ✕
            </button>
          </div>
        </div>
        
        <!-- Radius Slider -->
        <div v-if="searchCenter" class="radius-control">
          <label for="radius-slider" class="slider-label">
            Raio: <strong>{{ radiusKm }}</strong> km
          </label>
          <input
            id="radius-slider"
            type="range"
            min="1"
            max="100"
            step="1"
            v-model.number="radiusKm"
            @input="debouncedSearch"
            class="radius-slider"
          />
          <div class="slider-marks">
            <span>1km</span>
            <span>25km</span>
            <span>50km</span>
            <span>75km</span>
            <span>100km</span>
          </div>
        </div>
        
        <!-- Search Button -->
        <div v-if="searchCenter" class="search-actions">
          <button 
            @click="executeSearch" 
            :disabled="isSearching"
            class="search-button"
          >
            <span v-if="isSearching" class="spinner-small"></span>
            <span v-else>🔎</span>
            {{ isSearching ? 'Buscando...' : 'Buscar Sites' }}
          </button>
        </div>
        
        <!-- Results Summary -->
        <div v-if="searchResults" class="results-summary">
          <div class="summary-header">
            <span class="result-count">{{ searchResults.count }} site(s) encontrado(s)</span>
          </div>
          
          <div v-if="searchResults.count > 0" class="results-list">
            <div 
              v-for="site in searchResults.sites" 
              :key="site.id"
              class="result-item"
              @click="zoomToSite(site)"
              @mouseenter="highlightSite(site.id)"
              @mouseleave="unhighlightSite()"
            >
              <div class="site-name">{{ site.display_name }}</div>
              <div class="site-distance">📍 {{ site.distance_km }} km</div>
            </div>
          </div>
          
          <div v-else class="no-results">
            Nenhum site encontrado neste raio
          </div>
        </div>
        
        <!-- Error Display -->
        <div v-if="searchError" class="error-message">
          <strong>⚠️ Erro:</strong> {{ searchError }}
        </div>
      </div>
    </div>
    
    <!-- Map Click Instructions Overlay -->
    <div 
      v-if="!searchCenter && !isPanelCollapsed" 
      class="map-instruction-overlay"
    >
      <div class="instruction-bubble">
        📍 Clique no mapa para iniciar busca
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted, onBeforeUnmount } from 'vue';
import { debounce } from '@/utils/debounce';

const props = defineProps({
  /**
   * Referência ao objeto do Google Maps
   * Deve conter { map: google.maps.Map }
   */
  mapRef: {
    type: Object,
    required: true
  },
  
  /**
   * Se true, ativa o modo de busca automaticamente
   */
  autoActivate: {
    type: Boolean,
    default: false
  },
  
  /**
   * Raio inicial em km
   */
  initialRadius: {
    type: Number,
    default: 10,
    validator: (value) => value >= 1 && value <= 100
  }
});

const emit = defineEmits([
  'search-started',
  'search-completed',
  'search-error',
  'results-changed'
]);

// State
const isPanelCollapsed = ref(false);
const searchCenter = ref(null); // { lat, lng }
const radiusKm = ref(props.initialRadius);
const isSearching = ref(false);
const searchResults = ref(null);
const searchError = ref(null);
const highlightedSiteId = ref(null);

// Google Maps objects
let mapClickListener = null;
let searchCircle = null;
let resultMarkers = [];

// Computed
const map = computed(() => props.mapRef?.map || null);

/**
 * Toggle panel visibility
 */
function togglePanel() {
  isPanelCollapsed.value = !isPanelCollapsed.value;
}

/**
 * Clear search and reset state
 */
function clearSearch() {
  searchCenter.value = null;
  searchResults.value = null;
  searchError.value = null;
  highlightedSiteId.value = null;
  
  // Remove circle and markers from map
  clearMapOverlays();
}

/**
 * Clear all map overlays (circle, markers)
 */
function clearMapOverlays() {
  if (searchCircle) {
    searchCircle.setMap(null);
    searchCircle = null;
  }
  
  resultMarkers.forEach(marker => marker.setMap(null));
  resultMarkers = [];
}

/**
 * Execute search via API
 */
async function executeSearch() {
  if (!searchCenter.value || isSearching.value) return;
  
  isSearching.value = true;
  searchError.value = null;
  emit('search-started');
  
  try {
    const params = new URLSearchParams({
      lat: searchCenter.value.lat.toString(),
      lng: searchCenter.value.lng.toString(),
      radius_km: radiusKm.value.toString(),
      limit: '100'
    });
    
    const response = await fetch(`/api/v1/inventory/sites/radius?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include' // Include auth cookies
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    searchResults.value = data;
    
    emit('search-completed', data);
    emit('results-changed', data.sites);
    
    // Draw circle and markers on map
    drawSearchCircle();
    drawResultMarkers(data.sites);
    
  } catch (error) {
    console.error('Radius search error:', error);
    searchError.value = error.message || 'Erro ao buscar sites';
    emit('search-error', error);
  } finally {
    isSearching.value = false;
  }
}

/**
 * Debounced search (triggered by slider)
 */
const debouncedSearch = debounce(() => {
  executeSearch();
}, 500);

/**
 * Draw search radius circle on map
 */
function drawSearchCircle() {
  if (!map.value || !searchCenter.value) return;
  
  // Remove existing circle
  if (searchCircle) {
    searchCircle.setMap(null);
  }
  
  // Create new circle
  searchCircle = new google.maps.Circle({
    map: map.value,
    center: searchCenter.value,
    radius: radiusKm.value * 1000, // Convert km to meters
    strokeColor: '#2563eb',
    strokeOpacity: 0.8,
    strokeWeight: 2,
    fillColor: '#3b82f6',
    fillOpacity: 0.15,
    clickable: false
  });
}

/**
 * Draw result markers on map
 */
function drawResultMarkers(sites) {
  if (!map.value || !sites) return;
  
  // Clear existing markers
  resultMarkers.forEach(marker => marker.setMap(null));
  resultMarkers = [];
  
  // Create new markers
  sites.forEach((site, index) => {
    const marker = new google.maps.Marker({
      map: map.value,
      position: { lat: site.latitude, lng: site.longitude },
      title: `${site.display_name} (${site.distance_km} km)`,
      label: {
        text: (index + 1).toString(),
        color: 'white',
        fontSize: '12px',
        fontWeight: 'bold'
      },
      icon: {
        path: google.maps.SymbolPath.CIRCLE,
        scale: 10,
        fillColor: getMarkerColor(site.distance_km),
        fillOpacity: 0.9,
        strokeColor: 'white',
        strokeWeight: 2
      },
      zIndex: 1000 + (sites.length - index) // Closer sites on top
    });
    
    // InfoWindow on click
    const infoWindow = new google.maps.InfoWindow({
      content: `
        <div style="padding: 8px;">
          <strong>${site.display_name}</strong><br>
          📍 Distância: <strong>${site.distance_km} km</strong><br>
          Lat: ${site.latitude.toFixed(6)}<br>
          Lng: ${site.longitude.toFixed(6)}
        </div>
      `
    });
    
    marker.addListener('click', () => {
      // Close other info windows
      resultMarkers.forEach(m => m.infoWindow?.close());
      infoWindow.open(map.value, marker);
    });
    
    marker.infoWindow = infoWindow;
    resultMarkers.push(marker);
  });
  
  // Fit map bounds to show all markers
  if (sites.length > 0) {
    const bounds = new google.maps.LatLngBounds();
    bounds.extend(searchCenter.value); // Include center
    sites.forEach(site => {
      bounds.extend({ lat: site.latitude, lng: site.longitude });
    });
    map.value.fitBounds(bounds);
    
    // Prevent zooming too close
    google.maps.event.addListenerOnce(map.value, 'bounds_changed', () => {
      if (map.value.getZoom() > 15) {
        map.value.setZoom(15);
      }
    });
  }
}

/**
 * Get marker color based on distance
 */
function getMarkerColor(distanceKm) {
  const ratio = distanceKm / radiusKm.value;
  
  if (ratio < 0.25) return '#10b981'; // Green - very close
  if (ratio < 0.50) return '#3b82f6'; // Blue - close
  if (ratio < 0.75) return '#f59e0b'; // Orange - medium
  return '#ef4444'; // Red - far
}

/**
 * Zoom to specific site
 */
function zoomToSite(site) {
  if (!map.value) return;
  
  map.value.setCenter({ lat: site.latitude, lng: site.longitude });
  map.value.setZoom(14);
  
  // Open corresponding marker infoWindow
  const marker = resultMarkers.find(m => 
    m.getPosition().lat() === site.latitude && 
    m.getPosition().lng() === site.longitude
  );
  
  if (marker && marker.infoWindow) {
    // Close all others
    resultMarkers.forEach(m => m.infoWindow?.close());
    marker.infoWindow.open(map.value, marker);
  }
}

/**
 * Highlight site marker on hover
 */
function highlightSite(siteId) {
  highlightedSiteId.value = siteId;
  
  // Find and animate corresponding marker
  const site = searchResults.value?.sites.find(s => s.id === siteId);
  if (!site) return;
  
  const marker = resultMarkers.find(m => 
    m.getPosition().lat() === site.latitude && 
    m.getPosition().lng() === site.longitude
  );
  
  if (marker) {
    // Scale up marker
    const icon = marker.getIcon();
    marker.setIcon({
      ...icon,
      scale: 14,
      strokeWeight: 3
    });
  }
}

/**
 * Remove site highlight
 */
function unhighlightSite() {
  highlightedSiteId.value = null;
  
  // Reset all markers to normal size
  resultMarkers.forEach((marker, index) => {
    const site = searchResults.value?.sites[index];
    if (!site) return;
    
    const icon = marker.getIcon();
    marker.setIcon({
      ...icon,
      scale: 10,
      strokeWeight: 2
    });
  });
}

/**
 * Handle map click to set search center
 */
function handleMapClick(event) {
  if (!event.latLng) return;
  
  const lat = event.latLng.lat();
  const lng = event.latLng.lng();
  
  searchCenter.value = { lat, lng };
  
  // Auto-execute search on first click
  executeSearch();
}

/**
 * Setup map click listener
 */
function setupMapClickListener() {
  if (!map.value) {
    console.warn('RadiusSearchTool: Map not ready yet');
    return;
  }
  
  mapClickListener = map.value.addListener('click', handleMapClick);
  console.log('RadiusSearchTool: Map click listener attached');
}

/**
 * Remove map click listener
 */
function removeMapClickListener() {
  if (mapClickListener) {
    google.maps.event.removeListener(mapClickListener);
    mapClickListener = null;
  }
}

// Lifecycle hooks
onMounted(() => {
  // Wait for map to be ready
  if (map.value) {
    setupMapClickListener();
  } else {
    // Watch for map to become available
    const unwatchMap = watch(
      () => props.mapRef?.map,
      (newMap) => {
        if (newMap) {
          setupMapClickListener();
          unwatchMap(); // Stop watching
        }
      }
    );
  }
  
  if (props.autoActivate) {
    isPanelCollapsed.value = false;
  }
});

onBeforeUnmount(() => {
  removeMapClickListener();
  clearMapOverlays();
});

// Watch radius changes
watch(radiusKm, (newRadius) => {
  if (searchCircle) {
    searchCircle.setRadius(newRadius * 1000);
  }
});
</script>

<style scoped>
.radius-search-tool {
  position: relative;
}

.search-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 320px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  transition: all 0.3s ease;
}

.search-panel.collapsed {
  width: auto;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 8px 8px 0 0;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: white;
}

.toggle-button {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.toggle-button:hover {
  background: rgba(255, 255, 255, 0.3);
}

.panel-content {
  padding: 16px;
  max-height: 600px;
  overflow-y: auto;
}

.instructions {
  padding: 12px;
  background: #eff6ff;
  border-left: 3px solid #3b82f6;
  border-radius: 4px;
  margin-bottom: 16px;
}

.instructions p {
  margin: 0;
  font-size: 14px;
  color: #1e40af;
}

.center-info {
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.info-row .label {
  font-weight: 600;
  color: #374151;
}

.info-row .value {
  flex: 1;
  color: #6b7280;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.clear-button {
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 4px;
  width: 24px;
  height: 24px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.2s;
}

.clear-button:hover {
  background: #dc2626;
}

.radius-control {
  margin-bottom: 16px;
}

.slider-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #374151;
}

.slider-label strong {
  color: #3b82f6;
}

.radius-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: linear-gradient(to right, #10b981 0%, #3b82f6 50%, #ef4444 100%);
  outline: none;
  -webkit-appearance: none;
  cursor: pointer;
}

.radius-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: white;
  border: 3px solid #3b82f6;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.radius-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: white;
  border: 3px solid #3b82f6;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.slider-marks {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 10px;
  color: #9ca3af;
}

.search-actions {
  margin-bottom: 16px;
}

.search-button {
  width: 100%;
  padding: 10px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.search-button:hover:not(:disabled) {
  background: #2563eb;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
}

.search-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner-small {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.results-summary {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.summary-header {
  margin-bottom: 12px;
}

.result-count {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.result-item {
  padding: 10px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.result-item:hover {
  background: #eff6ff;
  border-color: #3b82f6;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
}

.site-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 4px;
}

.site-distance {
  font-size: 12px;
  color: #6b7280;
}

.no-results {
  padding: 16px;
  text-align: center;
  color: #6b7280;
  font-size: 13px;
  font-style: italic;
}

.error-message {
  padding: 12px;
  background: #fef2f2;
  border-left: 3px solid #ef4444;
  border-radius: 4px;
  margin-top: 12px;
  font-size: 13px;
  color: #991b1b;
}

.map-instruction-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 999;
}

.instruction-bubble {
  background: rgba(59, 130, 246, 0.95);
  color: white;
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  font-size: 16px;
  font-weight: 600;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.9;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.05);
  }
}

/* Scrollbar styling */
.panel-content::-webkit-scrollbar,
.results-list::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track,
.results-list::-webkit-scrollbar-track {
  background: #f3f4f6;
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb,
.results-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb:hover,
.results-list::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
</style>
