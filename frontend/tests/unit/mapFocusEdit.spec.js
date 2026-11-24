/** EV-0137 — «Editar no Projeto ↗»: location do Projeto de Rede a partir de site, cabo ou CEO. */
import { describe, it, expect } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import { focusLocationFor, parseFocusQuery } from '@/utils/mapFocus'
import EditInProjectLink from '@/components/Map/EditInProjectLink.vue'

describe('focusLocationFor', () => {
  it('site pelas coordenadas, cabo pelo ponto do meio do traçado, CEO pelo point [lng, lat]', () => {
    expect(focusLocationFor('site', { id: 10, name: 'POP A', latitude: '-16.6000', longitude: '-49.2000' }).query).toEqual({
      foco: 'site', id: '10', lat: '-16.6', lng: '-49.2', nome: 'POP A',
    })
    const cable = { id: 7, name: 'Anel', path_coordinates: [{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }, { lat: 5, lng: 6 }] }
    expect(focusLocationFor('cable', cable).query).toMatchObject({ foco: 'cable', id: '7', lat: '3', lng: '4' })
    const ceo = focusLocationFor('ceo', { id: 4, name: 'CEO-04', point: [-50, 0.045] })
    expect(parseFocusQuery(ceo.query)).toEqual({ type: 'ceo', id: 4, lat: 0.045, lng: -50, name: 'CEO-04' })
  })

  it('sem coordenadas não há link', () => {
    expect(focusLocationFor('cable', { id: 1, path_coordinates: [] })).toBeNull()
    expect(focusLocationFor('site', { id: 1 })).toBeNull()
    const w = mount(EditInProjectLink, { props: { type: 'site', target: { id: 1 } }, global: { stubs: { RouterLink: RouterLinkStub } } })
    expect(w.find('[data-testid="edit-in-project"]').exists()).toBe(false)
  })
})
