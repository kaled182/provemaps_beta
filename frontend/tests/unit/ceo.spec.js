/**
 * EV-0135 — CEO no traçado: inserir (nome, modo, reserva, bandejas) e derivar cabo a partir dela
 * (traçado desenhado no mapa a começar na CEO, destino site/porta ou outra CEO).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CeoCreateModal from '@/components/Ceo/CeoCreateModal.vue'
import CeoDerivePanel from '@/components/Ceo/CeoDerivePanel.vue'
import CeoCard from '@/components/Ceo/CeoCard.vue'
import CeoFusionsModal from '@/components/Ceo/CeoFusionsModal.vue'
import FiberTrace from '@/components/Inventory/Fibers/FiberTrace.vue'

const ok = (body, status = 200) => Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) })
const CEO = { id: 4, name: 'CEO-04', cable_id: 1, cable_name: 'MANDI - VLP', point: [-50, 0.045], km: 4.976, mode: 'sangria', mode_label: 'Sangria (passagem direta)', slack_m: 20, trays: 2, derived: [] }

function fakeMap() {
  const handlers = {}
  return {
    handlers,
    on: vi.fn((e, cb) => (handlers[e] ||= []).push(cb)),
    off: vi.fn((e, cb) => (handlers[e] = (handlers[e] || []).filter((h) => h !== cb))),
    fire(e, pl) {
      ;(handlers[e] || []).forEach((cb) => cb(pl))
    },
    createPolyline: vi.fn((opts) => ({ opts, setPath: vi.fn(), remove: vi.fn() })),
    createMarker: vi.fn((opts) => ({ position: { ...opts.position }, on: vi.fn(), getPosition() { return this.position }, setStyle: vi.fn(), remove: vi.fn() })),
    fitBounds: vi.fn(),
  }
}

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('CeoCreateModal', () => {
  it('envia o ponto do clique, o nome, o modo corte, a reserva e as bandejas', async () => {
    const calls = []
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, o = {}) => {
      calls.push([url, JSON.parse(o.body)])
      return ok({ ...CEO, mode: 'corte' }, 201)
    })
    const w = mount(CeoCreateModal, { props: { show: true, cable: { id: 1, name: 'MANDI - VLP' }, point: { lat: 0.045, lng: -49.99 } }, attachTo: document.body })
    await flushPromises()
    const q = (s) => document.body.querySelector(s)
    q('[data-testid="ceo-name"]').value = 'CEO-04'
    q('[data-testid="ceo-name"]').dispatchEvent(new Event('input'))
    q('[data-testid="ceo-mode-corte"]').click()
    q('[data-testid="ceo-slack"]').value = '20'
    q('[data-testid="ceo-slack"]').dispatchEvent(new Event('input'))
    q('[data-testid="ceo-trays"]').value = '4'
    q('[data-testid="ceo-trays"]').dispatchEvent(new Event('input'))
    await flushPromises()
    q('[data-testid="ceo-save"]').click()
    await flushPromises()
    expect(calls).toEqual([['/api/v1/inventory/ceos/', { cable_id: 1, lat: 0.045, lng: -49.99, name: 'CEO-04', mode: 'corte', slack_m: 20, trays: 4 }]])
    expect(w.emitted('created')[0][0].mode).toBe('corte')
    w.unmount()
  })
})

describe('CeoCard', () => {
  it('mostra km, modo, reserva e derivados; «Derivar cabo» emite a CEO', async () => {
    const w = mount(CeoCard, { props: { ceo: { ...CEO, derived: [{ id: 9, name: 'CEO-04 - VILA NOVA' }] } } })
    expect(w.text()).toContain('km 4,976')
    expect(w.get('[data-testid="ceo-card-mode"]').text()).toBe('Sangria (passagem direta)')
    expect(w.get('[data-testid="ceo-card-derived"]').text()).toBe('CEO-04 - VILA NOVA')
    await w.get('[data-testid="ceo-derive"]').trigger('click')
    expect(w.emitted('derive')[0][0].id).toBe(4)
  })
})

describe('CeoDerivePanel', () => {
  it('o traçado começa na CEO, cresce com cliques no mapa e o cabo vai para o site/porta escolhidos', async () => {
    const posts = []
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, o = {}) => {
      if (o.method === 'POST') {
        posts.push([url, JSON.parse(o.body)])
        return ok({ id: 30, name: 'CEO-04 - VILA NOVA', length_km: 5.5, needs_profile: false }, 201)
      }
      if (String(url).includes('cable-groups')) return ok({ results: [{ id: 1, name: '12-FO' }] })
      return ok({ site_id: 7, site_name: 'VILA NOVA', devices: [{ id: 3, name: 'SW', ports: [{ id: 11, name: 'ge-1', used_by: null }, { id: 12, name: 'ge-2', used_by: { strand_id: 5, absolute_number: 2, cable_name: 'X', end: 'b' } }] }] })
    })
    const map = fakeMap()
    const w = mount(CeoDerivePanel, { props: { map, ceo: CEO, ceos: [CEO], sites: [{ id: 7, name: 'VILA NOVA' }] } })
    await flushPromises()
    expect(w.get('[data-testid="derive-length"]').text()).toContain('1 pontos')
    map.fire('click', { lat: 0.045, lng: -49.97 })
    map.fire('click', { lat: 0.045, lng: -49.95 })
    await flushPromises()
    expect(w.get('[data-testid="derive-length"]').text()).toContain('3 pontos')
    await w.get('[data-testid="derive-name"]').setValue('CEO-04 - VILA NOVA')
    await w.get('[data-testid="derive-group"]').setValue('1')
    await w.get('[data-testid="derive-site"]').setValue('7')
    await flushPromises()
    expect(w.get('[data-testid="derive-port"]').findAll('option').find((o) => o.text().startsWith('ge-2')).attributes('disabled')).toBeDefined()
    await w.get('[data-testid="derive-port"]').setValue('11')
    await w.get('[data-testid="derive-save"]').trigger('click')
    await flushPromises()
    expect(posts).toEqual([
      [
        '/api/v1/inventory/ceos/4/derive/',
        {
          name: 'CEO-04 - VILA NOVA',
          path: [{ lat: 0.045, lng: -50 }, { lat: 0.045, lng: -49.97 }, { lat: 0.045, lng: -49.95 }],
          cable_group_id: 1,
          to_site_id: 7,
          to_port_id: 11,
          to_ceo_id: null,
        },
      ],
    ])
    expect(w.emitted('created')[0][0].id).toBe(30)
    w.unmount()
    expect(map.handlers.click).toHaveLength(0) // o desenho sai do mapa ao fechar
  })
})

const end = (strand, side, cable, n, toward, fusion = null) => ({ key: `${strand}:${side}`, strand_id: strand, side, cable_id: cable === 'MANDI - VLP' ? 1 : 2, cable_name: cable, tube_number: 1, tube_color: 'Verde', number: n, absolute_number: n, color: 'Verde', color_hex: '#009900', toward, fusion_id: fusion })
const FUSIONS = {
  ceo: { id: 4, name: 'CEO-04', mode: 'sangria', trays: 2, splices_per_tray: 24 },
  cables: [
    { id: 1, name: 'MANDI - VLP', role: 'tronco', ends: [end(101, 'a', 'MANDI - VLP', 1, 'SITE - VILA MANDI'), end(101, 'b', 'MANDI - VLP', 1, 'SITE - VILA RICA'), end(102, 'a', 'MANDI - VLP', 2, 'SITE - VILA MANDI', 9)] },
    { id: 2, name: 'CEO-04 - VILA NOVA', role: 'derivado', ends: [end(201, 'b', 'CEO-04 - VILA NOVA', 1, 'SITE - VILA NOVA')] },
  ],
  fusions: [{ id: 9, tray: 1, slot: 1, a: end(102, 'a', 'MANDI - VLP', 2, 'SITE - VILA MANDI'), b: end(202, 'b', 'CEO-04 - VILA NOVA', 2, 'SITE - VILA NOVA') }],
}

describe('CeoFusionsModal (EV-0136)', () => {
  it('escolhe fibra A e B (pontas emendadas desativadas), cria a fusão com bandeja/posição e desfaz', async () => {
    const calls = []
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, o = {}) => {
      calls.push([url, o.method || 'GET', o.body ? JSON.parse(o.body) : null])
      return o.method === 'DELETE' ? Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) }) : ok(o.method === 'POST' ? { id: 10 } : FUSIONS)
    })
    const w = mount(CeoFusionsModal, { props: { show: true, ceo: CEO }, attachTo: document.body })
    await flushPromises()
    const q = (sel) => document.body.querySelector(sel)
    expect(q('[data-testid="end-102:a"]').disabled).toBe(true)
    q('[data-testid="end-101:a"]').click()
    q('[data-testid="end-201:b"]').click()
    await flushPromises()
    expect(q('[data-testid="fusion-pick-b"]').textContent).toContain('CEO-04 - VILA NOVA · F1 (Verde) → SITE - VILA NOVA')
    q('[data-testid="fusion-tray"]').value = '1'
    q('[data-testid="fusion-tray"]').dispatchEvent(new Event('input'))
    q('[data-testid="fusion-slot"]').value = '2'
    q('[data-testid="fusion-slot"]').dispatchEvent(new Event('input'))
    await flushPromises()
    q('[data-testid="fusion-create"]').click()
    await flushPromises()
    q('[data-testid="fusion-del-9"]').click()
    await flushPromises()
    const writes = calls.filter(([, m]) => m !== 'GET')
    expect(writes).toEqual([
      ['/api/v1/inventory/ceos/4/fusions/', 'POST', { a: { strand_id: 101, side: 'a' }, b: { strand_id: 201, side: 'b' }, tray: 1, slot: 2 }],
      ['/api/v1/inventory/ceos/4/fusions/9/', 'DELETE', null],
    ])
    w.unmount()
  })
})

describe('FiberTrace (EV-0136)', () => {
  it('mostra porta → cabo → fusão → cabo → porta, o fim e a perda marcada como cálculo', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      ok({
        steps: [
          { type: 'port', device_name: 'OLT Mandi', port_name: 'gpon 1/1/1', site_name: 'SITE - VILA MANDI' },
          { type: 'cable', cable_name: 'MANDI - VLP', absolute_number: 1, color: 'Verde', color_hex: '#009900', toward: 'SITE - VILA RICA', km: 4.976, passes: [] },
          { type: 'fusion', ceo_name: 'CEO-04', tray: 1, slot: 1 },
          { type: 'cable', cable_name: 'CEO-04 - VILA NOVA', absolute_number: 1, color: 'Verde', color_hex: '#009900', toward: 'SITE - VILA NOVA', km: 5.56, passes: [] },
          { type: 'port', device_name: 'SW Vila Nova', port_name: 'ge-0/0/1', site_name: 'SITE - VILA NOVA' },
        ],
        end: { reason: 'port', label: 'SW Vila Nova → ge-0/0/1' },
        total_km: 10.536,
        fusions: 1,
        loss_db_estimate: 3.79,
      }),
    )
    const w = mount(FiberTrace, { props: { strandId: 101, start: 'a' } })
    await flushPromises()
    expect(globalThis.fetch.mock.calls[0][0]).toBe('/api/v1/inventory/strands/101/trace/?from=a')
    expect(w.findAll('[data-testid="trace-step-cable"]')).toHaveLength(2)
    expect(w.get('[data-testid="trace-step-fusion"]').text()).toContain('CEO-04')
    expect(w.get('[data-testid="trace-end"]').text()).toBe('Chega a: SW Vila Nova → ge-0/0/1')
    expect(w.get('[data-testid="trace-total"]').text().replace(/\s+/g, ' ')).toContain('10,54 km · 1 fusão · perda estimada 3,79 dB')
  })
})

