# -*- coding: utf-8 -*-
"""Synthetische STL-Prüfung, ohne FreeCAD."""

from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.stlcheck import pruefe_stl  # noqa: E402


def _stl(dreiecke) -> bytes:
    blob = bytearray(b"\0" * 80)
    blob += struct.pack("<I", len(dreiecke))
    for a, b, c in dreiecke:
        blob += struct.pack("<12fH", 0, 0, 0, *a, *b, *c, 0)
    return bytes(blob)


def _wuerfel(groesse=10.0):
    s = groesse
    p = [
        (0, 0, 0),
        (s, 0, 0),
        (s, s, 0),
        (0, s, 0),
        (0, 0, s),
        (s, 0, s),
        (s, s, s),
        (0, s, s),
    ]
    seiten = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    dreiecke = []
    for a, b, c, d in seiten:
        dreiecke.append((p[a], p[b], p[c]))
        dreiecke.append((p[a], p[c], p[d]))
    return dreiecke


class StlTest(unittest.TestCase):
    def test_wuerfel_bestanden(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "wuerfel.stl"
            pfad.write_bytes(_stl(_wuerfel(10)))
            bericht = pruefe_stl(pfad, (10, 10, 10))
            self.assertTrue(bericht["ok"], bericht)
            self.assertTrue(bericht["wasserdicht"])
            self.assertTrue(bericht["mannigfaltig"])

    def test_offenes_netz_faellt(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "offen.stl"
            dreiecke = _wuerfel(10)[:-1]
            pfad.write_bytes(_stl(dreiecke))
            bericht = pruefe_stl(pfad, (10, 10, 10))
            self.assertFalse(bericht["ok"])
            self.assertFalse(bericht["wasserdicht"])

    def test_falsche_groesse_faellt(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "wuerfel.stl"
            pfad.write_bytes(_stl(_wuerfel(10)))
            bericht = pruefe_stl(pfad, (20, 10, 10))
            self.assertFalse(bericht["ok"])
            self.assertFalse(bericht["groesse_ok"])

    def test_fehlende_datei(self):
        bericht = pruefe_stl("/tmp/cadstudio-gibt-es-nicht.stl")
        self.assertFalse(bericht["ok"])


if __name__ == "__main__":
    unittest.main()
