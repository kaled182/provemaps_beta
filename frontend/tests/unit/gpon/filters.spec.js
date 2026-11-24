/**
 * EV-0105 — recorte por fabricante e por POP: o seletor de OLT, os chassis/cartões, a tabela e
 * os KPIs seguem o recorte; o recorte vai para o endereço (?fabricante=&pop=).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import MonitoringGpon from '@/components/Monitoring/MonitoringGpon.vue'
import { VIEW_KEY, computeTotals } from '@/composables/useGponOverview'
import { NOW, payload, mockFetch } from './fixtures'

const t = (w, id) => w.find(`[data-testid="${id}"]`)
const options = (w, id) => t(w, id).findAll('option').map((o) => o.text())

async function mountView(url = '/monitoring/gpon') {
  window.history.replaceState(null, '', url)
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(NOW)
  mockFetch(payload())
  localStorage.setItem(VIEW_KEY, 'grid')
  const w = mount(MonitoringGpon, { attachTo: document.body })
  await flushPromises()
  return w
}

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
  window.history.replaceState(null, '', '/')
})

describe('filtros por fabricante e POP', () => {
  it('as listas vêm das OLTs do payload', async () => {
    const w = await mountView()
    expect(options(w, 'gpon-vendor-select')).toEqual(['Todos os fabricantes', 'VSOL', 'ZTE'])
    expect(options(w, 'gpon-pop-select')).toEqual(['Todos os POPs', 'BRV', 'NBR'])
    expect(options(w, 'gpon-olt-select')[0]).toBe('Todas as OLTs')
    w.unmount()
  })

  it('fabricante recorta OLTs, POPs, cartões e KPIs, e vai para o endereço', async () => {
    const w = await mountView()
    await t(w, 'gpon-vendor-select').setValue('zte')
    await flushPromises()
    expect(options(w, 'gpon-olt-select')).toEqual(['Todas as OLTs (1)', 'ZTE - OLT BRV C300'])
    expect(options(w, 'gpon-pop-select')).toEqual(['Todos os POPs', 'BRV'])
    expect(w.find('[data-testid="gpon-olt-22"]').exists()).toBe(true)
    expect(w.find('[data-testid="gpon-olt-11"]').exists()).toBe(false)
    expect(w.findAll('[data-testid="gpon-onu-row"]').every((r) => Number(r.attributes('data-onu-id')) < 600)).toBe(true)
    expect(window.location.search).toBe('?fabricante=zte')
    w.unmount()
  })

  it('POP lido do endereço no arranque; trocar de fabricante sem esse POP limpa-o', async () => {
    const w = await mountView('/monitoring/gpon?pop=NBR')
    expect(t(w, 'gpon-pop-select').element.value).toBe('NBR')
    expect(w.find('[data-testid="gpon-olt-11"]').exists()).toBe(true)
    expect(w.find('[data-testid="gpon-olt-22"]').exists()).toBe(false)
    await t(w, 'gpon-vendor-select').setValue('zte')
    await flushPromises()
    expect(t(w, 'gpon-pop-select').element.selectedIndex).toBe(0)
    expect(window.location.search).toBe('?fabricante=zte')
    w.unmount()
  })

  it('a OLT escolhida fora do novo recorte é desmarcada', async () => {
    const w = await mountView()
    await t(w, 'gpon-olt-select').setValue(11)
    await t(w, 'gpon-vendor-select').setValue('zte')
    await flushPromises()
    expect(t(w, 'gpon-olt-select').element.selectedIndex).toBe(0)
    w.unmount()
  })
})

describe('computeTotals', () => {
  it('as mesmas contas do backend sobre o recorte', () => {
    const p = payload()
    const olts = p.olts.filter((o) => o.vendor === 'zte')
    const onus = p.onus.filter((o) => o.device_id === 22)
    const tot = computeTotals(olts, onus)
    expect(Object.keys(tot)).toEqual(Object.keys(p.totals))
    expect(tot.olts).toBe(1)
    expect(tot.onus_provisioned).toBe(onus.length)
    expect(tot.los).toBe(onus.filter((o) => o.reason === 'los').length)
    expect(tot.pons).toBe(olts[0].pons.length)
  })
})
