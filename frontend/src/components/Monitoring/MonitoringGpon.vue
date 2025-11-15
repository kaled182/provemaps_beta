<script setup>
</script>

<template>
  <section class="monitoring-placeholder" aria-labelledby="gpon-monitoring-title">
    <header>
      <h1 id="gpon-monitoring-title">GPON Monitoring</h1>
      <p>Interface dedicada ao monitoramento dos elementos GPON.</p>
    </header>
    <div class="monitoring-placeholder__body">
      <p>Estamos preparando esta visualização. Em breve você poderá acompanhar OLTs, ONUs e splits em tempo real.</p>
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
