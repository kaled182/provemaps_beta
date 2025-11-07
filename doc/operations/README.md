# ⚙️ Operations Documentation

Production deployment, monitoring, and maintenance guides.

---

## 📚 Operations Documents

| Document | Description | Audience |
|----------|-------------|----------|
| **[DEPLOYMENT.md](DEPLOYMENT.md)** | **Production deployment guide** (unificado: setup, checklist, rollback) | DevOps, SRE |
| **[MIGRATION_PRODUCTION_GUIDE.md](MIGRATION_PRODUCTION_GUIDE.md)** | v2.0.0 migration specifics | DevOps, SRE |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Diagnostics and resolution | All |
| **[STATUS_SERVICOS.md](STATUS_SERVICOS.md)** | Service status and health | DevOps, SRE |

### Deprecated Documents
- ~~`DEPLOYMENT_CHECKLIST_v2.0.0.md`~~ → Consolidated into `DEPLOYMENT.md`

---

## 🚀 Quick Start

### Pre-Deployment Checklist

Before deploying to production:

- [ ] All tests passing (`pytest -q`)
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] Static files collected
- [ ] Health checks working
- [ ] Monitoring configured

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete checklist.

---

### Health Checks

```bash
# Full health check
curl http://localhost:8000/healthz/

# Readiness probe
curl http://localhost:8000/ready/

# Liveness probe
curl http://localhost:8000/live/

# Metrics
curl http://localhost:8000/metrics/
```

See [MONITORING.md](MONITORING.md) for monitoring setup.

---

## 🎯 Common Operations

### Deployment

```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart mapsprove-web
sudo systemctl restart mapsprove-celery
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed procedure.

---

### Database Migrations

```bash
# Check migration status
python manage.py showmigrations

# Run migrations
python manage.py migrate

# Rollback migration
python manage.py migrate <app_name> <migration_name>

# Create migration
python manage.py makemigrations
```

---

### Monitoring

```bash
# Check Celery workers
celery -A core inspect active

# Check Celery queues
celery -A core inspect stats

# View Prometheus metrics
curl http://localhost:8000/metrics/

# Check logs
tail -f logs/mapsprove.log
```

See [MONITORING.md](MONITORING.md) for monitoring best practices.

---

## 🔧 Troubleshooting

### Common Issues

| Problem | Solution | Guide |
|---------|----------|-------|
| Server won't start | Check logs, ports, database | [TROUBLESHOOTING.md](TROUBLESHOOTING.md#server-wont-start) |
| Migrations failing | Check database state, rollback | [TROUBLESHOOTING.md](TROUBLESHOOTING.md#migrations-failing) |
| Celery tasks not running | Check Redis, worker status | [TROUBLESHOOTING.md](TROUBLESHOOTING.md#celery-issues) |
| High memory usage | Check Celery, cache, queries | [TROUBLESHOOTING.md](TROUBLESHOOTING.md#performance) |
| Zabbix integration down | Check circuit breaker, API | [TROUBLESHOOTING.md](TROUBLESHOOTING.md#zabbix) |

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for complete guide.

---

## 📊 Monitoring Stack

### Components

| Component | Purpose | Endpoint |
|-----------|---------|----------|
| **Prometheus** | Metrics collection | `:9090/targets` |
| **Grafana** | Dashboards | `:3000/dashboards` |
| **AlertManager** | Alert routing | `:9093` |
| **Loki** | Log aggregation | `:3100` |

### Key Metrics

```promql
# Request rate
rate(django_http_requests_total[5m])

# Error rate
rate(django_http_responses_total{status=~"5.."}[5m])

# Response time (p95)
histogram_quantile(0.95, django_http_request_duration_seconds_bucket)

# Celery queue size
celery_queue_length

# Zabbix circuit breaker state
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

See [DEPLOYMENT.md](DEPLOYMENT.md#incident-response) for procedures.

---

## 🔄 Backup & Recovery

### Database Backups

```bash
# Create backup
python manage.py dumpdata > backup_$(date +%Y%m%d).json

# Restore backup
python manage.py loaddata backup_20250107.json

# PostgreSQL backup (if using)
pg_dump -U postgres mapsprove > backup.sql

# Restore PostgreSQL
psql -U postgres mapsprove < backup.sql
```

### Configuration Backups

```bash
# Backup .env
cp .env .env.backup

# Backup secrets
cp service_accounts/*.json backups/
```

---

## 📈 Performance Tuning

### Database Optimization

```bash
# Analyze queries
python manage.py debugsqlshell

# Check slow queries
tail -f logs/slow_queries.log

# Vacuum database (PostgreSQL)
python manage.py dbshell
VACUUM ANALYZE;
```

### Caching

```bash
# Check Redis status
redis-cli INFO stats

# Clear cache
python manage.py clear_cache

# Warm cache
python manage.py warm_cache
```

See [MONITORING.md](MONITORING.md#performance) for tuning guide.

---

## 🔐 Security Operations

### SSL/TLS

```bash
# Check certificate expiry
openssl x509 -in cert.pem -noout -dates

# Renew Let's Encrypt
certbot renew --nginx
```

### Access Control

```bash
# Create admin user
python manage.py createsuperuser

# Grant permissions
python manage.py shell
from django.contrib.auth.models import User, Permission
user = User.objects.get(username='john')
user.user_permissions.add(Permission.objects.get(codename='view_site'))
```

---

## 📖 Related Documentation

- **[Deployment Checklist](DEPLOYMENT.md)** — Pre-deployment steps
- **[Monitoring Guide](MONITORING.md)** — Prometheus, Grafana
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** — Common issues
- **[Architecture](../architecture/)** — System design

---

**Need urgent help?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or check runbooks.
