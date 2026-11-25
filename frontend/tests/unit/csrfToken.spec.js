/**
 * EV-0072 — o leitor de CSRF usa o nome real do cookie (`mapsprovefiber_csrftoken`).
 * Antes procurava `csrftoken=` no início do cookie e nunca o encontrava; o CronTab, que
 * não usava o window.CSRF_TOKEN, mandava o cabeçalho vazio e o DRF respondia 403.
 */
import { describe, it, expect, afterEach, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { getCsrfToken, readCookie, CSRF_COOKIE_NAMES } from '@/composables/useApi'

const src = (p) => readFileSync(resolve(__dirname, '../../src', p), 'utf8')
const clearCookies = () => {
  for (const c of document.cookie.split(';')) {
    const name = c.split('=')[0].trim()
    if (name) document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`
  }
}

afterEach(() => {
  delete window.CSRF_TOKEN
  clearCookies()
  vi.restoreAllMocks()
})

describe('getCsrfToken', () => {
  it('lê o cookie pelo nome do Django (CSRF_COOKIE_NAME)', () => {
    expect(CSRF_COOKIE_NAMES[0]).toBe('mapsprovefiber_csrftoken')
    document.cookie = 'mapsprovefiber_sessionid=abc; path=/'
    document.cookie = 'mapsprovefiber_csrftoken=tok123; path=/'
    expect(getCsrfToken()).toBe('tok123')
  })

  it('o window.CSRF_TOKEN injetado pelo base_spa.html vem primeiro', () => {
    document.cookie = 'mapsprovefiber_csrftoken=docookie; path=/'
    window.CSRF_TOKEN = 'dowindow'
    expect(getCsrfToken()).toBe('dowindow')
  })

  it('não confunde nomes que só terminam em «csrftoken»', () => {
    expect(readCookie('csrftoken', 'mapsprovefiber_csrftoken=x; outra=1')).toBe('')
    expect(readCookie('mapsprovefiber_csrftoken', 'a=1; mapsprovefiber_csrftoken=x%3Dy')).toBe('x=y')
  })

  it('sem token devolve vazio e avisa', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(getCsrfToken()).toBe('')
    expect(warn).toHaveBeenCalled()
  })
})

describe('um só leitor de CSRF (EV-0072)', () => {
  for (const p of [
    'components/Configuration/CronTab.vue',
    'components/Zabbix/ZabbixLookupView.vue',
    'components/Layout/SystemPanel.vue',
    'features/networkDesign/modules/apiClient.js',
  ]) {
    it(`${p} usa o getCsrfToken do useApi`, () => {
      const code = src(p)
      expect(code).toContain("getCsrfToken } from '@/composables/useApi'")
      expect(code).not.toMatch(/csrftoken=|['"]csrftoken['"]/)
    })
  }
})
