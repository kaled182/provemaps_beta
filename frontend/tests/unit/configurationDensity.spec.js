/**
 * EV-0056 — Configuração: cabeçalho numa linha (título · abas · ações, sem
 * subtítulo), cores por tokens (incluindo o CSS partilhado), tabelas densas.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'

const src = resolve(__dirname, '../../src')
const read = (p) => readFileSync(resolve(src, p), 'utf8')
const template = (sfc) => sfc.slice(sfc.indexOf('<template>'), sfc.lastIndexOf('</template>'))
const CONFIG_FILES = readdirSync(resolve(src, 'components/Configuration')).filter((f) => f.endsWith('.vue'))

describe('Configuração compacta e no tema (EV-0056)', () => {
  it('cabeçalho numa linha, sem subtítulo nem altura do layout antigo', () => {
    const t = template(read('views/ConfigurationPage.vue'))
    expect(t).not.toContain('Gestão centralizada de serviços e dados')
    expect(t).not.toMatch(/h-\[calc\(100vh-64px\)\]|min-h-screen/)
    expect(t).toMatch(/<h1[^>]*>Configurações<\/h1>\s*<nav/)
  })

  it('CSS partilhado da configuração sem cinzas/pares dark: literais', () => {
    const css = read('assets/configuration-styles.css')
    for (const line of css.split('\n').filter((l) => l.includes('@apply'))) {
      expect(line).not.toMatch(/\b(text|bg|border|ring)-(gray|slate)-\d/)
      expect(line).not.toMatch(/(^|\s)dark:(?!text-primary)/)
    }
  })

  for (const file of CONFIG_FILES) {
    it(`${file}: template sem cinzento com par dark:`, () => {
      const t = template(read(`components/Configuration/${file}`))
      // um cinzento com par dark: no mesmo atributo é o padrão que os tokens substituem
      expect(t).not.toMatch(/class="[^"]*(bg|text|border)-(gray|slate)-\d[^"]*dark:/)
      expect(t).not.toMatch(/class="[^"]*dark:(bg|text|border)-(gray|slate)-/)
    })
  }

  it('tabela de contactos com linhas densas e limiares dBm em mono tabular', () => {
    expect(read('components/Configuration/ContactList.vue')).toMatch(/\.contacts-table td \{[^}]*padding: 6px 12px/)
    expect(read('components/Configuration/MonitoringServersTab.vue')).toMatch(/distanceThresholds\[cat\.key\].warning"[\s\S]{0,300}font-mono tabular-nums/)
  })
})
