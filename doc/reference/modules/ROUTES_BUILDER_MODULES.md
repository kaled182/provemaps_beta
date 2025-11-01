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

#### 4. `contextMenu.js` (✅ Completed)
**Purpose**: Right-click context menu display and state management.

**Responsibilities**:
- Show/hide context menu at cursor position
- Update menu sections based on application state (3 scenarios)
- Auto-adjust position to stay within viewport
- Handle keyboard/click-outside to close menu

**Exports**:
- `initContextMenu()` - Initialize module, cache DOM refs
- `showContextMenu(x, y)` - Display menu at coordinates
- `hideContextMenu()` - Hide menu
- `updateContextMenuState(context)` - Update visible sections
- `isContextMenuVisible()` - Check visibility state
- `getContextMenuPosition()` - Get current menu position

**Context Object**:
```javascript
{
  hasActiveFiber: boolean,  // Cable selected?
  fiberMeta: object,        // Cable metadata (name, id)
  pathLength: number        // Number of points in path
}
```

**Three Scenarios**:
- **Scenario A (Empty)**: No cable, no points → Show "Import KML" + "Reload All"
- **Scenario B (Creating)**: No cable, has points → Show "Save New Cable" + "Clear Points"
- **Scenario C (Editing)**: Has cable → Show cable info + "Edit" + "Save Path" + "Delete"

**Usage**:
```javascript
import { initContextMenu, showContextMenu, updateContextMenuState } from './modules/contextMenu.js';

// Initialize once on page load
initContextMenu();

// Show menu on right-click
map.on('rightclick', (event) => {
  showContextMenu(event.clientX, event.clientY);
  updateContextMenuState({
    hasActiveFiber: !!activeFiberId,
    fiberMeta: currentFiberMeta,
    pathLength: getPath().length,
  });
});
```

### Next Steps (🚧 Planned)

#### 5. `modalEditor.js` (✅ Completed)
**Purpose**: Cable creation/editing modal form management.

**Responsibilities**:
- Open/close modal with CSS animations
- Populate form fields for editing mode
- Handle single-port checkbox logic (device sync)
- Load device ports into dropdowns
- Form validation and state management

**Exports**:
- `initModalEditor()` - Initialize module, cache DOM refs, setup listeners
- `openModalForCreate(distance)` - Open modal for new cable
- `openModalForEdit(cableData, distance)` - Open modal for editing
- `closeModal()` - Close modal with fade-out animation
- `getEditingFiberId()` - Get current editing fiber ID
- `isEditMode()` - Check if in editing mode
- `resetForm()` - Reset form to initial state

**Cable Data Object**:
```javascript
{
  id: number,
  name: string,
  single_port: boolean,
  origin_device_id: number,
  origin_port_id: number,
  dest_device_id: number,
  dest_port_id: number
}
```

**Features**:
- **Single-port mode**: Auto-syncs destination device with origin, disables port selection
- **Port loading**: Async loading with loading states ("Carregando...", "Selecione...")
- **Retry logic**: Ensures ports are loaded before setting selected value
- **Animation**: Tailwind CSS opacity and scale transitions
- **Auto-focus**: Focuses name input when modal opens

**Usage**:
```javascript
import { initModalEditor, openModalForCreate, openModalForEdit } from './modules/modalEditor.js';

// Initialize once
initModalEditor();

// Create new cable
openModalForCreate(12.5); // distance in km

// Edit existing cable
openModalForEdit({
  id: 123,
  name: 'Fiber Cable A-B',
  single_port: false,
  origin_device_id: 10,
  origin_port_id: 5,
  dest_device_id: 20,
  dest_port_id: 8
}, 15.3);
```

### Next Steps (🚧 Planned)

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
