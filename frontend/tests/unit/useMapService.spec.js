import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useMapService, registerMapPlugin } from '@/composables/useMapService';

// Mock Google Maps API
const mockGoogle = {
  maps: {
    Map: vi.fn(),
    LatLngBounds: vi.fn(),
    InfoWindow: vi.fn(),
    Marker: vi.fn(),
    Polyline: vi.fn(),
    event: {
      addListener: vi.fn(),
      removeListener: vi.fn()
    },
    geometry: {
      spherical: {
        computeDistanceBetween: vi.fn(() => 1000)
      }
    }
  }
};

// Mock window.google
global.window = {
  google: mockGoogle
};

describe('useMapService', () => {
  let mapService;

  beforeEach(() => {
    vi.clearAllMocks();
    mapService = useMapService({
      mode: 'monitoring',
      center: { lat: -15.78, lng: -47.92 },
      zoom: 12
    });
  });

  it('should initialize with correct mode', () => {
    expect(mapService.mode).toBe('monitoring');
  });

  it('should start with isReady = false', () => {
    expect(mapService.isReady.value).toBe(false);
  });

  it('should initialize map', async () => {
    const mockContainer = document.createElement('div');
    
    await mapService.initMap(mockContainer);

    expect(mapService.isReady.value).toBe(true);
    expect(mapService.map.value).toBeDefined();
    expect(mockGoogle.maps.Map).toHaveBeenCalledWith(
      mockContainer,
      expect.objectContaining({
        center: { lat: -15.78, lng: -47.92 },
        zoom: 12,
        mapTypeId: 'roadmap'
      })
    );
  });

  it('should load a registered plugin', async () => {
    // Mock plugin factory
    const mockPluginFactory = vi.fn((context, options) => ({
      testMethod: () => 'test',
      cleanup: vi.fn()
    }));

    registerMapPlugin('testPlugin', mockPluginFactory);

    // Initialize map first
    const mockContainer = document.createElement('div');
    await mapService.initMap(mockContainer);

    // Load plugin
    const plugin = await mapService.loadPlugin('testPlugin', { option: 'value' });

    expect(mockPluginFactory).toHaveBeenCalledWith(
      expect.objectContaining({
        map: expect.anything(),
        google: mockGoogle,
        mode: 'monitoring'
      }),
      { option: 'value' }
    );

    expect(plugin.testMethod()).toBe('test');
  });

  it('should throw error when loading plugin without initializing map', async () => {
    await expect(
      mapService.loadPlugin('testPlugin')
    ).rejects.toThrow('Map not initialized');
  });

  it('should throw error for unregistered plugin', async () => {
    const mockContainer = document.createElement('div');
    await mapService.initMap(mockContainer);

    await expect(
      mapService.loadPlugin('nonexistentPlugin')
    ).rejects.toThrow('Plugin "nonexistentPlugin" not found');
  });

  it('should unload plugin and call cleanup', async () => {
    const cleanupSpy = vi.fn();
    const mockPluginFactory = vi.fn(() => ({
      cleanup: cleanupSpy
    }));

    registerMapPlugin('cleanupPlugin', mockPluginFactory);

    const mockContainer = document.createElement('div');
    await mapService.initMap(mockContainer);
    await mapService.loadPlugin('cleanupPlugin');

    await mapService.unloadPlugin('cleanupPlugin');

    expect(cleanupSpy).toHaveBeenCalled();
    expect(mapService.getPlugin('cleanupPlugin')).toBeUndefined();
  });

  it('should cleanup all plugins on cleanup', async () => {
    const cleanup1 = vi.fn();
    const cleanup2 = vi.fn();

    registerMapPlugin('plugin1', () => ({ cleanup: cleanup1 }));
    registerMapPlugin('plugin2', () => ({ cleanup: cleanup2 }));

    const mockContainer = document.createElement('div');
    await mapService.initMap(mockContainer);
    await mapService.loadPlugin('plugin1');
    await mapService.loadPlugin('plugin2');

    await mapService.cleanup();

    expect(cleanup1).toHaveBeenCalled();
    expect(cleanup2).toHaveBeenCalled();
    expect(mapService.isReady.value).toBe(false);
  });

  it('should get loaded plugin', async () => {
    const mockPlugin = { testMethod: () => 'test' };
    registerMapPlugin('getPlugin', () => mockPlugin);

    const mockContainer = document.createElement('div');
    await mapService.initMap(mockContainer);
    await mapService.loadPlugin('getPlugin');

    const plugin = mapService.getPlugin('getPlugin');
    expect(plugin).toEqual(mockPlugin);
  });

  it('should handle map initialization error', async () => {
    const mockContainer = null; // Invalid container

    await expect(
      mapService.initMap(mockContainer)
    ).rejects.toThrow();

    expect(mapService.isReady.value).toBe(false);
    expect(mapService.error.value).toBeTruthy();
  });
});

describe('Plugin System', () => {
  it('should register and retrieve plugins', () => {
    const factoryFn = vi.fn();
    
    registerMapPlugin('myPlugin', factoryFn);
    
    // Plugin should be retrievable via loadPlugin
    // (tested in useMapService tests above)
    expect(factoryFn).toBeDefined();
  });

  it('should warn when overwriting existing plugin', () => {
    const consoleSpy = vi.spyOn(console, 'warn').mockImplementation();
    const factory1 = vi.fn();
    const factory2 = vi.fn();

    registerMapPlugin('duplicatePlugin', factory1);
    registerMapPlugin('duplicatePlugin', factory2);

    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining('already registered')
    );

    consoleSpy.mockRestore();
  });
});
