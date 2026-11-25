/**
 * EV-0060 / ADR 0009 — topologia: projeção geográfica estável, cabos paralelos
 * separados, capacidade nunca inventada, cabos fora do desenho com motivo.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { projectNodes, edgePaths, capacityLabel } from '@/utils/topologyLayout'

const NODES = [
  { id: 1, name: 'SITE - NORTE', lat: -10, lng: -50 },
  { id: 2, name: 'SITE - SUL', lat: -12, lng: -50 },
  { id: 3, name: 'SITE - LESTE', lat: -11, lng: -48 },
]
const EDGES = [
  { id: 10, name: 'N-S', source: 1, target: 2, health: 'healthy', length_km: 22.5, fiber_count: 36, occupancy: null },
  { id: 11, name: 'S-N 2', source: 2, target: 1, health: 'critical', length_km: null, fiber_count: null, occupancy: null },
  { id: 12, name: 'N-L', source: 1, target: 3, health: 'unknown', length_km: 5, fiber_count: 12, occupancy: { registered: 12, used: 4, free: 8, broken: 0 } },
]

afterEach(() => vi.restoreAllMocks())

describe('topologyLayout', () => {
  it('norte fica em cima, leste à direita, tudo dentro do retângulo', () => {
    const p = projectNodes(NODES, { width: 1000, height: 640, padding: 60 })
    expect(p.get(1).y).toBeLessThan(p.get(2).y)
    expect(p.get(3).x).toBeGreaterThan(p.get(1).x)
    for (const { x, y } of p.values()) {
      expect(x).toBeGreaterThanOrEqual(60)
      expect(x).toBeLessThanOrEqual(940)
      expect(y).toBeGreaterThanOrEqual(60)
      expect(y).toBeLessThanOrEqual(580)
    }
    expect(projectNodes(NODES)).toEqual(projectNodes(NODES)) // determinística
  })

  it('um só nó fica ao centro; nó sem coordenadas fica de fora', () => {
    const p = projectNodes([{ id: 1, lat: -10, lng: -50 }, { id: 2, lat: null, lng: -50 }], { width: 100, height: 50 })
    expect(p.get(1)).toEqual({ x: 50, y: 25 })
    expect(p.has(2)).toBe(false)
  })

  it('cabos paralelos entre o mesmo par viram curvas para lados opostos; um só é reta', () => {
    const paths = edgePaths(EDGES, projectNodes(NODES))
    const byId = Object.fromEntries(paths.map((p) => [p.edge.id, p.d]))
    expect(byId[12]).toMatch(/^M [\d.]+ [\d.]+ L /)
    expect(byId[10]).toMatch(/ Q /)
    expect(byId[11]).toMatch(/ Q /)
    expect(byId[10]).not.toBe(byId[11])
  })

  it('capacidade: nunca «0 %» sem fibras cadastradas', () => {
    expect(capacityLabel(EDGES[0])).toBe('36 FO · ocupação sem dados')
    expect(capacityLabel(EDGES[1])).toBe('sem dados')
    expect(capacityLabel(EDGES[2])).toBe('4/12 fibras em uso')
  })
})

describe('TopologyView', () => {
  it('desenha nós e arestas, mostra detalhe e lista o que ficou fora', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            nodes: NODES,
            edges: EDGES,
            unplaced: [{ id: 20, name: 'BRN - BRV', reason: 'as duas pontas no mesmo site (SITE - BARREIRA VELHA)' }],
            strands_registered: 0,
          }),
      }),
    )
    const { default: TopologyView } = await import('@/views/TopologyView.vue')
    const w = mount(TopologyView)
    await flushPromises()
    expect(w.findAll('[data-testid^="node-"]')).toHaveLength(3)
    expect(w.findAll('[data-testid^="edge-"]')).toHaveLength(3)
    expect(w.get('[data-testid="node-1"]').text()).toBe('NORTE')
    await w.get('[data-testid="edge-10"]').trigger('mouseenter')
    const detail = w.get('[data-testid="topology-detail"]').text()
    expect(detail).toContain('N-S')
    expect(detail).toContain('SITE - NORTE ↔ SITE - SUL')
    expect(detail).toContain('36 FO · ocupação sem dados')
    expect(w.get('[data-testid="topology-unplaced"]').text()).toContain('BRN - BRV')
    expect(w.find('[data-testid="topology-no-strands"]').exists()).toBe(true)
    w.unmount()
  })
})
