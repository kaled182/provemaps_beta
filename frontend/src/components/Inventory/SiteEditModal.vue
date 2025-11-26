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
import { computed, onMounted, ref, watch } from 'vue';
import { loadGoogleMaps } from '@/utils/googleMapsLoader';

const props = defineProps({
  show: Boolean,
  site: Object,
});

const emit = defineEmits(['close', 'saved']);

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
const geocoder = ref(null);
const addressQuery = ref('');
const addressSuggestions = ref([]);
const mapError = ref('');

const isEditing = computed(() => !!props.site);

watch(
  () => props.site,
  (newSite) => {
    if (newSite) {
      form.value = {
        ...newSite,
        // Zera o endereço para não reaproveitar dados antigos (ex.: import Zabbix)
        address: '',
      };
    } else {
      form.value = { name: '', type: 'pop', status: 'active', address: '', lat: '', lng: '' };
    }
    addressQuery.value = '';
  },
  { immediate: true },
);

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

const initMap = async () => {
  if (!mapContainer.value || mapInstance.value) return;
  mapError.value = '';
  try {
    await loadGoogleMaps();
    geocoder.value = new window.google.maps.Geocoder();
    const hasCoords = Number(form.value.lat) && Number(form.value.lng);
    mapInstance.value = new window.google.maps.Map(mapContainer.value, {
      center: { lat: Number(form.value.lat) || -15.793889, lng: Number(form.value.lng) || -47.882778 },
      zoom: hasCoords ? 15 : 6,
    });
    mapInstance.value.addListener('click', (event) => {
      const { latLng } = event;
      const lat = latLng.lat();
      const lng = latLng.lng();
      form.value.lat = lat;
      form.value.lng = lng;
      placeMarker({ lat, lng });
      reverseGeocode(lat, lng);
    });
    if (form.value.lat && form.value.lng) {
      const latNum = Number(form.value.lat);
      const lngNum = Number(form.value.lng);
      placeMarker({ lat: latNum, lng: lngNum });
      mapInstance.value.setZoom(16);
      reverseGeocode(latNum, lngNum);
    }
  } catch (err) {
    console.error('Erro ao carregar mapa', err);
    mapError.value = 'Não foi possível carregar o mapa. Verifique a chave de API ou a conexão.';
  }
};

const placeMarker = ({ lat, lng }) => {
  if (!mapInstance.value) return;
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
};

const onAddressInput = () => {
  if (addressQuery.value.length < 4) {
    addressSuggestions.value = [];
    return;
  }
  fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(addressQuery.value)}&format=json&addressdetails=1&limit=5`, {
    headers: {
      'User-Agent': 'provemaps-frontend',
    },
  })
    .then((res) => res.json())
    .then((data) => {
      addressSuggestions.value = data || [];
    })
    .catch(() => {
      addressSuggestions.value = [];
    });
};

const applySuggestion = (s) => {
  form.value.address = s.display_name || '';
  form.value.lat = parseFloat(s.lat);
  form.value.lng = parseFloat(s.lon);
  addressQuery.value = s.display_name || '';
  addressSuggestions.value = [];
  if (mapInstance.value) {
    placeMarker({ lat: form.value.lat, lng: form.value.lng });
    mapInstance.value.setZoom(14);
  }
};

const reverseGeocode = (lat, lng) => {
  if (geocoder.value) {
    geocoder.value.geocode({ location: { lat, lng } }, (results, status) => {
      if (status === 'OK' && results && results.length > 0) {
        const result = results[0];
        form.value.address = result.formatted_address || '';
        addressQuery.value = result.formatted_address || '';

        const addr = {};
        result.address_components?.forEach((c) => {
          if (c.types.includes('locality')) addr.city = c.long_name;
          if (c.types.includes('administrative_area_level_1')) addr.state = c.long_name;
          if (c.types.includes('postal_code')) addr.postcode = c.long_name;
          if (c.types.includes('sublocality') || c.types.includes('neighborhood')) addr.suburb = c.long_name;
          if (c.types.includes('route')) addr.road = c.long_name;
          if (c.types.includes('street_number')) addr.house_number = c.long_name;
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
    headers: {
      'User-Agent': 'provemaps-frontend',
    },
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
      const composedAddress = streetParts.join(', ') || data.display_name;

      form.value.address = composedAddress;
      addressQuery.value = composedAddress;

      form.value.city = addr.city || addr.town || addr.village || addr.county || form.value.city || '';
      form.value.state = addr.state || form.value.state || '';
      form.value.zip_code = addr.postcode || form.value.zip_code || '';
    })
    .catch(() => {});
};

onMounted(() => {
  initMap();
});

watch(
  () => props.show,
  (val) => {
    if (val) {
      setTimeout(() => initMap(), 50);
    }
  },
);
</script>
