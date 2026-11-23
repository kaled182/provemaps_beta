/**
 * EV-0034 — importação KML como componente Vue: sem DOM legado nem globais window.*,
 * POST por useApi (CSRF), resultado pelo evento `fiber:cable-created`.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import KmlImportModal from '@/components/NetworkDesign/KmlImportModal.vue'

const src = (p) => resolve(__dirname, '../../src', p)
const q = (sel) => document.body.querySelector(sel)
const DEVICES = [
  { id: 1, name: 'OLT BRV', site: 'BRV' },
  { id: 2, name: 'SW PLANURA', site: null },
]
const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })

function mockApi({ importResponse } = {}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((url, init = {}) => {
    if (url.startsWith('/api/v1/inventory/cable-groups/')) return ok({ results: [{ id: 7, name: 'Backbone' }] })
    if (url.startsWith('/api/users/')) return ok({ users: [{ id: 3, full_name: 'Ana' }] })
    if (url.startsWith('/api/v1/inventory/devices/1/ports/')) return ok({ ports: [{ id: 11, name: 'gpon 1/1' }] })
    if (url.startsWith('/api/v1/inventory/devices/2/ports/')) return ok({ ports: [{ id: 21, name: 'xe-0/0/1' }] })
    if (url === '/api/v1/inventory/fibers/import-kml/' && init.method === 'POST')
      return importResponse || ok({ fiber_id: 99, points: 42 })
    return ok({})
  })
}

async function choose(testid, value) {
  const el = q(`[data-testid="${testid}"]`)
  el.value = String(value)
  el.dispatchEvent(new Event('change'))
  await flushPromises()
}
async function type(testid, value) {
  const el = q(`[data-testid="${testid}"]`)
  el.value = value
  el.dispatchEvent(new Event('input'))
  await flushPromises()
}
async function pickFile() {
  const input = q('[data-testid="kml-file"]')
  const file = new File(['<kml/>'], 'rota.kml', { type: 'application/vnd.google-earth.kml+xml' })
  Object.defineProperty(input, 'files', { value: [file] })
  input.dispatchEvent(new Event('change'))
  await flushPromises()
}

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('KmlImportModal', () => {
  it('lista equipamentos, grupos e responsáveis; escolher o equipamento carrega as portas', async () => {
    mockApi()
    const w = mount(KmlImportModal, { props: { show: true, devices: DEVICES }, attachTo: document.body })
    await flushPromises()
    expect(q('.bm-title').textContent).toBe('Importar rota via KML')
    expect(q('[data-testid="kml-origin-device"]').textContent).toContain('OLT BRV (BRV)')
    await choose('kml-origin-device', 1)
    expect(q('[data-testid="kml-origin-port"]').textContent).toContain('gpon 1/1')
    w.unmount()
  })

  it('«só origem» esconde o destino', async () => {
    mockApi()
    const w = mount(KmlImportModal, { props: { show: true, devices: DEVICES }, attachTo: document.body })
    await flushPromises()
    expect(q('[data-testid="kml-dest-device"]')).not.toBeNull()
    const cb = q('[data-testid="kml-single-port"]')
    cb.checked = true
    cb.dispatchEvent(new Event('change'))
    await flushPromises()
    expect(q('[data-testid="kml-dest-device"]')).toBeNull()
    expect(q('[data-testid="kml-dest-notice"]')).not.toBeNull()
    w.unmount()
  })

  it('importa por POST multipart com CSRF, avisa o mapa e fecha', async () => {
    const fetchSpy = mockApi()
    const created = vi.fn()
    document.addEventListener('fiber:cable-created', created)
    const w = mount(KmlImportModal, { props: { show: true, devices: DEVICES }, attachTo: document.body })
    await flushPromises()
    await type('kml-name', 'BRV - PLANURA')
    await choose('kml-origin-device', 1)
    await choose('kml-origin-port', 11)
    await choose('kml-dest-device', 2)
    await choose('kml-dest-port', 21)
    await pickFile()
    q('[data-testid="kml-form"]').dispatchEvent(new Event('submit'))
    await flushPromises()
    const [, init] = fetchSpy.mock.calls.find(([u, i]) => u === '/api/v1/inventory/fibers/import-kml/' && i?.method === 'POST')
    expect(init.headers).toHaveProperty('X-CSRFToken')
    const body = init.body
    expect(body.get('name')).toBe('BRV - PLANURA')
    expect(body.get('origin_port_id')).toBe('11')
    expect(body.get('dest_port_id')).toBe('21')
    expect(body.get('single_port')).toBeNull()
    expect(body.get('kml_file').name).toBe('rota.kml')
    expect(created).toHaveBeenCalledTimes(1)
    expect(created.mock.calls[0][0].detail).toEqual({ fiberId: 99 })
    expect(w.emitted('imported')[0][0]).toMatchObject({ fiber_id: 99 })
    expect(w.emitted('close')).toHaveLength(1)
    document.removeEventListener('fiber:cable-created', created)
    w.unmount()
  })

  it('erro do backend fica no modal (sem alert) e não fecha', async () => {
    const alert = vi.spyOn(window, 'alert').mockImplementation(() => {})
    mockApi({
      importResponse: Promise.resolve({ ok: false, status: 400, statusText: 'Bad Request', json: () => Promise.resolve({ error: 'KML sem LineString' }) }),
    })
    const w = mount(KmlImportModal, { props: { show: true, devices: DEVICES }, attachTo: document.body })
    await flushPromises()
    await type('kml-name', 'X')
    await pickFile()
    q('[data-testid="kml-form"]').dispatchEvent(new Event('submit'))
    await flushPromises()
    expect(q('[data-testid="kml-error"]').textContent).toContain('KML sem LineString')
    expect(w.emitted('close')).toBeUndefined()
    expect(alert).not.toHaveBeenCalled()
    w.unmount()
  })
})

describe('sem DOM legado nem globais (EV-0034)', () => {
  it('o import_kml.js saiu e ninguém publica ou chama as globais do KML', () => {
    expect(existsSync(src('features/networkDesign/partials/import_kml.js'))).toBe(false)
    for (const p of ['components/NetworkDesign/NetworkDesignView.vue', 'features/networkDesign/fiberRouteBuilder.js']) {
      const code = readFileSync(src(p), 'utf8')
      expect(code, p).not.toMatch(/window\.(openKmlModal|closeKmlModal|initializeKmlModal|__FIBER_DEVICE_OPTIONS)\s*=|\bopenKmlModal\(\)|id="importKmlModal"/)
    }
    expect(readFileSync(src('features/networkDesign/fiberRouteBuilder.js'), 'utf8')).toContain("new CustomEvent('fiber:open-kml-import')")
  })
})
