# Docker Setup Guide - MapsProveFiber

This guide walks through the official Docker environment for MapsProveFiber, from preparation to ongoing maintenance.

---

## 1. Prerequisites
- Docker Engine 24+
- Docker Compose Plugin 2.20+
- Git (to clone the repository)
- Internet access to download base images

Confirm the versions:
```bash
docker --version
docker compose version
```

---

## 2. Clone the repository
```bash
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta
```

Key services defined in `docker/docker-compose.yml` (all `docker compose` commands below use `-f docker/docker-compose.yml`, or the `make` shortcuts):
- **web** - Django with Gunicorn/Uvicorn (container port 8000, published on host port **8100**)
- **celery** - Asynchronous task worker
- **beat** - Celery scheduler (periodic tasks)
- **redis** - Broker and cache
- **postgres** - PostgreSQL 16 + PostGIS (`postgis/postgis:16-3.4`) with a persistent volume (host port 5433)
- Observability and video extras: `prometheus`, `grafana`, `video-hls`, `video-transmuxer`, `mediamtx`, `whatsapp-qr`

---

## 3. Configure environment variables
Create the `.env` file from the template and adjust the minimum values:
```bash
cp .env.example .env

# Edit with your preferred editor
${EDITOR:-nano} .env
```

Recommended values for the default Docker stack:
```env
DJANGO_SETTINGS_MODULE=settings.dev
# The compose file already sets DB_ENGINE=postgis, DB_HOST=postgres, DB_NAME/DB_USER/DB_PASSWORD=app
REDIS_URL=redis://redis:6379/1
# Dashboard refresh interval (seconds, default=60)
DASHBOARD_CACHE_REFRESH_INTERVAL=60
# Inventory sync interval (seconds, default=86400)
INVENTORY_SYNC_INTERVAL_SECONDS=86400
# Automatic rotation interval (seconds, default=3600)
SERVICE_ACCOUNT_ROTATION_INTERVAL_SECONDS=3600
# Webhook timeout configuration (seconds)
SERVICE_ACCOUNT_WEBHOOK_CONNECT_TIMEOUT=3
SERVICE_ACCOUNT_WEBHOOK_READ_TIMEOUT=5
```

With these values the periodic task `service_accounts.enforce_rotation_policies_task`
runs every hour and sends alerts through the webhooks configured on the
service accounts. Adjust the timeout values to match the destination endpoint SLA.

> Generate a Fernet key after the first `up` with `docker compose exec web python manage.py generate_fernet_key --write` and store it securely.

---

## 4. First run
```bash
make up                # docker compose -f docker/docker-compose.yml up -d
# or, building images first:
docker compose -f docker/docker-compose.yml up --build
```

`docker-entrypoint.sh` automatically:
1. Waits for Redis and PostgreSQL
2. Applies Django migrations
3. Collects static files (`collectstatic`)
4. Starts Gunicorn/Uvicorn

After the stack is up:
- Application: http://localhost:8100/
- Admin: http://localhost:8100/admin/
- General health check: http://localhost:8100/healthz

---

## 5. Post-deploy tasks
- Create a superuser (if missing):
	```bash
	docker compose -f docker/docker-compose.yml exec web python manage.py ensure_superuser
	```
- Seed initial data (optional): run load scripts or fixtures via `docker compose -f docker/docker-compose.yml exec web`.
- Validate Celery workers at `/celery/status`.

---

## 6. Essential commands
| Action | Command |
|------|---------|
| Check container status | `docker compose -f docker/docker-compose.yml ps` |
| Tail logs | `make logs` or `docker compose -f docker/docker-compose.yml logs -f web` |
| Shell Django | `docker compose -f docker/docker-compose.yml exec web python manage.py shell` |
| Apply migrations | `docker compose -f docker/docker-compose.yml exec web python manage.py migrate` |
| Update Python dependencies | `docker compose -f docker/docker-compose.yml exec web pip install -r requirements.txt` |
| Restart only the Celery worker | `docker compose -f docker/docker-compose.yml restart celery` |

---

## 7. Troubleshooting
- **Container will not start:** review `.env`, occupied ports (`ss -ltnp | grep 8100`), and volume permissions.
- **Database errors:** inspect `docker compose -f docker/docker-compose.yml logs postgres` and the `DB_*` credentials.
- **Redis unavailable:** inspect `docker compose -f docker/docker-compose.yml logs redis`; on Windows hosts read [`doc/reference/SETUP_REDIS_WINDOWS.md`](../reference/SETUP_REDIS_WINDOWS.md).
- **Missing assets:** run `docker compose -f docker/docker-compose.yml exec web python manage.py collectstatic --noinput`.
- **Reset the stack:**
	```bash
	docker compose -f docker/docker-compose.yml down -v  # remove containers and volumes
	docker compose -f docker/docker-compose.yml up --build
	```

---

## 8. Next steps
- Adjust production settings using [`DEPLOY.md`](../../DEPLOY.md) and [`docker/docker-compose.prod.yml`](../../docker/docker-compose.prod.yml).
- Set up observability and alerts: [`doc/operations/MONITORING.md`](../operations/MONITORING.md) and [`doc/reference/PROMETHEUS_ALERTS.md`](../reference/PROMETHEUS_ALERTS.md).
- Review the Redis HA strategy before going live: [`doc/reference/REDIS_HIGH_AVAILABILITY.md`](../operations/REDIS_HA.md).
