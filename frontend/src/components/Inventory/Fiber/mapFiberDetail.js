// Utilitário para mapear detalhes de fibra para o objeto usado no modal.
// Facilita testes automatizados.

const normalizeStatus = (status) => {
  if (!status) return 'planned';
  const s = `${status}`.toLowerCase();
  if (['up', 'ativo', 'active', 'iluminado'].includes(s)) return 'active';
  if (['cut', 'rompido'].includes(s)) return 'cut';
  if (['dark', 'apagado'].includes(s)) return 'dark';
  if (['planned', 'em projeto', 'planejado', 'planned/em projeto'].includes(s)) return 'planned';
  return 'planned';
};

const findSiteIdByName = (sites, name) => {
  if (!name) return '';
  const match = (sites || []).find(
    (s) => (s.name || '').toLowerCase() === `${name}`.toLowerCase()
  );
  return match ? match.id : '';
};

export function mapFiberDetailToForm({
  cable,
  detail,
  sites = [],
  originPortInfo = null,
  destPortInfo = null,
}) {
  const merged = { ...cable };
  
  // PRIORIDADE 1: Usar campos enriquecidos do backend (origin_device_id, origin_site_id, etc.)
  // Esses campos são retornados por /api/v1/fiber-cables/{id}/ após as melhorias do serializer
  merged.site_a = cable.origin_site_id || detail?.origin?.site_id || '';
  merged.site_b = cable.destination_site_id || detail?.destination?.site_id || '';
  merged.device_a = cable.origin_device_id || detail?.origin?.device_id || '';
  merged.device_b = cable.destination_device_id || detail?.destination?.device_id || '';
  merged.port_a = cable.origin_port || detail?.origin?.port_id || '';
  merged.port_b = cable.destination_port || detail?.destination?.port_id || '';

  // FALLBACK: Se campos enriquecidos não existirem, tentar mapear por nome (legacy)
  if (!merged.site_a) {
    const originSiteName = detail?.origin?.site || cable.origin_site_name || cable.site_a_name;
    merged.site_a = findSiteIdByName(sites, originSiteName);
  }
  if (!merged.site_b) {
    const destSiteName = detail?.destination?.site || cable.destination_site_name || cable.site_b_name;
    merged.site_b = findSiteIdByName(sites, destSiteName);
  }

  // ENRIQUECIMENTO: Informações adicionais das portas (se disponível)
  if (originPortInfo) {
    merged.device_a = merged.device_a || originPortInfo.device_id || '';
    merged.site_a = merged.site_a || originPortInfo.site_id || '';
  }
  if (destPortInfo) {
    merged.device_b = merged.device_b || destPortInfo.device_id || '';
    merged.site_b = merged.site_b || destPortInfo.site_id || '';
  }

  // Comprimento e metadados
  merged.length = detail?.length_km
    ? Number(detail.length_km) * 1000
    : cable.length_km
      ? Number(cable.length_km) * 1000
      : cable.length || 0;

  merged.status = normalizeStatus(detail?.status || cable.status || 'planned');
  merged.type = cable.type || 'backbone';
  merged.fiber_count = cable.fiber_count || 12;

  // Modo single-port: backend indica quando origem == destino
  merged.single_port = !!(detail?.single_port || cable.single_port);
  // Se single-port e site_b não definido, alinhar ao site_a para evitar validação visual confusa
  if (merged.single_port && !merged.site_b) {
    merged.site_b = merged.site_a;
  }

  return merged;
}

export { normalizeStatus, findSiteIdByName };
