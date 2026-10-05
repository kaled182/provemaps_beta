"""Sync spatial fields before persisting inventory models."""

from __future__ import annotations

from typing import Any

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import FiberCable, Site
from .models_routes import RouteSegment
from .spatial import ensure_wgs84, has_gis_support


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


def sync_site_location(instance: Site) -> None:
    """Keep ``Site.location`` (geography, used by ST_DWithin) in step with lat/lng.

    EV-0024: até aqui ``latitude``/``longitude`` e ``location`` eram escritos à
    mão em sítios diferentes e divergiam — um site sem ``location`` é invisível
    para qualquer consulta espacial. lat/lng são a fonte (é o que a UI edita);
    quando só vem ``location``, preenche-se lat/lng a partir dele.
    """

    if not has_gis_support():
        return
    from django.contrib.gis.geos import Point

    lat, lng = instance.latitude, instance.longitude
    if lat is not None and lng is not None:
        point = Point(float(lng), float(lat), srid=4326)
        current = instance.location
        if current is None or (current.x, current.y) != (point.x, point.y):
            instance.location = point
    elif instance.location is not None:
        instance.longitude = round(instance.location.x, 6)
        instance.latitude = round(instance.location.y, 6)


@receiver(pre_save, sender=Site)
def sync_site_spatial_fields(sender: type[Site], instance: Site, **_: Any) -> None:
    sync_site_location(instance)
