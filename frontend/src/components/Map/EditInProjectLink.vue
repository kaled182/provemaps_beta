<template>
  <RouterLink
    v-if="location"
    :to="location"
    class="eip"
    :title="`Abrir ${LABEL[type]} no Projeto de Rede para editar a topologia física`"
    data-testid="edit-in-project"
  >
    Editar no Projeto <span aria-hidden="true">↗</span>
  </RouterLink>
</template>

<script setup>
/**
 * EV-0137: o mapa de monitoramento é só leitura para a topologia física; a edição faz-se no
 * Projeto de Rede, aberto já focado no objeto (contrato `?foco=&id=&lat=&lng=` do Ctrl K).
 */
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { focusLocationFor } from '@/utils/mapFocus'

const props = defineProps({
  type: { type: String, required: true }, // site | cable | ceo
  target: { type: Object, default: null },
})
const LABEL = { site: 'o site', cable: 'o cabo', ceo: 'a CEO' }
const location = computed(() => focusLocationFor(props.type, props.target))
</script>

<style scoped>
.eip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 6px;
  font-size: 12px;
  color: rgb(var(--n-600));
  white-space: nowrap;
}
.eip:hover {
  border-color: rgb(var(--primary-500));
  color: rgb(var(--primary-600));
}
</style>
