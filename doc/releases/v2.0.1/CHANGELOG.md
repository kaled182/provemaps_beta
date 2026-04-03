# Changelog — v2.0.1 (2025-11-11)

## 🎯 Overview
Minor stabilization release focused on restoring the Fiber Route Builder experience after the folder restructure.

## ✅ Fixes
- Rebuilt `inventory/templates/inventory/fiber_route_builder.html` to remove duplicate `content` blocks and keep the interface fully in English.
- Re-linked the Google Maps workflow panels, context menu, toast host, and manual-save modal so existing JavaScript modules continue to work.
- Corrected the ES module loader to reference `static/js/fiber_route_builder.js`, ensuring the Google Maps callback wires up again.

## 🧪 Quality
- `pytest -q` (Python 3.13.9, Django 5.2.7) — **194 passed, 6 skipped** in 12.26s.
  - Settings: `settings.test`
  - Key coverage: cache SWR, route services, Zabbix resilient client, inventory + monitoring use cases.

## 🚀 Deployment Notes
- No database migrations.
- No new dependencies.
- After deployment, perform a quick smoke test:
  1. Load `/routes/fiber-route-builder/` and add/remove map points.
  2. Trigger the context menu and ensure Toast/Confirm dialogs appear.
  3. Open the manual save modal and validate device/port dropdowns populate.

## 📌 Next Steps
- Tag `v2.0.1` once changes are merged to the default branch.
- Begin the Vue 3 migration with the stabilized backend as baseline.
