"""
Leitura de traçados a partir de KML/KMZ (EV-0015).

O parser antigo só via ``kml:LineString`` do namespace 2.2 e **concatenava
todas as LineStrings do ficheiro num único caminho** — vários Placemarks viravam
um zigue-zague. Este módulo:

- aceita KML sem namespace, 2.0, 2.1, 2.2 (e qualquer ``http://…/kml/x.y``) e
  KMZ (zip com ``doc.kml`` ou o primeiro ``*.kml``);
- devolve **um caminho por Placemark** (``parse_kml_paths``), juntando as
  LineStrings de um ``MultiGeometry`` do mesmo Placemark e lendo ``gx:Track``
  (``gx:coord`` = ``lng lat [alt]`` separados por espaço);
- remove pontos consecutivos repetidos e coordenadas fora de alcance;
- ``parse_kml_coordinates`` mantém a assinatura antiga e devolve o **caminho
  mais longo** (em pontos; empate → o primeiro), nunca a concatenação.
"""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from typing import Any

_KML_NS_RE = re.compile(r"^\{(?P<ns>[^}]*)\}(?P<tag>.+)$")
_GX_NS = "http://www.google.com/kml/ext/2.2"


class KmlParseError(ValueError):
    """KML/KMZ ilegível ou sem traçado utilizável."""


@dataclass
class KmlPath:
    name: str
    coords: list[dict[str, float]] = field(default_factory=list)
    source: str = "LineString"  # LineString | MultiGeometry | gx:Track


def _local(tag: str) -> str:
    m = _KML_NS_RE.match(tag)
    return m.group("tag") if m else tag


def _read_bytes(kml_file: Any) -> bytes:
    if isinstance(kml_file, bytes | bytearray):
        return bytes(kml_file)
    if isinstance(kml_file, str):
        return kml_file.encode("utf-8")
    data = kml_file.read()
    if hasattr(kml_file, "seek"):
        try:
            kml_file.seek(0)
        except Exception:
            pass
    return data.encode("utf-8") if isinstance(data, str) else data


def _unwrap_kmz(data: bytes) -> bytes:
    if not data.startswith(b"PK"):
        return data
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not names:
                raise KmlParseError("Failed to process KML: KMZ has no .kml inside")
            chosen = next((n for n in names if n.lower() == "doc.kml"), names[0])
            return zf.read(chosen)
    except zipfile.BadZipFile as exc:
        raise KmlParseError("KMZ inválido") from exc


def _parse_pairs(text: str) -> list[dict[str, float]]:
    """``lng,lat[,alt] lng,lat[,alt] …`` → [{lat, lng}] com validação e dedupe."""
    out: list[dict[str, float]] = []
    for token in (text or "").replace("\n", " ").replace("\t", " ").split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lng, lat = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        _append_point(out, lat, lng)
    return out


def _append_point(out: list[dict[str, float]], lat: float, lng: float) -> None:
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        return
    point = {"lat": lat, "lng": lng}
    if out and out[-1] == point:
        return
    out.append(point)


def _iter_children(el: ET.Element, name: str):
    for child in el.iter():
        if _local(child.tag) == name:
            yield child


def _coords_from_geometry(geom: ET.Element) -> list[dict[str, float]]:
    """Coordenadas de LineString / MultiGeometry / gx:Track (recursivo)."""
    kind = _local(geom.tag)
    if kind == "LineString":
        for c in geom:
            if _local(c.tag) == "coordinates":
                return _parse_pairs(c.text or "")
        return []
    if kind == "Track":  # gx:Track
        out: list[dict[str, float]] = []
        for c in geom:
            if _local(c.tag) == "coord":
                parts = (c.text or "").split()
                if len(parts) >= 2:
                    try:
                        _append_point(out, float(parts[1]), float(parts[0]))
                    except ValueError:
                        continue
        return out
    if kind in ("MultiGeometry", "MultiTrack"):
        out = []
        for c in geom:
            for pt in _coords_from_geometry(c):
                _append_point(out, pt["lat"], pt["lng"])
        return out
    return []


_GEOMETRY_TAGS = ("LineString", "Track", "MultiGeometry", "MultiTrack")
_SOURCE_LABEL = {"Track": "gx:Track", "MultiTrack": "gx:Track"}


def _placemark_path(placemark: ET.Element, seen: set[int], index: int) -> KmlPath | None:
    name_el = next((c for c in placemark if _local(c.tag) == "name"), None)
    name = (name_el.text or "").strip() if name_el is not None else ""
    coords: list[dict[str, float]] = []
    source = "LineString"
    for geom in placemark.iter():
        if geom is placemark or id(geom) in seen or _local(geom.tag) not in _GEOMETRY_TAGS:
            continue
        for pt in _coords_from_geometry(geom):
            _append_point(coords, pt["lat"], pt["lng"])
        source = _SOURCE_LABEL.get(_local(geom.tag), _local(geom.tag))
        seen.update(id(sub) for sub in geom.iter())
    if len(coords) < 2:
        return None
    return KmlPath(name=name or f"Traçado {index}", coords=coords, source=source)


def _loose_geometry_paths(root: ET.Element, seen: set[int], start_index: int) -> list[KmlPath]:
    """Geometrias fora de qualquer Placemark (ficheiros «crus»)."""
    paths: list[KmlPath] = []
    for geom in root.iter():
        if id(geom) in seen or _local(geom.tag) not in ("LineString", "Track"):
            continue
        coords = _coords_from_geometry(geom)
        seen.update(id(sub) for sub in geom.iter())
        if len(coords) >= 2:
            paths.append(
                KmlPath(
                    name=f"Traçado {start_index + len(paths)}",
                    coords=coords,
                    source=_SOURCE_LABEL.get(_local(geom.tag), _local(geom.tag)),
                )
            )
    return paths


def parse_kml_paths(kml_file: Any) -> list[KmlPath]:
    """Todos os traçados do ficheiro, um por Placemark (ou por geometria solta)."""
    data = _unwrap_kmz(_read_bytes(kml_file))
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise KmlParseError(f"Failed to process KML: invalid XML ({exc})") from exc

    seen: set[int] = set()
    paths: list[KmlPath] = []
    for placemark in _iter_children(root, "Placemark"):
        path = _placemark_path(placemark, seen, len(paths) + 1)
        if path is not None:
            paths.append(path)
    paths.extend(_loose_geometry_paths(root, seen, len(paths) + 1))

    if not paths:
        raise KmlParseError("No coordinates found in the KML payload")
    return paths


def longest_path(paths: list[KmlPath]) -> KmlPath:
    best = paths[0]
    for p in paths[1:]:
        if len(p.coords) > len(best.coords):
            best = p
    return best
