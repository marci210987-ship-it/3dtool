# -*- coding: utf-8 -*-
"""Parametrische Ersatzteile: Prüfung und Sollmaße, ohne FreeCAD.

Die Körper baut sidecar.ersatzteil_geom in FreeCAD. Wandstärken sind auf eine
0,4-mm-Düse ausgelegt (mindestens 1,2 mm, also drei Linien). Der Bauraum ist
der P2S mit 256 mm. Passungen sind Vorgaben, keine Messwerte.
"""

from __future__ import annotations

BAURAUM_MM = 256.0
WAND_MIN = 1.2
DUESSE = 0.4

KATALOG = [
    {
        "id": "kabelclip",
        "name": "Kabelclip",
        "text": "Hält ein oder mehrere Kabel. Oben bleibt ein Spalt, das Kabel wird eingedrückt.",
        "druck": "Flach drucken, Öffnung nach oben. Keine Stützen nötig.",
        "standard": {"durchmesser_mm": 6.0, "anzahl": 1, "wand_mm": 1.2, "befestigung": "schraube"},
        "felder": [
            {"key": "durchmesser_mm", "label": "Kabeldurchmesser", "min": 3, "max": 25, "step": 0.5, "einheit": "mm"},
            {"key": "anzahl", "label": "Anzahl Kabel nebeneinander", "min": 1, "max": 6, "step": 1, "ganzzahl": True},
            {"key": "wand_mm", "label": "Wandstärke", "min": 1.2, "max": 2.4, "step": 0.4, "einheit": "mm"},
            {"key": "befestigung", "label": "Befestigung", "auswahl": [
                {"wert": "schraube", "text": "Lasche für eine M3-Schraube"},
                {"wert": "kleben", "text": "Nur Klebepad, ohne Loch"},
            ]},
        ],
    },
    {
        "id": "distanzhuelse",
        "name": "Distanzhülse",
        "text": "Rohr, das zwei Teile auf Abstand hält, zum Beispiel um eine Schraube.",
        "druck": "Hochkant stellen, Loch nach oben. So bleibt die Bohrung rund.",
        "standard": {"aussen_mm": 8.0, "innen_mm": 4.2, "laenge_mm": 10.0},
        "felder": [
            {"key": "aussen_mm", "label": "Außendurchmesser", "min": 4, "max": 40, "step": 0.1, "einheit": "mm"},
            {"key": "innen_mm", "label": "Bohrung", "min": 1.5, "max": 30, "step": 0.1, "einheit": "mm"},
            {"key": "laenge_mm", "label": "Länge", "min": 2, "max": 80, "step": 0.5, "einheit": "mm"},
        ],
    },
    {
        "id": "unterlegscheibe",
        "name": "Unterlegscheibe",
        "text": "Flache Scheibe unter einem Schraubenkopf.",
        "druck": "Flach auf das Druckbett legen.",
        "standard": {"aussen_mm": 12.0, "innen_mm": 4.5, "dicke_mm": 1.6},
        "felder": [
            {"key": "aussen_mm", "label": "Außendurchmesser", "min": 6, "max": 60, "step": 0.1, "einheit": "mm"},
            {"key": "innen_mm", "label": "Bohrung", "min": 2, "max": 40, "step": 0.1, "einheit": "mm"},
            {"key": "dicke_mm", "label": "Dicke", "min": 0.8, "max": 6, "step": 0.4, "einheit": "mm"},
        ],
    },
    {
        "id": "wandhaken",
        "name": "Wandhaken",
        "text": "Kleiner Haken mit Schraubenloch, zum Aufhängen von leichten Teilen.",
        "druck": "Flach drucken. Der Haken liegt in der Ebene, keine Stützen.",
        "standard": {"hoehe_mm": 40.0, "ausladung_mm": 22.0, "ruecken_mm": 8.0, "haken_mm": 4.0, "breite_mm": 16.0, "loch_mm": 4.2},
        "felder": [
            {"key": "hoehe_mm", "label": "Höhe der Rückwand", "min": 20, "max": 80, "step": 1, "einheit": "mm"},
            {"key": "ausladung_mm", "label": "Wie weit der Haken vorsteht", "min": 12, "max": 50, "step": 1, "einheit": "mm"},
            {"key": "breite_mm", "label": "Dicke des Hakens", "min": 6, "max": 30, "step": 1, "einheit": "mm"},
            {"key": "loch_mm", "label": "Schraubenloch", "min": 2, "max": 8, "step": 0.1, "einheit": "mm"},
        ],
    },
    {
        "id": "moebelfuss",
        "name": "Möbelfuß",
        "text": "Runder Gleiter mit Sackloch für eine Schraube von oben.",
        "druck": "Mit der großen Fläche auf das Bett, Loch nach oben.",
        "standard": {"durchmesser_mm": 20.0, "hoehe_mm": 8.0, "loch_mm": 4.2},
        "felder": [
            {"key": "durchmesser_mm", "label": "Durchmesser", "min": 10, "max": 50, "step": 1, "einheit": "mm"},
            {"key": "hoehe_mm", "label": "Höhe", "min": 4, "max": 25, "step": 0.5, "einheit": "mm"},
            {"key": "loch_mm", "label": "Schraubenloch", "min": 2, "max": 8, "step": 0.1, "einheit": "mm"},
        ],
    },
    {
        "id": "knopf",
        "name": "Drehknopf",
        "text": "Knopf für eine runde Welle oder eine Welle mit einer abgeflachten Seite (D).",
        "druck": "Loch nach unten auf das Bett. Die Bohrung bleibt dann offen und rund.",
        "standard": {"durchmesser_mm": 24.0, "hoehe_mm": 14.0, "welle_mm": 6.0, "wellenart": "rund", "tiefe_mm": 8.0},
        "felder": [
            {"key": "durchmesser_mm", "label": "Außendurchmesser", "min": 12, "max": 50, "step": 1, "einheit": "mm"},
            {"key": "hoehe_mm", "label": "Höhe", "min": 8, "max": 30, "step": 0.5, "einheit": "mm"},
            {"key": "welle_mm", "label": "Wellendurchmesser", "min": 3, "max": 12, "step": 0.1, "einheit": "mm"},
            {"key": "tiefe_mm", "label": "Tiefe der Bohrung", "min": 3, "max": 20, "step": 0.5, "einheit": "mm"},
            {"key": "wellenart", "label": "Welle", "auswahl": [
                {"wert": "rund", "text": "Rund"},
                {"wert": "d", "text": "Abgeflacht (D)"},
            ]},
        ],
    },
    {
        "id": "stopfen",
        "name": "Stopfen",
        "text": "Verschließt ein rundes Loch. Der Kragen liegt auf dem Rand auf.",
        "druck": "Kragen nach oben. Das Spiel von 0,3 mm ist eine Vorgabe, kein Messwert.",
        "standard": {"loch_mm": 10.0, "tiefe_mm": 6.0, "spiel_mm": 0.3, "kragen_mm": 2.0},
        "felder": [
            {"key": "loch_mm", "label": "Loch, das verschlossen wird", "min": 4, "max": 40, "step": 0.5, "einheit": "mm"},
            {"key": "tiefe_mm", "label": "Wie tief er hineingeht", "min": 2, "max": 20, "step": 0.5, "einheit": "mm"},
            {"key": "spiel_mm", "label": "Spiel zum Loch", "min": 0, "max": 1, "step": 0.1, "einheit": "mm"},
            {"key": "kragen_mm", "label": "Kragen über den Rand", "min": 1.2, "max": 6, "step": 0.2, "einheit": "mm"},
        ],
    },
    {
        "id": "winkel",
        "name": "Winkel",
        "text": "L-förmiges Verbindungsstück mit einem Schraubenloch je Schenkel.",
        "druck": "Einen Schenkel flach auf das Bett. Der andere steht senkrecht, ohne Stütze.",
        "standard": {"laenge_mm": 30.0, "hoehe_mm": 30.0, "breite_mm": 16.0, "dicke_mm": 4.0, "loch_mm": 4.2},
        "felder": [
            {"key": "laenge_mm", "label": "Länge des liegenden Schenkels", "min": 16, "max": 80, "step": 1, "einheit": "mm"},
            {"key": "hoehe_mm", "label": "Höhe des stehenden Schenkels", "min": 16, "max": 80, "step": 1, "einheit": "mm"},
            {"key": "breite_mm", "label": "Breite", "min": 10, "max": 40, "step": 1, "einheit": "mm"},
            {"key": "dicke_mm", "label": "Materialstärke", "min": 2.4, "max": 8, "step": 0.4, "einheit": "mm"},
            {"key": "loch_mm", "label": "Schraubenloch", "min": 2, "max": 8, "step": 0.1, "einheit": "mm"},
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


def _wand_ok(wand: float, fehler: list[str], name: str = "Wandstärke") -> None:
    if wand < WAND_MIN - 1e-6:
        fehler.append(
            "%s %.2f mm ist zu dünn. Für eine 0,4-mm-Düse mindestens %.1f mm (drei Linien)."
            % (name, wand, WAND_MIN)
        )
    stufen = round(wand / DUESSE)
    if abs(wand - stufen * DUESSE) > 0.05:
        fehler.append(
            "%s %.2f mm ist kein Vielfaches von 0,4 mm. Sinnvoll sind 1,2 / 1,6 / 2,0 / 2,4."
            % (name, wand)
        )


def _passt(masse: tuple[float, float, float], fehler: list[str]) -> None:
    namen = ("Breite", "Tiefe", "Höhe")
    for name, wert in zip(namen, masse):
        if wert > BAURAUM_MM + 1e-6:
            fehler.append("%s %.1f mm passt nicht in den Bauraum von 256 mm." % (name, wert))


def masse(art: str, params: dict) -> tuple[float, float, float] | None:
    """Außenmaß in mm (X, Y, Z), oder None wenn die Zahlen fehlen."""
    p = params or {}
    if art == "kabelclip":
        d = p.get("durchmesser_mm")
        n = p.get("anzahl")
        wand = p.get("wand_mm", 1.2)
        if d is None or n is None:
            return None
        d, n, wand = float(d), int(float(n)), float(wand)
        rand, spalt, breite, boden = 3.0, 2.0, 14.0, 1.6
        laenge = rand + n * (d + 2 * wand) + max(0, n - 1) * spalt + rand
        if str(p.get("befestigung") or "schraube") == "schraube":
            laenge += 12.0
        return (breite, laenge, boden + d / 2.0 + wand)
    if art == "distanzhuelse":
        if p.get("aussen_mm") is None or p.get("laenge_mm") is None:
            return None
        aussen, laenge = float(p["aussen_mm"]), float(p["laenge_mm"])
        return (aussen, aussen, laenge)
    if art == "unterlegscheibe":
        if p.get("aussen_mm") is None or p.get("dicke_mm") is None:
            return None
        aussen, dicke = float(p["aussen_mm"]), float(p["dicke_mm"])
        return (aussen, aussen, dicke)
    if art == "wandhaken":
        if None in (p.get("ausladung_mm"), p.get("hoehe_mm"), p.get("breite_mm")):
            return None
        return (float(p["ausladung_mm"]), float(p["hoehe_mm"]), float(p["breite_mm"]))
    if art == "moebelfuss":
        if p.get("durchmesser_mm") is None or p.get("hoehe_mm") is None:
            return None
        d, h = float(p["durchmesser_mm"]), float(p["hoehe_mm"])
        return (d, d, h)
    if art == "knopf":
        if p.get("durchmesser_mm") is None or p.get("hoehe_mm") is None:
            return None
        d, h = float(p["durchmesser_mm"]), float(p["hoehe_mm"])
        return (d, d, h)
    if art == "stopfen":
        if None in (p.get("loch_mm"), p.get("tiefe_mm"), p.get("spiel_mm"), p.get("kragen_mm")):
            return None
        loch, tiefe = float(p["loch_mm"]), float(p["tiefe_mm"])
        spiel, kragen = float(p["spiel_mm"]), float(p["kragen_mm"])
        aussen = loch - 2 * spiel + 2 * kragen
        return (aussen, aussen, tiefe + 1.6)
    if art == "winkel":
        if None in (p.get("laenge_mm"), p.get("breite_mm"), p.get("hoehe_mm")):
            return None
        return (float(p["laenge_mm"]), float(p["breite_mm"]), float(p["hoehe_mm"]))
    return None


def pruefe(art: str, params: dict) -> list[str]:
    """Leere Liste = die Parameter sind druckbar."""
    eintrag = katalog_nach_id(art)
    if not eintrag:
        return ["Unbekanntes Ersatzteil „%s“." % art]
    p = dict(eintrag["standard"])
    p.update(params or {})
    fehler: list[str] = []
    for feld in eintrag["felder"]:
        if "auswahl" in feld:
            werte = {a["wert"] for a in feld["auswahl"]}
            if str(p.get(feld["key"])) not in werte:
                fehler.append("%s: bitte eine der Vorgaben wählen." % feld["label"])
            continue
        wert = _zahl(p, feld["key"], fehler, feld["label"])
        if wert is None:
            continue
        if feld.get("ganzzahl") and abs(wert - round(wert)) > 1e-6:
            fehler.append("%s muss eine ganze Zahl sein." % feld["label"])
        if wert < float(feld["min"]) - 1e-6 or wert > float(feld["max"]) + 1e-6:
            fehler.append(
                "%s %s liegt außerhalb von %s bis %s%s."
                % (
                    feld["label"],
                    ("%g" % wert),
                    feld["min"],
                    feld["max"],
                    (" " + feld["einheit"]) if feld.get("einheit") else "",
                )
            )
    if fehler:
        return fehler
    if art == "kabelclip":
        _wand_ok(float(p["wand_mm"]), fehler)
    elif art == "distanzhuelse":
        rand = (float(p["aussen_mm"]) - float(p["innen_mm"])) / 2.0
        if rand < WAND_MIN - 1e-6:
            fehler.append(
                "Die Wand der Hülse ist nur %.2f mm. Mindestens %.1f mm für eine 0,4-mm-Düse."
                % (rand, WAND_MIN)
            )
    elif art == "unterlegscheibe":
        rand = (float(p["aussen_mm"]) - float(p["innen_mm"])) / 2.0
        if rand < WAND_MIN - 1e-6:
            fehler.append(
                "Der Rand der Scheibe ist nur %.2f mm. Mindestens %.1f mm lassen." % (rand, WAND_MIN)
            )
        if abs(float(p["dicke_mm"]) / DUESSE - round(float(p["dicke_mm"]) / DUESSE)) > 0.05:
            fehler.append("Die Dicke soll ein Vielfaches von 0,4 mm sein, zum Beispiel 0,8 oder 1,6.")
    elif art == "wandhaken":
        ruecken = float(eintrag["standard"]["ruecken_mm"])
        if float(p["loch_mm"]) > ruecken - 2 * WAND_MIN:
            fehler.append(
                "Das Schraubenloch %.1f mm ist zu groß für den %g mm dicken Rücken. Mindestens %.1f mm Material je Seite lassen."
                % (float(p["loch_mm"]), ruecken, WAND_MIN)
            )
        if float(p["ausladung_mm"]) <= ruecken + float(eintrag["standard"]["haken_mm"]):
            fehler.append("Der Haken steht nicht weit genug vor, um etwas aufzunehmen.")
    elif art == "moebelfuss":
        if float(p["loch_mm"]) > float(p["durchmesser_mm"]) - 2 * WAND_MIN:
            fehler.append("Das Schraubenloch lässt weniger als 1,2 mm Rand. Durchmesser erhöhen oder Loch verkleinern.")
        if float(p["hoehe_mm"]) < 1.6 + 2.0:
            fehler.append("Der Fuß ist zu niedrig für ein Sackloch mit geschlossenem Boden.")
    elif art == "knopf":
        if float(p["welle_mm"]) > float(p["durchmesser_mm"]) - 2 * WAND_MIN:
            fehler.append("Die Welle ist zu dick für diesen Knopf. Mindestens 1,2 mm Wand lassen.")
        if float(p["tiefe_mm"]) > float(p["hoehe_mm"]) - 1.6:
            fehler.append("Die Bohrung geht durch den Knopf. Mindestens 1,6 mm Deckel stehen lassen.")
    elif art == "stopfen":
        stecker = float(p["loch_mm"]) - 2 * float(p["spiel_mm"])
        if stecker < 2.0:
            fehler.append("Mit diesem Spiel bleibt vom Stopfen zu wenig übrig.")
        _wand_ok(float(p["kragen_mm"]), fehler, "Kragen")
    elif art == "winkel":
        _wand_ok(float(p["dicke_mm"]), fehler, "Materialstärke")
        if float(p["loch_mm"]) > float(p["breite_mm"]) - 2 * WAND_MIN:
            fehler.append("Das Schraubenloch ist breiter als der Schenkel erlaubt. Mindestens 1,2 mm Rand je Seite.")
        if float(p["loch_mm"]) > float(p["dicke_mm"]) + 2:
            # durch die Materialstärke ist ein größeres Loch in Ordnung, solange es in der Breite passt
            pass
        if float(p["laenge_mm"]) < float(p["dicke_mm"]) + float(p["loch_mm"]) + 2 * WAND_MIN:
            fehler.append("Der liegende Schenkel ist zu kurz für Loch und Ecke.")
        if float(p["hoehe_mm"]) < float(p["dicke_mm"]) + float(p["loch_mm"]) + 2 * WAND_MIN:
            fehler.append("Der stehende Schenkel ist zu kurz für Loch und Ecke.")
    aussen = masse(art, p)
    if aussen:
        _passt(aussen, fehler)
    return fehler


def teil_anlegen(art: str, parameter: dict | None = None, name: str | None = None, id_: str = "ET1") -> dict:
    eintrag = katalog_nach_id(art)
    if not eintrag:
        raise ValueError("Unbekanntes Ersatzteil.")
    werte = standard_parameter(art)
    werte.update(parameter or {})
    return {
        "id": id_,
        "art": art,
        "name": name or eintrag["name"],
        "parameter": werte,
    }
