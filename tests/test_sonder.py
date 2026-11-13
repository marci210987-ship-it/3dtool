# -*- coding: utf-8 -*-
"""Deckel, Kabelbox und Bestecksortierer über die vorhandenen Generatoren."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.engine import generiere  # noqa: E402
from sidecar.layout import Box, Projekt, Schublade  # noqa: E402


def _freecad() -> str | None:
    env = os.environ.get("FREECADCMD")
    if env and Path(env).exists():
        return env
    apprun = Path("/tmp/freecad/squashfs-root/AppRun")
    return str(apprun) if apprun.exists() else None


class SonderTest(unittest.TestCase):
    def test_deckel_kabel_besteck(self):
        freecad = _freecad()
        if not freecad:
            self.fail("FreeCADCmd fehlt.")
        projekt = Projekt(
            name="Sonder",
            schublade=Schublade(480, 420, 80, spiel_mm=1.0, verbinder_spiel_mm=0.2),
            boxen=[
                Box("D1", "Mit Deckel", 0, 0, 2, 2, 3, deckel=True),
                Box("K1", "Kabelbox", 3, 0, 3, 3, 4, fach_x=2, fach_y=2, kabelkerben=True),
                Box("S1", "Besteck", 0, 4, 6, 3, 4, art="besteck"),
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            ergebnis = generiere(projekt, Path(tmp), freecad_pfad=freecad)
            self.assertTrue(ergebnis["ok"], ergebnis.get("fehler"))
            namen = {datei["id"] for teil in ergebnis["teile"] for datei in teil["dateien"]}
            self.assertIn("D1_Deckel", namen)
            self.assertIn("D1_Box", namen)
            self.assertTrue(any(name.startswith("S1_Segment_") for name in namen))
            self.assertIn("S1_Segmentverbinder", namen)
