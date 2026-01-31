/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useCameraConfig } from '../useCameraConfig'
import { useApi } from '../useApi'
import { useNotification } from '../useNotification'

vi.mock('../useApi')
vi.mock('../useNotification')

describe('useCameraConfig', () => {
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
    it('should initialize with default settings', () => {
      const { cameraSettings, hasPresets, cameraPresets } = useCameraConfig()
      
      expect(cameraSettings.value.default_stream_type).toBe('rtmp')
      expect(cameraSettings.value.default_resolution).toBe('1080p')
      expect(hasPresets.value).toBe(true)
      expect(cameraPresets.value.length).toBeGreaterThan(0)
    })

    it('should have camera presets for common manufacturers', () => {
      const { cameraPresets } = useCameraConfig()
      
      const presetNames = cameraPresets.value.map(p => p.manufacturer)
      expect(presetNames).toContain('Hikvision')
      expect(presetNames).toContain('Dahua')
      expect(presetNames).toContain('Intelbras')
      expect(presetNames).toContain('Axis Communications')
    })
  })

  describe('loadCameraSettings', () => {
    it('should load camera settings successfully', async () => {
      mockApi.get.mockResolvedValueOnce({
        success: true,
        settings: {
          default_stream_type: 'rtsp',
          default_resolution: '4k',
          max_concurrent_streams: 20,
        },
      })

      const { loadCameraSettings, cameraSettings } = useCameraConfig()
      
      await loadCameraSettings()

      expect(mockApi.get).toHaveBeenCalledWith('/setup_app/api/camera-settings/')
      expect(cameraSettings.value.default_stream_type).toBe('rtsp')
      expect(cameraSettings.value.default_resolution).toBe('4k')
      expect(cameraSettings.value.max_concurrent_streams).toBe(20)
    })

    it('should handle load failure', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Network error'))

      const { loadCameraSettings } = useCameraConfig()
      
      await loadCameraSettings()

      // Should not throw
      expect(true).toBe(true)
    })
  })

  describe('saveCameraSettings', () => {
    it('should save camera settings successfully', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Configurações salvas',
      })

      const { saveCameraSettings, cameraSettings } = useCameraConfig()
      
      cameraSettings.value.default_fps = 60
      const result = await saveCameraSettings()

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/camera-settings/', expect.objectContaining({
        default_fps: 60,
      }))
      expect(mockNotify.success).toHaveBeenCalled()
      expect(result).toBe(true)
    })
  })

  describe('validateStreamUrl', () => {
    it('should validate RTSP URLs', () => {
      const { validateStreamUrl } = useCameraConfig()
      
      const result = validateStreamUrl('rtsp://192.168.1.100:554/stream')
      expect(result.valid).toBe(true)
      expect(result.type).toBe('rtsp')
    })

    it('should validate RTMP URLs', () => {
      const { validateStreamUrl } = useCameraConfig()
      
      const result = validateStreamUrl('rtmp://192.168.1.100/live/stream')
      expect(result.valid).toBe(true)
      expect(result.type).toBe('rtmp')
    })

    it('should validate HLS URLs', () => {
      const { validateStreamUrl } = useCameraConfig()
      
      const result = validateStreamUrl('https://example.com/stream.m3u8')
      expect(result.valid).toBe(true)
      expect(result.type).toBe('hls')
    })

    it('should validate HTTP URLs', () => {
      const { validateStreamUrl } = useCameraConfig()
      
      const result = validateStreamUrl('http://example.com/stream')
      expect(result.valid).toBe(true)
      expect(result.type).toBe('http')
    })

    it('should validate WebRTC URLs', () => {
      const { validateStreamUrl } = useCameraConfig()
      
      const result = validateStreamUrl('webrtc://example.com/stream')
      expect(result.valid).toBe(true)
      expect(result.type).toBe('webrtc')
    })

    it('should reject invalid URLs', () => {
      const { validateStreamUrl } = useCameraConfig()
      
      const result = validateStreamUrl('ftp://example.com/stream')
      expect(result.valid).toBe(false)
      expect(result.error).toBeDefined()
    })

    it('should handle empty URLs', () => {
      const { validateStreamUrl } = useCameraConfig()
      
      const result = validateStreamUrl('')
      expect(result.valid).toBe(false)
      expect(result.error).toBe('URL vazia ou inválida')
    })
  })

  describe('generateStreamUrlFromPreset', () => {
    it('should generate Hikvision URL', () => {
      const { generateStreamUrlFromPreset } = useCameraConfig()
      
      const url = generateStreamUrlFromPreset('hikvision', {
        ip: '192.168.1.100',
        port: '554',
        username: 'admin',
        password: 'password123',
      })
      
      expect(url).toContain('rtsp://')
      expect(url).toContain('192.168.1.100')
      expect(url).toContain('admin')
      expect(url).toContain('password123')
    })

    it('should generate Dahua URL', () => {
      const { generateStreamUrlFromPreset } = useCameraConfig()
      
      const url = generateStreamUrlFromPreset('dahua', {
        ip: '192.168.1.101',
        port: '554',
        username: 'admin',
        password: 'pass',
      })
      
      expect(url).toContain('192.168.1.101')
      expect(url).toContain('cam/realmonitor')
    })

    it('should use default port if not provided', () => {
      const { generateStreamUrlFromPreset } = useCameraConfig()
      
      const url = generateStreamUrlFromPreset('hikvision', {
        ip: '192.168.1.100',
        username: 'admin',
        password: 'pass',
      })
      
      expect(url).toContain(':554')
    })

    it('should return empty string for unknown preset', () => {
      const { generateStreamUrlFromPreset } = useCameraConfig()
      
      const url = generateStreamUrlFromPreset('unknown_preset', {})
      expect(url).toBe('')
    })
  })

  describe('detectStreamType', () => {
    it('should detect stream types correctly', () => {
      const { detectStreamType } = useCameraConfig()
      
      expect(detectStreamType('rtsp://test.com/stream')).toBe('rtsp')
      expect(detectStreamType('rtmp://test.com/stream')).toBe('rtmp')
      expect(detectStreamType('https://test.com/stream.m3u8')).toBe('hls')
      expect(detectStreamType('http://test.com/stream')).toBe('http')
      expect(detectStreamType('webrtc://test.com/stream')).toBe('webrtc')
      expect(detectStreamType('invalid://test.com')).toBe('unknown')
    })
  })

  describe('parseRtspUrl', () => {
    it('should parse RTSP URL correctly', () => {
      const { parseRtspUrl } = useCameraConfig()
      
      const parsed = parseRtspUrl('rtsp://admin:pass123@192.168.1.100:554/stream/channel1')
      
      expect(parsed.protocol).toBe('rtsp')
      expect(parsed.ip).toBe('192.168.1.100')
      expect(parsed.port).toBe('554')
      expect(parsed.username).toBe('admin')
      expect(parsed.password).toBe('pass123')
      expect(parsed.path).toContain('/stream/channel1')
    })

    it('should use default port if not specified', () => {
      const { parseRtspUrl } = useCameraConfig()
      
      const parsed = parseRtspUrl('rtsp://192.168.1.100/stream')
      expect(parsed.port).toBe('554')
    })

    it('should handle invalid URLs', () => {
      const { parseRtspUrl } = useCameraConfig()
      
      const parsed = parseRtspUrl('not a url')
      expect(parsed.error).toBe('URL inválida')
    })
  })

  describe('testStreamConnection', () => {
    it('should test stream connection successfully', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: true,
        message: 'Conexão bem-sucedida!',
      })

      const { testStreamConnection } = useCameraConfig()
      
      const result = await testStreamConnection('rtsp://192.168.1.100/stream')

      expect(mockApi.post).toHaveBeenCalledWith('/setup_app/api/test-stream/', expect.objectContaining({
        stream_url: 'rtsp://192.168.1.100/stream',
        stream_type: 'rtsp',
      }))
      expect(mockNotify.success).toHaveBeenCalled()
      expect(result.success).toBe(true)
    })

    it('should handle test failure', async () => {
      mockApi.post.mockResolvedValueOnce({
        success: false,
        message: 'Timeout',
      })

      const { testStreamConnection } = useCameraConfig()
      
      const result = await testStreamConnection('rtsp://invalid.local/stream')

      expect(mockNotify.error).toHaveBeenCalled()
      expect(result.success).toBe(false)
    })
  })

  describe('validateCameraCredentials', () => {
    it('should validate complete credentials', () => {
      const { validateCameraCredentials } = useCameraConfig()
      
      const result = validateCameraCredentials({
        ip: '192.168.1.100',
        username: 'admin',
        password: 'pass123',
        port: '554',
      })
      
      expect(result.valid).toBe(true)
      expect(result.errors).toHaveLength(0)
    })

    it('should reject invalid IP', () => {
      const { validateCameraCredentials } = useCameraConfig()
      
      const result = validateCameraCredentials({
        ip: 'invalid-ip',
        username: 'admin',
        password: 'pass',
        port: '554',
      })
      
      expect(result.valid).toBe(false)
      expect(result.errors).toContain('IP inválido')
    })

    it('should reject missing credentials', () => {
      const { validateCameraCredentials } = useCameraConfig()
      
      const result = validateCameraCredentials({
        ip: '192.168.1.100',
        username: '',
        password: '',
        port: '554',
      })
      
      expect(result.valid).toBe(false)
      expect(result.errors.length).toBeGreaterThan(0)
    })

    it('should reject invalid port', () => {
      const { validateCameraCredentials } = useCameraConfig()
      
      const result = validateCameraCredentials({
        ip: '192.168.1.100',
        username: 'admin',
        password: 'pass',
        port: '70000', // Invalid port
      })
      
      expect(result.valid).toBe(false)
      expect(result.errors).toContain('Porta inválida (1-65535)')
    })
  })

  describe('Utility Methods', () => {
    it('should create default camera config', () => {
      const { createDefaultCameraConfig, cameraSettings } = useCameraConfig()
      
      const config = createDefaultCameraConfig()
      
      expect(config.stream_type).toBe(cameraSettings.value.default_stream_type)
      expect(config.resolution).toBe(cameraSettings.value.default_resolution)
      expect(config.enable_audio).toBe(false)
    })

    it('should create default camera config with overrides', () => {
      const { createDefaultCameraConfig } = useCameraConfig()
      
      const config = createDefaultCameraConfig({
        enable_audio: true,
        retention_days: 30,
      })
      
      expect(config.enable_audio).toBe(true)
      expect(config.retention_days).toBe(30)
    })

    it('should normalize stream URL', () => {
      const { normalizeStreamUrl } = useCameraConfig()
      
      expect(normalizeStreamUrl('192.168.1.100/stream')).toBe('rtsp://192.168.1.100/stream')
      expect(normalizeStreamUrl('rtsp://192.168.1.100/stream')).toBe('rtsp://192.168.1.100/stream')
      expect(normalizeStreamUrl('')).toBe('')
    })

    it('should get preset by ID', () => {
      const { getPresetById } = useCameraConfig()
      
      const preset = getPresetById('hikvision')
      expect(preset.manufacturer).toBe('Hikvision')
    })

    it('should get presets by manufacturer', () => {
      const { getPresetsByManufacturer } = useCameraConfig()
      
      const presets = getPresetsByManufacturer('Hik')
      expect(presets.length).toBeGreaterThan(0)
      expect(presets[0].manufacturer).toContain('Hikvision')
    })
  })
})
