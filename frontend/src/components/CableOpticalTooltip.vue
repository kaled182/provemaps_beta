<template>
  <Teleport to="body">
    <Transition name="tooltip-float">
      <div
        v-if="visible && cableData"
        ref="panelEl"
        class="optical-panel"
        :class="{ dragging: isDragging }"
        :style="panelStyle"
        @click.stop
      >
        <!-- Header / drag handle -->
        <div
          class="panel-header"
          @mousedown.prevent="startDrag"
          @touchstart.passive="startDrag"
        >
          <div class="drag-grip" aria-hidden="true">
            <span></span><span></span><span></span>
          </div>
          <div class="header-text">
            <div class="panel-title">{{ cableData.label || cableData.name }}</div>
            <div class="panel-subtitle">{{ cableData.origin }} ↔ {{ cableData.destination }}</div>
          </div>
          <button class="close-btn" @click.stop="$emit('close')" title="Fechar">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Loading -->
        <div v-if="loading" class="panel-state">
          <div class="spinner"></div>
          <span>Carregando níveis ópticos…</span>
        </div>

        <!-- Erro -->
        <div v-else-if="error" class="panel-state error">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          {{ error }}
        </div>

        <!-- Sem dados -->
        <div v-else-if="!hasOpticalData" class="panel-state muted">
          Nenhum dado óptico disponível para este cabo.
        </div>

        <!-- Conteúdo óptico -->
        <div v-else class="panel-body">
          <!-- Origem -->
          <div class="iface-block">
            <div class="iface-header">
              <span class="iface-end">A</span>
              <span class="iface-name">{{ opticalData.origin?.interface || 'Origem não configurada' }}</span>
            </div>
            <div v-if="opticalData.origin" class="levels">
              <div class="level-row">
                <span class="level-label">TX</span>
                <span class="level-value" :class="getLevelClass(opticalData.origin.tx, 'origin')">
                  {{ formatLevel(opticalData.origin.tx) }}
                </span>
              </div>
              <div class="level-row">
                <span class="level-label">RX</span>
                <span class="level-value" :class="getLevelClass(opticalData.origin.rx, 'origin')">
                  {{ formatLevel(opticalData.origin.rx) }}
                </span>
              </div>
            </div>
            <p v-else class="iface-empty">Dados indisponíveis para a origem</p>
          </div>

          <!-- Destino -->
          <div class="iface-block">
            <div class="iface-header">
              <span class="iface-end">B</span>
              <span class="iface-name">{{ opticalData.destination?.interface || 'Destino não configurado' }}</span>
            </div>
            <div v-if="opticalData.destination" class="levels">
              <div class="level-row">
                <span class="level-label">TX</span>
                <span class="level-value" :class="getLevelClass(opticalData.destination.tx, 'destination')">
                  {{ formatLevel(opticalData.destination.tx) }}
                </span>
              </div>
              <div class="level-row">
                <span class="level-label">RX</span>
                <span class="level-value" :class="getLevelClass(opticalData.destination.rx, 'destination')">
                  {{ formatLevel(opticalData.destination.rx) }}
                </span>
              </div>
            </div>
            <p v-else class="iface-empty">Dados indisponíveis para o destino</p>
          </div>

          <!-- Atenuação -->
          <div v-if="opticalData.attenuation !== null" class="attenuation-row">
            <span class="atten-label">Atenuação estimada:</span>
            <span class="atten-value">{{ formatValue(opticalData.attenuation, 'dB') }}</span>
          </div>

          <!-- Timestamp + Refresh -->
          <div class="panel-footer">
            <span v-if="lastCheckLabel" class="last-check">{{ lastCheckLabel }}</span>
            <button
              class="refresh-btn"
              :disabled="refreshing"
              @click.stop="refreshOpticalData"
              :title="refreshing ? 'Atualizando…' : 'Forçar leitura agora (consulta Zabbix em tempo real)'"
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" :class="{ spinning: refreshing }">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              <span>{{ refreshing ? 'Atualizando…' : 'Atualizar' }}</span>
            </button>
          </div>
        </div>

        <!-- Rodapé com botão de detalhes -->
        <div class="panel-actions">
          <button class="details-btn" @click.stop="$emit('open-details', cableData)">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Ver Detalhes do Cabo
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useApi } from '@/composables/useApi'

const props = defineProps({
  visible: { type: Boolean, default: false },
  cableData: { type: Object, default: null },
  // position prop mantido por compatibilidade mas não usado para posicionamento
  position: { type: Object, default: () => ({ x: 0, y: 0 }) },
})

const emit = defineEmits(['close', 'open-details'])

const { get } = useApi()

// ── Drag ────────────────────────────────────────────────────────────────────
const panelEl = ref(null)
const pos = ref({ x: 0, y: 0 })
const isDragging = ref(false)
const dragOrigin = { mx: 0, my: 0, px: 0, py: 0 }

const PANEL_W = 400
const PANEL_H = 320

const initPosition = () => {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const w = Math.min(PANEL_W, vw - 16)
  const h = Math.min(PANEL_H, vh - 80)
  pos.value = {
    x: Math.max(8, Math.round((vw - w) / 2)),
    y: Math.max(8, Math.round((vh - h) / 3)),
  }
}

const panelStyle = computed(() => ({
  left: `${pos.value.x}px`,
  top: `${pos.value.y}px`,
}))

const clientXY = (e) =>
  e.touches?.length
    ? { x: e.touches[0].clientX, y: e.touches[0].clientY }
    : { x: e.clientX, y: e.clientY }

const startDrag = (e) => {
  const { x, y } = clientXY(e)
  dragOrigin.mx = x; dragOrigin.my = y
  dragOrigin.px = pos.value.x; dragOrigin.py = pos.value.y
  isDragging.value = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('touchend', stopDrag)
}

const onDrag = (e) => {
  if (!isDragging.value) return
  if (e.cancelable) e.preventDefault()
  const { x, y } = clientXY(e)
  const vw = window.innerWidth
  const vh = window.innerHeight
  pos.value = {
    x: Math.max(0, Math.min(vw - 120, dragOrigin.px + x - dragOrigin.mx)),
    y: Math.max(0, Math.min(vh - 60, dragOrigin.py + y - dragOrigin.my)),
  }
}

const stopDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
}

onUnmounted(stopDrag)

// ── Dados ópticos ────────────────────────────────────────────────────────────
const loading = ref(false)
const error = ref(null)
const opticalData = ref(null)
const refreshing = ref(false)
// Timestamp da última coleta (vem do campo last_check do backend)
const lastCheckIso = ref('')

const lastCheckLabel = computed(() => {
  if (!lastCheckIso.value) return ''
  try {
    const d = new Date(lastCheckIso.value)
    const ageSec = Math.round((Date.now() - d.getTime()) / 1000)
    if (ageSec < 5) return 'Atualizado agora'
    if (ageSec < 60) return `Atualizado há ${ageSec}s`
    if (ageSec < 3600) return `Atualizado há ${Math.round(ageSec / 60)} min`
    return `Atualizado há ${Math.round(ageSec / 3600)}h`
  } catch {
    return ''
  }
})

const { post } = useApi()

async function refreshOpticalData() {
  if (!props.cableData?.id || refreshing.value) return
  refreshing.value = true
  try {
    const response = await post(`/api/v1/inventory/fibers/${props.cableData.id}/refresh-optical/`, {})
    if (response.error) {
      error.value = response.error
      return
    }
    const origin = buildInterfaceData(response.origin_optical)
    const destination = buildInterfaceData(response.destination_optical)
    opticalData.value = {
      origin, destination,
      attenuation: calculateAttenuation(origin?.tx, destination?.rx),
      timestamp: origin?.timestamp || destination?.timestamp || null,
    }
    lastCheckIso.value = response.origin_optical?.last_check
                       || response.destination_optical?.last_check
                       || new Date().toISOString()
  } catch (err) {
    console.error('[CableOpticalTooltip] Refresh falhou:', err)
    error.value = 'Falha ao consultar Zabbix em tempo real.'
  } finally {
    refreshing.value = false
  }
}

const hasOpticalData = computed(() => {
  const d = opticalData.value
  return Boolean(d?.origin || d?.destination)
})

const normalizeNumber = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

const buildInterfaceData = (data) => {
  if (!data) return null
  return {
    interface: `${data.device_name || 'Dispositivo'} - ${data.port_name || 'Porta'}`,
    tx: normalizeNumber(data.tx_dbm),
    rx: normalizeNumber(data.rx_dbm),
    timestamp: data.last_check || null,
    // Thresholds vindos do backend — usados pelo getLevelClass para classificar
    // a cor (warning/critical) de forma consistente com o status persistido.
    warning_threshold: normalizeNumber(data.warning_threshold),
    critical_threshold: normalizeNumber(data.critical_threshold),
    status: data.status || null,
  }
}

const calculateAttenuation = (txOrigin, rxDest) => {
  const tx = normalizeNumber(txOrigin)
  const rx = normalizeNumber(rxDest)
  return tx !== null && rx !== null ? Math.abs(tx - rx) : null
}

const loadOpticalData = async () => {
  if (!props.cableData?.id) return
  loading.value = true
  error.value = null
  opticalData.value = null
  try {
    const response = await get(`/api/v1/inventory/fibers/${props.cableData.id}/cached-status/`)
    if (response.error) { error.value = response.error; return }
    const origin = buildInterfaceData(response.origin_optical)
    const destination = buildInterfaceData(response.destination_optical)
    opticalData.value = {
      origin,
      destination,
      attenuation: calculateAttenuation(origin?.tx, destination?.rx),
      timestamp: origin?.timestamp || destination?.timestamp || null,
    }
    lastCheckIso.value = response.origin_optical?.last_check
                       || response.destination_optical?.last_check
                       || ''
  } catch (err) {
    console.error('[CableOpticalTooltip] Erro:', err)
    error.value = 'Não foi possível carregar os níveis ópticos'
  } finally {
    loading.value = false
  }
}

// `immediate: true` cobre o caso em que o componente é montado já com
// visible=true (parent usa lazy v-if → não há transição false→true).
watch(
  () => [props.visible, props.cableData?.id],
  ([vis]) => {
    if (vis && props.cableData) {
      initPosition()
      loadOpticalData()
    } else if (!vis) {
      opticalData.value = null
      error.value = null
    }
  },
  { immediate: true }
)

// ── Formatação ───────────────────────────────────────────────────────────────
const formatValue = (value, unit = 'dBm') => {
  const n = normalizeNumber(value)
  return n !== null ? `${n.toFixed(2)} ${unit}` : 'N/A'
}
const formatLevel = (v) => formatValue(v, 'dBm')

// Defaults usados quando o backend não forneceu thresholds para a porta
// (compatibilidade com cabos antigos sem optical_summary completo).
const DEFAULT_WARN_TH = -24
const DEFAULT_CRIT_TH = -27

const getLevelClass = (value, side = 'origin') => {
  const n = normalizeNumber(value)
  if (n === null) return 'level-unknown'

  // Thresholds vindos do backend (calculados por distância ou config global).
  // Ficam em opticalData.{origin|destination}.warning_threshold/critical_threshold.
  const block = opticalData.value?.[side]
  const warnTh = Number.isFinite(Number(block?.warning_threshold))
    ? Number(block.warning_threshold)
    : DEFAULT_WARN_TH
  const critTh = Number.isFinite(Number(block?.critical_threshold))
    ? Number(block.critical_threshold)
    : DEFAULT_CRIT_TH

  if (n <= critTh) return 'level-critical'
  if (n <= warnTh) return 'level-warning'
  // Bonus visual: ≥ -10 dBm é "excellent" (verde mais forte). Não vem do
  // backend porque não afeta o status — só o destaque de UI.
  if (n >= -10) return 'level-excellent'
  return 'level-good'
}

const formatTimestamp = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
/* EV-0064: superfície e bordas por tokens (claro/escuro), 320 px, valores em mono */
.optical-panel {
  position: fixed;
  z-index: 10000;
  width: min(320px, calc(100vw - 16px));
  background: rgb(var(--surface));
  border: 1px solid rgb(var(--n-200));
  border-radius: 10px;
  box-shadow: 0 12px 28px -8px rgb(0 0 0 / 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-size: 13px;
  color: rgb(var(--n-900));
}
.optical-panel.dragging {
  box-shadow: 0 18px 36px -8px rgb(0 0 0 / 0.35), 0 0 0 2px rgb(var(--primary-500) / 0.5);
  cursor: grabbing;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid rgb(var(--n-200));
  cursor: grab;
  user-select: none;
  -webkit-user-select: none;
  touch-action: none;
  flex-shrink: 0;
}
.panel-header:active { cursor: grabbing; }
.drag-grip { display: flex; flex-direction: column; gap: 3px; flex-shrink: 0; }
.drag-grip span { display: block; width: 12px; height: 2px; background: rgb(var(--n-400)); border-radius: 1px; }
.header-text { flex: 1; min-width: 0; }
.panel-title {
  font-weight: 600;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.panel-subtitle {
  font-size: 11px;
  color: rgb(var(--n-500));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.close-btn {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  color: rgb(var(--n-500));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.close-btn:hover { background: rgb(var(--n-100)); color: rgb(var(--n-900)); }
.close-btn svg { width: 14px; height: 14px; }

.panel-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 18px 12px;
  color: rgb(var(--n-500));
}
.panel-state.error { color: rgb(var(--danger)); }
.panel-state svg { width: 16px; height: 16px; flex-shrink: 0; }
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgb(var(--n-200));
  border-top-color: rgb(var(--primary-500));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

.panel-body { padding: 4px 12px 8px; display: flex; flex-direction: column; }
.iface-block { padding: 8px 0; border-bottom: 1px solid rgb(var(--n-100)); }
.iface-block:last-of-type { border-bottom: none; }
.iface-header { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }
.iface-end {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: rgb(var(--n-100));
  color: rgb(var(--n-600));
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}
.iface-name {
  font-weight: 600;
  font-size: 12px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* TX e RX lado a lado */
.levels { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.level-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 3px 6px 3px 8px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 6px;
}
.level-label { color: rgb(var(--n-500)); font-size: 11px; font-weight: 600; }
.level-value {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  font-size: 12px;
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
}
.level-excellent,
.level-good { color: rgb(var(--success)); background: rgb(var(--success) / 0.12); }
.level-warning { color: rgb(var(--warning)); background: rgb(var(--warning) / 0.14); }
.level-critical { color: rgb(var(--danger)); background: rgb(var(--danger) / 0.12); }
.level-unknown { color: rgb(var(--n-500)); background: rgb(var(--n-100)); }
.iface-empty { color: rgb(var(--n-500)); font-size: 11px; margin: 0; }

.attenuation-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0 2px;
  border-top: 1px solid rgb(var(--n-100));
}
.atten-label { color: rgb(var(--n-500)); font-size: 12px; }
.atten-value {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 11px;
  color: rgb(var(--n-500));
  padding-top: 6px;
}
.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  color: rgb(var(--n-700));
  font-size: 11px;
}
.refresh-btn:hover:not(:disabled) { background: rgb(var(--n-100)); }
.refresh-btn:disabled { opacity: 0.6; cursor: progress; }
.refresh-btn svg { width: 12px; height: 12px; }
.refresh-btn svg.spinning { animation: spin 1s linear infinite; }

.panel-actions { padding: 8px 12px 10px; border-top: 1px solid rgb(var(--n-200)); }
.details-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 7px 12px;
  border-radius: 7px;
  background: rgb(var(--primary-600));
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}
.details-btn:hover { background: rgb(var(--primary-700)); }
.details-btn svg { width: 14px; height: 14px; }
</style>
