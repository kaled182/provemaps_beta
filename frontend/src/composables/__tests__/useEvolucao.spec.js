/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useEvolucao, contextoAtual, BASE } from '../useEvolucao';
import { useApi } from '../useApi';

vi.mock('../useApi');

describe('useEvolucao (EV-0027c)', () => {
  let api;
  beforeEach(() => {
    api = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), postFormData: vi.fn() };
    vi.mocked(useApi).mockReturnValue(api);
  });
  afterEach(() => vi.clearAllMocks());

  it('carrega itens com filtros e guarda o erro', async () => {
    api.get.mockResolvedValueOnce([{ id: 1, codigo: 'EV-0001' }]);
    const ev = useEvolucao();
    await ev.carregar({ estado: 'entrada' });
    expect(api.get).toHaveBeenCalledWith(`${BASE}/itens/`, { estado: 'entrada', tipo: null });
    expect(ev.itens.value).toEqual([{ id: 1, codigo: 'EV-0001' }]);
    expect(ev.loading.value).toBe(false);
    api.get.mockRejectedValueOnce(new Error('401'));
    await ev.carregar();
    expect(ev.error.value).toBe('401');
    expect(ev.itens.value).toEqual([]);
  });

  it('etiquetas vêm do envelope e falham para vazio', async () => {
    api.get.mockResolvedValueOnce({ etiquetas: ['mapa'] });
    const ev = useEvolucao();
    expect(await ev.carregarEtiquetas()).toEqual(['mapa']);
    api.get.mockRejectedValueOnce(new Error('x'));
    expect(await ev.carregarEtiquetas()).toEqual([]);
  });

  it('anexo vai por FormData e devolve o id; criar faz POST', async () => {
    api.postFormData.mockResolvedValueOnce({ id: 7 });
    api.post.mockResolvedValueOnce({ id: 3, codigo: 'EV-0003' });
    const ev = useEvolucao();
    const file = new File([new Uint8Array([1])], 'p.png', { type: 'image/png' });
    expect(await ev.carregarAnexo(file)).toBe(7);
    const [url, form] = api.postFormData.mock.calls[0];
    expect(url).toBe(`${BASE}/anexos/`);
    expect(form.get('file')).toBe(file);
    const item = await ev.criar({ tipo: 'ideia', titulo: 'abc', descricao: 'def' });
    expect(api.post).toHaveBeenCalledWith(`${BASE}/itens/`, { tipo: 'ideia', titulo: 'abc', descricao: 'def' });
    expect(item.codigo).toBe('EV-0003');
  });

  it('triar faz PATCH e substitui o item na lista', async () => {
    api.get.mockResolvedValueOnce([{ id: 1, estado: 'entrada' }, { id: 2, estado: 'entrada' }]);
    api.patch.mockResolvedValueOnce({ id: 2, estado: 'a_fazer' });
    const ev = useEvolucao();
    await ev.carregar();
    await ev.triar(2, { estado: 'a_fazer' });
    expect(api.patch).toHaveBeenCalledWith(`${BASE}/itens/2/`, { estado: 'a_fazer' });
    expect(ev.itens.value[1]).toEqual({ id: 2, estado: 'a_fazer' });
  });

  it('contextoAtual captura rota, viewport, navegador e módulo', () => {
    const win = { location: { pathname: '/monitoring/backbone', href: 'http://x/monitoring/backbone' }, innerWidth: 800, innerHeight: 600, navigator: { userAgent: 'UA' } };
    expect(contextoAtual(win)).toEqual({ rota: '/monitoring/backbone', url: 'http://x/monitoring/backbone', viewport: '800x600', navegador: 'UA', modulo: 'monitoring' });
    expect(contextoAtual(null)).toEqual({});
  });
});
