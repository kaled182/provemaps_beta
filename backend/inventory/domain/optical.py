from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
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
    "is_plausible_dbm",
    "optical_item_problem",
    "optical_value_problem",
    "validate_optical_reading",
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


# EV-0082: os itens de ONU das OLT ZTE («OLT ZTE GPON», `onu.rx[<serial>,<slot>,<pon>,<onu>]`)
# e VSOL (`SinalRXS0P<pon>[GPON0/<pon>:<onu> - <onu>]`) usam valores-sentinela: 0 = ONU
# online sem leitura, -80 = ONU offline. Nessas chaves não são medidas. Fora delas, 0 dBm
# é potência real possível (TX de muitos transceptores) e grava-se.
OPTICAL_SENTINEL_KEY_PREFIXES = ("onu.rx[", "onu.tx[", "sinalrxs0p")
OPTICAL_SENTINEL_VALUES = frozenset({0.0, -80.0})


def optical_item_problem(item: Mapping[str, Any] | None) -> str | None:
    """Return why an ``item.get`` row is not a current reading (``None`` when it is).

    EV-0082: o Zabbix devolve ``lastvalue "0"`` em itens nunca coletados
    (``lastclock`` 0) e em itens «unsupported» (``state`` 1); usá-lo gravava 0,00 dBm
    como leitura fresca. Exige os campos ``state``/``lastclock``/``lastvalue`` no
    ``output`` do ``item.get`` — campo ausente conta como leitura inválida.
    """
    if not item:
        return "item inexistente"
    state = str(item.get("state", "")).strip()
    if state != "0":
        if state == "1":
            return "item unsupported no Zabbix"
        return f"estado do item desconhecido ({state or 'ausente'})"
    try:
        lastclock = int(str(item.get("lastclock") or "0").strip())
    except (TypeError, ValueError):
        lastclock = 0
    if lastclock <= 0:
        return "item sem coleta (lastclock 0)"
    raw = item.get("lastvalue")
    if raw is None or not str(raw).strip():
        return "lastvalue vazio"
    return None


def optical_value_problem(key: str | None, value: float | None) -> str | None:
    """Return why a numeric value is not an optical power in dBm (``None`` when it is)."""
    if value is None:
        return "valor não numérico"
    if not is_plausible_dbm(value):
        return f"{value:g} fora de {OPTICAL_DBM_MIN:g}…+{OPTICAL_DBM_MAX:g} dBm"
    key_lower = (key or "").strip().lower()
    if key_lower.startswith(OPTICAL_SENTINEL_KEY_PREFIXES) and (
        float(value) in OPTICAL_SENTINEL_VALUES
    ):
        return f"{value:g} é valor-sentinela de ONU sem leitura"
    return None


def validate_optical_reading(
    item: Mapping[str, Any] | None,
    value: float | None,
    key: str | None = None,
) -> tuple[float | None, str | None]:
    """Return ``(dbm, problem)`` for an item and its numeric value.

    ``(None, None)`` = não há item (nada a registar); ``(None, motivo)`` = há item
    mas o valor não é uma medida atual em dBm; ``(dbm, None)`` = leitura válida.
    Regra única da coleta (``fetch_ports_optical_snapshots``) e do estado do cabo
    (``services.fiber_status``).
    """
    if item is None:
        return None, None
    problem = optical_item_problem(item) or optical_value_problem(
        key or cast(str | None, item.get("key_")), value
    )
    if problem:
        return None, problem
    return float(cast(float, value)), None


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
        "output": ["itemid", "key_", "lastvalue", "lastclock", "state", "value_type", "units"],
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
    # EV-0082: item sem leitura atual (nunca coletado, unsupported) não vai ao histórico.
    if value is None and optical_item_problem(item) is None:
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

    # EV-0082: a descoberta pelo nome da porta (LIKE no Zabbix) só corre quando as chaves
    # descobertas são gravadas e revistas (descoberta de equipamentos, `persist_keys=True`).
    # Na coleta periódica (`persist_keys=False`) uma chave vazia é «sem leitura»: antes a
    # porta lia, a cada ciclo, um item escolhido por heurística — de outra ONU/interface —
    # e esse valor era gravado como medida (o EV-0081 esvazia chaves erradas de propósito).
    if persist_keys and (not rx_key or not tx_key) and port.name:
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
        "output": ["itemid", "key_", "lastvalue", "lastclock", "state", "value_type", "units"],
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
        # EV-0082: item sem leitura atual não vai ao histórico (o valor seria antigo).
        if value is None and optical_item_problem(item) is None:
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


def _read_optical_value(
    hostid: str,
    key: str,
    value_cache: ValueCache | None,
) -> tuple[float | None, Any | None, str | None]:
    """Return ``(dbm, raw, problem)`` for a port key — ``dbm`` só com leitura válida."""
    value, raw, item = _fetch_item_value(hostid, key, value_cache=value_cache)
    dbm, problem = validate_optical_reading(item, value, key)
    return dbm, raw, problem


def _optical_payload(
    rx: tuple[float | None, Any | None, str | None],
    tx: tuple[float | None, Any | None, str | None],
    rx_key: str,
    tx_key: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "rx_dbm": rx[0],
        "tx_dbm": tx[0],
        "rx_raw": rx[1],
        "tx_raw": tx[1],
        "rx_key": rx_key or None,
        "tx_key": tx_key or None,
    }
    # EV-0082: motivo da leitura descartada (só quando há item e o valor não serve).
    if rx[2]:
        payload["rx_problem"] = rx[2]
    if tx[2]:
        payload["tx_problem"] = tx[2]
    return payload


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

    empty: tuple[float | None, Any | None, str | None] = (None, None, None)
    rx = _read_optical_value(hostid, rx_key, value_cache) if rx_key else empty
    tx = _read_optical_value(hostid, tx_key, value_cache) if tx_key else empty

    result = _optical_payload(rx, tx, rx_key, tx_key)
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

        empty: tuple[float | None, Any | None, str | None] = (None, None, None)
        for port, rx_key, tx_key, status_meta, updates in contexts:
            rx = _read_optical_value(hostid, rx_key, value_cache) if rx_key else empty
            tx = _read_optical_value(hostid, tx_key, value_cache) if tx_key else empty

            payload = _optical_payload(rx, tx, rx_key, tx_key)
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
