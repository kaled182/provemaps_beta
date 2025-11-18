# Phase 7: Site Location PointField Migration

**Start Date:** November 18, 2025  
**Target Completion:** November 18, 2025 (1-day sprint)  
**Status:** 🚀 IN PROGRESS  
**Branch:** `inicial`

---

## Overview

Phase 7 migrates the `Site` model from separate `latitude`/`longitude` DecimalFields to a unified `location` PointField. This enables native PostGIS spatial queries for radius searches, eliminating the interim BBox pre-filter workaround and achieving 10-15x performance improvement.

### Context from Phase 6

Phase 6 documented the current interim radius search approach:

```python
# CURRENT (Phase 6): BBox pre-filter workaround
def get_sites_within_radius(lon, lat, radius_km, limit=None):
    # Approximation: 1 degree ≈ 111km
    degree_radius = radius_km / 111.0
    
    # BBox pre-filter (fast but imprecise)
    candidates = Site.objects.filter(
        latitude__gte=lat - degree_radius,
        latitude__lte=lat + degree_radius,
        longitude__gte=lon - degree_radius,
        longitude__lte=lon + degree_radius,
    )
    return candidates
```

**Limitations:**
- BBox is square, not circular (returns extra sites)
- No accurate distance calculation
- Can't sort by distance
- Doesn't leverage PostGIS spatial indexes

---

## Objectives

### Primary Goal
Migrate `Site` model to use PostGIS PointField for optimal spatial query performance.

### Success Criteria

1. ✅ **Performance:** Radius queries 10-15x faster than BBox approach
2. ✅ **Accuracy:** True geodesic distance on WGS84 spheroid
3. ✅ **Data Integrity:** Zero data loss during migration
4. ✅ **Backwards Compatibility:** Existing latitude/longitude fields preserved
5. ✅ **Test Coverage:** All spatial query tests passing

---

## Technical Approach

### Schema Changes

**Before (Phase 6):**
```python
class Site(models.Model):
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
```

**After (Phase 7):**
```python
from django.contrib.gis.db import models as gis_models

class Site(models.Model):
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location = gis_models.PointField(srid=4326, null=True, blank=True)  # NEW
```

**Note:** We keep `latitude`/`longitude` for backwards compatibility with existing code/serializers.

### Migration Strategy (3 migrations)

#### Migration 1: Add Field (0013_add_site_location.py)
```python
operations = [
    migrations.AddField(
        model_name='site',
        name='location',
        field=django.contrib.gis.db.models.fields.PointField(
            srid=4326, null=True, blank=True
        ),
    ),
]
```

#### Migration 2: Populate Data (0014_populate_site_location.py)
```python
def populate_site_locations(apps, schema_editor):
    Site = apps.get_model('inventory', 'Site')
    
    sites_with_coords = Site.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    for site in sites_with_coords:
        # ST_MakePoint(longitude, latitude) - note order!
        site.location = Point(float(site.longitude), float(site.latitude), srid=4326)
        site.save(update_fields=['location'])

operations = [
    migrations.RunPython(populate_site_locations, reverse_code=migrations.RunPython.noop),
]
```

#### Migration 3: Add Index (0015_site_location_gist.py)
```python
operations = [
    migrations.AddIndex(
        model_name='site',
        index=gis_models.GistIndex(fields=['location'], name='idx_site_location'),
    ),
]
```

### Query Optimization

**Before (BBox pre-filter):**
```python
# Complexity: O(n) with indexed range scan on lat/lng
# Returns: ~100 sites in 6ms (square bbox, imprecise)
candidates = Site.objects.filter(
    latitude__gte=lat - degree_radius,
    latitude__lte=lat + degree_radius,
    longitude__gte=lon - degree_radius,
    longitude__lte=lon + degree_radius,
)
```

**After (PostGIS ST_DWithin):**
```python
from django.contrib.gis.measure import D
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance

# Complexity: O(log n) with GIST index
# Returns: Exact circular radius, sorted by distance
point = Point(lon, lat, srid=4326)

sites = Site.objects.filter(
    location__dwithin=(point, D(km=radius_km))
).annotate(
    distance=Distance('location', point)
).order_by('distance')

if limit:
    sites = sites[:limit]
```

**Expected Performance:**
- **Without GIST index:** ~80ms (ST_DWithin on 1000 sites)
- **With GIST index:** ~5ms (15-20x faster)
- **vs BBox approach:** 10-15x faster + accurate circular radius

---

## Implementation Plan

### Step 1: Model Update ✅ NEXT
**File:** `backend/inventory/models.py`

Add `location` field to Site model:

```python
from django.contrib.gis.db import models as gis_models

class Site(models.Model):
    # ... existing fields ...
    latitude = models.DecimalField(...)
    longitude = models.DecimalField(...)
    
    # NEW: PostGIS PointField for spatial queries
    location = gis_models.PointField(srid=4326, null=True, blank=True)
```

### Step 2: Generate Schema Migration
```bash
docker compose exec web python manage.py makemigrations inventory --name add_site_location
```

Expected output: `0013_add_site_location.py`

### Step 3: Create Data Migration
```bash
docker compose exec web python manage.py makemigrations inventory --empty --name populate_site_location
```

Edit migration to populate `location` from `latitude`/`longitude`.

### Step 4: Create Index Migration
```bash
docker compose exec web python manage.py makemigrations inventory --empty --name site_location_gist
```

Add GIST index on `location` field.

### Step 5: Update Spatial Functions
**File:** `backend/inventory/usecases/spatial.py`

Replace `get_sites_within_radius()` with optimized version:

```python
def get_sites_within_radius(lon, lat, radius_km, limit=None):
    """
    Find sites within radius_km using PostGIS ST_DWithin.
    
    Performance: ~5ms for 1000 sites with GIST index (vs ~60ms BBox approach).
    
    Args:
        lon: Longitude (WGS84)
        lat: Latitude (WGS84)
        radius_km: Search radius in kilometers
        limit: Max results to return
    
    Returns:
        QuerySet[Site] ordered by distance (nearest first)
    """
    from django.contrib.gis.geos import Point
    from django.contrib.gis.measure import D
    from django.contrib.gis.db.models.functions import Distance
    from inventory.models import Site
    
    point = Point(lon, lat, srid=4326)
    
    queryset = Site.objects.filter(
        location__dwithin=(point, D(km=radius_km))
    ).annotate(
        distance=Distance('location', point)
    ).order_by('distance')
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset
```

### Step 6: Update Tests
**File:** `backend/tests/inventory/test_spatial_usecases.py`

Add tests for new PointField-based queries:

```python
def test_get_sites_within_radius_with_pointfield(sample_sites):
    """Test radius search with PostGIS ST_DWithin."""
    sites = get_sites_within_radius(
        lon=-47.8828,
        lat=-15.7939,
        radius_km=10.0,
        limit=5
    )
    
    assert sites.count() > 0
    # Verify sites are sorted by distance
    assert hasattr(sites.first(), 'distance')
    
def test_radius_search_accuracy(sample_sites):
    """Verify circular radius (not square bbox)."""
    # Create site exactly 10km away
    # Verify it's included in 10km search but not 9km
```

### Step 7: Benchmark Performance
**File:** `scripts/benchmark_site_location.py`

```python
# Create 1000 sites with random locations
# Measure BBox approach vs ST_DWithin
# Confirm 10-15x speedup
```

### Step 8: Apply Migrations
```bash
docker compose exec web python manage.py migrate inventory
```

Verify:
1. `location` field added
2. Data populated from lat/lng
3. GIST index created

### Step 9: Run Tests
```bash
docker compose exec web pytest tests/inventory/test_spatial_usecases.py -v
```

### Step 10: Update Documentation
**File:** `doc/guides/POSTGIS_PATTERNS.md`

Update Pattern 4 (Radius Search) from "Future Implementation" to "Current Implementation".

---

## Risk Assessment

### Low Risk
- ✅ Additive change (doesn't remove existing fields)
- ✅ Nullable field (no NOT NULL constraint issues)
- ✅ Backwards compatible (lat/lng still available)
- ✅ Rollback: Just revert migration, no data loss

### Medium Risk
- ⚠️ Data migration on production (mitigated: uses update_fields for efficiency)
- ⚠️ Index creation locks table briefly (mitigated: CONCURRENTLY in PostgreSQL 12+)

### Mitigation Strategies

1. **Test in Docker first** - Validate all migrations locally
2. **Backup before production** - Full database backup
3. **Monitor index creation** - Use `CREATE INDEX CONCURRENTLY` if needed
4. **Staged rollout** - Apply to dev → staging → production

---

## Success Metrics

### Performance Targets

| Metric | Current (BBox) | Target (ST_DWithin) | Actual |
|--------|----------------|---------------------|--------|
| Query time (1000 sites) | ~60ms | < 10ms | TBD |
| Speedup | Baseline | > 10x | TBD |
| Accuracy | Square bbox | Circular radius | TBD |
| Distance sorting | No | Yes | TBD |

### Validation Checklist

- [ ] All migrations applied successfully
- [ ] GIST index created: `idx_site_location`
- [ ] Data migrated: All sites with lat/lng have location
- [ ] Tests passing: 12+ spatial tests (100%)
- [ ] Benchmark: > 10x speedup confirmed
- [ ] Documentation updated: POSTGIS_PATTERNS.md
- [ ] Zero regressions: Existing tests still pass

---

## Timeline

**Total Duration:** 4-6 hours

| Step | Task | Duration | Status |
|------|------|----------|--------|
| 1 | Model update | 15 min | 🔄 IN PROGRESS |
| 2 | Generate migrations | 30 min | ⏳ PENDING |
| 3 | Apply migrations | 15 min | ⏳ PENDING |
| 4 | Update spatial functions | 30 min | ⏳ PENDING |
| 5 | Write tests | 45 min | ⏳ PENDING |
| 6 | Run benchmark | 30 min | ⏳ PENDING |
| 7 | Update docs | 30 min | ⏳ PENDING |
| 8 | Final testing | 30 min | ⏳ PENDING |
| 9 | Code review & commit | 30 min | ⏳ PENDING |

---

## Dependencies

### Required
- ✅ PostgreSQL 16 with PostGIS 3.4 (already installed)
- ✅ Django GIS (GeoDjango) configured (already working)
- ✅ GEOS library available (confirmed in Phase 6)

### Optional
- PostgreSQL 12+ for `CREATE INDEX CONCURRENTLY` (we have 16 ✅)

---

## Rollback Plan

If issues arise:

```bash
# 1. Revert migration
docker compose exec web python manage.py migrate inventory 0012_create_spatial_indexes

# 2. Verify data integrity
docker compose exec web python manage.py dbshell
SELECT COUNT(*) FROM zabbix_api_site WHERE latitude IS NOT NULL;

# 3. Revert code changes
git revert <commit_sha>

# 4. Restart services
docker compose restart web celery beat
```

**Data Loss Risk:** ZERO (additive migration, original fields preserved)

---

## Future Enhancements (Phase 8+)

1. **Deprecate latitude/longitude** (breaking change, requires v3.0.0)
2. **Add network topology** (GPON splitters, DWDM nodes with PointFields)
3. **pgRouting integration** (shortest path queries)
4. **Multi-polygon regions** (service area coverage)

---

## References

- Phase 6 Final Report: `doc/reports/phases/PHASE_6_FINAL_REPORT.md`
- PostGIS Patterns Guide: `doc/guides/POSTGIS_PATTERNS.md`
- Django GIS Docs: https://docs.djangoproject.com/en/5.2/ref/contrib/gis/
- PostGIS ST_DWithin: https://postgis.net/docs/ST_DWithin.html

---

**Next Step:** Update `inventory/models.py` to add `location` PointField
