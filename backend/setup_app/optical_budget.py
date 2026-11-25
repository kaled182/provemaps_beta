"""Orçamento óptico do projeto (EV-0140): atenuações padrão e TX de partida.

Usado pelo rastreamento da luz (km * dB/km + fusões + splitters) para estimar a potência em
cada ponto. A atenuação do tipo de cabo (``CableGroup.attenuation_db_per_km``) vence a da
fibra daqui; o TX real da porta de origem (``Port.last_tx_power``, coletado do Zabbix) vence
o TX padrão.
"""

from __future__ import annotations

import json
from typing import Any

SPLITTER_RATIOS = ("1x2", "1x4", "1x8", "1x16", "1x32")

DEFAULT_OPTICAL_BUDGET: dict[str, Any] = {
    "fiber_db_km": 0.25,
    "fusion_db": 0.10,
    "splitters": {"1x2": 3.7, "1x4": 7.1, "1x8": 10.5, "1x16": 13.7, "1x32": 17.1},
    "tx_default_dbm": 5.0,
}

# limites de sanidade de cada valor (dB, dB/km, dBm)
_RANGES = {"fiber_db_km": (0.0, 2.0), "fusion_db": (0.0, 2.0), "tx_default_dbm": (-10.0, 15.0)}
_SPLITTER_RANGE = (0.0, 30.0)


def _num(value: Any, default: float, lo: float, hi: float) -> float:
    try:
        v = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default
    return v if lo <= v <= hi else default


def parse_optical_budget(value: Any) -> dict[str, Any]:
    """Normaliza o orçamento vindo da base, do .env (JSON) ou do ecrã: valores fora do intervalo
    ou ilegíveis voltam ao padrão — nunca quebra o rastreamento."""
    if isinstance(value, str):
        try:
            value = json.loads(value) if value.strip() else {}
        except ValueError:
            value = {}
    if not isinstance(value, dict):
        value = {}
    out: dict[str, Any] = {
        key: _num(value.get(key), DEFAULT_OPTICAL_BUDGET[key], *_RANGES[key]) for key in _RANGES
    }
    raw = value.get("splitters") if isinstance(value.get("splitters"), dict) else {}
    out["splitters"] = {
        r: _num(raw.get(r), DEFAULT_OPTICAL_BUDGET["splitters"][r], *_SPLITTER_RANGE)
        for r in SPLITTER_RATIOS
    }
    return {
        "fiber_db_km": out["fiber_db_km"],
        "fusion_db": out["fusion_db"],
        "splitters": out["splitters"],
        "tx_default_dbm": out["tx_default_dbm"],
    }
