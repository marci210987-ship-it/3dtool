# -*- coding: utf-8 -*-
"""Eigene Teile: Text, Senkungen, Seitenlöcher, Drehprofil, Vieleck-Rundung und Druckhinweise."""

from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.eigenteil import Eigenteil, eigenteil_pruefen, eigenteil_sollgroesse  # noqa: E402
from sidecar.layout import Projekt  # noqa: E402
from sidecar.pixelschrift import text_groesse, text_rechtecke, unbekannte_zeichen  # noqa: E402


def _rechteck(b=40.0, t=30.0, loch=False, x=0.0, y=0.0, **extra):
    return {"typ": "rechteck", "x": x, "y": y, "b": b, "t": t, "loch": loch, **extra}


def _kreis(x, y, r, loch=True, **extra):
    return {"typ": "kreis", "x": x, "y": y, "r": r, "loch": loch, **extra}


def _teil(formen, **kw):
    return Eigenteil(id="E1", name="Test", hoehe_mm=kw.pop("hoehe_mm", 12), formen=formen, **kw)


def _fehler(teil):
    return " | ".join(eigenteil_pruefen(teil))


class Pixelschrift(unittest.TestCase):
    def test_groesse_und_zeichen(self):
        self.assertEqual(text_groesse("AB", 7), (11.0, 7.0))
        self.assertEqual(unbekannte_zeichen("ä#"), ["#"])  # Ä wird zu AE, # fehlt
        self.assertEqual(unbekannte_zeichen("Größe 5"), [])

    def test_rechtecke_liegen_im_rahmen(self):
        rects = text_rechtecke("HALLO 12", 10, 20, 7)
        self.assertTrue(rects)
        b, t = text_groesse("HALLO 12", 7)
        for x, y, w, h in rects:
            self.assertGreaterEqual(x, 10 - 1e-6)
            self.assertLessEqual(x + w, 10 + b + 1e-6)
            self.assertGreaterEqual(y, 20 - 1e-6)
            self.assertLessEqual(y + h, 20 + t + 1e-6)


class Pruefung(unittest.TestCase):
    def test_text(self):
        gut = {"typ": "text", "x": 2, "y": 2, "text": "M3", "schrift_mm": 5, "loch": False, "z_mm": 12, "h_mm": 0.6}
        self.assertEqual(eigenteil_pruefen(_teil([_rechteck(), gut])), [])
        self.assertIn("leer", _fehler(_teil([_rechteck(), dict(gut, text=" ")])))
        self.assertIn("zu klein", _fehler(_teil([_rechteck(), dict(gut, schrift_mm=2)])))
        self.assertIn("nicht", _fehler(_teil([_rechteck(), dict(gut, text="a#")])))
        self.assertIn("zu lang", _fehler(_teil([_rechteck(), dict(gut, text="A" * 41)])))

    def test_senkung(self):
        loch = _kreis(20, 15, 2, senk_art="senkung", senk_d_mm=6, senk_seite="oben")
        self.assertEqual(eigenteil_pruefen(_teil([_rechteck(), loch])), [])
        self.assertIn("größer", _fehler(_teil([_rechteck(), dict(loch, senk_d_mm=4)])))
        self.assertIn("Tiefe", _fehler(_teil([_rechteck(), dict(loch, senk_art="gegenbohrung", senk_t_mm=0)])))
        self.assertIn("nur an Löchern", _fehler(_teil([_rechteck(), _kreis(20, 15, 2, loch=False, senk_art="senkung", senk_d_mm=6)])))
        self.assertIn("Unbekannte", _fehler(_teil([_rechteck(), dict(loch, senk_art="x")])))
        self.assertIn("kein Material", _fehler(_teil([_rechteck(), dict(loch, senk_art="gegenbohrung", senk_t_mm=12)])))

    def test_polygon_radius(self):
        dreieck = {"typ": "polygon", "punkte": [[0, 0], [40, 0], [0, 30]], "loch": False}
        self.assertEqual(eigenteil_pruefen(_teil([dict(dreieck, radius=4)])), [])
        self.assertIn("halbe kürzeste", _fehler(_teil([dict(dreieck, radius=20)])))
        self.assertIn("nicht mit Fase", _fehler(_teil([dict(dreieck, radius=2, kante_art="fase", kante_mm=1)])))

    def test_seitenloecher(self):
        ok = {"seite": "vorne", "art": "rund", "pos_mm": 20, "z_mm": 6, "d_mm": 4, "tiefe_mm": 0}
        self.assertEqual(eigenteil_pruefen(_teil([_rechteck()], seitenloecher=[ok])), [])
        self.assertIn("Position", _fehler(_teil([_rechteck()], seitenloecher=[dict(ok, pos_mm=39)])))
        self.assertIn("Teilhöhe", _fehler(_teil([_rechteck()], seitenloecher=[dict(ok, z_mm=11)])))
        self.assertIn("Seite", _fehler(_teil([_rechteck()], seitenloecher=[dict(ok, seite="oben")])))
        self.assertIn("Tiefe", _fehler(_teil([_rechteck()], seitenloecher=[dict(ok, tiefe_mm=99)])))

    def test_profil(self):
        profil = [[0, 0], [10, 0], [10, 5], [4, 20], [0, 20]]
        t = _teil([], profil=profil, dreh_x_mm=15, dreh_y_mm=15)
        self.assertEqual(eigenteil_pruefen(t), [])
        self.assertEqual(eigenteil_sollgroesse(t), [20.0, 20.0, 20.0])
        self.assertIn("überschneidet", _fehler(_teil([], profil=[[0, 0], [10, 10], [10, 0], [0, 10]], dreh_x_mm=15, dreh_y_mm=15)))
        self.assertIn("negativ", _fehler(_teil([], profil=[[0, 0], [-5, 0], [0, 5]], dreh_x_mm=15, dreh_y_mm=15)))
        self.assertIn("Nullpunkt", _fehler(_teil([], profil=profil, dreh_x_mm=5, dreh_y_mm=15)))
        self.assertIn("mindestens 3", _fehler(_teil([], profil=[[0, 0], [5, 5]], dreh_x_mm=15, dreh_y_mm=15)))

    def test_alte_projekte_ohne_felder(self):
        t = Eigenteil.from_dict({"id": "E1", "formen": [_rechteck()]})
        self.assertEqual((t.seitenloecher, t.profil), ([], []))
        self.assertEqual(Projekt.from_dict(Projekt(eigene=[t]).to_dict()).eigene[0].profil, [])


@unittest.skipUnless(os.environ.get("FREECADCMD"), "FREECADCMD fehlt")
class MitFreeCAD(unittest.TestCase):
    def _export(self, teil):
        from sidecar.engine import generiere

        with tempfile.TemporaryDirectory() as tmp:
            r = generiere(Projekt(nur_eigene=True, eigene=[teil]), Path(tmp), freecad_pfad=os.environ["FREECADCMD"])
            self.assertTrue(r["ok"], r["fehler"])
            datei = r["teile"][0]["dateien"][0]
            self.assertTrue(datei["ok"])
            return datei["solid"], r

    def _volumen(self, teil):
        return self._export(teil)[0]["volume_mm3"]

    def test_text_erhaben_und_vertieft(self):
        platte = _rechteck(60, 20)
        basis = self._volumen(_teil([platte]))
        px = 5 / 7
        rects = text_rechtecke("HI", 5, 5, 5)
        flaeche = sum(b * t for _x, _y, b, t in rects)
        erhaben = _teil([platte, {"typ": "text", "x": 5, "y": 5, "text": "HI", "schrift_mm": 5, "loch": False, "z_mm": 12, "h_mm": 0.6}])
        solid, _ = self._export(erhaben)
        self.assertAlmostEqual(solid["bbox_mm"][2], 12.6, delta=0.1)
        self.assertAlmostEqual(solid["volume_mm3"], basis + flaeche * 0.6, delta=1.0)
        vertieft = _teil([platte, {"typ": "text", "x": 5, "y": 5, "text": "HI", "schrift_mm": 5, "loch": True, "z_mm": 11.4, "h_mm": 1.6}])
        self.assertAlmostEqual(self._volumen(vertieft), basis - flaeche * 0.6, delta=1.0)

    def test_senkung_gegenbohrung_sechskant(self):
        platte = _rechteck(40, 30)
        d, hoehe = 4.0, 12.0
        basis = self._volumen(_teil([platte, _kreis(20, 15, 2)]))
        # 90°-Senkung oben: Kegelstumpf von Ø4 auf Ø8 über 2 mm Tiefe
        r1, r2, h = 2.0, 4.0, 2.0
        kegel = math.pi * h / 3 * (r1 * r1 + r1 * r2 + r2 * r2) - math.pi * r1 * r1 * h
        v = self._volumen(_teil([platte, _kreis(20, 15, 2, senk_art="senkung", senk_d_mm=8, senk_seite="oben")]))
        self.assertAlmostEqual(v, basis - kegel, delta=1.5)
        v = self._volumen(_teil([platte, _kreis(20, 15, 2, senk_art="senkung", senk_d_mm=8, senk_seite="unten")]))
        self.assertAlmostEqual(v, basis - kegel, delta=1.5)
        zyl = math.pi * (4.5 ** 2 - 2 ** 2) * 3
        v = self._volumen(_teil([platte, _kreis(20, 15, 2, senk_art="gegenbohrung", senk_d_mm=9, senk_t_mm=3)]))
        self.assertAlmostEqual(v, basis - zyl, delta=1.5)
        hexflaeche = 3 ** 0.5 / 2 * 8 ** 2 * 1.0  # Schlüsselweite 8 mm: Fläche = 0,866 · SW²
        v = self._volumen(_teil([platte, _kreis(20, 15, 2, senk_art="sechskant", senk_d_mm=8, senk_t_mm=3)]))
        self.assertAlmostEqual(v, basis - (hexflaeche - math.pi * 4) * 3, delta=1.5)

    def test_seitenloecher(self):
        platte = _rechteck(40, 30)
        basis = self._volumen(_teil([platte]))
        durch = {"seite": "vorne", "art": "rund", "pos_mm": 20, "z_mm": 6, "d_mm": 4, "tiefe_mm": 0}
        self.assertAlmostEqual(self._volumen(_teil([platte], seitenloecher=[durch])), basis - math.pi * 4 * 30, delta=1.0)
        sack = {"seite": "links", "art": "rund", "pos_mm": 15, "z_mm": 6, "d_mm": 4, "tiefe_mm": 10}
        self.assertAlmostEqual(self._volumen(_teil([platte], seitenloecher=[sack])), basis - math.pi * 4 * 10, delta=1.0)
        schlitz = {"seite": "hinten", "art": "schlitz", "pos_mm": 20, "z_mm": 6, "b_mm": 10, "h_mm": 3, "tiefe_mm": 5}
        self.assertAlmostEqual(self._volumen(_teil([platte], seitenloecher=[schlitz])), basis - 10 * 3 * 5, delta=1.0)

    def test_drehteil(self):
        profil = [[0, 0], [10, 0], [10, 5], [4, 20], [0, 20]]
        t = _teil([], profil=profil, dreh_x_mm=15, dreh_y_mm=15)
        solid, _ = self._export(t)
        # Zylinder r=10, h=5 plus Kegelstumpf r 10 -> 4 über 15 mm plus Zylinder r=4 ... Profil ist ein Vieleck, Volumen nach Guldin
        flaeche = 0.0
        schwerpunkt_r = 0.0
        pts = profil
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            kreuz = x1 * y2 - x2 * y1
            flaeche += kreuz / 2
            schwerpunkt_r += (x1 + x2) * kreuz
        schwerpunkt_r /= 6 * flaeche
        self.assertAlmostEqual(solid["volume_mm3"], 2 * math.pi * schwerpunkt_r * abs(flaeche), delta=2.0)
        self.assertAlmostEqual(solid["bbox_mm"][0], 20.0, delta=0.2)
        self.assertAlmostEqual(solid["bbox_mm"][2], 20.0, delta=0.1)
        # Drehteil mit Querbohrung und Loch durch die Mitte
        t2 = _teil([_kreis(15, 15, 2)], profil=profil, dreh_x_mm=15, dreh_y_mm=15,
                   seitenloecher=[{"seite": "vorne", "art": "rund", "pos_mm": 15, "z_mm": 2.5, "d_mm": 2, "tiefe_mm": 0}])
        self.assertLess(self._volumen(t2), solid["volume_mm3"])

    def test_senkung_an_niedrigem_drehteil_sitzt_an_der_echten_oberkante(self):
        # Profil nur 5 mm hoch, Standardhöhe 10 mm: die Gegenbohrung muss an der Oberkante bei 5 mm liegen
        profil = [[0, 0], [10, 0], [10, 5], [0, 5]]
        plain = _teil([_kreis(10, 10, 2)], hoehe_mm=10, profil=profil, dreh_x_mm=10, dreh_y_mm=10)
        mit = _teil([_kreis(10, 10, 2, senk_art="gegenbohrung", senk_d_mm=6, senk_t_mm=2, senk_seite="oben")], hoehe_mm=10, profil=profil, dreh_x_mm=10, dreh_y_mm=10)
        unterschied = self._volumen(plain) - self._volumen(mit)
        self.assertAlmostEqual(unterschied, math.pi * (9 - 4) * 2, delta=1.0)

    def test_gerundetes_vieleck(self):
        quadrat = {"typ": "polygon", "punkte": [[0, 0], [30, 0], [30, 30], [0, 30]], "loch": False}
        v = self._volumen(_teil([dict(quadrat, radius=5)], hoehe_mm=10))
        erwartet = (30 * 30 - (4 - math.pi) * 25) * 10
        self.assertAlmostEqual(v, erwartet, delta=1.0)
        dreieck = {"typ": "polygon", "punkte": [[0, 0], [40, 0], [0, 30]], "loch": False, "radius": 3}
        v2 = self._volumen(_teil([dreieck], hoehe_mm=10))
        self.assertLess(v2, 600 * 10)
        self.assertGreater(v2, 580 * 10 - 60)

    def test_druckhinweise(self):
        # Platte auf Stützen: freitragende Decke von 30 × 30 mm, dazu eine dünne Rippe (0,5 mm)
        decke = _teil([
            _rechteck(30, 30, z_mm=8, h_mm=2),
            _rechteck(4, 4, x=0, y=0, z_mm=0, h_mm=8),
            _rechteck(4, 4, x=26, y=26, z_mm=0, h_mm=8),
            _rechteck(0.5, 20, x=10, y=5, z_mm=0, h_mm=8),
        ], hoehe_mm=10)
        _solid, r = self._export(decke)
        text = " ".join(r["hinweise"])
        self.assertIn("Druckhinweis", text)
        self.assertIn("Decke", text)
        self.assertIn("Dünne Stelle", text)
        # Regression: Platte mit Loch und Senkung ist keine dünne Stelle (Orientierung der Innenkontur nach dem Versatz)
        _solid, r = self._export(_teil([_rechteck(40, 30), _kreis(20, 15, 3, senk_art="senkung", senk_d_mm=8, senk_seite="oben")]))
        self.assertFalse([h for h in r["hinweise"] if "Dünne" in h], r["hinweise"])
        # Ein einfacher Klotz erzeugt keinen Hinweis
        _solid, r = self._export(_teil([_rechteck(30, 20)]))
        self.assertFalse([h for h in r["hinweise"] if "Druckhinweis" in h])


def _ueberhang_mm2(netz) -> float:
    """Fläche der Dreiecke, die steiler als 45° nach unten zeigen und nicht auf dem Bett liegen (wie die Ausrichtung in der Oberfläche)."""
    p, t = netz["punkte"], netz["dreiecke"]
    summe = 0.0
    for i in range(0, len(t), 3):
        a, b, c = [(p[j * 3], p[j * 3 + 1], p[j * 3 + 2]) for j in t[i:i + 3]]
        u = [b[k] - a[k] for k in range(3)]
        v = [c[k] - a[k] for k in range(3)]
        n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        laenge = math.sqrt(sum(x * x for x in n))
        if laenge < 1e-9:
            continue
        if n[2] / laenge < -0.7072 and max(a[2], b[2], c[2]) > 0.05:
            summe += laenge / 2
    return summe


@unittest.skipUnless(os.environ.get("FREECADCMD"), "FREECADCMD fehlt")
class Druckausrichtung(unittest.TestCase):
    """Teile, die in Einbaulage modelliert sind, werden für den Druck passend gedreht."""

    def _netze(self, projekt):
        from sidecar.engine import vorschau_bauen

        modus = "gehaeuse" if projekt.nur_gehaeuse else "ersatz"
        r = vorschau_bauen(projekt.to_dict(), None, os.environ["FREECADCMD"], modus)
        self.assertTrue(r["ok"], r["fehler"])
        return r["netze"]

    def test_gehaeusedeckel_stopfen_und_knopf_haben_keinen_ueberhang(self):
        from sidecar.ersatzteil import standard_parameter
        from sidecar.gehaeuse import standard

        for netz in self._netze(Projekt(nur_gehaeuse=True, gehaeuse=standard())):
            if "Deckel" in netz["name"]:
                self.assertLess(_ueberhang_mm2(netz), 5.0, netz["name"])
        for art in ("stopfen", "knopf"):
            projekt = Projekt(nur_ersatz=True, ersatzteile=[{"id": "ET1", "art": art, "name": art, "parameter": standard_parameter(art)}])
            self.assertLess(_ueberhang_mm2(self._netze(projekt)[0]), 5.0, art)


@unittest.skipUnless(os.environ.get("FREECADCMD"), "FREECADCMD fehlt")
class Vorschau(unittest.TestCase):
    def test_netze_fuer_eigenes_teil_und_wiederverwendung(self):
        from sidecar.engine import vorschau_bauen

        teil = _teil([_rechteck(40, 30), _kreis(20, 15, 3), {"typ": "text", "x": 3, "y": 3, "text": "A1", "schrift_mm": 5, "loch": False, "z_mm": 12, "h_mm": 0.6}])
        projekt = Projekt(nur_eigene=True, eigene=[teil, Eigenteil(id="E2", formen=[_rechteck(10, 10)])]).to_dict()
        r = vorschau_bauen(projekt, ["E1"], os.environ["FREECADCMD"])
        self.assertTrue(r["ok"], r["fehler"])
        self.assertEqual(len(r["netze"]), 1)  # nur das gewählte Teil
        netz = r["netze"][0]
        self.assertEqual(len(netz["punkte"]) % 3, 0)
        self.assertEqual(len(netz["dreiecke"]) % 3, 0)
        self.assertGreater(len(netz["dreiecke"]), 50)
        self.assertLess(max(netz["dreiecke"]), len(netz["punkte"]) // 3)
        self.assertAlmostEqual(netz["bbox_mm"][3], 40.0, delta=0.1)
        self.assertAlmostEqual(netz["bbox_mm"][5], 12.6, delta=0.1)
        # zweiter Aufruf nutzt die offene Sitzung und ändert das Ergebnis mit den Maßen
        teil.formen[0]["b"] = 60
        r2 = vorschau_bauen(Projekt(nur_eigene=True, eigene=[teil]).to_dict(), ["E1"], os.environ["FREECADCMD"])
        self.assertAlmostEqual(r2["netze"][0]["bbox_mm"][3], 60.0, delta=0.1)

    def test_ungueltig_und_gehaeuse(self):
        from sidecar.engine import vorschau_bauen

        r = vorschau_bauen(Projekt(nur_eigene=True, eigene=[_teil([_rechteck(b=300)])]).to_dict(), ["E1"], os.environ["FREECADCMD"])
        self.assertFalse(r["ok"])
        self.assertTrue(r["fehler"])
        from sidecar.gehaeuse import standard

        g = Projekt(nur_gehaeuse=True, gehaeuse=standard()).to_dict()
        r = vorschau_bauen(g, None, os.environ["FREECADCMD"])
        self.assertTrue(r["ok"], r["fehler"])
        self.assertEqual(len(r["netze"]), 2)  # Korpus und Deckel
        # Druckfertig: Der Schraubdeckel liegt mit der glatten Oberseite auf dem Bett (keine freitragende Platte)
        deckel = next(n for n in r["netze"] if "Deckel" in n["name"])
        punkte, dreiecke = deckel["punkte"], deckel["dreiecke"]
        flaeche_unten = 0.0
        for i in range(0, len(dreiecke), 3):
            a, b, c = [(punkte[j * 3], punkte[j * 3 + 1], punkte[j * 3 + 2]) for j in dreiecke[i:i + 3]]
            if max(a[2], b[2], c[2]) < 0.05:
                flaeche_unten += abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
        breite = deckel["bbox_mm"][3] - deckel["bbox_mm"][0]
        tiefe = deckel["bbox_mm"][4] - deckel["bbox_mm"][1]
        self.assertGreater(flaeche_unten, 0.9 * breite * tiefe, "Die Deckelplatte liegt nicht auf dem Bett")


if __name__ == "__main__":
    unittest.main()
