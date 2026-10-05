/**
 * EV-0027c — o modal Reportar valida, carrega anexos ANTES de criar, envia o contexto e diz o código.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

const api = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), postFormData: vi.fn() };
vi.mock('@/composables/useApi', () => ({ useApi: () => api, getCsrfToken: () => 'tok' }));
const notify = { success: vi.fn(), error: vi.fn() };
vi.mock('@/composables/useNotification', () => ({ useNotification: () => notify }));

import ReportarModal from '@/components/Evolucao/ReportarModal.vue';

beforeEach(() => { vi.clearAllMocks(); document.body.innerHTML = ''; });
afterEach(() => vi.restoreAllMocks());

function montar() {
  return mount(ReportarModal, { props: { show: true }, attachTo: document.body, global: { stubs: { Teleport: true } } });
}

describe('ReportarModal', () => {
  it('não envia com assunto curto e mostra o erro', async () => {
    const w = montar();
    await w.find('input[type="text"]').setValue('ab');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();
    expect(api.post).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain('Escreva o assunto');
    w.unmount();
  });

  it('cria um problema com impacto, contexto e anexos carregados antes; emite criado e close', async () => {
    api.postFormData.mockResolvedValueOnce({ id: 11 });
    api.post.mockResolvedValueOnce({ id: 1, codigo: 'EV-0042' });
    const w = montar();
    await w.find('input[type="text"]').setValue('Mapa cinzento');
    await w.find('textarea').setValue('O OSM não carrega no /map');
    await w.find('input[type="radio"][value="bloqueia"]').setValue();
    const file = new File([new Uint8Array([1])], 'print.png', { type: 'image/png' });
    const input = w.find('input[type="file"]');
    Object.defineProperty(input.element, 'files', { value: [file] });
    await input.trigger('change');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();
    expect(api.postFormData).toHaveBeenCalledTimes(1);
    expect(api.post).toHaveBeenCalledTimes(1);
    const corpo = api.post.mock.calls[0][1];
    expect(corpo).toMatchObject({ tipo: 'problema', titulo: 'Mapa cinzento', descricao: 'O OSM não carrega no /map', impacto: 'bloqueia', anexos: [11] });
    expect(corpo.contexto).toMatchObject({ rota: expect.any(String), viewport: expect.stringMatching(/^\d+x\d+$/) });
    expect(notify.success).toHaveBeenCalledWith('Registado como EV-0042', expect.any(String));
    expect(w.emitted('criado')[0][0].codigo).toBe('EV-0042');
    expect(w.emitted('close')).toHaveLength(1);
    w.unmount();
  });

  it('ideia não leva impacto e um erro do servidor não fecha o modal', async () => {
    api.post.mockRejectedValueOnce(new Error('Serviço indisponível'));
    const w = montar();
    const botoes = w.findAll('.ev-tipo');
    await botoes[1].trigger('click');
    expect(w.find('fieldset').exists()).toBe(false);
    await w.find('input[type="text"]').setValue('Ideia boa');
    await w.find('textarea').setValue('Resolve X');
    await w.find('form').trigger('submit.prevent');
    await flushPromises();
    expect(api.post.mock.calls[0][1]).toMatchObject({ tipo: 'ideia', impacto: '' });
    expect(w.emitted('close')).toBeUndefined();
    expect(document.body.textContent).toContain('Serviço indisponível');
    w.unmount();
  });
});
