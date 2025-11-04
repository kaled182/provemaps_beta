# Deployment Guide - MapsProveFiber

Instructions for deploying **MapsProveFiber** to production.

---

## Service Layout

| Service | Port | Description |
|---------|------|-------------|
| web     | 8000 | Django with Gunicorn |
| celery  | -    | Celery worker |
| beat    | -    | Celery scheduler |
| redis   | 6379 | Cache and queues (single point of failure in dev) |
| db      | 3306 | MariaDB or MySQL |

---

## Critical: Redis High Availability

Development runs a single Redis instance, which becomes a single point of failure in production. Use one of the following approaches for high availability.

### Option A: Managed Redis (preferred)
Use a cloud managed service with replication, such as AWS ElastiCache, Google Cloud Memorystore, or Azure Cache for Redis.

```
REDIS_URL=redis://prod-cluster.example.cache.amazonaws.com:6379/0
```

### Option B: Redis Sentinel
Deploy a three-node Sentinel cluster (one primary, two replicas) and configure the application to discover the active primary.

```
REDIS_USE_SENTINEL=true
REDIS_SENTINELS=sentinel1:26379,sentinel2:26379,sentinel3:26379
REDIS_MASTER_NAME=mymaster
REDIS_PASSWORD=your-secure-password
```

See `doc/reference/REDIS_HIGH_AVAILABILITY.md` for detailed guidance.

---

## Setup Steps

### 1. Configure environment variables

```
cp .env.production.example .env.production
nano .env.production
```

Required settings:
- `SECRET_KEY` (at least 50 characters)
- `ALLOWED_HOSTS`
- Database credentials (`DB_PASSWORD`, host, name)
- Redis configuration (`REDIS_URL` or Sentinel variables)

Common tuning parameters:
- `DASHBOARD_CACHE_REFRESH_INTERVAL=60`
- `INVENTORY_SYNC_INTERVAL_SECONDS=86400`

### 2. Build and deploy

```
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

### 3. Run migrations

```
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### 4. Create a superuser

```
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### 5. Collect static files

```
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

---

## Health Checks

| Endpoint | Purpose | Expected response |
|----------|---------|-------------------|
| `/health/` | Overall status | `200 OK` with JSON |
| `/health/ready/` | Ready for traffic | `200 OK` |
| `/health/live/` | Process alive | `200 OK` |
| `/metrics/` | Prometheus metrics | `200 OK` with text |

Example:

```
curl http://localhost:8000/health/

{
  "status": "healthy",
  "database": "ok",
  "redis": "ok",
  "celery": "ok"
}
```

---

## Backup and Recovery

### Database

```
docker compose -f docker-compose.prod.yml exec db sh -c \
  'mysqldump -u root -p$MYSQL_ROOT_PASSWORD mapspro_db > /backups/db_$(date +%Y%m%d_%H%M%S).sql'

docker compose -f docker-compose.prod.yml exec -T db sh -c \
  'mysql -u root -p$MYSQL_ROOT_PASSWORD mapspro_db < /backups/db_20250127_120000.sql'
```

### Redis (RDB persistence)

```
docker compose -f docker-compose.prod.yml exec redis redis-cli BGSAVE
docker cp redis:/data/dump.rdb ./backups/redis_$(date +%Y%m%d_%H%M%S).rdb
```

---

## Rollback Procedures

### Deploy rollback

```
git checkout <previous-tag>
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
curl http://localhost:8000/health/
```

### Full rollback with database recovery

```
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d db
docker compose -f docker-compose.prod.yml exec -T db sh -c \
  'mysql -u root -p$MYSQL_ROOT_PASSWORD mapspro_db < /backups/db_backup_before_deploy.sql'
git checkout <previous-tag>
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Monitoring

### Container logs

```
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs --tail=100 celery
```

### Prometheus metrics

```
curl http://localhost:8000/metrics/
# Track metrics such as:
# - django_http_requests_latency_seconds
# - django_db_query_duration_seconds
# - celery_task_total
# - redis_connected_clients
```

---

## Troubleshooting

### Service will not start

```
docker compose -f docker-compose.prod.yml logs <service-name>
docker compose -f docker-compose.prod.yml ps
docker inspect <container-id>
```

### Database connectivity

```
docker compose -f docker-compose.prod.yml exec web python manage.py dbshell
docker compose -f docker-compose.prod.yml exec db mysql -u root -p -e "SHOW DATABASES;"
```

### Redis connectivity

```
docker compose -f docker-compose.prod.yml exec redis redis-cli PING
docker compose -f docker-compose.prod.yml exec redis redis-cli INFO
```

### Celery tasks idle

```
docker compose -f docker-compose.prod.yml logs celery
docker compose -f docker-compose.prod.yml exec celery celery -A core inspect active
docker compose -f docker-compose.prod.yml logs beat
```

---

## Pre-Deployment Checklist

- [ ] SECRET_KEY is unique to production
- [ ] DEBUG is set to false
- [ ] ALLOWED_HOSTS includes the production domain
- [ ] Redis HA (managed or Sentinel) is in place
- [ ] Database backups are automated
- [ ] HTTPS enforced (`SECURE_SSL_REDIRECT=true`)
- [ ] CSRF_TRUSTED_ORIGINS includes production domain
- [ ] SMTP configuration is complete
- [ ] Error tracking (Sentry or similar) configured if required
- [ ] Health endpoints reachable
- [ ] Prometheus metrics enabled
- [ ] Static files collected
- [ ] Migrations applied
- [ ] Superuser created

---

## Additional Resources

- `doc/reference/REDIS_HIGH_AVAILABILITY.md`
- `doc/reference/performance_phase6.md`
- `doc/reference/operations_checklist.md`

---

## Quick Fix Table

| Issue | Remedy |
|-------|--------|
| Database container fails to start | Inspect volumes or `.env` credentials |
| Celery stopped | `docker compose restart celery beat` |
| Health endpoint returns 503 | Validate Redis and database status |
| Static assets missing | `python manage.py collectstatic --noinput` |

---

MapsProveFiber - 2025
