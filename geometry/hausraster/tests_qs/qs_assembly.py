# -*- coding: utf-8 -*-
"""Baugruppen, Rasterpassung, Schubladenplaene, Gridfinity-Referenz."""
from __future__ import annotations

import math
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

from qs_common import (
    REPORT, _rec, _place, common_volume, shape_info, mesh_quality,
    COLLISION_EPS, GF_DIR,
)
from hausraster_const import RASTER_MM, default_params
from hausraster_geom import (
    make_plate_shape, make_box_shape, make_verbinder_clip_shape, make_rastclip_shape,
    plate_outer_size, seated_box_z_on_plate,
)
from hausraster_plan import plane_schublade


def test_assemblies():
    p_pl = default_params(Einheiten_X=3, Einheiten_Y=3, Verbinder=1, Verriegelung=1)
    p_b11 = default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=3, Stapellippe=1)
    p_b22 = default_params(Einheiten_X=2, Einheiten_Y=2, Einheiten_Z=3, Stapellippe=1)
    p_b13 = default_params(Einheiten_X=1, Einheiten_Y=3, Einheiten_Z=2, Stapellippe=1)

    pl = make_plate_shape(p_pl)
    sx, sy, sz = plate_outer_size(p_pl)
    pl_l = _place(pl, 0, 0, 0)
    pl_r = _place(pl, sx, 0, 0)

    v_pl = common_volume(pl_l, pl_r)
    st = "BESTANDEN" if (not math.isnan(v_pl) and v_pl < COLLISION_EPS) else "FEHLERHAFT"
    _rec("Baugruppe", "Zwei 3x3-Platten stossen ohne Durchdringung", st,
         messwerte={"common_mm3": v_pl, "platte_mm": [sx, sy, sz]})

    clip = make_verbinder_clip_shape(p_pl)
    clip_bb = clip.BoundBox
    _rec("Verbinder-Lage", "Rohclip-BBox vor Platzierung", "HINWEIS",
         messwerte={"bbox": [clip_bb.XMin, clip_bb.YMin, clip_bb.ZMin, clip_bb.XMax, clip_bb.YMax, clip_bb.ZMax],
                    "zmin": clip_bb.ZMin, "groesse": [clip_bb.XLength, clip_bb.YLength, clip_bb.ZLength]})
    if clip_bb.ZMin > 0.3:
        _rec("Drucklage", "Plattenverbinder schwebt ueber der Bauplatte (ZMin>0,3 mm)", "FEHLERHAFT",
             details="Das Einzelteil liegt in Fuegeposition, nicht auf Z=0. Ohne manuelles Auf-das-Bett-Setzen waere der Druck nicht stuetzfrei.",
             messwerte={"zmin": clip_bb.ZMin})
        REPORT["fehler"].append({
            "id": "VERBINDER_ZMIN", "zmin": clip_bb.ZMin, "schwere": "mittel",
            "ursache": "make_verbinder_clip_shape setzt z0 = Boden + Abstand + 0,1 mm statt 0.",
        })
    else:
        _rec("Drucklage", "Plattenverbinder steht auf Z=0", "BESTANDEN", messwerte={"zmin": clip_bb.ZMin})

    y_mid = 0.0
    clip_at = _place(clip, sx / 2.0, y_mid, 0)
    v_l = common_volume(pl_l, clip_at)
    v_r = common_volume(pl_r, clip_at)
    clip_vol = float(clip.Volume)
    ok_engage = (v_l > 5.0 and v_r > 5.0 and v_l < clip_vol * 0.9 and v_r < clip_vol * 0.9)
    _rec("Baugruppe", "Verbinder greift in beide Plattentaschen ein",
         "BESTANDEN" if ok_engage else "FEHLERHAFT",
         messwerte={"common_links_mm3": v_l, "common_rechts_mm3": v_r, "clip_mm3": clip_vol,
                    "clip_zmin": clip_bb.ZMin})
    if not ok_engage:
        REPORT["fehler"].append({
            "id": "VERBINDER_EINGRIFF", "v_l": v_l, "v_r": v_r, "schwere": "hoch",
            "ursache": "Geometrische Eingriffspruefung an der Plattenfuge fehlgeschlagen.",
        })

    b11 = make_box_shape(p_b11)
    b22 = make_box_shape(p_b22)
    b13 = make_box_shape(p_b13)
    z_sit = seated_box_z_on_plate(p_pl)

    def cell(i, j):
        return (-sx / 2.0 + (i + 0.5) * RASTER_MM, -sy / 2.0 + (j + 0.5) * RASTER_MM)

    c00 = cell(0, 0)
    c01 = cell(0, 1)
    c2x2 = ((cell(1, 0)[0] + cell(2, 1)[0]) / 2.0, (cell(1, 0)[1] + cell(2, 1)[1]) / 2.0)
    boxA = _place(b11, c00[0], c00[1], z_sit)
    boxB = _place(b11, c01[0], c01[1], z_sit)
    boxC = _place(b22, c2x2[0], c2x2[1], z_sit)
    c13 = (sx + cell(0, 1)[0], cell(0, 1)[1])
    boxD = _place(b13, c13[0], c13[1], z_sit)

    for pname, a, b in (("A-B", boxA, boxB), ("A-C", boxA, boxC), ("B-C", boxB, boxC)):
        v = common_volume(a, b)
        st = "BESTANDEN" if (not math.isnan(v) and v < COLLISION_EPS) else "FEHLERHAFT"
        _rec("Baugruppe", "Boxen " + pname + " kollisionsfrei", st, messwerte={"common_mm3": v})

    for name, box, plate in (("1x1_A", boxA, pl_l), ("1x1_B", boxB, pl_l), ("2x2", boxC, pl_l), ("1x3_rechts", boxD, pl_r)):
        v = common_volume(box, plate)
        st = "BESTANDEN" if (not math.isnan(v) and v < 50.0) else "FEHLERHAFT"
        _rec("Baugruppe", "Box " + name + " auf Platte im Sitz (common)", st,
             messwerte={"common_mm3": v, "sitz_z": z_sit})

    steps = []
    collide_before_seat = False
    for z in [20.0, 12.0, 6.0, 3.0, 1.6, 1.2, 0.8, 0.4]:
        b = _place(b11, c00[0], c00[1], z)
        v = common_volume(b, pl_l)
        steps.append({"z": z, "common_mm3": v})
        if z > z_sit + 0.25 and v > 50.0:
            collide_before_seat = True
    _rec("Einsetzen", "Box 1x1 in 3x3-Platte, Z-Schritte",
         "FEHLERHAFT" if collide_before_seat else "BESTANDEN",
         details="Kollision vor Erreichen der Auflage" if collide_before_seat else "Keine nennenswerte Interferenz oberhalb der Auflage.",
         messwerte={"schritte": steps, "sitz_z": z_sit})
    b_up = _place(b11, c00[0], c00[1], z_sit + 15)
    v_up = common_volume(b_up, pl_l)
    _rec("Ausheben", "Box 1x1 15 mm ueber Sitz", "BESTANDEN" if v_up < COLLISION_EPS else "FEHLERHAFT",
         messwerte={"common_mm3": v_up})

    clip_r = make_rastclip_shape(p_pl)
    rbb = clip_r.BoundBox
    _rec("Rastclip-BBox", "Rohteil", "HINWEIS",
         messwerte={"bbox_size": [rbb.XLength, rbb.YLength, rbb.ZLength], "zmin": rbb.ZMin,
                    "xmin": rbb.XMin, "xmax": rbb.XMax})
    rc = _place(clip_r, sx / 2.0, 0, 0)
    v_rc_pl = common_volume(rc, pl_l)
    c21 = cell(2, 1)
    box_edge = _place(b11, c21[0], c21[1], z_sit)
    v_rc_box = common_volume(rc, box_edge)
    _rec("Baugruppe", "Rastclip an Plattenkante (Eingriff Nut / Box)",
         "BESTANDEN" if v_rc_pl > 0.1 else "EINGESCHRAENKT",
         messwerte={"common_platte_mm3": v_rc_pl, "common_box_mm3": v_rc_box,
                    "hinweis": "Physische Rastkraft ist digital nicht nachgewiesen."})

    for name, W, D in (("450x350", 450, 350), ("500x400", 500, 400), ("387x293", 387, 293)):
        try:
            plan = plane_schublade(W, D)
            ok = plan is not None and not getattr(plan, "ungueltig", False)
            text = plan_als_safe(plan)
            _rec("Schubladenplan", name, "BESTANDEN" if ok else "FEHLERHAFT",
                 details="; ".join(getattr(plan, "hinweise", None) or []),
                 messwerte={"plan_typ": type(plan).__name__, "text": text[:1500]})
        except Exception as exc:
            _rec("Schubladenplan", name, "FEHLERHAFT", details=str(exc))


def plan_als_safe(plan):
    try:
        from hausraster_plan import plan_als_text
        return plan_als_text(plan)
    except Exception as exc:
        return "plan_als_text: " + str(exc) + " attrs=" + ",".join(sorted(getattr(plan, "__dict__", {}).keys()))


def test_gridfinity_ref():
    needed = {
        "gf_base_1x1": GF_DIR / "Baseplate 1x1.stl",
        "gf_base_3x3": GF_DIR / "Baseplate 3x3.stl",
        "gf_bin_1x1_3u": GF_DIR / "GF_Bin_1x1_3u_label_nomag_01.stl",
        "gf_bin_2x2_3u": GF_DIR / "Gridfinity Bin - 2x2x3 - No Label.stl",
    }
    meshes = {}
    for k, p in needed.items():
        if not p.exists():
            _rec("Gridfinity-Referenz", "Datei fehlt: " + str(p), "NICHT_GETESTET")
            return
        m = Mesh.Mesh()
        m.read(str(p))
        meshes[k] = m
        _rec("Gridfinity-Referenz", "STL geladen: " + p.name, "BESTANDEN", messwerte=mesh_quality(m))

    def mesh_to_shape(mesh):
        sh = Part.Shape()
        sh.makeShapeFromMesh(mesh.Topology, 0.15)
        solids = sh.Solids
        if solids:
            s = solids[0]
            for extra in solids[1:]:
                s = s.fuse(extra)
            return s
        return sh

    try:
        gf_base = mesh_to_shape(meshes["gf_base_1x1"])
        gf_bin = mesh_to_shape(meshes["gf_bin_1x1_3u"])
        gf_base3 = mesh_to_shape(meshes["gf_base_3x3"])
        gf_bin22 = mesh_to_shape(meshes["gf_bin_2x2_3u"])
    except Exception as exc:
        _rec("Gridfinity-Referenz", "Mesh-zu-Shape", "NICHT_GETESTET",
             details="Konvertierung fehlgeschlagen: %s. Keine Boolean-Passung moeglich." % exc)
        for k, m in meshes.items():
            bb = m.BoundBox
            _rec("Gridfinity-Referenz", "BBox " + k, "HINWEIS",
                 messwerte={"size": [bb.XLength, bb.YLength, bb.ZLength], "zmin": bb.ZMin})
        return

    for name, sh in (("gf_base_1x1", gf_base), ("gf_bin_1x1_3u", gf_bin),
                     ("gf_base_3x3", gf_base3), ("gf_bin_2x2_3u", gf_bin22)):
        _rec("Gridfinity-Referenz", "Shape " + name, "BESTANDEN" if sh and not sh.isNull() else "FEHLERHAFT",
             messwerte=shape_info(sh))

    hr_pl1 = make_plate_shape(default_params(Einheiten_X=1, Einheiten_Y=1, Verbinder=0, Verriegelung=0))
    hr_b11 = make_box_shape(default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=3, Stapellippe=1))

    def align_xy_center(shape):
        bb = shape.BoundBox
        return _place(shape, - (bb.XMin + bb.XMax) / 2.0, - (bb.YMin + bb.YMax) / 2.0, -bb.ZMin)

    gf_base_a = align_xy_center(gf_base)
    gf_bin_a = align_xy_center(gf_bin)
    hr_pl1_a = align_xy_center(hr_pl1)
    hr_b11_a = align_xy_center(hr_b11)

    def sizes(sh):
        bb = sh.BoundBox
        return [bb.XLength, bb.YLength, bb.ZLength]

    from qs_common import almost
    _rec("Gridfinity-Referenz", "Aussenmasse 1x1 Platte HR vs GF Lite",
         "BESTANDEN" if almost(sizes(hr_pl1_a)[0], sizes(gf_base_a)[0], 0.6) else "EINGESCHRAENKT",
         messwerte={"hr": sizes(hr_pl1_a), "gf": sizes(gf_base_a),
                    "hinweis": "Lite-Grundplatten koennen niedriger sein als Hausraster."})

    z_sit = seated_box_z_on_plate(default_params())
    v0 = common_volume(gf_bin_a, hr_pl1_a)
    vs = common_volume(_place(gf_bin_a, 0, 0, z_sit), hr_pl1_a)
    v_hr_on_gf0 = common_volume(hr_b11_a, gf_base_a)
    scan = []
    for z in [0.0, 0.4, 0.8, 1.2, 2.0, 4.0]:
        scan.append({
            "z": z,
            "gf_bin_auf_hr_platte": common_volume(_place(gf_bin_a, 0, 0, z), hr_pl1_a),
            "hr_box_auf_gf_platte": common_volume(_place(hr_b11_a, 0, 0, z), gf_base_a),
        })
    _rec("Gridfinity-Passung", "GF-Box 1x1 auf Hausraster-Platte 1x1 (Z-Scan)", "HINWEIS",
         details="Geometrisch geprueft, nicht physisch bestaetigt.",
         messwerte={"scan": scan, "common_z0": v0, "common_zsitz_hr": vs,
                    "hr_box_auf_gf_z0": v_hr_on_gf0,
                    "hr_platte": sizes(hr_pl1_a), "gf_base": sizes(gf_base_a),
                    "hr_box": sizes(hr_b11_a), "gf_bin": sizes(gf_bin_a)})

    def eval_scan(vals):
        finite = [v for v in vals if not math.isnan(v)]
        if not finite:
            return "NICHT_GETESTET"
        if min(finite) < 80 and max(finite) > min(finite) + 10:
            return "BESTANDEN"
        if min(finite) < 80:
            return "EINGESCHRAENKT"
        return "FEHLERHAFT"

    commons_gf_on_hr = [s["gf_bin_auf_hr_platte"] for s in scan]
    commons_hr_on_gf = [s["hr_box_auf_gf_platte"] for s in scan]
    _rec("Gridfinity-Passung", "GF-Bin auf HR-Platte, Bewertung Z-Scan", eval_scan(commons_gf_on_hr),
         messwerte={"werte": commons_gf_on_hr})
    _rec("Gridfinity-Passung", "HR-Box auf GF-Lite-Platte, Bewertung Z-Scan", eval_scan(commons_hr_on_gf),
         messwerte={"werte": commons_hr_on_gf})
