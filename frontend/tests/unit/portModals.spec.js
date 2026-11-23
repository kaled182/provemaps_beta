/**
 * EV-0068a — modais de porta no BaseModal. O PortActionsModal só faz o que o backend
 * faz (descrição em `notes`); sem «Resetar»/«Logs» sem endpoint nem log inventado.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import PortActionsModal from '@/components/PortActionsModal.vue'
import AlarmConfigModal from '@/components/AlarmConfigModal.vue'
import ConnectivityMapModal from '@/components/ConnectivityMapModal.vue'

const read = (p) => readFileSync(resolve(__dirname, '../../src/components', p), 'utf8')
const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
const q = (sel) => document.body.querySelector(sel)
const PORT = { id: 42, name: 'gpon 1/1/1', notes: 'uplink BRV', optical_rx_power: -20, optical_tx_power: 2 }

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('PortActionsModal', () => {
  it('grava a descrição em `notes` e só fica ativo com alterações', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok({ id: 42 }))
    const w = mount(PortActionsModal, { props: { isOpen: true, port: PORT }, attachTo: document.body })
    await flushPromises()
    expect(q('.bm-title').textContent).toContain('gpon 1/1/1')
    const ta = q('[data-testid="port-notes"]')
    expect(ta.value).toBe('uplink BRV')
    expect(q('[data-testid="port-notes-save"]').disabled).toBe(true)
    ta.value = 'uplink BRV-2'
    ta.dispatchEvent(new Event('input'))
    await flushPromises()
    q('[data-testid="port-notes-save"]').click()
    await flushPromises()
    const [url, init] = fetchSpy.mock.calls.at(-1)
    expect(url).toBe('/api/v1/ports/42/')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body)).toEqual({ notes: 'uplink BRV-2' })
    expect(w.emitted('refresh')).toHaveLength(1)
    w.unmount()
  })

  it('fechar com alterações pede confirmação no rodapé, sem window.confirm', async () => {
    const confirm = vi.spyOn(window, 'confirm')
    const w = mount(PortActionsModal, { props: { isOpen: true, port: PORT }, attachTo: document.body })
    await flushPromises()
    const ta = q('[data-testid="port-notes"]')
    ta.value = 'outra'
    ta.dispatchEvent(new Event('input'))
    await flushPromises()
    q('[data-testid="base-modal-close"]').click()
    await flushPromises()
    expect(q('[data-testid="base-modal-discard"]')).not.toBeNull()
    expect(w.emitted('close')).toBeUndefined()
    expect(confirm).not.toHaveBeenCalled()
    w.unmount()
  })

  it('sem «Resetar porta» nem «Logs» (não há endpoint) e sem log inventado', () => {
    const sfc = read('PortActionsModal.vue')
    expect(sfc).not.toMatch(/\/reset\/|\/logs\/|em desenvolvimento|confirm\(/)
  })
})

describe('AlarmConfigModal', () => {
  it('no BaseModal; aviso de alterações só depois de mexer', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) =>
      url.startsWith('/setup_app/api/config/')
        ? ok({ success: true, configuration: { OPTICAL_RX_WARNING_THRESHOLD: '-24', OPTICAL_RX_CRITICAL_THRESHOLD: '-27' } })
        : ok([]),
    )
    const w = mount(AlarmConfigModal, { props: { isOpen: false, port: PORT }, attachTo: document.body })
    await w.setProps({ isOpen: true })
    await flushPromises()
    expect(q('.bm-title').textContent).toContain('gpon 1/1/1')
    q('[data-testid="base-modal-close"]').click()
    await flushPromises()
    expect(w.emitted('close')).toHaveLength(1) // nada mudou → fecha logo
    w.unmount()
  })
})

describe('ConnectivityMapModal', () => {
  it('no BaseModal', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok({}))
    const w = mount(ConnectivityMapModal, {
      props: { isOpen: true, port: PORT, deviceInfo: { name: 'OLT', ip: '10.0.0.1' } },
      attachTo: document.body,
    })
    await flushPromises()
    expect(q('.bm-title').textContent).toContain('gpon 1/1/1')
    w.unmount()
  })
})

describe('sem moldura antiga nem window.confirm (EV-0068a)', () => {
  for (const p of ['PortActionsModal.vue', 'AlarmConfigModal.vue', 'ConnectivityMapModal.vue', 'PortTrafficModal.vue']) {
    it(p, () => {
      const sfc = read(p)
      expect(sfc).toContain('<BaseModal')
      expect(sfc).not.toMatch(/#667eea|#764ba2|-modal-overlay|useEscapeKey|window\.confirm/)
    })
  }
})
