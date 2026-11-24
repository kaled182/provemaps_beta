/**
 * EV-0133 — estrutura do cabo: pede a rota certa (/api/v1/…), mostra os tubos e fibras do JSON
 * (o useApi não tem .data) e, sem perfil, deixa escolher o nº de fibras e gera.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CableStructureView from '@/components/Inventory/Fibers/CableStructureView.vue'

const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
const strands = Array.from({ length: 12 }, (_, i) => ({ id: i + 1, number: i + 1, absolute_number: i + 1, color: 'Verde', color_hex: '#009900', status: 'dark', state: i === 0 ? 'lit' : i === 1 ? 'fused' : 'free', port_a: i === 0 ? { id: 31, name: 'XGigabitEthernet0/0/3', device_name: 'Huawei - Switch Vila Mandi' } : null, port_b: null, fusions: [] }))
const ENDS = {
  a: { site_id: 1, site_name: 'SITE - VILA MANDI', devices: [{ id: 9, name: 'Huawei - Switch Vila Mandi', ports: [
    { id: 31, name: 'XGigabitEthernet0/0/3', used_by: { strand_id: 1, absolute_number: 1, cable_name: 'MANDI - VLP', end: 'a' } },
    { id: 32, name: 'XGigabitEthernet0/0/4', used_by: null },
    { id: 33, name: 'XGigabitEthernet0/0/5', used_by: { strand_id: 99, absolute_number: 4, cable_name: 'VLP - ELAGRO', end: 'a' } },
  ] }] },
  b: { site_id: 2, site_name: 'SITE - VILA RICA', devices: [] },
}
const STRUCT = { id: 1, name: 'MANDI - VLP', profile_name: 'Cabo 12FO (Tubo Único)', needs_profile: false, otdr_alert: null, ends: ENDS, tubes: [{ id: 1, number: 1, color: 'Verde', color_hex: '#009900', strands }] }

afterEach(() => vi.restoreAllMocks())

describe('CableStructureView (EV-0133)', () => {
  it('pede /api/v1/fiber-cables/<id>/structure/ e mostra tubos e fibras', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(STRUCT))
    const w = mount(CableStructureView, { props: { cableId: 1 } })
    await flushPromises()
    expect(spy.mock.calls[0][0]).toBe('/api/v1/fiber-cables/1/structure/')
    expect(w.text()).not.toContain('Erro ao carregar estrutura')
    expect(w.text()).toContain('MANDI - VLP')
    expect(w.text()).toContain('1 tubo · 12 fibras')
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
    expect(w.text()).toContain('12 fibras')
  })
})

describe('Diagrama e pontas (EV-0134)', () => {
  it('estado de cada fibra no anel, contagens na legenda, e o aviso de OTDR ativo', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok({ ...STRUCT, otdr_alert: { id: 5, map_distance_m: 14630.5, origin_name: 'SITE - VILA MANDI' } }))
    const w = mount(CableStructureView, { props: { cableId: 1 } })
    await flushPromises()
    expect(w.get('[data-testid="fiber-1"]').classes()).toContain('st-lit')
    expect(w.get('[data-testid="fiber-2"]').classes()).toContain('st-fused')
    expect(w.get('[data-testid="fiber-3"]').classes()).toContain('st-free')
    expect(w.get('[data-testid="legend-free"]').text()).toContain('10')
    expect(w.get('[data-testid="structure-otdr"]').text()).toContain('a 14,63 km de SITE - VILA MANDI')
  })

  it('painel da fibra: porta da ponta A, portas ocupadas por outras fibras desativadas, conectar e desligar', async () => {
    const calls = []
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, opts = {}) => {
      calls.push([url, opts.method || 'GET', opts.body])
      return ok(opts.method === 'POST' ? { strand_id: 1, end: 'a', port: null, state: 'free' } : STRUCT)
    })
    const w = mount(CableStructureView, { props: { cableId: 1 } })
    await flushPromises()
    await w.get('[data-testid="fiber-1"]').trigger('click')
    expect(w.get('[data-testid="fiber-state"]').text()).toBe('Iluminada')
    expect(w.get('[data-testid="end-a-port"]').text()).toContain('Huawei - Switch Vila Mandi → XGigabitEthernet0/0/3')
    const opts = w.get('[data-testid="end-a-select"]').findAll('option')
    expect(opts.find((o) => o.text().startsWith('XGigabitEthernet0/0/3')).attributes('disabled')).toBeUndefined() // é desta fibra
    expect(opts.find((o) => o.text().startsWith('XGigabitEthernet0/0/5')).attributes('disabled')).toBeDefined()
    expect(opts.find((o) => o.text().startsWith('XGigabitEthernet0/0/5')).text()).toContain('fibra 4 · VLP - ELAGRO')
    expect(w.get('[data-testid="end-b"]').text()).toContain('Nenhum equipamento cadastrado neste site.')
    await w.get('[data-testid="end-a-select"]').setValue('32')
    await w.get('[data-testid="end-a-connect"]').trigger('click')
    await flushPromises()
    await w.get('[data-testid="end-a-disconnect"]').trigger('click')
    await flushPromises()
    const posts = calls.filter(([, m]) => m === 'POST')
    expect(posts.map(([u]) => u)).toEqual(['/api/v1/fiber-cables/1/strands/1/port/', '/api/v1/fiber-cables/1/strands/1/port/'])
    expect(posts.map(([, , b]) => JSON.parse(b))).toEqual([{ end: 'a', port_id: 32 }, { end: 'a', port_id: null }])
  })

  it('erro do servidor (porta ocupada) aparece no painel', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url, opts = {}) =>
      opts.method === 'POST'
        ? Promise.resolve({ ok: false, status: 400, json: () => Promise.resolve({ detail: 'a porta XGigabitEthernet0/0/4 já está ligada à fibra 7 do cabo X' }) })
        : ok(STRUCT),
    )
    const w = mount(CableStructureView, { props: { cableId: 1 } })
    await flushPromises()
    await w.get('[data-testid="fiber-3"]').trigger('click')
    await w.get('[data-testid="end-a-select"]').setValue('32')
    await w.get('[data-testid="end-a-connect"]').trigger('click')
    await flushPromises()
    expect(w.get('[data-testid="fiber-error"]').text()).toContain('já está ligada à fibra 7')
  })
})

