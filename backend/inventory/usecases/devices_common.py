# ruff: noqa: E501
"""Tipos, exceções e utilitários partilhados pelos usecases de dispositivos.

Saiu de `inventory/usecases/devices.py` em EV-0017f. `ZABBIX_REQUEST` é o único ponto de
chamada ao gateway Zabbix destes usecases (e o alvo a simular nos testes); os módulos irmãos
chamam-no como `common.ZABBIX_REQUEST(...)` para que o patch num só sítio valha para todos.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, TypedDict, cast

from integrations.zabbix.zabbix_service import zabbix_request
from inventory.models import Device, Port, Site

ZABBIX_REQUEST = zabbix_request


class InventoryUseCaseError(Exception):
    """Generic error raised by inventory use cases."""


class InventoryValidationError(InventoryUseCaseError):
    """Input validation error."""


class InventoryNotFound(InventoryUseCaseError):
    """Requested resource not found."""


class HostItem(TypedDict, total=False):
    itemid: str
    key_: str
    name: str
    interfaceid: str
    lastvalue: str
    units: str
    snmpindex: str
    value_type: str
    _role: str | None


HostItemList = list[HostItem]


class TrafficPoint(TypedDict):
    timestamp: int
    value: float


class TrafficChannel(TypedDict):
    history: list[TrafficPoint]
    unit: str
    configured: bool


TrafficData = TypedDict(
    "TrafficData",
    {
        "port_id": int,
        "port_name": str,
        "device_name": str,
        "in": TrafficChannel,
        "out": TrafficChannel,
        "period": str,
        "period_seconds": int,
        "since": int | None,
        "incremental": bool,
        "generated_at": int,
        "time_from": int,
        "history_limit": int,
        "bucket_seconds": int,
    },
    total=False,
)


def _new_str_set() -> set[str]:
    return set()


@dataclass
class PortRecord:
    port: Port
    created: bool
    defaults: dict[str, str]
    updated_fields: set[str] = field(default_factory=_new_str_set)
    optical_snapshot: dict[str, Any] | None = None


@dataclass
class _PortEntry:
    port: Port
    record: PortRecord
    lower: str
    normalized: str
    trimmed: str
    normalized_trimmed: str


class PortLike(Protocol):
    id: int
    name: str
    device_id: int
    device: Device
    zabbix_item_key: str | None
    zabbix_itemid: str | None
    zabbix_interfaceid: str | None
    zabbix_item_id_traffic_in: str | None
    zabbix_item_id_traffic_out: str | None
    rx_power_item_key: str | None
    tx_power_item_key: str | None
    notes: str

    def refresh_from_db(self) -> None: ...


class DeviceLike(Protocol):
    id: int
    name: str
    zabbix_hostid: str | None
    site: Site
    device_icon: Any

    def save(self, *, update_fields: Iterable[str]) -> None: ...


class SiteLike(Protocol):
    id: int
    name: str
    city: str
    latitude: Decimal | None
    longitude: Decimal | None
    devices: Any


def _port_map_key(port: Port) -> tuple[int, str]:
    """Return the (device_id, lower_port_name) tuple for mapping operations."""
    port_like = cast(PortLike, port)
    return port_like.device_id, port_like.name.lower()


def _coerce_host_items(raw_items: Any) -> HostItemList:
    if not isinstance(raw_items, list):
        return []
    result: HostItemList = []
    entries = cast(Sequence[object], raw_items)
    for entry_obj in entries:
        if isinstance(entry_obj, dict):
            result.append(cast(HostItem, entry_obj))
    return result


def _resolve_host_inventory(host: Mapping[str, Any]) -> dict[str, Any]:
    """Return the host inventory record or an empty dict when absent."""

    inventory = host.get("inventory")
    if isinstance(inventory, dict):
        return cast(dict[str, Any], inventory)
    return {}


def _coerce_dict_list(raw_items: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    result: list[dict[str, Any]] = []
    entries = cast(Sequence[object], raw_items)
    for entry in entries:
        if isinstance(entry, dict):
            result.append(cast(dict[str, Any], entry))
    return result


def _normalize_identifier(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _extract_key_tokens(key: str | None) -> list[str]:
    if not key or "[" not in key or "]" not in key:
        return []
    try:
        start = key.index("[") + 1
        end = key.rindex("]")
    except ValueError:
        return []
    inside = key[start:end]
    tokens: list[str] = []
    for part in inside.split(","):
        token = part.strip().strip('"').strip("'")
        if token:
            tokens.append(token)
    return tokens


def _identify_item_role(key_lower: str, name_lower: str) -> str | None:
    if not key_lower:
        return None

    if "ifoperstatus" in key_lower:
        return "primary_oper"
    if "lastdowntime" in key_lower:
        return "legacy_lastdown"

    traffic_in_markers = ("net.if.in", "ifhcin", "ifinoctets")
    traffic_out_markers = ("net.if.out", "ifhcout", "ifoutoctets")
    if any(marker in key_lower for marker in traffic_in_markers):
        return "traffic_in"
    if any(marker in key_lower for marker in traffic_out_markers):
        return "traffic_out"

    is_threshold = any(word in key_lower for word in ("threshold", "warn", "alarm", "limit"))

    rx_markers = (
        "hwentityopticallanerxpower",
        "rxpower",
        "opticalrx",
        "opticrx",
        "rx_dbm",
    )
    tx_markers = (
        "hwentityopticallanetxpower",
        "txpower",
        "opticaltx",
        "optictx",
        "tx_dbm",
    )

    if not is_threshold:
        if any(marker in key_lower for marker in tx_markers) or (
            "power" in key_lower and "tx" in key_lower and "rx" not in key_lower
        ):
            return "optical_tx"
        if any(marker in key_lower for marker in rx_markers) or (
            "power" in key_lower and "rx" in key_lower and "tx" not in key_lower
        ):
            return "optical_rx"

    return None


def _apply_port_updates(port: Port, updates: dict[str, Any], updated_fields: set[str]) -> None:
    if not updates:
        return
    Port.objects.filter(pk=port.pk).update(**updates)
    for attr, value in updates.items():
        setattr(port, attr, value)
        updated_fields.add(attr)
