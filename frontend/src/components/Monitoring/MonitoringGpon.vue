<template>
  <div class="h-full flex flex-col bg-canvas text-neutral-900">
    <GponHeader
      v-model:olt="oltFilter"
      v-model:filter="filter"
      v-model:query="query"
      :zabbix="zabbix"
      :zabbix-error="data?.zabbix_error || null"
      :thresholds="thresholds"
      :olts="allOlts"
      :loading="loading"
      @refresh="load"
    />

    <main class="flex-1 min-h-0 overflow-auto px-4 md:px-6 py-3 flex flex-col gap-3">
      <p v-if="error" class="px-3 py-2 rounded-md border border-danger/40 bg-danger/10 text-sm text-danger" role="alert" data-testid="gpon-error">
        Erro ao carregar o monitoramento GPON: {{ error }}
      </p>
      <p v-if="data && !data.zabbix_ok" class="px-3 py-2 rounded-md border border-warning/40 bg-warning/10 text-sm text-warning" role="alert" data-testid="gpon-zabbix-down">
        Zabbix indisponível na última coleta: os estados abaixo podem estar desatualizados.
      </p>
      <p v-if="loading && !data" class="text-sm text-neutral-500">Carregando…</p>

      <template v-if="data">
        <GponKpis :totals="totals" />

        <p v-if="!visibleOlts.length" class="px-3 py-4 rounded-lg border border-neutral-200 bg-surface text-center text-sm text-neutral-500" data-testid="gpon-no-olts">
          Nenhuma OLT neste filtro.
        </p>
        <div v-if="visibleOlts.length" class="flex items-center justify-end">
          <div class="view-toggle" role="group" aria-label="Vista das OLTs" data-testid="gpon-view-toggle">
            <button
              v-for="v in VIEWS"
              :key="v.value"
              type="button"
              :class="{ 'view-on': view === v.value }"
              :aria-pressed="view === v.value"
              :data-testid="`gpon-view-${v.value}`"
              @click="setView(v.value)"
            >
              <component :is="v.icon" :size="14" /> {{ v.label }}
            </button>
          </div>
        </div>

        <template v-if="view === 'chassis'">
          <OltChassis
            v-for="o in visibleOlts"
            :key="o.device_id"
            :olt="o"
            :pons="ponsOf(o.device_id)"
            :filtered="filter !== 'all'"
            :selected-pon="selectedPon"
            :selected-slot="selectedSlot"
            :thresholds="thresholds"
            @toggle-pon="togglePon"
            @toggle-slot="toggleSlot"
          />
        </template>
        <template v-else>
          <OltCard
            v-for="o in visibleOlts"
            :key="o.device_id"
            :olt="o"
            :selected-pon="selectedPon"
            @toggle-pon="togglePon"
          />
        </template>

        <OnuTable
          :onus="visibleOnus"
          :scope="tableScope"
          :show-olt="oltFilter === null && selectedPon === null && selectedSlot === null"
          @history="openHistory"
        />
      </template>
    </main>

    <OnuHistoryModal :show="historyOnu !== null" :onu="historyOnu" :thresholds="thresholds" @close="historyOnu = null" />
  </div>
</template>

<script setup>
/**
 * Monitoramento GPON (EV-0095): OLTs, PONs e ONUs a partir do estado que a tarefa
 * de coleta gravou (o pedido não vai ao Zabbix). «Zabbix fora» ≠ «sem dados».
 */
import { ref } from 'vue'
import { PhCube, PhSquaresFour } from '@phosphor-icons/vue'
import GponHeader from '@/components/Gpon/GponHeader.vue'
import GponKpis from '@/components/Gpon/GponKpis.vue'
import OltCard from '@/components/Gpon/OltCard.vue'
import OltChassis from '@/components/Gpon/OltChassis.vue'
import OnuTable from '@/components/Gpon/OnuTable.vue'
import OnuHistoryModal from '@/components/Gpon/OnuHistoryModal.vue'
import { VIEW_KEY, useGponOverview } from '@/composables/useGponOverview'

const {
  data,
  loading,
  error,
  oltFilter,
  filter,
  query,
  selectedPon,
  selectedSlot,
  allOlts,
  thresholds,
  totals,
  zabbix,
  visibleOlts,
  visibleOnus,
  tableScope,
  load,
  togglePon,
  toggleSlot,
} = useGponOverview()

/** Vista das OLTs (EV-0101): painel frontal (padrão) ou a grade compacta de cartões. */
const VIEWS = [
  { value: 'chassis', label: 'Vista do chassi', icon: PhCube },
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
  if (v === 'grid') selectedSlot.value = null
  try {
    localStorage.setItem(VIEW_KEY, v)
  } catch {
    /* sem localStorage (janela privada): a escolha vale só nesta visita */
  }
}

/** Todas as PONs de uma OLT (sem a pílula), para os LEDs do chassi. */
function ponsOf(deviceId) {
  return allOlts.value.find((o) => o.device_id === deviceId)?.pons || []
}

const historyOnu = ref(null)
function openHistory(onu) {
  if (onu.has_history) historyOnu.value = onu
}
</script>

<style scoped>
.view-toggle {
  display: inline-flex;
  padding: 2px;
  border-radius: 8px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
}
.view-toggle button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: rgb(var(--n-600));
}
.view-toggle button:hover {
  color: rgb(var(--n-800));
}
.view-toggle .view-on {
  color: rgb(var(--primary-600));
  background: rgb(var(--primary-500) / 0.12);
  font-weight: 600;
}
.view-toggle button:focus-visible {
  outline: 2px solid rgb(var(--primary-500));
  outline-offset: 1px;
}
</style>
