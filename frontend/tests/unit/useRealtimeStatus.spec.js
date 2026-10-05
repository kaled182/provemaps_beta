import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, nextTick } from 'vue'

const wsState = {}
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: vi.fn((url, options) => {
    wsState.url = url
    wsState.options = options
    wsState.lastMessage = ref(null)
    wsState.connect = vi.fn()
    wsState.disconnect = vi.fn()
    return {
      connected: ref(false), connecting: ref(false), error: ref(null), reconnectAttempts: ref(0),
      lastMessage: wsState.lastMessage, connect: wsState.connect, disconnect: wsState.disconnect,
    }
  }),
}))

import { normalizeRealtimeMessage, availabilityToStatus, useRealtimeStatus } from '@/composables/useRealtimeStatus'
import { useWebSocket } from '@/composables/useWebSocket'

describe('normalizeRealtimeMessage (EV-0014)', () => {
  it('entende o evento dashboard.status que o backend publica', () => {
    const out = normalizeRealtimeMessage({
      event: 'dashboard.status',
      data: { summary: {}, hosts: [{ hostid: '10101', device_id: 7, name: 'SW-01', available: '1' }, { hostid: '10102', available: '2' }] },
    })
    expect(out.kind).toBe('hosts')
    expect(out.hosts).toHaveLength(2)
    expect(out.hosts[0]).toMatchObject({ device_id: 7, host_id: '10101', status: 'online' })
    expect(out.hosts[1].status).toBe('offline')
  })

  it('entende cable_status_update', () => {
    const out = normalizeRealtimeMessage({ type: 'cable_status_update', cables: [{ cable_id: 3, status: 'critical' }, { id: 4, status: 'online' }, null] })
    expect(out.kind).toBe('cables')
    expect(out.cables.map(c => [c.cable_id, c.status])).toEqual([[3, 'critical'], [4, 'online']])
  })

  it('mantém compatibilidade com host_update/dashboard_snapshot do store', () => {
    expect(normalizeRealtimeMessage({ type: 'host_update', host_id: 1, status: 'online' }).hosts[0].status).toBe('online')
    expect(normalizeRealtimeMessage({ type: 'dashboard_snapshot', hosts: [{ id: 9, available: '2' }] }).hosts[0].status).toBe('offline')
  })

  it('devolve kind null para lixo', () => {
    expect(normalizeRealtimeMessage(null).kind).toBeNull()
    expect(normalizeRealtimeMessage({ type: 'outra_coisa' }).kind).toBeNull()
    expect(availabilityToStatus('9', 'x')).toBe('x')
  })
})

describe('useRealtimeStatus', () => {
  beforeEach(() => { useWebSocket.mockClear() })

  it('não liga sozinho e atualiza os mapas de estado a partir das mensagens', async () => {
    const rt = useRealtimeStatus()
    expect(useWebSocket).toHaveBeenCalledTimes(1)
    expect(wsState.options.autoConnect).toBe(false)
    expect(wsState.url).toMatch(/\/ws\/dashboard\/status\/$/)

    const seenHosts = vi.fn()
    rt.onHosts(seenHosts)
    wsState.lastMessage.value = { event: 'dashboard.status', data: { hosts: [{ device_id: 7, available: '2' }] } }
    await nextTick()
    expect(rt.deviceStatus.value.get('7')).toBe('offline')
    expect(seenHosts).toHaveBeenCalledTimes(1)

    wsState.lastMessage.value = { type: 'cable_status_update', cables: [{ cable_id: 3, status: 'warning' }] }
    await nextTick()
    expect(rt.cableStatus.value.get('3')).toBe('warning')
    expect(rt.lastUpdate.value).toBeInstanceOf(Date)

    rt.connect(); rt.disconnect()
    expect(wsState.connect).toHaveBeenCalled()
    expect(wsState.disconnect).toHaveBeenCalled()
  })
})
