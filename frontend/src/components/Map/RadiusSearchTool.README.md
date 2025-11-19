# RadiusSearchTool Component

**Phase 7 Day 4** - Frontend Integration for Spatial Radius Search

## Overview

`RadiusSearchTool` is a Vue 3 component that provides an interactive map-based interface for searching sites within a specified radius using PostGIS ST_DWithin queries.

### Features

- ✅ **Click-to-search**: Click anywhere on the map to set search center
- ✅ **Interactive slider**: Adjust search radius (1-100km) with visual feedback
- ✅ **Visual circle**: Blue circle overlay showing search radius on map
- ✅ **Color-coded markers**: Sites colored by distance (green → blue → orange → red)
- ✅ **Distance labels**: Each site shows exact distance in kilometers
- ✅ **Auto-zoom**: Map automatically fits bounds to show all results
- ✅ **Hover effects**: Highlight markers on result list hover
- ✅ **Collapsible panel**: Minimize/expand search panel
- ✅ **Error handling**: Graceful error messages for API failures
- ✅ **Loading states**: Visual feedback during API requests

## Installation

The component is located at `frontend/src/components/Map/RadiusSearchTool.vue`.

### Dependencies

```json
{
  "vue": "^3.x",
  "vue3-google-map": "^0.x",
  "@/utils/debounce": "utility function",
  "@/stores/*": "optional for state management"
}
```

## Basic Usage

### Integrate with MapView

```vue
<template>
  <MapView 
    :enableRadiusSearch="true"
    :sidebarCollapsed="false"
  />
</template>

<script setup>
import MapView from '@/components/MapView.vue';
</script>
```

### Standalone Usage

```vue
<template>
  <div style="position: relative; width: 100%; height: 100vh;">
    <GoogleMap
      ref="mapRef"
      :api-key="apiKey"
      :center="{ lat: -15.7801, lng: -47.9292 }"
      :zoom="12"
      style="width: 100%; height: 100%;"
    />
    
    <RadiusSearchTool
      :map-ref="mapRef"
      :initial-radius="10"
      @search-completed="handleSearchComplete"
      @search-error="handleSearchError"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { GoogleMap } from 'vue3-google-map';
import RadiusSearchTool from '@/components/Map/RadiusSearchTool.vue';

const mapRef = ref(null);
const apiKey = 'YOUR_API_KEY';

function handleSearchComplete(results) {
  console.log(`Found ${results.count} sites`);
}

function handleSearchError(error) {
  console.error('Search failed:', error);
}
</script>
```

## Props

| Prop | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `mapRef` | Object | Yes | - | Reference to Google Maps instance (`{ map: google.maps.Map }`) |
| `autoActivate` | Boolean | No | `false` | Auto-expand panel on mount |
| `initialRadius` | Number | No | `10` | Initial search radius in kilometers (1-100) |

### Prop Validation

```javascript
{
  mapRef: {
    type: Object,
    required: true
  },
  autoActivate: {
    type: Boolean,
    default: false
  },
  initialRadius: {
    type: Number,
    default: 10,
    validator: (value) => value >= 1 && value <= 100
  }
}
```

## Events

| Event | Payload | Description |
|-------|---------|-------------|
| `search-started` | - | Emitted when search begins (before API call) |
| `search-completed` | `Object` | Emitted when search succeeds (full API response) |
| `search-error` | `Error` | Emitted when search fails |
| `results-changed` | `Array<Site>` | Emitted when results update (sites array only) |

### Event Payloads

**`search-completed` payload:**
```javascript
{
  count: 3,
  center: {
    lat: -15.7801,
    lng: -47.9292
  },
  radius_km: 10,
  sites: [
    {
      id: 1,
      display_name: "Site Name",
      latitude: -15.7801,
      longitude: -47.9292,
      distance_km: 0.0
    },
    // ...
  ]
}
```

**`search-error` payload:**
```javascript
Error {
  message: "Latitude must be between -90 and 90",
  // or "HTTP 400: Bad Request"
  // or "radius_km cannot exceed 1000km"
}
```

**`results-changed` payload:**
```javascript
[
  {
    id: 1,
    display_name: "Site A",
    latitude: -15.7801,
    longitude: -47.9292,
    distance_km: 0.0
  },
  // ...
]
```

## API Integration

The component calls `/api/v1/inventory/sites/radius` (Phase 7 Day 3 endpoint).

### Request Format

```http
GET /api/v1/inventory/sites/radius?lat=-15.7801&lng=-47.9292&radius_km=10&limit=100
```

### Parameters

| Parameter | Type | Required | Validation | Description |
|-----------|------|----------|------------|-------------|
| `lat` | float | Yes | -90 ≤ lat ≤ 90 | Latitude (WGS84) |
| `lng` | float | Yes | -180 ≤ lng ≤ 180 | Longitude (WGS84) |
| `radius_km` | float | Yes | 0 < r ≤ 1000 | Search radius in kilometers |
| `limit` | int | No | 1 ≤ limit ≤ 500 | Max results (default: 100) |

### Response Format

**Success (200 OK):**
```json
{
  "count": 2,
  "center": { "lat": -15.7801, "lng": -47.9292 },
  "radius_km": 10,
  "sites": [
    {
      "id": 1,
      "display_name": "Brasília Center",
      "latitude": -15.7801,
      "longitude": -47.9292,
      "distance_km": 0.0
    },
    {
      "id": 2,
      "display_name": "Brasília North",
      "latitude": -15.7350,
      "longitude": -47.9292,
      "distance_km": 5.01
    }
  ]
}
```

**Error (400 Bad Request):**
```json
{
  "error": "Latitude must be between -90 and 90"
}
```

## User Interface

### Panel Layout

```
┌─────────────────────────────┐
│ 🔍 Busca por Raio      [▲]  │  ← Header (collapsible)
├─────────────────────────────┤
│ 📍 Clique no mapa para      │  ← Instructions (initial state)
│    definir o ponto central  │
│    da busca                 │
└─────────────────────────────┘

After click:
┌─────────────────────────────┐
│ 🔍 Busca por Raio      [▲]  │
├─────────────────────────────┤
│ Centro: -15.780100,         │  ← Center coordinates
│         -47.929200     [✕]  │     (clear button)
│                             │
│ Raio: 10 km                 │  ← Slider label
│ [====|====================] │  ← Radius slider (1-100km)
│ 1km  25km  50km  75km  100km│     (color gradient)
│                             │
│ [🔎 Buscar Sites]           │  ← Search button
│                             │
│ 3 site(s) encontrado(s)     │  ← Results summary
│ ┌─────────────────────────┐ │
│ │ Brasília Center         │ │  ← Result item (clickable)
│ │ 📍 0 km                  │ │     (hover highlights marker)
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ Brasília North          │ │
│ │ 📍 5.01 km               │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ Asa Sul                 │ │
│ │ 📍 7.45 km               │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

### Map Overlays

1. **Search Circle**: Blue circle with 15% opacity fill showing search radius
2. **Result Markers**: Numbered circles colored by distance
   - Green (🟢): 0-25% of radius
   - Blue (🔵): 25-50% of radius
   - Orange (🟠): 50-75% of radius
   - Red (🔴): 75-100% of radius
3. **InfoWindows**: Click marker to see site details + distance

### States

**Initial State:**
- Panel expanded
- Instructions visible
- Map clickable

**Search Active:**
- Center coordinates displayed
- Radius slider enabled
- Search button enabled

**Loading:**
- Search button disabled
- Spinner animation
- Button text: "Buscando..."

**Results:**
- Result count displayed
- Sites list scrollable
- Markers rendered on map
- Circle overlay visible

**No Results:**
- Message: "Nenhum site encontrado neste raio"
- Empty results list

**Error:**
- Red error banner
- Error message from API
- Search remains active (can retry)

## Customization

### Styling

Override component styles using `:deep()` selector:

```vue
<style>
/* Position panel on left */
:deep(.search-panel) {
  left: 10px;
  right: auto;
}

/* Custom theme */
:deep(.panel-header) {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

:deep(.search-button) {
  background: #10b981;
}

/* Custom marker colors */
:deep(.result-item:hover) {
  background: #d1fae5;
  border-color: #10b981;
}
</style>
```

### Marker Color Logic

Override `getMarkerColor()` method via mixin or extend component:

```javascript
function getMarkerColor(distanceKm) {
  const ratio = distanceKm / radiusKm.value;
  
  // Custom color scheme
  if (ratio < 0.20) return '#00ff00'; // Bright green
  if (ratio < 0.40) return '#00ccff'; // Cyan
  if (ratio < 0.60) return '#ffaa00'; // Gold
  if (ratio < 0.80) return '#ff5500'; // Orange-red
  return '#ff0000'; // Bright red
}
```

## Testing

### Unit Tests (Vitest)

Run tests:
```bash
npm run test:unit -- RadiusSearchTool.test.js
```

Coverage areas:
- ✅ Component rendering
- ✅ Panel toggle
- ✅ Search center state
- ✅ API integration (mocked)
- ✅ Error handling
- ✅ Event emissions
- ✅ Marker color calculation
- ✅ Props validation

### E2E Tests (Playwright)

Run tests:
```bash
npm run test:e2e -- radius-search.spec.js
```

Scenarios:
- ✅ Panel display and interaction
- ✅ Map click to set center
- ✅ Search execution and results display
- ✅ Slider adjustment
- ✅ No results handling
- ✅ Error display
- ✅ Clear search state
- ✅ Hover effects
- ✅ API request validation
- ✅ Loading states
- ✅ Keyboard navigation

## Performance

### Optimization Strategies

1. **Debounced Slider**: 500ms delay prevents excessive API calls
2. **Lazy Marker Creation**: Markers created only when results available
3. **Circle Reuse**: Single circle object updated on radius change
4. **Result Limit**: Default 100 sites, max 500 (API enforced)
5. **Auto-zoom Throttle**: Bounds adjustment throttled to prevent jank

### Expected Performance

| Scenario | Response Time | Notes |
|----------|---------------|-------|
| Click to search | < 50ms | Instant UI update |
| API call (10km) | 10-50ms | ST_DWithin query |
| API call (100km) | 30-100ms | Larger dataset |
| Render 100 markers | 100-200ms | Google Maps API |
| Slider drag | 0ms | Debounced (500ms) |

## Troubleshooting

### Common Issues

**1. Map click not working**

**Symptom:** Clicking map does nothing

**Causes:**
- `mapRef` not provided
- Google Maps not loaded
- Event listener not attached

**Fix:**
```javascript
// Ensure mapRef.map exists
console.log('mapRef.map:', mapRef.map);

// Check listener setup in component lifecycle
onMounted(() => {
  if (map.value) {
    console.log('Map available, attaching listener');
    setupMapClickListener();
  }
});
```

**2. API errors**

**Symptom:** Error message displayed after search

**Common errors:**
- `Latitude must be between -90 and 90`: Invalid coordinates
- `radius_km cannot exceed 1000km`: Radius too large
- `HTTP 401`: Authentication required (session expired)
- `HTTP 500`: Server error (check backend logs)

**Fix:**
- Check coordinates are valid WGS84
- Ensure radius slider is clamped 1-100km
- Re-login if session expired
- Check backend logs for server errors

**3. Markers not appearing**

**Symptom:** API returns results but markers not visible

**Causes:**
- Google Maps not fully initialized
- Marker creation failed
- Z-index conflict

**Fix:**
```javascript
// Wait for map idle before drawing
google.maps.event.addListenerOnce(map.value, 'idle', () => {
  drawResultMarkers(sites);
});

// Check marker z-index
console.log('Marker zIndex:', marker.getZIndex());
```

**4. Panel not visible**

**Symptom:** Panel missing from UI

**Causes:**
- `apiKey` prop missing in MapView
- CSS position conflict
- Panel collapsed by default

**Fix:**
```javascript
// Check API key
console.log('API Key:', apiKey);

// Force panel expansion
isPanelCollapsed.value = false;
```

## Browser Compatibility

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | 90+ | ✅ Full support |
| Firefox | 88+ | ✅ Full support |
| Safari | 14+ | ✅ Full support |
| Edge | 90+ | ✅ Full support |
| Mobile Chrome | Latest | ✅ Touch optimized |
| Mobile Safari | Latest | ✅ Touch optimized |

## Accessibility

### Keyboard Navigation

- `Tab`: Navigate between interactive elements
- `Enter/Space`: Toggle panel, trigger search
- `Arrow keys`: Adjust slider value

### Screen Readers

- ARIA labels on all buttons
- Semantic HTML structure
- Status updates announced

### WCAG Compliance

- ✅ Color contrast > 4.5:1
- ✅ Focus indicators visible
- ✅ Touch targets ≥ 44x44px
- ✅ Keyboard accessible

## Future Enhancements

### Planned Features (Phase 7 Day 5+)

- [ ] **SWR Cache**: Cache common radius queries (5km, 10km, 50km)
- [ ] **Geolocation**: "Search near me" button
- [ ] **History**: Save recent searches
- [ ] **Export**: Download results as CSV/GeoJSON
- [ ] **Filters**: Filter sites by type, status, etc.
- [ ] **Heatmap**: Show site density visualization
- [ ] **Multiple searches**: Compare different radii simultaneously
- [ ] **Polygon search**: Draw custom search area

## License

Internal use only - MapsProveFiber project

## Contributors

- **Phase 7 Day 4**: GitHub Copilot + Development Team
- **Backend API**: Phase 7 Day 3 implementation
- **PostGIS ST_DWithin**: Phase 7 Day 2 optimization

## Related Documentation

- [Phase 7 Day 3 Completion Report](../../../doc/reports/phases/PHASE_7_DAY_3_COMPLETION.md)
- [Phase 7 Summary](../../../doc/reports/phases/PHASE_7_SUMMARY.md)
- [API Endpoint Documentation](../../../backend/inventory/api/spatial.py)
- [ST_DWithin Implementation](../../../backend/inventory/usecases/sites.py)

---

**Last Updated:** November 19, 2025  
**Component Version:** 1.0.0  
**Phase:** 7 Day 4
