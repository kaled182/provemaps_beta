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

        <!-- Coordenadas + botão de mapa -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs text-gray-500 uppercase font-bold mb-1">Latitude</label>
            <input
              v-model="form.lat"
              type="text"
              class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
              placeholder="-23.5505"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-500 uppercase font-bold mb-1">Longitude</label>
            <input
              v-model="form.lng"
              type="text"
              class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
              placeholder="-46.6333"
            />
          </div>
        </div>

        <button
          type="button"
          @click="showPicker = true"
          class="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:border-blue-400 hover:text-blue-500 dark:hover:border-blue-500 dark:hover:text-blue-400 transition-colors text-sm"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          Selecionar localização no mapa
        </button>
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

  <LocationPickerModal
    :is-open="showPicker"
    :lat="pickerLat"
    :lng="pickerLng"
    :zoom="pickerLat !== -15.7801 ? 15 : 6"
    @confirm="onLocationPicked"
    @close="showPicker = false"
  />
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import LocationPickerModal from '@/components/Configuration/LocationPickerModal.vue'

const props = defineProps({
  show: Boolean,
  site: Object,
})

const emit = defineEmits(['close', 'saved'])

// ─── State ───────────────────────────────────────────────────
const form = ref({
  name: '',
  type: 'pop',
  status: 'active',
  address: '',
  lat: '',
  lng: '',
})
const addressQuery = ref('')
const addressSuggestions = ref([])
const showPicker = ref(false)

const isEditing = computed(() => !!props.site)

const pickerLat = computed(() => Number(form.value.lat) || -15.7801)
const pickerLng = computed(() => Number(form.value.lng) || -47.9292)

// ─── Form sync ───────────────────────────────────────────────
watch(
  () => props.site,
  (newSite) => {
    if (newSite) {
      form.value = { ...newSite, address: newSite.address || '' }
    } else {
      form.value = { name: '', type: 'pop', status: 'active', address: '', lat: '', lng: '' }
    }
    addressQuery.value = form.value.address || ''
  },
  { immediate: true },
)

// ─── Save ────────────────────────────────────────────────────
const save = () => {
  if (!form.value.name) {
    alert('Nome é obrigatório')
    return
  }
  const toFixed6 = (value) => {
    if (value === null || value === undefined || value === '') return null
    const num = Number(value)
    if (Number.isNaN(num)) return null
    return Number(num.toFixed(6))
  }
  emit('saved', {
    ...form.value,
    lat: toFixed6(form.value.lat),
    lng: toFixed6(form.value.lng),
  })
}

// ─── Location picker ─────────────────────────────────────────
const onLocationPicked = ({ lat, lng }) => {
  form.value.lat = lat
  form.value.lng = lng
  showPicker.value = false
  reverseGeocodeNominatim(lat, lng)
}

// ─── Address search (Nominatim) ───────────────────────────────
const onAddressInput = () => {
  if (addressQuery.value.length < 4) {
    addressSuggestions.value = []
    return
  }
  fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(addressQuery.value)}&format=json&addressdetails=1&limit=5`, {
    headers: { 'User-Agent': 'provemaps-frontend' },
  })
    .then((res) => res.json())
    .then((data) => { addressSuggestions.value = data || [] })
    .catch(() => { addressSuggestions.value = [] })
}

const applySuggestion = (s) => {
  const lat = parseFloat(s.lat)
  const lng = parseFloat(s.lon)
  form.value.address = s.display_name || ''
  form.value.lat = lat
  form.value.lng = lng
  addressQuery.value = s.display_name || ''
  addressSuggestions.value = []
}

// ─── Reverse geocode (Nominatim) ──────────────────────────────
const reverseGeocodeNominatim = (lat, lng) => {
  fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&addressdetails=1`, {
    headers: { 'User-Agent': 'provemaps-frontend' },
  })
    .then((res) => res.json())
    .then((data) => {
      if (!data?.display_name) return
      const addr = data.address || {}
      const streetParts = [
        addr.road || addr.pedestrian || addr.cycleway || addr.footway || '',
        addr.house_number || '',
        addr.suburb || addr.neighbourhood || '',
      ].filter(Boolean)
      form.value.address = streetParts.join(', ') || data.display_name
      addressQuery.value = form.value.address
      form.value.city = addr.city || addr.town || addr.village || addr.county || form.value.city || ''
      form.value.state = addr.state || form.value.state || ''
      form.value.zip_code = addr.postcode || form.value.zip_code || ''
    })
    .catch(() => {})
}
</script>
