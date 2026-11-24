/**
 * Contrato do «abrir no mapa» da busca rápida (EV-0044): a paleta de comandos
 * monta a rota, o Projeto de rede lê a query. Um sítio só para os dois lados.
 * @module mapFocus
 */

export const FOCUS_ROUTE = '/Network/NetworkDesign/';
const FOCUS_TYPES = new Set(['site', 'cable', 'device', 'ceo']);

/** Resultado de `/api/v1/inventory/search/` → location do vue-router, ou `null` sem coordenadas. */
export function buildFocusLocation(result) {
  if (!result || result.lat == null || result.lng == null) return null;
  return {
    path: FOCUS_ROUTE,
    query: {
      foco: result.type,
      id: String(result.id),
      lat: String(result.lat),
      lng: String(result.lng),
      nome: result.name || '',
    },
  };
}

/** `route.query` → item no formato da busca (`{type, id, lat, lng, name}`), ou `null`. */
export function parseFocusQuery(query = {}) {
  const type = query.foco;
  if (!FOCUS_TYPES.has(type)) return null;
  const lat = Number.parseFloat(query.lat);
  const lng = Number.parseFloat(query.lng);
  const id = Number.parseInt(query.id, 10);
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) {
    return null;
  }
  if (!Number.isFinite(id)) return null;
  return { type, id, lat, lng, name: typeof query.nome === 'string' ? query.nome : '' };
}

/**
 * EV-0137: «Editar no Projeto ↗» a partir de um objeto do mapa de monitoramento.
 * site: latitude/longitude; cable: ponto do meio do traçado (`path_coordinates`); ceo: `point` [lng, lat].
 * Devolve a location do vue-router (mesmo contrato do Ctrl K) ou `null` sem coordenadas.
 */
export function focusLocationFor(type, obj) {
  if (!obj) return null;
  let lat = null;
  let lng = null;
  if (type === 'site') {
    lat = obj.latitude ?? obj.lat;
    lng = obj.longitude ?? obj.lng;
  } else if (type === 'cable') {
    const path = (obj.path_coordinates || []).filter((p) => p && p.lat != null && p.lng != null);
    const mid = path[Math.floor(path.length / 2)];
    if (mid) ({ lat, lng } = mid);
  } else if (type === 'ceo' && Array.isArray(obj.point)) {
    [lng, lat] = obj.point;
  }
  const latN = Number.parseFloat(lat);
  const lngN = Number.parseFloat(lng);
  if (!Number.isFinite(latN) || !Number.isFinite(lngN)) return null;
  return buildFocusLocation({ type, id: obj.id, name: obj.name || obj.display_name || '', lat: latN, lng: lngN });
}

