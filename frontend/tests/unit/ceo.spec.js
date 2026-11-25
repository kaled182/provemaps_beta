/**
 * EV-0135 — CEO no traçado: inserir (nome, modo, reserva, bandejas) e derivar cabo a partir dela
 * (traçado desenhado no mapa a começar na CEO, destino site/porta ou outra CEO).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import CeoCreateModal from '@/components/Ceo/CeoCreateModal.vue'
import CeoDerivePanel from '@/components/Ceo/CeoDerivePanel.vue'
import CeoCard from '@/components/Ceo/CeoCard.vue'
import SpliceBoxModal from '@/components/Ceo/SpliceBoxModal.vue'
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
  it('só leitura (EV-0137): km, modo, reserva e derivados; «Ver emendas» emite a CEO; «Editar no Projeto ↗» focado na CEO', async () => {
    const w = mount(CeoCard, { props: { ceo: { ...CEO, derived: [{ id: 9, name: 'CEO-04 - VILA NOVA' }] } }, global: { stubs: { RouterLink: RouterLinkStub } } })
    expect(w.text()).toContain('km 4,976')
    expect(w.get('[data-testid="ceo-card-mode"]').text()).toBe('Sangria (passagem direta)')
    expect(w.get('[data-testid="ceo-card-derived"]').text()).toBe('CEO-04 - VILA NOVA')
    expect(w.find('[data-testid="ceo-derive"]').exists()).toBe(false)
    expect(w.getComponent(RouterLinkStub).props('to')).toEqual({ path: '/Network/NetworkDesign/', query: { foco: 'ceo', id: '4', lat: '0.045', lng: '-50', nome: 'CEO-04' } })
    await w.get('[data-testid="ceo-fusions"]').trigger('click')
    expect(w.emitted('fusions')[0][0].id).toBe(4)
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

const end = (strand, side, cable, n, toward, fusion = null) => ({ key: `${strand}:${side}`, strand_id: strand, side, cable_id: cable === 'MANDI - VLP' ? 1 : 2, cable_name: cable, tube_number: 1, tube_color: 'Verde', tube_color_hex: '#009900', number: n, absolute_number: n, color: 'Verde', color_hex: '#009900', toward, fusion_id: fusion })
const FUSIONS = {
  ceo: { id: 4, name: 'CEO-04', mode: 'sangria', trays: 2, splices_per_tray: 24 },
  cables: [
    { id: 1, name: 'MANDI - VLP', role: 'tronco', ends: [end(101, 'a', 'MANDI - VLP', 1, 'SITE - VILA MANDI'), end(101, 'b', 'MANDI - VLP', 1, 'SITE - VILA RICA'), end(102, 'a', 'MANDI - VLP', 2, 'SITE - VILA MANDI', 9)] },
    { id: 2, name: 'CEO-04 - VILA NOVA', role: 'derivado', ends: [end(201, 'b', 'CEO-04 - VILA NOVA', 1, 'SITE - VILA NOVA')] },
  ],
  fusions: [{ id: 9, tray: 1, slot: 1, a: end(102, 'a', 'MANDI - VLP', 2, 'SITE - VILA MANDI'), b: end(202, 'b', 'CEO-04 - VILA NOVA', 2, 'SITE - VILA NOVA') }],
}

describe('SpliceBoxModal (EV-0141)', () => {
  function mountBox(extra = {}) {
    const calls = []
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, o = {}) => {
      calls.push([url, o.method || 'GET', o.body ? JSON.parse(o.body) : null])
      if (o.method === 'DELETE') return Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
      if (o.method === 'POST') return ok(String(url).endsWith('/tube/') ? { created: 11, skipped: 1 } : { id: 10 })
      return ok(FUSIONS)
    })
    const w = mount(SpliceBoxModal, { props: { show: true, ceo: CEO, ...extra }, attachTo: document.body, global: { stubs: { RouterLink: RouterLinkStub } } })
    return { w, calls, q: (sel) => document.body.querySelector(sel) }
  }

  it('3 colunas: lado A à esquerda, B à direita, fusões na bandeja; o tubo mostra a ocupação', async () => {
    const { w, q } = mountBox()
    await flushPromises()
    expect(q('[data-testid="splice-side-a"]').textContent).toContain('MANDI - VLP')
    expect(q('[data-testid="splice-side-b"]').textContent).toContain('CEO-04 - VILA NOVA')
    expect(q('[data-testid="tube-badge-1-a-1"]').textContent.trim()).toBe('1/2') // fibra 2 (lado A) está emendada
    expect(q('[data-testid="splice-tray"]').textContent).toContain('Bandeja 1')
    expect(q('[data-testid="fiber-102:a"]').disabled).toBe(true)
    expect(q('[data-testid="fiber-102:a"]').textContent).toContain('↔ CEO-04 - VILA NOVA · F2')
    w.unmount()
  })

  it('dois cliques criam a fusão (posição automática); «1:1» + «Fundir aqui» funde o tubo; «Desfazer» apaga', async () => {
    const { w, calls, q } = mountBox()
    await flushPromises()
    q('[data-testid="fiber-101:a"]').click()
    await flushPromises()
    expect(q('[data-testid="splice-help"]').textContent).toContain('MANDI - VLP · fibra 1')
    q('[data-testid="fiber-201:b"]').click()
    await flushPromises()
    q('[data-testid="tube-11-1-a-1"]').click()
    await flushPromises()
    q('[data-testid="tube-target-2-b-1"]').click()
    await flushPromises()
    expect(q('[data-testid="splice-notice"]').textContent).toContain('11 fusões criadas · 1 fibra(s)')
    q('[data-testid="fusion-del-9"]').click()
    await flushPromises()
    expect(calls.filter(([, m]) => m !== 'GET')).toEqual([
      ['/api/v1/inventory/ceos/4/fusions/', 'POST', { a: { strand_id: 101, side: 'a' }, b: { strand_id: 201, side: 'b' } }],
      ['/api/v1/inventory/ceos/4/fusions/tube/', 'POST', { a: { cable_id: 1, tube_number: 1, side: 'a' }, b: { cable_id: 2, tube_number: 1, side: 'b' } }],
      ['/api/v1/inventory/ceos/4/fusions/9/', 'DELETE', null],
    ])
    w.unmount()
  })

  it('só leitura (monitoramento): sem cliques de fusão, sem «1:1» nem «Desfazer»; com «Rastrear» e «Editar no Projeto ↗»', async () => {
    const { w, q } = mountBox({ readonly: true })
    await flushPromises()
    expect(q('[data-testid="fiber-101:a"]').disabled).toBe(true)
    expect(q('[data-testid="tube-11-1-a-1"]')).toBeNull()
    expect(q('[data-testid="fusion-del-9"]')).toBeNull()
    expect(q('[data-testid="fusion-trace-9"]')).not.toBeNull()
    expect(q('[data-testid="splice-help"]')).toBeNull()
    w.unmount()
  })
})

describe('Splitters na bandeja (EV-0142)', () => {
  const SPLIT = {
    ...FUSIONS,
    // o servidor marca as pontas ligadas a um splitter (aqui: entrada do 1x4)
    cables: FUSIONS.cables.map((c) => ({ ...c, ends: c.ends.map((e) => (e.key === '101:b' ? { ...e, splitter_use: 'a entrada do splitter 1x4' } : e)) })),
    splitters: [
      {
        id: 7, name: 'Primário', ratio: '1x8', loss_db: 10.5,
        input: null,
        power: { dbm: null, reason: 'sem fibra de entrada' },
        counts: { livre: 7, reservada: 1, ocupada: 0, bloqueada: 0 },
        ports: Array.from({ length: 8 }, (_, k) => ({ number: k + 1, status: k === 1 ? 'reservada' : 'livre', customer: k === 1 ? 'Fulano' : '', note: '', output: null, dbm: null })),
      },
      {
        id: 8, name: 'Splitter 1x4', ratio: '1x4', loss_db: 7.1,
        input: end(101, 'b', 'MANDI - VLP', 1, 'SITE - VILA RICA'),
        power: { dbm: 3.26, source: 'zabbix', from: 'OLT Mandi → gpon 1/1/1', km: 4.98, loss_db: 1.74 },
        counts: { livre: 4, reservada: 0, ocupada: 0, bloqueada: 0 },
        ports: Array.from({ length: 4 }, (_, k) => ({ number: k + 1, status: 'livre', customer: '', note: '', output: null, dbm: -3.84 })),
      },
    ],
  }
  function mountSplit(extra = {}) {
    const calls = []
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, o = {}) => {
      calls.push([url, o.method || 'GET', o.body ? JSON.parse(o.body) : null])
      return o.method && o.method !== 'GET' ? ok({ id: 9 }, 201) : ok(SPLIT)
    })
    mount(SpliceBoxModal, { props: { show: true, ceo: CEO, ...extra }, attachTo: document.body, global: { stubs: { RouterLink: RouterLinkStub } } })
    return { calls, q: (sel) => document.body.querySelector(sel) }
  }

  it('mostra a potência que chega e o dBm por porta; reservada a âmbar; sem entrada diz porquê', async () => {
    const { q } = mountSplit()
    await flushPromises()
    expect(q('[data-testid="splitter-power-8"]').textContent.replace(/\s+/g, ' ')).toContain('Chega +3,26 dBm · TX do Zabbix em OLT Mandi → gpon 1/1/1, 4,98 km, −1,74 dB')
    expect(q('[data-testid="port-8-1"]').textContent).toContain('-3,84')
    expect(q('[data-testid="port-7-2"]').className).toContain('st-reservada')
    expect(q('[data-testid="splitter-power-7"]').textContent).toContain('sem fibra de entrada')
    expect(q('[data-testid="fiber-101:b"]').disabled).toBe(true) // já é entrada do 1x4
  })

  it('acrescenta splitter, liga a entrada clicando numa fibra e grava o estado da porta', async () => {
    const { calls, q } = mountSplit()
    await flushPromises()
    q('[data-testid="splitter-add"]').click()
    await flushPromises()
    q('[data-testid="splitter-pick-input-7"]').click()
    await flushPromises()
    expect(q('[data-testid="splice-help"]').textContent).toContain('entrada do Primário')
    q('[data-testid="fiber-101:a"]').click()
    await flushPromises()
    q('[data-testid="port-7-3"]').click()
    await flushPromises()
    const status = q('[data-testid="port-status"]')
    status.value = 'ocupada'
    status.dispatchEvent(new Event('change'))
    const cust = q('[data-testid="port-customer"]')
    cust.value = 'Cliente 3'
    cust.dispatchEvent(new Event('input'))
    await flushPromises()
    q('[data-testid="port-save"]').click()
    await flushPromises()
    expect(calls.filter(([, m]) => m !== 'GET')).toEqual([
      ['/api/v1/inventory/ceos/4/splitters/', 'POST', { ratio: '1x8' }],
      ['/api/v1/inventory/ceos/4/splitters/7/', 'PATCH', { input: { strand_id: 101, side: 'a' } }],
      ['/api/v1/inventory/ceos/4/splitters/7/ports/3/', 'PATCH', { status: 'ocupada', customer: 'Cliente 3', note: '' }],
    ])
  })

  it('só leitura: sem acrescentar nem editar; a porta mostra o estado e o cliente', async () => {
    const { q } = mountSplit({ readonly: true })
    await flushPromises()
    expect(q('[data-testid="splitter-add"]')).toBeNull()
    q('[data-testid="port-7-2"]').click()
    await flushPromises()
    expect(q('[data-testid="port-editor-7"]').textContent).toContain('Reservada · Fulano')
    expect(q('[data-testid="port-save"]')).toBeNull()
  })
})

describe('FiberTrace (EV-0136)', () => {
  it('mostra porta → cabo → fusão → cabo → porta, o fim e a perda marcada como cálculo', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      ok({
        steps: [
          { type: 'port', device_name: 'OLT Mandi', port_name: 'gpon 1/1/1', site_name: 'SITE - VILA MANDI' },
          { type: 'cable', cable_name: 'MANDI - VLP', absolute_number: 1, color: 'Verde', color_hex: '#009900', toward: 'SITE - VILA RICA', km: 4.976, passes: [] },
          { type: 'fusion', ceo_name: 'CEO-04', tray: 1, slot: 1, loss_db: 0.1, dbm: 1.36 },
          { type: 'cable', cable_name: 'CEO-04 - VILA NOVA', absolute_number: 1, color: 'Verde', color_hex: '#009900', toward: 'SITE - VILA NOVA', km: 5.56, passes: [] },
          { type: 'port', device_name: 'SW Vila Nova', port_name: 'ge-0/0/1', site_name: 'SITE - VILA NOVA' },
        ],
        end: { reason: 'port', label: 'SW Vila Nova → ge-0/0/1' },
        total_km: 10.536,
        fusions: 1,
        loss_db_estimate: 3.79,
        tx: { dbm: 3.2, source: 'zabbix', port_name: 'gpon 1/1/1' },
        rx_estimate_dbm: -0.59,
        budget: { fiber_db_km: 0.25, fusion_db: 0.1 },
      }),
    )
    const w = mount(FiberTrace, { props: { strandId: 101, start: 'a' } })
    await flushPromises()
    expect(globalThis.fetch.mock.calls[0][0]).toBe('/api/v1/inventory/strands/101/trace/?from=a')
    expect(w.findAll('[data-testid="trace-step-cable"]')).toHaveLength(2)
    expect(w.get('[data-testid="trace-step-fusion"]').text()).toContain('CEO-04')
    expect(w.get('[data-testid="trace-end"]').text()).toBe('Chega a: SW Vila Nova → ge-0/0/1')
    expect(w.get('[data-testid="trace-total"]').text().replace(/\s+/g, ' ')).toContain('10,54 km · 1 fusão · perda estimada 3,79 dB · chega com ≈ -0,59 dBm')
    // EV-0140: partida com a origem do TX, dBm acumulado por passo, e a nota de que é cálculo
    expect(w.get('[data-testid="trace-tx"]').text()).toContain('+3,20 dBm — TX coletado do Zabbix (gpon 1/1/1)')
    expect(w.get('[data-testid="trace-step-fusion"]').text()).toContain('+1,36 dBm')
    expect(w.get('[data-testid="trace-note"]').text()).toContain('0,25 dB/km')
  })
})

