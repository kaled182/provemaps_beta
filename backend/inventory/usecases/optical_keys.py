"""EV-0081 — correção das chaves ópticas das portas e do host Zabbix do OLT BRV.

Diagnóstico em `doc/analysis/2026-11-23-ev0081-chaves-zabbix-portas.md` (propostas A e B).

`build_optical_key_plan()` só lê (ORM + 3 chamadas ao Zabbix pelo gateway) e devolve um dict
com as mudanças por equipamento e por porta. `apply_optical_key_plan()` grava esse plano numa
transação, depois de escrever uma cópia JSON dos valores antigos, e invalida as caches.

Regras (cada uma só toca no que o critério do relatório descreve; nunca «todas as portas»):

- **A** — Device 22 (`ZTE - OLT BRV C300`): `zabbix_hostid` 10694 → 10744, só se o 10694 já não
  existir no Zabbix e o 10744 existir com o mesmo nome do equipamento.
- **B / ZTE** (portas do device 22 com chaves `zxolt*`, `net.if.in[…]` ou `olt[power…]`):
  - porta-ONU (`name` = `<ifIndex>.<onu>`, chave `zxoltrxsignal.[<ifIndex>.<onu>]`, ifIndex
    antigo `0x10SSPP00`) com **um** item `onu.rx[<serial>,<slot>,<pon>,<onu>]` ativo no host
    novo → RX = essa chave, TX = "" (não há TX por ONU);
  - porta-ONU sem nenhum `onu.rx` na posição → "" / "";
  - porta-ONU com mais de um candidato ativo, ou só com itens LLD «perdidos» → sem
    correspondência (não muda);
  - portas de cartão (chave `zxolt*` noutra porta), de tráfego (`net.if.in[…]`) e de fonte
    (`olt[power…]`) → "" / "".
- **B / VSOL**: RX com macro LLD por expandir (`{#…}`) → "" / ""; RX `SinalRX…` igual ao TX →
  TX = "".
- **B / Huawei sem DDM**: porta com `hwEntityOpticalLane{Rx,Tx}Power[…]` cujo TX lê 32,2471 dBm
  (registo «todo a uns») e cujo RX está `unsupported` → "" / "".
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from django.db import transaction

from inventory.cache.fibers import invalidate_fiber_cache
from inventory.models import Device, Port
from inventory.usecases import devices_common as common
from maps_view.cache_swr import invalidate_dashboard_cache

# --- Proposta A -----------------------------------------------------------------------------
ZTE_DEVICE_ID = 22
ZTE_OLD_HOSTID = "10694"
ZTE_NEW_HOSTID = "10744"

# --- Padrões das chaves --------------------------------------------------------------------
ZXOLT_RX_RE = re.compile(r"^zxoltrxsignal\.\[(\d+)\.(\d+)\]$")
ZXOLT_ANY_RE = re.compile(r"^zxolt(?:rx|tx)signal\.\[")
ONU_PORT_NAME_RE = re.compile(r"^(\d+)\.(\d+)$")
ONU_RX_KEY_RE = re.compile(r"^onu\.rx\[([^,\]]+),(\d+),(\d+),(\d+)\]$")
NET_IF_IN_PREFIX = "net.if.in["
OLT_POWER_PREFIX = "olt[power"
VSOL_RX_PREFIX = "SinalRX"
LLD_MACRO_MARK = "{#"
HUAWEI_RX_PREFIX = "hwEntityOpticalLaneRxPower["
HUAWEI_TX_PREFIX = "hwEntityOpticalLaneTxPower["
# 10·log10(2^24 * 0,1 µW / 1 mW): o TX que o switch calcula de um registo inválido.
HUAWEI_NO_DDM_TX_DBM = 32.2471
HUAWEI_NO_DDM_TOLERANCE = 0.001

# Regras (o nome aparece no ensaio e no resumo).
RULE_DEVICE_HOSTID = "A_device_hostid"
RULE_ZTE_ONU = "zte_onu_para_onu_rx"
RULE_ZTE_ONU_SEM_ITEM = "zte_onu_sem_item"
RULE_ZTE_CARTAO = "zte_cartao"
RULE_ZTE_TRAFEGO = "zte_trafego_net_if_in"
RULE_ZTE_FONTE = "zte_fonte_olt_power"
RULE_VSOL_MACRO = "vsol_macro_lld"
RULE_VSOL_RX_IGUAL_TX = "vsol_rx_igual_tx"
RULE_HUAWEI_SEM_DDM = "huawei_sem_ddm"

BACKUP_PREFIX = "ev0081-chaves-opticas"


class OpticalKeyPlanError(Exception):
    """Plano inválido para aplicar (ex.: o Zabbix falhou numa das leituras)."""


def _s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _call_zabbix(method: str, params: dict[str, Any], plan: dict[str, Any]) -> list[dict]:
    """Chamada de leitura pelo gateway; falha vira erro no plano (nunca resultado vazio mudo)."""
    plan["zabbix_calls"] += 1
    try:
        result = common.ZABBIX_REQUEST(method, params)
    except Exception as exc:  # qualquer falha do Zabbix vira erro do plano
        plan["errors"].append(f"{method}: {exc.__class__.__name__}: {exc}")
        return []
    if result is None:
        plan["errors"].append(f"{method}: o gateway devolveu None (Zabbix indisponível?)")
        return []
    if not isinstance(result, list):
        plan["errors"].append(f"{method}: resposta inesperada ({type(result).__name__})")
        return []
    return [r for r in result if isinstance(r, Mapping)]


def _port_change(
    port: Mapping[str, Any], rule: str, rx_new: str, tx_new: str, **extra: Any
) -> dict[str, Any]:
    rx_old = _s(port["rx_power_item_key"])
    tx_old = _s(port["tx_power_item_key"])
    return {
        "port_id": port["id"],
        "device_id": port["device_id"],
        "device_name": port["device__name"],
        "port_name": port["name"],
        "rule": rule,
        "rx_old": rx_old,
        "rx_new": rx_new,
        "tx_old": tx_old,
        "tx_new": tx_new,
        "changed": (rx_old, tx_old) != (rx_new, tx_new),
        **extra,
    }


def _unmatched(port: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "port_id": port["id"],
        "device_id": port["device_id"],
        "device_name": port["device__name"],
        "port_name": port["name"],
        "rx_old": _s(port["rx_power_item_key"]),
        "tx_old": _s(port["tx_power_item_key"]),
        "reason": reason,
    }


_PORT_FIELDS = (
    "id",
    "name",
    "rx_power_item_key",
    "tx_power_item_key",
    "device_id",
    "device__name",
    "device__zabbix_hostid",
)


# --- Proposta A -----------------------------------------------------------------------------
def _plan_device(plan: dict[str, Any]) -> bool:
    """Planeia o hostid do device 22. Devolve True se o host novo está confirmado."""
    device = Device.objects.filter(pk=ZTE_DEVICE_ID).values("id", "name", "zabbix_hostid").first()
    if device is None:
        plan["notes"].append(f"device {ZTE_DEVICE_ID} não existe no inventário")
        return False

    current = _s(device["zabbix_hostid"])
    hosts = _call_zabbix(
        "host.get",
        {"hostids": [ZTE_OLD_HOSTID, ZTE_NEW_HOSTID], "output": ["hostid", "host", "name"]},
        plan,
    )
    by_id = {_s(h.get("hostid")): h for h in hosts}
    new_host = by_id.get(ZTE_NEW_HOSTID)
    entry: dict[str, Any] = {
        "device_id": device["id"],
        "device_name": device["name"],
        "field": "zabbix_hostid",
        "old": current,
        "new": current,
        "rule": RULE_DEVICE_HOSTID,
        "changed": False,
        "reason": "",
    }
    plan["devices"].append(entry)

    if plan["errors"]:
        entry["reason"] = "Zabbix indisponível — nada a decidir"
        return False
    if new_host is None:
        entry["reason"] = f"host {ZTE_NEW_HOSTID} não existe no Zabbix"
        return False
    device_name = _s(device["name"])
    host_names = {_s(new_host.get("name")), _s(new_host.get("host"))}
    if device_name not in host_names:
        entry["reason"] = (
            f"host {ZTE_NEW_HOSTID} tem outro nome ({sorted(host_names)!r} ≠ {device_name!r})"
        )
        return False
    if current == ZTE_NEW_HOSTID:
        entry["reason"] = "já corrigido"
        return True
    if current != ZTE_OLD_HOSTID:
        entry["reason"] = f"hostid inesperado ({current!r}); não mexo"
        return False
    if ZTE_OLD_HOSTID in by_id:
        entry["reason"] = f"host {ZTE_OLD_HOSTID} ainda existe no Zabbix; não mexo"
        return False
    entry.update(new=ZTE_NEW_HOSTID, changed=True, reason="host antigo apagado; mesmo nome")
    return True


# --- Proposta B / ZTE -----------------------------------------------------------------------
def decode_zte_old_ifindex(ifindex: int) -> tuple[int, int] | None:
    """`0x10SSPP00` → (slot, pon). Qualquer outra forma → None (não se adivinha)."""
    if (ifindex >> 24) != 0x10 or (ifindex & 0xFF) != 0:
        return None
    slot = (ifindex >> 16) & 0xFF
    pon = (ifindex >> 8) & 0xFF
    if slot == 0 or pon == 0:
        return None
    return slot, pon


def build_onu_rx_index(items: Iterable[Mapping[str, Any]]) -> dict[tuple[int, int, int], dict]:
    """(slot, pon, onu) → {"active": [itens], "lost": [itens]} a partir do `item.get` do host."""
    index: dict[tuple[int, int, int], dict[str, list]] = defaultdict(
        lambda: {"active": [], "lost": []}
    )
    for item in items:
        match = ONU_RX_KEY_RE.match(_s(item.get("key_")))
        if not match:
            continue
        pos = (int(match.group(2)), int(match.group(3)), int(match.group(4)))
        discovery = item.get("itemDiscovery") or {}
        lost = isinstance(discovery, Mapping) and _s(discovery.get("status")) == "1"
        enabled = _s(item.get("status")) in ("", "0")
        bucket = "active" if enabled and not lost else "lost"
        index[pos][bucket].append({"key": _s(item.get("key_")), "lastvalue": item.get("lastvalue")})
    return dict(index)


def _is_broken_zte_key(key: str) -> bool:
    return bool(
        ZXOLT_ANY_RE.match(key)
        or key.startswith(NET_IF_IN_PREFIX)
        or key.startswith(OLT_POWER_PREFIX)
    )


def _plan_zte_ports(plan: dict[str, Any], host_ok: bool) -> None:
    ports = [
        p
        for p in Port.objects.filter(device_id=ZTE_DEVICE_ID).order_by("id").values(*_PORT_FIELDS)
        if _is_broken_zte_key(_s(p["rx_power_item_key"]))
        or _is_broken_zte_key(_s(p["tx_power_item_key"]))
    ]
    if not ports:
        return
    if not host_ok:
        for p in ports:
            plan["unmatched"].append(_unmatched(p, f"host {ZTE_NEW_HOSTID} não confirmado"))
        return

    items = _call_zabbix(
        "item.get",
        {
            "hostids": [ZTE_NEW_HOSTID],
            "search": {"key_": "onu.rx["},
            "startSearch": True,
            "output": ["itemid", "key_", "status", "lastvalue", "units"],
            "selectItemDiscovery": ["status", "ts_delete"],
        },
        plan,
    )
    index = build_onu_rx_index(items)
    if plan["errors"] or not index:
        reason = "item.get do host novo falhou" if plan["errors"] else "host novo sem itens onu.rx"
        for p in ports:
            plan["unmatched"].append(_unmatched(p, reason))
        return

    for p in ports:
        rx = _s(p["rx_power_item_key"])
        tx = _s(p["tx_power_item_key"])
        if tx and not _is_broken_zte_key(tx):
            plan["unmatched"].append(_unmatched(p, f"TX inesperado ({tx!r})"))
            continue
        name_match = ONU_PORT_NAME_RE.match(_s(p["name"]))
        rx_match = ZXOLT_RX_RE.match(rx)
        if rx_match and name_match:
            if name_match.groups() != rx_match.groups():
                plan["unmatched"].append(_unmatched(p, "nome da porta ≠ índice da chave"))
                continue
            decoded = decode_zte_old_ifindex(int(rx_match.group(1)))
            if decoded is None:
                plan["unmatched"].append(_unmatched(p, "ifIndex fora da forma 0x10SSPP00"))
                continue
            pos = (decoded[0], decoded[1], int(rx_match.group(2)))
            bucket = index.get(pos, {"active": [], "lost": []})
            active, lost = bucket["active"], bucket["lost"]
            onu = "{}/{}/{}".format(*pos)
            if len(active) == 1:
                plan["ports"].append(
                    _port_change(
                        p, RULE_ZTE_ONU, active[0]["key"], "", onu=onu, value=active[0]["lastvalue"]
                    )
                )
            elif not active and not lost:
                plan["ports"].append(_port_change(p, RULE_ZTE_ONU_SEM_ITEM, "", "", onu=onu))
            else:
                keys = [i["key"] for i in active] + [f"{i['key']} (perdido)" for i in lost]
                plan["unmatched"].append(
                    _unmatched(p, f"ONU {onu}: {len(active)} ativos, {len(lost)} perdidos {keys}")
                )
        elif ZXOLT_ANY_RE.match(rx) or (not rx and ZXOLT_ANY_RE.match(tx)):
            plan["ports"].append(_port_change(p, RULE_ZTE_CARTAO, "", ""))
        elif rx.startswith(NET_IF_IN_PREFIX):
            plan["ports"].append(_port_change(p, RULE_ZTE_TRAFEGO, "", ""))
        elif rx.startswith(OLT_POWER_PREFIX):
            plan["ports"].append(_port_change(p, RULE_ZTE_FONTE, "", ""))
        else:
            plan["unmatched"].append(_unmatched(p, "não casa com nenhuma regra ZTE"))


# --- Proposta B / VSOL ----------------------------------------------------------------------
def _plan_vsol_ports(plan: dict[str, Any]) -> None:
    ports = (
        Port.objects.filter(rx_power_item_key__startswith=VSOL_RX_PREFIX)
        .order_by("id")
        .values(*_PORT_FIELDS)
    )
    for p in ports:
        rx = _s(p["rx_power_item_key"])
        tx = _s(p["tx_power_item_key"])
        if LLD_MACRO_MARK in rx:
            plan["ports"].append(_port_change(p, RULE_VSOL_MACRO, "", ""))
        elif tx == rx:
            plan["ports"].append(_port_change(p, RULE_VSOL_RX_IGUAL_TX, rx, ""))


# --- Proposta B / Huawei sem DDM ------------------------------------------------------------
def _plan_huawei_ports(plan: dict[str, Any]) -> None:
    ports = list(
        Port.objects.filter(
            rx_power_item_key__startswith=HUAWEI_RX_PREFIX,
            tx_power_item_key__startswith=HUAWEI_TX_PREFIX,
        )
        .exclude(device__zabbix_hostid="")
        .order_by("id")
        .values(*_PORT_FIELDS)
    )
    if not ports:
        return
    errors_before = len(plan["errors"])
    items = _call_zabbix(
        "item.get",
        {
            "hostids": sorted({_s(p["device__zabbix_hostid"]) for p in ports}),
            "filter": {
                "key_": sorted(
                    {_s(p["tx_power_item_key"]) for p in ports}
                    | {_s(p["rx_power_item_key"]) for p in ports}
                )
            },
            "output": ["hostid", "key_", "lastvalue", "lastclock", "state"],
        },
        plan,
    )
    if len(plan["errors"]) > errors_before:
        return
    by_key = {(_s(i.get("hostid")), _s(i.get("key_"))): i for i in items}
    for p in ports:
        hostid = _s(p["device__zabbix_hostid"])
        tx_item = by_key.get((hostid, _s(p["tx_power_item_key"])))
        rx_item = by_key.get((hostid, _s(p["rx_power_item_key"])))
        if not tx_item or not rx_item:
            continue
        try:
            tx_value = float(_s(tx_item.get("lastvalue")))
        except ValueError:
            continue
        if (
            abs(tx_value - HUAWEI_NO_DDM_TX_DBM) <= HUAWEI_NO_DDM_TOLERANCE
            and _s(rx_item.get("state")) == "1"
        ):
            plan["ports"].append(_port_change(p, RULE_HUAWEI_SEM_DDM, "", "", value=tx_value))


# --- Plano ----------------------------------------------------------------------------------
def build_optical_key_plan() -> dict[str, Any]:
    """Ensaio: lê inventário e Zabbix e devolve as mudanças propostas (não escreve nada)."""
    plan: dict[str, Any] = {
        "devices": [],
        "ports": [],
        "unmatched": [],
        "errors": [],
        "notes": [],
        "zabbix_calls": 0,
    }
    host_ok = _plan_device(plan)
    _plan_zte_ports(plan, host_ok)
    _plan_vsol_ports(plan)
    _plan_huawei_ports(plan)

    changed_ports = [c for c in plan["ports"] if c["changed"]]
    plan["summary"] = {
        "devices_a_mudar": sum(1 for d in plan["devices"] if d["changed"]),
        "portas_avaliadas": len(plan["ports"]),
        "portas_a_mudar": len(changed_ports),
        "portas_sem_mudanca": len(plan["ports"]) - len(changed_ports),
        "sem_correspondencia": len(plan["unmatched"]),
        "por_regra": dict(sorted(Counter(c["rule"] for c in changed_ports).items())),
        "erros": len(plan["errors"]),
    }
    return plan


# --- Aplicação ------------------------------------------------------------------------------
def write_backup(plan: Mapping[str, Any], backup_dir: Path) -> Path:
    """Cópia JSON dos valores antigos (só do que vai mudar). Devolve o caminho."""
    now = datetime.now(UTC)
    payload = {
        "item": "EV-0081",
        "criado_em": now.isoformat(),
        "devices": [
            {"id": d["device_id"], "zabbix_hostid": d["old"]}
            for d in plan["devices"]
            if d["changed"]
        ],
        "ports": [
            {"id": c["port_id"], "rx_power_item_key": c["rx_old"], "tx_power_item_key": c["tx_old"]}
            for c in plan["ports"]
            if c["changed"]
        ],
    }
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / f"{BACKUP_PREFIX}-{now.strftime('%Y%m%d%H%M%S%f')}.json"
    with path.open("x", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return path


def apply_optical_key_plan(plan: Mapping[str, Any], backup_dir: Path) -> dict[str, Any]:
    """Grava o plano: cópia JSON primeiro, depois uma transação, depois as duas caches.

    Cada linha só é escrita se o valor atual ainda for o do ensaio (senão conta como conflito
    e fica como está).
    """
    if plan["errors"]:
        raise OpticalKeyPlanError("o plano tem erros de leitura do Zabbix; não aplico")

    devices = [d for d in plan["devices"] if d["changed"]]
    ports = [c for c in plan["ports"] if c["changed"]]
    result: dict[str, Any] = {
        "backup_path": None,
        "devices_atualizados": 0,
        "portas_atualizadas": 0,
        "conflitos": [],
        "caches_invalidadas": False,
    }
    if not devices and not ports:
        return result

    result["backup_path"] = str(write_backup(plan, backup_dir))

    with transaction.atomic():
        for d in devices:
            updated = Device.objects.filter(pk=d["device_id"], zabbix_hostid=d["old"]).update(
                zabbix_hostid=d["new"]
            )
            if updated:
                result["devices_atualizados"] += 1
            else:
                result["conflitos"].append({"device_id": d["device_id"]})
        for c in ports:
            updated = Port.objects.filter(
                pk=c["port_id"],
                rx_power_item_key=c["rx_old"],
                tx_power_item_key=c["tx_old"],
            ).update(rx_power_item_key=c["rx_new"], tx_power_item_key=c["tx_new"])
            if updated:
                result["portas_atualizadas"] += 1
            else:
                result["conflitos"].append({"port_id": c["port_id"]})

    invalidate_fiber_cache()
    invalidate_dashboard_cache()
    result["caches_invalidadas"] = True
    return result


__all__ = [
    "OpticalKeyPlanError",
    "apply_optical_key_plan",
    "build_onu_rx_index",
    "build_optical_key_plan",
    "decode_zte_old_ifindex",
    "write_backup",
]
