# Service Status - MapsProveFiber

## Executive Summary

- **Date:** 2025-10-25 23:34
- **Environment:** Local development (Windows)
- **Overall Status:** All services operational

---

## Redis (cache and session)

- **Status:** Online
- **Technology:** Docker Redis Alpine
- **Container:** `redis-mapspro`
- **Port:** 6379
- **Auto restart:** Enabled (`unless-stopped`)

### Useful commands

```powershell
# Show status
docker ps | findstr redis

# Tail logs
docker logs -f redis-mapspro

# Stop temporarily
docker stop redis-mapspro

# Start again
docker start redis-mapspro

# Restart
docker restart redis-mapspro

# Remove container (only if required)
docker rm -f redis-mapspro
```

### Monitoring

```powershell
# Connect to redis-cli
docker exec -it redis-mapspro redis-cli

# Inside redis-cli:
PING                  # Expect PONG
DBSIZE                # Number of keys in cache
INFO stats            # Operation statistics
INFO memory           # Memory usage
KEYS mapspro:*        # Inspect application keys (dev only)
MONITOR               # Live commands (CTRL+C to exit)
CLIENT LIST           # Active connections
```

### Python verification

```powershell
python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('Redis:', 'Online' if r.ping() else 'Offline')"
```

Expected output: `Redis: Online`

---

## Django application server

- **Status:** Running in background
- **URL:** http://localhost:8000
- **Port:** 8000
- **Terminal ID:** `28271102-c51f-4d6b-afa3-62e6590f538d`

### Key endpoints

- Dashboard: http://localhost:8000/maps_view/dashboard/
- Admin: http://localhost:8000/admin/
- Health: http://localhost:8000/healthz
- Metrics: http://localhost:8000/metrics/metrics
- Zabbix Lookup: http://localhost:8000/zabbix/lookup/
- Docs: http://localhost:8000/setup_app/docs/

### Observed behavior

- No offline cache warnings (Redis healthy)
- HTTP 200 responses across endpoints
- Cache layer active (Redis storing and returning values)
- WebSocket 404 expected (Channels not configured; non-critical)

### Performance

- Initial request: about 600 to 900 ms (uncached, direct Zabbix call)
- Subsequent requests: expected under 50 ms (cache hit)
- Zabbix queries cached automatically

---

## SQLite database

- **Status:** Operational
- **File:** `d:\provemaps_beta\db.sqlite3`
- **Size:** roughly 1.5 MB
- **Migrations:** Applied (0003, 0009)

### Seed data

- Superuser `admin` / `admin123`
- Device models
- Fiber cables
- Ports (38 plus)
- Sites (2 plus)

---

## Optional services (not configured)

### Celery worker
- **Status:** Not running
- **Purpose:** Asynchronous tasks (route building, batch work)
- **Start:**
```powershell
celery -A core worker -l info --pool=solo
```

### Celery beat
- **Status:** Not running
- **Purpose:** Periodic tasks
- **Start:**
```powershell
celery -A core beat -l info
```

### Django Channels (WebSocket)
- **Status:** Not configured
- **Purpose:** Real-time dashboard updates
- **Requires:** Daphne or Uvicorn plus Redis channel layer

---

## External integrations

### Zabbix API
- **Status:** Reachable
- **URL:** Provided in `.env` via `ZABBIX_API_URL`
- **Auth:** Token valid
- **Latency:** About 600 to 900 ms per request
- **Note:** All Zabbix responses are cached in Redis to reduce load

### Google Maps API
- **Status:** Not configured
- **Requires:** `GOOGLE_MAPS_API_KEY` in `.env`
- **Impact:** Maps may not render correctly

---

## Starting all services

### Full startup

```powershell
# 1. Start Redis if not running
docker start redis-mapspro

# 2. Check Redis
docker ps | findstr redis

# 3. Start Django
cd D:\provemaps_beta
python manage.py runserver 0.0.0.0:8000

# 4. Optional Celery worker
celery -A core worker -l info --pool=solo

# 5. Optional Celery beat
celery -A core beat -l info
```

### Quick verification

```powershell
# Redis online?
docker ps | findstr redis

# Django responding?
curl http://localhost:8000/healthz

# Cache responding?
python -c "from django.core.cache import cache; cache.set('test', 'ok', 10); print('Cache:', cache.get('test'))"
```

---

## Logs and debugging

### Django Logs
**Location:** Terminal running `manage.py runserver`  
**Level:** DEBUG (set in .env)  
**Filter cache:** `findstr "cache" logs\application.log`

### Redis Logs
```powershell
docker logs redis-mapspro --tail 100 -f
```

### Docker Logs
```powershell
# List all containers
docker ps -a

# Specific logs
docker logs <container_id>
```

---

## Validation tests

### 1. Health Check
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/healthz"
```
**Expected:** HTTP 200 and JSON with `"status": "ok"`

### 2. Cache Hit Test
```powershell
# First call (cold cache, about 800 ms)
Measure-Command { Invoke-WebRequest -Uri "http://localhost:8000/zabbix_api/api/sites/" }

# Second call (cache hit, expected under 50 ms)
Measure-Command { Invoke-WebRequest -Uri "http://localhost:8000/zabbix_api/api/sites/" }
```

### 3. Redis Persistence Test
```powershell
# Set key
docker exec redis-mapspro redis-cli SET test_key "Hello Redis"

# Fetch key
docker exec redis-mapspro redis-cli GET test_key

# Delete key
docker exec redis-mapspro redis-cli DEL test_key
```

---

## Next steps

### Essentials
- [x] Redis configured and running
- [x] Django with cache enabled
- [x] SQLite database operational
- [x] Superuser created
- [x] Static files collected

### Optional
- [ ] Configure Celery worker
- [ ] Configure Celery beat
- [ ] Add Google Maps API key
- [ ] Configure Django Channels (WebSocket)
- [ ] Enable local SSL/TLS (for https)
- [ ] Configure automatic SQLite backups

### Production
- [ ] Migrate SQLite to MySQL or PostgreSQL
- [ ] Configure Gunicorn or Uvicorn
- [ ] Nginx reverse proxy
- [ ] SSL certificates (Let's Encrypt)
- [ ] Redis persistence (RDB plus AOF)
- [ ] Monitoring (Prometheus and Grafana)

---

## Troubleshooting

### Redis does not start
```powershell
# Check if port is in use
netstat -ano | findstr :6379

# Kill process if required
taskkill /PID <pid> /F

# Remove old container
docker rm -f redis-mapspro

# Recreate
docker run -d --name redis-mapspro -p 6379:6379 --restart unless-stopped redis:alpine
```

### Django cannot connect to Redis
```powershell
# Check REDIS_URL in .env
cat .env | findstr REDIS_URL

# Should be redis://127.0.0.1:6379/0 or redis://localhost:6379/0

# Test Python connection
python -c "import redis; redis.Redis().ping()"
```

### Performance issues even with cache
```powershell
# Check cache statistics
docker exec redis-mapspro redis-cli INFO stats

# Check hit rate
# hits / (hits + misses) should stay above 70%
```

---

## Support

**Documentation:** See [`doc/reference/SETUP_REDIS_WINDOWS.md`](../reference/SETUP_REDIS_WINDOWS.md) for full details  
**Redis issues:** https://github.com/redis/redis/issues  
**Django cache:** https://docs.djangoproject.com/en/5.2/topics/cache/  

---

**Last update:** 2025-10-25 23:34  
**Owner:** DevOps Team  
**Environment:** Windows local development  
**Status:** All essential services operational
