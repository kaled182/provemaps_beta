<template>
  <div
    ref="el"
    class="om"
    role="menu"
    :style="{ left: `${pos.x}px`, top: `${pos.y}px` }"
    data-testid="nd-object-menu"
    @contextmenu.prevent
  >
    <p class="om-title">{{ title }}</p>
    <button
      v-for="it in items"
      :key="it.key"
      type="button"
      role="menuitem"
      class="om-item"
      :class="{ 'om-danger': it.danger }"
      :data-testid="`om-${it.key}`"
      @click="$emit('pick', it.key)"
    >
      {{ it.label }}
    </button>
  </div>
</template>

<script setup>
/** Menu de contexto de um objeto do Projeto de Rede (site, CEO, reserva) — EV-0138. */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  x: { type: Number, required: true },
  y: { type: Number, required: true },
  title: { type: String, default: '' },
  items: { type: Array, required: true },
})
const emit = defineEmits(['pick', 'close'])
const el = ref(null)

/** Não sair do ecrã (menu com ~200 px de largura). */
const pos = computed(() => ({
  x: Math.min(props.x, window.innerWidth - 230),
  y: Math.min(props.y, window.innerHeight - (40 + props.items.length * 34)),
}))

function outside(e) {
  if (el.value && !el.value.contains(e.target)) emit('close')
}
function key(e) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => {
  setTimeout(() => document.addEventListener('mousedown', outside), 0)
  document.addEventListener('keydown', key)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', outside)
  document.removeEventListener('keydown', key)
})
</script>

<style scoped>
.om {
  position: fixed;
  z-index: 70;
  min-width: 210px;
  padding: 6px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 10px;
  background: rgb(var(--surface));
  box-shadow: 0 10px 28px rgb(0 0 0 / 0.22);
}
.om-title {
  margin: 2px 8px 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: rgb(var(--n-500));
}
.om-item {
  display: block;
  width: 100%;
  padding: 7px 10px;
  border-radius: 6px;
  text-align: left;
  font-size: 13px;
  color: rgb(var(--n-800));
}
.om-item:hover {
  background: rgb(var(--n-100));
}
.om-danger {
  color: rgb(var(--danger));
}
</style>
