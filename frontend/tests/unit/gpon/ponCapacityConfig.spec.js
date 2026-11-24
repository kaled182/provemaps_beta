/** EV-0095 — capacidade da PON por tecnologia no ecrã de Configuração, gravada com os nomes do backend. */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SystemParamsTab from '@/components/Configuration/SystemParamsTab.vue'
import { ok } from './fixtures'

afterEach(() => vi.restoreAllMocks())

describe('SystemParamsTab — capacidade da PON', () => {
  it('lê GPON_PON_CAPACITY/EPON_PON_CAPACITY e grava os valores editados', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation((url, init = {}) => {
      if (url === '/setup_app/api/config/') {
        return ok({ success: true, configuration: { GPON_PON_CAPACITY: '100', EPON_PON_CAPACITY: '32', OPTICAL_RX_WARNING_THRESHOLD: '-24' } })
      }
      if (url === '/setup_app/api/config/update/' && init.method === 'POST') return ok({ success: true, message: 'ok' })
      return ok({})
    })
    const w = mount(SystemParamsTab, { global: { stubs: { CronTab: true } } })
    await flushPromises()
    await w.findAll('nav button').find((b) => b.text() === 'Serviços').trigger('click')

    const gpon = w.find('[data-testid="cfg-gpon-pon-capacity"]')
    const epon = w.find('[data-testid="cfg-epon-pon-capacity"]')
    expect(gpon.element.value).toBe('100')
    expect(epon.element.value).toBe('32')
    await gpon.setValue('120')
    await epon.setValue('48')

    const save = w.findAll('button').find((b) => b.text().includes('Salvar') && !b.attributes('disabled'))
    await save.trigger('click')
    await flushPromises()
    const post = spy.mock.calls.find(([u, i]) => u === '/setup_app/api/config/update/' && i?.method === 'POST')
    const body = JSON.parse(post[1].body)
    expect(Number(body.GPON_PON_CAPACITY)).toBe(120)
    expect(Number(body.EPON_PON_CAPACITY)).toBe(48)
    w.unmount()
  })
})
