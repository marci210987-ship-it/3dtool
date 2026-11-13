# -*- coding: utf-8 -*-
"""Automatische Bestückung: Wunschliste platzieren, freie Rasterzellen füllen.

Einfaches, vorhersehbares Verfahren (kein Optimierer):

1. Wünsche (Sorte und Anzahl) werden nach Fläche absteigend gesetzt. Für jede Box
   wird unter allen freien Stellen (auch um 90° gedreht) die mit dem meisten
   Kontakt zu Schubladenwand, anderen Boxen und eigenen Teilen gewählt. So
   rücken Wünsche in Ecken und aneinander statt Lücken zu reißen; bei
   Gleichstand gewinnt die erste Stelle von vorne links.
2. Danach werden die übrigen freien Zellen zeilenweise gefüllt. Füllstil:
   ``einheitlich`` (Standard) wählt die Zielgröße mit den geringsten Kosten
   (Anzahl Boxen plus 4 je verschiedener Größe), also wenige, einheitliche, große
   Boxen; ``gross`` nimmt überall die größtmögliche Box;
   ``klein`` setzt lauter 1 × 1 Boxen.

Vorhandene Boxen bleiben unverändert, Felder unter platzierten eigenen Teilen
bleiben frei.
"""

from __future__ import annotations

from sidecar.eigenteil import eigenteil_rechteck_mm
from sidecar.layout import (
    Box,
    Projekt,
    Schublade,
    _rechtecke_schneiden,
    box_rechteck_mm,
    footprint,
    layout_pruefen,
    neue_id,
    plan_berechnen,
    raster_ursprung_mm,
    benoetigte_hoehe_mm,
)
from hausraster_const import kasten_aussen, BAURAUM_X, BAURAUM_Y  # noqa: E402

STILE = ("einheitlich", "gross", "klein")

NAMEN = {
    (1, 1): "Kleine Box",
    (1, 2): "Schmale Box",
    (2, 1): "Schmale Box",
    (2, 2): "Mittlere Box",
}

# Gleiche Sorten wie der Katalog in der Oberfläche (ui/src/layout.ts).
SORTEN: dict[str, dict] = {
    "klein": {"name": "Kleine Box", "ex": 1, "ey": 1, "ez": 3},
    "schmal": {"name": "Schmale Box", "ex": 1, "ey": 2, "ez": 3},
    "mittel": {"name": "Mittlere Box", "ex": 2, "ey": 2, "ez": 3, "fach_x": 2, "fach_y": 2},
    "gross": {"name": "Große Box", "ex": 2, "ey": 3, "ez": 3},
    "besteckfach": {"name": "Besteckfach", "ex": 1, "ey": 4, "ez": 2, "fach_x": 1, "fach_y": 4},
    "deckel": {"name": "Box mit Deckel", "ex": 2, "ey": 2, "ez": 3, "deckel": True},
    "kabel": {"name": "Kabelbox", "ex": 3, "ey": 3, "ez": 4, "fach_x": 2, "fach_y": 2, "kabelkerben": True},
    "besteck": {"name": "Bestecksortierer", "ex": 6, "ey": 3, "ez": 4, "art": "besteck"},
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


def _box_fehler(box: Box, schublade: Schublade, plan) -> list[str]:
    """Prüft eine einzelne Box (Höhe, Bauraum, Besteck-Mindestmaße)."""
    fehler = layout_pruefen(Projekt(schublade=schublade, boxen=[box]), plan)["fehler"]
    # Die Lage im Raster wird erst bei der Platzsuche geprüft.
    return [f for f in fehler if "ragt aus dem Raster" not in f]


def _hoehe_ok(box: Box, schublade: Schublade) -> bool:
    return benoetigte_hoehe_mm(box, schublade.boden_platte_mm) <= float(schublade.nutzhoehe_mm) + 1e-6


def auto_bestuecken(
    projekt: Projekt,
    max_zellen: int = 3,
    ez: int | None = None,
    wuensche: list[dict] | None = None,
    rest_fuellen: bool = True,
    stil: str = "einheitlich",
) -> dict:
    """Ergänzt ``projekt.boxen``.

    ``wuensche``: Liste aus ``{"sorte": <Schlüssel aus SORTEN>, "anzahl": n}``.
    ``stil``: Füllstil für den Rest (siehe Modulbeschreibung).
    """
    plan = plan_berechnen(projekt.schublade)
    if plan.ungueltig or not plan.einheiten_x or not plan.einheiten_y:
        return {"ok": False, "fehler": ["Für diese Schublade lässt sich kein Raster bilden."], "neu": 0}
    if stil not in STILE:
        return {"ok": False, "fehler": ["Unbekannter Füllstil „%s“." % stil], "neu": 0}
    sch = projekt.schublade
    belegt = _belegt(projekt.boxen)
    ox, oy = raster_ursprung_mm(sch, plan)
    gesperrt = [r for r in (eigenteil_rechteck_mm(e) for e in projekt.eigene) if r is not None]
    nx, ny = plan.einheiten_x, plan.einheiten_y
    cache: dict[tuple, bool] = {}

    def statisch_ok(i: int, j: int, w: int, h: int, art: str = "raster") -> bool:
        """Im Raster und frei von platzierten eigenen Teilen (unabhängig von anderen Boxen)."""
        if i < 0 or j < 0 or i + w > nx or j + h > ny:
            return False
        if not gesperrt:
            return True
        schluessel = (i, j, w, h, art)
        if schluessel not in cache:
            rect = box_rechteck_mm(Box(id="probe", name="probe", x=i, y=j, ex=w, ey=h, art=art), ox, oy)
            cache[schluessel] = not any(_rechtecke_schneiden(rect, g) for g in gesperrt)
        return cache[schluessel]

    def frei(i: int, j: int, w: int, h: int, art: str = "raster", occ: set | None = None) -> bool:
        if not statisch_ok(i, j, w, h, art):
            return False
        belegung = belegt if occ is None else occ
        return not any((a, b) in belegung for a in range(i, i + w) for b in range(j, j + h))

    def belegen(box: Box) -> None:
        x, y, w, h = footprint(box)
        for a in range(x, x + w):
            for b in range(y, y + h):
                belegt.add((a, b))
        projekt.boxen.append(box)

    def kontakt(i: int, j: int, w: int, h: int) -> int:
        """Anzahl der Zellkanten, an denen die Box an Wand, Box oder gesperrtes Feld grenzt."""

        def besetzt(a: int, b: int) -> bool:
            return a < 0 or b < 0 or a >= nx or b >= ny or (a, b) in belegt or not statisch_ok(a, b, 1, 1)

        summe = 0
        for b in range(j, j + h):
            summe += besetzt(i - 1, b) + besetzt(i + w, b)
        for a in range(i, i + w):
            summe += besetzt(a, j - 1) + besetzt(a, j + h)
        return summe

    neu: list[Box] = []
    bericht: list[dict] = []
    hinweise: list[str] = []

    # ---- 1. Wünsche
    gewuenscht: list[tuple[str, dict]] = []
    for eintrag in wuensche or []:
        sorte = str(eintrag.get("sorte") or "")
        if sorte not in SORTEN:
            hinweise.append("Unbekannte Sorte „%s“ wurde übersprungen." % sorte)
            continue
        anzahl = max(0, min(int(eintrag.get("anzahl") or 0), 200))
        bericht.append({"sorte": sorte, "name": SORTEN[sorte]["name"], "gewuenscht": anzahl, "platziert": 0})
        gewuenscht.extend((sorte, SORTEN[sorte]) for _ in range(anzahl))
    gewuenscht.sort(key=lambda item: -(item[1]["ex"] * item[1]["ey"]))
    # Prüfung je Sorte einmal, mit Absenken der Höhe, wenn sie nicht passt
    geprueft: dict[str, tuple[dict | None, str]] = {}
    for sorte, vorlage in gewuenscht:
        if sorte in geprueft:
            continue
        werte = dict(vorlage)
        probe = Box(id="probe", name=werte["name"], x=0, y=0, **{k: v for k, v in werte.items() if k != "name"})
        while not _hoehe_ok(probe, sch) and probe.art == "raster" and probe.ez > 1:
            probe.ez -= 1
        fehler = _box_fehler(probe, sch, plan)
        if fehler:
            geprueft[sorte] = (None, fehler[0])
        else:
            werte["ez"] = probe.ez
            geprueft[sorte] = (werte, "")

    for sorte, vorlage in gewuenscht:
        werte, grund = geprueft[sorte]
        eintrag = next(b for b in bericht if b["sorte"] == sorte)
        if werte is None:
            eintrag.setdefault("grund", grund)
            continue
        beste: tuple[int, int, int, int, int] | None = None  # Kontakt, i, j, Drehung (Reihenfolge nur für Vergleich)
        for rotation in (0, 90):
            ex, ey = (werte["ex"], werte["ey"]) if rotation == 0 else (werte["ey"], werte["ex"])
            if rotation == 90 and ex == ey:
                continue
            for j in range(ny):
                for i in range(nx):
                    if not frei(i, j, ex, ey, werte.get("art", "raster")):
                        continue
                    punkte = kontakt(i, j, ex, ey)
                    # Mehr Kontakt gewinnt; bei Gleichstand bleibt die frühere Stelle (vorne links, ungedreht)
                    if beste is None or punkte > beste[0]:
                        beste = (punkte, i, j, rotation, 0)
        if beste is None:
            eintrag.setdefault("grund", "Kein freier Platz")
            continue
        _, i, j, rotation, _ = beste
        felder = {k: v for k, v in werte.items() if k != "name"}
        box = Box(id=neue_id("B"), name=werte["name"], x=i, y=j, rotation=rotation, **felder)
        belegen(box)
        neu.append(box)
        eintrag["platziert"] += 1

    # ---- 2. Rest füllen
    stufe = 3 if ez is None else int(ez)
    if rest_fuellen:
        max_zellen = 1 if stil == "klein" else max(1, min(int(max_zellen), _max_zellen_im_bauraum()))
        probe = Box(id="probe", name="probe", x=0, y=0, ex=1, ey=1, ez=stufe)
        while stufe > 1 and not _hoehe_ok(probe, sch):
            stufe -= 1
            probe.ez = stufe
        if not _hoehe_ok(probe, sch):
            if not neu:
                return {"ok": False, "fehler": ["Die Schublade ist zu niedrig für eine Box."], "neu": 0}
            hinweise.append("Zum Füllen ist die Schublade zu niedrig.")
        else:

            def simuliere(zielgroesse: tuple[int, int]) -> list[tuple[int, int, int, int]]:
                """Zeilenweise füllen: erst die Zielgröße, sonst die größte Box, die hineinpasst."""
                occ = set(belegt)
                boxen: list[tuple[int, int, int, int]] = []
                for j in range(ny):
                    for i in range(nx):
                        if (i, j) in occ or not statisch_ok(i, j, 1, 1):
                            continue
                        beste_groesse = (1, 1)
                        if frei(i, j, zielgroesse[0], zielgroesse[1], "raster", occ):
                            beste_groesse = zielgroesse
                        else:
                            for h in range(1, zielgroesse[1] + 1):
                                for w in range(1, zielgroesse[0] + 1):
                                    if w * h > beste_groesse[0] * beste_groesse[1] and frei(i, j, w, h, "raster", occ):
                                        beste_groesse = (w, h)
                        w, h = beste_groesse
                        for a in range(i, i + w):
                            for b in range(j, j + h):
                                occ.add((a, b))
                        boxen.append((i, j, w, h))
                return boxen

            if stil == "einheitlich":
                kandidaten = [(w, h) for h in range(1, max_zellen + 1) for w in range(1, max_zellen + 1)]
                ergebnisse = []
                for groesse in kandidaten:
                    plan_boxen = simuliere(groesse)
                    verschiedene = len({(w, h) for _, _, w, h in plan_boxen})
                    # Wenige Boxen (große Boxen) und wenige verschiedene Größen (einheitlicher Eindruck).
                    # Das glatteste Tiling mit schmalen Streifen verliert dadurch gegen größere Boxen.
                    kosten = len(plan_boxen) + 4 * verschiedene
                    ergebnisse.append((kosten, -groesse[0] * groesse[1], plan_boxen))
                fuell_plan = min(ergebnisse, key=lambda e: (e[0], e[1]))[2]
            else:
                fuell_plan = simuliere((max_zellen, max_zellen))

            for i, j, w, h in fuell_plan:
                name = NAMEN.get((w, h)) or ("Große Box" if w * h >= 6 else "Mittlere Box")
                box = Box(id=neue_id("B"), name=name, x=i, y=j, ex=w, ey=h, ez=stufe)
                belegen(box)
                neu.append(box)

    for eintrag in bericht:
        fehlt = eintrag["gewuenscht"] - eintrag["platziert"]
        if fehlt > 0:
            hinweise.append(
                "%s: %d von %d platziert (%s)."
                % (eintrag["name"], eintrag["platziert"], eintrag["gewuenscht"], eintrag.get("grund") or "Kein freier Platz")
            )
    return {"ok": True, "fehler": [], "neu": len(neu), "ez": stufe, "stil": stil, "wuensche": bericht, "hinweise": hinweise}
