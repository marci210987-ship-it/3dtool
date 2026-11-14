# -*- coding: utf-8 -*-
"""Körper der Ersatzteile. Nur aus FreeCADCmd aufrufen."""

from __future__ import annotations

import FreeCAD as App
import Part

from sidecar.ersatzteil import masse, pruefe


def _box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


def _zyl(radius, hoehe, x, y, z, dx=0.0, dy=0.0, dz=1.0):
    return Part.makeCylinder(radius, hoehe, App.Vector(x, y, z), App.Vector(dx, dy, dz))


def _vereinigen(teile):
    koerper = teile[0]
    for weiter in teile[1:]:
        koerper = koerper.fuse(weiter)
    return koerper


def _einzel(shape, name: str):
    shape = shape.removeSplitter()
    solids = shape.Solids
    if len(solids) != 1:
        raise RuntimeError("%s ist kein einzelner Körper (%d Teile)." % (name, len(solids)))
    if not solids[0].isValid():
        raise RuntimeError("%s ist geometrisch ungültig." % name)
    return solids[0]


def _kabelclip(p):
    d = float(p["durchmesser_mm"])
    n = int(p["anzahl"])
    wand = float(p["wand_mm"])
    breite, laenge, hoehe = masse("kabelclip", p)
    boden = 1.6
    rand = 3.0
    spalt = 2.0
    teile = [_box(0, 0, 0, breite, laenge, boden)]
    cursor = rand
    lip = min(1.2, d * 0.2)
    for _ in range(n):
        teile.append(_box(0, cursor, boden - 0.05, breite, cursor + wand, hoehe))
        rechts = cursor + wand + d
        teile.append(_box(0, rechts, boden - 0.05, breite, rechts + wand, hoehe))
        if lip >= 0.8:
            teile.append(_box(0, cursor + wand - 0.2, hoehe - wand, breite, cursor + wand + lip, hoehe))
            teile.append(_box(0, rechts - lip, hoehe - wand, breite, rechts + 0.2, hoehe))
        cursor += d + 2 * wand + spalt
    koerper = _vereinigen(teile)
    if str(p.get("befestigung")) == "schraube":
        koerper = koerper.cut(_zyl(1.6, boden + 1.0, breite / 2.0, laenge - 6.0, -0.4))
    return _einzel(koerper, "Kabelclip")


def _rohr(aussen, innen, laenge, name):
    koerper = _zyl(aussen / 2.0, laenge, 0, 0, 0)
    koerper = koerper.cut(_zyl(innen / 2.0, laenge + 1.0, 0, 0, -0.5))
    # Zylinder liegt mit der Achse in Z, der Mittelpunkt ist der Ursprung.
    # Für eine Bounding-Box ab 0 verschieben wir um den Radius.
    koerper.translate(App.Vector(aussen / 2.0, aussen / 2.0, 0))
    return _einzel(koerper, name)


def _wandhaken(p):
    hoehe = float(p["hoehe_mm"])
    ausladung = float(p["ausladung_mm"])
    breite = float(p["breite_mm"])
    ruecken = 8.0
    haken = 4.0
    pts = [
        App.Vector(0, 0, 0),
        App.Vector(ruecken, 0, 0),
        App.Vector(ruecken, hoehe - haken, 0),
        App.Vector(ausladung, hoehe - haken, 0),
        App.Vector(ausladung, hoehe, 0),
        App.Vector(0, hoehe, 0),
        App.Vector(0, 0, 0),
    ]
    flaeche = Part.Face(Part.makePolygon(pts))
    koerper = flaeche.extrude(App.Vector(0, 0, breite))
    loch = float(p["loch_mm"]) / 2.0
    koerper = koerper.cut(_zyl(loch, breite + 1.0, ruecken / 2.0, hoehe * 0.38, -0.5))
    return _einzel(koerper, "Wandhaken")


def _moebelfuss(p):
    d = float(p["durchmesser_mm"])
    h = float(p["hoehe_mm"])
    loch = float(p["loch_mm"])
    koerper = _zyl(d / 2.0, h, 0, 0, 0)
    tiefe = min(h - 1.6, max(2.0, h * 0.6))
    koerper = koerper.cut(_zyl(loch / 2.0, tiefe + 0.4, 0, 0, h - tiefe))
    koerper.translate(App.Vector(d / 2.0, d / 2.0, 0))
    return _einzel(koerper, "Möbelfuß")


def _knopf(p):
    d = float(p["durchmesser_mm"])
    h = float(p["hoehe_mm"])
    welle = float(p["welle_mm"])
    tiefe = float(p["tiefe_mm"])
    koerper = _zyl(d / 2.0, h, 0, 0, 0)
    koerper = koerper.cut(_zyl(welle / 2.0, tiefe + 0.2, 0, 0, -0.2))
    if str(p.get("wellenart")) == "d":
        # Abflachung: eine Seite der Bohrung wird bis zur Sehne freigeschnitten.
        sehne = welle / 2.0 - min(1.5, welle * 0.25)
        koerper = koerper.cut(_box(sehne, -welle, -0.2, welle, welle, tiefe))
    koerper.translate(App.Vector(d / 2.0, d / 2.0, 0))
    return _einzel(koerper, "Drehknopf")


def _stopfen(p):
    loch = float(p["loch_mm"])
    tiefe = float(p["tiefe_mm"])
    spiel = float(p["spiel_mm"])
    kragen = float(p["kragen_mm"])
    stecker = loch - 2 * spiel
    aussen = stecker + 2 * kragen
    koerper = _zyl(stecker / 2.0, tiefe, 0, 0, 0)
    flansch = _zyl(aussen / 2.0, 1.6, 0, 0, tiefe - 0.05)
    koerper = koerper.fuse(flansch)
    koerper.translate(App.Vector(aussen / 2.0, aussen / 2.0, 0))
    return _einzel(koerper, "Stopfen")


def _winkel(p):
    laenge = float(p["laenge_mm"])
    hoehe = float(p["hoehe_mm"])
    breite = float(p["breite_mm"])
    dicke = float(p["dicke_mm"])
    loch = float(p["loch_mm"]) / 2.0
    boden = _box(0, 0, 0, laenge, breite, dicke)
    wand = _box(0, 0, 0, dicke, breite, hoehe)
    koerper = boden.fuse(wand)
    koerper = koerper.cut(_zyl(loch, dicke + 1.2, laenge * 0.62, breite / 2.0, -0.6))
    koerper = koerper.cut(_zyl(loch, dicke + 1.2, -0.6, breite / 2.0, hoehe * 0.62, 1, 0, 0))
    return _einzel(koerper, "Winkel")


_BAUER = {
    "kabelclip": _kabelclip,
    "distanzhuelse": lambda p: _rohr(float(p["aussen_mm"]), float(p["innen_mm"]), float(p["laenge_mm"]), "Distanzhülse"),
    "unterlegscheibe": lambda p: _rohr(float(p["aussen_mm"]), float(p["innen_mm"]), float(p["dicke_mm"]), "Unterlegscheibe"),
    "wandhaken": _wandhaken,
    "moebelfuss": _moebelfuss,
    "knopf": _knopf,
    "stopfen": _stopfen,
    "winkel": _winkel,
}


def baue_ersatzteil(params: dict):
    art = str(params.get("art") or "")
    fehler = pruefe(art, params)
    if fehler:
        raise ValueError("\n".join(fehler))
    bauer = _BAUER.get(art)
    if not bauer:
        raise ValueError("Unbekanntes Ersatzteil „%s“." % art)
    return bauer(params)
