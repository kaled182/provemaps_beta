/**
 * Localizador OTDR (EV-0127) — utilitários puros do frontend. O cálculo vive no backend
 * (`GET /api/v1/inventory/cables/<id>/otdr-locate/`); aqui só formatação e ações de campo.
 * @module otdr
 */

/** Folgas rápidas (% de reserva técnica sobre o traçado). */
export const SLACK_PRESETS = Object.freeze([
  { value: 0, label: '0% Exato' },
  { value: 1.5, label: '1,5% Rural/Backbone' },
  { value: 3, label: '3,0% Urbano' },
])
export const SLACK_MAX = 20

/** metros → «14,85 km» (ou «850 m» abaixo de 1 km). */
export function formatMeters(m) {
  if (m === null || m === undefined || !Number.isFinite(Number(m))) return '—'
  const v = Number(m)
  if (Math.abs(v) < 1000) return `${Math.round(v).toLocaleString('pt-BR')} m`
  return `${(v / 1000).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} km`
}

/** [lng, lat] do backend → «-9.533887, -50.733088» (lat, lng — o formato que o técnico cola). */
export function formatCoords(point) {
  const [lng, lat] = point || []
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return '—'
  return `${lat.toFixed(6)}, ${lng.toFixed(6)}`
}

export function googleMapsUrl(point) {
  const [lng, lat] = point
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
}

/** EV-0130: Street View no ponto (inspeção do poste/rodovia pelo NOC). */
export function streetViewUrl(point) {
  const [lng, lat] = point
  return `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${lat},${lng}`
}

/** EV-0130: passos do ajuste fino em campo (m sobre o traçado). */
export const ADJUST_STEPS = Object.freeze([-500, -100, 100, 500])

export function wazeUrl(point) {
  const [lng, lat] = point
  return `https://waze.com/ul?ll=${lat},${lng}&navigate=yes`
}

/** Mensagem para o técnico de campo (WhatsApp). */
export function whatsappText(r) {
  const from = r.origin?.name || (r.direction === 'ab' ? 'Site A' : 'Site B')
  const to = r.target?.name || (r.direction === 'ab' ? 'Site B' : 'Site A')
  return [
    '*Rompimento de fibra — localização OTDR*',
    `Cabo: ${r.cable_name}`,
    `Sentido: ${from} → ${to}`,
    `Leitura OTDR: ${formatMeters(r.otdr_m)} (folga ${String(r.slack_pct).replace('.', ',')}% → ${formatMeters(r.map_distance_m)} no traçado)`,
    ...(Number(r.offset_m) ? [`Ajuste em campo: ${r.offset_m > 0 ? '+' : ''}${formatMeters(r.offset_m)} sobre o traçado`] : []),
    `Coordenadas: ${formatCoords(r.point)} (±${Math.round(r.tolerance_m)} m)`,
    `Até ${from}: ${formatMeters(r.origin?.distance_m)} · até ${to}: ${formatMeters(r.target?.distance_m)}`,
    `Google Maps: ${googleMapsUrl(r.point)}`,
    `Street View: ${streetViewUrl(r.point)}`,
  ].join('\n')
}
