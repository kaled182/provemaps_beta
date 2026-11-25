/**
 * EV-0085 — «Saúde da coleta»: KPIs, listas e tabela de portas a partir do contrato
 * de /api/v1/inventory/collection-health/; «Zabbix fora» ≠ «tudo a ser coletado».
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import CollectionHealthView from '@/views/CollectionHealthView.vue'

const PAYLOAD = {
  generated_at: '2026-11-24T01:30:00Z',
  stale_hours: 2,
  zabbix_ok: true,
  zabbix_error: null,
  totals: { devices: 22, devices_missing_host: 1, devices_without_readings: 1, ports_with_key: 179, ports_reading: 130, ports_problem: 49 },
  devices_missing_host: [{ device_id: 22, device_name: 'OLT BRV', site_name: 'BRV', zabbix_hostid: '10694' }],
  devices_without_readings: [{ device_id: 7, device_name: 'Switch Santa Terezinha', site_name: 'STZ', ports_with_key: 12, ports_reading: 0 }],
  ports: [
    { port_id: 500, port_name: 'XGE0/0/4', device_id: 3, device_name: 'SW A', rx_key: 'k', tx_key: 'k', last_rx_power: -20.1, last_tx_power: null, last_optical_check: '2026-11-24T00:10:00Z', reason: 'item_problem', problem: 'item unsupported' },
    { port_id: 501, port_name: 'XGE0/0/5', device_id: 3, device_name: 'SW A', rx_key: 'k', tx_key: 'k', last_rx_power: null, last_tx_power: null, last_optical_check: null, reason: 'never', problem: null },
  ],
}
const EMPTY = {
  ...PAYLOAD,
  totals: { devices: 5, devices_missing_host: 0, devices_without_readings: 0, ports_with_key: 10, ports_reading: 10, ports_problem: 0 },
  devices_missing_host: [],
  devices_without_readings: [],
  ports: [],
}

function mockFetch(body) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve(body) })
}
async function mountView(body) {
  const spy = mockFetch(body)
  const w = mount(CollectionHealthView)
  await flushPromises()
  return { w, spy }
}
const t = (w, id) => w.find(`[data-testid="${id}"]`)

afterEach(() => vi.restoreAllMocks())

describe('CollectionHealthView', () => {
  it('renderiza KPIs, listas e tabela de portas; o pedido leva stale_hours', async () => {
    const { w, spy } = await mountView(PAYLOAD)
    expect(spy.mock.calls[0][0]).toBe('/api/v1/inventory/collection-health/?stale_hours=2')
    expect(t(w, 'ch-kpi-missing-host').text()).toContain('1')
    expect(t(w, 'ch-kpi-with-key').text()).toContain('179')
    expect(t(w, 'ch-kpi-problem').text()).toContain('49')
    expect(t(w, 'ch-missing-host').text()).toContain('OLT BRV')
    expect(t(w, 'ch-missing-host').text()).toContain('10694')
    expect(t(w, 'ch-no-readings').text()).toContain('Switch Santa Terezinha')
    expect(w.findAll('[data-testid="ch-port-row"]')).toHaveLength(2)
    expect(t(w, 'ch-ports-table').text()).toContain('Item com problema')
    expect(t(w, 'ch-ports-table').text()).toContain('Nunca coletada')
    expect(t(w, 'ch-zabbix-down').exists()).toBe(false)
    expect(t(w, 'ch-all-clear').exists()).toBe(false)
  })

  it('devices_missing_host null mostra «desconhecido», não 0, e a faixa de Zabbix indisponível', async () => {
    const { w } = await mountView({
      ...PAYLOAD,
      zabbix_ok: false,
      zabbix_error: 'timeout',
      totals: { ...PAYLOAD.totals, devices_missing_host: null },
      devices_missing_host: [],
    })
    expect(t(w, 'ch-kpi-missing-host').text()).toContain('desconhecido')
    expect(t(w, 'ch-zabbix-down').text()).toContain('Zabbix indisponível')
    expect(t(w, 'ch-zabbix-down').text()).toContain('timeout')
  })

  it('Zabbix fora nunca mostra «Tudo a ser coletado»', async () => {
    const { w } = await mountView({ ...EMPTY, zabbix_ok: false, zabbix_error: 'x', totals: { ...EMPTY.totals, devices_missing_host: null } })
    expect(t(w, 'ch-all-clear').exists()).toBe(false)
  })

  it('payload vazio mostra «Tudo a ser coletado»', async () => {
    const { w } = await mountView(EMPTY)
    expect(t(w, 'ch-all-clear').text()).toContain('Tudo a ser coletado')
    expect(t(w, 'ch-zabbix-down').exists()).toBe(false)
  })

  it('last_rx_power null mostra «—», nunca 0', async () => {
    const { w } = await mountView(PAYLOAD)
    const cells = w.findAll('[data-testid="ch-port-row"]')[1].findAll('td')
    expect(cells[4].text()).toBe('—')
    expect(cells[5].text()).toBe('—')
    expect(cells[6].text()).toBe('—')
    const first = w.findAll('[data-testid="ch-port-row"]')[0].findAll('td')
    expect(first[4].text()).toBe('-20.1 dBm')
    expect(first[5].text()).toBe('—')
  })

  it('o filtro por motivo e por texto reduz as linhas', async () => {
    const { w } = await mountView(PAYLOAD)
    await t(w, 'ch-reason-filter').setValue('never')
    expect(w.findAll('[data-testid="ch-port-row"]')).toHaveLength(1)
    expect(w.find('[data-testid="ch-port-row"]').text()).toContain('XGE0/0/5')
    await t(w, 'ch-reason-filter').setValue('all')
    await t(w, 'ch-query').setValue('0/0/4')
    expect(w.findAll('[data-testid="ch-port-row"]')).toHaveLength(1)
  })

  it('mudar o seletor de horas volta a pedir com o novo stale_hours', async () => {
    const { w, spy } = await mountView(PAYLOAD)
    await t(w, 'ch-stale-hours').setValue(24)
    await flushPromises()
    expect(spy.mock.calls.at(-1)[0]).toBe('/api/v1/inventory/collection-health/?stale_hours=24')
  })

  it('erro da API aparece como erro, sem KPIs inventados', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: false, status: 500, statusText: 'x', json: () => Promise.resolve({ error: 'falhou' }) })
    const w = mount(CollectionHealthView)
    await flushPromises()
    expect(t(w, 'ch-error').text()).toContain('falhou')
    expect(t(w, 'ch-kpi-problem').exists()).toBe(false)
  })
})
