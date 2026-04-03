<template>
  <div class="alert-templates-tab">
    <div class="tab-header">
      <div>
        <h3>Modelos de Aviso</h3>
        <p class="caption">Configure mensagens reutilizáveis para alertas automáticos.</p>
      </div>
      <button class="btn-primary" type="button" @click="openCreateModal">
        <i class="fas fa-plus"></i>
        Novo Modelo
      </button>
    </div>

    <div class="filters">
      <label>
        Categoria
        <select v-model="filters.category" @change="applyFilters">
          <option value="">Todas</option>
          <option v-for="option in categoryOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label>
        Canal
        <select v-model="filters.channel" @change="applyFilters">
          <option value="">Todos</option>
          <option v-for="option in channelOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>

      <label>
        Status
        <select v-model="filters.is_active" @change="applyFilters">
          <option value="">Todos</option>
          <option value="true">Ativos</option>
          <option value="false">Inativos</option>
        </select>
      </label>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="spinner"></span>
      <span>Carregando modelos...</span>
    </div>

    <div v-else>
      <div v-if="templates.length === 0" class="empty-state">
        <i class="fas fa-envelope-open-text"></i>
        <p>Nenhum modelo cadastrado.</p>
        <button class="btn-secondary" type="button" @click="openCreateModal">Criar primeiro modelo</button>
      </div>

      <div v-else class="templates-table">
        <div class="table-header">
          <span class="col-name">Nome</span>
          <span class="col-category">Categoria</span>
          <span class="col-channel">Canal</span>
          <span class="col-updated">Atualizado</span>
          <span class="col-status">Status</span>
          <span class="col-actions">Ações</span>
        </div>

        <div v-for="template in templates" :key="template.id" class="table-row">
          <div class="col-name">
            <h4>{{ template.name }}</h4>
            <p class="description" v-if="template.description">{{ template.description }}</p>
          </div>
          <div class="col-category">{{ formatCategory(template.category) }}</div>
          <div class="col-channel">{{ formatChannel(template.channel) }}</div>
          <div class="col-updated">{{ formatDate(template.updated_at) }}</div>
          <div class="col-status">
            <span :class="['status-pill', template.is_active ? 'active' : 'inactive']">
              {{ template.is_active ? 'Ativo' : 'Inativo' }}
            </span>
          </div>
          <div class="col-actions">
            <button class="btn-icon" type="button" @click="handleEdit(template)" title="Editar">
              <i class="fas fa-edit"></i>
            </button>
            <button
              class="btn-icon"
              type="button"
              :title="template.is_active ? 'Desativar' : 'Ativar'"
              @click="handleToggle(template)"
            >
              <i :class="template.is_active ? 'fas fa-toggle-on' : 'fas fa-toggle-off'"></i>
            </button>
            <button class="btn-icon danger" type="button" title="Excluir" @click="handleDelete(template)">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <AlertTemplateModal
      v-if="showModal"
      :template="editingTemplate"
      :channels="channelOptions"
      :categories="categoryOptions"
      :placeholder-catalog="placeholderCatalog"
      @close="closeModal"
      @save="handleSave"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useAlertTemplatesStore } from '@/stores/alertTemplates'
import AlertTemplateModal from './AlertTemplateModal.vue'

const props = defineProps({
  modalTrigger: {
    type: Number,
    default: 0,
  },
})

const alertTemplatesStore = useAlertTemplatesStore()
const { templates, loading, meta } = storeToRefs(alertTemplatesStore)
const { loadTemplates, saveTemplate, deleteTemplate, toggleActive } = alertTemplatesStore

const filters = ref({ category: '', channel: '', is_active: '' })
const showModal = ref(false)
const editingTemplate = ref(null)

const categoryOptions = computed(() =>
  (meta.value.categories || []).map(([value, label]) => ({ value, label }))
)
const channelOptions = computed(() =>
  (meta.value.channels || []).map(([value, label]) => ({ value, label }))
)
const placeholderCatalog = computed(() => meta.value.placeholders || {})

const defaultCategory = computed(() => {
  if (categoryOptions.value.length === 0) return 'optical_level'
  return categoryOptions.value.find(option => option.value === 'optical_level')?.value || categoryOptions.value[0].value
})

const applyFilters = () => {
  const payload = {
    category: filters.value.category || undefined,
    channel: filters.value.channel || undefined,
  }
  if (filters.value.is_active !== '') {
    payload.is_active = filters.value.is_active
  }
  loadTemplates(payload)
}

const openCreateModal = () => {
  editingTemplate.value = {
    category: defaultCategory.value,
    channel: channelOptions.value[0]?.value || 'whatsapp',
  }
  showModal.value = true
}

const handleEdit = (template) => {
  editingTemplate.value = { ...template }
  showModal.value = true
}

const handleDelete = async (template) => {
  if (!template?.id) return
  const confirmed = window.confirm(`Excluir o modelo "${template.name}"?`)
  if (!confirmed) return
  await deleteTemplate(template.id)
}

const handleToggle = async (template) => {
  if (!template?.id) return
  await toggleActive(template.id, !template.is_active)
}

const handleSave = async (data) => {
  const payload = {
    ...data,
    id: editingTemplate.value?.id,
  }
  const result = await saveTemplate(payload)
  if (result) {
    closeModal()
  }
}

const closeModal = () => {
  showModal.value = false
  editingTemplate.value = null
}

const formatCategory = (value) => {
  return categoryOptions.value.find(option => option.value === value)?.label || value
}

const formatChannel = (value) => {
  return channelOptions.value.find(option => option.value === value)?.label || value
}

const formatDate = (value) => {
  if (!value) return '—'
  try {
    const date = new Date(value)
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch (error) {
    return value
  }
}

onMounted(async () => {
  await loadTemplates()
})

watch(
  () => props.modalTrigger,
  (value, oldValue) => {
    if (value > 0 && value !== oldValue) {
      openCreateModal()
    }
  }
)
</script>

<style scoped>
.alert-templates-tab {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.tab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tab-header h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary, #0f172a);
  margin: 0;
}

.caption {
  margin: 4px 0 0;
  color: var(--text-secondary, #64748b);
  font-size: 13px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
  color: #fff;
  border: none;
  cursor: pointer;
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.25);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--border-secondary, #cbd5e1);
  background: var(--surface-card, #ffffff);
  color: var(--text-primary, #0f172a);
  cursor: pointer;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.filters label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary, #475569);
}

.filters select {
  min-width: 160px;
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid var(--border-secondary, #cbd5e1);
  background: var(--surface-card, #ffffff);
  color: var(--text-primary, #0f172a);
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary, #64748b);
}

.spinner {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--border-secondary, #cbd5e1);
  border-top-color: var(--accent-primary, #2563eb);
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  border: 1px dashed var(--border-secondary, #cbd5e1);
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  color: var(--text-secondary, #64748b);
  display: grid;
  gap: 12px;
  justify-items: center;
}

.empty-state i {
  font-size: 32px;
  color: var(--accent-primary, #2563eb);
}

.templates-table {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 1fr auto;
  gap: 12px;
  align-items: center;
}

.table-header {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-tertiary, #94a3b8);
  padding: 0 8px;
}

.table-row {
  background: var(--surface-card, #ffffff);
  border-radius: 10px;
  padding: 16px 18px;
  box-shadow: var(--shadow-sm, 0 8px 24px rgba(15, 23, 42, 0.06));
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.table-row:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.12);
}

.col-name h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #0f172a);
}

.col-name .description {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-secondary, #64748b);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.status-pill.active {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.status-pill.inactive {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.btn-icon {
  border: none;
  background: transparent;
  color: var(--text-secondary, #64748b);
  cursor: pointer;
  font-size: 16px;
  padding: 6px;
  border-radius: 6px;
  transition: background 0.2s ease, color 0.2s ease;
}

.btn-icon:hover {
  background: var(--surface-highlight, #e2e8f0);
  color: var(--text-primary, #0f172a);
}

.btn-icon.danger {
  color: #ef4444;
}

.btn-icon.danger:hover {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.col-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

@media (max-width: 1024px) {
  .table-header,
  .table-row {
    grid-template-columns: 2.2fr 1.2fr 1fr 1fr auto;
  }

  .col-status {
    display: none;
  }
}

@media (max-width: 768px) {
  .table-header,
  .table-row {
    grid-template-columns: 1.8fr 1.2fr 1fr auto;
  }

  .col-updated {
    display: none;
  }
}
</style>
