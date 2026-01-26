import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

// Mock API functions
const mockGet = vi.fn()
const mockPost = vi.fn()

// Mock useApi
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    get: mockGet,
    post: mockPost
  })
}))

describe('useSiteCameras', () => {
  let useSiteCameras
  
  beforeEach(async () => {
    // Import após mock
    const module = await import('@/composables/useSiteCameras')
    useSiteCameras = module.useSiteCameras
    
    vi.clearAllMocks()
    mockGet.mockClear()
    mockPost.mockClear()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('fetchMosaics', () => {
    it('deve buscar mosaicos por site_id', async () => {
      const mockMosaics = [
        { id: 1, name: 'Mosaico A', site_id: 100, cameras: [1, 2] },
        { id: 2, name: 'Mosaico B', site_id: 200, cameras: [3, 4] }
      ]
      
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaics: mockMosaics
      })

      const { fetchMosaics, mosaics, error } = useSiteCameras()
      await fetchMosaics(100)
      await flushPromises()

      expect(mockGet).toHaveBeenCalledWith('/setup_app/video/api/mosaics/')
      expect(mosaics.value).toHaveLength(1)
      expect(mosaics.value[0].id).toBe(1)
      expect(mosaics.value[0].name).toBe('Mosaico A')
      expect(error.value).toBeNull()
    })

    it('deve filtrar mosaicos do site correto', async () => {
      const mockMosaics = [
        { id: 1, site_id: 100, cameras: [1] },
        { id: 2, site_id: 200, cameras: [2] },
        { id: 3, site_id: 100, cameras: [3] }
      ]
      
      mockGet.mockResolvedValueOnce({
        success: true,
        results: mockMosaics
      })

      const { fetchMosaics, mosaics } = useSiteCameras()
      await fetchMosaics(100)
      await flushPromises()

      expect(mosaics.value).toHaveLength(2)
      expect(mosaics.value.every(m => m.site_id === 100)).toBe(true)
    })

    it('deve capturar erro quando API falhar', async () => {
      mockGet.mockRejectedValueOnce(new Error('API offline'))

      const { fetchMosaics, mosaics, error, loading } = useSiteCameras()
      await fetchMosaics(100)
      await flushPromises()

      expect(mosaics.value).toHaveLength(0)
      expect(error.value).toBeTruthy()
      expect(loading.value).toBe(false)
    })

    it('deve retornar array vazio se success=false', async () => {
      mockGet.mockResolvedValueOnce({ success: false })

      const { fetchMosaics, mosaics } = useSiteCameras()
      await fetchMosaics(100)
      await flushPromises()

      expect(mosaics.value).toHaveLength(0)
    })
  })

  describe('loadMosaic', () => {
    it('deve carregar mosaico com detalhes completos', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: {
          id: 1,
          name: 'Mosaico Teste',
          cameras: [10, 20, 30]
        }
      })
      
      mockGet.mockResolvedValueOnce({
        results: [
          { id: 10, name: 'Cam A', playback_url: 'http://test/10' },
          { id: 20, name: 'Cam B', playback_url: 'http://test/20' },
          { id: 30, name: 'Cam C', playback_url: 'http://test/30' }
        ]
      })

      const { loadMosaic, currentMosaic, cameras, error } = useSiteCameras()
      await loadMosaic(1, 100)
      await flushPromises()

      expect(mockGet).toHaveBeenCalledWith('/setup_app/video/api/mosaics/1/')
      expect(mockGet).toHaveBeenCalledWith('/api/v1/cameras/?site=100')
      expect(currentMosaic.value).toEqual({ id: 1, name: 'Mosaico Teste', cameras: [10, 20, 30] })
      expect(cameras.value).toHaveLength(3)
      expect(cameras.value[0].name).toBe('Cam A')
      expect(error.value).toBeNull()
    })

    it('deve enriquecer câmeras com dados da API', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        data: { id: 1, cameras: [10] }
      })
      
      mockGet.mockResolvedValueOnce({
        results: [{ id: 10, name: 'Camera Enriquecida', whep_url: 'whep://test' }]
      })

      const { loadMosaic, cameras } = useSiteCameras()
      await loadMosaic(1, 100)
      await flushPromises()

      expect(cameras.value[0].whep_url).toBe('whep://test')
      expect(cameras.value[0].name).toBe('Camera Enriquecida')
    })

    it('deve criar objetos básicos se API de câmeras falhar', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10, 20] }
      })
      
      mockGet.mockRejectedValueOnce(new Error('Câmeras API offline'))

      const { loadMosaic, cameras, error } = useSiteCameras()
      await loadMosaic(1, 100)
      await flushPromises()

      expect(cameras.value).toHaveLength(2)
      expect(cameras.value[0]).toMatchObject({ id: 10, name: 'Camera 10' })
      expect(cameras.value[1]).toMatchObject({ id: 20, name: 'Camera 20' })
      expect(error.value).toBeNull() // Não falha, usa fallback
    })

    it('deve adicionar connectionKey único para cada câmera', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10, 20] }
      })
      
      mockGet.mockResolvedValueOnce({ results: [] })

      const { loadMosaic, cameras } = useSiteCameras()
      await loadMosaic(1, 100)
      await flushPromises()

      expect(cameras.value[0].connectionKey).toBeTruthy()
      expect(cameras.value[1].connectionKey).toBeTruthy()
      expect(cameras.value[0].connectionKey).not.toBe(cameras.value[1].connectionKey)
    })
  })

  describe('startStreams', () => {
    it('deve iniciar streams em paralelo', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10, 20, 30, 40] }
      })
      
      mockGet.mockResolvedValueOnce({
        results: [
          { id: 10, name: 'Cam 1' },
          { id: 20, name: 'Cam 2' },
          { id: 30, name: 'Cam 3' },
          { id: 40, name: 'Cam 4' }
        ]
      })

      mockPost.mockResolvedValue({
        success: true,
        playback_url: 'http://test/stream.m3u8',
        playback_proxy_url: 'http://proxy/stream.m3u8'
      })

      const { loadMosaic, startStreams, cameras } = useSiteCameras()
      await loadMosaic(1, 100)
      await flushPromises()

      const startTime = performance.now()
      await startStreams()
      await flushPromises()
      const duration = performance.now() - startTime

      expect(mockPost).toHaveBeenCalledTimes(4)
      expect(cameras.value[0].playback_url).toBe('http://proxy/stream.m3u8')
      expect(cameras.value[1].playback_url).toBe('http://proxy/stream.m3u8')
      // Processar em paralelo deve ser mais rápido que sequencial
      expect(duration).toBeLessThan(1000) // Menos de 1 segundo para 4 câmeras
    })

    it('deve usar playback_proxy_url prioritariamente', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10] }
      })
      
      mockGet.mockResolvedValueOnce({ results: [{ id: 10 }] })
      
      mockPost.mockResolvedValueOnce({
        success: true,
        playback_url: 'http://direct/stream.m3u8',
        playback_proxy_url: 'http://proxy/stream.m3u8'
      })

      const { loadMosaic, startStreams, cameras } = useSiteCameras()
      await loadMosaic(1, 100)
      await startStreams()
      await flushPromises()

      expect(cameras.value[0].playback_url).toBe('http://proxy/stream.m3u8')
    })

    it('deve fazer fallback para playback_url se proxy não existir', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10] }
      })
      
      mockGet.mockResolvedValueOnce({ results: [{ id: 10 }] })
      
      mockPost.mockResolvedValueOnce({
        success: true,
        playback_url: 'http://direct/stream.m3u8'
      })

      const { loadMosaic, startStreams, cameras } = useSiteCameras()
      await loadMosaic(1, 100)
      await startStreams()
      await flushPromises()

      expect(cameras.value[0].playback_url).toBe('http://direct/stream.m3u8')
    })

    it('deve continuar se uma câmera falhar (resilient)', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10, 20, 30] }
      })
      
      mockGet.mockResolvedValueOnce({
        results: [
          { id: 10, name: 'Cam 1' },
          { id: 20, name: 'Cam 2' },
          { id: 30, name: 'Cam 3' }
        ]
      })

      mockPost
        .mockResolvedValueOnce({ success: true, playback_url: 'http://test/1.m3u8' })
        .mockRejectedValueOnce(new Error('Câmera offline'))
        .mockResolvedValueOnce({ success: true, playback_url: 'http://test/3.m3u8' })

      const { loadMosaic, startStreams, cameras } = useSiteCameras()
      await loadMosaic(1, 100)
      await startStreams()
      await flushPromises()

      expect(cameras.value[0].playback_url).toBe('http://test/1.m3u8')
      expect(cameras.value[1].playback_url).toBeUndefined() // Falhou
      expect(cameras.value[2].playback_url).toBe('http://test/3.m3u8')
    })

    it('deve pular câmeras sem id', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10] }
      })
      
      mockGet.mockResolvedValueOnce({ results: [] })

      const { loadMosaic, cameras, startStreams } = useSiteCameras()
      await loadMosaic(1, 100)
      
      // Remover id de uma câmera
      cameras.value.push({ name: 'Sem ID' })
      
      await startStreams()
      await flushPromises()

      // Só a câmera com ID deve fazer POST
      expect(mockPost).toHaveBeenCalledTimes(1)
    })
  })

  describe('stopStreams', () => {
    it('deve parar streams de todas as câmeras', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10, 20] }
      })
      
      mockGet.mockResolvedValueOnce({
        results: [
          { id: 10, gateway_id: 100 },
          { id: 20, gateway_id: 200 }
        ]
      })

      mockPost.mockResolvedValue({ success: true })

      const { loadMosaic, stopStreams } = useSiteCameras()
      await loadMosaic(1, 100)
      await flushPromises()

      await stopStreams()
      await flushPromises()

      expect(mockPost).toHaveBeenCalledWith('/setup_app/api/gateways/100/video/preview/stop/', { camera_id: 10 })
      expect(mockPost).toHaveBeenCalledWith('/setup_app/api/gateways/200/video/preview/stop/', { camera_id: 20 })
    })

    it('deve pular câmeras sem gateway_id', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10, 20] }
      })
      
      mockGet.mockResolvedValueOnce({
        results: [
          { id: 10 }, // Sem gateway_id
          { id: 20, gateway_id: 200 }
        ]
      })

      mockPost.mockResolvedValue({ success: true })

      const { loadMosaic, stopStreams } = useSiteCameras()
      await loadMosaic(1, 100)
      await stopStreams()
      await flushPromises()

      expect(mockPost).toHaveBeenCalledTimes(1)
      expect(mockPost).toHaveBeenCalledWith('/setup_app/api/gateways/200/video/preview/stop/', { camera_id: 20 })
    })

    it('deve continuar mesmo se parar um stream falhar', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10, 20] }
      })
      
      mockGet.mockResolvedValueOnce({
        results: [
          { id: 10, gateway_id: 100 },
          { id: 20, gateway_id: 200 }
        ]
      })

      mockPost
        .mockRejectedValueOnce(new Error('Falha ao parar'))
        .mockResolvedValueOnce({ success: true })

      const { loadMosaic, stopStreams } = useSiteCameras()
      await loadMosaic(1, 100)
      
      await expect(stopStreams()).resolves.not.toThrow()
      await flushPromises()

      expect(mockPost).toHaveBeenCalledTimes(2)
    })

    it('deve limpar estado após parar', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10] }
      })
      
      mockGet.mockResolvedValueOnce({ results: [{ id: 10, gateway_id: 100 }] })
      mockPost.mockResolvedValue({ success: true })

      const { loadMosaic, stopStreams, cameras, currentMosaic } = useSiteCameras()
      await loadMosaic(1, 100)
      await stopStreams()
      await flushPromises()

      expect(cameras.value).toHaveLength(0)
      expect(currentMosaic.value).toBeNull()
    })
  })

  describe('computed: hasCameras', () => {
    it('deve retornar true quando há câmeras', async () => {
      mockGet.mockResolvedValueOnce({
        success: true,
        mosaic: { id: 1, cameras: [10] }
      })
      
      mockGet.mockResolvedValueOnce({ results: [{ id: 10 }] })

      const { loadMosaic, hasCameras } = useSiteCameras()
      await loadMosaic(1, 100)
      await flushPromises()

      expect(hasCameras.value).toBe(true)
    })

    it('deve retornar false quando não há câmeras', () => {
      const { hasCameras } = useSiteCameras()
      expect(hasCameras.value).toBe(false)
    })
  })

  describe('estado inicial', () => {
    it('deve ter valores iniciais corretos', () => {
      const { mosaics, cameras, currentMosaic, loading, error, hasCameras } = useSiteCameras()
      
      expect(mosaics.value).toEqual([])
      expect(cameras.value).toEqual([])
      expect(currentMosaic.value).toBeNull()
      expect(loading.value).toBe(false)
      expect(error.value).toBeNull()
      expect(hasCameras.value).toBe(false)
    })
  })
})
