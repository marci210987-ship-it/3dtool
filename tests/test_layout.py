# -*- coding: utf-8 -*-
"""Layout-Tests ohne FreeCAD."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.layout import (  # noqa: E402
    Box,
    Projekt,
    Schublade,
    auftrag_bauen,
    footprint,
    kollisionen,
    plan_ansicht,
    ueberlappung,
)


class LayoutTest(unittest.TestCase):
    def test_plan_480x420(self):
        projekt = Projekt(name="Abnahme", schublade=Schublade(480, 420, 80, spiel_mm=1.0))
        ansicht = plan_ansicht(projekt)
        self.assertFalse(ansicht["ungueltig"])
        self.assertEqual(ansicht["einheiten_x"], 11)
        self.assertEqual(ansicht["einheiten_y"], 9)
        self.assertAlmostEqual(ansicht["nutz_x"], 478.0, places=3)
        self.assertAlmostEqual(ansicht["nutz_y"], 418.0, places=3)
        self.assertAlmostEqual(ansicht["rest_x"], 16.0, places=3)
        self.assertAlmostEqual(ansicht["rest_y"], 40.0, places=3)
        self.assertEqual(len(ansicht["platten"]), 4)
        self.assertEqual(ansicht["randstreifen"], [])
        self.assertFalse(ansicht["randstreifen_geometrie"])
        erwartet = [
            (5, 4, 0, 0, 16.0, 0.0, 20.0, 0.0, 226.0, 188.0),
            (5, 5, 0, 4, 16.0, 0.0, 0.0, 20.0, 226.0, 230.0),
            (6, 4, 5, 0, 0.0, 0.0, 20.0, 0.0, 252.0, 188.0),
            (6, 5, 5, 4, 0.0, 0.0, 0.0, 20.0, 252.0, 230.0),
        ]
        for platte, soll in zip(ansicht["platten"], erwartet):
            ist = (
                platte["einheiten_x"],
                platte["einheiten_y"],
                platte["pos_x"],
                platte["pos_y"],
                platte["rand_links"],
                platte["rand_rechts"],
                platte["rand_vorne"],
                platte["rand_hinten"],
                platte["breite_mm"],
                platte["tiefe_mm"],
            )
            for a, b in zip(ist, soll):
                if isinstance(b, float):
                    self.assertAlmostEqual(a, b, places=2)
                else:
                    self.assertEqual(a, b)
            self.assertTrue(platte["passt_in_bauraum"])
        self.assertEqual(ansicht["verbinder_anzahl"], 16)
        self.assertTrue(all(p["breite_mm"] <= 256 and p["tiefe_mm"] <= 256 for p in ansicht["platten"]))

    def test_randstreifen_werden_nur_ausgewiesen(self):
        # 12 Einheiten, Rest größer als die Reserve beider 6er-Platten.
        projekt = Projekt(schublade=Schublade(innenbreite_mm=526, innentiefe_mm=200, nutzhoehe_mm=50, spiel_mm=1.0))
        # nutz_x = 524, 12*42=504, rest=20, Reserve je 6er-Platte = 4 mm.
        ansicht = plan_ansicht(projekt)
        self.assertTrue(ansicht["randstreifen"], ansicht["text"])
        self.assertFalse(ansicht["randstreifen_geometrie"])
        self.assertIn("nicht", ansicht["randstreifen_hinweis"].lower())

    def test_vier_boxen_drehen_verschieben_ueberlappung(self):
        boxen = [
            Box("B1", "Klein", 0, 0, 1, 1, 3),
            Box("B2", "Mittel", 2, 0, 2, 2, 3, fach_x=2, fach_y=2),
            Box("B3", "Lang", 5, 0, 1, 3, 2, fach_x=1, fach_y=3),
            Box("B4", "Gross", 0, 4, 2, 3, 3),
        ]
        projekt = Projekt(schublade=Schublade(480, 420, 80), boxen=boxen)
        self.assertEqual(kollisionen(boxen), [])
        ansicht = plan_ansicht(projekt)
        self.assertTrue(ansicht["ok"], ansicht["fehler"])
        self.assertEqual(ansicht["belegte_zellen"], 1 + 4 + 3 + 6)

        boxen[0].x, boxen[0].y = 8, 6
        boxen[2].rotation = 90
        self.assertEqual(footprint(boxen[2]), (5, 0, 3, 1))
        self.assertEqual(kollisionen(boxen), [])
        ansicht = plan_ansicht(projekt)
        self.assertTrue(ansicht["ok"], ansicht["fehler"])

        boxen[1].x, boxen[1].y = 0, 4
        fund = kollisionen(boxen)
        self.assertEqual(len(fund), 1)
        self.assertEqual(set(fund[0]["boxen"]), {"B2", "B4"})
        ansicht = plan_ansicht(projekt)
        self.assertFalse(ansicht["ok"])
        auftrag = auftrag_bauen(projekt)
        self.assertFalse(auftrag["ok"])

        boxen[1].x, boxen[1].y = 2, 0
        boxen[3].ez = 4
        ansicht = plan_ansicht(projekt)
        self.assertTrue(ansicht["ok"], ansicht["fehler"])
        self.assertTrue(ueberlappung(Box("a", "a", 0, 0, 2, 2), Box("b", "b", 1, 1, 2, 2)))
        self.assertFalse(ueberlappung(Box("a", "a", 0, 0, 2, 2), Box("b", "b", 2, 0, 2, 2)))

    def test_hoehe_blockiert(self):
        box = Box("B1", "Hoch", 0, 0, 1, 1, 6, stapellippe=True)
        projekt = Projekt(schublade=Schublade(480, 420, nutzhoehe_mm=30), boxen=[box])
        ansicht = plan_ansicht(projekt)
        self.assertFalse(ansicht["ok"])
        self.assertTrue(any("Höhe" in f or "Hoehe" in f for f in ansicht["fehler"]))

    def test_phase4_ohne_lippe_behaelt_die_sollhoehe(self):
        box = Box("K1", "Kabelbox", 0, 0, 3, 3, 3, stapellippe=False, kabelkerben=True, fach_x=2, fach_y=2)
        auftrag = auftrag_bauen(Projekt(schublade=Schublade(480, 420, 80), boxen=[box]))
        teil = next(item for item in auftrag["teile"] if item["id"] == "K1")
        self.assertEqual(teil["params"]["Verriegelungsart"], 0)
        self.assertEqual(teil["params"]["Stapellippe"], 0)
        self.assertAlmostEqual(teil["soll_mm"][2], 21.0)

    def test_phase4_mit_lippe_und_deckel(self):
        mit_lippe = Box("K2", "Kabelbox", 0, 0, 3, 3, 3, stapellippe=True, kabelkerben=True, fach_x=2, fach_y=2)
        deckel = Box("D1", "Deckel", 4, 0, 2, 2, 3, stapellippe=False, deckel=True)
        auftrag = auftrag_bauen(Projekt(schublade=Schublade(480, 420, 80), boxen=[mit_lippe, deckel]))
        kabel = next(item for item in auftrag["teile"] if item["id"] == "K2")
        lid = next(item for item in auftrag["teile"] if item["id"] == "D1")
        self.assertEqual(kabel["params"]["Verriegelungsart"], 1)
        self.assertEqual(kabel["params"]["Stapellippe"], 1)
        self.assertAlmostEqual(kabel["soll_mm"][2], 25.4)
        self.assertEqual(lid["params"]["Verriegelungsart"], 2)
        self.assertEqual(lid["params"]["Stapellippe"], 1)
        self.assertAlmostEqual(lid["soll_mm"][2], 25.4)

    def test_freier_bereich(self):
        projekt = Projekt(
            schublade=Schublade(480, 420, 80),
            boxen=[Box("B1", "Klein", 0, 0, 1, 1)],
        )
        ansicht = plan_ansicht(projekt)
        self.assertEqual(len(ansicht["freie_zellen"]), 11 * 9 - 1)
        self.assertNotIn({"x": 0, "y": 0}, ansicht["freie_zellen"])


if __name__ == "__main__":
    unittest.main()
