import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

const instances = []
vi.mock('chart.js/auto', () => ({
  default: vi.fn(function FakeChart(el, config) {
    this.el = el
    this.config = config
    this.data = config.data
    this.options = config.options
    this.destroy = vi.fn()
    this.update = vi.fn()
    this.toBase64Image = vi.fn(() => 'data:image/png;base64,AAA')
    instances.push(this)
  }),
}))

import Chart from 'chart.js/auto'
import TimeSeriesChart from '@/components/charts/TimeSeriesChart.vue'

const series = (points) => [{ label: 'RX', data: points }]

describe('TimeSeriesChart (EV-0011 / EV-0026)', () => {
  beforeEach(() => {
    instances.length = 0
    Chart.mockClear()
  })

  it('cria uma única instância quando há dados e passa x em epoch ms', async () => {
    const wrapper = mount(TimeSeriesChart, {
      props: { series: series([{ x: '2026-10-04T10:00:00Z', y: -21 }, { x: '2026-10-04T10:01:00Z', y: null }]) },
    })
    await nextTick()
    expect(Chart).toHaveBeenCalledTimes(1)
    const ds = instances[0].data.datasets[0]
    expect(ds.data[0].x).toBe(Date.parse('2026-10-04T10:00:00Z'))
    expect(ds.data[1].y).toBeNull() // buraco preservado
    expect(ds.spanGaps).toBe(false)
    expect(instances[0].options.scales.x.type).toBe('linear')
    expect(wrapper.find('canvas').exists()).toBe(true)
  })

  it('atualiza a instância existente em vez de criar outra quando a série muda', async () => {
    const wrapper = mount(TimeSeriesChart, { props: { series: series([{ x: 1, y: 1 }]) } })
    await nextTick()
    await wrapper.setProps({ series: series([{ x: 1, y: 1 }, { x: 2, y: 2 }]) })
    await nextTick()
    expect(Chart).toHaveBeenCalledTimes(1)
    expect(instances[0].update).toHaveBeenCalledWith('none')
    expect(instances[0].data.datasets[0].data).toHaveLength(2)
  })

  it('mostra a mensagem de vazio (sem canvas, sem Chart) quando não há valores', async () => {
    const wrapper = mount(TimeSeriesChart, {
      props: { series: series([{ x: 1, y: null }]), emptyMessage: 'Nada aqui' },
    })
    await nextTick()
    expect(Chart).not.toHaveBeenCalled()
    expect(wrapper.find('canvas').exists()).toBe(false)
    expect(wrapper.text()).toContain('Nada aqui')
  })

  it('destrói o gráfico quando os dados somem e quando o componente desmonta', async () => {
    const wrapper = mount(TimeSeriesChart, { props: { series: series([{ x: 1, y: 1 }]) } })
    await nextTick()
    const first = instances[0]
    await wrapper.setProps({ series: [] })
    await nextTick()
    expect(first.destroy).toHaveBeenCalled()
    await wrapper.setProps({ series: series([{ x: 5, y: 5 }]) })
    await nextTick()
    const second = instances[instances.length - 1]
    wrapper.unmount()
    expect(second.destroy).toHaveBeenCalled()
  })

  it('desenha limiares como datasets tracejados do primeiro ao último x', async () => {
    mount(TimeSeriesChart, {
      props: {
        series: series([{ x: 10, y: -20 }, { x: 30, y: -22 }]),
        thresholds: [{ value: -24, label: 'Atenção' }, { value: -27, label: 'Crítico' }],
        unit: 'dBm',
      },
    })
    await nextTick()
    const datasets = instances[0].data.datasets
    expect(datasets).toHaveLength(3)
    expect(datasets[1].borderDash).toEqual([6, 4])
    expect(datasets[1].data).toEqual([{ x: 10, y: -24 }, { x: 30, y: -24 }])
    expect(datasets[2].label).toBe('Crítico')
  })

  it('expõe toDataURL para os exports', async () => {
    const wrapper = mount(TimeSeriesChart, { props: { series: series([{ x: 1, y: 1 }]) } })
    await nextTick()
    expect(wrapper.vm.toDataURL()).toMatch(/^data:image\/png/)
  })
})
