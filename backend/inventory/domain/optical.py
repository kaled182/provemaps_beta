from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, cast

from integrations.zabbix.zabbix_service import zabbix_request
from inventory.models import Port
from inventory.services.fiber_status import fetch_interface_status_advanced

logger = logging.getLogger(__name__)

__all__ = [
    "_safe_float",
    "_fetch_item_value",
    "_discover_optical_keys_by_portname",
    "OPTICAL_KEY_FAMILIES",
    "classify_optical_item",
    "match_optical_keys",
    "match_optical_keys_for_ports",
    "optical_item_port_refs",
    "optical_key_family",
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


# --- EV-0086: o que é uma potência óptica (regra única da descoberta de chaves) -------------
#
# A descoberta de chaves (`persist_keys=True`: descoberta/importação de equipamentos, ecrãs de
# portas) só propõe ou grava uma chave óptica quando o item É uma potência óptica. Critério
# positivo e obrigatório: a UNIDADE do item (`units` = dBm, sem distinguir maiúsculas). Sem
# unidade no template, aceita-se só uma família conhecida (`OPTICAL_KEY_FAMILIES`). E a porta
# tem de ser a do item por correspondência EXATA (nome da interface ou índice), nunca `LIKE`;
# com mais de um candidato não se escolhe. Na dúvida, sem chave.

OPTICAL_POWER_UNITS = frozenset({"dbm"})

# Famílias de chaves de potência óptica conhecidas: prefixo (minúsculas) → sentido.
# Lista ÚNICA — lida por `classify_optical_item` e por `devices_common._identify_item_role`.
# - Huawei: `hwEntityOpticalLaneRxPower[<entidade>]` / `hwEntityOpticalLaneTxPower[<entidade>]`
#   (dBm, multiplicador 0,01); a porta vem do nome do item («… na interface XGigabitEthernet0/0/9»).
# - ZTE «OLT ZTE GPON»: `onu.rx[<serial>,<slot>,<pon>,<onu>]` — RX na OLT (upstream), dBm,
#   multiplicador 0,001. Não há item de TX por ONU (não se inventa TX).
# - VSOL: `SinalRXS0P<pon>[<interface> - <onu>]` — RX da ONU (há templates sem unidade).
#   Não há item de TX: a mesma chave nunca serve de TX.
OPTICAL_KEY_FAMILIES: tuple[tuple[str, str], ...] = (
    ("hwentityopticallanerxpower[", "rx"),
    ("hwentityopticallanetxpower[", "tx"),
    ("onu.rx[", "rx"),
    ("sinalrxs0p", "rx"),
)

# Nunca são potência óptica, mesmo com unidade dBm mal configurada ou nome enganador
# (EV-0081: `net.if.in[ifHCInOctets…]` em bps e `olt[power0|1]` em W foram gravados como RX/TX).
NON_OPTICAL_KEY_MARKERS: tuple[str, ...] = (
    # tráfego
    "net.if.in",
    "net.if.out",
    "ifhcinoctets",
    "ifhcoutoctets",
    "ifinoctets",
    "ifoutoctets",
    # energia (fonte de alimentação da OLT, W)
    "olt[power",
    # estado
    "status",
    "operstat",
    "adminstat",
    "lastdowntime",
)
# Itens em dBm que não são a potência medida (limiares do transceptor) e grandezas vizinhas.
NON_OPTICAL_WORDS: tuple[str, ...] = (
    "threshold",
    "warn",
    "alarm",
    "limit",
    "bias",
    "temperature",
    "voltage",
    "fault",
)
# `value_type` do Zabbix: 0 float, 3 inteiro; 1/2/4 (carácter, log, texto) não são medidas.
NUMERIC_VALUE_TYPES = frozenset({"0", "3"})
LLD_MACRO_MARK = "{#"
_RX_WORDS = ("rx", "receiv", "recebid", "input")
_TX_WORDS = ("tx", "transmit", "output")

_INTERFACE_IN_NAME_RE = re.compile(r"\binterface\s+(\S+)\s*$", re.IGNORECASE)
_ONU_RX_KEY_RE = re.compile(r"^onu\.rx\[([^,\]]+),(\d+),(\d+),(\d+)\]$", re.IGNORECASE)
_HUAWEI_LANE_PREFIXES = ("hwentityopticallanerxpower[", "hwentityopticallanetxpower[")

# Campos do `item.get` que a descoberta precisa (um pedido por host).
DISCOVERY_ITEM_OUTPUT = [
    "itemid",
    "key_",
    "name",
    "units",
    "value_type",
    "state",
    "lastvalue",
    "lastclock",
]
DISCOVERY_ITEMS_CACHE_PREFIX = "__items__:"


def optical_key_family(key: str | None) -> str | None:
    """Return ``"rx"``/``"tx"`` when the key belongs to a known optical power family."""
    key_lower = (key or "").strip().lower()
    for prefix, direction in OPTICAL_KEY_FAMILIES:
        if key_lower.startswith(prefix):
            return direction
    return None


def _current_value_problem(item: Mapping[str, Any], key: str) -> str | None:
    """Why the item's CURRENT reading shows it is not a dBm power (``None`` if it may be).

    Só com leitura atual no ``item.get`` (``lastclock`` > 0 e valor numérico). Ex.: os
    Huawei sem DDM (portas 334/514, EV-0081) leem TX = 32,2471 «dBm». Os sentinelas de
    ONU (0/-80 em `onu.rx`/`SinalRXS0P`) não desqualificam o item: são ONU sem leitura.
    """
    try:
        lastclock = int(str(item.get("lastclock") or "0").strip())
    except (TypeError, ValueError):
        lastclock = 0
    value = _safe_float(item.get("lastvalue"))
    if lastclock <= 0 or value is None or is_plausible_dbm(value):
        return None
    if key.lower().startswith(OPTICAL_SENTINEL_KEY_PREFIXES) and value in OPTICAL_SENTINEL_VALUES:
        return None
    return f"lê {value:g}, fora de {OPTICAL_DBM_MIN:g}…+{OPTICAL_DBM_MAX:g} dBm"


def classify_optical_item(item: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Return ``(direction, None)`` for an optical power item, ``(None, reason)`` otherwise."""
    key = str(item.get("key_") or "").strip()
    if not key:
        return None, "item sem chave"
    key_lower = key.lower()
    if LLD_MACRO_MARK in key:
        return None, "macro LLD por expandir na chave"
    if any(marker in key_lower for marker in NON_OPTICAL_KEY_MARKERS):
        return None, "chave de tráfego, energia ou estado"
    text = f"{key_lower} {str(item.get('name') or '').lower()}"
    if any(word in text for word in NON_OPTICAL_WORDS):
        return None, "limiar/alarme/bias/temperatura, não potência medida"
    raw_value_type = item.get("value_type")
    value_type = "" if raw_value_type is None else str(raw_value_type).strip()
    if value_type and value_type not in NUMERIC_VALUE_TYPES:
        return None, f"value_type {value_type} não numérico"

    if str(item.get("state") or "").strip() == "1":
        return None, "item unsupported no Zabbix"
    current_problem = _current_value_problem(item, key)
    if current_problem:
        return None, current_problem

    family = optical_key_family(key)
    units = str(item.get("units") or "").strip().lower()
    if units:
        if units not in OPTICAL_POWER_UNITS:
            return None, f"unidade {units!r} não é dBm"
    elif family is None:
        return None, "sem unidade e fora das famílias conhecidas"
    if family is not None:
        return family, None

    is_rx = any(word in text for word in _RX_WORDS)
    is_tx = any(word in text for word in _TX_WORDS)
    if is_rx == is_tx:
        return None, "sentido RX/TX indefinido"
    return ("rx" if is_rx else "tx"), None


def _key_params(key: str) -> list[str]:
    if "[" not in key or not key.endswith("]"):
        return []
    inside = key[key.index("[") + 1 : -1]
    return [part.strip().strip('"').strip("'") for part in inside.split(",") if part.strip()]


def _zte_onu_port_names(slot: int, pon: int, onu: int) -> set[str]:
    """Port names of a ZTE ONU: ``<ifIndex da PON>.<onu>``, ifIndex antigo ou novo.

    Antigo (template `zxolt*`, nomes das portas do inventário): ``0x10SSPP00``;
    novo (template «OLT ZTE GPON», `ifOperStatus[<ifIndex>]`): ``0x1101SSPP``.
    """
    old_ifindex = (0x10 << 24) | (slot << 16) | (pon << 8)
    new_ifindex = (0x1101 << 16) | (slot << 8) | pon
    return {f"{old_ifindex}.{onu}", f"{new_ifindex}.{onu}"}


def optical_item_port_refs(item: Mapping[str, Any]) -> set[str]:
    """Return the port names (casefolded) an optical item refers to, by exact identity.

    Huawei: interface no fim do nome do item; ZTE `onu.rx`: posição (slot, PON, ONU) no
    formato ``<ifIndex>.<onu>``; VSOL: interface antes de `` - `` na chave e no fim do nome;
    outros: parâmetros da chave, interface no fim do nome, prefixo do nome antes de ``:``.
    """
    key = str(item.get("key_") or "").strip()
    key_lower = key.lower()
    name = str(item.get("name") or "").strip()
    refs: set[str] = set()
    if key_lower.startswith(_HUAWEI_LANE_PREFIXES):
        match = _INTERFACE_IN_NAME_RE.search(name)
        if match:
            refs.add(match.group(1))
    elif key_lower.startswith("onu.rx["):
        onu_match = _ONU_RX_KEY_RE.match(key)
        if onu_match:
            slot, pon, onu = (int(onu_match.group(i)) for i in (2, 3, 4))
            refs |= _zte_onu_port_names(slot, pon, onu)
    elif key_lower.startswith("sinalrxs0p"):
        params = _key_params(key)
        if len(params) == 1:
            refs.add(params[0].split(" - ")[0])
        if " - " in name:
            refs.add(name.rsplit(" - ", 1)[1])
    else:
        refs.update(_key_params(key))
        match = _INTERFACE_IN_NAME_RE.search(name)
        if match:
            refs.add(match.group(1))
        if ":" in name:
            refs.add(name.split(":", 1)[0])
    return {
        ref.strip().casefold()
        for ref in refs
        if ref.strip() and LLD_MACRO_MARK not in ref and ref.strip().casefold() != "null"
    }


def match_optical_keys_for_ports(
    port_names: Iterable[str | None],
    items: Iterable[Mapping[str, Any]],
    *,
    hostid: Any = None,
) -> dict[str, dict[str, str | None]]:
    """Map each port name to ``{"rx": key|None, "tx": key|None}`` (EV-0086).

    Só itens que `classify_optical_item` aceita, só correspondência exata
    (`optical_item_port_refs`), e só com UM candidato por sentido — com dois ou mais a
    porta fica sem chave nesse sentido e o motivo vai para o log.
    """
    by_ref: dict[str, dict[str, set[str]]] = {}
    for item in items:
        direction, _reason = classify_optical_item(item)
        if direction is None:
            continue
        key = str(item.get("key_") or "").strip()
        for ref in optical_item_port_refs(item):
            by_ref.setdefault(ref, {"rx": set(), "tx": set()})[direction].add(key)

    result: dict[str, dict[str, str | None]] = {}
    for port_name in port_names:
        if not port_name:
            continue
        candidates = by_ref.get(port_name.strip().casefold(), {"rx": set(), "tx": set()})
        chosen: dict[str, str | None] = {"rx": None, "tx": None}
        for direction in ("rx", "tx"):
            keys = sorted(candidates[direction])
            if len(keys) == 1:
                chosen[direction] = keys[0]
            elif keys:
                logger.info(
                    "EV-0086: host %s, porta %r: %d candidatos %s em dBm (%s) — fica sem chave",
                    hostid,
                    port_name,
                    len(keys),
                    direction.upper(),
                    ", ".join(keys[:5]),
                )
        if chosen["rx"] and chosen["rx"] == chosen["tx"]:
            chosen["tx"] = None
        result[port_name] = chosen
    return result


def match_optical_keys(
    port_name: str,
    items: Iterable[Mapping[str, Any]],
    *,
    hostid: Any = None,
) -> dict[str, str | None]:
    """Single-port form of `match_optical_keys_for_ports`."""
    matched = match_optical_keys_for_ports([port_name], items, hostid=hostid)
    return matched.get(port_name, {"rx": None, "tx": None})


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


def _host_items_for_discovery(
    hostid: Any,
    cache: dict[Any, Any] | None,
) -> list[dict[str, Any]]:
    """Active items of a host for key discovery — one ``item.get`` per host (cached)."""
    cache_key = (f"{DISCOVERY_ITEMS_CACHE_PREFIX}{hostid}", None)
    if cache is not None and cache_key in cache:
        return cast(list[dict[str, Any]], cache[cache_key].get("items") or [])
    items = cast(
        list[dict[str, Any]],
        zabbix_request(
            "item.get",
            {
                "output": DISCOVERY_ITEM_OUTPUT,
                "hostids": [str(hostid)],
                "filter": {"status": "0"},
            },
        )
        or [],
    )
    if cache is not None:
        cache[cache_key] = {"items": items}
    return items


def _discover_optical_keys_by_portname(
    hostid: Any,
    port_name: str | None,
    cache: dict[Any, Any] | None = None,
) -> dict[str, str | None]:
    """Discover the optical power items of a port by its name.

    EV-0086: um só ``item.get`` por host (guardado em ``cache``) e a regra única
    ``match_optical_keys``: só potências ópticas (unidade dBm ou família conhecida) cujo
    nome de interface/índice é EXATAMENTE o nome da porta; mais de um candidato → sem
    chave. Antes: ``LIKE %<nome>%`` no Zabbix e pontuação por palavras («input»,
    «power»), que atribuía tráfego, a fonte da OLT e itens de outras ONU.
    Returns ``{"rx": key, "tx": key}`` with ``None`` when nothing is found.
    """
    cache_key: tuple[str, str | None] = (str(hostid), port_name)
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    result: dict[str, str | None] = {"rx": None, "tx": None}
    if hostid and port_name:
        items = _host_items_for_discovery(hostid, cache)
        result = match_optical_keys(port_name, items, hostid=hostid)
    if cache is not None:
        cache[cache_key] = result
    return result


def _resolve_optical_keys(
    port: Port,
    hostid: str,
    discovery_cache: dict[Any, Any],
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
                port_name=port.name or None,
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

    # EV-0086: `fiber_status` só devolve `rx_key`/`tx_key` descobertos pela regra única
    # (`match_optical_keys`); o antigo `rx_key_generic` («rx» em qualquer chave) acabou.
    if status_meta.get("rx_key"):
        rx_key = str(status_meta["rx_key"]).strip()
    if status_meta.get("tx_key"):
        tx_key = str(status_meta["tx_key"]).strip()

    # EV-0082: a descoberta pelo nome da porta (EV-0086: correspondência exata, só
    # potências ópticas, um candidato) só corre quando as chaves
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
    persist_keys: bool = False,
    include_status_meta: bool = True,
    value_cache: ValueCache | None = None,
) -> dict[str, Any]:
    """Public wrapper for ``_fetch_port_optical_snapshot``.

    Exposed to avoid importing the private helper from downstream modules while
    keeping the original implementation intact. Delegates all parameters to the
    internal function.

    EV-0090: ``persist_keys`` é False por omissão — ler nunca grava. Só quem descobre
    chaves (descoberta/importação de equipamentos) passa ``persist_keys=True``.
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
    discovery_cache: dict[Any, Any] | None = None,
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
    persist_keys: bool = False,
    include_status_meta: bool = True,
) -> dict[int, dict[str, Any]]:
    """Fetch optical snapshots for a sequence of ports with batching.

    EV-0090: ``persist_keys`` é False por omissão — ler nunca grava; a descoberta de
    equipamentos pede ``persist_keys=True`` explicitamente.
    """

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
