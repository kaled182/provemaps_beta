"""EV-0115 — limiares de RX das portas de switch (backbone): gravados na base, lidos depois
de um reinício, e com -20/-24 por omissão; não mexem nos limiares do GPON."""

from __future__ import annotations

import pytest
from django.core.cache import cache

from setup_app.models import FirstTimeSetup
from setup_app.services import runtime_settings as rs
from setup_app.tests.test_usecases_config import _runtime_config
from setup_app.usecases import config as uc


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.delete(rs._VERSION_KEY)
    rs.reload_config()
    yield
    rs.reload_config()


@pytest.mark.django_db
def test_backbone_thresholds_are_persisted_and_read_back():
    payload = uc.build_configuration_payload(
        {"BACKBONE_RX_WARNING_THRESHOLD": "-19.5", "BACKBONE_RX_CRITICAL_THRESHOLD": "-23"},
        _runtime_config(),
        "",
    )
    assert (
        payload["BACKBONE_RX_WARNING_THRESHOLD"],
        payload["BACKBONE_RX_CRITICAL_THRESHOLD"],
    ) == ("-19.5", "-23.0")
    FirstTimeSetup.objects.create(
        company_name="X", zabbix_url="http://z", auth_type="token", configured=True
    )
    uc._persist_configuration(payload)
    rec = FirstTimeSetup.objects.get(configured=True)
    assert (rec.backbone_rx_warning_threshold, rec.backbone_rx_critical_threshold) == (-19.5, -23.0)
    rs.reload_config()
    cfg = rs.get_runtime_config()
    assert (cfg.backbone_rx_warning_threshold, cfg.backbone_rx_critical_threshold) == (-19.5, -23.0)
    assert cfg.optical_rx_warning_threshold == -24.0  # o GPON fica como estava


@pytest.mark.django_db
def test_defaults_without_values():
    FirstTimeSetup.objects.create(
        company_name="X", zabbix_url="http://z", auth_type="token", configured=True
    )
    cfg = rs.get_runtime_config()
    assert (cfg.backbone_rx_warning_threshold, cfg.backbone_rx_critical_threshold) == (-20.0, -24.0)
