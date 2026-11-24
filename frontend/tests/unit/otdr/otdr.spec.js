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

describe('OtdrResultCard — EV-0130', () => {
  const withRefs = (over = {}) => ({
    ...RESULT,
    base_map_distance_m: 14630.5,
    offset_m: 0,
    references: {
      registered: 2,
      before: { id: 1, type: 'splice_box', type_label: 'Caixa de Emenda (CEO)', name: 'CEO-07', distance_m: 820 },
      after: { id: 2, type: 'slack', type_label: 'Reserva Técnica', name: null, distance_m: 1450 },
    },
    ...over,
  })

  it('passos e slider emitem o novo deslocamento; Street View abre noutra aba', async () => {
    const w = mount(OtdrResultCard, { props: { result: withRefs({ offset_m: 100 }) } })
    await w.get('[data-testid="otdr-step-500"]').trigger('click')
    await w.get('[data-testid="otdr-step--100"]').trigger('click')
    expect(w.emitted('adjust').map(([v]) => v)).toEqual([600, 0])
    const slider = w.get('[data-testid="otdr-slider"]')
    expect(slider.attributes('max')).toBe('73130')
    await slider.setValue('15000')
    await slider.trigger('change')
    expect(w.emitted('adjust').at(-1)[0]).toBeCloseTo(369.5)
    expect(w.get('[data-testid="otdr-card-offset"]').text()).toBe('ajuste +100 m')
    const sv = w.get('[data-testid="otdr-streetview"]')
    expect(sv.attributes('href')).toBe('https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-9.5338865,-50.7330878')
    expect(sv.attributes('target')).toBe('_blank')
  })

  it('caixas anterior e posterior; sem cadastro diz isso', () => {
    let w = mount(OtdrResultCard, { props: { result: withRefs() } })
    const refs = w.get('[data-testid="otdr-refs"]').text()
    expect(refs).toContain('Anterior: Caixa de Emenda (CEO) CEO-07 · 820 m')
    expect(refs).toContain('Posterior: Reserva Técnica · 1,45 km')
    w = mount(OtdrResultCard, { props: { result: withRefs({ references: { registered: 0, before: null, after: null } }) } })
    expect(w.get('[data-testid="otdr-refs"]').text()).toBe('Nenhuma caixa ou reserva cadastrada neste cabo.')
  })

  it('WhatsApp leva o ajuste e o Street View', () => {
    const msg = whatsappText(withRefs({ offset_m: -200 }))
    expect(msg).toContain('Ajuste em campo: -200 m sobre o traçado')
    expect(msg).toContain('Street View: https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=-9.5338865,-50.7330878')
  })
})

describe('Medição cruzada — EV-0131', () => {
  const CROSS = {
    ...RESULT, mode: 'cross', direction: 'ab', otdr_m: 22000, slack_pct: 3, offset_m: 0, base_map_distance_m: 21300,
    map_distance_m: 21300, references: { registered: 0, before: null, after: null },
    cross: { reading_a_m: 22000, reading_b_m: 53300, fiber_length_m: 75300, slack_real_pct: 2.97, proportion: 0.2922 },
    warnings: [],
  }

  it('formulário: duas leituras com os nomes dos sites, prévia da folga real e pedido com distance_b_m', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok(CROSS))
    const w = mount(OtdrLocatorModal, { props: { show: true, cable: CABLE }, attachTo: document.body })
    await flushPromises()
    document.body.querySelector('[data-testid="otdr-mode-cross"]').click()
    await flushPromises()
    expect(document.body.querySelector('label[for="otdr-a"]').textContent).toContain('Vila Mandi')
    expect(document.body.querySelector('label[for="otdr-b"]').textContent).toContain('Vila Rica')
    const set = async (sel, v) => {
      const el = document.body.querySelector(sel)
      el.value = v
      el.dispatchEvent(new Event('input'))
      await flushPromises()
    }
    await set('[data-testid="otdr-distance"]', '22')
    await set('[data-testid="otdr-distance-b"]', '53.3')
    const preview = document.body.querySelector('[data-testid="otdr-cross-preview"]').textContent
    expect(preview).toContain('Folga real 3,0%') // (22 + 53,3) / 73,13 − 1
    expect(preview).toContain('29,2%')
    document.body.querySelector('[data-testid="otdr-submit"]').click()
    await flushPromises()
    expect(spy.mock.calls[0][0]).toBe('/api/v1/inventory/cables/7/otdr-locate/?direction=ab&distance_m=22000&distance_b_m=53300')
    w.unmount()
  })

  it('cartão e WhatsApp mostram as duas leituras e a folga real; avisos aparecem', () => {
    const w = mount(OtdrResultCard, { props: { result: { ...CROSS, warnings: ['A soma das leituras é menor que o traçado do mapa'] } } })
    expect(w.get('[data-testid="otdr-card-cross"]').text()).toContain('22,00 km + 53,30 km')
    expect(w.get('[data-testid="otdr-card-cross"]').text()).toContain('folga real 2,97%')
    expect(w.get('[data-testid="otdr-card-warning"]').text()).toContain('menor que o traçado')
    expect(whatsappText(CROSS)).toContain('Medição cruzada: 22,00 km (de SITE - VILA MANDI) + 53,30 km (de SITE - VILA RICA) · folga real 2,97%')
  })
})

describe('EV-0132: estado do atendimento e histórico do cabo', () => {
  it('cartão de um fixado: estado atual e botões (o atual fica desativado); sem «Limpar»', async () => {
    const alert = { id: 5, created_by: 'Ana', created_at: '2026-11-24T19:00:00Z', note: '', status: 'en_route', status_label: 'Em deslocamento' }
    const w = mount(OtdrResultCard, { props: { result: { ...RESULT, references: { registered: 0 } }, alert } })
    expect(w.get('[data-testid="otdr-status-label"]').text()).toBe('Em deslocamento')
    expect(w.get('[data-testid="otdr-status-en_route"]').attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid="otdr-clear"]').exists()).toBe(false)
    await w.get('[data-testid="otdr-status-done"]').trigger('click')
    expect(w.emitted('status')[0][0]).toBe('done')
  })

  it('histórico: rompimentos do cabo com o estado e a linha do tempo', async () => {
    const { default: OtdrCableHistory } = await import('@/components/Otdr/OtdrCableHistory.vue')
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      ok([
        {
          id: 5, cable_id: 7, created_by: 'Ana', created_at: '2026-11-24T19:00:00Z', status: 'done', status_label: 'Concluído',
          result: { ...RESULT, mode: 'single' },
          log: [
            { at: '2026-11-24T19:00:00Z', by: 'Ana', action: 'pinned' },
            { at: '2026-11-24T19:10:00Z', by: 'Ana', action: 'adjusted', delta_m: 200 },
            { at: '2026-11-24T19:30:00Z', by: 'Rui', action: 'status', status: 'en_route' },
            { at: '2026-11-24T21:00:00Z', by: 'Rui', action: 'status', status: 'done' },
          ],
        },
      ]),
    )
    const w = mount(OtdrCableHistory, { props: { cableId: 7 } })
    await flushPromises()
    expect(spy.mock.calls[0][0]).toBe('/api/v1/inventory/cables/7/otdr-alerts/')
    const item = w.get('[data-testid="otdr-history-5"]').text()
    expect(item).toContain('Concluído')
    expect(item).toContain('OTDR 14,85 km de SITE - VILA MANDI → 14,63 km no traçado')
    expect(item).toContain('Ajuste fino +200 m — Ana')
    expect(item).toContain('Atendimento: Em deslocamento — Rui')
  })

  it('histórico vazio diz isso', async () => {
    const { default: OtdrCableHistory } = await import('@/components/Otdr/OtdrCableHistory.vue')
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => ok([]))
    const w = mount(OtdrCableHistory, { props: { cableId: 7 } })
    await flushPromises()
    expect(w.get('[data-testid="otdr-history-empty"]').text()).toContain('Nenhum rompimento')
  })
})

