<template>
  <BaseModal
    :show="true"
    :title="contact ? 'Editar contato' : 'Novo contato'"
    :icon="PhAddressBook"
    :dirty="dirty"
    size="md"
    flush
    @close="$emit('close')"
  >
    <form id="contact-edit-form" class="modal-body" @submit.prevent="handleSubmit">
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
      <p v-if="formError" class="form-error" role="alert" data-testid="contact-form-error">{{ formError }}</p>
    </form>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <button type="button" class="btn btn-secondary" @click="$emit('close')">Cancelar</button>
        <button type="submit" form="contact-edit-form" class="btn btn-primary">
          <i class="fas fa-save"></i>
          {{ contact ? 'Atualizar' : 'Criar' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { PhAddressBook } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'

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
// EV-0068c: aviso ao fechar com alterações; validação no próprio modal (sem alert).
const initial = ref('')
const dirty = computed(() => JSON.stringify(formData.value) !== initial.value)
const formError = ref('')

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
  initial.value = JSON.stringify(formData.value)
  formError.value = ''
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
    formError.value = 'Nome e telefone são obrigatórios.'
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
  color: var(--text-primary, rgb(var(--n-950)));
}

.form-error {
  margin-top: 8px;
  padding: 6px 10px;
  border: 1px solid rgb(var(--danger) / 0.4);
  border-radius: 6px;
  background: rgb(var(--danger) / 0.1);
  color: rgb(var(--danger));
  font-size: 13px;
}

.required {
  color: var(--accent-danger, rgb(var(--danger)));
}

.form-control {
  width: 100%;
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-secondary, rgb(var(--n-300)));
  background: var(--surface-card, #ffffff);
  color: var(--text-primary, rgb(var(--n-950)));
  font-size: 14px;
}

.form-control:focus {
  outline: none;
  border-color: var(--accent-primary, rgb(var(--info)));
  box-shadow: 0 0 0 3px rgb(var(--info) / 0.15);
}

.form-control:disabled {
  background: var(--bg-secondary, rgb(var(--n-50)));
  cursor: not-allowed;
}

textarea.form-control {
  resize: vertical;
  min-height: 90px;
}

.form-hint {
  font-size: 12px;
  color: var(--text-tertiary, rgb(var(--n-400)));
}

.text-muted {
  color: var(--text-tertiary, rgb(var(--n-400)));
}

.checkbox-group {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--border-secondary, rgb(var(--n-300)));
  border-radius: 6px;
  background: var(--bg-secondary, rgb(var(--n-50)));
  max-height: 160px;
  overflow-y: auto;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: var(--text-secondary, rgb(var(--n-600)));
}

.checkbox-label input[type='checkbox'] {
  width: 16px;
  height: 16px;
  cursor: pointer;
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
  background: var(--accent-primary, rgb(var(--info)));
  color: #fff;
}

.btn-primary:hover {
  background: var(--accent-primary-dark, rgb(var(--info-strong)));
}

.btn-secondary {
  background: var(--bg-secondary, rgb(var(--n-50)));
  color: var(--text-primary, rgb(var(--n-950)));
  border: 1px solid var(--border-secondary, rgb(var(--n-300)));
}

.btn-secondary:hover {
  background: var(--surface-highlight, rgb(var(--n-100)));
}

@media (max-width: 768px) {

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>