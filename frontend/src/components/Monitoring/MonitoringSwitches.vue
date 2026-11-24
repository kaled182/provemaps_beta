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

        <!-- EV-0116: vista do chassi (padrão) ou grade compacta -->
        <div class="flex items-center gap-2">
          <div class="pills" role="group" aria-label="Vista">
            <button
              v-for="v in VIEWS"
              :key="v.value"
              type="button"
              class="pill"
              :class="{ 'pill-on': view === v.value }"
              :aria-pressed="view === v.value"
              :data-testid="`sw-view-${v.value}`"
              @click="setView(v.value)"
            >
              <component :is="v.icon" :size="13" class="inline -mt-0.5" /> {{ v.label }}
            </button>
          </div>
        </div>

        <template v-if="view === 'chassis'">
          <SwitchChassisBlock
            v-for="s in visibleSwitches"
            :key="s.device_id"
            :sw="s"
            :ports="allPortsOf(s.device_id)"
            :visible-names="visibleNamesOf(s.device_id)"
            :selected="selectedPort"
            :thresholds="thresholds"
            @select="selectPort"
          />
          <p v-if="!visibleSwitches.length" class="py-6 text-center text-sm text-neutral-500" data-testid="sw-none">Nenhum switch neste recorte.</p>
        </template>

        <section v-else-if="visibleSwitches.length" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-2" aria-label="Switches" data-testid="sw-grid">
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
import SwitchChassisBlock from '@/components/Switches/SwitchChassisBlock.vue'
import { PhRows, PhSquaresFour } from '@phosphor-icons/vue'
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

// EV-0116: vista guardada por utilizador neste browser (conveniência; falha sem efeito)
const VIEW_KEY = 'provemaps.switches.view'
const VIEWS = [
  { value: 'chassis', label: 'Vista do chassi', icon: PhRows },
  { value: 'grid', label: 'Grade compacta', icon: PhSquaresFour },
]
function readView() {
  try {
    return localStorage.getItem(VIEW_KEY) === 'grid' ? 'grid' : 'chassis'
  } catch {
    return 'chassis'
  }
}
const view = ref(readView())
function setView(v) {
  view.value = v
  try {
    localStorage.setItem(VIEW_KEY, v)
  } catch {
    /* sem armazenamento: a escolha vale só nesta visita */
  }
}

/** Todas as portas do switch (com a gerência) para o chassi. */
const allPortsOf = (id) => scopedPorts.value.filter((p) => p.device_id === id)
/** Portas que passam no filtro/busca — as outras ficam esbatidas no chassi. */
const filtering = computed(() => filter.value !== 'all' || query.value.trim() !== '')
const visibleNamesOf = (id) => (filtering.value ? visiblePorts.value.filter((p) => p.device_id === id).map((p) => p.name) : null)

/** Gráfico histórico: o modal de tráfego da porta do inventário (TimeSeriesChart). */
const historyPort = ref(null)
function openHistory(p) {
  if (!p.port_id) return
  historyPort.value = { id: p.port_id, name: `${p.name}${p.description ? ` · ${p.description}` : ''}` }
}
</script>

<style scoped>
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
