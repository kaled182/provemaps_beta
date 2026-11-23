/**
 * EV-0068c — modais de Configuração e da manutenção no BaseModal: sem alert do
 * navegador, aviso de alterações, cores que seguem o tema (eram desenhos só-escuros).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import ContactEditModal from '@/components/Configuration/ContactEditModal.vue'
import BulkMessageModal from '@/components/Configuration/BulkMessageModal.vue'
import ContactImportModal from '@/components/Configuration/ContactImportModal.vue'
import BackupServiceSettingsModal from '@/components/Configuration/BackupServiceSettingsModal.vue'
import MaintenanceNotifyModal from '@/views/monitoring/components/MaintenanceNotifyModal.vue'

const read = (p) => readFileSync(resolve(__dirname, '../../src', p), 'utf8')
const q = (sel) => document.body.querySelector(sel)

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('ContactEditModal', () => {
  it('gravar sem nome/telefone mostra o erro no modal, sem alert', async () => {
    const alert = vi.spyOn(window, 'alert').mockImplementation(() => {})
    const w = mount(ContactEditModal, { props: { contact: null, groups: [] }, attachTo: document.body })
    await flushPromises()
    expect(q('.bm-title').textContent).toBe('Novo contato')
    q('#contact-edit-form').dispatchEvent(new Event('submit'))
    await flushPromises()
    expect(q('[data-testid="contact-form-error"]').textContent).toContain('obrigatórios')
    expect(alert).not.toHaveBeenCalled()
    expect(w.emitted('save')).toBeUndefined()
    w.unmount()
  })

  it('o botão do rodapé submete o formulário (form="contact-edit-form")', async () => {
    const w = mount(ContactEditModal, { props: { contact: null, groups: [] }, attachTo: document.body })
    await flushPromises()
    const submit = q('.bm-footer button[type="submit"]')
    expect(submit.getAttribute('form')).toBe('contact-edit-form')
    w.unmount()
  })

  it('fechar com alterações pede confirmação no rodapé', async () => {
    const w = mount(ContactEditModal, { props: { contact: { id: 1, name: 'Ana', phone: '+5562999' }, groups: [] }, attachTo: document.body })
    await flushPromises()
    const name = q('#contact-name')
    name.value = 'Ana Maria'
    name.dispatchEvent(new Event('input'))
    await flushPromises()
    q('[data-testid="base-modal-close"]').click()
    await flushPromises()
    expect(q('[data-testid="base-modal-discard"]')).not.toBeNull()
    expect(w.emitted('close')).toBeUndefined()
    w.unmount()
  })
})

describe('BulkMessageModal', () => {
  it('sem nada escrito fecha logo', async () => {
    const w = mount(BulkMessageModal, { props: { selectedContactIds: [], groups: [], gateways: [] }, attachTo: document.body })
    await flushPromises()
    q('[data-testid="base-modal-close"]').click()
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
  })
})

describe('montagem (apanha template inválido, não só o build)', () => {
  const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
  for (const [name, comp, props, title] of [
    ['ContactImportModal', ContactImportModal, {}, 'Importar contatos'],
    ['BackupServiceSettingsModal', BackupServiceSettingsModal, { open: true }, 'Serviços de backup'],
    ['MaintenanceNotifyModal', MaintenanceNotifyModal, { visible: true, cables: [], devices: [] }, 'Notificar responsáveis'],
  ]) {
    it(name, async () => {
      vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok({ results: [], users: [], contacts: [] }))
      vi.spyOn(console, 'error').mockImplementation(() => {})
      const w = mount(comp, { props, attachTo: document.body })
      await flushPromises()
      expect(q('.bm-title').textContent).toBe(title)
      w.unmount()
    })
  }
})

describe('código dos modais de Configuração e manutenção (EV-0068c)', () => {
  const files = [
    'components/Configuration/ContactEditModal.vue',
    'components/Configuration/ContactImportModal.vue',
    'components/Configuration/BulkMessageModal.vue',
    'components/Configuration/BackupServiceSettingsModal.vue',
    'views/monitoring/components/MaintenanceNotifyModal.vue',
  ]
  for (const p of files) {
    it(`${p}: BaseModal, sem alert/confirm, sem branco translúcido de desenho só-escuro`, () => {
      const sfc = read(p)
      const css = sfc.slice(sfc.indexOf('<style'))
      expect(sfc).toContain('<BaseModal')
      expect(sfc).not.toMatch(/\balert\(|\bconfirm\(/)
      expect(css).not.toMatch(/rgba\(255,\s*255,\s*255|rgba\(15,\s*23,\s*42|:root\[data-theme="light"\]/)
    })
  }

  it('a notificação de manutenção mantém a camada acima do mapa (9200)', () => {
    expect(read('views/monitoring/components/MaintenanceNotifyModal.vue')).toMatch(/:z-index="9200"/)
  })
})
