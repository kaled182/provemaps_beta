/**
 * Disposição da topologia (EV-0060, ADR 0009): projeção equiretangular das
 * coordenadas dos POPs num retângulo SVG, com correção de latitude, e caminhos
 * das arestas (retas; cabos paralelos entre o mesmo par afastados em curva).
 * @module topologyLayout
 */

/**
 * @param {{id, lat, lng}[]} nodes
 * @param {{width?: number, height?: number, padding?: number}} box
 * @returns {Map<id, {x: number, y: number}>}
 */
export function projectNodes(nodes, { width = 1000, height = 640, padding = 60 } = {}) {
  const placed = new Map()
  const valid = (nodes || []).filter((n) => Number.isFinite(n.lat) && Number.isFinite(n.lng))
  if (!valid.length) return placed
  const meanLat = valid.reduce((s, n) => s + n.lat, 0) / valid.length
  const kx = Math.cos((meanLat * Math.PI) / 180) // 1° de longitude encolhe com a latitude
  const xs = valid.map((n) => n.lng * kx)
  const ys = valid.map((n) => n.lat)
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
  const spanX = maxX - minX || 1
  const spanY = maxY - minY || 1
  const scale = Math.min((width - 2 * padding) / spanX, (height - 2 * padding) / spanY)
  // centra o desenho no retângulo
  const offX = (width - spanX * scale) / 2
  const offY = (height - spanY * scale) / 2
  valid.forEach((n, i) => {
    const x = maxX === minX ? width / 2 : offX + (xs[i] - minX) * scale
    const y = maxY === minY ? height / 2 : offY + (maxY - ys[i]) * scale // norte para cima
    placed.set(n.id, { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10 })
  })
  return placed
}

/**
 * Caminho SVG de cada aresta. A k-ésima de n arestas entre o mesmo par curva para
 * um lado alternado, a distância crescente; uma só aresta é uma reta.
 * @returns {{edge, d: string, mid: {x, y}}[]}
 */
export function edgePaths(edges, positions, { spread = 26 } = {}) {
  const groups = new Map()
  for (const e of edges || []) {
    const key = [e.source, e.target].sort().join('|')
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(e)
  }
  const out = []
  for (const list of groups.values()) {
    list.forEach((edge, k) => {
      const a = positions.get(edge.source)
      const b = positions.get(edge.target)
      if (!a || !b) return
      const n = list.length
      const offset = n === 1 ? 0 : (k - (n - 1) / 2) * spread
      const mx = (a.x + b.x) / 2
      const my = (a.y + b.y) / 2
      if (!offset) {
        out.push({ edge, d: `M ${a.x} ${a.y} L ${b.x} ${b.y}`, mid: { x: mx, y: my } })
        return
      }
      const dx = b.x - a.x
      const dy = b.y - a.y
      const len = Math.hypot(dx, dy) || 1
      // ponto de controlo na perpendicular ao segmento
      const cx = mx + (-dy / len) * offset * 2
      const cy = my + (dx / len) * offset * 2
      out.push({ edge, d: `M ${a.x} ${a.y} Q ${cx} ${cy} ${b.x} ${b.y}`, mid: { x: (mx + cx) / 2, y: (my + cy) / 2 } })
    })
  }
  return out
}

/** Texto de capacidade: nunca «0 %» sem fibras cadastradas. */
export function capacityLabel(edge) {
  if (edge.occupancy) {
    const { used, registered } = edge.occupancy
    return `${used}/${registered} fibras em uso`
  }
  if (edge.fiber_count) return `${edge.fiber_count} FO · ocupação sem dados`
  return 'sem dados'
}
