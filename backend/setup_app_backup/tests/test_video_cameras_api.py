"""Tests for the video cameras API endpoints."""

from __future__ import annotations

import sys
import types

import json

import pytest
from django.test import RequestFactory

from inventory.models import Site
from setup_app.models import MessagingGateway
from setup_app.api_views import video_cameras_list


class _DummyStats:
    percent = 0.0
    used = 0.0
    total = 1.0


_dummy_psutil = types.SimpleNamespace(
    cpu_percent=lambda interval=None: 0.0,
    virtual_memory=lambda: _DummyStats(),
    disk_usage=lambda path: _DummyStats(),
)

sys.modules.setdefault("psutil", _dummy_psutil)


@pytest.mark.django_db
def test_video_cameras_list_returns_whep_url(admin_user):
    """The API must expose MediaMTX WHEP endpoints with the correct path order."""
    site = Site.objects.create(display_name="Central Hub")
    gateway = MessagingGateway.objects.create(
        name="Central Camera",
        gateway_type="video",
        site_name=site.display_name,
        config={
            "webrtc_public_base_url": "http://media.example",
            "restream_key": "camera-main",
        },
    )

    request = RequestFactory().get("/api/v1/cameras/", {"site": site.id})
    request.user = admin_user

    response = video_cameras_list(request)

    assert response.status_code == 200
    payload = json.loads(response.content)
    assert payload["success"] is True
    assert payload["count"] == 1

    camera_data = payload["results"][0]
    assert camera_data["id"] == gateway.id
    assert camera_data["whep_url"] == "http://media.example/whep/camera-main"
