"""EV-0024: proximidade no PostGIS (ST_DWithin) e sincronização lat/lng <-> location."""

from __future__ import annotations

import importlib
import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, Point
from django.db import connection
from django.test import Client
from django.urls import reverse

from inventory.models import Device, FiberCable, Port, Site
from inventory.usecases.spatial import find_cables_near_path, find_site_within

pytestmark = pytest.mark.django_db

# ~1 m em graus de latitude; longitude a -16° ≈ 0.96 disso.
DEG_PER_M_LAT = 1 / 111_320


def _site(name: str, lat: float, lng: float) -> Site:
    return Site.objects.create(display_name=name, latitude=lat, longitude=lng)


# ---------------------------------------------------------------- sinal / migração


def test_saving_lat_lng_fills_location():
    site = _site("POP-A", -16.6799, -49.2550)
    site.refresh_from_db()
    assert site.location is not None
    assert (round(site.location.x, 4), round(site.location.y, 4)) == (-49.255, -16.6799)


def test_changing_lat_lng_moves_location():
    site = _site("POP-B", -16.0, -49.0)
    site.latitude, site.longitude = -17.0, -50.0
    site.save()
    site.refresh_from_db()
    assert (site.location.x, site.location.y) == (-50.0, -17.0)


def test_location_only_fills_lat_lng():
    site = Site.objects.create(display_name="POP-C", location=Point(-48.5, -15.5, srid=4326))
    site.refresh_from_db()
    assert float(site.latitude) == -15.5 and float(site.longitude) == -48.5


def test_backfill_migration_fills_legacy_sites():
    site = _site("POP-LEGADO", -16.1, -49.1)
    Site.objects.filter(pk=site.pk).update(location=None)  # como ficou antes do sinal
    assert Site.objects.get(pk=site.pk).location is None
    mig = importlib.import_module("inventory.migrations.0070_backfill_site_location")
    from django.apps import apps

    mig.backfill_site_location(apps, connection.schema_editor())
    assert Site.objects.get(pk=site.pk).location is not None


# ---------------------------------------------------------------- regra dos 100 m


def test_find_site_within_returns_nearest_inside_radius():
    _site("LONGE", -16.70, -49.30)  # ~ vários km
    perto = _site("PERTO", -16.6799 + 30 * DEG_PER_M_LAT, -49.2550)  # ~30 m a norte
    mais_perto = _site("MAIS-PERTO", -16.6799 + 10 * DEG_PER_M_LAT, -49.2550)  # ~10 m
    match = find_site_within(-16.6799, -49.2550, 100.0)
    assert match is not None
    site, dist_m = match
    assert site.pk == mais_perto.pk
    assert 5 < dist_m < 15
    assert perto.pk != site.pk


def test_find_site_within_is_none_beyond_radius():
    _site("A-150M", -16.6799 + 150 * DEG_PER_M_LAT, -49.2550)
    assert find_site_within(-16.6799, -49.2550, 100.0) is None


# ---------------------------------------------------------------- cabos próximos


def _cable(name: str, lat_offset_m: float) -> FiberCable:
    site = Site.objects.create(display_name=f"S-{name}")
    device = Device.objects.create(site=site, name=f"D-{name}")
    p1 = Port.objects.create(device=device, name="p1")
    p2 = Port.objects.create(device=device, name="p2")
    lat = -16.68 + lat_offset_m * DEG_PER_M_LAT
    return FiberCable.objects.create(
        name=name,
        origin_port=p1,
        destination_port=p2,
        path=LineString((-49.26, lat), (-49.25, lat), srid=4326),
    )


PLANNED = [{"lat": -16.68, "lng": -49.26}, {"lat": -16.68, "lng": -49.25}]


def test_find_cables_near_path_orders_by_distance_and_respects_threshold():
    a_20 = _cable("A-20M", 20)
    b_40 = _cable("B-40M", 40)
    _cable("C-500M", 500)
    found = find_cables_near_path(PLANNED, threshold_m=50.0)
    assert [c["id"] for c in found] == [a_20.pk, b_40.pk]
    assert 15 < found[0]["distance_meters"] < 25
    assert 35 < found[1]["distance_meters"] < 45


def test_find_cables_near_path_excludes_self_and_ignores_short_paths():
    me = _cable("EU", 0)
    assert find_cables_near_path(PLANNED, exclude_id=me.pk) == []
    assert find_cables_near_path([{"lat": -16.68, "lng": -49.26}]) == []


def test_validate_nearby_endpoint_uses_postgis_path():
    _cable("VIZINHO", 10)
    client = Client()
    client.force_login(get_user_model().objects.create_user(username="eng", password="x"))
    response = client.post(
        reverse("inventory-api:fibers-validate-nearby"),
        data=json.dumps({"path": PLANNED}),
        content_type="application/json",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["has_nearby"] is True
    assert payload["threshold_meters"] == 50.0
    assert payload["nearby_cables"][0]["name"] == "VIZINHO"
