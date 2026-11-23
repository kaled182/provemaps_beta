/**
 * EV-0068b — modais do inventário no BaseModal: sem moldura roxa, sem `dark:` literais,
 * validação no próprio modal (sem alert do navegador), aviso de alterações por guardar.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import FiberConnectionModal from '@/components/Inventory/Fiber/FiberConnectionModal.vue'
import FiberCreateModal from '@/components/Inventory/Fiber/FiberCreateModal.vue'
import CableStructureModal from '@/components/Inventory/Fibers/CableStructureModal.vue'
import DeviceGroupEditModal from '@/components/Inventory/Groups/DeviceGroupEditModal.vue'

const read = (p) => readFileSync(resolve(__dirname, '../../src/components', p), 'utf8')
const q = (sel) => document.body.querySelector(sel)
const SITES = [{ id: 1, name: 'BRV' }, { id: 2, name: 'PLANURA' }]

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

const select = async (el, value) => {
  el.value = String(value)
  el.dispatchEvent(new Event('change'))
  await flushPromises()
}

describe('FiberConnectionModal', () => {
  it('mesmo site nas duas pontas não grava; mudar e fechar pede confirmação no rodapé', async () => {
    const confirm = vi.spyOn(window, 'confirm')
    const w = mount(FiberConnectionModal, { props: { show: true, cable: { id: 5, name: 'BRV - PLANURA' }, sites: SITES }, attachTo: document.body })
    await flushPromises()
    expect(q('.bm-subtitle').textContent).toBe('BRV - PLANURA')
    const [a, b] = document.body.querySelectorAll('select')
    await select(a, 1)
    await select(b, 1)
    const save = [...document.body.querySelectorAll('.bm-footer button')].find((x) => x.textContent.includes('Salvar Rota'))
    expect(save.disabled).toBe(true)
    q('[data-testid="base-modal-close"]').click()
    await flushPromises()
    expect(q('[data-testid="base-modal-discard"]')).not.toBeNull()
    expect(w.emitted('close')).toBeUndefined()
    expect(confirm).not.toHaveBeenCalled()
    w.unmount()
  })
})

describe('FiberCreateModal', () => {
  it('falha a carregar perfis aparece no modal, sem alert', async () => {
    const alert = vi.spyOn(window, 'alert').mockImplementation(() => {})
    vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve({ ok: false, status: 500, statusText: 'Server Error', json: () => Promise.resolve({ detail: 'boom' }) }),
    )
    const w = mount(FiberCreateModal, { props: { show: true, cable: null }, attachTo: document.body })
    await flushPromises()
    expect(q('[data-testid="profiles-error"]')).not.toBeNull()
    expect(alert).not.toHaveBeenCalled()
    w.unmount()
  })
})

describe('CableStructureModal', () => {
  it('sem fibra escolhida os botões ficam desativados, com dica (sem alert)', async () => {
    const w = mount(CableStructureModal, {
      props: { show: true, cableId: 7 },
      attachTo: document.body,
      global: { stubs: { CableStructureView: true } },
    })
    await flushPromises()
    expect(q('[data-testid="fiber-hint"]')).not.toBeNull()
    const fusion = [...document.body.querySelectorAll('.bm-footer button')].find((x) => x.textContent.includes('Criar Fusão'))
    expect(fusion.disabled).toBe(true)
    w.unmount()
  })
})

describe('DeviceGroupEditModal', () => {
  it('sem nome não grava e avisa no rodapé', async () => {
    const w = mount(DeviceGroupEditModal, { props: { show: true, group: null, allDevices: [] }, attachTo: document.body })
    await flushPromises()
    expect(q('[data-testid="group-name-required"]')).not.toBeNull()
    const save = [...document.body.querySelectorAll('.bm-footer button')].find((x) => x.textContent.includes('Salvar Grupo'))
    expect(save.disabled).toBe(true)
    w.unmount()
  })
})

describe('código dos modais do inventário (EV-0068b)', () => {
  const files = [
    'Inventory/Fiber/FiberConnectionModal.vue',
    'Inventory/Fiber/FiberCreateModal.vue',
    'Inventory/Fibers/CableStructureModal.vue',
    'Inventory/Groups/DeviceGroupEditModal.vue',
    'DeviceImport/DeviceEditModal.vue',
  ]
  for (const p of files) {
    it(`${p}: BaseModal, sem alert/confirm, sem gradiente roxo nem dark: no template`, () => {
      const sfc = read(p)
      const tpl = sfc.slice(0, sfc.indexOf('<script'))
      expect(sfc).toContain('<BaseModal')
      expect(sfc).not.toMatch(/\balert\(|\bconfirm\(/)
      expect(tpl).not.toMatch(/from-(purple|indigo)|dark:/)
    })
  }

  it('DeviceEditModal: os 4 sub-modais também são BaseModal, por cima do principal', () => {
    const sfc = read('DeviceImport/DeviceEditModal.vue')
    for (const show of ['showMapPicker', 'syncModal', 'syncResult.open', 'showInterfacesModal']) {
      const m = sfc.match(new RegExp(`<BaseModal\\s+:show="${show.replace('.', '\\.')}"([\\s\\S]*?)\\n  >`))
      expect(m, show).not.toBeNull()
      expect(Number(m[1].match(/:z-index="(\d+)"/)[1]), show).toBeGreaterThan(3000)
    }
    expect(sfc).toContain('data-testid="device-form-error"')
  })

  it('FiberCableQuickModal (janela flutuante, fica sem BaseModal): sem azul-marinho fixo', () => {
    const css = read('FiberCableQuickModal.vue').split('<style')[1]
    expect(css).not.toMatch(/#1e293b|#0f172a|rgba\(15, 23, 42|rgba\(30, 41, 59/)
  })
})
