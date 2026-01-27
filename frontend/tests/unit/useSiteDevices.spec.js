import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useSiteDevices } from '@/composables/useSiteDevices'
import * as useApi from '@/composables/useApi'

// Mock useApi
vi.mock('@/composables/useApi', () => ({
  get: vi.fn(),
}))

describe('useSiteDevices', () => {
  let siteDevices

  beforeEach(() => {
    vi.clearAllMocks()
    siteDevices = useSiteDevices()
  })

  // ===== State Initialization =====
  
  describe('State Initialization', () => {
    it('should initialize with empty devices', () => {
      expect(siteDevices.devices.value).toEqual([])
    })

    it('should initialize with loading false', () => {
      expect(siteDevices.loading.value).toBe(false)
    })

    it('should initialize with null error', () => {
      expect(siteDevices.error.value).toBeNull()
    })
  })

  // ===== Computed Properties =====
  
  describe('Computed Properties', () => {
    it('should compute hasDevices correctly', () => {
      expect(siteDevices.hasDevices.value).toBe(false)

      siteDevices.devices.value = [
        { id: 1, name: 'Device 1', status: 'online' },
      ]

      expect(siteDevices.hasDevices.value).toBe(true)
    })

    it('should compute deviceCount correctly', () => {
      expect(siteDevices.deviceCount.value).toBe(0)

      siteDevices.devices.value = [
        { id: 1, name: 'Device 1' },
        { id: 2, name: 'Device 2' },
        { id: 3, name: 'Device 3' },
      ]

      expect(siteDevices.deviceCount.value).toBe(3)
    })

    it('should compute deviceStats correctly', () => {
      siteDevices.devices.value = [
        { id: 1, status: 'online' },
        { id: 2, status: 'online' },
        { id: 3, status: 'warning' },
        { id: 4, status: 'critical' },
        { id: 5, status: 'offline' },
        { id: 6, status: 'offline' },
      ]

      const stats = siteDevices.deviceStats.value

      expect(stats.online).toBe(2)
      expect(stats.warning).toBe(1)
      expect(stats.critical).toBe(1)
      expect(stats.offline).toBe(2)
    })

    it('should handle Portuguese status labels in stats', () => {
      siteDevices.devices.value = [
        { id: 1, status: 'atenção' },
        { id: 2, status: 'crítico' },
      ]

      const stats = siteDevices.deviceStats.value

      expect(stats.warning).toBe(1)
      expect(stats.critical).toBe(1)
    })

    it('should compute onlineDevices correctly', () => {
      siteDevices.devices.value = [
        { id: 1, status: 'online' },
        { id: 2, status: 'online' },
        { id: 3, status: 'offline' },
      ]

      expect(siteDevices.onlineDevices.value).toBe(2)
    })

    it('should compute warningDevices correctly', () => {
      siteDevices.devices.value = [
        { id: 1, status: 'warning' },
        { id: 2, status: 'online' },
      ]

      expect(siteDevices.warningDevices.value).toBe(1)
    })

    it('should compute criticalDevices correctly', () => {
      siteDevices.devices.value = [
        { id: 1, status: 'critical' },
        { id: 2, status: 'critical' },
        { id: 3, status: 'online' },
      ]

      expect(siteDevices.criticalDevices.value).toBe(2)
    })

    it('should compute offlineDevices correctly', () => {
      siteDevices.devices.value = [
        { id: 1, status: 'offline' },
        { id: 2, status: 'offline' },
        { id: 3, status: 'offline' },
        { id: 4, status: 'online' },
      ]

      expect(siteDevices.offlineDevices.value).toBe(3)
    })
  })

  // ===== fetchDevices =====
  
  describe('fetchDevices', () => {
    const mockApiResponse = {
      count: 2,
      results: [
        {
          id: 1,
          name: 'Router 1',
          group_name: 'Router',
          site: 123,
          primary_ip: '192.168.1.1',
          zabbix_hostid: 'zbx-001',
          cpu_usage_item_key: 'system.cpu.util',
          cpu_usage_manual_percent: 45,
          memory_usage_manual_percent: 60,
          uptime: 86400,
        },
        {
          id: 2,
          name: 'Switch 1',
          group_name: 'Switch',
          site: 456, // Different site
          primary_ip: '192.168.1.2',
          zabbix_hostid: 'zbx-002',
        },
      ],
    }

    it('should fetch and filter devices by siteId', async () => {
      useApi.get.mockResolvedValue(mockApiResponse)

      await siteDevices.fetchDevices(123)

      expect(useApi.get).toHaveBeenCalledWith('/api/v1/devices/')
      expect(siteDevices.devices.value).toHaveLength(1)
      expect(siteDevices.devices.value[0].name).toBe('Router 1')
      expect(siteDevices.loading.value).toBe(false)
      expect(siteDevices.error.value).toBeNull()
    })

    it('should map device fields correctly', async () => {
      useApi.get.mockResolvedValue(mockApiResponse)

      await siteDevices.fetchDevices(123)

      const device = siteDevices.devices.value[0]

      expect(device.id).toBe(1)
      expect(device.name).toBe('Router 1')
      expect(device.type).toBe('Router')
      expect(device.status).toBe('offline') // Default status
      expect(device.cpu).toBe(45)
      expect(device.memory).toBe(60)
      expect(device.uptime).toBe(86400)
      expect(device.ip).toBe('192.168.1.1')
      expect(device.zabbixHostId).toBe('zbx-001')
      expect(device.cpuItemKey).toBe('system.cpu.util')
    })

    it('should handle missing optional fields', async () => {
      useApi.get.mockResolvedValue({
        count: 1,
        results: [
          {
            id: 3,
            site: 123,
          },
        ],
      })

      await siteDevices.fetchDevices(123)

      const device = siteDevices.devices.value[0]

      expect(device.name).toBe('Dispositivo sem nome')
      expect(device.type).toBe('Dispositivo')
      expect(device.cpu).toBe(0)
      expect(device.memory).toBe(0)
      expect(device.uptime).toBe(0)
      expect(device.ip).toBe('N/A')
    })

    it('should set loading state during fetch', async () => {
      let resolvePromise
      const promise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      useApi.get.mockReturnValue(promise)

      const fetchPromise = siteDevices.fetchDevices(123)

      expect(siteDevices.loading.value).toBe(true)

      resolvePromise(mockApiResponse)
      await fetchPromise

      expect(siteDevices.loading.value).toBe(false)
    })

    it('should handle API errors', async () => {
      const error = new Error('Network error')
      useApi.get.mockRejectedValue(error)

      await siteDevices.fetchDevices(123)

      expect(siteDevices.error.value).toBe('Network error')
      expect(siteDevices.devices.value).toEqual([])
      expect(siteDevices.loading.value).toBe(false)
    })

    it('should handle missing siteId', async () => {
      await siteDevices.fetchDevices(null)

      expect(useApi.get).not.toHaveBeenCalled()
      expect(siteDevices.devices.value).toEqual([])
    })

    it('should handle empty API response', async () => {
      useApi.get.mockResolvedValue({ count: 0, results: [] })

      await siteDevices.fetchDevices(123)

      expect(siteDevices.devices.value).toEqual([])
      expect(siteDevices.error.value).toBeNull()
    })
  })

  // ===== refreshDevices =====
  
  describe('refreshDevices', () => {
    it('should call fetchDevices', async () => {
      useApi.get.mockResolvedValue({ count: 0, results: [] })

      await siteDevices.refreshDevices(123)

      expect(useApi.get).toHaveBeenCalledWith('/api/v1/devices/')
    })
  })

  // ===== clearDevices =====
  
  describe('clearDevices', () => {
    it('should clear all state', () => {
      siteDevices.devices.value = [{ id: 1 }]
      siteDevices.error.value = 'Some error'
      siteDevices.loading.value = true

      siteDevices.clearDevices()

      expect(siteDevices.devices.value).toEqual([])
      expect(siteDevices.error.value).toBeNull()
      expect(siteDevices.loading.value).toBe(false)
    })
  })

  // ===== Utility Functions =====
  
  describe('Utility Functions', () => {
    describe('getStatusClass', () => {
      it('should return lowercase status', () => {
        expect(siteDevices.getStatusClass('Online')).toBe('online')
        expect(siteDevices.getStatusClass('WARNING')).toBe('warning')
        expect(siteDevices.getStatusClass('Critical')).toBe('critical')
      })

      it('should return offline for null/undefined', () => {
        expect(siteDevices.getStatusClass(null)).toBe('offline')
        expect(siteDevices.getStatusClass(undefined)).toBe('offline')
      })
    })

    describe('getStatusLabel', () => {
      it('should return translated label', () => {
        expect(siteDevices.getStatusLabel('online')).toBe('Online')
        expect(siteDevices.getStatusLabel('warning')).toBe('Atenção')
        expect(siteDevices.getStatusLabel('critical')).toBe('Crítico')
        expect(siteDevices.getStatusLabel('offline')).toBe('Offline')
      })

      it('should default to Offline', () => {
        expect(siteDevices.getStatusLabel(null)).toBe('Offline')
        expect(siteDevices.getStatusLabel('unknown')).toBe('Offline')
      })
    })

    describe('getDeviceIcon', () => {
      it('should return correct icon for device types', () => {
        expect(siteDevices.getDeviceIcon('Router')).toBe('fas fa-network-wired')
        expect(siteDevices.getDeviceIcon('switch')).toBe('fas fa-code-branch')
        expect(siteDevices.getDeviceIcon('SERVER')).toBe('fas fa-server')
        expect(siteDevices.getDeviceIcon('firewall')).toBe('fas fa-shield-alt')
      })

      it('should return default icon for unknown types', () => {
        expect(siteDevices.getDeviceIcon('unknown')).toBe('fas fa-server')
        expect(siteDevices.getDeviceIcon(null)).toBe('fas fa-server')
      })
    })

    describe('getMetricClass', () => {
      it('should return critical for >= 90', () => {
        expect(siteDevices.getMetricClass(90)).toBe('critical')
        expect(siteDevices.getMetricClass(95)).toBe('critical')
        expect(siteDevices.getMetricClass(100)).toBe('critical')
      })

      it('should return warning for >= 70', () => {
        expect(siteDevices.getMetricClass(70)).toBe('warning')
        expect(siteDevices.getMetricClass(80)).toBe('warning')
        expect(siteDevices.getMetricClass(89)).toBe('warning')
      })

      it('should return normal for < 70', () => {
        expect(siteDevices.getMetricClass(0)).toBe('normal')
        expect(siteDevices.getMetricClass(50)).toBe('normal')
        expect(siteDevices.getMetricClass(69)).toBe('normal')
      })
    })

    describe('formatUptime', () => {
      it('should format days and hours', () => {
        expect(siteDevices.formatUptime(86400)).toBe('1d 0h') // 1 day
        expect(siteDevices.formatUptime(172800)).toBe('2d 0h') // 2 days
        expect(siteDevices.formatUptime(90000)).toBe('1d 1h') // 1 day 1 hour
      })

      it('should format hours and minutes', () => {
        expect(siteDevices.formatUptime(3600)).toBe('1h 0m') // 1 hour
        expect(siteDevices.formatUptime(7200)).toBe('2h 0m') // 2 hours
        expect(siteDevices.formatUptime(3660)).toBe('1h 1m') // 1 hour 1 minute
      })

      it('should format minutes only', () => {
        expect(siteDevices.formatUptime(60)).toBe('1m')
        expect(siteDevices.formatUptime(120)).toBe('2m')
        expect(siteDevices.formatUptime(3540)).toBe('59m')
      })

      it('should return N/A for zero or null', () => {
        expect(siteDevices.formatUptime(0)).toBe('N/A')
        expect(siteDevices.formatUptime(null)).toBe('N/A')
        expect(siteDevices.formatUptime(undefined)).toBe('N/A')
      })
    })

    describe('getDeviceTooltip', () => {
      it('should build tooltip with all fields', () => {
        const device = {
          name: 'Router 1',
          status: 'online',
          ip: '192.168.1.1',
          uptime: 86400,
          cpuItemKey: 'system.cpu.util',
          uptimeItemKey: 'system.uptime',
          zabbixHostId: 'zbx-001',
        }

        const tooltip = siteDevices.getDeviceTooltip(device)

        expect(tooltip).toContain('Router 1')
        expect(tooltip).toContain('Status: Online')
        expect(tooltip).toContain('IP: 192.168.1.1')
        expect(tooltip).toContain('Uptime: 1d 0h')
        expect(tooltip).toContain('CPU Key: system.cpu.util')
        expect(tooltip).toContain('Uptime Key: system.uptime')
        expect(tooltip).toContain('Zabbix Host ID: zbx-001')
      })

      it('should build tooltip with minimal fields', () => {
        const device = {
          name: 'Device 1',
          status: 'offline',
          ip: 'N/A',
        }

        const tooltip = siteDevices.getDeviceTooltip(device)

        expect(tooltip).toContain('Device 1')
        expect(tooltip).toContain('Status: Offline')
        expect(tooltip).toContain('IP: N/A')
        expect(tooltip).not.toContain('Uptime:')
        expect(tooltip).not.toContain('CPU Key:')
      })
    })
  })
})
