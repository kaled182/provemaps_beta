<template>
  <div class="modal-overlay" @click="$emit('close')">
    <div class="modal-dialog" @click.stop>
      <header class="modal-header">
        <h3>Gerenciar Grupos de Contatos</h3>
        <button type="button" class="btn-close" @click="$emit('close')">&times;</button>
      </header>

      <div class="modal-body">
        <section class="group-form">
          <h4>{{ editingGroupId ? 'Editar Grupo' : 'Novo Grupo' }}</h4>
          <form class="form" @submit.prevent="handleSubmit">
            <div class="form-group">
              <label for="group-name">Nome <span class="required">*</span></label>
              <input
                id="group-name"
                v-model="form.name"
                class="form-control"
                type="text"
                placeholder="Nome do grupo"
                required
              />
            </div>
            <div class="form-group">
              <label for="group-description">Descrição</label>
              <textarea
                id="group-description"
                v-model="form.description"
                class="form-control"
                rows="2"
                placeholder="Descrição opcional"
              ></textarea>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" @click="resetForm" :disabled="saving">
                Cancelar
              </button>
              <button type="submit" class="btn btn-primary" :disabled="saving">
                <i v-if="!saving" class="fas fa-save"></i>
                <i v-else class="fas fa-spinner fa-spin"></i>
                {{ editingGroupId ? 'Atualizar' : 'Criar' }}
              </button>
            </div>
          </form>
        </section>

        <section class="group-list">
          <h4>Grupos existentes</h4>
          <div v-if="sortedGroups.length === 0" class="empty-list">
            <i class="fas fa-layer-group"></i>
            <p>Nenhum grupo cadastrado ainda.</p>
          </div>
          <ul v-else class="groups">
            <li v-for="group in sortedGroups" :key="group.id" class="group-card">
              <div>
                <h5>{{ group.name }}</h5>
                <p v-if="group.description">{{ group.description }}</p>
                <small v-else class="text-muted">Sem descrição</small>
              </div>
              <div class="group-footer">
                <span class="badge">{{ group.contact_count ?? 0 }} contatos</span>
                <div class="card-actions">
                  <button type="button" class="btn-icon" @click="startEdit(group)">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button
                    type="button"
                    class="btn-icon btn-danger"
                    :disabled="deletingId === group.id"
                    @click="handleDelete(group)"
                  >
                    <i v-if="deletingId === group.id" class="fas fa-spinner fa-spin"></i>
                    <i v-else class="fas fa-trash"></i>
                  </button>
                </div>
              </div>
            </li>
          </ul>
        </section>
      </div>

      <footer class="modal-footer">
        <button type="button" class="btn btn-secondary" @click="$emit('close')">Fechar</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useContactsStore } from '@/stores/contacts'

const props = defineProps({
  groups: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'refresh'])

const contactsStore = useContactsStore()
const { saveGroup, deleteGroup } = contactsStore

const editingGroupId = ref(null)
const saving = ref(false)
const deletingId = ref(null)

const form = reactive({
  name: '',
  description: '',
})

const sortedGroups = computed(() => {
  return [...props.groups].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR', { sensitivity: 'base' }))
})

const resetForm = () => {
  editingGroupId.value = null
  form.name = ''
  form.description = ''
}

const startEdit = (group) => {
  editingGroupId.value = group.id
  form.name = group.name || ''
  form.description = group.description || ''
}

const handleSubmit = async () => {
  if (!form.name.trim()) {
    alert('Informe o nome do grupo.')
    return
  }

  saving.value = true
  try {
    const payload = {
      id: editingGroupId.value || undefined,
      name: form.name.trim(),
      description: form.description.trim(),
    }

    const success = await saveGroup(payload)
    if (success) {
      emit('refresh')
      resetForm()
    }
  } finally {
    saving.value = false
  }
}

const handleDelete = async (group) => {
  if (!confirm(`Excluir o grupo "${group.name}"?`)) {
    return
  }
  deletingId.value = group.id
  try {
    const success = await deleteGroup(group.id)
    if (success) {
      emit('refresh')
      if (editingGroupId.value === group.id) {
        resetForm()
      }
    }
  } finally {
    deletingId.value = null
  }
}

const startCreate = () => {
  resetForm()
}

startCreate()
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.modal-dialog {
  width: 100%;
  max-width: 760px;
  background: var(--surface-card, #ffffff);
  border-radius: 12px;
  box-shadow: 0 28px 52px rgba(15, 23, 42, 0.35);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header,
.modal-footer {
  background: var(--bg-secondary, #f8fafc);
  border-color: var(--border-secondary, #cbd5e1);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-secondary, #cbd5e1);
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary, #0f172a);
}

.btn-close {
  background: none;
  border: none;
  font-size: 28px;
  color: var(--text-tertiary, #94a3b8);
  cursor: pointer;
  line-height: 1;
}

.btn-close:hover {
  color: var(--text-primary, #0f172a);
}

.modal-body {
  padding: 24px;
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: 24px;
}

.group-form {
  padding: 18px;
  border-radius: 12px;
  border: 1px solid var(--border-secondary, #cbd5e1);
  background: var(--bg-secondary, #f8fafc);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.group-form h4,
.group-list h4 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary, #0f172a);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-weight: 500;
  color: var(--text-primary, #0f172a);
}

.required {
  color: var(--accent-danger, #dc2626);
}

.form-control {
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-secondary, #cbd5e1);
  background: var(--surface-card, #ffffff);
  color: var(--text-primary, #0f172a);
  font-size: 14px;
}

.form-control:focus {
  outline: none;
  border-color: var(--accent-primary, #2563eb);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

textarea.form-control {
  resize: vertical;
  min-height: 70px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-list {
  border: 1px dashed var(--border-secondary, #cbd5e1);
  border-radius: 12px;
  padding: 32px 18px;
  text-align: center;
  color: var(--text-tertiary, #94a3b8);
}

.empty-list i {
  font-size: 28px;
  margin-bottom: 8px;
}

.groups {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 14px;
}

.group-card {
  border: 1px solid var(--border-secondary, #cbd5e1);
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  justify-content: space-between;
  gap: 24px;
  background: var(--surface-card, #ffffff);
  box-shadow: var(--shadow-xs, 0 6px 18px rgba(15, 23, 42, 0.08));
}

.group-card h5 {
  margin: 0 0 6px;
  font-size: 15px;
  color: var(--text-primary, #0f172a);
}

.group-card p {
  margin: 0;
  color: var(--text-secondary, #475569);
  line-height: 1.5;
}

.text-muted {
  color: var(--text-tertiary, #94a3b8);
}

.group-footer {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  background: var(--surface-highlight, #e2e8f0);
  color: var(--text-secondary, #475569);
}

.card-actions {
  display: flex;
  gap: 8px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.btn-primary {
  background: var(--accent-primary, #2563eb);
  color: #fff;
}

.btn-primary:hover {
  background: var(--accent-primary-dark, #1e40af);
}

.btn-secondary {
  background: var(--bg-secondary, #f8fafc);
  color: var(--text-primary, #0f172a);
  border: 1px solid var(--border-secondary, #cbd5e1);
}

.btn-secondary:hover {
  background: var(--surface-highlight, #f1f5f9);
}

.btn-icon {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--border-secondary, #cbd5e1);
  background: transparent;
  color: var(--text-secondary, #475569);
  cursor: pointer;
}

.btn-icon:hover {
  background: var(--surface-highlight, #f1f5f9);
  color: var(--text-primary, #0f172a);
}

.btn-danger {
  border-color: rgba(220, 38, 38, 0.35);
  color: var(--accent-danger, #dc2626);
}

.btn-danger:hover {
  background: rgba(220, 38, 38, 0.1);
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--border-secondary, #cbd5e1);
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .modal-body {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .modal-dialog {
    max-width: 92vw;
  }
}
</style>