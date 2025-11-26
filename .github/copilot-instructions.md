## Copilot Instructions — MapsProveFiber (Condensed v2.0.0)

Use CURRENT patterns only. For deep details see `doc/architecture/{MODULES,DATA_FLOW}.md`.

1. Environment
- Docker-only services (PostgreSQL+PostGIS, Redis, Celery, web). Never start DB/Redis directly on Windows.
```powershell
cd docker; docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web pytest
docker compose build --no-cache web
docker compose down
```
- Host DB: `localhost:5433`; in containers: `postgres:5432`.

2. Apps Snapshot
`core` spine; `inventory` SSOT (Sites, Devices, Ports, Fibers, Routes); `monitoring` Zabbix+inventory usecases; `integrations/zabbix` circuit-breaker client; `maps_view` dashboard + WS publishers; `setup_app` runtime encrypted config; `service_accounts` token rotation. Retired: `routes_builder/`. Placeholders: `dwdm/`, `gpon/`.

3. Core Patterns
- Place business logic in `services.py` / `usecases.py` (not views). Example: `inventory/routes/services.py` for route build & cache invalidation.
- Zabbix calls only via `integrations/zabbix/zabbix_service.zabbix_request()`.
- Caching: `SWRCache` + `safe_cache_get/set`; invalidate via `inventory.cache.fibers.invalidate_fiber_cache()` / `inventory.routes.services.invalidate_route_cache(id)`.
- Spatial: LineString (SRID 4326); helpers in `inventory/spatial.py`.
- Preserve DTO field order (`RouteBuildResult` etc.) — tests assert exact ordering.

4. Testing & Quality
`make test` (fast, may use SQLite; avoid spatial ops). Full PostGIS tests inside Docker. Celery eager mode (`CELERY_TASK_ALWAYS_EAGER=True`). Format/lint: `make fmt` / `make lint` (Ruff, Black, isort in `backend/pyproject.toml`).

5. Frontend & Rollout
Vue 3 SPA (`frontend/` → build to `backend/staticfiles/vue-spa/`). Dashboard selection: `maps_view/views.py::dashboard_view` using `USE_VUE_DASHBOARD` + rollout percentage in `database/runtime.env`.

6. Secrets & Config
Encrypted runtime settings via `setup_app.services.runtime_settings.get_runtime_config()`. After DB changes call `reload_config()`. No hardcoded secrets.

7. Service Accounts
Rotation logic + webhooks in `service_accounts/` (`tasks.py`). Respect rotation intervals & notify-before settings; add new tasks and route in `core/celery.py`.

8. Device Import Workflow (Domain)
- Vue components under `frontend/src/components/DeviceImport/`; batch import posts to `/api/v1/inventory/devices/import-batch/`.
- Category mapping: `backbone`, `gpon` (GPON/FTTx), `dwdm` chosen in modal; internal Zabbix group matching via keyword map (`DeviceImportManager.vue` `matchGroup()`).
- Alert channels toggles: screen (`dashboard map`) and WhatsApp Ops (`formState.alerts.whatsapp`). CSV export includes `enable_whatsapp_alert`.
- Validate devices before batch (`validateDevices()`); surface errors via notification helpers.
- **Import Rules**: Auto-association via `ImportRule` model (`inventory/models.py`) with regex patterns; CRUD through `/api/v1/import-rules/` + `ImportRulesModal.vue`; applied in priority order (lowest first); supports reordering, activation toggle, pattern testing. Applied during: (1) new device import, (2) existing device sync if still default category/no group (`add_device_from_zabbix` in `usecases/devices.py`), (3) sync action `POST /api/v1/devices/<id>/sync/`.
- **Device Groups**: Full list via `/api/v1/device-groups/` (NOT `/api/v1/inventory/device-groups/`). Devices carregam `monitoring_group` e `role` (alias de `category`) via serializer. Picker de grupos no inventário usa endpoint dedicado `/api/v1/devices/available-for-group/?group_id=<id>` para trazer apenas devices livres ou do próprio grupo (regra de unicidade). Sync from Zabbix via `sync_device_groups_for_device()` auto-creates missing groups e preenche `monitoring_group` se vazio.
- **Sync Endpoint**: `POST /api/v1/devices/<id>/sync/` (action in `DeviceViewSet`) re-fetches Zabbix data, re-applies rules if needed, syncs groups, updates site/name/IP. Frontend uses this via `api.post()` with CSRF token in both `ImportPreviewTab.vue` ("Sincronizar" button) and `DeviceEditModal.vue` ("Sincronizar Zabbix" button in readonly mode). Check logs for `Applied import rule #<id> (existing device sync)` confirmation.
- **Data Consistency (Edit Modal)**: `DeviceImportManager.openEditModal()` always fetches fresh device data from server before opening edit modal (async GET `/api/v1/devices/<id>/`), ensuring modal shows current DB state regardless of cached array state.
- **Data Consistency (Readonly Modal)**: `ImportPreviewTab.viewDeviceDetails()` fetches fresh data via `/api/v1/devices/by-zabbix/<zabbix_id>/` (primary) or `/api/v1/devices/<id>/` (fallback) before opening readonly modal. Modal receives complete device object including `group_name`, `monitoring_group`, `category`, `alerts`. Uses `DeviceEditModal` with `readOnly=true` prop.
- **Readonly Modal Features**: Shows "Detalhes do Dispositivo" title; displays current device data (name, IP, group, category, alerts); action buttons: "Abrir Dashboard", "Editar Configurações", "Sincronizar Zabbix" (calls sync endpoint with CSRF), "Ver Interfaces". Sync button visibility controlled by `showSyncButton` computed (requires valid numeric device ID).
- **API Endpoints**: All device operations use `/api/v1/devices/*` (NOT `/api/v1/inventory/devices/*`). Correct endpoints: GET `/api/v1/devices/<id>/`, GET `/api/v1/devices/by-zabbix/<zabbix_id>/`, POST `/api/v1/devices/<id>/sync/`. Import operations still use `/api/v1/inventory/devices/import-batch/`.
- **CSRF Protection**: All POST/PUT/PATCH/DELETE requests must use `useApi` composable (`api.post()`, `api.put()`, etc.) which automatically includes `X-CSRFToken` header via `getAuthHeaders()`. Direct `fetch()` calls will fail with 403 Forbidden. CSRF token sourced from `window.CSRF_TOKEN` or `csrftoken` cookie.

9. Common Do / Don't
DO rebuild web image after Python/migrations; DO use publisher helpers (`broadcast_dashboard_status`, `broadcast_cable_status_update`). DON'T bypass service layer, skip cache invalidation, or reorder DTO fields. DON'T use SQLite for spatial logic in production.

10. Extending
- New endpoint: service/usecase → serializer/view/viewset → app `urls` → include in `core/urls.py`.
- New Celery task: define in `<app>/tasks.py`, route in `core/celery.py`, assign proper queue (`default`, `zabbix`, `maps`).
- New cache: use `safe_cache_*`, define clear key namespace + invalidation.

11. Quick Commands
`make up` | `make down` | `make migrate` | `make test` | `make fmt` | `celery -A core worker -Q default,zabbix,maps -l info` | `npm run build`

12. Validating Import Rules
**Check if rules are working:**
```powershell
# View recent rule applications in logs
cd docker; docker compose logs web --since 5m | Select-String -Pattern "Applied import rule" -Context 1

# Test rule logic directly (Django shell)
docker compose exec web python manage.py shell
>>> from inventory.services.import_rules import apply_import_rules
>>> apply_import_rules("Huawei - Switch Teste")  # Should return dict with category, group_id
>>> apply_import_rules("OLT-GPON-Centro")  # Should return None if no rule matches
```
**Expected log output:** `INFO ... devices Applied import rule #<id> (<description>) to <device_name>: category=<cat>, group_id=<gid>`

**UI validation:** Import/sync a device matching regex → check "Inventário Atual (Pós)" tab → group and category should be auto-assigned.

Feedback: Clarify placeholder apps (`dwdm/`, `gpon/`) future scope before large refactors.
