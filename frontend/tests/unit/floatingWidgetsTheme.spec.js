/**
 * EV-0050 — widgets flutuantes do mapa usam tokens (invertem com o tema) e não
 * fundos escuros fixos; o estado de ligação do Dashboard está em PT-BR.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(__dirname, '../..')
const read = (p) => readFileSync(resolve(root, p), 'utf8')
const style = (sfc) => sfc.slice(sfc.indexOf('<style'))

// Fundos escuros fixos que apareciam nos widgets antes do EV-0050
const DARK_LITERALS = [/rgba\(15,\s*23,\s*42/, /rgba\(10,\s*60,\s*40/, /rgba\(80,\s*10,\s*10/, /rgba\(70,\s*45,\s*0/, /#1e2433/i]

const ruleBody = (css, selector) => {
  const start = css.indexOf(`${selector} {`)
  expect(start, selector).toBeGreaterThan(-1)
  return css.slice(css.indexOf('{', start) + 1, css.indexOf('}', start))
}

describe('widgets flutuantes nos dois temas (EV-0050)', () => {
  it('a legenda do mapa não tem fundo escuro fixo nem bloco de tema à parte', () => {
    const css = style(read('src/views/monitoring/components/MapLegend.vue'))
    for (const re of DARK_LITERALS) expect(css).not.toMatch(re)
    expect(css).not.toContain('data-theme="light"')
    expect(ruleBody(css, '.legend-pill')).toContain('rgb(var(--surface)')
  })

  it('Reenquadrar, aviso de notificação e toasts do mapa vêm dos tokens', () => {
    const css = style(read('src/views/monitoring/CustomMapViewer.vue'))
    for (const sel of ['.map-fit-btn', '.notify-sent-badge', '.map-toast']) {
      const body = ruleBody(css, sel)
      expect(body, sel).toContain('rgb(var(--surface)')
      for (const re of DARK_LITERALS) expect(body, sel).not.toMatch(re)
    }
    for (const kind of ['success', 'error', 'warning']) {
      for (const re of DARK_LITERALS) expect(ruleBody(css, `.map-toast--${kind}`)).not.toMatch(re)
    }
  })

  it('o estado de ligação do Dashboard está em PT-BR', () => {
    const sfc = read('src/components/Dashboard/DashboardView.vue')
    expect(sfc).toContain('Tempo real')
    expect(sfc).not.toMatch(/>\s*(Connected|Connecting\.\.\.)\s*</)
  })
})
