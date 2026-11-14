# -*- coding: utf-8 -*-
"""Automatische Bestückung: Wunschliste platzieren, freie Rasterzellen füllen.

Verfahren:

1. Wünsche (Sorte, Anzahl, optional Seite und Gruppe) werden nach Fläche absteigend
   gesetzt. Jede Box bekommt Punkte für Kontakt zu Schubladenwand, anderen Boxen und
   eigenen Teilen, für die gewünschte Seite (links, rechts, vorne, hinten) und für
   die Nähe zu Boxen derselben Gruppe. Eine Strahlsuche verfolgt mehrere gute
   Zwischenstände statt nur dem ersten; unter gleich guten Endständen gewinnt der,
   dessen Rest sich besser füllen lässt. Die gierige Wahl bleibt immer im Rennen.
2. Danach werden die übrigen freien Zellen zeilenweise gefüllt. Füllstil:
   ``einheitlich`` (Standard) wählt die Zielgröße mit den geringsten Kosten
   (Anzahl Boxen plus 4 je verschiedener Größe), also wenige, einheitliche, große
   Boxen; ``gross`` nimmt überall die größtmögliche Box;
   ``klein`` setzt lauter 1 × 1 Boxen. Beim Stil ``einheitlich`` sucht ein Verzweigen
   und Beschneiden (feste Knotenzahl) nach einer Aufteilung mit geringeren Kosten und
   ersetzt das Zeilenverfahren nur, wenn sie echt besser ist.

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
SEITEN = ("egal", "links", "rechts", "vorne", "hinten")

# Einstellungen der Suche (feste Werte, damit gleiche Eingaben gleiche Ergebnisse liefern)
STRAHL_BREITE = 12  # Zwischenstände, die nach jedem Wunsch weiterverfolgt werden
STRAHL_KANDIDATEN = 6  # beste Stellen je Zwischenstand
FINALISTEN = 4  # so viele Endstände werden nach der Füllqualität verglichen
KNOTEN_LIMIT = 120000  # Obergrenze der Suchschritte beim Verbessern der Füllung
SEITEN_GEWICHT = 6.0  # Punkte für „ganz links“ usw.
GRUPPEN_GEWICHT = 2.0  # Punkte je Zellkante zur gleichen Gruppe
FUELL_GEWICHT = 2.0  # Abzug je Fülkosten-Punkt beim Vergleich der Endstände

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

    ``wuensche``: Liste aus ``{"sorte": <Schlüssel aus SORTEN>, "anzahl": n, "seite": egal|links|rechts|vorne|hinten, "gruppe": Text}``
    (Seite und Gruppe sind optional).
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

    def kontakt(i: int, j: int, w: int, h: int, occ: set | None = None) -> int:
        """Anzahl der Zellkanten, an denen die Box an Wand, Box oder gesperrtes Feld grenzt."""
        belegung = belegt if occ is None else occ

        def besetzt(a: int, b: int) -> bool:
            return a < 0 or b < 0 or a >= nx or b >= ny or (a, b) in belegung or not statisch_ok(a, b, 1, 1)

        summe = 0
        for b in range(j, j + h):
            summe += besetzt(i - 1, b) + besetzt(i + w, b)
        for a in range(i, i + w):
            summe += besetzt(a, j - 1) + besetzt(a, j + h)
        return summe

    neu: list[Box] = []
    bericht: list[dict] = []
    hinweise: list[str] = []

    # ---- 1. Wünsche vorbereiten
    gewuenscht: list[tuple[str, dict, str, str]] = []  # Sorte, Werte, Seite, Gruppe
    for eintrag in wuensche or []:
        sorte = str(eintrag.get("sorte") or "")
        if sorte not in SORTEN:
            hinweise.append("Unbekannte Sorte „%s“ wurde übersprungen." % sorte)
            continue
        anzahl = max(0, min(int(eintrag.get("anzahl") or 0), 200))
        seite = str(eintrag.get("seite") or "egal")
        if seite not in SEITEN:
            hinweise.append("Unbekannte Seite „%s“ bei %s wurde ignoriert." % (seite, SORTEN[sorte]["name"]))
            seite = "egal"
        gruppe = str(eintrag.get("gruppe") or "")[:12]
        bericht.append({"sorte": sorte, "name": SORTEN[sorte]["name"], "gewuenscht": anzahl, "platziert": 0, "seite": seite, "gruppe": gruppe})
        gewuenscht.extend((sorte, SORTEN[sorte], seite, gruppe) for _ in range(anzahl))
    # Große Boxen zuerst; bei gleicher Fläche bleiben die Wünsche in der Reihenfolge der Eingabe
    gewuenscht.sort(key=lambda item: -(item[1]["ex"] * item[1]["ey"]))
    # Prüfung je Sorte einmal, mit Absenken der Höhe, wenn sie nicht passt
    geprueft: dict[str, tuple[dict | None, str]] = {}
    for sorte, vorlage, _seite, _gruppe in gewuenscht:
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

    # ---- Füllplanung (Rest): Zeilenverfahren je Zielgröße, danach Verbesserung durch Suche
    stufe = 3 if ez is None else int(ez)
    max_zellen = 1 if stil == "klein" else max(1, min(int(max_zellen), _max_zellen_im_bauraum()))
    fuell_moeglich = False
    if rest_fuellen:
        probe_box = Box(id="probe", name="probe", x=0, y=0, ex=1, ey=1, ez=stufe)
        while stufe > 1 and not _hoehe_ok(probe_box, sch):
            stufe -= 1
            probe_box.ez = stufe
        fuell_moeglich = _hoehe_ok(probe_box, sch)

    def simuliere(zielgroesse: tuple[int, int], occ0: set) -> list[tuple[int, int, int, int]]:
        """Zeilenweise füllen: erst die Zielgröße, sonst die größte Box, die hineinpasst."""
        occ = set(occ0)
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

    def fuellkosten(plan_boxen) -> int:
        # Wenige Boxen (große Boxen) und wenige verschiedene Größen (einheitlicher Eindruck).
        return len(plan_boxen) + 4 * len({(w, h) for _, _, w, h in plan_boxen})

    def fuellplan(occ0: set) -> list[tuple[int, int, int, int]]:
        if stil == "einheitlich":
            kandidaten = [(w, h) for h in range(1, max_zellen + 1) for w in range(1, max_zellen + 1)]
            ergebnisse = []
            for groesse in kandidaten:
                plan_boxen = simuliere(groesse, occ0)
                ergebnisse.append((fuellkosten(plan_boxen), -groesse[0] * groesse[1], plan_boxen))
            return min(ergebnisse, key=lambda e: (e[0], e[1]))[2]
        return simuliere((max_zellen, max_zellen), occ0)

    def verbessern(occ0: set, start: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
        """Verzweigen und Beschneiden über alle Rechtecke bis max_zellen. Beginnt beim Zeilenverfahren und ersetzt es
        nur durch eine echt bessere Aufteilung. Die Knotenzahl ist begrenzt, damit das Ergebnis reproduzierbar bleibt."""
        zellen = [(i, j) for j in range(ny) for i in range(nx) if (i, j) not in occ0 and statisch_ok(i, j, 1, 1)]
        if not zellen or len(zellen) > 150:
            return start
        beste = {"kosten": fuellkosten(start), "plan": start}
        knoten = [0]
        occ = set(occ0)
        folge: list[tuple[int, int, int, int]] = []
        groessen: dict[tuple[int, int], int] = {}
        flaeche_max = max_zellen * max_zellen
        rechtecke = sorted(((w, h) for w in range(1, max_zellen + 1) for h in range(1, max_zellen + 1)), key=lambda g: (-g[0] * g[1], -g[0]))

        def suche(start_index: int, offen: int) -> None:
            if knoten[0] >= KNOTEN_LIMIT:
                return
            knoten[0] += 1
            k = start_index
            while k < len(zellen) and zellen[k] in occ:
                k += 1
            if k >= len(zellen):
                kosten = len(folge) + 4 * len(groessen)
                if kosten < beste["kosten"]:
                    beste["kosten"], beste["plan"] = kosten, list(folge)
                return
            untergrenze = len(folge) + -(-offen // flaeche_max) + 4 * max(len(groessen), 1)
            if untergrenze >= beste["kosten"]:
                return
            i, j = zellen[k]
            for w, h in rechtecke:
                if not frei(i, j, w, h, "raster", occ):
                    continue
                for a in range(i, i + w):
                    for b in range(j, j + h):
                        occ.add((a, b))
                folge.append((i, j, w, h))
                groessen[(w, h)] = groessen.get((w, h), 0) + 1
                suche(k + 1, offen - w * h)
                groessen[(w, h)] -= 1
                if not groessen[(w, h)]:
                    del groessen[(w, h)]
                folge.pop()
                for a in range(i, i + w):
                    for b in range(j, j + h):
                        occ.discard((a, b))

        suche(0, len(zellen))
        return beste["plan"]

    # ---- 2. Wünsche platzieren (Strahlsuche: mehrere gute Zwischenstände statt nur dem ersten)
    def seitenbonus(seite: str, i: int, j: int, w: int, h: int) -> float:
        cx = (i + w / 2.0) / nx
        cy = (j + h / 2.0) / ny
        if seite == "links":
            return SEITEN_GEWICHT * (1.0 - cx)
        if seite == "rechts":
            return SEITEN_GEWICHT * cx
        if seite == "vorne":
            return SEITEN_GEWICHT * (1.0 - cy)
        if seite == "hinten":
            return SEITEN_GEWICHT * cy
        return 0.0

    def gruppenbonus(zellen: frozenset, i: int, j: int, w: int, h: int) -> float:
        if not zellen:
            return 0.0
        n = 0
        for b in range(j, j + h):
            n += ((i - 1, b) in zellen) + ((i + w, b) in zellen)
        for a in range(i, i + w):
            n += ((a, j - 1) in zellen) + ((a, j + h) in zellen)
        return GRUPPEN_GEWICHT * n

    breite_strahl = STRAHL_BREITE if len(gewuenscht) <= 60 else 2
    # Zustand: (Punkte, Zahl platzierter Wünsche, Platzierungen, belegte Zellen, Zellen je Gruppe)
    zustaende: list[tuple[float, int, tuple, frozenset, dict]] = [(0.0, 0, (), frozenset(belegt), {})]
    for index, (sorte, _vorlage, seite, gruppe) in enumerate(gewuenscht):
        werte, _grund = geprueft[sorte]
        if werte is None:
            zustaende = [(p, n, plat + (None,), occ, grp) for p, n, plat, occ, grp in zustaende]
            continue
        art = werte.get("art", "raster")
        folgende = []
        for punkte, anzahl_platziert, plat, occ, grp in zustaende:
            occ_set = set(occ)
            kand = []
            for rotation in (0, 90):
                ex, ey = (werte["ex"], werte["ey"]) if rotation == 0 else (werte["ey"], werte["ex"])
                if rotation == 90 and ex == ey:
                    continue
                for j in range(ny):
                    for i in range(nx):
                        if not frei(i, j, ex, ey, art, occ_set):
                            continue
                        wert = kontakt(i, j, ex, ey, occ_set) + seitenbonus(seite, i, j, ex, ey)
                        if gruppe:
                            wert += gruppenbonus(grp.get(gruppe, frozenset()), i, j, ex, ey)
                        kand.append((-wert, rotation, j, i, ex, ey))
            if not kand:
                folgende.append((punkte, anzahl_platziert, plat + (None,), occ, grp))
                continue
            kand.sort()
            for negwert, rotation, j, i, ex, ey in kand[:STRAHL_KANDIDATEN]:
                zellen = frozenset((a, b) for a in range(i, i + ex) for b in range(j, j + ey))
                neu_grp = grp
                if gruppe:
                    neu_grp = dict(grp)
                    neu_grp[gruppe] = grp.get(gruppe, frozenset()) | zellen
                folgende.append((punkte - negwert, anzahl_platziert + 1, plat + ((index, i, j, rotation),), occ | zellen, neu_grp))
        # Mehr platzierte Wünsche, dann mehr Punkte; bei Gleichstand bleibt die frühere (gierige) Reihenfolge
        folgende.sort(key=lambda z: (-z[1], -z[0]))
        zustaende = folgende[:breite_strahl]

    if gewuenscht:
        beste_zahl = max(z[1] for z in zustaende)
        finalisten = [z for z in zustaende if z[1] == beste_zahl][:FINALISTEN]
        wahl = finalisten[0]
        if len(finalisten) > 1 and fuell_moeglich:
            # Zwischen gleich guten Ständen entscheidet, wie gut sich der Rest füllen lässt
            bewertung = []
            for z in finalisten:
                bewertung.append((z[0] - FUELL_GEWICHT * fuellkosten(fuellplan(set(z[3]))), z))
            wahl = max(bewertung, key=lambda e: e[0])[1]
        for eintrag_plat in wahl[2]:
            if eintrag_plat is None:
                continue
            index, i, j, rotation = eintrag_plat
            sorte = gewuenscht[index][0]
            werte = geprueft[sorte][0]
            felder = {k: v for k, v in werte.items() if k != "name"}
            box = Box(id=neue_id("B"), name=werte["name"], x=i, y=j, rotation=rotation, **felder)
            belegen(box)
            neu.append(box)
            next(b for b in bericht if b["sorte"] == sorte)["platziert"] += 1
    for sorte, (werte, grund) in geprueft.items():
        if werte is None:
            next(b for b in bericht if b["sorte"] == sorte).setdefault("grund", grund)
    for b in bericht:
        if b["platziert"] < b["gewuenscht"] and "grund" not in b:
            b["grund"] = "Kein freier Platz"

    # ---- 3. Rest füllen
    optimierung = None
    if rest_fuellen:
        if not fuell_moeglich:
            if not neu:
                return {"ok": False, "fehler": ["Die Schublade ist zu niedrig für eine Box."], "neu": 0}
            hinweise.append("Zum Füllen ist die Schublade zu niedrig.")
        else:
            fuell_plan = fuellplan(set(belegt))
            if stil == "einheitlich":
                vorher = fuellkosten(fuell_plan)
                fuell_plan = verbessern(set(belegt), fuell_plan)
                nachher = fuellkosten(fuell_plan)
                optimierung = {"kosten_vorher": vorher, "kosten_nachher": nachher}
                if nachher < vorher:
                    hinweise.append("Optimierung: Die Aufteilung des Rests ist besser als beim Zeilenverfahren (Kosten %d statt %d)." % (nachher, vorher))
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
    return {"ok": True, "fehler": [], "neu": len(neu), "ez": stufe, "stil": stil, "wuensche": bericht, "hinweise": hinweise, "optimierung": optimierung}
