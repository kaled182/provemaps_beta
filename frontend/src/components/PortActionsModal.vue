<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="actions-modal-overlay" @click.self="close">
        <div class="actions-modal-container" :class="{ dark: isDark }">
          <!-- Header -->
          <div class="actions-modal-header">
            <h3>
              <i class="fas fa-cog"></i>
              Ações - {{ port?.name }}
            </h3>
            <button class="close-button" @click="close">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <!-- Content -->
          <div class="actions-modal-content">
            <!-- Edit Description -->
            <div class="action-section">
              <h4><i class="fas fa-tag"></i> Editar Descrição</h4>
              <div class="form-field">
                <textarea
                  v-model="editedDescription"
                  class="form-textarea"
                  placeholder="Digite a descrição da porta..."
                  rows="3"
                ></textarea>
              </div>
              <button class="btn-primary" @click="saveDescription" :disabled="saving">
                <i class="fas fa-save"></i>
                {{ saving ? 'Salvando...' : 'Salvar Descrição' }}
              </button>
            </div>

            <!-- Reset Port -->
            <div class="action-section">
              <h4><i class="fas fa-redo"></i> Resetar Porta</h4>
              <p class="action-description">
                Reinicia a porta para resolver problemas de conectividade.
              </p>
              <button class="btn-warning" @click="resetPort" :disabled="resetting">
                <i class="fas fa-power-off"></i>
                {{ resetting ? 'Resetando...' : 'Resetar Porta' }}
              </button>
            </div>

            <!-- View Logs -->
            <div class="action-section">
              <h4><i class="fas fa-history"></i> Logs de Eventos</h4>
              <div v-if="loadingLogs" class="loading-logs">
                <i class="fas fa-spinner fa-spin"></i>
                Carregando logs...
              </div>
              <div v-else-if="logs.length === 0" class="empty-logs">
                Nenhum evento registrado
              </div>
              <div v-else class="logs-container">
                <div v-for="(log, index) in logs" :key="index" class="log-entry">
                  <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                  <span class="log-message" :class="log.level">{{ log.message }}</span>
                </div>
              </div>
              <button class="btn-secondary" @click="loadLogs">
                <i class="fas fa-sync"></i>
                Atualizar Logs
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'
import { useUiStore } from '@/stores/ui'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  port: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'refresh'])

const { patch, get } = useApi()
const { success, error: notifyError } = useNotification()
const uiStore = useUiStore()

const editedDescription = ref('')
const saving = ref(false)
const resetting = ref(false)
const logs = ref([])
const loadingLogs = ref(false)

const isDark = computed(() => uiStore.theme === 'dark')

const close = () => {
  emit('close')
}

const saveDescription = async () => {
  if (!props.port?.id) return
  
  saving.value = true
  try {
    await patch(`/api/v1/ports/${props.port.id}/`, {
      description: editedDescription.value
    })
    success('Descrição salva', 'A descrição da porta foi atualizada.')
    emit('refresh')
    close()
  } catch (error) {
    console.error('[PortActionsModal] Error saving description:', error)
    notifyError('Erro', 'Não foi possível salvar a descrição.')
  } finally {
    saving.value = false
  }
}

const resetPort = async () => {
  if (!props.port?.id) return
  if (!confirm(`Deseja realmente resetar a porta ${props.port.name}?`)) return
  
  resetting.value = true
  try {
    // TODO: Implement reset endpoint
    await patch(`/api/v1/ports/${props.port.id}/reset/`, {})
    success('Porta resetada', 'A porta foi reiniciada com sucesso.')
    emit('refresh')
  } catch (error) {
    console.error('[PortActionsModal] Error resetting port:', error)
    notifyError('Erro', 'Não foi possível resetar a porta.')
  } finally {
    resetting.value = false
  }
}

const loadLogs = async () => {
  if (!props.port?.id) return
  
  loadingLogs.value = true
  try {
    // TODO: Implement logs endpoint
    const response = await get(`/api/v1/ports/${props.port.id}/logs/`)
    logs.value = response.logs || []
  } catch (error) {
    console.error('[PortActionsModal] Error loading logs:', error)
    logs.value = [
      { timestamp: new Date().toISOString(), level: 'info', message: 'Sistema de logs em desenvolvimento' }
    ]
  } finally {
    loadingLogs.value = false
  }
}

const formatLogTime = (timestamp) => {
  return new Date(timestamp).toLocaleString('pt-BR')
}

watch(() => props.isOpen, (newVal) => {
  if (newVal && props.port) {
    editedDescription.value = props.port.description || ''
    loadLogs()
  }
})
</script>

<style scoped>
.actions-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 12000;
  padding: 20px;
}

.actions-modal-container {
  background: #ffffff;
  border-radius: 12px;
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.actions-modal-container.dark {
  background: #1e293b;
  color: #f1f5f9;
}

.actions-modal-header {
  padding: 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.actions-modal-container.dark .actions-modal-header {
  border-bottom-color: #334155;
}

.actions-modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #1e293b;
}

.actions-modal-container.dark .actions-modal-header h3 {
  color: #f1f5f9;
}

.actions-modal-header h3 i {
  color: #667eea;
}

.close-button {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f1f5f9;
  border: none;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.actions-modal-container.dark .close-button {
  background: #334155;
  color: #cbd5e1;
}

.close-button:hover {
  background: #e2e8f0;
  transform: scale(1.1);
}

.actions-modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.action-section {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #e2e8f0;
}

.actions-modal-container.dark .action-section {
  border-bottom-color: #334155;
}

.action-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.action-section h4 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1e293b;
}

.actions-modal-container.dark .action-section h4 {
  color: #f1f5f9;
}

.action-section h4 i {
  color: #667eea;
}

.action-description {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 12px 0;
}

.form-field {
  margin-bottom: 12px;
}

.form-textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  color: #1e293b;
  background: white;
  resize: vertical;
}

.actions-modal-container.dark .form-textarea {
  background: #0f172a;
  border-color: #334155;
  color: #f1f5f9;
}

.form-textarea:focus {
  outline: none;
  border-color: #667eea;
}

.btn-primary,
.btn-warning,
.btn-secondary {
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
}

.btn-warning {
  background: #f59e0b;
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #d97706;
}

.btn-secondary {
  background: #f1f5f9;
  color: #475569;
}

.actions-modal-container.dark .btn-secondary {
  background: #334155;
  color: #cbd5e1;
}

.btn-secondary:hover {
  background: #e2e8f0;
}

.btn-primary:disabled,
.btn-warning:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-logs,
.empty-logs {
  padding: 20px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.logs-container {
  max-height: 200px;
  overflow-y: auto;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.actions-modal-container.dark .logs-container {
  background: #0f172a;
}

.log-entry {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #e2e8f0;
  font-size: 12px;
}

.actions-modal-container.dark .log-entry {
  border-bottom-color: #334155;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-time {
  color: #64748b;
  font-family: 'Monaco', 'Courier New', monospace;
  white-space: nowrap;
}

.log-message {
  flex: 1;
  color: #1e293b;
}

.actions-modal-container.dark .log-message {
  color: #f1f5f9;
}

.log-message.error {
  color: #ef4444;
}

.log-message.warning {
  color: #f59e0b;
}

.log-message.info {
  color: #3b82f6;
}
</style>
