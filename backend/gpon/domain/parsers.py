"""Leitura dos itens do Zabbix das OLT (EV-0095) — módulo puro, sem Django.

Recebe a lista devolvida por UM ``item.get`` do host da OLT e devolve o que a coleta grava:
o estado de cada ONU e o estado da própria OLT. Nada aqui chama o Zabbix nem a base.

Fontes (levantadas em produção a 2026-11-24, só leitura):

- **ZTE C300 (GPON)** — ``onu.status[<serial>,<slot>,<pon>,<onu>]`` (texto online/offline),
  ``onu.offreason[…]`` (código numérico com valuemap no Zabbix), ``onu.rx[…]`` (RX **na OLT**,
  dBm; 0/-80 são sentinelas), ``onu.dist[…]`` (m; 0 = sem leitura). ``onu.last_offline`` não
  se usa: o relógio da OLT está errado (ADR 0010). Interfaces PON em
  ``ifOperStatus[<ifIndex>]`` com ``ifIndex = 0x11 RR SS PP`` (rack, slot, porta).
- **VSOL** — ``OnlineStateS<s>P<p>[…]`` (1 online, 2 offline, outro = desconhecido) e
  ``SinalRXS<s>P<p>[…]`` (RX **na ONU**; 0 = sem leitura). O parâmetro da chave varia entre
  OLTs (``GPON0/1:10 - 10`` numas, ``<mac> - <n>`` noutras); a posição e o identificador saem do
  NOME do item («Status da ONU 0/<p>/<n> - <mac ou serial> - <descrição>», «NULL» = vazio).

A validação da leitura óptica (item coletado e suportado, gama de dBm, sentinelas de ONU) é a
regra única ``inventory.domain.optical.validate_optical_reading``; entra aqui por parâmetro
(``validate_rx``) para este módulo não importar Django.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

RxValidator = Callable[
    [Mapping[str, Any] | None, float | None, str | None], tuple[float | None, str | None]
]

VENDOR_ZTE = "zte"
VENDOR_VSOL = "vsol"
TECHNOLOGY_GPON = "gpon"
TECHNOLOGY_EPON = "epon"
# Tecnologia por omissão do fabricante. Na VSOL decide a própria OLT (EV-0097): há VSOL GPON
# com «EPON» no nome (Furacão, Granada) — ONUs com serial GPON e interfaces «GPON0/<p>».
TECHNOLOGY_BY_VENDOR = {VENDOR_ZTE: TECHNOLOGY_GPON, VENDOR_VSOL: TECHNOLOGY_EPON}

STATUS_ONLINE = "online"
STATUS_OFFLINE = "offline"
STATUS_UNKNOWN = "unknown"

REASON_LOS = "los"
REASON_DYING_GASP = "dying_gasp"
REASON_OTHER = "other"

PON_UP = "up"
PON_DOWN = "down"
PON_UNKNOWN = "unknown"

# Famílias de chave pedidas ao Zabbix (``search`` com ``startSearch``): só o que se lê.
ZTE_KEY_FAMILIES: tuple[str, ...] = (
    "onu.status",
    "onu.offreason",
    "onu.rx",
    "onu.dist",
    "ifOperStatus",
    "cardcpu",
    # EV-0101: inventário das placas para o chassi (Card[<slot>] = tipo da placa).
    "Card[",
    "cardoperstat",
    "cardstandby",
    "cardmem",
    "cpu",
    "TempGeral",
    "sysDescr",
    "icmpping",
)
VSOL_KEY_FAMILIES: tuple[str, ...] = (
    "OnlineStateS",
    "SinalRXS",
    "ifOperStatus",
    "cpuLoad",
    "sysTemperature",
    "icmpping",
)
KEY_FAMILIES = {VENDOR_ZTE: ZTE_KEY_FAMILIES, VENDOR_VSOL: VSOL_KEY_FAMILIES}

# ``output`` mínimo do item.get: o nome só é preciso na VSOL (MAC e descrição vêm dele) e o
# valuemap só na ZTE (motivo da queda).
_BASE_OUTPUT = ["key_", "value_type", "lastvalue", "lastclock", "state"]
ITEM_OUTPUT = {
    VENDOR_ZTE: [*_BASE_OUTPUT, "valuemapid"],
    VENDOR_VSOL: [*_BASE_OUTPUT, "name"],
}

NUMERIC_VALUE_TYPES = frozenset({"0", "3"})


@dataclass
class OnuReading:
    onu_key: str
    pon_id: str
    onu_index: int | None
    serial: str = ""
    mac: str = ""
    description: str = ""
    status: str = STATUS_UNKNOWN
    raw_status: str = ""
    raw_reason: str = ""
    reason_valuemapid: str = ""
    rx_onu_dbm: float | None = None
    rx_olt_dbm: float | None = None
    distance_m: int | None = None
    rx_item_key: str = ""


@dataclass
class CardReading:
    """Placa de um slot ZTE (EV-0101). Códigos sem valuemap no Zabbix: ``oper_status_code`` 1 =
    em serviço; ``standby_code`` 1 = ativa, 2 = reserva (par SCXN 10/11 da BRV)."""

    slot: int
    card_type: str = ""
    oper_status_code: int | None = None
    standby_code: int | None = None
    cpu_pct: float | None = None
    mem_pct: float | None = None


@dataclass
class OltReading:
    vendor: str
    technology: str
    ping: int | None = None
    cpu_pct: float | None = None
    temperature_c: float | None = None
    model: str | None = None
    # «slot/porta» → up/down/unknown. No ZTE vem de TODAS as interfaces 0x11 (PON, controlo,
    # uplink); quem é PON decide-se pelas ONUs/placas.
    pon_status: dict[str, str] = field(default_factory=dict)
    onus: list[OnuReading] = field(default_factory=list)
    cards: dict[int, CardReading] = field(default_factory=dict)

    @property
    def has_known_onu(self) -> bool:
        """Alguma ONU com estado conhecido ou RX — senão a coleta desta OLT não deu nada."""
        return any(
            onu.status != STATUS_UNKNOWN or onu.rx_onu_dbm is not None or onu.rx_olt_dbm is not None
            for onu in self.onus
        )


# ---------------------------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------------------------


def detect_vendor(*texts: str | None) -> str | None:
    """Fabricante pelo nome/fabricante do equipamento: «ZTE» → zte, «VSOL»/«V-SOL» → vsol."""
    blob = " ".join(t for t in texts if t).upper()
    if "ZTE" in blob:
        return VENDOR_ZTE
    if "VSOL" in blob or "V-SOL" in blob:
        return VENDOR_VSOL
    return None


def current_value(item: Mapping[str, Any] | None) -> str | None:
    """``lastvalue`` só quando é leitura atual: item suportado (``state`` 0) e já coletado.

    O Zabbix devolve ``lastvalue "0"`` em itens nunca coletados (``lastclock`` 0) — o caso das
    196 ONUs da VSOL Nova Barreira. Isso não é «offline», é «sem dados».
    """
    if not item or str(item.get("state", "")).strip() != "0":
        return None
    try:
        lastclock = int(str(item.get("lastclock") or "0").strip())
    except (TypeError, ValueError):
        return None
    if lastclock <= 0:
        return None
    raw = item.get("lastvalue")
    if raw is None or not str(raw).strip():
        return None
    return str(raw).strip()


def _float(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return None


def _is_numeric(item: Mapping[str, Any]) -> bool:
    return str(item.get("value_type", "")).strip() in NUMERIC_VALUE_TYPES


def _rx(item: Mapping[str, Any], key: str, validate_rx: RxValidator) -> float | None:
    dbm, _problem = validate_rx(item, _float(item.get("lastvalue")), key)
    return dbm


def _oper_status(value: str | None) -> str:
    # IF-MIB ifOperStatus: 1 up, 2 down, 7 lowerLayerDown; o resto não se interpreta.
    if value in {"1"}:
        return PON_UP
    if value in {"2", "7"}:
        return PON_DOWN
    return PON_UNKNOWN


def _ping(value: str | None) -> int | None:
    number = _float(value)
    if number is None:
        return None
    return 1 if number >= 1 else 0


def pon_sort_key(pon_id: str) -> tuple[int, ...]:
    """«9/14» depois de «9/2» (ordem numérica, não alfabética)."""
    parts = []
    for part in str(pon_id).split("/"):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(10**6)
    return tuple(parts)


# ---------------------------------------------------------------------------------------------
# Motivo da queda (valuemap do Zabbix)
# ---------------------------------------------------------------------------------------------

_LOS_RE = re.compile(r"\blos[i]?\b|\blofi\b|loss", re.IGNORECASE)
_DYING_RE = re.compile(r"dying|gasp|power", re.IGNORECASE)


def classify_reason_text(text: str | None) -> str | None:
    """Texto do valuemap → ``los`` / ``dying_gasp`` / ``other``; sem texto → ``None``.

    Valuemap 1406 «Motivo Offline ONU» em produção: 2 LOS, 3 LOSi, 4 LOFi → los; 9 PowerOff →
    dying_gasp; 1 Desconhecido, 5 SFi, 6 LOAi, 7 LOAMi, 8 AuthFail, 10 DeactivateSucc,
    11 DeactivateFail, 12 Reboot, 13 Shutdown → other.
    """
    if not text or not str(text).strip():
        return None
    if _LOS_RE.search(text):
        return REASON_LOS
    if _DYING_RE.search(text):
        return REASON_DYING_GASP
    return REASON_OTHER


def valuemap_text(mappings: Iterable[Mapping[str, Any]] | None, code: str | None) -> str | None:
    """Texto do valuemap para o código (só correspondência exata, ``type`` 0). Nunca adivinha."""
    if not code or not mappings:
        return None
    for mapping in mappings:
        if str(mapping.get("type", "0")) != "0":
            continue
        if str(mapping.get("value", "")).strip() == str(code).strip():
            text = str(mapping.get("newvalue") or "").strip()
            return text or None
    return None


# ---------------------------------------------------------------------------------------------
# ZTE
# ---------------------------------------------------------------------------------------------

_ZTE_ONU_KEY = re.compile(r"^onu\.(status|offreason|rx|dist)\[([^,\]]+),(\d+),(\d+),(\d+)\]$")
_ZTE_IF_KEY = re.compile(r"^ifOperStatus\[(\d+)\]$")
_ZTE_CARD_TYPE = re.compile(r"^Card\[(\d+)\]$")
_ZTE_CARD_METRIC = re.compile(r"^card(operstat|standby|cpu|mem)\[\d+\.\d+\.(\d+)\]$")
_ZTE_MODEL = re.compile(r"^\s*([A-Za-z]\w+)\s+Version\b")
ZTE_GPON_IFINDEX_TYPE = 0x11


def zte_pon_from_ifindex(ifindex: int) -> str | None:
    """``ifIndex`` ZTE ``0x11 RR SS PP`` → «<slot>/<porta>» (só interfaces gpon-olt)."""
    if (ifindex >> 24) != ZTE_GPON_IFINDEX_TYPE:
        return None
    return f"{(ifindex >> 8) & 0xFF}/{ifindex & 0xFF}"


def _zte_status(value: str | None) -> str:
    text = (value or "").strip().lower()
    if text == "online":
        return STATUS_ONLINE
    if text == "offline":
        return STATUS_OFFLINE
    return STATUS_UNKNOWN


def parse_zte(items: Iterable[Mapping[str, Any]], *, validate_rx: RxValidator) -> OltReading:
    olt = OltReading(vendor=VENDOR_ZTE, technology=TECHNOLOGY_GPON)
    onus: dict[str, OnuReading] = {}
    card_cpus: list[float] = []
    cpu_total: float | None = None

    for item in items:
        key = str(item.get("key_") or "").strip()
        value = current_value(item)
        match = _ZTE_ONU_KEY.match(key)
        if match:
            family, serial, slot, pon, onu_number = match.groups()
            reading = onus.get(serial)
            if reading is None:
                reading = OnuReading(
                    onu_key=serial,
                    pon_id=f"{int(slot)}/{int(pon)}",
                    onu_index=int(onu_number),
                    serial=serial,
                )
                onus[serial] = reading
            if family == "status":
                reading.raw_status = value or ""
                reading.status = _zte_status(value)
            elif family == "offreason":
                reading.raw_reason = value or ""
                valuemapid = str(item.get("valuemapid") or "").strip()
                reading.reason_valuemapid = "" if valuemapid in {"", "0"} else valuemapid
            elif family == "rx":
                reading.rx_item_key = key if _is_numeric(item) else ""
                reading.rx_olt_dbm = _rx(item, key, validate_rx)
            elif family == "dist":
                distance = _float(value)
                reading.distance_m = int(distance) if distance and distance > 0 else None
            continue

        card_match = _ZTE_CARD_TYPE.match(key) or _ZTE_CARD_METRIC.match(key)
        if card_match:
            slot = int(card_match.group(card_match.lastindex or 1))
            card = olt.cards.setdefault(slot, CardReading(slot=slot))
            metric = card_match.group(1) if card_match.re is _ZTE_CARD_METRIC else "type"
            if metric == "type":
                card.card_type = (value or "").strip()
            elif metric in ("operstat", "standby"):
                number = _float(value)
                code = int(number) if number is not None else None
                if metric == "operstat":
                    card.oper_status_code = code
                else:
                    card.standby_code = code
            else:
                number = _float(value)
                if metric == "cpu":
                    card.cpu_pct = number
                    if number is not None:
                        card_cpus.append(number)
                else:
                    card.mem_pct = number
            continue

        if_match = _ZTE_IF_KEY.match(key)
        if if_match:
            pon_id = zte_pon_from_ifindex(int(if_match.group(1)))
            if pon_id:
                olt.pon_status[pon_id] = _oper_status(value)
        elif key == "icmpping":
            olt.ping = _ping(value)
        elif key == "cpu":
            cpu_total = _float(value)
        elif key == "TempGeral":
            olt.temperature_c = _float(value)
        elif key == "sysDescr" and value:
            model = _ZTE_MODEL.match(value)
            olt.model = model.group(1) if model else None

    # CPU: o item agregado quando coleta; senão a placa mais carregada (a pior é a que importa).
    olt.cpu_pct = cpu_total if cpu_total is not None else (max(card_cpus) if card_cpus else None)
    # Uma placa sem tipo (só métricas) não é inventário — fica de fora.
    olt.cards = {slot: card for slot, card in olt.cards.items() if card.card_type}
    olt.onus = list(onus.values())
    return olt


# ---------------------------------------------------------------------------------------------
# VSOL
# ---------------------------------------------------------------------------------------------

_VSOL_ONU_KEY = re.compile(r"^(OnlineState|SinalRX)S(\d+)P(\d+)\[(.*)\]$", re.IGNORECASE)
_VSOL_NAME = re.compile(r"ONU\s+(\d+)/(\d+)/(\d+)\s+-\s+(.*?)\s+-\s+(.*?)\s*$")
_VSOL_KEY_INDEX = re.compile(r"-\s*(\d+)\s*$")
_VSOL_IF_KEY = re.compile(r"^ifOperStatus\[[GE]PON(\d+)/(\d+)\]$", re.IGNORECASE)
_MAC_LIKE = re.compile(r"^[0-9a-fA-F]{1,4}([:.\-][0-9a-fA-F]{1,4})+$")
_MAC_OK = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")
_MAC_STRIPPED = re.compile(r"^[0-9a-f]{2,}(:[0-9a-f]{2,})+$")
# Serial GPON: 4 letras do fabricante + 8 hex (SHLN3C4CAB56, DACM91889c5c, ZYXE8caeed48).
_GPON_SERIAL = re.compile(r"^[A-Za-z]{4}[0-9A-Fa-f]{8}$")


def repair_vsol_mac(text: str) -> str:
    """Desfaz o defeito do template VSOL do Zabbix (EV-0099), que apaga «:0» do MAC:
    ``a8:bf:3c:35:0a:32`` chega como ``a8:bf:3c:35a:32``. Cada grupo tem o octeto de 2 hex e,
    a seguir, um hex por cada octeto «0X» que perdeu o «:0» — a inversão é única. Medido em
    produção (2026-11-24): 0 dos 165 MACs bem formados tinham «:0» (esperavam-se ~45) e os 91
    malformados dão todos exatamente 6 octetos. O que não encaixa fica como veio."""
    mac = text.lower()
    if _MAC_OK.match(mac) or not _MAC_STRIPPED.match(mac):
        return mac
    octets: list[str] = []
    for group in mac.split(":"):
        octets.append(group[:2])
        octets.extend(f"0{char}" for char in group[2:])
    return ":".join(octets) if len(octets) == 6 else mac


_INTERFACE_LIKE = re.compile(r"^[GE]PON\d+/\d+:\d+$", re.IGNORECASE)


def _clean(text: str | None) -> str:
    value = (text or "").strip()
    return "" if value.upper() == "NULL" else value


def _vsol_status(value: str | None) -> str:
    if value == "1":
        return STATUS_ONLINE
    if value == "2":
        return STATUS_OFFLINE
    return STATUS_UNKNOWN


def parse_vsol(items: Iterable[Mapping[str, Any]], *, validate_rx: RxValidator) -> OltReading:
    olt = OltReading(vendor=VENDOR_VSOL, technology=TECHNOLOGY_EPON)
    onus: dict[tuple[int, int, int | None], OnuReading] = {}
    if_prefixes: set[str] = set()

    for item in items:
        key = str(item.get("key_") or "").strip()
        value = current_value(item)
        match = _VSOL_ONU_KEY.match(key)
        if match:
            family, slot_raw, pon_raw, param = match.groups()
            slot, pon = int(slot_raw), int(pon_raw)
            name_match = _VSOL_NAME.search(str(item.get("name") or ""))
            ident = description = ""
            onu_index: int | None = None
            if name_match:
                onu_index = int(name_match.group(3))
                ident = _clean(name_match.group(4))
                description = _clean(name_match.group(5))
            else:
                index_match = _VSOL_KEY_INDEX.search(param)
                onu_index = int(index_match.group(1)) if index_match else None
            group = (slot, pon, onu_index)
            reading = onus.get(group)
            if ident and _MAC_LIKE.match(ident):
                ident = repair_vsol_mac(ident)
            if reading is None:
                base_key = f"{pon}:{onu_index if onu_index is not None else param}"
                reading = OnuReading(
                    onu_key=f"{base_key}|{ident.lower()}" if ident else base_key,
                    pon_id=f"{slot}/{pon}",
                    onu_index=onu_index,
                )
                onus[group] = reading
            if ident and not (reading.mac or reading.serial):
                if _MAC_LIKE.match(ident):
                    reading.mac = ident.lower()
                else:
                    reading.serial = ident
            if description and not _INTERFACE_LIKE.match(description) and not reading.description:
                reading.description = description
            if family.lower() == "onlinestate":
                reading.raw_status = value or ""
                reading.status = _vsol_status(value)
            else:
                reading.rx_item_key = key if _is_numeric(item) else ""
                reading.rx_onu_dbm = _rx(item, key, validate_rx)
            continue

        if_match = _VSOL_IF_KEY.match(key)
        if if_match:
            if_prefixes.add(key[len("ifOperStatus[") :][0].upper())
            olt.pon_status[f"{int(if_match.group(1))}/{int(if_match.group(2))}"] = _oper_status(
                value
            )
        elif key == "icmpping":
            olt.ping = _ping(value)
        elif key == "cpuLoad":
            olt.cpu_pct = _float(value)
        elif key == "sysTemperature":
            olt.temperature_c = _float(value)

    olt.onus = list(onus.values())
    olt.technology = vsol_technology(olt.onus, if_prefixes)
    return olt


def vsol_technology(onus: Iterable[OnuReading], if_prefixes: set[str]) -> str:
    """GPON ou EPON pela própria OLT (EV-0097): manda o identificador das ONUs (serial GPON vs
    MAC); sem ONUs identificadas, o nome das interfaces PON; sem nada, EPON."""
    serials = macs = 0
    for onu in onus:
        if onu.mac:
            macs += 1
        elif _GPON_SERIAL.match(onu.serial or ""):
            serials += 1
    if serials != macs:
        return TECHNOLOGY_GPON if serials > macs else TECHNOLOGY_EPON
    if if_prefixes == {"G"}:
        return TECHNOLOGY_GPON
    return TECHNOLOGY_EPON


PARSERS: dict[str, Callable[..., OltReading]] = {VENDOR_ZTE: parse_zte, VENDOR_VSOL: parse_vsol}


def parse_olt_items(
    vendor: str, items: Iterable[Mapping[str, Any]], *, validate_rx: RxValidator
) -> OltReading:
    return PARSERS[vendor](items, validate_rx=validate_rx)
