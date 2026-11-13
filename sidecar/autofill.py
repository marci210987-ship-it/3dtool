# -*- coding: utf-8 -*-
"""Automatische Bestückung: füllt freie Rasterzellen mit Rasterboxen.

Einfaches, vorhersehbares Verfahren (kein Optimierer): Zellen werden zeilenweise
durchlaufen. An jeder freien Zelle wird das größte freie Rechteck bis zur
Höchstgröße gewählt. Vorhandene Boxen bleiben unverändert.
"""

from __future__ import annotations

from sidecar.layout import (
    Box,
    Projekt,
    footprint,
    neue_id,
    plan_berechnen,
    benoetigte_hoehe_mm,
)
from hausraster_const import kasten_aussen, BAURAUM_X, BAURAUM_Y  # noqa: E402

NAMEN = {
    (1, 1): "Kleine Box",
    (1, 2): "Schmale Box",
    (2, 1): "Schmale Box",
    (2, 2): "Mittlere Box",
}


def _belegt(boxen) -> set:
    zellen = set()
    for box in boxen:
        x, y, w, h = footprint(box)
        for i in range(x, x + w):
            for j in range(y, y + h):
                zellen.add((i, j))
    return zellen


def _max_zellen_im_bauraum() -> int:
    n = 1
    while kasten_aussen(n + 1, 0.0) <= min(BAURAUM_X, BAURAUM_Y) + 1e-6:
        n += 1
    return n


def auto_bestuecken(projekt: Projekt, max_zellen: int = 3, ez: int | None = None) -> dict:
    """Ergänzt ``projekt.boxen``. Gibt Angaben zum Ergebnis zurück."""
    plan = plan_berechnen(projekt.schublade)
    if plan.ungueltig or not plan.einheiten_x or not plan.einheiten_y:
        return {"ok": False, "fehler": ["Für diese Schublade lässt sich kein Raster bilden."], "neu": 0}
    max_zellen = max(1, min(int(max_zellen), _max_zellen_im_bauraum()))
    # Höhe: so hoch wie die Schublade erlaubt, höchstens 4 Stufen.
    stufe = 3 if ez is None else int(ez)
    probe = Box(id="probe", name="probe", x=0, y=0, ex=1, ey=1, ez=stufe)
    while stufe > 1 and benoetigte_hoehe_mm(probe, projekt.schublade.boden_platte_mm) > float(projekt.schublade.nutzhoehe_mm):
        stufe -= 1
        probe.ez = stufe
    if benoetigte_hoehe_mm(probe, projekt.schublade.boden_platte_mm) > float(projekt.schublade.nutzhoehe_mm):
        return {"ok": False, "fehler": ["Die Schublade ist zu niedrig für eine Box."], "neu": 0}

    belegt = _belegt(projekt.boxen)
    neu = []
    for j in range(plan.einheiten_y):
        for i in range(plan.einheiten_x):
            if (i, j) in belegt:
                continue
            beste = (1, 1)
            for h in range(1, max_zellen + 1):
                for w in range(1, max_zellen + 1):
                    if i + w > plan.einheiten_x or j + h > plan.einheiten_y:
                        continue
                    if all((a, b) not in belegt for a in range(i, i + w) for b in range(j, j + h)):
                        if w * h > beste[0] * beste[1]:
                            beste = (w, h)
            w, h = beste
            for a in range(i, i + w):
                for b in range(j, j + h):
                    belegt.add((a, b))
            name = NAMEN.get((w, h)) or ("Große Box" if w * h >= 6 else "Mittlere Box")
            box = Box(id=neue_id("B"), name=name, x=i, y=j, ex=w, ey=h, ez=stufe)
            projekt.boxen.append(box)
            neu.append(box)
    return {"ok": True, "fehler": [], "neu": len(neu), "ez": stufe}
