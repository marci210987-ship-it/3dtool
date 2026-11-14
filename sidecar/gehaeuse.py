# -*- coding: utf-8 -*-
"""Elektronik-Gehäusebaukasten: Prüfung und Sollmaße, ohne FreeCAD.

Innenmaße, Schraub- oder Schiebedeckel, Platinenhalter und Wandöffnungen.
Die Körper baut sidecar.gehaeuse_geom. Lochbilder stammen aus den genannten
Zeichnungen, nicht aus einem vermessenen Brett. Das Spiel ist die Lücke im
Modell, kein gemessener Druck.
"""

from __future__ import annotations

BAURAUM_MM = 256.0
WAND_MIN = 1.2
DUESSE = 0.4
UEBERGRIFF = 3.0
PLATINE_DICK = 1.6
LASCHE_TIEFE = 12.0
LASCHE_BREITE = 14.0
LASCHE_LOCH = 4.2

# Pilot und Durchgangsloch für Blechschrauben. Die Säule bleibt mindestens 1,2 mm dick.
SCHRAUBEN = {
    "m3": {"pilot_mm": 2.5, "durchgang_mm": 3.2, "pfosten_mm": 7.0, "senkung_mm": 6.0, "text": "M3, Kernloch 2,5 mm"},
    "m2_5": {"pilot_mm": 2.0, "durchgang_mm": 2.7, "pfosten_mm": 6.0, "senkung_mm": 5.0, "text": "M2,5, Kernloch 2,0 mm"},
}

# Nennlöcher. Einpressgewinde sind typische Herstellerangaben, nicht gedruckt geprüft.
STANOFF = {
    "m2_5": {"loch_mm": 2.2, "text": "M2,5 ins Kunststoff (Kernloch 2,2 mm)"},
    "m3": {"loch_mm": 2.5, "text": "M3 ins Kunststoff (Kernloch 2,5 mm)"},
    "einsatz_m2_5": {"loch_mm": 3.2, "text": "Einpressgewinde M2,5, Nennloch 3,2 mm, nicht geprüft"},
    "einsatz_m3": {"loch_mm": 4.0, "text": "Einpressgewinde M3, Nennloch 4,0 mm, nicht geprüft"},
}

# Quellen stehen auch in der Bedienungsanleitung.
VORLAGEN = {
    "raspberry_pi_4": {
        "name": "Raspberry Pi 4",
        "quelle": (
            "Raspberry Pi Ltd, Mechanical Drawing der Raspberry Pi 4 Model B "
            "(RP-008343-DS): Platine 85 × 56 mm, vier Bohrungen Ø 2,7 mm, "
            "Raster 58 × 49 mm, 3,5 mm vom linken Rand und von beiden Längskanten."
        ),
        "platine_b_mm": 85.0,
        "platine_t_mm": 56.0,
        "loecher": [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]],
        "standoff_loch": "m2_5",
    },
    "raspberry_pi_5": {
        "name": "Raspberry Pi 5",
        "quelle": (
            "Raspberry Pi Ltd, Mechanical Drawing der Raspberry Pi 5: dieselbe Platinengröße "
            "85 × 56 mm und dasselbe Lochbild 58 × 49 mm, Ø 2,7 mm, wie bei der Pi 4."
        ),
        "platine_b_mm": 85.0,
        "platine_t_mm": 56.0,
        "loecher": [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]],
        "standoff_loch": "m2_5",
    },
    "arduino_uno": {
        "name": "Arduino Uno R3",
        "quelle": (
            "Arduino, Datenblatt A000066, Board Outline & Mounting Holes, und die UNO-R3-Referenz: "
            "Platine 68,58 × 53,34 mm, vier Bohrungen Ø 3,2 mm. Ursprung an der USB-Kante unten links: "
            "(13,97 / 2,54), (15,24 / 50,80), (66,04 / 7,62), (66,04 / 35,56) mm. Das Lochbild ist kein Rechteck."
        ),
        "platine_b_mm": 68.58,
        "platine_t_mm": 53.34,
        "loecher": [[13.97, 2.54], [15.24, 50.80], [66.04, 7.62], [66.04, 35.56]],
        "standoff_loch": "m3",
    },
    "eigene": {
        "name": "Eigenes Rechteck",
        "quelle": "Vier Löcher als Rechteck, in der Platine zentriert. Kein Datenblatt.",
        "platine_b_mm": 60.0,
        "platine_t_mm": 40.0,
        "loecher": [],
        "standoff_loch": "m3",
    },
    "keine": {
        "name": "Keine Platine",
        "quelle": "",
        "platine_b_mm": 0.0,
        "platine_t_mm": 0.0,
        "loecher": [],
        "standoff_loch": "m3",
    },
}

STANDARD = {
    "innen_b_mm": 100.0,
    "innen_t_mm": 72.0,
    "innen_h_mm": 32.0,
    "wand_mm": 1.6,
    "boden_mm": 1.6,
    "deckel_mm": 1.6,
    "radius_mm": 2.0,
    "spiel_mm": 0.2,
    "deckel": "schraube",
    "schraube": "m3",
    "senkung": "nein",
    "platine": "raspberry_pi_4",
    "platine_b_mm": 85.0,
    "platine_t_mm": 56.0,
    "loch_x_mm": 50.0,
    "loch_y_mm": 30.0,
    "standoff_h_mm": 8.0,
    "standoff_d_mm": 6.0,
    "standoff_loch": "m2_5",
    "lueftung": "nein",
    "laschen": "nein",
    "oeffnungen": [
        {"seite": "vorne", "form": "rechteck", "pos_mm": 51.6, "unten_mm": 12.0, "breite_mm": 14.0, "hoehe_mm": 6.0},
        {"seite": "links", "form": "rund", "pos_mm": 38.0, "unten_mm": 16.0, "durchmesser_mm": 8.0},
    ],
}


def standard() -> dict:
    return {
        **STANDARD,
        "oeffnungen": [dict(o) for o in STANDARD["oeffnungen"]],
    }


def _zahl(params: dict, key: str, fehler: list[str], name: str) -> float | None:
    if key not in params or params[key] in ("", None):
        fehler.append("%s fehlt." % name)
        return None
    try:
        wert = float(params[key])
    except (TypeError, ValueError):
        fehler.append("%s ist keine Zahl." % name)
        return None
    if wert != wert or wert in (float("inf"), float("-inf")):
        fehler.append("%s ist keine gültige Zahl." % name)
        return None
    return wert


def _fmt(wert: float) -> str:
    return "%g" % wert


def _wand_ok(wand: float, fehler: list[str], name: str) -> None:
    if wand < WAND_MIN - 1e-6:
        fehler.append(
            "%s %s mm ist zu dünn. Für eine 0,4-mm-Düse mindestens %.1f mm."
            % (name, _fmt(wand), WAND_MIN)
        )
    stufen = round(wand / DUESSE)
    if abs(wand - stufen * DUESSE) > 0.05:
        fehler.append("%s %s mm ist kein Vielfaches von 0,4 mm." % (name, _fmt(wand)))


def aussen(params: dict) -> tuple[float, float, float]:
    wand = float(params["wand_mm"])
    return (
        float(params["innen_b_mm"]) + 2.0 * wand,
        float(params["innen_t_mm"]) + 2.0 * wand,
        float(params["boden_mm"]) + float(params["innen_h_mm"]),
    )


def loecher(params: dict) -> list[list[float]]:
    art = str(params.get("platine") or "keine")
    if art == "keine":
        return []
    vorlage = VORLAGEN.get(art)
    if vorlage and art != "eigene":
        return [list(p) for p in vorlage["loecher"]]
    breite = float(params.get("platine_b_mm") or 0)
    tiefe = float(params.get("platine_t_mm") or 0)
    lx = float(params.get("loch_x_mm") or 0)
    ly = float(params.get("loch_y_mm") or 0)
    rx = (breite - lx) / 2.0
    ry = (tiefe - ly) / 2.0
    return [[rx, ry], [rx + lx, ry], [rx, ry + ly], [rx + lx, ry + ly]]


def platinenmass(params: dict) -> tuple[float, float]:
    art = str(params.get("platine") or "keine")
    if art == "keine":
        return 0.0, 0.0
    vorlage = VORLAGEN.get(art)
    if vorlage and art != "eigene":
        return float(vorlage["platine_b_mm"]), float(vorlage["platine_t_mm"])
    return float(params.get("platine_b_mm") or 0), float(params.get("platine_t_mm") or 0)


def ursprung(params: dict) -> tuple[float, float]:
    """Lage der Platinenecke im Innenraum, von der inneren linken hinteren Ecke."""
    pb, pt = platinenmass(params)
    if params.get("platine_x_mm") not in (None, ""):
        return float(params["platine_x_mm"]), float(params["platine_y_mm"])
    return (float(params["innen_b_mm"]) - pb) / 2.0, (float(params["innen_t_mm"]) - pt) / 2.0


def pfosten(params: dict) -> list[tuple[float, float]]:
    if str(params.get("deckel")) != "schraube":
        return []
    ow, od, _h = aussen(params)
    wand = float(params["wand_mm"])
    radius = max(0.0, float(params["radius_mm"]) - wand)
    halbe = SCHRAUBEN[str(params.get("schraube") or "m3")]["pfosten_mm"] / 2.0
    inset = wand + radius + halbe + 0.8
    return [(inset, inset), (ow - inset, inset), (inset, od - inset), (ow - inset, od - inset)]


def standoff_loch_mm(params: dict) -> float:
    art = str(params.get("standoff_loch") or "m2_5")
    if str(params.get("platine")) in VORLAGEN and str(params.get("platine")) not in ("eigene", "keine"):
        art = VORLAGEN[str(params["platine"])]["standoff_loch"]
    return float(STANOFF.get(art, STANOFF["m2_5"])["loch_mm"])


def _oeffnungen(params: dict) -> list[dict]:
    liste = [dict(o) for o in (params.get("oeffnungen") or [])]
    if str(params.get("lueftung")) == "ja":
        ow, od, h = aussen(params)
        boden = float(params["boden_mm"])
        innen_h = float(params["innen_h_mm"])
        unten = boden + max(4.0, (innen_h - 12.0) / 2.0)
        for seite, laenge in (("links", od), ("rechts", od)):
            mitte = laenge / 2.0
            for index, versatz in enumerate((-9.0, -3.0, 3.0, 9.0)):
                liste.append(
                    {
                        "seite": seite,
                        "form": "rechteck",
                        "pos_mm": mitte + versatz,
                        "unten_mm": unten,
                        "breite_mm": 2.0,
                        "hoehe_mm": 12.0,
                        "name": "Lüftung %s %d" % (seite, index + 1),
                    }
                )
    return liste


def masse_korpus(params: dict) -> tuple[float, float, float]:
    ow, od, h = aussen(params)
    if str(params.get("laschen")) == "ja":
        od += LASCHE_TIEFE
    return ow, od, h


def masse_deckel(params: dict) -> tuple[float, float, float]:
    ow, od, _h = aussen(params)
    spiel = float(params["spiel_mm"])
    wand = float(params["wand_mm"])
    deckel = float(params["deckel_mm"])
    if str(params.get("deckel")) == "schiebe":
        return (
            float(params["innen_b_mm"]) - 2.0 * spiel,
            float(params["innen_t_mm"]) - 2.4 - 2.0 * spiel,
            deckel,
        )
    return ow + 2.0 * (spiel + wand), od + 2.0 * (spiel + wand), deckel + UEBERGRIFF


def _bereich(wert: float, unten: float, oben: float, name: str, fehler: list[str]) -> None:
    if wert < unten - 1e-6 or wert > oben + 1e-6:
        fehler.append("%s %s liegt außerhalb von %s bis %s mm." % (name, _fmt(wert), _fmt(unten), _fmt(oben)))


def pruefe(params: dict) -> list[str]:
    p = standard()
    roh = dict(params or {})
    oeffnungen = roh.pop("oeffnungen", None)
    p.update(roh)
    if oeffnungen is not None:
        p["oeffnungen"] = oeffnungen
    fehler: list[str] = []
    felder = (
        ("innen_b_mm", "Innenbreite", 40, 240),
        ("innen_t_mm", "Innentiefe", 30, 240),
        ("innen_h_mm", "Innenhöhe", 16, 200),
        ("wand_mm", "Wandstärke", 1.2, 4.0),
        ("boden_mm", "Bodenstärke", 1.2, 4.0),
        ("deckel_mm", "Deckelstärke", 1.2, 4.0),
        ("radius_mm", "Eckenradius", 0, 20),
        ("spiel_mm", "Spiel zum Deckel", 0.1, 0.5),
        ("standoff_h_mm", "Höhe der Stützen", 3, 40),
        ("standoff_d_mm", "Durchmesser der Stützen", 4, 12),
    )
    zahlen = {}
    for key, name, unten, oben in felder:
        wert = _zahl(p, key, fehler, name)
        if wert is None:
            continue
        _bereich(wert, unten, oben, name, fehler)
        zahlen[key] = wert
    if str(p.get("deckel")) not in ("schraube", "schiebe"):
        fehler.append("Deckel: bitte Schraubdeckel oder Schiebedeckel wählen.")
    if str(p.get("schraube")) not in SCHRAUBEN:
        fehler.append("Schraube: bitte M3 oder M2,5 wählen.")
    if str(p.get("senkung")) not in ("ja", "nein"):
        fehler.append("Senkung: bitte ja oder nein wählen.")
    if str(p.get("platine")) not in VORLAGEN:
        fehler.append("Platine: diese Vorlage gibt es nicht.")
    if str(p.get("lueftung")) not in ("ja", "nein") or str(p.get("laschen")) not in ("ja", "nein"):
        fehler.append("Lüftung und Laschen: bitte ja oder nein wählen.")
    if fehler:
        return fehler
    for key, name in (("wand_mm", "Wandstärke"), ("boden_mm", "Bodenstärke"), ("deckel_mm", "Deckelstärke")):
        _wand_ok(zahlen[key], fehler, name)
    ow, od, h = aussen(p)
    radius = zahlen["radius_mm"]
    if radius > min(ow, od) / 2.0 - 1.0:
        fehler.append("Der Eckenradius ist zu groß für das Außenmaß.")
    innen_r = radius - zahlen["wand_mm"]
    if innen_r > min(zahlen["innen_b_mm"], zahlen["innen_t_mm"]) / 2.0 - 1.0:
        fehler.append("Die Eckenrundung ist zu groß für das Innenmaß.")
    if str(p["deckel"]) == "schraube":
        halbe = SCHRAUBEN[p["schraube"]]["pfosten_mm"] / 2.0
        inset = zahlen["wand_mm"] + max(0.0, innen_r) + halbe + 0.8
        if inset + halbe > ow / 2.0 or inset + halbe > od / 2.0:
            fehler.append("Die Schraubensäulen passen nicht in die Ecken. Gehäuse vergrößern oder Rundung verkleinern.")
        pilot = SCHRAUBEN[p["schraube"]]["pilot_mm"]
        if SCHRAUBEN[p["schraube"]]["pfosten_mm"] < pilot + 2.0 * WAND_MIN:
            fehler.append("Die Schraubensäule ist zu dünn für das Kernloch.")
    else:
        schiene = 2.4
        if zahlen["innen_h_mm"] < zahlen["deckel_mm"] + 2.0 * zahlen["spiel_mm"] + schiene + 4.0:
            fehler.append("Die Innenhöhe ist zu klein für Schiene und Schiebedeckel.")
    if str(p["platine"]) != "keine":
        pb, pt = platinenmass(p)
        ux, uy = ursprung(p)
        if pb > zahlen["innen_b_mm"] - 2.0 or pt > zahlen["innen_t_mm"] - 2.0:
            fehler.append(
                "Die Platine %s × %s mm passt nicht in den Innenraum. Mindestens 1 mm Luft je Seite lassen."
                % (_fmt(pb), _fmt(pt))
            )
        if ux < 1.0 or uy < 1.0 or ux + pb > zahlen["innen_b_mm"] - 1.0 or uy + pt > zahlen["innen_t_mm"] - 1.0:
            fehler.append("Die Platine ragt aus dem Innenraum oder liegt näher als 1 mm an der Wand.")
        loch = standoff_loch_mm(p)
        if zahlen["standoff_d_mm"] < loch + 2.0 * WAND_MIN:
            fehler.append(
                "Die Stütze %s mm ist zu dünn für das Loch %s mm. Mindestens 1,2 mm Wand lassen."
                % (_fmt(zahlen["standoff_d_mm"]), _fmt(loch))
            )
        if zahlen["standoff_h_mm"] + PLATINE_DICK + 2.0 > zahlen["innen_h_mm"]:
            fehler.append("Stütze plus Platine (1,6 mm) plus 2 mm Luft sind höher als das Gehäuse.")
        halbe = zahlen["standoff_d_mm"] / 2.0
        saeulen = pfosten(p)
        for hx, hy in loecher(p):
            wx = zahlen["wand_mm"] + ux + hx
            wy = zahlen["wand_mm"] + uy + hy
            if hx < halbe or hy < halbe or hx > pb - halbe or hy > pt - halbe:
                fehler.append("Ein Platinenloch liegt zu nah am Rand der Platine.")
                break
            if wx - halbe < zahlen["wand_mm"] + 0.4 or wy - halbe < zahlen["wand_mm"] + 0.4:
                fehler.append("Eine Stütze schneidet die Gehäusewand.")
                break
            if wx + halbe > ow - zahlen["wand_mm"] - 0.4 or wy + halbe > od - zahlen["wand_mm"] - 0.4:
                fehler.append("Eine Stütze schneidet die Gehäusewand.")
                break
            for sx, sy in saeulen:
                if (wx - sx) ** 2 + (wy - sy) ** 2 < (halbe + SCHRAUBEN[p["schraube"]]["pfosten_mm"] / 2.0 + 0.6) ** 2:
                    fehler.append("Eine Platinenstütze trifft eine Schraubensäule. Platine verschieben oder das Gehäuse vergrößern.")
                    break
    _oeffnungen_pruefen(p, fehler)
    korpus = masse_korpus(p)
    deckel = masse_deckel(p)
    for name, mass in (("Gehäuse", korpus), ("Deckel", deckel)):
        for achse, wert in zip(("Länge", "Breite", "Höhe"), mass):
            if wert > BAURAUM_MM + 1e-6:
                fehler.append("%s: %s %s mm passt nicht in den Bauraum von 256 mm." % (name, achse, _fmt(round(wert, 1))))
            if wert <= 1.0:
                fehler.append("%s: %s ist nicht plausibel." % (name, achse))
    return fehler


def _oeffnungen_pruefen(params: dict, fehler: list[str]) -> None:
    ow, od, h = aussen(params)
    wand = float(params["wand_mm"])
    boden = float(params["boden_mm"])
    saeulen = pfosten(params)
    if saeulen:
        sperre = saeulen[0][0] + SCHRAUBEN[str(params["schraube"])]["pfosten_mm"] / 2.0 + 1.0
    else:
        sperre = 6.0
    for oeffnung in _oeffnungen(params):
        seite = str(oeffnung.get("seite") or "")
        form = str(oeffnung.get("form") or "")
        name = oeffnung.get("name") or "Öffnung"
        if seite not in ("vorne", "hinten", "links", "rechts", "boden") or form not in ("rechteck", "rund"):
            fehler.append("%s: Seite oder Form ist unbekannt." % name)
            continue
        try:
            pos = float(oeffnung.get("pos_mm"))
            unten = float(oeffnung.get("unten_mm"))
        except (TypeError, ValueError):
            fehler.append("%s: die Position ist keine Zahl." % name)
            continue
        laenge = ow if seite in ("vorne", "hinten", "boden") else od
        if form == "rund":
            try:
                dm = float(oeffnung.get("durchmesser_mm"))
            except (TypeError, ValueError):
                fehler.append("%s: der Durchmesser fehlt." % name)
                continue
            halb_l, halb_h = dm / 2.0, dm / 2.0
            if dm < 2.0 or dm > 40:
                fehler.append("%s: Durchmesser %s mm liegt außerhalb von 2 bis 40 mm." % (name, _fmt(dm)))
        else:
            try:
                breit = float(oeffnung.get("breite_mm"))
                hoch = float(oeffnung.get("hoehe_mm"))
            except (TypeError, ValueError):
                fehler.append("%s: Breite oder Höhe fehlt." % name)
                continue
            halb_l, halb_h = breit / 2.0, hoch
            if breit < 2.0 or hoch < 2.0 or breit > 80 or hoch > 60:
                fehler.append("%s: Breite oder Höhe liegt außerhalb des zulässigen Bereichs." % name)
        if seite == "boden":
            hy = halb_h if form == "rund" else float(oeffnung.get("hoehe_mm")) / 2.0
            if pos - halb_l < sperre or pos + halb_l > ow - sperre or unten - hy < sperre or unten + hy > od - sperre:
                fehler.append("%s liegt zu nah an einer Schraubensäule oder am Rand." % name)
            continue
        von = pos - halb_l
        bis = pos + (halb_l if form == "rund" else halb_l)
        if von < sperre or bis > laenge - sperre:
            fehler.append("%s liegt zu nah an einer Schraubensäule oder an der Ecke." % name)
        z0 = unten - halb_h if form == "rund" else unten
        z1 = unten + halb_h if form == "rund" else unten + halb_h
        if z0 < boden + 1.2 or z1 > h - 1.2:
            fehler.append("%s schneidet Boden oder oberen Rand. Mindestens 1,2 mm stehen lassen." % name)


def teile(params: dict) -> list[dict]:
    korpus = dict(params)
    korpus["teil"] = "korpus"
    deckel = dict(params)
    deckel["teil"] = "deckel"
    return [
        {"id": "G_korpus", "name": "Gehäuse", "params": korpus, "soll": masse_korpus(params)},
        {"id": "G_deckel", "name": "Deckel", "params": deckel, "soll": masse_deckel(params)},
    ]
