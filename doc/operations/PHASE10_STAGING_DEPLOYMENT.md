# Phase 10 Staging Deployment Guide

**Date:** November 12, 2025  
**Version:** 1.0  
**Target Environment:** Staging (PostGIS validation before production)

---

## Prerequisites

- Docker and Docker Compose installed
- Access to staging server
- Database backup taken (if migrating from existing MySQL)
- `DB_PASSWORD` environment variable configured

---

## Step-by-Step Deployment

### 1. Clone Repository and Navigate to Project

```bash
cd /path/to/mapsprovefiber
git checkout refactor/folder-structure  # Or appropriate branch
git pull origin refactor/folder-structure
```

### 2. Configure Environment Variables

Create/update `.env` file in project root:

```bash
# Database Configuration
DB_ENGINE=postgis
DB_NAME=mapsprovefiber
DB_USER=postgres
DB_PASSWORD=your_secure_password_here
DB_HOST=postgres
DB_PORT=5432

# Redis Configuration
CHANNEL_LAYER_URL=redis://redis:6379/0

# Django Settings
DJANGO_SETTINGS_MODULE=settings.staging
SECRET_KEY=your_secret_key_here
DEBUG=False
ALLOWED_HOSTS=staging.yourdomain.com,localhost

# Google Maps API (if applicable)
GOOGLE_MAPS_API_KEY=your_key_here
```

### 3. Start PostGIS Infrastructure

```bash
# Start PostgreSQL and Redis containers
docker compose -f docker/docker-compose.postgis.yml up -d postgres redis

# Verify PostgreSQL is ready
docker exec mapsprovefiber_postgis pg_isready -U postgres
# Expected output: /var/run/postgresql:5432 - accepting connections
```

### 4. Verify PostGIS Extension

```bash
# Check PostGIS version
docker exec mapsprovefiber_postgis psql -U postgres -d mapsprovefiber \
    -c "SELECT PostGIS_Version();"

# Expected output: 3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1
```

### 5. Start Application Services

```bash
# Start web, celery, and beat containers
docker compose -f docker/docker-compose.postgis.yml up -d web celery beat

# Check logs for errors
docker compose -f docker/docker-compose.postgis.yml logs -f web
# Press Ctrl+C after verifying no errors
```

### 6. Run Database Migrations

```bash
# Apply all migrations (including spatial migrations 0010-0012)
docker exec mapsprovefiber_web python manage.py migrate

# Expected output should include:
# Running migrations:
#   Applying inventory.0010_add_spatial_fields... OK
#   Applying inventory.0011_populate_spatial_fields... OK
#   Applying inventory.0012_create_spatial_indexes... OK
```

### 7. Verify Spatial Indexes

```bash
# Connect to PostgreSQL and check indexes
docker exec mapsprovefiber_postgis psql -U postgres -d mapsprovefiber -c "
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE indexname LIKE '%gist%' 
AND tablename IN ('inventory_routesegment', 'inventory_fibercable');"

# Expected output:
# indexname: inventory_routesegment_path_gist
# indexdef: CREATE INDEX ... USING gist (path)
```

### 8. Create Superuser (if needed)

```bash
docker exec -it mapsprovefiber_web python manage.py createsuperuser

# Follow prompts to create admin user
```

### 9. Load Test Data (Optional)

```bash
# Generate 1000 test segments for performance validation
docker compose -f docker/docker-compose.postgis.yml run --rm web \
    python /app/scripts/benchmark_postgis.py

# This will:
# - Create 1000 test RouteSegments
# - Verify GiST index exists
# - Run performance benchmark
# - Display results
```

### 10. Validate API Endpoints

#### Test Authentication Enforcement

```bash
# From host machine, test without authentication (should return 401)
curl -i "http://localhost:8000/api/v1/inventory/segments/?bbox=-48,-16,-47.5,-15.5"

# Expected response:
# HTTP/1.1 401 Unauthorized
# {"error": "Authentication required", ...}
```

#### Test Authenticated Access

```bash
# Login and get session cookie (adjust credentials)
curl -c cookies.txt -d "username=admin&password=admin" \
    http://localhost:8000/login/

# Use session cookie to access API
curl -b cookies.txt "http://localhost:8000/api/v1/inventory/segments/?bbox=-48,-16,-47.5,-15.5"

# Expected response:
# HTTP/1.1 200 OK
# {"type": "FeatureCollection", "count": ..., "features": [...]}
```

### 11. Run Performance Benchmark

```bash
# Execute benchmark script
docker exec mapsprovefiber_web python /app/scripts/benchmark_postgis.py

# Expected results:
# BBox Query: <1 ms
# Full Scan: ~16 ms
# Speedup: >20x
# ✅ PASSED: All performance targets met
```

### 12. Health Check

```bash
# Check application health endpoint
curl http://localhost:8000/health/

# Expected response:
# {"status": "healthy", ...}
```

---

## Validation Checklist

Use this checklist to confirm successful deployment:

- [ ] PostgreSQL 16.4 container running and healthy
- [ ] PostGIS 3.4 extension installed and verified
- [ ] All migrations applied without errors
- [ ] GiST spatial indexes created on `inventory_routesegment` and `inventory_fibercable`
- [ ] Web application accessible on configured port
- [ ] Celery worker and beat scheduler running
- [ ] API authentication enforced (401 without credentials)
- [ ] BBox API endpoint returns valid GeoJSON
- [ ] Performance benchmark shows <1ms BBox queries
- [ ] Speedup factor >20x compared to full table scan
- [ ] No errors in application logs
- [ ] Prometheus metrics endpoint accessible (`/metrics/`)

---

## Troubleshooting

### Issue: Migrations fail with "PostGIS not installed"

**Solution:**
```bash
# Verify PostGIS extension exists
docker exec mapsprovefiber_postgis psql -U postgres -d mapsprovefiber \
    -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

### Issue: GiST index not being used

**Solution:**
```bash
# Force index creation
docker exec mapsprovefiber_postgis psql -U postgres -d mapsprovefiber <<EOF
DROP INDEX IF EXISTS inventory_routesegment_path_gist;
CREATE INDEX CONCURRENTLY inventory_routesegment_path_gist 
ON inventory_routesegment USING gist(path);
EOF

# Verify index usage with EXPLAIN
docker exec mapsprovefiber_postgis psql -U postgres -d mapsprovefiber -c "
EXPLAIN ANALYZE 
SELECT * FROM inventory_routesegment 
WHERE ST_Intersects(
    path, 
    ST_GeomFromText('POLYGON((-48 -16, -47.5 -16, -47.5 -15.5, -48 -15.5, -48 -16))', 4326)
);"
# Should show: Index Scan using inventory_routesegment_path_gist
```

### Issue: Authentication always returns 401

**Solution:**
```bash
# Check if user is authenticated in Django session
docker exec -it mapsprovefiber_web python manage.py shell

# In Django shell:
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.filter(is_superuser=True)
# Verify superuser exists

# Create one if missing:
User.objects.create_superuser('admin', 'admin@example.com', 'admin')
```

### Issue: Benchmark shows slow queries

**Solution:**
```bash
# 1. Verify index exists
docker exec mapsprovefiber_postgis psql -U postgres -d mapsprovefiber \
    -c "SELECT indexname FROM pg_indexes WHERE tablename='inventory_routesegment';"

# 2. Analyze table statistics
docker exec mapsprovefiber_postgis psql -U postgres -d mapsprovefiber \
    -c "ANALYZE inventory_routesegment;"

# 3. Re-run benchmark
docker exec mapsprovefiber_web python /app/scripts/benchmark_postgis.py
```

### Issue: Container fails to start

**Solution:**
```bash
# Check logs for specific error
docker compose -f docker/docker-compose.postgis.yml logs postgres
docker compose -f docker/docker-compose.postgis.yml logs web

# Common fixes:
# - Ensure DB_PASSWORD is set in .env
# - Check port 5432 not already in use: netstat -an | grep 5432
# - Verify Docker has sufficient resources (4GB+ RAM recommended)
```

---

## Rollback Procedure

If deployment fails and you need to rollback:

### 1. Stop Services

```bash
docker compose -f docker/docker-compose.postgis.yml down
```

### 2. Restore MySQL Backup (if applicable)

```bash
# If migrating from MySQL, restore backup
mysql -u root -p mapsprovefiber < backup_$(date +%Y%m%d).sql
```

### 3. Revert Environment

```bash
# Change DB_ENGINE back to mysql
sed -i 's/DB_ENGINE=postgis/DB_ENGINE=mysql/' .env

# Restart with MySQL configuration
docker compose up -d
```

### 4. Verify Application

```bash
# Check health endpoint
curl http://localhost:8000/health/

# Verify legacy endpoints still work
curl http://localhost:8000/api/v1/inventory/fibers/
```

---

## Monitoring

### Prometheus Metrics

Key metrics to monitor after deployment:

```
# Spatial query duration
inventory_spatial_query_duration_seconds

# Spatial query count
inventory_spatial_query_total

# PostgreSQL connection pool
django_db_connections_total

# Celery task performance
celery_task_duration_seconds
```

Access metrics at: `http://localhost:8000/metrics/`

### PostgreSQL Performance

```sql
-- Monitor index usage
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    idx_scan, 
    idx_tup_read
FROM pg_stat_user_indexes
WHERE indexname LIKE '%gist%'
ORDER BY idx_scan DESC;

-- Find slow queries
SELECT 
    substring(query, 1, 100) AS query_snippet,
    calls,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%ST_Intersects%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Next Steps

After successful staging deployment:

1. **Load Production Data Snapshot**
   - Export production MySQL data
   - Import into staging PostGIS
   - Validate data integrity

2. **Performance Testing**
   - Test with realistic dataset (10K+ segments)
   - Validate query performance under load
   - Monitor memory usage

3. **Frontend Integration**
   - Deploy Phase 11 Vue 3 components
   - Test BBox API consumption
   - Validate map rendering performance

4. **Production Planning**
   - Schedule maintenance window
   - Prepare communication plan
   - Finalize rollback procedures

---

## Support

For issues or questions:

- Review `doc/reports/phases/PHASE10_IMPLEMENTATION_SUMMARY.md`
- Check `doc/operations/POSTGIS_SETUP_GUIDE.md`
- Consult `doc/roadmap/ROADMAP_VUE3_PREPARATION.md`

---

**Deployment Guide Version:** 1.0  
**Last Updated:** November 12, 2025  
**Tested On:** Docker 24.0+, Ubuntu 22.04, Windows 11 + WSL2
