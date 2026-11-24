"""Saúde da coleta óptica (EV-0085).

Quais equipamentos apontam para um host Zabbix que já não existe e quais portas com chave
óptica estão sem leitura (e porquê). Tudo vem da base — o que a coleta de 60 s gravou em
``Port.last_*`` e ``Port.optical_problem`` — mais UM ``host.get`` pelo gateway para saber
que hosts ainda existem. Zabbix em baixo ≠ host inexistente: nesse caso
``devices_missing_host`` fica vazio e o total é ``None`` (desconhecido, não zero).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, cast

from django.db.models import Q
from django.utils import timezone

from integrations.zabbix.zabbix_service import zabbix_request
from inventory.models import Device, Port

logger = logging.getLogger(__name__)

STALE_HOURS_DEFAULT = 2
STALE_HOURS_MIN = 1
STALE_HOURS_MAX = 168

REASON_ITEM_PROBLEM = "item_problem"
REASON_NEVER = "never"
REASON_STALE = "stale"


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _dbm(value: Decimal | float | None) -> float | None:
    return None if value is None else float(value)


def _existing_hostids(hostids: list[str]) -> tuple[set[str] | None, str | None]:
    """Hosts que o Zabbix devolve; ``(None, erro)`` quando o Zabbix não responde."""
    if not hostids:
        return set(), None
    try:
        rows = cast(
            list[dict[str, Any]],
            zabbix_request("host.get", {"output": ["hostid"], "hostids": hostids}) or [],
        )
    except Exception as exc:
        logger.warning("collection_health: host.get falhou: %s", exc)
        return None, (str(exc) or exc.__class__.__name__)[:200]
    return {str(row.get("hostid")) for row in rows if row.get("hostid")}, None


def collection_health(
    *, stale_hours: int = STALE_HOURS_DEFAULT, now: datetime | None = None
) -> dict:
    """Estado da coleta óptica por equipamento e por porta (formato do contrato EV-0085)."""
    now = now or timezone.now()
    cutoff = now - timedelta(hours=stale_hours)

    devices = list(
        Device.objects.values("id", "name", "site__display_name", "zabbix_hostid").order_by(
            "name", "id"
        )
    )
    by_hostid: dict[str, list[dict[str, Any]]] = {}
    for dev in devices:
        hostid = (dev["zabbix_hostid"] or "").strip()
        if hostid:
            by_hostid.setdefault(hostid, []).append(dev)

    existing, zabbix_error = _existing_hostids(sorted(by_hostid))
    zabbix_ok = existing is not None
    missing_host: list[dict[str, Any]] = []
    if existing is not None:
        for hostid, devs in by_hostid.items():
            if hostid in existing:
                continue
            missing_host.extend(
                {
                    "device_id": d["id"],
                    "device_name": d["name"],
                    "site_name": d["site__display_name"],
                    "zabbix_hostid": hostid,
                }
                for d in devs
            )
        missing_host.sort(key=lambda d: (d["device_name"], d["device_id"]))

    # Uma consulta para todas as portas com chave; a agregação por equipamento é em memória.
    port_rows = (
        Port.objects.filter(
            (Q(rx_power_item_key__isnull=False) & ~Q(rx_power_item_key=""))
            | (Q(tx_power_item_key__isnull=False) & ~Q(tx_power_item_key=""))
        )
        .values(
            "id",
            "name",
            "device_id",
            "device__name",
            "device__site__display_name",
            "rx_power_item_key",
            "tx_power_item_key",
            "last_rx_power",
            "last_tx_power",
            "last_optical_check",
            "optical_problem",
        )
        .order_by("device__name", "name", "id")
    )

    per_device: dict[int, dict[str, Any]] = {}
    problem_ports: list[dict[str, Any]] = []
    ports_with_key = 0
    ports_reading = 0
    for row in port_rows:
        ports_with_key += 1
        agg = per_device.setdefault(
            row["device_id"],
            {
                "device_id": row["device_id"],
                "device_name": row["device__name"],
                "site_name": row["device__site__display_name"],
                "ports_with_key": 0,
                "ports_reading": 0,
            },
        )
        agg["ports_with_key"] += 1

        problem = (row["optical_problem"] or "").strip()
        checked = row["last_optical_check"]
        if problem:
            reason = REASON_ITEM_PROBLEM
        elif checked is None:
            reason = REASON_NEVER
        elif checked < cutoff:
            reason = REASON_STALE
        else:
            ports_reading += 1
            agg["ports_reading"] += 1
            continue

        problem_ports.append(
            {
                "port_id": row["id"],
                "port_name": row["name"],
                "device_id": row["device_id"],
                "device_name": row["device__name"],
                "rx_key": row["rx_power_item_key"] or None,
                "tx_key": row["tx_power_item_key"] or None,
                "last_rx_power": _dbm(row["last_rx_power"]),
                "last_tx_power": _dbm(row["last_tx_power"]),
                "last_optical_check": _iso(checked),
                "reason": reason,
                "problem": problem or None,
            }
        )

    without_readings = sorted(
        (agg for agg in per_device.values() if agg["ports_reading"] == 0),
        key=lambda d: (d["device_name"], d["device_id"]),
    )

    return {
        "generated_at": _iso(now),
        "stale_hours": stale_hours,
        "zabbix_ok": zabbix_ok,
        "zabbix_error": zabbix_error,
        "totals": {
            "devices": len(devices),
            "devices_missing_host": len(missing_host) if zabbix_ok else None,
            "devices_without_readings": len(without_readings),
            "ports_with_key": ports_with_key,
            "ports_reading": ports_reading,
            "ports_problem": len(problem_ports),
        },
        "devices_missing_host": missing_host,
        "devices_without_readings": without_readings,
        "ports": problem_ports,
    }
