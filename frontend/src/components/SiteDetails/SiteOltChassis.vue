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
      <!-- EV-0121: chassi + inspetor na metade de cima (rola por dentro); ONUs logo por baixo -->
      <div class="soc-top" data-testid="site-olt-top">
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
      </div>

      <section class="soc-onus" data-testid="site-olt-onus">
        <h3 class="soc-onus-title">
          {{ listScope }} · <span class="num">{{ listOnus.length }}</span> ONUs
        </h3>
        <PonOnuList :onus="listOnus" :show-olt="false" :thresholds="data.thresholds || null" :reset-key="listKey" />
      </section>
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
import PonOnuList from '@/components/Gpon/PonOnuList.vue'
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

/**
 * EV-0121: ONUs da porta escolhida no chassi (a mais crítica ao abrir), da placa escolhida, ou
 * — sem escolha («Todas as portas») — da OLT inteira. Sincroniza com o inspetor à direita.
 */
const BAND_LABEL = { normal: 'normal', warning: 'atenção', critical: 'crítico' }
const afterColon = (key) => (key === null ? null : key.slice(key.indexOf(':') + 1))
const listOnus = computed(() => {
  const onus = data.value?.onus || []
  const pon = afterColon(selectedPon.value)
  // a faixa do histograma do inspetor (EV-0107) filtra também a lista
  if (pon !== null) return onus.filter((o) => String(o.pon_id) === pon && (signalBand.value === null || o.signal === signalBand.value))
  const slot = afterColon(selectedSlot.value)
  if (slot !== null) return onus.filter((o) => String(o.pon_id).startsWith(`${slot}/`))
  return onus
})
const listScope = computed(() => {
  const pon = afterColon(selectedPon.value)
  if (pon !== null) {
    const label = (olt.value?.pons || []).find((p) => String(p.pon_id) === pon)?.label || `PON ${pon}`
    return signalBand.value === null ? label : `${label} · sinal ${BAND_LABEL[signalBand.value] || signalBand.value}`
  }
  const slot = afterColon(selectedSlot.value)
  if (slot !== null) return `Slot ${slot}`
  return 'Todas as portas'
})
const listKey = computed(() => `${props.deviceId}|${selectedPon.value}|${selectedSlot.value}`)
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

<style scoped>
.soc-top {
  max-height: 340px;
  overflow-y: auto;
}
.soc-onus {
  margin-top: 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  background: rgb(var(--surface));
  overflow: hidden;
}
.soc-onus-title {
  margin: 0;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: rgb(var(--n-600));
  border-bottom: 1px solid rgb(var(--n-200));
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
</style>
