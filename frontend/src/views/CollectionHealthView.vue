<template>
  <div class="h-full flex flex-col bg-canvas text-neutral-900">
    <header class="flex-none px-4 md:px-6 py-2 border-b border-neutral-200 bg-surface flex items-center gap-3 flex-wrap">
      <h1 class="text-base font-semibold mr-2">Saúde da coleta</h1>
      <label class="flex items-center gap-2 text-sm text-neutral-600">
        Sem leitura há mais de
        <select v-model.number="staleHours" class="field" data-testid="ch-stale-hours" aria-label="Horas sem leitura">
          <option v-for="h in STALE_OPTIONS" :key="h" :value="h">{{ h }} h</option>
        </select>
      </label>
      <button
        type="button"
        class="ml-auto px-3 py-1.5 rounded-md border border-neutral-300 text-sm text-neutral-700 hover:bg-neutral-100 disabled:opacity-50"
        :disabled="loading"
        data-testid="ch-refresh"
        @click="load"
      >
        <i class="fas fa-rotate mr-1" :class="{ 'animate-spin': loading }"></i>Atualizar
      </button>
    </header>

    <main class="flex-1 min-h-0 overflow-auto px-4 md:px-6 py-3 flex flex-col gap-3">
      <p v-if="error" class="px-3 py-2 rounded-md border border-danger/40 bg-danger/10 text-sm text-danger" role="alert" data-testid="ch-error">
        Erro ao carregar a saúde da coleta: {{ error }}
      </p>
      <p v-if="data && !data.zabbix_ok" class="px-3 py-2 rounded-md border border-warning/40 bg-warning/10 text-sm text-warning" role="alert" data-testid="ch-zabbix-down">
        Zabbix indisponível: não é possível verificar os hosts.
        <span v-if="data.zabbix_error" class="num">{{ data.zabbix_error }}</span>
      </p>

      <p v-if="loading && !data" class="text-sm text-neutral-500">Carregando…</p>

      <template v-if="data">
        <section class="grid grid-cols-2 lg:grid-cols-5 gap-2" aria-label="Resumo da coleta">
          <div class="kpi" data-testid="ch-kpi-missing-host">
            <span class="kpi-label">Equipamentos sem host</span>
            <span v-if="totals.devices_missing_host === null" class="kpi-value text-neutral-500 text-sm">desconhecido</span>
            <span v-else class="kpi-value" :class="totals.devices_missing_host ? 'text-danger' : ''">{{ totals.devices_missing_host }}</span>
          </div>
          <div class="kpi" data-testid="ch-kpi-no-readings">
            <span class="kpi-label">Equipamentos sem leitura</span>
            <span class="kpi-value" :class="totals.devices_without_readings ? 'text-warning' : ''">{{ totals.devices_without_readings }}</span>
            <span class="text-xs text-neutral-500">de {{ totals.devices }} equipamentos</span>
          </div>
          <div class="kpi" data-testid="ch-kpi-reading">
            <span class="kpi-label">Portas com leitura</span>
            <span class="kpi-value text-success">{{ totals.ports_reading }}</span>
          </div>
          <div class="kpi" data-testid="ch-kpi-with-key">
            <span class="kpi-label">Portas com chave</span>
            <span class="kpi-value">{{ totals.ports_with_key }}</span>
          </div>
          <div class="kpi" data-testid="ch-kpi-problem">
            <span class="kpi-label">Portas com problema</span>
            <span class="kpi-value" :class="totals.ports_problem ? 'text-danger' : ''">{{ totals.ports_problem }}</span>
          </div>
        </section>

        <p v-if="allClear" class="px-3 py-2 rounded-md border border-success/40 bg-success/10 text-sm text-success" data-testid="ch-all-clear">
          Tudo a ser coletado
        </p>

        <section v-if="data.devices_missing_host.length" class="panel" data-testid="ch-missing-host">
          <h2 class="panel-title">Equipamentos com host Zabbix inexistente</h2>
          <table class="w-full text-sm">
            <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
              <tr><th class="th">Equipamento</th><th class="th">Site</th><th class="th">Host ID no Zabbix</th></tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              <tr v-for="d in data.devices_missing_host" :key="d.device_id">
                <td class="td font-semibold">{{ d.device_name }}</td>
                <td class="td">{{ d.site_name || '—' }}</td>
                <td class="td num">{{ d.zabbix_hostid }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section v-if="data.devices_without_readings.length" class="panel" data-testid="ch-no-readings">
          <h2 class="panel-title">Equipamentos sem nenhuma leitura</h2>
          <table class="w-full text-sm">
            <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
              <tr><th class="th">Equipamento</th><th class="th">Site</th><th class="th text-right">Portas com chave</th><th class="th text-right">Portas com leitura</th></tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              <tr v-for="d in data.devices_without_readings" :key="d.device_id">
                <td class="td font-semibold">{{ d.device_name }}</td>
                <td class="td">{{ d.site_name || '—' }}</td>
                <td class="td text-right num">{{ d.ports_with_key }}</td>
                <td class="td text-right num">{{ d.ports_reading }}</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section v-if="data.ports.length" class="panel" data-testid="ch-ports-panel">
          <div class="flex items-center gap-2 flex-wrap px-3 py-2 border-b border-neutral-200">
            <h2 class="panel-title !p-0 !border-0 mr-2">Portas com problema</h2>
            <select v-model="reasonFilter" class="field" data-testid="ch-reason-filter" aria-label="Filtrar por motivo">
              <option value="all">Todos os motivos</option>
              <option value="item_problem">Item com problema</option>
              <option value="never">Nunca coletada</option>
              <option value="stale">Sem leitura há mais de {{ data.stale_hours }} h</option>
            </select>
            <input v-model="query" type="search" placeholder="Buscar equipamento ou porta…" class="field ml-auto w-64" data-testid="ch-query" aria-label="Buscar portas" />
          </div>
          <p v-if="!visiblePorts.length" class="p-4 text-sm text-neutral-500">Nenhuma porta neste filtro.</p>
          <table v-else class="w-full text-sm" data-testid="ch-ports-table">
            <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="th">Equipamento</th><th class="th">Porta</th><th class="th">Motivo</th><th class="th">Detalhe</th>
                <th class="th text-right">RX</th><th class="th text-right">TX</th><th class="th">Última leitura</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              <tr v-for="p in visiblePorts" :key="p.port_id" data-testid="ch-port-row">
                <td class="td whitespace-nowrap font-semibold">{{ p.device_name }}</td>
                <td class="td whitespace-nowrap">{{ p.port_name }}</td>
                <td class="td whitespace-nowrap">
                  <span class="tag" :class="`tag-${p.reason}`">{{ reasonLabel(p.reason) }}</span>
                </td>
                <td class="td text-neutral-600">{{ p.problem || '—' }}</td>
                <td class="td text-right num">{{ dbm(p.last_rx_power) }}</td>
                <td class="td text-right num">{{ dbm(p.last_tx_power) }}</td>
                <td class="td whitespace-nowrap text-neutral-600">{{ ago(p.last_optical_check) }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
/**
 * Saúde da coleta — EV-0085. O que o inventário espera do Zabbix e não está a
 * chegar: hosts apagados, equipamentos sem leitura, portas com problema.
 * «Zabbix fora» (zabbix_ok false) é distinto de «nada em alarme».
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'

const URL = '/api/v1/inventory/collection-health/'
const STALE_OPTIONS = [1, 2, 6, 24, 72]
const REFRESH_MS = 5 * 60 * 1000

const api = useApi()
const data = ref(null)
const loading = ref(false)
const error = ref('')
const staleHours = ref(2)
const reasonFilter = ref('all')
const query = ref('')
let timer = null

const totals = computed(() => data.value?.totals || {})
const allClear = computed(
  () =>
    Boolean(data.value) &&
    data.value.zabbix_ok &&
    !data.value.devices_missing_host.length &&
    !data.value.devices_without_readings.length &&
    !data.value.ports.length,
)
const visiblePorts = computed(() => {
  const q = query.value.trim().toLowerCase()
  return (data.value?.ports || []).filter(
    (p) =>
      (reasonFilter.value === 'all' || p.reason === reasonFilter.value) &&
      (!q || `${p.device_name} ${p.port_name}`.toLowerCase().includes(q)),
  )
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = await api.get(URL, { stale_hours: staleHours.value })
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    loading.value = false
  }
}

function reasonLabel(reason) {
  if (reason === 'item_problem') return 'Item com problema'
  if (reason === 'never') return 'Nunca coletada'
  if (reason === 'stale') return `Sem leitura há mais de ${data.value?.stale_hours ?? staleHours.value} h`
  return reason
}

function dbm(v) {
  return v === null || v === undefined ? '—' : `${Number(v).toFixed(1)} dBm`
}

function ago(iso) {
  if (!iso) return '—'
  const secs = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000))
  if (secs < 60) return `há ${secs} s`
  if (secs < 3600) return `há ${Math.floor(secs / 60)} min`
  if (secs < 172800) return `há ${Math.floor(secs / 3600)} h`
  return `há ${Math.floor(secs / 86400)} dias`
}

watch(staleHours, load)

onMounted(() => {
  load()
  timer = setInterval(load, REFRESH_MS)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.kpi {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgb(var(--n-500));
}
.kpi-value {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 20px;
  font-weight: 600;
}
.panel {
  border-radius: 8px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
  overflow: auto;
}
.panel-title {
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  border-bottom: 1px solid rgb(var(--n-200));
}
.field {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid rgb(var(--n-300));
  background: rgb(var(--surface));
  font-size: 13px;
  color: rgb(var(--n-900));
}
.th {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  white-space: nowrap;
}
.td {
  padding: 6px 12px;
  vertical-align: middle;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.tag {
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
  border: 1px solid rgb(var(--n-300));
}
.tag-item_problem {
  color: rgb(var(--danger));
  border-color: rgb(var(--danger) / 0.4);
  background: rgb(var(--danger) / 0.1);
}
.tag-never,
.tag-stale {
  color: rgb(var(--warning));
  border-color: rgb(var(--warning) / 0.4);
  background: rgb(var(--warning) / 0.1);
}
</style>
