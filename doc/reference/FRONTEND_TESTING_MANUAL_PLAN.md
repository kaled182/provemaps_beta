
# Manual Test Plan - Modular Frontend

Date: 27 October 2025
Goal: Validate that the modular refactor of `fiber_route_builder.js` introduced no regressions
Scope: All workflows for cable creation, editing, deletion, and visualization

---

## Prerequisites

### Environment
- [ ] Docker services running (`docker compose ps`)
- [ ] Django web server available at http://localhost:8000
- [ ] MariaDB seeded with test data
- [ ] Redis cache operational
- [ ] User authenticated in the system

### Required Test Data
- [ ] At least two Sites registered
- [ ] At least three Devices registered
- [ ] Google Maps API key configured (when applicable)

---

## Test Scenarios

### Scenario 1: Map Initialization

Goal: Ensure the map loads correctly with ES6 modules.

#### Steps
1. Open http://localhost:8000/routes/builder/
2. Wait for the page to finish loading
3. Inspect the browser console (F12)

#### Success Criteria
- [ ] Map renders: Leaflet map visible with tiles loaded
- [ ] No JavaScript errors: Console free of import or export errors
- [ ] Modules load correctly: verify in DevTools > Network > JS files
  - [ ] `apiClient.js` loaded
  - [ ] `mapCore.js` loaded
  - [ ] `contextMenu.js` loaded
  - [ ] `modalEditor.js` loaded
  - [ ] `cableService.js` loaded
  - [ ] `pathState.js` loaded
  - [ ] `uiHelpers.js` loaded
- [ ] Core buttons visible: "New Cable", "Save", "Cancel"
- [ ] Sidebar functional: list of cables displayed when available

#### Test Notes
```
Date/Time: _________________
Browser: ___________________
Result: [ ] PASS  [ ] FAIL
Notes:
_________________________________
_________________________________
```

---

### Scenario 2: Create New Cable (Full Workflow)

Goal: Validate end-to-end cable creation.

#### Steps
1. Click the "New Cable" button or equivalent control
2. Confirm the cursor switches to drawing mode (crosshair)
3. Click three to five points on the map to draw the route
4. Right-click or double-click to finish the path
5. Complete the modal form:
   - Cable name: `TEST_CABLE_001`
   - Type: select from the dropdown
   - Distance: auto-calculated
   - Notes: `Modularization test`
6. Click "Save"
7. Wait for the confirmation message

#### Success Criteria
- [ ] Drawing mode activates: cursor changes to crosshair
- [ ] Polyline rendered: line appears on the map following the clicks
- [ ] Correct styling: line uses the expected default color
- [ ] Modal opens: edit form appears after finishing the drawing
- [ ] Fields populated: distance auto-calculated accurately
- [ ] Validation behaves: required fields enforced
- [ ] POST request succeeds: 201 Created visible in the Network tab
- [ ] Cable stored: entry appears in the cable list
- [ ] Notification displayed: success toast or alert shown
- [ ] State reset: drawing mode disabled after saving

#### Test Notes
```
Date/Time: _________________
ID of created cable: _______
Result: [ ] PASS  [ ] FAIL
Notes:
_________________________________
_________________________________
```

---

### Scenario 3: View Existing Cables

Goal: Confirm previously saved cables render correctly.

#### Steps
1. Reload the page
2. Wait for existing cables to load
3. Review the cable list in the sidebar
4. Click multiple cables in the list

#### Success Criteria
- [ ] Cables fetched: GET /api/cables/ returns 200
- [ ] Polylines rendered: all routes visible on the map
- [ ] Distinct colors: each cable type uses its designated color
- [ ] Hover works: tooltip shown on mouseover
- [ ] Click works: cable highlighted when selected
- [ ] Zoom to cable: map recenters on the chosen cable
- [ ] Details visible: name, distance, and type presented
- [ ] Performance: load completes under two seconds for 50 cables

#### Test Notes
```
Date/Time: _________________
Number of cables: __________
Result: [ ] PASS  [ ] FAIL
Notes:
_________________________________
_________________________________
```

---

### Scenario 4: Edit Existing Cable

Goal: Validate property and geometry editing.

#### Steps
1. Select a cable from the list or click it on the map
2. Click "Edit" or use the right-click menu > "Edit"
3. Edit properties:
   - Change the name to `TEST_CABLE_001_EDITED`
   - Change the cable type
   - Add a note
4. Edit geometry:
   - Enable vertex edit mode
   - Drag a vertex to a new position
   - Add a vertex mid-line
   - Remove an existing vertex
5. Click "Save Changes"
6. Verify updates on the map and in the database

#### Success Criteria
- [ ] Modal opens: edit form pre-populated with data
- [ ] Data accurate: fields show the correct values
- [ ] Vertex editing works: drag operations are smooth
- [ ] Add vertex works: new point inserted correctly
- [ ] Remove vertex works: line remains intact
- [ ] Distance recalculated: updated after geometry changes
- [ ] PUT request succeeds: 200 OK visible in the Network tab
- [ ] Map updated: polyline reflects the new shape immediately
- [ ] List updated: sidebar shows the new name and details
- [ ] No duplicates: only one cable instance remains

#### Test Notes
```
Date/Time: _________________
Edited cable ID: ___________
Result: [ ] PASS  [ ] FAIL
Notes:
_________________________________
_________________________________
```

---

### Scenario 5: Delete Cable

Goal: Validate the deletion flow with confirmation.

#### Steps
1. Select cable `TEST_CABLE_001_EDITED`
2. Click "Delete" or use the right-click menu > "Delete"
3. Confirm the modal appears
4. Click "Yes, delete"
5. Wait for the confirmation message
6. Reload the page to confirm persistence

#### Success Criteria
- [ ] Confirmation modal: prompt asks "Are you sure?"
- [ ] Data shown: modal displays cable name and details
- [ ] Cancel works: closing the modal does not delete
- [ ] DELETE request succeeds: 204 No Content in the Network tab
- [ ] Polyline removed: cable disappears from the map
- [ ] List updated: cable removed from the sidebar
- [ ] Notification displayed: success toast shown
- [ ] Persistence confirmed: cable does not return after reload

#### Test Notes
```
Date/Time: _________________
Deleted cable ID: _________
Result: [ ] PASS  [ ] FAIL
Notes:
_________________________________
_________________________________
```

---

### Scenario 6: Context Menu (Right Click)

Goal: Validate context menus for cables and the map.

#### Steps
1. Menu on a cable:
   - Right-click a polyline
   - Check options such as Edit, Delete, View Details
   - Click "View Details"
2. Menu on the map:
   - Right-click an empty area
   - Check options such as New Cable, Center Map
3. Close the menu by clicking elsewhere or pressing ESC

#### Success Criteria
- [ ] Menu appears: context popup visible
- [ ] Position correct: menu anchored near the cursor
- [ ] Options relevant: actions match the context
- [ ] Icons visible: each action shows the correct icon
- [ ] Hover works: items highlight on mouseover
- [ ] Click works: selected action executes
- [ ] Close works: ESC or outside click hides the menu
- [ ] No clipping: menu fully visible within the viewport

#### Test Notes
```
Date/Time: _________________
Result: [ ] PASS  [ ] FAIL
Notes:
_________________________________
_________________________________
```

---

### Scenario 7: Filters and Search

Goal: Validate filtering features when present.

#### Steps
1. Filter by cable type (dropdown)
2. Search by name (text input)
3. Filter by distance (range slider)
4. Clear all filters

#### Success Criteria
- [ ] Type filter: only cables of the selected type remain visible
- [ ] Name search: results filter in real time
- [ ] Distance filter: cables outside the range are hidden
- [ ] Clear filters: all cables return
- [ ] Performance: filtering responds within 100 ms
- [ ] Counter updated: "Showing X of Y cables"

#### Test Notes
```
Date/Time: _________________
Result: [ ] PASS  [ ] FAIL
Notes:
_________________________________
_________________________________
```

---

### Scenario 8: Map Interactions

Goal: Validate core Leaflet controls.

#### Steps
1. Zoom in and out with the buttons
2. Zoom in and out with the mouse scroll wheel
3. Pan the map by dragging
4. Use the layers control (if available)
5. Use fullscreen mode (if available)

#### Success Criteria
- [ ] Zoom buttons: plus and minus respond
- [ ] Scroll zoom: mouse wheel works
- [ ] Smooth panning: drag without lag
- [ ] Layers: switch between Street, Satellite, Terrain
- [ ] Fullscreen: toggles correctly
- [ ] Bounds preserved: map state maintained

#### Test Notes
```
Date/Time: _________________
Result: [ ] PASS  [ ] FAIL
Notes:
_________________________________
_________________________________
```

---

### Scenario 9: Errors and Edge Cases

Goal: Validate error handling paths.

#### Steps
1. Create cable without a name: attempt to save an empty form
2. Edit a missing cable: tamper with the URL to use an invalid ID
3. Delete while editing: delete the cable in another tab while the modal is open
4. Network offline: disable connectivity and attempt to save
5. Duplicate request: double-click the "Save" button quickly

#### Success Criteria
- [ ] Frontend validation: clear error messages displayed
- [ ] 404 handled: "Cable not found" presented
- [ ] Conflict handled: concurrent changes detected
- [ ] Offline detected: "No connection" message shown
- [ ] Loading state: button disabled during the request
- [ ] No crash: application remains stable
- [ ] Automatic rollback: inconsistent state reverted

#### Test Notes
```
Date/Time: _________________
Result: [ ] PASS  [ ] FAIL
Notes:
_________________________________
_________________________________
```

---

### Scenario 10: Performance and Responsiveness

Goal: Validate performance under load.

#### Steps
1. Create 20 cables quickly
2. Select multiple cables in succession
3. Perform rapid zoom in and zoom out several times
4. Test in mobile or tablet view (DevTools responsive mode)

#### Success Criteria
- [ ] Fast rendering: 20 cables render in under one second
- [ ] No lag: selection responds immediately
- [ ] Smooth zoom: no stuttering
- [ ] Mobile ready: touch interactions work and buttons remain accessible
- [ ] Memory healthy: no apparent leaks (DevTools Performance tab)

#### Test Notes
```
Date/Time: _________________
Result: [ ] PASS  [ ] FAIL
Notes:
_________________________________
_________________________________
```

---

## Compatibility Matrix

Test across multiple browsers.

| Scenario | Chrome | Firefox | Edge | Safari | Mobile |
| --- | --- | --- | --- | --- | --- |
| 1. Initialization | [ ] | [ ] | [ ] | [ ] | [ ] |
| 2. Create Cable | [ ] | [ ] | [ ] | [ ] | [ ] |
| 3. View | [ ] | [ ] | [ ] | [ ] | [ ] |
| 4. Edit | [ ] | [ ] | [ ] | [ ] | [ ] |
| 5. Delete | [ ] | [ ] | [ ] | [ ] | [ ] |
| 6. Context Menu | [ ] | [ ] | [ ] | [ ] | [ ] |
| 7. Filters | [ ] | [ ] | [ ] | [ ] | [ ] |
| 8. Map Interactions | [ ] | [ ] | [ ] | [ ] | [ ] |
| 9. Errors | [ ] | [ ] | [ ] | [ ] | [ ] |
| 10. Performance | [ ] | [ ] | [ ] | [ ] | [ ] |

---

## Bug Log

| ID | Scenario | Description | Severity | Status |
| --- | --- | --- | --- | --- |
| BUG-001 | | | [ ] Critical [ ] High [ ] Medium [ ] Low | [ ] Open [ ] Resolved |
| BUG-002 | | | [ ] Critical [ ] High [ ] Medium [ ] Low | [ ] Open [ ] Resolved |
| BUG-003 | | | [ ] Critical [ ] High [ ] Medium [ ] Low | [ ] Open [ ] Resolved |

Severity definitions:
- Critical: application unavailable or data loss
- High: primary feature broken, no practical workaround
- Medium: secondary feature affected, workaround available
- Low: cosmetic issue or minor UX concern

---

## Final Acceptance Criteria

The refactor is approved when:

- [ ] All ten scenarios pass in at least one browser
- [ ] Zero critical bugs remain
- [ ] Fewer than two high severity bugs remain
- [ ] Performance acceptable (under two seconds for primary actions)
- [ ] Console free of errors (benign warnings allowed)
- [ ] Compatibility confirmed on Chrome and Firefox
- [ ] Basic mobile usage validated (touch and navigation work)

---

## Execution Report

Tester: _________________________
Start date: _____________________
End date: _______________________
Total duration: _________________

Summary:
- Scenarios executed: ____/10
- Scenarios passing: ____
- Scenarios failing: ____
- Bugs found: ____
- Critical bugs: ____

Final decision:
[ ] APPROVED - refactor with no regressions
[ ] APPROVED WITH CONDITIONS - minor bugs to fix
[ ] REJECTED - critical regressions found

General notes:
```
______________________________________________
______________________________________________
______________________________________________
______________________________________________
```

---

Next steps:
1. If approved: merge into the main branch
2. If rejected: fix bugs and rerun the manual plan
3. Document lessons learned
4. Add automated tests (Jest or Playwright) for the critical scenarios

---

Document generated on 27 October 2025
Based on the ES6 modular refactor of `fiber_route_builder.js`
