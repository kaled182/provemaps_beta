/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useBackupConfig } from '../useBackupConfig'
import { useApi } from '../useApi'
import { useNotification } from '../useNotification'

vi.mock('../useApi')
vi.mock('../useNotification')

describe('useBackupConfig', () => {
  let mockApi
  let mockNotify

  beforeEach(() => {
    mockApi = {
      get: vi.fn(),
      post: vi.fn(),
      postFormData: vi.fn(),
    }
    mockNotify = {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
    }
    
    vi.mocked(useApi).mockReturnValue(mockApi)
    vi.mocked(useNotification).mockReturnValue(mockNotify)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initialization', () => {
    it('should initialize with empty backups', () => {
      const { backups, hasBackups, backupSettings } = useBackupConfig()
      
      expect(backups.value).toEqual([])
      expect(hasBackups.value).toBe(false)
      expect(backupSettings.value.retention_days).toBe(7)
      expect(backupSettings.value.retention_count).toBe(10)
    })
  })

  describe('loadBackups', () => {
    it('should load backups and settings', async () => {
      const mockBackups = [
        { name: 'backup_2026-01-27.zip', size: 1024000, created_at: '2026-01-27T10:00:00Z' },
        { name: 'backup_2026-01-26.zip', size: 2048000, created_at: '2026-01-26T10:00:00Z' },
      ]

      mockApi.get.mockResolvedValueOnce({
        success: true,
        backups: mockBackups,
        settings: {
          retention_days: 14,
          retention_count: 20,
        },
      })

      const { loadBackups, backups, backupSettings } = useBackupConfig()
      
      await loadBackups()

      expect(mockApi.get).toHaveBeenCalledWith('/setup_app/api/backups/')
      expect(backups.value).toEqual(mockBackups)
      expect(backupSettings.value.retention_days).toBe(14)
      expect(backupSettings.value.retention_count).toBe(20)
    })

    it('should handle load failure', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Network error'))

      const { loadBackups } = useBackupConfig()
      
      await loadBackups()

      // Should not throw, just log error
      expect(true).toBe(true)
    })
  })

  describe('createBackup', () => {
    it('should create backup successfully', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Backup iniciado!',
      })

      mockApi.get.mockResolvedValueOnce({ success: true, backups: [] })

      const { createBackup } = useBackupConfig()
      
      const result = await createBackup()

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/backups/', {})
      expect(mockNotify.success).toHaveBeenCalledWith('Backups', 'Backup iniciado!')
      expect(result).toBeDefined()
    })

    it('should handle Google Drive upload notification', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Backup iniciado!',
        gdrive_upload: {
          success: true,
          message: 'Enviado para Google Drive',
        },
      })

      mockApi.get.mockResolvedValueOnce({ success: true, backups: [] })

      const { createBackup } = useBackupConfig()
      
      await createBackup()

      expect(mockNotify.success).toHaveBeenCalledWith('Google Drive', 'Enviado para Google Drive')
    })

    it('should handle FTP upload notification', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Backup iniciado!',
        ftp_upload: {
          success: true,
          message: 'Enviado para FTP',
        },
      })

      mockApi.get.mockResolvedValueOnce({ success: true, backups: [] })

      const { createBackup } = useBackupConfig()
      
      await createBackup()

      expect(mockNotify.success).toHaveBeenCalledWith('FTP', 'Enviado para FTP')
    })
  })

  describe('restoreBackup', () => {
    it('should restore backup successfully', async () => {
      const backup = { name: 'backup_2026-01-27.zip' }

      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Restauração iniciada',
      })

      // Mock window.confirm
      global.window.confirm = vi.fn().mockReturnValue(true)

      const { restoreBackup } = useBackupConfig()
      
      const result = await restoreBackup(backup)

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/backups/restore/', {
        filename: 'backup_2026-01-27.zip',
      })
      expect(mockNotify.success).toHaveBeenCalled()
      expect(result).toBe(true)
    })

    it('should handle user cancellation', async () => {
      const backup = { name: 'backup_2026-01-27.zip' }

      global.window.confirm = vi.fn().mockReturnValue(false)

      const { restoreBackup } = useBackupConfig()
      
      const result = await restoreBackup(backup)

      expect(mockApi.post).not.toHaveBeenCalled()
      expect(result).toBe(false)
    })

    it('should accept filename string', async () => {
      mockApi.post.mockResolvedValueOnce({ success: true })
      global.window.confirm = vi.fn().mockReturnValue(true)

      const { restoreBackup } = useBackupConfig()
      
      await restoreBackup('backup.zip')

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/backups/restore/', {
        filename: 'backup.zip',
      })
    })
  })

  describe('deleteBackup', () => {
    it('should delete backup successfully', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Removido',
      })

      mockApi.get.mockResolvedValueOnce({ success: true, backups: [] })

      global.window.confirm = vi.fn().mockReturnValue(true)

      const { deleteBackup } = useBackupConfig()
      
      const result = await deleteBackup('backup.zip')

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/backups/delete/', {
        filename: 'backup.zip',
      })
      expect(mockNotify.success).toHaveBeenCalled()
      expect(result).toBe(true)
    })
  })

  describe('uploadBackupToCloud', () => {
    it('should upload backup to cloud successfully', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Envio iniciado',
        gdrive_upload: { success: true, message: 'Google Drive OK' },
        ftp_upload: { success: true, message: 'FTP OK' },
      })

      const { uploadBackupToCloud } = useBackupConfig()
      
      const result = await uploadBackupToCloud('backup.zip')

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/backups/upload-cloud/', {
        filename: 'backup.zip',
      })
      expect(mockNotify.success).toHaveBeenCalledWith('Backups', 'Envio iniciado')
      expect(mockNotify.success).toHaveBeenCalledWith('Google Drive', 'Google Drive OK')
      expect(mockNotify.success).toHaveBeenCalledWith('FTP', 'FTP OK')
      expect(result).toBeDefined()
    })
  })

  describe('saveBackupSettings', () => {
    it('should save backup settings successfully', async () => {
      mockApi.post.mockResolvedValueOnce({ success: true, message: 'Retenção salva' })
      mockApi.get.mockResolvedValueOnce({ success: true, backups: [] })

      const { saveBackupSettings, backupSettings } = useBackupConfig()
      
      const settings = { retention_days: 30, retention_count: 15 }
      const result = await saveBackupSettings(settings)

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/backups/settings/', settings)
      expect(mockNotify.success).toHaveBeenCalled()
      expect(backupSettings.value).toEqual(settings)
      expect(result).toBe(true)
    })
  })

  describe('uploadBackupFile', () => {
    it('should upload external backup file', async () => {
      const file = new File(['content'], 'backup.zip', { type: 'application/zip' })

      mockApi.postFormData.mockResolvedValueOnce({
        success: true,
        message: 'Upload OK!',
      })

      mockApi.get.mockResolvedValueOnce({ success: true, backups: [] })

      const { uploadBackupFile } = useBackupConfig()
      
      const result = await uploadBackupFile(file)

      expect(mockApi.postFormData).toHaveBeenCalled()
      expect(mockNotify.success).toHaveBeenCalledWith('Backups', 'Upload OK!')
      expect(result).toBe(true)
    })

    it('should handle missing file', async () => {
      const { uploadBackupFile } = useBackupConfig()
      
      const result = await uploadBackupFile(null)

      expect(mockNotify.warning).toHaveBeenCalledWith('Backups', 'Nenhum arquivo selecionado.')
      expect(result).toBe(false)
    })
  })

  describe('Computed Properties', () => {
    it('should calculate total backup size', async () => {
      mockApi.get.mockResolvedValueOnce({
        success: true,
        backups: [
          { name: 'backup1.zip', size: 1000 },
          { name: 'backup2.zip', size: 2000 },
          { name: 'backup3.zip', size: 3000 },
        ],
      })

      const { loadBackups, totalBackupSize } = useBackupConfig()
      
      await loadBackups()

      expect(totalBackupSize.value).toBe(6000)
    })

    it('should find oldest and newest backups', async () => {
      mockApi.get.mockResolvedValueOnce({
        success: true,
        backups: [
          { name: 'backup1.zip', created_at: '2026-01-25T10:00:00Z' },
          { name: 'backup2.zip', created_at: '2026-01-27T10:00:00Z' },
          { name: 'backup3.zip', created_at: '2026-01-26T10:00:00Z' },
        ],
      })

      const { loadBackups, oldestBackup, newestBackup } = useBackupConfig()
      
      await loadBackups()

      expect(oldestBackup.value.name).toBe('backup1.zip')
      expect(newestBackup.value.name).toBe('backup2.zip')
    })
  })

  describe('Utility Methods', () => {
    it('should format file size correctly', () => {
      const { formatSize } = useBackupConfig()
      
      expect(formatSize(0)).toBe('0 B')
      expect(formatSize(1024)).toBe('1 KB')
      expect(formatSize(1048576)).toBe('1 MB')
      expect(formatSize(1073741824)).toBe('1 GB')
    })

    it('should format date correctly', () => {
      const { formatDate } = useBackupConfig()
      
      const formatted = formatDate('2026-01-27T10:00:00Z')
      expect(formatted).toContain('27/01/2026')
    })

    it('should get backup by filename', async () => {
      mockApi.get.mockResolvedValueOnce({
        success: true,
        backups: [
          { name: 'backup1.zip' },
          { name: 'backup2.zip' },
        ],
      })

      const { loadBackups, getBackupByFilename } = useBackupConfig()
      
      await loadBackups()

      const backup = getBackupByFilename('backup1.zip')
      expect(backup.name).toBe('backup1.zip')
    })
  })
})
