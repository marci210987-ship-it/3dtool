# -*- coding: utf-8 -*-
"""Inkrementeller Geometrie-Rauchtest für Phase 3."""
from __future__ import annotations
import sys
import traceback
from pathlib import Path

sys.path.insert(0, "/workspace/ordnungssystem/src")
import FreeCAD as App  # noqa: F401
import Part

from hausraster_phase3_plan import plane_besteck
from hausraster_phase3_geom import (
    make_besteck_segment_shape, make_segmentverbinder_clip,
    make_passung_segmentverbinder, make_halter_shape,
    besteck_teile, stufen_teile, schraege_teile, halter_teile,
)
from hausraster_phase3_plan import plane_halter

OUT = Path("/workspace/ordnungssystem/tests/phase3_smoke.txt")
lines = []

def report(name, ok, detail):
    s = "[%s] %s: %s" % ("OK" if ok else "FAIL", name, detail)
    print(s, flush=True)
    lines.append(s)

def shape_info(sh):
    bb = sh.BoundBox
    return "valid=%s solids=%d size=%.2f×%.2f×%.2f vol=%.1f" % (
        sh.isValid(), len(sh.Solids), bb.XLength, bb.YLength, bb.ZLength, sh.Volume or 0)

try:
    # 1) unsegmentierter Besteckeinsatz 240×200
    params = {"Schubladenbreite": 240, "Schubladentiefe": 200, "Einsatzhoehe": 45}
    plan = plane_besteck(params)
    assert not plan.ungueltig, plan.hinweise
    assert len(plan.segmente) == 1, "erwartet 1 Segment, got %d" % len(plan.segmente)
    seg = plan.segmente[0]
    sh = make_besteck_segment_shape(plan, seg, params)
    report("besteck_240", sh.isValid() and len(sh.Solids) == 1, shape_info(sh) + " soll=%.1f×%.1f×45" % (seg.breite, seg.tiefe))
except Exception as e:
    report("besteck_240", False, traceback.format_exc())

try:
    clip = make_segmentverbinder_clip()
    report("clip", clip.isValid() and len(clip.Solids) == 1, shape_info(clip))
except Exception as e:
    report("clip", False, traceback.format_exc())

try:
    a, b, c = make_passung_segmentverbinder()
    ok = all(s.isValid() and len(s.Solids) == 1 for s in (a, b, c))
    report("passung", ok, " | ".join(shape_info(s) for s in (a, b, c)))
except Exception as e:
    report("passung", False, traceback.format_exc())

try:
    plan, shapes = halter_teile({"Glasdurchmesser": 55})
    sh = shapes["Halter"]
    report("halter_55", sh.isValid() and len(sh.Solids) == 1, shape_info(sh))
except Exception as e:
    report("halter_55", False, traceback.format_exc())

try:
    plan, shapes = stufen_teile({"Gesamtbreite": 180, "Gesamttiefe": 120, "Ebenenanzahl": 3, "Glasdurchmesser": 55})
    sh = shapes["Segment_1"]
    report("stufen_180", sh.isValid() and len(sh.Solids) >= 1, shape_info(sh) + " n=%d" % len(shapes))
except Exception as e:
    report("stufen_180", False, traceback.format_exc())

try:
    plan, shapes = schraege_teile({"Schubladenbreite": 200, "Schubladentiefe": 200, "Neigungswinkel": 15, "Verfuegbare_Hoehe": 90})
    sh = shapes["Segment_1"]
    report("schraege_200", sh.isValid() and len(sh.Solids) >= 1, shape_info(sh) + " n=%d" % len(shapes))
except Exception as e:
    report("schraege_200", False, traceback.format_exc())

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote", OUT)
