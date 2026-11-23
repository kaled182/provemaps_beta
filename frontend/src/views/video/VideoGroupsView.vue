<template>
  <div :class="embedded ? 'p-6' : 'p-6'">
    <h1 v-if="!embedded" class="text-2xl font-semibold text-neutral-900">Grupos de Câmeras</h1>
    <p class="mt-2 text-sm text-neutral-500">
      Gerenciamento de grupos de câmeras será disponibilizado em breve.
    </p>
  </div>
</template>

<script setup>
const props = defineProps({
  embedded: { type: Boolean, default: false }
});

// TODO: Implement camera groups management
</script>
