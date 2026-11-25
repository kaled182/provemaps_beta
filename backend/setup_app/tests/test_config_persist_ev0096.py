"""EV-0096 — limiares ópticos e capacidades de PON sobrevivem a um reinício e chegam aos
outros processos (Celery, outros workers do web).

Antes: `update_configuration` só os punha no `os.environ`/`settings` do processo que gravou e
o `get_runtime_config` era um `lru_cache` por processo — reiniciar voltava aos padrões e o
Celery nunca via o valor editado.
"""

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


def _record(**fields) -> FirstTimeSetup:
    return FirstTimeSetup.objects.create(
        company_name="X", zabbix_url="http://z", auth_type="token", configured=True, **fields
    )


@pytest.mark.django_db
def test_persist_writes_thresholds_and_capacity_to_the_database():
    payload = uc.build_configuration_payload(
        {
            "OPTICAL_RX_WARNING_THRESHOLD": "-22.5",
            "OPTICAL_RX_CRITICAL_THRESHOLD": "-26",
            "GPON_PON_CAPACITY": "256",
            "EPON_PON_CAPACITY": "32",
        },
        _runtime_config(),
        "",
    )
    uc._persist_configuration(payload)
    rec = FirstTimeSetup.objects.get(configured=True)
    assert rec.optical_rx_warning_threshold == -22.5
    assert rec.optical_rx_critical_threshold == -26.0
    assert (rec.gpon_pon_capacity, rec.epon_pon_capacity) == (256, 32)
    assert isinstance(rec.optical_thresholds_by_distance, dict)


@pytest.mark.django_db
def test_after_restart_values_come_from_the_database_not_from_settings(settings):
    """O «reinício»: o settings tem os padrões (nada no ambiente) e a cópia em memória está
    vazia; os valores gravados têm de voltar."""
    _record(
        optical_rx_warning_threshold=-22.5,
        optical_rx_critical_threshold=-26.0,
        optical_thresholds_by_distance={"10": {"warning": -20.0, "critical": -23.0}},
        gpon_pon_capacity=256,
        epon_pon_capacity=32,
    )
    settings.OPTICAL_RX_WARNING_THRESHOLD = -24.0
    settings.GPON_PON_CAPACITY = 128
    rs.reload_config()
    cfg = rs.get_runtime_config()
    assert cfg.optical_rx_warning_threshold == -22.5
    assert cfg.optical_rx_critical_threshold == -26.0
    assert cfg.optical_thresholds_by_distance == {"10": {"warning": -20.0, "critical": -23.0}}
    assert (cfg.gpon_pon_capacity, cfg.epon_pon_capacity) == (256, 32)


@pytest.mark.django_db
def test_record_without_values_falls_back_to_settings_defaults():
    _record()
    cfg = rs.get_runtime_config()
    assert cfg.optical_rx_warning_threshold == -24.0
    assert (cfg.gpon_pon_capacity, cfg.epon_pon_capacity) == (128, 64)


@pytest.mark.django_db
def test_other_process_sees_the_change_through_the_shared_version(monkeypatch):
    """Outro processo (Celery) tem a configuração antiga em memória; quem grava sobe a versão
    na cache partilhada e a cópia do outro processo é refeita na verificação seguinte."""
    rec = _record(gpon_pon_capacity=128)
    assert rs.get_runtime_config().gpon_pon_capacity == 128

    # o «web» grava e avisa (reload_config sobe a versão partilhada)…
    FirstTimeSetup.objects.filter(pk=rec.pk).update(gpon_pon_capacity=200)
    cache.set(rs._VERSION_KEY, "nova-versao", timeout=None)
    # …o «Celery» ainda está dentro da janela: continua com a cópia que tem
    assert rs.get_runtime_config().gpon_pon_capacity == 128
    # passada a janela, compara a versão e recarrega
    monkeypatch.setattr(rs, "_VERSION_CHECK_SECONDS", 0.0)
    assert rs.get_runtime_config().gpon_pon_capacity == 200


@pytest.mark.django_db
def test_unchanged_version_does_not_hit_the_database(monkeypatch, django_assert_num_queries):
    _record()
    rs.reload_config()  # sobe a versão
    rs.get_runtime_config()
    monkeypatch.setattr(rs, "_VERSION_CHECK_SECONDS", 0.0)
    with django_assert_num_queries(0):
        rs.get_runtime_config()
