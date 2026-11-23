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
} from '@/utils/siteDevices'
import SiteDetailsModal from '@/components/SiteDetailsModal.vue'

const lastMessage = ref(null)
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({ connected: ref(false), lastMessage, connect: vi.fn(), disconnect: vi.fn() }),
}))
vi.mock('@/components/Video/CameraPlayer.vue', () => ({ default: { render: () => null } }))

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

describe('SiteDetailsModal', () => {
  const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
  const DEVICES = [
    { id: 1, name: 'OLT-Centro', group_name: 'OLT', primary_ip: '10.0.0.1', zabbix_hostid: '100' },
    { id: 2, name: 'SW-Norte', group_name: 'Switch', primary_ip: '10.0.0.2', zabbix_hostid: '200' },
    { id: 3, name: 'RT-Sul', group_name: null, primary_ip: null, zabbix_hostid: null },
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
      if (url.startsWith('/api/v1/inventory/devices/zabbix-status/')) return ok(status)
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
