/**
 * RadiusSearchTool.test.js - Unit Tests
 * Phase 7 Day 4
 * 
 * Tests for RadiusSearchTool component logic
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import RadiusSearchTool from '@/components/Map/RadiusSearchTool.vue';

// Mock Google Maps API
global.google = {
  maps: {
    event: {
      addListener: vi.fn((map, event, handler) => ({ remove: vi.fn() })),
      removeListener: vi.fn(),
      addListenerOnce: vi.fn()
    },
    Circle: vi.fn(function(options) {
      this.options = options;
      this.setMap = vi.fn();
      this.setRadius = vi.fn();
    }),
    Marker: vi.fn(function(options) {
      this.options = options;
      this.setMap = vi.fn();
      this.addListener = vi.fn();
      this.getPosition = vi.fn(() => ({
        lat: () => options.position.lat,
        lng: () => options.position.lng
      }));
      this.getIcon = vi.fn(() => options.icon);
      this.setIcon = vi.fn();
    }),
    InfoWindow: vi.fn(function(options) {
      this.options = options;
      this.open = vi.fn();
      this.close = vi.fn();
    }),
    LatLngBounds: vi.fn(function() {
      this.extend = vi.fn();
    }),
    SymbolPath: {
      CIRCLE: 0
    }
  }
};

// Mock fetch
global.fetch = vi.fn();

describe('RadiusSearchTool', () => {
  let wrapper;
  let mockMapRef;

  beforeEach(() => {
    mockMapRef = {
      map: {
        addListener: vi.fn((event, handler) => ({ remove: vi.fn() })),
        setCenter: vi.fn(),
        setZoom: vi.fn(),
        fitBounds: vi.fn(),
        getZoom: vi.fn(() => 12)
      }
    };

    global.fetch.mockReset();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('renders panel with correct initial state', () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    expect(wrapper.find('.search-panel').exists()).toBe(true);
    expect(wrapper.find('.panel-header h3').text()).toBe('🔍 Busca por Raio');
    expect(wrapper.find('.instructions').exists()).toBe(true);
  });

  it('toggles panel collapse state', async () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    const toggleButton = wrapper.find('.toggle-button');
    
    // Initially expanded
    expect(wrapper.find('.search-panel').classes()).not.toContain('collapsed');
    expect(wrapper.find('.panel-content').exists()).toBe(true);

    // Collapse
    await toggleButton.trigger('click');
    await nextTick();
    
    expect(wrapper.find('.search-panel').classes()).toContain('collapsed');
    expect(wrapper.find('.panel-content').exists()).toBe(false);

    // Expand again
    await toggleButton.trigger('click');
    await nextTick();
    
    expect(wrapper.find('.search-panel').classes()).not.toContain('collapsed');
  });

  it('initializes with custom radius', () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef,
        initialRadius: 25
      }
    });

    // Click map to enable search (mocked)
    wrapper.vm.searchCenter = { lat: -15.7801, lng: -47.9292 };
    
    expect(wrapper.vm.radiusKm).toBe(25);
  });

  it('shows center info after setting search center', async () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    expect(wrapper.find('.center-info').exists()).toBe(false);
    expect(wrapper.find('.instructions').exists()).toBe(true);

    // Simulate map click
    wrapper.vm.searchCenter = { lat: -15.7801, lng: -47.9292 };
    await nextTick();

    expect(wrapper.find('.center-info').exists()).toBe(true);
    expect(wrapper.find('.instructions').exists()).toBe(false);
    expect(wrapper.find('.center-info .value').text()).toContain('-15.780100');
    expect(wrapper.find('.center-info .value').text()).toContain('-47.929200');
  });

  it('clears search state when clear button clicked', async () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    // Set search state
    wrapper.vm.searchCenter = { lat: -15.7801, lng: -47.9292 };
    wrapper.vm.searchResults = {
      count: 5,
      sites: [{ id: 1, display_name: 'Test Site' }]
    };
    await nextTick();

    expect(wrapper.find('.center-info').exists()).toBe(true);
    expect(wrapper.find('.results-summary').exists()).toBe(true);

    // Click clear button
    await wrapper.find('.clear-button').trigger('click');
    await nextTick();

    expect(wrapper.vm.searchCenter).toBe(null);
    expect(wrapper.vm.searchResults).toBe(null);
    expect(wrapper.find('.center-info').exists()).toBe(false);
  });

  it('executes search with valid parameters', async () => {
    const mockResponse = {
      count: 2,
      center: { lat: -15.7801, lng: -47.9292 },
      radius_km: 10,
      sites: [
        {
          id: 1,
          display_name: 'Site A',
          latitude: -15.7801,
          longitude: -47.9292,
          distance_km: 0.0
        },
        {
          id: 2,
          display_name: 'Site B',
          latitude: -15.7350,
          longitude: -47.9292,
          distance_km: 5.01
        }
      ]
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    wrapper.vm.searchCenter = { lat: -15.7801, lng: -47.9292 };
    wrapper.vm.radiusKm = 10;

    await wrapper.vm.executeSearch();
    await nextTick();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/inventory/sites/radius'),
      expect.objectContaining({
        method: 'GET',
        credentials: 'include'
      })
    );

    const fetchUrl = global.fetch.mock.calls[0][0];
    expect(fetchUrl).toContain('lat=-15.7801');
    expect(fetchUrl).toContain('lng=-47.9292');
    expect(fetchUrl).toContain('radius_km=10');
    expect(fetchUrl).toContain('limit=100');

    expect(wrapper.vm.searchResults).toEqual(mockResponse);
  });

  it('emits search-completed event with results', async () => {
    const mockResponse = {
      count: 1,
      center: { lat: -15.7801, lng: -47.9292 },
      radius_km: 10,
      sites: [{ id: 1, display_name: 'Test', distance_km: 0.0 }]
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    wrapper.vm.searchCenter = { lat: -15.7801, lng: -47.9292 };
    await wrapper.vm.executeSearch();

    expect(wrapper.emitted('search-completed')).toBeTruthy();
    expect(wrapper.emitted('search-completed')[0][0]).toEqual(mockResponse);
  });

  it('handles API error gracefully', async () => {
    const errorResponse = {
      error: 'Latitude must be between -90 and 90'
    };

    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => errorResponse
    });

    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    wrapper.vm.searchCenter = { lat: 95, lng: -47.9292 }; // Invalid lat
    await wrapper.vm.executeSearch();
    await nextTick();

    expect(wrapper.vm.searchError).toContain('Latitude must be between');
    expect(wrapper.emitted('search-error')).toBeTruthy();
  });

  it('displays results list correctly', async () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    wrapper.vm.searchCenter = { lat: -15.7801, lng: -47.9292 };
    wrapper.vm.searchResults = {
      count: 3,
      sites: [
        { id: 1, display_name: 'Site A', distance_km: 0.0 },
        { id: 2, display_name: 'Site B', distance_km: 5.01 },
        { id: 3, display_name: 'Site C', distance_km: 9.85 }
      ]
    };
    await nextTick();

    expect(wrapper.find('.results-summary').exists()).toBe(true);
    expect(wrapper.find('.result-count').text()).toBe('3 site(s) encontrado(s)');
    
    const resultItems = wrapper.findAll('.result-item');
    expect(resultItems).toHaveLength(3);
    expect(resultItems[0].find('.site-name').text()).toBe('Site A');
    expect(resultItems[0].find('.site-distance').text()).toBe('📍 0 km');
    expect(resultItems[1].find('.site-name').text()).toBe('Site B');
    expect(resultItems[1].find('.site-distance').text()).toBe('📍 5.01 km');
  });

  it('shows no results message when count is 0', async () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    wrapper.vm.searchCenter = { lat: 0, lng: 0 }; // Ocean
    wrapper.vm.searchResults = {
      count: 0,
      sites: []
    };
    await nextTick();

    expect(wrapper.find('.results-summary').exists()).toBe(true);
    expect(wrapper.find('.no-results').exists()).toBe(true);
    expect(wrapper.find('.no-results').text()).toContain('Nenhum site encontrado');
  });

  it('calculates correct marker color based on distance', () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef,
        initialRadius: 100
      }
    });

    // Very close (< 25% of radius)
    expect(wrapper.vm.getMarkerColor(10)).toBe('#10b981'); // Green
    
    // Close (25-50% of radius)
    expect(wrapper.vm.getMarkerColor(40)).toBe('#3b82f6'); // Blue
    
    // Medium (50-75% of radius)
    expect(wrapper.vm.getMarkerColor(60)).toBe('#f59e0b'); // Orange
    
    // Far (>75% of radius)
    expect(wrapper.vm.getMarkerColor(85)).toBe('#ef4444'); // Red
  });

  it('auto-activates panel when autoActivate prop is true', () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef,
        autoActivate: true
      }
    });

    expect(wrapper.vm.isPanelCollapsed).toBe(false);
  });

  it('sets up map click listener on mount', async () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    await nextTick();

    expect(mockMapRef.map.addListener).toHaveBeenCalledWith(
      'click',
      expect.any(Function)
    );
  });

  it('updates circle radius when slider changes', async () => {
    wrapper = mount(RadiusSearchTool, {
      props: {
        mapRef: mockMapRef
      }
    });

    wrapper.vm.searchCenter = { lat: -15.7801, lng: -47.9292 };
    
    // Create mock circle
    const mockCircle = {
      setRadius: vi.fn(),
      setMap: vi.fn()
    };
    wrapper.vm.searchCircle = mockCircle;

    // Change radius
    wrapper.vm.radiusKm = 50;
    await nextTick();

    expect(mockCircle.setRadius).toHaveBeenCalledWith(50000); // 50km in meters
  });

  it('validates initialRadius prop', () => {
    const validator = RadiusSearchTool.props.initialRadius.validator;
    
    expect(validator(1)).toBe(true);
    expect(validator(50)).toBe(true);
    expect(validator(100)).toBe(true);
    expect(validator(0)).toBe(false);
    expect(validator(101)).toBe(false);
    expect(validator(-5)).toBe(false);
  });
});
