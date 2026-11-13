# -*- coding: utf-8 -*-
"""Eigene Teile, Randstreifen-Füllplatten und Auto-Bestückung."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.autofill import auto_bestuecken  # noqa: E402
from sidecar.eigenteil import Eigenteil, eigenteil_pruefen, eigenteil_sollgroesse  # noqa: E402
from sidecar.layout import Box, Projekt, Schublade, auftrag_bauen, layout_pruefen, footprint, ueberlappung  # noqa: E402


def _rechteck(b=40.0, t=30.0, loch=False, x=0.0, y=0.0):
    return {"typ": "rechteck", "x": x, "y": y, "b": b, "t": t, "loch": loch}


class EigenteilPruefung(unittest.TestCase):
    def test_gueltiges_teil(self):
        teil = Eigenteil(id="E1", name="Halter", hoehe_mm=12, formen=[_rechteck(), {"typ": "kreis", "x": 20, "y": 15, "r": 5, "loch": True}])
        self.assertEqual(eigenteil_pruefen(teil), [])
        self.assertEqual(eigenteil_sollgroesse(teil), [40.0, 30.0, 12.0])

    def test_fehler(self):
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", formen=[])))
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", formen=[_rechteck(loch=True)])))
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=0.1, formen=[_rechteck()])))
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=5, boden_mm=5, formen=[_rechteck()])))
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", formen=[_rechteck(b=300)])))
        schleife = {"typ": "polygon", "punkte": [[0, 0], [10, 10], [10, 0], [0, 10]]}
        self.assertTrue(any("überschneidet" in f for f in eigenteil_pruefen(Eigenteil(id="E", formen=[schleife]))))
        zwei = {"typ": "polygon", "punkte": [[0, 0], [10, 0]]}
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", formen=[zwei])))
        nan = {"typ": "kreis", "x": 0, "y": 0, "r": float("nan")}
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", formen=[nan])))

    def test_projekt_roundtrip_und_altdatei(self):
        p = Projekt(eigene=[Eigenteil(id="E1", formen=[_rechteck()])])
        p2 = Projekt.from_dict(p.to_dict())
        self.assertEqual(p2.eigene[0].formen[0]["b"], 40.0)
        d = p.to_dict()
        del d["eigene"]
        self.assertEqual(Projekt.from_dict(d).eigene, [])


class Auftrag(unittest.TestCase):
    def test_eigenteil_im_auftrag(self):
        p = Projekt(schublade=Schublade(innenbreite_mm=300, innentiefe_mm=200), eigene=[Eigenteil(id="E1", name="Halter", anzahl=2, formen=[_rechteck()])])
        a = auftrag_bauen(p)
        self.assertTrue(a["ok"], a["fehler"])
        eigen = [t for t in a["teile"] if t["id"] == "E1"]
        self.assertEqual(len(eigen), 1)
        self.assertEqual(eigen[0]["anzahl"], 2)

    def test_ungueltiges_eigenteil_blockiert_export(self):
        p = Projekt(eigene=[Eigenteil(id="E1", formen=[])])
        self.assertFalse(layout_pruefen(p)["ok"])

    def test_randstreifen_werden_zu_fuellplatten(self):
        for breite in (500, 537, 613):
            p = Projekt(schublade=Schublade(innenbreite_mm=breite, innentiefe_mm=300))
            a = auftrag_bauen(p)
            self.assertTrue(a["ok"], a["fehler"])
            streifen = [t for t in a["teile"] if t["rolle"] == "eigen"]
            for teil in streifen:
                self.assertTrue(teil["passt_in_bauraum"])
                self.assertGreater(teil["soll_mm"][0], 0)
            self.assertEqual(len(a["ansicht"]["randstreifen"]), len(streifen))


class Kanten(unittest.TestCase):
    def test_gueltige_kanten(self):
        teil = Eigenteil(id="E", hoehe_mm=10, kante_oben_art="rund", kante_oben_mm=1.5, kante_unten_mm=0.6, formen=[dict(_rechteck(40, 30), radius=5)])
        self.assertEqual(eigenteil_pruefen(teil), [])
        params = auftrag_bauen(Projekt(nur_eigene=True, eigene=[teil]))["teile"][0]["params"]
        self.assertEqual((params["KanteObenArt"], params["KanteObenMm"], params["KanteUntenMm"]), (2, 1.5, 0.6))

    def test_ungueltige_kanten(self):
        def pruefe(**kw):
            formen = kw.pop("formen", [_rechteck(40, 30)])
            return eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=10, formen=formen, **kw))

        self.assertTrue(pruefe(kante_oben_art="rund", kante_oben_mm=6))  # mehr als halbe Höhe
        self.assertTrue(pruefe(kante_oben_art="rund", kante_oben_mm=3, kante_unten_mm=3))  # zusammen > halbe Höhe
        self.assertTrue(pruefe(kante_oben_art="keine", kante_oben_mm=1))
        self.assertTrue(pruefe(kante_oben_art="schief", kante_oben_mm=0))
        self.assertTrue(pruefe(kante_unten_mm=-1))
        self.assertTrue(pruefe(formen=[dict(_rechteck(40, 30), radius=16)]))  # größer als halbe kurze Seite
        self.assertTrue(pruefe(formen=[dict(_rechteck(40, 30), radius=-1)]))
        self.assertEqual(pruefe(formen=[dict(_rechteck(40, 30), radius=15)]), [])

    def test_altdatei_ohne_kantenfelder(self):
        d = Projekt(eigene=[Eigenteil(id="E1", formen=[_rechteck()])]).to_dict()
        for k in ("kante_oben_art", "kante_oben_mm", "kante_unten_mm"):
            del d["eigene"][0][k]
        e = Projekt.from_dict(d).eigene[0]
        self.assertEqual((e.kante_oben_art, e.kante_oben_mm, e.kante_unten_mm), ("keine", 0.0, 0.0))


class Platzierung(unittest.TestCase):
    def _projekt(self, **eigen):
        teil = Eigenteil(id="E1", name="Halter", hoehe_mm=12, formen=[_rechteck(40, 30)], platziert=True, **eigen)
        return Projekt(schublade=Schublade(innenbreite_mm=300, innentiefe_mm=200, nutzhoehe_mm=60), eigene=[teil])

    def test_gueltige_lage(self):
        p = self._projekt(x_mm=100, y_mm=50)
        self.assertTrue(layout_pruefen(p)["ok"], layout_pruefen(p)["fehler"])
        a = auftrag_bauen(p)
        lage = next(t for t in a["teile"] if t["id"] == "E1")["lage"]
        self.assertEqual((lage["links_mm"], lage["vorne_mm"]), (100.0, 50.0))
        self.assertEqual([e["id"] for e in a["ansicht"]["eigene_mm"]], ["E1"])

    def test_drehung_tauscht_masse(self):
        p = self._projekt(x_mm=10, y_mm=10, drehung=90)
        r = [e for e in auftrag_bauen(p)["ansicht"]["eigene_mm"]][0]
        self.assertEqual((r["breite_mm"], r["tiefe_mm"]), (30.0, 40.0))

    def test_ausserhalb_und_zu_hoch(self):
        self.assertFalse(layout_pruefen(self._projekt(x_mm=290, y_mm=50))["ok"])
        self.assertFalse(layout_pruefen(self._projekt(x_mm=-5, y_mm=50))["ok"])
        p = self._projekt(x_mm=100, y_mm=50)
        p.eigene[0].hoehe_mm = 80
        self.assertFalse(layout_pruefen(p)["ok"])

    def test_kollision_mit_box_und_teil(self):
        p = self._projekt(x_mm=100, y_mm=50)
        p.boxen.append(Box(id="B1", name="Box", x=2, y=1, ex=1, ey=1, ez=3))
        self.assertTrue(any("überlappt die Box" in f for f in layout_pruefen(p)["fehler"]))
        q = self._projekt(x_mm=100, y_mm=50)
        q.eigene.append(Eigenteil(id="E2", name="Zweit", formen=[_rechteck(20, 20)], platziert=True, x_mm=110, y_mm=60))
        self.assertTrue(any("überlappt" in f for f in layout_pruefen(q)["fehler"]))
        q.eigene[1].x_mm = 200
        self.assertTrue(layout_pruefen(q)["ok"], layout_pruefen(q)["fehler"])

    def test_autofill_laesst_teile_frei(self):
        p = self._projekt(x_mm=100, y_mm=50)
        r = auto_bestuecken(p)
        self.assertTrue(r["ok"] and r["neu"] > 0)
        pruefung = layout_pruefen(p)
        self.assertTrue(pruefung["ok"], pruefung["fehler"])
        # Ohne das Teil wären mehr Felder belegt
        leer = Projekt(schublade=p.schublade)
        auto_bestuecken(leer)
        self.assertGreater(sum(footprint(b)[2] * footprint(b)[3] for b in leer.boxen), sum(footprint(b)[2] * footprint(b)[3] for b in p.boxen))

    def test_nicht_platziert_wird_ignoriert(self):
        p = self._projekt(x_mm=9999, y_mm=9999)
        p.eigene[0].platziert = False
        self.assertTrue(layout_pruefen(p)["ok"])
        self.assertEqual(auftrag_bauen(p)["ansicht"]["eigene_mm"], [])

    def test_altdatei_ohne_felder(self):
        d = Projekt(eigene=[Eigenteil(id="E1", formen=[_rechteck()])]).to_dict()
        for k in ("platziert", "x_mm", "y_mm", "drehung"):
            del d["eigene"][0][k]
        e = Projekt.from_dict(d).eigene[0]
        self.assertFalse(e.platziert)


class NurEigene(unittest.TestCase):
    def test_ohne_schublade(self):
        p = Projekt(nur_eigene=True, eigene=[Eigenteil(id="E1", formen=[_rechteck()])])
        a = auftrag_bauen(p)
        self.assertTrue(a["ok"], a["fehler"])
        self.assertEqual([t["id"] for t in a["teile"]], ["E1"])
        self.assertTrue(layout_pruefen(p)["ok"])
        self.assertTrue(Projekt.from_dict(p.to_dict()).nur_eigene)

    def test_leer_ist_fehler(self):
        self.assertFalse(layout_pruefen(Projekt(nur_eigene=True))["ok"])
        self.assertFalse(auftrag_bauen(Projekt(nur_eigene=True))["ok"])


class Autofill(unittest.TestCase):
    def test_fuellt_alles_ohne_ueberlappung(self):
        for breite, tiefe in ((480, 420), (213, 377), (95, 95), (700, 150)):
            p = Projekt(schublade=Schublade(innenbreite_mm=breite, innentiefe_mm=tiefe, nutzhoehe_mm=80))
            r = auto_bestuecken(p)
            self.assertTrue(r["ok"], (breite, tiefe, r))
            pruefung = layout_pruefen(p)
            self.assertTrue(pruefung["ok"], (breite, tiefe, pruefung["fehler"]))
            for i, a in enumerate(p.boxen):
                for b in p.boxen[i + 1:]:
                    self.assertFalse(ueberlappung(a, b))
            self.assertGreater(sum(footprint(b)[2] * footprint(b)[3] for b in p.boxen), 0)

    def test_behaelt_vorhandene_boxen(self):
        p = Projekt(schublade=Schublade(innenbreite_mm=300, innentiefe_mm=300))
        auto_bestuecken(p)
        anzahl = len(p.boxen)
        r = auto_bestuecken(p)
        self.assertEqual(r["neu"], 0)
        self.assertEqual(len(p.boxen), anzahl)

    def test_zu_niedrige_schublade(self):
        p = Projekt(schublade=Schublade(nutzhoehe_mm=3))
        self.assertFalse(auto_bestuecken(p)["ok"])


@unittest.skipUnless(os.environ.get("FREECADCMD") and Path(os.environ["FREECADCMD"]).exists(), "FREECADCMD nicht gesetzt")
class MitFreeCAD(unittest.TestCase):
    def test_eigenteil_und_streifen_export(self):
        from sidecar.engine import generiere

        loch = {"typ": "kreis", "x": 20, "y": 15, "r": 4, "loch": True}
        dreieck = {"typ": "polygon", "punkte": [[40, 0], [60, 0], [40, 30]], "loch": False}
        p = Projekt(
            schublade=Schublade(innenbreite_mm=513, innentiefe_mm=300),
            eigene=[Eigenteil(id="E1", name="Halter", hoehe_mm=12, boden_mm=2, formen=[_rechteck(), dreieck, loch])],
        )
        with tempfile.TemporaryDirectory() as tmp:
            r = generiere(p, Path(tmp), freecad_pfad=os.environ["FREECADCMD"])
            self.assertTrue(r["ok"], r["fehler"])
            ids = {d["id"] for t in r["teile"] for d in t["dateien"]}
            self.assertIn("E1", ids)
            e1 = next(d for t in r["teile"] for d in t["dateien"] if d["id"] == "E1")
            bb = e1["solid"]["bbox_mm"]
            self.assertAlmostEqual(bb[0], 60.0, delta=0.1)
            self.assertAlmostEqual(bb[2], 12.0, delta=0.1)
            voll = 40 * 30 * 12 + 0.5 * 20 * 30 * 12
            # Sackloch ab 2 mm: Volumen kleiner als der Vollkörper, aber nicht durchgebohrt
            self.assertLess(e1["solid"]["volume_mm3"], voll)
            self.assertGreater(e1["solid"]["volume_mm3"], voll - 3.1416 * 16 * 12)

    def test_nur_eigene_export(self):
        from sidecar.engine import generiere

        p = Projekt(nur_eigene=True, eigene=[Eigenteil(id="E1", name="Klotz", hoehe_mm=8, formen=[_rechteck(30, 20)])])
        with tempfile.TemporaryDirectory() as tmp:
            r = generiere(p, Path(tmp), freecad_pfad=os.environ["FREECADCMD"])
            self.assertTrue(r["ok"], r["fehler"])
            self.assertTrue((Path(tmp) / "E1.stl").is_file())
            self.assertTrue((Path(tmp) / "Stueckliste.csv").is_file())

    def test_kanten_und_radius_export(self):
        from sidecar.engine import generiere

        loch = {"typ": "kreis", "x": 20, "y": 15, "r": 4, "loch": True}
        eckig = Eigenteil(id="E1", name="Eckig", hoehe_mm=12, formen=[_rechteck(40, 30), loch])
        weich = Eigenteil(
            id="E2", name="Weich", hoehe_mm=12, kante_oben_art="rund", kante_oben_mm=1.5, kante_unten_mm=0.6,
            formen=[dict(_rechteck(40, 30), radius=6), loch],
        )
        fase = Eigenteil(id="E3", name="Fase", hoehe_mm=12, kante_oben_art="fase", kante_oben_mm=1.0, formen=[_rechteck(40, 30)])
        p = Projekt(nur_eigene=True, eigene=[eckig, weich, fase])
        with tempfile.TemporaryDirectory() as tmp:
            r = generiere(p, Path(tmp), freecad_pfad=os.environ["FREECADCMD"])
            self.assertTrue(r["ok"], r["fehler"])
            teile = {d["id"]: d["solid"] for t in r["teile"] for d in t["dateien"]}
            for solid in teile.values():
                self.assertAlmostEqual(solid["bbox_mm"][0], 40.0, delta=0.1)
                self.assertAlmostEqual(solid["bbox_mm"][2], 12.0, delta=0.1)
            self.assertLess(teile["E2"]["volume_mm3"], teile["E1"]["volume_mm3"] - 20)  # Ecken, Kanten abgetragen
            self.assertLess(teile["E3"]["volume_mm3"], 40 * 30 * 12 - 20)  # Fase trägt Material ab

    def test_zu_grosse_kante_wird_gemeldet(self):
        from sidecar.engine import generiere

        # 5 mm Rundung an einem nur 12 mm hohen Teil: Prüfung erlaubt 6 mm, Geometrie bleibt aber gültig
        teil = Eigenteil(id="E1", hoehe_mm=12, kante_oben_art="rund", kante_oben_mm=6, formen=[_rechteck(40, 30)])
        p = Projekt(nur_eigene=True, eigene=[teil])
        with tempfile.TemporaryDirectory() as tmp:
            r = generiere(p, Path(tmp), freecad_pfad=os.environ["FREECADCMD"])
            self.assertIsInstance(r["ok"], bool)
            if not r["ok"]:
                self.assertTrue(any("Obere Kante" in f or "Kante" in f for f in r["fehler"]), r["fehler"])


if __name__ == "__main__":
    unittest.main()
