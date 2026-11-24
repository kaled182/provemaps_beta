/**
 * Regras puras do chassi da OLT (EV-0101): cor dos LEDs, texto do tooltip, estado e
 * diagnóstico do inspetor. Só factos do payload — o que não existe é «—» (§2.1).
 *
 * Estados de LED (viram a classe `led-<estado>` nos SVG):
 * - `off`      apagado (neutral)
 * - `unknown`  apagado com contorno tracejado (estado da porta não coletado)
 * - `ok`       success · `warning` warning · `critical` danger (pulsa)
 */
import { formatCompact, formatDbm, formatInt, formatPercent } from '@/utils/ptBrFormat'
import { OCCUPANCY_LIMIT } from '@/composables/useGponOverview'

/** Papéis de placa que têm portas PON. */
export const PON_ROLE = 'pon'

/** Índice `pon_id → pon` das PONs de uma OLT. */
export function indexPons(pons) {
  const idx = new Map()
  for (const p of pons || []) idx.set(String(p.pon_id), p)
  return idx
}

/** LED de uma porta PON: sem PON ou sem ONUs → off; depois a severity do backend. */
export function ponLed(pon) {
  if (!pon || !(pon.onus_provisioned > 0)) return 'off'
  if (pon.severity === 'critical') return 'critical'
  if (pon.severity === 'warning') return 'warning'
  return 'ok'
}

/** LED de porta de uplink/controlo: up → ok; down → off (pode ser porta sem uso); unknown → tracejado. */
export function linkLed(status) {
  if (status === 'up') return 'ok'
  if (status === 'down') return 'off'
  return 'unknown'
}

/** LED de qualquer porta, consoante o papel da placa. */
export function portLed(port, role, ponIdx) {
  return role === PON_ROLE ? ponLed(ponIdx.get(String(port.port_id))) : linkLed(port.status)
}

/** PONs (do índice) que pertencem a um slot: pon_id «<slot>/…». */
export function slotPons(slot, ponIdx) {
  const prefix = `${slot}/`
  return [...ponIdx.values()].filter((p) => String(p.pon_id).startsWith(prefix))
}

/**
 * LEDs da placa: PWR = in_service (true ok, false critical, null off); RUN = ok se em serviço;
 * ALM = critical se alguma PON da placa está critical; MS só em controlo («M» ativa, «S» reserva).
 */
export function cardLeds(slot, ponIdx) {
  const inService = slot.in_service
  const pwr = inService === true ? 'ok' : inService === false ? 'critical' : 'off'
  const run = inService === true ? 'ok' : 'off'
  const alarmed = slot.role === PON_ROLE && slotPons(slot.slot, ponIdx).some((p) => p.severity === 'critical')
  let ms = null
  if (slot.role === 'control') ms = slot.standby === 'active' ? 'M' : slot.standby === 'standby' ? 'S' : null
  return { pwr, run, alm: alarmed ? 'critical' : 'off', ms }
}

const attentionOf = (pon) => (pon?.signal_warning ?? 0) + (pon?.signal_critical ?? 0)

/** Texto do tooltip e do aria-label de uma porta PON. */
export function ponTooltip(portId, pon, status = null) {
  if (!pon) {
    const down = status === 'down' ? ' · porta em baixo' : ''
    return `PON ${portId} · sem ONUs${down}`
  }
  const parts = [
    pon.label || `PON ${portId}`,
    `${formatInt(pon.onus_provisioned)}/${formatInt(pon.capacity)} ONUs`,
    `RX méd: ${formatDbm(pon.rx_avg_dbm)}`,
  ]
  if (pon.los > 0) parts.push(`${formatInt(pon.los)} LOS`)
  const att = attentionOf(pon)
  if (att > 0) parts.push(`${formatInt(att)} atenção`)
  return parts.join(' · ')
}

/** Texto do tooltip de uma porta de uplink/controlo. */
export function linkTooltip(portId, role, status) {
  const kind = role === 'control' ? 'Controlo' : role === 'uplink' ? 'Uplink' : 'Porta'
  const label = { up: 'up', down: 'down' }[status] || 'estado desconhecido'
  return `${kind} ${portId} · ${label}`
}

/**
 * Estado da porta no inspetor: { label, tone } com tone = success|warning|danger|neutral.
 * Ordem: queda massiva > porta em baixo > sem ONUs > atenção óptica > operacional.
 */
export function ponState(pon, status = null) {
  if (pon?.collective_drop) return { label: 'Queda massiva', tone: 'danger' }
  if ((pon?.status ?? status) === 'down') return { label: 'Porta em baixo', tone: 'danger' }
  if (!pon || !(pon.onus_provisioned > 0)) return { label: 'Sem ONUs', tone: 'neutral' }
  // severity warning só por ocupação ou dying gasp não é óptica: o LED mostra-a, o estado não.
  if (pon.severity === 'critical' || (pon.los ?? 0) > 0 || attentionOf(pon) > 0) {
    return { label: 'Atenção óptica', tone: 'warning' }
  }
  // O LED fica âmbar também por ocupação (> 85 %): o estado tem de dizer porquê.
  if ((pon.occupancy_pct ?? 0) > OCCUPANCY_LIMIT) return { label: 'Ocupação alta', tone: 'warning' }
  return { label: 'Operacional', tone: 'success' }
}

/** Diagnóstico do inspetor — só frases com base em factos do payload. */
export function ponDiagnostics(pon, thresholds, status = null) {
  const out = []
  if (pon?.collective_drop) {
    out.push(
      `Queda massiva: ${formatInt(pon.los)} ONUs em LOS na mesma janela de 10 min — provável rompimento a montante (cabo/fusão/splitter primário).`,
    )
  }
  const att = attentionOf(pon)
  if (att > 0) {
    const limit = thresholds?.warning ?? null
    const below = limit === null ? 'com sinal em atenção' : `com sinal abaixo de ${formatCompact(limit)} dBm`
    out.push(`${formatInt(att)} ONUs ${below} — verificar fusão, conector ou splitter da caixa.`)
  }
  if ((pon?.occupancy_pct ?? 0) > OCCUPANCY_LIMIT) {
    out.push(`Ocupação de ${formatPercent(pon.occupancy_pct)} da capacidade da PON — planear expansão ou balanceamento.`)
  }
  if ((pon?.status ?? status) === 'down') out.push('Porta PON em baixo no Zabbix.')
  return out
}

/** Número do slot com dois dígitos («09»). */
export const slotLabel = (n) => String(n).padStart(2, '0')
