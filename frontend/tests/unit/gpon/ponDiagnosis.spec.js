/**
 * EV-0107 — painel da PON: histograma de saúde óptica, diagnóstico de causa raiz
 * (regras do Paulo), resumo para OS, cópia, filtro por faixa e «Ver no mapa».
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import {
  affectedOnus,
  copyText,
  ponDiagnostics,
  ponOsSummary,
  ponSignalBands,
  recentLos,
} from '@/components/Gpon/ponDiagnosis'
import PonInspector from '@/components/Gpon/PonInspector.vue'
import OnuTable from '@/components/Gpon/OnuTable.vue'
import { useGponOverview } from '@/composables/useGponOverview'
import { NOW, payload, mockFetch } from './fixtures'

const TH = { warning: -24, critical: -27 }
const HOUR = 3600 * 1000
const iso = (msAgo) => new Date(NOW - msAgo).toISOString()
const onu = (over = {}) => ({
  id: 1,
  pon_id: '8/2',
  onu_index: 1,
  serial: 'ZTEG00000001',
  mac: null,
  status: 'online',
  reason: null,
  signal: 'normal',
  rx_onu_dbm: null,
  rx_olt_dbm: -20,
  status_since: iso(HOUR),
  status_since_is_first_seen: false,
  cliente_nome: null,
  ...over,
})
const pon = (over = {}) => ({
  pon_id: '8/2',
  label: 'PON 8/2',
  status: 'up',
  onus_provisioned: 10,
  onus_online: 10,
  occupancy_pct: 15.6,
  rx_avg_dbm: -20.4,
  rx_worst_dbm: -22.1,
  los: 0,
  dying_gasp: 0,
  signal_warning: 0,
  signal_critical: 0,
  collective_drop: false,
  ...over,
})
const los = (id, msAgo, over = {}) =>
  onu({ id, serial: `LOS${id}`, status: 'offline', reason: 'los', signal: null, rx_olt_dbm: null, status_since: iso(msAgo), ...over })

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('histograma de saúde óptica', () => {
  it('conta só ONUs com sinal medido e rotula pelos limiares da configuração', () => {
    const bands = ponSignalBands(
      [onu(), onu({ id: 2 }), onu({ id: 3, signal: 'warning' }), onu({ id: 4, signal: 'critical' }), los(5, HOUR)],
      TH,
    )
    expect(bands.map((b) => [b.band, b.count])).toEqual([['normal', 2], ['warning', 1], ['critical', 1]])
    expect(bands.map((b) => b.label)).toEqual(['Bom (> -24 dBm)', 'Atenção (-24 a -27 dBm)', 'Crítico (< -27 dBm)'])
    expect(bands[0].pct).toBe(50)
    expect(ponSignalBands([], null).map((b) => b.label)).toEqual(['Bom', 'Atenção', 'Crítico'])
  })
})

describe('diagnóstico de causa raiz', () => {
  it('LOS recente só conta quedas OBSERVADAS nas últimas 24 h', () => {
    const list = [los(1, HOUR), los(2, 30 * HOUR), los(3, HOUR, { status_since_is_first_seen: true })]
    expect(recentLos(list, NOW).map((o) => o.id)).toEqual([1])
  })

  it('≥ 3 LOS recentes sem dying gasp → rompimento de ramal/CTO', () => {
    const onus = [los(1, HOUR), los(2, 2 * HOUR), los(3, 3 * HOUR), onu({ id: 4 })]
    expect(ponDiagnostics(pon({ los: 3 }), TH, null, onus, NOW)[0]).toBe(
      'Queda coletiva por perda de sinal (LOS) — 3 ONUs nas últimas 24 h, sem dying gasp: provável rompimento de ramal ou CTO.',
    )
  })

  it('com dying gasp na porta não acusa rompimento; ≥ 3 dying gasp → falta de energia', () => {
    const dg = (id) => onu({ id, status: 'offline', reason: 'dying_gasp', signal: null })
    const onus = [los(1, HOUR), los(2, HOUR), los(3, HOUR), dg(4), dg(5), dg(6)]
    const d = ponDiagnostics(pon({ los: 3, dying_gasp: 3 }), TH, null, onus, NOW)
    expect(d.some((x) => x.includes('rompimento de ramal'))).toBe(false)
    expect(d[0]).toBe(
      'Queda coletiva por falta de energia na região (dying gasp) — 3 ONUs; sem indício de rompimento óptico.',
    )
  })

  it('a queda massiva (janela de 10 min) tem precedência sobre a regra das 24 h', () => {
    const onus = [los(1, HOUR), los(2, HOUR), los(3, HOUR)]
    const d = ponDiagnostics(pon({ los: 3, collective_drop: true }), TH, null, onus, NOW)
    expect(d[0]).toMatch(/^Queda massiva: 3 ONUs em LOS/)
    expect(d.some((x) => x.includes('Queda coletiva por perda de sinal'))).toBe(false)
  })

  it('RX médio abaixo do limiar de ATENÇÃO da configuração → atenuação generalizada', () => {
    const d = ponDiagnostics(pon({ rx_avg_dbm: -25.3, signal_warning: 6 }), TH, null, [], NOW)
    expect(d).toEqual([
      'Atenuação generalizada na PON — RX médio -25,3 dBm, abaixo de -24 dBm: verificar splitter, fusão ou patch cord na OLT.',
    ])
    // o limiar é o da configuração: com -26 configurado o mesmo RX médio já não acusa
    expect(ponDiagnostics(pon({ rx_avg_dbm: -25.3 }), { warning: -26, critical: -28 }, null, [], NOW)).toEqual([])
  })

  it('1–2 ONUs más com RX médio bom → drop/conector do cliente', () => {
    expect(ponDiagnostics(pon({ signal_critical: 1 }), TH, null, [], NOW)).toEqual([
      'Atenuação isolada em 1 ONU (drop/conector do cliente) — RX médio da porta -20,4 dBm, rede tronco normal.',
    ])
    expect(ponDiagnostics(pon({ signal_warning: 1, signal_critical: 1 }), TH, null, [], NOW)[0]).toMatch(
      /^Atenuação isolada em 2 ONUs/,
    )
    expect(ponDiagnostics(pon({ signal_warning: 4 }), TH, null, [], NOW)).toEqual([
      '4 ONUs com sinal abaixo de -24 dBm — verificar fusão, conector ou splitter da caixa.',
    ])
  })

  it('porta em baixo e ocupação alta continuam', () => {
    expect(ponDiagnostics(null, TH, 'down', [], NOW)).toEqual(['Porta PON em baixo no Zabbix.'])
    expect(ponDiagnostics(pon({ occupancy_pct: 92 }), TH, null, [], NOW)[0]).toMatch(/^Ocupação de 92%/)
  })
})

describe('resumo para OS', () => {
  it('traz OLT, POP, porta, estado, RX e as ONUs afetadas com motivo e hora', () => {
    const onus = [
      los(1, HOUR, { serial: 'ZTEGLOS00001', cliente_nome: 'João' }),
      onu({ id: 2, serial: 'ZTEGWARN0001', signal: 'warning', rx_olt_dbm: -25.5 }),
      onu({ id: 3, serial: 'ZTEGOK000001' }),
    ]
    const text = ponOsSummary({
      olt: { name: 'ZTE - OLT BRV C300', site_name: 'SITE - BARREIRA VELHA' },
      pon: pon({ los: 1, signal_warning: 1, onus_online: 9 }),
      portId: '8/2',
      stateLabel: 'Crítico',
      onus,
      diagnostics: ['Diagnóstico X'],
      now: NOW,
    })
    expect(text).toContain('OS — ZTE - OLT BRV C300 (SITE - BARREIRA VELHA)')
    expect(text).toContain('Porta: PON 8/2 · estado: Crítico')
    expect(text).toContain('RX médio: -20,4 dBm · pior RX: -22,1 dBm')
    expect(text).toContain('Diagnóstico: Diagnóstico X')
    expect(text).toContain('ONUs afetadas (2):')
    expect(text).toMatch(/- ZTEGLOS00001 — LOS desde .+ · João/)
    expect(text).toContain('- ZTEGWARN0001 — RX -25,5 dBm')
    expect(text).not.toContain('ZTEGOK000001')
    expect(affectedOnus(onus)).toHaveLength(2)
  })

  it('limita a lista e diz quantas ficaram de fora', () => {
    const many = Array.from({ length: 45 }, (_, i) => los(i + 1, HOUR))
    const text = ponOsSummary({ pon: pon(), portId: '8/2', onus: many, now: NOW })
    expect(text).toContain('ONUs afetadas (45):')
    expect(text).toContain('… e mais 5')
  })

  it('copyText usa a Clipboard API', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    await copyText('abc')
    expect(writeText).toHaveBeenCalledWith('abc')
  })
})

describe('PonInspector (EV-0107)', () => {
  async function mountInspector(props = {}) {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/:p(.*)*', component: defineComponent({ render: () => h('div') }) }],
    })
    router.push('/monitoring/gpon')
    await router.isReady()
    const w = mount(PonInspector, {
      props: {
        portId: '8/2',
        pon: pon({ signal_warning: 1, signal_critical: 1, los: 1 }),
        thresholds: TH,
        onus: [onu(), onu({ id: 2, signal: 'warning' }), onu({ id: 3, signal: 'critical' }), los(4, HOUR)],
        olt: { name: 'ZTE - OLT BRV C300', site_name: 'SITE - BRV', site_id: 7 },
        ...props,
      },
      global: { plugins: [router] },
    })
    return { w, router }
  }

  it('histograma com contagens e clique emite a faixa', async () => {
    const { w } = await mountInspector()
    expect(w.get('[data-testid="insp-band-normal"]').text()).toContain('1')
    await w.get('[data-testid="insp-band-critical"]').trigger('click')
    expect(w.emitted('band')).toEqual([['critical']])
    await w.setProps({ signalBand: 'critical' })
    expect(w.get('[data-testid="insp-band-critical"]').attributes('aria-pressed')).toBe('true')
  })

  it('Copiar resumo OS copia e mostra «Copiado!»', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const { w } = await mountInspector()
    await w.get('[data-testid="insp-copy-os"]').trigger('click')
    await flushPromises()
    expect(writeText.mock.calls[0][0]).toContain('OS — ZTE - OLT BRV C300 (SITE - BRV)')
    expect(w.get('[data-testid="insp-copy-os"]').text()).toBe('Copiado!')
  })

  it('Ver no mapa abre o mapa backbone com o POP; sem POP fica desativado', async () => {
    const { w, router } = await mountInspector()
    await w.get('[data-testid="insp-map"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/monitoring/backbone/map/default')
    expect(router.currentRoute.value.query).toEqual({ site: '7' })
    const { w: w2 } = await mountInspector({ olt: { name: 'X', site_id: null } })
    expect(w2.get('[data-testid="insp-map"]').attributes('disabled')).toBeDefined()
  })
})

describe('filtro por faixa de sinal (useGponOverview)', () => {
  it('seleciona a PON, filtra a tabela pela faixa e a mesma faixa limpa', async () => {
    mockFetch(payload())
    let api
    const Host = defineComponent({
      setup() {
        api = useGponOverview({ autoRefresh: false })
        return () => h('div')
      },
    })
    mount(Host)
    await flushPromises()
    api.toggleSignalBand(22, '9/15', 'warning')
    await nextTick()
    expect(api.selectedPon.value).toBe('22:9/15')
    expect(api.visibleOnus.value.map((o) => o.id)).toEqual([503])
    expect(api.tableScope.value).toMatch(/sinal em atenção$/)
    api.toggleSignalBand(22, '9/15', 'warning')
    await nextTick()
    expect(api.signalBand.value).toBe(null)
    expect(api.visibleOnus.value.map((o) => o.id)).toContain(504)
    // trocar de PON à mão não arrasta a faixa
    api.toggleSignalBand(22, '9/15', 'warning')
    api.togglePon(22, '9/14')
    await nextTick()
    expect(api.signalBand.value).toBe(null)
  })
})

describe('OnuTable — copiar serial (EV-0107)', () => {
  it('copia com um clique e confirma', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const w = mount(OnuTable, { props: { onus: [onu({ id: 9, serial: 'ZTEG12345678' })] } })
    await w.get('[data-testid="onu-copy-9"]').trigger('click')
    await flushPromises()
    expect(writeText).toHaveBeenCalledWith('ZTEG12345678')
    expect(w.get('[data-testid="onu-copy-9"]').attributes('title')).toBe('Copiado')
  })
})
