<template>
  <div class="h-full flex flex-col bg-canvas" data-testid="monitoring-switches">
    <SwitchesHeader
      v-model:vendor="vendor"
      v-model:pop="pop"
      v-model:switch-id="switchId"
      v-model:filter="filter"
      v-model:query="query"
      :zabbix="zabbix"
      :zabbix-error="data?.zabbix_error || null"
      :thresholds="thresholds"
      :switches="scopedSwitches"
      :all-count="allCount"
      :vendors="vendors"
      :pops="pops"
      :loading="loading"
      @refresh="load({ refresh: true })"
    />

    <main class="flex-1 overflow-auto px-4 md:px-6 py-3 space-y-3">
      <p v-if="error && !data" class="sw-alert" role="alert" data-testid="sw-error">Erro ao carregar os switches: {{ error }}</p>
      <p v-else-if="!data" class="py-10 text-center text-sm text-neutral-500">A carregar os switches…</p>
      <template v-else>
        <p v-if="!data.zabbix_ok" class="sw-alert" role="alert" data-testid="sw-zabbix-down">
          Zabbix indisponível: o estado das portas não pôde ser lido. {{ data.zabbix_error || '' }}
        </p>
        <p v-else-if="error" class="sw-note" role="status">A última atualização falhou ({{ error }}); a mostrar a coleta de {{ collectedAt }}.</p>

        <SwitchesKpis :kpis="kpis" />

        <section v-if="visibleSwitches.length" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-2" aria-label="Switches" data-testid="sw-grid">
          <SwitchCard
            v-for="s in visibleSwitches"
            :key="s.device_id"
            :sw="s"
            :ports="portsOf(s.device_id)"
            :thresholds="thresholds"
            :selected="switchId === s.device_id"
            @select="(id) => (switchId = switchId === id ? null : id)"
          />
        </section>
        <p v-else class="py-6 text-center text-sm text-neutral-500" data-testid="sw-none">Nenhum switch neste recorte.</p>

        <SwitchPortTable
          :ports="visiblePorts"
          :thresholds="thresholds"
          :show-switch="visibleSwitches.length > 1"
          :selected-key="selectedPort ? `${selectedPort.device_id}:${selectedPort.name}` : null"
          :free-hidden="freeHidden"
          @select="selectPort"
          @history="openHistory"
        />
        <p class="text-xs text-neutral-500" data-testid="sw-collected">
          Coleta do Zabbix {{ collectedAt }} · atualiza a cada minuto
        </p>
      </template>
    </main>

    <PortTrafficModal :is-open="historyPort !== null" :port="historyPort" @close="historyPort = null" />
  </div>
</template>

<script setup>
/**
 * Monitoramento de Switches (/monitoring/switches, EV-0115): cabeçalho com recortes, 5 KPIs,
 * grade compacta dos switches e a tabela das portas. O chassi 1U e o inspetor da porta
 * entram no EV-0116. Só Huawei por agora (Ubiquiti: EV-0117).
 */
import { computed, defineAsyncComponent, ref } from 'vue'
import SwitchesHeader from '@/components/Switches/SwitchesHeader.vue'
import SwitchesKpis from '@/components/Switches/SwitchesKpis.vue'
import SwitchCard from '@/components/Switches/SwitchCard.vue'
import SwitchPortTable from '@/components/Switches/SwitchPortTable.vue'
import { useSwitchesOverview } from '@/composables/useSwitchesOverview'

const PortTrafficModal = defineAsyncComponent(() => import('@/components/PortTrafficModal.vue'))

const {
  data,
  loading,
  error,
  load,
  thresholds,
  vendor,
  pop,
  switchId,
  filter,
  query,
  vendors,
  pops,
  scopedSwitches,
  visibleSwitches,
  scopedPorts,
  visiblePorts,
  freeHidden,
  kpis,
  selectedPort,
  selectPort,
  allCount,
} = useSwitchesOverview()

const zabbix = computed(() => {
  if (!data.value) return null
  if (!data.value.zabbix_ok) return 'down'
  return data.value.switches.some((s) => !s.collection_ok) ? 'partial' : 'ok'
})
const collectedAt = computed(() =>
  data.value?.collected_at ? new Date(data.value.collected_at).toLocaleString('pt-BR') : '—',
)

const portsBySwitch = computed(() => {
  const map = new Map()
  for (const p of scopedPorts.value) {
    if (p.kind === 'mgmt') continue
    if (!map.has(p.device_id)) map.set(p.device_id, [])
    map.get(p.device_id).push(p)
  }
  return map
})
const portsOf = (id) => portsBySwitch.value.get(id) || []

/** Gráfico histórico: o modal de tráfego da porta do inventário (TimeSeriesChart). */
const historyPort = ref(null)
function openHistory(p) {
  if (!p.port_id) return
  historyPort.value = { id: p.port_id, name: `${p.name}${p.description ? ` · ${p.description}` : ''}` }
}
</script>

<style scoped>
.sw-alert {
  padding: 8px 12px;
  border: 1px solid rgb(var(--danger) / 0.4);
  border-radius: 8px;
  background: rgb(var(--danger) / 0.08);
  color: rgb(var(--danger));
  font-size: 13px;
}
.sw-note {
  padding: 6px 12px;
  border: 1px solid rgb(var(--warning) / 0.4);
  border-radius: 8px;
  background: rgb(var(--warning) / 0.08);
  color: rgb(var(--warning));
  font-size: 12px;
}
</style>
