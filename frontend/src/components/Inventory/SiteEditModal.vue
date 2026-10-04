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
import { computed, nextTick, onMounted, ref, shallowRef, watch } from 'vue';
import { createMap } from '@/providers/maps/MapProviderFactory.js';

const props = defineProps({
  show: Boolean,
  site: Object,
});

const emit = defineEmits(['close', 'saved']);

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
const mapInstance = shallowRef(null); // IMap (providers/maps)
const marker = shallowRef(null);      // IMarker
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

// ─── Map lifecycle (EV-0012c: provider configurado, via factory) ─────────

const destroyMap = () => {
  try { marker.value?.remove(); } catch (_) { /* best-effort */ }
  marker.value = null;
  try { mapInstance.value?.destroy(); } catch (_) { /* best-effort */ }
  mapInstance.value = null;
};

const initMap = async () => {
  if (!mapContainer.value || mapInstance.value) return;
  mapError.value = '';

  try {
    const hasCoords = !!Number(form.value.lat) && !!Number(form.value.lng);
    const lat = Number(form.value.lat) || -15.793889;
    const lng = Number(form.value.lng) || -47.882778;
    const zoom = hasCoords ? 15 : 6;

    const map = await createMap(mapContainer.value, {
      center: { lat, lng },
      zoom,
      controls: { mapType: false, streetView: false, fullscreen: false },
    });
    mapInstance.value = map;

    map.on('click', (event) => {
      if (!Number.isFinite(event?.lat) || !Number.isFinite(event?.lng)) return;
      form.value.lat = event.lat;
      form.value.lng = event.lng;
      placeMarker({ lat: event.lat, lng: event.lng });
      reverseGeocode(event.lat, event.lng);
    });

    if (hasCoords) {
      placeMarker({ lat, lng });
      map.setZoom(16);
      reverseGeocode(lat, lng);
    }
  } catch (err) {
    console.error('[SiteEditModal] Erro ao carregar mapa:', err);
    mapError.value = 'Não foi possível carregar o mapa. Verifique a configuração.';
  }
};

// ─── Marcador arrastável (IMarker) ───────────────────────────

const placeMarker = ({ lat, lng }) => {
  if (!mapInstance.value) return;
  if (!marker.value) {
    marker.value = mapInstance.value.createMarker({
      position: { lat, lng },
      draggable: true,
      title: 'Posição do site',
    });
    marker.value.on('dragend', () => {
      const pos = marker.value.getPosition();
      form.value.lat = pos.lat;
      form.value.lng = pos.lng;
      reverseGeocode(pos.lat, pos.lng);
    });
  } else {
    marker.value.setPosition({ lat, lng });
  }
  mapInstance.value.panTo({ lat, lng });
};

const panToCoords = (lat, lng, zoom) => {
  if (!mapInstance.value) return;
  mapInstance.value.panTo({ lat, lng });
  if (zoom) mapInstance.value.setZoom(zoom);
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
// Sempre Nominatim: igual para os três provedores e sem depender de um SDK.

const reverseGeocode = (lat, lng) => reverseGeocodeNominatim(lat, lng);

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
