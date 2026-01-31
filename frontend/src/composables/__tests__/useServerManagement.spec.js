/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useServerManagement } from '../useServerManagement'
import { useApi } from '../useApi'
import { useNotification } from '../useNotification'

vi.mock('../useApi')
vi.mock('../useNotification')

describe('useServerManagement', () => {
  let mockApi
  let mockNotify

  beforeEach(() => {
    mockApi = {
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
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
    it('should initialize with empty servers', () => {
      const { servers, hasServers } = useServerManagement()
      
      expect(servers.value).toEqual([])
      expect(hasServers.value).toBe(false)
    })
  })

  describe('loadServers', () => {
    it('should load servers successfully', async () => {
      const mockServers = [
        { id: 1, name: 'Zabbix Primary', server_type: 'zabbix', url: 'http://zabbix.local', is_active: true },
        { id: 2, name: 'Prometheus', server_type: 'prometheus', url: 'http://prom.local', is_active: true },
      ]

      mockApi.get.mockResolvedValueOnce({
        success: true,
        servers: mockServers,
      })

      const { loadServers, servers } = useServerManagement()
      
      await loadServers()

      expect(mockApi.get).toHaveBeenCalledWith('/setup_app/api/monitoring-servers/')
      expect(servers.value).toEqual(mockServers)
    })

    it('should handle load failure', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Network error'))

      const { loadServers } = useServerManagement()
      
      await loadServers()

      // Should not throw
      expect(true).toBe(true)
    })
  })

  describe('saveServer', () => {
    it('should create new server', async () => {
      const newServer = {
        name: 'Zabbix Secondary',
        server_type: 'zabbix',
        url: 'http://zabbix2.local',
        auth_token: 'token123',
        is_active: true,
        extra_config: {},
      }

      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Criado!',
        server: { id: 1, ...newServer },
      })

      mockApi.get.mockResolvedValueOnce({ success: true, servers: [] })

      const { saveServer } = useServerManagement()
      
      const result = await saveServer(newServer)

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/monitoring-servers/', expect.objectContaining({
        name: 'Zabbix Secondary',
        server_type: 'zabbix',
      }))
      expect(mockNotify.success).toHaveBeenCalledWith('Servidores', 'Criado!')
      expect(result).toBeDefined()
    })

    it('should update existing server', async () => {
      const existingServer = {
        id: 1,
        name: 'Zabbix Primary Updated',
        server_type: 'zabbix',
        url: 'http://zabbix.local',
        auth_token: 'newtoken',
        is_active: true,
        extra_config: {},
      }

      mockApi.patch.mockResolvedValueOnce({
        success: true,
        message: 'Atualizado!',
        server: existingServer,
      })

      mockApi.get.mockResolvedValueOnce({ success: true, servers: [] })

      const { saveServer } = useServerManagement()
      
      const result = await saveServer(existingServer)

      expect(mockApi.patch).toHaveBeenCalledWith('/setup_app/api/monitoring-servers/1/', expect.any(Object))
      expect(mockNotify.success).toHaveBeenCalledWith('Servidores', 'Atualizado!')
      expect(result).toBeDefined()
    })

    it('should parse extra_config_text from JSON string', async () => {
      const server = {
        name: 'Test Server',
        server_type: 'zabbix',
        url: 'http://test.local',
        auth_token: 'token',
        is_active: true,
        extra_config_text: '{"key": "value"}',
      }

      mockApi.post.mockResolvedValueOnce({ success: true, message: 'Criado!' })
      mockApi.get.mockResolvedValueOnce({ success: true, servers: [] })

      const { saveServer } = useServerManagement()
      
      await saveServer(server)

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/monitoring-servers/', expect.objectContaining({
        extra_config: { key: 'value' },
      }))
    })

    it('should handle invalid JSON in extra_config', async () => {
      const server = {
        name: 'Test Server',
        server_type: 'zabbix',
        url: 'http://test.local',
        extra_config_text: 'invalid json',
      }

      const { saveServer } = useServerManagement()
      
      const result = await saveServer(server)

      expect(mockNotify.error).toHaveBeenCalledWith('Servidores', 'JSON inválido.')
      expect(result).toBeNull()
    })
  })

  describe('deleteServer', () => {
    it('should delete server successfully', async () => {
      mockApi.delete.mockResolvedValueOnce({
        success: true,
        message: 'Removido',
      })

      mockApi.get.mockResolvedValueOnce({ success: true, servers: [] })

      global.window.confirm = vi.fn().mockReturnValue(true)

      const { deleteServer } = useServerManagement()
      
      const result = await deleteServer(1)

      expect(mockApi.delete).toHaveBeenCalledWith('/setup_app/api/monitoring-servers/1/')
      expect(mockNotify.success).toHaveBeenCalled()
      expect(result).toBe(true)
    })

    it('should handle user cancellation', async () => {
      global.window.confirm = vi.fn().mockReturnValue(false)

      const { deleteServer } = useServerManagement()
      
      const result = await deleteServer(1)

      expect(mockApi.delete).not.toHaveBeenCalled()
      expect(result).toBe(false)
    })
  })

  describe('testServerConnection', () => {
    it('should test server connection successfully', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Conexão bem-sucedida!',
      })

      const { testServerConnection } = useServerManagement()
      
      const serverData = {
        server_type: 'zabbix',
        url: 'http://zabbix.local',
        auth_token: 'token',
        extra_config: {},
      }
      
      const result = await testServerConnection(serverData)

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/monitoring-servers/test/', expect.any(Object))
      expect(mockNotify.success).toHaveBeenCalled()
      expect(result.success).toBe(true)
    })

    it('should handle test failure', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: false,
        message: 'Falha na conexão',
      })

      const { testServerConnection } = useServerManagement()
      
      const result = await testServerConnection({ server_type: 'zabbix', url: 'http://test.local' })

      expect(mockNotify.error).toHaveBeenCalled()
      expect(result).toBeNull()
    })
  })

  describe('toggleServerStatus', () => {
    it('should toggle server active status', async () => {
      const mockServers = [
        { id: 1, name: 'Server 1', server_type: 'zabbix', url: 'http://test.local', is_active: true },
      ]

      mockApi.get.mockResolvedValueOnce({ success: true, servers: mockServers })
      mockApi.patch.mockResolvedValueOnce({ success: true, message: 'Atualizado!' })
      mockApi.get.mockResolvedValueOnce({ success: true, servers: [] })

      const { loadServers, toggleServerStatus } = useServerManagement()
      
      await loadServers()
      await toggleServerStatus(1, false)

      expect(mockApi.patch).toHaveBeenCalledWith('/setup_app/api/monitoring-servers/1/', expect.objectContaining({
        is_active: false,
      }))
    })
  })

  describe('Computed Properties', () => {
    it('should filter active and inactive servers', async () => {
      const mockServers = [
        { id: 1, name: 'Server 1', is_active: true },
        { id: 2, name: 'Server 2', is_active: false },
        { id: 3, name: 'Server 3', is_active: true },
      ]

      mockApi.get.mockResolvedValueOnce({ success: true, servers: mockServers })

      const { loadServers, activeServers, inactiveServers, serverCount } = useServerManagement()
      
      await loadServers()

      expect(activeServers.value).toHaveLength(2)
      expect(inactiveServers.value).toHaveLength(1)
      expect(serverCount.value.active).toBe(2)
      expect(serverCount.value.inactive).toBe(1)
      expect(serverCount.value.total).toBe(3)
    })

    it('should group servers by type', async () => {
      const mockServers = [
        { id: 1, name: 'Zabbix 1', server_type: 'zabbix' },
        { id: 2, name: 'Zabbix 2', server_type: 'zabbix' },
        { id: 3, name: 'Prometheus', server_type: 'prometheus' },
      ]

      mockApi.get.mockResolvedValueOnce({ success: true, servers: mockServers })

      const { loadServers, serversByType } = useServerManagement()
      
      await loadServers()

      expect(serversByType.value.zabbix).toHaveLength(2)
      expect(serversByType.value.prometheus).toHaveLength(1)
    })
  })

  describe('Utility Methods', () => {
    it('should get server by ID', async () => {
      const mockServers = [
        { id: 1, name: 'Server 1' },
        { id: 2, name: 'Server 2' },
      ]

      mockApi.get.mockResolvedValueOnce({ success: true, servers: mockServers })

      const { loadServers, getServerById } = useServerManagement()
      
      await loadServers()

      const server = getServerById(1)
      expect(server.name).toBe('Server 1')
    })

    it('should get servers by type', async () => {
      const mockServers = [
        { id: 1, name: 'Zabbix 1', server_type: 'zabbix' },
        { id: 2, name: 'Zabbix 2', server_type: 'zabbix' },
        { id: 3, name: 'Prometheus', server_type: 'prometheus' },
      ]

      mockApi.get.mockResolvedValueOnce({ success: true, servers: mockServers })

      const { loadServers, getServersByType } = useServerManagement()
      
      await loadServers()

      const zabbixServers = getServersByType('zabbix')
      expect(zabbixServers).toHaveLength(2)
    })

    it('should validate extra_config JSON', () => {
      const { validateExtraConfig } = useServerManagement()
      
      const valid = validateExtraConfig('{"key": "value"}')
      expect(valid.valid).toBe(true)
      expect(valid.parsed).toEqual({ key: 'value' })

      const invalid = validateExtraConfig('invalid json')
      expect(invalid.valid).toBe(false)
      expect(invalid.error).toBeDefined()
    })

    it('should convert server to form object', () => {
      const { serverToForm } = useServerManagement()
      
      const server = {
        id: 1,
        name: 'Zabbix',
        server_type: 'zabbix',
        url: 'http://zabbix.local',
        is_active: true,
        extra_config: { timeout: 30 },
      }
      
      const form = serverToForm(server)
      
      expect(form.id).toBe(1)
      expect(form.name).toBe('Zabbix')
      expect(form.auth_token).toBe('') // Security: don't fill token
      expect(form.extra_config_text).toBe('{\n  "timeout": 30\n}')
    })

    it('should create empty server form', () => {
      const { createEmptyServerForm } = useServerManagement()
      
      const form = createEmptyServerForm()
      
      expect(form.name).toBe('')
      expect(form.server_type).toBe('zabbix')
      expect(form.is_active).toBe(true)
      expect(form.extra_config_text).toBe('{}')
    })
  })
})
