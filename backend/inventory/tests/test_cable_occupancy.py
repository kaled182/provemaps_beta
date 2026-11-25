"""EV-0061 — ocupação dos cabos pelas fibras cadastradas; sem fibras é null, nunca 0."""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from inventory.domain.strands import occupancy_from_counts
from inventory.models import BufferTube, FiberCable, FiberStrand


@pytest.fixture
def client(db):
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    return c


def _strands(cable, statuses):
    tube = BufferTube.objects.create(cable=cable, number=1, color="azul", color_hex="#0000ff")
    for i, status in enumerate(statuses, start=1):
        FiberStrand.objects.create(
            tube=tube, number=i, absolute_number=i, color="c", color_hex="#000000", status=status
        )


def test_occupancy_from_counts():
    assert occupancy_from_counts(0, 0, 0, 0) is None
    assert occupancy_from_counts(4, 2, 1, 1) == {"registered": 4, "used": 2, "free": 1, "broken": 1}


@pytest.mark.django_db
def test_list_and_detail_expose_occupancy(client):
    empty = FiberCable.objects.create(name="sem-fibras")
    full = FiberCable.objects.create(name="com-fibras")
    _strands(full, ["lit", "reserved", "dark", "broken", "lit"])
    for i in range(5):
        FiberCable.objects.create(name=f"extra-{i}")

    body = client.get("/api/v1/fiber-cables/").json()
    rows = {r["name"]: r for r in body.get("results", body)}
    assert rows["sem-fibras"]["occupancy"] is None
    assert rows["com-fibras"]["occupancy"] == {"registered": 5, "used": 3, "free": 1, "broken": 1}
    assert list(rows["com-fibras"])[-1] == "occupancy"  # chave nova no fim (ordem estável)

    detail = client.get(f"/api/v1/fiber-cables/{empty.id}/").json()
    assert detail["occupancy"] is None


@pytest.mark.django_db
def test_list_occupancy_has_no_per_cable_query(client):
    """A ocupação vem anotada na consulta principal: o nº de consultas que tocam nas
    fibras não cresce com o nº de cabos (o N+1 de infraestrutura é outro — EV-0062)."""
    import django.db
    from django.test.utils import CaptureQueriesContext

    def strand_queries():
        with CaptureQueriesContext(django.db.connection) as q:
            client.get("/api/v1/fiber-cables/")
        return sum(1 for x in q.captured_queries if "inventory_fiber_strand" in x["sql"])

    for i in range(2):
        _strands(FiberCable.objects.create(name=f"c{i}"), ["lit", "dark"])
    few = strand_queries()
    for i in range(2, 8):
        _strands(FiberCable.objects.create(name=f"c{i}"), ["lit", "dark"])
    assert strand_queries() == few


@pytest.mark.django_db
def test_list_infrastructure_points_are_prefetched(client):
    """EV-0062: os pontos de infraestrutura vêm de um prefetch, não de uma
    consulta por cabo."""
    import django.db
    from django.contrib.gis.geos import Point
    from django.test.utils import CaptureQueriesContext

    from inventory.models import FiberInfrastructure

    def infra_queries():
        with CaptureQueriesContext(django.db.connection) as q:
            body = client.get("/api/v1/fiber-cables/").json()
        n = sum(1 for x in q.captured_queries if "inventory_fiber_infrastructure" in x["sql"])
        return n, body

    def add(i):
        cable = FiberCable.objects.create(name=f"infra-{i}")
        FiberInfrastructure.objects.create(
            cable=cable,
            type=FiberInfrastructure.TYPES[0][0],
            name=f"p{i}",
            location=Point(-49, -16),
        )

    for i in range(2):
        add(i)
    few, _ = infra_queries()
    for i in range(2, 8):
        add(i)
    many, body = infra_queries()
    assert many == few
    rows = body.get("results", body)
    assert all(len(r["infrastructure_points"]) == 1 for r in rows)
