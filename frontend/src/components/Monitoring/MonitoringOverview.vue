<script setup>
import { computed } from 'vue';
import { PhShareNetwork, PhStackSimple, PhWaveform } from '@phosphor-icons/vue';

const modules = computed(() => [
  {
    label: 'Backbone',
    description: 'Visualize real-time backbone assets and status.',
    path: '/monitoring/backbone/',
    icon: PhShareNetwork,
  },
  {
    label: 'GPON',
    description: 'Operational view for GPON optical networks.',
    path: '/monitoring/gpon/',
    icon: PhStackSimple,
  },
  {
    label: 'DWDM',
    description: 'Insights for DWDM transport layers.',
    path: '/monitoring/dwdm/',
    icon: PhWaveform,
  },
]);
</script>

<template>
  <section class="monitoring-overview" aria-labelledby="monitoring-overview-title">
    <header class="monitoring-overview__header">
      <h1 id="monitoring-overview-title">Monitoring Suite</h1>
      <p>Selecione um módulo para acompanhar a infraestrutura.</p>
    </header>

    <div class="monitoring-overview__grid">
      <a
        v-for="module in modules"
        :key="module.path"
        :href="module.path"
        class="monitoring-overview__card"
      >
        <span class="monitoring-overview__icon" aria-hidden="true">
          <component :is="module.icon" :size="28" weight="duotone" />
        </span>
        <div class="monitoring-overview__content">
          <h2>{{ module.label }}</h2>
          <p>{{ module.description }}</p>
        </div>
      </a>
    </div>
  </section>
</template>

<style scoped>
.monitoring-overview {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1.5rem 2rem;
  color: var(--text-primary);
}

.monitoring-overview__header h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 700;
}

.monitoring-overview__header p {
  margin: 0.25rem 0 0;
  color: var(--text-tertiary);
}

.monitoring-overview__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem;
}

.monitoring-overview__card {
  display: flex;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 10px;
  text-decoration: none;
  background: var(--surface-highlight);
  border: 1px solid var(--border-primary);
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
  color: inherit;
}

.monitoring-overview__card:hover {
  transform: translateY(-2px);
  border-color: var(--accent-info);
  background: var(--surface-muted);
}

.monitoring-overview__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  background: var(--accent-info-light);
  color: var(--accent-info);
}

.monitoring-overview__content h2 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.monitoring-overview__content p {
  margin: 0.35rem 0 0;
  color: var(--text-secondary);
  font-size: 0.9rem;
}
</style>
