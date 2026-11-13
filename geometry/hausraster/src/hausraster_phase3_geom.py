# -*- coding: utf-8 -*-
"""Geometrie für Bestecksortierer und Gewürzorganizer. Nur von FreeCADCmd ausführen."""

from __future__ import annotations

import math

import FreeCAD as App
import Part

from hausraster_const import (
    RASTER_MM, FUSS_PROFIL_HOEHE, ECKENRADIUS_BOX_OBEN,
    VERBINDER_TIEFE, VERBINDER_KOPF_BREITE, VERBINDER_HALS_BREITE,
    VERBINDER_SPIEL_STANDARD, VERBINDER_BODEN_ABSTAND,
)
from hausraster_geom import (
    VEC, loft_sections, _als_solid, _r_ok, _extrude_polygon,
    verbinder_tasche_solid, verbinder_clip_solid, einzel_fuss,
)
from hausraster_phase3_plan import (
    plane_besteck, plane_stufenregal, plane_schraege, plane_halter,
    BAURAUM_SICHER,
)

# Höherer Segmentclip als der 5,45-mm-Plattenclip, gleiches XY-Profil
SEGMENT_CLIP_H = 8.0
SEGMENT_SCHIENE_H = 12.0
SEGMENT_SCHIENE_B = 10.0
ECKENRADIUS_EINSATZ = 4.0


def _box(x0, y0, z0, x1, y1, z1):
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        return None
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, VEC(x0, y0, z0))


def _fillet_outer_corners(solid, w, d, h, r, corners):
    """corners: Menge von ('sw','se','ne','nw') in lokaler XY, Ursprung vorne links."""
    if r < 0.4 or not corners:
        return solid
    r = min(r, w / 2.0 - 0.2, d / 2.0 - 0.2)
    wanted = []
    pos = {
        "sw": (0.0, 0.0),
        "se": (w, 0.0),
        "ne": (w, d),
        "nw": (0.0, d),
    }
    for e in solid.Edges:
        v = e.Vertexes
        if len(v) < 2:
            continue
        if abs(v[0].X - v[1].X) > 1e-4 or abs(v[0].Y - v[1].Y) > 1e-4:
            continue
        if abs(v[0].Z - v[1].Z) < h * 0.5:
            continue
        x, y = v[0].X, v[0].Y
        for name in corners:
            px, py = pos[name]
            if abs(x - px) < 0.2 and abs(y - py) < 0.2:
                wanted.append(e)
                break
    if not wanted:
        return solid
    try:
        return solid.makeFillet(r, wanted)
    except Exception:
        return solid


def _pocket_loft(lx, ly, z0, z1, radius, kehle=2.0):
    if lx < 4 or ly < 4 or z1 <= z0:
        return None
    r = _r_ok(lx, ly, radius)
    schnitte = []
    if kehle > 0.2 and z1 - z0 > kehle + 1.0:
        k = min(kehle, (z1 - z0) * 0.35, lx / 4.0, ly / 4.0)
        lx0, ly0 = max(6.0, lx - 2 * k), max(6.0, ly - 2 * k)
        schnitte.append((z0, lx0, ly0, _r_ok(lx0, ly0, max(0.4, r - k))))
        schnitte.append((z0 + k, lx, ly, r))
    else:
        schnitte.append((z0, lx, ly, r))
    schnitte.append((z1, lx, ly, r))
    return loft_sections(schnitte)


def _joint_is_divider(plan, achse, position, tol=1.0):
    for t in plan.trenner:
        if t.achse == achse and abs(t.position - position) <= (t.dicke / 2.0 + tol):
            return True
    return False


def _clip_pockets_on_edge(length, z0, z1, spiel, inward_is_neg_x=True):
    """Taschen entlang einer Kante der Länge length, lokale Kante bei x=0, Platte in -X."""
    if length < 24 or z1 - z0 < 3:
        return []
    n = max(1, int(math.floor((length - 30.0) / 80.0)) + 1)
    # gleichmässig, Abstand zu den Enden mindestens 16 mm
    if n == 1:
        ys = [length / 2.0]
    else:
        span = length - 32.0
        ys = [16.0 + i * span / (n - 1) for i in range(n)]
    out = []
    for y in ys:
        tasche = verbinder_tasche_solid(
            VERBINDER_TIEFE, VERBINDER_KOPF_BREITE, VERBINDER_HALS_BREITE, spiel, z0, z1
        )
        if not inward_is_neg_x:
            tasche.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 180)
        tasche.translate(VEC(0, y, 0))
        out.append(tasche)
    return out


def make_segmentverbinder_clip(spiel=None, hoehe=None, drucklage=True):
    """Einzelner Segmentclip, gleiches Profil wie der Plattenverbinder, höhere Ausführung."""
    sp = VERBINDER_SPIEL_STANDARD if spiel is None else float(spiel)
    h = SEGMENT_CLIP_H if hoehe is None else float(hoehe)
    # Clip bleibt nominal, Spiel sitzt in der Tasche (wie Phase 2)
    z0, z1 = 0.0, h
    clip = verbinder_clip_solid(VERBINDER_TIEFE, VERBINDER_KOPF_BREITE, VERBINDER_HALS_BREITE, z0, z1)
    return _als_solid(clip, "Segmentverbinder")


def make_passung_segmentverbinder(params=None):
    """Zwei kurze Schienen plus Clip, wenig Filament."""
    spiel = VERBINDER_SPIEL_STANDARD
    if params:
        spiel = float(params.get("Verbinder_Spiel", spiel))
    h = SEGMENT_SCHIENE_H
    b = 28.0
    l = 50.0
    z0 = 1.0
    z1 = z0 + SEGMENT_CLIP_H + 0.4
    schienen = []
    for side, xoff, rot in ((0, 0.0, 0), (1, 40.0, 180)):
        body = loft_sections([(0.0, b, l, 2.0), (h, b, l, 2.0)], cx=0, cy=0)
        tasche = verbinder_tasche_solid(
            VERBINDER_TIEFE, VERBINDER_KOPF_BREITE, VERBINDER_HALS_BREITE, spiel, z0, z1 + 0.05
        )
        # rechte Kante der ersten Schiene, linke der zweiten
        if side == 0:
            tasche.translate(VEC(b / 2.0, 0, 0))
        else:
            tasche.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 180)
            tasche.translate(VEC(-b / 2.0, 0, 0))
        body = body.cut(tasche)
        body.translate(VEC(xoff, 0, 0))
        schienen.append(_als_solid(body, "Schiene%d" % side))
    clip = make_segmentverbinder_clip(spiel)
    # Clip zwischen die Schienen legen, auf z=0
    clip.translate(VEC(20.0, 0, 0))
    return schienen[0], schienen[1], clip


def default_besteck_params(**overrides):
    p = {
        "Schubladenbreite": 450.0,
        "Schubladentiefe": 350.0,
        "Verfuegbare_Hoehe": 80.0,
        "Schubladenspiel": 1.0,
        "Einsatzhoehe": 45.0,
        "Wandstaerke": 1.2,
        "Bodenstaerke": 1.6,
        "Innenradius": 5.0,
        "Bodenkehle": 2.4,
        "Trennwandstaerke": 1.2,
        "Trennwande_herausnehmbar": 0,
        "Nutspiel": 0.20,
        "Fuesse": 0,
        "Passungsspiel": 0.0,
        "Verbinder_Spiel": 0.20,
        "Max_Segmentmass": 250.0,
        "Fach_1_Breite": 48.0,
        "Fach_1_Laenge": 0.0,
        "Fach_2_Breite": 55.0,
        "Fach_2_Laenge": 0.0,
        "Fach_3_Breite": 55.0,
        "Fach_3_Laenge": 0.0,
        "Fach_4_Breite": 50.0,
        "Fach_4_Laenge": 0.0,
        "Fach_5_Breite": 0.0,
        "Fach_5_Laenge": 0.0,
    }
    p.update(overrides)
    return p


def _fuss_positionen(seg, margin=2.0):
    """Fusspunkte, die vollständig auf dem Segment liegen, im 42-mm-Globalraster."""
    pts = []
    # i,j so dass Zentrum (i+0.5)*42 in [seg.x0+margin+20.75, seg.x1-margin-20.75]
    half = 20.75  # 41.5/2
    i0 = int(math.floor((seg.x0 + margin + half) / RASTER_MM - 0.5 - 1e-9))
    i1 = int(math.ceil((seg.x1 - margin - half) / RASTER_MM - 0.5 + 1e-9))
    j0 = int(math.floor((seg.y0 + margin + half) / RASTER_MM - 0.5 - 1e-9))
    j1 = int(math.ceil((seg.y1 - margin - half) / RASTER_MM - 0.5 + 1e-9))
    for i in range(max(0, i0), i1 + 1):
        for j in range(max(0, j0), j1 + 1):
            cx = (i + 0.5) * RASTER_MM
            cy = (j + 0.5) * RASTER_MM
            if (seg.x0 + margin + half <= cx <= seg.x1 - margin - half and
                    seg.y0 + margin + half <= cy <= seg.y1 - margin - half):
                pts.append((cx, cy))
    return pts


def make_besteck_segment_shape(plan, seg, params):
    """Ein Segment des Besteckeinsatzes, lokale Ursprung vorne links, z=0 am Boden (bzw. unter den Füssen)."""
    p = default_besteck_params(**params) if params is not None else default_besteck_params()
    w, d, h = seg.breite, seg.tiefe, plan.hoehe
    boden = plan.boden
    wand = plan.wand
    r_in = plan.innenradius
    kehle = float(p.get("Bodenkehle", 2.4))
    spiel_v = float(p.get("Verbinder_Spiel", VERBINDER_SPIEL_STANDARD))
    fuesse_an = plan.fuesse
    z_body = FUSS_PROFIL_HOEHE if fuesse_an else 0.0
    z_top = z_body + h
    z_floor = z_body + boden

    # Korpus
    body = Part.makeBox(w, d, h, VEC(0, 0, z_body))
    corners = set()
    # Tray-Aussenecken: (0,0), (nutz_x,0), (nutz_x,nutz_y), (0,nutz_y)
    if abs(seg.x0) < 0.2 and abs(seg.y0) < 0.2:
        corners.add("sw")
    if abs(seg.x1 - plan.nutz_x) < 0.2 and abs(seg.y0) < 0.2:
        corners.add("se")
    if abs(seg.x1 - plan.nutz_x) < 0.2 and abs(seg.y1 - plan.nutz_y) < 0.2:
        corners.add("ne")
    if abs(seg.x0) < 0.2 and abs(seg.y1 - plan.nutz_y) < 0.2:
        corners.add("nw")
    body = _fillet_outer_corners(body, w, d, h, ECKENRADIUS_EINSATZ, corners)

    cutters = []
    # Fächer
    for fach in plan.faecher:
        lx0 = fach.x - seg.x0
        lx1 = fach.x + fach.breite - seg.x0
        ly0 = fach.y - seg.y0
        ly1 = fach.y + fach.laenge - seg.y0
        # Durchstoss an Stosskanten, wenn das Fach weitergeht
        offen_l = seg.stoesse[0] and (fach.x < seg.x0 - 0.05)
        offen_r = seg.stoesse[1] and (fach.x + fach.breite > seg.x1 + 0.05)
        offen_v = seg.stoesse[2] and (fach.y < seg.y0 - 0.05)
        offen_h = seg.stoesse[3] and (fach.y + fach.laenge > seg.y1 + 0.05)
        # Fach, das genau an der Kante endet, aber die Kante ist ein Stoss MITTEN im Fach:
        # (fach reicht bis zur oder über die Kante)
        if seg.stoesse[0] and fach.x <= seg.x0 + 0.05 and fach.x + fach.breite > seg.x0 + 1.0:
            offen_l = True
        if seg.stoesse[1] and fach.x + fach.breite >= seg.x1 - 0.05 and fach.x < seg.x1 - 1.0:
            offen_r = True
        if seg.stoesse[2] and fach.y <= seg.y0 + 0.05 and fach.y + fach.laenge > seg.y0 + 1.0:
            offen_v = True
        if seg.stoesse[3] and fach.y + fach.laenge >= seg.y1 - 0.05 and fach.y < seg.y1 - 1.0:
            offen_h = True

        if offen_l:
            lx0 = -0.4
        if offen_r:
            lx1 = w + 0.4
        if offen_v:
            ly0 = -0.4
        if offen_h:
            ly1 = d + 0.4
        # auf eine kleine Überlappung mit dem Segment begrenzen, sonst skip
        cx0, cx1 = max(lx0, -0.4), min(lx1, w + 0.4)
        cy0, cy1 = max(ly0, -0.4), min(ly1, d + 0.4)
        if cx1 - cx0 < 3 or cy1 - cy0 < 3:
            continue
        offen = offen_l or offen_r or offen_v or offen_h
        if not offen:
            poc = _pocket_loft(cx1 - cx0, cy1 - cy0, z_floor, z_top + 0.3, r_in, kehle)
            if poc is None:
                continue
            poc.translate(VEC((cx0 + cx1) / 2.0, (cy0 + cy1) / 2.0, 0))
        else:
            # offenes Fach: Quader, damit die Stossseite wirklich offen ist
            poc = _box(cx0, cy0, z_floor, cx1, cy1, z_top + 0.3)
        if poc is not None:
            cutters.append(poc)

    # Falls herausnehmbare Trennwände: Nuten statt festem Material bereits durch
    # zusammenhängende Fächer... Bei festem Modus bleiben Stege stehen, weil
    # die Taschen nur die Fachinnenräume wegnehmen.
    if plan.herausnehmbar:
        nut_b = plan.trenn + float(p.get("Nutspiel", 0.20))
        nut_t = min(2.0, boden * 0.7)
        for t in plan.trenner:
            if t.achse == "x":
                # Nut längs Y, Breite nut_b um t.position
                px = t.position - seg.x0
                if -nut_b < px < w + nut_b:
                    y0 = max(0.0, t.a0 - seg.y0) - 0.2
                    y1 = min(d, t.a1 - seg.y0) + 0.2
                    cutters.append(_box(px - nut_b / 2.0, y0, z_floor - nut_t, px + nut_b / 2.0, y1, z_top + 0.3))
            else:
                py = t.position - seg.y0
                if -nut_b < py < d + nut_b:
                    x0 = max(0.0, t.a0 - seg.x0) - 0.2
                    x1 = min(w, t.a1 - seg.x0) + 0.2
                    cutters.append(_box(x0, py - nut_b / 2.0, z_floor - nut_t, x1, py + nut_b / 2.0, z_top + 0.3))

    # Verbindungsschienen an offenen Stosskanten (wenn der Stoss durch ein Fach geht)
    # bzw. Taschen in der Wand, wenn der Stoss auf einer Trennwand liegt.
    z_c0 = z_body + max(boden * 0.6, 1.0)
    z_c1 = min(z_body + SEGMENT_SCHIENE_H - 0.3, z_c0 + SEGMENT_CLIP_H + 0.4)
    stoesse = (
        (seg.stoesse[0], "x", seg.x0, 180, VEC(0, d, 0)),       # links, öffnet nach -X (nach 180° liegt +Y auf -Y)
        (seg.stoesse[1], "x", seg.x1, 0, VEC(w, 0, 0)),         # rechts, öffnet nach +X
        (seg.stoesse[2], "y", seg.y0, 270, VEC(0, 0, 0)),       # vorne, öffnet nach -Y
        (seg.stoesse[3], "y", seg.y1, 90, VEC(w, d, 0)),        # hinten, öffnet nach +Y
    )
    for is_joint, achse, world_pos, rot, origin in stoesse:
        if not is_joint:
            continue
        length = d if achse == "x" else w
        # Schiene an jeder Stosskante (auch auf einer Trennwand: 1,2 mm Wand
        # allein reicht nicht für eine 8 mm tiefe Tasche).
        if achse == "x":
            if rot == 0:  # rechts, x von w-SCHIENE bis w
                rail = _box(w - SEGMENT_SCHIENE_B, 0, z_body, w, d, z_body + SEGMENT_SCHIENE_H)
            else:
                rail = _box(0, 0, z_body, SEGMENT_SCHIENE_B, d, z_body + SEGMENT_SCHIENE_H)
        else:
            if rot == 90:  # hinten
                rail = _box(0, d - SEGMENT_SCHIENE_B, z_body, w, d, z_body + SEGMENT_SCHIENE_H)
            else:
                rail = _box(0, 0, z_body, w, SEGMENT_SCHIENE_B, z_body + SEGMENT_SCHIENE_H)
        if rail is not None:
            body = body.fuse(rail)

        pockets = _clip_pockets_on_edge(length, z_c0, z_c1 + 0.05, spiel_v, inward_is_neg_x=True)
        for tsc in pockets:
            tsc.rotate(VEC(0, 0, 0), VEC(0, 0, 1), rot)
            tsc.translate(origin)
            cutters.append(tsc)

    cutter = None
    for c in cutters:
        if c is None:
            continue
        cutter = c if cutter is None else cutter.fuse(c)
    if cutter is not None:
        body = body.cut(cutter)
    body = _als_solid(body, "Bestecksegment")

    if fuesse_an:
        fuesse = []
        for cx, cy in _fuss_positionen(seg):
            f = einzel_fuss(cx - seg.x0, cy - seg.y0, RASTER_MM - 0.5, ECKENRADIUS_BOX_OBEN, float(p.get("Passungsspiel", 0.0)))
            fuesse.append(f)
        if fuesse:
            fused = fuesse[0]
            for f in fuesse[1:]:
                fused = fused.fuse(f)
            body = body.fuse(fused)
            body = _als_solid(body, "Bestecksegment")
    if not body.isValid():
        body = body.removeSplitter()
        if not body.isValid():
            raise RuntimeError("Bestecksegment ist geometrisch ungültig.")
    return body


def make_trennwand_shape(laenge, hoehe, dicke, spiel=0.20, radius=2.0):
    """Herausnehmbare Trennwand, etwas kürzer/niedriger als die Nut."""
    l = max(10.0, laenge - 2 * spiel)
    h = max(8.0, hoehe - spiel - 0.4)
    t = max(0.8, dicke)
    r = min(radius, t / 2.0 - 0.05, l / 4.0)
    sh = loft_sections([(0.0, t, l, r), (h, t, l, r)])
    return _als_solid(sh, "Trennwand")


def _clean_poly(pts, tol=1e-7):
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > tol or abs(p[1] - out[-1][1]) > tol:
            out.append((float(p[0]), float(p[1])))
    if len(out) >= 2 and abs(out[0][0] - out[-1][0]) <= tol and abs(out[0][1] - out[-1][1]) <= tol:
        out = out[:-1]
    return out


def _extrude_yz(pts_yz, x0, x1):
    """Polygon (y, z) in der YZ-Ebene, Extrusion von x0 nach x1."""
    if x1 <= x0 + 1e-9:
        raise ValueError("leere Extrusion")
    pts = _clean_poly(pts_yz)
    if len(pts) < 3:
        raise ValueError("Polygon braucht mindestens 3 Punkte")
    verts = [VEC(x0, y, z) for y, z in pts]
    verts.append(verts[0])
    wire = Part.makePolygon(verts)
    face = Part.Face(wire)
    if not face.isValid() or face.Area <= 0:
        # Orientierung tauschen und erneut versuchen
        verts = [VEC(x0, y, z) for y, z in reversed(pts)]
        verts.append(verts[0])
        wire = Part.makePolygon(verts)
        face = Part.Face(wire)
    if not face.isValid():
        raise RuntimeError("YZ-Profil erzeugt keine gültige Fläche.")
    return face.extrude(VEC(x1 - x0, 0, 0))


def _cut_all(body, cutters):
    for c in cutters:
        if c is None:
            continue
        try:
            body = body.cut(c)
        except Exception:
            body = body.cut(c.removeSplitter())
    return body


def _joint_posts_and_pockets(w, d, hoehe, stoesse, spiel, back_only=True):
    """Stege und Taschen an X-Stössen. stoesse = (links, rechts)."""
    rails = []
    pockets = []
    post_w = SEGMENT_SCHIENE_B
    post_d = 28.0
    z0 = 1.0
    z1 = min(hoehe - 0.4, z0 + SEGMENT_CLIP_H + 0.4)
    if z1 - z0 < 4:
        return rails, pockets
    y0 = (d - post_d) if back_only else 0.0
    y0 = max(0.0, y0)
    y1 = d
    if stoesse[0]:
        rails.append(_box(0, y0, 0, post_w, y1, hoehe))
        for tsc in _clip_pockets_on_edge(y1 - y0, z0, z1 + 0.05, spiel, True):
            tsc.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 180)
            tsc.translate(VEC(0, y1, 0))
            pockets.append(tsc)
    if stoesse[1]:
        rails.append(_box(w - post_w, y0, 0, w, y1, hoehe))
        for tsc in _clip_pockets_on_edge(y1 - y0, z0, z1 + 0.05, spiel, True):
            tsc.translate(VEC(w, y0, 0))
            pockets.append(tsc)
    return rails, pockets


def make_stufenregal_segment_shape(plan, x0, x1, params=None):
    params = params or {}
    p = plan.parameter
    st_h = float(p["Stufenhoehe"])
    st_t = float(p["Stufentiefe"])
    boden = float(p["Bodenstaerke"])
    wand = float(p["Wandstaerke"])
    lippe = float(p.get("Stufenlippe", params.get("Stufenlippe", 12.0)))
    hinter = float(p.get("Hinterlippe", params.get("Hinterlippe", 25.0)))
    glas_d = float(p["Glasdurchmesser"])
    glas_n = int(p["Glasanzahl"])
    gap = float(params.get("Glasabstand", 4.0))
    spiel = float(params.get("Verbinder_Spiel", VERBINDER_SPIEL_STANDARD))
    ebenen = plan.ebenen
    tiefe = plan.tiefe
    hoehe = plan.hoehe
    breite = plan.breite
    w = x1 - x0

    pts = [(0.0, 0.0), (0.0, boden)]
    if lippe > 0.8:
        lh = min(lippe, max(4.0, st_h * 0.5))
        pts += [(0.0, boden + lh), (wand, boden + lh), (wand, boden)]
    for i in range(ebenen):
        y0 = i * st_t
        y1 = (i + 1) * st_t if i < ebenen - 1 else tiefe
        z_t = boden + i * st_h
        if i > 0:
            pts.append((y0, z_t))
        # Letzte Stufe nicht bis zur hinteren Aussenkante, sonst überlappen
        # Steigkante und Rückwand (Nullstärke). Hinterwand bekommt Dicke.
        if i == ebenen - 1:
            y1 = max(y0 + 4.0, tiefe - max(2.4, wand * 2.0))
        pts.append((y1, z_t))
    hinter_t = max(2.4, wand * 2.0)
    pts += [
        (tiefe - hinter_t, hoehe),
        (tiefe, hoehe),
        (tiefe, 0.0),
    ]
    body = _extrude_yz(pts, 0.0, w)

    # Geschlossener Boden (abwischbar, keine Hohlräume als Schmutzfallen).
    # Stützenfrei, weil die Stufen von unten massiv getragen werden. Füllung im Slicer wählen.
    cutters = []
    # Flache Mulden für Gläser, nur wenn das Zentrum im Segment liegt
    pitch = glas_d + gap
    inner = breite - 2 * wand
    if glas_n < 1:
        glas_n = max(1, int(math.floor(inner / pitch + 1e-9)))
    # gleichmässig in der vollen Breite
    if glas_n == 1:
        centers = [breite / 2.0]
    else:
        span = max(pitch, inner - glas_d)
        start = wand + glas_d / 2.0
        if glas_n > 1:
            step = (breite - wand - glas_d / 2.0 - start) / (glas_n - 1)
        else:
            step = 0
        centers = [start + i * step for i in range(glas_n)]
    r_mulde = min(12.0, glas_d * 0.22)
    for i in range(ebenen):
        y0 = i * st_t
        y1 = (i + 1) * st_t if i < ebenen - 1 else tiefe
        z_t = boden + i * st_h
        cy = (y0 + y1) / 2.0
        for cx in centers:
            lx = cx - x0
            if lx < 8 or lx > w - 8:
                continue
            sph = Part.makeSphere(r_mulde, VEC(lx, cy, z_t + r_mulde * 0.45))
            cutters.append(sph)

    # Seitenlippen an den wahren Aussenenden
    for i in range(ebenen):
        y0 = i * st_t + 0.2
        y1 = ((i + 1) * st_t if i < ebenen - 1 else tiefe) - 0.2
        z_t = boden + i * st_h
        z1 = z_t + min(lippe, 10.0)
        if abs(x0) < 0.2:
            body = body.fuse(_box(0, y0, z_t, wand, y1, z1))
        if abs(x1 - breite) < 0.2:
            body = body.fuse(_box(w - wand, y0, z_t, w, y1, z1))

    stoesse = (x0 > 0.2, x1 < breite - 0.2)
    rails, pockets = _joint_posts_and_pockets(w, tiefe, hoehe, stoesse, spiel, back_only=True)
    for r in rails:
        body = body.fuse(r)
    body = _cut_all(body, cutters + pockets)
    body = _als_solid(body, "Stufenregal")
    if not body.isValid():
        body = body.removeSplitter()
        if not body.isValid():
            raise RuntimeError("Stufenregal-Segment ist geometrisch ungültig.")
    return body


def make_schraege_segment_shape(plan, x0, x1, y0=0.0, y1=None, params=None):
    params = params or {}
    p = plan.parameter
    nutz_x = float(p["Nutzbreite"])
    tiefe = float(p["Nutztiefe"])
    back_h = float(p["Hoehe_hinten"])
    wand = float(p["Wandstaerke"])
    glas_d = float(params.get("Glasdurchmesser", p.get("Glasdurchmesser", 55.0)))
    gap = float(params.get("Glasabstand", 4.0))
    reihen = int(p["Reihen"])
    spiel = float(params.get("Verbinder_Spiel", VERBINDER_SPIEL_STANDARD))
    front_h = min(8.0, max(3.0, back_h * 0.15))
    if back_h <= front_h + 2:
        front_h = max(2.0, back_h * 0.2)
    if y1 is None:
        y1 = tiefe
    w = x1 - x0
    d = y1 - y0

    def z_at(y):
        return front_h + (back_h - front_h) * (y / max(tiefe, 1.0))

    z_v, z_h = z_at(y0), z_at(y1)
    pts = [
        (0.0, 0.0),
        (0.0, z_v),
        (d, z_h),
        (d, 0.0),
    ]
    body = _extrude_yz(pts, 0.0, w)
    cutters = []
    wall_h = 12.0
    ang = math.atan2(back_h - front_h, tiefe)
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
    r_rinne = min(10.0, glas_d * 0.18)
    direction = VEC(0, math.cos(ang), math.sin(ang))
    normal = VEC(0, -math.sin(ang), math.cos(ang))
    bahn = math.hypot(tiefe, back_h - front_h)
    start_s = 12.0
    length = max(20.0, bahn - 24.0)
    for cx in centers:
        lx = cx - x0
        if lx < 8 or lx > w - 8:
            continue
        # in lokalen Koordinaten (Ursprung des Segments bei y0)
        base = VEC(lx, -y0, front_h) + direction * start_s + normal * (r_rinne * 0.55)
        cyl = Part.makeCylinder(r_rinne, length, base, direction)
        cutters.append(cyl)

    def _slant_wall(xw0, xw1):
        # Seitenwand nicht höher als die geplante hintere Höhe (Schubladenlicht)
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
        body = body.fuse(_slant_wall(w - wand, w))

    stoesse_x = (x0 > 0.2, x1 < nutz_x - 0.2)
    rails, pockets = _joint_posts_and_pockets(w, d, max(z_v, z_h), stoesse_x, spiel, back_only=True)
    for r in rails:
        if r is not None:
            body = body.fuse(r)

    # Stösse in der Tiefe
    post_w = SEGMENT_SCHIENE_B
    z0p = 1.0
    if y0 > 0.2:
        z1p = min(z_v - 0.3, z0p + SEGMENT_CLIP_H + 0.4)
        if z1p - z0p >= 4:
            rail = _box(0, 0, 0, w, post_w, z_v)
            if rail is not None:
                body = body.fuse(rail)
            for tsc in _clip_pockets_on_edge(w, z0p, z1p + 0.05, spiel, True):
                tsc.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 270)
                tsc.translate(VEC(0, 0, 0))
                pockets.append(tsc)
    if y1 < tiefe - 0.2:
        z1p = min(z_h - 0.3, z0p + SEGMENT_CLIP_H + 0.4)
        if z1p - z0p >= 4:
            rail = _box(0, d - post_w, 0, w, d, z_h)
            if rail is not None:
                body = body.fuse(rail)
            for tsc in _clip_pockets_on_edge(w, z0p, z1p + 0.05, spiel, True):
                tsc.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 90)
                tsc.translate(VEC(w, d, 0))
                pockets.append(tsc)

    body = _cut_all(body, cutters + pockets)
    # Auf das Segmentmass beschneiden (Rinnen-Zylinder können an der Fuge überstehen)
    crop = Part.makeBox(w + 0.02, d + 0.02, max(z_v, z_h, back_h) + 20.0, VEC(-0.01, -0.01, -1.0))
    body = body.common(crop)
    body = _als_solid(body, "Schraege")
    if not body.isValid():
        body = body.removeSplitter()
        if not body.isValid():
            raise RuntimeError("Schrägeinsatz-Segment ist geometrisch ungültig.")
    return body


def make_halter_shape(plan, params=None):
    params = params or {}
    p = plan.parameter
    innen_d = float(p["Innen_D"])
    boden = float(p["Bodenstaerke"])
    wand = float(p["Wandstaerke"])
    hoehe = float(p["Hoehe"])
    spiel = float(params.get("Verbinder_Spiel", VERBINDER_SPIEL_STANDARD))
    ausschnitt = int(params.get("Frontausschnitt", 1)) == 1
    # Becher bleibt dünnwandig; Verbinder sitzen in seitlichen Ansätzen (nicht rundum dick).
    aussen = innen_d + 2.0 * wand
    r_aus = min(6.0, aussen / 6.0)
    body = loft_sections([(0.0, aussen, aussen, r_aus), (hoehe, aussen, aussen, r_aus)])
    pad_t = VERBINDER_TIEFE + 0.4
    pad_b = 16.0
    pad_h = min(hoehe, max(12.0, SEGMENT_SCHIENE_H))
    body = body.fuse(_box(aussen / 2.0 - 0.05, -pad_b / 2.0, 0, aussen / 2.0 + pad_t, pad_b / 2.0, pad_h))
    body = body.fuse(_box(-aussen / 2.0 - pad_t, -pad_b / 2.0, 0, -aussen / 2.0 + 0.05, pad_b / 2.0, pad_h))
    # Innenöffnung
    z1 = hoehe + 0.4
    inn = Part.makeCylinder(innen_d / 2.0, z1 - boden, VEC(0, 0, boden), VEC(0, 0, 1))
    # 45°-Bodenkehle als Kegelstumpf
    kehle = min(2.2, boden * 0.9, innen_d / 8.0)
    if kehle > 0.4:
        # einfacher Ring: Zylinder etwas weiter unten reicht; zusätzlich Konus
        cone_h = kehle
        try:
            cone = Part.makeCone(innen_d / 2.0 - kehle, innen_d / 2.0, cone_h, VEC(0, 0, boden), VEC(0, 0, 1))
            inn = inn.fuse(cone)
        except Exception:
            pass
    cutters = [inn]
    if ausschnitt:
        slot_b = innen_d * 0.72
        # von der Vorderseite bis zur Zylindermitte, Boden bleibt stehen
        cutters.append(_box(-slot_b / 2.0, -aussen / 2.0 - 0.4, boden + 0.4, slot_b / 2.0, 0.0, z1))
    # Taschen ±X, bei ausreichender Höhe
    z0 = max(1.0, boden * 0.5)
    zc1 = min(hoehe - 0.3, z0 + SEGMENT_CLIP_H)
    if zc1 - z0 >= 4:
        pad_t = VERBINDER_TIEFE + 0.4
        t_r = verbinder_tasche_solid(VERBINDER_TIEFE, VERBINDER_KOPF_BREITE, VERBINDER_HALS_BREITE, spiel, z0, zc1 + 0.05)
        t_r.translate(VEC(aussen / 2.0 + pad_t, 0, 0))
        t_l = verbinder_tasche_solid(VERBINDER_TIEFE, VERBINDER_KOPF_BREITE, VERBINDER_HALS_BREITE, spiel, z0, zc1 + 0.05)
        t_l.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 180)
        t_l.translate(VEC(-aussen / 2.0 - pad_t, 0, 0))
        cutters.extend([t_r, t_l])
    body = _cut_all(body, cutters)
    body = _als_solid(body, "Gewuerzhalter")
    if not body.isValid():
        body = body.removeSplitter()
        if not body.isValid():
            raise RuntimeError("Gewürzhalter ist geometrisch ungültig.")
    return body


def besteck_teile(params):
    """Plan plus Dict name->Shape (Segmente, Clip, optionale Trennwände)."""
    plan = plane_besteck(params)
    if plan.ungueltig:
        raise ValueError("; ".join(plan.hinweise))
    shapes = {}
    for seg in plan.segmente:
        name = "Segment_%d_%d" % (seg.ix + 1, seg.iy + 1)
        shapes[name] = make_besteck_segment_shape(plan, seg, params)
    shapes["Segmentverbinder"] = make_segmentverbinder_clip(params.get("Verbinder_Spiel") if params else None)
    if plan.herausnehmbar:
        spiel = float(params.get("Nutspiel", 0.20))
        for i, t in enumerate(plan.trenner, 1):
            laenge = t.a1 - t.a0
            # Höhe der Trennwand: Einsatzhöhe minus Boden plus Nut
            hoehe = plan.hoehe - plan.boden + min(2.0, plan.boden * 0.7) - 0.4
            shapes["Trennwand_%d" % i] = make_trennwand_shape(laenge, hoehe, plan.trenn, spiel)
    return plan, shapes


def stufen_teile(params):
    plan = plane_stufenregal(params)
    if plan.ungueltig:
        raise ValueError("; ".join(plan.hinweise))
    shapes = {}
    x = 0.0
    teile = plan.segmente_x
    for i, w in enumerate(teile, 1):
        shapes["Segment_%d" % i] = make_stufenregal_segment_shape(plan, x, x + w, params)
        x += w
    if len(teile) > 1:
        shapes["Segmentverbinder"] = make_segmentverbinder_clip(params.get("Verbinder_Spiel") if params else None)
    return plan, shapes


def schraege_teile(params):
    plan = plane_schraege(params)
    if plan.ungueltig:
        raise ValueError("; ".join(plan.hinweise))
    shapes = {}
    teile_x = plan.segmente_x
    teile_y = plan.segmente_y or [plan.tiefe]
    y = 0.0
    for iy, dy in enumerate(teile_y, 1):
        x = 0.0
        for ix, dx in enumerate(teile_x, 1):
            shapes["Segment_%d_%d" % (ix, iy)] = make_schraege_segment_shape(
                plan, x, x + dx, y, y + dy, params
            )
            x += dx
        y += dy
    if len(teile_x) * len(teile_y) > 1:
        shapes["Segmentverbinder"] = make_segmentverbinder_clip(params.get("Verbinder_Spiel") if params else None)
    return plan, shapes


def halter_teile(params):
    plan = plane_halter(params)
    if plan.ungueltig:
        raise ValueError("; ".join(plan.hinweise))
    shapes = {"Halter": make_halter_shape(plan, params),
              "Segmentverbinder": make_segmentverbinder_clip(params.get("Verbinder_Spiel") if params else None)}
    return plan, shapes
