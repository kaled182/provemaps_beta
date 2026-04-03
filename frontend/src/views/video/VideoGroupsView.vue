<template>
  <div :class="embedded ? 'p-6' : 'p-6'">
    <h1 v-if="!embedded" class="text-2xl font-semibold text-gray-900 dark:text-white">Grupos de Câmeras</h1>
    <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
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
