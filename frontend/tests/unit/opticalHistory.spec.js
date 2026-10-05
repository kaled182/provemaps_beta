import { describe, it, expect } from 'vitest'
import {
  normalizeOpticalHistory,
  OPTICAL_HISTORY_EMPTY_MESSAGE,
  OPTICAL_HISTORY_ERROR_MESSAGE,
} from '@/utils/opticalHistory'

describe('normalizeOpticalHistory (EV-0001)', () => {
  it('devolve vazio para resposta vazia, nula ou sem history', () => {
    expect(normalizeOpticalHistory([]).isEmpty).toBe(true)
    expect(normalizeOpticalHistory(null).isEmpty).toBe(true)
    expect(normalizeOpticalHistory({}).isEmpty).toBe(true)
    expect(normalizeOpticalHistory({ history: [] }).isEmpty).toBe(true)
  })

  it('nunca inventa pontos: vazio continua vazio, sem valores aleatórios', () => {
    const a = normalizeOpticalHistory([])
    const b = normalizeOpticalHistory([])
    expect(a.points).toEqual([])
    expect(b.points).toEqual([])
  })

  it('mapeia lista do backend para {timestamp, rx, tx} ordenado', () => {
    const { points, isEmpty } = normalizeOpticalHistory([
      { timestamp: '2026-10-04T10:05:00Z', rx_power: -21.5, tx_power: -3.1 },
      { timestamp: '2026-10-04T10:00:00Z', rx_power: '-22.0', tx_power: null },
    ])
    expect(isEmpty).toBe(false)
    expect(points).toHaveLength(2)
    expect(points[0]).toEqual({
      timestamp: Date.parse('2026-10-04T10:00:00Z'),
      rx: -22,
      tx: null,
    })
    expect(points[1].rx).toBe(-21.5)
    expect(points[1].tx).toBe(-3.1)
  })

  it('aceita o envelope { history: [...] } e descarta entradas inválidas', () => {
    const { points } = normalizeOpticalHistory({
      history: [
        { timestamp: 'não é data', rx_power: -20 },
        { timestamp: '2026-10-04T10:00:00Z', rx_power: null, tx_power: undefined },
        { timestamp: '2026-10-04T10:01:00Z', rx_power: -20 },
      ],
    })
    expect(points).toHaveLength(1)
    expect(points[0].rx).toBe(-20)
  })

  it('expõe mensagens distintas para vazio e erro', () => {
    expect(OPTICAL_HISTORY_EMPTY_MESSAGE).not.toBe(OPTICAL_HISTORY_ERROR_MESSAGE)
    expect(OPTICAL_HISTORY_ERROR_MESSAGE).toMatch(/Zabbix/)
  })
})
