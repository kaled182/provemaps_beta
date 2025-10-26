# Copilot Instructions for django-maps-prove-master-fixed

## Project Overview
This is a multi-app Django project for network mapping, route building, and device management. The main apps are:
- `core`: Project settings and root URLs
- `maps_view`: Network maps, device visualization, custom management commands
- `routes_builder`: Route planning and visualization
- `inventory`: Local database models for Sites, Devices, Ports
- `setup_app`: Device setup and configuration
- `zabbix_api`: Integration layer with Zabbix monitoring API (client and legacy services)

## Architecture & Data Flow
- Each app follows Django conventions: models, views, urls, templates, migrations, static files.
- Cross-app communication is via Django's ORM and shared templates/static assets.
- External integration: Zabbix API (see `zabbix_api/client.py` for resilient client; legacy helpers in `zabbix_api/services/`).
- Custom management commands are in `maps_view/management/commands/`.
- **Development Environment:** The primary development workflow uses Docker Compose (`docker compose up`). See `docker-compose.yml` for service definitions.

## Developer Workflows
- **Run server (Docker Compose):** `docker compose up` or `make run` (primary development workflow)
- **Run server (local Django only):** `python manage.py runserver` or `make run-web-local`
- **Migrate DB:** `python manage.py migrate` or `make migrate`
- **Create superuser:** `python manage.py createsuperuser` or `make superuser`
- **Run tests:** `pytest -q` or `make test`
- **Lint & Format:** `make fmt` (runs ruff, black, isort)
- **Build Docker images:** `make build`
- **See all commands:** `make help`
- **Static files:** Use Django's staticfiles system; see `maps_view/static/`, `routes_builder/static/`, etc.
- **Debugging:** Use Django's built-in error pages; settings in `settings/base.py`, overrides in `settings/dev.py`.

## Project-Specific Patterns
- Core data models reside in `inventory/models.py` (Site, Device, Port) and `routes_builder/models.py` (FiberCable, FiberEvent).
- `zabbix_api/models.py` should be minimal or empty following recent refactoring (data fetched via API, not persisted).
- Business logic should ideally be placed in `services.py` files within each app (e.g., `maps_view/services.py`) rather than directly in views.
- Views and URLs are in each app's `views.py` and `urls.py` files
- Templates are organized per app; shared templates in `templates/` and partials in `maps_view/templates/partials/`.
- Static assets are per-app and global (`staticfiles/`).
- Management commands extend Django's CLI for custom DB or network operations.

## Integration Points
- Zabbix API: See `zabbix_api/client.py` for core resilient client implementation; legacy services in `zabbix_api/services/`.
- Media files (device icons, images) in `media/`.

## Examples
- To add a new network map, create a model in `maps_view/models.py`, a view in `maps_view/views.py`, and a template in `maps_view/templates/`.
- For a new route builder feature, update `routes_builder/models.py`, `routes_builder/views.py`, and corresponding templates/static files.

## Conventions
- Use standard Django file structure: `models.py`, `views.py`, `urls.py`
- Organize static and template files per app for maintainability
- Place custom management commands in the relevant app's `management/commands/` directory

---
For questions or unclear patterns, review the relevant app's main files or ask for clarification.
