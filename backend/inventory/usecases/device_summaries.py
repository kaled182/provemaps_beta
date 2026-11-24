"""Resumo de portas por dispositivo para os cards do modal de Site (EV-0111).

Mesmos critérios do modal de Dispositivo (``frontend/src/utils/devicePorts.js``):
porta «em uso» = tem leitura óptica ou cabo ligado; leitura com mais de
``OPTICAL_STALE_AFTER_SECONDS`` é velha e não entra no pior RX; limiares da
configuração (os mesmos que os cards das portas usam).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from django.shortcuts import get_object_or_404
from django.utils import timezone

from inventory.domain.optical import is_plausible_dbm
from inventory.domain.port_cable import annotate_connected_cable
from inventory.models import Device, Port

from . import devices_common as common
from .fibers import OPTICAL_STALE_AFTER_SECONDS, _resolve_port_thresholds

# EV-0112: temperatura do equipamento. Não há chave fixa por modelo (Huawei:
# sensor.temp.value[hwEntityTemperature.<idx>]; outros: device.temperature…) — procura-se
# por nome/chave e unidade em graus. 0 °C ou menos num equipamento ligado não é leitura
# (o item «device.temperature» dos Huawei devolve 0); acima de 150 °C também não.
TEMPERATURE_UNITS = {"C", "°C", "ºC", "degC"}
TEMPERATURE_MIN_C = 0.0
TEMPERATURE_MAX_C = 150.0
TEMPERATURE_STALE_SECONDS = 3600


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


def device_temperature(device_id: int, now: datetime | None = None) -> dict[str, Any]:
    """Temperatura mais alta entre os sensores do equipamento no Zabbix (EV-0112).

    ``temperature_c`` None com ``reason``: ``no_host`` (sem host Zabbix), ``no_item`` (o
    template não tem sensor), ``no_reading`` (sensores sem leitura válida/recente);
    ``zabbix_ok`` false quando o Zabbix não respondeu — nunca um valor inventado.
    """
    now = now or timezone.now()
    device = get_object_or_404(Device.objects.only("id", "zabbix_hostid"), pk=device_id)
    payload: dict[str, Any] = {
        "device_id": device.pk,
        "temperature_c": None,
        "sensor": None,
        "sensors": 0,
        "at": None,
        "reason": None,
        "zabbix_ok": True,
    }
    hostid = str(device.zabbix_hostid or "").strip()
    if not hostid:
        payload["reason"] = "no_host"
        return payload
    raw = common.ZABBIX_REQUEST(
        "item.get",
        {
            "output": ["key_", "name", "units", "lastvalue", "lastclock"],
            "hostids": [hostid],
            "search": {"name": "emperat", "key_": "temp"},
            "searchByAny": True,
            "filter": {"status": "0"},
        },
    )
    if raw is None:
        payload["zabbix_ok"] = False
        return payload
    sensors = [
        i
        for i in raw
        if isinstance(i, dict) and str(i.get("units") or "").strip() in TEMPERATURE_UNITS
    ]
    payload["sensors"] = len(sensors)
    if not sensors:
        payload["reason"] = "no_item"
        return payload
    best: tuple[float, str, int] | None = None
    for item in sensors:
        try:
            value = float(item.get("lastvalue"))
            clock = int(item.get("lastclock") or 0)
        except (TypeError, ValueError):
            continue
        fresh = clock > 0 and now.timestamp() - clock <= TEMPERATURE_STALE_SECONDS
        if not fresh or not TEMPERATURE_MIN_C < value <= TEMPERATURE_MAX_C:
            continue
        if best is None or value > best[0]:
            best = (value, str(item.get("name") or item.get("key_") or ""), clock)
    if best is None:
        payload["reason"] = "no_reading"
        return payload
    payload["temperature_c"] = round(best[0], 1)
    payload["sensor"] = best[1]
    payload["at"] = datetime.fromtimestamp(best[2], tz=UTC).isoformat().replace("+00:00", "Z")
    return payload
