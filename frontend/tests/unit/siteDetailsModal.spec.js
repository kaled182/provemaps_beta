/**
 * EV-0065 — Modal de Site no BaseModal: estado pela disponibilidade real do Zabbix
 * (não pelo uptime), atenção/crítico só por métricas medidas, sem «0 %» inventado.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  deriveDeviceStatus,
  countDeviceStatuses,
  siteHeaderStatus,
  metricBar,
  formatUptimeSeconds,
  buildSiteDevice,
  applyRealtimeHost,
  deviceIndicator,
} from '@/utils/siteDevices'
import SiteDetailsModal from '@/components/SiteDetailsModal.vue'

const lastMessage = ref(null)
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({ connected: ref(false), lastMessage, connect: vi.fn(), disconnect: vi.fn() }),
}))
vi.mock('@/components/Video/CameraPlayer.vue', () => ({ default: { render: () => null } }))
const routerPush = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push: routerPush }) }))

describe('siteDevices', () => {
  it('disponibilidade decide online/offline; sem ela fica «sem estado»', () => {
    expect(deriveDeviceStatus('offline', { cpu: 10, cpu_source: 'zabbix' })).toBe('offline')
    expect(deriveDeviceStatus('unknown', { cpu: 10, cpu_source: 'zabbix' })).toBe('unknown')
    expect(deriveDeviceStatus(undefined)).toBe('unknown')
    expect(deriveDeviceStatus('online')).toBe('online')
  })

  it('atenção/crítico só por métrica medida pelo Zabbix (manual não agrava)', () => {
    expect(deriveDeviceStatus('online', { cpu: 95, cpu_source: 'manual' })).toBe('online')
    expect(deriveDeviceStatus('online', { cpu: 75, cpu_source: 'zabbix' })).toBe('warning')
    expect(deriveDeviceStatus('online', { cpu: 20, cpu_source: 'zabbix', memory: 92, memory_source: 'zabbix' })).toBe('critical')
  })

  it('contagens, cor do cabeçalho e barras sem valor inventado', () => {
    const c = countDeviceStatuses([{ status: 'online' }, { status: 'offline' }, { status: 'unknown' }, { status: 'x' }])
    expect(c).toEqual({ online: 1, warning: 0, critical: 0, offline: 1, unknown: 2 })
    expect(siteHeaderStatus(c)).toBe('critical')
    expect(siteHeaderStatus({ online: 2, warning: 1, critical: 0, offline: 0 })).toBe('attention')
    expect(siteHeaderStatus({ online: 0, warning: 0, critical: 0, offline: 0, unknown: 3 })).toBe('neutral')
    expect(metricBar(null)).toBeNull()
    expect(metricBar(0)).toEqual({ pct: 0, level: 'normal', label: '0%' })
    expect(metricBar(130).pct).toBe(100)
    expect(formatUptimeSeconds(0)).toBeNull()
    expect(formatUptimeSeconds(90061)).toBe('1d 1h')
  })

  it('buildSiteDevice: métrica ausente é null, não 0; WebSocket só mexe na disponibilidade', () => {
    const d = buildSiteDevice({ id: 7, name: 'SW', primary_ip: null }, 'online', { cpu: 80, cpu_source: 'zabbix' })
    expect(d).toMatchObject({ status: 'warning', cpu: 80, memory: null, uptime: null, ip: null })
    applyRealtimeHost(d, { status: 'offline', raw: { uptime_seconds: 0 } })
    expect(d.status).toBe('offline')
    applyRealtimeHost(d, { status: 'unknown', raw: {} })
    expect(d.availability).toBe('offline') // «unknown» do canal não apaga o último estado conhecido
    applyRealtimeHost(d, { status: 'online', raw: { uptime_seconds: 3600, uptime_human: '1h' } })
    expect(d).toMatchObject({ status: 'warning', uptime: 3600, uptimeHuman: '1h' })
  })
})

describe('deviceIndicator (EV-0111)', () => {
  it('OLT: ONUs online/total e alertas; sem ONUs não diz «0/0»', () => {
    const olt = { technology: 'gpon', onus_total: 347, onus_online: 282, signal_warning: 5, signal_critical: 3 }
    expect(deviceIndicator({ olt })).toEqual({
      kind: 'olt',
      badge: 'OLT GPON',
      main: '282/347 ONUs',
      alerts: [
        { level: 'critical', text: '3 crít.' },
        { level: 'warning', text: '5 atenção' },
      ],
    })
    expect(deviceIndicator({ olt: { ...olt, onus_total: 0, onus_online: 0, signal_warning: 0, signal_critical: 0 } }).main).toBe(
      'sem ONUs coletadas',
    )
  })

  it('switch: portas em uso e pior RX; sem resumo não há indicador', () => {
    const ports = { ports_total: 24, ports_in_use: 6, worst_rx_dbm: -25.1, worst_rx_level: 'warning' }
    expect(deviceIndicator({ ports })).toMatchObject({ kind: 'ports', main: '6 de 24 portas em uso', worstRx: -25.1, worstLevel: 'warning' })
    expect(deviceIndicator({ olt: null, ports: null })).toBeNull()
  })
})

describe('SiteDetailsModal', () => {
  const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
  const DEVICES = [
    { id: 1, name: 'OLT-Centro', group_name: 'OLT', primary_ip: '10.0.0.1', zabbix_hostid: '100' },
    { id: 2, name: 'SW-Norte', group_name: 'Switch', primary_ip: '10.0.0.2', zabbix_hostid: '200' },
    { id: 3, name: 'RT-Sul', group_name: null, primary_ip: null, zabbix_hostid: null },
  ]

  const fresh = new Date().toISOString()
  const PORTS = [
    { id: 21, name: 'XGigabitEthernet0/0/1', description: 'ENLACE CDT', last_rx_power: '-12.50', last_tx_power: '-2.10', last_optical_check: fresh },
    { id: 22, name: 'XGigabitEthernet0/0/2', description: 'ENLACE STA', last_rx_power: '-27.80', last_tx_power: '-2.00', last_optical_check: fresh },
    { id: 23, name: 'GigabitEthernet0/0/9', description: '', last_rx_power: null, last_tx_power: null },
  ]

  async function mountModal({ status = { statuses: { 1: 'online', 2: 'offline', 3: 'unknown' } }, metrics } = {}) {
    setActivePinia(createPinia())
    const m = metrics || {
      results: {
        1: { cpu: 93, cpu_source: 'zabbix', memory: 40, memory_source: 'zabbix', uptime_seconds: 90061 },
        2: { cpu: 99, cpu_source: 'manual' },
      },
    }
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url.startsWith('/api/v1/devices/metrics-batch/')) return ok(m)
      if (url.startsWith('/api/v1/monitoring/gpon/olt-summary/'))
        return ok({ olts: { 1: { vendor: 'zte', technology: 'gpon', onus_total: 347, onus_online: 282, signal_warning: 5, signal_critical: 0 } } })
      if (url.startsWith('/api/v1/inventory/devices/ports-summary/'))
        return ok({ devices: { 2: { ports_total: 24, ports_in_use: 6, worst_rx_dbm: -27.5, worst_rx_level: 'critical', stale_readings: 0 } } })
      if (url.startsWith('/api/v1/inventory/devices/zabbix-status/')) return ok(status)
      if (url.startsWith('/api/v1/inventory/devices/2/temperature/'))
        return ok({ device_id: 2, temperature_c: 41, sensor: 'LPU Board 1: Temperature', sensors: 2, at: '2026-11-24T15:00:00Z', reason: null, zabbix_ok: true })
      if (url.startsWith('/api/v1/inventory/devices/3/temperature/'))
        return ok({ device_id: 3, temperature_c: null, sensor: null, sensors: 0, at: null, reason: 'no_host', zabbix_ok: true })
      if (url.startsWith('/api/v1/ports/')) return ok({ results: PORTS, next: null })
      if (url.startsWith('/setup_app/api/config/')) return ok({ configuration: { OPTICAL_RX_WARNING_THRESHOLD: -24, OPTICAL_RX_CRITICAL_THRESHOLD: -27 } })
      if (url.startsWith('/api/v1/devices/')) return ok({ results: DEVICES })
      if (url.startsWith('/api/v1/cameras/')) return ok({ results: [], count: 4 })
      return ok({})
    })
    const w = mount(SiteDetailsModal, {
      props: { isOpen: true, site: { id: 10, name: 'POP Centro', location: 'Goiânia' } },
      attachTo: document.body,
    })
    await flushPromises()
    return w
  }
  const q = (sel) => document.body.querySelector(sel)
  const qa = (sel) => [...document.body.querySelectorAll(sel)]

  afterEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('cabeçalho no BaseModal, KPIs reais e «sem estado» à parte', async () => {
    const w = await mountModal()
    expect(q('[data-testid="base-modal"]')).not.toBeNull()
    expect(q('.bm-title').textContent).toBe('POP Centro')
    expect(q('.bm-icon').classList.contains('bm-icon-critical')).toBe(true) // há um offline e um crítico
    expect(q('[data-testid="site-kpi-online"]').textContent.trim()).toBe('0')
    expect(q('[data-testid="site-kpi-critical"]').textContent.trim()).toBe('1')
    expect(q('[data-testid="site-kpi-offline"]').textContent.trim()).toBe('1')
    expect(q('[data-testid="site-unknown-count"]').textContent).toContain('1 sem estado')
    expect(qa('[data-testid="site-device-status"]').map((e) => e.textContent.trim())).toEqual(['Crítico', 'Offline', 'Sem estado'])
    w.unmount()
  })

  it('métrica em falta mostra «—», CPU manual é marcada; uptime e IP numa linha', async () => {
    const w = await mountModal()
    const cards = qa('[data-testid="site-device-card"]')
    expect(cards[0].querySelector('[data-testid="site-device-cpu"]').textContent.trim()).toBe('93%')
    expect(cards[0].querySelector('.sdc-foot').textContent).toMatch(/uptime\s*1d 1h\s*·\s*IP\s*10\.0\.0\.1/)
    expect(cards[1].querySelector('[data-testid="site-device-cpu"]').textContent).toContain('manual')
    expect(cards[2].querySelector('[data-testid="site-device-cpu"]').textContent.trim()).toBe('—')
    expect(cards[2].querySelector('[data-testid="site-device-memory"]').textContent.trim()).toBe('—')
    w.unmount()
  })

  it('EV-0111: cards com badge do tipo, ONUs da OLT, portas e pior RX do switch, e «Inspecionar →»', async () => {
    await mountModal()
    const cards = qa('[data-testid="site-device-card"]')
    expect(cards[0].querySelector('[data-testid="site-device-type"]').textContent.trim()).toBe('OLT GPON')
    expect(cards[0].querySelector('[data-testid="site-device-indicator"]').textContent).toContain('282/347 ONUs')
    expect(cards[0].querySelector('[data-testid="site-device-indicator"]').textContent).toContain('5 atenção')
    expect(cards[1].querySelector('[data-testid="site-device-type"]').textContent.trim()).toBe('Switch')
    expect(cards[1].querySelector('[data-testid="site-device-indicator"]').textContent).toContain('6 de 24 portas em uso')
    const rx = cards[1].querySelector('[data-testid="site-device-worst-rx"]')
    expect(rx.textContent).toContain('-27.50 dBm')
    expect(rx.className).toContain('sdc-lv-critical')
    expect(cards[2].querySelector('[data-testid="site-device-indicator"]')).toBeNull() // sem resumo: nada inventado
    expect(cards[0].textContent).toContain('Inspecionar →')
  })

  it('EV-0112: clicar no card abre o equipamento no próprio modal (trilha, faixa, portas ópticas) e Voltar regressa', async () => {
    const w = await mountModal()
    qa('[data-testid="site-device-card"]')[1].click() // SW-Norte
    await flushPromises()
    expect(q('[data-testid="site-devices-grid"]')).toBeNull()
    expect(q('[data-testid="site-inspector-name"]').textContent).toBe('SW-Norte')
    expect(q('[data-testid="site-inspector-status"]').textContent).toBe('Offline')
    expect(q('[data-testid="site-inspector-temperature"]').textContent).toBe('41 °C')
    expect(q('[data-testid="site-inspector-cpu"]').textContent).toBe('99%') // manual
    const ports = qa('[data-testid="site-inspector-port"]')
    expect(ports).toHaveLength(2) // só as com leitura óptica
    expect(ports[0].textContent).toContain('XGigabitEthernet0/0/2') // pior primeiro
    expect(ports[0].querySelector('.lv-critical').textContent).toContain('-27.80 dBm')
    expect(ports[1].querySelector('.lv-normal').textContent).toContain('-12.50 dBm')
    q('[data-testid="site-inspector-back"]').click()
    await flushPromises()
    expect(q('[data-testid="site-devices-grid"]')).not.toBeNull()
    w.unmount()
  })

  it('EV-0112: sem temperatura mostra «—» com o motivo; Esc volta à lista antes de fechar', async () => {
    const w = await mountModal()
    qa('[data-testid="site-device-card"]')[2].click() // RT-Sul, sem host Zabbix
    await flushPromises()
    const temp = q('[data-testid="site-inspector-temperature"]')
    expect(temp.textContent).toBe('—')
    expect(temp.parentElement.getAttribute('title')).toBe('Equipamento sem host no Zabbix')
    q('[data-testid="base-modal-close"]').click()
    await flushPromises()
    expect(q('[data-testid="site-devices-grid"]')).not.toBeNull()
    expect(w.emitted('close')).toBeFalsy()
    w.unmount()
  })

  it('EV-0113: uma OLT abre o chassi (dados GPON da OLT) em vez da grelha de portas', async () => {
    const w = await mountModal()
    qa('[data-testid="site-device-card"]')[0].click() // OLT-Centro
    await flushPromises()
    expect(q('[data-testid="site-olt-chassis"]')).not.toBeNull()
    expect(q('[data-testid="site-inspector-ports"]')).toBeNull()
    const calls = globalThis.fetch.mock.calls.map(([u]) => u)
    expect(calls).toContain('/api/v1/monitoring/gpon/?olt=1')
    expect(calls.some((u) => u.includes('/devices/1/temperature/'))).toBe(false) // a da OLT vem da coleta GPON
    w.unmount()
  })

  it('EV-0112: «Abrir tela completa» — OLT vai ao ecrã GPON do POP; switch abre o modal de Dispositivo', async () => {
    const w = await mountModal()
    qa('[data-testid="site-device-card"]')[1].click()
    await flushPromises()
    q('[data-testid="site-inspector-full"]').click()
    await flushPromises()
    expect(qa('[data-testid="base-modal"]').some((m) => m.querySelector('.bm-title')?.textContent === 'SW-Norte')).toBe(true)
    w.unmount()
    document.body.innerHTML = ''
    const w2 = await mountModal()
    qa('[data-testid="site-device-card"]')[0].click() // OLT-Centro (tem resumo GPON)
    await flushPromises()
    q('[data-testid="site-inspector-full"]').click()
    expect(routerPush).toHaveBeenCalledWith({ path: '/monitoring/gpon', query: { pop: 'POP Centro' } })
    expect(w2.emitted('close')).toBeTruthy()
    w2.unmount()
  })

  it('Zabbix fora é avisado', async () => {
    const w = await mountModal({ status: { statuses: {}, zabbix_error: true } })
    expect(q('[data-testid="site-zabbix-error"]')).not.toBeNull()
    w.unmount()
  })

  it('a engrenagem abre a edição por cima do modal de Site, com aviso de alterações', async () => {
    const w = await mountModal()
    document.body.querySelector('[data-testid="site-device-card"] .sdc-edit').click()
    await flushPromises()
    const modals = qa('[data-testid="base-modal"]')
    const edit = modals.find((m) => m.querySelector('.bm-title')?.textContent === 'Editar dispositivo')
    expect(edit).toBeTruthy()
    expect(Number(edit.style.zIndex)).toBeGreaterThan(3000)
    const input = edit.querySelector('input[placeholder^="ex: sysUpTime"]')
    input.value = 'system.uptime'
    input.dispatchEvent(new Event('input'))
    await flushPromises()
    edit.querySelector('[data-testid="base-modal-close"]').click()
    await flushPromises()
    expect(edit.querySelector('[data-testid="base-modal-discard"]')).not.toBeNull()
    w.unmount()
  })

  it('WebSocket põe o equipamento offline e o X fecha', async () => {
    const w = await mountModal()
    lastMessage.value = { event: 'dashboard.status', data: { hosts: [{ device_id: 1, status: 'offline' }] } }
    await flushPromises()
    expect(q('[data-testid="site-kpi-offline"]').textContent.trim()).toBe('2')
    q('[data-testid="base-modal-close"]').click()
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
  })
})

describe('modais filhos por cima do BaseModal (regressão do EV-0065, EV-0068a)', () => {
  const read = (p) => readFileSync(resolve(__dirname, '../../src', p), 'utf8')
  // z-index de cada <BaseModal> pelo :show, na ordem do template
  const layers = (sfc) =>
    Object.fromEntries(
      [...sfc.matchAll(/<BaseModal\s+:show="([^"]+)"([^>]*)>/g)].map((m) => {
        const z = m[2].match(/:z-index="(\d+)"/)
        return [m[1], z ? Number(z[1]) : 3000]
      }),
    )

  it('edição, câmeras e mosaico abrem acima do modal de Site (3000 por omissão)', () => {
    const z = layers(read('components/SiteDetailsModal.vue'))
    for (const key of ['showEditModal', 'showCameraModal', 'showMosaicModal']) {
      expect(z[key], key).toBeGreaterThan(3000)
    }
  })

  it('o modal de Dispositivo e os seus sub-modais empilham por ordem', () => {
    const device = layers(read('components/DeviceDetailsModal.vue')).isOpen
    expect(device).toBeGreaterThan(3300)
    for (const p of ['PortActionsModal', 'ConnectivityMapModal', 'PortTrafficModal', 'AlarmConfigModal']) {
      expect(layers(read(`components/${p}.vue`)).isOpen, p).toBeGreaterThan(device)
    }
    // o alarme abre também por cima do tráfego
    expect(layers(read('components/AlarmConfigModal.vue')).isOpen).toBeGreaterThan(layers(read('components/PortTrafficModal.vue')).isOpen)
  })
})
