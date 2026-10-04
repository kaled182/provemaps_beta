/**
 * Estado em tempo real vindo do WebSocket `/ws/dashboard/status/` (EV-0014).
 *
 * O backend publica DOIS formatos (maps_view/realtime):
 *  - `{ event: 'dashboard.status', data: { summary, hosts: [hosts_status…] } }`
 *  - `{ type: 'cable_status_update', cables: [{ cable_id, status, … }] }`
 * e o frontend tinha três consumidores a esperar formatos que nunca chegavam
 * (`host_update`/`dashboard_snapshot` no store, `data.devices` no SiteDetailsModal)
 * enquanto o mapa fazia polling de 30 s. Este módulo é o único lugar que conhece
 * o contrato e devolve algo simples: mapas `device_id → status` e `cable_id → status`.
 */
import { ref, watch } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

export const DASHBOARD_WS_PATH = '/ws/dashboard/status/'

export function dashboardWsUrl() {
  if (typeof window === 'undefined') return DASHBOARD_WS_PATH
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${DASHBOARD_WS_PATH}`
}

/** Zabbix `available`: '1' online, '2' offline, resto desconhecido. */
export function availabilityToStatus(available, fallback = 'unknown') {
  const s = String(available ?? '').trim()
  if (s === '1') return 'online'
  if (s === '2') return 'offline'
  return fallback
}

/**
 * Normaliza qualquer mensagem do canal.
 * @returns {{ kind: 'hosts'|'cables'|null, hosts: Array, cables: Array, timestamp: string|number|null }}
 */
export function normalizeRealtimeMessage(message) {
  const empty = { kind: null, hosts: [], cables: [], timestamp: null }
  if (!message || typeof message !== 'object') return empty

  const event = message.event || message.type

  if (event === 'dashboard.status' || event === 'dashboard_snapshot') {
    const raw = Array.isArray(message.data?.hosts)
      ? message.data.hosts
      : Array.isArray(message.hosts)
        ? message.hosts
        : []
    const hosts = raw
      .filter(Boolean)
      .map((h) => ({
        device_id: h.device_id ?? null,
        host_id: h.hostid ?? h.host_id ?? h.id ?? null,
        name: h.name ?? null,
        status: h.status && !/^\d+$/.test(String(h.status)) ? h.status : availabilityToStatus(h.available, 'unknown'),
        raw: h,
      }))
    return { kind: 'hosts', hosts, cables: [], timestamp: message.timestamp ?? null }
  }

  if (event === 'host_update') {
    const { host_id, device_id, status, available, ...rest } = message
    return {
      kind: 'hosts',
      hosts: [{ device_id: device_id ?? null, host_id: host_id ?? null, name: rest.name ?? null, status: status || availabilityToStatus(available), raw: message }],
      cables: [],
      timestamp: message.timestamp ?? null,
    }
  }

  if (event === 'cable_status_update' || event === 'cable.status') {
    const cables = (Array.isArray(message.cables) ? message.cables : [])
      .filter((c) => c && (c.cable_id ?? c.id) !== undefined)
      .map((c) => ({ cable_id: c.cable_id ?? c.id, status: c.status ?? 'unknown', raw: c }))
    return { kind: 'cables', hosts: [], cables, timestamp: message.timestamp ?? null }
  }

  return empty
}

/**
 * Composable: liga ao canal e mantém `deviceStatus` (Map device_id→status) e
 * `cableStatus` (Map cable_id→status) atualizados. `autoConnect` desligado por
 * omissão — quem usa decide quando ligar (ao abrir o modal, ao ter o mapa pronto).
 */
export function useRealtimeStatus(options = {}) {
  const { autoConnect = false, reconnectDelay = 5000, maxReconnectAttempts = 10 } = options
  const ws = useWebSocket(dashboardWsUrl(), { autoConnect, reconnectDelay, maxReconnectAttempts })

  const deviceStatus = ref(new Map())
  const cableStatus = ref(new Map())
  const lastUpdate = ref(null)
  const hostListeners = new Set()
  const cableListeners = new Set()

  watch(ws.lastMessage, (message) => {
    const normalized = normalizeRealtimeMessage(message)
    if (normalized.kind === 'hosts' && normalized.hosts.length) {
      const next = new Map(deviceStatus.value)
      normalized.hosts.forEach((h) => {
        const key = h.device_id ?? h.host_id
        if (key !== null && key !== undefined) next.set(String(key), h.status)
      })
      deviceStatus.value = next
      lastUpdate.value = new Date()
      hostListeners.forEach((cb) => cb(normalized.hosts, next))
    } else if (normalized.kind === 'cables' && normalized.cables.length) {
      const next = new Map(cableStatus.value)
      normalized.cables.forEach((c) => next.set(String(c.cable_id), c.status))
      cableStatus.value = next
      lastUpdate.value = new Date()
      cableListeners.forEach((cb) => cb(normalized.cables, next))
    }
  })

  return {
    connected: ws.connected,
    connecting: ws.connecting,
    error: ws.error,
    reconnectAttempts: ws.reconnectAttempts,
    connect: ws.connect,
    disconnect: ws.disconnect,
    deviceStatus,
    cableStatus,
    lastUpdate,
    onHosts: (cb) => { hostListeners.add(cb); return () => hostListeners.delete(cb) },
    onCables: (cb) => { cableListeners.add(cb); return () => cableListeners.delete(cb) },
  }
}
