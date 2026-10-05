# ⚙️ Operations Documentation

Production deployment, monitoring, and maintenance guides.

**Versão do produto**: ver [VERSION](../../VERSION)  
**Last Updated**: 2026-10-04

---

## 📚 Operations Documents

The current deployment guide is [`DEPLOY.md`](../../DEPLOY.md) (repository root), together with
[`docker/docker-compose.prod.yml`](../../docker/docker-compose.prod.yml) and
[`scripts/deploy.sh`](../../scripts/deploy.sh).

| Document | Description | Audience |
|----------|-------------|----------|
| **[DEPLOY.md](../../DEPLOY.md)** | **Production deployment guide** (requirements, `.env.production`, profiles, SSL, backup, update, troubleshooting) | DevOps, SRE |
| **[DOCKER_PRODUCTION.md](DOCKER_PRODUCTION.md)** | Alternative install via `scripts/deploy-docker.sh` (nginx, Gunicorn/Uvicorn, PostgreSQL + PostGIS, Redis, Celery) | DevOps, SRE |
| **[MONITORING.md](MONITORING.md)** | Prometheus metrics, Celery/Zabbix alerts, Grafana panels | DevOps, SRE |
| **[REDIS_HA.md](REDIS_HA.md)** | Redis high availability (managed service or Sentinel) | DevOps, SRE |
| **[dashboards/](dashboards/)** | Grafana dashboard JSON (Celery tasks, inventory API) | DevOps, SRE |
| **[Troubleshooting notes](../troubleshooting/)** | Case-by-case diagnostics and fixes (there is no single `TROUBLESHOOTING.md`) | All |

Historical 2025 deployment and rollout material (Sprint 1, Phase 1/7/10, v2.0.0 migration, PostGIS setup) lives in
[`doc/archive/2025-historico/`](../archive/2025-historico/) (index in [`doc/archive/README.md`](../archive/README.md)); it does not describe the current system.

---

## 🚀 Quick Start

### Pre-Deployment Checklist

Before deploying to production:

- [ ] All tests passing (see [CLAUDE.md](../../CLAUDE.md) section 9)
- [ ] `.env.production` configured (template: `.env.production.example`)
- [ ] Database migrations reviewed
- [ ] Health checks working
- [ ] Monitoring profile enabled if required

See [DEPLOY.md](../../DEPLOY.md) for the complete procedure.

---

### Health Checks

```bash
# Full health check
curl http://localhost:8000/healthz

# Readiness probe
curl http://localhost:8000/ready

# Liveness probe
curl http://localhost:8000/live

# Prometheus metrics
curl http://localhost:8000/metrics/metrics

# Celery status (staff authentication required)
curl http://localhost:8000/celery/status
```

See [MONITORING.md](MONITORING.md) for monitoring setup.

---

## 🎯 Common Operations

### Deployment

```bash
# Pull latest code and redeploy (migrations run automatically before restart)
git pull
./scripts/deploy.sh
```

See [DEPLOY.md](../../DEPLOY.md) for the detailed procedure, profiles and SSL.

---

### Database Migrations

```bash
# Check migration status
docker compose -f docker/docker-compose.prod.yml exec web \
  python manage.py showmigrations

# Run migrations
docker compose -f docker/docker-compose.prod.yml exec web \
  python manage.py migrate

# Rollback migration
docker compose -f docker/docker-compose.prod.yml exec web \
  python manage.py migrate <app_name> <migration_name>
```

---

### Monitoring

```bash
# Check Celery workers
docker compose -f docker/docker-compose.prod.yml exec celery \
  celery -A core.celery_app inspect active

# Check Celery stats
docker compose -f docker/docker-compose.prod.yml exec celery \
  celery -A core.celery_app inspect stats

# View Prometheus metrics
curl http://localhost:8000/metrics/metrics

# Check logs
docker compose -f docker/docker-compose.prod.yml logs -f web
```

See [MONITORING.md](MONITORING.md) for monitoring best practices.

---

## 🔧 Troubleshooting

### Common Issues

| Problem | Solution | Guide |
|---------|----------|-------|
| Server won't start / health check fails | Check logs, `manage.py check --deploy`, ports, database | [DEPLOY.md](../../DEPLOY.md#troubleshooting) |
| Migrations pending | `showmigrations`, then `migrate` | [DEPLOY.md](../../DEPLOY.md#troubleshooting) |
| Redis authentication error | Match `REDIS_PASSWORD` and `REDIS_URL` | [DEPLOY.md](../../DEPLOY.md#troubleshooting) |
| Celery workers not responding | Check Redis, worker status | [MONITORING.md](MONITORING.md#-troubleshooting) |
| Zabbix integration down | Check circuit breaker, Zabbix API | [MONITORING.md](MONITORING.md#-troubleshooting) |
| Docker / Celery startup problems, port and fiber data issues | Case notes | [doc/troubleshooting/](../troubleshooting/) |

---

## 📊 Monitoring Stack

Prometheus and Grafana run only with the `monitoring` profile (see [DEPLOY.md](../../DEPLOY.md)).

### Components

| Component | Purpose | Endpoint |
|-----------|---------|----------|
| **Prometheus** | Metrics collection | `127.0.0.1:9090/targets` |
| **Grafana** | Dashboards | `127.0.0.1:3002` |

### Key Metrics

```promql
# Celery workers available
celery_worker_available

# Zabbix request rate by method and status
sum(rate(zabbix_requests_total[5m])) by (method, status)

# Zabbix circuit breaker state (0=closed, 1=open, 2=half_open)
zabbix_circuit_breaker_state
```

See [MONITORING.md](MONITORING.md) for dashboard setup.

---

## 🚨 Incident Response

### Severity Levels

| Level | Response Time | Escalation |
|-------|---------------|------------|
| **P0 (Critical)** | 15 min | Immediate |
| **P1 (High)** | 1 hour | After 2 hours |
| **P2 (Medium)** | 4 hours | After 8 hours |
| **P3 (Low)** | Next business day | N/A |

### Incident Workflow

1. **Acknowledge**: Confirm you're investigating
2. **Assess**: Check health, logs, metrics
3. **Mitigate**: Apply temporary fix if possible
4. **Resolve**: Fix root cause
5. **Document**: Update runbook, create postmortem

See [DEPLOY.md](../../DEPLOY.md#troubleshooting) for procedures.

---

## 🔄 Backup & Recovery

PostgreSQL 16 + PostGIS is the only database; see [DEPLOY.md](../../DEPLOY.md#backup).

### Database Backups

```bash
# Full backup (postgres + redis), keep last 7
./scripts/backup.sh

# PostgreSQL only
./scripts/backup.sh --no-redis

# Manual PostgreSQL dump
docker compose -f docker/docker-compose.prod.yml exec -T postgres \
  pg_dump -U mapsprovefiber mapsprovefiber > backup.sql

# Restore PostgreSQL
docker compose -f docker/docker-compose.prod.yml exec -T postgres \
  psql -U mapsprovefiber mapsprovefiber < backup.sql
```

### Configuration Backups

```bash
# Backup environment file
cp .env.production .env.production.backup
```

---

## 📈 Performance Tuning

### Database Optimization

```bash
# Vacuum and analyze (PostgreSQL)
docker compose -f docker/docker-compose.prod.yml exec postgres \
  psql -U mapsprovefiber mapsprovefiber -c "VACUUM ANALYZE;"
```

### Caching

```bash
# Check Redis status
docker compose -f docker/docker-compose.prod.yml exec redis \
  sh -c 'redis-cli -a "$REDIS_PASSWORD" INFO stats'
```

See [REDIS_HA.md](REDIS_HA.md) for Redis availability options.

---

## 🔐 Security Operations

### SSL/TLS

```bash
# Renew Let's Encrypt (manual)
docker compose -f docker/docker-compose.prod.yml exec certbot \
  certbot renew --webroot -w /var/www/certbot
docker compose -f docker/docker-compose.prod.yml exec nginx nginx -s reload
```

### Access Control

```bash
# Create admin user
docker compose -f docker/docker-compose.prod.yml exec web \
  python manage.py createsuperuser
```

---

## 📖 Related Documentation

- **[Deployment Guide](../../DEPLOY.md)** — Production deployment
- **[Monitoring Guide](MONITORING.md)** — Prometheus, Grafana
- **[Troubleshooting notes](../troubleshooting/)** — Case-by-case fixes
- **[Architecture](../architecture/)** — System design
- **[Historical archive](../archive/README.md)** — 2025 deployment reports (not current)

---

**Need urgent help?** See [DEPLOY.md](../../DEPLOY.md#troubleshooting) or [doc/troubleshooting/](../troubleshooting/).
