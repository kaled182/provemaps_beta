import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import SiteFibersTab from '@/components/Site/SiteFibersTab.vue'

// Mock composables
const mockFetchFibers = vi.fn()
const mockRefreshFibers = vi.fn()

// Reactive state for mock
const mockFibers = ref([])
const mockLoading = ref(false)
const mockError = ref(null)
const mockHasFibers = ref(false)
const mockFiberCount = ref(0)
const mockActiveFibers = ref([])
const mockTotalLength = ref(0)

vi.mock('@/composables/useSiteFibers', () => ({
  useSiteFibers: () => ({
    fibers: mockFibers,
    loading: mockLoading,
    error: mockError,
    hasFibers: mockHasFibers,
    fiberCount: mockFiberCount,
    activeFibers: mockActiveFibers,
    totalLength: mockTotalLength,
    fetchFibers: mockFetchFibers,
    refreshFibers: mockRefreshFibers,
    formatLength: (km) => {
      if (!km) return '-'
      return km < 1 ? `${(km * 1000).toFixed(0)} m` : `${km.toFixed(2)} km`
    },
    getStatusClass: (status) => `status-${status || 'unknown'}`,
    getStatusLabel: (status) => {
      const labels = { up: 'Ativo', down: 'Inativo', planned: 'Planejado' }
      return labels[status] || 'Desconhecido'
    },
    getConnectionLabel: (conn) => {
      const labels = { physical: 'Conexão Física', logical: 'Conexão Lógica', floating: 'Não Conectado' }
      return labels[conn] || 'Indefinido'
    }
  })
}))

describe('SiteFibersTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset reactive state
    mockFibers.value = []
    mockLoading.value = false
    mockError.value = null
    mockHasFibers.value = false
    mockFiberCount.value = 0
    mockActiveFibers.value = []
    mockTotalLength.value = 0
  })

  it('deve renderizar estado de loading', async () => {
    mockLoading.value = true

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    expect(wrapper.find('.loading-state').exists()).toBe(true)
    expect(wrapper.find('.loading-state i').classes()).toContain('fa-spinner')
    expect(wrapper.text()).toContain('Carregando cabos de fibra')
  })

  it('deve renderizar estado de erro', async () => {
    mockError.value = new Error('Erro de teste')

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    expect(wrapper.find('.error-state').exists()).toBe(true)
    expect(wrapper.find('.retry-button').exists()).toBe(true)
    expect(wrapper.text()).toContain('Erro ao carregar cabos')
  })

  it('deve chamar refreshFibers ao clicar em retry', async () => {
    mockError.value = new Error('Erro de teste')

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const retryButton = wrapper.find('.retry-button')
    await retryButton.trigger('click')

    expect(mockRefreshFibers).toHaveBeenCalledWith(100)
  })

  it('deve renderizar estado vazio quando não há fibras', async () => {
    mockFibers.value = []
    mockHasFibers.value = false
    mockLoading.value = false

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('Nenhum cabo de fibra conectado')
  })

  it('deve renderizar lista de fibras', async () => {
    mockFibers.value = [
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
    mockHasFibers.value = true
    mockFiberCount.value = 2
    mockActiveFibers.value = [mockFibers.value[0]]
    mockTotalLength.value = 8.7
    mockLoading.value = false

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    expect(wrapper.find('.fibers-content').exists()).toBe(true)
    
    const fiberCards = wrapper.findAll('.fiber-card')
    expect(fiberCards).toHaveLength(2)
    
    expect(wrapper.text()).toContain('Cabo A-B')
    expect(wrapper.text()).toContain('Site A')
    expect(wrapper.text()).toContain('Site B')
    expect(wrapper.text()).toContain('Cabo B-C')
  })

  it('deve exibir summary header correto', async () => {
    mockFibers.value = [
      { id: 1, status: 'up', length_km: 5 },
      { id: 2, status: 'up', length_km: 3 }
    ]
    mockHasFibers.value = true
    mockFiberCount.value = 2
    mockActiveFibers.value = mockFibers.value
    mockTotalLength.value = 8
    mockLoading.value = false

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const summaryHeader = wrapper.find('.summary-header')
    expect(summaryHeader.exists()).toBe(true)
    expect(summaryHeader.text()).toContain('Total de Cabos')
    expect(summaryHeader.text()).toContain('2')
    expect(summaryHeader.text()).toContain('Ativos')
    expect(summaryHeader.text()).toContain('Comprimento Total')
  })

  it('deve emitir view-details ao clicar em card', async () => {
    const mockFiber = {
      id: 1,
      name: 'Cabo Teste',
      site_a_name: 'A',
      site_b_name: 'B',
      status: 'up'
    }
    
    mockFibers.value = [mockFiber]
    mockHasFibers.value = true
    mockLoading.value = false

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const fiberCard = wrapper.find('.fiber-card')
    await fiberCard.trigger('click')

    expect(wrapper.emitted('view-details')).toBeTruthy()
    expect(wrapper.emitted('view-details')[0][0]).toEqual(mockFiber)
  })

  it('deve emitir view-structure ao clicar em botão estrutura', async () => {
    const mockFiber = {
      id: 1,
      name: 'Cabo Teste',
      site_a_name: 'A',
      site_b_name: 'B',
      status: 'up'
    }
    
    mockFibers.value = [mockFiber]
    mockHasFibers.value = true
    mockLoading.value = false

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const structureBtn = wrapper.findAll('.action-btn')[0]
    await structureBtn.trigger('click')

    expect(wrapper.emitted('view-structure')).toBeTruthy()
    expect(wrapper.emitted('view-structure')[0][0]).toEqual(mockFiber)
    
    // Não deve ter emitido view-details (click.stop)
    expect(wrapper.emitted('view-details')).toBeFalsy()
  })

  it('deve emitir view-map ao clicar em botão mapa', async () => {
    const mockFiber = {
      id: 1,
      name: 'Cabo Teste',
      site_a_name: 'A',
      site_b_name: 'B',
      status: 'up'
    }
    
    mockFibers.value = [mockFiber]
    mockHasFibers.value = true
    mockLoading.value = false

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const mapBtn = wrapper.findAll('.action-btn')[1]
    await mapBtn.trigger('click')

    expect(wrapper.emitted('view-map')).toBeTruthy()
    expect(wrapper.emitted('view-map')[0][0]).toEqual(mockFiber)
  })

  it('deve emitir edit-fiber ao clicar em botão editar', async () => {
    const mockFiber = {
      id: 1,
      name: 'Cabo Teste',
      site_a_name: 'A',
      site_b_name: 'B',
      status: 'up'
    }
    
    mockFibers.value = [mockFiber]
    mockHasFibers.value = true
    mockLoading.value = false

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const editBtn = wrapper.findAll('.action-btn')[2]
    await editBtn.trigger('click')

    expect(wrapper.emitted('edit-fiber')).toBeTruthy()
    expect(wrapper.emitted('edit-fiber')[0][0]).toEqual(mockFiber)
  })

  it('deve renderizar status com classe CSS correta', async () => {
    mockFibers.value = [
      {
        id: 1,
        name: 'Cabo Up',
        site_a_name: 'A',
        site_b_name: 'B',
        status: 'up'
      }
    ]
    mockHasFibers.value = true
    mockLoading.value = false

    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const statusBadge = wrapper.find('.fiber-status')
    expect(statusBadge.classes()).toContain('status-up')
    expect(statusBadge.text()).toBe('Ativo')
  })

  it('deve chamar fetchFibers ao montar', async () => {
    mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    expect(mockFetchFibers).toHaveBeenCalledWith(100)
  })

  it('deve chamar fetchFibers quando siteId mudar', async () => {
    const wrapper = mount(SiteFibersTab, {
      props: { siteId: 100 }
    })

    await flushPromises()
    expect(mockFetchFibers).toHaveBeenCalledWith(100)

    await wrapper.setProps({ siteId: 200 })
    await flushPromises()

    expect(mockFetchFibers).toHaveBeenCalledWith(200)
  })
})
