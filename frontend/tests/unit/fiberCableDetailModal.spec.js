/**
 * EV-0067 — Modal de Cabo no BaseModal: sem modo de edição falso (o «Salvar» era um
 * setTimeout), sem window.confirm, detalhes em duas colunas, pontas A/B lado a lado,
 * mini-cards do tráfego acima do gráfico.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

vi.mock('@/services/fiberService', () => ({
  getCableOpticalHistory: vi.fn(() => Promise.resolve(null)),
  getCableTrafficHistory: vi.fn(() => Promise.resolve(null)),
  getCableAlarms: vi.fn(() => Promise.resolve([])),
  createCableAlarm: vi.fn(),
  deleteCableAlarm: vi.fn(),
  testCableAlarm: vi.fn(),
  getCableAlarmNotifications: vi.fn(() => Promise.resolve([])),
  snoozeCableAlarm: vi.fn(),
}))

import FiberCableDetailModal from '@/components/FiberCableDetailModal.vue'

const sfc = readFileSync(resolve(__dirname, '../../src/components/FiberCableDetailModal.vue'), 'utf8')
const CABLE = { id: 5, name: 'BRV - PLANURA', site_a_name: 'BRV', site_b_name: 'PLANURA', status: 'down', fiber_count: 12 }

describe('FiberCableDetailModal (EV-0067)', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

  async function mountModal() {
    setActivePinia(createPinia())
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) }),
    )
    const w = mount(FiberCableDetailModal, { props: { show: true, cable: CABLE }, attachTo: document.body })
    await flushPromises()
    return w
  }
  const q = (sel) => document.body.querySelector(sel)

  it('cabeçalho no BaseModal: nome, rota e ícone na cor do estado; acima do mapa', async () => {
    const w = await mountModal()
    expect(q('.bm-title').textContent).toBe('BRV - PLANURA')
    expect(q('.bm-subtitle').textContent).toBe('BRV → PLANURA')
    expect(q('.bm-icon').classList.contains('bm-icon-critical')).toBe(true)
    expect(q('[data-testid="base-modal"]').style.zIndex).toBe('10000')
    w.unmount()
  })

  it('sem modo de edição falso nem rodapé «Salvar»; o X fecha sem window.confirm', async () => {
    const confirm = vi.spyOn(window, 'confirm')
    const w = await mountModal()
    expect(document.body.textContent).not.toMatch(/Salvar Alterações|Editar Cabo/)
    expect(w.props()).not.toHaveProperty('canEdit')
    q('[data-testid="base-modal-close"]').click()
    expect(w.emitted('close')).toHaveLength(1)
    expect(confirm).not.toHaveBeenCalled()
    w.unmount()
  })

  it('o código não usa window.confirm nem o save simulado', () => {
    expect(sfc).not.toMatch(/window\.confirm|\bconfirm\(/)
    expect(sfc).not.toMatch(/saveChanges|isEditMode|TODO: Implementar salvamento/)
    expect(sfc).toContain('data-testid="alarm-delete-confirm"')
  })

  it('tráfego: mini-cards antes do gráfico nas duas pontas', () => {
    for (const side of ['Origin', 'Destination']) {
      const chart = sfc.indexOf(`ref="traffic${side}ChartRef"`)
      const stats = sfc.lastIndexOf('class="traffic-stats-grid"', chart)
      expect(stats).toBeGreaterThan(-1)
      expect(chart - stats).toBeLessThan(3000) // o bloco imediatamente acima, não o da outra ponta
    }
  })

  it('layout: detalhes em 2 colunas e pontas lado a lado, ambas abertas', () => {
    expect(sfc).toMatch(/\.info-grid \{\s*grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/)
    expect(sfc).toMatch(/\.port-charts-container,\s*\.traffic-ports-container \{\s*display: grid;\s*grid-template-columns: repeat\(2/)
    expect(sfc).toContain('const expandedDestination = ref(true)')
    expect(sfc).toContain('const trafficExpandedDestination = ref(true)')
  })

  it('a configuração de alarmes vive fora do BaseModal e acima dele', () => {
    const end = sfc.indexOf('</BaseModal>')
    expect(sfc.indexOf('class="alarm-modal-backdrop"')).toBeGreaterThan(end)
    const css = sfc.slice(sfc.indexOf('.alarm-modal-backdrop {'))
    expect(Number(css.match(/z-index:\s*(\d+)/)[1])).toBeGreaterThan(10000)
  })
})
