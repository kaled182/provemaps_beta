/**
 * EV-0027c — a Central lista por estado e tipo, mostra a triagem só a staff e tria por PATCH.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

const api = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), postFormData: vi.fn() };
vi.mock('@/composables/useApi', () => ({ useApi: () => api, getCsrfToken: () => 'tok' }));
const notify = { success: vi.fn(), error: vi.fn() };
vi.mock('@/composables/useNotification', () => ({ useNotification: () => notify }));

import EvolucaoView from '@/views/EvolucaoView.vue';
import { resetCurrentUser } from '@/composables/useCurrentUser';

const ITENS = [
  { id: 1, codigo: 'EV-0001', tipo: 'problema', titulo: 'Mapa cinzento', descricao: 'd1', estado: 'a_fazer', prioridade: 1, impacto: 'bloqueia', etiquetas: ['mapa'], origem: 'humano', autor: 'paulo', contexto: { rota: '/map' }, evidencia: null, fechado_por: null, anexos: [], criado_em: '2026-09-20T00:00:00Z', atualizado_em: '2026-09-20T00:00:00Z' },
  { id: 2, codigo: 'EV-0002', tipo: 'ideia', titulo: 'Tema roxo', descricao: 'd2', estado: 'entrada', prioridade: null, impacto: null, etiquetas: [], origem: 'agente', autor: null, contexto: {}, evidencia: { ficheiro: 'a.py' }, fechado_por: null, anexos: [{ id: 9, nome_original: 'p.png' }], criado_em: '2026-10-01T00:00:00Z', atualizado_em: '2026-10-01T00:00:00Z' },
  { id: 3, codigo: 'EV-0003', tipo: 'problema', titulo: 'Feito e no ar', descricao: 'd3', estado: 'feito', prioridade: 2, impacto: null, etiquetas: [], origem: 'humano', autor: 'ana', contexto: {}, evidencia: null, fechado_por: { commit: 'abc1234', mensagem: 'fix', deploy_em: '2026-10-02T00:00:00Z' }, anexos: [], criado_em: '2026-09-01T00:00:00Z', atualizado_em: '2026-10-02T00:00:00Z' },
];

function responder(user) {
  api.get.mockImplementation(async (url) => {
    if (url === '/api/users/me/') return { success: true, user };
    if (url.endsWith('/etiquetas/')) return { etiquetas: ['mapa', 'zabbix'] };
    return ITENS;
  });
}

beforeEach(() => { vi.clearAllMocks(); resetCurrentUser(); });
afterEach(() => vi.restoreAllMocks());

describe('EvolucaoView', () => {
  it('staff vê abas com contagens, secções por estado e os controlos de triagem', async () => {
    responder({ username: 'paulo', is_staff: true });
    const w = mount(EvolucaoView, { global: { stubs: { Teleport: true } } });
    await flushPromises();
    expect(w.text()).toContain('Problemas');
    expect(w.findAll('.ev-aba')[0].text()).toContain('2');
    expect(w.findAll('.ev-aba')[1].text()).toContain('1');
    // aba Problemas por omissão: EV-0001 (A fazer) e EV-0003 (Feito), ideia escondida
    expect(w.text()).toContain('EV-0001');
    expect(w.text()).toContain('EV-0003');
    expect(w.text()).not.toContain('EV-0002');
    expect(w.text()).toContain('P1');
    expect(w.text()).toContain('Não consigo trabalhar');
    await w.findAll('.ev-aba')[2].trigger('click');
    expect(w.text()).toContain('EV-0002');
    expect(w.text()).toContain('agente');
    // detalhe do EV-0003 mostra o fecho observado
    await w.find('[data-codigo="EV-0003"] .ev-toggle').trigger('click');
    expect(w.find('[data-codigo="EV-0003"]').text()).toContain('abc1234');
    expect(w.find('[data-codigo="EV-0003"]').text()).toContain('em produção desde');
    expect(w.find('[data-codigo="EV-0003"] form.ev-triagem').exists()).toBe(true);
    w.unmount();
  });

  it('não-staff não vê triagem; triagem faz PATCH e recusa pede motivo', async () => {
    responder({ username: 'rep', is_staff: false });
    const w = mount(EvolucaoView, { global: { stubs: { Teleport: true } } });
    await flushPromises();
    await w.find('[data-codigo="EV-0001"] .ev-toggle').trigger('click');
    expect(w.find('form.ev-triagem').exists()).toBe(false);
    expect(w.text()).toContain('a triagem é da equipe');
    w.unmount();

    resetCurrentUser();
    responder({ username: 'paulo', is_staff: true });
    api.patch.mockResolvedValue({ ...ITENS[0], estado: 'recusado', recusa_motivo: 'duplicado' });
    const w2 = mount(EvolucaoView, { global: { stubs: { Teleport: true } } });
    await flushPromises();
    await w2.find('[data-codigo="EV-0001"] .ev-toggle').trigger('click');
    const prioridade = w2.findAll('[data-codigo="EV-0001"] select')[1];
    await prioridade.setValue('');
    expect(api.patch).toHaveBeenLastCalledWith('/api/v1/evolucao/itens/1/', { prioridade: null });
    vi.spyOn(window, 'prompt').mockReturnValueOnce('');
    const estado = w2.findAll('[data-codigo="EV-0001"] select')[0];
    await estado.setValue('recusado');
    expect(api.patch).toHaveBeenCalledTimes(1); // sem motivo não envia
    vi.spyOn(window, 'prompt').mockReturnValueOnce('duplicado');
    await estado.setValue('recusado');
    expect(api.patch).toHaveBeenLastCalledWith('/api/v1/evolucao/itens/1/', { estado: 'recusado', recusa_motivo: 'duplicado' });
    expect(notify.success).toHaveBeenCalled();
    w2.unmount();
  });
});
