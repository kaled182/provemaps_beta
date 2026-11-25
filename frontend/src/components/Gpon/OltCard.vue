<template>
  <section class="rounded-lg border border-neutral-200 bg-surface" :data-testid="`gpon-olt-${olt.device_id}`">
    <header class="flex items-center gap-3 flex-wrap px-3 py-2 border-b border-neutral-200 text-sm">
      <PhHardDrives :size="16" class="text-neutral-500" />
      <span class="font-semibold">{{ olt.name }}</span>
      <span class="text-xs text-neutral-500">{{ vendorModel }}</span>
      <span class="num text-xs text-neutral-600">{{ olt.ip || '—' }}</span>
      <span v-if="olt.status === 'offline'" class="flag flag-danger" data-testid="gpon-olt-offline">offline</span>
      <span v-else-if="olt.status === 'unknown'" class="flag" data-testid="gpon-olt-unknown">estado desconhecido</span>
      <span v-if="olt.collection_ok === false" class="flag flag-warning" data-testid="gpon-olt-nodata">coleta sem dados</span>
      <span class="ml-auto flex items-center gap-3 text-xs text-neutral-600 num">
        <span title="CPU"><PhCpu :size="13" class="inline -mt-0.5" /> {{ olt.cpu_pct === null || olt.cpu_pct === undefined ? '—' : formatPercent(olt.cpu_pct) }}</span>
        <span title="Temperatura" data-testid="gpon-olt-temp"><PhThermometer :size="13" class="inline -mt-0.5" /> {{ olt.temperature_c === null || olt.temperature_c === undefined ? '—' : `${formatNumber(olt.temperature_c, 0)} °C` }}</span>
        <span title="ONUs online / total">{{ formatInt(olt.onus_online) }}/{{ formatInt(olt.onus_total) }} ONUs</span>
      </span>
    </header>
    <div v-if="olt.pons.length" class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 p-3">
      <PonCard
        v-for="p in olt.pons"
        :key="p.pon_id"
        :pon="p"
        :selected="selectedPon === ponKey(olt.device_id, p.pon_id)"
        @toggle="$emit('toggle-pon', olt.device_id, p.pon_id)"
      />
    </div>
    <p v-else class="px-3 py-2 text-xs text-neutral-500">Nenhuma PON conhecida.</p>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { PhCpu, PhHardDrives, PhThermometer } from '@phosphor-icons/vue'
import PonCard from './PonCard.vue'
import { ponKey } from '@/composables/useGponOverview'
import { formatInt, formatNumber, formatPercent } from '@/utils/ptBrFormat'

const props = defineProps({
  olt: { type: Object, required: true },
  selectedPon: { type: String, default: null },
})
defineEmits(['toggle-pon'])

const vendorModel = computed(() =>
  [props.olt.vendor ? props.olt.vendor.toUpperCase() : null, props.olt.model, props.olt.technology?.toUpperCase()]
    .filter(Boolean)
    .join(' · '),
)
</script>

<style scoped>
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.flag {
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  color: rgb(var(--n-600));
  border: 1px solid rgb(var(--n-300));
}
.flag-danger {
  color: rgb(var(--danger));
  border-color: rgb(var(--danger) / 0.4);
}
.flag-warning {
  color: rgb(var(--warning));
  border-color: rgb(var(--warning) / 0.4);
}
</style>
