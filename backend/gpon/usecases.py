"""Monitoramento GPON (EV-0095, ADR 0010): coleta do estado das ONU e leitura para o ecrã.

- ``collect_onu_states`` — a tarefa de 120 s: UM ``item.get`` por OLT pelo gateway, grava
  ``OnuState`` (transições observadas pelo ProVeMaps) e o estado da OLT em cache.
- ``gpon_overview`` — o payload de ``/api/v1/monitoring/gpon/``: só base + cache, nenhuma
  chamada ao Zabbix no pedido.
- ``onu_history`` — histórico do RX de uma ONU, fachada de ``fetch_aligned_series`` (§7).

Que equipamentos são OLT: ``Device`` com ``zabbix_hostid`` preenchido, «OLT» no nome e
fabricante reconhecível pelo nome ou pelo campo ``vendor`` («ZTE» → zte, «VSOL» → vsol).
Critério determinista e barato (uma consulta); um equipamento novo entra quando o nome segue
a convenção do inventário («ZTE - OLT …», «VSOL - OLT …»).
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from integrations.zabbix.zabbix_service import zabbix_request
from inventory.domain import zabbix_history
from inventory.domain.optical import (
    OPTICAL_SENTINEL_VALUES,
    is_plausible_dbm,
    validate_optical_reading,
)
from inventory.models import Device
from setup_app.services import runtime_settings

from .domain import parsers, rules
from .models import OnuState

logger = logging.getLogger(__name__)

LAST_RUN_CACHE_KEY = "gpon:collect:last-run"
OLT_CACHE_KEY = "gpon:collect:olt:{device_id}"
VALUEMAP_CACHE_KEY = "gpon:valuemap:{valuemapid}"
VALUEMAP_CACHE_SECONDS = 3600
# O estado da OLT em cache vale 5 ciclos de coleta; depois disso o ecrã mostra «desconhecido».
OLT_CACHE_SECONDS = 600
LAST_RUN_CACHE_SECONDS = 86400
# ONU que deixou de vir do Zabbix há mais de 1 dia aparece como «unknown» (não se apaga).
STALE_AFTER = timedelta(days=1)

HISTORY_HOURS_MIN = 1
HISTORY_HOURS_MAX = 168
HISTORY_HOURS_DEFAULT = 24

_UPDATE_FIELDS = [
    "vendor",
    "technology",
    "pon_id",
    "onu_index",
    "serial",
    "mac",
    "description",
    "status",
    "reason",
    "reason_label",
    "raw_status",
    "raw_reason",
    "rx_onu_dbm",
    "rx_olt_dbm",
    "distance_m",
    "rx_item_key",
    "status_since",
    "status_since_is_first_seen",
    "last_seen",
]


class ZabbixUnavailable(Exception):
    """O gateway não respondeu (``None``: circuito aberto, falha de rede, método bloqueado)."""


# ---------------------------------------------------------------------------------------------
# Que equipamentos são OLT
# ---------------------------------------------------------------------------------------------


def olt_devices() -> list[tuple[Device, str]]:
    """``[(device, vendor)]`` das OLT conhecidas, por nome; ver o critério no topo do módulo."""
    queryset = (
        Device.objects.select_related("site")
        .filter(name__icontains="OLT")
        .exclude(Q(zabbix_hostid__isnull=True) | Q(zabbix_hostid=""))
        .only("id", "name", "vendor", "model", "primary_ip", "zabbix_hostid", "site__display_name")
        .order_by("name", "id")
    )
    result: list[tuple[Device, str]] = []
    for device in queryset:
        vendor = parsers.detect_vendor(device.name, device.vendor)
        if vendor:
            result.append((device, vendor))
    return result


# ---------------------------------------------------------------------------------------------
# Coleta
# ---------------------------------------------------------------------------------------------


def _request(method: str, params: dict[str, Any]) -> Any:
    result = zabbix_request(method, params)
    if result is None:
        raise ZabbixUnavailable(f"{method} sem resposta do Zabbix")
    return result


def _fetch_olt_items(hostid: str, vendor: str) -> list[Mapping[str, Any]]:
    raw = _request(
        "item.get",
        {
            "hostids": [str(hostid)],
            "output": parsers.ITEM_OUTPUT[vendor],
            "search": {"key_": list(parsers.KEY_FAMILIES[vendor])},
            "searchByAny": True,
            "startSearch": True,
            "filter": {"status": "0"},
        },
    )
    return [entry for entry in raw if isinstance(entry, Mapping)] if isinstance(raw, list) else []


def _valuemap_mappings(valuemapid: str) -> list[Mapping[str, Any]] | None:
    """Mapeamentos do valuemap (cache 1 h). ``None`` = ilegível (sem permissão, Zabbix fora)."""
    key = VALUEMAP_CACHE_KEY.format(valuemapid=valuemapid)
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        raw = _request(
            "valuemap.get",
            {
                "valuemapids": [valuemapid],
                "output": ["valuemapid", "name"],
                "selectMappings": ["type", "value", "newvalue"],
            },
        )
    except Exception:
        logger.warning("gpon.valuemap_unavailable", extra={"valuemapid": valuemapid})
        return None
    mappings: list[Mapping[str, Any]] = []
    if isinstance(raw, list) and raw and isinstance(raw[0], Mapping):
        mappings = [m for m in raw[0].get("mappings") or [] if isinstance(m, Mapping)]
    if not mappings:
        return None
    cache.set(key, mappings, VALUEMAP_CACHE_SECONDS)
    return mappings


def _reason(
    reading: parsers.OnuReading, valuemaps: Mapping[str, list[Mapping[str, Any]] | None]
) -> tuple[str, str]:
    """``(reason, reason_label)`` — só para ONU offline e só com valuemap legível."""
    if reading.status != parsers.STATUS_OFFLINE or not reading.raw_reason:
        return "", ""
    label = parsers.valuemap_text(valuemaps.get(reading.reason_valuemapid), reading.raw_reason)
    reason = parsers.classify_reason_text(label)
    return (reason, label) if reason and label else ("", "")


def _store_olt(device: Device, vendor: str, now: datetime, reading: parsers.OltReading) -> int:
    """Upsert das ONU de uma OLT; devolve quantas mudaram de estado/motivo."""
    existing = {state.onu_key: state for state in OnuState.objects.filter(device=device)}
    to_create: list[OnuState] = []
    to_update: list[OnuState] = []
    transitions = 0
    # Um valuemap.get por OLT (e em cache 1 h), não um por ONU.
    valuemaps = {
        valuemapid: _valuemap_mappings(valuemapid)
        for valuemapid in {
            onu.reason_valuemapid
            for onu in reading.onus
            if onu.status == parsers.STATUS_OFFLINE and onu.reason_valuemapid
        }
    }
    for onu in reading.onus:
        reason, reason_label = _reason(onu, valuemaps)
        values = {
            "vendor": vendor,
            "technology": reading.technology,
            "pon_id": onu.pon_id,
            "onu_index": onu.onu_index,
            "serial": onu.serial,
            "mac": onu.mac,
            "description": onu.description,
            "status": onu.status,
            "reason": reason,
            "reason_label": reason_label,
            "raw_status": onu.raw_status[:32],
            "raw_reason": onu.raw_reason[:32],
            "rx_onu_dbm": onu.rx_onu_dbm,
            "rx_olt_dbm": onu.rx_olt_dbm,
            "distance_m": onu.distance_m,
            "rx_item_key": onu.rx_item_key[:255],
            "last_seen": now,
        }
        state = existing.get(onu.onu_key)
        if state is None:
            to_create.append(
                OnuState(
                    device=device,
                    onu_key=onu.onu_key,
                    status_since=now,
                    status_since_is_first_seen=True,
                    first_seen=now,
                    **values,
                )
            )
            continue
        if state.status != onu.status or state.reason != reason:
            state.status_since = now
            state.status_since_is_first_seen = False
            transitions += 1
        for field_name, value in values.items():
            setattr(state, field_name, value)
        to_update.append(state)

    with transaction.atomic():
        if to_create:
            OnuState.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            OnuState.objects.bulk_update(to_update, _UPDATE_FIELDS, batch_size=500)
    return transitions


def _olt_meta(
    reading: parsers.OltReading | None, now: datetime, error: str | None
) -> dict[str, Any]:
    if reading is None:
        return {
            "collected_at": now.isoformat(),
            "ok": False,
            "error": error,
            "ping": None,
            "cpu_pct": None,
            "temperature_c": None,
            "model": None,
            "pon_status": {},
            "has_known_onu": False,
        }
    return {
        "collected_at": now.isoformat(),
        "ok": True,
        "error": None,
        "ping": reading.ping,
        "cpu_pct": reading.cpu_pct,
        "temperature_c": reading.temperature_c,
        "model": reading.model,
        "pon_status": dict(reading.pon_status),
        "has_known_onu": reading.has_known_onu,
    }


def collect_onu_states(now: datetime | None = None) -> dict[str, Any]:
    """Coleta todas as OLT. Nunca rebenta por Zabbix fora: regista ``zabbix_ok`` false."""
    now = now or timezone.now()
    started = time.monotonic()
    olts = olt_devices()
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    onus_seen = 0
    transitions = 0

    for device, vendor in olts:
        try:
            items = _fetch_olt_items(str(device.zabbix_hostid), vendor)
            reading = parsers.parse_olt_items(vendor, items, validate_rx=validate_optical_reading)
            transitions += _store_olt(device, vendor, now, reading)
        except Exception as exc:  # uma OLT que falha não para as outras
            message = str(exc) or exc.__class__.__name__
            logger.warning(
                "gpon.collect_olt_failed",
                extra={"device_id": device.pk, "error": message},
                exc_info=not isinstance(exc, ZabbixUnavailable),
            )
            failures.append(f"{device.name}: {message}")
            cache.set(
                OLT_CACHE_KEY.format(device_id=device.pk),
                _olt_meta(None, now, message),
                OLT_CACHE_SECONDS,
            )
            results.append({"device_id": device.pk, "ok": False, "error": message})
            continue
        cache.set(
            OLT_CACHE_KEY.format(device_id=device.pk),
            _olt_meta(reading, now, None),
            OLT_CACHE_SECONDS,
        )
        onus_seen += len(reading.onus)
        results.append({"device_id": device.pk, "ok": True, "onus": len(reading.onus)})

    # «Zabbix fora» = nenhuma OLT respondeu. Falhas parciais ficam em `zabbix_error` e no
    # `collection_ok` de cada OLT.
    zabbix_ok = not olts or len(failures) < len(olts)
    zabbix_error = None
    if failures:
        zabbix_error = f"{len(failures)} de {len(olts)} OLT sem resposta — " + "; ".join(failures)
    last_run = {
        "collected_at": now.isoformat(),
        "zabbix_ok": zabbix_ok,
        "zabbix_error": zabbix_error,
    }
    cache.set(LAST_RUN_CACHE_KEY, last_run, LAST_RUN_CACHE_SECONDS)
    return {
        **last_run,
        "olts": len(olts),
        "onus_seen": onus_seen,
        "transitions": transitions,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "results": results,
    }


# ---------------------------------------------------------------------------------------------
# Leitura para o ecrã
# ---------------------------------------------------------------------------------------------


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _iso_text(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _iso(datetime.fromisoformat(value))
    except ValueError:
        return None


def _thresholds() -> tuple[float, float, dict[str, int]]:
    config = runtime_settings.get_runtime_config()
    warning = float(getattr(config, "optical_rx_warning_threshold", -24.0))
    critical = float(getattr(config, "optical_rx_critical_threshold", -27.0))
    capacity = {
        parsers.TECHNOLOGY_GPON: int(getattr(config, "gpon_pon_capacity", 128)),
        parsers.TECHNOLOGY_EPON: int(getattr(config, "epon_pon_capacity", 64)),
    }
    return warning, critical, capacity


def _olt_status(meta: Mapping[str, Any] | None) -> str:
    ping = (meta or {}).get("ping")
    if ping == 1:
        return "online"
    if ping == 0:
        return "offline"
    return "unknown"


def _onu_payload(
    state: OnuState, olt_name: str, now: datetime, warning: float, critical: float
) -> dict[str, Any]:
    stale = state.last_seen < now - STALE_AFTER
    status = parsers.STATUS_UNKNOWN if stale else state.status
    reason = None if stale else (state.reason or None)
    signal = (
        None
        if stale
        else rules.classify_signal(
            rules.signal_dbm(state.rx_onu_dbm, state.rx_olt_dbm), warning, critical
        )
    )
    return {
        "id": state.pk,
        "device_id": state.device_id,
        "olt_name": olt_name,
        "pon_id": state.pon_id,
        "onu_index": state.onu_index,
        "serial": state.serial or None,
        "mac": state.mac or None,
        "description": state.description or None,
        "status": status,
        "reason": reason,
        "reason_label": (state.reason_label or None) if reason else None,
        "rx_onu_dbm": state.rx_onu_dbm,
        "rx_olt_dbm": state.rx_olt_dbm,
        "signal": signal,
        "distance_m": state.distance_m,
        "status_since": _iso(state.status_since),
        "status_since_is_first_seen": state.status_since_is_first_seen,
        "last_seen": _iso(state.last_seen),
        "cliente_nome": state.cliente_nome or None,
        "login_radius": state.login_radius or None,
        "caixa_cto": state.caixa_cto or None,
        "severity_rank": rules.onu_severity_rank(status, reason, signal),
        "has_history": bool(state.rx_item_key),
    }


def _pon_payload(
    pon_id: str,
    onus: list[dict[str, Any]],
    since: dict[int, datetime],
    pon_status: str,
    capacity: int,
) -> dict[str, Any]:
    online = [o for o in onus if o["status"] == parsers.STATUS_ONLINE]
    los = [o for o in onus if o["reason"] == parsers.REASON_LOS]
    signals = [
        rules.signal_dbm(o["rx_onu_dbm"], o["rx_olt_dbm"])
        for o in online
        if o["signal"] is not None
    ]
    rx_values = [value for value in signals if value is not None]
    signal_warning = sum(1 for o in onus if o["signal"] == rules.SIGNAL_WARNING)
    signal_critical = sum(1 for o in onus if o["signal"] == rules.SIGNAL_CRITICAL)
    # Queda coletiva só com instantes OBSERVADOS (não a hora da primeira coleta).
    drop = rules.is_collective_drop(since[o["id"]] for o in los if o["id"] in since)
    occupancy = rules.occupancy_pct(len(onus), capacity)
    return {
        "pon_id": pon_id,
        "label": f"PON {pon_id}",
        "status": pon_status,
        "capacity": capacity,
        "onus_provisioned": len(onus),
        "onus_online": len(online),
        "occupancy_pct": occupancy,
        "rx_avg_dbm": round(sum(rx_values) / len(rx_values), 1) if rx_values else None,
        "los": len(los),
        "dying_gasp": sum(1 for o in onus if o["reason"] == parsers.REASON_DYING_GASP),
        "signal_warning": signal_warning,
        "signal_critical": signal_critical,
        "collective_drop": drop,
        "severity": rules.pon_severity(
            collective_drop=drop,
            los=len(los),
            status=pon_status,
            signal_warning=signal_warning,
            signal_critical=signal_critical,
            occupancy=occupancy,
        ),
    }


def gpon_overview(olt_id: int | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Payload de ``GET /api/v1/monitoring/gpon/`` (contrato EV-0095; ordem das chaves fixa).

    Duas consultas (OLT e ONU) + uma leitura de cache por OLT; nenhuma chamada ao Zabbix.
    Levanta ``Device.DoesNotExist`` se ``olt_id`` não é uma OLT conhecida.
    """
    now = now or timezone.now()
    warning, critical, capacity_by_tech = _thresholds()
    olts = olt_devices()
    if olt_id is not None:
        olts = [(device, vendor) for device, vendor in olts if device.pk == olt_id]
        if not olts:
            raise Device.DoesNotExist(f"OLT {olt_id} não encontrada")

    device_by_id = {device.pk: device for device, _ in olts}
    states = list(
        OnuState.objects.filter(device_id__in=list(device_by_id)).only(
            "id",
            "device_id",
            "pon_id",
            "onu_index",
            "serial",
            "mac",
            "description",
            "status",
            "reason",
            "reason_label",
            "rx_onu_dbm",
            "rx_olt_dbm",
            "distance_m",
            "rx_item_key",
            "status_since",
            "status_since_is_first_seen",
            "last_seen",
            "cliente_nome",
            "login_radius",
            "caixa_cto",
        )
    )
    observed_since = {
        state.pk: state.status_since for state in states if not state.status_since_is_first_seen
    }
    onus_by_olt: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for state in states:
        onus_by_olt[state.device_id].append(
            _onu_payload(state, device_by_id[state.device_id].name, now, warning, critical)
        )

    metas = cache.get_many([OLT_CACHE_KEY.format(device_id=pk) for pk in device_by_id])
    olt_payloads: list[dict[str, Any]] = []
    all_onus: list[dict[str, Any]] = []
    for device, vendor in olts:
        meta = metas.get(OLT_CACHE_KEY.format(device_id=device.pk))
        technology = parsers.TECHNOLOGY_BY_VENDOR[vendor]
        capacity = capacity_by_tech[technology]
        onus = onus_by_olt.get(device.pk, [])
        status = _olt_status(meta)
        by_pon: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for onu in onus:
            by_pon[onu["pon_id"]].append(onu)
        pon_status = (meta or {}).get("pon_status") or {}
        pons = [
            _pon_payload(
                pon_id,
                by_pon[pon_id],
                observed_since,
                pon_status.get(pon_id, parsers.PON_UNKNOWN),
                capacity,
            )
            for pon_id in sorted(by_pon, key=parsers.pon_sort_key)
        ]
        collection_ok = bool(meta and meta.get("ok")) and not (
            status == "online" and not meta.get("has_known_onu")
        )
        olt_payloads.append(
            {
                "device_id": device.pk,
                "name": device.name,
                "vendor": vendor,
                "technology": technology,
                "model": (meta or {}).get("model") or device.model or None,
                "ip": device.primary_ip or None,
                "site_name": device.site.display_name if device.site_id else None,
                "status": status,
                "collection_ok": collection_ok,
                "cpu_pct": (meta or {}).get("cpu_pct"),
                "temperature_c": (meta or {}).get("temperature_c"),
                "onus_total": len(onus),
                "onus_online": sum(1 for o in onus if o["status"] == parsers.STATUS_ONLINE),
                "pons": pons,
            }
        )
        all_onus.extend(onus)

    all_onus.sort(
        key=lambda o: (
            o["severity_rank"],
            o["olt_name"],
            parsers.pon_sort_key(o["pon_id"]),
            o["onu_index"] if o["onu_index"] is not None else 10**9,
        )
    )
    all_pons = [pon for olt in olt_payloads for pon in olt["pons"]]
    last_run = cache.get(LAST_RUN_CACHE_KEY) or {}
    return {
        "collected_at": _iso_text(last_run.get("collected_at")),
        "zabbix_ok": last_run.get("zabbix_ok"),
        "zabbix_error": last_run.get("zabbix_error"),
        "thresholds": {"warning": warning, "critical": critical},
        "capacity": {
            "gpon": capacity_by_tech[parsers.TECHNOLOGY_GPON],
            "epon": capacity_by_tech[parsers.TECHNOLOGY_EPON],
        },
        "totals": {
            "olts": len(olt_payloads),
            "olts_online": sum(1 for o in olt_payloads if o["status"] == "online"),
            "olts_offline": sum(1 for o in olt_payloads if o["status"] == "offline"),
            "pons": len(all_pons),
            "onus_provisioned": len(all_onus),
            "onus_online": sum(1 for o in all_onus if o["status"] == parsers.STATUS_ONLINE),
            "onus_offline": sum(1 for o in all_onus if o["status"] == parsers.STATUS_OFFLINE),
            "onus_unknown": sum(1 for o in all_onus if o["status"] == parsers.STATUS_UNKNOWN),
            "signal_warning": sum(1 for o in all_onus if o["signal"] == rules.SIGNAL_WARNING),
            "signal_critical": sum(1 for o in all_onus if o["signal"] == rules.SIGNAL_CRITICAL),
            "los": sum(1 for o in all_onus if o["reason"] == parsers.REASON_LOS),
            "dying_gasp": sum(1 for o in all_onus if o["reason"] == parsers.REASON_DYING_GASP),
            "pons_collective_drop": sum(1 for p in all_pons if p["collective_drop"]),
        },
        "olts": olt_payloads,
        "onus": all_onus,
    }


# ---------------------------------------------------------------------------------------------
# Histórico do RX de uma ONU
# ---------------------------------------------------------------------------------------------


def _is_rx_measure(value: float) -> bool:
    return is_plausible_dbm(value) and float(value) not in OPTICAL_SENTINEL_VALUES


def _history_points(series: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Pontos ``{x, y}``; um bucket só com sentinelas (0/-80) fica ``null`` (buraco real)."""
    bucket = int(series["bucket_seconds"])
    samples = series["samples"].get("rx", [])
    valid = [(clock, value) for clock, value in samples if _is_rx_measure(value)]
    rows = {
        row["timestamp"]: row["rx"]
        for row in zabbix_history.merge_series({"rx": valid}, bucket_seconds=bucket)
    }
    for clock, value in samples:
        if not _is_rx_measure(value):
            start = (int(clock) // bucket) * bucket
            stamp = datetime.fromtimestamp(start, tz=UTC).isoformat()
            rows.setdefault(stamp, None)
    return [{"x": stamp.replace("+00:00", "Z"), "y": rows[stamp]} for stamp in sorted(rows)]


def onu_history(onu_id: int, hours: int = HISTORY_HOURS_DEFAULT) -> dict[str, Any]:
    """Histórico do RX da ONU. ``Http404`` se não existe; Zabbix fora → ``zabbix_ok`` false."""
    if not HISTORY_HOURS_MIN <= int(hours) <= HISTORY_HOURS_MAX:
        raise ValueError(f"hours fora de {HISTORY_HOURS_MIN}..{HISTORY_HOURS_MAX}")
    state = get_object_or_404(
        OnuState.objects.select_related("device").only(
            "id", "vendor", "rx_item_key", "device__zabbix_hostid"
        ),
        pk=onu_id,
    )
    label = "RX na ONU" if state.vendor == parsers.VENDOR_VSOL else "RX na OLT"
    payload: dict[str, Any] = {
        "onu_id": state.pk,
        "unit": "dBm",
        "label": label,
        "points": [],
        "zabbix_ok": True,
        "zabbix_error": None,
    }
    hostid = state.device.zabbix_hostid
    if not state.rx_item_key or not hostid:
        return payload
    try:
        raw = _request(
            "item.get",
            {
                "hostids": [str(hostid)],
                "filter": {"key_": state.rx_item_key},
                "output": ["itemid", "value_type", "units"],
            },
        )
        entries = raw if isinstance(raw, list) else []
        entry = next((e for e in entries if isinstance(e, Mapping) and e.get("itemid")), None)
        if entry is None:
            return payload  # o item já não existe no host: sem histórico, não é erro do Zabbix
        itemid = str(entry["itemid"])
        try:
            value_type = int(entry.get("value_type", zabbix_history.DEFAULT_VALUE_TYPE))
        except (TypeError, ValueError):
            value_type = zabbix_history.DEFAULT_VALUE_TYPE
        meta = {
            itemid: zabbix_history.ItemMeta(
                itemid=itemid, value_type=value_type, units=str(entry.get("units") or "")
            )
        }
        time_till = int(time.time())
        series = zabbix_history.fetch_aligned_series(
            {"rx": itemid}, time_till - int(hours) * 3600, time_till, meta=meta
        )
    except Exception as exc:  # o ecrã distingue «Zabbix fora» de «sem dados»
        logger.warning("gpon.history_failed", extra={"onu_id": state.pk, "error": str(exc)})
        payload["zabbix_ok"] = False
        payload["zabbix_error"] = str(exc) or exc.__class__.__name__
        return payload
    payload["points"] = _history_points(series)
    return payload
