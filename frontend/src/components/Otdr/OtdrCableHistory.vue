<template>
  <section class="och" data-testid="otdr-history">
    <h3>Rompimentos OTDR</h3>
    <p v-if="loading && !items" class="och-muted">A carregar…</p>
    <p v-else-if="error" class="och-error" role="alert">Erro ao carregar os rompimentos: {{ error }}</p>
    <p v-else-if="!items?.length" class="och-muted" data-testid="otdr-history-empty">Nenhum rompimento localizado por OTDR neste cabo.</p>
    <ol v-else class="och-list">
      <li v-for="a in items" :key="a.id" class="och-item" :data-testid="`otdr-history-${a.id}`">
        <header class="och-head">
          <span class="och-status" :class="`och-${a.status}`">{{ a.status_label }}</span>
          <span class="och-when">{{ fmt(a.created_at) }}</span>
          <span v-if="a.created_by" class="och-muted">por {{ a.created_by }}</span>
        </header>
        <p class="och-line num">
          {{ summary(a.result) }} · {{ formatCoords(a.result.point) }}
        </p>
        <ul class="och-log">
          <li v-for="(e, i) in a.log" :key="i">
            <span class="och-when">{{ fmt(e.at) }}</span> {{ describe(e) }}<template v-if="e.by"> — {{ e.by }}</template>
          </li>
        </ul>
      </li>
    </ol>
  </section>
</template>

<script setup>
/** Histórico dos rompimentos OTDR do cabo (EV-0132), na aba «Histórico» do modal do cabo. */
import { ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import { formatCoords, formatMeters } from '@/utils/otdr'

const props = defineProps({
  cableId: { type: [Number, String], required: true },
})

const STATUS = { registered: 'Registado', en_route: 'Em deslocamento', splicing: 'Em fusão', done: 'Concluído' }

const api = useApi()
const items = ref(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    items.value = await api.get(`/api/v1/inventory/cables/${encodeURIComponent(props.cableId)}/otdr-alerts/`)
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    loading.value = false
  }
}
watch(() => props.cableId, load, { immediate: true })

const fmt = (iso) =>
  iso ? new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'

function summary(r) {
  if (!r) return '—'
  const from = r.origin?.name || 'origem'
  if (r.mode === 'cross' && r.cross) {
    return `A + B: ${formatMeters(r.cross.reading_a_m)} + ${formatMeters(r.cross.reading_b_m)} → ${formatMeters(r.map_distance_m)} de ${from}`
  }
  return `OTDR ${formatMeters(r.otdr_m)} de ${from} → ${formatMeters(r.map_distance_m)} no traçado`
}

function describe(e) {
  if (e.action === 'pinned') return 'Fixado no mapa'
  if (e.action === 'adjusted') return `Ajuste fino ${e.delta_m > 0 ? '+' : ''}${formatMeters(e.delta_m)}`
  if (e.action === 'cleared') return 'Removido do mapa'
  if (e.action === 'status') return `Atendimento: ${STATUS[e.status] || e.status}`
  return e.action
}
</script>

<style scoped>
.och {
  margin-bottom: 16px;
}
.och h3 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: rgb(var(--n-900));
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.och-muted {
  font-size: 12px;
  color: rgb(var(--n-500));
}
.och-error {
  font-size: 12px;
  color: rgb(var(--danger));
}
.och-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.och-item {
  padding: 8px 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  background: rgb(var(--surface));
}
.och-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.och-status {
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid rgb(var(--n-300));
  color: rgb(var(--n-700));
}
.och-registered,
.och-en_route,
.och-splicing {
  color: rgb(var(--danger));
  border-color: rgb(var(--danger) / 0.45);
  background: rgb(var(--danger) / 0.08);
}
.och-done {
  color: rgb(var(--success));
  border-color: rgb(var(--success) / 0.4);
  background: rgb(var(--success) / 0.08);
}
.och-when {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 11px;
  color: rgb(var(--n-500));
}
.och-line {
  margin: 4px 0;
  font-size: 12px;
  color: rgb(var(--n-800));
}
.och-log {
  margin: 0;
  padding-left: 14px;
  font-size: 11px;
  color: rgb(var(--n-700));
}
</style>
