<template>
  <div class="cc" :data-testid="`ceo-card-${ceo.id}`">
    <header class="cc-head">
      <span class="cc-mark" aria-hidden="true" />
      <span class="font-semibold">{{ ceo.name }}</span>
      <button type="button" class="cc-x" aria-label="Fechar" @click="$emit('close')">×</button>
    </header>
    <dl class="cc-facts">
      <dt>Cabo</dt>
      <dd>{{ ceo.cable_name || '—' }}</dd>
      <dt>No cabo</dt>
      <dd class="num">km {{ ceo.km.toLocaleString('pt-BR', { minimumFractionDigits: 3 }) }}</dd>
      <dt>Passagem</dt>
      <dd data-testid="ceo-card-mode">{{ ceo.mode_label }}</dd>
      <dt>Reserva</dt>
      <dd class="num">{{ ceo.slack_m === null || ceo.slack_m === undefined ? '—' : `${ceo.slack_m} m` }}</dd>
      <dt>Bandejas</dt>
      <dd class="num">{{ ceo.trays ?? '—' }}</dd>
      <dt>Derivados</dt>
      <dd data-testid="ceo-card-derived">{{ ceo.derived.length ? ceo.derived.map((d) => d.name).join(', ') : 'nenhum' }}</dd>
    </dl>
    <div class="cc-actions">
      <button type="button" class="cc-btn" data-testid="ceo-fusions" @click="$emit('fusions', ceo)">Ver emendas</button>
      <EditInProjectLink type="ceo" :target="ceo" />
    </div>
  </div>
</template>

<script setup>
/** Cartão de uma CEO no mapa de monitoramento (EV-0135), só leitura (EV-0137): editar é no Projeto. */
import EditInProjectLink from '@/components/Map/EditInProjectLink.vue'

defineProps({ ceo: { type: Object, required: true } })
defineEmits(['close', 'fusions'])
</script>

<style scoped>
.cc {
  width: 270px;
  padding: 10px 12px;
  font-size: 12px;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.cc-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
  color: rgb(var(--n-900));
}
.cc-mark {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: rgb(var(--info));
  transform: rotate(45deg);
}
.cc-x {
  margin-left: auto;
  font-size: 16px;
  color: rgb(var(--n-500));
}
.cc-facts {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 3px 10px;
  margin: 0;
}
.cc-facts dt {
  color: rgb(var(--n-500));
}
.cc-facts dd {
  margin: 0;
  color: rgb(var(--n-900));
  overflow-wrap: anywhere;
}
.cc-actions {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}
.cc-btn {
  height: 28px;
  padding: 0 10px;
  border: 1px solid rgb(var(--primary-500));
  border-radius: 6px;
  font-size: 12px;
  color: rgb(var(--primary-700));
  background: rgb(var(--surface));
}
.cc-btn:hover {
  background: rgb(var(--primary-500) / 0.1);
}
</style>
