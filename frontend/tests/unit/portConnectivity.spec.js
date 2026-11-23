/**
 * EV-0071 — a porta mostra o cabo ligado e o mapa de conectividade usa a outra ponta
 * real do cabo (rota /api/v1/fiber-cables/), sem fibra inventada.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { otherEnd, cableLengthMeters, linkLossDb } from '@/utils/portConnectivity'
import { normalizePort } from '@/utils/devicePorts'
import ConnectivityMapModal from '@/components/ConnectivityMapModal.vue'
import DevicePortCard from '@/components/DeviceDetails/DevicePortCard.vue'

const CABLE = {
  id: 5,
  name: 'BRV - PLANURA',
  origin_port: 42,
  origin_port_name: 'gpon 1/1',
  origin_device_name: 'OLT BRV',
  destination_port: 77,
  destination_port_name: 'xe-0/0/1',
  destination_device_name: 'SW PLANURA',
  length_km: '12.345',
  fibers: [{ id: 1, number: 1, color: 'azul' }],
}
const ok = (body) => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) })
const q = (sel) => document.body.querySelector(sel)

afterEach(() => {
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

describe('portConnectivity', () => {
  it('a outra ponta depende do lado em que a porta está', () => {
    expect(otherEnd(CABLE, 42)).toEqual({ portId: 77, portName: 'xe-0/0/1', deviceName: 'SW PLANURA' })
    expect(otherEnd(CABLE, 77)).toEqual({ portId: 42, portName: 'gpon 1/1', deviceName: 'OLT BRV' })
    expect(otherEnd({ ...CABLE, destination_port: null }, 42)).toBeNull()
    expect(otherEnd(CABLE, 999)).toBeNull()
  })

  it('extensão em metros e perda; sem leitura → null (0 dBm é leitura)', () => {
    expect(cableLengthMeters(CABLE)).toBe(12345)
    expect(cableLengthMeters({ length_km: null })).toBeNull()
    expect(linkLossDb(0, -20)).toBe(20)
    expect(linkLossDb(null, -20)).toBeNull()
  })

  it('a porta da API com cabo mostra o botão do mapa de conectividade', () => {
    const port = normalizePort({ id: 42, name: 'gpon 1/1', last_rx_power: '-20', cable_id: 5, cable_name: 'BRV - PLANURA' })
    expect(port.connected_cable).toEqual({ id: 5, name: 'BRV - PLANURA' })
    const w = mount(DevicePortCard, { props: { port } })
    expect(w.find('button[title="Mapa de conectividade"]').exists()).toBe(true)
    expect(w.text()).toContain('BRV - PLANURA')
  })
})

describe('ConnectivityMapModal', () => {
  it('lê o cabo em /api/v1/fiber-cables/ e o destino na outra ponta; sem fibra inventada', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (url.startsWith('/api/v1/fiber-cables/5/')) return ok(CABLE)
      if (url.startsWith('/api/v1/ports/77/')) return ok({ id: 77, name: 'xe-0/0/1', device_name: 'SW PLANURA', last_rx_power: '-21.5' })
      return ok({})
    })
    const port = { id: 42, name: 'gpon 1/1', optical_tx_power: 2, optical_rx_power: -19, connected_cable: { id: 5, name: 'BRV - PLANURA' } }
    const w = mount(ConnectivityMapModal, { props: { isOpen: false, port, deviceInfo: { name: 'OLT BRV', ip: '10.0.0.1' } }, attachTo: document.body })
    await w.setProps({ isOpen: true })
    await flushPromises()
    const urls = fetchSpy.mock.calls.map(([u]) => u)
    expect(urls.some((u) => u.startsWith('/api/v1/fiber-cables/5/'))).toBe(true)
    expect(urls.some((u) => u.startsWith('/api/v1/cables/'))).toBe(false)
    const text = document.body.textContent
    expect(text).toContain('SW PLANURA')
    expect(text).toContain('xe-0/0/1')
    expect(text).toContain('-21.50 dBm')
    expect(text).toContain('12345 m')
    expect(text).toContain('23.50') // perda TX 2 → RX -21,5
    expect(text).not.toMatch(/Fibra\s*#?1/) // a 1.ª fibra do cabo não é a da porta
    w.unmount()
  })

  it('cabo sem porta na outra ponta → «Não conectado»', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) =>
      url.startsWith('/api/v1/fiber-cables/5/') ? ok({ ...CABLE, destination_port: null }) : ok({}),
    )
    const port = { id: 42, name: 'gpon 1/1', optical_tx_power: 2, connected_cable: { id: 5 } }
    const w = mount(ConnectivityMapModal, { props: { isOpen: false, port, deviceInfo: { name: 'OLT', ip: '' } }, attachTo: document.body })
    await w.setProps({ isOpen: true })
    await flushPromises()
    expect(document.body.textContent).toContain('Não Conectado')
    w.unmount()
  })
})
