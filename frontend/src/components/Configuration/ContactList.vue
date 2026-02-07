<template>
  <div class="contact-list">
    <div v-if="loading" class="state state-loading">
      <div class="spinner"></div>
      <p>Carregando contatos...</p>
    </div>

    <div v-else-if="contacts.length === 0" class="state state-empty">
      <i class="fas fa-address-book empty-icon"></i>
      <h3>Nenhum contato encontrado</h3>
      <p>Adicione um novo contato ou importe de um arquivo CSV/Excel.</p>
    </div>

    <div v-else class="table-wrapper">
      <table class="contacts-table">
        <thead>
          <tr>
            <th class="col-checkbox">
              <input
                type="checkbox"
                :checked="isAllSelected"
                @change="handleSelectAll"
              />
            </th>
            <th>Nome</th>
            <th>Telefone</th>
            <th>Email</th>
            <th>Empresa</th>
            <th>Grupos</th>
            <th>Mensagens</th>
            <th>Status</th>
            <th class="col-actions">Ações</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="contact in contacts"
            :key="contact.id"
            :class="{
              selected: isSelected(contact.id),
              inactive: contact.is_active === false,
            }"
          >
            <td class="col-checkbox">
              <input
                type="checkbox"
                :checked="isSelected(contact.id)"
                @change="$emit('toggleSelection', contact.id)"
              />
            </td>
            <td class="cell-name">
              <i class="fas fa-user"></i>
              <span>{{ contact.name }}</span>
            </td>
            <td>
              <a
                v-if="contact.phone"
                :href="whatsAppLink(contact)"
                class="phone-link"
                target="_blank"
                rel="noopener"
              >
                {{ contact.phone }}
              </a>
              <span v-else>-</span>
            </td>
            <td>{{ contact.email || '-' }}</td>
            <td>{{ contact.company || '-' }}</td>
            <td>
              <div class="group-tags">
                <span v-if="!hasGroups(contact)" class="tag-muted">Sem grupo</span>
                <span v-for="groupName in contact.group_names || []" :key="groupName" class="tag">
                  {{ groupName }}
                </span>
              </div>
            </td>
            <td class="cell-messages">
              <div class="message-count">
                <i class="fas fa-paper-plane"></i>
                <span>{{ contact.message_count || 0 }}</span>
              </div>
              <small v-if="contact.last_message_sent" class="last-message">
                {{ formatDate(contact.last_message_sent) }}
              </small>
            </td>
            <td>
              <span
                class="status-badge"
                :class="contact.is_active ? 'status-active' : 'status-inactive'"
              >
                {{ contact.is_active ? 'Ativo' : 'Inativo' }}
              </span>
            </td>
            <td class="col-actions">
              <div class="actions">
                <button
                  type="button"
                  class="btn-action btn-send"
                  :disabled="contact.is_active === false"
                  title="Enviar mensagem"
                  @click="handleSendMessage(contact)"
                >
                  <i class="fas fa-paper-plane"></i>
                </button>
                <button
                  type="button"
                  class="btn-action btn-edit"
                  title="Editar"
                  @click="$emit('edit', contact)"
                >
                  <i class="fas fa-edit"></i>
                </button>
                <button
                  type="button"
                  class="btn-action btn-delete"
                  title="Excluir"
                  @click="$emit('delete', contact.id)"
                >
                  <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showSendMessageDialog" class="modal-overlay" @click="closeSendMessage">
      <div class="modal-dialog" @click.stop>
        <header class="modal-header">
          <h3>Enviar mensagem para {{ selectedContactForMessage?.name }}</h3>
          <button type="button" class="btn-close" @click="closeSendMessage">&times;</button>
        </header>
        <div class="modal-body">
          <div class="form-group">
            <label>Canal</label>
            <div class="channel-options">
              <button
                v-for="channel in messageChannels"
                :key="channel.value"
                type="button"
                class="channel-option"
                :class="{ active: messageChannel === channel.value }"
                @click="messageChannel = channel.value"
              >
                <i :class="channel.icon"></i>
                <span>{{ channel.label }}</span>
              </button>
            </div>
          </div>
          <div class="form-group">
            <label for="message-gateway">Gateway {{ currentChannelLabel }}</label>
            <select
              id="message-gateway"
              v-model="messageGatewayId"
              class="form-control"
              :disabled="gatewaysLoading || availableGateways.length === 0"
            >
              <option value="">Selecione um gateway...</option>
              <option
                v-for="gateway in availableGateways"
                :key="gateway.id"
                :value="String(gateway.id)"
              >
                {{ gateway.name || ('Gateway ' + gateway.id) }}
              </option>
            </select>
            <p v-if="gatewaysLoading" class="form-helper">Carregando gateways...</p>
            <p v-else-if="availableGateways.length === 0" class="form-helper">
              Nenhum gateway {{ currentChannelLabel }} configurado.
            </p>
          </div>
          <div class="form-group">
            <label for="message-text">Mensagem</label>
            <textarea
              id="message-text"
              v-model="messageText"
              class="form-control"
              rows="4"
              placeholder="Digite sua mensagem"
            ></textarea>
          </div>
        </div>
        <footer class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="closeSendMessage">Cancelar</button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="isSendDisabled"
            @click="confirmSendMessage"
          >
            <i :class="currentChannelIcon"></i>
            Enviar
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useGatewayConfig } from '@/composables/useGatewayConfig'

const props = defineProps({
  contacts: {
    type: Array,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  selectedContacts: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['edit', 'delete', 'sendMessage', 'toggleSelection', 'selectAll'])

const showSendMessageDialog = ref(false)
const selectedContactForMessage = ref(null)
const messageText = ref('')
const messageGatewayId = ref('')
const messageChannel = ref('whatsapp')

const messageChannels = [
  { value: 'sms', label: 'SMS', icon: 'fas fa-comment-dots' },
  { value: 'whatsapp', label: 'WhatsApp', icon: 'fab fa-whatsapp' },
  { value: 'smtp', label: 'E-mail', icon: 'fas fa-envelope' },
  { value: 'telegram', label: 'Telegram', icon: 'fab fa-telegram-plane' },
]

const channelLabelMap = {
  sms: 'SMS',
  whatsapp: 'WhatsApp',
  smtp: 'E-mail',
  telegram: 'Telegram',
}

const channelIconMap = {
  sms: 'fas fa-comment-dots',
  whatsapp: 'fab fa-whatsapp',
  smtp: 'fas fa-envelope',
  telegram: 'fab fa-telegram-plane',
}

const { loadGateways, gateways, loading: gatewaysLoading } = useGatewayConfig()

const availableGateways = computed(() =>
  gateways.value.filter(
    (gateway) => gateway.gateway_type === messageChannel.value && gateway.enabled !== false,
  ),
)

const currentChannelLabel = computed(() => channelLabelMap[messageChannel.value] || 'Canal')
const currentChannelIcon = computed(() => channelIconMap[messageChannel.value] || 'fas fa-paper-plane')

const isSendDisabled = computed(() => {
  if (!messageText.value.trim()) {
    return true
  }
  if (!messageGatewayId.value) {
    return true
  }
  return availableGateways.value.length === 0
})

onMounted(async () => {
  await loadGateways()
})

const ensureGatewaySelection = () => {
  const options = availableGateways.value
  if (!Array.isArray(options) || options.length === 0) {
    messageGatewayId.value = ''
    return
  }
  const hasCurrent = options.some(
    (gateway) => String(gateway.id) === String(messageGatewayId.value),
  )
  if (!hasCurrent) {
    messageGatewayId.value = String(options[0].id)
  }
}

watch(
  () => [messageChannel.value, availableGateways.value],
  ensureGatewaySelection,
  { immediate: true },
)

const isAllSelected = computed(() => {
  if (!props.contacts.length) {
    return false
  }
  return props.contacts.every((contact) => props.selectedContacts.includes(contact.id))
})

const isSelected = (contactId) => props.selectedContacts.includes(contactId)

const hasGroups = (contact) => Array.isArray(contact.group_names) && contact.group_names.length > 0

const handleSelectAll = () => {
  emit('selectAll')
}

const whatsAppLink = (contact) => {
  const number = contact.formatted_phone || contact.phone || ''
  const digits = number.replace(/\D/g, '')
  return `https://wa.me/${digits}`
}

const handleSendMessage = (contact) => {
  selectedContactForMessage.value = contact
  messageText.value = ''
  messageGatewayId.value = ''
  messageChannel.value = 'whatsapp'
  showSendMessageDialog.value = true
  ensureGatewaySelection()
}

const closeSendMessage = () => {
  showSendMessageDialog.value = false
  selectedContactForMessage.value = null
  messageText.value = ''
  messageGatewayId.value = ''
  messageChannel.value = 'whatsapp'
}

const confirmSendMessage = () => {
  const contact = selectedContactForMessage.value
  const trimmedMessage = messageText.value.trim()
  const gatewayId = Number(messageGatewayId.value)

  if (!contact || !trimmedMessage || !messageGatewayId.value || Number.isNaN(gatewayId)) {
    return
  }

  emit('sendMessage', contact.id, trimmedMessage, gatewayId, messageChannel.value)
  closeSendMessage()
}

const formatDate = (value) => {
  if (!value) {
    return '-'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return '-'
  }
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.contact-list {
  background: var(--surface-card, #ffffff);
  border-radius: 12px;
  box-shadow: var(--shadow-sm, 0 8px 24px rgba(15, 23, 42, 0.06));
  overflow: hidden;
}

.table-wrapper {
  overflow-x: hidden;
  padding: 0 16px 16px;
  box-sizing: border-box;
}

.contacts-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  min-width: 760px;
  font-size: 14px;
}

.contacts-table thead {
  background: var(--surface-card, #ffffff);
  color: var(--text-secondary, #475569);
  border-bottom: 1px solid var(--border-secondary, #cbd5e1);
  text-transform: uppercase;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.contacts-table th,
.contacts-table td {
  padding: 12px 14px;
  text-align: left;
  border-bottom: 1px solid var(--border-secondary, #cbd5e1);
}

.contacts-table thead tr th:first-child {
  border-top-left-radius: 12px;
}

.contacts-table thead tr th:last-child {
  border-top-right-radius: 12px;
}

.contacts-table th:first-child,
.contacts-table td:first-child {
  padding-left: 20px;
}

.contacts-table th:last-child,
.contacts-table td:last-child {
  padding-right: 20px;
}

.contacts-table tbody tr {
  background: var(--surface-card, #ffffff);
  transition: background-color 0.2s ease;
}

.contacts-table tbody tr:hover {
  background: var(--surface-highlight, #f1f5f9);
}

.contacts-table tbody tr.selected {
  background: var(--accent-info-light, rgba(59, 130, 246, 0.08));
}

.contacts-table tbody tr.inactive {
  opacity: 0.65;
}

.col-checkbox {
  width: 56px;
  text-align: center;
}

.col-checkbox input[type='checkbox'] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.cell-name {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 500;
  color: var(--text-primary, #0f172a);
}

.cell-name i {
  color: var(--accent-info, #38bdf8);
}

.group-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: var(--accent-primary, #2563eb);
  color: #fff;
}

.tag-muted {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
  font-style: italic;
}

.cell-messages {
  text-align: center;
  color: var(--text-secondary, #475569);
}

.message-count {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--accent-primary, #2563eb);
}

.last-message {
  display: block;
  margin-top: 4px;
  color: var(--text-tertiary, #94a3b8);
  font-size: 12px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.status-active {
  background: var(--status-online-light, rgba(22, 163, 74, 0.12));
  color: var(--status-online, #16a34a);
}

.status-inactive {
  background: var(--status-offline-light, rgba(148, 163, 184, 0.16));
  color: var(--status-offline, #64748b);
}

.col-actions {
  width: 160px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-action {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.btn-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-action:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
}

.btn-send {
  background: var(--status-online, #16a34a);
  color: #fff;
}

.btn-edit {
  background: var(--accent-primary, #2563eb);
  color: #fff;
}

.btn-delete {
  background: var(--accent-danger, #dc2626);
  color: #fff;
}

.phone-link {
  color: var(--accent-primary, #2563eb);
  text-decoration: none;
}

.phone-link:hover {
  text-decoration: underline;
}

.state {
  padding: 60px 20px;
  text-align: center;
  color: var(--text-tertiary, #94a3b8);
}

.state h3 {
  margin: 12px 0 6px;
  color: var(--text-primary, #0f172a);
}

.state-empty p {
  margin: 0;
}

.empty-icon {
  font-size: 56px;
  color: var(--text-tertiary, #94a3b8);
}

.spinner {
  width: 44px;
  height: 44px;
  margin: 0 auto;
  border-radius: 50%;
  border: 3px solid var(--border-secondary, #cbd5e1);
  border-top-color: var(--accent-primary, #2563eb);
  animation: spin 1s linear infinite;
}

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
  max-width: 520px;
  border-radius: 12px;
  background: var(--surface-card, #ffffff);
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.25);
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
  padding: 18px 22px;
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
  padding: 22px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 22px;
  border-top: 1px solid var(--border-secondary, #cbd5e1);
}

.form-group {
  margin-bottom: 18px;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: var(--text-primary, #0f172a);
}

.form-helper {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
}

.channel-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.channel-option {
  flex: 1 1 100px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid var(--border-secondary, #cbd5e1);
  background: var(--surface-card, #ffffff);
  color: var(--text-secondary, #475569);
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.channel-option i {
  font-size: 14px;
}

.channel-option:hover {
  border-color: var(--accent-primary, #2563eb);
  color: var(--accent-primary, #2563eb);
}

.channel-option.active {
  background: var(--accent-primary, #2563eb);
  border-color: var(--accent-primary, #2563eb);
  color: #fff;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.25);
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

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
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

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1024px) {
  .table-wrapper {
    overflow-x: auto;
    padding: 0 12px 12px;
  }

  .contacts-table {
    min-width: 680px;
  }
}

@media (max-width: 768px) {
  .contact-list {
    border-radius: 8px;
  }

  .contacts-table {
    min-width: 600px;
  }
}
</style>