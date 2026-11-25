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

describe('modal do cabo — tema claro e perda de sinal (EV-0053)', () => {
  const css = sfc.slice(sfc.indexOf('<style'))
  const rules = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({ sel: m[1].trim(), body: m[2] }))

  it('texto branco só sobre fundos coloridos (botões); nada de cinza-claro fixo', () => {
    for (const { sel, body } of rules) {
      if (/color:\s*(white|#fff\b|#ffffff)/i.test(body)) {
        expect(body, sel).toMatch(/background[^;]*(gradient|#[0-9a-f]{3,6})/i)
      }
      expect(body, sel).not.toMatch(/(^|[^-])color:\s*#(e2e8f0|cbd5e1|94a3b8|64748b|fca5a5|6ee7b7|bfdbfe|f1f5f9)/i)
    }
  })

  it('nenhum fundo/borda branco translúcido (invisível no tema claro)', () => {
    for (const { sel, body } of rules) {
      expect(body.replace(/linear-gradient\([^;]*\)/g, ''), sel).not.toMatch(/rgba\(255,\s*255,\s*255/)
    }
  })

  it('a ponta em perda de sinal é realçada pela regra da configuração', () => {
    for (const side of ['origin', 'destination']) {
      expect(sfc).toContain(`'port-los': portLos('${side}')`)
      expect(sfc).toContain(`data-testid="los-badge-${side}"`)
    }
    expect(sfc).toContain('isRxCritical(opticalData.value?.stats?.[side]?.lastRx, opticalData.value?.thresholds?.[side]?.critical)')
    expect(css).toMatch(/\.port-chart-panel\.port-los\s*\{[^}]*--danger/)
  })
})
