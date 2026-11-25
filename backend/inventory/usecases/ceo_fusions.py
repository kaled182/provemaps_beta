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
from inventory.models import (
    FiberCable,
    FiberFusion,
    FiberInfrastructure,
    FiberStrand,
    Splitter,
    SplitterPort,
)
from maps_view.cache_swr import invalidate_dashboard_cache
from setup_app.services import runtime_settings

from .ceo import CEO_TYPE
from .devices_common import InventoryValidationError
from .strand_ports import active_otdr, end_site

# EV-0141: emendas também na CTO (caixa de atendimento, splitter_box)
BOX_TYPES = (CEO_TYPE, "splitter_box")
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
        "tube_color_hex": strand.tube.color_hex,
        "number": strand.number,
        "absolute_number": strand.absolute_number,
        "color": strand.color,
        "color_hex": strand.color_hex,
        "toward": _end_label(cable, side),
    }


def ceo_fusions(ceo_id: int) -> dict[str, Any]:
    """Pontas de fibra disponíveis na CEO (por cabo) e as fusões feitas nela."""
    ceo = get_object_or_404(
        FiberInfrastructure.objects.select_related("cable"), pk=ceo_id, type__in=BOX_TYPES
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
    # EV-0142: pontas ligadas a um splitter (entrada ou saída de porta)
    splitter_use = {
        f"{sid}:{side}": what
        for (sid, side), what in _busy_ends(ceo).items()
        if what != "uma fusão"
    }
    cables = []
    for cable in _cables_at(ceo):
        sides = sides_at(cable, ceo)
        strands = FiberStrand.objects.filter(tube__cable=cable).select_related("tube")
        ends = [
            {
                **_fiber_end(s, side, cable),
                "fusion_id": used.get(f"{s.pk}:{side}"),
                "splitter_use": splitter_use.get(f"{s.pk}:{side}"),
            }
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
            "kind": "cto" if ceo.type == "splitter_box" else "ceo",
            "mode": _mode(ceo),
            "trays": ceo.installed_trays or 1,
            "splices_per_tray": SPLICES_PER_TRAY,
        },
        "cables": cables,
        "splitters": splitters_payload(ceo),
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
    ceo = get_object_or_404(FiberInfrastructure, pk=ceo_id, type__in=BOX_TYPES)
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
        used = _busy_ends(ceo)
        for strand, side, label in ((sa, side_a, "A"), (sb, side_b, "B")):
            what = used.get((strand.pk, side))
            if what == "uma fusão":
                raise InventoryValidationError(
                    f"a ponta {label} (fibra {strand.absolute_number} de "
                    f"{strand.tube.cable.name}) já está emendada nesta CEO"
                )
            if what:
                raise InventoryValidationError(
                    f"a ponta {label} (fibra {strand.absolute_number} de "
                    f"{strand.tube.cable.name}) já está ligada a {what}"
                )
        if tray is not None and slot is not None and busy.filter(tray=tray, slot=slot).exists():
            raise InventoryValidationError(f"a posição {slot} da bandeja {tray} já está ocupada")
        if tray is None and slot is None:
            tray, slot = _next_free_slot(ceo)  # EV-0141: sem posição indicada, a próxima livre
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


def _next_free_slot(ceo: FiberInfrastructure) -> tuple[int | None, int | None]:
    """Primeira posição livre, bandeja a bandeja; (None, None) se a caixa está cheia."""
    taken = set(
        FiberFusion.objects.filter(
            infrastructure=ceo, tray__isnull=False, slot__isnull=False
        ).values_list("tray", "slot")
    )
    for tray in range(1, (ceo.installed_trays or 1) + 1):
        for slot in range(1, SPLICES_PER_TRAY + 1):
            if (tray, slot) not in taken:
                return tray, slot
    return None, None


def fuse_tubes(ceo_id: int, *, a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """«Fusionar tubo 1:1» (EV-0141): fibra n do tubo A com a fibra n do tubo B (cor com cor).

    ``a``/``b`` = ``{cable_id, tube_number, side}``. Fibras já emendadas (de um lado ou do
    outro) ficam de fora e são contadas em ``skipped``; posições na bandeja automáticas.
    """
    ceo = get_object_or_404(FiberInfrastructure, pk=ceo_id, type__in=BOX_TYPES)

    def strands(end: dict[str, Any], label: str) -> tuple[list[FiberStrand], str]:
        cable = get_object_or_404(FiberCable, pk=end.get("cable_id"))
        sides = sides_at(cable, ceo)
        side = end.get("side") or (sides[0] if len(sides) == 1 else "")
        if side not in sides:
            raise InventoryValidationError(f"indique o lado do tubo {label} nesta caixa")
        rows = list(
            FiberStrand.objects.filter(tube__cable=cable, tube__number=end.get("tube_number"))
            .select_related("tube__cable")
            .order_by("number")
        )
        if not rows:
            raise InventoryValidationError(f"o tubo {label} não existe no cabo {cable.name}")
        return rows, side

    fa, side_a = strands(a, "A")
    fb, side_b = strands(b, "B")
    if fa[0].tube_id == fb[0].tube_id and side_a == side_b:
        raise InventoryValidationError("escolha dois tubos diferentes (ou lados diferentes)")
    created = skipped = 0
    with transaction.atomic():
        FiberFusion.objects.select_for_update().filter(infrastructure=ceo).exists()
        used = set(_busy_ends(ceo))  # EV-0142: fusões e splitters
        for sa, sb in zip(
            fa, fb, strict=False
        ):  # tubos de tamanhos diferentes: o resto conta em skipped
            if (sa.pk, side_a) in used or (sb.pk, side_b) in used:
                skipped += 1
                continue
            tray, slot = _next_free_slot(ceo)
            FiberFusion.objects.create(
                infrastructure=ceo,
                tray=tray,
                slot=slot,
                fiber_a=sa,
                fiber_a_side=side_a,
                fiber_b=sb,
                fiber_b_side=side_b,
            )
            used |= {(sa.pk, side_a), (sb.pk, side_b)}
            created += 1
        skipped += abs(len(fa) - len(fb))
    invalidate_fiber_cache()
    invalidate_dashboard_cache()
    return {"created": created, "skipped": skipped}


def delete_fusion(ceo_id: int, fusion_id: int) -> None:
    fusion = get_object_or_404(FiberFusion, pk=fusion_id, infrastructure_id=ceo_id)
    fusion.delete()
    invalidate_fiber_cache()
    invalidate_dashboard_cache()


# ── rastreamento ─────────────────────────────────────────────────────────────


def _where(box: FiberInfrastructure) -> dict[str, Any]:
    """EV-0143: coordenadas da caixa, para o destaque no mapa."""
    loc = box.location
    return {"lat": loc.y, "lng": loc.x} if loc is not None else {"lat": None, "lng": None}


def _port_step(port) -> dict[str, Any]:
    device = port.device
    site = device.site
    return {
        "type": "port",
        "port_id": port.pk,
        "port_name": port.name,
        "device_name": device.name,
        "site_name": getattr(site, "display_name", None),
        "lat": float(site.latitude) if site and site.latitude is not None else None,
        "lng": float(site.longitude) if site and site.longitude is not None else None,
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


def _splitter_at(box: FiberInfrastructure, strand_id: int, side: str) -> dict[str, Any] | None:
    """EV-0142: a ponta (fibra, lado) na caixa liga-se a um splitter? → {splitter, role, port}."""
    sp = (
        Splitter.objects.filter(infrastructure=box, input_strand_id=strand_id, input_side=side)
        .select_related("input_strand__tube__cable")
        .first()
    )
    if sp is not None:
        return {"splitter": sp, "role": "in", "port": None}
    port = (
        SplitterPort.objects.filter(
            splitter__infrastructure=box, output_strand_id=strand_id, output_side=side
        )
        .select_related("splitter__input_strand__tube__cable")
        .first()
    )
    if port is not None:
        return {"splitter": port.splitter, "role": "out", "port": port}
    return None


def _through_splitter(
    sp: dict[str, Any],
    box: FiberInfrastructure,
    steps: list[dict[str, Any]],
    budget: dict[str, Any],
    upstream: bool,
) -> tuple[FiberStrand, str, float] | None:
    """A montante, chegar à saída de um splitter continua pela entrada dele (com a perda do
    splitter). A jusante a luz reparte-se: o rastreamento linear para ali (None)."""
    splitter = sp["splitter"]
    if not upstream or sp["role"] != "out" or splitter.input_strand is None:
        return None
    steps.append(
        {
            "type": "splitter",
            "ceo_id": box.pk,
            "ceo_name": _ceo_label(box),
            "ratio": splitter.ratio,
            "port": sp["port"].number,
            "loss_db": budget["splitters"].get(splitter.ratio, 0.0),
            **_where(box),
        }
    )
    strand = splitter.input_strand
    return strand, splitter.input_side, _pos_on(strand.tube.cable, box)


def _splitter_stop(sp: dict[str, Any], box: FiberInfrastructure, upstream: bool) -> dict[str, Any]:
    splitter = sp["splitter"]
    label = f"splitter {splitter.ratio} da {_ceo_label(box)}"
    if not upstream and sp["role"] == "in":
        return {"reason": "splitter", "label": f"entra no {label}", "splitter_id": splitter.pk}
    if upstream and sp["role"] == "out":
        return {
            "reason": "dead_end",
            "label": f"{label} sem fibra de entrada",
            "splitter_id": splitter.pk,
        }
    return {"reason": "dead_end", "label": f"chega a uma porta do {label} no sentido contrário"}


def _walk(
    strand: FiberStrand,
    direction: str,
    pos: float,
    budget: dict[str, Any],
    *,
    upstream: bool = False,
) -> dict[str, Any]:
    """Percorre a fibra a partir de ``pos`` (km no cabo) no sentido ``direction``, atravessando
    fusões e (a montante, EV-0142) splitters, até uma porta ou um fim sem saída."""
    steps: list[dict[str, Any]] = []
    seen: set[tuple[int, str, float]] = set()
    total_km = 0.0
    fusions = 0
    last_port = None
    port_end: tuple[int, str] | None = None
    end: dict[str, Any] = {"reason": "loop", "label": "rastreamento interrompido (laço)"}

    for _ in range(MAX_HOPS):
        cable = strand.tube.cable
        if (strand.pk, direction, pos) in seen:
            break
        seen.add((strand.pk, direction, pos))
        length = float(cable.length_km or 0)
        mids = list(
            FiberInfrastructure.objects.filter(cable=cable, type__in=BOX_TYPES).order_by(
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
            step["from_km"], step["to_km"] = start_km, at_km  # EV-0143: troço para o mapa
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
                        **_where(x),
                    }
                )
                strand, direction, pos = partner, p_side, _pos_on(partner.tube.cable, x)
                jumped = True
                break
            sp = _splitter_at(x, strand.pk, our_side)
            if sp is not None:
                close_cable(km(x))
                hop = _through_splitter(sp, x, steps, budget, upstream)
                if hop is None:
                    stop = _splitter_stop(sp, x, upstream)
                    break
                strand, direction, pos = hop
                jumped = True
                break
            cut = (
                _mode(x) == "corte"
                or _fusion_at(x, strand.pk, direction) is not None
                or _splitter_at(x, strand.pk, direction) is not None
            )
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
            last_port = port
            port_end = (strand.pk, direction)
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
                        **_where(end_ceo),
                    }
                )
                strand, direction, pos = partner, p_side, _pos_on(partner.tube.cable, end_ceo)
                continue
            sp = _splitter_at(end_ceo, strand.pk, our_side)
            if sp is not None:
                hop = _through_splitter(sp, end_ceo, steps, budget, upstream)
                if hop is not None:
                    strand, direction, pos = hop
                    continue
                end = _splitter_stop(sp, end_ceo, upstream)
                break
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

    return {
        "steps": steps,
        "end": end,
        "total_km": total_km,
        "fusions": fusions,
        "port": last_port,
        "port_end": port_end,
    }


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
    budget = runtime_settings.get_runtime_config().optical_budget
    walked = _walk(strand, direction, pos, budget)
    steps += walked["steps"]
    end, total_km, fusions = walked["end"], walked["total_km"], walked["fusions"]
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
    steps: list[dict[str, Any]],
    budget: dict[str, Any],
    tx: dict[str, Any] | None,
    *,
    km0: float = 0.0,
    loss0: float = 0.0,
) -> float:
    """Acrescenta a cada passo os km, a perda e (com TX) a potência estimada acumulados, a partir
    de ``km0``/``loss0`` (EV-0143: um ramo continua do que já se perdeu até ao splitter)."""
    km, loss = km0, loss0
    for step in steps:
        if step["type"] == "cable":
            seg = step.get("km") or 0.0
            km += seg
            step["loss_db"] = round(seg * step.get("db_km", budget["fiber_db_km"]), 3)
            loss += step["loss_db"]
        elif step["type"] == "fusion":
            step["loss_db"] = budget["fusion_db"]
            loss += budget["fusion_db"]
        elif step["type"] == "splitter":  # EV-0142: perda do splitter (orçamento óptico)
            loss += step["loss_db"]
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


# ── splitters na bandeja (EV-0142) ───────────────────────────────────────────

_UNSET: Any = object()


def _busy_ends(box: FiberInfrastructure) -> dict[tuple[int, str], str]:
    """(fibra, lado) já usados na caixa → o que os usa (fusão ou splitter)."""
    out: dict[tuple[int, str], str] = {}
    for f in FiberFusion.objects.filter(infrastructure=box):
        out[(f.fiber_a_id, f.fiber_a_side)] = "uma fusão"
        out[(f.fiber_b_id, f.fiber_b_side)] = "uma fusão"
    for sp in Splitter.objects.filter(infrastructure=box, input_strand__isnull=False):
        out[(sp.input_strand_id, sp.input_side)] = f"a entrada do splitter {sp.ratio}"
    for p in SplitterPort.objects.filter(splitter__infrastructure=box, output_strand__isnull=False):
        out[(p.output_strand_id, p.output_side)] = f"a porta {p.number} de um splitter"
    return out


def _check_free(box: FiberInfrastructure, strand: FiberStrand, side: str, label: str) -> None:
    used = _busy_ends(box).get((strand.pk, side))
    if used:
        raise InventoryValidationError(
            f"a {label} (fibra {strand.absolute_number} de {strand.tube.cable.name}) já está em {used}"
        )


def _splitter_power(
    sp: Splitter, box: FiberInfrastructure, budget: dict[str, Any]
) -> dict[str, Any]:
    """Potência estimada na entrada do splitter: TX da fonte (a montante) - perdas até à caixa."""
    if sp.input_strand is None:
        return {"dbm": None, "reason": "sem fibra de entrada"}
    strand = sp.input_strand
    walked = _walk(strand, sp.input_side, _pos_on(strand.tube.cable, box), budget, upstream=True)
    if walked["end"]["reason"] != "port":
        return {"dbm": None, "reason": walked["end"]["label"]}
    tx = _start_tx(walked["port"], budget)
    loss = _accumulate(walked["steps"], budget, None)
    return {
        "dbm": round(tx["dbm"] - loss, 2),
        "source": tx["source"],
        "from": f"{walked['port'].device.name} → {walked['port'].name}",
        "loss_db": round(loss, 2),
        "km": round(walked["total_km"], 3),
    }


def splitters_payload(box: FiberInfrastructure) -> list[dict[str, Any]]:
    budget = runtime_settings.get_runtime_config().optical_budget
    out = []
    qs = Splitter.objects.filter(infrastructure=box).select_related("input_strand__tube__cable")
    for sp in qs.prefetch_related("ports__output_strand__tube__cable"):
        loss = budget["splitters"].get(sp.ratio, 0.0)
        power = _splitter_power(sp, box, budget)
        port_dbm = round(power["dbm"] - loss, 2) if power["dbm"] is not None else None
        ports = [
            {
                "number": p.number,
                "status": p.status,
                "customer": p.customer,
                "note": p.note,
                "output": (
                    _fiber_end(p.output_strand, p.output_side, p.output_strand.tube.cable)
                    if p.output_strand_id
                    else None
                ),
                "dbm": port_dbm,
            }
            for p in sp.ports.all()
        ]
        counts = {k: 0 for k, _ in SplitterPort.STATUSES}
        for p in ports:
            counts[p["status"]] += 1
        out.append(
            {
                "id": sp.pk,
                "name": sp.name or f"Splitter {sp.ratio}",
                "ratio": sp.ratio,
                "loss_db": loss,
                "input": (
                    _fiber_end(sp.input_strand, sp.input_side, sp.input_strand.tube.cable)
                    if sp.input_strand_id
                    else None
                ),
                "power": power,
                "counts": counts,
                "ports": ports,
            }
        )
    return out


def _box(box_id: int) -> FiberInfrastructure:
    return get_object_or_404(FiberInfrastructure, pk=box_id, type__in=BOX_TYPES)


def create_splitter(box_id: int, *, ratio: str, name: str = "") -> dict[str, Any]:
    box = _box(box_id)
    if ratio not in dict(Splitter.RATIOS):
        raise InventoryValidationError("razão do splitter: 1x2, 1x4, 1x8, 1x16 ou 1x32")
    with transaction.atomic():
        sp = Splitter.objects.create(
            infrastructure=box, ratio=ratio, name=(name or "").strip()[:60]
        )
        SplitterPort.objects.bulk_create(
            [SplitterPort(splitter=sp, number=n) for n in range(1, sp.port_count + 1)]
        )
    _invalidate_all()
    return {"id": sp.pk}


def update_splitter(
    box_id: int, splitter_id: int, *, name: Any = _UNSET, input: Any = _UNSET
) -> dict[str, Any]:
    box = _box(box_id)
    sp = get_object_or_404(Splitter, pk=splitter_id, infrastructure=box)
    with transaction.atomic():
        if name is not _UNSET:
            sp.name = (name or "").strip()[:60]
        if input is not _UNSET:
            if input is None:
                sp.input_strand, sp.input_side = None, ""
            else:
                strand, side = _resolve_end(box, input, "entrada")
                if (strand.pk, side) != (sp.input_strand_id, sp.input_side):
                    _check_free(box, strand, side, "fibra de entrada")
                sp.input_strand, sp.input_side = strand, side
        sp.save()
    _invalidate_all()
    return {"id": sp.pk}


def delete_splitter(box_id: int, splitter_id: int) -> None:
    sp = get_object_or_404(Splitter, pk=splitter_id, infrastructure=_box(box_id))
    sp.delete()
    _invalidate_all()


def update_splitter_port(
    box_id: int,
    splitter_id: int,
    number: int,
    *,
    status: Any = _UNSET,
    customer: Any = _UNSET,
    note: Any = _UNSET,
    output: Any = _UNSET,
) -> dict[str, Any]:
    box = _box(box_id)
    port = get_object_or_404(
        SplitterPort, splitter_id=splitter_id, splitter__infrastructure=box, number=number
    )
    with transaction.atomic():
        if status is not _UNSET:
            if status not in dict(SplitterPort.STATUSES):
                raise InventoryValidationError("estado: livre, reservada, ocupada ou bloqueada")
            port.status = status
        if customer is not _UNSET:
            port.customer = (customer or "").strip()[:120]
        if note is not _UNSET:
            port.note = (note or "").strip()[:200]
        if port.status == SplitterPort.STATUS_RESERVED and not port.customer:
            raise InventoryValidationError("uma porta reservada precisa do cliente/reserva")
        if output is not _UNSET:
            if output is None:
                port.output_strand, port.output_side = None, ""
            else:
                strand, side = _resolve_end(box, output, "saída")
                if (strand.pk, side) != (port.output_strand_id, port.output_side):
                    _check_free(box, strand, side, "fibra de saída")
                port.output_strand, port.output_side = strand, side
        port.save()
    _invalidate_all()
    return {"number": port.number, "status": port.status}


def _invalidate_all() -> None:
    invalidate_fiber_cache()
    invalidate_dashboard_cache()
