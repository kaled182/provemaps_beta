"""Helper utilities for synchronizing GeoDjango spatial fields."""
from __future__ import annotations

from typing import Any, Iterable, List, Mapping, MutableMapping, Sequence, cast

from django.core.exceptions import ImproperlyConfigured

try:  # pragma: no cover
    from django.contrib.gis.geos import LineString as GeoLineString
except (ImportError, ImproperlyConfigured):  # pragma: no cover - fallback mode
    GeoLineString = None  # type: ignore[assignment]

SRID_WGS84 = 4326


def has_gis_support() -> bool:
    """Return True when GeoDjango spatial types are available."""

    return GeoLineString is not None


def coords_to_linestring(
    coords: Sequence[Mapping[str, Any]] | None,
) -> Any:
    """Convert a list of {lat, lng} dicts into a LineString."""

    if GeoLineString is None or not coords or len(coords) < 2:
        return None

    points: List[tuple[float, float]] = []
    for coord in coords:
        lat = coord.get("lat")
        lng = coord.get("lng")
        if lat is None or lng is None:
            return None
        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (TypeError, ValueError):
            return None
        if not (-90 <= lat_f <= 90) or not (-180 <= lng_f <= 180):
            return None
        points.append((lng_f, lat_f))

    if len(points) < 2:
        return None

    try:
        return GeoLineString(points, srid=SRID_WGS84)
    except Exception:  # pragma: no cover - invalid geometry
        return None


def linestring_to_coords(path: Any) -> List[MutableMapping[str, float]]:
    """Return [{lat, lng}] payload for a LineString or compatible object."""

    if path is None:
        return []

    coords_attr = getattr(path, "coords", None)
    if coords_attr is None:
        if isinstance(path, Iterable):
            result: List[MutableMapping[str, float]] = []
            for item in path:  # pragma: no cover - fallback JSON mode
                if (
                    isinstance(item, Mapping)
                    and "lat" in item
                    and "lng" in item
                ):
                    lat_val = cast(Any, item["lat"])
                    lng_val = cast(Any, item["lng"])
                    try:
                        lat_f = float(lat_val)
                        lng_f = float(lng_val)
                    except (TypeError, ValueError):
                        continue
                    result.append({"lat": lat_f, "lng": lng_f})
            return result
        return []

    return [
        {"lat": float(lat), "lng": float(lng)}
        for lng, lat in coords_attr
    ]


def ensure_wgs84(path: Any) -> Any:
    """Force SRID 4326 when spatial support is available."""

    if GeoLineString is None or path is None:
        return path
    current_srid = getattr(path, "srid", None)
    if current_srid != SRID_WGS84:
        path.srid = SRID_WGS84
    return path
