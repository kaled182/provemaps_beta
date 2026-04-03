# Migration Squash Plan — Routes Consolidation

**Status:** Completed  
**Target:** Fase 8 (post Vue 3 migration) — delivered Nov 2025  
**Risk:** Historical reference only (app removido)

---

## Context

During the folder restructure (Fase 6), route-related models (`Route`, `RouteSegment`, `RouteEvent`) were migrated from the `routes_builder` app to `inventory`. We originally kept a "zombie app" pattern for migration compatibility, but as of v2.1.0 the `routes_builder` Django app has been fully removed from the codebase. Historic notes below are retained for audit purposes only.

---

## Current Migration Timeline

### Inventory App
```
0001_initial_from_existing_tables.py    # Site, Device, Port, FiberCable, FiberEvent
0002_alter_port_zabbix_item_id_...      # Port field updates
0003_route_models_relocation.py         # ⚠️ Move Route models from routes_builder
0004_rename_route_tables.py             # ⚠️ Rename routes_builder_* → inventory_*
0005_site_schema_normalization.py       # Site display_name/slug refactor
0006_alter_device_options_...           # Meta ordering updates
0007_routes_table_rename.py             # ⚠️ Final route table names
```

### Routes Builder App (Zombie)
```
0001_initial.py                         # Original Route model definitions
0002_move_route_models_to_inventory.py  # ⚠️ Marks models as moved
```

---

## Squash Strategy

### Phase 1: Squash Inventory Migrations (Safe)

**Target:** Combine `0003` + `0004` + `0007` into a single migration

**Command:**
```bash
cd backend
python manage.py squashmigrations inventory 0003 0007 --squashed-name route_consolidation
```

**Expected Output:**
- New migration: `inventory/migrations/0003_route_consolidation_squashed.py`
- Preserves all operations from the three migrations
- References `routes_builder.0001_initial` as dependency

**Validation:**
```bash
# Fresh DB (staging/dev)
python manage.py migrate inventory 0002
python manage.py migrate inventory 0003_route_consolidation_squashed
python manage.py migrate inventory --fake-zero
python manage.py migrate
```

**Rollout:**
1. Deploy squashed migration to staging
2. Test full migration path (empty DB → latest)
3. Test existing installations (with old migrations already applied)
4. Deploy to production
5. After 1 release cycle, delete old migrations (`0003`, `0004`, `0007`)

---

### Phase 2: Remove Zombie App (Requires Production Coordination)

**Prerequisites:**
- All environments must have applied squashed migration
- No rollback to pre-squash versions planned

**Steps:**

1. **Update `routes_builder/0002`** to be a no-op:
   ```python
   # routes_builder/migrations/0002_move_route_models_to_inventory.py
   class Migration(migrations.Migration):
       dependencies = [('routes_builder', '0001_initial')]
       operations = []  # Empty - models already in inventory
   ```

2. **Remove from `INSTALLED_APPS`:**
   ```python
   # backend/settings/base.py
   INSTALLED_APPS = [
       # ...
       "inventory",
       # "routes_builder",  # REMOVED - models consolidated in inventory
   ]
   ```

3. **Archive `routes_builder` app:**
   ```bash
   mkdir -p archive/apps/
   mv backend/routes_builder archive/apps/routes_builder
   ```

4. **Update documentation:**
   - Add note to `CHANGELOG.md` about routes_builder removal
   - Update developer onboarding docs

**Validation:**
```bash
# Ensure migrations still apply cleanly
python manage.py migrate --fake-zero
python manage.py migrate
python manage.py check --deploy
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Old environments fail migration | High | Keep original migrations for 2+ release cycles before deletion |
| Rollback to pre-squash version | Medium | Document migration path reversal; test in staging |
| Third-party tools reference `routes_builder` | Low | Grep codebase for `routes_builder` imports before removal |
| Developer confusion | Low | Update README.md and architecture docs |

---

## Timeline

- **Fase 7 (Current):** Vue 3 migration — no changes to migrations
- **Fase 8 (Q1 2026):** Deploy squashed migration to production
- **Fase 9 (Q2 2026):** Remove zombie app after 2 release cycles

---

## Verification Checklist

Before removing `routes_builder`:

- [ ] Squashed migration deployed to all environments
- [ ] No references to `routes_builder` in:
  - [ ] `settings/*.py` (except INSTALLED_APPS removal)
  - [ ] `*.py` imports
  - [ ] External monitoring/deployment scripts
- [ ] Fresh DB migration tested (empty → latest)
- [ ] Existing DB upgrade tested (with old migrations)
- [ ] Rollback scenario documented
- [ ] Team notified via changelog

---

## References

- [Django Migration Squashing Docs](https://docs.djangoproject.com/en/5.0/topics/migrations/#squashing-migrations)
- `PHASE6_COMPLETION_REPORT.md` — Original context for routes_builder consolidation
- `backend/inventory/models_routes.py` — Current location of Route models
