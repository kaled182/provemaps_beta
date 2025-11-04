# Quick Commands - MapsProveFiber Dev

## Daily Startup

```powershell
# 1. Change into the project folder
cd D:\provemaps_beta

# 2. Start Redis (if stopped)
docker compose up -d redis

# 3. Start Django
python manage.py runserver 0.0.0.0:8000

# 4. Open the browser
start http://localhost:8000
```

---

## Redis

```powershell
# Status
docker compose ps redis

# Start
docker compose up -d redis

# Stop
docker compose stop redis

# Logs
docker compose logs redis --tail 50

# Interactive CLI
docker compose exec redis redis-cli

# List keys
docker compose exec redis redis-cli KEYS "*"

# Clear cache
docker compose exec redis redis-cli FLUSHDB
```

---

## Django

```powershell
# Development server
python manage.py runserver 0.0.0.0:8000

# Migrations
python manage.py makemigrations
python manage.py migrate

# Interactive shell
python manage.py shell

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Show routes
python manage.py show_urls
```

---

## Quick Checks

```powershell
# Redis online?
python -c "import redis; print('OK' if redis.Redis().ping() else 'Offline')"

# Django responding?
Invoke-WebRequest http://localhost:8000/healthz

# Cache working?
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'ok'); print('Cache OK' if cache.get('test') == 'ok' else 'Cache failed')"

# Check versions
python --version
docker --version
python -c "import django; print('Django:', django.get_version())"
```

---

## Tests

```powershell
# Full test suite
python -m pytest tests/ -v

# Specific test
python -m pytest tests/test_smoke.py -v

# With coverage
python -m pytest --cov --cov-report=html
```

---

## Database

```powershell
# Database shell
python manage.py dbshell

# Dump database
python manage.py dumpdata > backup.json

# Load dump
python manage.py loaddata backup.json

# Reset database (danger!)
Remove-Item db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

---

## Docker

```powershell
# List running containers
docker compose ps

# List all containers (including stopped)
docker compose ps --all

# Stop all running containers
docker compose stop

# Remove stopped containers
docker container prune -f

# List images
docker images

# Remove unused data (danger!)
docker system prune -a
```

---

## Monitoring

```powershell
# Prometheus metrics
Invoke-WebRequest http://localhost:8000/metrics/metrics

# Health checks
Invoke-WebRequest http://localhost:8000/healthz        # Full check
Invoke-WebRequest http://localhost:8000/ready          # Readiness
Invoke-WebRequest http://localhost:8000/live           # Liveness

# Redis stats
docker compose exec redis redis-cli INFO stats
docker compose exec redis redis-cli INFO memory
docker compose exec redis redis-cli DBSIZE
```

---

## Maintenance

```powershell
# Clear Python cache
Remove-Item -Recurse -Force __pycache__
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force

# Clear logs
Remove-Item logs\*.log

# Upgrade dependencies
pip install -r requirements.txt --upgrade

# Check outdated packages
pip list --outdated
```

---

## Emergency

```powershell
# Stop Django (CTRL+C or use PowerShell)
Get-Process python | Stop-Process -Force

# Stop Redis
docker compose stop redis

# Restart everything
docker compose restart redis
python manage.py runserver 0.0.0.0:8000

# Port 8000 busy? Inspect usage
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <number> /F
```

---

## Logs

```powershell
# Django logs (check the running terminal)

# Redis logs
docker compose logs redis --tail 100

# Filter Django logs
Get-Content logs\application.log | Select-String "ERROR"
Get-Content logs\application.log | Select-String "cache"
Get-Content logs\application.log | Select-String "zabbix"
```

---

## Debug

```powershell
# Interactive Django shell
python manage.py shell

# Inside the shell:
from django.core.cache import cache
from zabbix_api.services.zabbix_service import *
from django.contrib.auth.models import User

# Show settings diff
python manage.py diffsettings

# Show generated SQL
python manage.py sqlmigrate zabbix_api 0009
```

---

## Important URLs

- **Dashboard:** http://localhost:8000/maps_view/dashboard/
- **Admin:** http://localhost:8000/admin/
- **Docs:** http://localhost:8000/setup_app/docs/
- **Zabbix Lookup:** http://localhost:8000/zabbix/lookup/
- **Route Builder:** http://localhost:8000/routes_builder/fiber-route-builder/
- **Metrics:** http://localhost:8000/metrics/metrics
- **Health:** http://localhost:8000/healthz

---

## Tips

### Useful aliases (add to $PROFILE)
```powershell
function Start-MapsProDev {
    cd D:\provemaps_beta
    docker compose up -d redis
    python manage.py runserver 0.0.0.0:8000
}

function Test-MapsProHealth {
    python -c "import redis; print('Redis:', 'OK' if redis.Redis().ping() else 'Offline')"
    Invoke-WebRequest http://localhost:8000/healthz -UseBasicParsing | Select-Object StatusCode
}
```

### Environment variables
```powershell
# Show current .env
Get-Content .env

# Set temporarily (current session)
$env:DEBUG = "True"
$env:REDIS_URL = "redis://localhost:6379/0"
```

### Performance
```powershell
# Measure request time
Measure-Command { Invoke-WebRequest http://localhost:8000/zabbix_api/api/sites/ }

# Show active connections
netstat -ano | findstr :8000
netstat -ano | findstr :6379
```

---

Keep this file handy for quick reference.
