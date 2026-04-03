# Phase 10 Development Notes

## ⚠️ Windows Development Limitations

### GDAL Dependency Issue

GeoDjango requires GDAL (Geospatial Data Abstraction Library) which is **complex to install on Windows**:

```
django.core.exceptions.ImproperlyConfigured: Could not find the GDAL library
```

**Solution:** Use Docker for PostGIS development instead of local installation.

---

## 🐳 Docker-Based Development (Recommended)

### 1. Setup PostGIS Container

```powershell
# From project root
cd d:\provemaps_beta

# Start PostGIS container
docker-compose -f docker/docker-compose.postgis.yml up -d postgres

# Wait for health check
docker-compose -f docker/docker-compose.postgis.yml ps
```

### 2. Configure Django for PostGIS

```powershell
# Set environment variables
$env:DB_ENGINE="postgis"
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="mapsprovefiber"
$env:DB_USER="provemaps"
$env:DB_PASSWORD="secure_password_here"
```

### 3. Run Migrations Inside Container

**Option A: Django Shell in Container**

```powershell
# Run Django inside PostGIS container
docker exec -it mapsprovefiber_postgis bash

# Inside container:
cd /app
python manage.py migrate
python manage.py createsuperuser
```

**Option B: Django on Host + PostGIS in Container**

This requires GDAL installed on Windows host (complex). Use Option A instead.

---

## 📋 Migration Files Created

### 0010_add_spatial_fields.py

- Adds `path` LineStringField to `RouteSegment` and `FiberCable`
- Keeps `path_coordinates` JSONField for MySQL compatibility
- Updates help text to mark JSONField as deprecated

### 0011_populate_spatial_fields.py

- Data migration: converts JSON → LineString
- Only runs when `DB_ENGINE=postgis` (safe for MySQL)
- Handles errors gracefully:
  - Logs invalid coordinates
  - Skips records with <2 points
  - Validates lat/lng ranges
- **Important:** PostGIS uses `(lng, lat)` order, not `(lat, lng)`!

---

## 🧪 Testing Migrations

### Test in Docker

```powershell
# Start PostGIS container
docker-compose -f docker/docker-compose.postgis.yml up -d postgres

# Run migrations inside container
docker exec -it mapsprovefiber_postgis bash -c "
  export DB_ENGINE=postgis &&
  export DB_HOST=localhost &&
  export DB_NAME=mapsprovefiber &&
  export DB_USER=provemaps &&
  export DB_PASSWORD=secure_password &&
  cd /app &&
  python manage.py migrate
"

# Check migration status
docker exec -it mapsprovefiber_postgis bash -c "
  cd /app &&
  python manage.py showmigrations inventory
"
```

Expected output:
```
inventory
 [X] 0001_initial
 [X] 0002_...
 ...
 [X] 0009_fibercable_status_cache
 [X] 0010_add_spatial_fields
 [X] 0011_populate_spatial_fields
```

### Verify Spatial Indexes

```powershell
# Connect to PostgreSQL
docker exec -it mapsprovefiber_postgis psql -U provemaps -d mapsprovefiber

# Check if spatial columns exist
\d inventory_routesegment
\d zabbix_api_fibercable

# Verify GiST indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('inventory_routesegment', 'zabbix_api_fibercable')
AND indexdef LIKE '%USING gist%';
```

---

## 🔍 Next Steps

1. ✅ **Completed:**
   - Added `path` LineStringField to models
   - Created migrations (0010 + 0011)
   - Documented Windows limitations

2. **TODO (Phase 10.3):**
   - Create GiST indexes for spatial fields
   - Add index migration: `CREATE INDEX USING GIST (path)`

3. **TODO (Phase 10.4):**
   - Implement BBox filtering API
   - Add `RouteSegmentViewSet` with `bbox` query param
   - Test spatial queries: `path__bboverlaps=bbox_polygon`

4. **TODO (Phase 10.5):**
   - Write spatial query tests
   - Performance benchmark (10k+ segments)
   - Frontend integration (Vue 3 map)

---

## 📚 References

- [GeoDjango Installation](https://docs.djangoproject.com/en/5.0/ref/contrib/gis/install/)
- [GDAL Windows Binaries](https://www.gisinternals.com/release.php)
- [PostGIS Docker Hub](https://hub.docker.com/r/postgis/postgis)
- [Spatial Lookups Cheat Sheet](https://docs.djangoproject.com/en/5.0/ref/contrib/gis/geoquerysets/#spatial-lookups)
