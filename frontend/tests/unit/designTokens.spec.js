/**
 * EV-0028 / ADR 0007 Fase 1: os tokens do CRM existem, invertem no escuro,
 * as fontes são auto-hospedadas e o theme.css deixou de ter o acento verde.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(__dirname, '../..')
const tokens = readFileSync(resolve(root, 'src/design-system/tokens.css'), 'utf8')
const theme = readFileSync(resolve(root, 'src/assets/theme.css'), 'utf8')

const block = (css, selector) => {
  const start = css.indexOf(selector)
  expect(start, `seletor ${selector}`).toBeGreaterThan(-1)
  const open = css.indexOf('{', start)
  const close = css.indexOf('}', open)
  return css.slice(open + 1, close)
}

describe('design tokens (ADR 0007, Fase 1)', () => {
  it('define a escala neutra, surface e canvas no claro e inverte no escuro', () => {
    const light = block(tokens, ':root {')
    const dark = block(tokens, ':root[data-theme="dark"],\n.dark {')
    for (const step of [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]) {
      expect(light).toMatch(new RegExp(`--n-${step}: \\d+ \\d+ \\d+;`))
      expect(dark).toMatch(new RegExp(`--n-${step}: \\d+ \\d+ \\d+;`))
    }
    expect(light).toContain('--n-50: 248 250 252;')
    expect(dark).toContain('--n-50: 15 21 23;') // 50 passa a ser o mais escuro
    expect(light).toContain('--surface: 255 255 255;')
    expect(dark).toContain('--canvas: 15 21 23;')
  })

  it('a marca é o teal do CRM (#42B4B8) e não o verde antigo', () => {
    expect(tokens).toContain('--primary-500: 66 180 184;')
    expect(theme).toContain('--accent-primary: rgb(var(--primary-500));')
    expect(theme).not.toMatch(/--accent-primary:\s*#22c55e/i)
    expect(theme).not.toMatch(/--menu-item-active-start:\s*#10b981/i)
  })

  it('as variáveis que os componentes usam vêm todas dos tokens', () => {
    for (const v of ['--text-primary', '--text-tertiary', '--border-primary', '--surface-card', '--bg-primary', '--status-online', '--accent-info']) {
      const m = theme.match(new RegExp(`${v}: ([^;]+);`))
      expect(m, v).not.toBeNull()
      expect(m[1]).toMatch(/var\(--/)
    }
  })

  it('fontes Inter, JetBrains Mono e Outfit auto-hospedadas (sem CDN)', () => {
    for (const file of ['Inter-400', 'Inter-700', 'JetBrainsMono-400', 'Outfit-600']) {
      expect(existsSync(resolve(root, `src/design-system/fonts/${file}.woff2`)), file).toBe(true)
    }
    expect((tokens.match(/@font-face/g) || []).length).toBe(10)
    expect(tokens).not.toMatch(/fonts\.googleapis|fonts\.gstatic/)
    expect(tokens).toContain("--font-sans: 'Inter'")
    expect(readFileSync(resolve(root, 'src/assets/base.css'), 'utf8')).toContain('font-family: var(--font-sans)')
  })

  it('tailwind.config usa os mesmos tokens', () => {
    const tw = readFileSync(resolve(root, 'tailwind.config.js'), 'utf8')
    expect(tw).toContain("500: '#42B4B8'")
    expect(tw).toContain("rgb(var(--n-700) / <alpha-value>)")
    expect(tw).toContain("canvas: 'rgb(var(--canvas) / <alpha-value>)'")
    expect(tw).not.toContain('colors.emerald')
  })
})
