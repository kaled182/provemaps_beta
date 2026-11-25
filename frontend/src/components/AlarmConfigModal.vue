<template>
  <BaseModal
    :show="isOpen"
    :title="`Alarme de sinal óptico · ${port?.name || ''}`"
    :icon="PhBell"
    :dirty="dirty"
    :z-index="3600"
    size="md"
    @close="close"
  >
    <!-- Content -->
    <div class="alarm-modal-content">
      <!-- Current Signal -->
      <div class="current-signal">
        <h4>Sinal Atual</h4>
        <div class="signal-display">
          <div class="signal-item">
            <span class="label">RX:</span>
            <span class="value" :class="getSignalClass(port?.optical_rx_power)">
              {{ formatPower(port?.optical_rx_power) }} dBm
            </span>
          </div>
          <div class="signal-item">
            <span class="label">TX:</span>
            <span class="value" :class="getSignalClass(port?.optical_tx_power)">
              {{ formatPower(port?.optical_tx_power) }} dBm
            </span>
          </div>
        </div>
      </div>

      <!-- Signal History Chart -->
      <div class="signal-history">
        <h4>Histórico do Sinal (últimas 24h)</h4>
        <div class="chart-container">
          <TimeSeriesChart :series="historySeries" :thresholds="thresholdLines" unit="dBm" :decimals="2" :height="200" :empty-message="historyEmptyMessage" />
        </div>
      </div>

      <!-- Alarm Configuration -->
      <div class="alarm-config">
        <h4>Configuração de Alarme</h4>
        
        <!-- Info sobre configuração global -->
        <div v-if="!alarmEnabled" class="config-info">
          <i class="fas fa-info-circle"></i>
          <span>Valores padrão globais: {{ globalWarningThreshold }} dBm (Atenção) / {{ globalCriticalThreshold }} dBm (Crítico)</span>
        </div>
        
        <div class="form-field">
          <label>
            <input type="checkbox" v-model="alarmEnabled" />
            Habilitar Alarme Personalizado
          </label>
          <p v-if="!alarmEnabled" class="field-help">Quando desabilitado, usa configuração global do sistema</p>
        </div>

        <div v-if="alarmEnabled" class="threshold-config">
          <div class="form-field">
            <label>Threshold de Atenção (dBm)</label>
            <input 
              v-model.number="warningThreshold" 
              type="number" 
              step="0.5" 
              class="form-input"
              placeholder="-24"
            />
            <p class="field-help">Alerta quando sinal ficar abaixo deste valor</p>
          </div>

          <div class="form-field">
            <label>Threshold Crítico (dBm)</label>
            <input 
              v-model.number="criticalThreshold" 
              type="number" 
              step="0.5" 
              class="form-input"
              placeholder="-27"
            />
            <p class="field-help">Alarme crítico quando sinal ficar abaixo deste valor</p>
          </div>

          <div class="form-field">
            <label>Notificações</label>
            <div class="notification-options">
              <label>
                <input type="checkbox" v-model="notifications.email" />
                <i class="fas fa-envelope"></i>
                E-mail
              </label>
              <label>
                <input type="checkbox" v-model="notifications.dashboard" />
                <i class="fas fa-th-large"></i>
                Dashboard
              </label>
              <label>
                <input type="checkbox" v-model="notifications.whatsapp" />
                <i class="fab fa-whatsapp"></i>
                WhatsApp
              </label>
              <label>
                <input type="checkbox" v-model="notifications.telegram" />
                <i class="fab fa-telegram-plane"></i>
                Telegram
              </label>
              <label>
                <input type="checkbox" v-model="notifications.webhook" />
                <i class="fas fa-link"></i>
                Webhook
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex justify-end gap-2">
        <button type="button" class="h-8 rounded-md border border-neutral-200 px-3 text-sm text-neutral-700 hover:bg-neutral-100" @click="close">
          Cancelar
        </button>
        <button
          type="button"
          class="h-8 rounded-md bg-primary-600 px-3 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          :disabled="saving"
          data-testid="alarm-config-save"
          @click="saveAlarmConfig"
        >
          {{ saving ? 'A guardar…' : 'Guardar configuração' }}
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'
import { PhBell } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import {
  normalizeOpticalHistory,
  OPTICAL_HISTORY_EMPTY_MESSAGE,
  OPTICAL_HISTORY_ERROR_MESSAGE,
} from '@/utils/opticalHistory'
import TimeSeriesChart from './charts/TimeSeriesChart.vue'

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

const emit = defineEmits(['close', 'saved'])

const { get, patch } = useApi()
const { success, error: notifyError } = useNotification()

const alarmEnabled = ref(false)
const warningThreshold = ref(-24)
const criticalThreshold = ref(-27)
const notifications = ref({
  email: true,
  dashboard: true,
  webhook: false,
  whatsapp: false,
  telegram: false
})
const saving = ref(false)
// EV-0011: o gráfico é o TimeSeriesChart; aqui só vivem os dados.
const historyPoints = ref([])
const historyEmptyMessage = ref(OPTICAL_HISTORY_EMPTY_MESSAGE)

// Global thresholds from configuration
const globalWarningThreshold = ref(-24)
const globalCriticalThreshold = ref(-27)

// EV-0068a: o BaseModal avisa ao fechar com alterações por guardar.
const formSnapshot = () =>
  JSON.stringify([alarmEnabled.value, warningThreshold.value, criticalThreshold.value, notifications.value])
const savedSnapshot = ref('')
const dirty = computed(() => Boolean(savedSnapshot.value) && formSnapshot() !== savedSnapshot.value)

// Load global thresholds from configuration
const loadGlobalThresholds = async () => {
  try {
    const response = await get('/setup_app/api/config/')
    if (response.success && response.configuration) {
      const cfg = response.configuration
      globalWarningThreshold.value = parseFloat(cfg.OPTICAL_RX_WARNING_THRESHOLD || '-24')
      globalCriticalThreshold.value = parseFloat(cfg.OPTICAL_RX_CRITICAL_THRESHOLD || '-27')
    }
  } catch (error) {
    console.log('[AlarmConfigModal] Could not load global thresholds, using defaults')
  }
}

const close = () => {
  emit('close')
}

const formatPower = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return value.toFixed(2)
}

const getSignalClass = (value) => {
  if (value === null || value === undefined) return ''
  if (value < criticalThreshold.value) return 'signal-critical'
  if (value < warningThreshold.value) return 'signal-warning'
  return 'signal-good'
}

const loadHistoricalData = async () => {
  if (!props.port?.id) return

  // EV-0001: histórico vazio ou erro mostram mensagem explícita — nunca dados inventados.
  historyEmptyMessage.value = OPTICAL_HISTORY_EMPTY_MESSAGE
  try {
    const response = await get(`/api/v1/ports/${props.port.id}/optical_history/`, { hours: 24 })
    historyPoints.value = normalizeOpticalHistory(response).points
  } catch (error) {
    console.error('[AlarmConfigModal] Falha ao carregar histórico óptico:', error)
    historyPoints.value = []
    historyEmptyMessage.value = OPTICAL_HISTORY_ERROR_MESSAGE
  }
}

const historySeries = computed(() => {
  if (!historyPoints.value.length) return []
  return [
    { label: 'RX (dBm)', data: historyPoints.value.map(p => ({ x: p.timestamp, y: p.rx })) },
    { label: 'TX (dBm)', data: historyPoints.value.map(p => ({ x: p.timestamp, y: p.tx })) },
  ]
})

const thresholdLines = computed(() => [
  { value: warningThreshold.value, label: 'Atenção' },
  { value: criticalThreshold.value, label: 'Crítico', color: '#f87171' },
])

const saveAlarmConfig = async () => {
  if (!props.port?.id) return
  
  saving.value = true
  try {
    await patch(`/api/v1/ports/${props.port.id}/`, {
      alarm_enabled: alarmEnabled.value,
      alarm_warning_threshold: warningThreshold.value,
      alarm_critical_threshold: criticalThreshold.value,
      alarm_notifications: notifications.value
    })
    savedSnapshot.value = formSnapshot()
    success('Alarme configurado', 'As configurações de alarme foram salvas.')
    emit('saved') // Notify parent to reload ports
    close()
  } catch (error) {
    console.error('[AlarmConfigModal] Error saving alarm config:', error)
    notifyError('Erro', 'Não foi possível salvar as configurações.')
  } finally {
    saving.value = false
  }
}

watch(() => props.isOpen, async (newVal) => {
  if (!newVal) savedSnapshot.value = ''
  if (newVal && props.port) {
    // Load global thresholds first
    await loadGlobalThresholds()
    
    // Load port-specific config or use global defaults
    alarmEnabled.value = props.port.alarm_enabled || false
    warningThreshold.value = props.port.alarm_warning_threshold || globalWarningThreshold.value
    criticalThreshold.value = props.port.alarm_critical_threshold || globalCriticalThreshold.value
    notifications.value = props.port.alarm_notifications || {
      email: true,
      dashboard: true,
      webhook: false,
      whatsapp: false,
      telegram: false
    }
    savedSnapshot.value = formSnapshot()

    await loadHistoricalData()
  }
})

// Redraw chart when thresholds change
// As linhas de limiar são computadas a partir dos refs: mudar o limiar redesenha
// o gráfico sem nova chamada ao Zabbix (antes recarregava o histórico a cada tecla).
</script>

<style scoped>

.alarm-modal-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.current-signal,
.alarm-config,
.signal-history {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid rgb(var(--n-200));
}

.current-signal:last-child,
.alarm-config:last-child,
.signal-history:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

h4 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: rgb(var(--n-900));
}

.signal-display {
  display: flex;
  gap: 16px;
}

.signal-item {
  flex: 1;
  padding: 16px;
  background: rgb(var(--n-50));
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.signal-item .label {
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--n-500));
  text-transform: uppercase;
}

.signal-item .value {
  font-size: 18px;
  font-weight: 700;
  font-family: 'Monaco', 'Courier New', monospace;
}

.signal-good {
  color: rgb(var(--success));
}

.signal-warning {
  color: rgb(var(--warning));
}

.signal-critical {
  color: rgb(var(--danger));
}

.form-field {
  margin-bottom: 16px;
}

.config-info {
  padding: 12px;
  background: rgb(var(--info) / 0.12);
  border-left: 4px solid rgb(var(--info));
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 13px;
  color: rgb(var(--info-strong));
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-info i {
  font-size: 16px;
}

.form-field label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: rgb(var(--n-900));
  margin-bottom: 6px;
}

.form-field label input[type="checkbox"] {
  margin-right: 8px;
}

.form-input {
  width: 100%;
  padding: 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  font-size: 14px;
  color: rgb(var(--n-900));
  background: rgb(var(--surface));
}

.form-input:focus {
  outline: none;
  border-color: rgb(var(--primary-500));
}

.field-help {
  font-size: 12px;
  color: rgb(var(--n-500));
  margin: 4px 0 0 0;
}

.threshold-config {
  margin-top: 16px;
  padding: 16px;
  background: rgb(var(--n-50));
  border-radius: 8px;
}

.notification-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notification-options label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: normal;
}

.notification-options label i {
  width: 16px;
  text-align: center;
  color: rgb(var(--primary-500));
}

.notification-options label i.fa-whatsapp {
  color: #25d366;
}

.notification-options label i.fa-telegram-plane {
  color: #0088cc;
}

.notification-options label i.fa-envelope {
  color: #ea4335;
}

.notification-options label i.fa-th-large {
  color: rgb(var(--primary-500));
}

.notification-options label i.fa-link {
  color: rgb(var(--n-500));
}

.chart-container {
  background: rgb(var(--n-50));
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
}

.chart-container canvas {
  width: 100%;
  display: block;
}
</style>
