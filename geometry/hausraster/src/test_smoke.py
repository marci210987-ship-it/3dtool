# -*- coding: utf-8 -*-
"""Erster Geometrietest: 1x1-Platte und Fussstumpf. Bei Fehlern abbrechen."""

import json
import sys
import traceback
from pathlib import Path

# FreeCADCmd setzt den Script-Pfad nicht immer auf sys.path
ROOT = Path("/workspace/ordnungssystem")
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import FreeCAD as App
import Part

from hausraster_const import default_params, plattenhoehe, FUSS_PROFIL_HOEHE
from hausraster_geom import (
    make_plate_shape,
    make_fuss_stumpf_shape,
    make_box_shape,
    make_verbinder_clip_shape,
    make_rastclip_shape,
    seated_box_z_on_plate,
    plate_outer_size,
    box_outer_size,
    einzel_fuss,
)
from hausraster_const import ECKENRADIUS_BOX_OBEN

OUT = ROOT / "tests" / "smoke"
OUT.mkdir(parents=True, exist_ok=True)


def report(name, ok, detail):
    status = "BESTANDEN" if ok else "NICHT BESTANDEN"
    print("[%s] %s: %s" % (status, name, detail))
    return {"name": name, "ok": ok, "detail": detail}


def main():
    results = []
    try:
        p_plate = default_params(
            Einheiten_X=1, Einheiten_Y=1, Verbinder=0, Verriegelung=0,
            Rand_X_links=0, Rand_X_rechts=0, Rand_Y_vorne=0, Rand_Y_hinten=0,
        )
        plate = make_plate_shape(p_plate)
        ok = plate.isValid() and len(plate.Solids) == 1 and plate.Volume > 0
        bb = plate.BoundBox
        sx, sy, sz = plate_outer_size(p_plate)
        size_ok = (
            abs(bb.XLength - sx) < 0.15
            and abs(bb.YLength - sy) < 0.15
            and abs(bb.ZLength - sz) < 0.15
        )
        results.append(report(
            "Platte 1x1 gültig",
            ok and size_ok,
            "valid=%s solids=%d vol=%.1f bbox=%.3fx%.3fx%.3f soll=%.3fx%.3fx%.3f"
            % (plate.isValid(), len(plate.Solids), plate.Volume, bb.XLength, bb.YLength, bb.ZLength, sx, sy, sz),
        ))
        plate.exportStep(str(OUT / "smoke_platte_1x1.step"))

        fuss = make_fuss_stumpf_shape(p_plate)
        okf = fuss.isValid() and fuss.Volume > 0
        results.append(report(
            "Fussstumpf gültig",
            okf,
            "valid=%s solids=%d vol=%.1f h=%.3f"
            % (fuss.isValid(), len(fuss.Solids), fuss.Volume, fuss.BoundBox.ZLength),
        ))

        z = seated_box_z_on_plate(p_plate)
        fuss2 = fuss.copy()
        fuss2.translate(App.Vector(0, 0, z))
        common = plate.common(fuss2)
        vol_i = float(common.Volume) if common and not common.isNull() else 0.0
        dist_touch = plate.distToShape(fuss2)[0]
        # 0,05 mm über dem Boden: Abstand soll das seitliche Spiel sein (Soll 0,25 mm)
        fuss3 = fuss.copy()
        fuss3.translate(App.Vector(0, 0, z + 1.0))
        dist_xy = plate.distToShape(fuss3)[0]
        no_clash = vol_i < 0.5
        results.append(report(
            "Passung Fuss in 1x1-Platte",
            no_clash and 0.12 <= dist_xy <= 0.35,
            "Interferenzvolumen=%.4f mm³, Abstand aufsitzend=%.4f mm, seitliches Spiel≈%.4f mm (Soll 0,25), Sitz-Z=%.3f mm"
            % (vol_i, dist_touch, dist_xy, z),
        ))
        print("DEBUG platte bbox", plate.BoundBox.XMin, plate.BoundBox.XMax, plate.BoundBox.YMin, plate.BoundBox.YMax, plate.BoundBox.ZMin, plate.BoundBox.ZMax)

        # Box 1x1x3
        p_box = default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=3, Stapellippe=1, Fachanzahl_X=1, Fachanzahl_Y=1)
        box = make_box_shape(p_box)
        bx, by, bz = box_outer_size(p_box)
        bb = box.BoundBox
        box_ok = box.isValid() and box.Volume > 0
        size_ok = abs(bb.XLength - bx) < 0.2 and abs(bb.YLength - by) < 0.2 and abs(bb.ZLength - bz) < 0.3
        results.append(report(
            "Box 1x1x3 gültig",
            box_ok and size_ok,
            "valid=%s solids=%d vol=%.1f bbox=%.3fx%.3fx%.3f soll=%.3fx%.3fx%.3f"
            % (box.isValid(), len(box.Solids), box.Volume, bb.XLength, bb.YLength, bb.ZLength, bx, by, bz),
        ))

        box2 = box.copy()
        box2.translate(App.Vector(0, 0, z))
        common = plate.common(box2)
        vol_i = float(common.Volume) if common and not common.isNull() else 0.0
        dist = plate.distToShape(box2)[0]
        results.append(report(
            "Passung Box 1x1x3 in 1x1-Platte",
            vol_i < 0.5,
            "Interferenzvolumen=%.4f mm³, Mindestabstand=%.4f mm" % (vol_i, dist),
        ))

        clip = make_verbinder_clip_shape(p_plate)
        results.append(report(
            "Plattenverbinder gültig",
            clip.isValid() and clip.Volume > 0,
            "valid=%s vol=%.1f size=%.2fx%.2fx%.2f" % (
                clip.isValid(), clip.Volume, clip.BoundBox.XLength, clip.BoundBox.YLength, clip.BoundBox.ZLength
            ),
        ))

        rast = make_rastclip_shape(p_box)
        results.append(report(
            "Rastclip gültig",
            rast.isValid() and rast.Volume > 0,
            "valid=%s vol=%.1f size=%.2fx%.2fx%.2f" % (
                rast.isValid(), rast.Volume, rast.BoundBox.XLength, rast.BoundBox.YLength, rast.BoundBox.ZLength
            ),
        ))

    except Exception:
        traceback.print_exc()
        results.append(report("Ausnahme im Smoke-Test", False, traceback.format_exc()))

    out = OUT / "smoke_results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    failed = [r for r in results if not r["ok"]]
    print("----")
    print("Smoke: %d bestanden, %d nicht bestanden" % (len(results) - len(failed), len(failed)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
