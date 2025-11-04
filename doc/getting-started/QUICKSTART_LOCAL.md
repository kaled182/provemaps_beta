# Local Development Quickstart

## Access Credentials
- **App:** http://localhost:8000
- **Admin:** http://localhost:8000/admin/
- **User:** `admin`
- **Password:** `admin123`

Note: When running in Docker the superuser is created automatically during the first deploy. For a local environment, run `python manage.py ensure_superuser` after the initial migration.

## Default Services
- **Database:** SQLite (`db.sqlite3`) - no MySQL or MariaDB required
- **Cache:** Redis is optional; health checks ignore cache outages in development

---

## Useful Commands

### Run the server
```powershell
# Start development server
python manage.py runserver

# Start on a specific port
python manage.py runserver 8080

# Expose to the local network
python manage.py runserver 0.0.0.0:8000
```

### Database tools
```powershell
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Ensure default admin user (admin/admin123)
python manage.py ensure_superuser

# Interactive superuser creation
python manage.py createsuperuser

# Open Django shell
python manage.py shell
```

### Static assets
```powershell
# Collect static files
python manage.py collectstatic --noinput
```

### Tests
```powershell
# Run entire suite
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_smoke.py -v

# With coverage report
python -m pytest --cov --cov-report=html
```

---

## Key Endpoints

### Application
- Dashboard: http://localhost:8000/maps_view/dashboard/
- Setup: http://localhost:8000/setup_app/
- Route Builder: http://localhost:8000/routes_builder/
- Admin: http://localhost:8000/admin/

### Health and metrics
- Full health: http://localhost:8000/healthz
- Readiness: http://localhost:8000/ready
- Liveness: http://localhost:8000/live
- Prometheus metrics: http://localhost:8000/metrics/metrics

### Documentation
- Docs index: http://localhost:8000/setup_app/docs/
- API docs: http://localhost:8000/setup_app/docs/reference-root/API_DOCUMENTATION.md/

---

## Quick Checks

### Health check (non strict)
```powershell
# PowerShell
Invoke-WebRequest http://localhost:8000/healthz | Select-Object StatusCode, Content

# Or use a browser

```

### Metrics
```powershell
Invoke-WebRequest http://localhost:8000/metrics/metrics
```

---

## Current .env Defaults

### Characteristics
- DEBUG set to True for verbose errors
- SQLite configured by default
- Relaxed health checks ignore Redis outages
- Cache-safe: application tolerates Redis being offline
- No external dependencies required

### Redis offline behavior
When Redis is unavailable in development:
- Application falls back gracefully and keeps running
- Debug logs mention the offline cache state
- No HTTP 500 responses are raised because of cache errors
- Overall performance is slower because calls hit Zabbix directly

### Adjusting settings
Update `.env` if you need different behavior:
```bash
DEBUG=True
HEALTHCHECK_STRICT=false
HEALTHCHECK_IGNORE_CACHE=true
ENABLE_DIAGNOSTIC_ENDPOINTS=false
```

---

## Troubleshooting

### Port already in use
```powershell
# Pick a different port
python manage.py runserver 8080
```

### Reset the database
```powershell
# Delete the SQLite file
Remove-Item db.sqlite3

# Recreate schema and user
python manage.py migrate
python manage.py createsuperuser
```

### Clear template cache
```powershell
# Restart the server (CTRL+C, then run again)
python manage.py runserver
```

### Redis offline (expected in development)
Symptom: log message `[DEBUG] Cache offline (Redis unavailable)`

Resolution: this is expected while developing. The app keeps working:
- Endpoints still return HTTP 200
- Performance is reduced without cache
- Optional: install Redis for faster responses
  ```powershell
  # Windows installer: https://github.com/microsoftarchive/redis/releases
  # Or, from the project directory, start the default Docker service
  docker compose up -d redis
  ```

See more details in `doc/reference/REDIS_GRACEFUL_DEGRADATION.md`.

---

## Next Steps

1. Explore the dashboard: http://localhost:8000/maps_view/dashboard/
2. Configure Zabbix credentials in `.env` (optional)
3. Exercise the health endpoints
4. Browse the documentation site: http://localhost:8000/setup_app/docs/

---

## Available Features Without Extra Configuration

- Django admin interface
- Visualization dashboard
- Health check endpoints
- Prometheus metrics
- Documentation site
- Route builder (ships without sample route data)

For complete features such as Zabbix and Google Maps layers, provide the required environment variables in `.env`.

---

## Notes

- For production, use `.env.prod.backup` as the baseline
- Current automated tests: 46 of 52 passing (88.5 percent)
- Development mode runs with limited observability tooling
- The default `SECRET_KEY` value is a placeholder; replace it for production deployments

---

Built with Django 5.2.7 and Python 3.13
- **Performance:** Development mode exposes limited observability
