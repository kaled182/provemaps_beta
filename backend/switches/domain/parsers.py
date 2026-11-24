"""Itens Zabbix de um switch Huawei → interfaces e estado do equipamento (EV-0115). Puro.

Template Huawei em uso (medido em 2026-11-24, host 10679 «huawei - Switch Confresa»):

- por interface ``<família>[<ifName>]``: ``ifOperStatus`` (1 up, 2 down, 7 lowerLayerDown…),
  ``ifAdminStatus`` (1 up, 2 down), ``ifSpeed`` (Mbps), ``ifHCInOctets``/``ifHCOutOctets``
  (já em bps, a cada 30 s), ``ifInErrors``/``ifOutErrors``, ``InterfaceUptime`` (ms);
  o ``name`` do item termina em ``" - <descrição da porta>"``;
- óptico por índice de entidade: ``hwEntityOpticalLaneRxPower[<idx>]`` com o nome
  «Potência Recebida (RX) na interface XGigabitEthernet0/0/1» (idem TX);
- equipamento: ``icmpping``, ``hwCpuDevDuty`` (%), ``sensor.temp.value[...]`` (°C),
  ``sysDescr`` (1.ª linha = modelo, ex. «S6730-H24X6C»), ``sysUpTime`` (s).

Os ``…Log`` (ifOperStatusLog…) são duplicados para gráficos e ficam de fora.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

IF_FAMILIES = {
    "ifOperStatus": "oper",
    "ifAdminStatus": "admin",
    "ifSpeed": "speed_mbps",
    "ifHCInOctets": "in_bps",
    "ifHCOutOctets": "out_bps",
    "ifInErrors": "in_errors",
    "ifOutErrors": "out_errors",
    "InterfaceUptime": "uptime_ms",
}
OPTICAL_FAMILIES = {"hwEntityOpticalLaneRxPower": "rx_dbm", "hwEntityOpticalLaneTxPower": "tx_dbm"}
DEVICE_KEYS = ("icmpping", "hwCpuDevDuty", "sysDescr", "sysUpTime")
TEMPERATURE_PREFIX = "sensor.temp.value["

SEARCH_KEYS = [f"{f}[" for f in (*IF_FAMILIES, *OPTICAL_FAMILIES)] + [
    *DEVICE_KEYS,
    TEMPERATURE_PREFIX,
]
ITEM_OUTPUT = ["key_", "name", "lastvalue", "lastclock", "value_type"]

# Leitura com mais de 10 min não é estado atual (o tráfego vem a cada 30 s, o estado a cada 1 min).
STALE_SECONDS = 600
# A Huawei devolve -40 dBm sem luz no transceptor: é LOS, não uma medida.
LOS_DBM = -40.0
OPTICAL_DBM_MIN = -40.0
OPTICAL_DBM_MAX = 10.0
UTILIZATION_WARNING_PCT = 80.0

_KEY_RE = re.compile(r"^(?P<family>[A-Za-z]+)\[(?P<param>.+)\]$")
_OPTICAL_NAME_RE = re.compile(r"interface\s+(?P<ifname>\S+)", re.IGNORECASE)
_DESC_RE = re.compile(r"^.*?\S+\d(?:/\d+)+\s+-\s?(?P<desc>.*)$")

OPER_STATES = {
    1: "up",
    2: "down",
    3: "testing",
    4: "unknown",
    5: "dormant",
    6: "notPresent",
    7: "down",
}

KIND_PREFIXES = (
    ("MEth", "mgmt"),
    ("100GE", "optical"),
    ("40GE", "optical"),
    ("25GE", "optical"),
    ("XGigabitEthernet", "optical"),
    ("GigabitEthernet", "electrical"),
    ("Ethernet", "electrical"),
)
NOMINAL_SPEED_MBPS = (
    ("100GE", 100_000),
    ("40GE", 40_000),
    ("25GE", 25_000),
    ("XGigabitEthernet", 10_000),
    ("GigabitEthernet", 1_000),
    ("MEth", 1_000),
)

# Ordem de gravidade (para escolher a porta mais crítica e ordenar a tabela).
SEVERITY = {"down": 0, "critical": 1, "warning": 2, "unknown": 3, "normal": 4, "free": 5}


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def port_kind(ifname: str) -> str:
    for prefix, kind in KIND_PREFIXES:
        if ifname.startswith(prefix):
            return kind
    return "electrical"


def speed_label(mbps: float | None, ifname: str) -> str | None:
    """«10G»/«1G»/«40G»; com a porta em baixo o ifSpeed vem 0 → velocidade nominal pelo nome."""
    value = mbps if mbps else next((s for p, s in NOMINAL_SPEED_MBPS if ifname.startswith(p)), None)
    if not value:
        return None
    if value >= 1000:
        g = value / 1000
        return f"{g:g}G"
    return f"{value:g}M"


def description_from_name(name: str) -> str:
    """«Status Operacional da Porta XGigabitEthernet0/0/3 - To-Pedro» → «To-Pedro»."""
    match = _DESC_RE.match(name or "")
    return match.group("desc").strip() if match else ""


def parse_items(items: Iterable[Mapping[str, Any]], now_ts: float) -> dict[str, Any]:
    """``{"device": {...}, "interfaces": {ifName: {...}}}`` com ``None`` para o que falta ou é velho."""
    interfaces: dict[str, dict[str, Any]] = {}
    device: dict[str, Any] = {
        "ping": None,
        "cpu_pct": None,
        "temperature_c": None,
        "model": None,
        "uptime_s": None,
        "last_clock": None,
    }

    def iface(name: str) -> dict[str, Any]:
        return interfaces.setdefault(
            name,
            {
                "oper": None,
                "admin": None,
                "speed_mbps": None,
                "in_bps": None,
                "out_bps": None,
                "in_errors": None,
                "out_errors": None,
                "uptime_ms": None,
                "rx_dbm": None,
                "tx_dbm": None,
                "description": "",
                "last_clock": None,
            },
        )

    for item in items:
        key = str(item.get("key_") or "")
        clock = int(_num(item.get("lastclock")) or 0)
        fresh = clock > 0 and now_ts - clock <= STALE_SECONDS
        raw = item.get("lastvalue")
        if key in DEVICE_KEYS:
            if key == "sysDescr":
                first = str(raw or "").strip().splitlines()
                device["model"] = first[0].strip() if first and first[0].strip() else None
                continue
            if not fresh:
                continue
            device["last_clock"] = max(device["last_clock"] or 0, clock)
            value = _num(raw)
            if key == "icmpping":
                device["ping"] = None if value is None else int(value)
            elif key == "hwCpuDevDuty":
                device["cpu_pct"] = value
            elif key == "sysUpTime":
                device["uptime_s"] = value if value and value > 0 else None
            continue
        if key.startswith(TEMPERATURE_PREFIX):
            value = _num(raw)
            if fresh and value is not None and 0 < value <= 150:
                current = device["temperature_c"]
                device["temperature_c"] = value if current is None else max(current, value)
            continue
        match = _KEY_RE.match(key)
        if not match:
            continue
        family, param = match.group("family"), match.group("param")
        if family in IF_FAMILIES:
            entry = iface(param)
            if not entry["description"]:
                entry["description"] = description_from_name(str(item.get("name") or ""))
            if fresh:
                entry[IF_FAMILIES[family]] = _num(raw)
                entry["last_clock"] = max(entry["last_clock"] or 0, clock)
        elif family in OPTICAL_FAMILIES:
            name_match = _OPTICAL_NAME_RE.search(str(item.get("name") or ""))
            if not name_match:
                continue
            entry = iface(name_match.group("ifname"))
            value = _num(raw)
            if fresh and value is not None:
                entry[OPTICAL_FAMILIES[family]] = round(value, 2)
    return {"device": device, "interfaces": interfaces}


def classify_port(
    entry: Mapping[str, Any],
    ifname: str,
    *,
    warning: float,
    critical: float,
    has_cable: bool = False,
) -> dict[str, Any]:
    """Estado da porta para LED, KPIs e tabela.

    - ``unknown``: sem estado operacional recente;
    - ``free``: administrativamente desligada, ou sem link e sem descrição nem cabo;
    - ``down``: em uso e sem link, ou com RX de LOS (-40 dBm);
    - ``critical``/``warning``: RX abaixo dos limiares de backbone; ``warning`` também com a
      banda acima de 80 % da velocidade;
    - ``normal``.
    """
    oper_code = entry.get("oper")
    admin_code = entry.get("admin")
    oper = OPER_STATES.get(int(oper_code), "unknown") if oper_code is not None else None
    admin = "down" if admin_code == 2 else ("up" if admin_code == 1 else None)
    rx = entry.get("rx_dbm")
    los = rx is not None and rx <= LOS_DBM
    rx_valid = (
        rx if rx is not None and not los and OPTICAL_DBM_MIN < rx <= OPTICAL_DBM_MAX else None
    )
    speed = entry.get("speed_mbps") or 0
    traffic = [v for v in (entry.get("in_bps"), entry.get("out_bps")) if v is not None]
    utilization = round(max(traffic) / (speed * 1_000_000) * 100, 1) if speed and traffic else None
    described = bool(entry.get("description"))
    # Sem estado operacional não se sabe se está em uso (switch offline): não conta.
    in_use = oper is not None and admin != "down" and (oper == "up" or described or has_cable)
    reasons: list[str] = []

    if oper is None:
        state = "unknown"
    elif not in_use:
        state = "free"
    elif oper != "up" or los:
        state = "down"
        reasons.append("los" if los else "link_down")
    else:
        state = "normal"
        if rx_valid is not None and rx_valid < critical:
            state = "critical"
            reasons.append("rx_critical")
        elif rx_valid is not None and rx_valid <= warning:
            state = "warning"
            reasons.append("rx_warning")
        if utilization is not None and utilization > UTILIZATION_WARNING_PCT:
            reasons.append("utilization")
            if state == "normal":
                state = "warning"
    uptime_ms = entry.get("uptime_ms")
    return {
        "oper": oper or "unknown",
        "admin": admin or "unknown",
        "in_use": bool(in_use),
        "state": state,
        "reasons": reasons,
        "rx_dbm": rx_valid,
        "los": los,
        "utilization_pct": utilization,
        "uptime_s": int(uptime_ms / 1000) if uptime_ms and oper == "up" else None,
        "severity_rank": SEVERITY[state],
    }


def ifname_sort_key(ifname: str) -> tuple[Any, ...]:
    """MEth no fim; dentro de cada tipo, pela numeração (0/0/2 antes de 0/0/10)."""
    kind_order = {"electrical": 0, "optical": 1, "mgmt": 2}
    prefix = re.match(r"^[A-Za-z]+", ifname)
    numbers = tuple(int(n) for n in re.findall(r"\d+", ifname[prefix.end() if prefix else 0 :]))
    return (kind_order.get(port_kind(ifname), 0), prefix.group(0) if prefix else "", numbers)
