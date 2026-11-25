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

const mean = (values) => (values.length ? values.reduce((a, b) => a + b, 0) / values.length : null)

/**
 * Estatísticas RX/TX de uma porta (EV-0053). Sem leituras → `null`, nunca 0:
 * «0.00 dBm» parece um sinal excelente e escondia justamente a ponta em LOS.
 * `lastRx` é a leitura RX mais recente (por timestamp) — é a que decide o alarme.
 *
 * @param {Array<{timestamp: string|number, rx_power?: number|null, tx_power?: number|null}>} historyArray
 */
export function opticalPortStats(historyArray) {
  const sorted = (Array.isArray(historyArray) ? [...historyArray] : []).sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
  )
  const rx = sorted.map((p) => toNumberOrNull(p.rx_power)).filter((v) => v !== null)
  const tx = sorted.map((p) => toNumberOrNull(p.tx_power)).filter((v) => v !== null)
  return {
    avgRx: mean(rx),
    minRx: rx.length ? Math.min(...rx) : null,
    maxRx: rx.length ? Math.max(...rx) : null,
    avgTx: mean(tx),
    minTx: tx.length ? Math.min(...tx) : null,
    maxTx: tx.length ? Math.max(...tx) : null,
    lastRx: rx.length ? rx[rx.length - 1] : null,
  }
}

/**
 * A ponta está em perda de sinal? Só com leitura real e limiar crítico da
 * configuração (CLAUDE.md §7: limiares não são constantes do componente).
 * Sem leitura ou sem limiar → `false` (não se acusa sem prova).
 */
export function isRxCritical(lastRx, critical) {
  if (lastRx === null || lastRx === undefined) return false
  if (critical === null || critical === undefined) return false
  return Number(lastRx) <= Number(critical)
}
