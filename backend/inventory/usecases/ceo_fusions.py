"""Fusões numa CEO e rastreamento da luz fim-a-fim (EV-0136).

Numa CEO a meio de um cabo (o cabo-tronco, ``FiberInfrastructure.cable``) uma fibra emendada é
cortada em duas metades; cada ponta de fibra disponível na caixa é ``(fibra, lado)``, em que o
lado diz para onde segue essa metade: ``"a"`` rumo à ponta A do cabo, ``"b"`` rumo à ponta B.
Um cabo que nasce na CEO (``origin_infrastructure``) só tem o lado ``"b"``; um que termina nela
(``destination_infrastructure``) só o lado ``"a"``.

No rastreamento, uma fibra do tronco sem emenda numa CEO em **sangria** passa direto (expressa);
numa CEO em **corte** a luz acaba ali. Uma fibra sangrada (emendada só de um lado) acaba no lado
sem emenda.
"""

from __future__ import annotations

import math
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from inventory.cache.fibers import invalidate_fiber_cache
from inventory.models import FiberCable, FiberFusion, FiberInfrastructure, FiberStrand
from maps_view.cache_swr import invalidate_dashboard_cache
from setup_app.services import runtime_settings

from .ceo import CEO_TYPE
from .devices_common import InventoryValidationError
from .strand_ports import active_otdr, end_site

SIDES = ("a", "b")
SPLICES_PER_TRAY = 24
MAX_HOPS = 64


def _ceo_label(ceo: FiberInfrastructure) -> str:
    return ceo.name or f"CEO #{ceo.pk}"


def _mode(ceo: FiberInfrastructure) -> str:
    return (ceo.metadata or {}).get("mode") or "sangria"


def _end_label(cable: FiberCable, end: str) -> str:
    site = end_site(cable, end)
    if site is not None:
        return site.display_name
    ceo = cable.origin_infrastructure if end == "a" else cable.destination_infrastructure
    return _ceo_label(ceo) if ceo is not None else f"ponta {end.upper()}"


def sides_at(cable: FiberCable, ceo: FiberInfrastructure) -> tuple[str, ...]:
    """Lados da fibra deste cabo disponíveis na CEO (vazio = o cabo não passa na caixa)."""
    if cable.pk == ceo.cable_id:
        return SIDES
    if cable.origin_infrastructure_id == ceo.pk:
        return ("b",)
    if cable.destination_infrastructure_id == ceo.pk:
        return ("a",)
    return ()


def _cables_at(ceo: FiberInfrastructure) -> list[FiberCable]:
    qs = FiberCable.objects.filter(
        Q(pk=ceo.cable_id) | Q(origin_infrastructure=ceo) | Q(destination_infrastructure=ceo)
    ).select_related(
        "site_a",
        "site_b",
        "origin_port__device__site",
        "destination_port__device__site",
        "origin_infrastructure",
        "destination_infrastructure",
    )
    return sorted(qs, key=lambda c: (c.pk != ceo.cable_id, c.name))


def _fiber_end(strand: FiberStrand, side: str, cable: FiberCable) -> dict[str, Any]:
    return {
        "key": f"{strand.pk}:{side}",
        "strand_id": strand.pk,
        "side": side,
        "cable_id": cable.pk,
        "cable_name": cable.name,
        "tube_number": strand.tube.number,
        "tube_color": strand.tube.color,
        "number": strand.number,
        "absolute_number": strand.absolute_number,
        "color": strand.color,
        "color_hex": strand.color_hex,
        "toward": _end_label(cable, side),
    }


def ceo_fusions(ceo_id: int) -> dict[str, Any]:
    """Pontas de fibra disponíveis na CEO (por cabo) e as fusões feitas nela."""
    ceo = get_object_or_404(
        FiberInfrastructure.objects.select_related("cable"), pk=ceo_id, type=CEO_TYPE
    )
    fusions = list(
        FiberFusion.objects.filter(infrastructure=ceo)
        .select_related("fiber_a__tube__cable", "fiber_b__tube__cable")
        .order_by("tray", "slot", "id")
    )
    used: dict[str, int] = {}
    for f in fusions:
        used[f"{f.fiber_a_id}:{f.fiber_a_side}"] = f.pk
        used[f"{f.fiber_b_id}:{f.fiber_b_side}"] = f.pk
    cables = []
    for cable in _cables_at(ceo):
        sides = sides_at(cable, ceo)
        strands = FiberStrand.objects.filter(tube__cable=cable).select_related("tube")
        ends = [
            {**_fiber_end(s, side, cable), "fusion_id": used.get(f"{s.pk}:{side}")}
            for s in strands.order_by("tube__number", "number")
            for side in sides
        ]
        role = (
            "tronco"
            if cable.pk == ceo.cable_id
            else ("derivado" if cable.origin_infrastructure_id == ceo.pk else "chegada")
        )
        cables.append({"id": cable.pk, "name": cable.name, "role": role, "ends": ends})
    return {
        "ceo": {
            "id": ceo.pk,
            "name": _ceo_label(ceo),
            "mode": _mode(ceo),
            "trays": ceo.installed_trays or 1,
            "splices_per_tray": SPLICES_PER_TRAY,
        },
        "cables": cables,
        "fusions": [
            {
                "id": f.pk,
                "tray": f.tray,
                "slot": f.slot,
                "a": _fiber_end(f.fiber_a, f.fiber_a_side, f.fiber_a.tube.cable),
                "b": _fiber_end(f.fiber_b, f.fiber_b_side, f.fiber_b.tube.cable),
            }
            for f in fusions
        ],
    }


def _resolve_end(
    ceo: FiberInfrastructure, end: dict[str, Any], label: str
) -> tuple[FiberStrand, str]:
    strand = get_object_or_404(
        FiberStrand.objects.select_related("tube__cable"), pk=end.get("strand_id")
    )
    sides = sides_at(strand.tube.cable, ceo)
    if not sides:
        raise InventoryValidationError(f"a fibra {label} é de um cabo que não passa nesta CEO")
    side = end.get("side") or (sides[0] if len(sides) == 1 else "")
    if side not in sides:
        raise InventoryValidationError(
            f"indique o lado da fibra {label} (rumo à ponta A ou à ponta B do cabo)"
        )
    return strand, side


def create_fusion(
    ceo_id: int,
    *,
    a: dict[str, Any],
    b: dict[str, Any],
    tray: int | None = None,
    slot: int | None = None,
) -> dict[str, Any]:
    ceo = get_object_or_404(FiberInfrastructure, pk=ceo_id, type=CEO_TYPE)
    if tray is not None and not 1 <= tray <= (ceo.installed_trays or 1):
        raise InventoryValidationError(f"bandeja entre 1 e {ceo.installed_trays or 1}")
    if slot is not None and not 1 <= slot <= SPLICES_PER_TRAY:
        raise InventoryValidationError(f"posição na bandeja entre 1 e {SPLICES_PER_TRAY}")
    with transaction.atomic():
        sa, side_a = _resolve_end(ceo, a, "A")
        sb, side_b = _resolve_end(ceo, b, "B")
        if sa.pk == sb.pk and side_a == side_b:
            raise InventoryValidationError("as duas pontas da fusão são a mesma")
        busy = FiberFusion.objects.select_for_update().filter(infrastructure=ceo)
        for strand, side, label in ((sa, side_a, "A"), (sb, side_b, "B")):
            taken = busy.filter(
                Q(fiber_a=strand, fiber_a_side=side) | Q(fiber_b=strand, fiber_b_side=side)
            ).first()
            if taken is not None:
                raise InventoryValidationError(
                    f"a ponta {label} (fibra {strand.absolute_number} de "
                    f"{strand.tube.cable.name}) já está emendada nesta CEO"
                )
        if tray is not None and slot is not None and busy.filter(tray=tray, slot=slot).exists():
            raise InventoryValidationError(f"a posição {slot} da bandeja {tray} já está ocupada")
        fusion = FiberFusion.objects.create(
            infrastructure=ceo,
            tray=tray,
            slot=slot,
            fiber_a=sa,
            fiber_a_side=side_a,
            fiber_b=sb,
            fiber_b_side=side_b,
        )
    invalidate_fiber_cache()
    invalidate_dashboard_cache()
    return {"id": fusion.pk}


def delete_fusion(ceo_id: int, fusion_id: int) -> None:
    fusion = get_object_or_404(FiberFusion, pk=fusion_id, infrastructure_id=ceo_id)
    fusion.delete()
    invalidate_fiber_cache()
    invalidate_dashboard_cache()


# ── rastreamento ─────────────────────────────────────────────────────────────


def _port_step(port) -> dict[str, Any]:
    device = port.device
    return {
        "type": "port",
        "port_id": port.pk,
        "port_name": port.name,
        "device_name": device.name,
        "site_name": getattr(device.site, "display_name", None),
    }


def _partner(fusion: FiberFusion, strand_id: int, side: str) -> tuple[FiberStrand, str]:
    if fusion.fiber_a_id == strand_id and fusion.fiber_a_side == side:
        return fusion.fiber_b, fusion.fiber_b_side
    return fusion.fiber_a, fusion.fiber_a_side


def _fusion_at(ceo: FiberInfrastructure, strand_id: int, side: str) -> FiberFusion | None:
    return (
        FiberFusion.objects.filter(infrastructure=ceo)
        .filter(
            Q(fiber_a_id=strand_id, fiber_a_side=side) | Q(fiber_b_id=strand_id, fiber_b_side=side)
        )
        .select_related(
            "fiber_a__tube__cable",
            "fiber_b__tube__cable",
            "fiber_a__connected_device_port__device__site",
            "fiber_a__connected_device_port_b__device__site",
            "fiber_b__connected_device_port__device__site",
            "fiber_b__connected_device_port_b__device__site",
        )
        .first()
    )


def trace_light(strand_id: int, *, start: str = "a") -> dict[str, Any]:
    """Segue a luz que entra pela ponta ``start`` da fibra até uma porta ou um fim sem saída."""
    if start not in SIDES:
        raise InventoryValidationError("a ponta de partida é «a» ou «b»")
    strand = get_object_or_404(
        FiberStrand.objects.select_related(
            "tube__cable",
            "connected_device_port__device__site",
            "connected_device_port_b__device__site",
        ),
        pk=strand_id,
    )
    steps: list[dict[str, Any]] = []
    first_port = strand.connected_device_port if start == "a" else strand.connected_device_port_b
    if first_port is not None:
        steps.append(_port_step(first_port))
    direction = "b" if start == "a" else "a"  # para onde a luz segue no cabo
    pos = -math.inf if start == "a" else math.inf  # km de onde a luz entrou no cabo
    seen: set[tuple[int, str, float]] = set()
    budget = runtime_settings.get_runtime_config().optical_budget
    total_km = 0.0
    fusions = 0
    end: dict[str, Any] = {"reason": "loop", "label": "rastreamento interrompido (laço)"}

    for _ in range(MAX_HOPS):
        cable = strand.tube.cable
        if (strand.pk, direction, pos) in seen:
            break
        seen.add((strand.pk, direction, pos))
        length = float(cable.length_km or 0)
        mids = list(
            FiberInfrastructure.objects.filter(cable=cable, type=CEO_TYPE).order_by(
                "distance_from_origin"
            )
        )
        km = lambda x: (x.distance_from_origin or 0) / 1000  # noqa: E731
        ahead = (
            [x for x in mids if km(x) > pos]
            if direction == "b"
            else [x for x in reversed(mids) if km(x) < pos]
        )
        our_side = "a" if direction == "b" else "b"  # metade em que a luz chega à caixa
        start_km = (
            min(max(pos, 0.0), length) if math.isfinite(pos) else (0.0 if pos < 0 else length)
        )
        step: dict[str, Any] = {
            "type": "cable",
            "cable_id": cable.pk,
            "cable_name": cable.name,
            "strand_id": strand.pk,
            "absolute_number": strand.absolute_number,
            "color": strand.color,
            "color_hex": strand.color_hex,
            "tube_number": strand.tube.number,
            "toward": _end_label(cable, direction),
            "passes": [],
        }
        steps.append(step)
        otdr = active_otdr(cable)

        def close_cable(
            at_km: float,
            step: dict[str, Any] = step,
            start_km: float = start_km,
            cable: FiberCable = cable,
        ) -> None:
            nonlocal total_km
            seg = abs(at_km - start_km)
            step["km"] = round(seg, 3)
            total_km += seg
            # EV-0140: atenuação do tipo de cabo; sem tipo, a da fibra do orçamento
            att = getattr(cable.cable_group, "attenuation_db_per_km", None)
            step["db_km"] = float(att) if att is not None else budget["fiber_db_km"]

        if otdr is not None:
            close_cable(length if direction == "b" else 0.0)
            step["broken"] = True
            end = {
                "reason": "broken",
                "label": f"rompimento OTDR ativo em {cable.name}",
                "otdr": otdr,
            }
            break

        jumped = False
        stop = None
        for x in ahead:
            fusion = _fusion_at(x, strand.pk, our_side)
            if fusion is not None:
                close_cable(km(x))
                partner, p_side = _partner(fusion, strand.pk, our_side)
                fusions += 1
                steps.append(
                    {
                        "type": "fusion",
                        "ceo_id": x.pk,
                        "ceo_name": _ceo_label(x),
                        "mode": _mode(x),
                        "tray": fusion.tray,
                        "slot": fusion.slot,
                    }
                )
                strand, direction, pos = partner, p_side, _pos_on(partner.tube.cable, x)
                jumped = True
                break
            cut = _mode(x) == "corte" or _fusion_at(x, strand.pk, direction) is not None
            if cut:
                close_cable(km(x))
                stop = {
                    "reason": "dead_end",
                    "label": f"fibra cortada na {_ceo_label(x)} sem emenda deste lado",
                    "ceo_name": _ceo_label(x),
                }
                break
            step["passes"].append(_ceo_label(x))  # sangria: passa direto
        if jumped:
            continue
        if stop is not None:
            end = stop
            break

        # chegou à ponta do cabo
        close_cable(length if direction == "b" else 0.0)
        port = strand.connected_device_port_b if direction == "b" else strand.connected_device_port
        if port is not None:
            steps.append(_port_step(port))
            end = {"reason": "port", "label": f"{port.device.name} → {port.name}"}
            break
        end_ceo = (
            cable.destination_infrastructure if direction == "b" else cable.origin_infrastructure
        )
        if end_ceo is not None:
            fusion = _fusion_at(end_ceo, strand.pk, our_side)
            if fusion is not None:
                partner, p_side = _partner(fusion, strand.pk, our_side)
                fusions += 1
                steps.append(
                    {
                        "type": "fusion",
                        "ceo_id": end_ceo.pk,
                        "ceo_name": _ceo_label(end_ceo),
                        "mode": _mode(end_ceo),
                        "tray": fusion.tray,
                        "slot": fusion.slot,
                    }
                )
                strand, direction, pos = partner, p_side, _pos_on(partner.tube.cable, end_ceo)
                continue
            end = {
                "reason": "dead_end",
                "label": f"ponta do cabo na {_ceo_label(end_ceo)} sem emenda",
                "ceo_name": _ceo_label(end_ceo),
            }
            break
        end = {
            "reason": "dead_end",
            "label": f"ponta {direction.upper()} do cabo ({_end_label(cable, direction)}) sem porta ligada",
        }
        break

    tx = _start_tx(first_port, budget)
    loss = _accumulate(steps, budget, tx)
    return {
        "start": {"strand_id": strand_id, "end": start},
        "steps": steps,
        "end": end,
        "total_km": round(total_km, 3),
        "fusions": fusions,
        # estimativa (orçamento óptico, EV-0140): dB/km do cabo * km + perda por fusão
        "loss_db_estimate": round(loss, 2),
        "tx": tx,
        "rx_estimate_dbm": round(tx["dbm"] - loss, 2) if tx else None,
        "budget": {"fiber_db_km": budget["fiber_db_km"], "fusion_db": budget["fusion_db"]},
    }


def _start_tx(port, budget: dict[str, Any]) -> dict[str, Any] | None:
    """Potência de partida: TX coletado da porta (Zabbix) ou o TX padrão; sem porta, nenhuma."""
    if port is None:
        return None
    if port.last_tx_power is not None:
        return {"dbm": float(port.last_tx_power), "source": "zabbix", "port_name": port.name}
    return {"dbm": budget["tx_default_dbm"], "source": "padrao", "port_name": port.name}


def _accumulate(
    steps: list[dict[str, Any]], budget: dict[str, Any], tx: dict[str, Any] | None
) -> float:
    """Acrescenta a cada passo os km, a perda e (com TX) a potência estimada acumulados."""
    km = loss = 0.0
    for step in steps:
        if step["type"] == "cable":
            seg = step.get("km") or 0.0
            km += seg
            step["loss_db"] = round(seg * step.get("db_km", budget["fiber_db_km"]), 3)
            loss += step["loss_db"]
        elif step["type"] == "fusion":
            step["loss_db"] = budget["fusion_db"]
            loss += budget["fusion_db"]
        step["acc_km"] = round(km, 3)
        step["acc_loss_db"] = round(loss, 2)
        step["dbm"] = round(tx["dbm"] - loss, 2) if tx else None
    return loss


def _pos_on(cable: FiberCable, ceo: FiberInfrastructure) -> float:
    """km da CEO no cabo (a meio do tronco; -inf/+inf nas pontas de um derivado/chegada)."""
    if cable.pk == ceo.cable_id:
        return (ceo.distance_from_origin or 0) / 1000
    if cable.origin_infrastructure_id == ceo.pk:
        return -math.inf
    return math.inf
