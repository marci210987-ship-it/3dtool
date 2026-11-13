# -*- coding: utf-8 -*-
"""Leichte Schalenversion von Stufenregal und Schrägeinsatz.

Neue Dateien, Phase-3-Vollkörper werden nicht verändert.
Drucklage: auf der glatten Aussenwand (X-Seite), dann stützenfrei.
Nutzseite (Oberseite und Front) geschlossen und abwischbar.
Unterseite offen, mit Rippen zur Aussteifung.
"""

from __future__ import annotations

import math

import Part

from hausraster_const import VERBINDER_SPIEL_STANDARD
from hausraster_geom import VEC, _als_solid
from hausraster_phase3_plan import plane_stufenregal, plane_schraege
from hausraster_phase3_geom import (
    _extrude_yz, _cut_all, _box, _joint_posts_and_pockets,
    _clip_pockets_on_edge, make_segmentverbinder_clip,
    SEGMENT_SCHIENE_B, SEGMENT_CLIP_H,
)

SCHALENWAND_STANDARD = 2.0  # im empfohlenen Band 1,6–2,0 mm
RIPPENABSTAND = 36.0
RIPPENBREITE = 2.0


def _wand(params):
    w = float((params or {}).get("Schalenwand", SCHALENWAND_STANDARD))
    if w < 1.5 or w > 2.2:
        raise ValueError("Schalenwand muss zwischen 1,6 und 2,0 mm liegen (zulässig 1,5–2,2).")
    return w


def _stufen_profil(plan, wand, lippe):
    """YZ-Profil: erste Stufe und Rückwand stehen auf z=0, Hohlraum unter den höheren Tritten (nach unten offen)."""
    p = plan.parameter
    st_h = float(p["Stufenhoehe"])
    st_t = float(p["Stufentiefe"])
    ebenen = plan.ebenen
    tiefe = plan.tiefe
    hinter = float(p.get("Hinterlippe", 25.0))
    hoehe = (ebenen - 1) * st_h + wand + hinter
    hinter_t = max(wand, 2.4)
    z = [wand + i * st_h for i in range(ebenen)]
    y0 = [i * st_t for i in range(ebenen)]
    y1 = [(i + 1) * st_t if i < ebenen - 1 else (tiefe - hinter_t) for i in range(ebenen)]
    y1[-1] = max(y0[-1] + 4.0, tiefe - hinter_t)

    pts = [(0.0, 0.0)]
    lh = min(lippe, max(4.0, st_h * 0.45))
    if lh > 0.8:
        pts += [(0.0, z[0] + lh), (wand, z[0] + lh), (wand, z[0])]
    else:
        pts.append((0.0, z[0]))
    for i in range(ebenen):
        if i > 0:
            pts.append((y0[i], z[i]))
        pts.append((y1[i], z[i]))
    pts += [
        (tiefe - hinter_t, hoehe),
        (tiefe, hoehe),
        (tiefe, 0.0),
        (tiefe - hinter_t, 0.0),
    ]
    # Innenseite der Rückwand hoch, unter den Tritten nach vorne, an der ersten Steigwand hinunter
    if ebenen >= 2:
        pts.append((tiefe - hinter_t, z[-1] - wand))
        for i in range(ebenen - 1, 0, -1):
            y_front = y0[i] + wand
            pts.append((y_front, z[i] - wand))
            if i > 1:
                # Steigwand hinunter auf die Unterseite der darunterliegenden Stufe, dann nach vorne
                pts.append((y_front, z[i - 1] - wand))
            else:
                pts.append((y_front, 0.0))
    return pts, hoehe


def make_stufenregal_schale_segment(plan, x0, x1, params=None):
    params = params or {}
    wand = _wand(params)
    lippe = float(params.get("Stufenlippe", plan.parameter.get("Stufenlippe", 12.0)))
    spiel = float(params.get("Verbinder_Spiel", VERBINDER_SPIEL_STANDARD))
    p = plan.parameter
    st_h = float(p["Stufenhoehe"])
    st_t = float(p["Stufentiefe"])
    glas_d = float(p["Glasdurchmesser"])
    glas_n = int(p["Glasanzahl"])
    gap = float(params.get("Glasabstand", 4.0))
    ebenen = plan.ebenen
    tiefe = plan.tiefe
    breite = plan.breite
    w = x1 - x0

    pts, hoehe = _stufen_profil(plan, wand, lippe)
    body = _extrude_yz(pts, 0.0, w)

    # Rippen quer (YZ), alle RIPPENABSTAND, 2 mm dick, unter den höheren Stufen
    cutters = []
    if ebenen >= 2 and w > 20:
        xs = []
        x = wand + 8.0
        while x < w - wand - 8.0:
            xs.append(x)
            x += RIPPENABSTAND
        if not xs:
            xs = [w / 2.0]
        z1 = wand + (ebenen - 1) * st_h
        for xr in xs:
            # Rippe: von der ersten Trittfläche bis zur Rückwand, Höhe bis Unterseite der jeweils höheren Stufe
            # als volles YZ-Rechteck unter dem inneren Hohlraum, dann auf die Schale zugeschnitten
            rib = _box(xr - RIPPENBREITE / 2.0, st_t, 0.0, xr + RIPPENBREITE / 2.0, tiefe - wand, z1)
            if rib is not None:
                rib = rib.common(body)
                # nur hinzufügen, wenn Material entsteht – wir fügen eine volle Rippe in den Hohlraum:
                # besser: Profil der Rippe als Steg von z=0 zur Unterseite, 45° nicht nötig bei Druck auf der Seite
                body = body.fuse(rib)

    # Flache Mulden, nicht durch die Schale
    pitch = glas_d + gap
    inner_w = breite - 2 * wand
    if glas_n < 1:
        glas_n = max(1, int(math.floor(inner_w / pitch + 1e-9)))
    if glas_n == 1:
        centers = [breite / 2.0]
    else:
        start = wand + glas_d / 2.0
        step = (breite - wand - glas_d / 2.0 - start) / max(1, glas_n - 1)
        centers = [start + i * step for i in range(glas_n)]
    r_mulde = min(10.0, glas_d * 0.18)
    tiefe_mulde = min(0.8, wand * 0.35)
    for i in range(ebenen):
        yy0 = i * st_t
        yy1 = (i + 1) * st_t if i < ebenen - 1 else tiefe
        z_t = wand + i * st_h
        cy = (yy0 + yy1) / 2.0
        for cx in centers:
            lx = cx - x0
            if lx < 8 or lx > w - 8:
                continue
            # Kugel leicht über der Fläche, nur eine flache Mulde
            sph = Part.makeSphere(r_mulde, VEC(lx, cy, z_t + r_mulde - tiefe_mulde))
            cutters.append(sph)

    # niedrige Seitenlippe an den wahren Aussenenden (oben auf den Tritten)
    for i in range(ebenen):
        yy0 = i * st_t + 0.2
        yy1 = ((i + 1) * st_t if i < ebenen - 1 else tiefe) - 0.2
        z_t = wand + i * st_h
        z1 = z_t + min(lippe, 8.0)
        if abs(x0) < 0.2:
            body = body.fuse(_box(0, yy0, z_t, wand, yy1, z1))
        if abs(x1 - breite) < 0.2:
            body = body.fuse(_box(w - wand, yy0, z_t, w, yy1, z1))

    stoesse = (x0 > 0.2, x1 < breite - 0.2)
    rails, pockets = _joint_posts_and_pockets(w, tiefe, hoehe, stoesse, spiel, back_only=True)
    for r in rails:
        if r is not None:
            body = body.fuse(r)
    body = _cut_all(body, cutters + pockets)
    body = _als_solid(body, "Stufenregal_Schale")
    if not body.isValid():
        body = body.removeSplitter()
        if not body.isValid():
            raise RuntimeError("Stufenregal-Schale ist geometrisch ungültig.")
    return body, hoehe


def make_schraege_schale_segment(plan, x0, x1, y0=0.0, y1=None, params=None):
    params = params or {}
    wand = _wand(params)
    p = plan.parameter
    nutz_x = float(p["Nutzbreite"])
    tiefe = float(p["Nutztiefe"])
    back_h = float(p["Hoehe_hinten"])
    glas_d = float(params.get("Glasdurchmesser", p.get("Glasdurchmesser", 55.0)))
    gap = float(params.get("Glasabstand", 4.0))
    reihen = int(p["Reihen"])
    spiel = float(params.get("Verbinder_Spiel", VERBINDER_SPIEL_STANDARD))
    front_h = min(8.0, max(3.0, back_h * 0.15))
    if back_h <= front_h + 2:
        front_h = max(2.0, back_h * 0.2)
    if y1 is None:
        y1 = tiefe
    wseg = x1 - x0
    d = y1 - y0
    ang = math.atan2(back_h - front_h, tiefe)
    deck_z = wand / max(0.35, math.cos(ang))  # senkrechte Dicke ≈ Schalenwand

    def z_at(y):
        return front_h + (back_h - front_h) * (y / max(tiefe, 1.0))

    z_v, z_h = z_at(y0), z_at(y1)
    zu_v = max(wand * 0.5, z_v - deck_z)
    zu_h = max(wand * 0.5, z_h - deck_z)
    # C-Profil: Front, Schräge, Rücken, offene Unterseite
    # Fussbreite vorne/hinten = wand
    fw = min(wand, d * 0.2)
    pts = [
        (0.0, 0.0),
        (0.0, z_v),
        (d, z_h),
        (d, 0.0),
        (d - fw, 0.0),
        (d - fw, zu_h),
        (fw, zu_v),
        (fw, 0.0),
    ]
    body = _extrude_yz(pts, 0.0, wseg)

    # Rippen im Hohlraum, Abstand RIPPENABSTAND, stehen auf z=0 bis zur Schrägenunterseite
    if wseg > 16 and d > 20:
        x = wand + 8.0
        while x < wseg - wand - 8.0:
            rib = _box(x - RIPPENBREITE / 2.0, fw, 0.0, x + RIPPENBREITE / 2.0, d - fw, max(zu_v, zu_h))
            if rib is not None:
                # auf den Hohlraum begrenzen: common mit einem vollen Keil unter der Schräge
                wedge = _extrude_yz(
                    [(fw, 0.0), (fw, zu_v), (d - fw, zu_h), (d - fw, 0.0)],
                    x - RIPPENBREITE / 2.0,
                    x + RIPPENBREITE / 2.0,
                )
                try:
                    rib = rib.common(wedge)
                    body = body.fuse(rib)
                except Exception:
                    pass
            x += RIPPENABSTAND

    cutters = []
    pitch = glas_d + gap
    inner = nutz_x - 2 * wand
    if reihen < 1:
        reihen = max(1, int(math.floor(inner / pitch + 1e-9)))
    if reihen == 1:
        centers = [nutz_x / 2.0]
    else:
        start = wand + glas_d / 2.0
        step = (nutz_x - wand - glas_d / 2.0 - start) / max(1, reihen - 1)
        centers = [start + i * step for i in range(reihen)]
    r_rinne = min(8.0, glas_d * 0.16)
    direction = VEC(0, math.cos(ang), math.sin(ang))
    normal = VEC(0, -math.sin(ang), math.cos(ang))
    bahn = math.hypot(tiefe, back_h - front_h)
    start_s = 12.0
    length = max(20.0, bahn - 24.0)
    # flache Rinne, bleibt über der Schalendicke
    offset = r_rinne - min(0.7, wand * 0.3)
    for cx in centers:
        lx = cx - x0
        if lx < 8 or lx > wseg - 8:
            continue
        base = VEC(lx, -y0, front_h) + direction * start_s + normal * offset
        cutters.append(Part.makeCylinder(r_rinne, length, base, direction))

    # Aussenwände als niedrige Leisten, nicht höher als back_h
    wall_h = 10.0

    def _slant_wall(xw0, xw1):
        poly = [
            (0.0, max(0.2, z_v - 0.05)),
            (0.0, min(z_v + wall_h, back_h)),
            (d, min(z_h + wall_h, back_h)),
            (d, max(0.2, z_h - 0.05)),
        ]
        return _extrude_yz(poly, xw0, xw1)

    if abs(x0) < 0.2:
        body = body.fuse(_slant_wall(0.0, wand))
    if abs(x1 - nutz_x) < 0.2:
        body = body.fuse(_slant_wall(wseg - wand, wseg))

    stoesse_x = (x0 > 0.2, x1 < nutz_x - 0.2)
    rails, pockets = _joint_posts_and_pockets(wseg, d, max(z_v, z_h), stoesse_x, spiel, back_only=True)
    for r in rails:
        if r is not None:
            body = body.fuse(r)
    z0p = 1.0
    post_w = SEGMENT_SCHIENE_B
    if y0 > 0.2:
        z1p = min(z_v - 0.3, z0p + SEGMENT_CLIP_H + 0.4)
        if z1p - z0p >= 4:
            rail = _box(0, 0, 0, wseg, post_w, z_v)
            if rail is not None:
                body = body.fuse(rail)
            for tsc in _clip_pockets_on_edge(wseg, z0p, z1p + 0.05, spiel, True):
                tsc.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 270)
                pockets.append(tsc)
    if y1 < tiefe - 0.2:
        z1p = min(z_h - 0.3, z0p + SEGMENT_CLIP_H + 0.4)
        if z1p - z0p >= 4:
            rail = _box(0, d - post_w, 0, wseg, d, z_h)
            if rail is not None:
                body = body.fuse(rail)
            for tsc in _clip_pockets_on_edge(wseg, z0p, z1p + 0.05, spiel, True):
                tsc.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 90)
                tsc.translate(VEC(wseg, d, 0))
                pockets.append(tsc)

    body = _cut_all(body, cutters + pockets)
    crop = Part.makeBox(wseg + 0.04, d + 0.04, max(z_v, z_h, back_h) + 20.0, VEC(-0.02, -0.02, -1.0))
    try:
        body = body.common(crop)
    except Exception:
        pass
    body = _als_solid(body, "Schraege_Schale")
    if not body.isValid():
        body = body.removeSplitter()
        if not body.isValid():
            raise RuntimeError("Schrägeinsatz-Schale ist geometrisch ungültig.")
    return body


def stufen_schale_teile(params):
    p = dict(params or {})
    wand = _wand(p)
    # Plan mit Boden = Schalenwand, damit die Stufenhöhen konsistent sind
    p.setdefault("Bodenstaerke", wand)
    plan = plane_stufenregal(p)
    if plan.ungueltig:
        raise ValueError("; ".join(plan.hinweise))
    shapes = {}
    x = 0.0
    hoehe = None
    for i, ws in enumerate(plan.segmente_x, 1):
        sh, hoehe = make_stufenregal_schale_segment(plan, x, x + ws, p)
        shapes["Segment_%d" % i] = sh
        x += ws
    if len(plan.segmente_x) > 1:
        shapes["Segmentverbinder"] = make_segmentverbinder_clip(p.get("Verbinder_Spiel"))
    plan.hoehe = hoehe if hoehe else plan.hoehe
    return plan, shapes


def schraege_schale_teile(params):
    p = dict(params or {})
    plan = plane_schraege(p)
    if plan.ungueltig:
        raise ValueError("; ".join(plan.hinweise))
    shapes = {}
    teile_x = plan.segmente_x
    teile_y = plan.segmente_y or [plan.tiefe]
    y = 0.0
    for iy, dy in enumerate(teile_y, 1):
        x = 0.0
        for ix, dx in enumerate(teile_x, 1):
            shapes["Segment_%d_%d" % (ix, iy)] = make_schraege_schale_segment(
                plan, x, x + dx, y, y + dy, p
            )
            x += dx
        y += dy
    if len(teile_x) * len(teile_y) > 1:
        shapes["Segmentverbinder"] = make_segmentverbinder_clip(p.get("Verbinder_Spiel"))
    return plan, shapes
