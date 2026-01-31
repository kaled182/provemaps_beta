<template>
  <div class="modal-overlay" @click="$emit('close')">
    <div class="modal-dialog" @click.stop>
      <header class="modal-header">
        <h3>Enviar mensagens em massa</h3>
        <button type="button" class="btn-close" @click="$emit('close')">&times;</button>
      </header>

      <div class="modal-body">
        <section class="section">
          <h4>Destinatários</h4>
          <p class="recipient-summary">
            <i class="fas fa-users"></i>
            <span>{{ contactSummary }}</span>
          </p>
          <div class="form-group">
            <label>Incluir contatos por grupo</label>
            <div class="checkbox-group">
              <label v-for="group in groups" :key="group.id" class="checkbox-label">
                <input v-model="selectedGroupIds" type="checkbox" :value="group.id" />
                {{ group.name }}
              </label>
            </div>
            <small v-if="groups.length === 0" class="form-hint text-muted">Nenhum grupo disponível.</small>
          </div>
        </section>

        <section class="section">
          <div class="form-group">
            <label for="bulk-gateway">Gateway WhatsApp <span class="required">*</span></label>
            <select id="bulk-gateway" v-model="gatewayId" class="form-control">
              <option value="">Selecione um gateway...</option>
              <option value="1">Gateway padrão</option>
            </select>
          </div>
        </section>

        <section class="section">
          <div class="form-group">
            <label for="bulk-message">Mensagem <span class="required">*</span></label>
            <textarea
              id="bulk-message"
              v-model="message"
              class="form-control"
              rows="6"
              placeholder="Digite a mensagem que será enviada"
            ></textarea>
            <small class="form-hint">{{ message.length }} caracteres</small>
          </div>
          <div class="variables-help">
            <p>Variáveis disponíveis:</p>
            <ul>
              <li><code>{name}</code> — Nome do contato</li>
              <li><code>{company}</code> — Empresa</li>
              <li><code>{position}</code> — Cargo</li>
            </ul>
          </div>
        </section>

        <section class="section">
          <label class="checkbox-label">
            <input v-model="enableSchedule" type="checkbox" />
            Agendar envio
          </label>
          <div v-if="enableSchedule" class="form-group schedule-group">
            <label for="bulk-schedule">Data e hora</label>
            <input id="bulk-schedule" v-model="scheduleAt" class="form-control" type="datetime-local" :min="minDateTime" />
          </div>
        </section>

        <section class="warning-box">
          <i class="fas fa-exclamation-triangle"></i>
          <div>
            <strong>Atenção</strong>
            <p>As mensagens serão enviadas para todos os contatos selecionados e grupos marcados. Verifique o conteúdo antes de confirmar.</p>
          </div>
        </section>
      </div>

      <footer class="modal-footer">
        <button type="button" class="btn btn-secondary" @click="$emit('close')">Cancelar</button>
        <button type="button" class="btn btn-primary" :disabled="!canSend" @click="handleSend">
          <i class="fas fa-paper-plane"></i>
          {{ enableSchedule ? 'Agendar envio' : 'Enviar agora' }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  selectedContactIds: {
    type: Array,
    default: () => [],
  },
  groups: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'send'])

const selectedGroupIds = ref([])
const gatewayId = ref('')
const message = ref('')
const enableSchedule = ref(false)
const scheduleAt = ref('')

const minDateTime = computed(() => {
  const date = new Date()
  date.setMinutes(date.getMinutes() + 5)
  return date.toISOString().slice(0, 16)
})

const contactSummary = computed(() => {
  const contactsCount = props.selectedContactIds.length
  const groupCount = selectedGroupIds.value.length
  const contactText = contactsCount === 1 ? '1 contato selecionado' : `${contactsCount} contatos selecionados`
  if (!groupCount) {
    return contactText
  }
  const groupText = groupCount === 1 ? '1 grupo adicional' : `${groupCount} grupos adicionais`
  return `${contactText} + ${groupText}`
})

const hasRecipients = computed(() => {
  return props.selectedContactIds.length > 0 || selectedGroupIds.value.length > 0
})

const canSend = computed(() => {
  if (!hasRecipients.value) {
    return false
  }
  if (!gatewayId.value) {
    return false
  }
  if (!message.value.trim()) {
    return false
  }
  if (enableSchedule.value && !scheduleAt.value) {
    return false
  }
  return true
})

watch(enableSchedule, (isEnabled) => {
  if (isEnabled && !scheduleAt.value) {
    scheduleAt.value = minDateTime.value
  }
})

const handleSend = () => {
  if (!canSend.value) {
    return
  }
  emit(
    'send',
    props.selectedContactIds,
    selectedGroupIds.value,
    message.value,
    gatewayId.value,
    enableSchedule.value ? scheduleAt.value : null,
  )
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
  background: var(--surface-card, #ffffff);
  border-radius: 12px;
  box-shadow: 0 26px 52px rgba(15, 23, 42, 0.32);
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
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section h4 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary, #0f172a);
}

.recipient-summary {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 10px;
  background: var(--accent-info-light, rgba(59, 130, 246, 0.1));
  color: var(--accent-info, #38bdf8);
  margin: 0;
  font-weight: 600;
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

.checkbox-group {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 10px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--border-secondary, #cbd5e1);
  background: var(--bg-secondary, #f8fafc);
  max-height: 140px;
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
}

.text-muted {
  color: var(--text-tertiary, #94a3b8);
}

.form-hint {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
}

.variables-help {
  padding: 14px 16px;
  border-radius: 8px;
  background: var(--bg-secondary, #f8fafc);
  border: 1px solid var(--border-secondary, #cbd5e1);
}

.variables-help p {
  margin: 0 0 8px;
  color: var(--text-primary, #0f172a);
}

.variables-help ul {
  margin: 0;
  padding-left: 20px;
  color: var(--text-secondary, #475569);
  line-height: 1.5;
}

.variables-help code {
  background: var(--surface-highlight, #e2e8f0);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.schedule-group {
  margin-top: 6px;
}

.warning-box {
  display: flex;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 10px;
  background: var(--warning-soft-bg, rgba(245, 158, 11, 0.12));
  border: 1px solid var(--warning-soft-text, rgba(245, 158, 11, 0.65));
  color: var(--warning-soft-text, #b45309);
}

.warning-box p {
  margin: 0;
  color: inherit;
  line-height: 1.5;
}

.modal-footer {
  padding: 16px 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
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

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-primary:not(:disabled):hover {
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

  .checkbox-group {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  }
}
</style>
