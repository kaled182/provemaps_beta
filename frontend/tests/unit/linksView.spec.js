/**
 * EV-0057 — ecrã Enlaces & fibra e helpers da tabela; EV-0049 — card do pior RX no HUD.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent, h } from 'vue'
import { filterAndSortLinks, formatDb, countByFilter, worstRx } from '@/utils/linksTable'
import MapKpiHud from '@/views/monitoring/components/MapKpiHud.vue'
import { computeMapKpis } from '@/utils/mapKpis'

vi.mock('@/components/FiberCableDetailModal.vue', () => ({
  __esModule: true,
  default: { name: 'FiberCableDetailModal', props: ['show', 'cable'], render: () => h('div', { 'data-stub': 'modal' }) },
}))

const end = (over = {}) => ({
  port_id: 1, port_name: 'p', device_name: 'D', site_name: null, rx: -20, tx: 2,
  status: 'online', warning_threshold: -24, critical_threshold: -27, last_check: '2026-11-23T16:00:00Z', stale: false, ...over,
})
const CABLES = [
  { id: 1, name: 'Anel Norte', length_km: 12.5, site_a: 'POP Centro', site_b: 'POP Norte', status: 'online', health: 'healthy',
    origin: end({ device_name: 'OLT-1', port_name: 'xe-0/0/1' }), destination: end({ rx: -21 }), loss_ab_db: 23, loss_ba_db: 22, center: { lat: -16, lng: -49 } },
  { id: 2, name: 'Backbone Sul', length_km: null, site_a: null, site_b: null, status: 'critical', health: 'critical',
    origin: end({ rx: -40, status: 'critical' }), destination: end({ rx: -20 }), loss_ab_db: 22, loss_ba_db: 42, center: null },
  { id: 3, name: 'Drop Escola', length_km: 0.4, site_a: null, site_b: null, status: 'unknown', health: 'unknown',
    origin: end({ rx: null, tx: null, status: 'unknown' }), destination: end({ rx: -45, stale: true }), loss_ab_db: null, loss_ba_db: null, center: null },
  { id: 4, name: 'Anel Leste', length_km: 3, site_a: null, site_b: null, status: 'warning', health: 'attention',
    origin: end({ rx: -25, status: 'warning' }), destination: end(), loss_ab_db: 22, loss_ba_db: 27, center: null },
]
const SUMMARY = {
  cables: CABLES,
  totals: { total: 4, healthy: 1, attention: 1, critical: 1, unknown: 1 },
  worst: { cable_id: 2, cable_name: 'Backbone Sul', side: 'origin', rx: -40 },
  last_check: '2026-11-23T16:00:00Z',
}

afterEach(() => vi.restoreAllMocks())

describe('linksTable', () => {
  it('ordena pela pior saúde e, dentro dela, pelo RX mais baixo; leitura velha não conta', () => {
    expect(filterAndSortLinks(CABLES).map((c) => c.id)).toEqual([2, 4, 3, 1])
    expect(worstRx(CABLES[2])).toBeNull() // só tem uma leitura, e é velha
  })

  it('filtra por saúde e por texto sem acentos (site, equipamento, porta)', () => {
    expect(filterAndSortLinks(CABLES, { filter: 'critical' }).map((c) => c.id)).toEqual([2])
    expect(filterAndSortLinks(CABLES, { query: 'pop norte' }).map((c) => c.id)).toEqual([1])
    expect(filterAndSortLinks(CABLES, { query: 'XE-0/0' }).map((c) => c.id)).toEqual([1])
    expect(filterAndSortLinks(CABLES, { query: 'escola' }).map((c) => c.id)).toEqual([3])
  })

  it('falta de valor é «—», nunca 0.00', () => {
    expect(formatDb(null)).toBe('—')
    expect(formatDb(undefined)).toBe('—')
    expect(formatDb(-18.5)).toBe('-18.50')
    expect(formatDb(0)).toBe('0.00')
  })

  it('contagens dos chips', () => {
    expect(countByFilter(CABLES)).toEqual({ all: 4, critical: 1, attention: 1, healthy: 1, unknown: 1 })
  })
})

describe('LinksView', () => {
  async function mountView(response) {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => response)
    const Stub = defineComponent({ render: () => h('div') })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/enlaces', component: Stub }, { path: '/Network/NetworkDesign/', component: Stub }],
    })
    router.push('/enlaces')
    await router.isReady()
    const { default: LinksView } = await import('@/views/LinksView.vue')
    const w = mount(LinksView, { global: { plugins: [router] } })
    await flushPromises()
    return { w, router }
  }
  const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })

  it('mostra KPIs, linhas ordenadas e valores em falta como «—»', async () => {
    const { w } = await mountView(ok(SUMMARY))
    expect(globalThis.fetch.mock.calls[0][0]).toBe('/api/v1/fiber-cables/optical-summary/')
    const rows = w.findAll('[data-testid^="link-row-"]')
    expect(rows.map((r) => r.attributes('data-testid'))).toEqual(['link-row-2', 'link-row-4', 'link-row-3', 'link-row-1'])
    expect(w.get('[data-testid="link-row-2"]').text()).toContain('-40.00')
    expect(w.get('[data-testid="link-row-3"]').text()).toContain('—')
    expect(w.get('[data-testid="link-row-3"]').text()).not.toContain('0.00 /')
    expect(w.text()).toContain('Críticos / LOS')
    w.unmount()
  })

  it('filtro «Críticos» deixa só os críticos', async () => {
    const { w } = await mountView(ok(SUMMARY))
    await w.get('[data-testid="links-filter-critical"]').trigger('click')
    expect(w.findAll('[data-testid^="link-row-"]')).toHaveLength(1)
    w.unmount()
  })

  it('«ver no mapa» abre o Projeto de rede centrado no cabo; gráfico abre o modal', async () => {
    const { w, router } = await mountView(ok(SUMMARY))
    const row = w.get('[data-testid="link-row-1"]')
    await row.get('button[title="Ver no mapa"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ foco: 'cable', id: '1', lat: '-16', lng: '-49' })
    expect(w.get('[data-testid="link-row-2"] button[title="Ver no mapa"]').attributes('disabled')).toBeDefined()
    await w.get('[data-testid="link-row-1"] button[title="Gráfico óptico"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-stub="modal"]').exists()).toBe(true)
    w.unmount()
  })

  it('erro do backend aparece como erro', async () => {
    const { w } = await mountView(Promise.resolve({ ok: false, status: 500, statusText: 'x', json: () => Promise.resolve({ error: 'falhou' }) }))
    expect(w.text()).toContain('Erro ao ler os níveis ópticos')
    w.unmount()
  })
})

describe('HUD — pior sinal RX (EV-0049)', () => {
  const kpis = computeMapKpis({ devices: [], cables: [] })

  it('mostra o pior RX real e realça-o quando passa o limiar crítico', () => {
    const w = mount(MapKpiHud, { props: { kpis, optical: { worst: SUMMARY.worst, critical: -27, error: '' } } })
    const card = w.get('[data-testid="kpi-attenuation"]')
    expect(card.text()).toContain('-40.00')
    expect(card.text()).toContain('Backbone Sul')
    expect(card.find('.text-danger').exists()).toBe(true)
    w.unmount()
  })

  it('sem leituras diz «sem dados»; com erro diz «erro»', () => {
    const a = mount(MapKpiHud, { props: { kpis, optical: { worst: null, critical: null, error: '' } } })
    expect(a.get('[data-testid="kpi-attenuation"]').text()).toContain('sem dados')
    const b = mount(MapKpiHud, { props: { kpis, optical: { worst: null, critical: null, error: 'HTTP 500' } } })
    expect(b.get('[data-testid="kpi-attenuation"]').text()).toContain('erro')
    a.unmount()
    b.unmount()
  })
})
