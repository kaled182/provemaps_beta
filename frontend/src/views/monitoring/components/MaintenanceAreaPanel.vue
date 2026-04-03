<template>
  <div v-if="visible" class="maint-panel">
    <div class="maint-header">
      <div class="maint-title">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="3 11 22 2 13 21 11 13 3 11"/>
        </svg>
        Área de Manutenção
      </div>
      <div class="maint-header-actions">
        <button
          class="btn-maint-action"
          :disabled="total === 0"
          title="Exportar CSV"
          @click="$emit('export-csv')"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          CSV
        </button>
        <button class="btn-maint-close" title="Fechar painel" @click="$emit('close')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="maint-hint" v-if="vertexCount < 3">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      Clique no mapa para desenhar o polígono ({{ vertexCount }}/3 pontos mínimos)
    </div>

    <div class="maint-summary" v-else>
      <span class="ms-item">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        </svg>
        {{ affectedDevices.length }} equipamentos
      </span>
      <span class="ms-sep">·</span>
      <span class="ms-item">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        {{ affectedCables.length }} cabos
      </span>
    </div>

    <div class="maint-body" v-if="vertexCount >= 3">
      <div v-if="total === 0" class="maint-empty">
        Nenhum elemento na área selecionada
      </div>

      <template v-else>
        <!-- Cabos afetados -->
        <div v-if="affectedCables.length > 0" class="maint-section">
          <div class="maint-section-title">
            Cabos ({{ affectedCables.length }})
          </div>
          <div
            v-for="cable in affectedCables"
            :key="cable.id"
            class="maint-row"
          >
            <span class="mr-dot" :class="`mr-dot--${cable.status || 'unknown'}`"></span>
            <span class="mr-name">{{ cable.name || `Cabo #${cable.id}` }}</span>
            <span v-if="cable.status" class="mr-status" :class="`mr-status--${cable.status}`">
              {{ statusLabel(cable.status) }}
            </span>
          </div>
        </div>

        <!-- Equipamentos afetados agrupados por site -->
        <div v-if="affectedDevices.length > 0" class="maint-section">
          <div class="maint-section-title">
            Equipamentos ({{ affectedDevices.length }})
          </div>
          <template v-for="site in devicesBySite" :key="site.site_name">
            <div class="maint-site-name">{{ site.site_name }}</div>
            <div
              v-for="device in site.devices"
              :key="device.id"
              class="maint-row maint-row--indent"
            >
              <span class="mr-dot" :class="`mr-dot--${device.status || 'unknown'}`"></span>
              <span class="mr-name">{{ device.name }}</span>
            </div>
          </template>
        </div>
      </template>
    </div>

    <div class="maint-footer">
      <button
        class="btn-notify-area"
        :disabled="total === 0"
        title="Notificar responsáveis"
        @click="$emit('notify')"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.41 2 2 0 0 1 3.6 1.23h3a2 2 0 0 1 2 1.72c.13 1 .36 1.97.72 2.9a2 2 0 0 1-.45 2.11L7.91 9A16 16 0 0 0 14 15.08l.96-.96a2 2 0 0 1 2.11-.45c.93.35 1.9.59 2.9.72a2 2 0 0 1 1.72 2.03z"/>
        </svg>
        Notificar
      </button>
      <button class="btn-clear-area" @click="$emit('clear')">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/>
        </svg>
        Limpar
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  vertexCount: { type: Number, default: 0 },
  affectedCables: { type: Array, default: () => [] },
  affectedDevices: { type: Array, default: () => [] }
})

defineEmits(['close', 'clear', 'export-csv', 'notify'])

const total = computed(() => props.affectedCables.length + props.affectedDevices.length)

const devicesBySite = computed(() => {
  const siteMap = new Map()
  props.affectedDevices.forEach(device => {
    const key = device.site_name || 'Sem Site'
    if (!siteMap.has(key)) siteMap.set(key, { site_name: key, devices: [] })
    siteMap.get(key).devices.push(device)
  })
  return Array.from(siteMap.values()).sort((a, b) => a.site_name.localeCompare(b.site_name))
})

const STATUS_LABELS = {
  online: 'Online', offline: 'Offline', warning: 'Atenção',
  critical: 'Crítico', unknown: 'Desconhecido'
}

function statusLabel(s) {
  return STATUS_LABELS[s] || s
}
</script>

<style scoped>
.maint-panel {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 200;
  width: 280px;
  max-height: calc(100% - 48px);
  display: flex;
  flex-direction: column;
  background: rgba(15, 23, 42, 0.92);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(245, 158, 11, 0.35);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}

.maint-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 10px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  flex-shrink: 0;
}

.maint-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  color: #f59e0b;
}

.maint-header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.btn-maint-action {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: rgba(16,185,129,0.15);
  border: 1px solid rgba(16,185,129,0.3);
  border-radius: 6px;
  color: #6ee7b7;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-maint-action:hover:not(:disabled) { background: rgba(16,185,129,0.25); }
.btn-maint-action:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-maint-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  color: rgba(255,255,255,0.5);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.btn-maint-close:hover { background: rgba(239,68,68,0.2); color: #fca5a5; border-color: rgba(239,68,68,0.3); }

.maint-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  font-size: 0.75rem;
  color: rgba(255,255,255,0.5);
  flex-shrink: 0;
}

.maint-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(245,158,11,0.08);
  border-bottom: 1px solid rgba(255,255,255,0.06);
  flex-shrink: 0;
}

.ms-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  color: #fbbf24;
  font-weight: 600;
}
.ms-sep { color: rgba(255,255,255,0.3); font-size: 0.75rem; }

.maint-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.maint-empty {
  padding: 16px 12px;
  font-size: 0.75rem;
  color: rgba(255,255,255,0.35);
  text-align: center;
}

.maint-section {
  margin-bottom: 4px;
}

.maint-section-title {
  padding: 6px 12px 4px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(255,255,255,0.35);
}

.maint-site-name {
  padding: 4px 12px 2px;
  font-size: 0.72rem;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
}

.maint-row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 4px 12px;
  font-size: 0.78rem;
}

.maint-row--indent {
  padding-left: 20px;
}

.mr-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.mr-dot--online   { background: #10b981; }
.mr-dot--offline  { background: #ef4444; }
.mr-dot--warning  { background: #f59e0b; }
.mr-dot--critical { background: #f97316; }
.mr-dot--unknown  { background: #64748b; }

.mr-name {
  flex: 1;
  color: #e2e8f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mr-status {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 4px;
  flex-shrink: 0;
}
.mr-status--online   { color: #6ee7b7; background: rgba(16,185,129,0.15); }
.mr-status--offline  { color: #fca5a5; background: rgba(239,68,68,0.15); }
.mr-status--warning  { color: #fde68a; background: rgba(245,158,11,0.15); }
.mr-status--critical { color: #fdba74; background: rgba(249,115,22,0.15); }
.mr-status--unknown  { color: #94a3b8; background: rgba(100,116,139,0.15); }

.maint-footer {
  flex-shrink: 0;
  padding: 10px 12px;
  border-top: 1px solid rgba(255,255,255,0.08);
  display: flex;
  gap: 6px;
}

.btn-notify-area {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: 1;
  padding: 7px 10px;
  background: rgba(245,158,11,0.15);
  border: 1px solid rgba(245,158,11,0.35);
  border-radius: 7px;
  color: #fde68a;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  justify-content: center;
  transition: background 0.15s;
}
.btn-notify-area:hover:not(:disabled) { background: rgba(245,158,11,0.25); }
.btn-notify-area:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-clear-area {
  display: flex;
  align-items: center;
  gap: 5px;
  flex: 1;
  padding: 7px 10px;
  background: rgba(239,68,68,0.12);
  border: 1px solid rgba(239,68,68,0.25);
  border-radius: 7px;
  color: #fca5a5;
  font-size: 0.75rem;
  font-weight: 500;
  cursor: pointer;
  justify-content: center;
  transition: background 0.15s;
}
.btn-clear-area:hover { background: rgba(239,68,68,0.22); }

/* Light theme */
:root[data-theme="light"] .maint-panel {
  background: rgba(255,255,255,0.96);
  border-color: rgba(245,158,11,0.4);
}
:root[data-theme="light"] .maint-title { color: #d97706; }
:root[data-theme="light"] .maint-hint { color: #64748b; }
:root[data-theme="light"] .ms-item { color: #b45309; }
:root[data-theme="light"] .maint-section-title { color: #94a3b8; }
:root[data-theme="light"] .maint-site-name { color: #475569; }
:root[data-theme="light"] .mr-name { color: #1e293b; }
:root[data-theme="light"] .maint-empty { color: #94a3b8; }
:root[data-theme="light"] .maint-summary { background: rgba(245,158,11,0.06); }
</style>
