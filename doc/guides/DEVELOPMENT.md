# Development Guide - MapsProveFiber

**Version**: v2.0.0  
**Last Updated**: 2025-11-10  
**Target Audience**: Developers

---

## 📖 Overview

This guide covers daily development workflows for MapsProveFiber, including local setup, common commands, debugging techniques, and best practices.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git
- Docker & Docker Compose (optional)
- Code editor (VS Code recommended)

### Initial Setup

```powershell
# Clone repository
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta

# Create virtual environment
python -m venv venv
venv\Scripts\Activate.ps1

# Install dependencies
cd backend
pip install -r requirements.txt

# Setup database
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Access at http://localhost:8000

---

## 💻 Daily Commands

### Development Server

```powershell
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

```powershell
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
```

### Static Files

```powershell
# Collect static files
python manage.py collectstatic --noinput

# Find static files
python manage.py findstatic <filename>
```

### Testing

```powershell
# Run all tests
pytest -q

# Run specific test file
pytest backend/tests/test_smoke.py -v

# Run with coverage
pytest --cov --cov-report=html

# Run specific test
pytest backend/inventory/tests/test_models.py::TestSiteModel::test_site_creation -v

# Run in parallel (faster)
pytest -n auto
```

### Code Quality

```powershell
# Format code (uses ruff + black + isort)
make fmt

# Lint code
make lint

# Type checking
make type-check

# Run all quality checks
make quality
```

---

## 🔧 Docker Development

### Start Services

```powershell
# Start all services
docker compose up -d

# Start specific service
docker compose up -d redis

# View logs
docker compose logs -f web

# Restart service
docker compose restart web
```

### Redis Operations

```powershell
# Check Redis status
docker compose ps redis

# Start Redis
docker compose up -d redis

# Connect to Redis CLI
docker compose exec redis redis-cli

# View all keys
docker compose exec redis redis-cli KEYS "*"

# Flush database
docker compose exec redis redis-cli FLUSHDB

# Get key value
docker compose exec redis redis-cli GET "key_name"
```

### Database Operations

```powershell
# Connect to MariaDB
docker compose exec db mysql -u app -p

# Create database backup
docker compose exec db mysqldump -u app -papp mapsprovefiber > backup.sql

# Restore database
docker compose exec -T db mysql -u app -papp mapsprovefiber < backup.sql
```

### Container Management

```powershell
# Execute command in container
docker compose exec web python manage.py shell

# View container stats
docker compose stats

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# Rebuild containers
docker compose up --build
```

---

## 🐛 Debugging

### Django Debug Toolbar

Add to `settings/dev.py`:

```python
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']
```

Install:
```powershell
pip install django-debug-toolbar
```

### Logging

View logs:
```powershell
# Application logs
tail -f backend/logs/django.log

# Celery logs
tail -f backend/logs/celery.log

# Docker logs
docker compose logs -f web
```

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
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

#### Database Locked (SQLite)
```powershell
# Close all connections and restart
rm database/db.sqlite3
python manage.py migrate
```

#### Redis Connection Error
```powershell
# Check if Redis is running
docker compose ps redis

# Start Redis
docker compose up -d redis

# Test connection
docker compose exec redis redis-cli PING
```

---

## 📁 Project Structure

```
provemaps_beta/
├── backend/                    # Django backend
│   ├── core/                   # Settings, URLs, ASGI/WSGI
│   ├── inventory/              # Inventory models & API
│   ├── monitoring/             # Health checks & monitoring
│   ├── maps_view/              # Dashboard views
│   ├── integrations/zabbix/    # Zabbix integration
│   ├── setup_app/              # Runtime configuration
│   ├── settings/               # Environment-specific settings
│   ├── templates/              # Django templates
│   └── tests/                  # Global tests
├── frontend/                   # Frontend assets
│   ├── src/                    # Vue 3 source (future)
│   └── static/                 # Static files
├── database/                   # Database files
│   └── db.sqlite3
├── docker/                     # Docker configuration
│   ├── dockerfile
│   └── docker-compose.yml
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

```powershell
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
# tests/test_models.py
def test_site_creation():
    site = Site.objects.create(name="HQ", latitude=-23.5505, longitude=-46.6333)
    assert site.name == "HQ"
    assert site.is_active is True
```

```python
# inventory/models.py
class Site(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    is_active = models.BooleanField(default=True)
```

---

## 📊 Health Checks

### Endpoints

```powershell
# Liveness check
Invoke-WebRequest http://localhost:8000/live

# Readiness check
Invoke-WebRequest http://localhost:8000/ready

# Full health check
Invoke-WebRequest http://localhost:8000/healthz

# Metrics
Invoke-WebRequest http://localhost:8000/metrics/metrics
```

### System Check

```powershell
# Run Django system check
python manage.py check

# Run with deployment settings
python manage.py check --deploy

# Run specific check
python manage.py check --tag models
```

---

## 🎨 Frontend Development

### Static Files

```powershell
# Collect static files
python manage.py collectstatic --noinput

# Find static file location
python manage.py findstatic js/dashboard.js

# Clear collected static files
rm -r backend/staticfiles/*
```

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

# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mapsprovefiber
DB_USER=app
DB_PASSWORD=app

# Redis (optional)
REDIS_URL=redis://localhost:6379/1

# Zabbix
ZABBIX_API_URL=http://zabbix.example.com/api_jsonrpc.php
ZABBIX_API_USER=your-user
ZABBIX_API_PASSWORD=your-password

# Google Maps
GOOGLE_MAPS_API_KEY=your-api-key
```

### Load Environment

```powershell
# Copy example
cp .env.example .env

# Edit with your values
notepad .env
```

---

## 🚨 Troubleshooting

### Import Errors

```powershell
# Ensure PYTHONPATH includes backend/
$env:PYTHONPATH = "d:\provemaps_beta\backend"
```

### Migration Conflicts

```powershell
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

```powershell
# Clear Django cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# Clear Redis cache
docker compose exec redis redis-cli FLUSHDB
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

- Check [Troubleshooting](../getting-started/TROUBLESHOOTING.md)
- Review [Common Issues](../operations/TROUBLESHOOTING.md)
- Ask in team chat or open an issue

---

**Last Updated**: 2025-11-10  
**Maintainers**: Development Team
