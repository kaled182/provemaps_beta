<template>
  <div class="skeleton-container" aria-busy="true" aria-label="Loading content">
    <!-- Status chart skeleton -->
    <div class="skeleton-chart">
      <div class="skeleton-bar"></div>
      <div class="skeleton-bar"></div>
      <div class="skeleton-bar"></div>
      <div class="skeleton-bar"></div>
    </div>
    
    <!-- Filter bar skeleton -->
    <div class="skeleton-filters">
      <div class="skeleton-input"></div>
      <div class="skeleton-dropdown"></div>
      <div class="skeleton-dropdown"></div>
      <div class="skeleton-dropdown"></div>
    </div>
    
    <!-- Host cards skeleton -->
    <div class="skeleton-cards">
      <div v-for="i in 5" :key="i" class="skeleton-card">
        <div class="skeleton-icon"></div>
        <div class="skeleton-content">
          <div class="skeleton-line skeleton-line--title"></div>
          <div class="skeleton-line skeleton-line--subtitle"></div>
        </div>
      </div>
    </div>
    
    <span class="sr-only">Loading dashboard data, please wait...</span>
  </div>
</template>

<style scoped>
@keyframes shimmer {
  0% {
    background-position: -468px 0;
  }
  100% {
    background-position: 468px 0;
  }
}

.skeleton-container {
  padding: 1rem;
}

.skeleton-chart,
.skeleton-filters,
.skeleton-cards {
  margin-bottom: 1.5rem;
}

.skeleton-bar,
.skeleton-input,
.skeleton-dropdown,
.skeleton-card,
.skeleton-icon,
.skeleton-line {
  background: linear-gradient(
    to right,
    var(--surface-muted) 0%,
    var(--surface-highlight) 20%,
    var(--surface-muted) 40%,
    var(--surface-muted) 100%
  );
  background-size: 800px 100px;
  animation: shimmer 1.5s infinite linear;
  border-radius: 4px;
}

.skeleton-bar {
  height: 40px;
  margin-bottom: 0.5rem;
}

.skeleton-input {
  height: 40px;
  margin-bottom: 1rem;
}

.skeleton-dropdown {
  height: 38px;
  margin-bottom: 0.5rem;
}

.skeleton-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  margin-bottom: 0.5rem;
  background: var(--surface-card);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
}

.skeleton-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton-content {
  flex: 1;
}

.skeleton-line {
  height: 16px;
  margin-bottom: 0.5rem;
}

.skeleton-line--title {
  width: 60%;
}

.skeleton-line--subtitle {
  width: 40%;
}

/* Screen reader only text */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
