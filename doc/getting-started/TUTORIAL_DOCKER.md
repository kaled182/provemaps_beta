# Docker Deployment Guide - MapsProveFiber

This tutorial targets new Docker users who need to start the full **MapsProveFiber** stack quickly and safely.

---

## Container Stack Overview

The Docker Compose stack defines these services:

| Service | Purpose |
|---------|---------|
| **web** | Django with Gunicorn and Uvicorn (port 8000) |
| **celery** | Celery worker for async tasks |
| **beat** | Celery beat scheduler |
| **redis** | Cache and message broker |
| **db** | MariaDB database |

The `docker-entrypoint.sh` script handles:
- Waiting for MariaDB and Redis to become healthy
- Running database migrations
- Collecting static files
- Starting the web server

---

## 1. Environment Preparation

### Install Docker and Docker Compose
```bash
sudo apt install docker.io docker-compose-plugin
```

Check the installed versions:
```bash
docker --version
docker compose version
```

### Clone the repository
```bash
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta
```

### Configure the `.env` file
Copy the example file and adjust the baseline variables:
```bash
cp .env.example .env
nano .env
```

Minimal values:
```env
DB_HOST=db
DB_USER=app
DB_PASSWORD=app
REDIS_URL=redis://redis:6379/1
DJANGO_SETTINGS_MODULE=settings.dev
# Automatic service account token rotation interval (seconds)
SERVICE_ACCOUNT_ROTATION_INTERVAL_SECONDS=3600
# Optional webhook timeouts (seconds)
SERVICE_ACCOUNT_WEBHOOK_CONNECT_TIMEOUT=3
SERVICE_ACCOUNT_WEBHOOK_READ_TIMEOUT=5
```

These values enable automatic service account rotation. Adjust the interval per internal policy and configure the webhook to receive `service_account.rotation_warning` and `service_account.token_rotated` events.

---

## 2. Start the Full Stack

### Build and launch
```bash
docker compose up -d --build
```

This command:
- Builds the Django and Celery images
- Creates persistent volumes for MariaDB and Redis
- Starts every required container

Check container status:
```bash
docker compose ps
docker compose logs -f web
```

Open the app at **http://localhost:8000**.

---

## 3. Manual Bootstrapping (first run)

Note: the default superuser (`admin`/`admin123`) is created automatically when `INIT_ENSURE_SUPERUSER=true` is set in the compose file.

Run manual commands if needed:
```bash
# Apply migrations (already handled automatically)
docker compose exec web python manage.py migrate

# Create a custom superuser (optional)
docker compose exec web python manage.py createsuperuser

# Collect static assets (already handled automatically)
docker compose exec web python manage.py collectstatic --noinput
```

---

## 4. Automatic Deployment Script

Use the bundled deployment orchestrator `scripts/deploy.sh`:

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh --compose docker-compose.yml --settings settings.prod --health http://localhost:8000/healthz
```

The script performs:
1. `docker compose build --pull`
2. `docker compose up -d db redis`
3. Database migrations and static collection
4. Bring up `web`, `celery`, and `beat`
5. Check `/healthz`
6. Roll back automatically on failure

---

## 5. Common Commands

| Action | Command |
|------|----------|
| Follow service logs | `docker compose logs -f web` |
| Restart the web app | `docker compose restart web` |
| Stop every container | `docker compose down` |
| Remove volumes | `docker compose down -v` |
| Open Django shell | `docker compose exec web python manage.py shell` |

---

## 6. Development Mode (hot reload)

To reload local code automatically:

1. In `docker-compose.yml`, uncomment:
   ```yaml
   volumes:
     - .:/app
     - ./logs:/app/logs
   ```

2. Start the development container:
   ```bash
   docker compose up -d web
   ```

3. Code changes now propagate instantly.

---

## 7. Troubleshooting

| Symptom | Fix |
|----------|----------|
| Web service is down | Check `docker compose logs web` |
| Database errors | Run `docker compose exec web python manage.py migrate` |
| Health check failing | Double check `.env` variables |
| Redis unavailable | Restart with `docker compose restart redis` |

---

## 8. Updates and Rollbacks

To update the deployment:
```bash
git pull
docker compose build
docker compose up -d
```

If you need to revert:
```bash
docker compose down
git checkout <previous-commit>
docker compose up -d
```

---

## 9. Relevant Directory Structure

```
provemaps_beta/
|- core/                    # Django project core
|- routes_builder/          # Fiber Route Builder frontend
|- zabbix_api/              # Zabbix integration layer
|- setup_app/               # Initial setup via UI
|- docker-compose.yml       # Container stack definition
|- Dockerfile               # Base image recipe
|- docker-entrypoint.sh     # Docker entrypoint script
|- scripts/deploy.sh        # Automated deployment script
`- README.md                # Main project guide
```

---

## Conclusion

You can now bootstrap the entire environment with a single command, even if Docker is new to you.

Monitor logs and metrics here:
- Django admin logs: `/admin/logs/`
- Prometheus metrics: `/metrics/`
- Health check endpoint: `/healthz`

Project maintained by **Simples Internet**. For questions or contributions, review `CONTRIBUTING.md`.
