# -*- coding: utf-8 -*-
"""Auto-Bestückung: Seiten, Gruppen, Strahlsuche und verbesserte Füllung."""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidecar.autofill import auto_bestuecken  # noqa: E402
from sidecar.eigenteil import Eigenteil  # noqa: E402
from sidecar.layout import Projekt, Schublade, footprint, layout_pruefen, plan_berechnen  # noqa: E402


def _projekt(breite=480, tiefe=420, **kw):
    return Projekt(schublade=Schublade(innenbreite_mm=breite, innentiefe_mm=tiefe, nutzhoehe_mm=60), **kw)


def _mitte(box, plan):
    x, y, w, h = footprint(box)
    return (x + w / 2) / plan.einheiten_x, (y + h / 2) / plan.einheiten_y


def _zusammenhaengend(boxen) -> bool:
    zellen = set()
    for b in boxen:
        x, y, w, h = footprint(b)
        zellen |= {(a, c) for a in range(x, x + w) for c in range(y, y + h)}
    if not zellen:
        return True
    start = next(iter(zellen))
    gesehen, stapel = {start}, [start]
    while stapel:
        a, c = stapel.pop()
        for n in ((a + 1, c), (a - 1, c), (a, c + 1), (a, c - 1)):
            if n in zellen and n not in gesehen:
                gesehen.add(n)
                stapel.append(n)
    return len(gesehen) == len(zellen)


class Seiten(unittest.TestCase):
    def _lauf(self, links, rechts):
        p = _projekt()
        plan = plan_berechnen(p.schublade)
        r = auto_bestuecken(
            p,
            wuensche=[
                {"sorte": links, "anzahl": 1, "seite": "links"},
                {"sorte": rechts, "anzahl": 1, "seite": "rechts"},
            ],
            rest_fuellen=False,
        )
        self.assertTrue(r["ok"], r)
        self.assertEqual(len(p.boxen), 2)
        self.assertTrue(layout_pruefen(p)["ok"], layout_pruefen(p)["fehler"])
        return p, plan

    def test_links_und_rechts(self):
        p, plan = self._lauf("besteckfach", "kabel")
        fach = next(b for b in p.boxen if b.name == "Besteckfach")
        kabel = next(b for b in p.boxen if b.name == "Kabelbox")
        self.assertEqual(footprint(fach)[0], 0)  # ganz links
        x, _y, w, _h = footprint(kabel)
        self.assertEqual(x + w, plan.einheiten_x)  # ganz rechts
        self.assertLess(_mitte(fach, plan)[0], _mitte(kabel, plan)[0])

    def test_vertauschte_seiten_vertauschen_die_lage(self):
        p, plan = self._lauf("kabel", "besteckfach")
        fach = next(b for b in p.boxen if b.name == "Besteckfach")
        kabel = next(b for b in p.boxen if b.name == "Kabelbox")
        self.assertLess(_mitte(kabel, plan)[0], _mitte(fach, plan)[0])

    def test_vorne_und_hinten(self):
        p = _projekt()
        plan = plan_berechnen(p.schublade)
        auto_bestuecken(p, wuensche=[{"sorte": "gross", "anzahl": 1, "seite": "hinten"}, {"sorte": "mittel", "anzahl": 1, "seite": "vorne"}], rest_fuellen=False)
        gross = next(b for b in p.boxen if b.name == "Große Box")
        mittel = next(b for b in p.boxen if b.name == "Mittlere Box")
        self.assertGreater(_mitte(gross, plan)[1], _mitte(mittel, plan)[1])

    def test_unbekannte_seite_wird_gemeldet_und_ignoriert(self):
        p = _projekt()
        r = auto_bestuecken(p, wuensche=[{"sorte": "klein", "anzahl": 1, "seite": "oben"}], rest_fuellen=False)
        self.assertTrue(r["ok"])
        self.assertTrue(any("Unbekannte Seite" in h for h in r["hinweise"]))
        self.assertEqual(len(p.boxen), 1)


class Gruppen(unittest.TestCase):
    def test_gruppen_liegen_zusammen(self):
        p = _projekt()
        r = auto_bestuecken(
            p,
            wuensche=[
                {"sorte": "klein", "anzahl": 4, "gruppe": "A", "seite": "links"},
                {"sorte": "schmal", "anzahl": 3, "gruppe": "B", "seite": "rechts"},
            ],
            rest_fuellen=False,
        )
        self.assertTrue(r["ok"])
        a = [b for b in p.boxen if b.name == "Kleine Box"]
        b = [b for b in p.boxen if b.name == "Schmale Box"]
        self.assertEqual((len(a), len(b)), (4, 3))
        self.assertTrue(_zusammenhaengend(a), "Gruppe A zerfällt")
        self.assertTrue(_zusammenhaengend(b), "Gruppe B zerfällt")


class Optimierer(unittest.TestCase):
    def _zufall(self, n=14):
        rnd = random.Random(7)
        for _ in range(n):
            breite, tiefe = rnd.choice([300, 380, 480, 520]), rnd.choice([250, 330, 420])
            eigene = []
            for k in range(rnd.randint(0, 3)):
                form = {"typ": "rechteck", "x": 0, "y": 0, "b": rnd.randint(20, 90), "t": rnd.randint(20, 90), "loch": False}
                eigene.append(Eigenteil(id="E%d" % k, formen=[form], platziert=True, x_mm=rnd.randint(0, breite - 100), y_mm=rnd.randint(0, tiefe - 100)))
            yield _projekt(breite, tiefe, eigene=eigene)

    def test_nie_schlechter_und_oft_besser(self):
        besser = 0
        for p in self._zufall():
            r = auto_bestuecken(p, max_zellen=3)
            self.assertTrue(r["ok"])
            o = r["optimierung"]
            self.assertLessEqual(o["kosten_nachher"], o["kosten_vorher"])
            besser += o["kosten_nachher"] < o["kosten_vorher"]
            pruefung = layout_pruefen(p)
            self.assertTrue(pruefung["ok"], pruefung["fehler"])
        self.assertGreaterEqual(besser, 3, "Die Suche sollte bei mehreren Schubladen besser als das Zeilenverfahren sein")

    def test_reproduzierbar(self):
        def lauf():
            p = _projekt(eigene=[Eigenteil(id="E1", formen=[{"typ": "rechteck", "x": 0, "y": 0, "b": 60, "t": 50, "loch": False}], platziert=True, x_mm=140, y_mm=120)])
            auto_bestuecken(p, wuensche=[{"sorte": "kabel", "anzahl": 2, "seite": "rechts"}, {"sorte": "klein", "anzahl": 3}])
            return [(b.x, b.y, b.ex, b.ey, b.rotation) for b in p.boxen]

        self.assertEqual(lauf(), lauf())

    def test_alle_zellen_belegt_oder_gesperrt(self):
        p = _projekt()
        auto_bestuecken(p, max_zellen=3)
        plan = plan_berechnen(p.schublade)
        belegt = sum(footprint(b)[2] * footprint(b)[3] for b in p.boxen)
        self.assertEqual(belegt, plan.einheiten_x * plan.einheiten_y)

    def test_stile_klein_und_gross_unveraendert(self):
        p = _projekt()
        auto_bestuecken(p, stil="klein")
        self.assertTrue(all(footprint(b)[2:] == (1, 1) for b in p.boxen))
        q = _projekt()
        r = auto_bestuecken(q, stil="gross", max_zellen=3)
        self.assertIsNone(r["optimierung"])


if __name__ == "__main__":
    unittest.main()
