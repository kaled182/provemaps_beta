"""EV-0071 — a API de portas devolve o cabo ligado (origem ou destino), numa só consulta."""

import django.db
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.test.utils import CaptureQueriesContext

from inventory.models import Device, FiberCable, Port, Site


@pytest.fixture
def client(db):
    c = Client()
    c.force_login(get_user_model().objects.create_user(username="noc", password="x"))
    return c


@pytest.fixture
def device(db):
    site = Site.objects.create(display_name="POP BRV")
    return Device.objects.create(name="OLT BRV", site=site)


def _rows(client, device):
    body = client.get(f"/api/v1/ports/?device={device.id}").json()
    return {r["name"]: r for r in body.get("results", body)}


@pytest.mark.django_db
def test_ports_expose_connected_cable_on_both_ends(client, device):
    origin = Port.objects.create(device=device, name="gpon-1")
    dest = Port.objects.create(device=device, name="gpon-2")
    Port.objects.create(device=device, name="livre")
    cable = FiberCable.objects.create(
        name="BRV - PLANURA", origin_port=origin, destination_port=dest
    )

    rows = _rows(client, device)
    assert rows["gpon-1"]["cable_id"] == cable.id
    assert rows["gpon-1"]["cable_name"] == "BRV - PLANURA"
    assert rows["gpon-2"]["cable_id"] == cable.id  # também como destino
    assert rows["livre"]["cable_id"] is None
    assert rows["livre"]["cable_name"] is None
    # chaves novas no fim (os serializers não reordenam — CLAUDE.md §5)
    assert list(rows["gpon-1"])[-2:] == ["cable_id", "cable_name"]


@pytest.mark.django_db
def test_detail_and_create_keep_the_contract(client, device):
    port = Port.objects.create(device=device, name="xe-0/0/1")
    cable = FiberCable.objects.create(name="C1", origin_port=port)
    detail = client.get(f"/api/v1/ports/{port.id}/").json()
    assert detail["cable_id"] == cable.id

    created = client.post(
        "/api/v1/ports/", {"device": device.id, "name": "nova"}, content_type="application/json"
    )
    assert created.status_code == 201, created.content
    assert created.json()["cable_id"] is None  # instância criada não vem anotada


@pytest.mark.django_db
def test_connected_cable_is_not_n_plus_one(client, device):
    """O nº de consultas à tabela de cabos não cresce com o nº de portas."""

    def cable_queries():
        with CaptureQueriesContext(django.db.connection) as q:
            client.get(f"/api/v1/ports/?device={device.id}")
        return sum(1 for x in q.captured_queries if "zabbix_api_fibercable" in x["sql"])

    for i in range(2):
        p = Port.objects.create(device=device, name=f"p{i}")
        FiberCable.objects.create(name=f"c{i}", origin_port=p)
    few = cable_queries()
    for i in range(2, 10):
        p = Port.objects.create(device=device, name=f"p{i}")
        FiberCable.objects.create(name=f"c{i}", origin_port=p)
    assert cable_queries() == few
