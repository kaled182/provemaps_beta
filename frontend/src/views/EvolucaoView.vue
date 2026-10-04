<template>
  <div class="app-page ev-page">
    <header class="ev-head">
      <div>
        <h1 class="ev-h1"><PhMegaphone :size="26" weight="regular" /> Central de Evolução</h1>
        <p class="app-text-tertiary ev-sub">
          O que falta fazer, com autor, data e fila. A ordem de trabalho é prioridade e depois código;
          problemas antes de ideias.
          <span v-if="!isStaff"> Vê os itens que reportou; a triagem é da equipe.</span>
        </p>
      </div>
      <div class="ev-head-actions">
        <button type="button" class="app-btn app-btn-primary" @click="mostrarReportar = true">
          <PhMegaphone :size="16" weight="regular" /> Reportar
        </button>
        <button type="button" class="app-btn" :disabled="loading" @click="recarregar">Atualizar</button>
      </div>
    </header>

    <nav class="ev-abas" aria-label="Tipo">
      <button
        v-for="a in ABAS"
        :key="a.valor ?? 'tudo'"
        type="button"
        class="app-tab ev-aba"
        :class="{ 'app-tab-underline': aba === a.valor }"
        :aria-pressed="aba === a.valor"
        @click="aba = a.valor"
      >
        {{ a.rotulo }} <span class="app-badge app-badge-muted">{{ contagem(a.valor) }}</span>
      </button>
    </nav>

    <p v-if="error" class="ev-erro" role="alert">{{ error }}</p>
    <p v-else-if="loading && !itens.length" class="app-text-tertiary">A carregar…</p>
    <p v-else-if="!visiveis.length" class="app-text-tertiary ev-vazio">Nada por aqui. Use «Reportar» para abrir o primeiro item.</p>

    <section v-for="grupo in porEstado" :key="grupo.valor" class="ev-seccao">
      <h2 class="ev-h2">{{ grupo.rotulo }} <span class="app-badge app-badge-muted">{{ grupo.itens.length }}</span></h2>
      <article v-for="item in grupo.itens" :key="item.id" class="app-surface ev-item" :data-codigo="item.codigo">
        <div class="ev-item-head">
          <component :is="item.tipo === 'ideia' ? PhLightbulb : PhBug" :size="18" weight="regular" class="ev-tipo-ico" :title="item.tipo" />
          <code class="ev-codigo">{{ item.codigo }}</code>
          <strong class="ev-titulo">{{ item.titulo }}</strong>
          <span v-if="item.prioridade" class="app-badge app-badge-info">P{{ item.prioridade }}</span>
          <span v-else-if="item.estado !== 'feito' && item.estado !== 'recusado'" class="app-badge app-badge-muted">por triar</span>
          <span v-if="item.impacto && IMPACTOS[item.impacto]" class="app-badge" :class="IMPACTOS[item.impacto].classe">{{ IMPACTOS[item.impacto].rotulo }}</span>
          <span v-if="item.origem === 'agente'" class="app-badge app-badge-muted" title="Aberto pelo assistente, com evidência"><PhRobot :size="12" /> agente</span>
          <span v-for="e in item.etiquetas" :key="e" class="app-chip">{{ e }}</span>
          <span class="app-text-tertiary ev-meta">{{ item.autor || item.origem }} · há {{ idadeEmDias(item.criado_em) }} dias</span>
          <button type="button" class="app-btn ev-toggle" @click="alternar(item.id)">{{ aberto(item.id) ? 'Menos' : 'Detalhe' }}</button>
        </div>

        <div v-if="aberto(item.id)" class="ev-item-body">
          <p class="ev-descricao">{{ item.descricao }}</p>
          <p v-if="item.estado === 'recusado' && item.recusa_motivo" class="ev-recusa"><strong>Recusado:</strong> {{ item.recusa_motivo }}</p>
          <p v-if="item.fechado_por" class="app-text-tertiary ev-fechado">
            Fechado por <code>{{ item.fechado_por.commit || '—' }}</code>
            <span v-if="item.fechado_por.mensagem"> — {{ item.fechado_por.mensagem }}</span>
            <span v-if="item.fechado_por.deploy_em"> · em produção desde {{ quando(item.fechado_por.deploy_em) }}</span>
            <span v-else> · aguarda deploy</span>
          </p>
          <details v-if="Object.keys(item.contexto || {}).length" class="ev-details">
            <summary>Contexto</summary>
            <dl class="ev-dl"><template v-for="[k, v] in Object.entries(item.contexto)" :key="k"><dt>{{ k }}</dt><dd>{{ v }}</dd></template></dl>
          </details>
          <details v-if="item.evidencia" class="ev-details">
            <summary>Evidência</summary>
            <dl class="ev-dl"><template v-for="[k, v] in Object.entries(item.evidencia)" :key="k"><dt>{{ k }}</dt><dd>{{ v }}</dd></template></dl>
          </details>
          <p v-if="item.anexos?.length" class="ev-anexos">
            Anexos:
            <a v-for="a in item.anexos" :key="a.id" :href="`${BASE}/anexos/${a.id}/`" target="_blank" rel="noopener" class="ev-anexo">{{ a.nome_original }}</a>
          </p>

          <form v-if="isStaff" class="ev-triagem" @submit.prevent>
            <label>Estado
              <select class="app-input" :value="item.estado" @change="mudar(item, 'estado', $event.target.value)">
                <option v-for="e in ESTADOS" :key="e.valor" :value="e.valor">{{ e.rotulo }}</option>
              </select>
            </label>
            <label>Prioridade
              <select class="app-input" :value="item.prioridade ?? ''" @change="mudar(item, 'prioridade', $event.target.value === '' ? null : Number($event.target.value))">
                <option value="">Sem prioridade</option>
                <option v-for="p in PRIORIDADES" :key="p.valor" :value="p.valor">{{ p.rotulo }}</option>
              </select>
            </label>
            <label>Tipo
              <select class="app-input" :value="item.tipo" @change="mudar(item, 'tipo', $event.target.value)">
                <option value="problema">Problema</option>
                <option value="ideia">Ideia</option>
              </select>
            </label>
            <label>Etiqueta
              <input class="app-input" list="ev-etiquetas" placeholder="Enter para acrescentar" @keydown.enter.prevent="acrescentarEtiqueta(item, $event)" />
            </label>
            <datalist id="ev-etiquetas"><option v-for="e in etiquetas" :key="e" :value="e" /></datalist>
          </form>
        </div>
      </article>
    </section>

    <ReportarModal :show="mostrarReportar" @close="mostrarReportar = false" @criado="recarregar" />
  </div>
</template>

<script setup>
/**
 * Central de Evolução — a fila do que falta (ADR 0006). Listas por estado e, dentro, por tipo;
 * sem Kanban. Staff vê tudo e tria; os outros veem o que escreveram (filtro do backend).
 */
import { ref, computed, onMounted } from 'vue';
import { PhMegaphone, PhBug, PhLightbulb, PhRobot } from '@phosphor-icons/vue';
import ReportarModal from '@/components/Evolucao/ReportarModal.vue';
import { useEvolucao, BASE, ESTADOS, PRIORIDADES, IMPACTOS } from '@/composables/useEvolucao';
import { useCurrentUser } from '@/composables/useCurrentUser';
import { useNotification } from '@/composables/useNotification';

const { itens, etiquetas, loading, error, carregar, carregarEtiquetas, triar } = useEvolucao();
const { isStaff, load: carregarUser } = useCurrentUser();
const notify = useNotification();

const ABAS = [
  { valor: 'problema', rotulo: 'Problemas' },
  { valor: 'ideia', rotulo: 'Ideias' },
  { valor: null, rotulo: 'Tudo' },
];
const aba = ref('problema');
const mostrarReportar = ref(false);
const abertos = ref(new Set());

function contagem(tipo) {
  return tipo ? itens.value.filter((i) => i.tipo === tipo).length : itens.value.length;
}
const visiveis = computed(() => (aba.value ? itens.value.filter((i) => i.tipo === aba.value) : itens.value));
/** Agrupa pela ordem dos ESTADOS; dentro, a ordem já vem do backend (prioridade, código). */
const porEstado = computed(() =>
  ESTADOS.map((e) => ({ ...e, itens: visiveis.value.filter((i) => i.estado === e.valor) })).filter((g) => g.itens.length)
);

function aberto(id) { return abertos.value.has(id); }
function alternar(id) {
  const s = new Set(abertos.value);
  s.has(id) ? s.delete(id) : s.add(id);
  abertos.value = s;
}
function idadeEmDias(iso) { return Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)); }
const _DATA = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'America/Sao_Paulo' });
function quando(iso) { try { return _DATA.format(new Date(iso)); } catch { return iso; } }

async function mudar(item, campo, valor) {
  const corpo = { [campo]: valor };
  if (campo === 'estado' && valor === 'recusado') {
    const motivo = window.prompt('Porquê recusar? (obrigatório — quem reportou vai ler isto)');
    if (!motivo || !motivo.trim()) return;
    corpo.recusa_motivo = motivo.trim();
  }
  try {
    await triar(item.id, corpo);
    notify.success(`${item.codigo} atualizado`);
    if (campo === 'estado' || campo === 'tipo') await carregarEtiquetas();
  } catch (err) {
    notify.error('Não foi possível atualizar', err.message || '');
  }
}

async function acrescentarEtiqueta(item, evento) {
  const campo = evento.target;
  const valor = campo.value.trim();
  if (!valor || item.etiquetas.includes(valor)) return;
  campo.value = '';
  try {
    await triar(item.id, { etiquetas: [...item.etiquetas, valor] });
    await carregarEtiquetas();
  } catch (err) {
    notify.error('Não foi possível etiquetar', err.message || '');
  }
}

async function recarregar() {
  await Promise.all([carregar(), carregarEtiquetas()]);
}

onMounted(async () => {
  await Promise.all([carregarUser(), recarregar()]);
});
</script>

<style scoped>
.ev-page { display: flex; flex-direction: column; gap: 16px; padding: 24px; max-width: 1100px; margin: 0 auto; }
.ev-head { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; align-items: flex-start; }
.ev-h1 { display: flex; align-items: center; gap: 10px; margin: 0; font-size: 1.5rem; font-weight: 600; color: var(--text-primary); }
.ev-sub { margin: 4px 0 0; font-size: 0.9rem; max-width: 60ch; }
.ev-head-actions { display: flex; gap: 8px; }
.ev-abas { display: flex; gap: 4px; border-bottom: 1px solid var(--border-primary); }
.ev-aba { display: inline-flex; align-items: center; gap: 6px; }
.ev-erro { color: var(--status-offline, #f87171); }
.ev-vazio { padding: 24px 0; }
.ev-seccao { display: flex; flex-direction: column; gap: 8px; }
.ev-h2 { display: flex; align-items: center; gap: 8px; margin: 8px 0 0; font-size: 1rem; font-weight: 600; color: var(--text-secondary); }
.ev-item { border: 1px solid var(--border-primary); border-radius: 12px; padding: 10px 14px; }
.ev-item-head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.ev-tipo-ico { color: var(--text-tertiary); }
.ev-codigo { font-family: var(--font-mono, monospace); font-size: 0.8rem; color: var(--text-tertiary); }
.ev-titulo { color: var(--text-primary); }
.ev-meta { margin-left: auto; font-size: 0.8rem; white-space: nowrap; }
.ev-toggle { padding: 2px 10px; font-size: 0.8rem; }
.ev-item-body { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; font-size: 0.9rem; color: var(--text-secondary); }
.ev-descricao { margin: 0; white-space: pre-wrap; }
.ev-recusa, .ev-fechado, .ev-anexos { margin: 0; font-size: 0.85rem; }
.ev-anexo { margin-left: 8px; color: var(--primary-500); text-decoration: underline; }
.ev-details summary { cursor: pointer; font-size: 0.85rem; }
.ev-dl { display: grid; grid-template-columns: max-content 1fr; gap: 2px 12px; margin: 6px 0 0; font-size: 0.8rem; }
.ev-dl dt { color: var(--text-tertiary); } .ev-dl dd { margin: 0; word-break: break-all; }
.ev-triagem { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; padding-top: 8px; border-top: 1px dashed var(--border-primary); }
.ev-triagem label { display: flex; flex-direction: column; gap: 4px; font-size: 0.8rem; color: var(--text-tertiary); }
</style>
