# -*- coding: utf-8 -*-
"""Ersatzteil-Generator: Prüfung ohne FreeCAD und Export mit FreeCADCmd."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.ersatzteil import KATALOG, masse, pruefe, standard_parameter, teil_anlegen  # noqa: E402
from sidecar.layout import Projekt, auftrag_bauen  # noqa: E402
from sidecar.stlcheck import pruefe_stl  # noqa: E402


def _freecad() -> str | None:
    env = os.environ.get("FREECADCMD")
    if env and Path(env).exists():
        return env
    apprun = Path("/tmp/freecad/squashfs-root/AppRun")
    return str(apprun) if apprun.exists() else None


EXTREM = {
    "kabelclip": {"durchmesser_mm": 25, "anzahl": 4, "wand_mm": 2.4, "befestigung": "kleben"},
    "distanzhuelse": {"aussen_mm": 30, "innen_mm": 8, "laenge_mm": 60},
    "unterlegscheibe": {"aussen_mm": 40, "innen_mm": 10, "dicke_mm": 3.2},
    "wandhaken": {"hoehe_mm": 70, "ausladung_mm": 40, "breite_mm": 24, "loch_mm": 5},
    "moebelfuss": {"durchmesser_mm": 40, "hoehe_mm": 20, "loch_mm": 6},
    "knopf": {"durchmesser_mm": 40, "hoehe_mm": 22, "welle_mm": 8, "wellenart": "d", "tiefe_mm": 14},
    "stopfen": {"loch_mm": 30, "tiefe_mm": 12, "spiel_mm": 0.5, "kragen_mm": 3.2},
    "winkel": {"laenge_mm": 60, "hoehe_mm": 50, "breite_mm": 24, "dicke_mm": 4.8, "loch_mm": 5},
}

UNGUELTIG = {
    "kabelclip": {"durchmesser_mm": 0},
    "distanzhuelse": {"aussen_mm": 6, "innen_mm": 5.5, "laenge_mm": 10},
    "unterlegscheibe": {"aussen_mm": 8, "innen_mm": 7, "dicke_mm": 1.6},
    "wandhaken": {"hoehe_mm": 40, "ausladung_mm": 22, "breite_mm": 16, "loch_mm": 8},
    "moebelfuss": {"durchmesser_mm": 10, "hoehe_mm": 8, "loch_mm": 9},
    "knopf": {"durchmesser_mm": 16, "hoehe_mm": 10, "welle_mm": 6, "tiefe_mm": 10, "wellenart": "rund"},
    "stopfen": {"loch_mm": 4, "tiefe_mm": 4, "spiel_mm": 1, "kragen_mm": 0.4},
    "winkel": {"laenge_mm": 16, "hoehe_mm": 16, "breite_mm": 10, "dicke_mm": 2.4, "loch_mm": 9},
}


class ErsatzPruefung(unittest.TestCase):
    def test_katalog_hat_den_kabelclip_und_weitere_teile(self):
        ids = [e["id"] for e in KATALOG]
        self.assertIn("kabelclip", ids)
        self.assertGreaterEqual(len(ids), 6)
        self.assertLessEqual(len(ids), 8)

    def test_standard_ist_gueltig_und_extrem_auch(self):
        for eintrag in KATALOG:
            self.assertEqual(pruefe(eintrag["id"], standard_parameter(eintrag["id"])), [], eintrag["id"])
            self.assertEqual(pruefe(eintrag["id"], EXTREM[eintrag["id"]]), [], eintrag["id"])

    def test_ungueltige_werte_auf_deutsch(self):
        for art, werte in UNGUELTIG.items():
            fehler = pruefe(art, werte)
            self.assertTrue(fehler, art)
            self.assertTrue(any(any(ord(c) > 127 or c.isalpha() for c in text) for text in fehler), fehler)

    def test_kabelclip_durchmesser_aendert_das_mass(self):
        klein = masse("kabelclip", standard_parameter("kabelclip"))
        gross = masse("kabelclip", {**standard_parameter("kabelclip"), "durchmesser_mm": 12})
        self.assertIsNotNone(klein)
        self.assertGreater(gross[1], klein[1])
        self.assertGreater(gross[2], klein[2])

    def test_ungueltiger_auftrag_startet_keinen_export(self):
        projekt = Projekt(name="Kaputt", nur_ersatz=True, ersatzteile=[teil_anlegen("kabelclip", {"durchmesser_mm": 0})])
        auftrag = auftrag_bauen(projekt)
        self.assertFalse(auftrag["ok"])
        self.assertTrue(any("außerhalb" in text or "Durchmesser" in text or "Kabeldurchmesser" in text for text in auftrag["fehler"]))


class ErsatzExport(unittest.TestCase):
    def test_jede_art_und_der_kabelclip_mit_anderem_durchmesser(self):
        freecad = _freecad()
        if not freecad:
            self.fail("FreeCADCmd fehlt. Der Export wurde nicht als bestanden gewertet.")
        os.environ["FREECADCMD"] = freecad
        from sidecar.engine import generiere

        def exportiere(name, teile):
            projekt = Projekt(name=name, nur_ersatz=True, ersatzteile=teile)
            with tempfile.TemporaryDirectory() as tmp:
                ergebnis = generiere(projekt, Path(tmp), freecad_pfad=freecad)
                self.assertTrue(ergebnis["ok"], ergebnis.get("fehler"))
                kaesten = []
                for teil in ergebnis["teile"]:
                    self.assertTrue(teil["ok"], teil)
                    for datei in teil["dateien"]:
                        stl = Path(datei["stl"])
                        fcstd = Path(datei["fcstd"])
                        self.assertGreater(stl.stat().st_size, 200)
                        self.assertGreater(fcstd.stat().st_size, 200)
                        mesh = pruefe_stl(stl, tuple(datei["soll_mm"]))
                        self.assertTrue(mesh["ok"], mesh)
                        self.assertTrue(datei["mesh_freecad"]["ok"], datei.get("mesh_freecad"))
                        self.assertTrue(datei["fcstd_erneut_geladen"]["ok"])
                        kaesten.append(mesh["bbox_mm"])
                return kaesten

        klein = exportiere("Clip klein", [teil_anlegen("kabelclip", {"durchmesser_mm": 4}, id_="ET1")])
        gross = exportiere("Clip gross", [teil_anlegen("kabelclip", {"durchmesser_mm": 12}, id_="ET1")])
        self.assertGreater(gross[0][1], klein[0][1] + 2)
        self.assertGreater(gross[0][2], klein[0][2] + 2)
        for eintrag in KATALOG:
            exportiere(eintrag["name"], [teil_anlegen(eintrag["id"], id_="ET1")])
            exportiere(eintrag["name"] + " extrem", [teil_anlegen(eintrag["id"], EXTREM[eintrag["id"]], id_="ET1")])


if __name__ == "__main__":
    unittest.main()
