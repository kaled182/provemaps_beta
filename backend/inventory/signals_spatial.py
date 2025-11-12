"""Sync spatial fields before persisting inventory models."""
from __future__ import annotations

import json
from typing import Any

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import FiberCable
from .models_routes import RouteSegment
from .spatial import coords_to_linestring, ensure_wgs84, linestring_to_coords


def _sync_spatial_fields(instance: Any, *, allow_coords_to_path: bool) -> None:
    path = getattr(instance, "path", None)
    coords = getattr(instance, "path_coordinates", None)

    if isinstance(coords, str):
        try:
            coords = json.loads(coords)
        except json.JSONDecodeError:
            coords = None
        else:
            instance.path_coordinates = coords

    if path:
        ensure_wgs84(path)
        if not coords:
            instance.path_coordinates = linestring_to_coords(path)
        return

    if coords and allow_coords_to_path:
        linestring = coords_to_linestring(coords)
        if linestring is None:
            return
        ensure_wgs84(linestring)
        instance.path = linestring


@receiver(pre_save, sender=FiberCable)
def sync_fiber_spatial_fields(
    sender: type[FiberCable],
    instance: FiberCable,
    **_: Any,
) -> None:
    _sync_spatial_fields(instance, allow_coords_to_path=True)


@receiver(pre_save, sender=RouteSegment)
def sync_route_spatial_fields(
    sender: type[RouteSegment],
    instance: RouteSegment,
    **_: Any,
) -> None:
    _sync_spatial_fields(instance, allow_coords_to_path=False)
