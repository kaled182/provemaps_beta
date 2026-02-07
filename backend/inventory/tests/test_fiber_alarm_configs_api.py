from __future__ import annotations

import pytest
from django.urls import reverse, path, include
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework.routers import DefaultRouter
from django.http import HttpResponse

from inventory.models import Device, FiberCable, Port, Site, FiberCableAlarmConfig
from inventory.viewsets import FiberCableViewSet
from setup_app.models import AlertTemplate
from setup_app.models_contacts import Contact, ContactGroup


router = DefaultRouter()
router.register(r"fibers", FiberCableViewSet, basename="fibercable")

def _dummy_setup_view(request):  # pragma: no cover - simple stub
    return HttpResponse("ok")

setup_patterns = (
    [path("first-time-setup/", _dummy_setup_view, name="first_time_setup")],
    "setup_app",
)

urlpatterns = [
    path("api/v1/inventory/", include(router.urls)),
    path("setup_app/", include(setup_patterns, namespace="setup_app")),
]


@pytest.fixture(autouse=True)
def override_urls() -> None:
    """Isolate URL configuration to avoid GIS dependencies during tests."""
    with override_settings(ROOT_URLCONF="inventory.tests.test_fiber_alarm_configs_api"):
        yield


@pytest.fixture
@pytest.mark.django_db
def inventory_setup(django_user_model):
    user = django_user_model.objects.create_user(
        username="alarm-admin",
        email="alarm@example.com",
        password="secret123",
    )

    site_a = Site.objects.create(display_name="Site A")
    site_b = Site.objects.create(display_name="Site B")

    device_a = Device.objects.create(site=site_a, name="Device A")
    device_b = Device.objects.create(site=site_b, name="Device B")

    port_a = Port.objects.create(device=device_a, name="Port A")
    port_b = Port.objects.create(device=device_b, name="Port B")

    cable = FiberCable.objects.create(
        name="ALARM-CABLE-001",
        origin_port=port_a,
        destination_port=port_b,
    )

    group = ContactGroup.objects.create(name="NOC", description="Equipe NOC")
    contact = Contact.objects.create(
        name="João da Silva",
        phone="+5561999999999",
        email="noc@example.com",
    )
    contact.groups.add(group)

    email_template = AlertTemplate.objects.create(
        name="Email Óptico",
        category=AlertTemplate.CATEGORY_OPTICAL_LEVEL,
        channel=AlertTemplate.CHANNEL_EMAIL,
        subject="Alerta nível óptico {{site_name}}",
        content="Nível óptico {{signal_level}} em {{device_name}}",
        is_default=True,
    )

    whatsapp_template = AlertTemplate.objects.create(
        name="WhatsApp Óptico",
        category=AlertTemplate.CATEGORY_OPTICAL_LEVEL,
        channel=AlertTemplate.CHANNEL_WHATSAPP,
        content="Alerta óptico {{signal_level}}",
        is_default=True,
    )

    return {
        "user": user,
        "cable": cable,
        "group": group,
        "contact": contact,
        "email_template": email_template,
        "whatsapp_template": whatsapp_template,
    }


@pytest.mark.django_db
def test_create_and_list_alarm_configs(inventory_setup):
    client = APIClient()
    client.force_authenticate(user=inventory_setup["user"])

    cable = inventory_setup["cable"]
    group = inventory_setup["group"]

    url = reverse("fibercable-alarms", kwargs={"pk": cable.pk})

    # Initially empty
    response = client.get(url)
    assert response.status_code == 200
    assert response.json() == {"results": []}

    payload = {
        "target": "department_group",
        "department_group": group.pk,
        "channels": ["email", "whatsapp"],
        "trigger_level": "warning",
        "persist_minutes": 5,
        "description": "Escalar NOC",
        "template_category": AlertTemplate.CATEGORY_OPTICAL_LEVEL,
        "templates": {
            "email": inventory_setup["email_template"].pk,
            "whatsapp": inventory_setup["whatsapp_template"].pk,
        },
    }

    response = client.post(url, payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["target_type"] == "department_group"
    assert data["target_display"].startswith(group.name)
    assert data["channels"] == ["email", "whatsapp"]
    assert data["persist_minutes"] == 5
    assert data["templates"]["category"] == AlertTemplate.CATEGORY_OPTICAL_LEVEL
    assert data["templates"]["bindings"]["email"] == inventory_setup["email_template"].pk
    assert data["templates"]["bindings"]["whatsapp"] == inventory_setup["whatsapp_template"].pk

    assert FiberCableAlarmConfig.objects.count() == 1
    config = FiberCableAlarmConfig.objects.first()
    assert config is not None
    assert config.contact_group_id == group.pk
    assert config.fiber_cable_id == cable.pk

    # GET should now return the saved configuration
    response = client.get(url)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["id"] == data["id"]
    assert results[0]["target_display"].startswith(group.name)
    assert results[0]["templates"]["bindings"]["email"] == inventory_setup["email_template"].pk


@pytest.mark.django_db
def test_create_alarm_uses_default_template_when_not_provided(inventory_setup):
    client = APIClient()
    client.force_authenticate(user=inventory_setup["user"])

    cable = inventory_setup["cable"]
    contact = inventory_setup["contact"]

    url = reverse("fibercable-alarms", kwargs={"pk": cable.pk})

    payload = {
        "target": "contact",
        "contact": contact.pk,
        "channels": ["whatsapp"],
        "trigger_level": "critical",
    }

    response = client.post(url, payload, format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["templates"]["bindings"]["whatsapp"] == inventory_setup["whatsapp_template"].pk


@pytest.mark.django_db
def test_create_alarm_requires_channels(inventory_setup):
    client = APIClient()
    client.force_authenticate(user=inventory_setup["user"])

    cable = inventory_setup["cable"]
    contact = inventory_setup["contact"]

    url = reverse("fibercable-alarms", kwargs={"pk": cable.pk})

    payload = {
        "target": "contact",
        "contact": contact.pk,
        "channels": [],
        "trigger_level": "critical",
    }

    response = client.post(url, payload, format="json")
    assert response.status_code == 400
    body = response.json()
    assert "error" in body
    assert "Selecione" in body["error"]
    assert FiberCableAlarmConfig.objects.count() == 0
