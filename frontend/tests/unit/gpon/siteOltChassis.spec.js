/**
 * EV-0113 — chassi de UMA OLT dentro do modal de Site: pede só essa OLT (?olt=), abre na
 * PON mais crítica, o inspetor mostra RX/LOS/diagnóstico sem «Ver no mapa» (já está no
 * mapa), seleção local e atualização a cada 60 s com limpeza ao desmontar.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { payload, ok } from './fixtures'

vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

import SiteOltChassis from '@/components/SiteDetails/SiteOltChassis.vue'

const oneOlt = () => {
  const p = payload()
  return { ...p, olts: [p.olts[0]], onus: p.onus.filter((o) => o.device_id === 22) }
}

function mockApi(body = oneOlt()) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    if (url.startsWith('/api/v1/monitoring/gpon/?')) return ok(body)
    return ok({ rx: [], traffic: { available: false }, zabbix_ok: true, events: [], hours: 24 })
  })
}

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('SiteOltChassis', () => {
  it('pede só a OLT, abre na PON mais crítica e não oferece «Ver no mapa»', async () => {
    const spy = mockApi()
    const w = mount(SiteOltChassis, { props: { deviceId: 22 } })
    await flushPromises()
    expect(spy.mock.calls[0][0]).toBe('/api/v1/monitoring/gpon/?olt=22')
    expect(w.get('[data-testid="insp-title"]').text()).toBe('PON 9/14')
    expect(w.get('[data-testid="insp-los"]').text()).toBe('3')
    expect(w.find('[data-testid="insp-map"]').exists()).toBe(false)
    expect(w.emitted('loaded')[0][0]).toMatchObject({ device_id: 22, cpu_pct: 12 })
    w.unmount()
  })

  it('erro na primeira carga é mostrado; Zabbix fora avisa que é a última coleta', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => Promise.resolve({ ok: false, status: 404, json: () => Promise.resolve({ detail: 'OLT 99 não encontrada' }) }))
    const w = mount(SiteOltChassis, { props: { deviceId: 99 } })
    await flushPromises()
    expect(w.find('[data-testid="site-olt-error"]').exists()).toBe(true)
    w.unmount()
    vi.restoreAllMocks()
    mockApi({ ...oneOlt(), zabbix_ok: false })
    const w2 = mount(SiteOltChassis, { props: { deviceId: 22 } })
    await flushPromises()
    expect(w2.find('[data-testid="site-olt-stale"]').exists()).toBe(true)
    w2.unmount()
  })

  it('EV-0121: a lista de ONUs por baixo segue a porta do chassi e abre a ficha na linha (sem modal)', async () => {
    mockApi()
    const w = mount(SiteOltChassis, { props: { deviceId: 22 }, attachTo: document.body })
    await flushPromises()
    const ids = () => w.findAll('[data-testid="gpon-onu-row"]').map((r) => r.attributes('data-onu-id'))
    expect(w.get('[data-testid="site-olt-onus"]').text()).toContain('PON 9/14 · 2 ONUs')
    expect(ids()).toEqual(['501', '502'])
    await w.get('[data-testid="chassis-port-9/15"]').trigger('click')
    expect(w.get('[data-testid="insp-title"]').text()).toBe('PON 9/15')
    expect(ids()).toEqual(['503', '504'])
    await w.findAll('[data-testid="gpon-onu-row"]')[0].trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="onu-detail-503"]').exists()).toBe(true)
    expect(document.body.querySelector('[data-testid="base-modal"]')).toBeNull()
    await w.get('[data-testid="insp-clear"]').trigger('click') // «Todas as portas»
    expect(w.get('[data-testid="site-olt-onus"]').text()).toContain('Todas as portas')
    expect(ids()).toHaveLength(6)
    w.unmount()
  })

  it('atualiza a cada 60 s e para ao desmontar', async () => {
    vi.useFakeTimers()
    const spy = mockApi()
    const w = mount(SiteOltChassis, { props: { deviceId: 22 } })
    await flushPromises()
    const gponCalls = () => spy.mock.calls.filter(([u]) => u.startsWith('/api/v1/monitoring/gpon/?')).length
    expect(gponCalls()).toBe(1)
    await vi.advanceTimersByTimeAsync(60_000)
    expect(gponCalls()).toBe(2)
    w.unmount()
    await vi.advanceTimersByTimeAsync(120_000)
    expect(gponCalls()).toBe(2)
  })
})
