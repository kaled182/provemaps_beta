# Breaking Changes - v2.0.0 Migration Guide

**Target Audience**: Developers, DevOps, Integration Partners  
**Effective Date**: Post-Phase 5 deployment  
**Migration Urgency**: 🔴 **HIGH** - Action required before upgrading to v2.0.0

---

## 🎯 Executive Summary

MapsProveFiber v2.0.0 introduces a **modular architecture** that consolidates inventory management, monitoring, and Zabbix integration into distinct, well-defined Django apps. This refactoring **breaks backward compatibility** with legacy code paths and endpoints.

### Quick Impact Assessment

| Area | Impact | Action Required |
|------|--------|-----------------|
| **Python Imports** | 🔴 Breaking | Update all `zabbix_api.*` imports |
| **API Endpoints** | 🟡 Deprecated | Migrate to `/api/v1/inventory/*` |
| **Database** | 🟢 Compatible | Apply migration `inventory.0003` (zero downtime) |
| **Frontend** | 🟢 Compatible | Already migrated (9 JS files updated) |
| **Tests** | 🔴 Breaking | Remove references to `zabbix_api` module |

---

## 🚨 Breaking Changes Detail

### 1. Module `zabbix_api` Removed

**Status**: ❌ **DELETED**  
**Removed in**: v2.0.0-alpha.1 (Phase 4 completion)

#### What Changed
The entire `zabbix_api/` Django app has been deleted. All functionality has been migrated to:
- **`inventory/`** — Authoritative models (Site, Device, Port, Route)
- **`integrations/zabbix/`** — Resilient Zabbix API client
- **`monitoring/`** — Health checks and combined status logic

#### Migration Path

**❌ BEFORE (v1.x - BROKEN)**:
```python
# These imports will fail with ModuleNotFoundError
from zabbix_api.models import Site, Device, Port
from zabbix_api.inventory_cache import FibersCache
from zabbix_api.inventory import get_fiber_status
from zabbix_api.domain.geometry import sanitize_path_points
```

**✅ AFTER (v2.0.0+)**:
```python
# Correct imports for modular architecture
from inventory.models import Site, Device, Port, Route
from inventory.cache.fibers import invalidate_fiber_cache
from inventory.services.fiber_status import get_oper_status_from_port
from inventory.domain.geometry import sanitize_path_points

# Zabbix client
from integrations.zabbix.client import resilient_client
from integrations.zabbix.zabbix_service import zabbix_request

# Monitoring
from monitoring.usecases import HostStatusProcessor
```

#### Search & Replace Commands

```bash
# Find all usages (run in project root)
grep -r "from zabbix_api" . --include="*.py"
grep -r "import zabbix_api" . --include="*.py"

# Example replacements
sed -i 's/from zabbix_api.models import/from inventory.models import/g' **/*.py
sed -i 's/from zabbix_api.inventory_cache/from inventory.cache.fibers/g' **/*.py
sed -i 's/zabbix_api.domain.geometry/inventory.domain.geometry/g' **/*.py
```

---

### 2. API Endpoints Deprecated

**Status**: 🟡 **DEPRECATED** (shims may be removed in v2.1.0)  
**Action Required**: Migrate to new endpoints before v2.1.0

#### Deprecated Endpoints

| Legacy Endpoint (v1.x) | New Endpoint (v2.0.0+) | Status |
|------------------------|------------------------|--------|
| `/zabbix_api/inventory/sites/` | `/api/v1/inventory/sites/` | ⚠️ Deprecated |
| `/zabbix_api/inventory/devices/` | `/api/v1/inventory/devices/` | ⚠️ Deprecated |
| `/zabbix_api/inventory/fibers/` | `/api/v1/inventory/fibers/` | ⚠️ Deprecated |
| `/zabbix_api/api/fibers/oper-status/` | `/api/v1/inventory/fibers/oper-status/` | ⚠️ Deprecated |
| `/zabbix_api/api/test/*` | `/api/v1/inventory/diagnostics/*` | ❌ **REMOVED** |

#### Migration Examples

**JavaScript/Frontend**:
```javascript
// ❌ OLD (will fail in v2.1.0)
fetch('/zabbix_api/inventory/fibers/')

// ✅ NEW
fetch('/api/v1/inventory/fibers/')
```

**Python/Backend**:
```python
# ❌ OLD
response = client.get('/zabbix_api/api/fibers/oper-status/')

# ✅ NEW
response = client.get('/api/v1/inventory/fibers/oper-status/')
```

**cURL/Integration Testing**:
```bash
# ❌ OLD
curl http://localhost:8000/zabbix_api/inventory/devices/

# ✅ NEW
curl http://localhost:8000/api/v1/inventory/devices/
```

---

### 3. URL Configuration Changes

**Status**: ✅ **COMPLETED**  
**Impact**: `urls.W005` warning resolved

#### What Changed
- **Removed**: Duplicate namespace `zabbix_api` from `core/urls.py`
- **Kept**: `routes_builder` temporarily (migration dependency)
- **Result**: Clean URL configuration with zero warnings

#### If You Extended `core/urls.py`
Ensure you're not relying on the removed `zabbix_api` namespace:

```python
# ❌ REMOVED
path('zabbix/api/', include('zabbix_api.urls')),

# ✅ Use inventory namespace instead
path('api/v1/inventory/', include('inventory.urls_api')),
```

---

### 4. Test Suite Changes

**Status**: ✅ **COMPLETED**  
**Impact**: Test count reduced from 200 → 199

#### Removed Tests
- `test_zabbix_api_models_reexport_inventory` (legacy compatibility check)
- Imports of `zabbix_api.inventory_cache` in test files

#### If You Have Custom Tests
Update test imports:

```python
# ❌ OLD
from zabbix_api.models import Site
from zabbix_api.tests.factories import SiteFactory

# ✅ NEW
from inventory.models import Site
from inventory.tests.conftest import SiteFactory  # or create_test_site
```

Update test discovery paths in `pytest.ini`:
```ini
# ✅ Correct testpaths
testpaths = 
    tests
    inventory/tests
    monitoring/tests
    routes_builder/tests
```

---

### 5. Configuration File Updates

**Status**: ✅ **COMPLETED**  
**Impact**: Type checking and linting aligned with new structure

#### `pyrightconfig.json`
```json
{
  "include": [
    "inventory/api",
    "inventory/usecases",
    "inventory/services",
    "monitoring/tests",
    "integrations/zabbix"
  ],
  "exclude": [
    "routes_builder"  // Excluded until migration dependency removed
  ]
}
```

#### `pytest.ini`
```ini
[pytest]
testpaths = 
    tests
    inventory/tests
    monitoring/tests
    routes_builder/tests
# Removed: zabbix_api/tests
```

#### CI/CD Workflows
Update `.github/workflows/*.yml`:
```yaml
# ❌ OLD
- name: Test inventory
  run: pytest inventory/tests/test_fibers_api.py zabbix_api/tests.py -q

# ✅ NEW
- name: Test inventory
  run: pytest inventory/tests/ tests/usecases/ tests/test_inventory_endpoints.py -q
```

---

## 🗄️ Database Migration

### Migration: `inventory.0003_route_models_relocation`

**Type**: Metadata-only (`SeparateDatabaseAndState`)  
**Downtime**: ⏱️ **ZERO** (no data changes)  
**Reversible**: ✅ Yes (rollback supported)

#### What It Does
Moves `Route` model metadata from `routes_builder` app to `inventory` app without touching data:
1. Updates Django's `ContentType` table
2. Adjusts model registration in Django's app registry
3. Preserves all foreign keys and constraints

#### How to Apply

**Development/Staging**:
```bash
python manage.py migrate inventory 0003_route_models_relocation
```

**Production** (zero downtime):
```bash
# Step 1: Backup (mandatory)
python manage.py dumpdata inventory routes_builder > backup_pre_migration.json

# Step 2: Apply migration
python manage.py migrate inventory 0003_route_models_relocation

# Step 3: Validate
python scripts/validate_migration_staging.py

# Step 4: Verify ContentTypes
python manage.py shell -c "
from django.contrib.contenttypes.models import ContentType
ct = ContentType.objects.get(app_label='inventory', model='route')
print(f'✅ Route model in inventory app: {ct}')
"
```

#### Rollback Plan
```bash
# If issues detected within 24h
python manage.py migrate inventory 0002
python manage.py loaddata backup_pre_migration.json
```

**Validation**: See [`doc/operations/MIGRATION_PRODUCTION_GUIDE.md`](../operations/MIGRATION_PRODUCTION_GUIDE.md) for full procedure.

---

## 🔄 Migration Checklist

### Pre-Deployment

- [ ] **Code Review**: Search codebase for `zabbix_api` imports
  ```bash
  grep -r "zabbix_api" . --include="*.py" | grep -v migration | grep -v __pycache__
  ```
- [ ] **Update Imports**: Replace with `inventory.*` or `integrations.zabbix.*`
- [ ] **Update Tests**: Remove `zabbix_api` references from test files
- [ ] **Update CI/CD**: Modify workflows to test new module structure
- [ ] **Frontend Check**: Verify all AJAX calls use `/api/v1/inventory/*`
- [ ] **Backup Database**: Create full backup before migration
  ```bash
  python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
  ```

### Deployment

- [ ] **Apply Migration**: Run `inventory.0003_route_models_relocation`
- [ ] **Restart Services**: Django, Celery workers, Celery beat
- [ ] **Validate Health**: Check `/healthz/`, `/ready/`, `/live/`
- [ ] **Run Smoke Tests**: Execute `python scripts/smoke_test_phase4.py`
- [ ] **Monitor Logs**: Watch for `ModuleNotFoundError: zabbix_api` in first 24h

### Post-Deployment

- [ ] **Verify Metrics**: Check Prometheus `/metrics/` endpoint
- [ ] **Test Critical Paths**: Dashboard, route creation, device listing
- [ ] **Validate Zabbix Integration**: Test API calls, circuit breaker, retries
- [ ] **Performance Baseline**: Compare response times vs. pre-migration
- [ ] **User Communication**: Notify stakeholders of breaking changes

---

## 🛠️ Troubleshooting

### Error: `ModuleNotFoundError: No module named 'zabbix_api'`

**Cause**: Code still importing from deleted module  
**Fix**: Update imports following migration path in section 1

### Error: `NoReverseMatch: 'zabbix_api' is not a registered namespace`

**Cause**: Template or view still using old URL namespace  
**Fix**:
```django
{# ❌ OLD #}
{% url 'zabbix_api:fiber_status' cable_id=cable.id %}

{# ✅ NEW #}
{% url 'inventory:fiber_status' cable_id=cable.id %}
```

### Error: `ContentType matching query does not exist`

**Cause**: Migration `inventory.0003` not applied  
**Fix**:
```bash
python manage.py migrate inventory 0003_route_models_relocation
python manage.py shell -c "from django.contrib.contenttypes.management import update_contenttypes; from django.apps import apps; update_contenttypes(apps.get_app_config('inventory'))"
```

### Tests Failing: `ImportError in conftest.py`

**Cause**: Test fixtures importing from `zabbix_api`  
**Fix**: Update `conftest.py` and test factories:
```python
# In tests/conftest.py or inventory/tests/conftest.py
from inventory.models import Site, Device, Port
from inventory.tests.factories import SiteFactory  # if using factory_boy
```

---

## 📞 Support

### Documentation
- [Migration Production Guide](../operations/MIGRATION_PRODUCTION_GUIDE.md)
- [Phase 4 Completion Report](./PHASE4_COMPLETION_REPORT.md)
- [API Documentation](../reference-root/API_DOCUMENTATION.md)

### Validation Scripts
- `scripts/validate_migration_staging.py` — Pre-deploy validation
- `scripts/smoke_test_phase4.py` — Post-deploy smoke test

### Contact
- **Technical Questions**: Open issue in GitHub repo
- **Production Issues**: Escalate to DevOps team
- **Migration Support**: Refer to `MIGRATION_PRODUCTION_GUIDE.md`

---

## 📊 Impact Summary

| Metric | Before (v1.x) | After (v2.0.0) | Change |
|--------|---------------|----------------|--------|
| **Django Apps** | 13 | 12 | -1 (zabbix_api removed) |
| **API Endpoints** | Mixed namespaces | Unified `/api/v1/inventory/` | ✅ Cleaner |
| **Test Count** | 200 | 199 | -1 (legacy test) |
| **Code Lines** | ~42,000 | ~41,500 | ↓ 500 lines |
| **Import Paths** | 3+ variants | 2 canonical paths | ✅ Simplified |
| **URL Warnings** | 1 (`urls.W005`) | 0 | ✅ Resolved |

---

**Last Updated**: 2025-01-07  
**Version**: v2.0.0-alpha.1  
**Author**: Don Jonhn  
**Review Status**: ✅ Approved for Phase 5
