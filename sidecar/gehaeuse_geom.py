# -*- coding: utf-8 -*-
"""Körper des Elektronikgehäuses. Nur aus FreeCADCmd aufrufen."""

from __future__ import annotations

import math

import FreeCAD as App
import Part

from sidecar.gehaeuse import (
    LASCHE_BREITE,
    LASCHE_LOCH,
    LASCHE_TIEFE,
    SCHRAUBEN,
    UEBERGRIFF,
    aussen,
    loecher,
    masse_deckel,
    masse_korpus,
    pfosten,
    pruefe,
    standoff_loch_mm,
    ursprung,
    _oeffnungen,
)


def _box(x0, y0, z0, x1, y1, z1):
    if x1 < x0 or y1 < y0 or z1 < z0:
        raise RuntimeError("Negatives Maß im Gehäuse.")
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


def _zyl(radius, hoehe, x, y, z):
    return Part.makeCylinder(radius, hoehe, App.Vector(x, y, z), App.Vector(0, 0, 1))


def _einzel(shape, name: str):
    try:
        shape = shape.removeSplitter()
    except Exception:
        pass
    solids = getattr(shape, "Solids", None) or []
    if len(solids) != 1:
        raise RuntimeError("%s ist kein einzelner Körper (%d Teile)." % (name, len(solids)))
    if not solids[0].isValid():
        raise RuntimeError("%s ist geometrisch ungültig." % name)
    return solids[0]


def _rund(x0, y0, z0, breite, tiefe, hoehe, radius):
    radius = float(radius)
    if radius < 0.05 or breite < 2.0 * radius + 0.2 or tiefe < 2.0 * radius + 0.2:
        return _box(x0, y0, z0, x0 + breite, y0 + tiefe, z0 + hoehe)
    r = radius

    def punkt(cx, cy, winkel):
        return App.Vector(cx + r * math.cos(winkel), cy + r * math.sin(winkel), z0)

    def bogen(cx, cy, w0, w1):
        wm = (w0 + w1) / 2.0
        return Part.Arc(punkt(cx, cy, w0), punkt(cx, cy, wm), punkt(cx, cy, w1)).toShape()

    kanten = [
        Part.makeLine(App.Vector(x0 + r, y0, z0), App.Vector(x0 + breite - r, y0, z0)),
        bogen(x0 + breite - r, y0 + r, -math.pi / 2.0, 0.0),
        Part.makeLine(App.Vector(x0 + breite, y0 + r, z0), App.Vector(x0 + breite, y0 + tiefe - r, z0)),
        bogen(x0 + breite - r, y0 + tiefe - r, 0.0, math.pi / 2.0),
        Part.makeLine(App.Vector(x0 + breite - r, y0 + tiefe, z0), App.Vector(x0 + r, y0 + tiefe, z0)),
        bogen(x0 + r, y0 + tiefe - r, math.pi / 2.0, math.pi),
        Part.makeLine(App.Vector(x0, y0 + tiefe - r, z0), App.Vector(x0, y0 + r, z0)),
        bogen(x0 + r, y0 + r, math.pi, 3.0 * math.pi / 2.0),
    ]
    flaeche = Part.Face(Part.Wire(kanten))
    koerper = flaeche.extrude(App.Vector(0, 0, hoehe))
    if koerper.BoundBox.ZLength < hoehe * 0.5:
        koerper = flaeche.extrude(App.Vector(0, 0, -hoehe))
        koerper.translate(App.Vector(0, 0, hoehe))
    return koerper


def _oeffnung_werkzeug(oeffnung, params):
    ow, od, h = aussen(params)
    wand = float(params["wand_mm"])
    seite = str(oeffnung["seite"])
    form = str(oeffnung["form"])
    pos = float(oeffnung["pos_mm"])
    unten = float(oeffnung["unten_mm"])
    tief = wand + 1.6
    if form == "rund":
        dm = float(oeffnung["durchmesser_mm"])
        if seite == "links":
            return _zyl_x(dm / 2.0, tief, -0.8, pos, unten)
        if seite == "rechts":
            return _zyl_x(dm / 2.0, tief, ow - wand - 0.8, pos, unten)
        if seite == "hinten":
            return _zyl_y(dm / 2.0, tief, pos, -0.8, unten)
        if seite == "vorne":
            return _zyl_y(dm / 2.0, tief, pos, od - wand - 0.8, unten)
        return _zyl(dm / 2.0, float(params["boden_mm"]) + 1.6, pos, unten, -0.8)
    breit = float(oeffnung["breite_mm"])
    hoch = float(oeffnung["hoehe_mm"])
    if seite == "links":
        return _box(-0.8, pos - breit / 2.0, unten, wand + 0.6, pos + breit / 2.0, unten + hoch)
    if seite == "rechts":
        return _box(ow - wand - 0.6, pos - breit / 2.0, unten, ow + 0.8, pos + breit / 2.0, unten + hoch)
    if seite == "hinten":
        return _box(pos - breit / 2.0, -0.8, unten, pos + breit / 2.0, wand + 0.6, unten + hoch)
    if seite == "vorne":
        return _box(pos - breit / 2.0, od - wand - 0.6, unten, pos + breit / 2.0, od + 0.8, unten + hoch)
    return _box(pos - breit / 2.0, unten - hoch / 2.0, -0.8, pos + breit / 2.0, unten + hoch / 2.0, float(params["boden_mm"]) + 0.6)


def _zyl_x(radius, laenge, x, y, z):
    return Part.makeCylinder(radius, laenge, App.Vector(x, y, z), App.Vector(1, 0, 0))


def _zyl_y(radius, laenge, x, y, z):
    return Part.makeCylinder(radius, laenge, App.Vector(x, y, z), App.Vector(0, 1, 0))


def _korpus(params: dict):
    fehler = pruefe(params)
    if fehler:
        raise ValueError(" ".join(fehler))
    ow, od, h = aussen(params)
    wand = float(params["wand_mm"])
    boden = float(params["boden_mm"])
    radius = float(params["radius_mm"])
    innen_r = max(0.0, radius - wand)
    koerper = _rund(0, 0, 0, ow, od, h, radius)
    koerper = koerper.cut(_rund(wand, wand, boden, float(params["innen_b_mm"]), float(params["innen_t_mm"]), h - boden + 0.4, innen_r))
    teile = [koerper]
    schraube = SCHRAUBEN[str(params.get("schraube") or "m3")]
    if str(params.get("deckel")) == "schraube":
        for x, y in pfosten(params):
            teile.append(_zyl(schraube["pfosten_mm"] / 2.0, h, x, y, 0))
    else:
        schiene_h = 2.4
        spiel = float(params["spiel_mm"])
        deckel = float(params["deckel_mm"])
        schiene_oben = h - spiel - deckel - spiel
        teile.append(_box(wand - 0.4, wand + 1.0, schiene_oben - schiene_h, wand + 3.0, od - wand - 2.4, schiene_oben))
        teile.append(_box(ow - wand - 3.0, wand + 1.0, schiene_oben - schiene_h, ow - wand + 0.4, od - wand - 2.4, schiene_oben))
        teile.append(_box(wand, wand - 0.4, schiene_oben - schiene_h, ow - wand, wand + 2.4, h - spiel))
        # Schlitz in der Vorderwand, damit der Deckel eingeschoben werden kann.
        teile_schlitz = _box(wand + spiel - 0.2, od - wand - 0.8, schiene_oben + spiel - 0.2, ow - wand - spiel + 0.2, od + 0.8, h + 0.4)
    if str(params.get("laschen")) == "ja":
        for mitte in (ow * 0.28, ow * 0.72):
            teile.append(_box(mitte - LASCHE_BREITE / 2.0, -LASCHE_TIEFE, 0, mitte + LASCHE_BREITE / 2.0, 0.4, max(wand, 2.0)))
    koerper = teile[0]
    for weiter in teile[1:]:
        koerper = koerper.fuse(weiter)
    if str(params.get("deckel")) == "schiebe":
        koerper = koerper.cut(teile_schlitz)
    for oeffnung in _oeffnungen(params):
        koerper = koerper.cut(_oeffnung_werkzeug(oeffnung, params))
    if str(params.get("deckel")) == "schraube":
        pilot = schraube["pilot_mm"] / 2.0
        for x, y in pfosten(params):
            koerper = koerper.cut(_zyl(pilot, h - boden - 1.2, x, y, boden + 1.2))
    if str(params.get("laschen")) == "ja":
        for mitte in (ow * 0.28, ow * 0.72):
            koerper = koerper.cut(_zyl(LASCHE_LOCH / 2.0, max(wand, 2.0) + 1.0, mitte, -LASCHE_TIEFE / 2.0, -0.4))
    if str(params.get("platine")) != "keine":
        ux, uy = ursprung(params)
        loch = standoff_loch_mm(params) / 2.0
        hoehe = float(params["standoff_h_mm"])
        durchmesser = float(params["standoff_d_mm"]) / 2.0
        for hx, hy in loecher(params):
            x = wand + ux + hx
            y = wand + uy + hy
            koerper = koerper.fuse(_zyl(durchmesser, boden + hoehe, x, y, 0))
        for hx, hy in loecher(params):
            x = wand + ux + hx
            y = wand + uy + hy
            koerper = koerper.cut(_zyl(loch, hoehe + 0.4, x, y, boden + 1.2))
    return _einzel(koerper, "Gehäuse")


def _deckel(params: dict):
    fehler = pruefe(params)
    if fehler:
        raise ValueError(" ".join(fehler))
    if str(params.get("deckel")) == "schiebe":
        return _schiebedeckel(params)
    ow, od, h = aussen(params)
    spiel = float(params["spiel_mm"])
    wand = float(params["wand_mm"])
    dick = float(params["deckel_mm"])
    aussen_x0 = -spiel - wand
    aussen_y0 = -spiel - wand
    aussen_x1 = ow + spiel + wand
    aussen_y1 = od + spiel + wand
    z0 = h + spiel - UEBERGRIFF
    z_platte = h + spiel
    z1 = z_platte + dick
    koerper = _box(aussen_x0, aussen_y0, z0, aussen_x1, aussen_y1, z1)
    koerper = koerper.cut(_box(-spiel, -spiel, z0 - 0.2, ow + spiel, od + spiel, z_platte))
    schraube = SCHRAUBEN[str(params.get("schraube") or "m3")]
    for x, y in pfosten(params):
        koerper = koerper.cut(_zyl(schraube["durchgang_mm"] / 2.0, dick + 0.8, x, y, z_platte - 0.2))
        if str(params.get("senkung")) == "ja":
            tiefe = min(dick * 0.55, 1.2)
            koerper = koerper.cut(
                Part.makeCone(
                    schraube["durchgang_mm"] / 2.0,
                    schraube["senkung_mm"] / 2.0,
                    tiefe,
                    App.Vector(x, y, z1 - tiefe),
                    App.Vector(0, 0, 1),
                )
            )
    return _einzel(koerper, "Deckel")


def _schiebedeckel(params: dict):
    spiel = float(params["spiel_mm"])
    wand = float(params["wand_mm"])
    dick = float(params["deckel_mm"])
    breite = float(params["innen_b_mm"]) - 2.0 * spiel
    tiefe = float(params["innen_t_mm"]) - 2.4 - 2.0 * spiel
    return _einzel(_box(wand + spiel, wand + 2.4 + spiel, 0, wand + spiel + breite, wand + 2.4 + spiel + tiefe, dick), "Schiebedeckel")


def baue_gehaeuse(params: dict):
    if str(params.get("teil")) == "deckel":
        return _deckel(params)
    return _korpus(params)


def _verschieben(shape, dx, dy=0.0, dz=0.0):
    kopie = shape.copy()
    kopie.translate(App.Vector(dx, dy, dz))
    return kopie


def passung(params: dict) -> dict:
    """Deckel auf dem Korpus, Schraubenlöcher und Platinenlöcher an den echten Körpern."""
    korpus = _korpus(params)
    deckel = _deckel(params)
    if str(params.get("deckel")) == "schiebe":
        deckel = _schiebedeckel_lage(params)
    gemeinsam = korpus.common(deckel)
    volumen = float(gemeinsam.Volume or 0.0)
    spiel = float(params["spiel_mm"])
    luecke = _luecken(korpus, deckel, params)
    abstand = None if not luecke else min(luecke)
    luecke_ok = bool(luecke) and all(abs(wert - spiel) <= 0.08 for wert in luecke)
    schrauben = _schrauben_fluchten(korpus, deckel, params) if str(params.get("deckel")) == "schraube" else {"ok": True}
    platine = _platine_fluchten(korpus, params)
    ok = volumen < 0.05 and luecke_ok and schrauben.get("ok") and platine.get("ok")
    if ok:
        meldung = "Der Deckel passt. Abstand im Modell %.2f mm." % abstand
    elif volumen >= 0.05:
        meldung = "Der Deckel schneidet das Gehäuse. Schnittvolumen %.2f mm³." % volumen
    elif not luecke_ok:
        meldung = "Die Lücke weicht vom Spiel %s mm ab." % ("%g" % spiel)
    elif not schrauben.get("ok"):
        meldung = schrauben.get("meldung") or "Die Schraubenlöcher treffen die Säulen nicht."
    else:
        meldung = platine.get("meldung") or "Die Platinenlöcher treffen die Stützen nicht."
    return {
        "ok": ok,
        "schnittvolumen_mm3": round(volumen, 6),
        "abstand_mm": None if abstand is None else round(abstand, 4),
        "luecken_mm": None if not luecke else [round(wert, 4) for wert in luecke],
        "spiel_mm": spiel,
        "schrauben_ok": schrauben.get("ok"),
        "platine_ok": platine.get("ok"),
        "meldung": meldung,
        "soll_korpus": masse_korpus(params),
        "soll_deckel": masse_deckel(params),
    }


def _schiebedeckel_lage(params: dict):
    """Der exportierte Deckel liegt bei Z=0. Hier steht er auf den Schienen."""
    wand = float(params["wand_mm"])
    spiel = float(params["spiel_mm"])
    deckel = float(params["deckel_mm"])
    _ow, _od, h = aussen(params)
    schiene_oben = h - spiel - deckel - spiel
    shape = _schiebedeckel(params)
    # _schiebedeckel beginnt schon bei x = wand+spiel, y = wand+2.4+spiel, z = 0
    return _verschieben(shape, 0, 0, schiene_oben + spiel)


def _luecken(korpus, deckel, params):
    ow, od, h = aussen(params)
    spiel = float(params["spiel_mm"])
    if str(params.get("deckel")) == "schiebe":
        bb = deckel.optimalBoundingBox()
        seite = korpus.common(_box(0, (bb.YMin + bb.YMax) / 2.0, bb.ZMin + 0.2, bb.XMin, (bb.YMin + bb.YMax) / 2.0 + 2.0, bb.ZMax - 0.2))
        hinten = korpus.common(_box(bb.XMin + 2.0, 0, bb.ZMin + 0.2, bb.XMax - 2.0, bb.YMin, bb.ZMax - 0.2))
        unten = korpus.common(_box(bb.XMin + 1.0, bb.YMin + 1.0, 0, bb.XMin + 4.0, bb.YMax - 1.0, bb.ZMin))
        if min(seite.Volume, hinten.Volume, unten.Volume) <= 0:
            return None
        return (
            float(bb.XMin - seite.optimalBoundingBox().XMax),
            float(bb.YMin - hinten.optimalBoundingBox().YMax),
            float(bb.ZMin - unten.optimalBoundingBox().ZMax),
        )
    # Seite +X, Seite +Y und der senkrechte Spalt über der Mitte.
    bx = korpus.optimalBoundingBox()
    probe_x = _box(ow, od * 0.4, h - 1.5, ow + 8, od * 0.6, h - 0.4)
    seite = deckel.common(probe_x)
    if not seite.Volume:
        return None
    links = seite.optimalBoundingBox().XMin - ow
    probe_y = _box(ow * 0.4, od, h - 1.5, ow * 0.6, od + 8, h - 0.4)
    vorn = deckel.common(probe_y)
    if not vorn.Volume:
        return None
    vorn_abstand = vorn.optimalBoundingBox().YMin - od
    probe_z = _box(ow * 0.4, od * 0.4, h, ow * 0.6, od * 0.6, h + 8)
    oben = deckel.common(probe_z)
    if not oben.Volume:
        return None
    oben_abstand = oben.optimalBoundingBox().ZMin - h
    return (float(links), float(vorn_abstand), float(oben_abstand))


def _schrauben_fluchten(korpus, deckel, params) -> dict:
    _ow, _od, h = aussen(params)
    spiel = float(params["spiel_mm"])
    dick = float(params["deckel_mm"])
    schraube = SCHRAUBEN[str(params.get("schraube") or "m3")]
    z = h + spiel
    for x, y in pfosten(params):
        nadel = _zyl(schraube["pilot_mm"] * 0.35, dick + 0.4, x, y, z - 0.1)
        if float(nadel.common(deckel).Volume or 0) > 0.02:
            return {"ok": False, "meldung": "Ein Schraubenloch sitzt nicht über der Säule."}
        kranz = _zyl(schraube["durchgang_mm"] / 2.0 + 0.35, 0.4, x, y, z + dick * 0.25)
        if float(kranz.common(deckel).Volume or 0) < 0.01:
            return {"ok": False, "meldung": "Ein Schraubenloch im Deckel fehlt oder ist zu groß."}
        kern = _zyl(schraube["pilot_mm"] * 0.35, 2.0, x, y, h - 2.2)
        if float(kern.common(korpus).Volume or 0) > 0.02:
            return {"ok": False, "meldung": "Das Kernloch der Säule sitzt nicht auf der Schraubenachse."}
    return {"ok": True}


def _platine_fluchten(korpus, params) -> dict:
    if str(params.get("platine")) == "keine":
        return {"ok": True}
    wand = float(params["wand_mm"])
    boden = float(params["boden_mm"])
    ux, uy = ursprung(params)
    loch = standoff_loch_mm(params)
    hoehe = float(params["standoff_h_mm"])
    for hx, hy in loecher(params):
        x = wand + ux + hx
        y = wand + uy + hy
        nadel = _zyl(loch * 0.35, hoehe * 0.6, x, y, boden + 1.4)
        if float(nadel.common(korpus).Volume or 0) > 0.02:
            return {"ok": False, "meldung": "Ein Platinenloch trifft die Stütze nicht."}
        kranz = _zyl(loch / 2.0 + 0.45, 0.5, x, y, boden + hoehe * 0.5)
        if float(kranz.common(korpus).Volume or 0) < 0.01:
            return {"ok": False, "meldung": "Eine Stütze hat kein Loch an der Platinenposition."}
    return {"ok": True}
