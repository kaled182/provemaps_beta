<template>
  <div
    class="group app-surface rounded-xl shadow-sm hover:shadow-md transition-all duration-200 flex flex-col overflow-hidden cursor-pointer h-full border-l-4 site-card"
    :style="statusStyles.card"
  >
    <div class="h-1.5 w-full" :style="{ background: statusStyles.bar }"></div>

    <div class="p-5 flex-1 flex flex-col">
      <div class="flex justify-between items-start mb-3">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg flex items-center justify-center text-lg" :style="iconStyle">
            <i :class="['fas', iconClass]"></i>
          </div>
          <div>
            <h3 class="text-base font-bold app-text-primary leading-tight transition-colors site-title">
              {{ site.name }}
            </h3>
            <span class="text-xs app-text-tertiary uppercase font-semibold tracking-wider">{{ site.type }}</span>
          </div>
        </div>
        <span
          class="text-xs px-2 py-1 rounded-full font-semibold"
          :style="statusStyles.badge"
        >
          {{ site.status || 'N/D' }}
        </span>
        <div class="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
          <button
            @click.stop="$emit('edit', site)"
            class="p-1.5 app-text-tertiary rounded-md transition-colors site-action"
            title="Editar"
          >
            <i class="fas fa-pencil-alt"></i>
          </button>
          <button
            @click.stop="$emit('delete', site)"
            class="p-1.5 app-text-tertiary rounded-md transition-colors site-action"
            title="Remover"
          >
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>

      <div class="mt-2 space-y-2 flex-1">
        <div class="flex items-start gap-2 text-sm app-text-tertiary min-h-[40px]">
          <i class="fas fa-map-marker-alt mt-1 app-text-tertiary"></i>
          <span class="line-clamp-2">{{ site.address || 'Sem endereço definido' }}</span>
        </div>
      </div>

      <div class="mt-4 pt-3 border-t app-divider flex justify-between items-center">
        <div class="flex items-center gap-2 text-sm font-medium app-text-secondary">
          <i class="fas fa-server app-text-tertiary"></i>
          {{ site.device_count }} <span class="text-xs font-normal app-text-tertiary">Devices</span>
        </div>
        <button
          @click.stop="$emit('view', site)"
          class="text-xs font-medium site-link"
        >
          Ver Detalhes
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  site: { type: Object, required: true },
});

const statusPalette = {
  active: { color: 'var(--status-online)', soft: 'var(--status-online-light)' },
  maintenance: { color: 'var(--status-warning)', soft: 'var(--warning-soft-bg)' },
  inactive: { color: 'var(--status-offline)', soft: 'var(--danger-soft-bg)' },
  down: { color: 'var(--status-offline)', soft: 'var(--danger-soft-bg)' },
  planning: { color: 'var(--accent-info)', soft: 'var(--info-soft-bg)' },
  unknown: { color: 'var(--status-unknown)', soft: 'var(--badge-neutral-bg)' },
};

const statusStyles = computed(() => {
  const key = props.site.status?.toLowerCase() || 'unknown';
  const palette = statusPalette[key] || statusPalette.unknown;
  return {
    bar: palette.color,
    card: { borderLeftColor: palette.color },
    badge: { background: palette.soft, color: palette.color },
  };
});

const iconClass = computed(() => {
  switch (props.site.type) {
    case 'datacenter':
      return 'fa-database';
    case 'pop':
      return 'fa-network-wired';
    case 'customer':
      return 'fa-building';
    default:
      return 'fa-map-pin';
  }
});

const iconStyle = computed(() => {
  switch (props.site.type) {
    case 'datacenter':
      return { background: 'var(--info-soft-bg)', color: 'var(--accent-info)' };
    case 'pop':
      return { background: 'var(--badge-info-bg)', color: 'var(--accent-info)' };
    case 'customer':
      return { background: 'var(--badge-neutral-bg)', color: 'var(--accent-primary)' };
    default:
      return { background: 'var(--surface-muted)', color: 'var(--text-tertiary)' };
  }
});
</script>

<style scoped>
.site-card:hover .site-title {
  color: var(--accent-info);
}

.site-action:hover {
  background: var(--menu-item-hover);
  color: var(--text-primary);
}

.site-link {
  color: var(--accent-info);
}

.site-link:hover {
  text-decoration: underline;
}
</style>
