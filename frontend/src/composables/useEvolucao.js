/**
 * Central de Evolução (ADR 0006): listar, reportar, triar, anexos, etiquetas.
 *
 * Quem não é staff recebe do backend só os itens que escreveu — a filtragem é lá, não aqui.
 * Mutações sempre por `useApi()` (CSRF).
 * @module useEvolucao
 */
import { ref } from 'vue';
import { useApi } from '@/composables/useApi';

export const BASE = '/api/v1/evolucao';

export const ESTADOS = [
  { valor: 'entrada', rotulo: 'Entrada' },
  { valor: 'aceite', rotulo: 'Aceite' },
  { valor: 'a_fazer', rotulo: 'A fazer' },
  { valor: 'feito', rotulo: 'Feito' },
  { valor: 'recusado', rotulo: 'Recusado' },
];

export const PRIORIDADES = [
  { valor: 1, rotulo: '1 — agora' },
  { valor: 2, rotulo: '2 — a seguir' },
  { valor: 3, rotulo: '3 — depois' },
  { valor: 4, rotulo: '4 — algum dia' },
];

/** As palavras são as do modal: quem reportou reconhece a própria resposta. */
export const IMPACTOS = {
  bloqueia: { rotulo: 'Não consigo trabalhar', classe: 'app-badge-danger' },
  atrasa: { rotulo: 'Atrasa o meu trabalho', classe: 'app-badge-warning' },
  incomoda: { rotulo: 'Incomoda, mas consigo continuar', classe: 'app-badge-muted' },
};

/** O que o browser já sabe sobre onde o relato aconteceu — resolve o «deu erro naquela tela lá». */
export function contextoAtual(win = typeof window !== 'undefined' ? window : null) {
  if (!win) return {};
  const rota = win.location?.pathname ?? '';
  return {
    rota,
    url: win.location?.href ?? '',
    viewport: `${win.innerWidth}x${win.innerHeight}`,
    navegador: (win.navigator?.userAgent ?? '').slice(0, 200),
    modulo: rota.split('/').filter(Boolean)[0] ?? 'geral',
  };
}

export function useEvolucao() {
  const api = useApi();
  const itens = ref([]);
  const etiquetas = ref([]);
  const loading = ref(false);
  const error = ref(null);

  async function carregar({ estado = null, tipo = null } = {}) {
    loading.value = true;
    error.value = null;
    try {
      itens.value = await api.get(`${BASE}/itens/`, { estado, tipo });
    } catch (err) {
      error.value = err.message || 'Falha ao carregar a Central.';
      itens.value = [];
    } finally {
      loading.value = false;
    }
    return itens.value;
  }

  async function carregarEtiquetas() {
    try {
      const data = await api.get(`${BASE}/etiquetas/`);
      etiquetas.value = data?.etiquetas ?? [];
    } catch {
      etiquetas.value = [];
    }
    return etiquetas.value;
  }

  /** Carrega um ficheiro ANTES do item; devolve o id a passar em `anexos`. */
  async function carregarAnexo(file) {
    const form = new FormData();
    form.append('file', file);
    const data = await api.postFormData(`${BASE}/anexos/`, form);
    return data.id;
  }

  async function criar(payload) {
    return api.post(`${BASE}/itens/`, payload);
  }

  /** Só staff. Campo omitido = não mexer; `prioridade: null` apaga (volta a «por triar»). */
  async function triar(id, corpo) {
    const atualizado = await api.patch(`${BASE}/itens/${id}/`, corpo);
    const i = itens.value.findIndex((x) => x.id === id);
    if (i >= 0) itens.value.splice(i, 1, atualizado);
    return atualizado;
  }

  return { itens, etiquetas, loading, error, carregar, carregarEtiquetas, carregarAnexo, criar, triar };
}
