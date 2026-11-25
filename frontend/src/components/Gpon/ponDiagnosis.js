/**
 * Painel da PON (EV-0107): histograma de saúde óptica, diagnóstico de causa raiz e
 * resumo para OS. Puro (sem Vue) — testado em tests/unit/gpon/ponDiagnosis.spec.js.
 *
 * Regras de causa raiz (pedido do Paulo, 2026-11-24):
 *  - ≥ 3 ONUs em LOS recente (queda OBSERVADA nas últimas 24 h) e nenhuma em dying gasp
 *    → rompimento de ramal ou CTO;
 *  - ≥ 3 ONUs em dying gasp → falta de energia na região;
 *  - RX médio da porta abaixo do limiar de ATENÇÃO da configuração → atenuação generalizada
 *    (decisão do Paulo: o limiar da configuração, não -25 fixo);
 *  - 1–2 ONUs com sinal mau e RX médio bom → drop/conector do cliente.
 * «Recente» exige a hora observada pelo ProVeMaps: uma ONU cuja `status_since` é só a da
 * primeira coleta não sabe quando caiu e não conta como recente (§2.1).
 */
import { formatDbm, formatInt, formatPercent } from '@/utils/ptBrFormat'
import { OCCUPANCY_LIMIT } from '@/composables/useGponOverview'

export const RECENT_HOURS = 24
export const COLLECTIVE_MIN = 3
export const SIGNAL_BANDS = ['normal', 'warning', 'critical']

const dbm = formatDbm
const thr = (v) => (v === null || v === undefined ? null : String(v).replace('.', ','))

/** Histograma (Bom/Atenção/Crítico) das ONUs com sinal medido, rótulos pelos limiares. */
export function ponSignalBands(onus, thresholds) {
  const w = thr(thresholds?.warning)
  const c = thr(thresholds?.critical)
  const counts = { normal: 0, warning: 0, critical: 0 }
  for (const o of onus || []) if (o.signal in counts) counts[o.signal] += 1
  const total = counts.normal + counts.warning + counts.critical
  const labels = {
    normal: w === null ? 'Bom' : `Bom (> ${w} dBm)`,
    warning: w === null || c === null ? 'Atenção' : `Atenção (${w} a ${c} dBm)`,
    critical: c === null ? 'Crítico' : `Crítico (< ${c} dBm)`,
  }
  return SIGNAL_BANDS.map((band) => ({
    band,
    label: labels[band],
    count: counts[band],
    pct: total ? (counts[band] / total) * 100 : 0,
  }))
}

/** ONUs em LOS cuja queda o ProVeMaps viu nas últimas `hours` horas. */
export function recentLos(onus, now = Date.now(), hours = RECENT_HOURS) {
  const since = now - hours * 3600 * 1000
  return (onus || []).filter(
    (o) =>
      o.reason === 'los' &&
      o.status === 'offline' &&
      !o.status_since_is_first_seen &&
      o.status_since &&
      new Date(o.status_since).getTime() >= since,
  )
}

/**
 * Diagnóstico da porta. `pon` = resumo do payload; `onus` = ONUs dessa porta (todas, sem os
 * filtros da tabela). Devolve frases, da mais grave para a menos.
 */
export function ponDiagnostics(pon, thresholds, status = null, onus = [], now = Date.now()) {
  const out = []
  const warn = thresholds?.warning ?? null
  const dyingGasp = (onus || []).filter((o) => o.reason === 'dying_gasp').length || (pon?.dying_gasp ?? 0)
  const losRecent = recentLos(onus, now).length

  if (pon?.collective_drop) {
    out.push(
      `Queda massiva: ${formatInt(pon.los)} ONUs em LOS na mesma janela de 10 min — provável rompimento a montante (cabo/fusão/splitter primário).`,
    )
  } else if (losRecent >= COLLECTIVE_MIN && dyingGasp === 0) {
    out.push(
      `Queda coletiva por perda de sinal (LOS) — ${formatInt(losRecent)} ONUs nas últimas ${RECENT_HOURS} h, sem dying gasp: provável rompimento de ramal ou CTO.`,
    )
  }
  if (dyingGasp >= COLLECTIVE_MIN) {
    out.push(
      `Queda coletiva por falta de energia na região (dying gasp) — ${formatInt(dyingGasp)} ONUs; sem indício de rompimento óptico.`,
    )
  }

  const avg = pon?.rx_avg_dbm ?? null
  const bad = (pon?.signal_warning ?? 0) + (pon?.signal_critical ?? 0)
  if (avg !== null && warn !== null && avg < warn) {
    out.push(
      `Atenuação generalizada na PON — RX médio ${dbm(avg)}, abaixo de ${thr(warn)} dBm: verificar splitter, fusão ou patch cord na OLT.`,
    )
  } else if (bad >= 1 && bad <= 2 && avg !== null && warn !== null) {
    out.push(
      `Atenuação isolada em ${formatInt(bad)} ONU${bad > 1 ? 's' : ''} (drop/conector do cliente) — RX médio da porta ${dbm(avg)}, rede tronco normal.`,
    )
  } else if (bad > 0) {
    const below = warn === null ? 'com sinal em atenção' : `com sinal abaixo de ${thr(warn)} dBm`
    out.push(`${formatInt(bad)} ONUs ${below} — verificar fusão, conector ou splitter da caixa.`)
  }

  if ((pon?.occupancy_pct ?? 0) > OCCUPANCY_LIMIT) {
    out.push(`Ocupação de ${formatPercent(pon.occupancy_pct)} da capacidade da PON — planear expansão ou balanceamento.`)
  }
  if ((pon?.status ?? status) === 'down') out.push('Porta PON em baixo no Zabbix.')
  return out
}

const REASON_TEXT = { los: 'LOS', dying_gasp: 'dying gasp', other: 'offline' }

/** ONUs que entram na OS: offline (com o motivo) e as com sinal em atenção/crítico. */
export function affectedOnus(onus) {
  return (onus || []).filter(
    (o) => o.status === 'offline' || o.signal === 'warning' || o.signal === 'critical',
  )
}

const fmtTime = (iso) =>
  new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

/** Texto técnico para colar no SGP/WhatsApp. Lista no máx. `limit` ONUs. */
export function ponOsSummary({ olt, pon, portId, stateLabel, onus, diagnostics, now = Date.now(), limit = 40 }) {
  const lines = []
  lines.push(`OS — ${olt?.name || 'OLT'}${olt?.site_name ? ` (${olt.site_name})` : ''}`)
  lines.push(`Porta: ${pon?.label || `PON ${portId}`} · estado: ${stateLabel || '—'}`)
  if (pon) {
    lines.push(
      `ONUs: ${formatInt(pon.onus_online)} online de ${formatInt(pon.onus_provisioned)} · LOS ${formatInt(pon.los)} · dying gasp ${formatInt(pon.dying_gasp ?? 0)}`,
    )
    lines.push(`RX médio: ${dbm(pon.rx_avg_dbm)} · pior RX: ${dbm(pon.rx_worst_dbm)}`)
  }
  if (diagnostics?.length) lines.push(`Diagnóstico: ${diagnostics[0]}`)
  const hit = affectedOnus(onus)
  if (hit.length) {
    lines.push(`ONUs afetadas (${hit.length}):`)
    for (const o of hit.slice(0, limit)) {
      const id = o.serial || o.mac || `ONU ${o.onu_index ?? '?'}`
      const what =
        o.status === 'offline'
          ? `${REASON_TEXT[o.reason] || 'offline'}${o.status_since && !o.status_since_is_first_seen ? ` desde ${fmtTime(o.status_since)}` : ''}`
          : `RX ${dbm(o.rx_onu_dbm ?? o.rx_olt_dbm)}`
      const who = o.cliente_nome ? ` · ${o.cliente_nome}` : ''
      lines.push(`- ${id} — ${what}${who}`)
    }
    if (hit.length > limit) lines.push(`… e mais ${hit.length - limit}`)
  } else {
    lines.push('ONUs afetadas: nenhuma')
  }
  lines.push(`Gerado pelo ProVeMaps em ${new Date(now).toLocaleString('pt-BR')}`)
  return lines.join('\n')
}

/** Copia para a área de transferência (com recurso para contexto sem Clipboard API). */
export async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }
  const ta = document.createElement('textarea')
  ta.value = text
  ta.setAttribute('readonly', '')
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  document.execCommand('copy')
  ta.remove()
}
