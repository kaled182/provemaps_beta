"""Resumo de portas por dispositivo para os cards do modal de Site (EV-0111).

Mesmos critérios do modal de Dispositivo (``frontend/src/utils/devicePorts.js``):
porta «em uso» = tem leitura óptica ou cabo ligado; leitura com mais de
``OPTICAL_STALE_AFTER_SECONDS`` é velha e não entra no pior RX; limiares da
configuração (os mesmos que os cards das portas usam).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from django.utils import timezone

from inventory.domain.optical import is_plausible_dbm
from inventory.domain.port_cable import annotate_connected_cable
from inventory.models import Port

from .fibers import OPTICAL_STALE_AFTER_SECONDS, _resolve_port_thresholds


def _level(rx: float, warning: float | None, critical: float | None) -> str:
    if critical is not None and rx <= critical:
        return "critical"
    if warning is not None and rx <= warning:
        return "warning"
    return "normal"


def ports_summaries(device_ids: Iterable[int], now: datetime | None = None) -> dict[str, Any]:
    """``{"devices": {id: {ports_total, ports_in_use, worst_rx_dbm, worst_rx_level, stale_readings}}}``.

    Uma consulta para todos os ids (com a subconsulta do cabo ligado). Dispositivo sem
    portas no inventário não aparece — o card mostra «—», não «0 portas».
    """
    now = now or timezone.now()
    th = _resolve_port_thresholds(None)
    warning, critical = th["warning"], th["critical"]
    rows = (
        annotate_connected_cable(Port.objects.filter(device_id__in=list(device_ids)))
        .values_list(
            "device_id",
            "last_rx_power",
            "last_tx_power",
            "last_optical_check",
            "connected_cable_id",
        )
        .order_by()
    )
    out: dict[str, dict[str, Any]] = {}
    for device_id, rx, tx, checked, cable_id in rows:
        item = out.setdefault(
            str(device_id),
            {
                "ports_total": 0,
                "ports_in_use": 0,
                "worst_rx_dbm": None,
                "worst_rx_level": None,
                "stale_readings": 0,
            },
        )
        item["ports_total"] += 1
        has_reading = rx is not None or tx is not None
        if has_reading or cable_id:
            item["ports_in_use"] += 1
        if not has_reading:
            continue
        if checked is None or (now - checked).total_seconds() > OPTICAL_STALE_AFTER_SECONDS:
            item["stale_readings"] += 1
            continue
        if rx is None or not is_plausible_dbm(float(rx)):
            continue
        value = float(rx)
        if item["worst_rx_dbm"] is None or value < item["worst_rx_dbm"]:
            item["worst_rx_dbm"] = round(value, 2)
            item["worst_rx_level"] = _level(value, warning, critical)
    return {"devices": out, "thresholds": {"warning": warning, "critical": critical}}
