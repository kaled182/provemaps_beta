<template>
  <div class="site-cameras-tab">
    <!-- Lista de Mosaicos -->
    <div v-if="!currentMosaic" class="mosaics-section">
      <div v-if="loading" class="loading-state">
        <i class="fas fa-spinner fa-spin"></i>
        <span>Carregando mosaicos...</span>
      </div>

      <div v-else-if="error" class="error-state">
        <i class="fas fa-exclamation-triangle"></i>
        <span>Erro ao carregar mosaicos</span>
        <button @click="handleFetchMosaics" class="retry-button">
          Tentar novamente
        </button>
      </div>

      <div v-else-if="mosaics.length === 0" class="empty-state">
        <i class="fas fa-video-slash"></i>
        <span>Nenhum mosaico configurado para este site</span>
        <p class="help-text">Configure mosaicos em Configurações > Câmeras</p>
      </div>

      <div v-else class="mosaics-grid">
        <div
          v-for="mosaic in mosaics"
          :key="mosaic.id"
          class="mosaic-card"
          @click="handleOpenMosaic(mosaic.id)"
        >
          <div class="mosaic-icon">
            <i class="fas fa-th"></i>
          </div>
          <div class="mosaic-info">
            <h4>{{ mosaic.name }}</h4>
            <p>{{ mosaic.cameras?.length || 0 }} câmeras</p>
          </div>
          <i class="fas fa-chevron-right"></i>
        </div>
      </div>
    </div>

    <!-- Visualizador de Mosaico -->
    <div v-else class="mosaic-viewer">
      <div class="mosaic-header">
        <button @click="handleCloseMosaic" class="back-button">
          <i class="fas fa-arrow-left"></i>
          Voltar
        </button>
        <h3>{{ currentMosaic.name }}</h3>
      </div>

      <div v-if="loading" class="loading-state">
        <i class="fas fa-spinner fa-spin"></i>
        <span>Carregando câmeras...</span>
      </div>

      <div v-else-if="cameras.length === 0" class="empty-state">
        <i class="fas fa-video-slash"></i>
        <span>Nenhuma câmera no mosaico</span>
      </div>

      <div v-else class="mosaic-grid" :class="gridClass">
        <div
          v-for="(camera, idx) in cameras"
          :key="camera.id || idx"
          class="mosaic-cell"
        >
          <div class="mosaic-video-container">
            <CameraPlayer
              :camera="camera"
              :autoplay="true"
              :muted="true"
            />
            <div class="mosaic-overlay">
              <span class="mosaic-camera-name">{{ camera.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useSiteCameras } from '@/composables/useSiteCameras'
import CameraPlayer from '@/components/Video/CameraPlayer.vue'

const props = defineProps({
  /**
   * ID do site para buscar mosaicos
   */
  siteId: {
    type: Number,
    required: true
  }
})

const {
  mosaics,
  cameras,
  currentMosaic,
  loading,
  error,
  hasCameras,
  fetchMosaics,
  loadMosaic,
  startStreams,
  stopStreams
} = useSiteCameras()

// Computed: classe da grid baseada no número de câmeras
const gridClass = computed(() => {
  const count = cameras.value.length
  if (count === 1) return 'mosaic-grid-1'
  if (count === 2) return 'mosaic-grid-2'
  if (count <= 4) return 'mosaic-grid-4'
  if (count <= 6) return 'mosaic-grid-6'
  if (count <= 9) return 'mosaic-grid-9'
  return 'mosaic-grid-16'
})

// Buscar mosaicos ao montar
onMounted(async () => {
  await handleFetchMosaics()
})

// Limpar ao desmontar
onUnmounted(async () => {
  await stopStreams()
})

// Handlers
async function handleFetchMosaics() {
  await fetchMosaics(props.siteId)
}

async function handleOpenMosaic(mosaicId) {
  await loadMosaic(mosaicId, props.siteId)
  
  if (!error.value) {
    // Streams iniciam em background (não bloqueia UI)
    setTimeout(() => {
      startStreams()
    }, 100)
  }
}

async function handleCloseMosaic() {
  await stopStreams()
}

// Watch siteId changes
watch(() => props.siteId, async (newId) => {
  if (newId) {
    await handleFetchMosaics()
  }
})
</script>

<style scoped>
.site-cameras-tab {
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

.loading-state i {
  color: #667eea;
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
  margin-top: 4px;
}

.retry-button {
  margin-top: 16px;
  padding: 8px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-button:hover {
  background: #5568d3;
}

/* Mosaics Grid */
.mosaics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.mosaic-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.2s;
}

.mosaic-card:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.mosaic-icon {
  width: 48px;
  height: 48px;
  background: #f1f5f9;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #667eea;
  font-size: 20px;
  flex-shrink: 0;
}

.mosaic-info {
  flex: 1;
}

.mosaic-info h4 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.mosaic-info p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
}

.mosaic-card > i {
  color: #cbd5e1;
  font-size: 14px;
}

/* Mosaic Viewer */
.mosaic-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.mosaic-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.back-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.back-button:hover {
  border-color: #667eea;
  color: #667eea;
}

.mosaic-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

/* Mosaic Grid Layouts */
.mosaic-grid {
  display: grid;
  gap: 16px;
  flex: 1;
  overflow: auto;
  align-content: start;
}

.mosaic-grid-1 {
  grid-template-columns: 1fr;
}

.mosaic-grid-2 {
  grid-template-columns: repeat(2, 1fr);
}

.mosaic-grid-4 {
  grid-template-columns: repeat(2, 1fr);
  grid-auto-rows: minmax(300px, 1fr);
}

.mosaic-grid-6 {
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: minmax(250px, 1fr);
}

.mosaic-grid-9 {
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: minmax(200px, 1fr);
}

.mosaic-grid-16 {
  grid-template-columns: repeat(4, 1fr);
  grid-auto-rows: minmax(180px, 1fr);
}

.mosaic-cell {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  min-height: 240px;
}

.mosaic-video-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.mosaic-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.7), transparent);
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mosaic-camera-name {
  color: white;
  font-size: 13px;
  font-weight: 500;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}

/* Dark Mode Support */
@media (prefers-color-scheme: dark) {
  .mosaic-card {
    background: #1e293b;
    border-color: #334155;
  }

  .mosaic-icon {
    background: #0f172a;
  }

  .mosaic-info h4 {
    color: #f1f5f9;
  }

  .back-button {
    background: #1e293b;
    border-color: #334155;
    color: #cbd5e1;
  }

  .mosaic-header h3 {
    color: #f1f5f9;
  }

  .mosaic-header {
    border-bottom-color: #334155;
  }
}

/* Responsive */
@media (max-width: 768px) {
  .mosaics-grid {
    grid-template-columns: 1fr;
  }

  .mosaic-grid-2,
  .mosaic-grid-4,
  .mosaic-grid-6,
  .mosaic-grid-9,
  .mosaic-grid-16 {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
  }

  .mosaic-cell {
    min-height: 200px;
  }
}
</style>
