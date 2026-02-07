<template>
  <teleport to="body">
    <div class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="fixed inset-0 bg-black/50 dark:bg-black/70 transition-opacity" @click="$emit('close')"></div>

        <!-- Modal -->
        <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
              {{ isEditing ? 'Editar Gateway' : 'Adicionar Gateway' }}
            </h3>
            <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
              </svg>
            </button>
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-4">
            <!-- Gateway Type (only for new gateways) -->
            <div v-if="!isEditing">
              <label class="label-custom">Tipo de Gateway *</label>
              <select v-model="form.type" class="input-custom" required>
                <option value="">Selecione...</option>
                <option value="sms">SMS</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="telegram">Telegram</option>
                <option value="smtp">E-mail (SMTP)</option>
                <option value="video">Vídeo</option>
              </select>
            </div>

            <!-- Common Fields -->
            <div>
              <label class="label-custom">Nome *</label>
              <input 
                v-model="form.name" 
                type="text" 
                class="input-custom" 
                placeholder="Ex: Gateway SMS Principal"
                required
              />
            </div>

            <!-- Type-specific fields -->
            <template v-if="form.type === 'sms'">
              <div>
                <label class="label-custom">Provedor</label>
                <select v-model="form.provider" class="input-custom">
                  <option value="smsnet">SMSNET</option>
                  <option value="twilio">Twilio</option>
                  <option value="nexmo">Nexmo/Vonage</option>
                  <option value="plivo">Plivo</option>
                  <option value="custom">Customizado</option>
                </select>
              </div>

              <div>
                <label class="label-custom">API URL *</label>
                <input 
                  v-model="form.api_url" 
                  type="url" 
                  class="input-custom" 
                  placeholder="https://api.twilio.com/2010-04-01"
                  required
                />
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="label-custom">API Key/SID *</label>
                  <input 
                    v-model="form.api_key" 
                    type="text" 
                    class="input-custom" 
                    required
                  />
                </div>

                <div>
                  <label class="label-custom">API Secret/Token *</label>
                  <input 
                    v-model="form.api_secret" 
                    type="password" 
                    class="input-custom" 
                    required
                  />
                </div>
              </div>

              <div>
                <label class="label-custom">Sender ID/Phone Number</label>
                <input 
                  v-model="form.sender_id" 
                  type="text" 
                  class="input-custom" 
                  placeholder="+5511999999999"
                />
              </div>
            </template>

            <template v-else-if="form.type === 'whatsapp'">
              <div>
                <label class="label-custom">Modo de Autenticação *</label>
                <select v-model="form.auth_mode" class="input-custom" required>
                  <option value="qr">QR Code</option>
                  <option value="api">API Token</option>
                </select>
              </div>

              <div>
                <label class="label-custom">URL do Serviço QR Code *</label>
                <input 
                  v-model="form.qr_service_url" 
                  type="url" 
                  class="input-custom" 
                  placeholder="http://localhost:3001"
                  required
                />
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  URL do serviço docker-whatsapp. Use <code class="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">http://localhost:3001</code> se estiver rodando localmente, ou <code class="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">http://whatsapp-qr-1:3000</code> se dentro do Docker.
                </p>
              </div>

              <div>
                <label class="label-custom">Session ID *</label>
                <input 
                  v-model="form.session_id" 
                  type="text" 
                  class="input-custom" 
                  placeholder="session-1"
                  required
                />
              </div>

              <div>
                <label class="label-custom">Número de Telefone</label>
                <input 
                  v-model="form.phone_number" 
                  type="tel" 
                  class="input-custom" 
                  placeholder="+5511999999999"
                />
              </div>

              <!-- WhatsApp Connection Status (only when editing) -->
              <div v-if="isEditing" class="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between mb-3">
                  <h4 class="text-sm font-semibold text-gray-900 dark:text-white">
                    Status da Conexão
                  </h4>
                  <button 
                    type="button"
                    @click="refreshWhatsAppStatus"
                    :disabled="checkingStatus"
                    class="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 flex items-center gap-1"
                  >
                    <svg :class="{'animate-spin': checkingStatus}" class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                    </svg>
                    Atualizar
                  </button>
                </div>

                <div class="flex items-center gap-3">
                  <div class="flex items-center gap-2">
                    <div 
                      class="w-2.5 h-2.5 rounded-full"
                      :class="{
                        'bg-green-500 animate-pulse': whatsappStatus === 'connected',
                        'bg-yellow-500': whatsappStatus === 'connecting' || whatsappStatus === 'qr_pending',
                        'bg-gray-400': whatsappStatus === 'disconnected' || !whatsappStatus,
                        'bg-red-500': whatsappStatus === 'error'
                      }"
                    ></div>
                    <span class="text-sm font-medium" :class="{
                      'text-green-600 dark:text-green-400': whatsappStatus === 'connected',
                      'text-yellow-600 dark:text-yellow-400': whatsappStatus === 'connecting' || whatsappStatus === 'qr_pending',
                      'text-gray-600 dark:text-gray-400': whatsappStatus === 'disconnected' || !whatsappStatus,
                      'text-red-600 dark:text-red-400': whatsappStatus === 'error'
                    }">
                      {{ getWhatsAppStatusText(whatsappStatus) }}
                    </span>
                  </div>

                  <div v-if="lastWhatsAppConnection" class="text-xs text-gray-500 dark:text-gray-400 border-l border-gray-300 dark:border-gray-600 pl-3">
                    Última conexão: {{ formatDate(lastWhatsAppConnection) }}
                  </div>
                </div>

                <div v-if="whatsappStatus === 'disconnected'" class="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  Conecte escaneando um QR Code
                </div>
              </div>
            </template>

            <template v-else-if="form.type === 'telegram'">
              <div>
                <label class="label-custom">Bot Token *</label>
                <input 
                  v-model="form.api_key" 
                  type="text" 
                  class="input-custom" 
                  placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                  required
                />
              </div>

              <div>
                <label class="label-custom">Chat ID Padrão</label>
                <input 
                  v-model="form.chat_id" 
                  type="text" 
                  class="input-custom" 
                  placeholder="-1001234567890"
                />
              </div>
            </template>

            <template v-else-if="form.type === 'smtp'">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="label-custom">Servidor SMTP *</label>
                  <input 
                    v-model="form.smtp_host" 
                    type="text" 
                    class="input-custom" 
                    placeholder="smtp.gmail.com"
                    required
                  />
                </div>

                <div>
                  <label class="label-custom">Porta *</label>
                  <input 
                    v-model.number="form.smtp_port" 
                    type="number" 
                    class="input-custom" 
                    placeholder="587"
                    required
                  />
                </div>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="label-custom">Usuário *</label>
                  <input 
                    v-model="form.username" 
                    type="text" 
                    class="input-custom" 
                    required
                  />
                </div>

                <div>
                  <label class="label-custom">Senha *</label>
                  <input 
                    v-model="form.password" 
                    type="password" 
                    class="input-custom" 
                    required
                  />
                </div>
              </div>

              <div>
                <label class="label-custom">E-mail Remetente *</label>
                <input 
                  v-model="form.sender_email" 
                  type="email" 
                  class="input-custom" 
                  placeholder="noreply@example.com"
                  required
                />
              </div>

              <div class="flex items-center gap-4">
                <div class="flex items-center">
                  <input 
                    v-model="form.use_tls" 
                    type="checkbox" 
                    id="use-tls"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label for="use-tls" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
                    Usar TLS
                  </label>
                </div>

                <div class="flex items-center">
                  <input 
                    v-model="form.use_ssl" 
                    type="checkbox" 
                    id="use-ssl"
                    class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label for="use-ssl" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
                    Usar SSL
                  </label>
                </div>
              </div>
            </template>

            <template v-else-if="form.type === 'video'">
              <div>
                <label class="label-custom">URL do Servidor de Vídeo *</label>
                <input 
                  v-model="form.api_url" 
                  type="url" 
                  class="input-custom" 
                  placeholder="rtsp://192.168.1.100:554"
                  required
                />
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="label-custom">Usuário</label>
                  <input 
                    v-model="form.username" 
                    type="text" 
                    class="input-custom" 
                  />
                </div>

                <div>
                  <label class="label-custom">Senha</label>
                  <input 
                    v-model="form.password" 
                    type="password" 
                    class="input-custom" 
                  />
                </div>
              </div>
            </template>

            <!-- Description (common) -->
            <div>
              <label class="label-custom">Descrição</label>
              <textarea 
                v-model="form.description" 
                class="input-custom" 
                rows="2"
                placeholder="Descrição opcional do gateway"
              ></textarea>
            </div>

            <!-- Active Status -->
            <div class="flex items-center">
              <input 
                v-model="form.is_active" 
                type="checkbox" 
                id="is-active-gateway"
                class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <label for="is-active-gateway" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
                Gateway ativo
              </label>
            </div>

            <!-- Action Buttons -->
            <div class="flex justify-between gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div class="flex gap-3">
                <!-- Test SMS Button (only for editing SMS) -->
                <button 
                  v-if="isEditing && form.type === 'sms'" 
                  type="button" 
                  @click="showTestModal = true"
                  class="btn-secondary text-blue-600 dark:text-blue-400"
                >
                  <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>
                  </svg>
                  Testar SMS
                </button>

                <!-- WhatsApp Buttons (only for editing) -->
                <div v-if="isEditing && form.type === 'whatsapp'" class="flex gap-2">
                  <!-- Test WhatsApp Button -->
                  <button 
                    type="button" 
                    @click="showTestWhatsAppModal = true"
                    class="btn-secondary text-blue-600 dark:text-blue-400"
                  >
                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                    </svg>
                    Testar WhatsApp
                  </button>

                  <!-- Generate QR Code Button -->
                  <button 
                    type="button" 
                    @click="handleGenerateQR"
                    class="btn-secondary text-green-600 dark:text-green-400"
                  >
                    <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v1m6 11h2m-6 0h-2v4m0-11v3m0 0h.01M12 12h4.01M16 20h4M4 12h4m12 0h.01M5 8h2a1 1 0 001-1V5a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1zm12 0h2a1 1 0 001-1V5a1 1 0 00-1-1h-2a1 1 0 00-1 1v2a1 1 0 001 1zM5 20h2a1 1 0 001-1v-2a1 1 0 00-1-1H5a1 1 0 00-1 1v2a1 1 0 001 1z"/>
                    </svg>
                    Gerar QR Code
                  </button>
                </div>
              </div>

              <div class="flex gap-3">
                <button type="button" @click="$emit('close')" class="btn-secondary">
                  Cancelar
                </button>
                <button type="submit" :disabled="saving" class="btn-primary">
                  <svg v-if="saving" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {{ isEditing ? 'Atualizar' : 'Criar' }}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Test SMS Modal -->
    <TestSMSModal 
      v-if="showTestModal"
      :gateway-config="buildTestConfig()"
      @close="showTestModal = false"
      @test="handleTestSMS"
    />

    <!-- Test WhatsApp Modal -->
    <TestWhatsAppModal 
      v-if="showTestWhatsAppModal"
      :gateway-id="form.id"
      :is-connected="whatsappConnectionStatus === 'connected'"
      @close="showTestWhatsAppModal = false"
      @test="handleTestWhatsApp"
    />

    <!-- WhatsApp QR Modal -->
    <WhatsAppQRModal 
      v-if="showQRModal"
      :gateway-id="qrGatewayId"
      :qr-code="qrCode"
      :status="qrStatus"
      :last-disconnect-reason="qrLastDisconnectReason"
      @close="closeQRModal"
      @check="handleCheckQRStatus"
      @reset="handleResetWhatsApp"
    />
  </teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useGatewayConfig } from '@/composables/useGatewayConfig'
import TestSMSModal from './TestSMSModal.vue'
import TestWhatsAppModal from './TestWhatsAppModal.vue'
import WhatsAppQRModal from './WhatsAppQRModal.vue'

const props = defineProps({
  gateway: {
    type: Object,
    default: null,
  },
  type: {
    type: String,
    default: 'sms',
  },
})

const emit = defineEmits(['close', 'save'])

const { testGateway, generateWhatsappQR, checkWhatsappQRStatus, resetWhatsappQR, testWhatsappMessage } = useGatewayConfig()

// Local state
const showTestModal = ref(false)
const showTestWhatsAppModal = ref(false)
const showQRModal = ref(false)
const qrGatewayId = ref(null)
const qrCode = ref(null)
const qrStatus = ref(null)
const qrLastDisconnectReason = ref(null)

// WhatsApp connection state
const whatsappStatus = ref(null)
const lastWhatsAppConnection = ref(null)
const checkingStatus = ref(false)

/**
 * Map gateway data from API format to form format
 * API format: { gateway_type: 'sms', config: { username, password, api_url } }
 * Form format: { type: 'sms', username, password, api_url }
 */
const mapGatewayToForm = (gateway) => {
  if (!gateway) return {}
  
  const config = gateway.config || {}
  const baseForm = {
    id: gateway.id,
    name: gateway.name || '',
    type: gateway.gateway_type || props.type || 'sms',
    is_active: gateway.enabled !== undefined ? gateway.enabled : true,
    description: config.description || '',
    provider: gateway.provider || '',
    priority: gateway.priority || 1,
  }

  // Map config fields based on gateway type
  switch (gateway.gateway_type) {
    case 'sms':
      return {
        ...baseForm,
        api_url: config.api_url || '',
        api_key: config.username || '',
        api_secret: config.password || config.api_token || '',
        sender_id: config.sender_id || '',
      }
    
    case 'whatsapp':
      return {
        ...baseForm,
        auth_mode: config.auth_mode || 'qr',
        qr_service_url: config.qr_service_url || '',
        session_id: config.session_id || '',
        phone_number: config.phone_number || '',
      }
    
    case 'telegram':
      return {
        ...baseForm,
        api_key: config.bot_token || config.api_token || '',
        chat_id: config.chat_id || '',
      }
    
    case 'smtp':
      return {
        ...baseForm,
        smtp_host: config.host || '',
        smtp_port: config.port || 587,
        username: config.user || '',
        password: config.password || '',
        sender_email: config.from_email || '',
        use_tls: config.security === 'tls' || false,
        use_ssl: config.security === 'ssl' || false,
      }
    
    case 'video':
      return {
        ...baseForm,
        api_url: config.url || config.api_url || '',
        username: config.username || '',
        password: config.password || '',
      }
    
    default:
      return baseForm
  }
}

// Local state
const form = ref(
  props.gateway 
    ? mapGatewayToForm(props.gateway)
    : {
        type: props.type || 'sms',
        name: '',
        is_active: true,
      }
)

const saving = ref(false)

// Computed
const isEditing = computed(() => !!props.gateway?.id)

// WhatsApp status helpers (DEFINIR ANTES DE USAR)
const getWhatsAppStatusText = (status) => {
  const statusMap = {
    'connected': 'Conectado',
    'connecting': 'Conectando...',
    'qr_pending': 'Aguardando QR',
    'disconnected': 'Desconectado',
    'error': 'Erro',
  }
  return statusMap[status] || 'Desconhecido'
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  try {
    const date = new Date(dateString)
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (e) {
    return dateString
  }
}

// Refresh WhatsApp connection status (DEFINIR ANTES DO WATCH)
const refreshWhatsAppStatus = async () => {
  console.log('[GatewayEditModal] refreshWhatsAppStatus called')
  console.log('[GatewayEditModal] form.value:', { id: form.value.id, type: form.value.type })
  
  if (!form.value.id || form.value.type !== 'whatsapp') {
    console.log('[GatewayEditModal] Skipping status check - not WhatsApp or no ID')
    return
  }
  
  checkingStatus.value = true
  try {
    console.log('[GatewayEditModal] Refreshing WhatsApp status...')
    const qrServiceUrl = form.value.qr_service_url || ''
    console.log('[GatewayEditModal] QR Service URL:', qrServiceUrl)
    
    const result = await checkWhatsappQRStatus(form.value.id, qrServiceUrl)
    
    console.log('[GatewayEditModal] Status result:', result)
    
    if (result) {
      whatsappStatus.value = result.qr_status || result.status || 'disconnected'
      console.log('[GatewayEditModal] Set whatsappStatus to:', whatsappStatus.value)
      
      // Se tiver updated_at, usar como última conexão
      if (result.updated_at) {
        lastWhatsAppConnection.value = result.updated_at
        console.log('[GatewayEditModal] Set lastWhatsAppConnection to:', lastWhatsAppConnection.value)
      }
      
      // Se status for connected e tiver updated_at, é a data da última conexão
      if (whatsappStatus.value === 'connected' && result.updated_at) {
        lastWhatsAppConnection.value = result.updated_at
      }
    } else {
      console.log('[GatewayEditModal] No result from checkWhatsappQRStatus')
    }
  } catch (error) {
    console.error('[GatewayEditModal] Error checking WhatsApp status:', error)
    whatsappStatus.value = 'error'
  } finally {
    checkingStatus.value = false
  }
}

// WhatsApp connection status computed
const whatsappConnectionStatus = computed(() => {
  return whatsappStatus.value || 'disconnected'
})

// Watch for gateway changes to update form (DEPOIS DE DEFINIR FUNÇÕES)
watch(() => props.gateway, (newGateway) => {
  if (newGateway) {
    form.value = mapGatewayToForm(newGateway)
    
    // Se for WhatsApp, verificar status automaticamente (usar form.value.type pois já foi mapeado)
    if (newGateway.gateway_type === 'whatsapp' && newGateway.id) {
      console.log('[GatewayEditModal] WhatsApp gateway detected, checking status...')
      console.log('[GatewayEditModal] Gateway data:', { 
        id: newGateway.id, 
        type: newGateway.gateway_type,
        form_id: form.value.id,
        form_type: form.value.type
      })
      // Delay para garantir que form.value foi atualizado
      nextTick(() => {
        refreshWhatsAppStatus()
      })
    }
  }
}, { deep: true, immediate: true })

// Watch for type changes to set default form
watch(() => props.type, (newType) => {
  if (!isEditing.value) {
    form.value.type = newType
  }
})

// Methods
const handleSubmit = async () => {
  saving.value = true
  try {
    // Map form back to API format
    const payload = {
      id: form.value.id,
      name: form.value.name,
      gateway_type: form.value.type,
      provider: form.value.provider || '',
      priority: form.value.priority || 1,
      enabled: form.value.is_active,
      config: {},
    }

    // Map fields back to config based on type
    switch (form.value.type) {
      case 'sms':
        payload.config = {
          username: form.value.api_key || '',
          password: form.value.api_secret || '',
          api_url: form.value.api_url || '',
          sender_id: form.value.sender_id || '',
          description: form.value.description || '',
        }
        break
      
      case 'whatsapp':
        payload.config = {
          auth_mode: form.value.auth_mode || 'qr',
          qr_service_url: form.value.qr_service_url || '',
          session_id: form.value.session_id || '',
          phone_number: form.value.phone_number || '',
          description: form.value.description || '',
        }
        break
      
      case 'telegram':
        payload.config = {
          bot_token: form.value.api_key || '',
          api_token: form.value.api_key || '',
          chat_id: form.value.chat_id || '',
          description: form.value.description || '',
        }
        break
      
      case 'smtp':
        payload.config = {
          host: form.value.smtp_host || '',
          port: form.value.smtp_port || 587,
          user: form.value.username || '',
          password: form.value.password || '',
          from_email: form.value.sender_email || '',
          security: form.value.use_tls ? 'tls' : (form.value.use_ssl ? 'ssl' : ''),
          description: form.value.description || '',
        }
        break
      
      case 'video':
        payload.config = {
          url: form.value.api_url || '',
          api_url: form.value.api_url || '',
          username: form.value.username || '',
          password: form.value.password || '',
          description: form.value.description || '',
        }
        break

        break
    }

    await emit('save', payload)
  } finally {
    saving.value = false
  }
}

// Build test config from current form
const buildTestConfig = () => {
  return {
    provider: form.value.provider || '',
    username: form.value.api_key || '',
    password: form.value.api_secret || '',
    api_token: form.value.api_secret || '',
    api_url: form.value.api_url || '',
    sender_id: form.value.sender_id || '',
  }
}

// Handle SMS test
const handleTestSMS = async (testConfig) => {
  try {
    await testGateway('sms', testConfig)
  } catch (error) {
    console.error('[GatewayEditModal] Error testing SMS:', error)
  }
}

// Handle WhatsApp message test
const handleTestWhatsApp = async ({ recipient, message }) => {
  if (!form.value.id) {
    console.error('[GatewayEditModal] Cannot test WhatsApp for unsaved gateway')
    return
  }

  try {
    console.log('[GatewayEditModal] Testing WhatsApp message:', { recipient, message })
    const qrServiceUrl = form.value.qr_service_url || ''
    const result = await testWhatsappMessage(form.value.id, recipient, message, qrServiceUrl)
    
    if (result) {
      console.log('[GatewayEditModal] WhatsApp test successful')
      showTestWhatsAppModal.value = false
    }
  } catch (error) {
    console.error('[GatewayEditModal] Error testing WhatsApp:', error)
  }
}

// Handle WhatsApp QR generation
const handleGenerateQR = async () => {
  if (!form.value.id) {
    console.error('[GatewayEditModal] Cannot generate QR code for unsaved gateway')
    return
  }

  // First, check current status
  const qrServiceUrl = form.value.qr_service_url || ''
  console.log('[GatewayEditModal] Checking WhatsApp status before generating QR...')
  
  const statusResult = await checkWhatsappQRStatus(form.value.id, qrServiceUrl)
  console.log('[GatewayEditModal] Current status:', statusResult)
  
  // If already connected, don't generate new QR
  if (statusResult && statusResult.qr_status === 'connected') {
    qrGatewayId.value = form.value.id
    qrCode.value = null
    qrStatus.value = 'connected'
    showQRModal.value = true
    return
  }
  
  // Generate new QR code
  console.log('[GatewayEditModal] Generating QR with:', { 
    gatewayId: form.value.id, 
    qrServiceUrl 
  })
  
  const result = await generateWhatsappQR(form.value.id, qrServiceUrl)
  console.log('[GatewayEditModal] QR generation result:', result)
  
  if (result) {
    qrGatewayId.value = form.value.id
    qrCode.value = result.qr_image_url || result.qr_code
    qrStatus.value = result.qr_status || result.status
    qrLastDisconnectReason.value = result.last_disconnect_reason || null
    
    console.log('[GatewayEditModal] Opening modal with:', {
      qrCode: qrCode.value,
      qrStatus: qrStatus.value,
      lastDisconnectReason: qrLastDisconnectReason.value
    })
    
    showQRModal.value = true
  }
}

// Handle QR status check
const handleCheckQRStatus = async () => {
  if (qrGatewayId.value) {
    const qrServiceUrl = form.value.qr_service_url || ''
    console.log('[GatewayEditModal] Checking QR status for gateway:', qrGatewayId.value)
    
    const result = await checkWhatsappQRStatus(qrGatewayId.value, qrServiceUrl)
    console.log('[GatewayEditModal] Status check result:', result)
    
    if (result) {
      const newStatus = result.qr_status || result.status
      console.log('[GatewayEditModal] Status changed from', qrStatus.value, 'to', newStatus)
      
      qrStatus.value = newStatus
      
      // Update QR code image if returned
      if (result.qr_image_url) {
        qrCode.value = result.qr_image_url
      }
      
      // Update last disconnect reason if present
      if (result.last_disconnect_reason !== undefined) {
        qrLastDisconnectReason.value = result.last_disconnect_reason
        console.log('[GatewayEditModal] Last disconnect reason:', result.last_disconnect_reason)
      }
      
      if (newStatus === 'connected') {
        console.log('[GatewayEditModal] WhatsApp connected! Closing modal in 2s...')
        setTimeout(() => {
          closeQRModal()
        }, 2000)
      }
    }
  }
}

// Close QR modal
const closeQRModal = () => {
  showQRModal.value = false
  qrGatewayId.value = null
  qrCode.value = null
  qrStatus.value = null
  qrLastDisconnectReason.value = null
  qrStatus.value = null
}

// Handle WhatsApp reset
const handleResetWhatsApp = async () => {
  if (!qrGatewayId.value) return
  
  if (confirm('Resetar sessão do WhatsApp? Isso irá desconectar e limpar todos os dados da sessão.')) {
    const qrServiceUrl = form.value.qr_service_url || ''
    const success = await resetWhatsappQR(qrGatewayId.value, qrServiceUrl)
    if (success) {
      closeQRModal()
    }
  }
}
</script>

<style scoped>
.label-custom {
  @apply block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5;
}

.input-custom {
  @apply w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-colors;
}

.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}

.btn-secondary {
  @apply inline-flex items-center justify-center rounded-md bg-white dark:bg-gray-800 px-4 py-2 text-sm font-semibold text-gray-900 dark:text-gray-200 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200;
}
</style>
