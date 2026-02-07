<template>
  <div class="space-y-6">
    <!-- Header with Add Button -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Gateways de Comunicação</h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {{ gatewayCount?.total || 0 }} {{ (gatewayCount?.total || 0) === 1 ? 'gateway' : 'gateways' }} configurado{{ (gatewayCount?.total || 0) !== 1 ? 's' : '' }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button type="button" class="btn-outline" @click="handleOpenTemplates">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 5h16a1.5 1.5 0 011.5 1.5v11A1.5 1.5 0 0120 19H4a1.5 1.5 0 01-1.5-1.5v-11A1.5 1.5 0 014 5z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4.5 7l7.5 5.25L19.5 7" />
          </svg>
          Modelos de Aviso
        </button>
        <button @click="showAddModal = true" class="btn-primary">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Adicionar Gateway
        </button>
      </div>
    </div>

    <!-- Gateway Type Tabs -->
    <div class="border-b border-gray-200 dark:border-gray-700">
      <nav class="-mb-px flex space-x-8">
        <button 
          v-for="tab in tabs" 
          :key="tab.type"
          @click="activeTab = tab.type"
          class="whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors"
          :class="activeTab === tab.type 
            ? 'border-primary-500 text-primary-600 dark:text-primary-400' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'"
        >
          {{ tab.label }}
          <span class="ml-2 px-2 py-0.5 rounded-full text-xs" 
                :class="activeTab === tab.type 
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400' 
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'">
            {{ tab.count }}
          </span>
        </button>
      </nav>
    </div>

    <!-- SMS Gateways -->
    <div v-if="activeTab === 'sms'">
      <GatewayList 
        :gateways="smsGateways" 
        type="sms"
        @edit="handleEdit"
        @delete="handleDelete"
        @test="handleTest"
      />
    </div>

    <!-- WhatsApp Gateways -->
    <div v-else-if="activeTab === 'whatsapp'">
      <WhatsAppGatewayList 
        :gateways="whatsappGateways"
        @edit="handleEdit"
        @delete="handleDelete"
        @generate-qr="handleGenerateQR"
        @check-qr="handleCheckQR"
        @disconnect="handleDisconnect"
      />
    </div>

    <!-- Telegram Gateways -->
    <div v-else-if="activeTab === 'telegram'">
      <GatewayList 
        :gateways="telegramGateways" 
        type="telegram"
        @edit="handleEdit"
        @delete="handleDelete"
        @test="handleTest"
      />
    </div>

    <!-- SMTP Gateways -->
    <div v-else-if="activeTab === 'smtp'">
      <GatewayList 
        :gateways="smtpGateways" 
        type="smtp"
        @edit="handleEdit"
        @delete="handleDelete"
        @test="handleTest"
      />
    </div>

    <!-- Video Gateways -->
    <div v-else-if="activeTab === 'video'">
      <GatewayList 
        :gateways="videoGateways" 
        type="video"
        @edit="handleEdit"
        @delete="handleDelete"
      />
    </div>

    <!-- Alert Templates -->
    <div v-else-if="activeTab === 'alert_templates'">
      <AlertTemplatesTab :modal-trigger="templatesModalTrigger" />
    </div>

    <!-- Contacts Tab -->
    <div v-else-if="activeTab === 'contacts'">
      <ContactsTab />
    </div>

    <!-- Add/Edit Modal -->
    <GatewayEditModal 
      v-if="showAddModal || editingGateway"
      :gateway="editingGateway"
      :type="activeTab"
      @close="closeModal"
      @save="handleSave"
    />

    <!-- WhatsApp QR Modal -->
    <WhatsAppQRModal 
      v-if="showQRModal"
      :gateway-id="qrGatewayId"
      :qr-code="qrCode"
      :status="qrStatus"
      @close="closeQRModal"
      @check="handleCheckQRStatus"
    />

    <!-- Test SMS Modal -->
    <TestSMSModal 
      v-if="showTestSMSModal && testingGateway"
      :gateway-config="buildTestConfig()"
      @close="closeTestSMSModal"
      @test="handleTestSMS"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useGatewayConfig } from '@/composables/useGatewayConfig'
import { useNotification } from '@/composables/useNotification'
import { useContactsStore } from '@/stores/contacts'
import { useAlertTemplatesStore } from '@/stores/alertTemplates'
import GatewayList from './GatewayList.vue'
import WhatsAppGatewayList from './WhatsAppGatewayList.vue'
import GatewayEditModal from './GatewayEditModal.vue'
import WhatsAppQRModal from './WhatsAppQRModal.vue'
import TestSMSModal from './TestSMSModal.vue'
import ContactsTab from './ContactsTab.vue'
import AlertTemplatesTab from './AlertTemplatesTab.vue'

// Composables
const {
  gateways,
  loading,
  smsGateways,
  whatsappGateways,
  telegramGateways,
  smtpGateways,
  videoGateways,
  gatewayCount,
  loadGateways,
  saveGateway,
  deleteGateway,
  testGateway,
  generateWhatsappQR,
  checkWhatsappQRStatus,
  disconnectWhatsappQR,
} = useGatewayConfig()

const notify = useNotification()

// Local state
const activeTab = ref('sms')
const showAddModal = ref(false)
const editingGateway = ref(null)
const showQRModal = ref(false)
const qrGatewayId = ref(null)
const qrCode = ref(null)
const qrStatus = ref(null)
const showTestSMSModal = ref(false)
const testingGateway = ref(null)
const templatesModalTrigger = ref(0)

const contactsStore = useContactsStore()
const { contacts } = storeToRefs(contactsStore)
const { loadContacts } = contactsStore

const alertTemplatesStore = useAlertTemplatesStore()
const { templateCount } = storeToRefs(alertTemplatesStore)
const { loadTemplates: loadAlertTemplates } = alertTemplatesStore

// Computed
const tabs = computed(() => [
  { type: 'sms', label: 'SMS', count: smsGateways.value.length },
  { type: 'whatsapp', label: 'WhatsApp', count: whatsappGateways.value.length },
  { type: 'telegram', label: 'Telegram', count: telegramGateways.value.length },
  { type: 'smtp', label: 'E-mail (SMTP)', count: smtpGateways.value.length },
  { type: 'contacts', label: 'Contatos', count: contacts.value.length },
  { type: 'alert_templates', label: 'Modelos de Aviso', count: templateCount.value },
])

// Methods
const handleEdit = (gateway) => {
  editingGateway.value = { ...gateway }
}

const handleDelete = async (gatewayId) => {
  if (confirm('Excluir este gateway?')) {
    await deleteGateway(gatewayId)
  }
}

const handleTest = async (gatewayId) => {
  // Find gateway by ID
  const gateway = gateways.value.find(g => g.id === gatewayId)
  if (!gateway) {
    console.error('[GatewaysTab] Gateway not found:', gatewayId)
    return
  }

  // Only SMS and SMTP have test functionality
  if (gateway.gateway_type !== 'sms' && gateway.gateway_type !== 'smtp') {
    notify.warning('Teste', `Teste não disponível para ${gateway.gateway_type}`)
    return
  }

  // For SMS, open the test SMS modal directly
  if (gateway.gateway_type === 'sms') {
    testingGateway.value = gateway
    showTestSMSModal.value = true
    return
  }

  // For SMTP, test directly with current config
  const config = gateway.config || {}
  await testGateway(gateway.gateway_type, config)
}

// Handle SMS test from modal
const handleTestSMS = async (testConfig) => {
  try {
    await testGateway('sms', testConfig)
  } catch (error) {
    console.error('[GatewaysTab] Error testing SMS:', error)
  }
}

// Close test SMS modal
const closeTestSMSModal = () => {
  showTestSMSModal.value = false
  testingGateway.value = null
}

// Build test config for SMS modal
const buildTestConfig = () => {
  if (!testingGateway.value) return {}
  
  const config = testingGateway.value.config || {}
  return {
    provider: testingGateway.value.provider || '',
    username: config.username || '',
    password: config.password || '',
    api_token: config.password || config.api_token || '',
    api_url: config.api_url || '',
    sender_id: config.sender_id || '',
  }
}

const handleSave = async (gatewayData) => {
  const success = await saveGateway(gatewayData)
  if (success) {
    closeModal()
  }
}

const closeModal = () => {
  showAddModal.value = false
  editingGateway.value = null
}

// WhatsApp specific methods
const handleGenerateQR = async (gatewayId) => {
  const gateway = gateways.value.find(g => g.id === gatewayId)
  if (!gateway) {
    console.error('[GatewaysTab] Gateway not found:', gatewayId)
    return
  }
  
  const config = gateway.config || {}
  const qrServiceUrl = config.qr_service_url || ''
  
  const result = await generateWhatsappQR(gatewayId, qrServiceUrl)
  if (result) {
    qrGatewayId.value = gatewayId
    qrCode.value = result.qr_image_url || result.qr_code
    qrStatus.value = result.qr_status || result.status
    showQRModal.value = true
  }
}

const handleCheckQR = async (gatewayId) => {
  const gateway = gateways.value.find(g => g.id === gatewayId)
  if (!gateway) return
  
  const config = gateway.config || {}
  const qrServiceUrl = config.qr_service_url || ''
  
  await checkWhatsappQRStatus(gatewayId, qrServiceUrl)
}

const handleCheckQRStatus = async () => {
  if (qrGatewayId.value) {
    const gateway = gateways.value.find(g => g.id === qrGatewayId.value)
    if (!gateway) return
    
    const config = gateway.config || {}
    const qrServiceUrl = config.qr_service_url || ''
    
    const result = await checkWhatsappQRStatus(qrGatewayId.value, qrServiceUrl)
    if (result) {
      qrStatus.value = result.qr_status || result.status
      if (qrStatus.value === 'connected') {
        setTimeout(() => {
          closeQRModal()
        }, 2000)
      }
    }
  }
}

const handleDisconnect = async (gatewayId) => {
  if (confirm('Desconectar WhatsApp? Será necessário escanear o QR Code novamente.')) {
    await disconnectWhatsappQR(gatewayId)
  }
}

const closeQRModal = () => {
  showQRModal.value = false
  qrGatewayId.value = null
  qrCode.value = null
  qrStatus.value = null
}

const handleOpenTemplates = async () => {
  activeTab.value = 'alert_templates'
  await nextTick()
  templatesModalTrigger.value += 1
}

// Lifecycle
onMounted(async () => {
  await Promise.all([
    loadGateways(),
    contacts.value.length ? Promise.resolve() : loadContacts(),
    templateCount.value ? Promise.resolve() : loadAlertTemplates(),
  ])
})
</script>

<style scoped>
.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 transition-all duration-200;
}

.btn-outline {
  @apply inline-flex items-center justify-center rounded-md border border-primary-200 px-4 py-2 text-sm font-semibold text-primary-600 hover:bg-primary-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 transition-all duration-200 dark:text-primary-300 dark:border-primary-700 dark:hover:bg-primary-900/40;
}
</style>
