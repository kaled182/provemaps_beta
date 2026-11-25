<template>
  <div class="h-full flex flex-col bg-canvas text-neutral-900">
    <header class="flex-none px-4 md:px-6 py-2 border-b border-neutral-200 bg-surface flex items-center gap-3 flex-wrap">
      <h1 class="text-base font-semibold mr-2">Alarmes</h1>
      <span class="text-xs text-neutral-500">
        Fibra pelo histórico de estado · equipamentos pelo Zabbix · MTTR em {{ board?.window_days ?? 30 }} dias
      </span>
      <button type="button" class="ml-auto px-2 py-1.5 rounded-md text-neutral-600 hover:bg-neutral-100" title="Atualizar" :disabled="loading" @click="load">
        <i class="fas fa-rotate" :class="{ 'animate-spin': loading }"></i>
      </button>
    </header>

    <main class="flex-1 min-h-0 overflow-auto px-4 md:px-6 py-3 flex flex-col gap-3">
      <section class="grid grid-cols-2 lg:grid-cols-4 gap-2" aria-label="Resumo dos alarmes">
        <div class="kpi"><span class="kpi-label">Críticos ativos</span><span class="kpi-value text-danger" data-testid="alarms-critical">{{ counts.critical }}</span></div>
        <div class="kpi"><span class="kpi-label">Atenção</span><span class="kpi-value text-warning" data-testid="alarms-attention">{{ counts.attention }}</span></div>
        <div class="kpi">
          <span class="kpi-label">Resolvidos (24 h)</span>
          <span class="kpi-value" data-testid="alarms-resolved">{{ board ? board.resolved_24h : '—' }}</span>
        </div>
        <div class="kpi">
          <span class="kpi-label">MTTR</span>
          <span class="kpi-value" data-testid="alarms-mttr">{{ board && board.mttr_seconds !== null ? formatDuration(board.mttr_seconds) : '—' }}</span>
          <span class="text-xs text-neutral-500">
            {{ board?.mttr_sample ? `${board.mttr_sample} incidentes fechados` : 'sem incidentes fechados' }}
          </span>
        </div>
      </section>

      <p v-if="zabbixError" class="px-3 py-2 rounded-md border border-warning/40 bg-warning/10 text-sm text-warning" role="alert" data-testid="alarms-zabbix-error">
        O Zabbix não respondeu: os equipamentos offline podem não aparecer.
      </p>
      <p v-if="error" class="px-3 py-2 rounded-md border border-danger/40 bg-danger/10 text-sm text-danger" role="alert">
        Erro ao carregar os alarmes: {{ error }}
      </p>

      <p v-if="loading && !board" class="text-sm text-neutral-500">Carregando alarmes…</p>
      <p v-else-if="board && !rows.length" class="px-3 py-6 rounded-lg border border-neutral-200 bg-surface text-center text-sm text-neutral-500" data-testid="alarms-empty">
        Nenhum alarme ativo.
      </p>

      <section v-for="g in groups" :key="g.severity" class="rounded-lg border border-neutral-200 bg-surface overflow-auto" :data-testid="`alarms-group-${g.severity}`">
        <h2 class="px-3 py-2 text-xs font-semibold uppercase tracking-wide border-b border-neutral-200" :class="g.severity === 'critical' ? 'text-danger' : 'text-warning'">
          {{ g.label }} · {{ g.rows.length }}
        </h2>
        <table class="w-full text-sm">
          <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th class="th">Ativo afetado</th>
              <th class="th">Tipo</th>
              <th class="th text-right">Valor medido</th>
              <th class="th">Desde</th>
              <th class="th text-right">Duração</th>
              <th class="th text-right"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            <tr v-for="r in g.rows" :key="r.key" class="hover:bg-neutral-50" :data-testid="`alarm-row-${r.key}`">
              <td class="td whitespace-nowrap">
                <span class="font-semibold">{{ r.name }}</span>
                <span v-if="r.site" class="ml-2 text-xs text-neutral-500">{{ r.site }}</span>
              </td>
              <td class="td">{{ r.kind === 'cable' ? 'Fibra' : 'Equipamento offline' }}</td>
              <td class="td text-right num">
                <template v-if="r.measured !== null">RX {{ r.measured.toFixed(2) }} dBm</template>
                <template v-else>—</template>
              </td>
              <td class="td num whitespace-nowrap">{{ r.openedAt ? formatDate(r.openedAt) : '—' }}</td>
              <td class="td text-right num">{{ formatDuration(r.durationSeconds) }}</td>
              <td class="td text-right">
                <button type="button" class="locate" :disabled="!r.center" @click="locate(r)">Localizar no mapa →</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>
  </div>
</template>

<script setup>
/**
 * Alarmes (EV-0059): incidentes de fibra derivados do histórico de estado
 * (`unknown` não abre nem fecha) + equipamentos offline pelo Zabbix.
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useApi } from '@/composables/useApi'
import { fetchAllPages } from '@/utils/paginate'
import { buildFocusLocation } from '@/utils/mapFocus'
import { buildAlarmRows, formatDuration, groupBySeverity } from '@/utils/alarmsBoard'

const api = useApi()
const router = useRouter()
const board = ref(null)
const offline = ref([])
const loading = ref(false)
const error = ref('')
const zabbixError = ref(false)

const rows = computed(() => buildAlarmRows(board.value, offline.value))
const groups = computed(() => groupBySeverity(rows.value))
const counts = computed(() => ({
  critical: rows.value.filter((r) => r.severity === 'critical').length,
  attention: rows.value.filter((r) => r.severity === 'attention').length,
}))

const formatDate = (iso) =>
  new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })

async function loadOfflineDevices() {
  const [devices, sites] = await Promise.all([fetchAllPages(api, '/api/v1/devices/'), fetchAllPages(api, '/api/v1/sites/')])
  const ids = devices.map((d) => d.id).join(',')
  if (!ids) return []
  const status = await api.get('/api/v1/inventory/devices/zabbix-status/', { device_ids: ids })
  zabbixError.value = Boolean(status.zabbix_error)
  const siteById = new Map(sites.map((s) => [s.id, s]))
  return devices
    .filter((d) => status.statuses?.[String(d.id)] === 'offline')
    .map((d) => {
      const s = siteById.get(d.site)
      const lat = s && s.latitude !== null ? Number(s.latitude) : null
      const lng = s && s.longitude !== null ? Number(s.longitude) : null
      return { id: d.id, name: d.name, site_name: d.site_name, center: lat !== null && lng !== null ? { lat, lng } : null }
    })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [b, off] = await Promise.all([
      api.get('/api/v1/fiber-cables/alarm-board/'),
      loadOfflineDevices().catch(() => {
        zabbixError.value = true
        return []
      }),
    ])
    board.value = b
    offline.value = off
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    loading.value = false
  }
}

function locate(r) {
  const loc = r.center && buildFocusLocation({ type: r.kind, id: r.id, name: r.name, lat: r.center.lat, lng: r.center.lng })
  if (loc) router.push(loc)
}

onMounted(load)
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
.locate {
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--primary-600));
  white-space: nowrap;
}
.locate:hover:not(:disabled) {
  text-decoration: underline;
}
.locate:disabled {
  color: rgb(var(--n-400));
  cursor: not-allowed;
}
</style>
