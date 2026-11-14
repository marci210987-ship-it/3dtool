# -*- coding: utf-8 -*-
"""Körper des Kabelmanagements. Nur aus FreeCADCmd aufrufen.

Buchse und Stecker sind für alle geraden Teile gleich: die Buchse ist eine
weitere U-Schale mit Spiel, der Stecker ist das Kanalende selbst.
"""

from __future__ import annotations

import FreeCAD as App
import Part

from sidecar.kabel import (
    DECKEL_ABSTAND,
    FLANSCH,
    LIPPE,
    LIPPE_TIEFE,
    aussen_u,
    deckel_laenge,
    masse,
    pruefe,
    schulter,
)


def _box(x0, y0, z0, x1, y1, z1):
    if x1 < x0 or y1 < y0 or z1 < z0:
        raise RuntimeError("Negatives Maß in der Kabelgeometrie.")
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


def _zyl(radius, hoehe, x, y, z):
    return Part.makeCylinder(radius, hoehe, App.Vector(x, y, z), App.Vector(0, 0, 1))


def _vereinigen(teile):
    koerper = teile[0]
    for weiter in teile[1:]:
        koerper = koerper.fuse(weiter)
    return koerper


def _einzel(shape, name: str):
    try:
        shape = shape.removeSplitter()
    except Exception:
        pass
    solids = shape.Solids
    if len(solids) != 1:
        raise RuntimeError("%s ist kein einzelner Körper (%d Teile)." % (name, len(solids)))
    if not solids[0].isValid():
        raise RuntimeError("%s ist geometrisch ungültig." % name)
    return solids[0]


def _werte(p):
    ib = float(p["innenbreite_mm"])
    ih = float(p["innenhoehe_mm"])
    wand = float(p["wand_mm"])
    spiel = float(p["spiel_mm"])
    zapfen = float(p["zapfen_mm"])
    ow, oh = aussen_u(p)
    return ib, ih, wand, spiel, zapfen, ow, oh


def _huelse(p, ueberstand=0.6):
    """Buchse ab x=0. Der Kanal des eigenen Teils beginnt an der Schulter."""
    _ib, _ih, wand, spiel, zapfen, ow, oh = _werte(p)
    y_aussen = ow / 2.0 + spiel + wand
    z_unten = -(spiel + wand)
    ende = schulter(p) + ueberstand
    boden = _box(0, -y_aussen, z_unten, ende, y_aussen, -spiel)
    links = _box(0, -y_aussen, z_unten, ende, -(ow / 2.0 + spiel), oh)
    rechts = _box(0, ow / 2.0 + spiel, z_unten, ende, y_aussen, oh)
    naht = schulter(p)
    bruecke_boden = _box(naht, -y_aussen, z_unten, ende, y_aussen, wand)
    bruecke_links = _box(naht, -y_aussen, 0, ende, -(ow / 2.0 - wand), oh)
    bruecke_rechts = _box(naht, ow / 2.0 - wand, 0, ende, y_aussen, oh)
    schale = _vereinigen([boden, links, rechts, bruecke_boden, bruecke_links, bruecke_rechts])
    hohl = _box(-0.4, -(ow / 2.0 + spiel), -spiel, naht, ow / 2.0 + spiel, oh + 2.0)
    return schale.cut(hohl)


def _kanal_roh(p, nutz: float):
    _ib, _ih, wand, _spiel, _zapfen, ow, oh = _werte(p)
    start = schulter(p)
    ende = start + float(nutz)
    balken = _box(start, -ow / 2.0, 0, ende, ow / 2.0, oh)
    hohl = _box(start - 0.2, -(ow / 2.0 - wand), wand, ende + 0.2, ow / 2.0 - wand, oh + 1.0)
    return _huelse(p).fuse(balken).cut(hohl)


def _deckel(p, nutz: float):
    _ib, _ih, wand, spiel, zapfen, ow, oh = _werte(p)
    laenge = deckel_laenge(p, nutz)
    if laenge <= 1.0:
        raise RuntimeError("Der Deckel wäre kürzer als 1 mm.")
    aussen = ow / 2.0 + spiel + LIPPE
    platte = _box(0, -aussen, LIPPE_TIEFE, laenge, aussen, LIPPE_TIEFE + wand)
    lippe_l = _box(0, -aussen, 0, laenge, -(ow / 2.0 + spiel), LIPPE_TIEFE + wand)
    lippe_r = _box(0, ow / 2.0 + spiel, 0, laenge, aussen, LIPPE_TIEFE + wand)
    return _einzel(_vereinigen([platte, lippe_l, lippe_r]), "Deckel")


def _kanal(p):
    nutz = float(p.get("nutz_mm") or p.get("laenge_mm"))
    return _einzel(_kanal_roh(p, nutz), "Kabelkanal")


def _ecke(p):
    _ib, _ih, wand, _spiel, zapfen, ow, oh = _werte(p)
    schenkel = float(p["schenkel_mm"])
    start = schulter(p)
    x_ende = start + schenkel
    x_balken = _box(start, -ow / 2.0, 0, x_ende, ow / 2.0, oh)
    y_balken = _box(x_ende - ow, 0, 0, x_ende, schenkel, oh)
    koerper = _vereinigen([_huelse(p), x_balken, y_balken])
    x_hohl = _box(start - 0.2, -(ow / 2.0 - wand), wand, x_ende + 0.2, ow / 2.0 - wand, oh + 1.0)
    y_hohl = _box(x_ende - ow + wand, -0.2, wand, x_ende - wand, schenkel + 0.2, oh + 1.0)
    return _einzel(koerper.cut(x_hohl).cut(y_hohl), "Ecke")


def _endkappe(p):
    _ib, _ih, wand, spiel, zapfen, ow, oh = _werte(p)
    y_aussen = ow / 2.0 + spiel + wand
    z_unten = -(spiel + wand)
    if str(p.get("passt_auf")) == "buchse":
        stecker = _box(-0.4, -ow / 2.0, 0, zapfen, ow / 2.0, oh)
        hohl = _box(-0.2, -(ow / 2.0 - wand), wand, zapfen + 0.2, ow / 2.0 - wand, oh + 1.0)
        platte = _box(-wand, -y_aussen, z_unten, 0, y_aussen, oh)
        return _einzel(stecker.cut(hohl).fuse(platte), "Endkappe")
    naht = schulter(p)
    platte = _box(naht, -y_aussen, z_unten, naht + wand, y_aussen, oh)
    return _einzel(_huelse(p).fuse(platte), "Endkappe")


def _halter(p):
    _ib, _ih, wand, spiel, _zapfen, ow, oh = _werte(p)
    laenge = float(p["laenge_mm"])
    y_aussen = ow / 2.0 + spiel + wand
    z_unten = -(spiel + wand)
    boden = _box(0, -y_aussen, z_unten, laenge, y_aussen, -spiel)
    links = _box(0, -y_aussen, z_unten, laenge, -(ow / 2.0 + spiel), oh)
    rechts = _box(0, ow / 2.0 + spiel, z_unten, laenge, y_aussen, oh)
    platte = _box(0, -y_aussen - FLANSCH, z_unten, laenge, -y_aussen + 0.4, z_unten + wand)
    schale = _vereinigen([boden, links, rechts, platte])
    hohl = _box(-0.4, -(ow / 2.0 + spiel), -spiel, laenge + 0.4, ow / 2.0 + spiel, oh + 2.0)
    loch = _zyl(float(p["loch_mm"]) / 2.0, wand + 2.0, laenge / 2.0, -y_aussen - FLANSCH / 2.0, z_unten - 1.0)
    return _einzel(schale.cut(hohl).cut(loch), "Wandhalter")


def _auslass(p):
    nutz = float(p["laenge_mm"])
    wand = float(p["wand_mm"])
    kanal = _kanal_roh(p, nutz)
    mitte = schulter(p) + nutz / 2.0
    loch = _zyl(float(p["auslass_mm"]) / 2.0, wand + 4.0, mitte, 0, -2.0)
    return _einzel(kanal.cut(loch), "Kabelauslass")


def baue_kabel(params: dict):
    art = str(params.get("art") or "")
    fehler = pruefe(art, params)
    if fehler:
        raise ValueError(" ".join(fehler))
    if art == "kanal":
        return _kanal(params)
    if art == "deckel":
        nutz = float(params.get("nutz_mm") or params.get("laenge_mm"))
        return _deckel(params, nutz)
    if art == "ecke":
        return _ecke(params)
    if art == "endkappe":
        return _endkappe(params)
    if art == "halter":
        return _halter(params)
    if art == "auslass":
        return _auslass(params)
    raise ValueError("Unbekanntes Kabelteil %s." % art)


def stecker_spitze_x(params: dict) -> float | None:
    """X-Lage der Steckerspitze. None, wenn der Stecker nicht entlang +X zeigt."""
    art = str(params.get("art"))
    if art in ("kanal", "auslass"):
        nutz = float(params.get("nutz_mm") or params.get("laenge_mm"))
        return schulter(params) + nutz
    if art == "endkappe" and str(params.get("passt_auf")) == "buchse":
        return float(params["zapfen_mm"])
    return None


def _ecke_auf_x(shape, params: dict, ziel_spitze: float):
    """Dreht den Stecker der Ecke von +Y auf +X und setzt die Spitze."""
    _ib, _ih, _wand, _spiel, _zapfen, ow, _oh = _werte(params)
    schenkel = float(params["schenkel_mm"])
    mitte = schulter(params) + schenkel - ow / 2.0
    kopie = shape.copy()
    kopie.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -90)
    kopie.translate(App.Vector(ziel_spitze - schenkel, mitte, 0))
    return kopie


def _verschieben(shape, dx, dy=0.0, dz=0.0):
    kopie = shape.copy()
    kopie.translate(App.Vector(dx, dy, dz))
    return kopie


def _umgriff(pa: dict, pb: dict) -> dict:
    """Der Halter liegt um den geraden Kanal, mit demselben Spiel wie die Buchse."""
    from sidecar.kabel import profil_unterschiede

    if str(pa.get("art")) == "halter":
        halter_p, kanal_p = pa, pb
    else:
        halter_p, kanal_p = pb, pa
    if str(kanal_p.get("art")) not in ("kanal", "auslass"):
        return {
            "ok": False,
            "schnittvolumen_mm3": None,
            "abstand_mm": None,
            "spiel_mm": None,
            "meldung": "Der Wandhalter greift um einen geraden Kanal oder einen Auslass.",
        }
    kanal = baue_kabel(kanal_p)
    halter = _verschieben(baue_kabel(halter_p), schulter(kanal_p) + 4.0)
    gemeinsam = kanal.common(halter)
    volumen = float(gemeinsam.Volume or 0.0)
    spiel = float(kanal_p["spiel_mm"])
    luecke = _luecken(kanal, halter)
    abstand = None if not luecke else min(luecke)
    unterschied = profil_unterschiede({"parameter": pa}, {"parameter": pb})
    luecke_ok = bool(luecke) and all(abs(wert - spiel) <= 0.08 for wert in luecke)
    passt = volumen < 0.05 and luecke_ok and not unterschied
    if passt:
        meldung = "Der Halter umgreift den Kanal. Abstand im Modell %.2f mm." % abstand
    elif unterschied:
        meldung = unterschied[0]
    else:
        meldung = "Der Halter passt geometrisch nicht um den Kanal."
    return {
        "ok": passt,
        "schnittvolumen_mm3": round(volumen, 6),
        "abstand_mm": None if abstand is None else round(abstand, 4),
        "luecken_mm": None if luecke is None else [round(wert, 4) for wert in luecke],
        "spiel_mm": spiel,
        "meldung": meldung,
    }


def passung_geometrisch(a: dict, b: dict) -> dict:
    """Stecker von a in die Buchse von b, an den gebauten Körpern gemessen."""
    from sidecar.kabel import profil_unterschiede

    pa = dict(a.get("parameter") or a)
    pb = dict(b.get("parameter") or b)
    pa["art"] = a.get("art") or pa.get("art")
    pb["art"] = b.get("art") or pb.get("art")
    if "halter" in (str(pa.get("art")), str(pb.get("art"))):
        return _umgriff(pa, pb)
    spitze = stecker_spitze_x(pa)
    if str(pb.get("art")) not in ("kanal", "auslass", "endkappe", "ecke"):
        return {
            "ok": False,
            "schnittvolumen_mm3": None,
            "abstand_mm": None,
            "spiel_mm": None,
            "meldung": "Die geometrische Prüfung verbindet einen geraden Stecker mit einer Buchse.",
        }
    if str(pb.get("art")) == "endkappe" and str(pb.get("passt_auf")) != "stecker":
        return {
            "ok": False,
            "schnittvolumen_mm3": None,
            "abstand_mm": None,
            "spiel_mm": None,
            "meldung": "Diese Endkappe ist selbst ein Stecker und hat keine Buchse.",
        }
    stecker = baue_kabel(pa)
    buchse = baue_kabel(pb)
    if spitze is None and str(pa.get("art")) == "ecke":
        stecker = _ecke_auf_x(stecker, pa, float(pb["zapfen_mm"]))
    elif spitze is None:
        return {
            "ok": False,
            "schnittvolumen_mm3": None,
            "abstand_mm": None,
            "spiel_mm": None,
            "meldung": "Die geometrische Prüfung verbindet einen Stecker mit einer Buchse.",
        }
    else:
        stecker = _verschieben(stecker, float(pb["zapfen_mm"]) - spitze)
    gemeinsam = stecker.common(buchse)
    volumen = float(gemeinsam.Volume or 0.0)
    spiel = float(pb["spiel_mm"])
    luecke = _luecken(stecker, buchse)
    abstand = None if not luecke else min(luecke)
    unterschied = profil_unterschiede({"parameter": pa}, {"parameter": pb})
    toleranz = 0.08
    luecke_ok = bool(luecke) and all(abs(wert - spiel) <= toleranz for wert in luecke)
    passt = volumen < 0.05 and luecke_ok and not unterschied
    if passt:
        meldung = "Der Stecker passt in die Buchse. Abstand im Modell %.2f mm." % abstand
    elif volumen >= 0.05:
        meldung = "Der Stecker schneidet die Buchse. Schnittvolumen %.1f mm³." % volumen
        if unterschied:
            meldung = unterschied[0] + " " + meldung
    elif unterschied:
        meldung = unterschied[0]
    else:
        meldung = "Die Lücke weicht vom Spiel %s mm ab (gemessen %s)." % (
            ("%g" % spiel),
            ", ".join("%.2f" % wert for wert in (luecke or [])),
        )
    return {
        "ok": passt,
        "schnittvolumen_mm3": round(volumen, 6),
        "abstand_mm": None if abstand is None else round(abstand, 4),
        "luecken_mm": None if luecke is None else [round(wert, 4) for wert in luecke],
        "spiel_mm": spiel,
        "meldung": meldung,
        "soll_a": masse(pa["art"], pa),
        "soll_b": masse(pb["art"], pb),
    }


def _luecken(stecker, buchse):
    """Seiten- und Bodenabstand im Überlapp, gemessen an den Körpern."""
    bs = stecker.optimalBoundingBox()
    bb = buchse.optimalBoundingBox()
    x0 = max(bs.XMin, bb.XMin) + 1.0
    x1 = min(bs.XMax, bb.XMax) - 1.0
    if x1 <= x0 + 0.5:
        return None
    slab = _box(x0, -200, -200, x1, 200, 200)
    mb = stecker.common(slab).optimalBoundingBox()

    def seite(y0, y1, aussen_nach_plus):
        probe = _box(x0, y0, mb.ZMin + 0.4, x1, y1, max(mb.ZMin + 0.8, mb.ZMax - 0.4))
        treffer = buchse.common(probe)
        if not treffer.Volume or treffer.Volume < 1e-4:
            return None
        tb = treffer.optimalBoundingBox()
        return (tb.YMin - mb.YMax) if aussen_nach_plus else (mb.YMin - tb.YMax)

    rechts = seite(mb.YMax, mb.YMax + 40.0, True)
    links = seite(mb.YMin - 40.0, mb.YMin, False)
    boden_probe = _box(x0, mb.YMin + 1.0, mb.ZMin - 40.0, x1, mb.YMax - 1.0, mb.ZMin)
    boden = buchse.common(boden_probe)
    unten = None
    if boden.Volume and boden.Volume >= 1e-4:
        unten = mb.ZMin - boden.optimalBoundingBox().ZMax
    if None in (links, rechts, unten):
        return None
    return (float(links), float(rechts), float(unten))
