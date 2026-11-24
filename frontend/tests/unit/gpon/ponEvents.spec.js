/**
 * EV-0108 — aba «Eventos recentes 24 h» da PON: pedido certo, etiquetas por tipo,
 * «registo desde», vazio e erro; abas só com PON selecionada e voltam às ONUs ao trocar.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PonEvents from '@/components/Gpon/PonEvents.vue'
import OnuTable from '@/components/Gpon/OnuTable.vue'

const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
const BODY = {
  device_id: 22,
  pon_id: '9/14',
  hours: 24,
  since: '2026-11-24T10:00:00Z',
  truncated: false,
  events: [
    { at: '2026-11-24T12:10:00Z', onu_id: 1, onu_index: 2, serial: 'ZTEG00000001', mac: null, cliente_nome: 'João', kind: 'los', label: 'LOS', previous_kind: 'online' },
    { at: '2026-11-24T11:00:00Z', onu_id: 2, onu_index: 3, serial: null, mac: 'aa:bb:cc:00:00:01', cliente_nome: null, kind: 'online', label: null, previous_kind: 'dying_gasp' },
  ],
}

afterEach(() => vi.restoreAllMocks())

describe('PonEvents', () => {
  it('pede os eventos da PON e mostra tipo, ONU e estado anterior', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(BODY))
    const w = mount(PonEvents, { props: { deviceId: 22, ponId: '9/14' } })
    await flushPromises()
    expect(fetchSpy.mock.calls[0][0]).toBe('/api/v1/monitoring/gpon/events/?device=22&pon=9%2F14&hours=24')
    const rows = w.findAll('[data-testid="pon-event-row"]')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('Queda — LOS')
    expect(rows[0].text()).toContain('ZTEG00000001')
    expect(rows[0].text()).toContain('Online')
    expect(rows[1].text()).toContain('Reconexão')
    expect(rows[1].text()).toContain('aa:bb:cc:00:00:01')
    expect(w.get('[data-testid="pon-events-since"]').text()).toMatch(/^Registo de eventos desde/)
  })

  it('recarrega quando há nova coleta', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(BODY))
    const w = mount(PonEvents, { props: { deviceId: 22, ponId: '9/14', refreshKey: 'a' } })
    await flushPromises()
    await w.setProps({ refreshKey: 'b' })
    await flushPromises()
    expect(fetchSpy).toHaveBeenCalledTimes(2)
  })

  it('sem eventos e sem registo diz isso; erro aparece como erro', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok({ ...BODY, since: null, events: [] }))
    const w = mount(PonEvents, { props: { deviceId: 22, ponId: '9/14' } })
    await flushPromises()
    expect(w.get('[data-testid="pon-events-empty"]').text()).toContain('Nenhum evento nesta porta nas últimas 24 h')
    expect(w.get('[data-testid="pon-events-since"]').text()).toContain('ainda não tem dados')
    vi.restoreAllMocks()
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve({ ok: false, status: 500, statusText: 'x', json: () => Promise.resolve({ error: 'falhou' }) }),
    )
    const e = mount(PonEvents, { props: { deviceId: 22, ponId: '9/15' } })
    await flushPromises()
    expect(e.find('[data-testid="pon-events-error"]').exists()).toBe(true)
  })
})

describe('OnuTable — abas (EV-0108)', () => {
  it('sem PON selecionada não há abas; com PON alterna e volta às ONUs ao trocar de PON', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(BODY))
    const w = mount(OnuTable, { props: { onus: [], scope: 'ONUs com problema' } })
    expect(w.find('[data-testid="gpon-onu-tabs"]').exists()).toBe(false)
    await w.setProps({ eventsFor: { deviceId: 22, ponId: '9/14' }, scope: 'PON 9/14' })
    expect(w.get('[data-testid="gpon-tab-onus"]').text()).toContain('PON 9/14')
    await w.get('[data-testid="gpon-tab-events"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="pon-events"]').exists()).toBe(true)
    await w.setProps({ eventsFor: { deviceId: 22, ponId: '9/15' } })
    expect(w.find('[data-testid="pon-events"]').exists()).toBe(false)
    expect(w.get('[data-testid="gpon-tab-onus"]').attributes('aria-selected')).toBe('true')
  })
})
