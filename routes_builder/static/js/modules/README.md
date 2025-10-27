// README.md - Fiber Route Builder Module Structure

## Module Architecture (ES6)

### Overview
The Fiber Route Builder has been refactored into ES6 modules to improve maintainability, testability, and separation of concerns.

### Module Breakdown

#### 1. `apiClient.js` (✅ Completed)
**Purpose**: Centralized API communication layer.

**Responsibilities**:
- Abstract fetch() calls and CSRF token handling
- Normalize error responses
- Provide typed functions for backend endpoints

**Exports**:
- `fetchFibers()` - Get list of all fiber cables
- `fetchFiber(id)` - Get detailed cable info
- `createFiberManual(payload)` - Create cable with manual assignment
- `updateFiber(id, payload)` - Update cable (path, metadata)
- `removeFiber(id)` - Delete cable
- `fetchDevicePorts(deviceId)` - Get ports for device

**Usage**:
```javascript
import { fetchFibers, updateFiber } from './modules/apiClient.js';

const cables = await fetchFibers();
await updateFiber(cableId, { path: newPath });
```

#### 2. `pathState.js` (✅ Completed)
**Purpose**: Manage coordinate path state and distance calculations.

**Responsibilities**:
- Maintain `currentPath` array (lat/lng points)
- Calculate Haversine distance
- Emit change events for UI updates
- Provide immutable getters and mutable setters

**Exports**:
- `getPath()` - Get current path (read-only)
- `setPath(points)` - Replace entire path
- `addPoint(lat, lng)` - Append point
- `removePoint(index)` - Remove by index
- `updatePoint(index, lat, lng)` - Modify existing point
- `reorderPath(from, to)` - Drag & drop support
- `clearPath()` - Reset path
- `totalDistance()` - Calculate km distance
- `onPathChange(callback)` - Subscribe to changes

**Usage**:
```javascript
import { addPoint, totalDistance, onPathChange } from './modules/pathState.js';

addPoint(-16.68, -49.26);
console.log(`Distance: ${totalDistance().toFixed(2)} km`);

onPathChange(({ path, distance }) => {
  updateUI(path, distance);
});
```

#### 3. `mapCore.js` (✅ Completed)
**Purpose**: Google Maps drawing and interaction primitives.

**Responsibilities**:
- Initialize Google Maps instance
- Draw/update polylines
- Manage markers (create, drag, delete)
- Fit bounds to path
- Handle click/right-click events

**Exports**:
- `initMap(elementId, options)` - Setup map
- `getMap()` - Access map instance
- `onMapClick(callback)` - Register click handler
- `onMapRightClick(callback)` - Register right-click handler
- `drawPolyline(path, options)` - Draw/update editable path
- `clearPolyline()` - Remove current polyline
- `addMarker(position, options)` - Create draggable marker
- `removeMarker(marker)` - Delete specific marker
- `clearMarkers()` - Remove all markers
- `fitMapToBounds(path, padding)` - Auto-zoom to path
- `createCablePolyline(path, options)` - Non-editable visualization
- `attachPolylineRightClick(polyline, callback)` - Add right-click to cable

**Usage**:
```javascript
import { initMap, onMapClick, drawPolyline } from './modules/mapCore.js';

initMap('builderMap');
onMapClick(({ lat, lng }) => {
  addPoint(lat, lng);
  drawPolyline(getPath());
});
```

### Next Steps (🚧 In Progress)

#### 4. `contextMenu.js` (Planned)
- Show/hide context menu
- Update menu state based on active cable
- Position menu within viewport
- Handle conditional visibility (creating vs editing vs empty)

#### 5. `modalEditor.js` (Planned)
- Open/close manual save modal
- Populate form fields
- Handle single-port checkbox logic
- Sync destination device/port selects
- Form validation and submission

#### 6. `fiberService.js` (Planned)
- High-level orchestration (load + draw cable)
- Combine API + pathState + mapCore
- Manage `activeFiberId` and `currentFiberMeta`
- Handle cable lifecycle (create, edit, delete, reload)

#### 7. `domBindings.js` (Planned)
- Attach all event listeners
- Cache DOM elements
- Wire modules together
- Bootstrap application

### Migration Strategy

**Phase 1** (Current):
- Extract pure functions (API, path, map)
- Keep monolith functional with imports

**Phase 2** (Next):
- Extract UI components (menu, modals)
- Wire via event callbacks

**Phase 3** (Future):
- Reduce global state
- Add TypeScript types (optional)
- Consider bundler (Vite) for production

### Testing Strategy

**Unit Tests** (Future):
- Mock Google Maps API
- Test path calculations
- Test API error handling
- Validate context menu state logic

**Integration Tests**:
- Manual testing in browser
- Validate CRUD operations
- Test drag & drop
- Verify context menu flows

### Browser Compatibility
- Requires ES6 modules support
- Chrome 61+, Firefox 60+, Safari 11+, Edge 79+
- No IE11 support (acceptable for internal tools)

### Performance Considerations
- No bundler = faster dev iteration
- HTTP/2 multiplexing handles multiple module requests
- Tree-shaking not available (acceptable for <50KB total)
- Consider lazy-loading for advanced features

### Security Notes
- CSRF tokens handled automatically in `apiClient.js`
- No sensitive data in frontend state
- All mutations go through Django backend
- Same-origin policy enforced
