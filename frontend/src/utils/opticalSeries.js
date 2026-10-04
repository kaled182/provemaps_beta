/**
 * Série óptica (RX/TX em dBm) pronta para Chart.js.
 *
 * EV-0010: um ponto sem valor é um BURACO (`null`), nunca o valor anterior
 * repetido. O forward-fill que existia em fiberService escondia quedas de
 * link: a linha continuava «plana» no último valor conhecido.
 */

const toNumberOrNull = (value) => {
  if (value === null || value === undefined) return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

export function formatTimestampLabel(timestamp) {
  return new Date(timestamp).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
  })
}

/**
 * @param {Array<{timestamp: string|number, rx_power?: number|null, tx_power?: number|null}>} historyArray
 * @param {{warning?: number|null, critical?: number|null}} [thresholds]
 * @returns {null | {timestamps: number[], labels: string[], rxData: (number|null)[], txData: (number|null)[], thresholds: object, warningLine: number[]|null, criticalLine: number[]|null}}
 */
export function formatOpticalSeries(historyArray, thresholds = {}) {
  if (!Array.isArray(historyArray) || historyArray.length === 0) return null

  const sorted = [...historyArray].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  )

  const timestamps = sorted.map((point) => new Date(point.timestamp).getTime())
  const labels = sorted.map((point) => formatTimestampLabel(point.timestamp))
  const rxData = sorted.map((point) => toNumberOrNull(point.rx_power))
  const txData = sorted.map((point) => toNumberOrNull(point.tx_power))

  const warningValue = thresholds?.warning ?? null
  const criticalValue = thresholds?.critical ?? null

  return {
    timestamps,
    labels,
    rxData,
    txData,
    thresholds,
    warningLine: warningValue !== null ? labels.map(() => warningValue) : null,
    criticalLine: criticalValue !== null ? labels.map(() => criticalValue) : null,
  }
}

/**
 * bps → Mbps preservando zero e devolvendo `null` só para ausência de valor.
 * `d.traffic_in ? d.traffic_in / 1e6 : null` apagava tráfego zero do gráfico.
 */
export function bpsToMbps(value) {
  const n = toNumberOrNull(value)
  return n === null ? null : n / 1_000_000
}
