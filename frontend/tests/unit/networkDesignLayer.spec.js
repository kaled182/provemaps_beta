/**
 * EV-0138 — Projeto de Rede: modos (cliques só desenham em «Traçar» ou com rota em edição),
 * snap em sites/CEOs, barra, menu de objeto, avisos sem HTML injetado e a camada que liga o
 * menu de contexto legado e os modos aos formulários de CEO, reserva e site.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

vi.mock('@/features/networkDesign/fiberRouteBuilder.js', () => ({
  clickFromLayer: vi.fn(),
  editCableRoute: vi.fn(),
  reloadNetworkDesignCables: vi.fn(),
  startRouteAt: vi.fn(),
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn() }) }))

import * as builder from '@/features/networkDesign/fiberRouteBuilder.js'
import {
  designMode,
  emitDesign,
  lastCableContext,
  routeClicksEnabled,
  setSnapProvider,
  snapPoint,
} from '@/features/networkDesign/modules/designMode.js'
import { useDesignPoints } from '@/components/NetworkDesign/design/useDesignPoints'
import NdDock from '@/components/NetworkDesign/design/NdDock.vue'
import NdObjectMenu from '@/components/NetworkDesign/design/NdObjectMenu.vue'
import DesignLayer from '@/components/NetworkDesign/design/DesignLayer.vue'
import { showConfirmDialog, showErrorMessage } from '@/features/networkDesign/modules/uiHelpers.js'

const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })

/** IMap falso: pixel = (lng*1000, -lat*1000); marcadores com on/fire. */
function fakeMap() {
  const markers = []
  return {
    markers,
    latLngToPixel: ({ lat, lng }) => ({ x: lng * 1000, y: -lat * 1000 }),
    on: vi.fn(),
    off: vi.fn(),
    createPolyline: vi.fn(() => ({ setPath: vi.fn(), remove: vi.fn() })),
    createMarker: vi.fn((opts) => {
      const h = {}
      const m = { opts, on: (e, cb) => ((h[e] ||= []).push(cb)), fire: (e, p) => (h[e] || []).forEach((cb) => cb(p)), remove: vi.fn(), setStyle: vi.fn(), getPosition: () => opts.position }
      markers.push(m)
      return m
    }),
  }
}

afterEach(() => {
  vi.restoreAllMocks()
  designMode.value = 'select'
  setSnapProvider(null)
  document.body.innerHTML = ''
})

describe('modos e snap', () => {
  it('cliques no mapa só desenham em «Traçar» ou com uma rota em edição', () => {
    expect(routeClicksEnabled({ editing: false })).toBe(false)
    expect(routeClicksEnabled({ editing: true })).toBe(true)
    designMode.value = 'trace'
    expect(routeClicksEnabled({ editing: false })).toBe(true)
  })

  it('snap: o ponto cola no site/CEO a menos de 18 px; longe fica onde foi clicado', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) =>
      ok(
        String(url).startsWith('/api/v1/sites/')
          ? { results: [{ id: 1, name: 'SITE A', latitude: '-0.010000', longitude: '0.020000' }] }
          : String(url).startsWith('/api/v1/inventory/ceos/')
            ? [{ id: 4, name: 'CEO-04', point: [0.1, -0.05] }]
            : [],
      ),
    )
    const pts = useDesignPoints()
    await pts.load()
    const map = fakeMap()
    expect(pts.snap(map, -0.0101, 0.0205)).toEqual({ lat: -0.01, lng: 0.02, snapped: 'site', name: 'SITE A' })
    // no mapa falso 0,001° = 1 px: a 10 px da CEO cola; a 100 px fica onde se clicou
    expect(pts.snap(map, -0.05, 0.11)).toEqual({ lat: -0.05, lng: 0.1, snapped: 'ceo', name: 'CEO-04' })
    expect(pts.snap(map, -0.05, 0.2)).toBeNull()
  })

  it('snapPoint usa o fornecedor registado e devolve o clique sem fornecedor', () => {
    expect(snapPoint(1, 2)).toEqual({ lat: 1, lng: 2 })
    setSnapProvider(() => ({ lat: 9, lng: 9 }))
    expect(snapPoint(1, 2)).toEqual({ lat: 9, lng: 9 })
  })
})

describe('NdDock e NdObjectMenu', () => {
  it('o botão ativa o modo e um segundo clique volta a «Selecionar»; a dica diz o que fazer', async () => {
    const w = mount(NdDock, { props: { modelValue: 'select' } })
    await w.get('[data-testid="dock-ceo"]').trigger('click')
    expect(w.emitted('update:modelValue')[0]).toEqual(['ceo'])
    await w.setProps({ modelValue: 'ceo' })
    expect(w.get('[data-testid="nd-dock-hint"]').text()).toContain('Clique sobre um cabo onde fica a caixa')
    await w.get('[data-testid="dock-ceo"]').trigger('click')
    expect(w.emitted('update:modelValue')[1]).toEqual(['select'])
  })

  it('o menu emite a escolha e fecha com Esc', async () => {
    const w = mount(NdObjectMenu, { props: { x: 10, y: 10, title: 'CEO-04', items: [{ key: 'move', label: 'Mover posição' }] }, attachTo: document.body })
    await w.get('[data-testid="om-move"]').trigger('click')
    expect(w.emitted('pick')[0]).toEqual(['move'])
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(w.emitted('close')).toBeTruthy()
    w.unmount()
  })
})

describe('avisos do construtor', () => {
  it('a mensagem e o diálogo são texto (sem HTML) e em português', async () => {
    showErrorMessage('<img src=x onerror=alert(1)>')
    const toast = document.querySelector('.toast-card')
    expect(toast.querySelector('img')).toBeNull()
    expect(toast.textContent).toContain('Erro')
    const answer = showConfirmDialog({ title: 'Excluir cabo', description: 'Excluir o cabo «<b>X</b>»?', confirmText: 'Excluir', tone: 'danger' })
    const card = document.querySelector('.confirm-card')
    expect(card.querySelector('b')).toBeNull()
    expect(card.textContent).toContain('Excluir o cabo «<b>X</b>»?')
    expect([...card.querySelectorAll('button')].map((b) => b.textContent)).toEqual(['Cancelar', 'Excluir'])
    card.querySelectorAll('button')[1].click()
    await expect(answer).resolves.toBe(true)
  })
})

describe('DesignLayer', () => {
  function mountLayer() {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) =>
      ok(String(url).startsWith('/api/v1/sites/') ? { results: [{ id: 7, name: 'SITE - VILA NOVA', latitude: '-10.5', longitude: '-50.1' }] } : []),
    )
    const map = fakeMap()
    const w = mount(DesignLayer, { props: { map }, attachTo: document.body, global: { stubs: { MapPopup: true } } })
    return { w, map }
  }

  it('desenha os sites; clique direito abre o menu; «Conectar novo cabo aqui» começa o traçado no site', async () => {
    const { w, map } = mountLayer()
    await flushPromises()
    expect(map.markers).toHaveLength(1)
    map.markers[0].fire('rightclick', { clientX: 100, clientY: 120 })
    await nextTick()
    expect(w.get('[data-testid="nd-object-menu"]').text()).toContain('SITE - VILA NOVA')
    await w.get('[data-testid="om-connect"]').trigger('click')
    expect(builder.startRouteAt).toHaveBeenCalledWith(-10.5, -50.1)
    w.unmount()
  })

  it('«Inserir CEO aqui» do menu do cabo abre o formulário no ponto do clique direito; em «Novo site» o clique no mapa abre o do site', async () => {
    const { w } = mountLayer()
    await flushPromises()
    lastCableContext.value = { cableId: 3, cableName: 'MANDI - VLP', lat: -10.1, lng: -50.2 }
    emitDesign('menu-action', { action: 'ceo' })
    await vi.dynamicImportSettled()
    await flushPromises()
    const ceo = w.findComponent({ name: 'CeoCreateModal' })
    expect(ceo.props('cable')).toEqual({ id: 3, name: 'MANDI - VLP' })
    expect(ceo.props('point')).toEqual({ lat: -10.1, lng: -50.2 })
    designMode.value = 'site'
    emitDesign('map-click', { lat: -10.3, lng: -50.4, mode: 'site' })
    await vi.dynamicImportSettled()
    await flushPromises()
    expect(w.findComponent({ name: 'SiteCreateModal' }).props('point')).toEqual({ lat: -10.3, lng: -50.4 })
    w.unmount()
  })

  it('no modo «Traçar» um clique num site conta como ponto do traçado (no centro do site)', async () => {
    const { w, map } = mountLayer()
    await flushPromises()
    designMode.value = 'trace'
    map.markers[0].fire('click', { clientX: 1, clientY: 1 })
    expect(builder.clickFromLayer).toHaveBeenCalledWith(-10.5, -50.1)
    w.unmount()
  })
})
