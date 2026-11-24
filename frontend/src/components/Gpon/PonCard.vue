<template>
  <button
    type="button"
    class="pon font-mono tabular-nums"
    :class="[`pon-${pon.severity || 'normal'}`, { 'pon-selected': selected }]"
    :aria-pressed="selected"
    :title="pon.collective_drop ? 'Queda em massa' : ''"
    :data-testid="`gpon-pon-${pon.pon_id}`"
    @click="$emit('toggle')"
  >
    <span class="row">
      <span class="font-semibold text-neutral-800">{{ pon.label }}</span>
      <span class="dot" :class="dotClass" :title="statusLabel" aria-hidden="true"></span>
    </span>
    <span class="row text-neutral-600">
      {{ formatInt(pon.onus_provisioned) }}/{{ formatInt(pon.capacity) }} ONUs
    </span>
    <span class="row">
      <span class="text-neutral-600" data-testid="gpon-pon-rx">RX méd: {{ formatDbm(pon.rx_avg_dbm) }}</span>
      <span v-if="pon.los > 0" class="chip chip-danger">{{ pon.los }} LOS</span>
      <span v-else-if="attention > 0" class="chip chip-warning">{{ attention }} aten.</span>
    </span>
    <span class="occ" aria-hidden="true">
      <span class="occ-fill" :class="highOccupancy ? 'bg-warning' : 'bg-neutral-400'" :style="{ width: `${Math.min(pon.occupancy_pct ?? 0, 100)}%` }"></span>
    </span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { OCCUPANCY_LIMIT } from '@/composables/useGponOverview'
import { formatDbm, formatInt } from '@/utils/ptBrFormat'

const props = defineProps({
  pon: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})
defineEmits(['toggle'])

const attention = computed(() => (props.pon.signal_warning ?? 0) + (props.pon.signal_critical ?? 0))
const highOccupancy = computed(() => (props.pon.occupancy_pct ?? 0) > OCCUPANCY_LIMIT)
const dotClass = computed(() => ({ up: 'bg-success', down: 'bg-danger' })[props.pon.status] || 'bg-neutral-400')
const statusLabel = computed(() => ({ up: 'PON ativa', down: 'PON em baixo' })[props.pon.status] || 'Estado da PON desconhecido')
</script>

<style scoped>
.pon {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px 8px;
  border-radius: 6px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
  font-size: 11.5px;
  text-align: left;
  overflow: hidden;
  cursor: pointer;
}
.pon:hover {
  border-color: rgb(var(--n-300));
}
.pon-warning {
  border-color: rgb(var(--warning) / 0.5);
  background: rgb(var(--warning) / 0.08);
}
.pon-critical {
  border-color: rgb(var(--danger) / 0.55);
  background: rgb(var(--danger) / 0.08);
}
.pon-selected {
  box-shadow: 0 0 0 2px rgb(var(--primary-500));
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  white-space: nowrap;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  flex: none;
}
.chip {
  padding: 0 4px;
  border-radius: 3px;
  font-size: 10.5px;
  font-weight: 600;
}
.chip-danger {
  color: rgb(var(--danger));
  background: rgb(var(--danger) / 0.12);
}
.chip-warning {
  color: rgb(var(--warning));
  background: rgb(var(--warning) / 0.14);
}
.occ {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 3px;
  background: rgb(var(--n-200));
}
.occ-fill {
  display: block;
  height: 100%;
}
</style>
