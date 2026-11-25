/**
 * KPIs do HUD do mapa (EV-0048) e filtros que os cards aplicam.
 *
 * Contam só o que está no mapa (itens selecionados). Nada é estimado: um
 * estado que o Zabbix ainda não deu conta como «desconhecido», não como online.
 * @module mapKpis
 */

const DEVICE_DOWN = new Set(['offline', 'critical']);
const DEVICE_UP = new Set(['online', 'warning']);
const CABLE_CRITICAL = new Set(['down', 'offline', 'critical']);
const CABLE_ATTENTION = new Set(['degraded', 'warning']);
const CABLE_HEALTHY = new Set(['up', 'online']);

export const KPI_FILTERS = Object.freeze({
  SITES_OFFLINE: 'sites-offline',
  LINKS_PROBLEM: 'links-problem',
});

function siteKey(device) {
  return String(device.site ?? device.site_id ?? `device-${device.id}`);
}

/**
 * Estado por site: offline se todos os equipamentos com estado conhecido estão
 * em baixo; online se algum responde; desconhecido sem nenhum estado.
 * @returns {Map<string, 'online'|'offline'|'unknown'>}
 */
export function siteStatuses(devices) {
  const bySite = new Map();
  for (const d of devices) {
    const key = siteKey(d);
    const entry = bySite.get(key) || { up: 0, down: 0 };
    if (DEVICE_UP.has(d.status)) entry.up += 1;
    else if (DEVICE_DOWN.has(d.status)) entry.down += 1;
    bySite.set(key, entry);
  }
  const out = new Map();
  bySite.forEach(({ up, down }, key) => {
    out.set(key, up > 0 ? 'online' : down > 0 ? 'offline' : 'unknown');
  });
  return out;
}

/** Categoria de um cabo para o HUD. */
export function cableHealth(status) {
  if (CABLE_CRITICAL.has(status)) return 'critical';
  if (CABLE_ATTENTION.has(status)) return 'attention';
  if (CABLE_HEALTHY.has(status)) return 'healthy';
  return 'unknown';
}

/**
 * @param {{devices: object[], cables: object[], selectedDeviceIds?: Iterable, selectedCableIds?: Iterable}} input
 */
export function computeMapKpis({ devices = [], cables = [], selectedDeviceIds, selectedCableIds }) {
  const devSel = selectedDeviceIds ? new Set(selectedDeviceIds) : null;
  const cabSel = selectedCableIds ? new Set(selectedCableIds) : null;
  const onMapDevices = devSel ? devices.filter((d) => devSel.has(d.id)) : devices;
  const onMapCables = cabSel ? cables.filter((c) => cabSel.has(c.id)) : cables;

  const sites = { online: 0, offline: 0, unknown: 0, total: 0 };
  siteStatuses(onMapDevices).forEach((status) => {
    sites[status] += 1;
    sites.total += 1;
  });

  const links = { healthy: 0, attention: 0, critical: 0, unknown: 0, total: onMapCables.length };
  for (const c of onMapCables) links[cableHealth(c.status)] += 1;

  return { sites, links };
}

/** O equipamento passa no filtro do card? Sem filtro, passa sempre. */
export function deviceMatchesKpiFilter(device, filter, statusBySite) {
  if (filter !== KPI_FILTERS.SITES_OFFLINE) return true;
  return statusBySite.get(siteKey(device)) === 'offline';
}

/** O cabo passa no filtro do card? Sem filtro, passa sempre. */
export function cableMatchesKpiFilter(cable, filter) {
  if (filter !== KPI_FILTERS.LINKS_PROBLEM) return true;
  const health = cableHealth(cable.status);
  return health === 'critical' || health === 'attention';
}

/** «há 5 s», «há 3 min», «há 2 h»; `null` sem data. */
export function formatAgo(date, now = Date.now()) {
  if (!date) return null;
  const secs = Math.max(0, Math.round((now - date.getTime()) / 1000));
  if (secs < 60) return `há ${secs} s`;
  if (secs < 3600) return `há ${Math.floor(secs / 60)} min`;
  return `há ${Math.floor(secs / 3600)} h`;
}
