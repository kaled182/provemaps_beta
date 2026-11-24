"""Monitoramento de Switches (EV-0115): estado vivo por interface, lido do Zabbix a pedido.

Sem tarefa Celery nem tabela: 11 switches com ~420 itens cada são um ``item.get`` por switch (em
paralelo) e o resultado fica 60 s em cache — o que a tela pede a cada atualização. Não há
histórico de estados a guardar (os gráficos vêm do Zabbix pelo inventário).

Quem é switch: ``Device`` com host Zabbix e «switch» e «huawei» no nome (o inventário não
tem fabricante/modelo preenchidos — mesmo critério por nome das OLT no GPON). Os Ubiquiti
usam outro template e ficam de fora até o EV-0117.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from integrations.zabbix.zabbix_service import zabbix_request
from inventory.domain.port_cable import annotate_connected_cable
from inventory.models import Device, Port
from setup_app.services import runtime_settings

from .domain import parsers

OVERVIEW_CACHE_KEY = "switches:overview:v1"
OVERVIEW_CACHE_SECONDS = 60
VENDOR_HUAWEI = "huawei"
MAX_WORKERS = 6


class ZabbixUnavailable(Exception):
    """O Zabbix não respondeu (circuito aberto, rede, credenciais)."""


def switch_devices() -> list[Device]:
    return list(
        Device.objects.select_related("site")
        .filter(name__icontains="switch")
        .filter(name__icontains="huawei")
        .exclude(Q(zabbix_hostid__isnull=True) | Q(zabbix_hostid=""))
        .order_by("name")
    )


def thresholds() -> dict[str, float]:
    config = runtime_settings.get_runtime_config()
    warning = float(getattr(config, "backbone_rx_warning_threshold", -20.0))
    critical = float(getattr(config, "backbone_rx_critical_threshold", -24.0))
    if warning < critical:
        warning, critical = critical, warning
    return {
        "warning": warning,
        "critical": critical,
        "utilization_pct": parsers.UTILIZATION_WARNING_PCT,
    }


def _fetch(hostid: str) -> list[Mapping[str, Any]]:
    raw = zabbix_request(
        "item.get",
        {
            "hostids": [hostid],
            "output": parsers.ITEM_OUTPUT,
            "search": {"key_": parsers.SEARCH_KEYS},
            "searchByAny": True,
            "startSearch": True,
            "filter": {"status": "0"},
        },
    )
    if raw is None:
        raise ZabbixUnavailable(f"item.get sem resposta para o host {hostid}")
    return [i for i in raw if isinstance(i, Mapping)]


def _iso(ts: float | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=UTC).isoformat().replace("+00:00", "Z")


def _inventory_ports(device_ids: list[int]) -> dict[tuple[int, str], dict[str, Any]]:
    rows = annotate_connected_cable(Port.objects.filter(device_id__in=device_ids)).values(
        "id", "device_id", "name", "connected_cable_id", "connected_cable_name"
    )
    return {(r["device_id"], r["name"]): r for r in rows}


def _switch_status(ping: int | None) -> str:
    if ping == 1:
        return "online"
    if ping == 0:
        return "offline"
    return "unknown"


def _build(now: datetime) -> dict[str, Any]:
    th = thresholds()
    devices = switch_devices()
    now_ts = now.timestamp()
    results: dict[int, list[Mapping[str, Any]] | Exception] = {}
    if devices:
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(devices))) as pool:
            futures = {d.pk: pool.submit(_fetch, str(d.zabbix_hostid)) for d in devices}
            for pk, future in futures.items():
                try:
                    results[pk] = future.result()
                except Exception as exc:  # um switch falhado não derruba a tela
                    results[pk] = exc
    failures = [r for r in results.values() if isinstance(r, Exception)]
    zabbix_ok = not devices or len(failures) < len(devices)
    inventory = _inventory_ports([d.pk for d in devices])

    switches: list[dict[str, Any]] = []
    ports: list[dict[str, Any]] = []
    for device in devices:
        result = results.get(device.pk)
        collection_ok = not isinstance(result, Exception)
        parsed = (
            parsers.parse_items(result, now_ts)
            if collection_ok and result is not None
            else {"device": {}, "interfaces": {}}
        )
        dev = parsed["device"]
        mine: list[dict[str, Any]] = []
        for ifname in sorted(parsed["interfaces"], key=parsers.ifname_sort_key):
            entry = parsed["interfaces"][ifname]
            inv = inventory.get((device.pk, ifname)) or {}
            cable_id = inv.get("connected_cable_id")
            cls = parsers.classify_port(
                entry,
                ifname,
                warning=th["warning"],
                critical=th["critical"],
                has_cable=bool(cable_id),
            )
            kind = parsers.port_kind(ifname)
            mine.append(
                {
                    "device_id": device.pk,
                    "switch_name": device.name,
                    "name": ifname,
                    "description": entry["description"] or None,
                    "kind": kind,
                    "speed_mbps": entry["speed_mbps"] or None,
                    "speed_label": parsers.speed_label(entry["speed_mbps"], ifname),
                    "admin": cls["admin"],
                    "oper": cls["oper"],
                    "in_use": cls["in_use"],
                    "state": cls["state"],
                    "reasons": cls["reasons"],
                    "rx_dbm": cls["rx_dbm"],
                    "tx_dbm": entry["tx_dbm"],
                    "los": cls["los"],
                    "in_bps": entry["in_bps"],
                    "out_bps": entry["out_bps"],
                    "utilization_pct": cls["utilization_pct"],
                    "in_errors": entry["in_errors"],
                    "out_errors": entry["out_errors"],
                    "uptime_s": cls["uptime_s"],
                    "port_id": inv.get("id"),
                    "cable_id": cable_id,
                    "cable_name": inv.get("connected_cable_name"),
                    "severity_rank": cls["severity_rank"],
                }
            )
        data_ports = [p for p in mine if p["kind"] != "mgmt"]
        rx_values = [p["rx_dbm"] for p in data_ports if p["rx_dbm"] is not None]
        switches.append(
            {
                "device_id": device.pk,
                "name": device.name,
                "vendor": VENDOR_HUAWEI,
                "model": dev.get("model"),
                "ip": device.primary_ip or None,
                "site_id": device.site_id,
                "site_name": device.site.display_name if device.site_id else None,
                "status": _switch_status(dev.get("ping")),
                "collection_ok": collection_ok and bool(parsed["interfaces"]),
                "cpu_pct": dev.get("cpu_pct"),
                "temperature_c": dev.get("temperature_c"),
                "uptime_s": dev.get("uptime_s"),
                "ports_total": len(data_ports),
                "ports_up": sum(1 for p in data_ports if p["oper"] == "up"),
                "ports_in_use": sum(1 for p in data_ports if p["in_use"]),
                "ports_down": sum(1 for p in data_ports if p["state"] == "down"),
                "signal_warning": sum(1 for p in data_ports if "rx_warning" in p["reasons"]),
                "signal_critical": sum(1 for p in data_ports if "rx_critical" in p["reasons"]),
                "high_utilization": sum(1 for p in data_ports if "utilization" in p["reasons"]),
                "worst_rx_dbm": min(rx_values) if rx_values else None,
                "last_clock": _iso(dev.get("last_clock")),
            }
        )
        ports.extend(mine)

    def hottest(field: str) -> dict[str, Any] | None:
        candidates = [s for s in switches if s[field] is not None]
        if not candidates:
            return None
        top = max(candidates, key=lambda s: s[field])
        return {"device_id": top["device_id"], "name": top["name"], "value": top[field]}

    data_ports_all = [p for p in ports if p["kind"] != "mgmt"]
    totals = {
        "switches": len(switches),
        "switches_online": sum(1 for s in switches if s["status"] == "online"),
        "switches_offline": sum(1 for s in switches if s["status"] == "offline"),
        "switches_unknown": sum(1 for s in switches if s["status"] == "unknown"),
        "ports_monitored": len(data_ports_all),
        "ports_up": sum(1 for p in data_ports_all if p["oper"] == "up"),
        "ports_in_use": sum(1 for p in data_ports_all if p["in_use"]),
        "ports_free": sum(1 for p in data_ports_all if p["state"] == "free"),
        "ports_down": sum(1 for p in data_ports_all if p["state"] == "down"),
        "signal_warning": sum(s["signal_warning"] for s in switches),
        "signal_critical": sum(s["signal_critical"] for s in switches),
        "high_utilization": sum(s["high_utilization"] for s in switches),
        "hottest": hottest("temperature_c"),
        "busiest_cpu": hottest("cpu_pct"),
    }
    return {
        "collected_at": _iso(now_ts),
        "zabbix_ok": zabbix_ok,
        "zabbix_error": (str(failures[0]) if failures else None) if not zabbix_ok else None,
        "thresholds": th,
        "totals": totals,
        "switches": switches,
        "ports": ports,
    }


def switches_overview(now: datetime | None = None, *, refresh: bool = False) -> dict[str, Any]:
    """Payload de ``GET /api/v1/monitoring/switches/`` (ordem das chaves fixa), em cache 60 s.

    Com o Zabbix fora em todos os switches não se guarda em cache: o próximo pedido tenta de novo.
    """
    if not refresh and now is None:
        cached = cache.get(OVERVIEW_CACHE_KEY)
        if cached is not None:
            return cached
    started = time.monotonic()
    payload = _build(now or timezone.now())
    payload["duration_ms"] = int((time.monotonic() - started) * 1000)
    if payload["zabbix_ok"]:
        cache.set(OVERVIEW_CACHE_KEY, payload, OVERVIEW_CACHE_SECONDS)
    return payload
