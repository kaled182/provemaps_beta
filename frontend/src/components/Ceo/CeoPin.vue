<template>
  <span class="ceo-pin" role="button" tabindex="0" :aria-label="`CEO ${name} — abrir o cartão`" :title="name" data-testid="ceo-pin" @click="$emit('open')" @keydown.enter.prevent="$emit('open')">
    <span class="ceo-core" :class="{ 'ceo-cut': mode === 'corte' }" aria-hidden="true" />
  </span>
</template>

<script setup>
/** Marcador da CEO no traçado (EV-0135): losango; sólido no modo corte, vazado na sangria. */
defineProps({ name: { type: String, default: '' }, mode: { type: String, default: 'sangria' } })
defineEmits(['open'])
</script>

<style scoped>
.ceo-pin {
  display: block;
  width: 16px;
  height: 16px;
  cursor: pointer;
  pointer-events: auto;
}
.ceo-core {
  display: block;
  width: 12px;
  height: 12px;
  margin: 2px;
  transform: rotate(45deg);
  border: 2px solid rgb(var(--info));
  border-radius: 2px;
  background: rgb(var(--surface));
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.35);
}
.ceo-cut {
  background: rgb(var(--info));
}
</style>
