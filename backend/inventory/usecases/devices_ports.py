# ruff: noqa: E501
"""Portas de dispositivos: estado vivo via Zabbix, níveis ópticos, descoberta de itens, tráfego.

Saiu de `inventory/usecases/devices.py` em EV-0017f. Toda chamada ao Zabbix passa por
`common.ZABBIX_REQUEST`; o histórico passa por `zabbix_history.fetch_aligned_series` (EV-0029).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, cast

from django.core.cache import cache
from django.db.models import Q, QuerySet

from inventory.domain.optical import fetch_port_optical_snapshot, fetch_ports_optical_snapshots
from inventory.domain.zabbix_history import fetch_aligned_series
from inventory.models import Device, FiberCable, Port

from . import devices_common as common
from .devices_common import (
    DeviceLike,
    InventoryNotFound,
    InventoryValidationError,
    PortLike,
    PortRecord,
    TrafficChannel,
    TrafficData,
    _coerce_dict_list,
    _extract_key_tokens,
    _normalize_identifier,
    _PortEntry,
)

logger = logging.getLogger(__name__)


OPTICAL_DISCOVERY_CACHE_TTL = 120  # seconds (2 minutes max)


def _score_optical_candidate_local(item: dict[str, Any], kind: str) -> int:
    text = " ".join(
        [
            (cast(str, item.get("key_", "")) or "").lower(),
            (cast(str, item.get("name", "")) or "").lower(),
        ]
    )
    units = (cast(str, item.get("units", "")) or "").lower()
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


def _preload_optical_discovery_cache(
    hostid: str,
    ports: Sequence[Port],
) -> dict[tuple[str, str | None], dict[str, str | None]]:
    hostid_str = str(hostid).strip()
    if not hostid_str:
        return {}

    # Try to reuse cached discovery map when port set did not change recently
    try:
        signature_data: list[dict[str, str]] = [
            {
                "id": str(getattr(port, "pk", getattr(port, "id", "")) or ""),
                "name": (getattr(cast(Any, port), "name", "") or "").strip(),
            }
            for port in ports
        ]
        signature_bytes = json.dumps(signature_data, sort_keys=True).encode("utf-8")
        signature_hash = hashlib.sha1(signature_bytes).hexdigest()
        cache_key_map = f"optical:discovery:{hostid_str}:{signature_hash}"
    except Exception:
        signature_hash = ""
        cache_key_map = f"optical:discovery:{hostid_str}:generic"

    cached_map: dict[tuple[str, str | None], dict[str, str | None]] | None = None
    try:
        cached_value = cache.get(cache_key_map)
        if isinstance(cached_value, dict):
            cached_map = cast(
                dict[tuple[str, str | None], dict[str, str | None]],
                cached_value,
            )
    except Exception:
        cached_map = None
    if cached_map:
        return cached_map

    port_entries: list[_PortEntry] = []
    for port in ports:
        name = (getattr(cast(Any, port), "name", "") or "").strip()
        if not name:
            continue
        lower = name.lower()
        trimmed = lower.replace(" ", "")
        normalized = _normalize_identifier(name)
        normalized_trimmed = _normalize_identifier(trimmed)
        port_entries.append(
            _PortEntry(
                port=port,
                record=PortRecord(port=port, created=False, defaults={}),
                lower=lower,
                normalized=normalized,
                trimmed=trimmed,
                normalized_trimmed=normalized_trimmed,
            )
        )

    if not port_entries:
        return {}

    default_cache: dict[tuple[str, str | None], dict[str, str | None]] = {}
    for entry in port_entries:
        entry_name = cast(str, getattr(cast(Any, entry.port), "name", "")) or None
        default_cache[(hostid_str, entry_name)] = {"rx": None, "tx": None}

    base_params: dict[str, Any] = {
        "output": ["itemid", "key_", "name", "units"],
        "hostids": [hostid_str],
        "filter": {"status": "0"},
        "limit": 5000,
    }

    search_variants: list[dict[str, Any]] = [
        {"search": {"key_": "power"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"name": "optical"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"key_": "optical"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"name": "dbm"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"name": "power"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"key_": "laser"}, "searchByAny": True, "searchWildcardsEnabled": True},
        {"search": {"name": "laser"}, "searchByAny": True, "searchWildcardsEnabled": True},
    ]

    gathered: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    gathered_items_cache_key = f"optical:gathered:{hostid_str}"
    cache_hit_items = False
    try:
        cached_items = cache.get(gathered_items_cache_key)
        if isinstance(cached_items, list):
            gathered = _coerce_dict_list(cached_items)
            cache_hit_items = True
    except Exception:
        cache_hit_items = False

    if not cache_hit_items:
        for variant in search_variants:
            params = base_params.copy()
            params.update(variant)
            try:
                raw_items = common.ZABBIX_REQUEST("item.get", params)
            except Exception as exc:  # pragma: no cover - network failure fallback
                logger.debug(
                    "Failed preloading optical items for host %s with params %s: %s",
                    hostid_str,
                    variant,
                    exc,
                )
                continue
            items = _coerce_dict_list(raw_items)
            for item in items:
                itemid = cast(str, item.get("itemid"))
                if not itemid or itemid in seen_ids:
                    continue
                seen_ids.add(itemid)
                gathered.append(item)

        if not gathered:
            try:
                fallback_items = _coerce_dict_list(common.ZABBIX_REQUEST("item.get", base_params))
                for item in fallback_items:
                    itemid = cast(str, item.get("itemid"))
                    if not itemid or itemid in seen_ids:
                        continue
                    seen_ids.add(itemid)
                    gathered.append(item)
            except Exception as exc:  # pragma: no cover - network failure fallback
                logger.debug(
                    "Fallback optical preload failed for host %s: %s",
                    hostid_str,
                    exc,
                )

        if gathered:
            try:
                cache.set(
                    gathered_items_cache_key,
                    gathered,
                    OPTICAL_DISCOVERY_CACHE_TTL,
                )
            except Exception:
                pass

    if not gathered:
        logger.debug(
            "Optical preload returned no candidates for host %s; using default discovery cache",
            hostid_str,
        )
        return default_cache

    port_match_map: dict[tuple[str, str | None], dict[str, Any]] = {}
    for item in gathered:
        key_value = cast(str, item.get("key_", ""))
        name_value = cast(str, item.get("name", ""))
        combined_text = f"{key_value.lower()} {name_value.lower()}".strip()
        if not combined_text:
            continue
        combined_normalized = _normalize_identifier(f"{key_value}{name_value}")
        tokens = _extract_key_tokens(key_value)
        rx_candidate_score = _score_optical_candidate_local(item, "rx")
        tx_candidate_score = _score_optical_candidate_local(item, "tx")

        for entry in port_entries:
            match_score = _score_port_match(entry, tokens, combined_text, combined_normalized)
            if match_score <= 0:
                continue

            entry_name = cast(str, getattr(cast(Any, entry.port), "name", "")) or None
            cache_key: tuple[str, str | None] = (hostid_str, entry_name)
            match_info = port_match_map.setdefault(
                cache_key,
                {"rx": None, "tx": None, "rx_score": float("-inf"), "tx_score": float("-inf")},
            )

            if rx_candidate_score > 0:
                rx_total = match_score + rx_candidate_score
                if rx_total > cast(float, match_info["rx_score"]):
                    match_info["rx_score"] = rx_total
                    match_info["rx"] = key_value or None

            if tx_candidate_score > 0:
                tx_total = match_score + tx_candidate_score
                if tx_total > cast(float, match_info["tx_score"]):
                    match_info["tx_score"] = tx_total
                    match_info["tx"] = key_value or None

    discovery_cache: dict[tuple[str, str | None], dict[str, str | None]] = default_cache.copy()
    for entry in port_entries:
        entry_name = cast(str, getattr(cast(Any, entry.port), "name", "")) or None
        cache_key = (hostid_str, entry_name)
        match_info = port_match_map.get(cache_key)
        if match_info is None:
            continue
        discovery_cache[cache_key] = {
            "rx": cast(str | None, match_info.get("rx")),
            "tx": cast(str | None, match_info.get("tx")),
        }

    logger.debug(
        "Prefetched %d optical candidates for host %s (ports=%d, mapped=%d)",
        len(gathered),
        hostid_str,
        len(port_entries),
        len([entry for entry in discovery_cache.values() if entry.get("rx") or entry.get("tx")]),
    )

    try:
        cache.set(
            cache_key_map,
            discovery_cache,
            OPTICAL_DISCOVERY_CACHE_TTL,
        )
    except Exception:
        pass

    return discovery_cache


def _score_port_match(
    entry: _PortEntry, tokens: Iterable[str], combined_text: str, combined_normalized: str
) -> int:
    score = 0
    port_lower = entry.lower
    normalized = entry.normalized
    trimmed = entry.trimmed
    normalized_trimmed = entry.normalized_trimmed

    if port_lower and port_lower in combined_text:
        score = max(score, len(port_lower) + 60)
    if trimmed and trimmed in combined_text:
        score = max(score, len(trimmed) + 55)
    if normalized and normalized in combined_normalized:
        score = max(score, len(normalized) + 50)
    if normalized_trimmed and normalized_trimmed in combined_normalized:
        score = max(score, len(normalized_trimmed) + 45)

    for token in tokens:
        token_lower = token.lower()
        token_norm = _normalize_identifier(token)
        if token_lower == port_lower:
            score = max(score, len(token_lower) + 120)
        if trimmed and token_lower == trimmed:
            score = max(score, len(token_lower) + 100)
        if token_norm and token_norm == normalized:
            score = max(score, len(token_norm) + 90)
        if normalized_trimmed and token_norm == normalized_trimmed:
            score = max(score, len(token_norm) + 85)
    return score


def get_device_ports(device_id: int) -> dict[str, Any]:
    try:
        device: Device = Device.objects.get(id=device_id)
    except Device.DoesNotExist as exc:
        raise InventoryNotFound("Device not found") from exc

    ports_qs: QuerySet[Port] = Port.objects.filter(device=device).select_related("device")
    ports_data: list[dict[str, Any]] = []

    for port in ports_qs:
        cable_as_origin = FiberCable.objects.filter(origin_port=port).first()
        cable_as_dest = FiberCable.objects.filter(destination_port=port).first()
        fiber_cable = cable_as_origin or cable_as_dest

        port_any = cast(Any, port)
        fiber_any = cast(Any, fiber_cable) if fiber_cable else None

        port_id = cast(int, getattr(port_any, "id", port_any.pk))
        device_name = cast(str, getattr(getattr(port_any, "device", None), "name", ""))
        fiber_cable_id = cast(int | None, getattr(fiber_any, "id", None) if fiber_any else None)
        ports_data.append(
            {
                "id": port_id,
                "name": cast(str, getattr(port_any, "name", "")),
                "device": device_name,
                "fiber_cable_id": fiber_cable_id,
                "zabbix_item_key": getattr(port_any, "zabbix_item_key", None),
                "notes": getattr(port_any, "notes", None),
            }
        )

    return {"ports": ports_data}


def get_device_ports_with_live_status(device_id: int) -> dict[str, Any]:
    """
    Retorna portas do dispositivo com status em tempo real do Zabbix.
    Inclui: status operacional, velocidade, e níveis de sinal óptico (RX/TX).
    """
    try:
        device: Device = Device.objects.select_related("site").get(id=device_id)
    except Device.DoesNotExist as exc:
        raise InventoryNotFound("Device not found") from exc

    ports_qs: QuerySet[Port] = Port.objects.filter(device=device).select_related("device")
    ports_list = list(ports_qs)

    hostid = (getattr(cast(Any, device), "zabbix_hostid", "") or "").strip()

    # Pre-fetch all cable associations in 2 queries (eliminates N+1)
    port_ids = [cast(int, getattr(cast(Any, p), "id", p.pk)) for p in ports_list]
    cables_by_origin: dict[int, Any] = {
        c.origin_port_id: c
        for c in FiberCable.objects.filter(origin_port_id__in=port_ids).only("id", "origin_port_id")
    }
    cables_by_dest: dict[int, Any] = {
        c.destination_port_id: c
        for c in FiberCable.objects.filter(destination_port_id__in=port_ids).only(
            "id", "destination_port_id"
        )
    }

    # Fetch Zabbix data: optical (sequential) + interface status (parallel)
    optical_snapshots: dict[int, dict[str, Any]] = {}
    interface_status_map: dict[str, dict[str, Any]] = {}

    if hostid:

        def _fetch_optical():
            cache = _preload_optical_discovery_cache(hostid, ports_list)
            return fetch_ports_optical_snapshots(
                ports_list,
                discovery_cache=cache,
                persist_keys=True,
                include_status_meta=False,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            f_optical = executor.submit(_fetch_optical)
            f_status = executor.submit(_fetch_interface_status_bulk, hostid, ports_list)
            optical_snapshots = f_optical.result()
            interface_status_map = f_status.result()

    ports_data: list[dict[str, Any]] = []

    for port in ports_list:
        port_any = cast(Any, port)
        port_id = cast(int, getattr(port_any, "id", port_any.pk))
        port_name = cast(str, getattr(port_any, "name", ""))

        # Get optical data
        optical = optical_snapshots.get(port_id, {})
        rx_dbm = optical.get("rx_dbm")
        tx_dbm = optical.get("tx_dbm")

        # Get interface status
        status_data = interface_status_map.get(port_name, {})
        status = status_data.get("status", "unknown")
        speed = status_data.get("speed", "")

        has_optical_signal = rx_dbm is not None or tx_dbm is not None
        if has_optical_signal:
            status = "up"
        elif status == "unknown":
            status = "down"

        # Get cable info from pre-fetched maps (no extra queries)
        fiber_cable = cables_by_origin.get(port_id) or cables_by_dest.get(port_id)
        fiber_cable_id = cast(int | None, getattr(fiber_cable, "id", None) if fiber_cable else None)

        # FILTRO: Apenas portas físicas em uso (com sinal óptico OU status UP OU com cabo conectado)
        is_in_use = (
            rx_dbm is not None or tx_dbm is not None or status == "up" or fiber_cable_id is not None
        )

        if not is_in_use:
            continue  # Pula portas não utilizadas

        ports_data.append(
            {
                "id": port_id,
                "name": port_name,
                "description": getattr(port_any, "notes", "") or "",
                "status": status,
                "speed": speed,
                "rx_power": round(rx_dbm, 2) if rx_dbm is not None else None,
                "tx_power": round(tx_dbm, 2) if tx_dbm is not None else None,
                "fiber_cable_id": fiber_cable_id,
                "zabbix_item_key": getattr(port_any, "zabbix_item_key", None),
            }
        )

    return {
        "device": {
            "id": device.id,
            "name": device.name,
            "zabbix_hostid": hostid,
        },
        "ports": ports_data,
    }


def _fetch_interface_status_bulk(hostid: str, ports: list[Port]) -> dict[str, dict[str, Any]]:
    """
    Busca status de interfaces no Zabbix usando item.get.
    Retorna mapa: {interface_name: {status: 'up'|'down'|'unknown', speed: '1 Gbps'}}
    """

    if not hostid:
        return {}

    result_map: dict[str, dict[str, Any]] = {}

    try:
        # Busca todos os items do host
        items_response = common.ZABBIX_REQUEST(
            "item.get",
            {
                "hostids": [hostid],
                "output": ["itemid", "key_", "name", "lastvalue", "units", "value_type"],
                "filter": {"state": "0"},  # Apenas items ativos
            },
        )

        if not items_response:
            return {}

        # Processa items para cada porta
        for port in ports:
            port_name = getattr(port, "name", "")
            if not port_name:
                continue

            # Mapeia items relevantes para esta porta
            status_item = None
            speed_item = None

            for item in items_response:
                key = item.get("key_", "")
                name = item.get("name", "")

                # Match por nome da interface em diferentes formatos
                # Verifica se o nome da porta está presente no key ou name do item
                port_match = (
                    port_name in key
                    or port_name in name
                    or port_name.replace("/", ".") in key  # Huawei usa ponto em vez de barra
                    or port_name.replace(".", "/") in key  # E vice-versa
                )

                if port_match:
                    key_lower = key.lower()
                    name_lower = name.lower()

                    # Status operacional: net.if.status[ifName] ou hwIfOperStatus
                    if (
                        "status" in key_lower
                        or "operstatus" in key_lower
                        or "ifoperstatus" in name_lower
                    ):
                        status_item = item
                    # Velocidade: net.if.speed[ifName] ou hwIfSpeed ou interface.speed
                    elif (
                        "speed" in key_lower or "bandwidth" in key_lower or "ifspeed" in name_lower
                    ):
                        speed_item = item

            # Processa status
            status = "unknown"
            if status_item:
                last_value = status_item.get("lastvalue", "")
                # Zabbix interface status: 0=down, 1=up, 2=unknown
                # Huawei também pode usar: 1=up, 2=down
                if last_value in ("1", "up", "UP"):
                    status = "up"
                elif last_value in ("0", "2", "down", "DOWN"):
                    status = "down"

            # Processa velocidade
            speed = ""
            if speed_item:
                last_value = speed_item.get("lastvalue", "")
                units = speed_item.get("units", "")
                name = speed_item.get("name", "")
                key = speed_item.get("key_", "")

                # DEBUG: Log do item de velocidade
                logger.debug(
                    f"[SPEED_DEBUG] Interface: {port_name}, "
                    f"Value: {last_value}, Units: {units}, "
                    f"Name: {name}, Key: {key}"
                )

                if last_value and last_value != "0":
                    try:
                        # Tenta converter para número
                        speed_val = float(last_value)

                        # DETECÇÃO INTELIGENTE baseada no nome da interface
                        # XGigabitEthernet = 10 Gbps
                        # GigabitEthernet = 1 Gbps
                        # 40GE = 40 Gbps
                        # FastEthernet = 100 Mbps

                        # Detecta pelo nome da INTERFACE (não do item)
                        interface_name_lower = port_name.lower()

                        if "xgigabit" in interface_name_lower or "10ge" in interface_name_lower:
                            # XGigabitEthernet sempre 10 Gbps
                            speed = "10 Gbps"
                            logger.debug(f"[SPEED_DEBUG] XGigabitEthernet detectado: {speed}")

                        elif "40ge" in interface_name_lower:
                            # 40GE sempre 40 Gbps
                            speed = "40 Gbps"
                            logger.debug(f"[SPEED_DEBUG] 40GE detectado: {speed}")

                        elif "100ge" in interface_name_lower:
                            # 100GE sempre 100 Gbps
                            speed = "100 Gbps"
                            logger.debug(f"[SPEED_DEBUG] 100GE detectado: {speed}")

                        elif (
                            "gigabit" in interface_name_lower
                            or "1ge" in interface_name_lower
                            or "ge0" in interface_name_lower
                        ):
                            # GigabitEthernet sempre 1 Gbps
                            speed = "1 Gbps"
                            logger.debug(f"[SPEED_DEBUG] GigabitEthernet detectado: {speed}")

                        elif (
                            "fastethernet" in interface_name_lower or "fe0" in interface_name_lower
                        ):
                            # FastEthernet sempre 100 Mbps
                            speed = "100 Mbps"
                            logger.debug(f"[SPEED_DEBUG] FastEthernet detectado: {speed}")

                        else:
                            # Fallback: Usa o valor do Zabbix com detecção de contexto
                            # Se o nome do item indica Gbps/Mbps, usa isso
                            if "Gbps" in name or "Gbit" in name or "GE" in name:
                                # Valor já está em Gbps ou é indicado como Gigabit
                                if speed_val >= 1000:
                                    speed = f"{int(speed_val // 1000)} Gbps"
                                else:
                                    speed = f"{int(speed_val)} Gbps"
                            elif "Mbps" in name or "Mbit" in name or "MB" in name:
                                # Valor está em Mbps
                                if speed_val >= 1000:
                                    speed = f"{int(speed_val // 1000)} Gbps"
                                else:
                                    speed = f"{int(speed_val)} Mbps"
                            # Conversão padrão de bps (assume que valor está em bits por segundo)
                            elif speed_val >= 1_000_000_000:
                                speed = f"{int(speed_val // 1_000_000_000)} Gbps"
                            elif speed_val >= 1_000_000:
                                speed = f"{int(speed_val // 1_000_000)} Mbps"
                            elif speed_val >= 1_000:
                                speed = f"{int(speed_val // 1_000)} Kbps"
                            else:
                                speed = f"{int(speed_val)} bps"

                            logger.debug(f"[SPEED_DEBUG] Fallback conversion: {speed}")

                    except (ValueError, TypeError):
                        # Se não conseguir converter, usa o valor bruto
                        speed = str(last_value)
                        if units:
                            speed += f" {units}"
                        logger.debug(f"[SPEED_DEBUG] Raw value used: {speed}")

            result_map[port_name] = {"status": status, "speed": speed}

    except Exception as e:
        logger.exception(f"Error fetching interface status from Zabbix for host {hostid}: {e}")

    return result_map


def import_interfaces_from_zabbix(device: Device) -> dict[str, Any]:
    """
    Importa automaticamente interfaces/portas do Zabbix para o Device.
    Busca apenas interfaces físicas relevantes (com sinal óptico ou UP).

    Returns:
        Dict com estatísticas: {created: int, updated: int, skipped: int}
    """

    if not device.zabbix_hostid:
        return {"created": 0, "updated": 0, "skipped": 0, "error": "Device sem zabbix_hostid"}

    hostid = device.zabbix_hostid.strip()
    stats = {"created": 0, "updated": 0, "skipped": 0}

    try:
        # 1. Busca todas as interfaces do host no Zabbix
        interfaces_response = common.ZABBIX_REQUEST(
            "hostinterface.get",
            {"hostids": [hostid], "output": ["interfaceid", "type", "ip", "port", "details"]},
        )

        if not interfaces_response:
            logger.info(f"Nenhuma interface Zabbix encontrada para host {hostid}")
            return stats

        # 2. Busca items do host para mapear nomes de interfaces
        items_response = common.ZABBIX_REQUEST(
            "item.get",
            {
                "hostids": [hostid],
                "output": ["itemid", "key_", "name", "lastvalue", "interfaceid"],
                "filter": {"state": "0"},
                "search": {
                    "key_": ["status", "speed", "optical", "ifOperStatus", "hwIfOperStatus"]
                },
                "searchWildcardsEnabled": True,
            },
        )

        if not items_response:
            logger.info(f"Nenhum item de interface encontrado para host {hostid}")
            return stats

        # 3. Agrupa items por nome de interface
        interface_map: dict[str, dict[str, Any]] = {}

        for item in items_response:
            key = item.get("key_", "")
            name = item.get("name", "")

            # Extrai nome da interface do key (ex: net.if.status[eth0] → eth0)
            interface_name = None

            # Padrões de extração
            import re

            patterns = [
                r"\[([^\]]+)\]",  # [ifname]
                r"\.([XG]?[Ee]thernet[\d/\.]+)",  # Ethernet/GigabitEthernet/XGigabitEthernet
                r"\.(\d+GE[\d/\.]+)",  # 40GE0/0/1
                r"Interface\s+([^\s]+)",  # "Interface eth0"
            ]

            for pattern in patterns:
                match = re.search(pattern, key + " " + name)
                if match:
                    interface_name = match.group(1)
                    break

            if not interface_name:
                continue

            # Normaliza nome (remove espaços, caso)
            interface_name = interface_name.strip()

            if interface_name not in interface_map:
                interface_map[interface_name] = {
                    "name": interface_name,
                    "status_item": None,
                    "speed_item": None,
                    "rx_optical_item": None,
                    "tx_optical_item": None,
                    "description": "",
                }

            key_lower = key.lower()

            # Classifica o item
            if "status" in key_lower or "operstatus" in key_lower:
                interface_map[interface_name]["status_item"] = item
                interface_map[interface_name]["description"] = name
            elif "speed" in key_lower or "bandwidth" in key_lower:
                interface_map[interface_name]["speed_item"] = item
            elif "rx" in key_lower and ("optical" in key_lower or "power" in key_lower):
                interface_map[interface_name]["rx_optical_item"] = item
            elif "tx" in key_lower and ("optical" in key_lower or "power" in key_lower):
                interface_map[interface_name]["tx_optical_item"] = item

        # 4. Filtra apenas interfaces relevantes e cria/atualiza portas
        for if_name, if_data in interface_map.items():
            # Verifica se é interface física relevante
            status_item = if_data.get("status_item")
            rx_item = if_data.get("rx_optical_item")
            tx_item = if_data.get("tx_optical_item")

            # Critério: Tem item de status OU tem itens ópticos
            is_relevant = status_item or rx_item or tx_item

            if not is_relevant:
                stats["skipped"] += 1
                continue

            # Prepara dados da porta
            port_defaults = {
                "notes": if_data.get("description", f"Status Operacional da Porta {if_name}"),
            }

            # Adiciona item keys se existirem
            if status_item:
                port_defaults["zabbix_item_key"] = status_item.get("key_", "")

            if rx_item:
                port_defaults["rx_power_item_key"] = rx_item.get("key_", "")

            if tx_item:
                port_defaults["tx_power_item_key"] = tx_item.get("key_", "")

            # Get or Create porta
            port, created = Port.objects.update_or_create(
                device=device, name=if_name, defaults=port_defaults
            )

            if created:
                stats["created"] += 1
                logger.info(f"Porta criada: {device.name} - {if_name}")
            else:
                stats["updated"] += 1
                logger.info(f"Porta atualizada: {device.name} - {if_name}")

        logger.info(
            f"Importação de interfaces concluída para {device.name}: "
            f"{stats['created']} criadas, {stats['updated']} atualizadas, "
            f"{stats['skipped']} ignoradas"
        )

    except Exception as e:
        logger.exception(f"Erro ao importar interfaces do Zabbix para device {device.id}: {e}")
        stats["error"] = str(e)

    return stats


def get_device_ports_with_optical(device_id: int) -> dict[str, Any]:
    start_time = time.perf_counter()
    try:
        device: Device = Device.objects.select_related("site").get(id=device_id)
    except Device.DoesNotExist as exc:
        raise InventoryNotFound("Device not found") from exc

    ports_qs: QuerySet[Port] = Port.objects.filter(device=device).select_related("device")
    cables_qs: QuerySet[FiberCable] = FiberCable.objects.filter(
        Q(origin_port__device=device) | Q(destination_port__device=device)
    ).select_related("origin_port", "destination_port")

    cable_origin_map: dict[int, FiberCable] = {}
    cable_dest_map: dict[int, FiberCable] = {}
    for cable in cables_qs:
        cable_any = cast(Any, cable)
        origin_id = cast(int | None, getattr(cable_any, "origin_port_id", None))
        if origin_id is not None:
            cable_origin_map.setdefault(origin_id, cable)
        dest_id = cast(int | None, getattr(cable_any, "destination_port_id", None))
        if dest_id is not None:
            cable_dest_map.setdefault(dest_id, cable)

    ports_list: list[Port] = list(ports_qs)
    hostid = (getattr(cast(Any, device), "zabbix_hostid", "") or "").strip()
    discovery_cache: dict[Any, Any] = {}
    if hostid:
        discovery_cache = _preload_optical_discovery_cache(hostid, ports_list)

    snapshots: dict[int, dict[str, Any]] = {}
    if hostid:
        snapshots = fetch_ports_optical_snapshots(
            ports_list,
            discovery_cache=discovery_cache,
            persist_keys=True,
            include_status_meta=False,
        )

    ports_with_optical: list[dict[str, Any]] = []

    for port in ports_list:
        port_any = cast(Any, port)
        port_id = cast(int, getattr(port_any, "id", port_any.pk))
        cable = cable_origin_map.get(port_id) or cable_dest_map.get(port_id)
        optical_snapshot = snapshots.get(
            port_id,
            {
                "rx_dbm": None,
                "tx_dbm": None,
                "rx_raw": None,
                "tx_raw": None,
                "rx_key": None,
                "tx_key": None,
            },
        )
        cable_any = cast(Any, cable) if cable else None
        port_notes = cast(str, getattr(port_any, "notes", ""))
        ports_with_optical.append(
            {
                "id": port_id,
                "name": cast(str, getattr(port_any, "name", "")),
                "notes": port_notes,
                "cable_id": cast(
                    int | None,
                    getattr(cable_any, "id", None) if cable_any else None,
                ),
                "cable_name": cast(
                    str | None,
                    getattr(cable_any, "name", None) if cable_any else None,
                ),
                "optical": optical_snapshot,
            }
        )

    duration = time.perf_counter() - start_time
    logger.info(
        "get_device_ports_with_optical completed device=%s hostid=%s ports=%d duration=%.3fs",
        cast(Any, device).pk,
        hostid or "",
        len(ports_with_optical),
        duration,
    )

    # Fetch uptime, CPU and Memory values from Zabbix
    uptime_value = None
    cpu_value = None
    memory_value = None

    uptime_key = getattr(cast(Any, device), "uptime_item_key", "")
    cpu_key = getattr(cast(Any, device), "cpu_usage_item_key", "")
    memory_key = getattr(cast(Any, device), "memory_usage_item_key", "")

    if uptime_key or cpu_key or memory_key:
        try:
            # Fetch item values from Zabbix
            items_to_fetch = []
            if uptime_key:
                items_to_fetch.append(uptime_key)
            if cpu_key:
                items_to_fetch.append(cpu_key)
            if memory_key:
                items_to_fetch.append(memory_key)

            item_values = common.ZABBIX_REQUEST(
                "item.get",
                {
                    "output": ["key_", "lastvalue", "units"],
                    "hostids": [hostid],
                    "filter": {"key_": items_to_fetch},
                },
            )

            # Map values
            for item in item_values:
                key = item.get("key_", "")
                lastvalue = item.get("lastvalue", "")
                units = item.get("units", "")

                if key == uptime_key and lastvalue:
                    # Convert uptime from seconds to human readable format
                    try:
                        seconds = int(lastvalue)
                        days = seconds // 86400
                        hours = (seconds % 86400) // 3600
                        minutes = (seconds % 3600) // 60

                        parts = []
                        if days > 0:
                            parts.append(f"{days}d")
                        if hours > 0:
                            parts.append(f"{hours}h")
                        if minutes > 0:
                            parts.append(f"{minutes}m")

                        uptime_value = " ".join(parts) if parts else "< 1m"
                    except (ValueError, TypeError):
                        uptime_value = lastvalue

                elif key == cpu_key and lastvalue:
                    # Format CPU value
                    try:
                        cpu_float = float(lastvalue)
                        cpu_value = f"{cpu_float:.1f}%"
                    except (ValueError, TypeError):
                        cpu_value = f"{lastvalue}{units}" if units else lastvalue

                elif key == memory_key and lastvalue:
                    # Format Memory value
                    try:
                        mem_float = float(lastvalue)
                        memory_value = f"{mem_float:.1f}%"
                    except (ValueError, TypeError):
                        memory_value = f"{lastvalue}{units}" if units else lastvalue

        except Exception as e:
            logger.warning(f"Failed to fetch Zabbix values for device {device.id}: {e}")

    # Fallback to manual overrides when Zabbix absent
    try:
        if not cpu_value:
            manual_cpu = getattr(cast(Any, device), "cpu_usage_manual_percent", None)
            if manual_cpu is not None:
                cpu_value = f"{float(manual_cpu):.1f}%"
        if not memory_value:
            manual_mem = getattr(cast(Any, device), "memory_usage_manual_percent", None)
            if manual_mem is not None:
                memory_value = f"{float(manual_mem):.1f}%"
    except Exception:
        pass

    return {
        "device_id": cast(int, getattr(cast(Any, device), "id", device.pk)),
        "device_name": cast(str, getattr(cast(Any, device), "name", "")),
        "primary_ip": cast(str | None, getattr(cast(Any, device), "primary_ip", None)),
        "uptime_value": uptime_value,
        "cpu_value": cpu_value,
        "memory_value": memory_value,
        "ports": ports_with_optical,
    }


def device_port_optical_status(port_id: int) -> dict[str, Any]:
    try:
        port = Port.objects.select_related("device").get(id=port_id)
    except Port.DoesNotExist as exc:
        raise InventoryNotFound("Port not found") from exc

    hostid = (port.device.zabbix_hostid or "").strip()
    if not hostid:
        raise InventoryValidationError("Device missing Zabbix Host ID")

    optical_snapshot = fetch_port_optical_snapshot(port)
    return {
        "port_id": port.pk,
        "port_name": port.name,
        "optical": optical_snapshot,
    }


def port_traffic_history(port_id: int, params: Mapping[str, str]) -> TrafficData:
    try:
        port = Port.objects.select_related("device").get(id=port_id)
    except Port.DoesNotExist as exc:
        raise InventoryNotFound("Port not found") from exc

    if not port.device.zabbix_hostid:
        raise InventoryValidationError("Device missing Zabbix Host ID configuration")

    if not port.zabbix_item_id_traffic_in and not port.zabbix_item_id_traffic_out:
        raise InventoryValidationError(
            "Port missing traffic items configured in Zabbix",
        )

    raw_period = (params.get("period") or "24h").lower().strip()
    seconds = None
    predefined = {
        "1h": 3600,
        "6h": 6 * 3600,
        "12h": 12 * 3600,
        "24h": 24 * 3600,
        "7d": 7 * 24 * 3600,
        "30d": 30 * 24 * 3600,
    }
    if raw_period in predefined:
        seconds = predefined[raw_period]
    else:
        match = re.match(r"^(\d+)([hdm])$", raw_period)
        if match:
            val = int(match.group(1))
            unit = match.group(2)
            if unit == "h":
                seconds = val * 3600
            elif unit == "d":
                seconds = val * 24 * 3600
            elif unit == "m":
                seconds = val * 60
    if not seconds:
        seconds = predefined["24h"]
        raw_period = "24h"
    max_seconds = predefined["30d"]
    if seconds > max_seconds:
        seconds = max_seconds
        raw_period = "30d"

    now_ts = int(datetime.now().timestamp())
    time_from = now_ts - seconds

    since_raw = params.get("since")
    since = None
    since_applied = False
    if since_raw:
        try:
            since_val = int(since_raw)
            if since_val > time_from and since_val < now_ts:
                since = since_val
                since_applied = True
        except ValueError:
            pass

    if seconds <= 24 * 3600:
        default_limit = min(1500, max(300, int(seconds / 60) + 50))
    else:
        default_limit = min(5000, max(1000, int(seconds / 120) + 100))

    limit_override: int | None = None
    limit_raw = params.get("limit")
    if limit_raw:
        try:
            limit_override = int(limit_raw)
        except ValueError:
            limit_override = None
    if limit_override and 50 <= limit_override <= 10000:
        default_limit = limit_override
    history_limit = default_limit

    port_like = cast(PortLike, port)
    device_like = cast(DeviceLike, port_like.device)

    traffic_in_channel: TrafficChannel = {
        "history": [],
        "unit": "bps",
        "configured": bool(port_like.zabbix_item_id_traffic_in),
    }
    traffic_out_channel: TrafficChannel = {
        "history": [],
        "unit": "bps",
        "configured": bool(port_like.zabbix_item_id_traffic_out),
    }

    traffic_data: TrafficData = {
        "port_id": port_like.id,
        "port_name": port_like.name,
        "device_name": device_like.name,
        "in": traffic_in_channel,
        "out": traffic_out_channel,
    }

    # EV-0029: a mesma fachada das rotas DRF — item.get único com value_type/units
    # (EV-0003), históricos em paralelo, IN/OUT alinhados por bucket (EV-0010).
    # O `limit` do Zabbix saiu: cortava pelo fim da janela e escondia os pontos
    # mais recentes em períodos longos; agora `history_limit` é o tecto de pontos
    # da SAÍDA, respeitado pelo bucket.
    bucket_seconds = 0
    try:
        series = fetch_aligned_series(
            {"in": port.zabbix_item_id_traffic_in, "out": port.zabbix_item_id_traffic_out},
            time_from,
            now_ts,
            max_points=history_limit,
        )
    except Exception as exc:
        logger.error("Failed to retrieve traffic history: %s", exc)
    else:
        bucket_seconds = series["bucket_seconds"]
        for name, channel in (("in", traffic_in_channel), ("out", traffic_out_channel)):
            if series["units"].get(name):
                channel["unit"] = series["units"][name]
            for row in series["rows"]:
                value = row.get(name)
                if value is None:
                    continue
                ts = int(datetime.fromisoformat(row["timestamp"]).timestamp())
                if since and ts <= since:
                    continue
                channel["history"].append({"timestamp": ts, "value": float(value)})

    traffic_data["period"] = raw_period
    traffic_data["period_seconds"] = seconds
    traffic_data["since"] = since if since_applied else None
    traffic_data["incremental"] = since_applied
    traffic_data["generated_at"] = now_ts
    traffic_data["time_from"] = time_from
    traffic_data["history_limit"] = history_limit
    traffic_data["bucket_seconds"] = bucket_seconds

    return traffic_data
