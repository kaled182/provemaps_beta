<template>
  <div data-testid="pon-events">
    <p v-if="loading && !body" class="p-4 text-sm text-neutral-500">Carregando eventos…</p>
    <p v-else-if="error" class="p-4 text-sm text-danger" role="alert" data-testid="pon-events-error">
      Erro ao carregar os eventos: {{ error }}
    </p>
    <template v-else-if="body">
      <p class="px-3 py-1.5 text-xs text-neutral-500 border-b border-neutral-100" data-testid="pon-events-since">
        <template v-if="body.since">Registo de eventos desde {{ fmt(body.since) }} (quedas e reconexões vistas pela coleta, a cada 2 min).</template>
        <template v-else>O registo de eventos ainda não tem dados — começa na próxima mudança de estado.</template>
        <span v-if="body.truncated"> Mostrando os {{ body.events.length }} mais recentes.</span>
      </p>
      <p v-if="!body.events.length" class="p-4 text-sm text-neutral-500" data-testid="pon-events-empty">
        Nenhum evento nesta porta nas últimas {{ body.hours }} h.
      </p>
      <table v-else class="w-full text-sm">
        <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
          <tr>
            <th class="th">Quando</th>
            <th class="th">Evento</th>
            <th class="th">ONU</th>
            <th class="th">Antes</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          <tr v-for="(e, i) in body.events" :key="`${e.onu_id}-${e.at}-${i}`" class="h-9" data-testid="pon-event-row">
            <td class="td num whitespace-nowrap text-neutral-600">{{ fmt(e.at) }}</td>
            <td class="td whitespace-nowrap">
              <span class="tag" :class="KIND[e.kind].cls" :title="e.label || ''">{{ KIND[e.kind].label }}</span>
            </td>
            <td class="td">
              <span class="num">{{ e.serial || e.mac || `ONU ${e.onu_index ?? '?'}` }}</span>
              <span v-if="e.cliente_nome" class="ml-2 text-xs text-neutral-500">{{ e.cliente_nome }}</span>
            </td>
            <td class="td whitespace-nowrap text-xs text-neutral-500">{{ e.previous_kind ? STATE[e.previous_kind] : '—' }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<script setup>
/**
 * Eventos recentes de uma PON (EV-0108): quedas (LOS, dying gasp, offline) e reconexões
 * observadas pela coleta. Recarrega quando há nova coleta (`refreshKey`).
 */
import { ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'

const EVENTS_URL = '/api/v1/monitoring/gpon/events/'

const props = defineProps({
  deviceId: { type: Number, required: true },
  ponId: { type: String, required: true },
  hours: { type: Number, default: 24 },
  /** muda a cada coleta (ex.: collected_at) para recarregar */
  refreshKey: { type: [String, Number], default: null },
})

const KIND = {
  los: { label: 'Queda — LOS', cls: 'tag-danger' },
  dying_gasp: { label: 'Queda — dying gasp', cls: 'tag-warning' },
  offline: { label: 'Offline', cls: 'tag-neutral' },
  online: { label: 'Reconexão', cls: 'tag-success' },
}

/** Estado anterior (coluna «Antes») — não é um evento, é como a ONU estava. */
const STATE = { online: 'Online', offline: 'Offline', los: 'Offline — LOS', dying_gasp: 'Offline — dying gasp' }

const api = useApi()
const body = ref(null)
const loading = ref(false)
const error = ref('')
let seq = 0

async function load() {
  const mine = ++seq
  loading.value = true
  error.value = ''
  try {
    const data = await api.get(EVENTS_URL, { device: props.deviceId, pon: props.ponId, hours: props.hours })
    if (mine === seq) body.value = data
  } catch (e) {
    if (mine === seq) error.value = e?.message || 'erro desconhecido'
  } finally {
    if (mine === seq) loading.value = false
  }
}

watch(() => [props.deviceId, props.ponId, props.hours, props.refreshKey], load, { immediate: true })

const fmt = (iso) =>
  new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
</script>

<style scoped>
.th {
  padding: 6px 10px;
  text-align: left;
  font-weight: 600;
  white-space: nowrap;
}
.td {
  padding: 4px 10px;
  vertical-align: middle;
}
.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
.tag {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid rgb(var(--n-300));
  color: rgb(var(--n-600));
}
.tag-danger {
  color: rgb(var(--danger));
  border-color: rgb(var(--danger) / 0.45);
  background: rgb(var(--danger) / 0.1);
}
.tag-warning {
  color: rgb(var(--warning));
  border-color: rgb(var(--warning) / 0.45);
  background: rgb(var(--warning) / 0.1);
}
.tag-success {
  color: rgb(var(--success));
  border-color: rgb(var(--success) / 0.4);
  background: rgb(var(--success) / 0.1);
}
</style>
