/**
 * EV-0118 — guarda: ninguém lê o CSRF de um `csrfmiddlewaretoken` no DOM (a SPA não o tem;
 * o DRF respondia 403). A fonte única é `getCsrfToken()` do useApi (window.CSRF_TOKEN ou cookie).
 */
import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'

function files(dir) {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) return files(p)
    return /\.(vue|js|ts)$/.test(name) ? [p] : []
  })
}

describe('CSRF (EV-0118)', () => {
  it('nenhum ficheiro lê o token de [name=csrfmiddlewaretoken] no DOM', () => {
    const src = resolve(__dirname, '../../src')
    const offenders = files(src).filter((f) => /querySelector\(\s*['"]\[name=csrfmiddlewaretoken\]['"]\s*\)/.test(readFileSync(f, 'utf8')))
    expect(offenders).toEqual([])
  })
})
