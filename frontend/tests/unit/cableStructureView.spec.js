/**
 * EV-0133 — estrutura do cabo: pede a rota certa (/api/v1/…), mostra os tubos e fibras do JSON
 * (o useApi não tem .data) e, sem perfil, deixa escolher o nº de fibras e gera.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CableStructureView from '@/components/Inventory/Fibers/CableStructureView.vue'

const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
const strands = Array.from({ length: 12 }, (_, i) => ({ id: i + 1, number: i + 1, absolute_number: i + 1, color: 'Verde', color_hex: '#009900', status: 'dark' }))
const STRUCT = { id: 1, name: 'MANDI - VLP', profile_name: 'Cabo 12FO (Tubo Único)', needs_profile: false, tubes: [{ id: 1, number: 1, color: 'Verde', color_hex: '#009900', strands }] }

afterEach(() => vi.restoreAllMocks())

describe('CableStructureView (EV-0133)', () => {
  it('pede /api/v1/fiber-cables/<id>/structure/ e mostra tubos e fibras', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(STRUCT))
    const w = mount(CableStructureView, { props: { cableId: 1 } })
    await flushPromises()
    expect(spy.mock.calls[0][0]).toBe('/api/v1/fiber-cables/1/structure/')
    expect(w.text()).not.toContain('Erro ao carregar estrutura')
    expect(w.text()).toContain('MANDI - VLP')
    expect(w.text()).toContain('1 Tubos • 12 Fibras')
  })

  it('sem perfil: escolhe o perfil, gera e recarrega', async () => {
    const calls = []
    let generated = false
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, opts = {}) => {
      calls.push([url, opts.method || 'GET', opts.body])
      if (opts.method === 'POST') {
        generated = true
        return ok({ created: true, needs_profile: false })
      }
      return ok(generated ? STRUCT : { id: 2, name: 'JBS-CFS', needs_profile: true, tubes: [], available_profiles: [{ id: 4, name: 'Cabo 12FO (Tubo Único)', total_fibers: 12 }] })
    })
    const w = mount(CableStructureView, { props: { cableId: 2 } })
    await flushPromises()
    expect(w.find('[data-testid="structure-needs-profile"]').exists()).toBe(true)
    await w.get('[data-testid="structure-profile-select"]').setValue('4')
    await w.get('[data-testid="structure-generate"]').trigger('click')
    await flushPromises()
    const post = calls.find(([, m]) => m === 'POST')
    expect(post[0]).toBe('/api/v1/fiber-cables/2/structure/profile/')
    expect(JSON.parse(post[2])).toEqual({ profile_id: 4 })
    expect(w.text()).toContain('12 Fibras')
  })
})
