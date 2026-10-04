import { describe, it, expect } from 'vitest'
import { formatOpticalSeries, bpsToMbps } from '@/utils/opticalSeries'

describe('formatOpticalSeries (EV-0010)', () => {
  it('devolve null para histórico vazio', () => {
    expect(formatOpticalSeries([])).toBeNull()
    expect(formatOpticalSeries(null)).toBeNull()
  })

  it('não faz forward-fill: ponto sem valor vira null (buraco)', () => {
    const out = formatOpticalSeries([
      { timestamp: '2026-10-04T10:00:00Z', rx_power: -21, tx_power: -3 },
      { timestamp: '2026-10-04T10:01:00Z', rx_power: null, tx_power: -3.1 },
      { timestamp: '2026-10-04T10:02:00Z', rx_power: -21.5, tx_power: null },
    ])
    expect(out.rxData).toEqual([-21, null, -21.5])
    expect(out.txData).toEqual([-3, -3.1, null])
    expect(out.labels).toHaveLength(3)
  })

  it('ordena por tempo e desenha linhas de limiar quando existem', () => {
    const out = formatOpticalSeries(
      [
        { timestamp: '2026-10-04T10:05:00Z', rx_power: -20 },
        { timestamp: '2026-10-04T10:00:00Z', rx_power: -22 },
      ],
      { warning: -24, critical: -27 },
    )
    expect(out.rxData).toEqual([-22, -20])
    expect(out.warningLine).toEqual([-24, -24])
    expect(out.criticalLine).toEqual([-27, -27])
  })

  it('sem limiares, as linhas são null', () => {
    const out = formatOpticalSeries([{ timestamp: '2026-10-04T10:00:00Z', rx_power: -20 }])
    expect(out.warningLine).toBeNull()
    expect(out.criticalLine).toBeNull()
  })
})

describe('bpsToMbps (EV-0010)', () => {
  it('preserva zero e converte bps em Mbps', () => {
    expect(bpsToMbps(0)).toBe(0)
    expect(bpsToMbps(1_500_000)).toBe(1.5)
    expect(bpsToMbps('2000000')).toBe(2)
  })
  it('só devolve null para ausência de valor', () => {
    expect(bpsToMbps(null)).toBeNull()
    expect(bpsToMbps(undefined)).toBeNull()
    expect(bpsToMbps('abc')).toBeNull()
  })
})
