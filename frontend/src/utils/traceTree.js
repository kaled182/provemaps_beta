/**
 * Rastreamento em árvore (EV-0143): leitura da resposta de `/strands/<id>/trace/tree/`.
 * Nó = {steps, end, km, loss_db, dbm, focus, splitter, branches: [{number, status, customer, dbm, node}]}.
 */

/** Nós do caminho em foco: a raiz e, em cada splitter, o ramo que contém a fibra pedida. */
export function focusPath(tree) {
  const out = []
  let node = tree
  while (node) {
    out.push(node)
    node = (node.branches || []).find((b) => b.node?.focus)?.node || null
  }
  return out
}

/** Passos do caminho em foco, em sequência (da fonte até ao destino). */
export function focusSteps(tree) {
  return focusPath(tree).flatMap((n) => n.steps || [])
}

/** Troços de cabo com geometria para o mapa: {key, path: [{lat, lng}], focus, broken}. */
export function traceSegments(tree) {
  const out = []
  const walk = (node, focus, prefix) => {
    const steps = node.steps || []
    steps.forEach((s, i) => {
      if (s.type !== 'cable' || !s.path?.length) return
      out.push({
        key: `${prefix}-${i}`,
        path: s.path.map(([lng, lat]) => ({ lat, lng })),
        focus: focus && node.focus,
        broken: !!s.broken,
      })
    })
    for (const b of node.branches || []) {
      if (b.node) walk(b.node, focus && node.focus, `${prefix}.${b.number}`)
    }
  }
  if (tree) walk(tree, true, 'r')
  return out
}

/** Último ponto conhecido de um nó (fim do último troço, que vem no sentido da luz, ou caixa/porta). */
function lastPoint(node) {
  for (let i = (node.steps || []).length - 1; i >= 0; i -= 1) {
    const s = node.steps[i]
    if (s.type === 'cable' && s.path?.length) {
      const [lng, lat] = s.path[s.path.length - 1]
      return { lat, lng }
    }
    if (s.lat != null && s.lng != null) return { lat: s.lat, lng: s.lng }
  }
  return null
}

const fmt = (v) => Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
export const fmtDbm = (v) => (v === null || v === undefined ? '' : `${v > 0 ? '+' : ''}${fmt(v)} dBm`)
export const fmtKm = (v) => `${fmt(v || 0)} km`

/**
 * Rótulos do mapa: a fonte, cada splitter (razão + dBm à saída) e o fim de cada ramo (km + dBm).
 * {key, lat, lng, kind: 'source'|'splitter'|'end', focus, text}
 */
export function traceLabels(trace) {
  const out = []
  const tree = trace?.tree
  if (!tree) return out
  const first = tree.steps?.[0]
  if (first?.type === 'port' && first.lat != null) {
    out.push({ key: 'src', lat: first.lat, lng: first.lng, kind: 'source', focus: true, text: `${first.device_name} ${fmtDbm(trace.tx?.dbm)}`.trim() })
  }
  const walk = (node, focus, prefix) => {
    const f = focus && node.focus
    if (node.splitter && node.splitter.lat != null) {
      out.push({
        key: `${prefix}-sp`,
        lat: node.splitter.lat,
        lng: node.splitter.lng,
        kind: 'splitter',
        focus: f,
        text: `${node.splitter.ratio} · ${node.splitter.ceo_name} ${fmtDbm(node.splitter.dbm_out)}`.trim(),
      })
    } else if (!node.splitter) {
      const p = lastPoint(node)
      if (p) out.push({ key: `${prefix}-end`, lat: p.lat, lng: p.lng, kind: 'end', focus: f, text: `${fmtKm(node.km)} ${fmtDbm(node.dbm)}`.trim() })
    }
    for (const b of node.branches || []) {
      if (b.node) walk(b.node, f, `${prefix}.${b.number}`)
    }
  }
  walk(tree, true, 'r')
  return out
}

/** Todos os pontos dos troços, para enquadrar o mapa. */
export function traceBounds(trace) {
  return traceSegments(trace?.tree).flatMap((s) => s.path)
}
