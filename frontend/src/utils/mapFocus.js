/**
 * Contrato do «abrir no mapa» da busca rápida (EV-0044): a paleta de comandos
 * monta a rota, o Projeto de rede lê a query. Um sítio só para os dois lados.
 * @module mapFocus
 */

export const FOCUS_ROUTE = '/Network/NetworkDesign/';
const FOCUS_TYPES = new Set(['site', 'cable', 'device']);

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
