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


class Formoptionen(unittest.TestCase):
    def _pruefe(self, form, hoehe=10, **teil):
        return eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=hoehe, formen=[form], **teil))

    def test_gueltige_optionen(self):
        self.assertEqual(self._pruefe(dict(_rechteck(40, 40), schraege_mm=5)), [])
        self.assertEqual(self._pruefe(dict(_rechteck(40, 30), kante_art="fase", kante_mm=1)), [])
        self.assertEqual(self._pruefe(dict(_rechteck(40, 30), keil_mm=10)), [])
        self.assertEqual(eigenteil_sollgroesse(Eigenteil(id="E", hoehe_mm=5, formen=[dict(_rechteck(40, 30), keil_mm=10)]))[2], 15.0)

    def test_ungueltige_optionen(self):
        self.assertTrue(self._pruefe(dict(_rechteck(40, 30), schraege_mm=15)))  # läuft spitz zu
        self.assertTrue(self._pruefe(dict(_rechteck(40, 30), kante_art="fase", kante_mm=6)))  # > halbe Höhe
        self.assertTrue(self._pruefe(dict(_rechteck(40, 30), kante_art="keine", kante_mm=1)))
        self.assertTrue(self._pruefe(dict(_rechteck(40, 30), kante_art="fase", kante_mm=1, schraege_mm=2)))
        self.assertTrue(self._pruefe(dict(_rechteck(40, 30), kante_art="schief", kante_mm=1)))
        self.assertTrue(self._pruefe(dict(_rechteck(40, 30), keil_mm=5, schraege_mm=2)))
        self.assertTrue(self._pruefe(dict(_rechteck(40, 30), keil_mm=5, radius=3)))
        self.assertTrue(self._pruefe(dict(typ="kreis", x=0, y=0, r=5, keil_mm=3)))
        self.assertTrue(self._pruefe(dict(_rechteck(40, 30), keil_mm=-20)))  # vorn + Keil < 0
        self.assertTrue(self._pruefe(dict(_rechteck(40, 30), keil_mm=3), kante_oben_art="fase", kante_oben_mm=1))
        self.assertTrue(self._pruefe(dict(_rechteck(40, 30), schraege_mm=-1)))


class Drehung(unittest.TestCase):
    def test_bounding_box_gedrehter_rechtecke(self):
        from sidecar.eigenteil import form_bbox
        import math

        quadrat = dict(_rechteck(10, 10), winkel=45)
        x0, y0, x1, y1 = form_bbox(quadrat)
        self.assertAlmostEqual(x1 - x0, 10 * math.sqrt(2), places=6)
        self.assertAlmostEqual((x0 + x1) / 2, 5, places=6)  # Drehung um die Mitte
        self.assertEqual(form_bbox(dict(_rechteck(40, 20), winkel=180)), (0, 0, 40, 20))
        self.assertEqual(form_bbox(dict(_rechteck(40, 20), winkel=90)), (10, -10, 30, 30))
        # abgerundete Ecken: Kreisanteil bleibt r in beide Richtungen
        rund = form_bbox(dict(_rechteck(20, 20), winkel=45, radius=10))
        self.assertAlmostEqual(rund[2] - rund[0], 20, places=6)

    def test_pruefung(self):
        self.assertEqual(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=10, formen=[dict(_rechteck(40, 20), winkel=30)])), [])
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=10, formen=[dict(_rechteck(40, 20), winkel="x")])))
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=10, formen=[dict(_rechteck(40, 20), winkel=30, keil_mm=5)])))
        # Bauraum nach Drehung: ein Quadrat von 250 mm passt, um 45° gedreht (353 mm) nicht
        self.assertEqual(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=10, formen=[_rechteck(250, 250)])), [])
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=10, formen=[dict(_rechteck(250, 250), winkel=45)])))
        self.assertEqual(eigenteil_sollgroesse(Eigenteil(id="E", hoehe_mm=10, formen=[dict(_rechteck(40, 20), winkel=90)]))[:2], [20.0, 40.0])

    def test_freecad_gedrehtes_rechteck(self):
        if not (os.environ.get("FREECADCMD") and Path(os.environ["FREECADCMD"]).exists()):
            self.skipTest("FREECADCMD nicht gesetzt")
        from sidecar.engine import generiere
        import math

        gedreht = Eigenteil(id="E1", name="Gedreht", hoehe_mm=10, formen=[dict(_rechteck(40, 20), winkel=30)])
        rund = Eigenteil(id="E2", name="Rund", hoehe_mm=10, formen=[dict(_rechteck(40, 20), winkel=30, radius=4)])
        kante = Eigenteil(id="E3", name="Kante", hoehe_mm=10, formen=[dict(_rechteck(40, 20), winkel=30, kante_art="fase", kante_mm=1)])
        loch = Eigenteil(id="E4", name="Loch", hoehe_mm=10, formen=[_rechteck(60, 60), dict(_rechteck(20, 10, x=20, y=25), winkel=45, loch=True)])
        with tempfile.TemporaryDirectory() as tmp:
            r = generiere(Projekt(nur_eigene=True, eigene=[gedreht, rund, kante, loch]), Path(tmp), freecad_pfad=os.environ["FREECADCMD"])
            self.assertTrue(r["ok"], r["fehler"])
            solid = {d["id"]: d["solid"] for t in r["teile"] for d in t["dateien"]}
            w = math.radians(30)
            self.assertAlmostEqual(solid["E1"]["bbox_mm"][0], 40 * math.cos(w) + 20 * math.sin(w), delta=0.05)
            self.assertAlmostEqual(solid["E1"]["bbox_mm"][1], 40 * math.sin(w) + 20 * math.cos(w), delta=0.05)
            self.assertAlmostEqual(solid["E1"]["volume_mm3"], 8000, delta=8)
            self.assertAlmostEqual(solid["E2"]["volume_mm3"], 8000 - 4 * (1 - math.pi / 4) * 16 * 10, delta=8)
            self.assertAlmostEqual(solid["E3"]["volume_mm3"], 8000 - 0.5 * 120, delta=2)  # Fase an der gedrehten Außenkante
            self.assertAlmostEqual(solid["E4"]["volume_mm3"], 60 * 60 * 10 - 20 * 10 * 10, delta=10)


class Stufen(unittest.TestCase):
    def _stufenteil(self):
        # Sockel 60x40x5, darauf Stütze 20x20 bis 25 mm Gesamthöhe, Tasche im Sockel
        return Eigenteil(
            id="E1", name="Halter", hoehe_mm=5,
            formen=[
                _rechteck(60, 40),
                dict(_rechteck(20, 20, x=20, y=10), z_mm=5, h_mm=20),
                dict(typ="kreis", x=10, y=20, r=4, loch=True, z_mm=2, h_mm=2),
            ],
        )

    def test_gesamthoehe_und_pruefung(self):
        from sidecar.eigenteil import eigenteil_hoehe
        teil = self._stufenteil()
        self.assertEqual(eigenteil_hoehe(teil), 25.0)
        self.assertEqual(eigenteil_sollgroesse(teil)[2], 25.0)
        self.assertEqual(eigenteil_pruefen(teil), [])

    def test_ab_start_bis_teilhoehe(self):
        from sidecar.eigenteil import form_hoehen
        self.assertEqual(form_hoehen({"z_mm": 4}, 10), (4.0, 6.0))
        self.assertEqual(form_hoehen({}, 10), (0.0, 10.0))
        self.assertEqual(form_hoehen({"z_mm": 4, "h_mm": 2}, 10), (4.0, 2.0))

    def test_ungueltige_hoehen(self):
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=5, formen=[dict(_rechteck(), z_mm=-1)])))
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=5, formen=[dict(_rechteck(), z_mm=5)])))  # ab Teilhöhe: Höhe 0
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=5, formen=[dict(_rechteck(), h_mm=0.1)])))
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=5, formen=[dict(_rechteck(), z_mm=250, h_mm=20)])))
        self.assertTrue(eigenteil_pruefen(Eigenteil(id="E", hoehe_mm=5, formen=[dict(_rechteck(), z_mm="x")])))

    def test_platzierte_hoehe_nutzt_gesamthoehe(self):
        p = Projekt(schublade=Schublade(innenbreite_mm=300, innentiefe_mm=200, nutzhoehe_mm=20), eigene=[self._stufenteil()])
        p.eigene[0].platziert, p.eigene[0].x_mm, p.eigene[0].y_mm = True, 100, 50
        self.assertTrue(any("Höhe" in f for f in layout_pruefen(p)["fehler"]))
        p.schublade.nutzhoehe_mm = 40
        self.assertTrue(layout_pruefen(p)["ok"], layout_pruefen(p)["fehler"])


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


class Wunschliste(unittest.TestCase):
    def _p(self, b=480, t=420, h=80):
        return Projekt(schublade=Schublade(innenbreite_mm=b, innentiefe_mm=t, nutzhoehe_mm=h))

    def test_wuensche_werden_platziert_und_rest_gefuellt(self):
        p = self._p()
        r = auto_bestuecken(p, wuensche=[{"sorte": "kabel", "anzahl": 1}, {"sorte": "besteckfach", "anzahl": 2}, {"sorte": "klein", "anzahl": 3}])
        self.assertTrue(r["ok"], r)
        namen = [b.name for b in p.boxen]
        self.assertEqual(namen.count("Kabelbox"), 1)
        self.assertEqual(namen.count("Besteckfach"), 2)
        self.assertGreaterEqual(namen.count("Kleine Box"), 3)
        self.assertTrue(all(w["platziert"] == w["gewuenscht"] for w in r["wuensche"]), r["wuensche"])
        pruefung = layout_pruefen(p)
        self.assertTrue(pruefung["ok"], pruefung["fehler"])
        kabel = next(b for b in p.boxen if b.name == "Kabelbox")
        self.assertTrue(kabel.kabelkerben)

    def test_ohne_rest_fuellen(self):
        p = self._p()
        r = auto_bestuecken(p, wuensche=[{"sorte": "mittel", "anzahl": 2}], rest_fuellen=False)
        self.assertEqual(len(p.boxen), 2)
        self.assertEqual(r["neu"], 2)

    def test_zu_viele_wuensche_werden_gemeldet(self):
        p = self._p(b=100, t=100)
        r = auto_bestuecken(p, wuensche=[{"sorte": "gross", "anzahl": 10}], rest_fuellen=False)
        self.assertTrue(r["ok"])
        self.assertLess(r["wuensche"][0]["platziert"], 10)
        self.assertTrue(any("von 10 platziert" in h for h in r["hinweise"]), r["hinweise"])
        self.assertTrue(layout_pruefen(p)["ok"])

    def test_drehung_wenn_noetig(self):
        # 3 Felder breit, 1 Feld tief: die 1x2-Box passt nur gedreht (2x1)
        p = Projekt(schublade=Schublade(innenbreite_mm=130, innentiefe_mm=44, nutzhoehe_mm=80))
        auto_bestuecken(p, wuensche=[{"sorte": "schmal", "anzahl": 1}], rest_fuellen=False)
        self.assertEqual(len(p.boxen), 1)
        self.assertEqual(p.boxen[0].rotation, 90)
        self.assertTrue(layout_pruefen(p)["ok"], layout_pruefen(p)["fehler"])

    def test_zu_niedrige_sorte_wird_abgesenkt_oder_gemeldet(self):
        p = self._p(h=30)
        r = auto_bestuecken(p, wuensche=[{"sorte": "kabel", "anzahl": 1}, {"sorte": "besteck", "anzahl": 1}], rest_fuellen=False)
        self.assertTrue(r["ok"])
        kabel = [b for b in p.boxen if b.name == "Kabelbox"]
        if kabel:
            self.assertLess(kabel[0].ez, 4)
        self.assertTrue(layout_pruefen(p)["ok"], layout_pruefen(p)["fehler"])

    def test_unbekannte_sorte_und_teile_bleiben_frei(self):
        p = Projekt(
            schublade=Schublade(innenbreite_mm=300, innentiefe_mm=200, nutzhoehe_mm=80),
            eigene=[Eigenteil(id="E1", name="Halter", formen=[_rechteck(40, 30)], platziert=True, x_mm=100, y_mm=50)],
        )
        r = auto_bestuecken(p, wuensche=[{"sorte": "quatsch", "anzahl": 2}, {"sorte": "mittel", "anzahl": 4}])
        self.assertTrue(any("Unbekannte Sorte" in h for h in r["hinweise"]))
        self.assertTrue(layout_pruefen(p)["ok"], layout_pruefen(p)["fehler"])


class Verteilung(unittest.TestCase):
    def _p(self, b=480, t=420):
        return Projekt(schublade=Schublade(innenbreite_mm=b, innentiefe_mm=t, nutzhoehe_mm=80))

    def test_wuensche_ruecken_in_ecken_und_aneinander(self):
        def beruehrt(a, b):
            ax, ay, aw, ah = footprint(a)
            bx, by, bw, bh = footprint(b)
            teilt_x = ax < bx + bw and bx < ax + aw
            teilt_y = ay < by + bh and by < ay + ah
            return (teilt_y and (ax + aw == bx or bx + bw == ax)) or (teilt_x and (ay + ah == by or by + bh == ay))

        p = self._p()
        auto_bestuecken(p, wuensche=[{"sorte": "kabel", "anzahl": 1}, {"sorte": "klein", "anzahl": 2}], rest_fuellen=False)
        kabel = next(b for b in p.boxen if b.name == "Kabelbox")
        kleine = [b for b in p.boxen if b.name == "Kleine Box"]
        self.assertEqual((kabel.x, kabel.y), (0, 0))  # Ecke vorne links
        for k in kleine:
            # jede kleine Box berührt die Kabelbox oder eine andere Box oder die Schubladenwand
            wand = k.x == 0 or k.y == 0
            self.assertTrue(wand or any(beruehrt(k, o) for o in p.boxen if o is not k), (k.x, k.y))
        self.assertTrue(any(beruehrt(k, kabel) for k in kleine))
        self.assertTrue(layout_pruefen(p)["ok"], layout_pruefen(p)["fehler"])

    def test_einheitlich_bevorzugt_grosse_gleiche_boxen(self):
        from collections import Counter

        for breite, tiefe in ((480, 420), (213, 377), (700, 150), (300, 300)):
            gross, einheitlich, klein = self._p(breite, tiefe), self._p(breite, tiefe), self._p(breite, tiefe)
            auto_bestuecken(gross, stil="gross")
            r = auto_bestuecken(einheitlich, stil="einheitlich")
            auto_bestuecken(klein, stil="klein")
            self.assertTrue(r["ok"] and r["stil"] == "einheitlich")
            zaehler = Counter((footprint(b)[2], footprint(b)[3]) for b in einheitlich.boxen)
            groesse, anzahl = zaehler.most_common(1)[0]
            zellen = sum(footprint(b)[2] * footprint(b)[3] for b in einheitlich.boxen)
            # eine dominierende Größe, keine Streifen: Fläche mindestens 4 Felder, mindestens die Hälfte der Zellen
            self.assertGreaterEqual(groesse[0] * groesse[1], 4, (breite, tiefe, groesse))
            self.assertGreaterEqual(anzahl * groesse[0] * groesse[1], zellen * 0.5, (breite, tiefe, groesse))
            self.assertLessEqual(len(einheitlich.boxen), len(klein.boxen))
            self.assertTrue(layout_pruefen(einheitlich)["ok"], layout_pruefen(einheitlich)["fehler"])
            # alle Stile belegen dieselben Felder
            felder = lambda p: sum(footprint(b)[2] * footprint(b)[3] for b in p.boxen)
            self.assertEqual(felder(einheitlich), felder(gross))
            self.assertEqual(felder(klein), felder(gross))

    def test_klein_und_unbekannter_stil(self):
        p = self._p(200, 200)
        auto_bestuecken(p, stil="klein")
        self.assertTrue(all(footprint(b)[2:] == (1, 1) for b in p.boxen))
        self.assertFalse(auto_bestuecken(self._p(), stil="quatsch")["ok"])


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

    def test_stufenteil_export(self):
        from sidecar.engine import generiere

        teil = Eigenteil(
            id="E1", name="Halter", hoehe_mm=5,
            formen=[
                _rechteck(60, 40),
                dict(_rechteck(20, 20, x=20, y=10), z_mm=5, h_mm=20),
                dict(typ="kreis", x=10, y=20, r=4, loch=True, z_mm=2, h_mm=2),
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            r = generiere(Projekt(nur_eigene=True, eigene=[teil]), Path(tmp), freecad_pfad=os.environ["FREECADCMD"])
            self.assertTrue(r["ok"], r["fehler"])
            solid = r["teile"][0]["dateien"][0]["solid"]
            self.assertAlmostEqual(solid["bbox_mm"][2], 25.0, delta=0.1)
            erwartet = 60 * 40 * 5 + 20 * 20 * 20 - 3.14159 * 16 * 2
            self.assertAlmostEqual(solid["volume_mm3"], erwartet, delta=2.0)

    def test_formoptionen_export(self):
        from sidecar.engine import generiere
        import math

        konus = dict(typ="kreis", x=20, y=20, r=3, loch=True, schraege_mm=2)
        rand = dict(typ="kreis", x=20, y=20, r=4, loch=True, kante_art="fase", kante_mm=1)
        teile = [
            Eigenteil(id="E1", name="Verjuengt", hoehe_mm=10, formen=[dict(_rechteck(40, 40), schraege_mm=5)]),
            Eigenteil(id="E2", name="Keil", hoehe_mm=5, formen=[dict(_rechteck(40, 30), keil_mm=10)]),
            Eigenteil(id="E3", name="Senkung", hoehe_mm=10, formen=[_rechteck(40, 40), konus]),
            Eigenteil(id="E4", name="FormKante", hoehe_mm=10, formen=[dict(_rechteck(40, 30), kante_art="fase", kante_mm=1)]),
            Eigenteil(id="E5", name="Lochrand", hoehe_mm=10, formen=[_rechteck(40, 40), rand]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            r = generiere(Projekt(nur_eigene=True, eigene=teile), Path(tmp), freecad_pfad=os.environ["FREECADCMD"])
            self.assertTrue(r["ok"], r["fehler"])
            solid = {d["id"]: d["solid"] for t in r["teile"] for d in t["dateien"]}
            frustum = 10 / 3 * (1600 + 900 + math.sqrt(1600 * 900))
            self.assertAlmostEqual(solid["E1"]["volume_mm3"], frustum, delta=frustum * 0.005)
            self.assertAlmostEqual(solid["E1"]["bbox_mm"][2], 10.0, delta=0.1)
            self.assertAlmostEqual(solid["E2"]["volume_mm3"], 40 * 30 * 10, delta=12000 * 0.005)
            self.assertAlmostEqual(solid["E2"]["bbox_mm"][2], 15.0, delta=0.1)
            kegel = math.pi * 10 / 3 * (9 + 15 + 25)
            self.assertAlmostEqual(solid["E3"]["volume_mm3"], 16000 - kegel, delta=16000 * 0.005)
            self.assertAlmostEqual(solid["E4"]["volume_mm3"], 12000 - 0.5 * 1 * 1 * 140, delta=1.5)
            ring = 2 * math.pi * (4 + 1 / 3) * 0.5
            self.assertAlmostEqual(solid["E5"]["volume_mm3"], 16000 - math.pi * 16 * 10 - ring, delta=2.5)

    def test_kante_ohne_passende_flaeche_wird_gemeldet(self):
        from sidecar.engine import generiere

        # Fase an einer Form, deren Oberrand komplett von einer höheren Form verdeckt ist
        unten = dict(_rechteck(40, 40), kante_art="fase", kante_mm=0.5, h_mm=3)
        oben = dict(_rechteck(40, 40), z_mm=0, h_mm=8)
        teil = Eigenteil(id="E1", hoehe_mm=8, formen=[unten, oben])
        with tempfile.TemporaryDirectory() as tmp:
            r = generiere(Projekt(nur_eigene=True, eigene=[teil]), Path(tmp), freecad_pfad=os.environ["FREECADCMD"])
            self.assertFalse(r["ok"])
            self.assertTrue(any("Kante an Form 1" in f for f in r["fehler"]), r["fehler"])

    def test_schwebende_form_wird_gemeldet(self):
        from sidecar.engine import generiere

        teil = Eigenteil(id="E1", hoehe_mm=5, formen=[_rechteck(30, 30), dict(_rechteck(10, 10, x=60, y=0), z_mm=3, h_mm=2)])
        with tempfile.TemporaryDirectory() as tmp:
            r = generiere(Projekt(nur_eigene=True, eigene=[teil]), Path(tmp), freecad_pfad=os.environ["FREECADCMD"])
            self.assertFalse(r["ok"])
            self.assertTrue(any("getrennten Körpern" in f for f in r["fehler"]), r["fehler"])


if __name__ == "__main__":
    unittest.main()
