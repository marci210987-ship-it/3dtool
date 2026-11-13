# -*- coding: utf-8 -*-
"""Planung für Bestecksortierer und Gewürzorganizer (ohne FreeCAD)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

BAURAUM_SICHER = 250.0  # Sicherheitsrand zum 256-mm-Bauraum
SCHUBLADENSPIEL = 1.0
WAND = 1.2
BODEN = 1.6
TRENN = 1.2
INNENRADIUS_BESTECK = 5.0  # grösser als die 2 mm der Boxen, weniger Schmutzecken


@dataclass
class Fach:
    name: str
    index: int
    x: float
    y: float
    breite: float
    laenge: float
    hinterfach: bool = False


@dataclass
class Trennlinie:
    """Achse 'x' = senkrechte Wand (konstantes x), 'y' = waagerechte Wand."""
    achse: str
    position: float  # Mitte der Trennwand
    a0: float
    a1: float
    dicke: float


@dataclass
class Segment:
    index: int
    ix: int
    iy: int
    x0: float
    y0: float
    x1: float
    y1: float
    stoesse: tuple  # ('links','rechts','vorne','hinten') als True, wenn Stosskante
    breite: float = 0.0
    tiefe: float = 0.0
    passt: bool = True

    def __post_init__(self):
        self.breite = self.x1 - self.x0
        self.tiefe = self.y1 - self.y0
        self.passt = self.breite <= BAURAUM_SICHER + 1e-6 and self.tiefe <= BAURAUM_SICHER + 1e-6


@dataclass
class Besteckplan:
    schublade_x: float
    schublade_y: float
    spiel: float
    nutz_x: float
    nutz_y: float
    hoehe: float
    wand: float
    boden: float
    trenn: float
    innenradius: float
    faecher: list
    trenner: list
    segmente: list
    herausnehmbar: bool
    fuesse: bool
    max_segment: float
    hinweise: list = field(default_factory=list)
    ungueltig: bool = False

    def to_dict(self):
        return asdict(self)


def default_besteck_faecher():
    """Annahme typischer Haushalt, keine Messung an Marcels Besteck."""
    return [
        {"name": "Messer", "breite": 48.0, "laenge": 0.0},
        {"name": "Gabeln", "breite": 55.0, "laenge": 0.0},
        {"name": "Essloeffel", "breite": 55.0, "laenge": 0.0},
        {"name": "Teeloeffel", "breite": 50.0, "laenge": 0.0},
        {"name": "Kochbesteck", "breite": 0.0, "laenge": 0.0},  # 0 = Restbreite
    ]


def _teile_laenge(laenge, max_seg, bevorzugte_schnitte=None):
    """Teilt laenge in Abschnitte <= max_seg, schnitte bevorzugt an Trennlinien."""
    if laenge <= max_seg + 1e-6:
        return [laenge]
    n = int(math.ceil(laenge / max_seg - 1e-12))
    # evtl. mehr Teile, falls bevorzugte Schnitte das erzwingen
    bevor = sorted(p for p in (bevorzugte_schnitte or []) if 0.5 < p < laenge - 0.5)

    def ok(teile):
        return all(t > 8.0 and t <= max_seg + 1e-6 for t in teile) and abs(sum(teile) - laenge) < 1e-6

    # Versuche, n-1 Schnitte an die nächsten bevorzugten Positionen zu legen
    for n_try in range(n, n + 3):
        ideal = [laenge / n_try] * n_try
        cuts = []
        acc = 0.0
        for i in range(n_try - 1):
            ziel = (i + 1) * (laenge / n_try)
            kandidat = ziel
            if bevor:
                nahe = min(bevor, key=lambda p: abs(p - ziel))
                # Nur übernehmen, wenn alle entstehenden Teile <= max_seg bleiben
                links = nahe - acc
                rechts_rest = laenge - nahe
                n_rechts = n_try - 1 - i
                if links <= max_seg + 1e-6 and links > 8 and (n_rechts == 0 or rechts_rest / n_rechts <= max_seg + 1e-6):
                    # nicht denselben Schnitt zweimal
                    if all(abs(nahe - c) > 4.0 for c in cuts):
                        kandidat = nahe
            cuts.append(kandidat)
            acc = kandidat
        teile = []
        prev = 0.0
        for c in cuts:
            teile.append(c - prev)
            prev = c
        teile.append(laenge - prev)
        if ok(teile):
            return teile
    # Fallback: gleichmässig
    n = int(math.ceil(laenge / max_seg - 1e-12))
    basis = laenge / n
    return [basis] * n


def plane_besteck(params: dict) -> Besteckplan:
    sx = float(params["Schubladenbreite"])
    sy = float(params["Schubladentiefe"])
    spiel = float(params.get("Schubladenspiel", SCHUBLADENSPIEL))
    hoehe = float(params.get("Einsatzhoehe", 45.0))
    wand = float(params.get("Wandstaerke", WAND))
    boden = float(params.get("Bodenstaerke", BODEN))
    trenn = float(params.get("Trennwandstaerke", TRENN))
    radius = float(params.get("Innenradius", INNENRADIUS_BESTECK))
    max_seg = float(params.get("Max_Segmentmass", BAURAUM_SICHER))
    heraus = int(params.get("Trennwande_herausnehmbar", 0)) == 1
    fuesse = int(params.get("Fuesse", 0)) == 1
    hinweise = []
    nutz_x = sx - 2 * spiel
    nutz_y = sy - 2 * spiel
    if nutz_x < 60 or nutz_y < 60:
        return Besteckplan(
            sx, sy, spiel, nutz_x, nutz_y, hoehe, wand, boden, trenn, radius,
            [], [], [], heraus, fuesse, max_seg,
            ["Nutzfläche zu klein für einen Besteckeinsatz."], True,
        )
    if hoehe < boden + 10:
        return Besteckplan(
            sx, sy, spiel, nutz_x, nutz_y, hoehe, wand, boden, trenn, radius,
            [], [], [], heraus, fuesse, max_seg,
            ["Einsatzhoehe ist zu niedrig (Boden plus nutzbare Wand)."], True,
        )

    inner_x = nutz_x - 2 * wand
    inner_y = nutz_y - 2 * wand
    vorlagen = default_besteck_faecher()
    specs = []
    for i, v in enumerate(vorlagen, 1):
        specs.append({
            "name": v["name"],
            "breite": float(params.get("Fach_%d_Breite" % i, v["breite"])),
            "laenge": float(params.get("Fach_%d_Laenge" % i, v["laenge"])),
        })

    fest = [s for s in specs[:-1]]
    koch = specs[-1]
    n_trenn = len(specs) - 1
    festbreite = sum(s["breite"] for s in fest)
    if any(s["breite"] < 12 for s in fest):
        hinweise.append("Mindestens ein vorderes Fach ist schmaler als 12 mm – bitte prüfen.")
    need = festbreite + n_trenn * trenn + (koch["breite"] if koch["breite"] > 0 else 0)
    if need > inner_x + 1e-6:
        return Besteckplan(
            sx, sy, spiel, nutz_x, nutz_y, hoehe, wand, boden, trenn, radius,
            [], [], [], heraus, fuesse, max_seg,
            ["Die angegebenen Fachbreiten plus Trennwände passen nicht in die Schubladenbreite "
             "(innen %.1f mm, benötigt %.1f mm)." % (inner_x, need)], True,
        )
    rest = inner_x - festbreite - n_trenn * trenn - (koch["breite"] if koch["breite"] > 0 else 0)
    if koch["breite"] <= 0:
        koch["breite"] = rest
    else:
        koch["breite"] += rest
    min_koch = min(80.0, max(40.0, inner_x * 0.22))
    if koch["breite"] < min_koch and festbreite > 0:
        available = inner_x - n_trenn * trenn - min_koch
        if available >= 48:
            scale = available / festbreite
            for s in fest:
                s["breite"] *= scale
            koch["breite"] = min_koch
            hinweise.append(
                "Die Fachbreiten der vorderen Fächer wurden anteilig auf %.0f %% verkleinert, "
                "damit das Kochbesteck-Fach mindestens %.0f mm breit bleibt."
                % (scale * 100, min_koch)
            )
        elif koch["breite"] < 20:
            hinweise.append("Das Kochbesteck-Fach ist mit %.1f mm sehr schmal." % koch["breite"])
    elif koch["breite"] < 20:
        hinweise.append("Das Kochbesteck-Fach ist mit %.1f mm sehr schmal." % koch["breite"])

    faecher = []
    trenner = []
    x = wand
    for i, s in enumerate(specs):
        laenge = s["laenge"] if s["laenge"] > 0 else inner_y
        laenge = min(laenge, inner_y)
        # Hinterfach nur, wenn wirklich Platz für eine zweite Reihe bleibt
        hinten_frei = inner_y - laenge
        if hinten_frei >= 20 + trenn:
            faecher.append(Fach(s["name"], i + 1, x, wand, s["breite"], laenge, False))
            hy = wand + laenge + trenn
            faecher.append(Fach("Hinten_%s" % s["name"], 100 + i + 1, x, hy, s["breite"], nutz_y - wand - hy, True))
            trenner.append(Trennlinie("y", wand + laenge + trenn / 2.0, x, x + s["breite"], trenn))
        else:
            faecher.append(Fach(s["name"], i + 1, x, wand, s["breite"], inner_y, False))
        if i < len(specs) - 1:
            trenner.append(Trennlinie("x", x + s["breite"] + trenn / 2.0, wand, nutz_y - wand, trenn))
        x += s["breite"] + trenn

    # Schnitte bevorzugt an vertikalen Trennern
    x_cuts = [t.position for t in trenner if t.achse == "x"]
    y_cuts = [t.position for t in trenner if t.achse == "y"]
    teile_x = _teile_laenge(nutz_x, max_seg, x_cuts)
    teile_y = _teile_laenge(nutz_y, max_seg, y_cuts)
    segmente = []
    accx = 0.0
    idx = 1
    for ix, tx in enumerate(teile_x):
        accy = 0.0
        for iy, ty in enumerate(teile_y):
            stoesse = (
                ix > 0,  # links
                ix < len(teile_x) - 1,  # rechts
                iy > 0,  # vorne
                iy < len(teile_y) - 1,  # hinten
            )
            segmente.append(Segment(
                index=idx, ix=ix, iy=iy,
                x0=accx, y0=accy, x1=accx + tx, y1=accy + ty,
                stoesse=stoesse,
            ))
            idx += 1
            accy += ty
        accx += tx

    if any(not s.passt for s in segmente):
        hinweise.append("Mindestens ein Segment überschreitet das maximale Segmentmass.")
    if len(segmente) > 1:
        hinweise.append(
            "Der Einsatz wird in %d Segmente geteilt (Maximalmass %.0f mm), "
            "die werkzeuglos mit dem Hausraster-Schwalbenschwanz verbunden werden."
            % (len(segmente), max_seg)
        )
        # liegen X-Schnitte auf Trennern?
        cut_x = []
        a = 0.0
        for t in teile_x[:-1]:
            a += t
            cut_x.append(a)
        for c in cut_x:
            if not any(abs(c - t.position) < (t.dicke / 2.0 + 0.6) for t in trenner if t.achse == "x"):
                hinweise.append(
                    "Ein Schnitt bei X=%.1f mm verläuft nicht genau in einer Trennwand. "
                    "Dort entsteht eine niedrige Verbindungsschiene im Fachboden." % c
                )

    if fuesse:
        hinweise.append(
            "Füsse sind eingeschaltet: der Einsatz steht um 4,75 mm höher und kann auf eine "
            "Hausraster-/Gridfinity-Platte gesetzt werden. Ohne Platte stehen nur die Füsse auf dem Schubladenboden."
        )
    if heraus:
        hinweise.append(
            "Trennwände sind als herausnehmbare Steckteile vorgesehen (Nuten). "
            "Das erleichtert die Anpassung, schafft aber zusätzliche Fugen."
        )
    hinweise.append(
        "Fachmasse sind Vorgaben bzw. typische Annahmen, keine Messung an vorhandenem Besteck. "
        "Breiten und Längen im Tabellenblatt anpassen."
    )
    return Besteckplan(
        sx, sy, spiel, nutz_x, nutz_y, hoehe, wand, boden, trenn, radius,
        faecher, trenner, segmente, heraus, fuesse, max_seg, hinweise, False,
    )


def plan_als_text(plan: Besteckplan) -> str:
    lines = []
    lines.append("Besteckeinsatz für Schublade %.1f × %.1f mm" % (plan.schublade_x, plan.schublade_y))
    lines.append("Spiel je Seite: %.1f mm  →  Nutzmass %.1f × %.1f × %.1f mm" % (
        plan.spiel, plan.nutz_x, plan.nutz_y, plan.hoehe))
    if plan.ungueltig:
        lines.append("Planung ungültig:")
        lines.extend("- " + h for h in plan.hinweise)
        return "\n".join(lines)
    lines.append("Trennwände: %s, Füsse: %s" % (
        "herausnehmbar" if plan.herausnehmbar else "fest gedruckt",
        "ja" if plan.fuesse else "nein"))
    lines.append("Fächer:")
    for f in plan.faecher:
        lines.append(
            "  - %s: %.1f × %.1f mm bei (%.1f, %.1f)%s" % (
                f.name, f.breite, f.laenge, f.x, f.y,
                " [Hinterfach]" if f.hinterfach else "",
            )
        )
    lines.append("Segmente: %d" % len(plan.segmente))
    for s in plan.segmente:
        st = []
        names = ("links", "rechts", "vorne", "hinten")
        for n, flag in zip(names, s.stoesse):
            if flag:
                st.append(n)
        lines.append(
            "  - Seg %d (Raster %d/%d): %.1f × %.1f mm, Ecke (%.1f, %.1f)%s%s" % (
                s.index, s.ix, s.iy, s.breite, s.tiefe, s.x0, s.y0,
                "  [passt]" if s.passt else "  [ZU GROSS]",
                ("  Stoss: " + ",".join(st)) if st else "  (einteilig oder Aussenstück ohne Stoss)",
            )
        )
    if plan.hinweise:
        lines.append("Hinweise:")
        lines.extend("- " + h for h in plan.hinweise)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gewürz
# ---------------------------------------------------------------------------

@dataclass
class Gewuerzplan:
    typ: str
    breite: float
    tiefe: float
    hoehe: float
    ebenen: int
    parameter: dict
    segmente_x: list
    passt_einteilig: bool
    hinweise: list
    ungueltig: bool = False
    segmente_y: list = field(default_factory=list)


def plane_stufenregal(params: dict) -> Gewuerzplan:
    wand = float(params.get("Wandstaerke", WAND))
    boden = float(params.get("Bodenstaerke", BODEN))
    ebenen = int(params.get("Ebenenanzahl", 3))
    stufenhoehe = float(params.get("Stufenhoehe", 35.0))
    stufentiefe = float(params.get("Stufentiefe", 0.0))
    glas_d = float(params.get("Glasdurchmesser", 55.0))
    glas_n = int(params.get("Glasanzahl", 0))
    breite = float(params.get("Gesamtbreite", 0.0))
    tiefe = float(params.get("Gesamttiefe", 0.0))
    max_seg = float(params.get("Max_Segmentmass", BAURAUM_SICHER))
    lippe = float(params.get("Stufenlippe", 12.0))
    hinterlippe = float(params.get("Hinterlippe", 25.0))
    gap = float(params.get("Glasabstand", 4.0))
    hinweise = [
        "Glasdurchmesser und -anzahl sind Annahmen typischer Streugläser, keine Messung an vorhandenen Gläsern."
    ]
    if ebenen < 2 or ebenen > 6:
        return Gewuerzplan("stufenregal", breite, tiefe, 0, ebenen, dict(params), [], False,
                           ["Ebenenanzahl muss zwischen 2 und 6 liegen."], True)
    if glas_d < 20 or glas_d > 120:
        return Gewuerzplan("stufenregal", breite, tiefe, 0, ebenen, dict(params), [], False,
                           ["Glasdurchmesser ausserhalb 20–120 mm."], True)
    pitch = glas_d + gap
    if breite <= 0 and glas_n > 0:
        breite = glas_n * pitch + 2 * wand
    if tiefe <= 0:
        tiefe = ebenen * (stufentiefe if stufentiefe > 0 else (glas_d + 8.0))
    if stufentiefe <= 0:
        stufentiefe = tiefe / ebenen
    if ebenen * stufentiefe - 1e-6 > tiefe:
        hinweise.append(
            "Ebenen × Stufentiefe überschreitet die Gesamttiefe. Stufentiefe wird auf %.1f mm gekürzt."
            % (tiefe / ebenen)
        )
        stufentiefe = tiefe / ebenen
    inner = breite - 2 * wand
    passt_n = int(math.floor(inner / pitch + 1e-9))
    if glas_n <= 0:
        glas_n = max(1, passt_n)
    elif glas_n > passt_n:
        return Gewuerzplan("stufenregal", breite, tiefe, 0, ebenen, dict(params), [], False,
                           ["Glasanzahl %d passt nicht in die Breite %.1f mm (max. %d bei Ø %.1f)." % (
                               glas_n, breite, passt_n, glas_d)], True)
    hoehe = (ebenen - 1) * stufenhoehe + boden + hinterlippe
    if hoehe > 256:
        return Gewuerzplan("stufenregal", breite, tiefe, hoehe, ebenen, dict(params), [], False,
                           ["Gesamthöhe %.1f mm überschreitet den P2S-Bauraum." % hoehe], True)
    teile = _teile_laenge(breite, max_seg, None)
    passt_ein = len(teile) == 1 and tiefe <= max_seg + 1e-6 and hoehe <= 256
    if tiefe > max_seg:
        hinweise.append(
            "Die Tiefe %.1f mm liegt über dem Segmentmass. Das Regal wird in der Tiefe nicht geteilt; "
            "bitte Tiefe verringern oder Stufenzahl/Stufentiefe anpassen." % tiefe
        )
        if tiefe > 256:
            return Gewuerzplan("stufenregal", breite, tiefe, hoehe, ebenen, dict(params), teile, False,
                               hinweise + ["Tiefe überschreitet den Bauraum."], True)
    p = dict(params)
    p.update({
        "Gesamtbreite": breite, "Gesamttiefe": tiefe, "Stufenhoehe": stufenhoehe,
        "Stufentiefe": stufentiefe, "Glasanzahl": glas_n, "Glasdurchmesser": glas_d,
        "Hoehe": hoehe, "Wandstaerke": wand, "Bodenstaerke": boden,
    })
    if len(teile) > 1:
        hinweise.append("Das Stufenregal wird in der Breite in %d Segmente geteilt." % len(teile))
    return Gewuerzplan("stufenregal", breite, tiefe, hoehe, ebenen, p, teile, passt_ein, hinweise, False)


def plane_schraege(params: dict) -> Gewuerzplan:
    wand = float(params.get("Wandstaerke", WAND))
    sx = float(params.get("Schubladenbreite", 0.0))
    sy = float(params.get("Schubladentiefe", 0.0))
    spiel = float(params.get("Schubladenspiel", SCHUBLADENSPIEL))
    glas_d = float(params.get("Glasdurchmesser", 55.0))
    glas_l = float(params.get("Glaslange", 110.0))
    winkel = float(params.get("Neigungswinkel", 15.0))
    reihen = int(params.get("Reihen", 0))
    verfuegbar = float(params.get("Verfuegbare_Hoehe", 90.0))
    max_seg = float(params.get("Max_Segmentmass", BAURAUM_SICHER))
    gap = float(params.get("Glasabstand", 4.0))
    hinweise = [
        "Glasdurchmesser und Glaslänge sind Annahmen typischer Streugläser (liegend), keine Messung."
    ]
    nutz_x = sx - 2 * spiel
    nutz_y = sy - 2 * spiel
    if nutz_x < 40 or nutz_y < 40:
        return Gewuerzplan("schraege", nutz_x, nutz_y, 0, 0, dict(params), [], False,
                           ["Nutzfläche zu klein."], True)
    if winkel < 5 or winkel > 40:
        return Gewuerzplan("schraege", nutz_x, nutz_y, 0, 0, dict(params), [], False,
                           ["Neigungswinkel muss zwischen 5° und 40° liegen (stützenfreies Drucken)."], True)
    hoehe_hinten = nutz_y * math.tan(math.radians(winkel))
    if hoehe_hinten > verfuegbar - 1.0:
        neu = math.degrees(math.atan((verfuegbar - 1.0) / nutz_y))
        hinweise.append(
            "Winkel %.1f° würde hinten %.1f mm Höhe brauchen, verfügbar sind %.1f mm. "
            "Winkel wird auf %.1f° begrenzt." % (winkel, hoehe_hinten, verfuegbar, neu)
        )
        winkel = neu
        hoehe_hinten = nutz_y * math.tan(math.radians(winkel))
    # Reihen quer zur Schubladenbreite
    inner_x = nutz_x - 2 * wand
    pitch = glas_d + gap
    max_reihen = max(1, int(math.floor(inner_x / pitch + 1e-9)))
    if reihen <= 0:
        reihen = max_reihen
    elif reihen > max_reihen:
        return Gewuerzplan("schraege", nutz_x, nutz_y, hoehe_hinten, reihen, dict(params), [], False,
                           ["%d Reihen passen nicht in die Breite (max. %d)." % (reihen, max_reihen)], True)
    # wie viele Gläser hintereinander auf der schrägen Bahn
    bahn = nutz_y / math.cos(math.radians(winkel))
    n_tief = max(1, int(math.floor((bahn - 10.0) / (glas_l + gap) + 1e-9)))
    teile = _teile_laenge(nutz_x, max_seg, None)
    teile_y = _teile_laenge(nutz_y, max_seg, None)
    p = dict(params)
    p.update({
        "Nutzbreite": nutz_x, "Nutztiefe": nutz_y, "Neigungswinkel": winkel,
        "Hoehe_hinten": hoehe_hinten, "Reihen": reihen, "Glaeser_je_Reihe": n_tief,
        "Wandstaerke": wand,
    })
    hinweise.append(
        "Es passen %d Reihe(n) mit je etwa %d Glas/Gläsern (Schätzung aus Durchmesser und Länge)."
        % (reihen, n_tief)
    )
    if len(teile) > 1:
        hinweise.append("Der Schrägeinsatz wird in der Breite in %d Segmente geteilt." % len(teile))
    if len(teile_y) > 1:
        hinweise.append("Der Schrägeinsatz wird in der Tiefe in %d Segmente geteilt (Bauraum)." % len(teile_y))
    passt = len(teile) == 1 and len(teile_y) == 1 and hoehe_hinten <= 256
    return Gewuerzplan("schraege", nutz_x, nutz_y, hoehe_hinten, reihen, p, teile, passt, hinweise, False, teile_y)


def plane_halter(params: dict) -> Gewuerzplan:
    wand = float(params.get("Wandstaerke", WAND))
    boden = float(params.get("Bodenstaerke", 1.6))
    glas_d = float(params.get("Glasdurchmesser", 55.0))
    spiel_g = float(params.get("Glasspiel", 2.0))
    wandhoehe = float(params.get("Wandhoehe", 28.0))
    auschnitt = int(params.get("Frontausschnitt", 1)) == 1
    if glas_d < 20 or glas_d > 120:
        return Gewuerzplan("halter", 0, 0, 0, 1, dict(params), [1], False,
                           ["Glasdurchmesser ausserhalb 20–120 mm."], True)
    innen_d = glas_d + 2 * spiel_g
    aussen_becher = innen_d + 2 * wand
    # Seitliche Verbinder-Ansaetze stehen um (Tiefe + 0,4 mm) je Seite über den Becher hinaus.
    # Das war in 0.2 dokumentiert als "stehen nicht über", weicht aber von der Geometrie ab.
    PAD = 8.0 + 0.4
    aussen_x = aussen_becher + 2 * PAD
    aussen_y = aussen_becher
    hoehe = boden + wandhoehe
    hinweise = [
        "Glasdurchmesser ist ein einstellbarer Parameter (Annahme, keine Messung).",
        "Becher %.1f × %.1f mm, mit Verbinder-Ansätzen %.1f × %.1f × %.1f mm, Innenöffnung Ø %.1f mm."
        % (aussen_becher, aussen_becher, aussen_x, aussen_y, hoehe, innen_d),
        "Seitliche Schwalbenschwanz-Ansaetze (je 8,4 mm) nutzen denselben Clip wie die Segmente.",
    ]
    aussen = aussen_x  # Planbreite = wirkliches Bounding-Box-X
    if aussen_x > BAURAUM_SICHER or aussen_y > BAURAUM_SICHER:
        return Gewuerzplan("halter", aussen_x, aussen_y, hoehe, 1, dict(params), [aussen_x], False,
                           ["Halter ist grösser als das Segmentmass."], True)
    p = dict(params)
    p.update({
        "Aussenmass": aussen_x,
        "Aussenmass_Becher": aussen_becher,
        "Aussenmass_X": aussen_x,
        "Aussenmass_Y": aussen_y,
        "Innen_D": innen_d,
        "Hoehe": hoehe,
        "Wandstaerke": wand,
        "Bodenstaerke": boden,
    })
    return Gewuerzplan("halter", aussen_x, aussen_y, hoehe, 1, p, [aussen_x], True, hinweise, False)


if __name__ == "__main__":
    for x, y in ((450, 350), (500, 400), (240, 200)):
        p = plane_besteck({"Schubladenbreite": x, "Schubladentiefe": y})
        print("=" * 70)
        print(plan_als_text(p))
        print()
