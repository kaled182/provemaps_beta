"""Helpers to keep migrations running when GDAL/GEOS are unavailable."""
from __future__ import annotations

from typing import Any

from django.core.exceptions import ImproperlyConfigured

from inventory.fields import LenientJSONField


class JSONPointField(LenientJSONField):
    """JSON-backed PointField replacement for SQLite test environments."""

    description = "JSON storage fallback for PointField when GIS libs are missing"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        for unsupported_key in ("srid", "geography", "spatial_index", "dim"):
            kwargs.pop(unsupported_key, None)
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        super().__init__(*args, **kwargs)


def get_point_field_class():
    try:  # pragma: no cover - depends on optional GDAL install
        from django.contrib.gis.db.models.fields import PointField
    except (ImportError, ImproperlyConfigured):
        return JSONPointField
    return PointField


def build_point(longitude: float, latitude: float, srid: int = 4326):
    try:  # pragma: no cover - depends on optional GEOS install
        from django.contrib.gis.geos import Point
    except (ImportError, ImproperlyConfigured):
        return {"longitude": longitude, "latitude": latitude, "srid": srid}
    return Point(longitude, latitude, srid=srid)
