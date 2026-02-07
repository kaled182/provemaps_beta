/**
 * Composable para gerenciar configuracoes dos servicos de backup.
 * Inclui integracoes com Google Drive e FTP, alem da senha de criptografia.
 */
import { ref, reactive } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

export function useBackupServiceSettings() {
  const api = useApi()
  const notify = useNotification()

  const loading = ref(false)
  const saving = ref(false)
  const testingGdrive = ref(false)
  const testingFtp = ref(false)
  const configSnapshot = ref(null)

  const toBoolean = (value) => {
    if (typeof value === 'boolean') {
      return value
    }
    if (value === null || value === undefined) {
      return false
    }
    const normalized = String(value).trim().toLowerCase()
    if (!normalized) {
      return false
    }
    return ['1', 'true', 'yes', 'on'].includes(normalized)
  }

  const form = reactive({
    backupPassword: '',
    ftp: {
      enabled: false,
      host: '',
      port: '21',
      user: '',
      password: '',
      path: '/backups/',
    },
    gdrive: {
      enabled: false,
      authMode: 'service_account',
      credentialsJson: '',
      folderId: '',
      sharedDriveId: '',
      oauthClientId: '',
      oauthClientSecret: '',
      oauthUserEmail: '',
      oauthConnected: false,
    },
  })

  const applySnapshotToForm = () => {
    const config = configSnapshot.value || {}
    form.backupPassword = config.BACKUP_ZIP_PASSWORD || ''
    form.ftp.enabled = toBoolean(config.FTP_ENABLED)
    form.ftp.host = config.FTP_HOST || ''
    form.ftp.port = config.FTP_PORT || '21'
    form.ftp.user = config.FTP_USER || ''
    form.ftp.password = config.FTP_PASSWORD || ''
    form.ftp.path = config.FTP_PATH || '/backups/'

    form.gdrive.enabled = toBoolean(config.GDRIVE_ENABLED)
    form.gdrive.authMode = config.GDRIVE_AUTH_MODE || 'service_account'
    form.gdrive.credentialsJson = config.GDRIVE_CREDENTIALS_JSON || ''
    form.gdrive.folderId = config.GDRIVE_FOLDER_ID || ''
    form.gdrive.sharedDriveId = config.GDRIVE_SHARED_DRIVE_ID || ''
    form.gdrive.oauthClientId = config.GDRIVE_OAUTH_CLIENT_ID || ''
    form.gdrive.oauthClientSecret = config.GDRIVE_OAUTH_CLIENT_SECRET || ''
    form.gdrive.oauthUserEmail = config.GDRIVE_OAUTH_USER_EMAIL || ''
    form.gdrive.oauthConnected = toBoolean(config.GDRIVE_OAUTH_CONNECTED)
  }

  const applyExternalConfig = (payload = {}) => {
    if (!payload || typeof payload !== 'object') {
      return
    }
    configSnapshot.value = {
      ...(configSnapshot.value || {}),
      ...payload,
    }
    applySnapshotToForm()
  }

  const loadSettings = async () => {
    loading.value = true
    try {
      const res = await api.get('/setup_app/api/config/')
      if (res?.success && res.configuration) {
        configSnapshot.value = { ...res.configuration }
        applySnapshotToForm()
      } else {
        notify.error('Backups', res?.message || 'Falha ao carregar configuracoes.')
      }
    } catch (error) {
      console.error('[useBackupServiceSettings] loadSettings error:', error)
      notify.error('Backups', error.message || 'Erro ao carregar configuracoes.')
    } finally {
      loading.value = false
    }
  }

  const resetForm = () => {
    applySnapshotToForm()
  }

  const saveSettings = async () => {
    if (!configSnapshot.value) {
      await loadSettings()
      if (!configSnapshot.value) {
        return null
      }
    }

    saving.value = true
    try {
      const payload = { ...configSnapshot.value }
      payload.BACKUP_ZIP_PASSWORD = form.backupPassword || ''
      payload.FTP_ENABLED = Boolean(form.ftp.enabled)
      payload.FTP_HOST = form.ftp.host || ''
      payload.FTP_PORT = form.ftp.port || ''
      payload.FTP_USER = form.ftp.user || ''
      payload.FTP_PASSWORD = form.ftp.password || ''
      payload.FTP_PATH = form.ftp.path || ''
      payload.GDRIVE_ENABLED = Boolean(form.gdrive.enabled)
      payload.GDRIVE_AUTH_MODE = form.gdrive.authMode || 'service_account'
      payload.GDRIVE_CREDENTIALS_JSON = form.gdrive.credentialsJson || ''
      payload.GDRIVE_FOLDER_ID = form.gdrive.folderId || ''
      payload.GDRIVE_SHARED_DRIVE_ID = form.gdrive.sharedDriveId || ''
      payload.GDRIVE_OAUTH_CLIENT_ID = form.gdrive.oauthClientId || ''
      payload.GDRIVE_OAUTH_CLIENT_SECRET = form.gdrive.oauthClientSecret || ''
      // Keep refresh token and email values already stored when API omits them
      payload.GDRIVE_OAUTH_USER_EMAIL = form.gdrive.oauthUserEmail || payload.GDRIVE_OAUTH_USER_EMAIL || ''

      const res = await api.post('/setup_app/api/config/update/', payload)
      if (res?.success) {
        notify.success('Backups', res.message || 'Configuracoes salvas com sucesso.')
        configSnapshot.value = { ...payload }
        await loadSettings()
        return res
      }

      notify.error('Backups', res?.message || 'Falha ao salvar configuracoes.')
      return null
    } catch (error) {
      console.error('[useBackupServiceSettings] saveSettings error:', error)
      notify.error('Backups', error.message || 'Erro ao salvar configuracoes.')
      return null
    } finally {
      saving.value = false
    }
  }

  const testGdrive = async () => {
    testingGdrive.value = true
    try {
      const payload = {
        gdrive_auth_mode: form.gdrive.authMode,
        gdrive_credentials_json: form.gdrive.credentialsJson,
        gdrive_folder_id: form.gdrive.folderId,
        gdrive_shared_drive_id: form.gdrive.sharedDriveId,
        gdrive_oauth_client_id: form.gdrive.oauthClientId,
        gdrive_oauth_client_secret: form.gdrive.oauthClientSecret,
      }
      const res = await api.post('/setup_app/api/test-gdrive/', payload)
      if (res?.success) {
        notify.success('Google Drive', res.message || 'Conexao validada.')
        return true
      }
      notify.error('Google Drive', res?.message || 'Falha ao testar integracao.')
      return false
    } catch (error) {
      console.error('[useBackupServiceSettings] testGdrive error:', error)
      notify.error('Google Drive', error.message || 'Erro ao testar Google Drive.')
      return false
    } finally {
      testingGdrive.value = false
    }
  }

  const testFtp = async () => {
    testingFtp.value = true
    try {
      const payload = {
        ftp_host: form.ftp.host,
        ftp_port: form.ftp.port,
        ftp_user: form.ftp.user,
        ftp_password: form.ftp.password,
        ftp_path: form.ftp.path,
      }
      const res = await api.post('/setup_app/api/test-ftp/', payload)
      if (res?.success) {
        notify.success('FTP', res.message || 'Conexao validada.')
        return true
      }
      notify.error('FTP', res?.message || 'Falha ao testar FTP.')
      return false
    } catch (error) {
      console.error('[useBackupServiceSettings] testFtp error:', error)
      notify.error('FTP', error.message || 'Erro ao testar FTP.')
      return false
    } finally {
      testingFtp.value = false
    }
  }

  return {
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
  }
}
