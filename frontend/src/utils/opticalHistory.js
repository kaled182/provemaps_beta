/**
 * Normalização do histórico óptico (RX/TX em dBm) devolvido por
 * `/api/v1/ports/<id>/optical_history/`.
 *
 * Regra do projeto (CLAUDE.md §2.1, EV-0001): um gráfico sem histórico mostra
 * «sem dados» ou «erro», nunca uma série inventada. Este módulo é a única
 * fonte das mensagens e do formato dos pontos, partilhada pelos modais.
 */

export const OPTICAL_HISTORY_EMPTY_MESSAGE =
  'Sem dados de histórico para o período selecionado'

export const OPTICAL_HISTORY_ERROR_MESSAGE =
  'Não foi possível consultar o histórico óptico (Zabbix indisponível ou erro no servidor)'

const toNumberOrNull = (value) => {
  if (value === null || value === undefined || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

/**
 * Converte a resposta do backend (lista ou `{ history: [...] }`) em pontos
 * `{ timestamp, rx, tx }` ordenados por tempo. Entradas sem timestamp válido
 * ou sem nenhum valor numérico são descartadas.
 *
 * @param {unknown} response
 * @returns {{ points: Array<{timestamp: number, rx: number|null, tx: number|null}>, isEmpty: boolean }}
 */
export function normalizeOpticalHistory(response) {
  const raw = Array.isArray(response)
    ? response
    : Array.isArray(response?.history)
      ? response.history
      : []

  const points = raw
    .map((snapshot) => {
      const ts = new Date(snapshot?.timestamp).getTime()
      if (!Number.isFinite(ts)) return null
      const rx = toNumberOrNull(snapshot.rx_power ?? snapshot.rx)
      const tx = toNumberOrNull(snapshot.tx_power ?? snapshot.tx)
      if (rx === null && tx === null) return null
      return { timestamp: ts, rx, tx }
    })
    .filter(Boolean)
    .sort((a, b) => a.timestamp - b.timestamp)

  return { points, isEmpty: points.length === 0 }
}
