<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Backups do Sistema</h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {{ hasBackups ? `${backups.length} backups • ${totalBackupSize}` : 'Nenhum backup disponível' }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button @click="handleSettings" class="btn-secondary">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.25 3.75a.75.75 0 011.5 0v1.129a6.001 6.001 0 014.122 2.249l.788-.455a.75.75 0 11.75 1.3l-.787.455a5.973 5.973 0 010 3l.787.455a.75.75 0 11-.75 1.3l-.788-.455a6.001 6.001 0 01-4.122 2.249v1.129a.75.75 0 11-1.5 0v-1.129a6.001 6.001 0 01-4.122-2.249l-.788.455a.75.75 0 11-.75-1.3l.787-.455a5.973 5.973 0 010-3l-.787-.455a.75.75 0 11.75-1.3l.788.455a6.001 6.001 0 014.122-2.249V3.75zM12 9a3 3 0 100 6 3 3 0 000-6z" />
          </svg>
          Configurar Servicos
        </button>
        <button @click="handleCreateBackup" :disabled="creating" class="btn-primary">
          <svg v-if="creating" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <svg v-else class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Criar Backup
        </button>
      </div>
    </div>

    <!-- Backup List -->
    <div v-if="hasBackups" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h4 class="text-base font-semibold text-gray-900 dark:text-white">Backups Disponíveis</h4>
      </div>

      <div class="divide-y divide-gray-200 dark:divide-gray-700">
        <div 
          v-for="backup in backups" 
          :key="backup.id"
          class="px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
        >
          <div class="flex items-center justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-3">
                <svg class="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"/>
                </svg>
                <div>
                  <p class="text-sm font-medium text-gray-900 dark:text-white">{{ backup.filename }}</p>
                  <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {{ formatDate(backup.created_at) }} • {{ formatSize(backup.size) }}
                    <span v-if="backup.cloud_uploaded" class="ml-2 text-green-600 dark:text-green-400">
                      ☁️ Enviado para nuvem
                    </span>
                  </p>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2 ml-4">
              <a 
                :href="backup.download_url" 
                download
                class="btn-icon"
                title="Download"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                </svg>
              </a>

              <button 
                v-if="!backup.cloud_uploaded"
                @click="handleUploadToCloud(backup)" 
                :disabled="uploading[backup.id]"
                class="btn-icon"
                title="Enviar para Nuvem"
              >
                <svg v-if="uploading[backup.id]" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                </svg>
              </button>

              <button 
                @click="handleRestore(backup)" 
                :disabled="restoring[backup.id]"
                class="btn-icon"
                title="Restaurar"
              >
                <svg v-if="restoring[backup.id]" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
              </button>

              <button 
                @click="handleDelete(backup)" 
                class="btn-icon text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                title="Excluir"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-700">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/>
      </svg>
      <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">Nenhum backup criado ainda</p>
      <button @click="handleCreateBackup" class="mt-4 btn-primary">
        Criar Primeiro Backup
      </button>
    </div>

    <!-- Upload File -->
    <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 p-4">
      <h4 class="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2">Restaurar de Arquivo</h4>
      <p class="text-xs text-blue-700 dark:text-blue-400 mb-3">Faça upload de um arquivo de backup (.zip) para restaurar</p>
      <input 
        type="file" 
        accept=".zip"
        @change="handleFileUpload"
        ref="fileInput"
        class="block w-full text-sm text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 rounded-md cursor-pointer bg-white dark:bg-gray-700 focus:outline-none"
      />
    </div>

    <BackupServiceSettingsModal
      v-if="showSettingsModal"
      :open="showSettingsModal"
      :seed-config="seedConfig"
      :initial-backup-settings="settings"
      :save-backup-settings-fn="saveBackupSettingsFromModal"
      @close="handleSettingsClosed"
      @saved="handleSettingsSaved"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useBackupConfig } from '@/composables/useBackupConfig'
import { useSystemConfig } from '@/composables/useSystemConfig'
import BackupServiceSettingsModal from './BackupServiceSettingsModal.vue'

// Composable
const {
  backups,
  loading,
  hasBackups,
  totalBackupSize,
  oldestBackup,
  newestBackup,
  loadBackups,
  createBackup,
  restoreBackup,
  deleteBackup,
  uploadBackupToCloud,
  uploadBackupFile,
  saveBackupSettings,
  formatSize,
  formatDate,
} = useBackupConfig()

const {
  configForm: systemConfigForm,
  loadSystemConfig,
} = useSystemConfig()

// Local state
const creating = ref(false)
const uploading = ref({})
const restoring = ref({})
const fileInput = ref(null)
const showSettingsModal = ref(false)
const seedConfig = ref(null)

const settings = reactive({
  auto_backup: false,
  frequency: 'weekly',
  retention_days: 30,
  cloud_upload: false,
  cloud_provider: 'google_drive',
  cloud_path: '/backups/provemaps',
})

const applySystemConfigToSettings = (config) => {
  if (!config) {
    return
  }

  const ftpEnabled = Boolean(config.FTP_ENABLED)
  const gdriveEnabled = Boolean(config.GDRIVE_ENABLED)
  const availableProviders = []

  if (gdriveEnabled) {
    availableProviders.push('google_drive')
  }
  if (ftpEnabled) {
    availableProviders.push('ftp')
  }

  if (availableProviders.length && !availableProviders.includes(settings.cloud_provider)) {
    settings.cloud_provider = availableProviders[0]
  }

  if (ftpEnabled && settings.cloud_provider === 'ftp' && config.FTP_PATH) {
    settings.cloud_path = config.FTP_PATH
  }
}

watch(
  () => systemConfigForm.value,
  (config) => {
    applySystemConfigToSettings(config)
  },
  { immediate: true, deep: true }
)

const hasCloudProvider = computed(() => {
  const config = systemConfigForm.value || {}
  const ftpEnabled = Boolean(config.FTP_ENABLED)
  const gdriveEnabled = Boolean(config.GDRIVE_ENABLED)
  const result = ftpEnabled || gdriveEnabled
  console.log('[BackupsTab] hasCloudProvider computed:', { 
    ftpEnabled, 
    gdriveEnabled, 
    result,
    FTP_ENABLED: config.FTP_ENABLED,
    GDRIVE_ENABLED: config.GDRIVE_ENABLED,
    configKeys: Object.keys(config)
  })
  return result
})

// Methods
const handleCreateBackup = async () => {
  creating.value = true
  try {
    const success = await createBackup()
    if (success && settings.cloud_upload && hasCloudProvider.value) {
      // Auto-upload to cloud if enabled
      const latestBackup = backups.value[0]
      if (latestBackup) {
        await handleUploadToCloud(latestBackup)
      }
    }
  } finally {
    creating.value = false
  }
}

const handleUploadToCloud = async (backup) => {
  uploading.value[backup.id] = true
  try {
    await uploadBackupToCloud(backup.id)
  } finally {
    uploading.value[backup.id] = false
  }
}

const handleRestore = async (backup) => {
  if (confirm(`Restaurar backup "${backup.filename}"? Esta ação substituirá os dados atuais.`)) {
    restoring.value[backup.id] = true
    try {
      await restoreBackup(backup.id)
    } finally {
      restoring.value[backup.id] = false
    }
  }
}

const handleDelete = async (backup) => {
  if (confirm(`Excluir backup "${backup.filename}"? Esta ação não pode ser desfeita.`)) {
    await deleteBackup(backup.id)
  }
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (file) {
    if (confirm(`Restaurar do arquivo "${file.name}"? Esta ação substituirá os dados atuais.`)) {
      await uploadBackupFile(file)
      // Reset file input
      if (fileInput.value) {
        fileInput.value.value = ''
      }
    }
  }
}

const handleSettings = async () => {
  try {
    await loadSystemConfig()
  } catch (error) {
    console.error('[BackupsTab] Failed to load system config:', error)
  }
  const snapshot = systemConfigForm.value ? JSON.parse(JSON.stringify(systemConfigForm.value)) : {}
  seedConfig.value = snapshot
  showSettingsModal.value = true
}

const saveBackupSettingsFromModal = async (nextSettings) => {
  console.log('[BackupsTab] Saving backup settings:', nextSettings)
  Object.assign(settings, nextSettings)
  console.log('[BackupsTab] Settings after assign:', settings)
  const result = await saveBackupSettings(settings)
  console.log('[BackupsTab] Save result:', result)
  return result
}

const handleSettingsSaved = async (payload) => {
  if (payload && payload.backupSettings) {
    Object.assign(settings, payload.backupSettings)
  }
  try {
    await loadSystemConfig()
    await loadBackups()
  } catch (error) {
    console.error('[BackupsTab] Failed to refresh after save:', error)
  }
}

const handleSettingsClosed = () => {
  showSettingsModal.value = false
  seedConfig.value = null
}

// Lifecycle
onMounted(async () => {
  await Promise.all([
    loadBackups(),
    loadSystemConfig().catch((error) => {
      console.error('[BackupsTab] Initial system config load failed:', error)
    }),
  ])
  
  // Load backup automation settings from system config
  if (systemConfigForm.value) {
    const config = systemConfigForm.value
    console.log('[BackupsTab] Loading backup settings from config:', {
      BACKUP_AUTO_ENABLED: config.BACKUP_AUTO_ENABLED,
      BACKUP_FREQUENCY: config.BACKUP_FREQUENCY,
      BACKUP_RETENTION_DAYS: config.BACKUP_RETENTION_DAYS,
      BACKUP_CLOUD_UPLOAD: config.BACKUP_CLOUD_UPLOAD,
      BACKUP_CLOUD_PROVIDER: config.BACKUP_CLOUD_PROVIDER,
      BACKUP_CLOUD_PATH: config.BACKUP_CLOUD_PATH,
    })
    
    if (config.BACKUP_AUTO_ENABLED !== undefined) {
      const autoBackup = Boolean(config.BACKUP_AUTO_ENABLED)
      console.log('[BackupsTab] Setting auto_backup to:', autoBackup)
      settings.auto_backup = autoBackup
    }
    if (config.BACKUP_FREQUENCY) {
      settings.frequency = config.BACKUP_FREQUENCY
    }
    if (config.BACKUP_RETENTION_DAYS) {
      const retention = Number(config.BACKUP_RETENTION_DAYS)
      if (Number.isFinite(retention) && retention > 0) {
        settings.retention_days = retention
      }
    }
    if (config.BACKUP_CLOUD_UPLOAD !== undefined) {
      const cloudUpload = Boolean(config.BACKUP_CLOUD_UPLOAD)
      console.log('[BackupsTab] Setting cloud_upload to:', cloudUpload)
      settings.cloud_upload = cloudUpload
    }
    if (config.BACKUP_CLOUD_PROVIDER) {
      settings.cloud_provider = config.BACKUP_CLOUD_PROVIDER
    }
    if (config.BACKUP_CLOUD_PATH) {
      settings.cloud_path = config.BACKUP_CLOUD_PATH
    }
    
    console.log('[BackupsTab] Final settings state:', settings)
  }
})
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
  @apply inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}

.btn-icon {
  @apply p-2 rounded-md text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed;
}
</style>
