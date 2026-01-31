/**
 * Composable para gerenciamento de configurações do sistema
 * 
 * Responsabilidades:
 * - Carregar e salvar configurações gerais do sistema
 * - Testar conexões (Redis, Database)
 * - Gerenciar parâmetros de debug, hosts permitidos, etc
 * 
 * @module useSystemConfig
 */

import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

/**
 * Composable para configurações do sistema
 * @returns {Object} Objetos e funções para gerenciar configurações do sistema
 */
export function useSystemConfig() {
  const api = useApi()
  const notify = useNotification()

  // Estado
  const loading = ref(false)
  const error = ref(null)
  
  const configForm = ref({
    SECRET_KEY: '',
    DEBUG: false,
    ALLOWED_HOSTS: '',
    ENABLE_DIAGNOSTIC_ENDPOINTS: false,
    // Database
    DB_HOST: '',
    DB_PORT: '',
    DB_NAME: '',
    DB_USER: '',
    DB_PASSWORD: '',
    // Redis
    REDIS_URL: '',
    // Services
    SERVICE_RESTART_COMMANDS: '',
    // Backups / Cloud
    BACKUP_ZIP_PASSWORD: '',
    BACKUP_AUTO_ENABLED: false,
    BACKUP_FREQUENCY: 'weekly',
    BACKUP_RETENTION_DAYS: '30',
    BACKUP_CLOUD_UPLOAD: false,
    BACKUP_CLOUD_PROVIDER: 'google_drive',
    BACKUP_CLOUD_PATH: '/backups/provemaps',
    FTP_ENABLED: false,
    FTP_HOST: '',
    FTP_PORT: '21',
    FTP_USER: '',
    FTP_PASSWORD: '',
    FTP_PATH: '/backups/',
    GDRIVE_ENABLED: false,
    GDRIVE_AUTH_MODE: 'service_account',
    GDRIVE_CREDENTIALS_JSON: '',
    GDRIVE_FOLDER_ID: '',
    GDRIVE_SHARED_DRIVE_ID: '',
    GDRIVE_OAUTH_CLIENT_ID: '',
    GDRIVE_OAUTH_CLIENT_SECRET: '',
    GDRIVE_OAUTH_CONNECTED: false,
    GDRIVE_OAUTH_USER_EMAIL: '',
    // Zabbix
    ZABBIX_API_URL: '',
    ZABBIX_API_USER: '',
    ZABBIX_API_PASSWORD: '',
    ZABBIX_API_KEY: '',
    // Maps - General
    MAP_PROVIDER: 'google',
    // Maps - Google Maps
    GOOGLE_MAPS_API_KEY: '',
    MAP_DEFAULT_ZOOM: '12',
    MAP_DEFAULT_LAT: '-15.7801',
    MAP_DEFAULT_LNG: '-47.9292',
    MAP_TYPE: 'terrain',  // terrain é mais claro e sem linhas de grid
    MAP_STYLES: '',
    ENABLE_STREET_VIEW: true,
    ENABLE_TRAFFIC: false,
    // Maps - Mapbox
    MAPBOX_TOKEN: '',
    MAPBOX_STYLE: 'mapbox://styles/mapbox/streets-v12',
    MAPBOX_CUSTOM_STYLE: '',
    MAPBOX_ENABLE_3D: false,
    // Maps - Esri
    ESRI_API_KEY: '',
    ESRI_BASEMAP: 'streets',
    // Maps - Common
    MAP_LANGUAGE: 'pt-BR',
    MAP_THEME: 'light',
    ENABLE_MAP_CLUSTERING: true,
    ENABLE_DRAWING_TOOLS: true,
    ENABLE_FULLSCREEN: true,
  })

  // Estados de teste
  const testingRedis = ref(false)
  const testingDatabase = ref(false)
  const testingZabbix = ref(false)
  const redisTestResult = ref(null)
  const databaseTestResult = ref(null)
  const zabbixTestResult = ref(null)

  // Computed
  const hasConfig = computed(() => {
    return !!(configForm.value.DB_HOST || configForm.value.REDIS_URL)
  })

  const isValid = computed(() => {
    // Validação básica: pelo menos DB ou Redis configurado
    const hasDatabase = !!(
      configForm.value.DB_HOST &&
      configForm.value.DB_PORT &&
      configForm.value.DB_NAME &&
      configForm.value.DB_USER
    )
    const hasRedis = !!configForm.value.REDIS_URL
    
    return hasDatabase || hasRedis
  })

  // Métodos

  /**
   * Carrega configurações do sistema da API
   * @returns {Promise<void>}
   */
  const loadSystemConfig = async () => {
    try {
      loading.value = true
      error.value = null
      
      console.log('[useSystemConfig] Loading system config from API...')
      const res = await api.get('/setup_app/api/config/')
      console.log('[useSystemConfig] API response:', res)
      
      if (res.success && res.configuration) {
        console.log('[useSystemConfig] Configuration received:', res.configuration)
        // Atualizar apenas os campos relevantes ao sistema
        const systemFields = [
          'SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS', 'ENABLE_DIAGNOSTIC_ENDPOINTS',
          'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
          'REDIS_URL', 'SERVICE_RESTART_COMMANDS',
          'BACKUP_ZIP_PASSWORD',
          'BACKUP_AUTO_ENABLED', 'BACKUP_FREQUENCY', 'BACKUP_RETENTION_DAYS',
          'BACKUP_CLOUD_UPLOAD', 'BACKUP_CLOUD_PROVIDER', 'BACKUP_CLOUD_PATH',
          'FTP_ENABLED', 'FTP_HOST', 'FTP_PORT', 'FTP_USER', 'FTP_PASSWORD', 'FTP_PATH',
          'GDRIVE_ENABLED', 'GDRIVE_AUTH_MODE', 'GDRIVE_CREDENTIALS_JSON', 'GDRIVE_FOLDER_ID',
          'GDRIVE_SHARED_DRIVE_ID', 'GDRIVE_OAUTH_CLIENT_ID', 'GDRIVE_OAUTH_CLIENT_SECRET',
          'GDRIVE_OAUTH_CONNECTED', 'GDRIVE_OAUTH_USER_EMAIL',
          'ZABBIX_API_URL', 'ZABBIX_API_USER', 'ZABBIX_API_PASSWORD', 'ZABBIX_API_KEY',
          // Maps configuration
          'MAP_PROVIDER', 'GOOGLE_MAPS_API_KEY', 'MAPBOX_TOKEN',
          'MAP_DEFAULT_ZOOM', 'MAP_DEFAULT_LAT', 'MAP_DEFAULT_LNG',
          'MAP_TYPE', 'MAP_STYLES', 'ENABLE_STREET_VIEW', 'ENABLE_TRAFFIC',
          'MAPBOX_STYLE', 'MAPBOX_CUSTOM_STYLE', 'MAPBOX_ENABLE_3D',
          'ESRI_API_KEY', 'ESRI_BASEMAP',
          'MAP_LANGUAGE', 'MAP_THEME', 'ENABLE_MAP_CLUSTERING', 'ENABLE_DRAWING_TOOLS', 'ENABLE_FULLSCREEN'
        ]
        
        const booleanFields = new Set([
          'DEBUG',
          'ENABLE_DIAGNOSTIC_ENDPOINTS',
          'FTP_ENABLED',
          'GDRIVE_ENABLED',
          'GDRIVE_OAUTH_CONNECTED',
          'BACKUP_AUTO_ENABLED',
          'BACKUP_CLOUD_UPLOAD',
          'ENABLE_STREET_VIEW',
          'ENABLE_TRAFFIC',
          'MAPBOX_ENABLE_3D',
          'ENABLE_MAP_CLUSTERING',
          'ENABLE_DRAWING_TOOLS',
          'ENABLE_FULLSCREEN',
        ])

        systemFields.forEach(field => {
          if (res.configuration[field] === undefined) {
            return
          }
          const rawValue = res.configuration[field]
          if (booleanFields.has(field)) {
            if (typeof rawValue === 'boolean') {
              configForm.value[field] = rawValue
            } else if (rawValue === null || rawValue === undefined) {
              configForm.value[field] = false
            } else {
              configForm.value[field] = String(rawValue).trim().toLowerCase() === 'true'
            }
          } else {
            configForm.value[field] = rawValue
          }
        })
        console.log('[useSystemConfig] Config form updated:', configForm.value)
      } else {
        console.warn('[useSystemConfig] Invalid response format:', res)
      }
    } catch (e) {
      error.value = e.message || 'Erro ao carregar configurações'
      console.error('[useSystemConfig] Error loading config:', e)
    } finally {
      loading.value = false
    }
  }

  /**
   * Salva configurações do sistema
   * @returns {Promise<boolean>} true se salvou com sucesso
   */
  const saveSystemConfig = async () => {
    try {
      loading.value = true
      error.value = null
      
      const res = await api.post('/setup_app/api/config/update/', configForm.value)
      
      if (res.success) {
        notify.success('Configurações', res.message || 'Configurações salvas!')
        if (res.restart_triggered) {
          notify.info('Serviços', 'Comandos de reinício foram disparados. Aguarde a aplicação aplicar as mudanças.')
        }

        await loadSystemConfig()
        return true
      }

      notify.error('Configurações', res.message || 'Erro ao salvar configurações.')
      return false
    } catch (e) {
      error.value = e.message || 'Erro ao salvar configurações'
      notify.error('Configurações', e.message || 'Erro ao salvar.')
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Testa conexão com Redis
   * @returns {Promise<boolean>} true se conectou com sucesso
   */
  const testRedis = async () => {
    try {
      testingRedis.value = true
      redisTestResult.value = null
      
      const payload = {
        redis_url: configForm.value.REDIS_URL
      }
      
      const res = await api.post('/setup_app/api/test-redis/', payload)
      
      if (res.success) {
        notify.success('Redis', res.message || 'Conexão bem-sucedida!')
        redisTestResult.value = { success: true, message: res.message }
        return true
      } else {
        notify.error('Redis', res.message || 'Erro na conexão')
        redisTestResult.value = { success: false, message: res.message }
        return false
      }
    } catch (e) {
      const message = e.message || 'Erro ao testar Redis.'
      notify.error('Redis', message)
      redisTestResult.value = { success: false, message }
      return false
    } finally {
      testingRedis.value = false
    }
  }

  /**
   * Testa conexão com banco de dados
   * @returns {Promise<boolean>} true se conectou com sucesso
   */
  const testDatabase = async () => {
    try {
      testingDatabase.value = true
      databaseTestResult.value = null
      
      const payload = {
        db_host: configForm.value.DB_HOST,
        db_port: configForm.value.DB_PORT,
        db_name: configForm.value.DB_NAME,
        db_user: configForm.value.DB_USER,
        db_password: configForm.value.DB_PASSWORD,
      }
      
      const res = await api.post('/setup_app/api/test-database/', payload)
      
      if (res.success) {
        notify.success('Banco de Dados', res.message || 'Conexão bem-sucedida!')
        databaseTestResult.value = { success: true, message: res.message }
        return true
      } else {
        notify.error('Banco de Dados', res.message || 'Erro na conexão')
        databaseTestResult.value = { success: false, message: res.message }
        return false
      }
    } catch (e) {
      const message = e.message || 'Erro ao testar banco.'
      notify.error('Banco de Dados', message)
      databaseTestResult.value = { success: false, message }
      return false
    } finally {
      testingDatabase.value = false
    }
  }

  /**
   * Limpa estado de testes
   */
  const clearTestResults = () => {
    redisTestResult.value = null
    databaseTestResult.value = null
    zabbixTestResult.value = null
  }

  /**
   * Reseta formulário para valores padrão
   */
  const resetForm = () => {
    configForm.value = {
      SECRET_KEY: '',
      DEBUG: false,
      ALLOWED_HOSTS: '',
      ENABLE_DIAGNOSTIC_ENDPOINTS: false,
      DB_HOST: '',
      DB_PORT: '',
      DB_NAME: '',
      DB_USER: '',
      DB_PASSWORD: '',
      REDIS_URL: '',
      SERVICE_RESTART_COMMANDS: '',
      BACKUP_ZIP_PASSWORD: '',
      FTP_ENABLED: false,
      FTP_HOST: '',
      FTP_PORT: '21',
      FTP_USER: '',
      FTP_PASSWORD: '',
      FTP_PATH: '/backups/',
      GDRIVE_ENABLED: false,
      GDRIVE_AUTH_MODE: 'service_account',
      GDRIVE_CREDENTIALS_JSON: '',
      GDRIVE_FOLDER_ID: '',
      GDRIVE_SHARED_DRIVE_ID: '',
      GDRIVE_OAUTH_CLIENT_ID: '',
      GDRIVE_OAUTH_CLIENT_SECRET: '',
      GDRIVE_OAUTH_CONNECTED: false,
      GDRIVE_OAUTH_USER_EMAIL: '',
      ZABBIX_API_URL: '',
      ZABBIX_API_USER: '',
      ZABBIX_API_PASSWORD: '',
      ZABBIX_API_KEY: '',
    }
    clearTestResults()
  }

  /**
   * Testa conexão com Zabbix utilizando credenciais fornecidas
   * @param {Object} override Valores opcionais para sobrescrever o formulário atual
   * @returns {Promise<Object|boolean>} Resultado da API ou false quando falhar antes da requisição
   */
  const testZabbix = async (override = {}) => {
    const rawUrl = override.zabbix_api_url ?? configForm.value.ZABBIX_API_URL ?? ''
    const rawUsername = override.zabbix_api_user ?? configForm.value.ZABBIX_API_USER ?? ''
    const rawPassword = override.zabbix_api_password ?? configForm.value.ZABBIX_API_PASSWORD ?? ''
    const rawApiKey = override.zabbix_api_key ?? configForm.value.ZABBIX_API_KEY ?? ''

    const url = String(rawUrl || '').trim()
    const username = String(rawUsername || '')
    const password = String(rawPassword || '')
    const apiKey = String(rawApiKey || '')
    const authType = override.auth_type || (apiKey ? 'token' : 'login')

    if (!url) {
      notify.error('Zabbix', 'Informe a URL do serviço para testar.')
      zabbixTestResult.value = { success: false, message: 'URL do Zabbix não informada.' }
      return false
    }

    const payload = {
      zabbix_api_url: url,
      zabbix_api_user: username,
      zabbix_api_password: password,
      zabbix_api_key: apiKey,
      auth_type: authType,
    }

    try {
      testingZabbix.value = true
      zabbixTestResult.value = null

      const res = await api.post('/setup_app/api/test-zabbix/', payload)

      if (res.success) {
        const message = res.message || 'Conexão com Zabbix bem-sucedida.'
        notify.success('Zabbix', message)
        zabbixTestResult.value = { success: true, message, version: res.version || null }
      } else {
        const message = res.message || 'Falha ao testar o Zabbix.'
        notify.error('Zabbix', message)
        zabbixTestResult.value = { success: false, message, status: res.status }
      }

      return res
    } catch (e) {
      const message = e.message || 'Erro ao testar o Zabbix.'
      notify.error('Zabbix', message)
      zabbixTestResult.value = { success: false, message }
      return false
    } finally {
      testingZabbix.value = false
    }
  }

  // Retorno do composable
  return {
    // Estado
    loading,
    error,
    config: configForm, // Alias para compatibilidade
    configForm,
    testingRedis,
    testingDatabase,
    testingZabbix,
    testResults: computed(() => ({
      redis: redisTestResult.value,
      database: databaseTestResult.value,
      zabbix: zabbixTestResult.value,
    })),
    
    // Computed
    hasConfig,
    isValid,
    
    // Métodos
    loadSystemConfig,
    saveSystemConfig,
    testRedis,
    testDatabase,
    testZabbix,
    clearTestResults,
    resetForm,
  }
}
