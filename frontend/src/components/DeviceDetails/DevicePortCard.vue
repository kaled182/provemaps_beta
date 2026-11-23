<template>
  <article
    class="dpc"
    :class="`dpc-${state.key}`"
    role="button"
    tabindex="0"
    data-testid="device-port-card"
    @click="emit('traffic', port)"
    @keydown.enter.prevent="emit('traffic', port)"
  >
    <header class="dpc-head">
      <span class="dpc-name" :title="port.name">{{ port.name }}</span>
      <span class="dpc-badge" data-testid="device-port-state">{{ state.label }}</span>
      <div class="dpc-actions">
        <button v-if="hasReading" type="button" class="dpc-btn" title="Configurar alarme" @click.stop="emit('alarm', port)">
          <PhBell :size="14" />
        </button>
        <button v-if="port.connected_cable" type="button" class="dpc-btn" title="Mapa de conectividade" @click.stop="emit('connectivity', port)">
          <PhGraph :size="14" />
        </button>
        <button type="button" class="dpc-btn" title="Ações" @click.stop="emit('actions', port)">
          <PhDotsThreeVertical :size="14" weight="bold" />
        </button>
      </div>
    </header>

    <p v-if="port.description" class="dpc-desc" :title="port.description">{{ port.description }}</p>

    <div class="dpc-levels">
      <span
        v-for="lv in levels"
        :key="lv.key"
        class="dpc-pill"
        :class="lv.cls"
        :title="lv.title"
        :data-testid="`device-port-${lv.key}`"
      >
        <span class="dpc-pill-k">{{ lv.label }}</span>{{ lv.text }}
      </span>
    </div>

    <footer v-if="port.connected_cable || stamp" class="dpc-foot">
      <span v-if="port.connected_cable" class="dpc-cable">{{ port.connected_cable.name || `Cabo #${port.connected_cable.id}` }}</span>
      <span v-if="stamp" class="dpc-stamp">{{ stamp }}</span>
    </footer>
  </article>
</template>

<script setup>
/** Card de porta do modal de Dispositivo (EV-0066): RX/TX em pílulas pelos limiares. */
import { computed } from 'vue'
import { PhBell, PhGraph, PhDotsThreeVertical } from '@phosphor-icons/vue'
import { DEFAULT_THRESHOLDS, formatDbm, levelOf, portState } from '@/utils/devicePorts'

const props = defineProps({
  port: { type: Object, required: true },
  thresholds: { type: Object, default: () => DEFAULT_THRESHOLDS },
})
const emit = defineEmits(['traffic', 'alarm', 'connectivity', 'actions'])

const state = computed(() => portState(props.port, props.thresholds))
const hasReading = computed(() => props.port.optical_rx_power !== null || props.port.optical_tx_power !== null)

const levels = computed(() =>
  [
    { key: 'rx', label: 'RX', value: props.port.optical_rx_power },
    { key: 'tx', label: 'TX', value: props.port.optical_tx_power },
  ].map((l) => {
    // Leitura velha não leva cor de estado: não é o estado atual.
    const level = props.port.stale ? null : levelOf(l.value, props.thresholds)
    return {
      ...l,
      text: formatDbm(l.value),
      cls: level ? `dpc-pill-${level}` : 'dpc-pill-none',
      title: l.value === null ? `${l.label} sem leitura` : `${l.label} ${formatDbm(l.value)} dBm`,
    }
  }),
)

const stamp = computed(() => {
  if (!props.port.lastCheck || !hasReading.value) return ''
  const d = new Date(props.port.lastCheck)
  const when = d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
  return props.port.stale ? `leitura de ${when}` : ''
})
</script>

<style scoped>
.dpc {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  background: rgb(var(--surface));
  cursor: pointer;
  transition: border-color 0.15s ease;
  min-width: 0;
}
.dpc:hover,
.dpc:focus-visible {
  border-color: rgb(var(--primary-500));
  outline: none;
}
.dpc-critical { border-color: rgb(var(--danger) / 0.45); }
.dpc-head {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.dpc-name {
  flex: 1;
  min-width: 0;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--n-900));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dpc-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 9999px;
  white-space: nowrap;
  background: rgb(var(--n-100));
  color: rgb(var(--n-600));
}
.dpc-normal .dpc-badge { background: rgb(var(--success) / 0.14); color: rgb(var(--success)); }
.dpc-warning .dpc-badge { background: rgb(var(--warning) / 0.16); color: rgb(var(--warning)); }
.dpc-critical .dpc-badge { background: rgb(var(--danger) / 0.14); color: rgb(var(--danger)); }
.dpc-actions { display: flex; gap: 2px; }
.dpc-btn {
  display: inline-flex;
  padding: 3px;
  border-radius: 6px;
  color: rgb(var(--n-500));
}
.dpc-btn:hover { background: rgb(var(--n-100)); color: rgb(var(--n-900)); }
.dpc-desc {
  margin: 0;
  font-size: 11px;
  color: rgb(var(--n-500));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dpc-levels { display: flex; gap: 6px; }
.dpc-pill {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 1px 8px;
  border-radius: 9999px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid transparent;
}
.dpc-pill-k { font-family: Inter, sans-serif; font-size: 9px; font-weight: 700; opacity: 0.75; }
.dpc-pill-normal { background: rgb(var(--success) / 0.12); color: rgb(var(--success)); }
.dpc-pill-warning { background: rgb(var(--warning) / 0.14); color: rgb(var(--warning)); }
.dpc-pill-critical { background: rgb(var(--danger) / 0.12); color: rgb(var(--danger)); }
.dpc-pill-none { background: rgb(var(--n-100)); color: rgb(var(--n-500)); border-color: rgb(var(--n-200)); }
.dpc-foot {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  font-size: 10px;
  color: rgb(var(--n-500));
  min-width: 0;
}
.dpc-cable { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dpc-stamp { white-space: nowrap; font-family: 'JetBrains Mono', ui-monospace, monospace; }
</style>
