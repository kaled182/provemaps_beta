
# Migration Guide: zabbix_api to inventory

## Goal
Move the inventory models (Site, Device, Port, FiberCable, FiberEvent) from the `zabbix_api` app into the dedicated `inventory` app without changing the existing database schema.

## Strategy
Leverage `Meta.db_table` on both apps so the new models reuse the current tables during the transition.

---

## Step 1: Mark legacy models as unmanaged

Edit `zabbix_api/models.py` and set `managed = False` plus `db_table` for each model:

```python
class Site(models.Model):
    # existing fields

    class Meta:
        ordering = ["name"]
        managed = False
        db_table = "zabbix_api_site"
```

Repeat the same change for `Device`, `Port`, `FiberCable`, and `FiberEvent`.

Important: add the `db_table` attribute with the current table name on every model.

---

## Step 2: Create a fake migration for zabbix_api

```powershell
python manage.py makemigrations zabbix_api --name unmanage_inventory_models
```

This migration tells Django the models are now unmanaged.

Apply it:
```powershell
python manage.py migrate zabbix_api
```

---

## Step 3: Create the initial migration for inventory

```powershell
python manage.py makemigrations inventory --name initial_from_existing_tables
```

This migration creates the model definitions inside `inventory` that point to the existing tables.

---

## Step 4: Apply the inventory migration as fake initial

Because the tables already exist, mark the migration as applied without running SQL:

```powershell
python manage.py migrate inventory --fake-initial
```

Django now records that `inventory` manages those tables without attempting to recreate them.

---

## Step 5: Update imports across the codebase

Replace each import line:

```python
from zabbix_api.models import Site, Device, Port, FiberCable, FiberEvent
```

with:

```python
from inventory.models import Site, Device, Port, FiberCable, FiberEvent
```

Files to double-check include:
- `zabbix_api/inventory.py`
- `zabbix_api/inventory_fibers.py`
- `zabbix_api/views.py`
- `zabbix_api/admin.py` (if those models were registered)
- `maps_view/views.py`
- `maps_view/services_old/`
- `routes_builder/views.py`
- Any tests that import the inventory models

---

## Step 6: Deprecate the old models module

Turn `zabbix_api/models.py` into a re-export that points to `inventory` so legacy imports continue working without duplicating model definitions:

```python
from inventory.models import Device, FiberCable, FiberEvent, Port, Site

__all__ = ["Site", "Device", "Port", "FiberCable", "FiberEvent"]
```

No additional migrations are required inside `zabbix_api`; the tables are now owned by `inventory`.

---

## Step 7: Run validation tests

Run the test suite to confirm nothing breaks:

```powershell
python manage.py test
```

Check that the tables still exist:

```powershell
python manage.py dbshell
```

Inside the database shell:
```sql
SHOW TABLES LIKE 'zabbix_api_%';
```

Expected list:
- `zabbix_api_site`
- `zabbix_api_device`
- `zabbix_api_port`
- `zabbix_api_fibercable`
- `zabbix_api_fiberevent`

---

## Integrity checks

### Locate every old import

```powershell
Get-ChildItem -Recurse -Include *.py | Select-String "from zabbix_api.models import.*Site|Device|Port|FiberCable|FiberEvent" | Select-Object Path, LineNumber, Line
```

### Alternative command using grep

```bash
grep -rn "from zabbix_api.models import.*(Site|Device|Port|FiberCable|FiberEvent)" --include="*.py" .
```

---

## Migration summary

| Step | Command | Effect |
| --- | --- | --- |
| 1 | Edit `zabbix_api/models.py` | Add `managed=False` and `db_table` |
| 2 | `makemigrations zabbix_api` | Record the unmanaged status |
| 3 | `migrate zabbix_api` | Apply the change without touching data |
| 4 | `makemigrations inventory` | Create the inventory models |
| 5 | `migrate inventory --fake-initial` | Register ownership of existing tables |
| 6 | Update imports | Switch code to read from `inventory.models` |
| 7 | Replace `zabbix_api/models.py` | Provide a re-export for backward compatibility |
| 8 | `makemigrations` / `migrate zabbix_api` | Capture final cleanup if needed |

---

## Warnings

1. Back up the database before starting.
2. Do not run `migrate` without `--fake-initial` in step 5.
3. The migration must never attempt to recreate the tables.
4. Foreign keys referencing those models must point to `inventory`:
   ```python
   # Before
   site = models.ForeignKey('zabbix_api.Site', ...)

   # After
   site = models.ForeignKey('inventory.Site', ...)
   ```

---

## Expected outcome

- The `inventory` app owns the five inventory models.
- Database tables remain untouched.
- Admin, views, and services continue to work.
- The `zabbix_api` app focuses on the Zabbix integration layer.
- The codebase becomes easier to maintain.
