# Docker Setup Guide - MapsProveFiber

This guide walks through the official Docker environment for MapsProveFiber, from preparation to ongoing maintenance.

---

## 1. Prerequisites
- Docker Engine 24+
- Docker Compose Plugin 2.20+
- Git (to clone the repository)
- Internet access to download base images

Confirm the versions:
```powershell
docker --version
docker compose version
```

---

## 2. Clone the repository
```powershell
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta
```

Key services defined in `docker-compose.yml`:
- **web** - Django with Gunicorn/Uvicorn (port 8000)
- **celery** - Asynchronous task worker
- **beat** - Celery scheduler (periodic tasks)
- **redis** - Broker and cache
- **db** - MariaDB with a persistent volume

---

## 3. Configure environment variables
Create the `.env` file from the template and adjust the minimum values:
```powershell
Copy-Item .env.example .env

# Edit with your preferred editor
notepad .env
```

Recommended values for the default Docker stack:
```env
DJANGO_SETTINGS_MODULE=settings.dev
DB_HOST=db
DB_USER=app
DB_PASSWORD=app
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
```powershell
docker compose up --build
```

`docker-entrypoint.sh` automatically:
1. Waits for Redis and MariaDB
2. Applies Django migrations
3. Collects static files (`collectstatic`)
4. Starts Gunicorn/Uvicorn

After the stack is up:
- Application: http://localhost:8000/
- Admin: http://localhost:8000/admin/
- General health check: http://localhost:8000/healthz

---

## 5. Post-deploy tasks
- Create a superuser (if missing):
	```powershell
	docker compose exec web python manage.py ensure_superuser
	```
- Seed initial data (optional): run load scripts or fixtures via `docker compose exec web`.
- Validate Celery workers at `/celery/status`.

---

## 6. Essential commands
| Action | Command |
|------|---------|
| Check container status | `docker compose ps` |
| Tail logs | `docker compose logs -f web` |
| Shell Django | `docker compose exec web python manage.py shell` |
| Apply migrations | `docker compose exec web python manage.py migrate` |
| Update Python dependencies | `docker compose exec web pip install -r requirements.txt` |
| Restart only the Celery worker | `docker compose restart celery` |

---

## 7. Troubleshooting
- **Container will not start:** review `.env`, occupied ports (`netstat -ano | findstr 8000`), and volume permissions.
- **Database errors:** inspect `docker compose logs db` and the `DB_*` credentials.
- **Redis unavailable:** inspect `docker compose logs redis`; on Windows hosts read [`doc/reference/SETUP_REDIS_WINDOWS.md`](../reference/SETUP_REDIS_WINDOWS.md).
- **Missing assets:** run `docker compose exec web python manage.py collectstatic --noinput`.
- **Reset the stack:**
	```powershell
	docker compose down -v  # remove containers e volumes
	docker compose up --build
	```

---

## 8. Next steps
- Adjust production settings using [`doc/operations/DEPLOYMENT.md`](../operations/DEPLOYMENT.md).
- Set up observability and alerts: [`doc/reference/prometheus_static_version.md`](../reference/prometheus_static_version.md) and [`doc/reference/PROMETHEUS_ALERTS.md`](../reference/PROMETHEUS_ALERTS.md).
- Review the Redis HA strategy before going live: [`doc/reference/REDIS_HIGH_AVAILABILITY.md`](../reference/REDIS_HIGH_AVAILABILITY.md).
