/**
 * EV-0044 — shell de duas linhas (ADR 0007 Fase 2): secções da navegação,
 * contrato do foco no mapa, paleta de comandos (Ctrl K) e cabeçalho.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import { createPinia, setActivePinia } from 'pinia';
import { defineComponent, h } from 'vue';
import {
  NAV_SECTIONS,
  normalizePath,
  isPathActive,
  activeSectionId,
  searchPages,
  foldText,
} from '@/composables/useNavSections';
import { buildFocusLocation, parseFocusQuery, FOCUS_ROUTE } from '@/utils/mapFocus';
import CommandPalette from '@/components/Layout/CommandPalette.vue';

const Stub = defineComponent({ render: () => h('div') });

function makeRouter() {
  const paths = ['/', ...NAV_SECTIONS.flatMap((s) => s.items.map((i) => i.path)), '/profile', '/meu-cadastro'];
  return createRouter({
    history: createMemoryHistory(),
    routes: [...new Set(paths)].map((path) => ({ path, component: Stub })),
  });
}

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: 'x',
    json: () => Promise.resolve(body),
  });
}

describe('useNavSections', () => {
  it('rótulos em PT-BR, sem os termos antigos em inglês', () => {
    const labels = NAV_SECTIONS.flatMap((s) => [s.label, ...s.items.map((i) => i.label)]);
    for (const banned of ['Monitoring', 'Network', 'System', 'Overview', 'Users', 'Metrics', 'Docs', 'Setup']) {
      expect(labels).not.toContain(banned);
    }
  });

  it('cada caminho aparece uma só vez', () => {
    const paths = NAV_SECTIONS.flatMap((s) => s.items.map((i) => normalizePath(i.path)));
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('normaliza barra final e caixa', () => {
    expect(normalizePath('/Network/NetworkDesign/')).toBe('/network/networkdesign');
    expect(normalizePath('/')).toBe('/');
  });

  it('caminho ativo cobre subcaminhos mas não prefixos soltos', () => {
    expect(isPathActive('/network/inventory/12', '/network/inventory')).toBe(true);
    expect(isPathActive('/network/inventory-x', '/network/inventory')).toBe(false);
    expect(isPathActive('/video/cameras', '/video')).toBe(true);
  });

  it('secção ativa pelo caminho atual', () => {
    expect(activeSectionId('/monitoring/gpon')).toBe('monitoramento');
    expect(activeSectionId('/Network/NetworkDesign/')).toBe('rede');
    expect(activeSectionId('/system/evolucao')).toBe('sistema');
    expect(activeSectionId('/profile')).toBeNull();
  });

  it('busca de páginas ignora acentos e inclui a secção', () => {
    expect(foldText('Inventário')).toBe('inventario');
    expect(searchPages('inventario').map((p) => p.path)).toContain('/network/inventory');
    expect(searchPages('evolucao')[0]).toMatchObject({ path: '/system/evolucao', section: 'Sistema' });
    expect(searchPages('   ')).toEqual([]);
  });
});

describe('mapFocus', () => {
  it('ida e volta resultado → rota → item', () => {
    const loc = buildFocusLocation({ type: 'cable', id: 7, name: 'Anel Norte', lat: -16.5, lng: -49.2 });
    expect(loc.path).toBe(FOCUS_ROUTE);
    expect(parseFocusQuery(loc.query)).toEqual({ type: 'cable', id: 7, lat: -16.5, lng: -49.2, name: 'Anel Norte' });
  });

  it('sem coordenadas não há rota', () => {
    expect(buildFocusLocation({ type: 'site', id: 1, lat: null, lng: -49 })).toBeNull();
  });

  it('rejeita query inválida', () => {
    expect(parseFocusQuery({})).toBeNull();
    expect(parseFocusQuery({ foco: 'x', id: '1', lat: '1', lng: '1' })).toBeNull();
    expect(parseFocusQuery({ foco: 'site', id: '1', lat: '91', lng: '1' })).toBeNull();
    expect(parseFocusQuery({ foco: 'site', id: 'a', lat: '1', lng: '1' })).toBeNull();
  });
});

describe('CommandPalette', () => {
  let router;

  beforeEach(async () => {
    vi.useFakeTimers();
    router = makeRouter();
    router.push('/');
    await router.isReady();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  function mountPalette(open = true) {
    return mount(CommandPalette, {
      props: { open, 'onUpdate:open': () => {} },
      global: { plugins: [router] },
      attachTo: document.body,
    });
  }

  it('Ctrl K pede para abrir', async () => {
    const wrapper = mountPalette(false);
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }));
    expect(wrapper.emitted('update:open')?.[0]).toEqual([true]);
    wrapper.unmount();
  });

  it('busca no inventário com debounce e agrupa por tipo', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      jsonResponse({
        results: [
          { type: 'cable', id: 3, name: 'Cabo Centro', subtitle: '2.00 km', lat: -16, lng: -49 },
          { type: 'site', id: 9, name: 'POP Centro', subtitle: 'Goiânia, GO', lat: null, lng: null },
        ],
      }),
    );
    const wrapper = mountPalette();
    await wrapper.setProps({ open: true });
    const input = document.querySelector('[data-testid="command-palette-input"]');
    input.value = 'centro';
    input.dispatchEvent(new Event('input'));
    await vi.advanceTimersByTimeAsync(100);
    expect(fetchMock).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(200);
    await flushPromises();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/inventory/search/?q=centro');
    const text = document.body.textContent;
    expect(text).toContain('Cabos');
    expect(text).toContain('Cabo Centro');
    expect(text).toContain('sem coordenadas');
    expect(document.querySelector('[data-testid="command-item-site-9"]').disabled).toBe(true);
    wrapper.unmount();
  });

  it('erro do backend aparece como erro, não como «nada encontrado»', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse({ error: 'Zabbix fora' }, 500));
    const wrapper = mountPalette();
    const input = document.querySelector('[data-testid="command-palette-input"]');
    input.value = 'xyz';
    input.dispatchEvent(new Event('input'));
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    expect(document.body.textContent).toContain('Erro ao consultar o inventário');
    expect(document.body.textContent).not.toContain('Nada encontrado');
    wrapper.unmount();
  });

  it('Enter num cabo abre o Projeto de rede com o foco', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      jsonResponse({ results: [{ type: 'cable', id: 3, name: 'Cabo Zeta', subtitle: '', lat: -16, lng: -49 }] }),
    );
    const wrapper = mountPalette();
    const input = document.querySelector('[data-testid="command-palette-input"]');
    input.value = 'zeta';
    input.dispatchEvent(new Event('input'));
    await vi.advanceTimersByTimeAsync(300);
    await flushPromises();
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }));
    await flushPromises();
    expect(router.currentRoute.value.path).toBe(FOCUS_ROUTE);
    expect(router.currentRoute.value.query).toMatchObject({ foco: 'cable', id: '3', lat: '-16', lng: '-49' });
    expect(wrapper.emitted('update:open')?.at(-1)).toEqual([false]);
    wrapper.unmount();
  });

  it('páginas aparecem sem esperar pelo backend', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}));
    const wrapper = mountPalette();
    const input = document.querySelector('[data-testid="command-palette-input"]');
    input.value = 'usuarios';
    input.dispatchEvent(new Event('input'));
    await flushPromises();
    expect(document.body.textContent).toContain('Páginas');
    expect(document.body.textContent).toContain('Usuários');
    wrapper.unmount();
  });
});

describe('AppHeader', () => {
  let AppHeader;

  beforeEach(async () => {
    setActivePinia(createPinia());
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => jsonResponse({ user: { username: 'paulo', first_name: 'Paulo' } }));
    globalThis.WebSocket = vi.fn(() => ({ close: vi.fn() }));
    AppHeader = (await import('@/components/Layout/AppHeader.vue')).default;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  async function mountHeader(path) {
    const router = makeRouter();
    router.push(path);
    await router.isReady();
    const wrapper = mount(AppHeader, {
      global: {
        plugins: [router],
        stubs: { ChangelogModal: true, ReportarModal: true, SystemPanel: true, CommandPalette: true },
      },
      attachTo: document.body,
    });
    await flushPromises();
    return { wrapper, router };
  }

  it('linha 2 marca a secção ativa', async () => {
    const { wrapper } = await mountHeader('/monitoring/gpon');
    expect(wrapper.get('[data-testid="nav-monitoramento"]').classes()).toContain('tab-active');
    expect(wrapper.get('[data-testid="nav-rede"]').classes()).not.toContain('tab-active');
    wrapper.unmount();
  });

  it('abre o menu da secção e fecha ao navegar', async () => {
    const { wrapper, router } = await mountHeader('/');
    await wrapper.get('[data-testid="nav-rede"]').trigger('click');
    expect(wrapper.find('[data-testid="menu-rede"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="menu-rede"]').text()).toContain('Inventário');
    await router.push('/network/inventory');
    await flushPromises();
    expect(wrapper.find('[data-testid="menu-rede"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it('mostra o nome do utilizador e alterna o tema', async () => {
    const { wrapper } = await mountHeader('/');
    expect(wrapper.get('[data-testid="header-user"]').text()).toContain('Paulo');
    const before = document.documentElement.classList.contains('dark');
    await wrapper.get('[data-testid="header-theme"]').trigger('click');
    expect(document.documentElement.classList.contains('dark')).toBe(!before);
    wrapper.unmount();
  });

  it('sem socket ligado o indicador diz «Conectando»/«Desconectado», nunca «Tempo real»', async () => {
    const { wrapper } = await mountHeader('/');
    expect(wrapper.get('[data-testid="header-realtime"]').text()).not.toContain('Tempo real');
    wrapper.unmount();
  });
});
