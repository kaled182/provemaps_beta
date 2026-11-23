/**
 * EV-0064 — BaseModal: cabeçalho compacto, tamanhos, e aviso de alterações por
 * guardar no rodapé em vez de window.confirm (Esc, clique fora e X).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { PhHardDrives } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
  document.body.style.overflow = ''
})

function open(props = {}, slots = {}) {
  return mount(BaseModal, {
    props: { show: true, title: 'SITE - FURACÃO', ...props },
    slots: { default: '<p data-testid="corpo">conteúdo</p>', ...slots },
    attachTo: document.body,
  })
}
const $ = (sel) => document.querySelector(sel)

describe('BaseModal', () => {
  it('cabeçalho numa linha com ícone na cor do estado, título e subtítulo', async () => {
    const w = open({ subtitle: '-16.6, -49.2', icon: PhHardDrives, status: 'online' })
    await nextTick()
    expect($('[role="dialog"]').getAttribute('aria-labelledby')).toBe($('.bm-title').id)
    expect($('.bm-title').textContent).toBe('SITE - FURACÃO')
    expect($('.bm-subtitle').textContent).toBe('-16.6, -49.2')
    expect($('.bm-icon').classList.contains('bm-icon-online')).toBe(true)
    expect($('.bm-panel').classList.contains('bm-detail')).toBe(true)
    expect($('[data-testid="corpo"]')).not.toBeNull()
    w.unmount()
  })

  it('sem alterações: X, Esc e clique fora fecham', async () => {
    const w = open()
    await nextTick()
    $('[data-testid="base-modal-close"]').click()
    $('[role="dialog"]').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    $('[data-testid="base-modal"]').dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    expect(w.emitted('close')).toHaveLength(3)
    w.unmount()
  })

  it('com alterações: não usa window.confirm, mostra aviso no rodapé', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm')
    const w = open({ dirty: true }, { footer: '<button data-testid="salvar">Salvar</button>' })
    await nextTick()
    $('[data-testid="base-modal-close"]').click()
    await nextTick()
    expect(confirmSpy).not.toHaveBeenCalled()
    expect(w.emitted('close')).toBeUndefined()
    expect($('[data-testid="base-modal-discard"]')).not.toBeNull()
    expect($('[data-testid="salvar"]')).toBeNull() // o aviso ocupa o rodapé

    $('[data-testid="base-modal-keep"]').click()
    await nextTick()
    expect($('[data-testid="base-modal-discard"]')).toBeNull()
    expect($('[data-testid="salvar"]')).not.toBeNull()

    $('[role="dialog"]').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await nextTick()
    $('[data-testid="base-modal-discard-confirm"]').click()
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
  })

  it('bloqueia o scroll da página enquanto aberto', async () => {
    const w = open()
    await nextTick()
    expect(document.body.style.overflow).toBe('hidden')
    await w.setProps({ show: false })
    expect(document.body.style.overflow).toBe('')
    w.unmount()
  })

  it('sem cores fixas: superfície e bordas por tokens', () => {
    const css = readFileSync(resolve(__dirname, '../../src/components/Common/BaseModal.vue'), 'utf8').split('<style')[1]
    expect(css).not.toMatch(/#[0-9a-f]{3,6}\b/i)
    expect(css).toMatch(/background: rgb\(var\(--surface\)\)/)
    expect(css).toMatch(/max-width: 64rem/)
  })
})

describe('popup do cabo no mapa (EV-0064)', () => {
  const css = readFileSync(resolve(__dirname, '../../src/components/CableOpticalTooltip.vue'), 'utf8').split('<style')[1]

  it('320 px, superfície por tokens, sem o azul-marinho antigo', () => {
    expect(css).toMatch(/width: min\(320px/)
    expect(css).toMatch(/background: rgb\(var\(--surface\)\)/)
    expect(css).not.toMatch(/#1e293b|#0f172a|rgba\(99,\s*102,\s*241/i)
  })

  it('níveis em mono e coloridos por semântica', () => {
    expect(css).toMatch(/\.level-value \{[^}]*JetBrains Mono/)
    expect(css).toMatch(/\.level-critical \{ color: rgb\(var\(--danger\)\)/)
  })
})
