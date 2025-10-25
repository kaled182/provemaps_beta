# AGENTS.md — Development Guide for MapsProveFiber

## Commands
- **Run server:** `python manage.py runserver 0.0.0.0:8000` or `make run`
- **Run tests:** `pytest -q` (all), `pytest -v tests/test_specific.py::TestClass::test_method` (single test)
- **Lint/format:** `make lint` (check), `make fmt` (fix with ruff/black/isort)
- **Coverage:** `pytest --cov --cov-report=html` or `make test-coverage`
- **Migrate:** `python manage.py migrate` or `make migrate`
- **Celery worker:** `celery -A core worker -l info`, **beat:** `celery -A core beat -l info`
- **Pre-commit:** `pre-commit run --all-files` (auto-runs black, ruff, isort, shellcheck, hadolint)
- **Frontend tests:** `npm test` (Jest for JS in maps_view/static/js)

## Architecture
- **Django 5.x** multi-app project: `core` (settings/root URLs), `maps_view` (network dashboard), `routes_builder` (fiber routes/KML), `setup_app` (config UI), `zabbix_api` (Zabbix integration, REST APIs, use cases)
- **Database:** MariaDB/MySQL (`mapspro_db`), models in `zabbix_api/models.py` (active), `maps_view/models_old.py` (legacy)
- **Async:** Celery (Redis broker), Django Channels (WebSocket `/ws/dashboard/status/`)
- **Observability:** Prometheus metrics (`/metrics/`), structured logs (`logs/application.log`), slow query tracking
- **Config:** Split settings (`settings/dev.py`, `settings/prod.py`, `settings/test.py`), `django-environ` for secrets

## Code Style
- **Formatting:** Black (line-length=100), isort (profile=black), Ruff (Django-aware linting)
- **Imports:** isort order → stdlib, third-party, first-party (`core`, `maps_view`, `setup_app`, `routes_builder`), `from django...` before `from core...`
- **Typing:** Encouraged but not enforced (mypy configured), exclude migrations/tests
- **Naming:** `snake_case` (functions/vars), `PascalCase` (classes), descriptive names (no abbreviations unless domain-specific like `OLT`, `OTDR`)
- **Error handling:** Raise Django exceptions (`Http404`, `PermissionDenied`), log errors with context, avoid bare `except:`
- **Templates/static:** Per-app organization (`maps_view/templates/`, `routes_builder/static/`), use `{% load static %}`, partials in `maps_view/templates/partials/`
- **Legacy files:** `*_old.py` files exist; prefer main files (`models.py`, `views.py`) unless maintaining legacy code
- **Security:** Never log/commit secrets, use `setup_app` for credential storage (encrypted with Fernet), validate all inputs, follow OWASP guidelines (see SECURITY.md)
