# -*- coding: utf-8 -*-
"""Schubladenplaner für Hausraster-Grundplatten."""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict, field

from hausraster_const import (
    RASTER_MM,
    BAURAUM_X,
    BAURAUM_Y,
    SCHUBLADENSPIEL_STANDARD,
    max_einheiten_je_seite,
    plattenhoehe,
    BODEN_PLATTE_STANDARD,
)


@dataclass
class Plattenzuschnitt:
    einheiten_x: int
    einheiten_y: int
    rand_x_links: float
    rand_x_rechts: float
    rand_y_vorne: float
    rand_y_hinten: float
    pos_einheit_x: int  # Startindex im Gesamtraster, 0-basiert
    pos_einheit_y: int
    breite_mm: float
    tiefe_mm: float
    passt_in_bauraum: bool
    muss_geteilt_werden: bool
    hinweis: str = ""


@dataclass
class Randstreifen:
    seite: str  # links, rechts, vorne, hinten
    laenge_mm: float
    breite_mm: float
    teile: int
    hinweis: str = ""


@dataclass
class Schubladenplan:
    schublade_x: float
    schublade_y: float
    spiel_je_seite: float
    nutz_x: float
    nutz_y: float
    raster_mm: float
    einheiten_x: int
    einheiten_y: int
    rest_x: float
    rest_y: float
    platten: list
    anzahl_platten: int
    randstreifen: list
    plattenhoehe_mm: float
    bauraum: tuple
    hinweise: list = field(default_factory=list)
    ungueltig: bool = False

    def to_dict(self):
        d = asdict(self)
        return d


def _teile_einheiten(n: int, max_u: int) -> list[int]:
    if n <= 0:
        return []
    if n <= max_u:
        return [n]
    n_teile = math.ceil(n / max_u)
    basis = n // n_teile
    extra = n % n_teile
    # extra auf die ersten Teile, typischerweise die kleineren aussen
    teile = [basis + (1 if i >= n_teile - extra else 0) for i in range(n_teile)]
    # Falls irgendetwas 0 wäre (sollte nicht), neu verteilen
    teile = [t for t in teile if t > 0]
    assert sum(teile) == n
    assert all(t <= max_u for t in teile)
    return teile


def _verteile_rest_auf_aussen(
    teile: list[int],
    rest: float,
    raster: float,
    bauraum: float,
) -> tuple[list[tuple[float, float]], float]:
    """Gibt je Teil (rand_start, rand_ende) und nicht integrierbaren Rest zurück.

    Der Rest wird bevorzugt der kleineren Aussenseite zugeschlagen, damit
    eine 6×-Platte (252 mm) nicht über den Bauraum wächst.
    """
    n = len(teile)
    raender = [(0.0, 0.0) for _ in teile]
    if rest <= 0.05 or n == 0:
        return raender, 0.0

    def passt(index: int, extra: float, an_start: bool) -> bool:
        r0, r1 = raender[index]
        add0 = extra if an_start else 0.0
        add1 = 0.0 if an_start else extra
        return teile[index] * raster + r0 + add0 + r1 + add1 <= bauraum + 1e-6

    # Eine Platte: Rest hälftig, bei Platzproblemen alles auf eine Seite, sonst Spacer.
    if n == 1:
        half = rest / 2.0
        if passt(0, rest, True) and teile[0] * raster + rest <= bauraum + 1e-6:
            # versuche hälftig
            if teile[0] * raster + rest <= bauraum + 1e-6:
                raender[0] = (half, half)
                if teile[0] * raster + rest <= bauraum + 1e-6:
                    return raender, 0.0
        # alles auf eine Seite
        if passt(0, rest, True):
            raender[0] = (rest, 0.0)
            return raender, 0.0
        return raender, rest

    # Mehrere Platten: Rest auf die beiden Aussenplatten verteilen.
    # Bevorzugt die kleinere Aussenplatte, bei Gleichheit hälftig.
    i_l, i_r = 0, n - 1
    # Versuche hälftig, sonst schiebe auf die Seite mit mehr Reserve.
    half = rest / 2.0
    reserve_l = bauraum - teile[i_l] * raster
    reserve_r = bauraum - teile[i_r] * raster
    if reserve_l < 0:
        reserve_l = 0.0
    if reserve_r < 0:
        reserve_r = 0.0

    if half <= reserve_l + 1e-6 and half <= reserve_r + 1e-6:
        raender[i_l] = (half, 0.0)
        raender[i_r] = (0.0, half)
        return raender, 0.0

    # So viel wie möglich aussen integrieren, Rest als Spacer.
    offen = rest
    # Zuerst die Seite mit mehr Reserve (oft die kleinere Platte)
    order = [i_l, i_r] if reserve_l >= reserve_r else [i_r, i_l]
    for i in order:
        reserve = bauraum - teile[i] * raster
        if reserve <= 0.05:
            continue
        take = min(offen, reserve)
        if i == i_l:
            raender[i] = (take, 0.0)
        else:
            raender[i] = (0.0, take)
        offen -= take
        if offen <= 0.05:
            return raender, 0.0
    return raender, max(0.0, offen)


def plane_schublade(
    schublade_x: float,
    schublade_y: float,
    spiel_je_seite: float = SCHUBLADENSPIEL_STANDARD,
    raster_mm: float = RASTER_MM,
    bauraum_x: float = BAURAUM_X,
    bauraum_y: float = BAURAUM_Y,
    bodenstaerke: float = BODEN_PLATTE_STANDARD,
) -> Schubladenplan:
    hinweise = []
    if spiel_je_seite < 0:
        raise ValueError("Schubladenspiel darf nicht negativ sein.")

    nutz_x = schublade_x - 2 * spiel_je_seite
    nutz_y = schublade_y - 2 * spiel_je_seite

    if nutz_x < raster_mm or nutz_y < raster_mm:
        return Schubladenplan(
            schublade_x=schublade_x,
            schublade_y=schublade_y,
            spiel_je_seite=spiel_je_seite,
            nutz_x=nutz_x,
            nutz_y=nutz_y,
            raster_mm=raster_mm,
            einheiten_x=0,
            einheiten_y=0,
            rest_x=max(0.0, nutz_x),
            rest_y=max(0.0, nutz_y),
            platten=[],
            anzahl_platten=0,
            randstreifen=[],
            plattenhoehe_mm=plattenhoehe(bodenstaerke),
            bauraum=(bauraum_x, bauraum_y),
            hinweise=[
                "Die nutzbare Schubladenfläche ist kleiner als eine Rastereinheit. "
                "Spiel verringern oder Masse prüfen."
            ],
            ungueltig=True,
        )

    ex = int(nutz_x // raster_mm)
    ey = int(nutz_y // raster_mm)
    rest_x = nutz_x - ex * raster_mm
    rest_y = nutz_y - ey * raster_mm

    max_u_x = int(bauraum_x // raster_mm)
    max_u_y = int(bauraum_y // raster_mm)

    teile_x = _teile_einheiten(ex, max_u_x)
    teile_y = _teile_einheiten(ey, max_u_y)

    raender_x, spacer_x = _verteile_rest_auf_aussen(teile_x, rest_x, raster_mm, bauraum_x)
    raender_y, spacer_y = _verteile_rest_auf_aussen(teile_y, rest_y, raster_mm, bauraum_y)

    # Startindizes
    start_x = []
    acc = 0
    for t in teile_x:
        start_x.append(acc)
        acc += t
    start_y = []
    acc = 0
    for t in teile_y:
        start_y.append(acc)
        acc += t

    platten = []
    for ix, sx in enumerate(teile_x):
        for iy, sy in enumerate(teile_y):
            rl, rr = raender_x[ix]
            rf, rb = raender_y[iy]
            # nur Aussenplatten bekommen den jeweiligen Rand
            # (raender_x ist bereits nur aussen gesetzt)
            breite = sx * raster_mm + rl + rr
            tiefe = sy * raster_mm + rf + rb
            passt = breite <= bauraum_x + 1e-6 and tiefe <= bauraum_y + 1e-6
            muss = not passt
            hinweis = ""
            if muss:
                hinweis = "Mass überschreitet den Bauraum – Rand als separaten Streifen drucken."
            platten.append(
                Plattenzuschnitt(
                    einheiten_x=sx,
                    einheiten_y=sy,
                    rand_x_links=round(rl, 3),
                    rand_x_rechts=round(rr, 3),
                    rand_y_vorne=round(rf, 3),
                    rand_y_hinten=round(rb, 3),
                    pos_einheit_x=start_x[ix],
                    pos_einheit_y=start_y[iy],
                    breite_mm=round(breite, 3),
                    tiefe_mm=round(tiefe, 3),
                    passt_in_bauraum=passt,
                    muss_geteilt_werden=muss,
                    hinweis=hinweis,
                )
            )

    streifen = []
    if spacer_x > 0.05:
        # zwei Streifen möglich, wir erzeugen einen (oder zwei, wenn länger als Bauraum)
        laenge = ey * raster_mm + (rest_y - spacer_y)
        teile = math.ceil(laenge / bauraum_y) if laenge > bauraum_y else 1
        streifen.append(
            Randstreifen(
                seite="X-Rest (links oder rechts anlegen)",
                laenge_mm=round(laenge, 3),
                breite_mm=round(spacer_x, 3),
                teile=teile,
                hinweis="Separater Randstreifen, weil der Rest nicht in den Bauraum der Aussenplatte passte.",
            )
        )
        hinweise.append(
            f"{spacer_x:.1f} mm Rest in der Breite können nicht in die Aussenplatte integriert "
            "werden und sind als Randstreifen vorgesehen."
        )
    if spacer_y > 0.05:
        laenge = ex * raster_mm + (rest_x - spacer_x)
        teile = math.ceil(laenge / bauraum_x) if laenge > bauraum_x else 1
        streifen.append(
            Randstreifen(
                seite="Y-Rest (vorn oder hinten anlegen)",
                laenge_mm=round(laenge, 3),
                breite_mm=round(spacer_y, 3),
                teile=teile,
                hinweis="Separater Randstreifen, weil der Rest nicht in den Bauraum der Aussenplatte passte.",
            )
        )
        hinweise.append(
            f"{spacer_y:.1f} mm Rest in der Tiefe können nicht in die Aussenplatte integriert "
            "werden und sind als Randstreifen vorgesehen."
        )

    if rest_x < 2.0 and rest_x > 0.05:
        hinweise.append(
            f"Der Breitenrest beträgt nur {rest_x:.1f} mm. Ein integrierter Rand dieser Breite "
            "ist filigran; ein etwas größeres Schubladenspiel kann sinnvoller sein."
        )
    if rest_y < 2.0 and rest_y > 0.05:
        hinweise.append(
            f"Der Tiefenrest beträgt nur {rest_y:.1f} mm. Ein integrierter Rand dieser Breite "
            "ist filigran; ein etwas größeres Schubladenspiel kann sinnvoller sein."
        )

    hinweise.append(
        f"Es verbleiben {spiel_je_seite:.1f} mm Spiel je Schubladenseite, damit die Platten "
        "nicht klemmen. Wert bei Bedarf am Parameter Schubladenspiel ändern."
    )

    return Schubladenplan(
        schublade_x=schublade_x,
        schublade_y=schublade_y,
        spiel_je_seite=spiel_je_seite,
        nutz_x=round(nutz_x, 3),
        nutz_y=round(nutz_y, 3),
        raster_mm=raster_mm,
        einheiten_x=ex,
        einheiten_y=ey,
        rest_x=round(rest_x, 3),
        rest_y=round(rest_y, 3),
        platten=platten,
        anzahl_platten=len(platten),
        randstreifen=streifen,
        plattenhoehe_mm=plattenhoehe(bodenstaerke),
        bauraum=(bauraum_x, bauraum_y),
        hinweise=hinweise,
        ungueltig=False,
    )


def plan_als_text(plan: Schubladenplan) -> str:
    lines = []
    lines.append(f"Schublade: {plan.schublade_x:.1f} × {plan.schublade_y:.1f} mm")
    lines.append(f"Spiel je Seite: {plan.spiel_je_seite:.1f} mm")
    lines.append(f"Nutzfläche: {plan.nutz_x:.1f} × {plan.nutz_y:.1f} mm")
    if plan.ungueltig:
        lines.append("Planung ungültig:")
        lines.extend(f"- {h}" for h in plan.hinweise)
        return "\n".join(lines)
    lines.append(
        f"Rastereinheiten: {plan.einheiten_x} × {plan.einheiten_y} "
        f"({plan.einheiten_x * plan.raster_mm:.0f} × {plan.einheiten_y * plan.raster_mm:.0f} mm)"
    )
    lines.append(f"Restmass nach Raster: {plan.rest_x:.1f} mm in X, {plan.rest_y:.1f} mm in Y")
    lines.append(f"Plattenanzahl: {plan.anzahl_platten}")
    lines.append(f"Plattenhöhe (Standardboden 0,8 mm): {plan.plattenhoehe_mm:.2f} mm")
    lines.append("")
    lines.append("Plattenzuschnitte:")
    for i, p in enumerate(plan.platten, 1):
        lines.append(
            f"  {i:2d}. {p.einheiten_x}×{p.einheiten_y}-Platte  "
            f"{p.breite_mm:.1f} × {p.tiefe_mm:.1f} mm  "
            f"an Rasterposition ({p.pos_einheit_x},{p.pos_einheit_y})  "
            f"Rand L/R/V/H = {p.rand_x_links:.1f}/{p.rand_x_rechts:.1f}/"
            f"{p.rand_y_vorne:.1f}/{p.rand_y_hinten:.1f} mm"
            + ("  [passt]" if p.passt_in_bauraum else "  [BAURAUM ÜBERSCHRITTEN]")
        )
        if p.hinweis:
            lines.append(f"      {p.hinweis}")
    if plan.randstreifen:
        lines.append("")
        lines.append("Separate Randstreifen:")
        for s in plan.randstreifen:
            lines.append(
                f"  - {s.seite}: {s.breite_mm:.1f} mm breit, {s.laenge_mm:.1f} mm lang, "
                f"{s.teile} Teil(e). {s.hinweis}"
            )
    if plan.hinweise:
        lines.append("")
        lines.append("Hinweise:")
        for h in plan.hinweise:
            lines.append(f"- {h}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if len(args) >= 2:
        x, y = float(args[0]), float(args[1])
        spiel = float(args[2]) if len(args) >= 3 else SCHUBLADENSPIEL_STANDARD
        print(plan_als_text(plane_schublade(x, y, spiel)))
    else:
        for x, y in ((450, 350), (500, 400)):
            print("=" * 72)
            print(plan_als_text(plane_schublade(x, y)))
            print()
