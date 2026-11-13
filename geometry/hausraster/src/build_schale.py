# -*- coding: utf-8 -*-
"""Neue leichte Schalenversionen von Stufenregal und Schräge. Phase-3-Dateien bleiben unverändert."""
from __future__ import annotations
import json, math, sys, traceback
from pathlib import Path

sys.path.insert(0, "/workspace/ordnungssystem/src")
import FreeCAD as App
import Part

from hausraster_const import PLA_DICHTE_G_CM3, BAURAUM_X, BAURAUM_Y, BAURAUM_Z
from hausraster_phase3_fcstd import create_document, export_stl, export_step, PHASE3_VERSION
from hausraster_phase3_geom import VEC, make_segmentverbinder_clip, SEGMENT_CLIP_H, VERBINDER_TIEFE
from hausraster_phase3_schale import stufen_schale_teile, schraege_schale_teile, SCHALENWAND_STANDARD

ROOT = Path("/workspace/ordnungssystem")
SRC = ROOT / "src"
DIR_GEW = ROOT / "04_gewuerz"
DIR_DOK = ROOT / "07_dokumentation"
DIR_TESTS = ROOT / "tests"
for d in (DIR_GEW, DIR_DOK, DIR_TESTS):
    d.mkdir(parents=True, exist_ok=True)

# Masse der Vollkörper aus Phase-3-Protokoll (100 % PLA), zum Vergleich
VORHER = {
    "stufen_180x120_e3": 988.39,
    "stufen_400x180_e4_seg": 2426.22,
    "stufen_250x150_e3": 1713.37,
    "schraege_450x350_vorn": 1336.39,
    "schraege_450x350_hinten": 3289.73,
    "schraege_300x250_seg": 1678.52,
    "schraege_200x200": 1451.98,
}

protocol = []
masses = {}

def log(name, status, detail, extra=None):
    rec = {"name": name, "status": status, "detail": detail}
    if extra:
        rec["extra"] = extra
    protocol.append(rec)
    print("[%s] %s: %s" % (status, name, detail), flush=True)

def mass_g(v):
    return (v or 0) / 1000.0 * PLA_DICHTE_G_CM3

def bauraum_ok(size):
    return size[0] <= BAURAUM_X + 1e-3 and size[1] <= BAURAUM_Y + 1e-3 and size[2] <= BAURAUM_Z + 1e-3

def check_shape(name, shape, soll=None, tol=1.2):
    ok, details = True, []
    if not shape.isValid():
        ok = False
        details.append("isValid=False")
    if len(shape.Solids) != 1:
        ok = False
        details.append("Solids=%d" % len(shape.Solids))
    vol = float(shape.Volume) if shape.Volume else 0.0
    if vol <= 0:
        ok = False
        details.append("Volumen ungültig")
    bb = shape.BoundBox
    size = [bb.XLength, bb.YLength, bb.ZLength]
    if soll:
        for a, b, ax in zip(size, soll, "XYZ"):
            if abs(a - b) > tol:
                ok = False
                details.append("%s %.3f ≠ %.3f" % (ax, a, b))
    if not bauraum_ok(size):
        ok = False
        details.append("Bauraum 256 überschritten")
    details.append("bbox=%.2f×%.2f×%.2f vol=%.1f mm³ Schätzung %.2f g PLA (100 %% Füllung)"
                   % (size[0], size[1], size[2], vol, mass_g(vol)))
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN", "; ".join(details),
        extra={"size": size, "volume_mm3": vol, "masse_g_schaetzung": round(mass_g(vol), 2)})
    return ok

def interference(a, b, name, max_vol=0.05):
    try:
        vol = float(a.common(b).Volume or 0)
    except Exception as exc:
        log(name, "NICHT BESTANDEN", "common fehlgeschlagen: %s" % exc)
        return False
    ok = vol <= max_vol
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN", "Interferenzvolumen %.4f mm³" % vol,
        extra={"interferenz_mm3": vol})
    return ok

def save_part(stem, params, shapes, bemerkung):
    # niemals bestehende Phase-3-Namen überschreiben
    if not any(tag in stem for tag in ("_Schale", "_leicht")):
        raise RuntimeError("Schalen-Export ohne Kennzeichnung im Dateinamen: %s" % stem)
    fcstd = DIR_GEW / (stem + ".FCStd")
    if fcstd.exists() and "_Schale" not in fcstd.name:
        raise RuntimeError("würde bestehende Datei treffen: %s" % fcstd)
    info = create_document(stem, params, shapes, fcstd, SRC, bemerkung)
    for name, shape in shapes.items():
        suffix = "" if len(shapes) == 1 else ("_" + name)
        stl = DIR_GEW / (stem + suffix + ".stl")
        step = DIR_GEW / (stem + suffix + ".step")
        export_stl(shape, stl, 0.12)
        export_step(shape, step)
        masses[str(stl.relative_to(ROOT))] = {
            "volume_mm3": float(shape.Volume or 0),
            "masse_g_schaetzung": round(mass_g(shape.Volume or 0), 2),
            "size": [shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength],
        }
    log("export_" + stem, "BESTANDEN", "FCStd/STL/STEP (%d Körper)" % len(shapes))
    return info

def pocket_ys(length):
    n = max(1, int(math.floor((length - 30.0) / 80.0)) + 1)
    if n == 1:
        return [length / 2.0]
    span = length - 32.0
    return [16.0 + i * span / (n - 1) for i in range(n)]

def test_stufen_stoesse(plan, shapes, tag):
    teile = plan.segmente_x
    if len(teile) == 1:
        log(tag + "_stoesse", "BESTANDEN", "einteilig")
        return True
    ok = True
    x = 0.0
    placed = []
    for i, w in enumerate(teile, 1):
        sh = shapes["Segment_%d" % i].copy()
        sh.translate(VEC(x, 0, 0))
        placed.append((x, x + w, sh))
        x += w
    for i in range(len(placed) - 1):
        x0, x1, a = placed[i]
        _, _, b = placed[i + 1]
        ok &= interference(a, b, "%s_stoss_%d" % (tag, i + 1))
        clip = make_segmentverbinder_clip()
        clip.translate(VEC(x1, plan.tiefe - 14.0, 1.0))
        ok &= interference(a, clip, "%s_clip_a_%d" % (tag, i + 1))
        ok &= interference(b, clip, "%s_clip_b_%d" % (tag, i + 1))
    return ok

def test_schraege_stoesse(plan, shapes, tag):
    teile_x = plan.segmente_x
    teile_y = list(plan.segmente_y or [plan.tiefe])
    if len(teile_x) * len(teile_y) == 1:
        log(tag + "_stoesse", "BESTANDEN", "einteilig")
        return True
    ok = True
    placed = {}
    y = 0.0
    for iy, dy in enumerate(teile_y, 1):
        x = 0.0
        for ix, w in enumerate(teile_x, 1):
            sh = shapes["Segment_%d_%d" % (ix, iy)].copy()
            sh.translate(VEC(x, y, 0))
            placed[(ix, iy)] = (x, y, w, dy, sh)
            x += w
        y += dy
    for (ix, iy), (x, y, w, dy, sh) in placed.items():
        if (ix + 1, iy) in placed:
            sh2 = placed[(ix + 1, iy)][4]
            ok &= interference(sh, sh2, "%s_stoss_x_%d_%d" % (tag, ix, iy))
            clip = make_segmentverbinder_clip()
            clip.translate(VEC(x + w, y + max(14.0, dy - 14.0), 1.0))
            ok &= interference(sh, clip, "%s_clip_x_a_%d_%d" % (tag, ix, iy))
            ok &= interference(sh2, clip, "%s_clip_x_b_%d_%d" % (tag, ix, iy))
        if (ix, iy + 1) in placed:
            sh2 = placed[(ix, iy + 1)][4]
            ok &= interference(sh, sh2, "%s_stoss_y_%d_%d" % (tag, ix, iy))
            clip = make_segmentverbinder_clip()
            clip.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 90)
            clip.translate(VEC(x + w / 2.0, y + dy, 1.0))
            ok &= interference(sh, clip, "%s_clip_y_a_%d_%d" % (tag, ix, iy))
            ok &= interference(sh2, clip, "%s_clip_y_b_%d_%d" % (tag, ix, iy))
    return ok

all_ok = True
vergleich = []

stufen_variants = [
    ({"Gesamtbreite": 180, "Gesamttiefe": 120, "Ebenenanzahl": 3, "Glasdurchmesser": 55},
     "stufen_180x120_e3", None),
    ({"Gesamtbreite": 400, "Gesamttiefe": 180, "Ebenenanzahl": 4, "Glasdurchmesser": 55},
     "stufen_400x180_e4_seg", None),
    ({"Gesamtbreite": 250, "Gesamttiefe": 150, "Ebenenanzahl": 3, "Glasdurchmesser": 55},
     "stufen_250x150_e3", None),
]
for params, vkey, _ in stufen_variants:
    tag = "schale_" + vkey
    try:
        pfull = dict(params)
        pfull.update({"Modelltyp": "stufenregal", "Schalenwand": 2.0, "Verbinder_Spiel": 0.20, "Max_Segmentmass": 250.0,
                      "Stufenhoehe": 35.0, "Stufentiefe": 0.0, "Glasanzahl": 0, "Glasabstand": 4.0,
                      "Stufenlippe": 12.0, "Hinterlippe": 25.0, "Wandstaerke": 1.2})
        plan, shapes = stufen_schale_teile(pfull)
        segs = [k for k in shapes if k.startswith("Segment_")]
        for i, w in enumerate(plan.segmente_x, 1):
            all_ok &= check_shape("%s_Segment_%d" % (tag, i), shapes["Segment_%d" % i],
                                  soll=(w, plan.tiefe, plan.hoehe), tol=1.2)
        all_ok &= test_stufen_stoesse(plan, shapes, tag)
        g_new = [round(mass_g(shapes[k].Volume), 2) for k in segs]
        g_old = VORHER[vkey] if "seg" not in vkey else VORHER[vkey]
        vergleich.append({"modell": tag, "vorher_g": g_old, "nachher_g": g_new,
                          "bemerkung": "je Segment" if len(g_new) > 1 else "einteilig"})
        stem = "HR_Stufenregal_%dx%d_E%d_Schale" % (params["Gesamtbreite"], params["Gesamttiefe"], params["Ebenenanzahl"])
        bemerkung = (
            "LEICHTE SCHALENVERSION (neu, ersetzt den Vollkörper nicht). "
            "Nutzseite geschlossen und abwischbar, Unterseite offen mit Rippen. "
            "Schalenwand 2,0 mm. Empfohlene Drucklage: auf der glatten Aussenwand (X), dann stützenfrei. "
            "Hinweise:\n- " + "\n- ".join(plan.hinweise)
        )
        save_part(stem, pfull, shapes, bemerkung)
    except Exception:
        all_ok = False
        log(tag, "NICHT BESTANDEN", traceback.format_exc())

schraege_variants = [
    ({"Schubladenbreite": 450, "Schubladentiefe": 350, "Neigungswinkel": 15, "Verfuegbare_Hoehe": 90},
     "schraege_450x350"),
    ({"Schubladenbreite": 300, "Schubladentiefe": 250, "Neigungswinkel": 15, "Verfuegbare_Hoehe": 90},
     "schraege_300x250"),
    ({"Schubladenbreite": 200, "Schubladentiefe": 200, "Neigungswinkel": 15, "Verfuegbare_Hoehe": 90},
     "schraege_200x200"),
]
for params, vkey in schraege_variants:
    tag = "schale_" + vkey
    try:
        pfull = dict(params)
        pfull.update({"Modelltyp": "schraege", "Schalenwand": 2.0, "Schubladenspiel": 1.0,
                      "Glasdurchmesser": 55.0, "Glaslange": 110.0, "Glasabstand": 4.0, "Reihen": 0,
                      "Wandstaerke": 1.2, "Verbinder_Spiel": 0.20, "Max_Segmentmass": 250.0})
        plan, shapes = schraege_schale_teile(pfull)
        teile_y = plan.segmente_y or [plan.tiefe]
        for iy, dy in enumerate(teile_y, 1):
            for ix, w in enumerate(plan.segmente_x, 1):
                sh = shapes["Segment_%d_%d" % (ix, iy)]
                all_ok &= check_shape("%s_Segment_%d_%d" % (tag, ix, iy), sh, soll=None, tol=1.2)
                bb = sh.BoundBox
                over_y = Part.makeBox(w + 20, 2.0, 200, VEC(-10, dy + 0.2, -1))
                over_x = Part.makeBox(2.0, dy + 20, 200, VEC(w + 0.2, -10, -1))
                vy = float(sh.common(over_y).Volume or 0)
                vx = float(sh.common(over_x).Volume or 0)
                okm = vy <= 0.05 and vx <= 0.05 and abs(bb.XLength - w) <= 1.2 and abs(bb.YLength - dy) <= 1.2
                log("%s_Segment_%d_%d_mass" % (tag, ix, iy), "BESTANDEN" if okm else "NICHT BESTANDEN",
                    "Sonde X/Y %.4f/%.4f mm³; BBox %.2f×%.2f Soll %.2f×%.2f" % (vx, vy, bb.XLength, bb.YLength, w, dy))
                all_ok &= okm
        all_ok &= test_schraege_stoesse(plan, shapes, tag)
        # Vergleich: vorn/hinten bzw. je Segment / einteilig
        segs = sorted(k for k in shapes if k.startswith("Segment_"))
        g_new = [round(mass_g(shapes[k].Volume), 2) for k in segs]
        vergleich.append({"modell": tag, "vorher_ref": vkey, "nachher_g": g_new, "segmente": segs})
        stem = "HR_Schraege_%dx%d_Schale" % (params["Schubladenbreite"], params["Schubladentiefe"])
        bemerkung = (
            "LEICHTE SCHALENVERSION (neu, ersetzt den Vollkörper nicht). "
            "Oberseite und Front geschlossen, Unterseite offen mit Rippen. Schalenwand 2,0 mm. "
            "Empfohlene Drucklage: auf der glatten Aussenwand (X), dann stützenfrei. "
            "Hinweise:\n- " + "\n- ".join(plan.hinweise)
        )
        save_part(stem, pfull, shapes, bemerkung)
    except Exception:
        all_ok = False
        log(tag, "NICHT BESTANDEN", traceback.format_exc())

# Recompute einer neuen Schalen-FCStd
try:
    path = DIR_GEW / "HR_Stufenregal_180x120_E3_Schale.FCStd"
    doc = App.openDocument(str(path))
    doc.recompute()
    n = 0
    ok_r = True
    for obj in doc.Objects:
        if hasattr(obj, "Shape") and obj.Shape and not obj.Shape.isNull():
            n += 1
            if not obj.Shape.isValid() or len(obj.Shape.Solids) != 1:
                ok_r = False
    App.closeDocument(doc.Name)
    log("recompute_schale_stufen180", "BESTANDEN" if ok_r and n >= 1 else "NICHT BESTANDEN",
        "geöffnet, recompute, %d gültige Körper" % n)
    all_ok &= ok_r and n >= 1
except Exception:
    all_ok = False
    log("recompute_schale_stufen180", "NICHT BESTANDEN", traceback.format_exc())

passed = sum(1 for r in protocol if r["status"] == "BESTANDEN")
failed = sum(1 for r in protocol if r["status"] == "NICHT BESTANDEN")
out = {"version": PHASE3_VERSION + "-schale", "passed": passed, "failed": failed,
       "all_ok": all_ok and failed == 0, "tests": protocol, "masses": masses, "vergleich": vergleich}
(DIR_TESTS / "phase3_schale_protokoll.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print("PROTOKOLL %d bestanden, %d nicht, all_ok=%s" % (passed, failed, out["all_ok"]), flush=True)
print("VERGLEICH", json.dumps(vergleich, ensure_ascii=False), flush=True)
