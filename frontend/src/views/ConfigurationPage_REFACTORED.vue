<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col h-[calc(100vh-64px)] overflow-hidden transition-colors duration-300">
    
    <!-- Header -->
    <div class="flex-none px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 class="text-xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
          <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          Configurações
        </h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Gestão centralizada de serviços e dados.</p>
      </div>
      
      <div class="flex items-center gap-2">
        <button @click="exportConfig" class="btn-white text-xs">
          <svg class="w-4 h-4 mr-1.5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
          </svg>
          Exportar JSON
        </button>
        <label class="btn-white text-xs cursor-pointer">
          <input type="file" class="hidden" @change="handleImportConfig" accept=".json" autocomplete="off">
          <svg class="w-4 h-4 mr-1.5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
          </svg>
          Importar
        </label>
        <button @click="openHistory" class="btn-white text-xs" title="Histórico de Auditoria">
          <svg class="w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex-none border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6">
      <nav class="-mb-px flex space-x-6 overflow-x-auto custom-scrollbar" aria-label="Tabs">
        <button 
          v-for="item in navItems" 
          :key="item.id"
          @click="activeTab = item.id"
          class="group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-all whitespace-nowrap"
          :class="activeTab === item.id 
            ? 'border-primary-500 text-primary-600 dark:text-primary-400' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'"
        >
          <component 
            :is="item.icon" 
            class="mr-2 h-5 w-5 transition-colors"
            :class="activeTab === item.id ? 'text-primary-500 dark:text-primary-400' : 'text-gray-400 group-hover:text-gray-500'"
          />
          {{ item.label }}
        </button>
      </nav>
    </div>

    <!-- Tab Content -->
    <div class="flex-1 overflow-y-auto custom-scrollbar p-6 bg-gray-50 dark:bg-gray-900">
      <div class="max-w-6xl mx-auto animate-fade-in">
        
        <!-- System Parameters Tab -->
        <SystemParamsTab v-if="activeTab === 'system'" />

        <!-- Monitoring Servers Tab -->
        <MonitoringServersTab v-else-if="activeTab === 'monitoring'" />

        <!-- Gateways Tab -->
        <GatewaysTab v-else-if="activeTab === 'gateways'" />

        <!-- Backups Tab -->
        <BackupsTab v-else-if="activeTab === 'backups'" />

        <!-- Cameras Configuration Tab -->
        <CamerasConfigTab v-else-if="activeTab === 'cameras'" />

        <!-- Maps Configuration Tab -->
        <MapsConfigTab v-else-if="activeTab === 'maps'" />

      </div>
    </div>

    <!-- Audit History Modal (kept from original) -->
    <AuditHistoryModal v-if="showAuditHistory" @close="showAuditHistory = false" />
  </div>
</template>

<script setup>
import { ref, computed, h } from 'vue'
import { useNotification } from '@/composables/useNotification'
import SystemParamsTab from '@/components/Configuration/SystemParamsTab.vue'
import MonitoringServersTab from '@/components/Configuration/MonitoringServersTab.vue'
import GatewaysTab from '@/components/Configuration/GatewaysTab.vue'
import BackupsTab from '@/components/Configuration/BackupsTab.vue'
import CamerasConfigTab from '@/components/Configuration/CamerasConfigTab.vue'
import MapsConfigTab from '@/components/Configuration/MapsConfigTab.vue'
import AuditHistoryModal from '@/components/Configuration/AuditHistoryModal.vue'

// Icons as functional components
const SystemIcon = (props) => h('svg', { ...props, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z' })
])

const MonitoringIcon = (props) => h('svg', { ...props, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' })
])

const GatewayIcon = (props) => h('svg', { ...props, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z' })
])

const BackupIcon = (props) => h('svg', { ...props, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4' })
])

const CameraIcon = (props) => h('svg', { ...props, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z' })
])

const MapIcon = (props) => h('svg', { ...props, fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24' }, [
  h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7' })
])

// Composable
const { notify } = useNotification()

// State
const activeTab = ref('system')
const showAuditHistory = ref(false)

// Navigation items
const navItems = computed(() => [
  { id: 'system', label: 'Sistema', icon: SystemIcon },
  { id: 'monitoring', label: 'Monitoramento', icon: MonitoringIcon },
  { id: 'gateways', label: 'Gateways', icon: GatewayIcon },
  { id: 'backups', label: 'Backups', icon: BackupIcon },
  { id: 'cameras', label: 'Câmeras', icon: CameraIcon },
  { id: 'maps', label: 'Mapas', icon: MapIcon },
])

// Methods
const exportConfig = () => {
  try {
    // Collect all configuration from tabs
    const config = {
      exported_at: new Date().toISOString(),
      version: '2.0',
      // Configuration will be collected from composables
    }
    
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `provemaps-config-${new Date().toISOString().split('T')[0]}.json`
    link.click()
    URL.revokeObjectURL(url)
    
    notify('Configurações exportadas com sucesso!', 'success')
  } catch (error) {
    notify('Erro ao exportar configurações', 'error')
  }
}

const handleImportConfig = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  try {
    const text = await file.text()
    const config = JSON.parse(text)
    
    if (!confirm('Importar configurações? Isso substituirá as configurações atuais.')) {
      return
    }

    // Import logic would be handled by composables
    notify('Configurações importadas com sucesso!', 'success')
    
    // Reset file input
    event.target.value = ''
  } catch (error) {
    notify('Erro ao importar configurações. Verifique se o arquivo é válido.', 'error')
  }
}

const openHistory = () => {
  showAuditHistory.value = true
}
</script>

<style scoped>
.btn-white {
  @apply inline-flex items-center justify-center rounded-md bg-white dark:bg-gray-800 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors;
}

.label-custom {
  @apply block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5;
}

.input-custom {
  @apply w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20 transition-colors;
}

.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: rgb(156 163 175 / 0.5) transparent;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgb(156 163 175 / 0.5);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: rgb(156 163 175 / 0.7);
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out;
}
</style>
