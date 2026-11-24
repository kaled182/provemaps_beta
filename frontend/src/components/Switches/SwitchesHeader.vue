<template>
  <header class="flex-none px-4 md:px-6 py-2 border-b border-neutral-200 bg-surface flex items-center gap-3 flex-wrap">
    <h1 class="text-base font-semibold">Monitoramento de Switches</h1>
    <span v-if="zabbix" class="badge" :class="badge.cls" :title="zabbixError || ''" data-testid="sw-zabbix-badge">
      <span class="dot" aria-hidden="true"></span>{{ badge.label }}
    </span>
    <span class="text-neutral-400 cursor-help" :title="thresholdText" :aria-label="thresholdText" data-testid="sw-thresholds">
      <PhQuestion :size="16" />
    </span>

    <div class="ml-auto flex items-center gap-2 flex-wrap">
      <select v-model="vendor" class="field" aria-label="Fabricante" data-testid="sw-vendor-select">
        <option :value="null">Todos os fabricantes</option>
        <option v-for="v in vendors" :key="v.value" :value="v.value">{{ v.label }}</option>
      </select>
      <select v-model="pop" class="field" aria-label="POP / Site" data-testid="sw-pop-select">
        <option :value="null">Todos os POPs</option>
        <option v-for="p in pops" :key="p.value" :value="p.value">{{ p.label }}</option>
      </select>
      <select v-model="switchId" class="field" aria-label="Switch" data-testid="sw-switch-select">
        <option :value="null">{{ switches.length === allCount ? 'Todos os switches' : `Todos os switches (${switches.length})` }}</option>
        <option v-for="s in switches" :key="s.device_id" :value="s.device_id">{{ s.name }}</option>
      </select>
      <div class="pills" role="group" aria-label="Filtro">
        <button
          v-for="f in FILTERS"
          :key="f.value"
          type="button"
          class="pill"
          :class="{ 'pill-on': filter === f.value }"
          :aria-pressed="filter === f.value"
          :data-testid="`sw-filter-${f.value}`"
          @click="filter = f.value"
        >
          {{ f.label }}
        </button>
      </div>
      <label class="search">
        <PhMagnifyingGlass :size="14" class="text-neutral-400" />
        <input v-model="query" type="search" placeholder="Porta ou descrição…" aria-label="Buscar porta" data-testid="sw-query" />
      </label>
      <button type="button" class="icon-btn" title="Atualizar agora" :disabled="loading" data-testid="sw-refresh" @click="$emit('refresh')">
        <PhArrowClockwise :size="16" :class="{ 'animate-spin': loading }" />
      </button>
    </div>
  </header>
</template>

<script setup>
/** Cabeçalho da tela de Switches (EV-0115) — o mesmo desenho do GPON (GponHeader). */
import { computed } from 'vue'
import { PhArrowClockwise, PhMagnifyingGlass, PhQuestion } from '@phosphor-icons/vue'
import { FILTERS } from '@/composables/useSwitchesOverview'
import { formatCompact } from '@/utils/ptBrFormat'

const props = defineProps({
  zabbix: { type: String, default: null },
  zabbixError: { type: String, default: null },
  thresholds: { type: Object, default: null },
  switches: { type: Array, default: () => [] },
  allCount: { type: Number, default: 0 },
  vendors: { type: Array, default: () => [] },
  pops: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
defineEmits(['refresh'])
const vendor = defineModel('vendor', { type: String, default: null })
const pop = defineModel('pop', { type: String, default: null })
const switchId = defineModel('switchId', { type: Number, default: null })
const filter = defineModel('filter', { type: String, default: 'all' })
const query = defineModel('query', { type: String, default: '' })

const BADGES = {
  ok: { label: 'Zabbix ativo', cls: 'badge-success' },
  down: { label: 'Zabbix indisponível', cls: 'badge-danger' },
  partial: { label: 'Coleta parcial', cls: 'badge-warning' },
}
const badge = computed(() => BADGES[props.zabbix] || BADGES.partial)

const thresholdText = computed(() => {
  const t = props.thresholds
  if (!t) return 'Limiares de sinal indisponíveis'
  const w = formatCompact(t.warning)
  const c = formatCompact(t.critical)
  return `RX de backbone: Normal > ${w} dBm · Atenção ${w} a ${c} · Crítico < ${c} · Banda > ${formatCompact(t.utilization_pct)}% = atenção`
})
</script>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid currentColor;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: currentColor;
}
.badge-success {
  color: rgb(var(--success));
  border-color: rgb(var(--success) / 0.4);
  background: rgb(var(--success) / 0.1);
}
.badge-danger {
  color: rgb(var(--danger));
  border-color: rgb(var(--danger) / 0.4);
  background: rgb(var(--danger) / 0.1);
}
.badge-warning {
  color: rgb(var(--warning));
  border-color: rgb(var(--warning) / 0.4);
  background: rgb(var(--warning) / 0.1);
}
.field {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid rgb(var(--n-300));
  background: rgb(var(--surface));
  font-size: 13px;
  color: rgb(var(--n-900));
}
.pills {
  display: inline-flex;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  overflow: hidden;
}
.pill {
  padding: 4px 10px;
  font-size: 12px;
  color: rgb(var(--n-600));
  background: rgb(var(--surface));
  border-left: 1px solid rgb(var(--n-200));
}
.pill:first-child {
  border-left: 0;
}
.pill:hover {
  background: rgb(var(--n-100));
}
.pill-on,
.pill-on:hover {
  color: rgb(var(--primary-600));
  background: rgb(var(--primary-500) / 0.12);
  font-weight: 600;
}
.search {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid rgb(var(--n-300));
  background: rgb(var(--surface));
}
.search input {
  width: 13rem;
  border: 0;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: rgb(var(--n-900));
}
.icon-btn {
  padding: 6px;
  border-radius: 6px;
  color: rgb(var(--n-600));
}
.icon-btn:hover {
  background: rgb(var(--n-100));
}
</style>
