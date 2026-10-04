"""EV-0013 — listagem de cabos: sem N+1 em cable_type, tolerante a porta nula, filtro bbox."""

from __future__ import annotations

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from inventory.models import CableType, Device, FiberCable, Port, Site
from inventory.usecases import fibers as fiber_uc


def _make_port(site_name, lat, lng, idx):
    site = Site.objects.create(display_name=site_name, city="Goiania", latitude=lat, longitude=lng)
    device = Device.objects.create(
        site=site, name=f"DEV-{idx}", vendor="X", model="Y", zabbix_hostid=str(1000 + idx)
    )
    return Port.objects.create(device=device, name=f"GE0/0/{idx}")


class ListFiberCablesTests(TestCase):
    def setUp(self):
        self.cable_type = CableType.objects.create(name="AS-80 12FO")
        self.p1 = _make_port("POP-A", -16.60, -49.30, 1)
        self.p2 = _make_port("POP-B", -16.70, -49.20, 2)
        self.p3 = _make_port("POP-C", -16.80, -49.10, 3)

    def test_query_count_does_not_grow_with_cables(self):
        """cable_type vem por JOIN: 1 cabo e 4 cabos custam o mesmo número de queries."""
        FiberCable.objects.create(
            name="CABO-0", origin_port=self.p1, destination_port=self.p2, cable_type=self.cable_type
        )
        with CaptureQueriesContext(connection) as one:
            payload = fiber_uc.list_fiber_cables()
        self.assertEqual(payload[0]["cable_type"], {"id": self.cable_type.id, "name": "AS-80 12FO"})

        for i in range(1, 4):
            FiberCable.objects.create(
                name=f"CABO-{i}",
                origin_port=self.p2,
                destination_port=self.p3,
                cable_type=self.cable_type,
            )
        with CaptureQueriesContext(connection) as four:
            payload = fiber_uc.list_fiber_cables()
        self.assertEqual(len(payload), 4)
        self.assertEqual(len(four.captured_queries), len(one.captured_queries))

    def test_cable_with_missing_destination_port_does_not_crash(self):
        FiberCable.objects.create(name="PONTA-SOLTA", origin_port=self.p1, destination_port=None)
        payload = fiber_uc.list_fiber_cables()
        row = payload[0]
        self.assertEqual(row["origin_port_id"], self.p1.id)
        self.assertIsNone(row["destination_port_id"])
        self.assertIsNone(row["destination"]["site"])
        self.assertEqual(row["origin"]["lat"], -16.6)


class BboxFilterTests(TestCase):
    def test_parse_bbox(self):
        self.assertEqual(
            fiber_uc.parse_bbox("-49.5,-16.9,-49.0,-16.5"), (-49.5, -16.9, -49.0, -16.5)
        )
        self.assertIsNone(fiber_uc.parse_bbox(None))
        self.assertIsNone(fiber_uc.parse_bbox("abc"))
        self.assertIsNone(fiber_uc.parse_bbox("1,2,3"))
        self.assertIsNone(fiber_uc.parse_bbox("-49.0,-16.5,-49.5,-16.9"))  # min > max

    def test_filter_keeps_cables_touching_the_box(self):
        inside = {
            "id": 1,
            "path": [{"lat": -16.60, "lng": -49.30}],
            "origin": {},
            "destination": {},
        }
        crossing = {
            "id": 2,
            "path": [],
            "origin": {"lat": -17.0, "lng": -50.0},
            "destination": {"lat": -16.0, "lng": -49.0},
        }
        outside = {"id": 3, "path": [{"lat": -20.0, "lng": -45.0}], "origin": {}, "destination": {}}
        no_coords = {"id": 4, "path": [], "origin": {}, "destination": {}}
        kept = fiber_uc.filter_cables_by_bbox(
            [inside, crossing, outside, no_coords], (-49.5, -16.9, -49.0, -16.5)
        )
        self.assertEqual([c["id"] for c in kept], [1, 2])
