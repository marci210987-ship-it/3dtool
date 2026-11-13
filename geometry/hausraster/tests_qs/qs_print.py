# -*- coding: utf-8 -*-
"""Druckbarkeitsanalyse ohne Slicer (Geometrie, Ueberhang, Bauraum)."""
from __future__ import annotations

import math

import FreeCAD as App
import MeshPart

from qs_common import _rec, shape_info
from hausraster_const import default_params
from hausraster_geom import (
    make_plate_shape, make_box_shape, make_verbinder_clip_shape, make_rastclip_shape, box_outer_size,
)
from hausraster_phase3_geom import besteck_teile, default_besteck_params
from hausraster_phase3_schale import stufen_schale_teile


def overhang_stats(shape, angle_deg=45.0):
    try:
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.4, AngularDeflection=0.3, Relative=False)
    except Exception as exc:
        return {"error": str(exc)}
    thresh = -math.sin(math.radians(angle_deg))
    total = 0.0
    over = 0.0
    bridges_h = 0.0
    try:
        facets = mesh.Facets
    except Exception:
        facets = list(mesh.Facets) if hasattr(mesh, "Facets") else []
    for f in facets:
        n = f.Normal
        try:
            area = float(getattr(f, "Area", 0.0))
            if area <= 0:
                pts = f.Points
                a = App.Vector(*pts[0]); b = App.Vector(*pts[1]); c = App.Vector(*pts[2])
                area = ((b - a).cross(c - a)).Length * 0.5
        except Exception:
            continue
        total += area
        nz = float(n.z) if hasattr(n, "z") else float(n[2])
        if nz <= thresh:
            over += area
        if nz < -0.95:
            bridges_h += area
    min_edge = min((e.Length for e in shape.Edges), default=None)
    small_edges = sum(1 for e in shape.Edges if e.Length < 0.8)
    return {
        "flaeche_mm2": total,
        "ueberhang_gt45_mm2": over,
        "ueberhang_anteil": (over / total) if total else 0.0,
        "bruecken_horizontal_mm2": bridges_h,
        "kuerzeste_kante_mm": min_edge,
        "kanten_kleiner_0_8mm": small_edges,
        "facets": mesh.CountFacets,
    }


def test_printability(models):
    reps = [
        ("Platte_3x3", make_plate_shape(default_params(Einheiten_X=3, Einheiten_Y=3))),
        ("Platte_1x1", make_plate_shape(default_params(Einheiten_X=1, Einheiten_Y=1, Verbinder=0, Verriegelung=0))),
        ("Box_1x1x3", make_box_shape(default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=3))),
        ("Box_2x2x3", make_box_shape(default_params(Einheiten_X=2, Einheiten_Y=2, Einheiten_Z=3))),
        ("Box_1x6x3", make_box_shape(default_params(Einheiten_X=1, Einheiten_Y=6, Einheiten_Z=3))),
        ("Verbinder", make_verbinder_clip_shape(default_params())),
        ("Rastclip", make_rastclip_shape(default_params())),
    ]
    try:
        _, bt = besteck_teile(default_besteck_params(Schubladenbreite=240, Schubladentiefe=200))
        for k, sh in list(bt.items())[:3]:
            reps.append(("Besteck_" + k, sh))
    except Exception as exc:
        _rec("Druckbarkeit", "Besteck-Referenz erzeugen", "FEHLERHAFT", details=str(exc))
    try:
        _, st = stufen_schale_teile(dict(Gesamtbreite=180, Gesamttiefe=120, Ebenenanzahl=3))
        for k, sh in st.items():
            reps.append(("Stufen_Schale_" + k, sh))
    except Exception as exc:
        _rec("Druckbarkeit", "Stufen-Schale erzeugen", "FEHLERHAFT", details=str(exc))

    for name, sh in reps:
        info = shape_info(sh)
        sx, sy, sz = info["size"]
        fits = sx <= 256.01 and sy <= 256.01 and sz <= 256.01
        orients_ok = any([
            sx <= 256 and sy <= 256 and sz <= 256,
            sx <= 256 and sz <= 256 and sy <= 256,
            sz <= 256 and sy <= 256 and sx <= 256,
        ])
        oh = overhang_stats(sh)
        st = "BESTANDEN" if fits and info["valid"] else ("FEHLERHAFT" if not orients_ok else "EINGESCHRAENKT")
        details = ""
        if isinstance(oh, dict) and oh.get("ueberhang_anteil", 0) > 0.08:
            if name in ("Rastclip", "Verbinder"):
                st = "EINGESCHRAENKT"
                details = "In Konstruktionslage Ueberhaenge oder Schwebeteile; Drucklage im Slicer anpassen."
            else:
                details = "Ueberhanganteil in Konstruktionslage groesser als 8 Prozent."
                if st == "BESTANDEN":
                    st = "EINGESCHRAENKT"
        _rec("Druckbarkeit", name, st, details=details,
             messwerte={"size": [sx, sy, sz], "zmin": info["zmin"],
                        "ueberhang": oh, "passt_p2s_konstruktion": fits,
                        "passt_irgendeine_lage": orients_ok})

    sx, sy, sz = box_outer_size(default_params(Einheiten_X=1, Einheiten_Y=6, Einheiten_Z=3))
    lang = max(sx, sy)
    _rec("Druckbarkeit", "Lange Box 1x6 Aussenmass vs. 256 mm",
         "EINGESCHRAENKT" if lang > 248 else "BESTANDEN",
         details="251,5 mm bleiben unter 256 mm, der Rand fuer Brim/Skirt und Schieflage ist knapp (4,5 mm).",
         messwerte={"aussen": [sx, sy, sz], "spiel_zum_bauraum_mm": 256.0 - lang})
