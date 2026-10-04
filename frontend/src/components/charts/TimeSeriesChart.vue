<template>
  <div class="tsc" :style="{ height: `${height}px` }">
    <canvas v-if="hasData" ref="canvasRef" class="tsc-canvas"></canvas>
    <p v-else class="tsc-empty" role="status">{{ emptyMessage }}</p>
  </div>
</template>

<script setup>
/**
 * TimeSeriesChart — o único gráfico de série temporal do produto (EV-0011/EV-0026).
 *
 * Regras (CLAUDE.md §5 «Gráficos»):
 * - eixo X temporal proporcional (epoch ms em escala linear; sem adaptador de datas);
 * - `null` é buraco, nunca zero nem valor anterior (`spanGaps` desligado por omissão);
 * - cores vêm de variáveis de tema, nunca hex fixo;
 * - uma instância Chart.js por componente, destruída em `onBeforeUnmount`;
 * - sem `setTimeout`: o gráfico nasce quando o canvas existe (watch no ref).
 */
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps({
  /** [{ label, color?, data: [{ x: epoch ms | ISO string, y: number|null }] }] */
  series: { type: Array, default: () => [] },
  /** [{ value, label?, color? }] — linhas horizontais tracejadas (ex.: limiares ópticos) */
  thresholds: { type: Array, default: () => [] },
  unit: { type: String, default: '' },
  height: { type: Number, default: 260 },
  decimals: { type: Number, default: 1 },
  beginAtZero: { type: Boolean, default: false },
  spanGaps: { type: Boolean, default: false },
  emptyMessage: { type: String, default: 'Sem dados para o período selecionado' },
})

const canvasRef = ref(null)
let chart = null

const toMs = (x) => {
  if (x === null || x === undefined) return null
  if (typeof x === 'number') return x
  const t = new Date(x).getTime()
  return Number.isFinite(t) ? t : null
}

const toNumberOrNull = (y) => {
  if (y === null || y === undefined) return null
  const n = Number(y)
  return Number.isFinite(n) ? n : null
}

const normalizedSeries = computed(() =>
  (props.series || []).map((s) => ({
    label: s.label ?? '',
    color: s.color ?? null,
    data: (s.data || [])
      .map((p) => ({ x: toMs(p.x), y: toNumberOrNull(p.y) }))
      .filter((p) => p.x !== null),
  })),
)

const hasData = computed(() =>
  normalizedSeries.value.some((s) => s.data.some((p) => p.y !== null)),
)

const cssVar = (name, fallback) => {
  if (typeof window === 'undefined' || !window.getComputedStyle) return fallback
  const value = window.getComputedStyle(document.documentElement).getPropertyValue(name)
  return value && value.trim() ? value.trim() : fallback
}

const palette = () => ({
  text: cssVar('--text-tertiary', '#94a3b8'),
  grid: cssVar('--border-secondary', 'rgba(148, 163, 184, 0.14)'),
  series: [
    cssVar('--accent-info', '#60a5fa'),
    cssVar('--accent-primary', '#22c55e'),
    cssVar('--status-warning', '#f59e0b'),
    cssVar('--accent-danger', '#f87171'),
  ],
  warning: cssVar('--status-warning', '#f59e0b'),
  danger: cssVar('--status-offline', '#f87171'),
})

const formatTick = (ms) =>
  new Date(ms).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

const formatValue = (v) => `${Number(v).toFixed(props.decimals)}${props.unit ? ` ${props.unit}` : ''}`

const buildData = () => {
  const colors = palette()
  const datasets = normalizedSeries.value.map((s, i) => {
    const color = s.color || colors.series[i % colors.series.length]
    return {
      label: s.label,
      data: s.data,
      borderColor: color,
      backgroundColor: color,
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      tension: 0.2,
      spanGaps: props.spanGaps,
      fill: false,
    }
  })

  const xs = normalizedSeries.value.flatMap((s) => s.data.map((p) => p.x))
  if (xs.length && props.thresholds.length) {
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    props.thresholds.forEach((t) => {
      const value = toNumberOrNull(t.value)
      if (value === null) return
      datasets.push({
        label: t.label ?? `Limiar ${formatValue(value)}`,
        data: [{ x: minX, y: value }, { x: maxX, y: value }],
        borderColor: t.color || colors.warning,
        borderWidth: 1,
        borderDash: [6, 4],
        pointRadius: 0,
        pointHoverRadius: 0,
        fill: false,
        isThreshold: true,
      })
    })
  }
  return { datasets }
}

const buildOptions = () => {
  const colors = palette()
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    parsing: false,
    normalized: true,
    interaction: { mode: 'nearest', axis: 'x', intersect: false },
    plugins: {
      legend: {
        display: true,
        labels: { color: colors.text, boxWidth: 12, usePointStyle: true },
      },
      tooltip: {
        callbacks: {
          title: (items) => (items.length ? new Date(items[0].parsed.x).toLocaleString('pt-BR') : ''),
          label: (item) =>
            item.parsed.y === null ? `${item.dataset.label}: sem dados` : `${item.dataset.label}: ${formatValue(item.parsed.y)}`,
        },
      },
    },
    scales: {
      x: {
        type: 'linear',
        grid: { color: colors.grid },
        ticks: { color: colors.text, maxTicksLimit: 8, maxRotation: 0, callback: (v) => formatTick(v) },
      },
      y: {
        beginAtZero: props.beginAtZero,
        grid: { color: colors.grid },
        ticks: { color: colors.text, callback: (v) => formatValue(v) },
      },
    },
  }
}

const destroyChart = () => {
  if (chart) {
    chart.destroy()
    chart = null
  }
}

const createChart = () => {
  if (!canvasRef.value || !hasData.value) return
  destroyChart()
  chart = new Chart(canvasRef.value, { type: 'line', data: buildData(), options: buildOptions() })
}

const refresh = () => {
  if (!hasData.value) {
    destroyChart()
    return
  }
  if (!chart) {
    createChart()
    return
  }
  chart.data = buildData()
  chart.options = buildOptions()
  chart.update('none')
}

// O canvas só existe quando há dados (v-if): criar quando aparecer, destruir quando sumir.
watch(canvasRef, (el) => {
  if (el) createChart()
  else destroyChart()
})
watch(() => [props.series, props.thresholds, props.unit, props.spanGaps, props.beginAtZero], refresh, { deep: true })

onBeforeUnmount(destroyChart)

defineExpose({
  /** PNG do gráfico atual (ou null sem gráfico) — usado pelos exports dos modais. */
  toDataURL: () => (chart ? chart.toBase64Image() : null),
  canvasRef,
})
</script>

<style scoped>
.tsc {
  position: relative;
  width: 100%;
}
.tsc-canvas {
  width: 100% !important;
  height: 100% !important;
}
.tsc-empty {
  margin: 0;
  padding: 16px;
  font-size: 13px;
  color: var(--text-tertiary, #94a3b8);
}
</style>
