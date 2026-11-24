<template>
  <BaseModal :show="show" :title="title" :subtitle="subtitle" :icon="PhChartLine" size="md" @close="$emit('close')">
    <template #header-actions>
      <select v-model.number="hours" class="field" aria-label="Período" data-testid="gpon-history-hours">
        <option v-for="h in HOURS" :key="h" :value="h">{{ h }} h</option>
      </select>
    </template>
    <p v-if="loading" class="text-sm text-neutral-500" data-testid="gpon-history-loading">Carregando…</p>
    <p v-else-if="error" class="msg msg-danger" role="alert" data-testid="gpon-history-error">Erro ao carregar o histórico: {{ error }}</p>
    <p v-else-if="history && !history.zabbix_ok" class="msg msg-warning" role="alert" data-testid="gpon-history-zabbix-down">
      Zabbix indisponível<span v-if="history.zabbix_error" class="num">: {{ history.zabbix_error }}</span>
    </p>
    <TimeSeriesChart v-else-if="history" :series="series" :thresholds="chartThresholds" :unit="history.unit || 'dBm'" :height="260" />
  </BaseModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { PhChartLine } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import TimeSeriesChart from '@/components/charts/TimeSeriesChart.vue'
import { useApi } from '@/composables/useApi'

const HOURS = [6, 24, 72, 168]
const props = defineProps({
  show: { type: Boolean, default: false },
  onu: { type: Object, default: null },
  thresholds: { type: Object, default: null },
})
defineEmits(['close'])

const api = useApi()
const hours = ref(24)
const history = ref(null)
const loading = ref(false)
const error = ref('')
let seq = 0

const title = computed(() => (props.onu ? `ONU ${props.onu.serial || props.onu.mac || props.onu.id}` : 'ONU'))
const subtitle = computed(() => (props.onu ? `${props.onu.olt_name} · ${props.onu.pon_id} : ${props.onu.onu_index}` : ''))
const series = computed(() => [{ label: history.value?.label || 'RX', data: history.value?.points || [] }])
const chartThresholds = computed(() => {
  const t = props.thresholds
  if (!t) return []
  return [
    { value: t.warning, label: 'Atenção' },
    { value: t.critical, label: 'Crítico' },
  ].filter((x) => typeof x.value === 'number')
})

async function load() {
  if (!props.show || !props.onu) return
  const mine = ++seq
  loading.value = true
  error.value = ''
  try {
    const res = await api.get(`/api/v1/monitoring/gpon/onus/${props.onu.id}/history/`, { hours: hours.value })
    if (mine === seq) history.value = res
  } catch (e) {
    if (mine === seq) error.value = e?.message || 'erro desconhecido'
  } finally {
    if (mine === seq) loading.value = false
  }
}

watch(
  () => [props.show, props.onu?.id],
  ([open]) => {
    history.value = null
    if (open) load()
  },
  { immediate: true },
)
watch(hours, load)
</script>

<style scoped>
.field {
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid rgb(var(--n-300));
  background: rgb(var(--surface));
  font-size: 13px;
  color: rgb(var(--n-900));
}
.msg {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  border: 1px solid;
}
.msg-danger {
  color: rgb(var(--danger));
  border-color: rgb(var(--danger) / 0.4);
  background: rgb(var(--danger) / 0.1);
}
.msg-warning {
  color: rgb(var(--warning));
  border-color: rgb(var(--warning) / 0.4);
  background: rgb(var(--warning) / 0.1);
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}
</style>
