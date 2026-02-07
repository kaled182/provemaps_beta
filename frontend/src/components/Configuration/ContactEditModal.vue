<template>
  <div class="modal-overlay" @click="$emit('close')">
    <div class="modal-dialog" @click.stop>
      <header class="modal-header">
        <h3>{{ contact ? 'Editar Contato' : 'Novo Contato' }}</h3>
        <button type="button" class="btn-close" @click="$emit('close')">&times;</button>
      </header>

      <form class="modal-body" @submit.prevent="handleSubmit">
        <div class="form-row">
          <div class="form-group">
            <label for="contact-name">Nome <span class="required">*</span></label>
            <input
              id="contact-name"
              v-model="formData.name"
              class="form-control"
              type="text"
              placeholder="Nome completo"
              required
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="contact-phone">Telefone <span class="required">*</span></label>
            <input
              id="contact-phone"
              v-model="formData.phone"
              class="form-control"
              type="tel"
              placeholder="+5561999999999 ou 61999999999"
              :disabled="Boolean(contact?.id)"
              required
            />
            <small class="form-hint">
              {{ contact?.id ? 'Telefone não pode ser alterado' : 'Formato: +5561999999999 ou 61999999999' }}
            </small>
          </div>
          <div class="form-group">
            <label for="contact-email">Email</label>
            <input
              id="contact-email"
              v-model="formData.email"
              class="form-control"
              type="email"
              placeholder="email@exemplo.com"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="contact-company">Empresa</label>
            <input
              id="contact-company"
              v-model="formData.company"
              class="form-control"
              type="text"
              placeholder="Nome da empresa"
            />
          </div>
          <div class="form-group">
            <label for="contact-position">Cargo</label>
            <input
              id="contact-position"
              v-model="formData.position"
              class="form-control"
              type="text"
              placeholder="Cargo na empresa"
            />
          </div>
        </div>

        <div class="form-group">
          <label>Grupos</label>
          <div class="checkbox-group">
            <label v-for="group in groups" :key="group.id" class="checkbox-label">
              <input v-model="formData.groups" type="checkbox" :value="group.id" />
              <span>{{ group.name }}</span>
            </label>
          </div>
          <small v-if="groups.length === 0" class="form-hint text-muted">Nenhum grupo disponível.</small>
        </div>

        <div class="form-group">
          <label for="contact-notes">Observações</label>
          <textarea
            id="contact-notes"
            v-model="formData.notes"
            class="form-control"
            rows="3"
            placeholder="Informações adicionais"
          ></textarea>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input v-model="formData.is_active" type="checkbox" />
            Contato ativo
          </label>
        </div>

        <footer class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="$emit('close')">Cancelar</button>
          <button type="submit" class="btn btn-primary">
            <i class="fas fa-save"></i>
            {{ contact ? 'Atualizar' : 'Criar' }}
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  contact: {
    type: Object,
    default: null,
  },
  groups: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'save'])

const emptyForm = () => ({
  id: null,
  name: '',
  phone: '',
  email: '',
  company: '',
  position: '',
  groups: [],
  notes: '',
  is_active: true,
})

const formData = ref(emptyForm())

const initForm = () => {
  if (props.contact) {
    formData.value = {
      id: props.contact.id,
      name: props.contact.name || '',
      phone: props.contact.phone || '',
      email: props.contact.email || '',
      company: props.contact.company || '',
      position: props.contact.position || '',
      groups: props.contact.groups ? [...props.contact.groups] : [],
      notes: props.contact.notes || '',
      is_active: props.contact.is_active !== false,
    }
  } else {
    formData.value = emptyForm()
  }
}

watch(
  () => props.contact,
  () => {
    initForm()
  },
  { immediate: true }
)

const normalizePhone = (value) => {
  const digits = (value || '').replace(/\D/g, '')
  if (!digits) {
    return ''
  }
  let formatted = digits
  if (!value.startsWith('+') && digits.length === 11) {
    formatted = `55${formatted}`
  }
  if (!formatted.startsWith('+')) {
    formatted = `+${formatted}`
  }
  return formatted
}

const handleSubmit = () => {
  if (!formData.value.name.trim() || !formData.value.phone.trim()) {
    alert('Nome e telefone são obrigatórios.')
    return
  }

  const payload = {
    ...formData.value,
    phone: normalizePhone(formData.value.phone),
  }

  emit('save', payload)
}
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
  max-width: 720px;
  border-radius: 12px;
  background: var(--surface-card, #ffffff);
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.35);
  overflow: hidden;
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
  font-size: 20px;
  color: var(--text-primary, #0f172a);
}

.btn-close {
  background: none;
  border: none;
  font-size: 30px;
  color: var(--text-tertiary, #94a3b8);
  cursor: pointer;
  line-height: 1;
}

.btn-close:hover {
  color: var(--text-primary, #0f172a);
}

.modal-body {
  padding: 24px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.form-row + .form-row {
  margin-top: 18px;
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
  width: 100%;
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

.form-control:disabled {
  background: var(--bg-secondary, #f8fafc);
  cursor: not-allowed;
}

textarea.form-control {
  resize: vertical;
  min-height: 90px;
}

.form-hint {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
}

.text-muted {
  color: var(--text-tertiary, #94a3b8);
}

.checkbox-group {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--border-secondary, #cbd5e1);
  border-radius: 6px;
  background: var(--bg-secondary, #f8fafc);
  max-height: 160px;
  overflow-y: auto;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: var(--text-secondary, #475569);
}

.checkbox-label input[type='checkbox'] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid var(--border-secondary, #cbd5e1);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
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

@media (max-width: 768px) {
  .modal-dialog {
    max-width: 92vw;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>