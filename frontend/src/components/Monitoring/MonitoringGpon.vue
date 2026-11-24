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
        <OltCard
          v-for="o in visibleOlts"
          :key="o.device_id"
          :olt="o"
          :selected-pon="selectedPon"
          @toggle-pon="togglePon"
        />

        <OnuTable :onus="visibleOnus" :scope="tableScope" :show-olt="oltFilter === null && selectedPon === null" @history="openHistory" />
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
import GponHeader from '@/components/Gpon/GponHeader.vue'
import GponKpis from '@/components/Gpon/GponKpis.vue'
import OltCard from '@/components/Gpon/OltCard.vue'
import OnuTable from '@/components/Gpon/OnuTable.vue'
import OnuHistoryModal from '@/components/Gpon/OnuHistoryModal.vue'
import { useGponOverview } from '@/composables/useGponOverview'

const {
  data,
  loading,
  error,
  oltFilter,
  filter,
  query,
  selectedPon,
  allOlts,
  thresholds,
  totals,
  zabbix,
  visibleOlts,
  visibleOnus,
  tableScope,
  load,
  togglePon,
} = useGponOverview()

const historyOnu = ref(null)
function openHistory(onu) {
  if (onu.has_history) historyOnu.value = onu
}
</script>
