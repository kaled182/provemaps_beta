"""Rastreamento destacado em árvore (EV-0143).

A partir de uma ponta de fibra, procura primeiro a fonte da luz (a porta da OLT/switch a
montante, atravessando fusões e splitters) e depois desce dela até cada destino: num splitter a
luz reparte-se e cada porta com fibra de saída vira um ramo. Cada passo leva os km, a perda e o
dBm acumulados (orçamento óptico, EV-0140) e cada troço de cabo a geometria percorrida, para o
destaque no mapa. O ramo que contém a fibra pedida vem marcado com ``focus``.
"""

from __future__ import annotations

import json
import math
from typing import Any

from django.db import connection
from django.shortcuts import get_object_or_404

from inventory.models import FiberCable, FiberStrand, Splitter
from setup_app.services import runtime_settings

from .ceo_fusions import (
    SIDES,
    _accumulate,
    _ceo_label,
    _port_step,
    _pos_on,
    _start_tx,
    _walk,
    _where,
)
from .devices_common import InventoryValidationError

MAX_DEPTH = 4  # splitters em cascata (OLT → CEO → CTO → …)
MAX_BRANCHES = 128  # ramos percorridos num rastreamento


def _port_at(strand: FiberStrand, end: str):
    return strand.connected_device_port if end == "a" else strand.connected_device_port_b


def _find_source(
    strand: FiberStrand, start: str, budget: dict[str, Any]
) -> tuple[FiberStrand, str, dict[str, Any]]:
    """Ponta de onde a luz parte: a própria, se tem porta; senão a porta a montante, procurada
    primeiro pela ponta ``start`` e depois pela outra."""
    if _port_at(strand, start) is not None:
        return strand, start, {"found": True}
    reasons = []
    for end in (start, "b" if start == "a" else "a"):
        pos = -math.inf if end == "a" else math.inf
        up = _walk(strand, end, pos, budget, upstream=True)
        if up["end"]["reason"] == "port" and up["port_end"] is not None:
            strand_id, side = up["port_end"]
            src = FiberStrand.objects.select_related(
                "tube__cable",
                "connected_device_port__device__site",
                "connected_device_port_b__device__site",
            ).get(pk=strand_id)
            return src, side, {"found": True}
        reasons.append(up["end"]["label"])
    return strand, start, {"found": False, "label": "; ".join(dict.fromkeys(reasons))}


def _branch(
    strand: FiberStrand,
    direction: str,
    pos: float,
    ctx: dict[str, Any],
    *,
    prefix: list[dict[str, Any]],
    km0: float,
    loss0: float,
    depth: int,
) -> dict[str, Any]:
    budget, tx = ctx["budget"], ctx["tx"]
    walked = _walk(strand, direction, pos, budget)
    steps = prefix + walked["steps"]
    loss = _accumulate(steps, budget, tx, km0=km0, loss0=loss0)
    km = steps[-1]["acc_km"] if steps else km0
    node: dict[str, Any] = {
        "steps": steps,
        "end": walked["end"],
        "km": round(km, 3),
        "loss_db": round(loss, 2),
        "dbm": round(tx["dbm"] - loss, 2) if tx else None,
        "focus": any(s.get("strand_id") == ctx["focus"] for s in steps),
        "splitter": None,
        "branches": [],
    }
    end = walked["end"]
    if end["reason"] != "splitter":
        return node
    sp = (
        Splitter.objects.select_related("infrastructure")
        .prefetch_related(
            "ports__output_strand__tube__cable",
            "ports__output_strand__connected_device_port__device__site",
            "ports__output_strand__connected_device_port_b__device__site",
        )
        .get(pk=end["splitter_id"])
    )
    box = sp.infrastructure
    sp_loss = budget["splitters"].get(sp.ratio, 0.0)
    after = loss + sp_loss
    node["splitter"] = {
        "id": sp.pk,
        "name": sp.name or f"Splitter {sp.ratio}",
        "ratio": sp.ratio,
        "loss_db": sp_loss,
        "ceo_id": box.pk,
        "ceo_name": _ceo_label(box),
        "kind": "cto" if box.type == "splitter_box" else "ceo",
        "dbm_out": round(tx["dbm"] - after, 2) if tx else None,
        **_where(box),
    }
    for port in sp.ports.all():
        item: dict[str, Any] = {
            "number": port.number,
            "status": port.status,
            "customer": port.customer,
            "dbm": round(tx["dbm"] - after, 2) if tx else None,
            "node": None,
        }
        if port.output_strand_id and depth < MAX_DEPTH and ctx["branches"] < MAX_BRANCHES:
            ctx["branches"] += 1
            out = port.output_strand
            item["node"] = _branch(
                out,
                port.output_side,
                _pos_on(out.tube.cable, box),
                ctx,
                prefix=[],
                km0=km,
                loss0=after,
                depth=depth + 1,
            )
        elif port.output_strand_id:
            ctx["truncated"] = True
        node["branches"].append(item)
    node["focus"] = node["focus"] or any(b["node"] and b["node"]["focus"] for b in node["branches"])
    return node


def _cable_steps(node: dict[str, Any]):
    for step in node["steps"]:
        if step["type"] == "cable":
            yield step
    for b in node["branches"]:
        if b["node"]:
            yield from _cable_steps(b["node"])


def _attach_geometry(root: dict[str, Any]) -> None:
    """Cada troço de cabo recebe ``path`` ([[lng, lat], …]) — a parte do traçado percorrida,
    cortada por ST_LineSubstring na proporção dos km sobre o comprimento geográfico do traçado
    (o mesmo em que se mede a posição das caixas; ``length_km`` pode incluir folgas)."""
    table = FiberCable._meta.db_table
    sql = (
        "WITH c AS (SELECT path, NULLIF(ST_Length(path::geography), 0) / 1000.0 AS km "
        f"FROM {table} WHERE id = %s AND path IS NOT NULL) "
        "SELECT ST_AsGeoJSON(ST_LineSubstring(path, "
        "COALESCE(LEAST(GREATEST(%s / km, 0), 1), 0), COALESCE(LEAST(GREATEST(%s / km, 0), 1), 1)"
        "), 6) FROM c"
    )
    with connection.cursor() as cur:
        for step in _cable_steps(root):
            start, stop = step.pop("from_km", 0.0), step.pop("to_km", math.inf)
            lo, hi = sorted((start, min(stop, 1e9)))
            cur.execute(sql, [step["cable_id"], lo, hi])
            row = cur.fetchone()
            geo = json.loads(row[0]) if row and row[0] else None
            coords = geo.get("coordinates") if geo else None
            if coords and geo["type"] == "Point":
                coords = [coords, coords]
            if coords and start > stop:  # no sentido da luz (rumo à ponta A)
                coords.reverse()
            step["path"] = coords or None


def trace_tree(strand_id: int, *, start: str = "a") -> dict[str, Any]:
    """Rastreamento da fonte (OLT/switch) até aos destinos, com os ramos dos splitters."""
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
    budget = runtime_settings.get_runtime_config().optical_budget
    src, src_end, source = _find_source(strand, start, budget)
    port = _port_at(src, src_end)
    tx = _start_tx(port, budget)
    if port is not None:
        source["label"] = f"{port.device.name} → {port.name}"
    ctx = {"budget": budget, "tx": tx, "focus": strand_id, "branches": 0, "truncated": False}
    root = _branch(
        src,
        "b" if src_end == "a" else "a",
        -math.inf if src_end == "a" else math.inf,
        ctx,
        prefix=[_port_step(port)] if port is not None else [],
        km0=0.0,
        loss0=0.0,
        depth=0,
    )
    _attach_geometry(root)
    return {
        "start": {"strand_id": strand_id, "end": start},
        "source": source,
        "tx": tx,
        "tree": root,
        "truncated": ctx["truncated"],
        "budget": {
            "fiber_db_km": budget["fiber_db_km"],
            "fusion_db": budget["fusion_db"],
            "splitters": budget["splitters"],
        },
    }
