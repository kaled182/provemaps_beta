# Development Guide - MapsProveFiber

**Versão do produto**: ver [VERSION](../../VERSION)  
**Last Updated**: 2026-10-04  
**Target Audience**: Developers

---

## 📖 Overview

This guide covers daily development workflows for MapsProveFiber, including local setup, common commands, debugging techniques, and best practices.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Git
- Docker & Docker Compose (the easiest way to get PostgreSQL 16 + PostGIS and Redis)
- GDAL/GEOS system libraries when running Django outside Docker (see [GIS setup](../developer/gis-setup.md)); PostgreSQL + PostGIS is the only supported database
- Node.js 20+ for the frontend (Vue 3 + Vite)
- Code editor (VS Code recommended)

### Initial Setup

```bash
# Clone repository
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta

# Start PostGIS + Redis (host ports 5433 and 6380)
docker compose -f docker/docker-compose.yml up -d postgres redis
cp .env.example .env   # then set DB_ENGINE=postgis, DB_HOST=127.0.0.1, DB_PORT=5433 (see Environment Variables)

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies (runtime + tests/lint; `make requirements-dev` from the repo root does the same)
cd backend
pip install -r requirements-dev.txt

# Setup database
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Access at http://localhost:8000 (the full Docker stack, `make up`, serves on http://localhost:8100).

---

## 💻 Daily Commands

### Development Server

```bash
# Start development server
python manage.py runserver

# Start with specific host/port
python manage.py runserver 0.0.0.0:8000

# Start Django shell
python manage.py shell

# Start Django shell with ipython
python manage.py shell -i ipython
```

### Database Operations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration status
python manage.py showmigrations

# Rollback migration
python manage.py migrate <app_name> <migration_number>

# Create database dump
python manage.py dumpdata > data/backup.json

# Load database dump
python manage.py loaddata data/backup.json

# (Docker) Postgres dump/restore: see "Docker Development > Database Operations"
```

### Static Files

```bash
# Collect static files
python manage.py collectstatic --noinput

# Find static files
python manage.py findstatic <filename>
```

### Testing

```bash
# Run all tests (from the repo root; settings.test is SQLite by default,
# set TEST_DB_ENGINE=postgis plus DB_* to run on PostGIS like the CI does)
pytest -q

# Run specific test file
pytest -q backend/tests/test_smoke.py

# Run with coverage
pytest --cov --cov-report=html

# Run specific test
pytest -q backend/inventory/tests/test_fibers_api.py -k "some_name"

# Frontend unit tests (Vitest)
cd frontend && npm ci && npm run test:unit
```

Spatial tests need GDAL/GEOS and PostGIS; without them some files fail at collection (not a code regression).

### Code Quality

```bash
# Lint code (ruff + black --check + isort --check)
make lint

# Format code (ruff --fix + black + isort; touches the whole tree, avoid when others are editing)
make fmt
```

---

## 🔧 Docker Development

### Start Services

```bash
# Start all services (make up) -- compose file: docker/docker-compose.yml
docker compose -f docker/docker-compose.yml up -d

# Start specific service
docker compose -f docker/docker-compose.yml up -d redis

# View logs (make logs)
docker compose -f docker/docker-compose.yml logs -f web

# Restart service
docker compose -f docker/docker-compose.yml restart web
```

### Redis Operations

```bash
# Check Redis status
docker compose -f docker/docker-compose.yml ps redis

# Start Redis
docker compose -f docker/docker-compose.yml up -d redis

# Connect to Redis CLI
docker compose -f docker/docker-compose.yml exec redis redis-cli

# View all keys
docker compose -f docker/docker-compose.yml exec redis redis-cli KEYS "*"

# Flush database
docker compose -f docker/docker-compose.yml exec redis redis-cli FLUSHDB

# Get key value
docker compose -f docker/docker-compose.yml exec redis redis-cli GET "key_name"
```

### Database Operations

```bash
# Connect to PostgreSQL (service `postgres`, database `app`)
docker compose -f docker/docker-compose.yml exec postgres psql -U app -d app

# Create database backup
docker compose -f docker/docker-compose.yml exec postgres pg_dump -U app app > backup.sql

# Restore database
docker compose -f docker/docker-compose.yml exec -T postgres psql -U app -d app < backup.sql
```

### Container Management

```bash
# Execute command in container
docker compose -f docker/docker-compose.yml exec web python manage.py shell

# View container stats
docker stats

# Stop all services (make down)
docker compose -f docker/docker-compose.yml down

# Stop and remove volumes
docker compose -f docker/docker-compose.yml down -v

# Rebuild containers (make build)
docker compose -f docker/docker-compose.yml up --build
```

---

## 🐛 Debugging

### Django Debug Toolbar

`settings/dev.py` already enables the toolbar automatically when the package is installed (it is pinned in `backend/requirements-dev.txt`, so `make requirements-dev` installs it). Set `ENABLE_DEBUG_TOOLBAR=False` to turn it off (the Docker compose file does).

### Logging

View logs:
```bash
# Application logs go to the console (the terminal running `make run`)

# Docker logs
docker compose -f docker/docker-compose.yml logs -f web
docker compose -f docker/docker-compose.yml logs -f celery
```
An optional rotating log file is available in non-debug settings via `ENABLE_FILE_LOGGING=true` and `LOG_FILE`.

### Interactive Debugging

Use `breakpoint()` in code:

```python
def my_view(request):
    breakpoint()  # Debugger will stop here
    return JsonResponse({"status": "ok"})
```

Or use `pdb`:

```python
import pdb; pdb.set_trace()
```

### Common Issues

#### Port Already in Use
```bash
# Find process using port 8000
ss -ltnp | grep :8000

# Kill process (replace PID)
kill <PID>
```

#### Database Connection Refused (PostgreSQL)
```bash
# Is the postgres container up and healthy?
docker compose -f docker/docker-compose.yml ps postgres

# Outside Docker the host port is 5433 (DB_PORT=5433, DB_HOST=127.0.0.1)
docker compose -f docker/docker-compose.yml exec postgres pg_isready -U app -d app
```

#### Redis Connection Error
```bash
# Check if Redis is running
docker compose -f docker/docker-compose.yml ps redis

# Start Redis
docker compose -f docker/docker-compose.yml up -d redis

# Test connection
docker compose -f docker/docker-compose.yml exec redis redis-cli PING
```

---

## 📁 Project Structure

```
provemaps_beta/
├── backend/                    # Django backend
│   ├── core/                   # URLs, ASGI/WSGI, middleware, 2FA auth, health
│   ├── inventory/              # Site/Device/Port/FiberCable models, usecases/, api/, viewsets.py
│   ├── monitoring/             # Zabbix-derived state (up/down, traffic)
│   ├── maps_view/              # Dashboard, SWR cache, WebSocket (realtime/)
│   ├── integrations/zabbix/    # Zabbix client + gateway (zabbix_service.zabbix_request)
│   ├── setup_app/              # Runtime configuration
│   ├── settings/               # base / dev / prod / test settings
│   ├── templates/              # Django templates
│   └── tests/                  # Global tests
├── frontend/                   # Vue 3 + Vite SPA
│   ├── src/                    # Vue source
│   └── tests/                  # Vitest (unit) + Playwright (e2e)
├── database/                   # Runtime data mounted into the containers
├── docker/                     # Docker configuration
│   ├── dockerfile
│   └── docker-compose.yml      # dev stack (prod: docker-compose.prod.yml)
├── doc/                        # Documentation
└── scripts/                    # Utility scripts
```

---

## 🔄 Git Workflow

### Branch Strategy

- `inicial` - Main production branch
- `refactor/*` - Refactoring work
- `feat/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

### Common Operations

```bash
# Create feature branch
git checkout -b feat/new-feature

# Check status
git status

# Stage changes
git add .

# Commit with message
git commit -m "feat: add new feature"

# Push to remote
git push origin feat/new-feature

# Update from main
git checkout inicial
git pull
git checkout feat/new-feature
git rebase inicial
```

---

## 🧪 Testing Workflow

### Test-Driven Development (TDD)

1. Write failing test
2. Implement minimal code to pass
3. Refactor while keeping tests green

Example:

```python
# backend/inventory/tests/test_site.py
def test_site_creation():
    site = Site.objects.create(display_name="HQ", latitude=-23.5505, longitude=-46.6333)
    assert site.name == "HQ"  # `name` is an alias of `display_name`
```

```python
# backend/inventory/models.py (simplified)
class Site(models.Model):
    display_name = models.CharField(max_length=160, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        db_table = "zabbix_api_site"  # inherited table name; the model lives in `inventory`
```

---

## 📊 Health Checks

### Endpoints

```bash
# Liveness check (make live)
curl -fsS http://localhost:8000/live

# Readiness check (make ready)
curl -fsS http://localhost:8000/ready

# Full health check (make health)
curl -fsS http://localhost:8000/healthz

# Metrics
curl http://localhost:8000/metrics/metrics
```
(Use port 8100 against the Docker dev stack.)

### System Check

```bash
# Run Django system check
python manage.py check

# Run with deployment settings
python manage.py check --deploy

# Run specific check
python manage.py check --tag models
```

---

## 🎨 Frontend Development

### Vue SPA (Vite)

```bash
cd frontend
npm ci                # install from package-lock.json
npm run dev           # Vite dev server (port 5173)
npm run build         # outputs to backend/staticfiles/vue-spa
npm run test:unit     # Vitest
npm run lint          # ESLint (currently fails; tracked as EV-0022)
```

E2E specs (Playwright) live in `frontend/tests/e2e` (`npm run test:e2e`).

### Static Files

```bash
# Collect static files
python manage.py collectstatic --noinput

# Find static file location
python manage.py findstatic js/dashboard.js
```

Do not wipe `backend/staticfiles/`: it also holds the SPA build (`vue-spa/`); rebuild it with `npm run build`.

### Cache Busting

Always append version to static files in templates:

```django
{% load static %}
<script src="{% static 'js/dashboard.js' %}?v={{ STATIC_ASSET_VERSION }}"></script>
```

The `STATIC_ASSET_VERSION` is automatically provided via context processor.

---

## 🔐 Environment Variables

### Required Variables

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
DJANGO_SETTINGS_MODULE=settings.dev
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL + PostGIS; DB_ENGINE=postgis is required)
DB_ENGINE=postgis
DB_HOST=localhost      # 127.0.0.1 when using the Compose postgres
DB_PORT=5433           # host port published by docker/docker-compose.yml (5432 inside Docker)
DB_NAME=app
DB_USER=app
DB_PASSWORD=app

# Redis (optional)
REDIS_URL=redis://localhost:6380/0   # host port published by Compose (6379 inside Docker)

# Zabbix
ZABBIX_API_URL=http://zabbix.example.com/api_jsonrpc.php
ZABBIX_API_USER=your-user
ZABBIX_API_PASSWORD=your-password

# Google Maps
GOOGLE_MAPS_API_KEY=your-api-key
```

### Load Environment

```bash
# Copy example
cp .env.example .env

# Edit with your values
${EDITOR:-nano} .env
```

---

## 🚨 Troubleshooting

### Import Errors

```bash
# Ensure PYTHONPATH includes backend/
export PYTHONPATH="$PWD/backend"
```

### Migration Conflicts

```bash
# Show migration plan
python manage.py showmigrations

# Fake migration (if already applied manually)
python manage.py migrate --fake <app_name> <migration_number>

# Reset migrations (DANGER - dev only)
python manage.py migrate <app_name> zero
rm backend/<app_name>/migrations/0*.py
python manage.py makemigrations
python manage.py migrate
```

### Cache Issues

```bash
# Clear Django cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# Clear Redis cache
docker compose -f docker/docker-compose.yml exec redis redis-cli FLUSHDB
```

---

## 📚 Additional Resources

- [Testing Guide](TESTING.md) - Comprehensive testing documentation
- [Docker Guide](DOCKER.md) - Docker development workflows
- [Observability Guide](OBSERVABILITY.md) - Monitoring and metrics
- [API Documentation](../api/ENDPOINTS.md) - REST API reference
- [Architecture Overview](../architecture/OVERVIEW.md) - System architecture

---

## 🤝 Getting Help

- Check the troubleshooting notes in [`doc/troubleshooting/`](../troubleshooting/)
- Ask in team chat or open an issue

---

**Last Updated**: 2026-10-04  
**Maintainers**: Development Team
