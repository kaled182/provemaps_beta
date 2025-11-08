from __future__ import annotations

import json
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT

from inventory.api import fibers as fibers_api


def _disable_guard(_: Any) -> None:
    return None


@pytest.mark.django_db
def test_api_import_fiber_kml_requires_mandatory_fields(
    rf: Any,
    django_user_model: Any,
    monkeypatch: Any,
) -> None:
    user = django_user_model.objects.create_user(
        username="staff",
        email="staff@example.com",
        password="test123",
    )

    request = rf.post("/api/v1/inventory/fibers/import-kml/", {})
    request.user = user

    monkeypatch.setattr(fibers_api, "diagnostics_guard", _disable_guard)

    response = fibers_api.api_import_fiber_kml(request)

    assert response.status_code == 400
    assert json.loads(response.content) == {"error": "Missing required fields"}


@pytest.mark.django_db
def test_api_import_fiber_kml_success(
    monkeypatch: Any,
    rf: Any,
    django_user_model: Any,
) -> None:
    user = django_user_model.objects.create_user(
        username="operator",
        email="operator@example.com",
        password="secret123",
    )

    upload = SimpleUploadedFile(
        "trace.kml",
        b"<kml></kml>",
        content_type="application/vnd.google-earth.kml+xml",
    )
    request = rf.post(
        "/api/v1/inventory/fibers/import-kml/",
        data={
            "name": "Cable CI",
            "origin_device_id": "1",
            "dest_device_id": "2",
            "origin_port_id": "10",
            "dest_port_id": "20",
            "single_port": "true",
            "kml_file": upload,
        },
        content_type=MULTIPART_CONTENT,
    )
    request.user = user

    monkeypatch.setattr(fibers_api, "diagnostics_guard", _disable_guard)

    captured: dict[str, object] = {}

    def fake_create_fiber(
        name: str,
        origin_device_id: str,
        dest_device_id: str,
        origin_port_id: str,
        dest_port_id: str,
        kml_file: object,
        *,
        single_port: bool = False,
    ) -> dict[str, object]:
        captured.update(
            {
                "name": name,
                "origin_device_id": origin_device_id,
                "dest_device_id": dest_device_id,
                "origin_port_id": origin_port_id,
                "dest_port_id": dest_port_id,
                "single_port": single_port,
                "kml_file_provided": bool(kml_file),
            }
        )
        return {"ok": True}

    monkeypatch.setattr(
        fibers_api.fiber_uc,
        "create_fiber_from_kml",
        fake_create_fiber,
    )

    response = fibers_api.api_import_fiber_kml(request)

    assert response.status_code == 200
    assert json.loads(response.content) == {"ok": True}
    assert captured["name"] == "Cable CI"
    assert captured["single_port"] is True


@pytest.mark.django_db
def test_api_fiber_cables_returns_payload(
    rf: Any,
    django_user_model: Any,
    monkeypatch: Any,
) -> None:
    user = django_user_model.objects.create_user(
        username="viewer",
        email="viewer@example.com",
        password="secret123",
    )

    expected_payload = [
        {"fiber_id": 1, "name": "Backbone"},
    ]

    monkeypatch.setattr(
        fibers_api.fiber_uc,
        "list_fiber_cables",
        lambda: expected_payload,
    )

    request = rf.get("/api/v1/inventory/fibers/")
    request.user = user

    response = fibers_api.api_fiber_cables(request)

    assert response.status_code == 200
    assert json.loads(response.content) == {"cables": expected_payload}
