/**
 * EV-0066 — Modal de Dispositivo no BaseModal: KPIs sem «0 %» inventado, todas as
 * páginas de portas, RX/TX em pílulas pelos limiares da configuração, leitura
 * velha sem cor de estado.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import {
  thresholdsFromConfig,
  normalizePort,
  levelOf,
  portState,
  filterPorts,
  sortPorts,
  portsToCsv,
  OPTICAL_STALE_AFTER_MS,
} from '@/utils/devicePorts'
import DeviceDetailsModal from '@/components/DeviceDetailsModal.vue'

const NOW = Date.parse('2026-11-23T20:00:00Z')
const fresh = new Date(NOW - 60_000).toISOString()
const old = new Date(NOW - OPTICAL_STALE_AFTER_MS - 60_000).toISOString()
const TH = { warning: -24, critical: -27 }

describe('devicePorts', () => {
  it('limiares da configuração; em falta ou inválidos → omissão', () => {
    expect(thresholdsFromConfig({ OPTICAL_RX_WARNING_THRESHOLD: '-22', OPTICAL_RX_CRITICAL_THRESHOLD: -26 })).toEqual({ warning: -22, critical: -26 })
    expect(thresholdsFromConfig({ OPTICAL_RX_WARNING_THRESHOLD: '', OPTICAL_RX_CRITICAL_THRESHOLD: 'x' })).toEqual(TH)
  })

  it('nível com <= como o backend; sem valor → null', () => {
    expect(levelOf(-27, TH)).toBe('critical')
    expect(levelOf(-24, TH)).toBe('warning')
    expect(levelOf(-23.9, TH)).toBe('normal')
    expect(levelOf(null, TH)).toBeNull()
  })

  it('normaliza a porta: strings → números, descrição limpa, leitura velha marcada', () => {
    const p = normalizePort({ id: 1, name: 'gpon 1/1', last_rx_power: '-20.5', last_tx_power: '', notes: 'Status Operacional da Porta uplink -', last_optical_check: old }, NOW)
    expect(p).toMatchObject({ optical_rx_power: -20.5, optical_tx_power: null, description: 'uplink', stale: true })
    expect(normalizePort({ id: 2, last_rx_power: null, last_optical_check: old }, NOW).stale).toBe(false) // sem leitura não é «velha»
  })

  it('estado: leitura velha não conta como atual; pior primeiro na ordenação', () => {
    const ports = [
      normalizePort({ id: 1, name: 'p10', last_rx_power: -20, last_optical_check: fresh }, NOW),
      normalizePort({ id: 2, name: 'p2', last_rx_power: -30, last_optical_check: old }, NOW),
      normalizePort({ id: 3, name: 'p3', last_rx_power: -28, last_optical_check: fresh }, NOW),
      normalizePort({ id: 4, name: 'p4' }, NOW),
    ]
    expect(ports.map((p) => portState(p, TH).key)).toEqual(['normal', 'stale', 'critical', 'none'])
    expect(sortPorts(ports, TH).map((p) => p.id)).toEqual([3, 1, 2, 4])
    expect(filterPorts(ports).map((p) => p.id)).toEqual([1, 2, 3])
    expect(filterPorts(ports, { onlyInUse: false, query: 'P1' }).map((p) => p.id)).toEqual([1])
  })

  it('CSV escapa aspas e deixa vazio o que não tem leitura', () => {
    const csv = portsToCsv([normalizePort({ id: 1, name: 'a"b', last_tx_power: -3 }, NOW)], TH)
    expect(csv.split('\n')[1]).toBe('"a""b","","Normal","","-3.00","",""')
  })
})

describe('DeviceDetailsModal', () => {
  const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
  const PAGE1 = Array.from({ length: 100 }, (_, i) => ({ id: i + 1, name: `p${i + 1}`, last_rx_power: null, last_tx_power: null }))
  const PAGE2 = [
    { id: 201, name: 'gpon-1', last_rx_power: '-28.1', last_tx_power: '2.1', last_optical_check: new Date().toISOString() },
    { id: 202, name: 'gpon-2', last_rx_power: '-20', last_tx_power: '1.5', last_optical_check: new Date().toISOString() },
  ]
  const DEVICE = { id: 9, name: 'OLT BRV', type: 'OLT', ip: '10.0.0.9', status: 'online', cpu: null, memory: 55, memorySource: 'manual', uptime: 90061 }
  const stubs = { PortActionsModal: true, AlarmConfigModal: true, ConnectivityMapModal: true, PortTrafficModal: true }

  async function mountModal({ portsFail = false } = {}) {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url.startsWith('/setup_app/api/config/')) return ok({ configuration: { OPTICAL_RX_WARNING_THRESHOLD: -24, OPTICAL_RX_CRITICAL_THRESHOLD: -27 } })
      if (url.startsWith('/api/v1/ports/')) {
        if (portsFail) return Promise.resolve({ ok: false, status: 500, statusText: 'Server Error', json: () => Promise.resolve({ detail: 'boom' }) })
        return url.includes('page=2') ? ok({ results: PAGE2, next: null }) : ok({ results: PAGE1, next: 'http://x/api/v1/ports/?device=9&page=2' })
      }
      return ok({})
    })
    const w = mount(DeviceDetailsModal, { props: { isOpen: true, device: DEVICE }, attachTo: document.body, global: { stubs } })
    await flushPromises()
    return w
  }
  const q = (sel) => document.body.querySelector(sel)
  const qa = (sel) => [...document.body.querySelectorAll(sel)]

  afterEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  it('cabeçalho, KPIs sem 0 % inventado e camada acima do modal de Site', async () => {
    const w = await mountModal()
    expect(q('.bm-title').textContent).toBe('OLT BRV')
    expect(q('.bm-subtitle').textContent).toBe('OLT · 10.0.0.9')
    expect(q('[data-testid="base-modal"]').style.zIndex).toBe('3400')
    expect(q('[data-testid="device-kpi-cpu"]').textContent.trim()).toBe('—')
    expect(q('[data-testid="device-kpis"]').textContent).toContain('manual')
    expect(q('[data-testid="device-kpi-uptime"]').textContent.trim()).toBe('1d 1h')
    expect(q('[data-testid="device-kpi-status"]').textContent.trim()).toBe('Online')
    w.unmount()
  })

  it('lê todas as páginas; mostra só as portas em uso, pior primeiro, com pílulas pelos limiares', async () => {
    const w = await mountModal()
    expect(q('[data-testid="device-ports-count"]').textContent.trim()).toBe('2 em uso de 102')
    const cards = qa('[data-testid="device-port-card"]')
    expect(cards).toHaveLength(2)
    expect(cards[0].querySelector('[data-testid="device-port-state"]').textContent.trim()).toBe('Sinal crítico')
    expect(cards[0].querySelector('[data-testid="device-port-rx"]').classList.contains('dpc-pill-critical')).toBe(true)
    expect(cards[1].querySelector('[data-testid="device-port-rx"]').classList.contains('dpc-pill-normal')).toBe(true)
    q('[data-testid="device-ports-toggle"]').click()
    await flushPromises()
    expect(qa('[data-testid="device-port-card"]')).toHaveLength(102)
    w.unmount()
  })

  it('erro ao carregar portas ≠ «sem portas»', async () => {
    const w = await mountModal({ portsFail: true })
    expect(q('[data-testid="device-ports-error"]')).not.toBeNull()
    expect(q('[data-testid="device-ports-empty"]')).toBeNull()
    w.unmount()
  })

  it('o X fecha', async () => {
    const w = await mountModal()
    q('[data-testid="base-modal-close"]').click()
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
  })
})
