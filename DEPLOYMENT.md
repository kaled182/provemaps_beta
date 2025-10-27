# 🚀 Deployment Guide — MapsProveFiber

Guia para implantar o **MapsProveFiber** em produção.

---

## 🧩 Estrutura dos serviços

| Serviço | Porta | Descrição |
|----------|--------|------------|
| web | 8000 | Django + Gunicorn |
| celery | - | Worker de tarefas |
| beat | - | Scheduler Celery |
| redis | 6379 | Cache e filas (⚠️ SPOF - ver seção Redis HA) |
| db | 3306 | MariaDB/MySQL |

---

## ⚠️ **CRITICAL: Redis High Availability**

**Development uses a single Redis container, which is a Single Point of Failure (SPOF) in production.**

### Recommended Solutions:

#### **Option A: Managed Service (Recommended ✅)**
Use cloud provider managed Redis with built-in HA:
- **AWS ElastiCache for Redis**
- **Google Cloud Memorystore**
- **Azure Cache for Redis**

**Setup:**
1. Create managed Redis cluster with replication enabled
2. Update `.env.production`:
   ```bash
   REDIS_URL=redis://prod-cluster.abc123.0001.use1.cache.amazonaws.com:6379/0
   ```

#### **Option B: Self-Managed Redis Sentinel**
Deploy 3-node Sentinel cluster (1 master + 2 replicas)

**Setup:**
1. Update `.env.production`:
   ```bash
   REDIS_USE_SENTINEL=true
   REDIS_SENTINELS=sentinel1:26379,sentinel2:26379,sentinel3:26379
   REDIS_MASTER_NAME=mymaster
   REDIS_PASSWORD=your-secure-password
   ```
2. Deploy using `docker-compose.prod.yml` (includes Sentinel containers)

📖 **Full documentation:** [docs/REDIS_HIGH_AVAILABILITY.md](docs/REDIS_HIGH_AVAILABILITY.md)

---

## ⚙️ Setup

### 1. Configure Environment
```bash
# Copy example configuration
cp .env.production.example .env.production

# Edit with your values
nano .env.production

# ⚠️ REQUIRED: Set these variables
# - SECRET_KEY (min 50 characters)
# - ALLOWED_HOSTS
# - DB_PASSWORD
# - REDIS_URL (or Redis Sentinel config)
```

### 2. Build and Deploy
```bash
# Production deployment
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Check services
docker compose -f docker-compose.prod.yml ps
```

### 3. Run Migrations
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### 4. Create Superuser
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### 5. Collect Static Files
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

---

## 🌐 Health Checks

| Endpoint | Description | Expected Response |
|-----------|------------|-------------------|
| `/health/` | Complete status | `200 OK` + JSON |
| `/health/ready/` | Ready for traffic | `200 OK` |
| `/health/live/` | Process alive | `200 OK` |
| `/metrics/` | Prometheus metrics | `200 OK` + plaintext |

### Health Check Example
```bash
# Check all services
curl http://localhost:8000/health/

# Expected response
{
  "status": "healthy",
  "database": "ok",
  "redis": "ok",
  "celery": "ok"
}
```

---

## 🧱 Backup & Recovery

### Database Backup
```bash
# Create backup
docker compose -f docker-compose.prod.yml exec db sh -c \
  'mysqldump -u root -p$MYSQL_ROOT_PASSWORD mapspro_db > /backups/db_$(date +%Y%m%d_%H%M%S).sql'

# Restore backup
docker compose -f docker-compose.prod.yml exec -T db sh -c \
  'mysql -u root -p$MYSQL_ROOT_PASSWORD mapspro_db < /backups/db_20250127_120000.sql'
```

### Redis Backup (if using RDB persistence)
```bash
# Trigger save
docker compose -f docker-compose.prod.yml exec redis redis-cli BGSAVE

# Copy RDB file
docker cp redis:/data/dump.rdb ./backups/redis_$(date +%Y%m%d_%H%M%S).rdb
```

---

## 🔄 Rollback

### Roll back to previous version
```bash
# 1. Checkout previous release
git checkout <previous-tag>

# 2. Rebuild and deploy
docker compose -f docker-compose.prod.yml up -d --build

# 3. Run migrations (if needed - careful with reversals!)
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# 4. Verify health
curl http://localhost:8000/health/
```

### Emergency rollback (database included)
```bash
# 1. Stop services
docker compose -f docker-compose.prod.yml down

# 2. Restore database backup
docker compose -f docker-compose.prod.yml up -d db
docker compose -f docker-compose.prod.yml exec -T db sh -c \
  'mysql -u root -p$MYSQL_ROOT_PASSWORD mapspro_db < /backups/db_backup_before_deploy.sql'

# 3. Checkout previous code
git checkout <previous-tag>

# 4. Rebuild and start
docker compose -f docker-compose.prod.yml up -d --build
```

---

## � Monitoring

### Container Logs
```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f web

# Last 100 lines
docker compose -f docker-compose.prod.yml logs --tail=100 celery
```

### Prometheus Metrics
```bash
# Scrape metrics
curl http://localhost:8000/metrics/

# Key metrics to monitor:
# - django_http_requests_latency_seconds (response time)
# - django_db_query_duration_seconds (database performance)
# - celery_task_total (task throughput)
# - redis_connected_clients (connection pool usage)
```

---

## 🚨 Troubleshooting

### Service won't start
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs <service-name>

# Check container status
docker compose -f docker-compose.prod.yml ps

# Inspect container
docker inspect <container-id>
```

### Database connection issues
```bash
# Test database connection
docker compose -f docker-compose.prod.yml exec web python manage.py dbshell

# Check database is running
docker compose -f docker-compose.prod.yml exec db mysql -u root -p -e "SHOW DATABASES;"
```

### Redis connection issues
```bash
# Test Redis connection
docker compose -f docker-compose.prod.yml exec redis redis-cli PING

# Check Redis info
docker compose -f docker-compose.prod.yml exec redis redis-cli INFO
```

### Celery tasks not running
```bash
# Check Celery worker logs
docker compose -f docker-compose.prod.yml logs celery

# Inspect Celery worker status
docker compose -f docker-compose.prod.yml exec celery celery -A core inspect active

# Check beat scheduler
docker compose -f docker-compose.prod.yml logs beat
```

---

## 📋 Pre-Deployment Checklist

- [ ] ✅ SECRET_KEY is set and different from development
- [ ] ✅ DEBUG=false in production settings
- [ ] ✅ ALLOWED_HOSTS configured correctly
- [ ] ✅ Redis HA solution deployed (ElastiCache/Sentinel)
- [ ] ✅ Database backups automated
- [ ] ✅ SSL/HTTPS configured (SECURE_SSL_REDIRECT=true)
- [ ] ✅ CSRF_TRUSTED_ORIGINS includes production domain
- [ ] ✅ Email SMTP configured
- [ ] ✅ Sentry/error tracking configured (optional)
- [ ] ✅ Health checks accessible
- [ ] ✅ Prometheus metrics endpoint enabled
- [ ] ✅ Static files collected (`collectstatic`)
- [ ] ✅ Migrations applied
- [ ] ✅ Superuser created

---

## 📚 Additional Resources

- [Redis High Availability Strategy](docs/REDIS_HIGH_AVAILABILITY.md)
- [Performance Optimization Phases](docs/performance_phase6.md)
- [Security Best Practices](SECURITY.md)
- [Operations Checklist](docs/operations_checklist.md)

---

## 🧰 Troubleshooting

| Problema | Solução |
|-----------|----------|
| DB não sobe | Verifique volume ou `.env` |
| Celery parado | `docker compose restart celery beat` |
| Health 503 | Verifique Redis/DB |
| Static 404 | `python manage.py collectstatic --noinput` |

---

**MapsProveFiber — 2025**
