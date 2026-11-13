# -*- coding: utf-8 -*-
"""Geometrieerzeugung für Hausraster. Wird von FreeCADCmd ausgeführt."""

from __future__ import annotations

import math

import FreeCAD as App
import Part

from hausraster_const import (
    RASTER_MM,
    HOEHENEINHEIT_MM,
    PLATTE_PROFIL_P0,
    PLATTE_PROFIL_P1,
    PLATTE_PROFIL_P2,
    FUSS_PROFIL_P0,
    FUSS_PROFIL_P1,
    FUSS_PROFIL_P2,
    FUSS_PROFIL_HOEHE,
    ECKENRADIUS_BOX_OBEN,
    LIPPE_P0,
    LIPPE_P1,
    LIPPE_P2,
    LIPPE_HOEHE,
    VERBINDER_TIEFE,
    VERBINDER_KOPF_BREITE,
    VERBINDER_HALS_BREITE,
    VERBINDER_BODEN_ABSTAND,
    VERBINDER_OBEN_FREI,
    NUT_TIEFE,
    NUT_HOEHE,
    NUT_ECKENABSTAND,
    kasten_aussen,
    box_hoehe,
    plattenhoehe,
    default_params,
    pruefe_parameter,
)

VEC = App.Vector


def _r_ok(width, depth, radius, min_r=0.05):
    r = float(radius)
    r = min(r, width * 0.5 - 0.02, depth * 0.5 - 0.02)
    return max(min_r, r)


def rounded_rect_wire(width, depth, radius, z=0.0, cx=0.0, cy=0.0):
    """Geschlossener Draht: abgerundetes Rechteck, Mittelpunkt (cx, cy), CCW, 8 Kanten."""
    w, d = float(width), float(depth)
    r = _r_ok(w, d, radius)
    hx, hy = w / 2.0, d / 2.0

    def v(x, y):
        return VEC(cx + x, cy + y, z)

    p_bl = v(-hx + r, -hy)
    p_br = v(hx - r, -hy)
    p_rb = v(hx, -hy + r)
    p_rt = v(hx, hy - r)
    p_tr = v(hx - r, hy)
    p_tl = v(-hx + r, hy)
    p_lt = v(-hx, hy - r)
    p_lb = v(-hx, -hy + r)
    c_br = v(hx - r, -hy + r)
    c_tr = v(hx - r, hy - r)
    c_tl = v(-hx + r, hy - r)
    c_bl = v(-hx + r, -hy + r)

    def qarc(center, start, end, mid_deg, rad):
        a = math.radians(mid_deg)
        mid = VEC(center.x + rad * math.cos(a), center.y + rad * math.sin(a), z)
        return Part.Arc(start, mid, end).toShape()

    edges = [
        Part.makeLine(p_bl, p_br),
        qarc(c_br, p_br, p_rb, -45, r),
        Part.makeLine(p_rb, p_rt),
        qarc(c_tr, p_rt, p_tr, 45, r),
        Part.makeLine(p_tr, p_tl),
        qarc(c_tl, p_tl, p_lt, 135, r),
        Part.makeLine(p_lt, p_lb),
        qarc(c_bl, p_lb, p_bl, 225, r),
    ]
    wire = Part.Wire(edges)
    if not wire.isClosed():
        raise RuntimeError("rounded_rect_wire ist nicht geschlossen.")
    return wire


def loft_sections(sections, cx=0.0, cy=0.0):
    """sections: Liste (z, width, depth, radius). Erzeugt einen Volumenkörper."""
    if len(sections) < 2:
        raise ValueError("Loft braucht mindestens zwei Schnitte.")
    wires = [rounded_rect_wire(w, d, r, z=z, cx=cx, cy=cy) for z, w, d, r in sections]
    # Ruled-Loft: Profile bestehen aus Geraden und 45°-Abschnitten.
    # Ein glatter Loft interpoliert zu stark und bläht Masse auf.
    loft = Part.makeLoft(wires, True, True, False)
    solids = loft.Solids
    if not solids:
        loft = Part.makeLoft(wires, True, False, False)
        solids = loft.Solids
    if not solids:
        raise RuntimeError("Loft erzeugte keinen Volumenkörper.")
    if len(solids) == 1:
        return solids[0]
    fused = solids[0]
    for s in solids[1:]:
        fused = fused.fuse(s)
    return fused.removeSplitter() if hasattr(fused, "removeSplitter") else fused


def _als_solid(shape, name="shape"):
    if shape is None:
        raise RuntimeError("%s: leere Form." % name)
    if shape.ShapeType == "Solid":
        return shape
    if shape.Solids:
        if len(shape.Solids) == 1:
            return shape.Solids[0]
        fused = shape.Solids[0]
        for s in shape.Solids[1:]:
            fused = fused.fuse(s)
        if fused.Solids:
            return fused.Solids[0] if len(fused.Solids) == 1 else fused
    try:
        return Part.makeSolid(shape)
    except Exception as exc:
        raise RuntimeError("%s: kein Solid (%s): %s" % (name, shape.ShapeType, exc)) from exc


def _extrude_polygon(pts_xy, z0, z1):
    verts = [VEC(x, y, z0) for x, y in pts_xy]
    verts.append(verts[0])
    wire = Part.makePolygon(verts)
    face = Part.Face(wire)
    return face.extrude(VEC(0, 0, z1 - z0))


def _taschen_profil_schnitte(pitch, hoehe, boden, p0, p1, p2, r_aussen, extra_oben=0.2, grat=0.10):
    """Horizontale Schnitte der Aufnahmetasche, von oben nach unten (quadratisch).

    grat: schmale Plateau-Breite je Zelle (gesamt). Verhindert eine
    scharfe Gratschneide und macht den Boolean stabil. 0,10 mm bedeutet
    0,05 mm je Seite, Öffnung 41,90 mm statt 42,00 mm.
    """
    w_top = pitch - grat
    w_vert = w_top - 2.0 * p2
    w_bot = w_vert - 2.0 * p0
    r_top = max(0.2, r_aussen - grat / 2.0)
    r_vert = r_top - p2
    r_bot = r_vert - p0
    z_top = hoehe
    z_p2 = hoehe - p2
    z_vert = hoehe - p2 - p1
    z_p0 = hoehe - p2 - p1 - p0
    z_floor = boden

    def clamp_r(w, r):
        return _r_ok(w, w, r)

    # Über der Oberseite etwas weiter, damit der Boolean die Fläche sicher öffnet,
    # ohne die Tasche unterhalb der Oberkante zu verbreitern.
    schnitte = [
        (z_top + extra_oben, w_top, w_top, clamp_r(w_top, r_top)),
        (z_top, w_top, w_top, clamp_r(w_top, r_top)),
    ]
    if z_p2 >= z_floor - 1e-9:
        schnitte.append((z_p2, w_vert, w_vert, clamp_r(w_vert, r_vert)))
    if z_vert >= z_floor - 1e-9:
        schnitte.append((z_vert, w_vert, w_vert, clamp_r(w_vert, r_vert)))

    if z_p0 >= z_floor - 1e-9:
        schnitte.append((z_p0, w_bot, w_bot, clamp_r(w_bot, r_bot)))
        w_at_floor, r_at_floor = w_bot, r_bot
    else:
        t = (z_vert - z_floor) / (z_vert - z_p0) if (z_vert - z_p0) else 0.0
        t = max(0.0, min(1.0, t))
        w_at_floor = w_vert + t * (w_bot - w_vert)
        r_at_floor = r_vert + t * (r_bot - r_vert)

    if abs(schnitte[-1][0] - z_floor) > 1e-6:
        schnitte.append((z_floor, w_at_floor, w_at_floor, clamp_r(w_at_floor, r_at_floor)))

    cleaned = [schnitte[0]]
    for s in schnitte[1:]:
        if abs(s[0] - cleaned[-1][0]) > 1e-7:
            cleaned.append(s)
        else:
            cleaned[-1] = s
    return cleaned


def zelle_tasche(pitch, hoehe, boden, p0, p1, p2, r_aussen, cx, cy):
    schnitte = _taschen_profil_schnitte(pitch, hoehe, boden, p0, p1, p2, r_aussen)
    return loft_sections(schnitte, cx=cx, cy=cy)


def _verbinder_halb_polygon(tiefe, kopf, hals, extra_out=0.3):
    """Kante bei x=0, Platte in -X, Öffnung nach +X."""
    return [
        (extra_out, hals / 2.0),
        (extra_out, -hals / 2.0),
        (-tiefe, -kopf / 2.0),
        (-tiefe, kopf / 2.0),
    ]


def verbinder_tasche_solid(tiefe, kopf, hals, spiel, z0, z1):
    kopf_c = kopf + 2.0 * spiel
    hals_c = hals + 2.0 * spiel
    tiefe_c = tiefe + spiel
    return _extrude_polygon(_verbinder_halb_polygon(tiefe_c, kopf_c, hals_c), z0, z1)


def verbinder_clip_solid(tiefe, kopf, hals, z0, z1):
    pts = [
        (-tiefe, kopf / 2.0),
        (-tiefe, -kopf / 2.0),
        (0.0, -hals / 2.0),
        (tiefe, -kopf / 2.0),
        (tiefe, kopf / 2.0),
        (0.0, hals / 2.0),
    ]
    return _extrude_polygon(pts, z0, z1)


def _nut_cutter(length, tiefe, hoehe, z_mitte):
    z0 = z_mitte - hoehe / 2.0
    z1 = z_mitte + hoehe / 2.0
    return Part.makeBox(tiefe + 0.3, length, z1 - z0, VEC(-tiefe, -length / 2.0, z0))


def _platten_fehler(errors):
    keep = []
    for e in errors:
        if any(k in e for k in (
            "Bodenstaerke_Box", "Lichter Innenraum", "Fachanzahl",
            "Einheiten_Z", "Wandstaerke",
        )):
            continue
        keep.append(e)
    return keep


def make_plate_shape(params: dict) -> Part.Shape:
    p = default_params(**params)
    errors = _platten_fehler(pruefe_parameter(p))
    if errors:
        raise ValueError("Ungültige Plattenparameter:\n- " + "\n- ".join(errors))

    nx = int(p["Einheiten_X"])
    ny = int(p["Einheiten_Y"])
    raster = float(p["Raster_mm"])
    boden = float(p["Bodenstaerke_Platte"])
    hoehe = plattenhoehe(boden)
    rand_l = float(p["Rand_X_links"])
    rand_r = float(p["Rand_X_rechts"])
    rand_f = float(p["Rand_Y_vorne"])
    rand_b = float(p["Rand_Y_hinten"])
    r_aussen = float(p["Eckenradius_Platte"])
    p0 = float(p["Profil_Platte_P0"])
    p1 = float(p["Profil_Platte_P1"])
    p2 = float(p["Profil_Platte_P2"])
    verbinder = int(p["Verbinder"])
    verriegelung = int(p["Verriegelung"])
    spiel_v = float(p["Verbinder_Spiel"])

    breite = nx * raster + rand_l + rand_r
    tiefe = ny * raster + rand_f + rand_b
    if breite > 256 + 1e-6 or tiefe > 256 + 1e-6:
        raise ValueError("Platte %s x %s mm passt nicht in den P2S-Bauraum." % (breite, tiefe))
    r_aussen_platte = min(r_aussen, (min(breite, tiefe) / 2.0) - 0.2)
    cx0 = -breite / 2.0
    cy0 = -tiefe / 2.0

    korpus = loft_sections(
        [
            (0.0, breite, tiefe, r_aussen_platte),
            (hoehe, breite, tiefe, r_aussen_platte),
        ],
        cx=0.0,
        cy=0.0,
    )

    cutters = []
    for i in range(nx):
        for j in range(ny):
            cx = cx0 + rand_l + (i + 0.5) * raster
            cy = cy0 + rand_f + (j + 0.5) * raster
            cutters.append(zelle_tasche(raster, hoehe, boden, p0, p1, p2, r_aussen, cx, cy))

    if verbinder:
        z0 = boden + VERBINDER_BODEN_ABSTAND
        z1 = hoehe + 0.05
        if z1 - z0 > 1.0:
            def _rippen_indizes(n_entlang):
                """Taschen gehören auf die massiven Rippen zwischen den Zellen,
                nicht in die Zellmitte (die ist bereits die Rastervertiefung).
                Eine Kante mit nur einer Zelle hat keine Rippe; dort gibt es
                keinen Plattenverbinder."""
                return list(range(1, n_entlang))  # 1 .. n-1

            def place_pockets(n_entlang, rand_aussen_null, origin_fn, rotation_deg):
                if not rand_aussen_null:
                    return
                for k in _rippen_indizes(n_entlang):
                    tasche = verbinder_tasche_solid(
                        VERBINDER_TIEFE, VERBINDER_KOPF_BREITE, VERBINDER_HALS_BREITE, spiel_v, z0, z1
                    )
                    if rotation_deg:
                        tasche.rotate(VEC(0, 0, 0), VEC(0, 0, 1), rotation_deg)
                    tasche.translate(origin_fn(k))
                    cutters.append(tasche)

            # origin_fn(k) mit k an der Rippe: k * raster von der ersten Zellkante
            place_pockets(
                ny, rand_r <= 0.05,
                lambda k: VEC(cx0 + rand_l + nx * raster, cy0 + rand_f + k * raster, 0),
                0,
            )
            place_pockets(
                ny, rand_l <= 0.05,
                lambda k: VEC(cx0 + rand_l, cy0 + rand_f + k * raster, 0),
                180,
            )
            place_pockets(
                nx, rand_b <= 0.05,
                lambda k: VEC(cx0 + rand_l + k * raster, cy0 + rand_f + ny * raster, 0),
                90,
            )
            place_pockets(
                nx, rand_f <= 0.05,
                lambda k: VEC(cx0 + rand_l + k * raster, cy0 + rand_f, 0),
                270,
            )

    if verriegelung:
        z_m = boden + (hoehe - boden) * 0.45

        def add_nut(length, pos, rot):
            nut_len = max(8.0, length - 2 * NUT_ECKENABSTAND)
            if nut_len < 8.0:
                return
            nut = _nut_cutter(nut_len, NUT_TIEFE, NUT_HOEHE, z_m)
            if rot:
                nut.rotate(VEC(0, 0, 0), VEC(0, 0, 1), rot)
            nut.translate(pos)
            cutters.append(nut)

        add_nut(tiefe, VEC(breite / 2.0, 0, 0), 0)
        add_nut(tiefe, VEC(-breite / 2.0, 0, 0), 180)
        add_nut(breite, VEC(0, tiefe / 2.0, 0), 90)
        add_nut(breite, VEC(0, -tiefe / 2.0, 0), 270)

    cutter = cutters[0]
    for c in cutters[1:]:
        cutter = cutter.fuse(c)
    platte = korpus.cut(cutter)
    # Überstand über der Sollhöhe abschneiden
    oben = Part.makeBox(breite + 10.0, tiefe + 10.0, 5.0, VEC(-breite / 2.0 - 5.0, -tiefe / 2.0 - 5.0, hoehe))
    platte = platte.cut(oben)
    platte = _als_solid(platte, "Grundplatte")
    if not platte.isValid():
        platte = platte.removeSplitter()
        if not platte.isValid():
            raise RuntimeError("Grundplatte ist nach dem Zuschnitt geometrisch ungültig.")
    return platte


def _fuss_schnitte(aussen_oben, r_oben, extra_spiel=0.0):
    top = aussen_oben - 2.0 * extra_spiel
    p0, p1, p2 = FUSS_PROFIL_P0, FUSS_PROFIL_P1, FUSS_PROFIL_P2
    mid = top - 2.0 * p2
    bot = mid - 2.0 * p0
    r_top = _r_ok(top, top, r_oben)
    r_mid = _r_ok(mid, mid, r_oben - p2)
    r_bot = _r_ok(bot, bot, r_oben - p2 - p0)
    return [
        (0.0, bot, bot, r_bot),
        (p0, mid, mid, r_mid),
        (p0 + p1, mid, mid, r_mid),
        (p0 + p1 + p2, top, top, r_top),
    ]


def einzel_fuss(cx, cy, aussen_oben, r_oben, extra_spiel=0.0):
    return loft_sections(_fuss_schnitte(aussen_oben, r_oben, extra_spiel), cx=cx, cy=cy)


def _innen_hohlraum(innen_x, innen_y, z0, z1, r_innen, boden_fillet=1.2):
    r = _r_ok(innen_x, innen_y, r_innen)
    schnitte = []
    if boden_fillet > 0.05 and z1 - z0 > boden_fillet + 0.4:
        innen_bot_x = max(6.0, innen_x - 2 * boden_fillet)
        innen_bot_y = max(6.0, innen_y - 2 * boden_fillet)
        r_bot = _r_ok(innen_bot_x, innen_bot_y, max(0.2, r - boden_fillet))
        schnitte.append((z0, innen_bot_x, innen_bot_y, r_bot))
        schnitte.append((z0 + boden_fillet, innen_x, innen_y, r))
    else:
        schnitte.append((z0, innen_x, innen_y, r))
    schnitte.append((z1 + 0.2, innen_x, innen_y, r))
    return loft_sections(schnitte)


def _lippen_tasche_rechteck(aussen_x, aussen_y, r_aussen, z0, z1, p0, p1, p2):
    w_top_x, w_top_y = aussen_x, aussen_y
    w_vert_x, w_vert_y = aussen_x - 2 * p2, aussen_y - 2 * p2
    w_bot_x, w_bot_y = w_vert_x - 2 * p0, w_vert_y - 2 * p0
    r_top = r_aussen
    r_vert = r_aussen - p2
    r_bot = r_aussen - p2 - p0
    z_top = z1
    schnitte = [
        (z_top + 0.1, w_top_x, w_top_y, _r_ok(w_top_x, w_top_y, r_top)),
        (z_top, w_top_x, w_top_y, _r_ok(w_top_x, w_top_y, r_top)),
        (z_top - p2, w_vert_x, w_vert_y, _r_ok(w_vert_x, w_vert_y, r_vert)),
        (z_top - p2 - p1, w_vert_x, w_vert_y, _r_ok(w_vert_x, w_vert_y, r_vert)),
    ]
    z_p0 = z_top - p2 - p1 - p0
    if z_p0 > z0 + 1e-6:
        schnitte.append((z_p0, w_bot_x, w_bot_y, _r_ok(w_bot_x, w_bot_y, r_bot)))
    schnitte.append((z0, w_bot_x, w_bot_y, _r_ok(w_bot_x, w_bot_y, r_bot)))
    # identische Z-Lagen entfernen (sonst scheitert der Loft)
    cleaned = [schnitte[0]]
    for s in schnitte[1:]:
        if abs(s[0] - cleaned[-1][0]) > 0.05:
            cleaned.append(s)
        else:
            cleaned[-1] = s
    return cleaned


def _stapel_lippe(aussen_x, aussen_y, r_aussen, z_basis, wand, innen_x, innen_y, r_innen):
    z0 = z_basis
    z1 = z_basis + LIPPE_HOEHE
    aussen = loft_sections(
        [(z0, aussen_x, aussen_y, r_aussen), (z1, aussen_x, aussen_y, r_aussen)]
    )
    p0, p1, p2 = LIPPE_P0, LIPPE_P1, LIPPE_P2
    schnitte = _lippen_tasche_rechteck(aussen_x, aussen_y, r_aussen, z0, z1, p0, p1, p2)
    tasche = loft_sections(schnitte)
    lippe = aussen.cut(tasche)

    lippen_tiefe = p0 + p2
    if wand + 0.05 < lippen_tiefe:
        stufe = lippen_tiefe - wand
        z_st_0 = z0 - stufe
        aussen_st_x = min(aussen_x, innen_x + 2 * stufe)
        aussen_st_y = min(aussen_y, innen_y + 2 * stufe)
        stuetze_aussen = loft_sections(
            [
                (z_st_0, innen_x, innen_y, _r_ok(innen_x, innen_y, r_innen)),
                (z0, aussen_st_x, aussen_st_y, _r_ok(aussen_st_x, aussen_st_y, r_innen + stufe)),
            ]
        )
        stuetze_loch = loft_sections(
            [
                (z_st_0 - 0.05, innen_x, innen_y, _r_ok(innen_x, innen_y, r_innen)),
                (z0 + 0.05, innen_x, innen_y, _r_ok(innen_x, innen_y, r_innen)),
            ]
        )
        stuetze = stuetze_aussen.cut(stuetze_loch)
        lippe = lippe.fuse(stuetze)
    return _als_solid(lippe, "Stapellippe")


def _faecher_trenner(innen_x, innen_y, fx, fy, trenn, z0, z1):
    if fx <= 1 and fy <= 1:
        return None
    teile = []
    r_w = min(0.3, trenn / 2.0 - 0.05) if trenn > 0.2 else 0.05
    if fx > 1:
        nutz = innen_x - (fx - 1) * trenn
        fach = nutz / fx
        for i in range(fx - 1):
            cx = -innen_x / 2.0 + fach + trenn / 2.0 + i * (fach + trenn)
            teile.append(loft_sections(
                [(z0, trenn, innen_y, r_w), (z1, trenn, innen_y, r_w)], cx=cx, cy=0.0
            ))
    if fy > 1:
        nutz = innen_y - (fy - 1) * trenn
        fach = nutz / fy
        for i in range(fy - 1):
            cy = -innen_y / 2.0 + fach + trenn / 2.0 + i * (fach + trenn)
            teile.append(loft_sections(
                [(z0, innen_x, trenn, r_w), (z1, innen_x, trenn, r_w)], cx=0.0, cy=cy
            ))
    if not teile:
        return None
    fused = teile[0]
    for t in teile[1:]:
        fused = fused.fuse(t)
    return fused


def make_box_shape(params: dict) -> Part.Shape:
    p = default_params(**params)
    errors = pruefe_parameter(p)
    # Plattenboden-Fehler sind hier irrelevant
    errors = [e for e in errors if "Bodenstaerke_Platte" not in e and "Plattenbreite" not in e and "Plattentiefe" not in e]
    if errors:
        raise ValueError("Ungültige Boxparameter:\n- " + "\n- ".join(errors))

    nx = int(p["Einheiten_X"])
    ny = int(p["Einheiten_Y"])
    ez = int(p["Einheiten_Z"])
    raster = float(p["Raster_mm"])
    wand = float(p["Wandstaerke"])
    boden_b = float(p["Bodenstaerke_Box"])
    spiel = float(p["Passungsspiel"])
    lippe_an = int(p["Stapellippe"])
    fx = int(p["Fachanzahl_X"])
    fy = int(p["Fachanzahl_Y"])
    trenn = float(p["Trennwandstaerke"])
    r_box = float(p["Eckenradius_Box"])
    r_innen_soll = float(p["Innenradius"])

    aussen_x = kasten_aussen(nx, spiel)
    aussen_y = kasten_aussen(ny, spiel)
    r_aussen = _r_ok(aussen_x, aussen_y, r_box)
    z_fuss = FUSS_PROFIL_HOEHE
    z_boden = z_fuss + boden_b
    z_wand = ez * float(p["Hoeheneinheit_mm"])
    if z_boden >= z_wand - 0.4:
        raise ValueError("Boxboden lässt keine nutzbare Innenhöhe.")

    # Füsse je Zelle, oben jeweils 41,5 mm minus Extra-Spiel (nicht die volle Boxbreite)
    fuss_oben = raster - 0.5 - 2.0 * spiel
    fuesse = []
    for i in range(nx):
        for j in range(ny):
            cx = (i + 0.5) * raster - (nx * raster) / 2.0
            cy = (j + 0.5) * raster - (ny * raster) / 2.0
            fuesse.append(einzel_fuss(cx, cy, fuss_oben, r_box, extra_spiel=0.0))
    fusswerk = fuesse[0]
    for f in fuesse[1:]:
        fusswerk = fusswerk.fuse(f)

    korpus = loft_sections(
        [(z_fuss, aussen_x, aussen_y, r_aussen), (z_wand, aussen_x, aussen_y, r_aussen)]
    )
    box = fusswerk.fuse(korpus)

    innen_x = aussen_x - 2 * wand
    innen_y = aussen_y - 2 * wand
    r_innen = _r_ok(innen_x, innen_y, min(r_innen_soll, r_aussen - wand))
    hohl = _innen_hohlraum(innen_x, innen_y, z_boden, z_wand + (LIPPE_HOEHE if lippe_an else 0.4), r_innen)
    box = box.cut(hohl)

    if fx > 1 or fy > 1:
        trenner = _faecher_trenner(innen_x, innen_y, fx, fy, trenn, z_boden, z_wand - 0.2)
        if trenner is not None:
            box = box.fuse(trenner)

    if lippe_an:
        lippe = _stapel_lippe(aussen_x, aussen_y, r_aussen, z_wand, wand, innen_x, innen_y, r_innen)
        box = box.fuse(lippe)

    box = _als_solid(box, "Box")
    if not box.isValid():
        box = box.removeSplitter()
        if not box.isValid():
            raise RuntimeError("Box ist nach dem Zuschnitt geometrisch ungültig.")
    return box


def make_fuss_stumpf_shape(params: dict) -> Part.Shape:
    """Kurzer Fuss mit Griffplatte, wenig Filament, für den Passungstest."""
    p = default_params(**params)
    spiel = float(p["Passungsspiel"])
    raster = float(p["Raster_mm"])
    r_box = float(p["Eckenradius_Box"])
    fuss_oben = raster - 0.5 - 2.0 * spiel
    fuss = einzel_fuss(0, 0, fuss_oben, r_box, extra_spiel=0.0)
    # Kleiner Griff über dem Fuss, sparsam im Filamentverbrauch
    griff_d = 16.0
    z0 = FUSS_PROFIL_HOEHE
    griff = loft_sections(
        [(z0, griff_d, griff_d, _r_ok(griff_d, griff_d, 4)), (z0 + 2.4, griff_d, griff_d, _r_ok(griff_d, griff_d, 4))]
    )
    return _als_solid(fuss.fuse(griff), "Fussstumpf")


def make_verbinder_clip_shape(params: dict, spiel=None, drucklage=True) -> Part.Shape:
    """Ein einzelner Plattenverbinder. 'spiel' wird hier NICHT abgezogen –
    das Spiel sitzt in der Tasche.

    drucklage=True (Standard): der Clip wird auf Z=0 gelegt, damit er ohne
    Stützen gedruckt werden kann. Für digitale Fügeprüfungen drucklage=False
    verwenden, dann bleibt der Clip auf der Taschenhöhe (z0 über der Platte).
    """
    p = default_params(**params)
    boden = float(p["Bodenstaerke_Platte"])
    hoehe = plattenhoehe(boden)
    z0 = boden + VERBINDER_BODEN_ABSTAND + 0.1
    z1 = hoehe - VERBINDER_OBEN_FREI
    if z1 - z0 < 1.2:
        raise ValueError("Für den Verbinderclip bleibt zu wenig Höhe.")
    sh = _als_solid(
        verbinder_clip_solid(VERBINDER_TIEFE, VERBINDER_KOPF_BREITE, VERBINDER_HALS_BREITE, z0, z1),
        "Plattenverbinder",
    )
    if drucklage:
        sh = sh.copy()
        sh.translate(VEC(0, 0, -sh.BoundBox.ZMin))
    return sh


def make_rastclip_shape(params: dict) -> Part.Shape:
    """C-förmiger Kantenclip: hakt in die Aussennut der Platte und über die Boxlippe."""
    p = default_params(**params)
    hoehe_p = plattenhoehe(float(p["Bodenstaerke_Platte"]))
    hoehe_b = box_hoehe(int(p["Einheiten_Z"]), bool(int(p["Stapellippe"])))
    spiel = 0.15
    boden = float(p["Bodenstaerke_Platte"])
    nut_z_m = boden + (hoehe_p - boden) * 0.45
    nut_z0 = nut_z_m - NUT_HOEHE / 2.0
    nut_z1 = nut_z_m + NUT_HOEHE / 2.0

    t = 1.2
    gap = 0.2
    hook_in = NUT_TIEFE - spiel
    hook_over = 2.2
    hook_down = 1.4
    z_bottom = max(0.0, nut_z0 - 0.8)
    z_top = hoehe_p + hoehe_b + 0.6
    x_in = gap
    x_out = gap + t
    x_hook = -hook_in

    pts = [
        (x_hook, nut_z0 + spiel),
        (x_hook, nut_z1 - spiel),
        (x_in, nut_z1 - spiel),
        (x_in, z_top - hook_down),
        (-hook_over, z_top - hook_down),
        (-hook_over, z_top),
        (x_out, z_top),
        (x_out, z_bottom),
        (x_hook, z_bottom),
    ]
    # Profil liegt in XZ; durch Extrusion in Y entsteht der Clip.
    # _extrude_polygon arbeitet in XY, daher zuerst in XY zeichnen (X, Z als Y)
    # und anschliessend um X um 90° drehen? Einfacher: Polygon in der XZ-Ebene bauen.
    verts = [VEC(x, 0, z) for x, z in pts]
    verts.append(verts[0])
    wire = Part.makePolygon(verts)
    face = Part.Face(wire)
    breite = 12.0
    clip = face.extrude(VEC(0, breite, 0))
    clip.translate(VEC(0, -breite / 2.0, 0))
    return _als_solid(clip, "Rastclip")


def make_passung_verbinder_shape(params: dict):
    """Gibt (leiste_mit_taschen, liste_der_clips, spiele) zurück.

    Fünf Spielstufen 0,10 / 0,15 / 0,20 / 0,25 / 0,30 mm je Seite.
    """
    p = default_params(**params)
    boden = float(p["Bodenstaerke_Platte"])
    hoehe = plattenhoehe(boden)
    spiele = [0.10, 0.15, 0.20, 0.25, 0.30]
    abstand = 22.0
    rand = 12.0
    leiste_l = 2 * rand + (len(spiele) - 1) * abstand
    leiste_b = VERBINDER_TIEFE + 6.0
    r = 2.0
    leiste = loft_sections(
        [(0.0, leiste_b, leiste_l, r), (hoehe, leiste_b, leiste_l, r)],
        cx=0.0,
        cy=0.0,
    )
    z0 = boden + VERBINDER_BODEN_ABSTAND
    z1 = hoehe + 0.05
    # Taschen öffnen nach +X an der rechten Kante der Leiste (x = leiste_b/2)
    cutters = []
    y0 = -leiste_l / 2.0 + rand
    for i, sp in enumerate(spiele):
        tasche = verbinder_tasche_solid(
            VERBINDER_TIEFE, VERBINDER_KOPF_BREITE, VERBINDER_HALS_BREITE, sp, z0, z1
        )
        tasche.translate(VEC(leiste_b / 2.0, y0 + i * abstand, 0))
        cutters.append(tasche)
        # Markierungsnoppen: Anzahl = Stufenindex + 1, auf der Oberseite
        # (werden nicht ausgeschnitten, sondern später als separate Körper
        # auf die Clips gesetzt). Auf der Leiste: kleine Senkungen.
        for n in range(i + 1):
            typ = Part.makeCylinder(0.7, 0.4, VEC(
                -leiste_b / 2.0 + 2.5,
                y0 + i * abstand + (n - i / 2.0) * 2.2,
                hoehe - 0.4,
            ))
            cutters.append(typ)

    cutter = cutters[0]
    for c in cutters[1:]:
        cutter = cutter.fuse(c)
    leiste = _als_solid(leiste.cut(cutter), "Verbinder-Leiste")

    clips = []
    zc0 = z0 + 0.1
    zc1 = hoehe - VERBINDER_OBEN_FREI
    for i, sp in enumerate(spiele):
        clip = verbinder_clip_solid(VERBINDER_TIEFE, VERBINDER_KOPF_BREITE, VERBINDER_HALS_BREITE, zc0, zc1)
        # Noppen oben zur Identifikation der Spielstufe (1..5)
        noppen = []
        for n in range(i + 1):
            noppen.append(Part.makeCylinder(
                0.8, 1.0,
                VEC(0, (n - i / 2.0) * 2.2, zc1),
            ))
        if noppen:
            nunion = noppen[0]
            for n in noppen[1:]:
                nunion = nunion.fuse(n)
            clip = clip.fuse(nunion)
        # neben die Leiste legen, gleicher Y-Abstand
        clip.translate(VEC(leiste_b / 2.0 + VERBINDER_TIEFE + 10.0, y0 + i * abstand, -zc0))
        # auf z=0 setzen (druckbar flach)
        clips.append(_als_solid(clip, "Clip-%s" % sp))

    return leiste, clips, spiele


def plate_outer_size(params: dict):
    p = default_params(**params)
    nx, ny = int(p["Einheiten_X"]), int(p["Einheiten_Y"])
    raster = float(p["Raster_mm"])
    breite = nx * raster + float(p["Rand_X_links"]) + float(p["Rand_X_rechts"])
    tiefe = ny * raster + float(p["Rand_Y_vorne"]) + float(p["Rand_Y_hinten"])
    return breite, tiefe, plattenhoehe(float(p["Bodenstaerke_Platte"]))


def box_outer_size(params: dict):
    p = default_params(**params)
    return (
        kasten_aussen(int(p["Einheiten_X"]), float(p["Passungsspiel"])),
        kasten_aussen(int(p["Einheiten_Y"]), float(p["Passungsspiel"])),
        box_hoehe(int(p["Einheiten_Z"]), bool(int(p["Stapellippe"]))),
    )


def seated_box_z_on_plate(params_plate: dict) -> float:
    """Theoretische Sitz-Z-Lage: Fuss steht auf dem Taschenboden."""
    p = default_params(**params_plate)
    return float(p["Bodenstaerke_Platte"])
