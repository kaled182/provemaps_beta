"""Sync spatial fields before persisting inventory models."""
from __future__ import annotations

from typing import Any

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import FiberCable
from .models_routes import RouteSegment
from .spatial import ensure_wgs84


def _sync_spatial_fields(instance: Any, *, allow_coords_to_path: bool) -> None:
    """Ensure path PostGIS field has WGS84 SRID."""
    path = getattr(instance, "path", None)
    
    if path:
        ensure_wgs84(path)


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
