/**
 * Projeto de Rede (EV-0138): sites, CEOs e reservas técnicas desenhados por cima dos cabos,
 * e o snap dos pontos do traçado nesses objetos.
 */
import { ref } from 'vue'
import { useApi } from '@/composables/useApi'

export const SNAP_PX = 18

export function useDesignPoints() {
  const api = useApi()
  const sites = ref([])
  const ceos = ref([])
  const slacks = ref([])
  const ctos = ref([])
  const poles = ref([])
  const error = ref('')

  const asList = (body) => (Array.isArray(body) ? body : body?.results || [])

  async function load() {
    const [s, c, k, t, p] = await Promise.allSettled([
      api.get('/api/v1/sites/', { page_size: 1000 }),
      api.get('/api/v1/inventory/ceos/'),
      api.get('/api/v1/inventory/slacks/'),
      api.get('/api/v1/inventory/ctos/'),
      api.get('/api/v1/inventory/poles/'),
    ])
    sites.value =
      s.status === 'fulfilled'
        ? asList(s.value)
            .map((x) => ({ id: x.id, name: x.name, lat: Number.parseFloat(x.latitude), lng: Number.parseFloat(x.longitude) }))
            .filter((x) => Number.isFinite(x.lat) && Number.isFinite(x.lng))
        : []
    ceos.value = c.status === 'fulfilled' ? asList(c.value).filter((x) => Array.isArray(x?.point)) : []
    slacks.value = k.status === 'fulfilled' ? asList(k.value).filter((x) => Array.isArray(x?.point)) : []
    const pointsOf = (r) => (r.status === 'fulfilled' ? asList(r.value).filter((x) => Array.isArray(x?.point)) : [])
    ctos.value = pointsOf(t)
    poles.value = pointsOf(p)
    const failed = [s, c, k, t, p].filter((r) => r.status === 'rejected')
    error.value = failed.length ? failed[0].reason?.message || 'erro ao carregar' : ''
  }

  /** Site, CEO, CTO ou poste a menos de SNAP_PX do ponto (em pixéis do ecrã), ou null. */
  function snap(map, lat, lng) {
    if (!map?.latLngToPixel) return null
    const p = map.latLngToPixel({ lat, lng })
    if (!p) return null
    let best = null
    const candidates = [
      ...sites.value.map((s) => ({ lat: s.lat, lng: s.lng, kind: 'site', name: s.name })),
      ...ceos.value.map((c) => ({ lat: c.point[1], lng: c.point[0], kind: 'ceo', name: c.name })),
      ...ctos.value.map((c) => ({ lat: c.point[1], lng: c.point[0], kind: 'cto', name: c.name })),
      ...poles.value.map((c) => ({ lat: c.point[1], lng: c.point[0], kind: 'pole', name: c.name })),
    ]
    for (const c of candidates) {
      const q = map.latLngToPixel({ lat: c.lat, lng: c.lng })
      if (!q) continue
      const d = Math.hypot(q.x - p.x, q.y - p.y)
      if (d <= SNAP_PX && (best === null || d < best.d)) best = { ...c, d }
    }
    return best ? { lat: best.lat, lng: best.lng, snapped: best.kind, name: best.name } : null
  }

  return { sites, ceos, slacks, ctos, poles, error, load, snap }
}
