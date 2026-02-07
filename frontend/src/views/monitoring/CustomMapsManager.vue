<template>
  <div class="custom-maps-manager">
    <!-- Header -->
    <div class="maps-header">
      <div class="header-content">
        <h1 class="title">
          <i class="fas fa-map-marked-alt"></i>
          Mapas Personalizados - {{ categoryLabel }}
        </h1>
        <button @click="showCreateModal = true" class="btn-create">
          <i class="fas fa-plus"></i>
          Criar Novo Mapa
        </button>
      </div>
    </div>

    <!-- Lista de Mapas -->
    <div class="maps-grid">
      <div 
        v-for="map in customMaps" 
        :key="map.id"
        class="map-card"
        @click="openMap(map)"
      >
        <div class="map-preview">
          <i class="fas fa-map"></i>
          <span class="items-count">{{ map.items_count || 0 }} itens</span>
        </div>
        <div class="map-info">
          <h3 class="map-name">{{ map.name }}</h3>
          <p class="map-description">{{ map.description || 'Sem descrição' }}</p>
          <div class="map-stats">
            <span class="stat">
              <i class="fas fa-server"></i> {{ map.devices_count || 0 }}
            </span>
            <span class="stat">
              <i class="fas fa-network-wired"></i> {{ map.cables_count || 0 }}
            </span>
            <span class="stat">
              <i class="fas fa-video"></i> {{ map.cameras_count || 0 }}
            </span>
          </div>
        </div>
        <div class="map-actions">
          <button @click.stop="editMap(map)" class="btn-icon">
            <i class="fas fa-edit"></i>
          </button>
          <button @click.stop="deleteMap(map)" class="btn-icon btn-danger">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>

      <!-- Mapa Padrão (sempre existe) -->
      <div class="map-card map-default" @click="openDefaultMap">
        <div class="map-preview default">
          <i class="fas fa-globe"></i>
          <span class="default-badge">Padrão</span>
        </div>
        <div class="map-info">
          <h3 class="map-name">Mapa Completo</h3>
          <p class="map-description">Visualização completa de todos os equipamentos</p>
        </div>
      </div>
    </div>

    <!-- Modal: Criar/Editar Mapa -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ editingMap ? 'Editar Mapa' : 'Criar Novo Mapa' }}</h2>
          <button @click="closeModal" class="btn-close">×</button>
        </div>
        
        <div class="modal-body">
          <div class="form-group">
            <label>Nome do Mapa</label>
            <input v-model="formData.name" type="text" placeholder="Ex: Backbone Brasília">
          </div>
          
          <div class="form-group">
            <label>Descrição</label>
            <textarea v-model="formData.description" rows="3" placeholder="Descreva o propósito deste mapa"></textarea>
          </div>

          <div class="form-group">
            <label>Categoria</label>
            <select v-model="formData.category">
              <option value="backbone">Backbone</option>
              <option value="gpon">GPON</option>
              <option value="dwdm">DWDM</option>
              <option value="custom">Personalizado</option>
            </select>
          </div>

          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_public">
              Mapa público (visível para todos os usuários)
            </label>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeModal" class="btn btn-secondary">Cancelar</button>
          <button @click="saveMap" class="btn btn-primary">
            {{ editingMap ? 'Salvar Alterações' : 'Criar Mapa' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useApi } from '@/composables/useApi'

const router = useRouter()
const route = useRoute()
const { get, post, put, del } = useApi()

const customMaps = ref([])
const showCreateModal = ref(false)
const editingMap = ref(null)
const formData = ref({
  name: '',
  description: '',
  category: 'backbone',
  is_public: true
})

const categoryLabel = computed(() => {
  const labels = {
    'backbone': 'Backbone',
    'gpon': 'GPON',
    'dwdm': 'DWDM'
  }
  return labels[route.params.category] || 'Todos'
})

const loadMaps = async () => {
  try {
    const response = await fetch('/api/v1/maps/custom/', {
      credentials: 'include'
    })
    
    if (!response.ok) {
      throw new Error(`Erro ao carregar mapas: ${response.status}`)
    }
    
    const data = await response.json()
    customMaps.value = data.maps || []
    console.log('[CustomMapsManager] Mapas carregados:', customMaps.value.length)
  } catch (error) {
    console.error('[CustomMapsManager] Erro ao carregar mapas:', error)
    customMaps.value = []
  }
}

const openMap = (map) => {
  router.push(`/monitoring/${map.category}/map/${map.id}`)
}

const openDefaultMap = () => {
  router.push(`/monitoring/${route.params.category || 'backbone'}/map/default`)
}

const editMap = (map) => {
  editingMap.value = map
  formData.value = { ...map }
  showCreateModal.value = true
}

const deleteMap = async (map) => {
  if (!confirm(`Tem certeza que deseja excluir o mapa "${map.name}"?`)) return
  
  try {
    const response = await fetch(`/api/v1/maps/custom/${map.id}/`, {
      method: 'DELETE',
      credentials: 'include',
      headers: {
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
      }
    })
    
    if (!response.ok) {
      throw new Error(`Erro ao excluir mapa: ${response.status}`)
    }
    
    loadMaps()
    console.log('[CustomMapsManager] Mapa excluído com sucesso')
  } catch (error) {
    console.error('[CustomMapsManager] Erro ao excluir mapa:', error)
    alert('Erro ao excluir mapa')
  }
}

const saveMap = async () => {
  try {
    const url = editingMap.value 
      ? `/api/v1/maps/custom/${editingMap.value.id}/`
      : '/api/v1/maps/custom/'
    
    const method = editingMap.value ? 'PUT' : 'POST'
    
    const response = await fetch(url, {
      method: method,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
      },
      body: JSON.stringify(formData.value)
    })
    
    if (!response.ok) {
      throw new Error(`Erro ao salvar mapa: ${response.status}`)
    }
    
    closeModal()
    loadMaps()
    console.log('[CustomMapsManager] Mapa salvo com sucesso')
  } catch (error) {
    console.error('[CustomMapsManager] Erro ao salvar mapa:', error)
    alert('Erro ao salvar mapa')
  }
}

const closeModal = () => {
  showCreateModal.value = false
  editingMap.value = null
  formData.value = {
    name: '',
    description: '',
    category: 'backbone',
    is_public: true
  }
}

onMounted(() => {
  loadMaps()
})
</script>

<style scoped>
.custom-maps-manager {
  min-height: 100vh;
  background: #1a1d2e;
  padding: 24px;
}

.maps-header {
  margin-bottom: 32px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1400px;
  margin: 0 auto;
}

.title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-create {
  padding: 12px 24px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-create:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
}

.maps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.map-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
}

.map-card:hover {
  border-color: rgba(16, 185, 129, 0.5);
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
}

.map-preview {
  height: 140px;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 78, 59, 0.1) 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  position: relative;
}

.map-preview i {
  font-size: 48px;
  color: rgba(16, 185, 129, 0.6);
}

.map-preview.default {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(67, 56, 202, 0.1) 100%);
}

.map-preview.default i {
  color: rgba(99, 102, 241, 0.6);
}

.items-count {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
}

.default-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 4px 12px;
  background: rgba(99, 102, 241, 0.2);
  border: 1px solid rgba(99, 102, 241, 0.4);
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  color: #6366f1;
  text-transform: uppercase;
}

.map-info {
  padding: 20px;
}

.map-name {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 8px 0;
}

.map-description {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 16px 0;
  line-height: 1.5;
}

.map-stats {
  display: flex;
  gap: 16px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 600;
}

.stat i {
  color: rgba(16, 185, 129, 0.6);
}

.map-actions {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.map-card:hover .map-actions {
  opacity: 1;
}

.btn-icon {
  width: 32px;
  height: 32px;
  background: rgba(0, 0, 0, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: rgba(16, 185, 129, 0.2);
  border-color: rgba(16, 185, 129, 0.5);
}

.btn-icon.btn-danger:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.5);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: #1e2139;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  width: 90%;
  max-width: 600px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  color: #fff;
}

.btn-close {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.6);
  font-size: 32px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.2s;
}

.btn-close:hover {
  color: #fff;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  font-weight: 600;
}

.form-group input[type="text"],
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
}

.form-group input[type="text"]:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: rgba(16, 185, 129, 0.5);
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
}

.form-group input[type="checkbox"] {
  margin-right: 8px;
}

.modal-footer {
  padding: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn {
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-primary {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #fff;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
}
</style>
