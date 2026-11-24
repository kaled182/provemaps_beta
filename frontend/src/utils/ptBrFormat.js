/**
 * Formatação PT-BR para ecrãs NOC (EV-0095): vírgula decimal, «—» para o que
 * não existe (CLAUDE.md §2.1 — nunca inventar um valor).
 */
export const DASH = '—'

const isNum = (v) => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v))

/** Número com casas fixas e vírgula decimal; null/undefined → «—». */
export function formatNumber(value, digits = 1) {
  if (!isNum(value)) return DASH
  return Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

/** Número com até `max` casas (sem zeros à direita): -24 → «-24», -24.5 → «-24,5». */
export function formatCompact(value, max = 1) {
  if (!isNum(value)) return DASH
  return Number(value).toLocaleString('pt-BR', { maximumFractionDigits: max })
}

/** Inteiro (contagens); null → «—». */
export function formatInt(value) {
  if (!isNum(value)) return DASH
  return Math.round(Number(value)).toLocaleString('pt-BR')
}

export function formatDbm(value) {
  return isNum(value) ? `${formatNumber(value, 1)} dBm` : DASH
}

export function formatPercent(value, digits = 0) {
  return isNum(value) ? `${formatNumber(value, digits)}%` : DASH
}

/** Metros → «850 m» ou «1,8 km». */
export function formatDistance(meters) {
  if (!isNum(meters)) return DASH
  const m = Number(meters)
  return m < 1000 ? `${Math.round(m)} m` : `${formatNumber(m / 1000, 1)} km`
}

/** Segundos → «< 1 min», «35 min», «4 h 10 min», «12 d 4 h». */
export function formatDuration(seconds) {
  if (!isNum(seconds)) return DASH
  const s = Math.max(0, Math.floor(Number(seconds)))
  if (s < 60) return '< 1 min'
  const min = Math.floor(s / 60)
  if (min < 60) return `${min} min`
  const h = Math.floor(min / 60)
  if (h < 24) return min % 60 ? `${h} h ${min % 60} min` : `${h} h`
  const d = Math.floor(h / 24)
  return h % 24 ? `${d} d ${h % 24} h` : `${d} d`
}

/**
 * Há quanto tempo, a partir de um ISO: «há 12 d 4 h». Quando o instante é só a
 * primeira observação (`firstSeen`), o tempo real é pelo menos esse: «≥ 12 d 4 h».
 */
export function formatSince(iso, firstSeen = false, now = Date.now()) {
  if (!iso) return DASH
  const t = new Date(iso).getTime()
  if (!Number.isFinite(t)) return DASH
  const d = formatDuration((now - t) / 1000)
  return firstSeen ? `≥ ${d}` : `há ${d}`
}

/** EV-0109: bits por segundo → «950 kbps» / «8,8 Mbps» / «1,2 Gbps»; ausência → «—». */
export function formatBps(bps) {
  if (!isNum(bps)) return DASH
  const v = Number(bps)
  if (Math.abs(v) >= 1e9) return `${formatNumber(v / 1e9, 1)} Gbps`
  if (Math.abs(v) >= 1e6) return `${formatNumber(v / 1e6, 1)} Mbps`
  if (Math.abs(v) >= 1e3) return `${formatNumber(v / 1e3, 0)} kbps`
  return `${formatNumber(v, 0)} bps`
}
