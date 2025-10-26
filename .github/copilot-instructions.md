# Copilot Instructions for django-maps-prove-master-fixed

## Project Overview
This is a multi-app Django project for network mapping, route building, and device management. The main apps are:
- `core`: Project settings and root URLs
- `maps_view`: Network maps, device visualization, custom management commands
- `routes_builder`: Route planning and visualization
- `setup_app`: Device setup and configuration
- `zabbix_api`: Integration with Zabbix monitoring

## Architecture & Data Flow
- Each app follows Django conventions: models, views, urls, templates, migrations, static files.
- Cross-app communication is via Django's ORM and shared templates/static assets.
- External integration: Zabbix API (see `zabbix_api/services/`), Oracle JDK (for legacy or external Java services).
- Custom management commands are in `maps_view/management/commands/`.

## Developer Workflows
- **Run server:** `python manage.py runserver`
- **Migrate DB:** `python manage.py migrate`
- **Create superuser:** `python manage.py createsuperuser`
- **Run tests:** `python manage.py test` (tests in each app's `tests.py`)
- **Static files:** Use Django's staticfiles system; see `maps_view/static/`, `routes_builder/static/`, etc.
- **Debugging:** Use Django's built-in error pages; settings in `core/settings.py`.

## Project-Specific Patterns
- Models are in each app's `models.py` file (e.g., `inventory/models.py`, `zabbix_api/models.py`)
- Views and URLs are in each app's `views.py` and `urls.py` files
- Templates are organized per app; shared templates in `templates/` and partials in `maps_view/templates/partials/`.
- Static assets are per-app and global (`staticfiles/`).
- Management commands extend Django's CLI for custom DB or network operations.

## Integration Points
- Zabbix API: See `zabbix_api/services/` for monitoring integration.
- Oracle JDK: Used for external Java services; see `oracleJdk-25/`.
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
