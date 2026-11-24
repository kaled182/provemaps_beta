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
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
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
from .models import OnuEvent, OnuState

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

# EV-0108: eventos de ONU (transições observadas)
EVENT_RETENTION_DAYS = 7
EVENTS_HOURS_DEFAULT = 24
EVENTS_HOURS_MAX = 168
EVENTS_LIMIT = 500

# EV-0109: tendência da PON (tendências horárias do Zabbix) e tráfego atual da porta
TREND_HOURS = 24
TREND_CACHE_KEY = "gpon:pon-trend:{device_id}:{pon_id}"
TREND_CACHE_SECONDS = 300
TRAFFIC_STALE_SECONDS = 600

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
    "last_known_status",
    "last_known_reason",
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
    events: list[OnuEvent] = []
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
        known = onu.status != parsers.STATUS_UNKNOWN
        state = existing.get(onu.onu_key)
        if state is None:
            to_create.append(
                OnuState(
                    device=device,
                    onu_key=onu.onu_key,
                    status_since=now,
                    status_since_is_first_seen=True,
                    first_seen=now,
                    last_known_status=onu.status if known else "",
                    last_known_reason=reason if known else "",
                    **values,
                )
            )
            continue
        if state.status != onu.status or state.reason != reason:
            state.status_since = now
            state.status_since_is_first_seen = False
            transitions += 1
        if known:
            event = _event_for(state, onu.status, reason, reason_label, now)
            if event is not None:
                events.append(event)
            state.last_known_status = onu.status
            state.last_known_reason = reason
        for field_name, value in values.items():
            setattr(state, field_name, value)
        to_update.append(state)

    with transaction.atomic():
        if to_create:
            OnuState.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            OnuState.objects.bulk_update(to_update, _UPDATE_FIELDS, batch_size=500)
        if events:
            OnuEvent.objects.bulk_create(events, batch_size=500)
    return transitions


def _event_for(
    state: OnuState, status: str, reason: str, reason_label: str, now: datetime
) -> OnuEvent | None:
    """Evento da passagem do último estado CONHECIDO para ``status`` (já conhecido).

    Sem estado conhecido anterior (ONU que só tinha estado em «unknown»), só a queda é
    informativa — «unknown → online» seria uma reconexão inventada.
    """
    previous = (state.last_known_status, state.last_known_reason)
    if previous == (status, reason):
        return None
    if not state.last_known_status and status != parsers.STATUS_OFFLINE:
        return None
    return OnuEvent(
        onu=state,
        device_id=state.device_id,
        pon_id=state.pon_id,
        at=now,
        previous_status=state.last_known_status,
        previous_reason=state.last_known_reason,
        status=status,
        reason=reason,
        reason_label=reason_label[:64],
    )


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
            "cards": [],
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
        "cards": [
            {
                "slot": card.slot,
                "card_type": card.card_type,
                "oper_status_code": card.oper_status_code,
                "standby_code": card.standby_code,
                "cpu_pct": card.cpu_pct,
                "mem_pct": card.mem_pct,
            }
            for card in sorted(reading.cards.values(), key=lambda c: c.slot)
        ],
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
    purged, _ = OnuEvent.objects.filter(at__lt=now - timedelta(days=EVENT_RETENTION_DAYS)).delete()
    return {
        **last_run,
        "olts": len(olts),
        "onus_seen": onus_seen,
        "transitions": transitions,
        "events_purged": purged,
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
        "rx_worst_dbm": round(min(rx_values), 1) if rx_values else None,
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


# EV-0101: função da placa pelo prefixo do tipo (ZTE: GTGH/GTGO/GPFA/ETGO, SCXN/SCXM, HUVQ/XUTQ/GUFQ,
# PRWH/PRAM).
# EV-0103: C600 GFGH/GFBT, C610 GVGH (PON) · SFUQ/SFUC (controlo) · PRVR/PUMD (energia) ·
# FCVDIC/FUMO (ventilação).
_CARD_ROLES = (
    (("GT", "GP", "ET", "EP", "GF", "GV"), "pon"),
    (("SC", "SF"), "control"),
    (("HU", "XU", "GU"), "uplink"),
    (("PR", "PU"), "power"),
    (("FC", "FU", "FA"), "fan"),
)
# A C300 tem 21 baias fixas (0..20); os outros chassis ZTE desenham-se com as baias que o
# Zabbix mostra (placas e interfaces), do menor ao maior slot.
_C300_BAYS = [0, 20]
# EV-0106: a C600 tem 17 baias de placa (1..17); alarga-se até ao maior slot que o Zabbix mostrar
# (energia 18/20 e ventilação 21 na CONFRESA).
_MIN_BAYS = {"C600": (1, 17)}
_STANDBY = {1: "active", 2: "standby"}


def card_role(card_type: str) -> str:
    upper = (card_type or "").upper()
    for prefixes, role in _CARD_ROLES:
        if upper.startswith(prefixes):
            return role
    return "other"


def _port_entry(port_id: str, status: str) -> dict[str, Any]:
    return {"port_id": port_id, "port": int(port_id.split("/")[1]), "status": status}


def _chassis_payload(
    vendor: str, meta: Mapping[str, Any] | None, pons: list[dict[str, Any]]
) -> dict[str, Any]:
    """Vista frontal (EV-0101): placas e portas que o Zabbix deu na última coleta desta OLT."""
    port_status: dict[str, str] = dict((meta or {}).get("pon_status") or {})
    if vendor == parsers.VENDOR_ZTE:
        by_slot: dict[int, list[str]] = defaultdict(list)
        for port_id in port_status:
            slot, _, port = port_id.partition("/")
            if slot.isdigit() and port.isdigit():
                by_slot[int(slot)].append(port_id)
        slots = []
        for card in (meta or {}).get("cards") or []:
            code = card.get("oper_status_code")
            slots.append(
                {
                    "slot": card["slot"],
                    "card_type": card["card_type"],
                    "role": card_role(card["card_type"]),
                    "in_service": None if code is None else code == 1,
                    "oper_status_code": code,
                    "standby": _STANDBY.get(card.get("standby_code")),
                    "cpu_pct": card.get("cpu_pct"),
                    "mem_pct": card.get("mem_pct"),
                    "ports": [
                        _port_entry(port_id, port_status[port_id])
                        for port_id in sorted(
                            by_slot.get(card["slot"], []), key=parsers.pon_sort_key
                        )
                    ],
                }
            )
        model = ((meta or {}).get("model") or "").upper() or None
        known = [s["slot"] for s in slots] + list(by_slot)
        if model in (None, "C300"):
            layout, bays = "zte_c300", list(_C300_BAYS)
        else:
            layout = "zte_modular"
            low, high = _MIN_BAYS.get(model, (None, None))
            edges = known + [v for v in (low, high) if v is not None]
            bays = [min(edges), max(edges)] if edges else []
        return {"layout": layout, "model": model, "bays": bays, "slots": slots, "ports": []}

    ports = {port_id: status for port_id, status in port_status.items() if "/" in port_id}
    for pon in pons:
        ports.setdefault(pon["pon_id"], parsers.PON_UNKNOWN)
    return {
        "layout": "rack_1u",
        "model": (meta or {}).get("model") or None,
        "bays": [],
        "slots": [],
        "ports": [
            _port_entry(port_id, ports[port_id])
            for port_id in sorted(ports, key=parsers.pon_sort_key)
            if port_id.split("/")[1].isdigit()
        ],
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
            "technology",
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
    # EV-0097: a tecnologia é a que a coleta leu da OLT (uma VSOL pode ser GPON).
    technologies: dict[int, Counter[str]] = defaultdict(Counter)
    for state in states:
        technologies[state.device_id][state.technology] += 1
    for state in states:
        onus_by_olt[state.device_id].append(
            _onu_payload(state, device_by_id[state.device_id].name, now, warning, critical)
        )

    metas = cache.get_many([OLT_CACHE_KEY.format(device_id=pk) for pk in device_by_id])
    olt_payloads: list[dict[str, Any]] = []
    all_onus: list[dict[str, Any]] = []
    for device, vendor in olts:
        meta = metas.get(OLT_CACHE_KEY.format(device_id=device.pk))
        counted = technologies.get(device.pk)
        technology = (
            counted.most_common(1)[0][0] if counted else parsers.TECHNOLOGY_BY_VENDOR[vendor]
        )
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
                # EV-0107: «Ver no mapa» foca o POP da OLT no mapa backbone
                "site_id": device.site_id,
                "status": status,
                "collection_ok": collection_ok,
                "cpu_pct": (meta or {}).get("cpu_pct"),
                "temperature_c": (meta or {}).get("temperature_c"),
                "onus_total": len(onus),
                "onus_online": sum(1 for o in onus if o["status"] == parsers.STATUS_ONLINE),
                "pons": pons,
                "chassis": _chassis_payload(vendor, meta, pons),
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


def _event_kind(status: str, reason: str) -> str:
    if status == parsers.STATUS_ONLINE:
        return "online"
    if reason in (parsers.REASON_LOS, parsers.REASON_DYING_GASP):
        return reason
    return "offline"


def pon_events(
    device_id: int, pon_id: str, hours: int = EVENTS_HOURS_DEFAULT, now: datetime | None = None
) -> dict[str, Any]:
    """Eventos de uma PON nas últimas ``hours`` horas, do mais recente (EV-0108).

    ``since`` é o evento mais antigo guardado (início do registo ou da retenção): o ecrã
    diz «registo desde …» em vez de dar a entender que antes não houve quedas.
    """
    now = now or timezone.now()
    hours = max(1, min(int(hours), EVENTS_HOURS_MAX))
    get_object_or_404(Device, pk=device_id)
    qs = (
        OnuEvent.objects.filter(
            device_id=device_id, pon_id=pon_id, at__gte=now - timedelta(hours=hours)
        )
        .select_related("onu")
        .order_by("-at", "-pk")
    )
    rows = list(qs[: EVENTS_LIMIT + 1])
    first = OnuEvent.objects.order_by("at").values_list("at", flat=True).first()
    return {
        "device_id": device_id,
        "pon_id": pon_id,
        "hours": hours,
        "since": _iso(first) if first else None,
        "truncated": len(rows) > EVENTS_LIMIT,
        "events": [
            {
                "at": _iso(e.at),
                "onu_id": e.onu_id,
                "onu_index": e.onu.onu_index,
                "serial": e.onu.serial or None,
                "mac": e.onu.mac or None,
                "cliente_nome": e.onu.cliente_nome or None,
                "kind": _event_kind(e.status, e.reason),
                "label": e.reason_label or None,
                "previous_kind": (
                    _event_kind(e.previous_status, e.previous_reason) if e.previous_status else None
                ),
            }
            for e in rows[:EVENTS_LIMIT]
        ],
    }


def zte_pon_ifindex(pon_id: str, rack: int = 1) -> int | None:
    """«slot/porta» → ``ifIndex`` ZTE ``0x11 RR SS PP`` (inversa de ``zte_pon_from_ifindex``)."""
    try:
        slot, port = (int(x) for x in str(pon_id).split("/"))
    except (TypeError, ValueError):
        return None
    if not (0 <= slot <= 0xFF and 0 <= port <= 0xFF):
        return None
    return (parsers.ZTE_GPON_IFINDEX_TYPE << 24) | (rack << 16) | (slot << 8) | port


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _hourly_rx(trends: list[Mapping[str, Any]], rx_itemids: set[str]) -> list[dict[str, Any]]:
    """Por hora: média das médias e pior mínimo das ONUs, só com horas «limpas».

    Uma hora cujo mínimo sai da gama de dBm (a ZTE devolve -80 com a ONU offline) mistura
    sentinela com sinal real — fica de fora dessa ONU nessa hora, em vez de puxar a média.
    """
    by_clock: dict[int, list[tuple[float, float]]] = defaultdict(list)
    for t in trends:
        if str(t.get("itemid")) not in rx_itemids:
            continue
        low, avg = _num(t.get("value_min")), _num(t.get("value_avg"))
        if low is None or avg is None or not is_plausible_dbm(low) or not is_plausible_dbm(avg):
            continue
        by_clock[int(t["clock"])].append((avg, low))
    return [
        {
            "t": _iso(datetime.fromtimestamp(clock, tz=UTC)),
            "rx_avg_dbm": round(sum(a for a, _ in vals) / len(vals), 2),
            "rx_worst_dbm": round(min(low for _, low in vals), 2),
            "onus": len(vals),
        }
        for clock, vals in sorted(by_clock.items())
    ]


def _hourly_traffic(trends: list[Mapping[str, Any]], itemid: str | None) -> list[dict[str, Any]]:
    if not itemid:
        return []
    return [
        {
            "t": _iso(datetime.fromtimestamp(int(t["clock"]), tz=UTC)),
            "bps": _num(t.get("value_avg")),
        }
        for t in sorted(trends, key=lambda x: int(x["clock"]))
        if str(t.get("itemid")) == itemid
    ]


def pon_trend(device_id: int, pon_id: str, now: datetime | None = None) -> dict[str, Any]:
    """Tendência de 24 h do RX da PON e tráfego da porta (EV-0109), em cache 5 min.

    RX: tendências HORÁRIAS do Zabbix (``trend.get``, uma chamada para todas as ONUs) — não
    um ``history.get`` por ONU. A hora em curso ainda não tem tendência: o ecrã junta-lhe o
    RX médio da última coleta. Tráfego: ZTE pelo ``ifIndex`` da PON; a VSOL não expõe tráfego
    por PON no Zabbix (só as GE de uplink) → ``traffic.available`` false.
    """
    now = now or timezone.now()
    device = get_object_or_404(Device.objects.only("id", "zabbix_hostid", "name"), pk=device_id)
    key = TREND_CACHE_KEY.format(device_id=device_id, pon_id=pon_id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    states = list(
        OnuState.objects.filter(device_id=device_id, pon_id=pon_id)
        .exclude(rx_item_key="")
        .values_list("vendor", "rx_item_key")
    )
    vendor = states[0][0] if states else ("zte" if "ZTE" in device.name.upper() else "vsol")
    rx_keys = sorted({k for _, k in states})
    ifindex = zte_pon_ifindex(pon_id) if vendor == parsers.VENDOR_ZTE else None
    traffic_keys = (
        {"in": f"net.if.in[ifHCInOctets.{ifindex}]", "out": f"net.if.out[ifHCOutOctets.{ifindex}]"}
        if ifindex is not None
        else {}
    )
    payload: dict[str, Any] = {
        "device_id": device_id,
        "pon_id": pon_id,
        "hours": TREND_HOURS,
        "rx": [],
        "traffic": {
            "available": bool(traffic_keys),
            "in_bps": None,
            "out_bps": None,
            "at": None,
            "stale": False,
            "in": [],
            "out": [],
        },
        "zabbix_ok": True,
        "zabbix_error": None,
    }
    hostid = str(device.zabbix_hostid or "")
    if not hostid or not (rx_keys or traffic_keys):
        cache.set(key, payload, TREND_CACHE_SECONDS)
        return payload
    try:
        items = _request(
            "item.get",
            {
                "hostids": [hostid],
                "filter": {"key_": rx_keys + list(traffic_keys.values())},
                "output": ["itemid", "key_", "lastvalue", "lastclock"],
            },
        )
        by_key = {str(i.get("key_")): i for i in items if isinstance(i, Mapping)}
        rx_ids = {str(by_key[k]["itemid"]) for k in rx_keys if k in by_key}
        traffic_ids = {d: str(by_key[k]["itemid"]) for d, k in traffic_keys.items() if k in by_key}
        till = int(now.timestamp())
        trends = []
        if rx_ids or traffic_ids:
            trends = _request(
                "trend.get",
                {
                    "itemids": sorted(rx_ids | set(traffic_ids.values())),
                    "time_from": till - TREND_HOURS * 3600,
                    "time_till": till,
                    "output": ["itemid", "clock", "value_min", "value_avg", "value_max"],
                },
            )
        payload["rx"] = _hourly_rx(trends, rx_ids)
        traffic = payload["traffic"]
        traffic["available"] = bool(traffic_ids)
        traffic["in"] = _hourly_traffic(trends, traffic_ids.get("in"))
        traffic["out"] = _hourly_traffic(trends, traffic_ids.get("out"))
        if traffic_ids:
            last_in = by_key[traffic_keys["in"]] if "in" in traffic_ids else {}
            last_out = by_key[traffic_keys["out"]] if "out" in traffic_ids else {}
            clock = (
                max(int(_num(x.get("lastclock")) or 0) for x in (last_in, last_out) if x)
                if (last_in or last_out)
                else 0
            )
            if clock > 0:
                traffic["in_bps"] = _num(last_in.get("lastvalue")) if last_in else None
                traffic["out_bps"] = _num(last_out.get("lastvalue")) if last_out else None
                traffic["at"] = _iso(datetime.fromtimestamp(clock, tz=UTC))
                traffic["stale"] = till - clock > TRAFFIC_STALE_SECONDS
    except ZabbixUnavailable as exc:
        payload["zabbix_ok"] = False
        payload["zabbix_error"] = str(exc)
        return payload  # sem cache: tenta de novo no próximo pedido
    cache.set(key, payload, TREND_CACHE_SECONDS)
    return payload


# ── EV-0111: resumo por OLT para os cards do modal de Site ───────────────────


def olt_summaries(device_ids: Iterable[int], now: datetime | None = None) -> dict[str, Any]:
    """ONUs online/total e alertas ópticos por OLT, para os ``device_ids`` que são OLT.

    Mesmas regras do ecrã GPON (ONU sem coleta há mais de ``STALE_AFTER`` = desconhecida,
    sinal pelos limiares da configuração), mas sem a lista de ONUs: uma consulta agregada
    em vez dos ~2 MB da visão geral. Quem não é OLT simplesmente não aparece.
    """
    now = now or timezone.now()
    warning, critical, _ = _thresholds()
    wanted = {int(pk) for pk in device_ids}
    olts = {device.pk: (device, vendor) for device, vendor in olt_devices() if device.pk in wanted}
    out: dict[str, dict[str, Any]] = {
        str(pk): {
            "vendor": vendor,
            "technology": parsers.TECHNOLOGY_BY_VENDOR[vendor],
            "onus_total": 0,
            "onus_online": 0,
            "signal_warning": 0,
            "signal_critical": 0,
        }
        for pk, (_, vendor) in olts.items()
    }
    technologies: dict[int, Counter[str]] = defaultdict(Counter)
    rows = OnuState.objects.filter(device_id__in=list(olts)).values_list(
        "device_id", "technology", "status", "rx_onu_dbm", "rx_olt_dbm", "last_seen"
    )
    for device_id, technology, status, rx_onu, rx_olt, last_seen in rows:
        item = out[str(device_id)]
        technologies[device_id][technology] += 1
        item["onus_total"] += 1
        if last_seen < now - STALE_AFTER:
            continue
        if status == parsers.STATUS_ONLINE:
            item["onus_online"] += 1
        signal = rules.classify_signal(rules.signal_dbm(rx_onu, rx_olt), warning, critical)
        if signal == rules.SIGNAL_WARNING:
            item["signal_warning"] += 1
        elif signal == rules.SIGNAL_CRITICAL:
            item["signal_critical"] += 1
    for device_id, counted in technologies.items():
        out[str(device_id)]["technology"] = counted.most_common(1)[0][0]
    return {"olts": out}
