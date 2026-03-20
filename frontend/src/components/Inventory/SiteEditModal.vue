<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-lg flex flex-col">
      <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
        <h3 class="text-lg font-bold text-gray-900 dark:text-white">
          {{ isEditing ? 'Editar Site' : 'Novo Site' }}
        </h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors">
          <i class="fas fa-times text-xl"></i>
        </button>
      </div>

      <div class="flex-1 min-h-0 p-3 space-y-1">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nome do Site</label>
          <input
            v-model="form.name"
            type="text"
            class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none text-sm"
            placeholder="Ex: POP Central"
          />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tipo</label>
            <select
              v-model="form.type"
              class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none text-sm"
            >
              <option value="pop">POP</option>
              <option value="datacenter">Data Center</option>
              <option value="customer">Cliente</option>
              <option value="hub">Hub</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status</label>
            <select
              v-model="form.status"
              class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none text-sm"
            >
              <option value="active">Ativo</option>
              <option value="maintenance">Manutenção</option>
              <option value="inactive">Inativo</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Endereço</label>
          <div class="space-y-2">
            <input
              v-model="addressQuery"
              @input="onAddressInput"
              type="text"
              class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none text-sm"
              placeholder="Buscar endereço..."
            />
            <div
              v-if="addressSuggestions.length > 0"
              class="max-h-40 overflow-auto border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 shadow-sm"
            >
              <button
                v-for="s in addressSuggestions"
                :key="s.place_id"
                @click.prevent="applySuggestion(s)"
                class="w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-600 text-sm text-gray-700 dark:text-gray-200"
              >
                {{ s.display_name }}
              </button>
            </div>
            <textarea
              v-model="form.address"
              rows="1"
              class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none resize-none text-sm"
              placeholder="Rua, Número, Bairro..."
            ></textarea>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-gray-500 uppercase font-bold mb-1">Latitude</label>
            <input
              v-model="form.lat"
              type="text"
              class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm"
              placeholder="-23.5505"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-500 uppercase font-bold mb-1">Longitude</label>
            <input
              v-model="form.lng"
              type="text"
              class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-sm"
              placeholder="-46.6333"
            />
          </div>
        </div>

        <div class="space-y-2 pt-1">
          <div
            class="w-full rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden"
            style="height: 200px;"
            ref="mapContainer"
          ></div>
          <p v-if="mapError" class="text-xs text-red-500 dark:text-red-300">
            {{ mapError }}
          </p>
        </div>
      </div>

      <div class="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-3">
        <button
          @click="$emit('close')"
          class="px-4 py-2 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors"
        >
          Cancelar
        </button>
        <button
          @click="save"
          class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm transition-colors flex items-center gap-2 text-sm"
        >
          <i class="fas fa-save"></i>
          Salvar
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { loadGoogleMaps } from '@/utils/googleMapsLoader';
import { loadMapbox } from '@/composables/map/providers/useMapbox';
import { loadLeaflet, getLeaflet } from '@/composables/map/providers/useLeaflet';
import { useSystemConfig } from '@/composables/useSystemConfig';

const props = defineProps({
  show: Boolean,
  site: Object,
});

const emit = defineEmits(['close', 'saved']);

const { configForm, loadSystemConfig } = useSystemConfig();

// ─── State ───────────────────────────────────────────────────
const form = ref({
  name: '',
  type: 'pop',
  status: 'active',
  address: '',
  lat: '',
  lng: '',
});
const mapContainer = ref(null);
const mapInstance = ref(null);
const marker = ref(null);
const activeProvider = ref('google');
const addressQuery = ref('');
const addressSuggestions = ref([]);
const mapError = ref('');

const isEditing = computed(() => !!props.site);

// ─── Form sync ───────────────────────────────────────────────
watch(
  () => props.site,
  (newSite) => {
    if (newSite) {
      form.value = { ...newSite, address: '' };
    } else {
      form.value = { name: '', type: 'pop', status: 'active', address: '', lat: '', lng: '' };
    }
    addressQuery.value = '';
  },
  { immediate: true },
);

// ─── Save ────────────────────────────────────────────────────
const save = () => {
  if (!form.value.name) {
    alert('Nome é obrigatório');
    return;
  }
  const toFixed6 = (value) => {
    if (value === null || value === undefined || value === '') return null;
    const num = Number(value);
    if (Number.isNaN(num)) return null;
    return Number(num.toFixed(6));
  };
  emit('saved', {
    ...form.value,
    lat: toFixed6(form.value.lat),
    lng: toFixed6(form.value.lng),
  });
};

// ─── Map lifecycle ───────────────────────────────────────────

const destroyMap = () => {
  if (!mapInstance.value) return;
  const p = activeProvider.value;
  try {
    if (p === 'mapbox' || p === 'osm') {
      mapInstance.value.remove();
    }
  } catch (_) {}
  mapInstance.value = null;
  marker.value = null;
};

const initMap = async () => {
  if (!mapContainer.value || mapInstance.value) return;
  mapError.value = '';

  try {
    await loadSystemConfig();
    activeProvider.value = configForm.value.MAP_PROVIDER || 'google';

    const hasCoords = !!Number(form.value.lat) && !!Number(form.value.lng);
    const lat = Number(form.value.lat) || -15.793889;
    const lng = Number(form.value.lng) || -47.882778;
    const zoom = hasCoords ? 15 : 6;

    if (activeProvider.value === 'mapbox') {
      await initMapboxMap(lat, lng, zoom, hasCoords);
    } else if (activeProvider.value === 'osm') {
      await initLeafletMap(lat, lng, zoom, hasCoords);
    } else {
      await initGoogleMap(lat, lng, zoom, hasCoords);
    }
  } catch (err) {
    console.error('[SiteEditModal] Erro ao carregar mapa:', err);
    mapError.value = 'Não foi possível carregar o mapa. Verifique a configuração.';
  }
};

// ─── Google Maps ─────────────────────────────────────────────

const initGoogleMap = async (lat, lng, zoom, hasCoords) => {
  await loadGoogleMaps();
  mapInstance.value = new window.google.maps.Map(mapContainer.value, {
    center: { lat, lng },
    zoom,
  });
  mapInstance.value.addListener('click', (event) => {
    const newLat = event.latLng.lat();
    const newLng = event.latLng.lng();
    form.value.lat = newLat;
    form.value.lng = newLng;
    placeMarker({ lat: newLat, lng: newLng });
    reverseGeocode(newLat, newLng);
  });
  if (hasCoords) {
    placeMarker({ lat, lng });
    mapInstance.value.setZoom(16);
    reverseGeocode(lat, lng);
  }
};

// ─── Mapbox ──────────────────────────────────────────────────

const initMapboxMap = async (lat, lng, zoom, hasCoords) => {
  const mapboxgl = await loadMapbox();
  window.mapboxgl = mapboxgl;

  const token = configForm.value.MAPBOX_TOKEN;
  if (!token) throw new Error('Token do Mapbox não configurado. Configure em Setup > Mapas.');
  mapboxgl.accessToken = token;

  const styleAliases = {
    streets: 'mapbox://styles/mapbox/streets-v12',
    satellite: 'mapbox://styles/mapbox/satellite-v9',
    dark: 'mapbox://styles/mapbox/dark-v11',
    light: 'mapbox://styles/mapbox/light-v11',
    outdoors: 'mapbox://styles/mapbox/outdoors-v12',
  };
  let style = configForm.value.MAPBOX_CUSTOM_STYLE || configForm.value.MAPBOX_STYLE || 'streets';
  if (!style.startsWith('mapbox://') && !style.startsWith('http')) {
    style = styleAliases[style] || styleAliases.streets;
  }

  mapInstance.value = new mapboxgl.Map({
    container: mapContainer.value,
    style,
    center: [lng, lat],
    zoom,
  });

  await new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => reject(new Error('Timeout ao carregar mapa Mapbox')), 15000);
    mapInstance.value.once('load', () => { clearTimeout(timeoutId); resolve(); });
    mapInstance.value.once('error', (e) => { clearTimeout(timeoutId); reject(e.error || e); });
  });

  mapInstance.value.on('click', (e) => {
    const newLat = e.lngLat.lat;
    const newLng = e.lngLat.lng;
    form.value.lat = newLat;
    form.value.lng = newLng;
    placeMarker({ lat: newLat, lng: newLng });
    reverseGeocode(newLat, newLng);
  });

  if (hasCoords) {
    placeMarker({ lat, lng });
    reverseGeocode(lat, lng);
  }
};

// ─── Leaflet / OSM ───────────────────────────────────────────

const initLeafletMap = async (lat, lng, zoom, hasCoords) => {
  const L = await loadLeaflet();

  mapInstance.value = L.map(mapContainer.value).setView([lat, lng], zoom);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
  }).addTo(mapInstance.value);

  mapInstance.value.on('click', (e) => {
    const newLat = e.latlng.lat;
    const newLng = e.latlng.lng;
    form.value.lat = newLat;
    form.value.lng = newLng;
    placeMarker({ lat: newLat, lng: newLng });
    reverseGeocode(newLat, newLng);
  });

  if (hasCoords) {
    placeMarker({ lat, lng });
    reverseGeocode(lat, lng);
  }
};

// ─── Provider-agnostic marker ────────────────────────────────

const placeMarker = ({ lat, lng }) => {
  if (!mapInstance.value) return;
  const p = activeProvider.value;

  if (p === 'google') {
    if (!marker.value) {
      marker.value = new window.google.maps.Marker({
        position: { lat, lng },
        map: mapInstance.value,
        draggable: true,
      });
      marker.value.addListener('dragend', (event) => {
        const newLat = event.latLng.lat();
        const newLng = event.latLng.lng();
        form.value.lat = newLat;
        form.value.lng = newLng;
        reverseGeocode(newLat, newLng);
      });
    } else {
      marker.value.setPosition({ lat, lng });
    }
    mapInstance.value.panTo({ lat, lng });

  } else if (p === 'mapbox') {
    if (!marker.value) {
      marker.value = new window.mapboxgl.Marker({ draggable: true })
        .setLngLat([lng, lat])
        .addTo(mapInstance.value);
      marker.value.on('dragend', () => {
        const pos = marker.value.getLngLat();
        form.value.lat = pos.lat;
        form.value.lng = pos.lng;
        reverseGeocode(pos.lat, pos.lng);
      });
    } else {
      marker.value.setLngLat([lng, lat]);
    }
    mapInstance.value.flyTo({ center: [lng, lat] });

  } else if (p === 'osm') {
    let L;
    try { L = getLeaflet(); } catch (_) { return; }
    if (!marker.value) {
      marker.value = L.marker([lat, lng], { draggable: true }).addTo(mapInstance.value);
      marker.value.on('dragend', (e) => {
        const pos = e.target.getLatLng();
        form.value.lat = pos.lat;
        form.value.lng = pos.lng;
        reverseGeocode(pos.lat, pos.lng);
      });
    } else {
      marker.value.setLatLng([lat, lng]);
    }
    mapInstance.value.setView([lat, lng]);
  }
};

// ─── Provider-agnostic pan ───────────────────────────────────

const panToCoords = (lat, lng, zoom) => {
  if (!mapInstance.value) return;
  const p = activeProvider.value;
  if (p === 'google') {
    mapInstance.value.panTo({ lat, lng });
    if (zoom) mapInstance.value.setZoom(zoom);
  } else if (p === 'mapbox') {
    mapInstance.value.flyTo({ center: [lng, lat], ...(zoom ? { zoom } : {}) });
  } else if (p === 'osm') {
    mapInstance.value.setView([lat, lng], zoom || mapInstance.value.getZoom());
  }
};

// ─── Address search (Nominatim) ───────────────────────────────

const onAddressInput = () => {
  if (addressQuery.value.length < 4) {
    addressSuggestions.value = [];
    return;
  }
  fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(addressQuery.value)}&format=json&addressdetails=1&limit=5`, {
    headers: { 'User-Agent': 'provemaps-frontend' },
  })
    .then((res) => res.json())
    .then((data) => { addressSuggestions.value = data || []; })
    .catch(() => { addressSuggestions.value = []; });
};

const applySuggestion = (s) => {
  const lat = parseFloat(s.lat);
  const lng = parseFloat(s.lon);
  form.value.address = s.display_name || '';
  form.value.lat = lat;
  form.value.lng = lng;
  addressQuery.value = s.display_name || '';
  addressSuggestions.value = [];
  if (mapInstance.value) {
    placeMarker({ lat, lng });
    panToCoords(lat, lng, 14);
  }
};

// ─── Reverse geocode ─────────────────────────────────────────

const reverseGeocode = (lat, lng) => {
  if (activeProvider.value === 'google' && window.google?.maps?.Geocoder) {
    const geocoder = new window.google.maps.Geocoder();
    geocoder.geocode({ location: { lat, lng } }, (results, status) => {
      if (status === 'OK' && results?.length > 0) {
        const result = results[0];
        form.value.address = result.formatted_address || '';
        addressQuery.value = result.formatted_address || '';
        const addr = {};
        result.address_components?.forEach((c) => {
          if (c.types.includes('locality')) addr.city = c.long_name;
          if (c.types.includes('administrative_area_level_1')) addr.state = c.long_name;
          if (c.types.includes('postal_code')) addr.postcode = c.long_name;
        });
        form.value.city = addr.city || form.value.city || '';
        form.value.state = addr.state || form.value.state || '';
        form.value.zip_code = addr.postcode || form.value.zip_code || '';
        return;
      }
      reverseGeocodeNominatim(lat, lng);
    });
  } else {
    reverseGeocodeNominatim(lat, lng);
  }
};

const reverseGeocodeNominatim = (lat, lng) => {
  fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&addressdetails=1`, {
    headers: { 'User-Agent': 'provemaps-frontend' },
  })
    .then((res) => res.json())
    .then((data) => {
      if (!data?.display_name) return;
      const addr = data.address || {};
      const streetParts = [
        addr.road || addr.pedestrian || addr.cycleway || addr.footway || '',
        addr.house_number || '',
        addr.suburb || addr.neighbourhood || '',
      ].filter(Boolean);
      form.value.address = streetParts.join(', ') || data.display_name;
      addressQuery.value = form.value.address;
      form.value.city = addr.city || addr.town || addr.village || addr.county || form.value.city || '';
      form.value.state = addr.state || form.value.state || '';
      form.value.zip_code = addr.postcode || form.value.zip_code || '';
    })
    .catch(() => {});
};

// ─── Watchers ────────────────────────────────────────────────

watch(
  () => props.show,
  (val) => {
    if (!val) {
      // Destroy runs before DOM update (flush: 'pre' is default)
      destroyMap();
    } else {
      nextTick(() => initMap());
    }
  },
);

onMounted(() => {
  if (props.show) initMap();
});
</script>
