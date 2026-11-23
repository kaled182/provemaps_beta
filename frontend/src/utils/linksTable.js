/**
 * Enlaces & fibra (EV-0057): filtro, ordenação e formatação da tabela, sobre o
 * payload de `GET /api/v1/fiber-cables/optical-summary/`.
 * @module linksTable
 */
import { foldText } from '@/composables/useNavSections'

export const LINK_FILTERS = Object.freeze([
  { id: 'all', label: 'Todos' },
  { id: 'critical', label: 'Críticos' },
  { id: 'attention', label: 'Atenção' },
  { id: 'healthy', label: 'Saudáveis' },
  { id: 'unknown', label: 'Sem leitura' },
])

export const HEALTH_LABEL = Object.freeze({
  critical: 'Crítico',
  attention: 'Atenção',
  healthy: 'Saudável',
  unknown: 'Sem leitura',
})

const SEVERITY = { critical: 3, attention: 2, unknown: 1, healthy: 0 }

/** Menor RX real (fresco) das duas pontas, ou `null`. */
export function worstRx(cable) {
  const values = [cable?.origin, cable?.destination]
    .filter((end) => end && end.rx !== null && end.rx !== undefined && !end.stale)
    .map((end) => end.rx)
  return values.length ? Math.min(...values) : null
}

/**
 * Filtra por saúde e texto (nome, sites, equipamentos, portas — sem acentos) e
 * ordena: pior saúde primeiro; dentro dela, RX mais baixo primeiro; sem RX no fim.
 */
export function filterAndSortLinks(cables, { filter = 'all', query = '' } = {}) {
  const q = foldText(query).trim()
  return (cables || [])
    .filter((c) => filter === 'all' || c.health === filter)
    .filter((c) => {
      if (!q) return true
      const hay = foldText(
        [c.name, c.site_a, c.site_b, c.origin?.device_name, c.origin?.port_name, c.destination?.device_name, c.destination?.port_name]
          .filter(Boolean)
          .join(' '),
      )
      return hay.includes(q)
    })
    .slice()
    .sort((a, b) => {
      const sev = (SEVERITY[b.health] ?? 0) - (SEVERITY[a.health] ?? 0)
      if (sev) return sev
      const ra = worstRx(a)
      const rb = worstRx(b)
      if (ra === null && rb === null) return a.name.localeCompare(b.name, 'pt-BR')
      if (ra === null) return 1
      if (rb === null) return -1
      return ra - rb
    })
}

/** `-18.5` → «-18.50»; ausência → «—». Nunca «0.00» para falta de valor. */
export function formatDb(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return Number(value).toFixed(2)
}

/** Contagens por filtro (para os chips). */
export function countByFilter(cables) {
  const counts = { all: 0, critical: 0, attention: 0, healthy: 0, unknown: 0 }
  for (const c of cables || []) {
    counts.all += 1
    if (c.health in counts) counts[c.health] += 1
  }
  return counts
}
