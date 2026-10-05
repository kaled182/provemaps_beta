"""EV-0015 — parser KML/KMZ: namespaces, MultiGeometry, gx:Track, um traçado por Placemark."""

from __future__ import annotations

import io
import zipfile

from django.test import SimpleTestCase

from inventory.domain import kml as kml_mod
from inventory.usecases.fibers import FiberValidationError, parse_kml_coordinates

LINE_A = "-49.30,-16.60,0 -49.31,-16.61,0 -49.32,-16.62,0"
LINE_B = "-49.10,-16.80,0 -49.11,-16.81,0"


def _kml(body: str, ns: str = 'xmlns="http://www.opengis.net/kml/2.2"') -> bytes:
    return f'<?xml version="1.0" encoding="UTF-8"?><kml {ns}><Document>{body}</Document></kml>'.encode()


def _placemark(name: str, coords: str) -> str:
    return f"<Placemark><name>{name}</name><LineString><coordinates>{coords}</coordinates></LineString></Placemark>"


class ParseKmlPathsTests(SimpleTestCase):
    def test_one_path_per_placemark_not_concatenated(self):
        paths = kml_mod.parse_kml_paths(_kml(_placemark("A", LINE_A) + _placemark("B", LINE_B)))
        self.assertEqual([p.name for p in paths], ["A", "B"])
        self.assertEqual([len(p.coords) for p in paths], [3, 2])

    def test_old_namespace_21_and_no_namespace(self):
        for ns in (
            'xmlns="http://earth.google.com/kml/2.1"',
            'xmlns="http://www.opengis.net/kml/2.0"',
            "",
        ):
            paths = kml_mod.parse_kml_paths(_kml(_placemark("A", LINE_A), ns=ns))
            self.assertEqual(len(paths), 1, ns)
            self.assertEqual(paths[0].coords[0], {"lat": -16.6, "lng": -49.3})

    def test_multigeometry_joins_segments_of_the_same_placemark(self):
        body = (
            "<Placemark><name>MG</name><MultiGeometry>"
            f"<LineString><coordinates>{LINE_A}</coordinates></LineString>"
            f"<LineString><coordinates>{LINE_B}</coordinates></LineString>"
            "</MultiGeometry></Placemark>"
        )
        paths = kml_mod.parse_kml_paths(_kml(body))
        self.assertEqual(len(paths), 1)
        self.assertEqual(len(paths[0].coords), 5)
        self.assertEqual(paths[0].source, "MultiGeometry")

    def test_gx_track(self):
        body = (
            '<Placemark><name>T</name><gx:Track xmlns:gx="http://www.google.com/kml/ext/2.2">'
            "<gx:coord>-49.30 -16.60 0</gx:coord><gx:coord>-49.31 -16.61 0</gx:coord>"
            "</gx:Track></Placemark>"
        )
        paths = kml_mod.parse_kml_paths(_kml(body))
        self.assertEqual(paths[0].source, "gx:Track")
        self.assertEqual(
            paths[0].coords, [{"lat": -16.6, "lng": -49.3}, {"lat": -16.61, "lng": -49.31}]
        )

    def test_kmz_is_unzipped(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("doc.kml", _kml(_placemark("Z", LINE_A)))
            zf.writestr("images/x.png", b"\x89PNG")
        paths = kml_mod.parse_kml_paths(buf.getvalue())
        self.assertEqual(paths[0].name, "Z")

    def test_dedupes_consecutive_points_and_drops_out_of_range(self):
        coords = "-49.30,-16.60 -49.30,-16.60 -49.31,-16.61 200,-16.62 -49.32,-16.62"
        paths = kml_mod.parse_kml_paths(_kml(_placemark("D", coords)))
        self.assertEqual(len(paths[0].coords), 3)

    def test_invalid_payloads(self):
        with self.assertRaises(kml_mod.KmlParseError):
            kml_mod.parse_kml_paths(b"<kml><Document></Document></kml>")
        with self.assertRaises(kml_mod.KmlParseError):
            kml_mod.parse_kml_paths(b"isto nao e xml")
        with self.assertRaises(kml_mod.KmlParseError):
            kml_mod.parse_kml_paths(b"PK\x03\x04lixo")


class ParseKmlCoordinatesCompatTests(SimpleTestCase):
    """A assinatura antiga continua, mas devolve o traçado mais longo — não um zigue-zague."""

    def test_returns_longest_placemark(self):
        coords = parse_kml_coordinates(
            io.BytesIO(_kml(_placemark("curto", LINE_B) + _placemark("longo", LINE_A)))
        )
        self.assertEqual(len(coords), 3)
        self.assertEqual(coords[0], {"lat": -16.6, "lng": -49.3})

    def test_raises_fiber_validation_error(self):
        with self.assertRaises(FiberValidationError):
            parse_kml_coordinates(io.BytesIO(b"<kml></kml>"))
        with self.assertRaises(FiberValidationError):
            parse_kml_coordinates(io.BytesIO(_kml(_placemark("um ponto", "-49.30,-16.60"))))
