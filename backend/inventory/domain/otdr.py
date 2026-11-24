"""Localização de rompimento por OTDR sobre o traçado de um cabo (EV-0127). Puro.

A leitura do OTDR é comprimento de FIBRA; o traçado no mapa é mais curto pela folga (reservas
técnicas, sobras em caixas, catenária). Distância sobre o traçado = OTDR / (1 + folga).
Mede-se como o inventário mede o comprimento do cabo (``calculate_path_length``: haversine
entre vértices consecutivos), para os quilómetros baterem com o «73,13 km» do cabo.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import pairwise

from .geometry import haversine_km

Coord = tuple[float, float]  # (lng, lat) — a ordem GeoJSON do backend
TOLERANCE_M = 40.0


def _seg_m(a: Coord, b: Coord) -> float:
    return haversine_km(a[1], a[0], b[1], b[0]) * 1000.0


def cumulative_m(coords: Sequence[Coord]) -> list[float]:
    """Distância acumulada (m) desde o 1.º vértice até cada vértice."""
    acc = [0.0]
    for a, b in pairwise(coords):
        acc.append(acc[-1] + _seg_m(a, b))
    return acc


def _lerp(a: Coord, b: Coord, t: float) -> Coord:
    # dentro de um segmento curto do traçado, a interpolação linear em graus basta
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def point_at(coords: Sequence[Coord], acc: Sequence[float], dist_m: float) -> Coord:
    """Ponto a ``dist_m`` metros do 1.º vértice, interpolado no segmento certo."""
    if dist_m <= 0:
        return coords[0]
    if dist_m >= acc[-1]:
        return coords[-1]
    for i in range(1, len(acc)):
        if acc[i] >= dist_m:
            span = acc[i] - acc[i - 1]
            t = 0.0 if span <= 0 else (dist_m - acc[i - 1]) / span
            return _lerp(coords[i - 1], coords[i], t)
    return coords[-1]


def substring(
    coords: Sequence[Coord], acc: Sequence[float], start_m: float, end_m: float
) -> list[Coord]:
    """Trecho do traçado entre duas distâncias (com os vértices do meio)."""
    start_m, end_m = max(0.0, start_m), min(acc[-1], end_m)
    out = [point_at(coords, acc, start_m)]
    out += [coords[i] for i in range(len(coords)) if start_m < acc[i] < end_m]
    out.append(point_at(coords, acc, end_m))
    return out


def path_starts_at_a(coords: Sequence[Coord], a: Coord | None, b: Coord | None) -> bool:
    """O traçado foi desenhado de A para B? Sem as duas pontas conhecidas, assume que sim."""
    if a is None or b is None:
        return True
    straight = _seg_m(coords[0], a) + _seg_m(coords[-1], b)
    swapped = _seg_m(coords[0], b) + _seg_m(coords[-1], a)
    return straight <= swapped
