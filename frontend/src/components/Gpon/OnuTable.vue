<template>
  <section class="shrink-0 rounded-lg border border-neutral-200 bg-surface overflow-x-auto" data-testid="gpon-onu-panel">
    <!-- shrink-0: no <main> flex-col com min-h-0, overflow-auto deixava o flex encolher a lista a 0 px
         debaixo de um chassi alto (EV-0122) -->
    <!-- EV-0108: com uma PON selecionada, abas ONUs | Eventos recentes 24 h -->
    <div v-if="eventsFor" class="tabs border-b border-neutral-200" role="tablist" data-testid="gpon-onu-tabs">
      <button
        type="button"
        role="tab"
        class="tab"
        :class="{ 'tab-on': tab === 'onus' }"
        :aria-selected="tab === 'onus'"
        data-testid="gpon-tab-onus"
        @click="tab = 'onus'"
      >
        {{ scope }} · <span class="num">{{ onus.length }}</span>
      </button>
      <button
        type="button"
        role="tab"
        class="tab"
        :class="{ 'tab-on': tab === 'events' }"
        :aria-selected="tab === 'events'"
        data-testid="gpon-tab-events"
        @click="tab = 'events'"
      >
        Eventos recentes 24 h
      </button>
    </div>
    <h2 v-else class="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-neutral-600 border-b border-neutral-200">
      {{ scope }} · <span class="num">{{ onus.length }}</span>
    </h2>
    <PonEvents
      v-if="eventsFor && tab === 'events'"
      :device-id="eventsFor.deviceId"
      :pon-id="eventsFor.ponId"
      :refresh-key="refreshKey"
    />
    <PonOnuList
      v-else
      :onus="onus"
      :show-olt="showOlt"
      :thresholds="thresholds"
      :reset-key="eventsFor ? `${eventsFor.deviceId}:${eventsFor.ponId}` : scope"
    />
  </section>
</template>

<script setup>
/** Painel inferior do ecrã GPON: abas (com PON selecionada) ONUs | Eventos 24 h; a lista é a PonOnuList (EV-0119). */
import { ref, watch } from 'vue'
import PonEvents from './PonEvents.vue'
import PonOnuList from './PonOnuList.vue'

const props = defineProps({
  onus: { type: Array, default: () => [] },
  scope: { type: String, default: 'ONUs' },
  showOlt: { type: Boolean, default: true },
  /** EV-0108: PON selecionada ({ deviceId, ponId }) — mostra a aba de eventos. */
  eventsFor: { type: Object, default: null },
  /** muda a cada coleta, para a aba de eventos recarregar */
  refreshKey: { type: [String, Number], default: null },
  thresholds: { type: Object, default: null },
})

const tab = ref('onus')
// Outra PON (ou nenhuma) volta à lista de ONUs.
watch(
  () => (props.eventsFor ? `${props.eventsFor.deviceId}:${props.eventsFor.ponId}` : null),
  () => {
    tab.value = 'onus'
  },
)
</script>

<style scoped>
.tabs {
  display: flex;
  gap: 2px;
  padding: 0 6px;
}
.tab {
  padding: 8px 10px;
  border-bottom: 2px solid transparent;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: rgb(var(--n-500));
}
.tab:hover {
  color: rgb(var(--n-800));
}
.tab-on {
  color: rgb(var(--n-900));
  border-bottom-color: rgb(var(--primary-500));
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
</style>
