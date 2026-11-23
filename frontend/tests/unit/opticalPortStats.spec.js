/**
 * EV-0053 — estatísticas da porta sem zeros inventados e regra de perda de sinal.
 */
import { describe, it, expect } from 'vitest'
import { opticalPortStats, isRxCritical } from '@/utils/opticalSeries'

describe('opticalPortStats', () => {
  it('sem leituras → null em tudo (o modal mostra N/A, não 0.00 dBm)', () => {
    expect(opticalPortStats([])).toEqual({
      avgRx: null, minRx: null, maxRx: null, avgTx: null, minTx: null, maxTx: null, lastRx: null,
    })
    const onlyTx = opticalPortStats([{ timestamp: 1, rx_power: null, tx_power: 2 }])
    expect(onlyTx.avgRx).toBeNull()
    expect(onlyTx.lastRx).toBeNull()
    expect(onlyTx.avgTx).toBe(2)
  })

  it('média/mín/máx e último RX por ordem temporal, ignorando buracos', () => {
    const s = opticalPortStats([
      { timestamp: '2026-11-23T10:02:00Z', rx_power: -40, tx_power: 2 },
      { timestamp: '2026-11-23T10:00:00Z', rx_power: -20, tx_power: 2 },
      { timestamp: '2026-11-23T10:03:00Z', rx_power: null, tx_power: 2 },
      { timestamp: '2026-11-23T10:01:00Z', rx_power: '-21', tx_power: 1 },
    ])
    expect(s.avgRx).toBeCloseTo(-27)
    expect(s.minRx).toBe(-40)
    expect(s.maxRx).toBe(-20)
    expect(s.lastRx).toBe(-40) // o null mais recente não apaga a última leitura real
    expect(s.avgTx).toBeCloseTo(1.75)
  })
})

describe('isRxCritical', () => {
  it('só acusa com leitura real e limiar configurado', () => {
    expect(isRxCritical(-35, -27)).toBe(true)
    expect(isRxCritical(-27, -27)).toBe(true)
    expect(isRxCritical(-20, -27)).toBe(false)
    expect(isRxCritical(null, -27)).toBe(false)
    expect(isRxCritical(-40, null)).toBe(false)
  })
})
