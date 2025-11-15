<script setup>
</script>

<template>
  <section class="monitoring-placeholder" aria-labelledby="dwdm-monitoring-title">
    <header>
      <h1 id="dwdm-monitoring-title">DWDM Monitoring</h1>
      <p>Gerencie enlaces óticos de alta capacidade e status de lambdas.</p>
    </header>
    <div class="monitoring-placeholder__body">
      <p>Este módulo está em desenvolvimento. Em breve trará métricas de canais, potência óptica e alertas específicos para DWDM.</p>
    </div>
  </section>
</template>

<style scoped>
.monitoring-placeholder {
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  color: var(--text-primary);
}

.monitoring-placeholder h1 {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 700;
}

.monitoring-placeholder p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 1rem;
}

.monitoring-placeholder__body {
  padding: 1.5rem;
  border-radius: 10px;
  border: 1px dashed var(--border-primary);
  background: var(--surface-highlight);
}
</style>
