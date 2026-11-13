# -*- coding: utf-8 -*-
"""Phase-4-Geometrie: Wrapper um das gemeinsame Box-Grundmodell.

Die Phase-2-Module bleiben unverändert. Neue Funktionen: herausnehmbare
Trennwände (Nuten in Innenrippen), abnehmbarer Deckel, optionale
Kabelkerben und Deckelrasten (Verriegelungsart).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import Part
import FreeCAD as App

from hausraster_const import (
    default_params,
    pruefe_parameter,
    kasten_aussen,
    box_hoehe,
    FUSS_PROFIL_HOEHE,
    LIPPE_HOEHE,
    LIPPE_P0,
    LIPPE_P1,
    LIPPE_P2,
    WANDSTAERKE_STANDARD,
    TRENNWAND_STANDARD,
    BODEN_BOX_STANDARD,
)
from hausraster_geom import (
    make_box_shape,
    make_plate_shape,
    make_rastclip_shape,
    box_outer_size,
    plate_outer_size,
    seated_box_z_on_plate,
    loft_sections,
    _als_solid,
    _r_ok,
    _faecher_trenner,
)

VEC = App.Vector
PHASE4_VERSION = "0.2-phase4"

# Verriegelungsart: 0 = keine, 1 = Rastclip (über die Stapellippe, Phase-2-Clip),
# 2 = Deckelraste (Nasen am Deckel).
VERRIEGELUNG_KEINE = 0
VERRIEGELUNG_RASTCLIP = 1
VERRIEGELUNG_DECKELRASTE = 2

DECKEL_STAERKE_STANDARD = 2.0
DECKEL_SPIEL_STANDARD = 0.25  # mm je Seite
NUT_SPIEL_STANDARD = 0.25
RIPPEN_TIEFE = 2.0
RIPPEN_RAND = 0.8
KABELKERBE_B = 10.0
KABELKERBE_H = 8.0


def phase4_params(**overrides) -> dict:
    p = default_params(
        Einheiten_X=2,
        Einheiten_Y=3,
        Einheiten_Z=3,
        Stapellippe=1,
        Verriegelung=1,
        Fachanzahl_X=1,
        Fachanzahl_Y=1,
        Wandstaerke=WANDSTAERKE_STANDARD,
        Bodenstaerke_Box=BODEN_BOX_STANDARD,
        Trennwandstaerke=TRENNWAND_STANDARD,
        Passungsspiel=0.0,
    )
    p.update({
        "Herausnehmbare_Trennwaende": 0,
        "Deckel": 0,
        "Deckelstaerke": DECKEL_STAERKE_STANDARD,
        "Deckel_Spiel": DECKEL_SPIEL_STANDARD,
        "Trennwand_Spiel": NUT_SPIEL_STANDARD,
        "Verriegelungsart": VERRIEGELUNG_RASTCLIP,
        "Kabelkerben": 0,
        "Modelltyp": "box",
    })
    p.update(overrides)
    return p


def _innenmasse(p):
    wand = float(p["Wandstaerke"])
    ax = kasten_aussen(int(p["Einheiten_X"]), float(p["Passungsspiel"]))
    ay = kasten_aussen(int(p["Einheiten_Y"]), float(p["Passungsspiel"]))
    return ax, ay, ax - 2 * wand, ay - 2 * wand


def _fach_achsen(innen, n, trenn):
    """Mitten der festen bzw. herausnehmbaren Trennwände."""
    if n <= 1:
        return []
    nutz = innen - (n - 1) * trenn
    fach = nutz / n
    return [-innen / 2.0 + fach + trenn / 2.0 + i * (fach + trenn) for i in range(n - 1)]


def _rippen_mit_nut(innen_x, innen_y, z0, z1, achsen, achse, trenn, spiel, wand):
    """Innenrippen an den gegenüberliegenden Wänden, mit Nut für eine Trennwand."""
    teile = []
    nut_b = trenn + 2.0 * spiel
    rip_b = nut_b + 2.0 * RIPPEN_RAND
    tiefe = RIPPEN_TIEFE
    h = max(1.0, z1 - z0)
    for c in achsen:
        if achse == "x":
            # Trennwand in YZ (konstante X) → Nuten in vorderer/hinterer Wand
            for sign in (-1.0, 1.0):
                cy = sign * (innen_y / 2.0 - tiefe / 2.0)
                rip = loft_sections(
                    [(z0, rip_b, tiefe, 0.2), (z1, rip_b, tiefe, 0.2)],
                    cx=c, cy=cy,
                )
                nut = loft_sections(
                    [(z0 - 0.2, nut_b, tiefe + 0.6, 0.05), (z1 + 0.2, nut_b, tiefe + 0.6, 0.05)],
                    cx=c, cy=cy,
                )
                teile.append(rip.cut(nut))
        else:
            for sign in (-1.0, 1.0):
                cx = sign * (innen_x / 2.0 - tiefe / 2.0)
                rip = loft_sections(
                    [(z0, tiefe, rip_b, 0.2), (z1, tiefe, rip_b, 0.2)],
                    cx=cx, cy=c,
                )
                nut = loft_sections(
                    [(z0 - 0.2, tiefe + 0.6, nut_b, 0.05), (z1 + 0.2, tiefe + 0.6, nut_b, 0.05)],
                    cx=cx, cy=c,
                )
                teile.append(rip.cut(nut))
    if not teile:
        return None
    fused = teile[0]
    for t in teile[1:]:
        fused = fused.fuse(t)
    return _als_solid(fused.removeSplitter() if hasattr(fused, "removeSplitter") else fused, "Nutrippen")


def make_trennwand(p, richtung, laenge, hoehe, kerben_achsen=None):
    """Eine herausnehmbare Trennwand. richtung 'x' = Wand in YZ (breite=trenn, tiefe=laenge)."""
    trenn = float(p["Trennwandstaerke"])
    spiel = float(p.get("Trennwand_Spiel", NUT_SPIEL_STANDARD))
    # Länge bis knapp vor die Innenwand: die Nuten liegen in den Rippen
    # innerhalb des Lichtraums, nicht in der Aussenwand.
    dicke = max(0.6, trenn)
    l = max(8.0, laenge - 2.0 * spiel)
    platte = loft_sections([(0.0, dicke, l, 0.15), (hoehe, dicke, l, 0.15)])
    # Kreuzungskerben auf halber Höhe, damit sich X- und Y-Wände kreuzen
    if kerben_achsen:
        kerbe_h = hoehe / 2.0 + 0.2
        for c in kerben_achsen:
            if richtung == "x":
                # Platte liegt in Y (cy variiert). Kerbe von oben oder unten.
                cut = loft_sections(
                    [(-0.2, dicke + 0.8, dicke + 2 * spiel, 0.05),
                     (kerbe_h, dicke + 0.8, dicke + 2 * spiel, 0.05)],
                    cx=0.0, cy=c,
                )
            else:
                cut = loft_sections(
                    [(-0.2, dicke + 2 * spiel, dicke + 0.8, 0.05),
                     (kerbe_h, dicke + 2 * spiel, dicke + 0.8, 0.05)],
                    cx=c, cy=0.0,
                )
            # X-Wände: Kerbe von oben; Y-Wände: Kerbe von unten (werden gedreht)
            if richtung == "x":
                # von oben: schneide [hoehe-kerbe_h, hoehe]
                cut = loft_sections(
                    [(hoehe - kerbe_h, dicke + 0.8, dicke + 2 * spiel, 0.05),
                     (hoehe + 0.2, dicke + 0.8, dicke + 2 * spiel, 0.05)],
                    cx=0.0, cy=c,
                )
            platte = platte.cut(cut)
    if int(p.get("Kabelkerben", 0)) == 1:
        # Eine U-Kerbe oben in der Mitte, 45°-Flanken (stützenfrei stehend druckbar)
        kb, kh = KABELKERBE_B, KABELKERBE_H
        z1 = hoehe
        pts = [
            (-kb / 2.0 - kh, 0.0, z1 + 0.2),
            (-kb / 2.0, 0.0, z1 - kh),
            (kb / 2.0, 0.0, z1 - kh),
            (kb / 2.0 + kh, 0.0, z1 + 0.2),
            (-kb / 2.0 - kh, 0.0, z1 + 0.2),
        ]
        # Profil in XZ, Extrusion in Y durch die komplette Dicke
        # Einfacher: Box mit Schrägen über Loft
        cut = loft_sections(
            [(hoehe - kh, kb, dicke + 2.0, 0.1), (hoehe + 0.4, kb + 2 * kh, dicke + 2.0, 0.1)]
        )
        platte = platte.cut(cut)
    return _als_solid(platte, "Trennwand")


def make_deckel_shape(p):
    """Deckel, der auf dem inneren Sims der Stapellippe sitzt."""
    aussen_x, aussen_y, innen_x, innen_y = _innenmasse(p)
    r_box = float(p["Eckenradius_Box"])
    spiel = float(p.get("Deckel_Spiel", DECKEL_SPIEL_STANDARD))
    d = float(p.get("Deckelstaerke", DECKEL_STAERKE_STANDARD))
    # Innere Auflageschulter der Lippe: aussen - 2*(P0+P2)
    shelf_x = aussen_x - 2.0 * (LIPPE_P0 + LIPPE_P2) - 2.0 * spiel
    shelf_y = aussen_y - 2.0 * (LIPPE_P0 + LIPPE_P2) - 2.0 * spiel
    if shelf_x < 12 or shelf_y < 12:
        raise ValueError("Deckel: Box zu klein für einen abnehmbaren Deckel.")
    r = _r_ok(shelf_x, shelf_y, max(0.8, r_box - (LIPPE_P0 + LIPPE_P2)))
    deckel = loft_sections([(0.0, shelf_x, shelf_y, r), (d, shelf_x, shelf_y, r)])
    # Leichte Fingervertiefung oben, nicht durchgehend
    vert_t = min(0.8, d * 0.4)
    vx = min(24.0, shelf_x * 0.45)
    vy = min(12.0, shelf_y * 0.35)
    if vx > 8 and vy > 6 and d - vert_t > 0.8:
        vert = loft_sections(
            [(d - vert_t, vx, vy, 3.0), (d + 0.2, vx + 1.6, vy + 1.6, 3.4)]
        )
        deckel = deckel.cut(vert)
    # Optional: zwei kleine Seiten-Nasen, die unter die Lippenschräge greifen
    if int(p.get("Verriegelungsart", 0)) == VERRIEGELUNG_DECKELRASTE:
        nasen_l = min(14.0, shelf_y * 0.25)
        nasen_h = 1.2
        nasen_t = 0.45
        for sign in (-1.0, 1.0):
            cx = sign * (shelf_x / 2.0 + nasen_t / 2.0 - 0.05)
            nase = loft_sections(
                [(-nasen_h, nasen_t, nasen_l, 0.2), (0.4, nasen_t, nasen_l, 0.2)],
                cx=cx, cy=0.0,
            )
            deckel = deckel.fuse(nase)
    # Auf die Oberkante der Boxwand setzen (z = Einheiten_Z * 7)
    z0 = int(p["Einheiten_Z"]) * float(p["Hoeheneinheit_mm"])
    deckel.translate(VEC(0, 0, z0))
    return _als_solid(deckel, "Deckel")


def make_phase4_box(params: dict):
    """Baut die Box über make_box_shape und ergänzt optionale Phase-4-Merkmale.

    Rückgabe: dict {name: Shape}, Hinweise (list).
    """
    p = phase4_params(**params)
    errors = [e for e in pruefe_parameter(p)
              if "Bodenstaerke_Platte" not in e and "Plattenbreite" not in e and "Plattentiefe" not in e]
    if errors:
        raise ValueError("Ungültige Phase-4-Parameter:\n- " + "\n- ".join(errors))

    heraus = int(p.get("Herausnehmbare_Trennwaende", 0))
    mit_deckel = int(p.get("Deckel", 0))
    art = int(p.get("Verriegelungsart", VERRIEGELUNG_RASTCLIP))
    fx = int(p["Fachanzahl_X"])
    fy = int(p["Fachanzahl_Y"])
    trenn = float(p["Trennwandstaerke"])
    hinweise = []

    # Feste Fächer nur, wenn die Trennwände nicht herausnehmbar sind
    box_params = dict(p)
    if heraus:
        box_params["Fachanzahl_X"] = 1
        box_params["Fachanzahl_Y"] = 1
        hinweise.append(
            "Herausnehmbare Trennwände: Nuten sitzen in Innenrippen, die Aussenwand bleibt geschlossen."
        )
    if art == VERRIEGELUNG_RASTCLIP:
        box_params["Stapellippe"] = 1
        hinweise.append("Verriegelungsart 1: Rastclip aus Phase 2 hakelt in die Plattennut und über die Stapellippe.")
    elif art == VERRIEGELUNG_DECKELRASTE:
        box_params["Stapellippe"] = 1
        box_params["Deckel"] = 1
        mit_deckel = 1
        hinweise.append("Verriegelungsart 2: Deckel mit seitlichen Nasen. Zum Abheben leicht federnd.")
    elif art == VERRIEGELUNG_KEINE:
        hinweise.append("Verriegelungsart 0: keine zusätzliche Verriegelung.")

    box = make_box_shape(box_params)
    aussen_x, aussen_y, innen_x, innen_y = _innenmasse(p)
    wand = float(p["Wandstaerke"])
    z_fuss = FUSS_PROFIL_HOEHE
    z_boden = z_fuss + float(p["Bodenstaerke_Box"])
    z_wand = int(p["Einheiten_Z"]) * float(p["Hoeheneinheit_mm"])
    shapes = {"Box": box}

    if heraus and (fx > 1 or fy > 1):
        ax = _fach_achsen(innen_x, fx, trenn)
        ay = _fach_achsen(innen_y, fy, trenn)
        rippen = None
        if ax:
            r1 = _rippen_mit_nut(innen_x, innen_y, z_boden, z_wand - 0.2, ax, "x", trenn,
                                 float(p.get("Trennwand_Spiel", NUT_SPIEL_STANDARD)), wand)
            rippen = r1 if rippen is None else rippen.fuse(r1)
        if ay:
            r2 = _rippen_mit_nut(innen_x, innen_y, z_boden, z_wand - 0.2, ay, "y", trenn,
                                 float(p.get("Trennwand_Spiel", NUT_SPIEL_STANDARD)), wand)
            rippen = r2 if rippen is None else rippen.fuse(r2)
        if rippen is not None:
            box = _als_solid(box.fuse(rippen).removeSplitter(), "Box")
            shapes["Box"] = box
        z_t0 = z_boden + 1.3  # über der 1,2-mm-Bodenkehle
        hoehe_t = (z_wand - 0.4) - z_t0
        # X-Trennwände (konstante X, Länge = innen_y)
        for i, c in enumerate(ax, 1):
            tw = make_trennwand(p, "x", innen_y, hoehe_t, kerben_achsen=ay or None)
            tw.translate(VEC(c, 0, z_t0))
            shapes["Trennwand_X_%d" % i] = tw
        for i, c in enumerate(ay, 1):
            tw = make_trennwand(p, "y", innen_x, hoehe_t, kerben_achsen=ax or None)
            # y-Richtung: Platte ist standardmässig in Y lang; um Z drehen
            tw.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 90)
            tw.translate(VEC(0, c, z_t0))
            # Y-Wände: Kerbe von unten an den Kreuzungen (X-Wände sind von oben gekerbt)
            if ax:
                kerbe_h = hoehe_t / 2.0 + 0.2
                for cx in ax:
                    cut = loft_sections(
                        [(z_t0 - 0.2, float(p["Trennwandstaerke"]) + 0.8,
                          float(p["Trennwandstaerke"]) + 2 * float(p.get("Trennwand_Spiel", NUT_SPIEL_STANDARD)),
                          0.05),
                         (z_t0 + kerbe_h, float(p["Trennwandstaerke"]) + 0.8,
                          float(p["Trennwandstaerke"]) + 2 * float(p.get("Trennwand_Spiel", NUT_SPIEL_STANDARD)),
                          0.05)],
                        cx=cx, cy=c,
                    )
                    tw = tw.cut(cut)
                shapes["Trennwand_Y_%d" % i] = _als_solid(tw, "Trennwand")
            else:
                shapes["Trennwand_Y_%d" % i] = tw
        hinweise.append(
            "Trennwände separat drucken und in die Nuten schieben. Spiel je Seite %.2f mm."
            % float(p.get("Trennwand_Spiel", NUT_SPIEL_STANDARD))
        )

    if int(p.get("Kabelkerben", 0)) == 1 and not heraus:
        # Kerben in festen Trennwänden: oben, Mitte jeder Trennwand
        ax = _fach_achsen(innen_x, fx, trenn)
        ay = _fach_achsen(innen_y, fy, trenn)
        kb, kh = KABELKERBE_B, KABELKERBE_H
        cuts = []
        for c in ax:
            cuts.append(loft_sections(
                [(z_wand - kh, kb, innen_y + 4, 0.2), (z_wand + 0.6, kb + 2 * kh, innen_y + 4, 0.2)],
                cx=c, cy=0.0,
            ))
        for c in ay:
            cuts.append(loft_sections(
                [(z_wand - kh, innen_x + 4, kb, 0.2), (z_wand + 0.6, innen_x + 4, kb + 2 * kh, 0.2)],
                cx=0.0, cy=c,
            ))
        for cut in cuts:
            box = box.cut(cut)
        shapes["Box"] = _als_solid(box, "Box")
        hinweise.append("Kabelkerben oben in den Trennwänden, 45° Öffnung, stützenfrei stehend druckbar.")

    if mit_deckel:
        if int(box_params.get("Stapellippe", 0)) != 1:
            raise ValueError("Ein abnehmbarer Deckel setzt Stapellippe=1 voraus.")
        shapes["Deckel"] = make_deckel_shape(p)
        hinweise.append(
            "Deckel sitzt auf dem inneren Lippen-Sims, Spiel %.2f mm je Seite. Separat drucken."
            % float(p.get("Deckel_Spiel", DECKEL_SPIEL_STANDARD))
        )
        # Passung Deckel/Box in der XY-Ebene prüfen lassen die Tests

    if not shapes["Box"].isValid():
        shapes["Box"] = _als_solid(shapes["Box"].removeSplitter(), "Box")
        if not shapes["Box"].isValid():
            raise RuntimeError("Phase-4-Box ist geometrisch ungültig.")
    return p, shapes, hinweise
