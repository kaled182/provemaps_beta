<template>
  <div data-testid="site-olt-chassis">
    <p v-if="loading && !data" class="py-6 text-center text-sm text-neutral-500">A carregar o chassi da OLT…</p>
    <p v-else-if="error" class="py-6 text-center text-sm text-danger" role="alert" data-testid="site-olt-error">
      Erro ao carregar a OLT: {{ error }}
    </p>
    <template v-else-if="olt">
      <p v-if="!data.zabbix_ok" class="mb-2 text-xs text-warning" role="alert" data-testid="site-olt-stale">
        Coleta GPON sem resposta do Zabbix — o chassi mostra a última coleta gravada.
      </p>
      <OltChassis
        :olt="olt"
        :pons="olt.pons || []"
        :selected-pon="selectedPon"
        :selected-slot="selectedSlot"
        :thresholds="data.thresholds || null"
        :onus="data.onus || []"
        :signal-band="signalBand"
        in-map
        @toggle-pon="togglePon"
        @toggle-slot="toggleSlot"
        @clear-selection="clearSelection"
        @signal-band="toggleSignalBand"
      />
    </template>
  </div>
</template>

<script setup>
/**
 * Chassi interativo de UMA OLT dentro do modal de Site (EV-0113): o mesmo `OltChassis` do
 * ecrã GPON (placas, LEDs das PONs, inspetor com RX médio/pior, LOS e diagnóstico), com os
 * dados de `GET /api/v1/monitoring/gpon/?olt=<id>` — só esta OLT — e a seleção local (não
 * mexe no endereço do mapa, ao contrário do ecrã GPON). Abre já na PON mais crítica.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import OltChassis from '@/components/Gpon/OltChassis.vue'
import { mostCriticalPon } from '@/components/Gpon/chassisLed'
import { GPON_URL, REFRESH_MS, ponKey, slotKey } from '@/composables/useGponOverview'

const props = defineProps({
  deviceId: { type: Number, required: true },
})
/** `loaded` leva a OLT (cpu_pct, temperature_c…) para a faixa do equipamento. */
const emit = defineEmits(['loaded'])

const api = useApi()
const data = ref(null)
const loading = ref(false)
const error = ref('')
const selectedPon = ref(null)
const selectedSlot = ref(null)
const bandChoice = ref(null)
let seq = 0
let timer = null

const olt = computed(() => data.value?.olts?.[0] || null)
const signalBand = computed(() =>
  bandChoice.value !== null && bandChoice.value.key === selectedPon.value ? bandChoice.value.band : null,
)

async function load({ reset = false } = {}) {
  const mine = ++seq
  loading.value = true
  if (reset) error.value = ''
  try {
    const body = await api.get(GPON_URL, { olt: props.deviceId })
    if (mine !== seq) return
    data.value = body
    error.value = ''
    const current = body?.olts?.[0] || null
    emit('loaded', current)
    if (reset && current) {
      const ponId = mostCriticalPon(current.pons)
      selectedSlot.value = null
      selectedPon.value = ponId === null ? null : ponKey(current.device_id, ponId)
    }
  } catch (e) {
    if (mine === seq && !data.value) error.value = e?.message || 'erro desconhecido'
  } finally {
    if (mine === seq) loading.value = false
  }
}

function startTimer() {
  stopTimer()
  timer = setInterval(() => load(), REFRESH_MS)
}
function stopTimer() {
  if (timer) clearInterval(timer)
  timer = null
}

watch(
  () => props.deviceId,
  () => {
    data.value = null
    selectedPon.value = null
    selectedSlot.value = null
    bandChoice.value = null
    load({ reset: true })
    startTimer()
  },
  { immediate: true },
)
onBeforeUnmount(stopTimer)

function togglePon(deviceId, ponId) {
  bandChoice.value = null
  const key = ponKey(deviceId, ponId)
  selectedPon.value = selectedPon.value === key ? null : key
  if (selectedPon.value !== null) selectedSlot.value = null
}
function toggleSlot(deviceId, slot) {
  bandChoice.value = null
  const key = slotKey(deviceId, slot)
  selectedSlot.value = selectedSlot.value === key ? null : key
  if (selectedSlot.value !== null) selectedPon.value = null
}
function clearSelection() {
  bandChoice.value = null
  selectedPon.value = null
  selectedSlot.value = null
}
function toggleSignalBand(deviceId, ponId, band) {
  const key = ponKey(deviceId, ponId)
  if (selectedPon.value !== key) {
    selectedSlot.value = null
    selectedPon.value = key
  }
  bandChoice.value = signalBand.value === band ? null : { key, band }
}
</script>
