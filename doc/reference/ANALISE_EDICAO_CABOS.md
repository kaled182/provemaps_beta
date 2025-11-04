# Cable Editing Feature Analysis

Date: 27 October 2025  
Status: Feature validated end to end  
Scope: Manual and automated review of the fiber cable editing workflow in the routes builder

---

## Executive Summary

- The edit workflow covers metadata, path geometry, and deletion in a single endpoint (`PUT /zabbix_api/api/fiber/{id}/`).
- Frontend modules (`routes_builder/static/js/modules`) orchestrate the Google Maps canvas, modal editor, and API client with clear separation of concerns.
- Backend validation sanitizes coordinates, guards against duplicate names, and keeps cache entries consistent via `invalidate_fiber_cache()`.
- Regression test coverage is provided by `tests/test_fiber_edit_persistence.py`, which verifies read, update, and reload cycles against the database.
- Remaining gaps: legacy docstrings are still in Portuguese; live status polling is outside the scope of this report but depends on the same endpoints.

---

## User Workflow Overview

1. Analyst opens `/routes/builder/fiber-route-builder/`, which renders `fiber_route_builder.html` with the Google Maps API key and device list.
2. `fiber_route_builder.js` loads modular helpers:
	 - `apiClient.js`: wraps REST calls such as `GET /zabbix_api/api/fiber/` and `PUT /zabbix_api/api/fiber/{id}/`.
	 - `mapCore.js`: instantiates the map and exposes `createCablePolyline()` used for drawing paths.
	 - `modalEditor.js`: handles the metadata form (name, devices, ports, single-port toggle).
	 - `pathState.js`: keeps the editable polyline in sync with the stored geometry.
	 - `contextMenu.js`: binds right-click actions (Edit, Delete, View Details) to polylines.
	 - `uiHelpers.js`: displays toast notifications and validation feedback.
3. Choosing a cable populates the modal with current metadata (`loadCableDetails()`), draws the existing path, and enables vertex editing through the injected callback in `cableService.js`.
4. Saving submits a payload containing any modified fields and optional `path` coordinates; success responses refresh the view and re-fetch the cable list.

---

## Backend Endpoints and Data Flow

| HTTP Method | URL | Purpose | Handler |
| --- | --- | --- | --- |
| GET | `/zabbix_api/api/fiber/` | List cables with path previews | `inventory_fibers.api_list_fibers` |
| POST | `/zabbix_api/api/fiber/manual/` | Create cable from manual input | `inventory_fibers.api_create_fiber_manual` |
| GET | `/zabbix_api/api/fiber/{id}/` | Retrieve detailed metadata and geometry | `inventory_fibers.api_fiber_detail` |
| PUT | `/zabbix_api/api/fiber/{id}/` | Update path and/or metadata | `inventory_fibers.api_fiber_detail` |
| DELETE | `/zabbix_api/api/fiber/{id}/` | Remove cable | `inventory_fibers.api_fiber_detail` |

Key backend functions inside `zabbix_api/usecases/fibers.py`:
- `update_fiber_path(cable, raw_path)`: cleans coordinates with `sanitize_path_points`, computes `length_km`, and updates `path_coordinates`.
- `update_fiber_metadata(cable, name, origin_port_id, dest_port_id)`: enforces non-empty names, validates port ownership, and saves only changed fields.
- `fiber_detail_payload(cable)`: hydrates response objects with site, device, and port context for both endpoints.
- `invalidate_fiber_cache()`: ensures cached `/zabbix_api/api/fiber/` responses are refreshed after edits.

---

## Validation and Error Handling

- Coordinate lists must contain at least two points after sanitization; otherwise the API returns HTTP 400 with the validation message.
- Names are stripped and rejected when empty; duplicate names are trapped during create operations (`FiberValidationError`).
- Port IDs are coerced to integers and validated individually; missing ports raise a 400 response with the offending identifier.
- Metadata updates are patch-friendly: unspecified fields remain untouched, preventing accidental resets.
- The frontend guards submission via `validateCablePayload()` (client side) and displays precise error messages supplied by the API.

---

## Persistence Guarantees

- `tests/test_fiber_edit_persistence.py` covers the three primary scenarios:
	1. Full update with new name, destination port, and extended path, confirmed via subsequent GET and database refresh.
	2. Partial update (destination port only) ensuring other attributes remain stable.
	3. Name-only update verifying that origin port and path are preserved.
- The test suite uses a Django auth client to mirror real requests, including JSON payload handling and login requirements.
- Additional coverage exists indirectly through map initialization tests and cable visualization helpers exercised in `routes_builder` Jest tests (`routes_builder/static/js/__tests__`).

---

## Frontend Editing Mechanics

- `cableService.initCableService()` receives the map instance and an editable polyline callback so visualization lines can expose context menu actions without altering the primary editor polyline.
- `loadAllCablesForVisualization()` redraws read-only polylines for every cable, optionally fitting map bounds and skipping the actively edited cable to reduce clutter.
- `removeCableVisualization()` and `clearCablePolylines()` keep the map free of stale overlays after deletes or reloads.
- The modal editor persists form state across context switches, preventing data loss while users inspect other cables.
- UI feedback: success toasts on save or delete, inline errors for validation issues, and console logging for debugging.

---

## Observations and Outstanding Work

- Portuguese docstrings remain in `tests/test_fiber_edit_persistence.py` and `zabbix_api/usecases/fibers.py`; consider translating to match repository standards.
- The API currently allows empty path submissions when `single_port` is true; confirm whether this is desirable or if at least two identical coordinates should be enforced.
- Frontend relies on DOM element `fiberSelect`; ensure server-side template always renders the dropdown even when the cable list is empty to avoid null references.
- No rate limiting is applied to the update endpoint; audit requirements if bulk edits become common.

---

## Recommended Next Steps

1. Translate remaining Portuguese inline documentation for consistency.
2. Add Playwright smoke tests covering edit, delete, and cancel flows to match the manual plan in `FRONTEND_TESTING_MANUAL_PLAN.md`.
3. Implement optimistic UI updates or skeleton loading to improve usability during API round-trips.
4. Evaluate webhook or signal-based cache invalidation to reduce repeated list fetches in the frontend.
