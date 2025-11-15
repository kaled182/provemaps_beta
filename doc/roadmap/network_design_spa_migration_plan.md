# Network Design SPA Migration Plan

Status tracking for the Network Design experience migration from the legacy Django template to the Vue 3 SPA. Use this as the single source of truth; update the checkboxes as tasks complete and append notes under the appropriate section when discoveries occur.

## 0. Snapshot & Guardrails
- [x] Confirm feature flags: `USE_VUE_DASHBOARD`, `VUE_DASHBOARD_ROLLOUT_PERCENTAGE`, and ensure `/NetworkDesign/?legacy=1` remains available during rollout.
- [ ] Capture reference screenshots / Loom of the legacy page (map, context menu, modals, list) for later parity checks.
- [ ] Export representative fixtures (devices, fibers, routes) via existing APIs or `scripts/` helpers; record seed instructions in `doc/getting-started/`.
- [ ] Verify logging & metrics: browser console, Django logs, Prometheus `/metrics` for route-related counters.

## 1. SPA Entrypoint Delivery
- [x] Serve `spa.html` for authenticated hits to `/NetworkDesign/` when Vue flag is on, keep `?legacy=1` fallback.
- [ ] Inject Google Maps API key into `<meta name="google-maps-api-key">` from runtime config and confirm spa build reads it.
- [ ] Update router base detection so `/NetworkDesign/` resolves to `/` history (covers direct loads and deep links).
- [ ] Strip CDN Tailwind dependency from `base_spa.html`; bundle required utility classes in `frontend` build.

## 2. Map Bootstrap & Layout
- [x] Implement `NetworkDesignView.vue` container mirroring legacy DOM IDs for compatibility.
- [ ] Ensure map canvas (`#builderMap`) occupies expected height when rendered inside SPA shell.
- [ ] Wire `initializeNetworkDesignApp({ force: true })` into component lifecycle; guarantee cleanup on unmount.
- [ ] Validate fullscreen behavior & modal parent syncing (`syncModalParent`) after migrating to SPA.

## 3. Device/Fiber Data Loading
- [ ] Confirm `fetchFibers`, `fetchFiber`, and `fetchDeviceOptions` endpoints work with Django session auth when served from SPA route (no CSRF issues).
- [ ] Preload device options before rendering selects; fallback gracefully when API fails (toast + retry button).
- [ ] Guard against duplicate Cable polylines when `loadAllCablesForVisualization` runs in SPA context.
- [ ] Audit cache invalidation hooks (`invalidate_fiber_cache`, websockets) to ensure new SPA flow triggers updates.

## 4. Context Menu & Map Interactions
- [ ] Verify right-click opens context menu with correct state (general actions vs selected cable vs creation flow).
- [ ] Ensure polyline right-click wiring works after Vue mounting; no duplicate listeners or stale references.
- [ ] Re-test drag/drop of route points; confirm reorder persists and updates the map.
- [ ] Review keyboard shortcuts (`Esc` to cancel) within Vue shell.

## 5. Manual Save Modal
- [ ] Confirm manual modal opens from context menu and from list action; ensure close button + overlay click works.
- [ ] Validate device+port selects populate with monitoring data (observe network tab). Handle single-port checkbox logic.
- [ ] Submit manual save form; check success toast, websocket broadcast, and DOM reset behavior.
- [ ] Implement client-side form validation messaging (missing required fields, invalid combinations).

## 6. KML Import Flow
- [x] Refactor `partials/import_kml.js` to expose `initializeKmlModal` and guard duplicates.
- [ ] Invoke KML initializer from SPA and confirm dataset toggles remain functional.
- [ ] Upload sample KML; inspect backend response, path drawing, and caches.
- [ ] Provide better user feedback (progress indicator, error details) vs current `alert()` usage.

## 7. Realtime & Notifications
- [ ] Confirm websocket topics (`fiber:cable-created`, `broadcast_cable_status_update`) still propagate to SPA via Pinia store.
- [ ] Replace `alert()`/console logs with toast notifications consistent with rest of SPA.
- [ ] Ensure `toastHost` container displays in Vue layout and cleans up on route leave.
- [ ] Hook Prometheus counters (if any) to new SPA actions, updating `core/metrics_*` as needed.

## 8. Testing Strategy
- [ ] Unit tests: extend `frontend/tests/` with component tests (Vitest) for `NetworkDesignView.vue` toggles and initialization logic.
- [ ] Integration tests: use Playwright scenario to load `/NetworkDesign/`, mock Google Maps, verify context menu and modals.
- [ ] Backend tests: add Django view test ensuring `USE_VUE_DASHBOARD` flag renders SPA and fallback works (`legacy=1`).
- [ ] API contract tests: ensure `fetchFibers` and KML endpoints return expected schema (pytest + factory data).
- [ ] Regression tests: rerun existing `backend/tests/routes/` suites; extend with SPA-specific coverage for manual save pipeline.
- [ ] Performance smoke: run `scripts/smoke_test_phase4.py` or equivalent after deployment to catch latency regressions.

## 9. Deployment & Rollout
- [ ] Document release plan: staging validation, flag flip sequence, and rollback steps in `doc/releases/`.
- [ ] Update `README.md` / `doc/getting-started/` with new SPA instructions.
- [ ] Coordinate comms with NOC/Suporte before rollout, include fallback URL.
- [ ] Monitor error rates/logs for 24h after enabling SPA globally; be ready to toggle back.

## Test Execution Guide
- Run frontend unit tests: `cd frontend && npm run test:unit`.
- Run Playwright E2E (with dev server or served static): `npm run test:e2e`.
- Backend tests (targeted): `cd backend && pytest tests/routes/test_fiber_route_builder.py tests/inventory/test_kml_import.py`.
- Full regression sweep: `make test` (ensures Celery eager paths are safe).
- Manual QA checklist (document results in this file or link to TestRail):
  1. Load `/NetworkDesign/` (SPA) → map renders, cables visible.
  2. Right-click map → context menu shows path options.
  3. Draw path, reorder points, save new cable → verify toast + API result.
  4. Edit existing cable → ensure polyline updates, websocket refresh.
  5. Import KML → confirm path drawn and metadata populated.
  6. Toggle theme, resize window, test fullscreen map.

## Notes & Findings
Use this section to log observations, bugs, or follow-ups discovered during migrations and tests.

- _Example_: 2025-11-15 — SPA loads but Google Maps not initialized when accessed via `/static/vue-spa/NetworkDesign/`; avoid deep linking to static path because router expects `/NetworkDesign/`.
- 2025-11-15 — Verified runtime flags inside container: `USE_VUE_DASHBOARD=True`, `VUE_DASHBOARD_ROLLOUT_PERCENTAGE=100`, legacy fallback `/NetworkDesign/?legacy=1` responds with 302 (auth redirect), SPA route `/NetworkDesign/` also enforcing auth.
- 2025-11-15 — Sempre que for validar no stack web (via Docker), lembrar de executar `npm run build` seguido de `docker compose build web && docker compose up -d web` para garantir que os assets atualizados estejam servidos.
