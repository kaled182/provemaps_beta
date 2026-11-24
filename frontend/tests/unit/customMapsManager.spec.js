/**
 * EV-0114 — /monitoring/backbone: cartões do design system, título da categoria certa
 * (a rota não tem :category), mutações pelo useApi com CSRF, exclusão por BaseModal.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const push = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ push }), useRoute: () => ({ params: {} }) }))

import CustomMapsManager from '@/views/monitoring/CustomMapsManager.vue'

const ok = (body, status = 200) =>
  Promise.resolve({ ok: true, status, json: () => Promise.resolve(body), text: () => Promise.resolve(body ? JSON.stringify(body) : '') })
const MAPS = [{ id: 7, name: 'Anel Norte', description: '', category: 'backbone', is_public: false, devices_count: 3, cables_count: 5, cameras_count: 0 }]

function mountPage() {
  document.cookie = 'csrftoken=tok123'
  const spy = vi.spyOn(globalThis, 'fetch').mockImplementation((url, opts = {}) => {
    if (!opts.method || opts.method === 'GET') return ok({ maps: MAPS, total: 1 })
    return ok(opts.method === 'DELETE' ? null : { id: 8 }, opts.method === 'DELETE' ? 204 : 201)
  })
  const w = mount(CustomMapsManager, { attachTo: document.body })
  return { w, spy }
}
const q = (sel) => document.body.querySelector(sel)

afterEach(() => {
  vi.restoreAllMocks()
  push.mockClear()
  document.body.innerHTML = ''
})

describe('CustomMapsManager', () => {
  it('título do Backbone, cartão do mapa completo e dos personalizados (sem gradiente)', async () => {
    const { w } = mountPage()
    await flushPromises()
    expect(w.get('.cmm-title').text()).toBe('Mapas · Backbone')
    expect(w.findAll('[data-testid="custom-maps-card"]')).toHaveLength(1)
    expect(w.get('[data-testid="custom-maps-card"]').text()).toContain('Privado')
    await w.get('[data-testid="custom-maps-default"]').trigger('click')
    expect(push).toHaveBeenCalledWith('/monitoring/backbone/map/default')
    w.unmount()
  })

  it('criar mapa envia POST pelo useApi com o CSRF do cookie', async () => {
    const { w, spy } = mountPage()
    await flushPromises()
    await w.get('[data-testid="custom-maps-create"]').trigger('click')
    await flushPromises()
    const name = q('[data-testid="custom-maps-name"]')
    name.value = 'Anel Sul'
    name.dispatchEvent(new Event('input'))
    await flushPromises()
    q('[data-testid="custom-maps-save"]').click()
    await flushPromises()
    const post = spy.mock.calls.find(([, o]) => o?.method === 'POST')
    expect(post[0]).toBe('/api/v1/maps/custom/')
    expect(post[1].headers['X-CSRFToken']).toBe('tok123')
    expect(JSON.parse(post[1].body)).toMatchObject({ name: 'Anel Sul', category: 'backbone', is_public: true })
    w.unmount()
  })

  it('excluir pede confirmação num BaseModal e faz DELETE (204 sem corpo)', async () => {
    const { w, spy } = mountPage()
    await flushPromises()
    await w.get('[data-testid="custom-maps-delete"]').trigger('click')
    await flushPromises()
    expect(spy.mock.calls.some(([, o]) => o?.method === 'DELETE')).toBe(false)
    q('[data-testid="custom-maps-confirm-delete"]').click()
    await flushPromises()
    const del = spy.mock.calls.find(([, o]) => o?.method === 'DELETE')
    expect(del[0]).toBe('/api/v1/maps/custom/7/')
    expect(q('[data-testid="custom-maps-confirm-delete"]')).toBeNull()
    w.unmount()
  })
})
