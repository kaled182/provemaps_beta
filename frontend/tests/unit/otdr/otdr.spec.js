/**
 * EV-0127 — localizador OTDR: utilitários (links, WhatsApp, formatação) e o formulário
 * (sentido com os nomes dos sites, km/m, folga, prévia e validação contra o cabo).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { formatMeters, formatCoords, googleMapsUrl, wazeUrl, whatsappText } from '@/utils/otdr'
import OtdrLocatorModal from '@/components/Otdr/OtdrLocatorModal.vue'
import OtdrResultCard from '@/components/Otdr/OtdrResultCard.vue'

const RESULT = {
  cable_id: 7, cable_name: 'MANDI - VLP', direction: 'ab', otdr_m: 14850, slack_pct: 1.5,
  map_distance_m: 14630.5, path_length_m: 73130, inventory_length_km: 73.13,
  origin: { id: 1, name: 'SITE - VILA MANDI', distance_m: 14630.5 },
  target: { id: 2, name: 'SITE - VILA RICA', distance_m: 58499.5 },
  point: [-50.7330878, -9.5338865], segment: [[-50.733, -9.5335], [-50.7331, -9.5342]], tolerance_m: 40,
}
const CABLE = { id: 7, name: 'MANDI - VLP', length_km: 73.13, site_a_name: 'Vila Mandi', site_b_name: 'Vila Rica' }
const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('utils/otdr', () => {
  it('formata, monta os links e a mensagem do WhatsApp', () => {
    expect(formatMeters(14850)).toBe('14,85 km')
    expect(formatMeters(850)).toBe('850 m')
    expect(formatCoords(RESULT.point)).toBe('-9.533886, -50.733088')
    expect(googleMapsUrl(RESULT.point)).toBe('https://www.google.com/maps/dir/?api=1&destination=-9.5338865,-50.7330878')
    expect(wazeUrl(RESULT.point)).toBe('https://waze.com/ul?ll=-9.5338865,-50.7330878&navigate=yes')
    const msg = whatsappText(RESULT)
    expect(msg).toContain('Cabo: MANDI - VLP')
    expect(msg).toContain('Sentido: SITE - VILA MANDI → SITE - VILA RICA')
    expect(msg).toContain('Leitura OTDR: 14,85 km (folga 1,5% → 14,63 km no traçado)')
    expect(msg).toContain('Google Maps: https://www.google.com/maps/dir/?api=1&destination=-9.5338865,-50.7330878')
  })
})

describe('OtdrLocatorModal', () => {
  function mountModal() {
    return mount(OtdrLocatorModal, { props: { show: true, cable: CABLE }, attachTo: document.body })
  }
  const q = (sel) => document.body.querySelector(sel)
  const setInput = async (sel, v) => {
    const el = q(sel)
    el.value = v
    el.dispatchEvent(new Event('input'))
    await flushPromises()
  }

  it('sentido com os nomes dos sites, prévia com a folga e pedido ao backend em metros', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(RESULT))
    const w = mountModal()
    await flushPromises()
    expect(q('[data-testid="otdr-dir-ab"]').textContent.trim()).toBe('Vila Mandi → Vila Rica')
    expect(q('[data-testid="otdr-dir-ba"]').textContent.trim()).toBe('Vila Rica → Vila Mandi')
    q('[data-testid="otdr-dir-ba"]').click()
    await setInput('[data-testid="otdr-distance"]', '14.85')
    expect(q('[data-testid="otdr-preview"]').textContent).toContain('14,63 km') // 1,5% por omissão
    q('[data-testid="otdr-submit"]').click()
    await flushPromises()
    expect(spy.mock.calls[0][0]).toBe('/api/v1/inventory/cables/7/otdr-locate/?direction=ba&distance_m=14850&slack_pct=1.5')
    expect(w.emitted('located')[0][0]).toEqual(RESULT)
    w.unmount()
  })

  it('metros, folga personalizada e validação contra a extensão do cabo (sem ir ao servidor)', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(RESULT))
    const w = mountModal()
    await flushPromises()
    q('[data-testid="otdr-unit-m"]').click()
    q('[data-testid="otdr-slack-custom"]').click()
    await flushPromises()
    await setInput('[data-testid="otdr-slack-value"]', '2')
    await setInput('[data-testid="otdr-distance"]', '90000')
    expect(q('[data-testid="otdr-error"]').textContent).toContain('passa da extensão do cabo (73,13 km)')
    q('[data-testid="otdr-submit"]').click()
    await flushPromises()
    expect(spy).not.toHaveBeenCalled()
    w.unmount()
  })

  it('erro do servidor aparece no formulário', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve({ ok: false, status: 400, json: () => Promise.resolve({ detail: 'o cabo não tem traçado no mapa' }) }),
    )
    const w = mountModal()
    await flushPromises()
    await setInput('[data-testid="otdr-distance"]', '5')
    q('[data-testid="otdr-submit"]').click()
    await flushPromises()
    expect(q('[data-testid="otdr-error"]').textContent).toContain('o cabo não tem traçado no mapa')
    w.unmount()
  })
})

describe('OtdrLocatorModal sem cabo (EV-0128)', () => {
  it('escolhe o cabo (só os com traçado) e pede para o escolhido', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(RESULT))
    const cables = [
      { id: 9, name: 'SEM TRAÇADO', path_coordinates: [] },
      { id: 7, name: 'MANDI - VLP', length_km: 73.13, site_a_name: 'Vila Mandi', site_b_name: 'Vila Rica', path_coordinates: [{}, {}] },
    ]
    const w = mount(OtdrLocatorModal, { props: { show: true, cable: null, cables }, attachTo: document.body })
    await flushPromises()
    const sel = document.body.querySelector('[data-testid="otdr-cable"]')
    expect([...sel.options].map((o) => o.textContent.trim())).toEqual(['Escolher o cabo…', 'MANDI - VLP · 73,13 km'])
    sel.value = '7'
    sel.dispatchEvent(new Event('change'))
    await flushPromises()
    expect(document.body.querySelector('[data-testid="otdr-dir-ab"]').textContent.trim()).toBe('Vila Mandi → Vila Rica')
    const d = document.body.querySelector('[data-testid="otdr-distance"]')
    d.value = '2'
    d.dispatchEvent(new Event('input'))
    await flushPromises()
    document.body.querySelector('[data-testid="otdr-submit"]').click()
    await flushPromises()
    expect(spy.mock.calls[0][0]).toContain('/api/v1/inventory/cables/7/otdr-locate/')
    w.unmount()
  })
})

describe('OtdrResultCard', () => {
  it('mostra sentido, distâncias e GPS; links abrem noutra aba; copia para o WhatsApp; limpa', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const w = mount(OtdrResultCard, { props: { result: RESULT } })
    expect(w.get('[data-testid="otdr-card-direction"]').text()).toBe('SITE - VILA MANDI → SITE - VILA RICA')
    expect(w.get('[data-testid="otdr-card-map"]').text()).toContain('14,63 km')
    expect(w.get('[data-testid="otdr-card-coords"]').text()).toContain('-9.533886, -50.733088')
    expect(w.get('[data-testid="otdr-gmaps"]').attributes('target')).toBe('_blank')
    expect(w.get('[data-testid="otdr-waze"]').attributes('href')).toContain('waze.com/ul?ll=-9.5338865,-50.7330878')
    await w.get('[data-testid="otdr-whatsapp"]').trigger('click')
    await flushPromises()
    expect(writeText.mock.calls[0][0]).toContain('Rompimento de fibra')
    expect(w.get('[data-testid="otdr-whatsapp"]').text()).toBe('Copiado!')
    await w.get('[data-testid="otdr-clear"]').trigger('click')
    expect(w.emitted('clear')).toBeTruthy()
  })
})
