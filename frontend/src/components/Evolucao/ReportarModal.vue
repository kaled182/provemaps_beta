<template>
  <Teleport to="body">
    <div v-if="show" class="ev-overlay" @click.self="fechar">
      <div class="ev-modal" role="dialog" aria-modal="true" aria-labelledby="ev-reportar-titulo">
        <div class="ev-header">
          <div class="ev-header-left">
            <PhMegaphone :size="22" weight="regular" />
            <div>
              <h2 id="ev-reportar-titulo" class="ev-title">Reportar</h2>
              <p class="ev-subtitle">Um problema que encontrou ou uma ideia para o ProVeMaps.</p>
            </div>
          </div>
          <button type="button" class="ev-close" title="Fechar" @click="fechar">
            <PhX :size="20" weight="bold" />
          </button>
        </div>

        <form class="ev-body" @submit.prevent="enviar">
          <div class="ev-tipos" role="radiogroup" aria-label="Tipo">
            <button
              v-for="t in TIPOS"
              :key="t.valor"
              type="button"
              class="ev-tipo"
              :class="{ active: tipo === t.valor }"
              :aria-pressed="tipo === t.valor"
              @click="tipo = t.valor"
            >
              <component :is="t.icone" :size="16" weight="regular" /> {{ t.rotulo }}
            </button>
          </div>

          <label class="ev-field">
            <span class="ev-label">Assunto</span>
            <input v-model="titulo" class="app-input" type="text" maxlength="200" placeholder="Em poucas palavras" />
          </label>

          <label class="ev-field">
            <span class="ev-label">{{ pergunta }}</span>
            <textarea v-model="descricao" class="app-input ev-textarea" rows="5"></textarea>
          </label>

          <fieldset v-if="tipo === 'problema'" class="ev-field">
            <legend class="ev-label">Quanto atrapalha?</legend>
            <label v-for="(imp, chave) in IMPACTOS" :key="chave" class="ev-radio">
              <input v-model="impacto" type="radio" :value="chave" />
              <span>{{ imp.rotulo }}</span>
            </label>
          </fieldset>

          <label class="ev-field">
            <span class="ev-label">Anexos (prints, PDF) — opcional</span>
            <input type="file" multiple class="ev-file" @change="escolher" />
            <span v-if="ficheiros.length" class="app-text-tertiary ev-hint">{{ ficheiros.length }} ficheiro(s)</span>
          </label>

          <p v-if="erro" class="ev-erro" role="alert">{{ erro }}</p>

          <div class="ev-actions">
            <button type="button" class="app-btn" @click="fechar">Cancelar</button>
            <button type="submit" class="app-btn app-btn-primary" :disabled="aEnviar">
              {{ aEnviar ? 'A enviar…' : 'Enviar' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
/**
 * Reportar um problema ou propor uma ideia (ADR 0006). As perguntas mudam com o tipo: quem
 * encontrou um erro e quem teve uma ideia não têm nada a dizer em comum.
 * Anexos carregam PRIMEIRO; só com os ids na mão é que o item é criado — um upload falhado
 * não deixa um item a prometer um print que nunca chegou.
 */
import { ref, computed, watch } from 'vue';
import { PhMegaphone, PhX, PhBug, PhLightbulb } from '@phosphor-icons/vue';
import { useEvolucao, IMPACTOS, contextoAtual } from '@/composables/useEvolucao';
import { useNotification } from '@/composables/useNotification';
import { useEscapeKey } from '@/composables/useEscapeKey';

const props = defineProps({ show: { type: Boolean, default: false } });
const emit = defineEmits(['close', 'criado']);

const TIPOS = [
  { valor: 'problema', rotulo: 'Problema', icone: PhBug },
  { valor: 'ideia', rotulo: 'Ideia', icone: PhLightbulb },
];

const { criar, carregarAnexo } = useEvolucao();
const notify = useNotification();

const tipo = ref('problema');
const titulo = ref('');
const descricao = ref('');
const impacto = ref('atrasa');
const ficheiros = ref([]);
const erro = ref('');
const aEnviar = ref(false);

const pergunta = computed(() =>
  tipo.value === 'problema'
    ? 'O que esperava que acontecesse, e o que aconteceu?'
    : 'Que problema do dia a dia é que esta ideia resolve?'
);

function escolher(evento) {
  ficheiros.value = Array.from(evento.target.files ?? []);
}

function limpar() {
  titulo.value = '';
  descricao.value = '';
  ficheiros.value = [];
  erro.value = '';
}

function fechar() {
  emit('close');
}

/** Os mínimos são os do backend (3 caracteres): validar aqui evita um 400 mudo. */
function validar() {
  if (titulo.value.trim().length < 3) return 'Escreva o assunto em poucas palavras.';
  if (descricao.value.trim().length < 3) return 'Descreva um pouco mais — três letras não chegam.';
  return '';
}

async function enviar() {
  erro.value = validar();
  if (erro.value) return;
  aEnviar.value = true;
  try {
    const anexos = [];
    for (const f of ficheiros.value) anexos.push(await carregarAnexo(f));
    const item = await criar({
      tipo: tipo.value,
      titulo: titulo.value.trim(),
      descricao: descricao.value.trim(),
      impacto: tipo.value === 'problema' ? impacto.value : '',
      contexto: contextoAtual(),
      anexos,
    });
    // Dizer o código fecha a dúvida «terá ido?» — é essa dúvida que faz reportar duas vezes.
    notify.success(`Registado como ${item.codigo}`, 'Obrigado. Quem tria vai olhar para isto.');
    limpar();
    emit('criado', item);
    emit('close');
  } catch (err) {
    // Nunca fechar em cima do erro: levava o texto todo com ele.
    erro.value = err.message || 'Não foi possível enviar. Tente outra vez.';
  } finally {
    aEnviar.value = false;
  }
}

watch(() => props.show, (aberto) => { if (aberto) erro.value = ''; });
useEscapeKey(() => { if (props.show) fechar(); });
</script>

<style scoped>
.ev-overlay { position: fixed; inset: 0; z-index: 9999; background: rgba(0, 0, 0, 0.55); display: flex; align-items: center; justify-content: center; padding: 16px; }
.ev-modal { background: var(--surface-primary); border: 1px solid var(--border-primary); border-radius: 16px; width: 100%; max-width: 560px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 24px 64px rgba(0, 0, 0, 0.45); overflow: hidden; color: var(--text-primary); }
.ev-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 20px 24px 16px; border-bottom: 1px solid var(--border-primary); }
.ev-header-left { display: flex; align-items: flex-start; gap: 12px; color: var(--primary-500, var(--text-primary)); }
.ev-title { margin: 0; font-size: 1.1rem; font-weight: 600; color: var(--text-primary); }
.ev-subtitle { margin: 2px 0 0; font-size: 0.85rem; color: var(--text-tertiary); }
.ev-close { background: transparent; border: none; cursor: pointer; color: var(--text-tertiary); padding: 6px; border-radius: 8px; display: flex; }
.ev-close:hover { background: var(--surface-muted); color: var(--text-primary); }
.ev-body { flex: 1; overflow-y: auto; padding: 20px 24px; display: flex; flex-direction: column; gap: 16px; }
.ev-tipos { display: flex; gap: 8px; }
.ev-tipo { display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 10px; border: 1px solid var(--border-primary); background: var(--surface-muted); color: var(--text-secondary); cursor: pointer; font-size: 0.9rem; }
.ev-tipo.active { border-color: var(--primary-500); color: var(--primary-500); background: rgb(var(--primary-500-rgb, 66 180 184) / 0.12); }
.ev-field { display: flex; flex-direction: column; gap: 6px; border: none; padding: 0; margin: 0; }
.ev-label { font-size: 0.85rem; font-weight: 500; color: var(--text-secondary); }
.ev-textarea { resize: vertical; min-height: 110px; }
.ev-radio { display: flex; align-items: center; gap: 8px; font-size: 0.9rem; color: var(--text-primary); }
.ev-file { font-size: 0.85rem; color: var(--text-secondary); }
.ev-hint { font-size: 0.8rem; }
.ev-erro { margin: 0; font-size: 0.85rem; color: var(--status-offline, #f87171); }
.ev-actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
</style>
