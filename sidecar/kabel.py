# -*- coding: utf-8 -*-
"""Modulares Kabelmanagement: Prüfung und Sollmaße, ohne FreeCAD.

Gerade Kanäle, Ecke, Endkappe, Wandhalter und Auslass teilen sich ein Profil
(Innenmaß, Wand, Spiel, Einstecktiefe). Die Körper baut sidecar.kabel_geom.
Das Spiel ist die Lücke im Modell, kein gemessener Druck.
"""

from __future__ import annotations

import math

BAURAUM_MM = 256.0
WAND_MIN = 1.2
DUESSE = 0.4
SEGMENT_MAX = 250.0
LIPPE = 1.2
LIPPE_TIEFE = 3.0
FLANSCH = 18.0
DECKEL_ABSTAND = 1.0

PROFIL = (
    "innenbreite_mm",
    "innenhoehe_mm",
    "wand_mm",
    "spiel_mm",
    "zapfen_mm",
)

PROFIL_FELDER = [
    {"key": "innenbreite_mm", "label": "Innenbreite", "min": 10, "max": 60, "step": 1, "einheit": "mm", "gruppe": "profil"},
    {"key": "innenhoehe_mm", "label": "Innenhöhe", "min": 8, "max": 30, "step": 1, "einheit": "mm", "gruppe": "profil"},
    {"key": "wand_mm", "label": "Wandstärke", "min": 1.2, "max": 3.2, "step": 0.4, "einheit": "mm", "gruppe": "profil"},
    {"key": "spiel_mm", "label": "Spiel der Verbindung", "min": 0.1, "max": 0.5, "step": 0.05, "einheit": "mm", "gruppe": "profil"},
    {"key": "zapfen_mm", "label": "Einstecktiefe", "min": 8, "max": 16, "step": 1, "einheit": "mm", "gruppe": "profil"},
]

PROFIL_STANDARD = {
    "innenbreite_mm": 20.0,
    "innenhoehe_mm": 12.0,
    "wand_mm": 1.6,
    "spiel_mm": 0.2,
    "zapfen_mm": 10.0,
}

KATALOG = [
    {
        "id": "kanal",
        "name": "Kabelkanal",
        "text": "Gerades Stück mit Buchse am Anfang und Stecker am Ende. Längere Stücke werden für das 256-mm-Bett geteilt.",
        "druck": "Öffnung nach oben auf das Bett legen. Keine Stützen. Einen Deckel flach daneben legen. Das Spiel ist die Lücke im Modell, nicht am Druck geprüft.",
        "standard": {**PROFIL_STANDARD, "laenge_mm": 120.0, "deckel": "nein"},
        "felder": [
            *PROFIL_FELDER,
            {"key": "laenge_mm", "label": "Nutzlänge", "min": 30, "max": 2000, "step": 1, "einheit": "mm"},
            {"key": "deckel", "label": "Deckel", "auswahl": [
                {"wert": "nein", "text": "Ohne Deckel"},
                {"wert": "ja", "text": "Mit aufsteckbarem Deckel"},
            ]},
        ],
    },
    {
        "id": "ecke",
        "name": "90°-Ecke",
        "text": "Winkel mit derselben Buchse und demselben Stecker wie der gerade Kanal.",
        "druck": "Flach drucken, Öffnung nach oben. Beide Schenkel liegen auf dem Bett.",
        "standard": {**PROFIL_STANDARD, "schenkel_mm": 50.0},
        "felder": [
            *PROFIL_FELDER,
            {"key": "schenkel_mm", "label": "Schenkellänge", "min": 30, "max": 180, "step": 1, "einheit": "mm"},
        ],
    },
    {
        "id": "endkappe",
        "name": "Endkappe",
        "text": "Schließt ein offenes Ende. Die Kappe für den Stecker ist eine Buchse, die Kappe für die Buchse ein Stecker.",
        "druck": "Die offene Seite nach oben auf das Bett legen.",
        "standard": {**PROFIL_STANDARD, "passt_auf": "stecker"},
        "felder": [
            *PROFIL_FELDER,
            {"key": "passt_auf", "label": "Passt auf", "auswahl": [
                {"wert": "stecker", "text": "das Stecker-Ende"},
                {"wert": "buchse", "text": "das Buchsen-Ende"},
            ]},
        ],
    },
    {
        "id": "halter",
        "name": "Wandhalter",
        "text": "Umgreift den Kanal von unten und wird mit einer Schraube an Wand oder Tischplatte befestigt.",
        "druck": "Lasche auf das Bett, Öffnung nach oben. Das Loch ist eine Vorgabe für eine M4-Schraube.",
        "standard": {**PROFIL_STANDARD, "laenge_mm": 24.0, "loch_mm": 4.5},
        "felder": [
            *PROFIL_FELDER,
            {"key": "laenge_mm", "label": "Länge der Schelle", "min": 16, "max": 80, "step": 1, "einheit": "mm"},
            {"key": "loch_mm", "label": "Schraubenloch", "min": 3, "max": 6, "step": 0.1, "einheit": "mm"},
        ],
    },
    {
        "id": "auslass",
        "name": "Kabelauslass",
        "text": "Kurzes Kanalstück mit einem Loch im Boden, damit ein Kabel nach unten austreten kann.",
        "druck": "Öffnung nach oben. Das Loch liegt auf dem Bett, der Rand bleibt stehen.",
        "standard": {**PROFIL_STANDARD, "laenge_mm": 50.0, "auslass_mm": 10.0},
        "felder": [
            *PROFIL_FELDER,
            {"key": "laenge_mm", "label": "Nutzlänge", "min": 30, "max": 200, "step": 1, "einheit": "mm"},
            {"key": "auslass_mm", "label": "Loch im Boden", "min": 4, "max": 24, "step": 0.5, "einheit": "mm"},
        ],
    },
]


def katalog_nach_id(art: str) -> dict | None:
    for eintrag in KATALOG:
        if eintrag["id"] == art:
            return eintrag
    return None


def standard_parameter(art: str) -> dict:
    eintrag = katalog_nach_id(art)
    if not eintrag:
        return {}
    return dict(eintrag["standard"])


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


def aussen_u(params: dict) -> tuple[float, float]:
    innen_b = float(params["innenbreite_mm"])
    innen_h = float(params["innenhoehe_mm"])
    wand = float(params["wand_mm"])
    return innen_b + 2.0 * wand, innen_h + wand


def huelse_yz(params: dict) -> tuple[float, float]:
    """Außenmaß der Buchse in Y und Z."""
    ow, oh = aussen_u(params)
    wand = float(params["wand_mm"])
    spiel = float(params["spiel_mm"])
    return ow + 2.0 * (spiel + wand), oh + spiel + wand


def schulter(params: dict) -> float:
    return float(params["zapfen_mm"]) + float(params["spiel_mm"])


def max_nutz(params: dict) -> float:
    return SEGMENT_MAX - schulter(params)


def nutzlaengen(params: dict) -> list[float]:
    gesamt = float(params.get("nutz_mm") or params.get("laenge_mm") or 0)
    if params.get("art") != "kanal" and "nutz_mm" not in params:
        return [gesamt]
    grenze = max_nutz(params)
    if gesamt <= grenze + 1e-6:
        return [round(gesamt, 3)]
    anzahl = int(math.ceil(gesamt / grenze - 1e-9))
    basis = round(gesamt / anzahl, 3)
    laengen = [basis] * (anzahl - 1)
    laengen.append(round(gesamt - basis * (anzahl - 1), 3))
    return laengen


def deckel_laenge(params: dict, nutz: float) -> float:
    return float(nutz) - float(params["zapfen_mm"]) - DECKEL_ABSTAND


def masse(art: str, params: dict) -> tuple[float, float, float] | None:
    """Außenmaß eines Stücks (X, Y, Z). Bei einem langen Kanal das größte Segment."""
    p = params or {}
    try:
        breite, hoehe = huelse_yz(p)
        zapfen = float(p["zapfen_mm"])
        spiel = float(p["spiel_mm"])
        wand = float(p["wand_mm"])
    except (KeyError, TypeError, ValueError):
        return None
    if art == "kanal":
        laengen = nutzlaengen({**p, "art": "kanal"})
        nutz = max(laengen) if laengen else 0.0
        return (schulter(p) + nutz, breite, hoehe)
    if art == "deckel":
        nutz = float(p.get("nutz_mm") or p.get("laenge_mm") or 0)
        return (deckel_laenge(p, nutz), aussen_u(p)[0] + 2.0 * (spiel + LIPPE), LIPPE_TIEFE + wand)
    if art == "ecke":
        schenkel = float(p.get("schenkel_mm") or 0)
        y_aussen = breite / 2.0
        return (schulter(p) + schenkel, schenkel + y_aussen, hoehe)
    if art == "endkappe":
        if str(p.get("passt_auf")) == "buchse":
            return (zapfen + wand, breite, hoehe)
        return (schulter(p) + wand, breite, hoehe)
    if art == "halter":
        laenge = float(p.get("laenge_mm") or 0)
        return (laenge, breite + FLANSCH, hoehe)
    if art == "auslass":
        nutz = float(p.get("laenge_mm") or 0)
        return (schulter(p) + nutz, breite, hoehe)
    return None


def _wand_ok(wand: float, fehler: list[str]) -> None:
    if wand < WAND_MIN - 1e-6:
        fehler.append(
            "Wandstärke %s mm ist zu dünn. Für eine 0,4-mm-Düse mindestens %.1f mm (drei Linien)."
            % (_fmt(wand), WAND_MIN)
        )
    stufen = round(wand / DUESSE)
    if abs(wand - stufen * DUESSE) > 0.05:
        fehler.append(
            "Wandstärke %s mm ist kein Vielfaches von 0,4 mm. Sinnvoll sind 1,2 / 1,6 / 2,0 / 2,4."
            % _fmt(wand)
        )


def _bereich(wert: float, feld: dict, fehler: list[str]) -> None:
    if wert < float(feld["min"]) - 1e-6 or wert > float(feld["max"]) + 1e-6:
        fehler.append(
            "%s %s liegt außerhalb von %s bis %s %s."
            % (feld["label"], _fmt(wert), feld["min"], feld["max"], feld.get("einheit") or "mm")
        )


def pruefe(art: str, params: dict) -> list[str]:
    if art == "deckel":
        eintrag = katalog_nach_id("kanal")
    else:
        eintrag = katalog_nach_id(art)
    if not eintrag:
        return ["Unbekanntes Kabelteil „%s“." % art]
    p = dict(eintrag["standard"])
    p.update(params or {})
    fehler: list[str] = []
    felder = PROFIL_FELDER if art == "deckel" else eintrag["felder"]
    for feld in felder:
        if "auswahl" in feld:
            werte = {a["wert"] for a in feld["auswahl"]}
            if str(p.get(feld["key"])) not in werte:
                fehler.append("%s: bitte eine der Vorgaben wählen." % feld["label"])
            continue
        wert = _zahl(p, feld["key"], fehler, feld["label"])
        if wert is None:
            continue
        _bereich(wert, feld, fehler)
    if fehler:
        return fehler
    _wand_ok(float(p["wand_mm"]), fehler)
    if art == "kanal" and float(p["laenge_mm"]) < float(p["zapfen_mm"]) + 8.0 - 1e-6:
        fehler.append(
            "Die Nutzlänge %s mm ist zu kurz für die Einstecktiefe von %s mm."
            % (_fmt(float(p["laenge_mm"])), _fmt(float(p["zapfen_mm"])))
        )
    if art == "auslass":
        loch = float(p["auslass_mm"])
        if loch > float(p["innenbreite_mm"]) - 2.4:
            fehler.append(
                "Das Loch %s mm lässt weniger als 1,2 mm Rand in der %s mm breiten Rinne."
                % (_fmt(loch), _fmt(float(p["innenbreite_mm"])))
            )
        if float(p["laenge_mm"]) < loch + float(p["zapfen_mm"]) + 4.0:
            fehler.append("Die Nutzlänge ist zu kurz für das Bodenloch und den Stecker.")
    if art == "ecke":
        ow, _oh = aussen_u(p)
        mindest = float(p["zapfen_mm"]) + ow / 2.0 + 8.0
        if float(p["schenkel_mm"]) < mindest - 1e-6:
            fehler.append(
                "Der Schenkel %s mm ist zu kurz. Mindestens %s mm, damit der Stecker frei aus der Ecke kommt."
                % (_fmt(float(p["schenkel_mm"])), _fmt(round(mindest, 1)))
            )
    if art == "halter":
        if float(p["loch_mm"]) > FLANSCH - 2.0 * WAND_MIN:
            fehler.append("Das Schraubenloch ist zu groß für die Lasche. Mindestens 1,2 mm Rand lassen.")
    aussen = masse(art, {**p, "art": art})
    if aussen:
        for name, wert in zip(("Länge", "Breite", "Höhe"), aussen):
            if wert > BAURAUM_MM + 1e-6:
                fehler.append("%s %s mm passt nicht in den Bauraum von 256 mm." % (name, _fmt(round(wert, 1))))
    return fehler


def profil_unterschiede(a: dict, b: dict) -> list[str]:
    namen = {
        "innenbreite_mm": "Innenbreite",
        "innenhoehe_mm": "Innenhöhe",
        "wand_mm": "Wandstärke",
        "spiel_mm": "Spiel",
        "zapfen_mm": "Einstecktiefe",
    }
    pa = a.get("parameter") or a
    pb = b.get("parameter") or b
    meldungen = []
    for key, name in namen.items():
        try:
            links = float(pa[key])
            rechts = float(pb[key])
        except (KeyError, TypeError, ValueError):
            meldungen.append("Die Teile passen nicht zusammen. %s fehlt an einem Teil." % name)
            continue
        if abs(links - rechts) > 0.011:
            meldungen.append(
                "Die Teile passen nicht zusammen. %s ist %s mm und %s mm."
                % (name, _fmt(links), _fmt(rechts))
            )
    return meldungen


def system_meldungen(teile: list) -> list[str]:
    fehler = []
    if not teile:
        return ["Noch kein Kabelteil ausgewählt."]
    for teil in teile:
        name = teil.get("name") or teil.get("art")
        for meldung in pruefe(teil.get("art"), teil.get("parameter") or {}):
            fehler.append("%s: %s" % (name, meldung))
    for index, links in enumerate(teile):
        for rechts in teile[index + 1 :]:
            for meldung in profil_unterschiede(links, rechts):
                fehler.append(
                    "%s und %s: %s" % (links.get("name") or links.get("art"), rechts.get("name") or rechts.get("art"), meldung)
                )
    return fehler


def teil_anlegen(art: str, parameter: dict | None = None, name: str | None = None, id_: str = "K1") -> dict:
    eintrag = katalog_nach_id(art)
    if not eintrag:
        raise ValueError("Unbekanntes Kabelteil.")
    werte = standard_parameter(art)
    werte.update(parameter or {})
    return {"id": id_, "art": art, "name": name or eintrag["name"], "parameter": werte}


def stuecke(teil: dict) -> list[dict]:
    """Ein Projektteil wird zu einem oder mehreren Druckteilen (Segmente, Deckel)."""
    art = teil.get("art")
    params = dict(teil.get("parameter") or {})
    params["art"] = art
    basis = str(teil.get("id") or "K")
    name = teil.get("name") or art
    if art != "kanal":
        soll = masse(art, params)
        return [{"id": basis, "art": art, "name": name, "params": params, "soll": soll}]
    laengen = nutzlaengen(params)
    ausgabe = []
    for index, nutz in enumerate(laengen, 1):
        stueck_id = basis if len(laengen) == 1 else "%s_%d" % (basis, index)
        segment = dict(params)
        segment["nutz_mm"] = nutz
        segment["laenge_mm"] = nutz
        segment["art"] = "kanal"
        segment["deckel"] = "nein"
        titel = name if len(laengen) == 1 else "%s %d" % (name, index)
        ausgabe.append({"id": stueck_id, "art": "kanal", "name": titel, "params": segment, "soll": masse("kanal", segment)})
        if str(params.get("deckel")) == "ja":
            deckel = dict(segment)
            deckel["art"] = "deckel"
            ausgabe.append(
                {
                    "id": stueck_id + "_deckel",
                    "art": "deckel",
                    "name": "Deckel %s" % titel,
                    "params": deckel,
                    "soll": masse("deckel", deckel),
                }
            )
    return ausgabe
