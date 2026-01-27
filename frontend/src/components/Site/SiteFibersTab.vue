<template>
  <div class="site-fibers-tab">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <i class="fas fa-spinner fa-spin"></i>
      <span>Carregando cabos de fibra...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <i class="fas fa-exclamation-triangle"></i>
      <span>Erro ao carregar cabos</span>
      <button @click="handleRefresh" class="retry-button">
        Tentar novamente
      </button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!hasFibers" class="empty-state">
      <i class="fas fa-network-wired"></i>
      <span>Nenhum cabo de fibra conectado a este site</span>
      <p class="help-text">Cabos serão exibidos quando conectados ao site</p>
    </div>

    <!-- Fibers List -->
    <div v-else class="fibers-content">
      <!-- Summary Header -->
      <div class="summary-header">
        <div class="summary-item">
          <i class="fas fa-network-wired"></i>
          <div>
            <span class="summary-label">Total de Cabos</span>
            <span class="summary-value">{{ fiberCount }}</span>
          </div>
        </div>
        <div class="summary-item">
          <i class="fas fa-check-circle text-green-500"></i>
          <div>
            <span class="summary-label">Ativos</span>
            <span class="summary-value">{{ activeFibers.length }}</span>
          </div>
        </div>
        <div class="summary-item">
          <i class="fas fa-ruler"></i>
          <div>
            <span class="summary-label">Comprimento Total</span>
            <span class="summary-value">{{ formatLength(totalLength) }}</span>
          </div>
        </div>
      </div>

      <!-- Fibers Grid -->
      <div class="fibers-grid">
        <div
          v-for="fiber in fibers"
          :key="fiber.id"
          class="fiber-card"
          @click="handleViewDetails(fiber)"
        >
          <!-- Header -->
          <div class="fiber-header">
            <div class="fiber-title">
              <i class="fas fa-link"></i>
              <span>{{ fiber.name }}</span>
            </div>
            <span
              class="fiber-status"
              :class="getStatusClass(fiber.status)"
            >
              {{ getStatusLabel(fiber.status) }}
            </span>
          </div>

          <!-- Route -->
          <div class="fiber-route">
            <div class="site-endpoint">
              <i class="fas fa-map-marker-alt text-blue-500"></i>
              <span>{{ fiber.site_a_name || 'Origem' }}</span>
            </div>
            <i class="fas fa-arrows-alt-h text-gray-400"></i>
            <div class="site-endpoint">
              <i class="fas fa-map-marker-alt text-purple-500"></i>
              <span>{{ fiber.site_b_name || 'Destino' }}</span>
            </div>
          </div>

          <!-- Info Row -->
          <div class="fiber-info">
            <div class="info-item">
              <i class="fas fa-ruler-horizontal"></i>
              <span>{{ formatLength(fiber.length_km) }}</span>
            </div>
            <div class="info-item" v-if="fiber.profile">
              <i class="fas fa-layer-group"></i>
              <span>{{ fiber.profile_name || 'Perfil' }}</span>
            </div>
            <div class="info-item">
              <i class="fas fa-sitemap"></i>
              <span>{{ getConnectionLabel(fiber.connection_status) }}</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="fiber-actions">
            <button
              @click.stop="handleViewStructure(fiber)"
              class="action-btn"
              title="Ver estrutura física"
            >
              <i class="fas fa-bullseye"></i>
            </button>
            <button
              @click.stop="handleViewMap(fiber)"
              class="action-btn"
              title="Ver no mapa"
            >
              <i class="fas fa-map-marked-alt"></i>
            </button>
            <button
              @click.stop="handleEdit(fiber)"
              class="action-btn"
              title="Editar cabo"
            >
              <i class="fas fa-edit"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { watch, onMounted } from 'vue'
import { useSiteFibers } from '@/composables/useSiteFibers'

const props = defineProps({
  /**
   * ID do site para buscar cabos de fibra
   */
  siteId: {
    type: Number,
    required: true
  }
})

const emit = defineEmits([
  'view-details',
  'view-structure',
  'view-map',
  'edit-fiber'
])

const {
  fibers,
  loading,
  error,
  hasFibers,
  fiberCount,
  activeFibers,
  totalLength,
  fetchFibers,
  refreshFibers,
  formatLength,
  getStatusClass,
  getStatusLabel,
  getConnectionLabel
} = useSiteFibers()

// Buscar fibras ao montar
onMounted(async () => {
  await fetchFibers(props.siteId)
})

// Watch siteId changes
watch(() => props.siteId, async (newId) => {
  if (newId) {
    await fetchFibers(newId)
  }
})

// Handlers
async function handleRefresh() {
  await refreshFibers(props.siteId)
}

function handleViewDetails(fiber) {
  emit('view-details', fiber)
}

function handleViewStructure(fiber) {
  emit('view-structure', fiber)
}

function handleViewMap(fiber) {
  emit('view-map', fiber)
}

function handleEdit(fiber) {
  emit('edit-fiber', fiber)
}
</script>

<style scoped>
.site-fibers-tab {
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Loading, Error, Empty States */
.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #64748b;
  text-align: center;
}

.loading-state i,
.error-state i,
.empty-state i {
  font-size: 48px;
  margin-bottom: 16px;
  color: #cbd5e1;
}

.loading-state i.fa-spin {
  color: #3b82f6;
}

.error-state i {
  color: #ef4444;
}

.loading-state span,
.error-state span,
.empty-state span {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
}

.help-text {
  font-size: 14px;
  color: #94a3b8;
  margin-top: 8px;
}

.retry-button {
  margin-top: 16px;
  padding: 8px 16px;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.2s;
}

.retry-button:hover {
  background-color: #2563eb;
}

/* Fibers Content */
.fibers-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  overflow-y: auto;
}

/* Summary Header */
.summary-header {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  padding: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.summary-item i {
  font-size: 24px;
  color: #3b82f6;
}

.summary-item div {
  display: flex;
  flex-direction: column;
}

.summary-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.summary-value {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
}

/* Fibers Grid */
.fibers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

/* Fiber Card */
.fiber-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.fiber-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
  transform: translateY(-2px);
}

/* Fiber Header */
.fiber-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.fiber-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #1e293b;
  flex: 1;
  min-width: 0;
}

.fiber-title i {
  color: #3b82f6;
  flex-shrink: 0;
}

.fiber-title span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fiber-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.status-up {
  background-color: #dcfce7;
  color: #166534;
}

.status-down {
  background-color: #fee2e2;
  color: #991b1b;
}

.status-degraded {
  background-color: #fed7aa;
  color: #9a3412;
}

.status-planned {
  background-color: #dbeafe;
  color: #1e40af;
}

.status-unknown {
  background-color: #f1f5f9;
  color: #475569;
}

/* Fiber Route */
.fiber-route {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background-color: #f8fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.site-endpoint {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
  font-size: 14px;
  color: #334155;
}

.site-endpoint i {
  flex-shrink: 0;
}

.site-endpoint span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Fiber Info */
.fiber-info {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #64748b;
  padding: 4px 8px;
  background-color: #f8fafc;
  border-radius: 4px;
}

.info-item i {
  color: #94a3b8;
  font-size: 12px;
}

/* Fiber Actions */
.fiber-actions {
  display: flex;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
}

.action-btn {
  flex: 1;
  padding: 8px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.action-btn:hover {
  background-color: #f1f5f9;
  color: #3b82f6;
  border-color: #3b82f6;
}

/* Utility Classes */
.text-green-500 {
  color: #22c55e;
}

.text-blue-500 {
  color: #3b82f6;
}

.text-purple-500 {
  color: #a855f7;
}

.text-gray-400 {
  color: #9ca3af;
}
</style>
