# -*- coding: utf-8 -*-
"""Einfache Druckprüfung eines Körpers (nur in FreeCAD). Liefert Hinweise, keine Fehler.

Geprüft werden Überhänge (Flächen, die nach unten zeigen, ohne auf dem Druckbett zu liegen) und
dünne Wände (Teile, die in einer Schicht schmaler als zwei Linienbreiten sind). Das sind Faustregeln
für einen Drucker mit 0,4-mm-Düse, keine Slicer-Simulation. Der Körper liegt in Druckausrichtung
(Unterseite bei z = 0).
"""

from __future__ import annotations

import math

LINIE_MM = 0.4  # Düsendurchmesser, Basis der Grenzwerte
MIN_WAND_MM = 2 * LINIE_MM
BRUECKE_MM = 10.0  # waagerechte Decken ab dieser Spannweite ohne Stütze melden
FLAECHE_MIN_MM2 = 1.0


def _ueberhaenge(shape) -> list[str]:
    import FreeCAD as App

    bruecken = []
    schraegen = []
    for flaeche in shape.Faces:
        bb = flaeche.BoundBox
        try:
            u0, u1, v0, v1 = flaeche.ParameterRange
            n = flaeche.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
        except Exception:
            continue
        if n.z >= -0.01:
            continue
        waagerecht = n.z < -0.99 and bb.ZLength < 1e-4
        if waagerecht:
            if bb.ZMin < 0.05 or flaeche.Area < FLAECHE_MIN_MM2:
                continue
            spannweite = min(bb.XLength, bb.YLength)
            if flaeche.Surface.__class__.__name__ == "Plane" and spannweite > BRUECKE_MM:
                bruecken.append((flaeche.Area, bb))
        elif n.z < -0.7072 and flaeche.Area >= FLAECHE_MIN_MM2 and bb.ZMin > 0.05:
            schraegen.append((flaeche.Area, bb))
    texte = []
    if bruecken:
        flaeche, bb = max(bruecken, key=lambda e: e[0])
        texte.append(
            "Druckhinweis: %d waagerechte Decke(n) mit mehr als %.0f mm Spannweite in der Luft, die größte bei z = %.1f mm (%.0f × %.0f mm). "
            "Dort ist Stützmaterial nötig oder die Brücke muss gedruckt werden können."
            % (len(bruecken), BRUECKE_MM, bb.ZMin, bb.XLength, bb.YLength)
        )
    if schraegen:
        flaeche, bb = max(schraegen, key=lambda e: e[0])
        texte.append(
            "Druckhinweis: %d Fläche(n) hängen steiler als 45° über, die größte bei z = %.1f bis %.1f mm. Dort ist Stützmaterial wahrscheinlich nötig."
            % (len(schraegen), bb.ZMin, bb.ZMax)
        )
    return texte


def _schnitt_flaeche(shape, z: float):
    import FreeCAD as App
    import Part

    drahtlisten = shape.slice(App.Vector(0, 0, 1), z)
    if not drahtlisten:
        return None
    try:
        return Part.makeFace(drahtlisten, "Part::FaceMakerBullseye")
    except Exception:
        return None


def _versatz_voll(flaeche, delta: float):
    """Offset einer vollen Fläche. Die Richtung hängt von der Orientierung der Kontur ab; deshalb wird sie an der Flächenänderung geprüft."""
    neu = flaeche.makeOffset2D(delta, 2)
    if neu.isNull() or not neu.Faces:
        return neu
    wuchs = neu.Area - flaeche.Area
    if (delta > 0 and wuchs < -1e-6) or (delta < 0 and wuchs > 1e-6):
        neu = flaeche.makeOffset2D(-delta, 2)
    return neu


def _versatz_flaeche(flaeche, delta: float):
    """Fläche um delta aufweiten (delta > 0) oder schrumpfen (delta < 0). Außen- und Innenkonturen werden einzeln behandelt,
    weil die Orientierung der Innenkonturen nach einem Versatz nicht verlässlich ist. Liefert None, wenn nichts übrig bleibt."""
    import Part

    try:
        aussen = _versatz_voll(Part.Face(flaeche.OuterWire), delta)
    except Exception:
        if delta < 0:
            return None
        raise
    if aussen.isNull() or not aussen.Faces or aussen.Area < 1e-6:
        return None
    for draht in flaeche.Wires:
        if draht.isSame(flaeche.OuterWire):
            continue
        loch = Part.Face(draht)
        try:
            neu = _versatz_voll(loch, -delta)
        except Exception:
            continue  # das Loch verschwindet beim Schrumpfen
        if neu.isNull() or not neu.Faces or neu.Area < 1e-6:
            continue
        aussen = aussen.cut(neu)
    return aussen if aussen.Area > 1e-6 else None


def _duenne_wand(flaeche) -> tuple[float, tuple[float, float]] | None:
    """Fläche, die beim Öffnen (Schrumpfen und Aufweiten um die halbe Mindestwand) verschwindet. Größter Fund über alle Teilflächen."""
    r = MIN_WAND_MM / 2.0
    beste = None
    for teil in flaeche.Faces:
        try:
            innen = _versatz_flaeche(teil, -r)
            if innen is None:
                if teil.Area <= FLAECHE_MIN_MM2:
                    continue
                mitte = teil.CenterOfMass
                fund = (teil.Area, (mitte.x, mitte.y))  # überall schmaler als die Mindestwand
            else:
                offen = None
                for stueck in innen.Faces:
                    breit = _versatz_flaeche(stueck, r)
                    if breit is not None:
                        offen = breit if offen is None else offen.fuse(breit)
                if offen is None:
                    continue
                rest = teil.cut(offen)
                if rest.Area <= FLAECHE_MIN_MM2:
                    continue
                c = rest.Faces[0].CenterOfMass
                fund = (rest.Area, (c.x, c.y))
        except Exception:
            continue  # Offset nicht berechenbar: lieber kein Hinweis als ein falscher
        if beste is None or fund[0] > beste[0]:
            beste = fund
    return beste


def _duenne_waende(shape) -> list[str]:
    bb = shape.BoundBox
    hoehe = bb.ZMax - bb.ZMin
    if hoehe < 1.0:
        return []
    # kleiner Versatz, damit eine Schnittebene nicht genau auf einer Kante (Stufe, Senkungsbeginn) liegt
    ebenen = sorted({round(bb.ZMin + hoehe * f + 0.0137, 3) for f in (0.08, 0.25, 0.5, 0.75, 0.92)})
    funde = []
    for z in ebenen:
        flaeche = _schnitt_flaeche(shape, z)
        if flaeche is None:
            continue
        fund = _duenne_wand(flaeche)
        if fund:
            funde.append((z, fund[0], fund[1]))
    if not funde:
        return []
    z, _fl, (x, y) = max(funde, key=lambda e: e[1])
    return [
        "Druckhinweis: Dünne Stelle unter %.1f mm (zwei Linienbreiten) in %d von %d geprüften Höhen, zum Beispiel bei z = %.1f mm nahe x = %.0f, y = %.0f mm. "
        "Dünne Wände werden vom Slicer oft weggelassen oder sind instabil." % (MIN_WAND_MM, len(funde), len(ebenen), z, x, y)
    ]


def druckhinweise(shape) -> list[str]:
    """Hinweise zu Überhängen und dünnen Wänden. Ein Fehler in der Prüfung verhindert nie den Export."""
    texte: list[str] = []
    for pruefung in (_ueberhaenge, _duenne_waende):
        try:
            texte.extend(pruefung(shape))
        except Exception:
            continue
    return texte
