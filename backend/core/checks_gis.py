"""Custom system checks for validating GIS prerequisites."""

from __future__ import annotations

import logging
from typing import Any, List

from django.conf import settings
from django.core import checks
from django.db import DEFAULT_DB_ALIAS, connections

logger = logging.getLogger(__name__)


@checks.register(checks.Tags.database, "gis")
def gis_environment_check(
    app_configs: Any = None,  # pragma: no cover - signature required by Django
    **kwargs: Any,
) -> List[checks.CheckMessage]:
    """Ensure GDAL/GEOS and PostGIS are available when GIS mode is enabled."""
    messages: List[checks.CheckMessage] = []

    spatial_enabled = getattr(settings, "SPATIAL_SUPPORT_ENABLED", False)
    if not spatial_enabled:
        messages.append(
            checks.Critical(
                "GDAL/GEOS bindings are missing; spatial features are disabled.",
                hint=(
                    "Install GDAL/GEOS native libraries and the matching Python wheel "
                    "(GDAL==3.10.3) or run inside the prepared Docker containers."
                ),
                id="core.E001",
            )
        )
        return messages

    default_db = settings.DATABASES.get(DEFAULT_DB_ALIAS, {})
    engine = default_db.get("ENGINE", "")
    if "postgis" not in engine:
        messages.append(
            checks.Warning(
                "Default database engine is not PostGIS; spatial queries will be unavailable.",
                hint="Set DB_ENGINE=postgis and run migrations against the PostGIS database.",
                id="core.W001",
            )
        )
        return messages

    try:
        connection = connections[DEFAULT_DB_ALIAS]
        with connection.cursor() as cursor:
            cursor.execute("SELECT PostGIS_Version();")
            cursor.fetchone()
    except Exception as exc:  # pragma: no cover - environment specific
        logger.debug("PostGIS health check failed", exc_info=exc)
        messages.append(
            checks.Critical(
                "PostGIS check failed: unable to execute PostGIS_Version().",
                hint="Confirm the database has CREATE EXTENSION postgis and credentials allow connections.",
                obj=DEFAULT_DB_ALIAS,
                id="core.E002",
            )
        )

    return messages
