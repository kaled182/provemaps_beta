/** EV-0143 — leitura da árvore de rastreamento e destaque no mapa (TraceOverlay sobre um IMap falso). */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { focusPath, traceLabels, traceSegments, traceBounds } from '@/utils/traceTree'
import TraceOverlay from '@/components/NetworkDesign/design/TraceOverlay.vue'

const leafA = {
  steps: [{ type: 'cable', strand_id: 2, path: [[-50, 0.045], [-49.96, 0.045]] }],
  end: { reason: 'dead_end', label: 'fim A' },
  km: 6, loss_db: 13, dbm: -8, focus: true, splitter: null, branches: [],
}
const leafB = {
  steps: [{ type: 'cable', strand_id: 3, broken: true, path: [[-50, 0.045], [-50, 0.06]] }],
  end: { reason: 'broken', label: 'rompido' },
  km: 7, loss_db: 14, dbm: -9, focus: false, splitter: null, branches: [],
}
const TRACE = {
  source: { found: true, label: 'OLT → gpon 1' },
  tx: { dbm: 5, source: 'padrao' },
  tree: {
    steps: [
      { type: 'port', device_name: 'OLT', lat: 0, lng: -50 },
      { type: 'cable', strand_id: 1, path: [[-50, 0], [-50, 0.045]] },
    ],
    end: { reason: 'splitter', label: 'entra no splitter' },
    km: 5, loss_db: 1.75, dbm: 3.25, focus: true,
    splitter: { ratio: '1x8', ceo_name: 'CEO-04', lat: 0.045, lng: -50, dbm_out: -7.25 },
    branches: [
      { number: 1, node: leafB },
      { number: 2, node: leafA },
      { number: 3, node: null },
    ],
  },
}

describe('traceTree (EV-0143)', () => {
  it('caminho em foco segue o ramo marcado', () => {
    expect(focusPath(TRACE.tree)).toEqual([TRACE.tree, leafA])
  })

  it('troços em {lat, lng}; só o caminho em foco é focus; rompido marcado', () => {
    const segs = traceSegments(TRACE.tree)
    expect(segs.map((s) => [s.focus, s.broken])).toEqual([[true, false], [false, true], [true, false]])
    expect(segs[0].path).toEqual([{ lat: 0, lng: -50 }, { lat: 0.045, lng: -50 }])
    expect(traceBounds(TRACE)).toHaveLength(6)
  })

  it('rótulos: fonte, splitter e fim de cada ramo com km/dBm', () => {
    const l = traceLabels(TRACE)
    expect(l.map((x) => [x.kind, x.text])).toEqual([
      ['source', 'OLT +5,00 dBm'],
      ['splitter', '1x8 · CEO-04 -7,25 dBm'],
      ['end', '7,00 km -9,00 dBm'],
      ['end', '6,00 km -8,00 dBm'],
    ])
    expect(l[3]).toMatchObject({ lat: 0.045, lng: -49.96, focus: true })
    expect(l[2].focus).toBe(false)
  })
})

describe('TraceOverlay (EV-0143)', () => {
  it('desenha uma polilinha por troço (foco mais grosso), enquadra e limpa ao desmontar', () => {
    const lines = []
    const map = {
      createPolyline: vi.fn((o) => {
        const l = { o, remove: vi.fn() }
        lines.push(l)
        return l
      }),
      fitBounds: vi.fn(),
      latLngToPixel: ({ lat, lng }) => ({ x: (lng + 50) * 1000, y: lat * 1000 }),
      on: vi.fn(),
      off: vi.fn(),
    }
    const w = mount(TraceOverlay, { props: { map, trace: TRACE } })
    expect(map.createPolyline).toHaveBeenCalledTimes(3)
    // o de fundo (ramo 1) é desenhado primeiro, os do foco por cima
    expect(lines.map((l) => l.o.strokeWeight)).toEqual([4, 7, 7])
    expect(map.fitBounds).toHaveBeenCalledWith(expect.any(Array), { padding: 130, maxZoom: 17 })
    expect(w.get('[data-testid="trace-panel"]').text()).toContain('OLT → gpon 1')
    expect(w.get('[data-testid="trace-panel-total"]').text().replace(/\s+/g, ' ')).toContain('6,00 km · chega com ≈ -8,00 dBm')
    w.get('[data-testid="trace-clear"]').trigger('click')
    expect(w.emitted('close')).toHaveLength(1)
    w.unmount()
    expect(lines.every((l) => l.remove.mock.calls.length === 1)).toBe(true)
  })
})
