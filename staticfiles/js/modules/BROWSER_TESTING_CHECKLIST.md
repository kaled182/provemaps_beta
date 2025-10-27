# Browser Testing Checklist for Module Integration

## Pre-Testing Setup
- [ ] Open browser DevTools (F12)
- [ ] Navigate to: http://localhost:8000/routes_builder/fiber-route-builder/
- [ ] Check Console tab for any errors on page load
- [ ] Verify no 404s in Network tab for module files

## Module Loading Tests
### Expected in Console (No Errors):
```
✓ Module apiClient.js loaded
✓ Module pathState.js loaded  
✓ Module mapCore.js loaded
✓ Google Maps API initialized
✓ Map rendered in #builderMap container
```

### Check Network Tab:
- [ ] apiClient.js - 200 OK
- [ ] pathState.js - 200 OK
- [ ] mapCore.js - 200 OK
- [ ] fiber_route_builder.js - 200 OK
- [ ] No CORS errors

## Map Initialization Tests
- [ ] **Map displays** with correct center (Goiás, Brazil region)
- [ ] **Zoom controls** work (+ / - buttons)
- [ ] **Map type selector** visible (terrain/satellite toggle)
- [ ] **No console errors** on map load

## Path Drawing Tests (Scenario A: Empty State)
1. [ ] Click map → **marker appears**
2. [ ] Click again → **second marker appears**
3. [ ] [ ] **Red polyline** connects markers
4. [ ] **Distance display** updates automatically
5. [ ] **Point list** shows coordinates
6. [ ] **Save button** enables (when ≥2 points)
7. [ ] Right-click → **context menu appears** with "Save New Cable" option

## Marker Interaction Tests
- [ ] **Drag marker** → polyline updates in real-time
- [ ] **Drag marker** → distance recalculates automatically
- [ ] **Click remove icon** on marker → marker disappears
- [ ] **Remove marker** → polyline redraws correctly
- [ ] **Remove marker** → point count updates in list

## Context Menu Tests (Empty State)
### Right-click map:
- [ ] Menu displays at cursor position
- [ ] Shows "Import KML" option
- [ ] Shows "Save New Cable" option (if ≥2 points)
- [ ] Shows "Clear Points" option (if points exist)
- [ ] Click outside menu → menu closes
- [ ] ESC key → menu closes

## Cable Creation Tests (Scenario B: Creating New)
### Steps:
1. [ ] Draw 2+ points on map
2. [ ] Right-click → select "Save New Cable"
3. [ ] Modal opens with form
4. [ ] Fill required fields (name, origin device, origin port)
5. [ ] Click "Save"
6. [ ] Success alert appears
7. [ ] Map clears
8. [ ] New cable appears in visualization (blue line)

### Verify in Console:
```javascript
// Should see:
POST /zabbix_api/api/fibers/ → 201 Created
GET /zabbix_api/api/fibers/ → 200 OK (reload list)
```

## Cable Visualization Tests
### On page load:
- [ ] **All cables load** automatically after ~300ms
- [ ] **Blue polylines** appear for each cable
- [ ] Console shows: `Visualization: X cables loaded.`
- [ ] No error alerts

### Right-click existing cable:
- [ ] Context menu shows **cable-specific options**
- [ ] Shows cable name with 📌 icon
- [ ] Shows "Edit Cable Details" option
- [ ] Shows "Save Path" option (if edited)
- [ ] Shows "Delete Cable" option
- [ ] Shows "Reload This Cable" option

## Cable Editing Tests (Scenario C: Selected Cable)
### Steps:
1. [ ] Right-click blue cable → select "Edit Cable Details"
2. [ ] Cable loads → **markers appear** at path points
3. [ ] Polyline changes from **blue → red** (editing mode)
4. [ ] Cable name shows in context menu with "- EDITING" suffix
5. [ ] **Drag markers** to modify path
6. [ ] Add points by clicking map
7. [ ] Remove points via marker remove icons
8. [ ] Right-click → "Save Path" option enabled (if ≥2 points)
9. [ ] Save changes → success alert
10. [ ] Map reloads → cable shows with new path (blue)

## Cable Selection Tests
### Fiber dropdown:
- [ ] Dropdown populates with all cables
- [ ] Select cable → **loads path** in editing mode
- [ ] Shows cable details in context menu
- [ ] Save button state updates correctly

## Cable Deletion Tests
### Steps:
1. [ ] Right-click cable → "Delete Cable"
2. [ ] Confirmation prompt appears
3. [ ] Confirm → DELETE request sent
4. [ ] Success alert appears
5. [ ] Cable removed from visualization
6. [ ] Fiber dropdown updates (cable removed)

## Import KML Tests
### Steps:
1. [ ] Right-click empty map → "Import KML"
2. [ ] File picker opens
3. [ ] Select valid KML file
4. [ ] Path imports → markers appear
5. [ ] Polyline draws correctly
6. [ ] Can save imported path as new cable

## State Management Tests
### Verify pub/sub pattern:
- [ ] **Add point** → distance updates automatically (no manual refresh call)
- [ ] **Remove point** → polyline redraws automatically
- [ ] **Drag marker** → all UI elements update (list, distance, button state)
- [ ] **Clear path** → all UI elements reset

### Check Console for:
```javascript
// Should NOT see these errors:
❌ "currentPath is not defined"
❌ "redrawPolyline is not a function"
❌ TypeError: Cannot read properties of undefined
```

## API Integration Tests
### Verify apiClient usage:
- [ ] **Fetch cables** uses apiClient.fetchFibers()
- [ ] **Load detail** uses apiClient.fetchFiber(id)
- [ ] **Create cable** uses apiClient.createFiberManual(payload)
- [ ] **Update cable** uses apiClient.updateFiber(id, payload)
- [ ] **Delete cable** uses apiClient.removeFiber(id)
- [ ] **CSRF token** sent automatically (check request headers)

### Check Network Tab Headers:
```
X-CSRFToken: <token_value>  ← Should be present
Content-Type: application/json
```

## Error Handling Tests
### Test failure scenarios:
- [ ] **Network offline** → graceful error message
- [ ] **Invalid cable ID** → error alert (not crash)
- [ ] **Backend 500 error** → error logged to console
- [ ] **Missing CSRF token** → request fails with clear error

## Performance Tests
- [ ] **Cable visualization loads** in <2 seconds (for ~20 cables)
- [ ] **Marker dragging** smooth (no lag)
- [ ] **Path updates** instant (no visible delay)
- [ ] **No memory leaks** (check DevTools Memory tab after 5 minutes of use)

## Regression Tests (Ensure Nothing Broke)
- [ ] **Device selection** in modal loads ports correctly
- [ ] **Single port mode** checkbox works
- [ ] **Port filtering** syncs between devices
- [ ] **Form validation** prevents invalid submissions
- [ ] **Reload button** refreshes cable list
- [ ] **Clear button** resets map state

## Edge Cases
- [ ] **Create cable with 1 point** → validation error
- [ ] **Delete all points while editing** → activeFiberId clears
- [ ] **Switch cables without saving** → warns about unsaved changes (if implemented)
- [ ] **Import KML over existing path** → replaces current path
- [ ] **Right-click during creation** → shows creation-specific menu
- [ ] **Right-click during editing** → shows editing-specific menu

## Console Error Checks
### Should NOT appear:
```javascript
❌ Uncaught ReferenceError: currentPath is not defined
❌ Uncaught TypeError: redrawPolyline is not a function
❌ Failed to load module: ./modules/apiClient.js
❌ CORS policy blocked
❌ 404 Not Found: /static/js/modules/...
```

### Should appear (expected):
```javascript
✓ Visualization: X cables loaded.
✓ (No errors)
```

## Module Isolation Tests
### In browser console, verify:
```javascript
// Modules are NOT in global scope:
typeof fetchFibers === 'undefined'  // ✓ true (good!)
typeof getPath === 'undefined'      // ✓ true (good!)
typeof initializeMap === 'undefined' // ✓ true (good!)

// Only main file exports necessary globals:
typeof clearMapAndResetState === 'function'  // ✓ true (for KML import)
```

## Test Results Template

### Passed: _____ / 100 tests
### Failed: _____ tests
### Critical Issues: _____

#### Failed Tests (if any):
1. **Test Name:** ___________
   - **Expected:** ___________
   - **Actual:** ___________
   - **Console Error:** ___________

2. **Test Name:** ___________
   - **Expected:** ___________
   - **Actual:** ___________
   - **Console Error:** ___________

## Next Actions Based on Results

### If All Tests Pass (✅):
- Proceed with **contextMenu.js extraction** (Sprint 2 Phase 2)
- Proceed with **modalEditor.js extraction** (Sprint 2 Phase 3)
- Document success in CHANGELOG

### If Critical Issues Found (❌):
- **Rollback** modular changes (git checkout)
- **Debug** specific failing test
- **Fix** issue in module or integration code
- **Re-test** until passing

### If Minor Issues Found (⚠️):
- Create **GitHub Issues** for each problem
- **Document** workaround if available
- **Prioritize** fixes in next sprint

## Testing Completed By: __________
## Date: __________
## Browser(s) Tested: Chrome _____ / Firefox _____ / Safari _____
## Overall Status: ✅ PASS / ⚠️ PARTIAL / ❌ FAIL

---

**Note:** This comprehensive checklist covers all integration points. Focus on critical path tests first (map init, path drawing, cable CRUD) before testing edge cases.
