/** EV-0095 — KPIs a partir dos totals e cartões de PON pelas classes de token. */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import GponKpis from '@/components/Gpon/GponKpis.vue'
import PonCard from '@/components/Gpon/PonCard.vue'
import OltCard from '@/components/Gpon/OltCard.vue'
import { payload } from './fixtures'

const t = (w, id) => w.find(`[data-testid="${id}"]`)

describe('GponKpis', () => {
  it('mostra os totals do payload', () => {
    const w = mount(GponKpis, { props: { totals: payload().totals } })
    expect(t(w, 'gpon-kpi-olts').text()).toContain('7')
    expect(t(w, 'gpon-kpi-olts').text()).toContain('/ 9')
    expect(t(w, 'gpon-kpi-olts').text()).toContain('2 offline · 30 PONs')
    expect(t(w, 'gpon-kpi-onus').text()).toContain('140')
    expect(t(w, 'gpon-kpi-onus-pct').text()).toBe('35,0%')
    expect(t(w, 'gpon-kpi-signal').text()).toContain('5')
    expect(t(w, 'gpon-kpi-signal').text()).toContain('+ 12')
    expect(t(w, 'gpon-kpi-los').text()).toContain('3')
    expect(t(w, 'gpon-kpi-los').classes()).not.toContain('kpi-alert')
    expect(t(w, 'gpon-kpi-dying').text()).toContain('10')
  })

  it('contagem desconhecida → «—» e queda em massa destacada', () => {
    const totals = { ...payload().totals, los: null, onus_provisioned: null, pons_collective_drop: 2 }
    const w = mount(GponKpis, { props: { totals } })
    expect(t(w, 'gpon-kpi-los').text()).toContain('—')
    expect(t(w, 'gpon-kpi-onus-pct').text()).toBe('—')
    expect(t(w, 'gpon-kpi-los').classes()).toContain('kpi-alert')
    expect(t(w, 'gpon-kpi-collective').text()).toContain('2 PON em queda em massa')
  })
})

describe('PonCard', () => {
  const [crit, warn, occ] = payload().olts[0].pons

  it('severidade vira classe de token e badge LOS/aten.', () => {
    const c = mount(PonCard, { props: { pon: crit } })
    expect(c.classes()).toContain('pon-critical')
    expect(c.text()).toContain('PON 9/14')
    expect(c.text()).toContain('12/128 ONUs')
    expect(c.text()).toContain('RX méd: -21,3 dBm')
    expect(c.find('.chip-danger').text()).toBe('3 LOS')

    const w = mount(PonCard, { props: { pon: warn } })
    expect(w.classes()).toContain('pon-warning')
    expect(w.find('.chip-warning').text()).toBe('4 aten.')
    expect(t(w, 'gpon-pon-rx').text()).toBe('RX méd: —')

    const o = mount(PonCard, { props: { pon: occ } })
    expect(o.find('.occ-fill').classes()).toContain('bg-warning')
    expect(o.find('.chip-danger').exists()).toBe(false)
  })

  it('selecionada leva anel e emite toggle', async () => {
    const w = mount(PonCard, { props: { pon: crit, selected: true } })
    expect(w.classes()).toContain('pon-selected')
    await w.trigger('click')
    expect(w.emitted('toggle')).toHaveLength(1)
  })
})

describe('OltCard', () => {
  it('null → «—» e aviso de coleta sem dados', () => {
    const [zte, vsol] = payload().olts
    const z = mount(OltCard, { props: { olt: zte } })
    expect(t(z, 'gpon-olt-temp').text()).toContain('—')
    expect(t(z, 'gpon-olt-nodata').exists()).toBe(false)
    const v = mount(OltCard, { props: { olt: vsol } })
    expect(t(v, 'gpon-olt-nodata').text()).toBe('coleta sem dados')
    expect(t(v, 'gpon-olt-temp').text()).toContain('41 °C')
    const off = mount(OltCard, { props: { olt: { ...zte, status: 'offline' } } })
    expect(t(off, 'gpon-olt-offline').text()).toBe('offline')
  })
})
