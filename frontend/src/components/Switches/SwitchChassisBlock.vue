<template>
  <section class="rounded-lg border border-neutral-200 bg-surface" :data-testid="`sw-block-${sw.device_id}`">
    <header class="flex items-center gap-3 flex-wrap px-3 py-2 border-b border-neutral-200 text-sm">
      <PhHardDrives :size="16" class="text-neutral-500" />
      <span class="font-semibold">{{ sw.name }}</span>
      <span class="text-xs text-neutral-500">{{ [sw.model, sw.site_name].filter(Boolean).join(' · ') }}</span>
      <span class="num text-xs text-neutral-600">{{ sw.ip || '—' }}</span>
      <span v-if="sw.status === 'offline'" class="flag flag-danger">offline</span>
      <span v-else-if="sw.status === 'unknown'" class="flag">estado desconhecido</span>
      <span v-if="!sw.collection_ok" class="flag flag-warning">coleta sem dados</span>
      <span class="ml-auto flex items-center gap-3 text-xs text-neutral-600 num">
        <span title="CPU"><PhCpu :size="13" class="inline -mt-0.5" /> {{ sw.cpu_pct === null ? '—' : `${sw.cpu_pct}%` }}</span>
        <span title="Temperatura"><PhThermometer :size="13" class="inline -mt-0.5" /> {{ sw.temperature_c === null ? '—' : `${sw.temperature_c} °C` }}</span>
        <span title="Uptime do switch">{{ sw.uptime_s ? formatDuration(sw.uptime_s) : '—' }}</span>
      </span>
    </header>

    <div class="split p-3">
      <div ref="wrap" class="stage" @mouseleave="tip = null">
        <SwitchChassis1u
          :sw="sw"
          :ports="ports"
          :selected-name="selectedName"
          :visible-names="visibleNames"
          @select="(p) => $emit('select', p)"
          @hover="onHover"
        />
        <div
          v-if="tip"
          class="tip num"
          :class="{ 'tip-below': tip.below }"
          :style="{ left: `${tip.left}px`, top: `${tip.top}px` }"
          role="tooltip"
          data-testid="sw-chassis-tooltip"
        >
          {{ tip.text }}
        </div>
      </div>
      <SwitchPortInspector :sw="sw" :port="inspectPort" :preview="isPreview" :thresholds="thresholds" />
    </div>
  </section>
</template>

<script setup>
/**
 * Um switch na «vista do chassi» (EV-0116): cabeçalho, painel frontal 1U e o inspetor da
 * porta. Sem porta escolhida neste switch, o inspetor abre na mais crítica (pré-visualização).
 */
import { computed, ref } from 'vue'
import { PhCpu, PhHardDrives, PhThermometer } from '@phosphor-icons/vue'
import SwitchChassis1u from './SwitchChassis1u.vue'
import SwitchPortInspector from './SwitchPortInspector.vue'
import { mostCriticalPort } from '@/composables/useSwitchesOverview'
import { formatDuration } from '@/utils/ptBrFormat'

const props = defineProps({
  sw: { type: Object, required: true },
  /** todas as portas deste switch (o chassi desenha-as todas) */
  ports: { type: Array, default: () => [] },
  /** portas que passam no filtro atual — as outras ficam esbatidas; null = todas */
  visibleNames: { type: Array, default: null },
  /** porta escolhida (de qualquer switch) */
  selected: { type: Object, default: null },
  thresholds: { type: Object, default: null },
})
defineEmits(['select'])

const selectedName = computed(() => (props.selected && props.selected.device_id === props.sw.device_id ? props.selected.name : null))
const previewPort = computed(() => (selectedName.value === null ? mostCriticalPort(props.ports) : null))
const isPreview = computed(() => previewPort.value !== null)
const inspectPort = computed(() =>
  selectedName.value !== null ? props.ports.find((p) => p.name === selectedName.value) || null : previewPort.value,
)

const wrap = ref(null)
const tip = ref(null)
function onHover(payload) {
  if (!payload || !wrap.value) {
    tip.value = null
    return
  }
  const r = payload.el.getBoundingClientRect()
  const w = wrap.value.getBoundingClientRect()
  const below = r.top - w.top < 36
  tip.value = {
    text: payload.text,
    left: Math.min(Math.max(r.left - w.left + r.width / 2, 130), Math.max(w.width - 130, 130)),
    top: below ? r.bottom - w.top : r.top - w.top,
    below,
  }
}
</script>

<style scoped>
.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.split {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}
@media (min-width: 1280px) {
  .split {
    grid-template-columns: minmax(0, 1fr) 340px;
  }
}
.stage {
  position: relative;
  min-width: 0;
}
.tip {
  position: absolute;
  z-index: 5;
  transform: translate(-50%, calc(-100% - 6px));
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  white-space: nowrap;
  pointer-events: none;
  color: rgb(var(--n-50));
  background: rgb(var(--n-900));
  box-shadow: 0 4px 12px rgb(var(--n-950) / 0.25);
}
.tip-below {
  transform: translate(-50%, 6px);
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
