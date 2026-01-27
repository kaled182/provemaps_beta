import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises } from '@vue/test-utils'

// Mock API functions
const mockGet = vi.fn()

// Mock useApi
vi.mock('@/composables/useApi', () => ({
  useApi: () => ({
    get: mockGet
  })
}))

describe('useSiteFibers', () => {
  let useSiteFibers
  
  beforeEach(async () => {
    // Import após mock
    const module = await import('@/composables/useSiteFibers')
    useSiteFibers = module.useSiteFibers
    
    vi.clearAllMocks()
    mockGet.mockClear()
  })

  describe('fetchFibers', () => {
    it('deve buscar cabos de fibra por site_id', async () => {
      const mockFibers = [
        {
          id: 1,
          name: 'Cabo A-B',
          site_a_name: 'Site A',
          site_b_name: 'Site B',
          length_km: 5.5,
          status: 'up',
          connection_status: 'physical'
        },
        {
          id: 2,
          name: 'Cabo B-C',
          site_a_name: 'Site B',
          site_b_name: 'Site C',
          length_km: 3.2,
          status: 'planned',
          connection_status: 'logical'
        }
      ]
      
      mockGet.mockResolvedValueOnce({
        site_id: 100,
        site_name: 'Site Test',
        fiber_count: 2,
        fibers: mockFibers
      })

      const { fetchFibers, fibers, fiberCount, error } = useSiteFibers()
      await fetchFibers(100)
      await flushPromises()

      expect(mockGet).toHaveBeenCalledWith('/api/v1/sites/100/fiber_cables/')
      expect(fibers.value).toHaveLength(2)
      expect(fiberCount.value).toBe(2)
      expect(fibers.value[0].name).toBe('Cabo A-B')
      expect(error.value).toBeNull()
    })

    it('deve retornar array vazio se não houver fibras', async () => {
      mockGet.mockResolvedValueOnce({
        site_id: 100,
        fiber_count: 0,
        fibers: []
      })

      const { fetchFibers, fibers, hasFibers } = useSiteFibers()
      await fetchFibers(100)
      await flushPromises()

      expect(fibers.value).toHaveLength(0)
      expect(hasFibers.value).toBe(false)
    })

    it('deve capturar erro quando API falhar', async () => {
      mockGet.mockRejectedValueOnce(new Error('API offline'))

      const { fetchFibers, fibers, error, loading } = useSiteFibers()
      await fetchFibers(100)
      await flushPromises()

      expect(fibers.value).toHaveLength(0)
      expect(error.value).toBeTruthy()
      expect(loading.value).toBe(false)
    })

    it('deve validar siteId obrigatório', async () => {
      const { fetchFibers, loading } = useSiteFibers()
      
      await fetchFibers(null)
      await flushPromises()

      expect(mockGet).not.toHaveBeenCalled()
      expect(loading.value).toBe(false)
    })

    it('deve setar loading=true durante fetch', async () => {
      mockGet.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      const { fetchFibers, loading } = useSiteFibers()
      const promise = fetchFibers(100)

      expect(loading.value).toBe(true)
      
      await promise
      expect(loading.value).toBe(false)
    })
  })

  describe('computed properties', () => {
    it('hasFibers deve retornar true quando há fibras', async () => {
      mockGet.mockResolvedValueOnce({
        fibers: [{ id: 1, name: 'Test' }]
      })

      const { fetchFibers, hasFibers } = useSiteFibers()
      await fetchFibers(100)
      await flushPromises()

      expect(hasFibers.value).toBe(true)
    })

    it('fiberCount deve retornar número correto de fibras', async () => {
      mockGet.mockResolvedValueOnce({
        fibers: [{ id: 1 }, { id: 2 }, { id: 3 }]
      })

      const { fetchFibers, fiberCount } = useSiteFibers()
      await fetchFibers(100)
      await flushPromises()

      expect(fiberCount.value).toBe(3)
    })

    it('connectedFibers deve filtrar fibras conectadas', async () => {
      mockGet.mockResolvedValueOnce({
        fibers: [
          { id: 1, connection_status: 'physical' },
          { id: 2, connection_status: 'logical' },
          { id: 3, connection_status: 'floating' }
        ]
      })

      const { fetchFibers, connectedFibers } = useSiteFibers()
      await fetchFibers(100)
      await flushPromises()

      expect(connectedFibers.value).toHaveLength(2)
      expect(connectedFibers.value.some(f => f.connection_status === 'floating')).toBe(false)
    })

    it('activeFibers deve filtrar apenas fibras ativas', async () => {
      mockGet.mockResolvedValueOnce({
        fibers: [
          { id: 1, status: 'up' },
          { id: 2, status: 'active' },
          { id: 3, status: 'down' },
          { id: 4, status: 'planned' }
        ]
      })

      const { fetchFibers, activeFibers } = useSiteFibers()
      await fetchFibers(100)
      await flushPromises()

      expect(activeFibers.value).toHaveLength(2)
      expect(activeFibers.value.every(f => ['up', 'active'].includes(f.status))).toBe(true)
    })

    it('totalLength deve somar comprimento de todos os cabos', async () => {
      mockGet.mockResolvedValueOnce({
        fibers: [
          { id: 1, length_km: 5.5 },
          { id: 2, length_km: 3.2 },
          { id: 3, length_km: 7.8 }
        ]
      })

      const { fetchFibers, totalLength } = useSiteFibers()
      await fetchFibers(100)
      await flushPromises()

      expect(totalLength.value).toBeCloseTo(16.5, 1)
    })

    it('totalLength deve tratar valores null/undefined', async () => {
      mockGet.mockResolvedValueOnce({
        fibers: [
          { id: 1, length_km: 5 },
          { id: 2, length_km: null },
          { id: 3, length_km: undefined },
          { id: 4 } // sem campo length_km
        ]
      })

      const { fetchFibers, totalLength } = useSiteFibers()
      await fetchFibers(100)
      await flushPromises()

      expect(totalLength.value).toBe(5)
    })
  })

  describe('refreshFibers', () => {
    it('deve atualizar lista de fibras', async () => {
      mockGet.mockResolvedValueOnce({
        fibers: [{ id: 1 }]
      })

      const { refreshFibers, fibers } = useSiteFibers()
      await refreshFibers(100)
      await flushPromises()

      expect(fibers.value).toHaveLength(1)
      expect(mockGet).toHaveBeenCalledTimes(1)
    })
  })

  describe('clearFibers', () => {
    it('deve limpar estado de fibras', async () => {
      mockGet.mockResolvedValueOnce({
        fibers: [{ id: 1 }, { id: 2 }]
      })

      const { fetchFibers, clearFibers, fibers, error } = useSiteFibers()
      await fetchFibers(100)
      await flushPromises()

      expect(fibers.value).toHaveLength(2)

      clearFibers()

      expect(fibers.value).toHaveLength(0)
      expect(error.value).toBeNull()
    })
  })

  describe('formatLength', () => {
    it('deve formatar comprimento em metros quando < 1km', () => {
      const { formatLength } = useSiteFibers()
      
      expect(formatLength(0.5)).toBe('500 m')
      expect(formatLength(0.123)).toBe('123 m')
    })

    it('deve formatar comprimento em km quando >= 1km', () => {
      const { formatLength } = useSiteFibers()
      
      expect(formatLength(1)).toBe('1.00 km')
      expect(formatLength(5.567)).toBe('5.57 km')
      expect(formatLength(25)).toBe('25.00 km')
    })

    it('deve retornar "-" para valores nulos/zero', () => {
      const { formatLength } = useSiteFibers()
      
      expect(formatLength(null)).toBe('-')
      expect(formatLength(undefined)).toBe('-')
      expect(formatLength(0)).toBe('-')
    })
  })

  describe('getStatusClass', () => {
    it('deve retornar classe CSS correta para cada status', () => {
      const { getStatusClass } = useSiteFibers()
      
      expect(getStatusClass('up')).toBe('status-up')
      expect(getStatusClass('active')).toBe('status-up')
      expect(getStatusClass('down')).toBe('status-down')
      expect(getStatusClass('degraded')).toBe('status-degraded')
      expect(getStatusClass('planned')).toBe('status-planned')
      expect(getStatusClass('unknown')).toBe('status-unknown')
    })

    it('deve retornar status-unknown para valores não mapeados', () => {
      const { getStatusClass } = useSiteFibers()
      
      expect(getStatusClass('invalid')).toBe('status-unknown')
      expect(getStatusClass(null)).toBe('status-unknown')
    })
  })

  describe('getStatusLabel', () => {
    it('deve retornar label em português para cada status', () => {
      const { getStatusLabel } = useSiteFibers()
      
      expect(getStatusLabel('up')).toBe('Ativo')
      expect(getStatusLabel('active')).toBe('Ativo')
      expect(getStatusLabel('down')).toBe('Inativo')
      expect(getStatusLabel('degraded')).toBe('Degradado')
      expect(getStatusLabel('planned')).toBe('Planejado')
      expect(getStatusLabel('unknown')).toBe('Desconhecido')
    })

    it('deve retornar "Desconhecido" para valores não mapeados', () => {
      const { getStatusLabel } = useSiteFibers()
      
      expect(getStatusLabel('invalid')).toBe('Desconhecido')
      expect(getStatusLabel(null)).toBe('Desconhecido')
    })
  })

  describe('getConnectionLabel', () => {
    it('deve retornar label em português para connection_status', () => {
      const { getConnectionLabel } = useSiteFibers()
      
      expect(getConnectionLabel('floating')).toBe('Não Conectado')
      expect(getConnectionLabel('logical')).toBe('Conexão Lógica')
      expect(getConnectionLabel('physical')).toBe('Conexão Física')
    })

    it('deve retornar "Indefinido" para valores não mapeados', () => {
      const { getConnectionLabel } = useSiteFibers()
      
      expect(getConnectionLabel('invalid')).toBe('Indefinido')
      expect(getConnectionLabel(null)).toBe('Indefinido')
    })
  })
})
