import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick, ref } from 'vue'
import SiteDevicesTab from '@/components/Site/SiteDevicesTab.vue'
import { useSiteDevices } from '@/composables/useSiteDevices'

// Mock the composable
vi.mock('@/composables/useSiteDevices')

describe('SiteDevicesTab', () => {
  let mockComposable

  beforeEach(() => {
    // Reset mock
    mockComposable = {
      devices: ref([]),
      loading: ref(false),
      error: ref(null),
      hasDevices: ref(false),
      deviceCount: ref(0),
      onlineDevices: ref(0),
      warningDevices: ref(0),
      criticalDevices: ref(0),
      offlineDevices: ref(0),
      fetchDevices: vi.fn(),
      refreshDevices: vi.fn(),
      clearDevices: vi.fn(),
      getStatusClass: vi.fn((status) => status?.toLowerCase() || 'offline'),
      getStatusLabel: vi.fn((status) => {
        const labels = { online: 'Online', warning: 'Atenção', critical: 'Crítico', offline: 'Offline' }
        return labels[status?.toLowerCase()] || 'Offline'
      }),
      getDeviceIcon: vi.fn((type) => {
        const icons = { router: 'fas fa-network-wired', switch: 'fas fa-code-branch', server: 'fas fa-server' }
        return icons[type?.toLowerCase()] || 'fas fa-server'
      }),
      getMetricClass: vi.fn((value) => {
        if (value >= 90) return 'critical'
        if (value >= 70) return 'warning'
        return 'normal'
      }),
      formatUptime: vi.fn((seconds) => {
        if (!seconds) return 'N/A'
        const days = Math.floor(seconds / 86400)
        const hours = Math.floor((seconds % 86400) / 3600)
        if (days > 0) return `${days}d ${hours}h`
        return `${hours}h`
      }),
      getDeviceTooltip: vi.fn((device) => `${device.name}\nStatus: ${device.status}`),
    }

    useSiteDevices.mockReturnValue(mockComposable)
  })

  // ===== Props & Initialization =====
  
  describe('Props & Initialization', () => {
    it('should render with required siteId prop', () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('should call fetchDevices on mount with siteId', async () => {
      mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      await nextTick()

      expect(mockComposable.fetchDevices).toHaveBeenCalledWith(123)
    })

    it('should call clearDevices on unmount', async () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      wrapper.unmount()

      expect(mockComposable.clearDevices).toHaveBeenCalled()
    })

    it('should refetch devices when siteId changes', async () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      await wrapper.setProps({ siteId: 456 })
      await nextTick()

      expect(mockComposable.fetchDevices).toHaveBeenCalledWith(456)
    })
  })

  // ===== Loading State =====
  
  describe('Loading State', () => {
    it('should show loading spinner when loading', () => {
      mockComposable.loading.value = true

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      expect(wrapper.find('.devices-loading').exists()).toBe(true)
      expect(wrapper.find('.devices-loading i.fa-spinner').exists()).toBe(true)
      expect(wrapper.text()).toContain('Carregando dispositivos')
    })

    it('should not show devices grid when loading', () => {
      mockComposable.loading.value = true

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      expect(wrapper.find('.devices-grid').exists()).toBe(false)
    })
  })

  // ===== Error State =====
  
  describe('Error State', () => {
    it('should show error message when error exists', () => {
      mockComposable.error.value = 'Network error'

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      expect(wrapper.find('.devices-error').exists()).toBe(true)
      expect(wrapper.text()).toContain('Network error')
    })

    it('should show retry button in error state', () => {
      mockComposable.error.value = 'API error'

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      expect(wrapper.find('.retry-button').exists()).toBe(true)
      expect(wrapper.find('.retry-button').text()).toContain('Tentar novamente')
    })

    it('should call refreshDevices when retry button clicked', async () => {
      mockComposable.error.value = 'Error'

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      await wrapper.find('.retry-button').trigger('click')

      expect(mockComposable.refreshDevices).toHaveBeenCalledWith(123)
    })
  })

  // ===== Empty State =====
  
  describe('Empty State', () => {
    it('should show empty state when no devices', () => {
      mockComposable.hasDevices.value = false
      mockComposable.loading.value = false
      mockComposable.error.value = null

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      expect(wrapper.find('.devices-empty').exists()).toBe(true)
      expect(wrapper.text()).toContain('Nenhum dispositivo encontrado neste site')
    })

    it('should not show devices grid in empty state', () => {
      mockComposable.hasDevices.value = false

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      expect(wrapper.find('.devices-grid').exists()).toBe(false)
    })
  })

  // ===== Header Summary =====
  
  describe('Header Summary', () => {
    it('should show device count in header', () => {
      mockComposable.deviceCount.value = 5

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      expect(wrapper.find('.summary-title h3').text()).toContain('Dispositivos (5)')
    })

    it('should show summary stats when devices exist', () => {
      mockComposable.hasDevices.value = true
      mockComposable.onlineDevices.value = 3
      mockComposable.warningDevices.value = 1
      mockComposable.criticalDevices.value = 0
      mockComposable.offlineDevices.value = 1
      mockComposable.deviceCount.value = 5

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      const stats = wrapper.find('.summary-stats')
      expect(stats.exists()).toBe(true)
      expect(stats.text()).toContain('3 Online')
      expect(stats.text()).toContain('1 Atenção')
      expect(stats.text()).toContain('1 Offline')
    })

    it('should not show summary stats when no devices', () => {
      mockComposable.hasDevices.value = false

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      expect(wrapper.find('.summary-stats').exists()).toBe(false)
    })

    it('should only show stats with non-zero values', () => {
      mockComposable.hasDevices.value = true
      mockComposable.onlineDevices.value = 5
      mockComposable.warningDevices.value = 0
      mockComposable.criticalDevices.value = 0
      mockComposable.offlineDevices.value = 0

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      const stats = wrapper.find('.summary-stats')
      expect(stats.text()).toContain('5 Online')
      expect(stats.text()).not.toContain('Atenção')
      expect(stats.text()).not.toContain('Crítico')
      expect(stats.text()).not.toContain('Offline')
    })
  })

  // ===== Devices Grid =====
  
  describe('Devices Grid', () => {
    const mockDevices = [
      {
        id: 1,
        name: 'Router 1',
        type: 'Router',
        status: 'online',
        cpu: 45,
        memory: 60,
        uptime: 86400,
        ip: '192.168.1.1',
      },
      {
        id: 2,
        name: 'Switch 1',
        type: 'Switch',
        status: 'warning',
        cpu: 75,
        memory: 80,
        uptime: 3600,
        ip: '192.168.1.2',
      },
    ]

    beforeEach(() => {
      mockComposable.devices.value = mockDevices
      mockComposable.hasDevices.value = true
      mockComposable.deviceCount.value = mockDevices.length
    })

    it('should render devices grid with device cards', () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      expect(wrapper.find('.devices-grid').exists()).toBe(true)
      expect(wrapper.findAll('.device-card')).toHaveLength(2)
    })

    it('should render device names and types', () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      const cards = wrapper.findAll('.device-card')

      expect(cards[0].text()).toContain('Router 1')
      expect(cards[0].text()).toContain('Router')
      expect(cards[1].text()).toContain('Switch 1')
      expect(cards[1].text()).toContain('Switch')
    })

    it('should apply correct status class to device cards', () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      const cards = wrapper.findAll('.device-card')

      expect(cards[0].classes()).toContain('online')
      expect(cards[1].classes()).toContain('warning')
    })

    it('should render device icons', () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      const cards = wrapper.findAll('.device-card')

      expect(mockComposable.getDeviceIcon).toHaveBeenCalledWith('Router')
      expect(mockComposable.getDeviceIcon).toHaveBeenCalledWith('Switch')
      expect(cards[0].find('.device-icon').classes()).toContain('fa-network-wired')
      expect(cards[1].find('.device-icon').classes()).toContain('fa-code-branch')
    })

    it('should render status badges', () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      const badges = wrapper.findAll('.status-badge')

      expect(badges[0].text()).toBe('Online')
      expect(badges[1].text()).toBe('Atenção')
      expect(badges[0].classes()).toContain('online')
      expect(badges[1].classes()).toContain('warning')
    })

    it('should render CPU and Memory metrics with progress bars', () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      const firstCard = wrapper.findAll('.device-card')[0]
      const metrics = firstCard.findAll('.metric')

      expect(metrics).toHaveLength(2) // CPU and Memory

      // CPU metric
      expect(metrics[0].text()).toContain('CPU')
      expect(metrics[0].text()).toContain('45%')
      const cpuBar = metrics[0].find('.metric-bar')
      expect(cpuBar.classes()).toContain('normal')
      expect(cpuBar.attributes('style')).toContain('width: 45%')

      // Memory metric
      expect(metrics[1].text()).toContain('Memória')
      expect(metrics[1].text()).toContain('60%')
      const memBar = metrics[1].find('.metric-bar')
      expect(memBar.classes()).toContain('normal')
      expect(memBar.attributes('style')).toContain('width: 60%')
    })

    it('should apply correct metric class based on value', () => {
      mockComposable.devices.value = [
        {
          id: 1,
          name: 'Device 1',
          type: 'Server',
          status: 'critical',
          cpu: 95,
          memory: 75,
          uptime: 0,
          ip: '192.168.1.1',
        },
      ]

      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      const metrics = wrapper.findAll('.metric-bar')

      expect(metrics[0].classes()).toContain('critical') // CPU 95%
      expect(metrics[1].classes()).toContain('warning')  // Memory 75%
    })

    it('should render uptime and IP metrics', () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      const firstCard = wrapper.findAll('.device-card')[0]
      const simpleMetrics = firstCard.findAll('.metric-simple')

      expect(simpleMetrics).toHaveLength(2) // Uptime and IP

      expect(simpleMetrics[0].text()).toContain('Uptime')
      expect(simpleMetrics[0].text()).toContain('1d 0h')

      expect(simpleMetrics[1].text()).toContain('IP')
      expect(simpleMetrics[1].text()).toContain('192.168.1.1')
    })
  })

  // ===== Events =====
  
  describe('Events', () => {
    const mockDevice = {
      id: 1,
      name: 'Router 1',
      type: 'Router',
      status: 'online',
      cpu: 45,
      memory: 60,
      uptime: 86400,
      ip: '192.168.1.1',
    }

    beforeEach(() => {
      mockComposable.devices.value = [mockDevice]
      mockComposable.hasDevices.value = true
      mockComposable.deviceCount.value = 1
    })

    it('should emit view-device-details when card clicked', async () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      await wrapper.find('.device-card').trigger('click')

      expect(wrapper.emitted('view-device-details')).toBeTruthy()
      expect(wrapper.emitted('view-device-details')[0]).toEqual([mockDevice])
    })

    it('should emit edit-device when edit button clicked', async () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      await wrapper.find('.edit-button').trigger('click')

      expect(wrapper.emitted('edit-device')).toBeTruthy()
      expect(wrapper.emitted('edit-device')[0]).toEqual([mockDevice])
    })

    it('should not emit view-device-details when edit button clicked', async () => {
      const wrapper = mount(SiteDevicesTab, {
        props: { siteId: 123 },
      })

      await wrapper.find('.edit-button').trigger('click')

      expect(wrapper.emitted('view-device-details')).toBeFalsy()
    })
  })
})
