<template>
  <BaseModal
    :show="open"
    title="Serviços de backup"
    subtitle="Envio automático para a nuvem, integrações e criptografia"
    :icon="PhCloudArrowUp"
    size="detail"
    @close="handleClose"
  >
    <section class="section-block">
      <div class="section-header">
        <button type="button" class="collapse-trigger" @click="toggleSection('scheduler')">
          <svg class="collapse-icon" :class="{ 'is-collapsed': !sectionsOpen.scheduler }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 9l6 6 6-6" />
          </svg>
          <span>Rotina de Backup</span>
        </button>
        <p v-if="sectionsOpen.scheduler">Configure criacao automatica e envio padrao dos backups do sistema.</p>
      </div>

      <div v-if="sectionsOpen.scheduler" class="space-y-5">
        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <label class="field-label">Backup Automatico</label>
            <p class="hint-text">Criar backups automaticamente em horarios programados.</p>
          </div>
          <label class="toggle">
            <input type="checkbox" v-model="backupForm.auto_backup" />
            <span>Habilitar</span>
          </label>
        </div>

        <div v-if="backupForm.auto_backup" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="field-label">Frequencia</label>
            <select v-model="backupForm.frequency" class="field-input">
              <option value="daily">Diario</option>
              <option value="weekly">Semanal</option>
              <option value="monthly">Mensal</option>
            </select>
          </div>
          <div>
            <label class="field-label">Retencao (dias)</label>
            <input v-model.number="backupForm.retention_days" type="number" min="1" max="365" class="field-input" />
          </div>
        </div>

        <div class="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <label class="field-label">Upload para Nuvem</label>
            <p class="hint-text">Enviar backups automaticamente para um provedor padrao.</p>
          </div>
          <label class="toggle">
            <input type="checkbox" v-model="backupForm.cloud_upload" />
            <span>Habilitar</span>
          </label>
        </div>

        <div v-if="backupForm.cloud_upload" class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="field-label">Provedor</label>
            <select v-model="backupForm.cloud_provider" class="field-input">
              <option value="google_drive">Google Drive</option>
              <option value="dropbox">Dropbox</option>
              <option value="ftp">FTP/SFTP</option>
              <option value="s3">Amazon S3</option>
            </select>
          </div>
          <div>
            <label class="field-label">Caminho/Pasta</label>
            <input v-model="backupForm.cloud_path" type="text" class="field-input" placeholder="/backups/provemaps" />
          </div>
        </div>
      </div>
    </section>

    <section class="section-block">
          <div class="section-header">
            <button type="button" class="collapse-trigger" @click="toggleSection('encryption')">
              <svg class="collapse-icon" :class="{ 'is-collapsed': !sectionsOpen.encryption }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 9l6 6 6-6" />
              </svg>
              <span>Criptografia de Backups</span>
            </button>
            <p v-if="sectionsOpen.encryption">Defina uma senha para proteger os arquivos ZIP gerados.</p>
          </div>
            <div v-if="sectionsOpen.encryption" class="grid grid-cols-1 gap-3">
        <label class="field-label">Senha do arquivo (.zip)</label>
        <input
          v-model="form.backupPassword"
          type="password"
          class="field-input"
          placeholder="Minimo de 8 caracteres"
          autocomplete="off"
        />
        <p class="hint-text">A senha sera usada ao restaurar backups protegidos.</p>
      </div>
    </section>

    <section class="section-block">
      <div class="section-header">
        <button type="button" class="collapse-trigger" @click="toggleSection('gdrive')">
          <svg class="collapse-icon" :class="{ 'is-collapsed': !sectionsOpen.gdrive }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 9l6 6 6-6" />
          </svg>
          <span>Google Drive</span>
        </button>
        <div v-if="sectionsOpen.gdrive" class="section-actions">
          <label class="toggle">
            <input type="checkbox" v-model="form.gdrive.enabled" />
            <span>Habilitar upload automatico</span>
          </label>
          <button class="secondary-button" @click="handleTestGdrive" :disabled="testingGdrive || !form.gdrive.enabled">
            <svg v-if="testingGdrive" class="spinner" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.37 0 0 5.37 0 12h4zm2 5.29A7.96 7.96 0 014 12H0c0 3.04 1.14 5.82 3 7.94l3-2.65z" />
            </svg>
            <span v-else>Testar conexao</span>
          </button>
        </div>
      </div>

      <div v-if="sectionsOpen.gdrive" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="field-label">Modo de autenticacao</label>
          <select v-model="form.gdrive.authMode" class="field-input">
            <option value="service_account">Service Account</option>
            <option value="oauth">OAuth</option>
          </select>
        </div>
        <div>
          <label class="field-label">ID da Pasta</label>
          <input v-model="form.gdrive.folderId" class="field-input" placeholder="ID da pasta de destino" autocomplete="off" />
        </div>
        <div>
          <label class="field-label">ID do Drive Compartilhado</label>
          <input v-model="form.gdrive.sharedDriveId" class="field-input" placeholder="Opcional" autocomplete="off" />
        </div>
        <div v-if="form.gdrive.authMode === 'service_account'" class="md:col-span-2">
          <label class="field-label">Credenciais (JSON)</label>
          <textarea v-model="form.gdrive.credentialsJson" class="field-input h-32" placeholder="Cole o JSON da service account"></textarea>
        </div>
        <template v-else>
          <div>
            <label class="field-label">Client ID</label>
            <input v-model="form.gdrive.oauthClientId" class="field-input" autocomplete="off" />
          </div>
          <div>
            <label class="field-label">Client Secret</label>
            <input v-model="form.gdrive.oauthClientSecret" class="field-input" autocomplete="off" />
          </div>
          <div class="md:col-span-2">
            <p class="hint-text" v-if="form.gdrive.oauthUserEmail">
              Conta autorizada: <strong>{{ form.gdrive.oauthUserEmail }}</strong>
            </p>
            <p class="hint-text" v-else>
              Conclua o fluxo OAuth na interface antiga para registrar o refresh token.
            </p>
          </div>
        </template>
      </div>
    </section>

    <section class="section-block">
      <div class="section-header">
        <button type="button" class="collapse-trigger" @click="toggleSection('ftp')">
          <svg class="collapse-icon" :class="{ 'is-collapsed': !sectionsOpen.ftp }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 9l6 6 6-6" />
          </svg>
          <span>FTP / SFTP</span>
        </button>
        <div v-if="sectionsOpen.ftp" class="section-actions">
          <label class="toggle">
            <input type="checkbox" v-model="form.ftp.enabled" />
            <span>Habilitar upload automatico</span>
          </label>
          <button class="secondary-button" @click="handleTestFtp" :disabled="testingFtp || !form.ftp.enabled">
            <svg v-if="testingFtp" class="spinner" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.37 0 0 5.37 0 12h4zm2 5.29A7.96 7.96 0 014 12H0c0 3.04 1.14 5.82 3 7.94l3-2.65z" />
            </svg>
            <span v-else>Testar conexao</span>
          </button>
        </div>
      </div>

      <div v-if="sectionsOpen.ftp" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label class="field-label">Host</label>
          <input v-model="form.ftp.host" class="field-input" placeholder="ftp.seudominio.com" autocomplete="off" />
        </div>
        <div>
          <label class="field-label">Porta</label>
          <input v-model="form.ftp.port" class="field-input" placeholder="21" autocomplete="off" />
        </div>
        <div>
          <label class="field-label">Usuario</label>
          <input v-model="form.ftp.user" class="field-input" autocomplete="username" />
        </div>
        <div>
          <label class="field-label">Senha</label>
          <input v-model="form.ftp.password" type="password" class="field-input" autocomplete="current-password" />
        </div>
        <div class="md:col-span-2">
          <label class="field-label">Pasta de destino</label>
          <input v-model="form.ftp.path" class="field-input" placeholder="/backups/" autocomplete="off" />
        </div>
      </div>
    </section>

    <template #footer>
      <div class="flex items-center justify-end gap-2">
        <button class="secondary-button" @click="handleCancel">Cancelar</button>
        <button class="primary-button" @click="handleSave" :disabled="saving">
          <svg v-if="saving" class="spinner" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.37 0 0 5.37 0 12h4zm2 5.29A7.96 7.96 0 014 12H0c0 3.04 1.14 5.82 3 7.94l3-2.65z" />
          </svg>
          <span v-else>Salvar alteracoes</span>
        </button>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { watch, reactive } from 'vue'
import { PhCloudArrowUp } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { useBackupServiceSettings } from '@/composables/useBackupServiceSettings'

const props = defineProps({
  open: {
    type: Boolean,
    default: false,
  },
  seedConfig: {
    type: Object,
    default: null,
  },
  initialBackupSettings: {
    type: Object,
    default: () => ({}),
  },
  saveBackupSettingsFn: {
    type: Function,
    required: true,
  },
})

const emit = defineEmits(['close', 'saved'])

const {
  form,
  loading,
  saving,
  testingGdrive,
  testingFtp,
  loadSettings,
  resetForm,
  saveSettings,
  testGdrive,
  testFtp,
  applyExternalConfig,
} = useBackupServiceSettings()

const sectionsOpen = reactive({
  scheduler: false,
  encryption: false,
  gdrive: false,
  ftp: false,
})

const toggleSection = (section) => {
  sectionsOpen[section] = !sectionsOpen[section]
}

const resetSectionState = () => {
  sectionsOpen.scheduler = false
  sectionsOpen.encryption = false
  sectionsOpen.gdrive = false
  sectionsOpen.ftp = false
}

const backupDefaults = {
  auto_backup: false,
  frequency: 'weekly',
  retention_days: 30,
  cloud_upload: false,
  cloud_provider: 'google_drive',
  cloud_path: '/backups/provemaps',
}

const backupForm = reactive({ ...backupDefaults })

const applyBackupSettings = (payload = {}) => {
  backupForm.auto_backup = Boolean(payload.auto_backup)
  backupForm.frequency = payload.frequency || backupDefaults.frequency
  const parsedRetention = Number(payload.retention_days)
  backupForm.retention_days = Number.isFinite(parsedRetention) && parsedRetention > 0 ? parsedRetention : backupDefaults.retention_days
  backupForm.cloud_upload = Boolean(payload.cloud_upload)
  backupForm.cloud_provider = payload.cloud_provider || backupDefaults.cloud_provider
  backupForm.cloud_path = payload.cloud_path || backupDefaults.cloud_path
}

const resetBackupSettings = () => {
  applyBackupSettings(backupDefaults)
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      applyBackupSettings(props.initialBackupSettings)
      applyExternalConfig(props.seedConfig)
      loadSettings()
    } else {
      resetForm()
      resetSectionState()
      resetBackupSettings()
    }
  },
  { immediate: true }
)

watch(
  () => props.seedConfig,
  () => {
    if (props.open) {
      applyExternalConfig(props.seedConfig)
    }
  },
  { deep: false }
)

watch(
  () => props.initialBackupSettings,
  (newValue) => {
    if (props.open) {
      applyBackupSettings(newValue)
    }
  },
  { deep: true }
)

const handleClose = () => {
  emit('close')
}

const handleCancel = () => {
  resetForm()
  resetBackupSettings()
  emit('close')
}

const handleSave = async () => {
  const backupPayload = {
    auto_backup: backupForm.auto_backup,
    frequency: backupForm.frequency,
    retention_days: backupForm.retention_days,
    cloud_upload: backupForm.cloud_upload,
    cloud_provider: backupForm.cloud_provider,
    cloud_path: backupForm.cloud_path,
  }

  const backupSaved = await props.saveBackupSettingsFn(backupPayload)
  if (!backupSaved) {
    return
  }

  const result = await saveSettings()
  if (result) {
    emit('saved', {
      serviceSettings: result,
      backupSettings: backupPayload,
    })
    emit('close')
  }
}

const handleTestGdrive = async () => {
  await testGdrive()
}

const handleTestFtp = async () => {
  await testFtp()
}
</script>

<style scoped>

.section-block {
  background: rgb(var(--n-50));
  border: 1px solid rgb(var(--n-200));
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.collapse-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: none;
  color: inherit;
  font-size: 1rem;
  font-weight: 600;
  padding: 0;
  cursor: pointer;
}

.collapse-trigger:hover {
  color: rgb(var(--primary-600));
}

.collapse-icon {
  width: 18px;
  height: 18px;
  transition: transform 0.2s ease;
}

.collapse-icon.is-collapsed {
  transform: rotate(-90deg);
}

.section-header h4 {
  font-size: 1rem;
  font-weight: 600;
}

.section-header p {
  font-size: 0.875rem;
  color: var(--text-secondary, #cbd5f5);
}

.section-actions {
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
}

.field-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 6px;
}

.field-input {
  width: 100%;
  border-radius: 10px;
  border: 1px solid rgb(var(--n-300));
  background: rgb(var(--n-50));
  color: inherit;
  padding: 10px 12px;
  font-size: 0.9rem;
  transition: border 0.2s ease, box-shadow 0.2s ease;
}

.field-input:focus {
  outline: none;
  border-color: rgb(var(--primary-500) / 0.9);
  box-shadow: 0 0 0 3px rgb(var(--primary-500) / 0.2);
}

.hint-text {
  font-size: 0.75rem;
  color: var(--text-secondary, #cbd5f5);
}

.secondary-button,
.primary-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease;
}

.secondary-button {
  background: rgb(var(--n-100));
  color: inherit;
}

.secondary-button:hover {
  background: rgb(var(--n-200));
}

.primary-button {
  background: linear-gradient(135deg, rgb(var(--primary-600)), rgb(var(--primary-500)));
  color: #ffffff;
}

.primary-button:hover {
  background: rgb(var(--primary-600));
}

.primary-button:disabled,
.secondary-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.spinner {
  width: 18px;
  height: 18px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
