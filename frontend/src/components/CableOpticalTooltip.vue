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
              <span class="iface-icon">📡</span>
              <span class="iface-name">{{ opticalData.origin?.interface || 'Origem não configurada' }}</span>
            </div>
            <div v-if="opticalData.origin" class="levels">
              <div class="level-row">
                <span class="level-label">TX (Transmissão):</span>
                <span class="level-value" :class="getLevelClass(opticalData.origin.tx, 'origin')">
                  {{ formatLevel(opticalData.origin.tx) }}
                </span>
              </div>
              <div class="level-row">
                <span class="level-label">RX (Recepção):</span>
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
              <span class="iface-icon">📡</span>
              <span class="iface-name">{{ opticalData.destination?.interface || 'Destino não configurado' }}</span>
            </div>
            <div v-if="opticalData.destination" class="levels">
              <div class="level-row">
                <span class="level-label">TX (Transmissão):</span>
                <span class="level-value" :class="getLevelClass(opticalData.destination.tx, 'destination')">
                  {{ formatLevel(opticalData.destination.tx) }}
                </span>
              </div>
              <div class="level-row">
                <span class="level-label">RX (Recepção):</span>
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
/* ── Painel flutuante ──────────────────────────────────────────────────────── */
.optical-panel {
  position: fixed;
  z-index: 10000;
  width: min(400px, calc(100vw - 16px));
  background: #1e293b;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  box-shadow: 0 20px 40px -10px rgba(0,0,0,0.7), 0 0 0 1px rgba(99,102,241,0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-size: 13px;
}

.optical-panel.dragging {
  box-shadow: 0 28px 52px -10px rgba(0,0,0,0.85), 0 0 0 2px rgba(99,102,241,0.45);
  cursor: grabbing;
}

/* ── Header ────────────────────────────────────────────────────────────────── */
.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  background: #0f172a;
  border-bottom: 1px solid rgba(255,255,255,0.07);
  cursor: grab;
  user-select: none;
  -webkit-user-select: none;
  touch-action: none;
  flex-shrink: 0;
}

.panel-header:active { cursor: grabbing; }

.drag-grip {
  display: flex;
  flex-direction: column;
  gap: 3px;
  opacity: 0.35;
  flex-shrink: 0;
}

.drag-grip span {
  display: block;
  width: 16px;
  height: 2px;
  background: #94a3b8;
  border-radius: 1px;
}

.header-text { flex: 1; min-width: 0; }

.panel-title {
  font-weight: 700;
  color: #f1f5f9;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.panel-subtitle {
  font-size: 11px;
  color: #64748b;
  margin-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.close-btn {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,255,255,0.08);
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
}

.close-btn:hover {
  background: rgba(239,68,68,0.18);
  border-color: rgba(239,68,68,0.3);
  color: #fca5a5;
}

.close-btn svg { width: 14px; height: 14px; }

/* ── Estados ───────────────────────────────────────────────────────────────── */
.panel-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px 16px;
  color: #64748b;
  font-size: 13px;
}

.panel-state.error { color: #ef4444; }
.panel-state.muted { color: #475569; }
.panel-state svg { width: 18px; height: 18px; flex-shrink: 0; }

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #334155;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Body ──────────────────────────────────────────────────────────────────── */
.panel-body {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.iface-block {
  padding: 10px 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.iface-block:last-of-type { border-bottom: none; }

.iface-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.iface-icon { font-size: 14px; line-height: 1; }

.iface-name {
  font-weight: 600;
  color: #e2e8f0;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.levels { display: flex; flex-direction: column; gap: 5px; padding-left: 22px; }

.level-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.level-label { color: #64748b; font-size: 12px; }

.level-value {
  font-weight: 700;
  font-size: 13px;
  padding: 2px 8px;
  border-radius: 5px;
  white-space: nowrap;
}

.level-excellent { color: #10b981; background: rgba(16,185,129,0.12); }
.level-good      { color: #3b82f6; background: rgba(59,130,246,0.12); }
.level-warning   { color: #f59e0b; background: rgba(245,158,11,0.12); }
.level-critical  { color: #ef4444; background: rgba(239,68,68,0.12); }
.level-unknown   { color: #64748b; background: rgba(100,116,139,0.12); }

.iface-empty { color: #475569; font-size: 11px; padding-left: 22px; margin: 0; }

/* ── Atenuação e footer ────────────────────────────────────────────────────── */
.attenuation-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0 4px;
  border-top: 1px solid rgba(255,255,255,0.06);
  margin-top: 4px;
}

.atten-label { color: #64748b; font-size: 12px; }

.atten-value { font-weight: 700; color: #f1f5f9; font-size: 13px; }

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 11px;
  color: #94a3b8;
  padding-top: 8px;
}
.last-check {
  color: #94a3b8;
}
.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.35);
  border-radius: 6px;
  color: #c7d2fe;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.15s;
}
.refresh-btn:hover:not(:disabled) {
  background: rgba(99, 102, 241, 0.22);
}
.refresh-btn:disabled {
  opacity: 0.6;
  cursor: progress;
}
.refresh-btn svg {
  width: 12px;
  height: 12px;
  transition: transform 0.3s;
}
.refresh-btn svg.spinning {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Botão Ver Detalhes ────────────────────────────────────────────────────── */
.panel-actions {
  padding: 10px 14px 12px;
  border-top: 1px solid rgba(255,255,255,0.07);
}

.details-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 8px 14px;
  background: rgba(59,130,246,0.15);
  border: 1px solid rgba(59,130,246,0.3);
  border-radius: 8px;
  color: #93c5fd;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  justify-content: center;
}

.details-btn:hover {
  background: rgba(59,130,246,0.28);
  border-color: rgba(59,130,246,0.5);
  color: #bfdbfe;
}

.details-btn svg { width: 15px; height: 15px; flex-shrink: 0; }

/* ── Animação ──────────────────────────────────────────────────────────────── */
.tooltip-float-enter-active {
  transition: opacity 0.16s ease, transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.tooltip-float-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.tooltip-float-enter-from {
  opacity: 0;
  transform: scale(0.93) translateY(8px);
}
.tooltip-float-leave-to {
  opacity: 0;
  transform: scale(0.97) translateY(4px);
}

/* ── Mobile ────────────────────────────────────────────────────────────────── */
@media (max-width: 480px) {
  .optical-panel {
    width: calc(100vw - 16px) !important;
    left: 8px !important;
    border-radius: 12px 12px 8px 8px;
  }

  .level-value { font-size: 12px; }
  .iface-name  { font-size: 11px; }
}
</style>
