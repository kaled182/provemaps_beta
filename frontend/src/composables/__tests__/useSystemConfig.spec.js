/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useSystemConfig } from '../useSystemConfig'
import { useApi } from '../useApi'
import { useNotification } from '../useNotification'

vi.mock('../useApi')
vi.mock('../useNotification')

describe('useSystemConfig', () => {
  let mockApi
  let mockNotify

  beforeEach(() => {
    mockApi = {
      get: vi.fn(),
      post: vi.fn(),
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
    it('should initialize with default state', () => {
      const { loading, error, config, hasConfig } = useSystemConfig()
      
      expect(loading.value).toBe(false)
      expect(error.value).toBeNull()
      expect(config.value).toEqual({})
      expect(hasConfig.value).toBe(false)
    })
  })

  describe('loadSystemConfig', () => {
    it('should load system configuration successfully', async () => {
      const mockConfig = {
        REDIS_URL: 'redis://localhost:6379',
        DB_HOST: 'localhost',
        DB_PORT: '5432',
        DEBUG: true,
      }

      mockApi.get.mockResolvedValueOnce({
        success: true,
        configuration: mockConfig,
      })

      const { loadSystemConfig, config, loading, error } = useSystemConfig()
      
      await loadSystemConfig()

      expect(mockApi.get).toHaveBeenCalledWith('/setup_app/api/config/')
      expect(config.value).toEqual(mockConfig)
      expect(loading.value).toBe(false)
      expect(error.value).toBeNull()
    })

    it('should handle load failure gracefully', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Network error'))

      const { loadSystemConfig, error, loading } = useSystemConfig()
      
      await loadSystemConfig()

      expect(error.value).toBe('Network error')
      expect(loading.value).toBe(false)
    })

    it('should set loading state during load', async () => {
      mockApi.get.mockImplementationOnce(() => new Promise(resolve => setTimeout(resolve, 100)))

      const { loadSystemConfig, loading } = useSystemConfig()
      
      const promise = loadSystemConfig()
      expect(loading.value).toBe(true)
      
      await promise
      expect(loading.value).toBe(false)
    })
  })

  describe('saveSystemConfig', () => {
    it('should save system configuration successfully', async () => {
      const configToSave = {
        REDIS_URL: 'redis://localhost:6379',
        DB_HOST: 'localhost',
      }

      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Configurações salvas!',
      })

      const { saveSystemConfig, config } = useSystemConfig()
      config.value = configToSave
      
      const result = await saveSystemConfig()

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/config/update/', configToSave)
      expect(mockNotify.success).toHaveBeenCalledWith('Configurações', 'Configurações salvas!')
      expect(result).toBe(true)
    })

    it('should handle save failure', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: false,
        message: 'Erro ao salvar',
      })

      const { saveSystemConfig } = useSystemConfig()
      
      const result = await saveSystemConfig()

      expect(mockNotify.error).toHaveBeenCalledWith('Configurações', 'Erro ao salvar')
      expect(result).toBe(false)
    })

    it('should handle network error during save', async () => {
      mockApi.post.mockRejectedValueOnce(new Error('Network error'))

      const { saveSystemConfig } = useSystemConfig()
      
      const result = await saveSystemConfig()

      expect(mockNotify.error).toHaveBeenCalled()
      expect(result).toBe(false)
    })
  })

  describe('testRedis', () => {
    it('should test Redis connection successfully', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Conexão OK!',
      })

      const { testRedis, config, testResults } = useSystemConfig()
      config.value.REDIS_URL = 'redis://localhost:6379'
      
      const result = await testRedis()

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/test-redis/', {
        redis_url: 'redis://localhost:6379',
      })
      expect(mockNotify.success).toHaveBeenCalledWith('Redis', 'Conexão OK!')
      expect(testResults.value.redis).toEqual({ success: true, message: 'Conexão OK!' })
      expect(result).toBe(true)
    })

    it('should handle Redis test failure', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: false,
        message: 'Falha na conexão',
      })

      const { testRedis, config, testResults } = useSystemConfig()
      config.value.REDIS_URL = 'redis://invalid:6379'
      
      const result = await testRedis()

      expect(mockNotify.error).toHaveBeenCalledWith('Redis', 'Falha na conexão')
      expect(testResults.value.redis).toEqual({ success: false, message: 'Falha na conexão' })
      expect(result).toBe(false)
    })
  })

  describe('testDatabase', () => {
    it('should test database connection successfully', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Banco conectado!',
      })

      const { testDatabase, config } = useSystemConfig()
      config.value = {
        DB_HOST: 'localhost',
        DB_PORT: '5432',
        DB_NAME: 'testdb',
        DB_USER: 'user',
        DB_PASSWORD: 'pass',
      }
      
      const result = await testDatabase()

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/test-database/', {
        db_host: 'localhost',
        db_port: '5432',
        db_name: 'testdb',
        db_user: 'user',
        db_password: 'pass',
      })
      expect(mockNotify.success).toHaveBeenCalledWith('Banco de Dados', 'Banco conectado!')
      expect(result).toBe(true)
    })

    it('should handle database test failure', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: false,
        message: 'Credenciais inválidas',
      })

      const { testDatabase, config } = useSystemConfig()
      config.value = {
        DB_HOST: 'localhost',
        DB_PORT: '5432',
        DB_NAME: 'testdb',
        DB_USER: 'wrong',
        DB_PASSWORD: 'wrong',
      }
      
      const result = await testDatabase()

      expect(mockNotify.error).toHaveBeenCalledWith('Banco de Dados', 'Credenciais inválidas')
      expect(result).toBe(false)
    })
  })

  describe('Computed Properties', () => {
    it('should compute hasConfig correctly', () => {
      const { config, hasConfig } = useSystemConfig()
      
      expect(hasConfig.value).toBe(false)
      
      config.value = { REDIS_URL: 'redis://localhost:6379' }
      expect(hasConfig.value).toBe(true)
    })

    it('should compute isValid correctly', () => {
      const { config, isValid } = useSystemConfig()
      
      expect(isValid.value).toBe(false)
      
      config.value = {
        REDIS_URL: 'redis://localhost:6379',
        DB_HOST: 'localhost',
        DB_PORT: '5432',
      }
      expect(isValid.value).toBe(true)
    })
  })

  describe('clearTestResults', () => {
    it('should clear all test results', async () => {
      const { testRedis, testDatabase, clearTestResults, testResults, config } = useSystemConfig()
      
      config.value = {
        REDIS_URL: 'redis://localhost:6379',
        DB_HOST: 'localhost',
        DB_PORT: '5432',
        DB_NAME: 'test',
        DB_USER: 'user',
        DB_PASSWORD: 'pass',
      }

      mockApi.post.mockResolvedValue({ success: true, message: 'OK' })
      
      await testRedis()
      await testDatabase()
      
      expect(testResults.value.redis).toBeDefined()
      expect(testResults.value.database).toBeDefined()
      
      clearTestResults()
      
      expect(testResults.value).toEqual({})
    })
  })

  describe('resetForm', () => {
    it('should reset config to empty object', () => {
      const { config, resetForm } = useSystemConfig()
      
      config.value = {
        REDIS_URL: 'redis://localhost:6379',
        DB_HOST: 'localhost',
      }
      
      resetForm()
      
      expect(config.value).toEqual({})
    })

    it('should preserve default values if provided', () => {
      const { config, resetForm } = useSystemConfig()
      
      config.value = {
        REDIS_URL: 'redis://localhost:6379',
        DB_HOST: 'localhost',
      }
      
      const defaults = {
        REDIS_URL: 'redis://default:6379',
        DEBUG: false,
      }
      
      resetForm(defaults)
      
      expect(config.value).toEqual(defaults)
    })
  })
})
