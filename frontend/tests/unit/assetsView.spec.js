/**
 * EV-0058 — Ativos: junção inventário + Zabbix + métricas + portas ópticas;
 * CPU manual nunca conta como medida; «Zabbix fora» é avisado.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent, h } from 'vue'
import { buildAssetRows, computeAssetKpis, filterAndSortAssets, opticalPortsByDevice } from '@/utils/assetsTable'

const DEVICES = [
  { id: 1, name: 'OLT-Centro', vendor: 'Huawei', model: 'MA5800', site: 10, site_name: 'POP Centro', primary_ip: '10.0.0.1' },
  { id: 2, name: 'SW-Norte', vendor: 'MikroTik', model: '', site: 11, site_name: 'POP Norte', primary_ip: '10.0.0.2' },
  { id: 3, name: 'RT-Sul', vendor: '', model: '', site: 12, site_name: null, primary_ip: null },
]
const SITES = [
  { id: 10, display_name: 'POP Centro', latitude: '-16.6', longitude: '-49.2' },
  { id: 11, display_name: 'POP Norte', latitude: null, longitude: null },
  { id: 12, display_name: 'POP Sul', latitude: '-17.0', longitude: '-49.5' },
]
const STATUS = { statuses: { 1: 'online', 2: 'offline', 3: 'unknown' } }
const METRICS = {
  results: {
    1: { cpu: 95, cpu_source: 'zabbix', uptime_human: '3d 2h', last_collected: new Date(Date.now() - 30_000).toISOString() },
    2: { cpu: 99, cpu_source: 'manual', uptime_human: null, last_collected: null },
    3: { cpu: null, cpu_source: null },
  },
  zabbix_error: false,
}
const OPTICAL = {
  cables: [
    { origin: { device_id: 1, rx: -20, stale: false }, destination: { device_id: 2, rx: -45, stale: true } },
    { origin: { device_id: 1, rx: null, stale: false }, destination: { device_id: 3, rx: -18, stale: false } },
  ],
}

afterEach(() => vi.restoreAllMocks())

describe('assetsTable', () => {
  const optical = opticalPortsByDevice(OPTICAL)
  const sites = new Map(SITES.map((s) => [s.id, { name: s.display_name, lat: s.latitude === null ? null : Number(s.latitude), lng: s.longitude === null ? null : Number(s.longitude) }]))
  const rows = buildAssetRows(DEVICES, { statuses: STATUS.statuses, metrics: METRICS.results, optical, sites })

  it('portas ópticas: só leitura fresca conta como «com leitura»', () => {
    expect(optical.get(1)).toEqual({ withReading: 1, total: 2 })
    expect(optical.get(2)).toEqual({ withReading: 0, total: 1 }) // a leitura é velha
  })

  it('KPIs: CPU manual não é alerta; disponibilidade só entre estados conhecidos', () => {
    expect(computeAssetKpis(rows)).toEqual({ total: 3, online: 1, offline: 1, availability: 50, cpuMeasured: 1, cpuAlerts: 1 })
  })

  it('ordena offline primeiro e filtra CPU só por medição', () => {
    expect(filterAndSortAssets(rows).map((r) => r.id)).toEqual([2, 3, 1])
    expect(filterAndSortAssets(rows, { filter: 'cpu' }).map((r) => r.id)).toEqual([1])
    expect(filterAndSortAssets(rows, { query: '10.0.0.2' }).map((r) => r.id)).toEqual([2])
  })

  it('sem coordenadas do site não há «abrir no mapa»', () => {
    expect(rows.find((r) => r.id === 2).center).toBeNull()
    expect(rows.find((r) => r.id === 1).center).toEqual({ lat: -16.6, lng: -49.2 })
  })
})

describe('AssetsView', () => {
  const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })

  async function mountView({ metrics = METRICS } = {}) {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url.startsWith('/api/v1/devices/metrics-batch/')) return ok(metrics)
      if (url.startsWith('/api/v1/devices/')) return ok({ results: DEVICES, next: null })
      if (url.startsWith('/api/v1/sites/')) return ok({ results: SITES, next: null })
      if (url.startsWith('/api/v1/inventory/devices/zabbix-status/')) return ok(STATUS)
      if (url.startsWith('/api/v1/fiber-cables/optical-summary/')) return ok(OPTICAL)
      return Promise.reject(new Error(`inesperado ${url}`))
    })
    const Stub = defineComponent({ render: () => h('div') })
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/ativos', component: Stub }, { path: '/Network/NetworkDesign/', component: Stub }, { path: '/network/inventory', component: Stub }] })
    router.push('/ativos')
    await router.isReady()
    const { default: AssetsView } = await import('@/views/AssetsView.vue')
    const w = mount(AssetsView, { global: { plugins: [router] } })
    await flushPromises()
    return { w, router }
  }

  it('tabela com CPU manual marcada e valores em falta como «—»', async () => {
    const { w } = await mountView()
    expect(w.findAll('[data-testid^="asset-row-"]').map((r) => r.attributes('data-testid'))).toEqual(['asset-row-2', 'asset-row-3', 'asset-row-1'])
    expect(w.get('[data-testid="asset-row-2"]').text()).toContain('manual')
    expect(w.get('[data-testid="asset-row-3"]').text()).toContain('—')
    expect(w.get('[data-testid="asset-row-1"]').text()).toMatch(/1\/2/)
    expect(w.get('[data-testid="assets-availability"]').text()).toContain('50.0 % disponível')
    expect(w.find('[data-testid="assets-zabbix-error"]').exists()).toBe(false)
    w.unmount()
  })

  it('Zabbix fora: aviso explícito', async () => {
    const { w } = await mountView({ metrics: { results: {}, zabbix_error: true } })
    expect(w.find('[data-testid="assets-zabbix-error"]').exists()).toBe(true)
    expect(w.get('[data-testid="assets-cpu-kpi"]').text()).toContain('sem dados')
    w.unmount()
  })

  it('abrir no mapa leva ao Projeto de rede centrado no site', async () => {
    const { w, router } = await mountView()
    await w.get('[data-testid="asset-row-1"] button[title="Abrir no mapa"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ foco: 'device', id: '1', lat: '-16.6' })
    w.unmount()
  })
})
