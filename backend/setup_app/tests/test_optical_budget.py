"""EV-0140 — orçamento óptico: padrões, normalização (valores fora do intervalo voltam ao padrão)
e o caminho completo pela configuração (gravar → base → configuração em memória)."""

import pytest

from setup_app.optical_budget import DEFAULT_OPTICAL_BUDGET, parse_optical_budget


def test_defaults_are_the_agreed_values():
    assert parse_optical_budget(None) == {
        "fiber_db_km": 0.25,
        "fusion_db": 0.10,
        "splitters": {"1x2": 3.7, "1x4": 7.1, "1x8": 10.5, "1x16": 13.7, "1x32": 17.1},
        "tx_default_dbm": 5.0,
    }
    assert parse_optical_budget(None) == DEFAULT_OPTICAL_BUDGET


def test_parse_accepts_json_and_comma_and_rejects_out_of_range():
    b = parse_optical_budget(
        '{"fiber_db_km": "0,35", "fusion_db": 9, "splitters": {"1x8": 10.9, "1x4": -1}, "tx_default_dbm": 3}'
    )
    assert b["fiber_db_km"] == pytest.approx(0.35)
    assert b["fusion_db"] == 0.10  # 9 dB por fusão é absurdo → padrão
    assert b["splitters"]["1x8"] == 10.9 and b["splitters"]["1x4"] == 7.1
    assert b["tx_default_dbm"] == 3.0
    assert parse_optical_budget("não é json") == DEFAULT_OPTICAL_BUDGET


@pytest.mark.django_db
def test_budget_persists_and_reaches_runtime_config():
    from setup_app.models import FirstTimeSetup
    from setup_app.services import runtime_settings
    from setup_app.services.config_loader import clear_runtime_config_cache

    FirstTimeSetup.objects.create(
        company_name="X", configured=True, optical_budget={"fiber_db_km": 0.3, "tx_default_dbm": 2}
    )
    clear_runtime_config_cache()
    cfg = runtime_settings.get_runtime_config()
    assert cfg.optical_budget["fiber_db_km"] == 0.3 and cfg.optical_budget["tx_default_dbm"] == 2.0
    assert cfg.optical_budget["fusion_db"] == 0.10
