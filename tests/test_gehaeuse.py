# -*- coding: utf-8 -*-
"""Elektronikgehäuse: Prüfung ohne FreeCAD, Export und Passung mit FreeCADCmd."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.gehaeuse import masse_korpus, pruefe, standard  # noqa: E402
from sidecar.layout import Projekt, auftrag_bauen  # noqa: E402
from sidecar.stlcheck import pruefe_stl  # noqa: E402


def _freecad() -> str | None:
    env = os.environ.get("FREECADCMD")
    if env and Path(env).exists():
        return env
    apprun = Path("/tmp/freecad/squashfs-root/AppRun")
    return str(apprun) if apprun.exists() else None


class GehaeusePruefung(unittest.TestCase):
    def test_standard_ist_gueltig_und_alte_datei_laedt(self):
        self.assertEqual(pruefe(standard()), [])
        projekt = Projekt.from_dict({"format": "cadstudio.projekt", "version": 1, "name": "Alt"})
        self.assertFalse(projekt.nur_gehaeuse)
        wieder = Projekt.from_dict(Projekt(name="Box", nur_gehaeuse=True, gehaeuse=standard()).to_dict())
        self.assertTrue(wieder.nur_gehaeuse)
        self.assertEqual(wieder.gehaeuse["platine"], "raspberry_pi_4")

    def test_extrem_und_schiebedeckel_sind_gueltig(self):
        extrem = standard()
        extrem.update(
            {
                "innen_b_mm": 160,
                "innen_t_mm": 110,
                "innen_h_mm": 48,
                "wand_mm": 2.4,
                "boden_mm": 2.0,
                "deckel_mm": 2.0,
                "radius_mm": 6,
                "spiel_mm": 0.35,
                "senkung": "ja",
                "lueftung": "ja",
                "laschen": "ja",
                "platine": "arduino_uno",
                "standoff_h_mm": 10,
                "standoff_d_mm": 5,
            }
        )
        self.assertEqual(pruefe(extrem), [], pruefe(extrem))
        schiebe = standard()
        schiebe["deckel"] = "schiebe"
        self.assertEqual(pruefe(schiebe), [])

    def test_ungueltige_werte_auf_deutsch(self):
        duenn = standard()
        duenn["wand_mm"] = 0.4
        self.assertTrue(any("außerhalb" in text for text in pruefe(duenn)))
        gross = standard()
        gross["platine"] = "eigene"
        gross["platine_b_mm"] = 200
        self.assertTrue(any("passt nicht" in text for text in pruefe(gross)))
        ecke = standard()
        ecke["oeffnungen"] = [{"seite": "vorne", "form": "rechteck", "pos_mm": 6, "unten_mm": 14, "breite_mm": 8, "hoehe_mm": 6}]
        self.assertTrue(any("Schraubensäule" in text or "Ecke" in text for text in pruefe(ecke)))
        auftrag = auftrag_bauen(Projekt(name="Kaputt", nur_gehaeuse=True, gehaeuse=duenn))
        self.assertFalse(auftrag["ok"])

    def test_innenbreite_aendert_das_aussenmass(self):
        schmal = masse_korpus(standard())
        breit = masse_korpus({**standard(), "innen_b_mm": 130})
        self.assertAlmostEqual(breit[0] - schmal[0], 30, places=2)


class GehaeuseExport(unittest.TestCase):
    def test_korpus_und_deckel_und_groessere_breite(self):
        freecad = _freecad()
        if not freecad:
            self.fail("FreeCADCmd fehlt. Der Export wurde nicht als bestanden gewertet.")
        os.environ["FREECADCMD"] = freecad
        from sidecar.engine import generiere

        def exportiere(name, daten):
            with tempfile.TemporaryDirectory() as tmp:
                ergebnis = generiere(Projekt(name=name, nur_gehaeuse=True, gehaeuse=daten), Path(tmp), freecad_pfad=freecad)
                self.assertTrue(ergebnis["ok"], ergebnis.get("fehler"))
                self.assertEqual(len(ergebnis["teile"]), 2)
                kaesten = {}
                for teil in ergebnis["teile"]:
                    self.assertTrue(teil["ok"], teil)
                    for datei in teil["dateien"]:
                        stl = Path(datei["stl"])
                        fcstd = Path(datei["fcstd"])
                        self.assertGreater(stl.stat().st_size, 200)
                        self.assertGreater(fcstd.stat().st_size, 200)
                        mesh = pruefe_stl(stl, tuple(datei["soll_mm"]))
                        self.assertTrue(mesh["ok"] and mesh["wasserdicht"] and mesh["mannigfaltig"], (datei["id"], mesh))
                        self.assertEqual(datei["solid"]["solids"], 1)
                        self.assertTrue(datei["solid"]["valid"])
                        self.assertTrue(datei["mesh_freecad"]["ok"], datei.get("mesh_freecad"))
                        self.assertTrue(datei["fcstd_erneut_geladen"]["ok"])
                        kaesten[datei["id"]] = mesh["bbox_mm"]
                return kaesten

        normal = exportiere("Normal", standard())
        self.assertIn("G_korpus", normal)
        self.assertIn("G_deckel", normal)
        weit = standard()
        weit["innen_b_mm"] = 130
        breiter = exportiere("Breiter", weit)
        self.assertGreater(breiter["G_korpus"][0], normal["G_korpus"][0] + 20)
        extrem = standard()
        extrem.update(
            {
                "innen_b_mm": 160,
                "innen_t_mm": 110,
                "innen_h_mm": 48,
                "wand_mm": 2.4,
                "boden_mm": 2.0,
                "deckel_mm": 2.0,
                "radius_mm": 6,
                "spiel_mm": 0.35,
                "senkung": "ja",
                "lueftung": "ja",
                "laschen": "ja",
                "platine": "arduino_uno",
                "standoff_h_mm": 10,
                "standoff_d_mm": 5,
            }
        )
        exportiere("Extrem", extrem)
        schiebe = standard()
        schiebe["deckel"] = "schiebe"
        exportiere("Schiebe", schiebe)

    def test_deckel_schrauben_und_platine_fluchten(self):
        freecad = _freecad()
        if not freecad:
            self.fail("FreeCADCmd fehlt. Der Export wurde nicht als bestanden gewertet.")
        os.environ["FREECADCMD"] = freecad
        from sidecar.detect_freecad import freecad_command
        from sidecar.engine import FreeCADSession

        session = FreeCADSession(freecad_command(Path(freecad)))
        session.start()
        try:
            normal = session.request({"cmd": "gehaeuse_passung", "parameter": standard()})["result"]
            self.assertTrue(normal["ok"], normal)
            self.assertLess(normal["schnittvolumen_mm3"], 0.05)
            self.assertTrue(all(abs(wert - 0.2) <= 0.08 for wert in normal["luecken_mm"]), normal)
            self.assertTrue(normal["schrauben_ok"] and normal["platine_ok"])
            eng = standard()
            eng["spiel_mm"] = 0.35
            gemessen = session.request({"cmd": "gehaeuse_passung", "parameter": eng})["result"]
            self.assertTrue(gemessen["ok"], gemessen)
            self.assertTrue(all(abs(wert - 0.35) <= 0.08 for wert in gemessen["luecken_mm"]), gemessen)
            schiebe = standard()
            schiebe["deckel"] = "schiebe"
            geschoben = session.request({"cmd": "gehaeuse_passung", "parameter": schiebe})["result"]
            self.assertTrue(geschoben["ok"], geschoben)
            self.assertLess(geschoben["schnittvolumen_mm3"], 0.05)
            uno = standard()
            uno["platine"] = "arduino_uno"
            uno["standoff_loch"] = "m3"
            uno["standoff_d_mm"] = 5
            arduino = session.request({"cmd": "gehaeuse_passung", "parameter": uno})["result"]
            self.assertTrue(arduino["ok"], arduino)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
