from __future__ import annotations

from math import atan2, cos, radians, sin, sqrt
from typing import Any, Dict, Iterable, List, cast

__all__ = ["haversine_km", "calculate_path_length", "sanitize_path_points"]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the distance between two geographic points using Haversine."""
    radius_km = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius_km * c


def calculate_path_length(path_points: Iterable[Dict[str, float]]) -> float:
    """Return the approximate length of a route in kilometers."""
    points: List[Dict[str, float]] = list(path_points or [])
    if len(points) < 2:
        return 0.0

    total = 0.0
    for current, nxt in zip(points, points[1:]):
        lat1, lng1 = current.get("lat"), current.get("lng")
        lat2, lng2 = nxt.get("lat"), nxt.get("lng")
        if (
            lat1 is None
            or lng1 is None
            or lat2 is None
            or lng2 is None
        ):
            continue
        total += haversine_km(
            float(lat1),
            float(lng1),
            float(lat2),
            float(lng2),
        )
    return round(total, 3)


def sanitize_path_points(
    raw_points: Any, *, allow_empty: bool = False
) -> List[Dict[str, float]]:
    """Normalize route points, discarding invalid entries.

    When ``allow_empty`` is ``False`` (default) the path must contain at least
    two valid points.
    """
    sanitized: List[Dict[str, float]] = []
    if isinstance(raw_points, list):
        iterable_points: List[Any] = cast(List[Any], raw_points)
    else:
        iterable_points = []

    for entry in iterable_points:
        if not isinstance(entry, dict):
            continue
        entry_dict = cast(Dict[str, Any], entry)
        lat_raw = entry_dict.get("lat")
        lng_raw = entry_dict.get("lng")
        if lat_raw is None or lng_raw is None:
            continue
        try:
            lat = float(lat_raw)
            lng = float(lng_raw)
        except (TypeError, ValueError):
            continue
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            sanitized.append({"lat": lat, "lng": lng})

    if len(sanitized) == 1:
        raise ValueError("Path requires at least two valid points")

    if not allow_empty and len(sanitized) < 2:
        raise ValueError("Path requires at least two valid points")
    return sanitized
