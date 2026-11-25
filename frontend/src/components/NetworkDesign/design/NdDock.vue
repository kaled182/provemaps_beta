<template>
  <nav class="dock" aria-label="Ferramentas do Projeto de Rede" data-testid="nd-dock">
    <button
      v-for="t in TOOLS"
      :key="t.mode"
      type="button"
      class="dock-btn"
      :class="{ 'dock-on': modelValue === t.mode }"
      :title="`${t.label} — ${t.hint}`"
      :aria-pressed="modelValue === t.mode"
      :data-testid="`dock-${t.mode}`"
      @click="$emit('update:modelValue', modelValue === t.mode ? 'select' : t.mode)"
    >
      <component :is="t.icon" :size="18" />
      <span class="dock-label">{{ t.label }}</span>
    </button>
  </nav>
  <p v-if="hint" class="dock-hint" role="status" data-testid="nd-dock-hint">
    {{ hint }} <span class="dock-esc">Esc sai</span>
  </p>
</template>

<script setup>
/** Barra de modos do Projeto de Rede (EV-0138). */
import { computed } from 'vue'
import { PhCursor, PhMapPin, PhPath, PhPackage, PhSquare, PhLineVertical, PhSpiral, PhRuler } from '@phosphor-icons/vue'

const props = defineProps({
  modelValue: { type: String, default: 'select' },
  /** texto do modo «move» (objeto a mover) */
  moving: { type: String, default: '' },
})
defineEmits(['update:modelValue'])

const TOOLS = [
  { mode: 'select', label: 'Selecionar', icon: PhCursor, hint: 'clique direito para ações; nada é desenhado' },
  { mode: 'site', label: 'Novo site', icon: PhMapPin, hint: 'clique no mapa onde fica o site / POP' },
  { mode: 'trace', label: 'Traçar cabo', icon: PhPath, hint: 'clique ponto a ponto; perto de um site ou CEO o ponto cola nele' },
  { mode: 'ceo', label: 'Inserir CEO', icon: PhPackage, hint: 'clique sobre um cabo onde fica a caixa' },
  { mode: 'cto', label: 'Inserir CTO', icon: PhSquare, hint: 'clique sobre um cabo (fica no traçado) ou no mapa (solta)' },
  { mode: 'pole', label: 'Inserir poste', icon: PhLineVertical, hint: 'clique no mapa onde fica o poste' },
  { mode: 'slack', label: 'Reserva técnica', icon: PhSpiral, hint: 'clique sobre um cabo onde fica a sobra' },
  { mode: 'measure', label: 'Medir', icon: PhRuler, hint: 'clique ponto a ponto para medir a distância' },
]

const hint = computed(() => {
  if (props.modelValue === 'move') return `Mover ${props.moving}: clique no novo ponto (sobre o cabo, para CEO e reserva).`
  if (props.modelValue === 'select') return ''
  return TOOLS.find((t) => t.mode === props.modelValue)?.hint.replace(/^./, (c) => c.toUpperCase()) || ''
})
</script>

<style scoped>
.dock {
  /* EV-0139: horizontal no topo, por baixo da busca — à esquerda abrem Pastas e Camadas */
  position: absolute;
  left: 50%;
  top: 62px;
  z-index: 25;
  transform: translateX(-50%);
  width: max-content;
  max-width: calc(100% - 32px);
  display: flex;
  flex-direction: row;
  gap: 2px;
  padding: 4px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 10px;
  background: rgb(var(--surface));
  box-shadow: 0 6px 18px rgb(0 0 0 / 0.18);
}
@media (max-width: 1280px) {
  .dock-label {
    display: none;
  }
  .dock-on .dock-label {
    display: inline;
  }
}
.dock-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 10px 0 8px;
  border-radius: 7px;
  font-size: 12px;
  color: rgb(var(--n-700));
  white-space: nowrap;
}
.dock-btn:hover {
  background: rgb(var(--n-100));
}
.dock-on {
  color: rgb(var(--primary-700));
  background: rgb(var(--primary-500) / 0.14);
  font-weight: 600;
}
.dock-hint {
  position: absolute;
  left: 50%;
  bottom: 28px;
  z-index: 25;
  transform: translateX(-50%);
  margin: 0;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgb(var(--n-900));
  color: rgb(var(--n-50));
  font-size: 12px;
  box-shadow: 0 4px 14px rgb(0 0 0 / 0.25);
}
.dock-esc {
  margin-left: 8px;
  opacity: 0.65;
}
</style>
