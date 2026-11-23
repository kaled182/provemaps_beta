from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import Any, cast

from integrations.zabbix.zabbix_service import zabbix_request
from inventory.models import Port
from inventory.services.fiber_status import fetch_interface_status_advanced

logger = logging.getLogger(__name__)

__all__ = [
    "_safe_float",
    "_fetch_item_value",
    "_score_optical_candidate",
    "_discover_optical_keys_by_portname",
    "_fetch_port_optical_snapshot",
    "fetch_ports_optical_snapshots",
    "fetch_port_optical_snapshot",
]


ItemValue = tuple[float | None, Any | None, dict[str, Any] | None]
ValueCache = dict[str, ItemValue]
PortContext = tuple[Port, str, str, dict[str, Any], dict[str, Any]]


# EV-0063: potência óptica real de transceptores fica bem dentro desta gama; um valor
# fora dela (ex.: 2.2e9 de um contador ifHCInOctets, 380 de um item em outra unidade)
# não é dBm e não pode ser gravado como tal.
OPTICAL_DBM_MIN = -60.0
OPTICAL_DBM_MAX = 15.0


def is_plausible_dbm(value: float | None) -> bool:
    return value is not None and OPTICAL_DBM_MIN <= float(value) <= OPTICAL_DBM_MAX


def _value_cache_key(hostid: str | int | None, key: str | None) -> str:
    """Return a stable cache key for `(hostid, key)` lookups."""
    return f"{hostid or ''}::{key or ''}"


def _safe_float(value: Any) -> float | None:
    """Convert values to float, returning None when conversion fails."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fetch_item_value(
    hostid: Any,
    key: str | None,
    *,
    value_cache: ValueCache | None = None,
) -> ItemValue:
    """Return ``(float_value, raw_value, item_dict)`` for a Zabbix item."""
    if not (hostid and key):
        return None, None, None

    cache_key = _value_cache_key(hostid, key)
    if value_cache is not None and cache_key in value_cache:
        return value_cache[cache_key]

    params: dict[str, Any] = {
        "output": ["itemid", "lastvalue", "value_type", "units"],
        "hostids": [str(hostid)],
        "filter": {"key_": key},
        "limit": 1,
    }
    items = cast(
        list[dict[str, Any]],
        zabbix_request("item.get", params) or [],
    )
    if not items:
        # EV-0063: sem procura «em todos os hosts» — devolvia o item de outro
        # equipamento com a mesma chave.
        return None, None, None

    item = items[0]
    raw = item.get("lastvalue")
    value = _safe_float(raw)
    if value is None:
        try:
            history = cast(
                list[dict[str, Any]],
                zabbix_request(
                    "history.get",
                    {
                        "itemids": [str(item["itemid"])],
                        "history": int(item.get("value_type", 0)),
                        "sortfield": "clock",
                        "sortorder": "DESC",
                        "limit": 1,
                    },
                )
                or [],
            )
        except Exception:  # pragma: no cover - defensive fallback
            history = []
        if history:
            raw = history[0].get("value")
            value = _safe_float(raw)
    result: ItemValue = (value, raw, item)
    if value_cache is not None:
        value_cache[cache_key] = result
    return result


def _score_optical_candidate(item: dict[str, Any], kind: str) -> int:
    """Apply a basic heuristic to score RX/TX optical power items."""
    text = " ".join(
        [
            (item.get("key_") or "").lower(),
            (item.get("name") or "").lower(),
        ]
    )
    units = (item.get("units") or "").lower()
    score = 0

    if "power" in text:
        score += 2
    if "optical" in text or "fiber" in text:
        score += 1
    if "dbm" in text or "dbm" in units:
        score += 3

    if kind == "rx":
        if any(token in text for token in ("rx", "receive", "input")):
            score += 2
        if "tx" in text:
            score -= 1
    else:
        if any(token in text for token in ("tx", "transmit", "output")):
            score += 2
        if "rx" in text:
            score -= 1

    if any(word in text for word in ("threshold", "alarm", "bias", "temperature", "fault")):
        score -= 3
    return score


def _discover_optical_keys_by_portname(
    hostid: Any,
    port_name: str | None,
    cache: dict[tuple[str, str | None], dict[str, str | None]] | None = None,
) -> dict[str, str | None]:
    """Discover optical power items using the port name as fallback.

    This is used when ``interfaceid`` is missing. Returns
    ``{"rx": key, "tx": key}`` with ``None`` when nothing is found.
    """
    cache_key: tuple[str, str | None] = (str(hostid), port_name)
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    if not (hostid and port_name):
        result: dict[str, str | None] = {"rx": None, "tx": None}
        if cache is not None:
            cache[cache_key] = result
        return result

    search_terms = [port_name]
    for sep in ("/", " ", ":"):
        if sep in port_name:
            compact = port_name.replace(sep, "")
            if compact and compact not in search_terms:
                search_terms.append(compact)

    candidates: list[dict[str, Any]] = []
    for term in search_terms:
        query: dict[str, Any] = {
            "output": ["itemid", "key_", "name", "lastvalue", "units"],
            "hostids": [str(hostid)],
            "filter": {"status": "0"},
            "search": {"key_": term},
            "searchByAny": True,
            "limit": 200,
        }
        items = cast(
            list[dict[str, Any]],
            zabbix_request("item.get", query) or [],
        )
        candidates.extend(items)
        if items:
            break

    if not candidates:
        for term in search_terms:
            query = {
                "output": ["itemid", "key_", "name", "lastvalue", "units"],
                "hostids": [str(hostid)],
                "filter": {"status": "0"},
                "search": {"name": term},
                "searchByAny": True,
                "limit": 200,
            }
            items = cast(
                list[dict[str, Any]],
                zabbix_request("item.get", query) or [],
            )
            candidates.extend(items)
            if items:
                break

    rx_key = tx_key = None
    best_rx = best_tx = -999

    for item in candidates:
        key = item.get("key_")
        if not key:
            continue
        rx_score = _score_optical_candidate(item, "rx")
        tx_score = _score_optical_candidate(item, "tx")
        if rx_score > best_rx:
            best_rx = rx_score
            rx_key = key if rx_score > 0 else rx_key
        if tx_score > best_tx:
            best_tx = tx_score
            tx_key = key if tx_score > 0 else tx_key

    result: dict[str, str | None] = {"rx": rx_key, "tx": tx_key}
    if cache is not None:
        cache[cache_key] = result
    return result


def _resolve_optical_keys(
    port: Port,
    hostid: str,
    discovery_cache: dict[tuple[str, str | None], dict[str, str | None]],
    *,
    include_status_meta: bool,
    persist_keys: bool,
) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    """Resolve RX/TX keys and optional status metadata for a port."""

    rx_key = (port.rx_power_item_key or "").strip()
    tx_key = (port.tx_power_item_key or "").strip()
    interfaceid = (port.zabbix_interfaceid or "").strip()

    status_meta: dict[str, Any] = {}
    if include_status_meta:
        try:
            _, status_meta = fetch_interface_status_advanced(
                hostid,
                primary_item_key=(port.zabbix_item_key or "").strip() or None,
                interfaceid=interfaceid or None,
                rx_key=rx_key or None,
                tx_key=tx_key or None,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug(
                "Failed to fetch optical status for port %s: %s",
                getattr(port, "pk", None),
                exc,
            )
            status_meta = {}

    original_rx_key = rx_key
    original_tx_key = tx_key

    for meta_key in ("rx_key", "rx_key_generic"):
        candidate = status_meta.get(meta_key)
        if candidate:
            rx_key = candidate.strip()
            break
    for meta_key in ("tx_key", "tx_key_generic"):
        candidate = status_meta.get(meta_key)
        if candidate:
            tx_key = candidate.strip()
            break

    if (not rx_key or not tx_key) and port.name:
        discovered = _discover_optical_keys_by_portname(
            hostid,
            port.name,
            cache=discovery_cache,
        )
        rx_key = rx_key or (discovered.get("rx") or "")
        tx_key = tx_key or (discovered.get("tx") or "")
        if discovered.get("rx") or discovered.get("tx"):
            status_meta.setdefault("auto_discovery", "port_name")

    updates: dict[str, Any] = {}
    if rx_key and rx_key != original_rx_key:
        updates["rx_power_item_key"] = rx_key
    if tx_key and tx_key != original_tx_key:
        updates["tx_power_item_key"] = tx_key

    if persist_keys and updates:
        Port.objects.filter(pk=port.pk).update(**updates)
        for field, value in updates.items():
            setattr(port, field, value)

    return rx_key, tx_key, status_meta, updates


def _bulk_fetch_item_values(hostid: str, keys: Iterable[str]) -> ValueCache:
    """Fetch multiple item values in a single request when possible."""

    unique_keys: list[str] = sorted({key.strip() for key in keys if key})
    if not unique_keys:
        return {}

    params: dict[str, Any] = {
        "output": ["itemid", "key_", "lastvalue", "value_type", "units"],
        "hostids": [hostid],
        "filter": {"status": "0", "key_": unique_keys},
        "limit": max(len(unique_keys), 1),
    }

    try:
        items = cast(
            list[dict[str, Any]],
            zabbix_request("item.get", params) or [],
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug(
            "Bulk item.get failed for host %s: %s",
            hostid,
            exc,
        )
        items = []

    cache: ValueCache = {}
    missing_keys: set[str] = set(unique_keys)
    history_candidates: dict[int, list[dict[str, Any]]] = {}

    for item in items:
        key_value = (item.get("key_") or "").strip()
        if not key_value:
            continue
        cache_key = _value_cache_key(hostid, key_value)
        raw = item.get("lastvalue")
        value = _safe_float(raw)
        cache[cache_key] = (value, raw, item)
        missing_keys.discard(key_value)
        if value is None:
            try:
                value_type = int(item.get("value_type", 0))
            except (TypeError, ValueError):
                continue
            history_candidates.setdefault(value_type, []).append(item)

    for value_type, typed_items in history_candidates.items():
        itemids = [str(it.get("itemid")) for it in typed_items if it.get("itemid")]
        if not itemids:
            continue
        try:
            history = cast(
                list[dict[str, Any]],
                zabbix_request(
                    "history.get",
                    {
                        "itemids": itemids,
                        "history": value_type,
                        "sortfield": "clock",
                        "sortorder": "DESC",
                        "limit": len(itemids),
                    },
                )
                or [],
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug(
                "Bulk history.get failed for host %s: %s",
                hostid,
                exc,
            )
            continue

        history_map = {str(entry.get("itemid")): entry.get("value") for entry in history}
        for item in typed_items:
            key_value = (item.get("key_") or "").strip()
            if not key_value:
                continue
            cache_key = _value_cache_key(hostid, key_value)
            itemid = str(item.get("itemid") or "")
            raw = history_map.get(itemid)
            value = _safe_float(raw)
            cache[cache_key] = (value, raw, item)

    # EV-0063: uma chave que não veio no item.get do host (filtrado por hostid, chave
    # e item ativo) não existe/está desativada NESTE equipamento — fica sem leitura.
    # Antes havia um fallback chave a chave (261 chamadas por coleta), que ainda
    # repetia a procura SEM hostid e podia atribuir à porta o valor de outro host.
    for key in missing_keys:
        cache[_value_cache_key(hostid, key)] = (None, None, None)
    if missing_keys:
        logger.debug(
            "Host %s: %d chave(s) óptica(s) sem item ativo: %s",
            hostid,
            len(missing_keys),
            sorted(missing_keys)[:10],
        )

    return cache


def fetch_port_optical_snapshot(
    port: Port,
    *,
    discovery_cache: dict[Any, Any] | None | None = None,
    persist_keys: bool = True,
    include_status_meta: bool = True,
    value_cache: ValueCache | None = None,
) -> dict[str, Any]:
    """Public wrapper for ``_fetch_port_optical_snapshot``.

    Exposed to avoid importing the private helper from downstream modules while
    keeping the original implementation intact. Delegates all parameters to the
    internal function.
    """

    return _fetch_port_optical_snapshot(
        port,
        discovery_cache=discovery_cache,
        persist_keys=persist_keys,
        include_status_meta=include_status_meta,
        value_cache=value_cache,
    )


def _fetch_port_optical_snapshot(
    port: Port | None,
    discovery_cache: dict[tuple[str, str | None], dict[str, str | None]] | None = None,
    persist_keys: bool = True,
    *,
    include_status_meta: bool = True,
    value_cache: ValueCache | None = None,
) -> dict[str, Any]:
    """Load an optical power (RX/TX) snapshot for a port.

    - Prefer item keys already configured on the model, otherwise fall back to
      automatic discovery.
    - Persist newly discovered keys when ``persist_keys`` is ``True``.

    Returns a mapping with numeric values (dBm) plus metadata.
    """
    if port is None:
        return {"rx_dbm": None, "tx_dbm": None, "rx_raw": None, "tx_raw": None}

    device = getattr(port, "device", None)
    if device is None:
        return {"rx_dbm": None, "tx_dbm": None, "rx_raw": None, "tx_raw": None}

    hostid = (getattr(device, "zabbix_hostid", "") or "").strip()
    if not hostid:
        return {"rx_dbm": None, "tx_dbm": None, "rx_raw": None, "tx_raw": None}

    discovery_cache = discovery_cache if discovery_cache is not None else {}

    rx_key, tx_key, status_meta, updates = _resolve_optical_keys(
        port,
        hostid,
        discovery_cache,
        include_status_meta=include_status_meta,
        persist_keys=persist_keys,
    )

    rx_value = rx_raw = None
    tx_value = tx_raw = None
    if rx_key:
        rx_value, rx_raw, _ = _fetch_item_value(
            hostid,
            rx_key,
            value_cache=value_cache,
        )
    if tx_key:
        tx_value, tx_raw, _ = _fetch_item_value(
            hostid,
            tx_key,
            value_cache=value_cache,
        )

    result: dict[str, Any] = {
        "rx_dbm": rx_value,
        "tx_dbm": tx_value,
        "rx_raw": rx_raw,
        "tx_raw": tx_raw,
        "rx_key": rx_key or None,
        "tx_key": tx_key or None,
    }
    if status_meta:
        result["meta"] = status_meta
    if updates:
        result["keys_updated"] = True
    return result


def fetch_ports_optical_snapshots(
    ports: Sequence[Port],
    *,
    discovery_cache: dict[Any, Any] | None | None = None,
    persist_keys: bool = True,
    include_status_meta: bool = True,
) -> dict[int, dict[str, Any]]:
    """Fetch optical snapshots for a sequence of ports with batching."""

    if discovery_cache is None:
        discovery_cache = {}

    grouped: dict[str, list[Port]] = {}
    results: dict[int, dict[str, Any]] = {}

    for port in ports:
        device = getattr(port, "device", None)
        hostid = (getattr(device, "zabbix_hostid", "") or "").strip()
        if not hostid:
            port_pk_any = getattr(port, "pk", None)
            if port_pk_any is None:
                continue
            port_pk = cast(int, port_pk_any)
            results[port_pk] = {
                "rx_dbm": None,
                "tx_dbm": None,
                "rx_raw": None,
                "tx_raw": None,
                "rx_key": None,
                "tx_key": None,
            }
            continue
        grouped.setdefault(hostid, []).append(port)

    for hostid, host_ports in grouped.items():
        contexts: list[PortContext] = []
        bulk_keys: set[str] = set()

        for port in host_ports:
            rx_key, tx_key, status_meta, updates = _resolve_optical_keys(
                port,
                hostid,
                discovery_cache,
                include_status_meta=include_status_meta,
                persist_keys=persist_keys,
            )
            contexts.append((port, rx_key, tx_key, status_meta, updates))
            if rx_key:
                bulk_keys.add(rx_key)
            if tx_key:
                bulk_keys.add(tx_key)

        value_cache = _bulk_fetch_item_values(hostid, bulk_keys)

        for port, rx_key, tx_key, status_meta, updates in contexts:
            rx_value = rx_raw = None
            tx_value = tx_raw = None
            if rx_key:
                rx_value, rx_raw, _ = _fetch_item_value(
                    hostid,
                    rx_key,
                    value_cache=value_cache,
                )
            if tx_key:
                tx_value, tx_raw, _ = _fetch_item_value(
                    hostid,
                    tx_key,
                    value_cache=value_cache,
                )

            payload: dict[str, Any] = {
                "rx_dbm": rx_value,
                "tx_dbm": tx_value,
                "rx_raw": rx_raw,
                "tx_raw": tx_raw,
                "rx_key": rx_key or None,
                "tx_key": tx_key or None,
            }
            if status_meta:
                payload["meta"] = status_meta
            if updates:
                payload["keys_updated"] = True

            port_pk_any = getattr(port, "pk", None)
            if port_pk_any is None:
                continue
            port_pk = cast(int, port_pk_any)
            results[port_pk] = payload

    return results
