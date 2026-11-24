/** EV-0095 — formatação PT-BR: vírgula decimal e «—» para o que não existe. */
import { describe, it, expect } from 'vitest'
import { formatCompact, formatDbm, formatDistance, formatDuration, formatInt, formatNumber, formatPercent, formatSince } from '@/utils/ptBrFormat'

describe('ptBrFormat', () => {
  it('usa vírgula decimal', () => {
    expect(formatNumber(-19.44, 1)).toBe('-19,4')
    expect(formatDbm(-21.3)).toBe('-21,3 dBm')
    expect(formatPercent(9.44, 1)).toBe('9,4%')
    expect(formatCompact(-24)).toBe('-24')
    expect(formatCompact(-27.5)).toBe('-27,5')
  })

  it('null/undefined → «—», nunca zero', () => {
    for (const fn of [formatNumber, formatDbm, formatPercent, formatInt, formatDistance, formatDuration, formatCompact]) {
      expect(fn(null)).toBe('—')
      expect(fn(undefined)).toBe('—')
    }
    expect(formatSince(null)).toBe('—')
    expect(formatInt(0)).toBe('0')
  })

  it('distância em m ou km', () => {
    expect(formatDistance(850)).toBe('850 m')
    expect(formatDistance(1854)).toBe('1,9 km')
  })

  it('duração e «desde»', () => {
    expect(formatDuration(30)).toBe('< 1 min')
    expect(formatDuration(35 * 60)).toBe('35 min')
    expect(formatDuration(4 * 3600 + 600)).toBe('4 h 10 min')
    expect(formatDuration((12 * 24 + 4) * 3600)).toBe('12 d 4 h')
    const now = Date.parse('2026-11-24T02:00:00Z')
    const iso = new Date(now - (12 * 24 + 4) * 3600 * 1000).toISOString()
    expect(formatSince(iso, false, now)).toBe('há 12 d 4 h')
    expect(formatSince(iso, true, now)).toBe('≥ 12 d 4 h')
  })
})
