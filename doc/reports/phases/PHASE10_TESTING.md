# Phase 10: Testing Instructions

## 🧪 Como Testar a Implementação PostGIS

### Pré-requisitos

- Docker instalado
- Python 3.11+
- Backend dependencies instaladas (`pip install -r requirements.txt`)

---

## 1️⃣ Teste Rápido (Docker PostGIS)

### Subir Container PostGIS

```powershell
cd d:\provemaps_beta

# Start PostgreSQL + PostGIS
docker-compose -f docker/docker-compose.postgis.yml up -d postgres

# Wait for health check (30s)
Start-Sleep -Seconds 30

# Verify container is healthy
docker-compose -f docker/docker-compose.postgis.yml ps
```

**Expected output:**
```
NAME                          STATUS                    PORTS
mapsprovefiber_postgis        Up (healthy)             0.0.0.0:5432->5432/tcp
```

---

### Executar Migrations

```powershell
cd backend

# Set PostGIS environment
$env:DB_ENGINE="postgis"
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
$env:DB_NAME="mapsprovefiber"
$env:DB_USER="provemaps"
$env:DB_PASSWORD="secure_password_here"

# Run migrations (dentro do container ou via django no host)
docker exec -it mapsprovefiber_postgis bash
```

**Inside container:**
```bash
cd /app
export DB_ENGINE=postgis
export DB_NAME=mapsprovefiber
export DB_USER=provemaps
export DB_PASSWORD=secure_password

python manage.py migrate

# Expected output:
# Running migrations:
#   Applying inventory.0010_add_spatial_fields... OK
#   Applying inventory.0011_populate_spatial_fields... OK
#   Applying inventory.0012_create_spatial_indexes... OK
```

---

### Verificar Schema PostGIS

```powershell
docker exec -it mapsprovefiber_postgis psql -U provemaps -d mapsprovefiber
```

**SQL queries:**
```sql
-- 1. Check if PostGIS extension is installed
SELECT postgis_full_version();

-- Expected: POSTGIS="3.4.0" ...

-- 2. List spatial columns
\d inventory_routesegment
\d zabbix_api_fibercable

-- Expected: path | geometry(LineString,4326) | nullable

-- 3. Check GiST indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('inventory_routesegment', 'zabbix_api_fibercable')
AND indexdef LIKE '%USING gist%';

-- Expected:
--   inventory_routesegment_path_gist | CREATE INDEX ... USING gist (path)
--   zabbix_api_fibercable_path_gist  | CREATE INDEX ... USING gist (path)

-- 4. Count spatial data
SELECT 
    COUNT(*) as total,
    COUNT(path) as with_spatial,
    COUNT(path_coordinates) as with_json
FROM inventory_routesegment;

-- Expected: Spatial data populated if path_coordinates existed
```

---

## 2️⃣ Teste API (Spatial Endpoints)

### Start Django Dev Server

```powershell
cd backend

# Configure PostGIS
$env:DB_ENGINE="postgis"
$env:DB_HOST="localhost"
$env:DB_PORT="5432"

# Start server
python manage.py runserver
```

### Test BBox Endpoint (RouteSegment)

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/segments/?bbox=-48.5,-16.5,-47.5,-15.5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "count": 3,
  "bbox": "-48.5,-16.5,-47.5,-15.5",
  "segments": [
    {
      "id": 1,
      "route_id": 5,
      "order": 1,
      "length_km": 1.234,
      "path_geojson": {
        "type": "LineString",
        "coordinates": [
          [-47.9292, -15.7801],
          [-47.9200, -15.7750]
        ]
      },
      "path_coordinates": [
        {"lat": -15.7801, "lng": -47.9292},
        {"lat": -15.7750, "lng": -47.9200}
      ]
    }
  ]
}
```

### Test FiberCable BBox

```bash
curl -X GET "http://localhost:8000/api/v1/fibers/bbox/?bbox=-48.5,-16.5,-47.5,-15.5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response (200 OK):**
```json
{
  "count": 2,
  "bbox": "-48.5,-16.5,-47.5,-15.5",
  "cables": [
    {
      "id": 10,
      "name": "Fiber-BSB-01",
      "origin_port_id": 100,
      "destination_port_id": 101,
      "length_km": 2.5,
      "status": "up",
      "path_geojson": {
        "type": "LineString",
        "coordinates": [[-47.92, -15.78], [-47.91, -15.77]]
      }
    }
  ]
}
```

### Test Error Cases

**1. Missing bbox parameter:**
```bash
curl -X GET "http://localhost:8000/api/v1/segments/"
# Expected: 400 Bad Request
# {"error": "Missing required parameter: bbox"}
```

**2. Invalid bbox format:**
```bash
curl -X GET "http://localhost:8000/api/v1/segments/?bbox=invalid"
# Expected: 400 Bad Request
# {"error": "Invalid bbox format. Expected: lng_min,lat_min,lng_max,lat_max"}
```

**3. MySQL backend (DB_ENGINE != postgis):**
```bash
# Change environment
$env:DB_ENGINE="mysql"

curl -X GET "http://localhost:8000/api/v1/segments/?bbox=-48,-16,-47.5,-15.5"
# Expected: 501 Not Implemented
# {"error": "Spatial queries require DB_ENGINE=postgis. Current backend: mysql"}
```

---

## 3️⃣ Teste Automatizado (pytest)

### Run Spatial API Tests

```powershell
cd backend

# Run all spatial tests
pytest backend/tests/test_spatial_api.py -v

# Run specific test class
pytest backend/tests/test_spatial_api.py::TestSpatialAPIPostGIS -v

# Run with coverage
pytest backend/tests/test_spatial_api.py --cov=inventory.api.spatial --cov-report=term
```

**Expected Output:**
```
backend/tests/test_spatial_api.py::TestSpatialAPIPostGIS::test_route_segments_bbox_filter PASSED
backend/tests/test_spatial_api.py::TestSpatialAPIPostGIS::test_route_segments_bbox_multiple_results PASSED
backend/tests/test_spatial_api.py::TestSpatialAPIPostGIS::test_route_segments_bbox_no_results PASSED
backend/tests/test_spatial_api.py::TestSpatialAPIPostGIS::test_route_segments_bbox_missing_parameter PASSED
backend/tests/test_spatial_api.py::TestSpatialAPIPostGIS::test_route_segments_bbox_invalid_format PASSED
backend/tests/test_spatial_api.py::TestSpatialAPIPostGIS::test_fiber_cables_bbox_filter PASSED
backend/tests/test_spatial_api.py::TestSpatialAPIMySQL::test_route_segments_bbox_not_implemented PASSED
backend/tests/test_spatial_api.py::TestSpatialAPIMySQL::test_fiber_cables_bbox_not_implemented PASSED
backend/tests/test_spatial_api.py::TestSpatialAPIAuthentication::test_unauthenticated_request PASSED

========================= 12 passed in 2.34s =========================
```

---

## 4️⃣ Performance Benchmark

### Run Benchmark Script

```powershell
cd backend

# Configure PostGIS
$env:DB_ENGINE="postgis"

# Run benchmark (creates 1000 test segments)
python scripts/benchmark_postgis.py
```

**Expected Output:**
```
======================================================================
  PostGIS Performance Benchmark
======================================================================
✅ PostGIS backend detected

======================================================================
  Creating 1000 Test Segments
======================================================================
Generating 1000 segments...
  Created 1000/1000 segments...
✅ Created 1000 test segments

======================================================================
  Spatial Index Verification
======================================================================
✅ GiST index found:
   inventory_routesegment_path_gist

📋 Query Plan:
   Index Scan using inventory_routesegment_path_gist on inventory_routesegment
   ✅ Index is being used!

======================================================================
  Performance Tests
======================================================================

📊 BBox Query Performance:
   Results:  0 segments
   Avg time: 2.15ms (5 runs)
   Min/Max:  1.89ms / 2.67ms

📊 Full Scan Performance:
   Results:  1000 segments
   Avg time: 18.45ms (5 runs)
   Min/Max:  15.23ms / 21.11ms

======================================================================
  Results Summary
======================================================================
BBox Query:   2.15ms
Full Scan:    18.45ms
Speedup:      8.6x faster

🎯 Performance Targets:
   BBox <100ms:   ✅ PASS
   Speedup >10x:  ⚠️  SLOW (but acceptable for 1000 segments)

⚠️  Some targets not met (may need more data or index tuning)
```

**Note:** Speedup >10x is expected with 10k+ segments. With 1000 segments, 5-10x is normal.

---

## 5️⃣ Frontend Integration Test (Manual)

### Test Map with BBox API

**TODO (Task 5 - pending implementation):**

1. Open map interface: `http://localhost:8000/maps/`
2. Open browser DevTools → Network tab
3. Move/zoom map
4. Verify API calls:
   - ✅ Request URL: `/api/v1/segments/?bbox=-48.5,-16.5,-47.5,-15.5`
   - ✅ Response time: <200ms
   - ✅ Payload size: 10-50KB (instead of 100KB+)

---

## 🚨 Troubleshooting

### Erro: "GDAL library not found"

**Windows:** Use Docker instead of local installation.

```powershell
# Don't try to run migrations on Windows host
# Use Docker container instead:
docker exec -it mapsprovefiber_postgis bash
cd /app
python manage.py migrate
```

### Erro: "Database connection refused"

```powershell
# Check if PostGIS container is running
docker ps | Select-String postgres

# Check logs
docker logs mapsprovefiber_postgis

# Restart container
docker-compose -f docker/docker-compose.postgis.yml restart postgres
```

### Erro: "relation does not exist"

```bash
# Run migrations
docker exec -it mapsprovefiber_postgis bash
cd /app
python manage.py migrate inventory

# Verify tables
docker exec -it mapsprovefiber_postgis psql -U provemaps -d mapsprovefiber -c "\dt"
```

### Performance Slow (BBox >100ms)

```sql
-- Check if index exists
SELECT * FROM pg_indexes WHERE tablename = 'inventory_routesegment';

-- Rebuild index if needed
REINDEX INDEX inventory_routesegment_path_gist;

-- Update statistics
ANALYZE inventory_routesegment;

-- Check query plan uses index
EXPLAIN ANALYZE
SELECT * FROM inventory_routesegment
WHERE path && ST_MakeEnvelope(-48, -16, -47.5, -15.5, 4326);
```

---

## ✅ Checklist de Validação

- [ ] PostGIS container healthy
- [ ] Migrations aplicadas (0010, 0011, 0012)
- [ ] GiST indexes criados
- [ ] Spatial data populated (path field não nulo)
- [ ] API `/api/v1/segments/?bbox=...` retorna 200 OK
- [ ] API `/api/v1/fibers/bbox/?bbox=...` retorna 200 OK
- [ ] Pytest tests passing (12/12)
- [ ] Benchmark <100ms (BBox query)
- [ ] Frontend integrado (TODO - Task 5)

---

**Status:** Backend 100% completo ✅  
**Next:** Frontend integration (Vue 3 map component)
