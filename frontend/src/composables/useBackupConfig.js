/**
 * Composable para gerenciamento de backups do sistema
 * 
 * Responsabilidades:
 * - Listar backups disponíveis
 * - Criar novos backups (manual/automático)
 * - Restaurar backups
 * - Upload para cloud (Google Drive, FTP)
 * - Gerenciar configurações de retenção
 * - Upload de backups externos
 * 
 * @module useBackupConfig
 */

import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

/**
 * Composable para gerenciamento de backups
 * @returns {Object} Objetos e funções para gerenciar backups
 */
export function useBackupConfig() {
  const api = useApi()
  const notify = useNotification()

  // Estado
  const loading = ref(false)
  const backupLoading = ref(false)
  const error = ref(null)
  const backups = ref([])
  
  // Configurações de retenção
  const backupSettings = ref({
    retention_days: 7,
    retention_count: 10,
  })

  // Computed
  const hasBackups = computed(() => backups.value.length > 0)
  
  const totalBackupSize = computed(() => {
    return backups.value.reduce((sum, backup) => sum + (backup.size || 0), 0)
  })

  const oldestBackup = computed(() => {
    if (!backups.value.length) return null
    return backups.value.reduce((oldest, backup) => {
      const backupDate = new Date(backup.created_at || backup.date)
      const oldestDate = new Date(oldest.created_at || oldest.date)
      return backupDate < oldestDate ? backup : oldest
    })
  })

  const newestBackup = computed(() => {
    if (!backups.value.length) return null
    return backups.value.reduce((newest, backup) => {
      const backupDate = new Date(backup.created_at || backup.date)
      const newestDate = new Date(newest.created_at || newest.date)
      return backupDate > newestDate ? backup : newest
    })
  })

  // Métodos

  /**
   * Carrega lista de backups disponíveis
   * @returns {Promise<void>}
   */
  const loadBackups = async () => {
    try {
      loading.value = true
      error.value = null
      
      const res = await api.get('/setup_app/api/backups/')
      
      if (res.success !== false) {
        backups.value = res.backups || []
        
        // Atualiza settings se retornado
        if (res.settings) {
          backupSettings.value = {
            retention_days: res.settings.retention_days || 7,
            retention_count: res.settings.retention_count || 10,
          }
        }
      }
    } catch (e) {
      error.value = e.message || 'Erro ao carregar backups'
      console.error('[useBackupConfig] Error loading backups:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * Cria novo backup do sistema
   * @param {Object} options - Opções de criação
   * @param {boolean} options.uploadToCloud - Se deve fazer upload automático
   * @returns {Promise<Object|null>} Resultado da criação ou null
   */
  const createBackup = async (options = {}) => {
    try {
      backupLoading.value = true
      error.value = null
      
      const res = await api.post('/setup_app/api/backups/', {})
      
      if (res.success) {
        notify.success('Backups', 'Backup iniciado!')
        
        // Notificações de upload Google Drive
        if (res.gdrive_upload) {
          if (res.gdrive_upload.success) {
            notify.success('Google Drive', res.gdrive_upload.message || 'Backup enviado.')
          } else if (res.gdrive_upload.message) {
            notify.warning('Google Drive', res.gdrive_upload.message)
          }
        }
        
        // Notificações de upload FTP
        if (res.ftp_upload) {
          if (res.ftp_upload.success) {
            notify.success('FTP', res.ftp_upload.message || 'Backup enviado.')
          } else if (res.ftp_upload.message) {
            notify.warning('FTP', res.ftp_upload.message)
          }
        }
        
        // Recarrega lista após 2 segundos
        setTimeout(() => loadBackups(), 2000)
        
        return res
      } else {
        notify.error('Backups', res.message || 'Erro ao criar backup')
        return null
      }
    } catch (e) {
      error.value = e.message || 'Erro ao criar backup'
      notify.error('Backups', e.message || 'Erro ao criar backup')
      return null
    } finally {
      backupLoading.value = false
    }
  }

  /**
   * Restaura backup específico
   * @param {Object|string} backup - Objeto backup ou nome do arquivo
   * @param {boolean} confirm - Se deve confirmar antes de restaurar (padrão: true)
   * @returns {Promise<boolean>} true se restaurou com sucesso
   */
  const restoreBackup = async (backup, confirm = true) => {
    const filename = typeof backup === 'string' ? backup : backup.name
    
    if (confirm && !window.confirm(`Restaurar ${filename}?\n\nATENÇÃO: Esta operação irá sobrescrever os dados atuais!`)) {
      return false
    }
    
    try {
      loading.value = true
      error.value = null
      
      const res = await api.post('/setup_app/api/backups/restore/', { filename })
      
      if (res.success) {
        notify.success('Backups', res.message || 'Restauração iniciada.')
        return true
      } else {
        notify.error('Backups', res.message || 'Erro ao restaurar.')
        return false
      }
    } catch (e) {
      error.value = e.message || 'Erro ao restaurar backup'
      notify.error('Backups', e.message || 'Erro ao restaurar.')
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Deleta backup específico
   * @param {Object|string} backup - Objeto backup ou nome do arquivo
   * @param {boolean} confirm - Se deve confirmar antes de deletar (padrão: true)
   * @returns {Promise<boolean>} true se deletou com sucesso
   */
  const deleteBackup = async (backup, confirm = true) => {
    const filename = typeof backup === 'string' ? backup : backup.name
    
    if (confirm && !window.confirm(`Excluir ${filename}?`)) {
      return false
    }
    
    try {
      loading.value = true
      error.value = null
      
      const res = await api.post('/setup_app/api/backups/delete/', { filename })
      
      if (res.success) {
        notify.success('Backups', res.message || 'Removido.')
        await loadBackups()
        return true
      } else {
        notify.error('Backups', res.message || 'Erro ao excluir.')
        return false
      }
    } catch (e) {
      error.value = e.message || 'Erro ao deletar backup'
      notify.error('Backups', e.message || 'Erro ao excluir.')
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Faz upload de backup para cloud (Google Drive, FTP)
   * @param {Object|string} backup - Objeto backup ou nome do arquivo
   * @returns {Promise<Object|null>} Resultado do upload ou null
   */
  const uploadBackupToCloud = async (backup) => {
    const filename = typeof backup === 'string' ? backup : backup.name
    
    try {
      loading.value = true
      error.value = null
      
      const res = await api.post('/setup_app/api/backups/upload-cloud/', { filename })
      
      if (res.success) {
        notify.success('Backups', 'Envio iniciado.')
        
        // Notificações de upload Google Drive
        if (res.gdrive_upload) {
          if (res.gdrive_upload.success) {
            notify.success('Google Drive', res.gdrive_upload.message || 'Backup enviado.')
          } else if (res.gdrive_upload.message) {
            notify.warning('Google Drive', res.gdrive_upload.message)
          }
        }
        
        // Notificações de upload FTP
        if (res.ftp_upload) {
          if (res.ftp_upload.success) {
            notify.success('FTP', res.ftp_upload.message || 'Backup enviado.')
          } else if (res.ftp_upload.message) {
            notify.warning('FTP', res.ftp_upload.message)
          }
        }
        
        return res
      } else {
        notify.error('Backups', res.message || 'Falha no envio.')
        return null
      }
    } catch (e) {
      error.value = e.message || 'Erro ao enviar para cloud'
      notify.error('Backups', e.message || 'Erro ao enviar para nuvem.')
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Salva configurações de retenção
   * @param {Object} settings - Configurações de retenção
   * @param {number} settings.retention_days - Dias de retenção
   * @param {number} settings.retention_count - Quantidade de backups a manter
   * @returns {Promise<boolean>} true se salvou com sucesso
   */
  const saveBackupSettings = async (settings) => {
    try {
      loading.value = true
      error.value = null
      
      console.log('[useBackupConfig] Saving settings:', settings)
      
      const payload = {
        retention_days: settings?.retention_days ?? backupSettings.value.retention_days,
        retention_count: settings?.retention_count ?? backupSettings.value.retention_count,
        auto_backup: settings?.auto_backup ?? false,
        frequency: settings?.frequency ?? 'weekly',
        cloud_upload: settings?.cloud_upload ?? false,
        cloud_provider: settings?.cloud_provider ?? 'google_drive',
        cloud_path: settings?.cloud_path ?? '/backups/provemaps',
      }
      
      console.log('[useBackupConfig] Payload to send:', payload)
      
      const res = await api.post('/setup_app/api/backups/settings/', payload)
      
      console.log('[useBackupConfig] API response:', res)
      
      if (res.success !== false) {
        notify.success('Backups', res.message || 'Configurações salvas.')
        
        // Atualiza estado local
        backupSettings.value = payload
        
        // Recarrega backups para refletir mudanças
        await loadBackups()
        return true
      } else {
        notify.error('Backups', res.message || 'Erro ao salvar configurações.')
        return false
      }
    } catch (e) {
      error.value = e.message || 'Erro ao salvar configurações'
      notify.error('Backups', e.message || 'Erro ao salvar configurações.')
      console.error('[useBackupConfig] Error saving settings:', e)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Faz upload de arquivo de backup externo
   * @param {File} file - Arquivo de backup (.zip)
   * @returns {Promise<boolean>} true se upload foi bem-sucedido
   */
  const uploadBackupFile = async (file) => {
    if (!file) {
      notify.warning('Backups', 'Nenhum arquivo selecionado.')
      return false
    }
    
    try {
      loading.value = true
      error.value = null
      
      const formData = new FormData()
      formData.append('file', file)
      
      const res = await api.postFormData('/setup_app/api/backups/', formData)
      
      if (res.success) {
        notify.success('Backups', res.message || 'Upload OK!')
        await loadBackups()
        return true
      } else {
        notify.error('Backups', res.message || 'Erro upload.')
        return false
      }
    } catch (e) {
      error.value = e.message || 'Erro ao fazer upload'
      notify.error('Backups', e.message || 'Erro upload.')
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Busca backup por nome
   * @param {string} filename - Nome do arquivo
   * @returns {Object|null} Backup encontrado ou null
   */
  const getBackupByFilename = (filename) => {
    return backups.value.find(b => b.name === filename) || null
  }

  /**
   * Formata tamanho em bytes para formato legível
   * @param {number} bytes - Tamanho em bytes
   * @returns {string} Tamanho formatado (ex: "1.5 MB")
   */
  const formatSize = (bytes) => {
    if (!bytes) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  /**
   * Formata data ISO para formato brasileiro
   * @param {string} isoDate - Data no formato ISO
   * @returns {string} Data formatada (ex: "27/01/2026 14:30:45")
   */
  const formatDate = (isoDate) => {
    return isoDate ? new Date(isoDate).toLocaleString('pt-BR') : '-'
  }

  /**
   * Limpa erros
   */
  const clearError = () => {
    error.value = null
  }

  // Retorno do composable
  return {
    // Estado
    loading,
    backupLoading,
    error,
    backups,
    backupSettings,
    
    // Computed
    hasBackups,
    totalBackupSize,
    oldestBackup,
    newestBackup,
    
    // Métodos CRUD
    loadBackups,
    createBackup,
    restoreBackup,
    deleteBackup,
    uploadBackupToCloud,
    uploadBackupFile,
    saveBackupSettings,
    
    // Utilitários
    getBackupByFilename,
    formatSize,
    formatDate,
    clearError,
  }
}
