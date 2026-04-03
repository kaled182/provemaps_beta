/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useGatewayConfig } from '../useGatewayConfig'
import { useApi } from '../useApi'
import { useNotification } from '../useNotification'

vi.mock('../useApi')
vi.mock('../useNotification')

describe('useGatewayConfig', () => {
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
    it('should initialize with empty gateways', () => {
      const { gateways, hasGateways } = useGatewayConfig()
      
      expect(gateways.value).toEqual([])
      expect(hasGateways.value).toBe(false)
    })
  })

  describe('loadGateways', () => {
    it('should load gateways successfully', async () => {
      const mockGateways = [
        { id: 1, gateway_type: 'sms', name: 'SMS Gateway', enabled: true },
        { id: 2, gateway_type: 'whatsapp', name: 'WhatsApp', enabled: true },
      ]

      mockApi.get.mockResolvedValueOnce({
        success: true,
        gateways: mockGateways,
      })

      const { loadGateways, gateways } = useGatewayConfig()
      
      await loadGateways()

      expect(mockApi.get).toHaveBeenCalledWith('/setup_app/api/gateways/')
      expect(gateways.value).toEqual(mockGateways)
    })

    it('should handle load failure', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Network error'))

      const { loadGateways } = useGatewayConfig()
      
      await loadGateways()

      expect(mockNotify.error).toHaveBeenCalled()
    })
  })

  describe('saveGateway', () => {
    it('should create new gateway', async () => {
      const newGateway = {
        name: 'SMS Gateway',
        gateway_type: 'sms',
        provider: 'smsnet',
        priority: 1,
        enabled: true,
        config: { api_url: 'https://api.sms.com' },
      }

      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Gateway criado!',
        gateway: { id: 1, ...newGateway },
      })

      mockApi.get.mockResolvedValueOnce({ success: true, gateways: [] })

      const { saveGateway } = useGatewayConfig()
      
      const result = await saveGateway(newGateway)

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/gateways/', newGateway)
      expect(mockNotify.success).toHaveBeenCalledWith('Gateways', 'Gateway criado!')
      expect(result).toEqual({ id: 1, ...newGateway })
    })

    it('should update existing gateway', async () => {
      const existingGateway = {
        id: 1,
        name: 'SMS Gateway Updated',
        gateway_type: 'sms',
        provider: 'smsnet',
        priority: 1,
        enabled: true,
        config: {},
      }

      mockApi.patch.mockResolvedValueOnce({
        success: true,
        message: 'Gateway atualizado!',
        gateway: existingGateway,
      })

      mockApi.get.mockResolvedValueOnce({ success: true, gateways: [] })

      const { saveGateway } = useGatewayConfig()
      
      const result = await saveGateway(existingGateway)

      expect(mockApi.patch).toHaveBeenCalledWith('/setup_app/api/gateways/1/', existingGateway)
      expect(mockNotify.success).toHaveBeenCalledWith('Gateways', 'Gateway atualizado!')
      expect(result).toEqual(existingGateway)
    })
  })

  describe('deleteGateway', () => {
    it('should delete gateway successfully', async () => {
      mockApi.delete.mockResolvedValueOnce({
        success: true,
        message: 'Gateway removido',
      })

      mockApi.get.mockResolvedValueOnce({ success: true, gateways: [] })

      const { deleteGateway } = useGatewayConfig()
      
      const result = await deleteGateway(1)

      expect(mockApi.delete).toHaveBeenCalledWith('/setup_app/api/gateways/1/')
      expect(mockNotify.success).toHaveBeenCalledWith('Gateways', 'Gateway removido')
      expect(result).toBe(true)
    })

    it('should handle delete failure', async () => {
      mockApi.delete.mockResolvedValueOnce({
        success: false,
        message: 'Erro ao remover',
      })

      const { deleteGateway } = useGatewayConfig()
      
      const result = await deleteGateway(1)

      expect(mockNotify.error).toHaveBeenCalledWith('Gateways', 'Erro ao remover')
      expect(result).toBe(false)
    })
  })

  describe('testGateway', () => {
    it('should test SMS gateway successfully', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Teste bem-sucedido!',
      })

      const { testGateway } = useGatewayConfig()
      
      const config = {
        provider: 'smsnet',
        api_url: 'https://api.sms.com',
        username: 'user',
        password: 'pass',
      }
      
      const result = await testGateway('sms', config)

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/test-sms/', expect.objectContaining({
        provider: 'smsnet',
      }))
      expect(mockNotify.success).toHaveBeenCalled()
      expect(result).toBe(true)
    })

    it('should test SMTP gateway successfully', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Conexão SMTP OK!',
      })

      const { testGateway } = useGatewayConfig()
      
      const config = {
        host: 'smtp.gmail.com',
        port: '587',
        user: 'user@gmail.com',
        password: 'pass',
      }
      
      const result = await testGateway('smtp', config)

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/test-smtp/', expect.objectContaining({
        smtp_host: 'smtp.gmail.com',
      }))
      expect(result).toBe(true)
    })
  })

  describe('WhatsApp QR Management', () => {
    it('should generate WhatsApp QR code', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'QR gerado',
        qr_status: 'pending',
        qr_image_url: 'https://example.com/qr.png',
        qr_code: 'ABC123',
      })

      const { generateWhatsappQR } = useGatewayConfig()
      
      const result = await generateWhatsappQR(1, 'https://qr-service.com')

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/gateways/1/whatsapp/qr/', {
        qr_service_url: 'https://qr-service.com',
      })
      expect(mockNotify.success).toHaveBeenCalled()
      expect(result.qr_status).toBe('pending')
    })

    it('should check WhatsApp QR status', async () => {
      mockApi.get.mockResolvedValueOnce({
        success: true,
        qr_status: 'connected',
      })

      const { checkWhatsappQRStatus } = useGatewayConfig()
      
      const result = await checkWhatsappQRStatus(1, 'https://qr-service.com')

      expect(mockApi.get).toHaveBeenCalled()
      expect(result.qr_status).toBe('connected')
    })

    it('should disconnect WhatsApp QR session', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Desconectado',
      })

      const { disconnectWhatsappQR } = useGatewayConfig()
      
      const result = await disconnectWhatsappQR(1, 'https://qr-service.com')

      expect(mockNotify.success).toHaveBeenCalled()
      expect(result).toBe(true)
    })
  })

  describe('Computed Properties', () => {
    it('should filter gateways by type', async () => {
      const mockGateways = [
        { id: 1, gateway_type: 'sms', name: 'SMS 1' },
        { id: 2, gateway_type: 'sms', name: 'SMS 2' },
        { id: 3, gateway_type: 'whatsapp', name: 'WhatsApp' },
        { id: 4, gateway_type: 'smtp', name: 'SMTP' },
      ]

      mockApi.get.mockResolvedValueOnce({ success: true, gateways: mockGateways })

      const { loadGateways, smsGateways, whatsappGateways, smtpGateways, gatewayCount } = useGatewayConfig()
      
      await loadGateways()

      expect(smsGateways.value).toHaveLength(2)
      expect(whatsappGateways.value).toHaveLength(1)
      expect(smtpGateways.value).toHaveLength(1)
      expect(gatewayCount.value.sms).toBe(2)
      expect(gatewayCount.value.total).toBe(4)
    })
  })

  describe('Utility Methods', () => {
    it('should get gateway by ID', async () => {
      const mockGateways = [
        { id: 1, gateway_type: 'sms', name: 'SMS' },
        { id: 2, gateway_type: 'whatsapp', name: 'WhatsApp' },
      ]

      mockApi.get.mockResolvedValueOnce({ success: true, gateways: mockGateways })

      const { loadGateways, getGatewayById } = useGatewayConfig()
      
      await loadGateways()

      const gateway = getGatewayById(1)
      expect(gateway.name).toBe('SMS')
    })

    it('should get gateways by type', async () => {
      const mockGateways = [
        { id: 1, gateway_type: 'sms', name: 'SMS 1' },
        { id: 2, gateway_type: 'sms', name: 'SMS 2' },
        { id: 3, gateway_type: 'whatsapp', name: 'WhatsApp' },
      ]

      mockApi.get.mockResolvedValueOnce({ success: true, gateways: mockGateways })

      const { loadGateways, getGatewaysByType } = useGatewayConfig()
      
      await loadGateways()

      const smsGateways = getGatewaysByType('sms')
      expect(smsGateways).toHaveLength(2)
    })
  })
})
