import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref } from 'vue'
import SiteCamerasTab from '@/components/Site/SiteCamerasTab.vue'

// Mock composables
const mockFetchMosaics = vi.fn()
const mockLoadMosaic = vi.fn()
const mockStartStreams = vi.fn()
const mockStopStreams = vi.fn()

// Reactive state for mock
const mockMosaics = ref([])
const mockCameras = ref([])
const mockCurrentMosaic = ref(null)
const mockLoading = ref(false)
const mockError = ref(null)

vi.mock('@/composables/useSiteCameras', () => ({
  useSiteCameras: () => ({
    mosaics: mockMosaics,
    cameras: mockCameras,
    currentMosaic: mockCurrentMosaic,
    loading: mockLoading,
    error: mockError,
    hasCameras: { value: false },
    fetchMosaics: mockFetchMosaics,
    loadMosaic: mockLoadMosaic,
    startStreams: mockStartStreams,
    stopStreams: mockStopStreams
  })
}))

// Mock CameraPlayer
vi.mock('@/components/Video/CameraPlayer.vue', () => ({
  default: {
    name: 'CameraPlayer',
    template: '<div class="mock-camera-player">{{ camera.name }}</div>',
    props: ['camera', 'autoplay', 'muted']
  }
}))

describe('SiteCamerasTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset reactive state
    mockMosaics.value = []
    mockCameras.value = []
    mockCurrentMosaic.value = null
    mockLoading.value = false
    mockError.value = null
  })

  it('deve renderizar estado de loading', async () => {
    mockLoading.value = true

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    expect(wrapper.find('.loading-state').exists()).toBe(true)
    expect(wrapper.find('.loading-state i').classes()).toContain('fa-spinner')
    expect(wrapper.text()).toContain('Carregando')
  })

  it('deve renderizar estado de erro', async () => {
    mockError.value = new Error('Erro de teste')

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    expect(wrapper.find('.error-state').exists()).toBe(true)
    expect(wrapper.find('.retry-button').exists()).toBe(true)
  })

  it('deve renderizar estado vazio quando não há mosaicos', async () => {
    mockMosaics.value = []
    mockLoading.value = false

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('Nenhum mosaico configurado')
  })

  it('deve renderizar lista de mosaicos', async () => {
    mockMosaics.value = [
      { id: 1, name: 'Mosaico A', cameras: [1, 2, 3] },
      { id: 2, name: 'Mosaico B', cameras: [4, 5] }
    ]
    mockLoading.value = false

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const mosaicCards = wrapper.findAll('.mosaic-card')
    expect(mosaicCards).toHaveLength(2)
    expect(wrapper.text()).toContain('Mosaico A')
    expect(wrapper.text()).toContain('3 câmeras')
    expect(wrapper.text()).toContain('Mosaico B')
    expect(wrapper.text()).toContain('2 câmeras')
  })

  it('deve chamar loadMosaic ao clicar em mosaico', async () => {
    mockMosaics.value = [
      { id: 1, name: 'Mosaico A', cameras: [1, 2] }
    ]
    mockLoading.value = false

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const mosaicCard = wrapper.find('.mosaic-card')
    await mosaicCard.trigger('click')
    await flushPromises()

    expect(mockLoadMosaic).toHaveBeenCalledWith(1, 100)
  })

  it('deve renderizar visualizador de mosaico', async () => {
    mockCurrentMosaic.value = { id: 1, name: 'Mosaico Teste' }
    mockCameras.value = [
      { id: 10, name: 'Camera 1', playback_url: 'http://test/1.m3u8' },
      { id: 20, name: 'Camera 2', playback_url: 'http://test/2.m3u8' }
    ]
    mockLoading.value = false

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    expect(wrapper.find('.mosaic-viewer').exists()).toBe(true)
    expect(wrapper.find('.mosaic-header h3').text()).toBe('Mosaico Teste')
    expect(wrapper.findAll('.mosaic-cell')).toHaveLength(2)
  })

  it('deve usar CameraPlayer para renderizar câmeras', async () => {
    mockCurrentMosaic.value = { id: 1, name: 'Mosaico' }
    mockCameras.value = [
      { id: 10, name: 'Camera 1' }
    ]

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const cameraPlayer = wrapper.findComponent({ name: 'CameraPlayer' })
    expect(cameraPlayer.exists()).toBe(true)
    expect(cameraPlayer.props('autoplay')).toBe(true)
    expect(cameraPlayer.props('muted')).toBe(true)
  })

  it('deve aplicar classe correta baseada no número de câmeras', async () => {
    mockCurrentMosaic.value = { id: 1, name: 'Mosaico' }
    mockCameras.value = [
      { id: 1, name: 'Cam 1' },
      { id: 2, name: 'Cam 2' },
      { id: 3, name: 'Cam 3' },
      { id: 4, name: 'Cam 4' }
    ]

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const mosaicGrid = wrapper.find('.mosaic-grid')
    expect(mosaicGrid.classes()).toContain('mosaic-grid-4')
  })

  it('deve voltar à lista de mosaicos ao clicar em Voltar', async () => {
    mockCurrentMosaic.value = { id: 1, name: 'Mosaico' }
    mockCameras.value = [{ id: 10, name: 'Cam 1' }]

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const backButton = wrapper.find('.back-button')
    await backButton.trigger('click')
    await flushPromises()

    expect(mockStopStreams).toHaveBeenCalled()
  })

  it('deve chamar fetchMosaics ao montar', async () => {
    mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    expect(mockFetchMosaics).toHaveBeenCalledWith(100)
  })

  it('deve chamar stopStreams ao desmontar', async () => {
    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    wrapper.unmount()
    await flushPromises()

    expect(mockStopStreams).toHaveBeenCalled()
  })

  it('deve reagir a mudança de siteId', async () => {
    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()
    mockFetchMosaics.mockClear()

    await wrapper.setProps({ siteId: 200 })
    await flushPromises()

    expect(mockFetchMosaics).toHaveBeenCalledWith(200)
  })

  it('deve renderizar botão de tentar novamente em caso de erro', async () => {
    mockError.value = new Error('API offline')

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const retryButton = wrapper.find('.retry-button')
    expect(retryButton.exists()).toBe(true)

    mockFetchMosaics.mockClear()
    await retryButton.trigger('click')
    await flushPromises()

    expect(mockFetchMosaics).toHaveBeenCalledWith(100)
  })

  it('deve iniciar streams após abrir mosaico', async () => {
    vi.useFakeTimers()

    mockMosaics.value = [{ id: 1, name: 'Mosaico A', cameras: [1] }]
    mockLoading.value = false

    const wrapper = mount(SiteCamerasTab, {
      props: { siteId: 100 }
    })

    await flushPromises()

    const mosaicCard = wrapper.find('.mosaic-card')
    await mosaicCard.trigger('click')
    await flushPromises()

    // Streams iniciam após 100ms
    vi.advanceTimersByTime(100)
    await flushPromises()

    expect(mockStartStreams).toHaveBeenCalled()

    vi.useRealTimers()
  })
})
