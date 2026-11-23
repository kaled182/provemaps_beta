/**
 * EV-0051 — no modal do cabo a faixa RX/TX Médio fica ACIMA do gráfico óptico e o
 * contentor não tem altura fixa menor que o gráfico (o gráfico de 260 px
 * transbordava a caixa de 175 px e ficava por baixo dos resumos).
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const sfc = readFileSync(resolve(__dirname, '../../src/components/FiberCableDetailModal.vue'), 'utf8')

describe('modal do cabo — gráfico óptico (EV-0051)', () => {
  for (const side of ['origin', 'destination']) {
    it(`${side}: resumos antes do gráfico`, () => {
      const stats = sfc.indexOf(`data-testid="optical-stats-${side}"`)
      const chart = sfc.indexOf(`ref="${side}ChartRef"`)
      expect(stats).toBeGreaterThan(-1)
      expect(chart).toBeGreaterThan(stats)
    })
  }

  it('o contentor do gráfico não fixa altura', () => {
    const start = sfc.indexOf('.optical-chart-container {')
    const body = sfc.slice(start, sfc.indexOf('}', start))
    expect(body).not.toMatch(/\bheight:/)
  })

  it('os valores da faixa usam tokens e números tabulares', () => {
    const start = sfc.indexOf('.stat-info .stat-value {')
    const body = sfc.slice(start, sfc.indexOf('}', start))
    expect(body).toContain('rgb(var(--n-900))')
    expect(body).toContain('tabular-nums')
  })
})
