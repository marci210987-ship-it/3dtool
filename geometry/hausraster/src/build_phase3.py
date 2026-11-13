# -*- coding: utf-8 -*-
"""Phase 3: Besteck- und Gewürzmodelle erzeugen, prüfen, exportieren. Bestehende Phase-2-Dateien bleiben unverändert."""

from __future__ import annotations

import json
import math
import sys
import traceback
from pathlib import Path

sys.path.insert(0, "/workspace/ordnungssystem/src")

import FreeCAD as App
import Part

from hausraster_const import PLA_DICHTE_G_CM3, BAURAUM_X, BAURAUM_Y, BAURAUM_Z, FUSS_PROFIL_HOEHE
from hausraster_phase3_fcstd import create_document, export_stl, export_step, PHASE3_VERSION
from hausraster_phase3_geom import (
    VEC, VERBINDER_SPIEL_STANDARD, SEGMENT_CLIP_H, VERBINDER_TIEFE,
    besteck_teile, stufen_teile, schraege_teile, halter_teile,
    make_passung_segmentverbinder, make_segmentverbinder_clip,
    make_besteck_segment_shape,
)
from hausraster_phase3_plan import plane_besteck, plan_als_text

ROOT = Path("/workspace/ordnungssystem")
SRC = ROOT / "src"
DIR_BEST = ROOT / "03_besteck"
DIR_GEW = ROOT / "04_gewuerz"
DIR_TEST = ROOT / "06_testdrucke"
DIR_DOK = ROOT / "07_dokumentation"
DIR_TESTS = ROOT / "tests"
for d in (DIR_BEST, DIR_GEW, DIR_TEST, DIR_DOK, DIR_TESTS):
    d.mkdir(parents=True, exist_ok=True)

protocol = []
masses = {}


def log(name, status, detail, extra=None):
    rec = {"name": name, "status": status, "detail": detail}
    if extra:
        rec["extra"] = extra
    protocol.append(rec)
    print("[%s] %s: %s" % (status, name, detail), flush=True)


def mass_g(volume_mm3):
    return volume_mm3 / 1000.0 * PLA_DICHTE_G_CM3


def bauraum_ok(size):
    return size[0] <= BAURAUM_X + 1e-3 and size[1] <= BAURAUM_Y + 1e-3 and size[2] <= BAURAUM_Z + 1e-3


def check_shape(name, shape, soll_size=None, tol=0.4):
    ok = True
    details = []
    if not shape.isValid():
        ok = False
        details.append("Shape.isValid()=False")
    nsol = len(shape.Solids)
    if nsol != 1:
        ok = False
        details.append("Solids=%d (erwartet 1)" % nsol)
    vol = float(shape.Volume) if shape.Volume else 0.0
    if vol <= 0:
        ok = False
        details.append("Volumen ungültig")
    bb = shape.BoundBox
    size = [bb.XLength, bb.YLength, bb.ZLength]
    if soll_size is not None:
        for a, b, achse in zip(size, soll_size, "XYZ"):
            if abs(a - b) > tol:
                ok = False
                details.append("%s %.3f ≠ Soll %.3f" % (achse, a, b))
    if not bauraum_ok(size):
        ok = False
        details.append("überschreitet P2S-Bauraum 256 mm")
    details.append(
        "bbox=%.2f×%.2f×%.2f vol=%.1f mm³  Schätzung %.2f g PLA (100 %% Füllung)"
        % (size[0], size[1], size[2], vol, mass_g(vol))
    )
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN", "; ".join(details),
        extra={"size": size, "soll": list(soll_size) if soll_size else None,
               "volume_mm3": vol, "masse_g_schaetzung": round(mass_g(vol), 2)})
    return ok


def save_part(folder, stem, params, shapes, bemerkung, stl_deflection=0.12):
    fcstd = folder / (stem + ".FCStd")
    info = create_document(stem, params, shapes, fcstd, SRC, bemerkung)
    exports = {"fcstd": str(fcstd)}
    for name, shape in shapes.items():
        suffix = "" if len(shapes) == 1 else ("_" + name)
        stl = folder / (stem + suffix + ".stl")
        step = folder / (stem + suffix + ".step")
        export_stl(shape, stl, stl_deflection)
        export_step(shape, step)
        exports[name] = {"stl": str(stl), "step": str(step)}
        masses[str(stl.relative_to(ROOT))] = {
            "volume_mm3": float(shape.Volume) if shape.Volume else 0.0,
            "masse_g_schaetzung": round(mass_g(shape.Volume or 0), 2),
            "size": [shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength],
        }
    log("export_" + stem, "BESTANDEN", "FCStd/STL/STEP geschrieben (%d Körper)" % len(shapes),
        extra={"fcstd": str(fcstd)})
    return info, exports


def interference(a, b, name, max_vol=0.05):
    try:
        com = a.common(b)
        vol = float(com.Volume) if com and com.Volume else 0.0
    except Exception as exc:
        log(name, "NICHT BESTANDEN", "Boolean common fehlgeschlagen: %s" % exc)
        return False
    ok = vol <= max_vol
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN",
        "Interferenzvolumen %.4f mm³" % vol, extra={"interferenz_mm3": vol})
    return ok


def gap_after_lift(a, b, lift_vec, name):
    moved = b.copy()
    moved.translate(lift_vec)
    try:
        dist, *_ = a.distToShape(moved)
    except Exception as exc:
        log(name, "NICHT BESTANDEN", "distToShape fehlgeschlagen: %s" % exc)
        return False
    log(name, "BESTANDEN", "Abstand nach Anheben: %.3f mm" % dist, extra={"abstand_mm": dist})
    return True


def wall_probes_besteck(plan, shape, name):
    """Proben: Wandbereich sollte Material enthalten, Fachinneren nicht."""
    if not plan.faecher:
        log(name, "NICHT BESTANDEN", "keine Fächer")
        return False
    fach = plan.faecher[0]
    wand = plan.wand
    z0 = plan.boden + 8.0
    z1 = z0 + 6.0
    # Probe in der linken Aussenwand, Mitte der Tiefe
    pw = Part.makeBox(wand * 0.7, 8.0, z1 - z0, VEC(wand * 0.15, plan.nutz_y / 2.0 - 4.0, z0))
    # Probe mitten im ersten Fach
    fx = fach.x + fach.breite / 2.0
    fy = fach.y + fach.laenge / 2.0
    pi = Part.makeBox(6.0, 6.0, 6.0, VEC(fx - 3.0, fy - 3.0, z0))
    try:
        vw = float(shape.common(pw).Volume)
        vi = float(shape.common(pi).Volume)
    except Exception as exc:
        log(name, "NICHT BESTANDEN", "Sonden-Boolean fehlgeschlagen: %s" % exc)
        return False
    ok_w = vw >= 0.6 * pw.Volume
    ok_i = vi <= 0.05 * pi.Volume
    ok = ok_w and ok_i
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN",
        "Wandsonde %.1f/%.1f mm³, Fachsonde %.2f mm³ (soll ~0)" % (vw, pw.Volume, vi),
        extra={"wand_mm3": vw, "fach_mm3": vi})
    return ok


def pocket_ys(length):
    n = max(1, int(math.floor((length - 30.0) / 80.0)) + 1)
    if n == 1:
        return [length / 2.0]
    span = length - 32.0
    return [16.0 + i * span / (n - 1) for i in range(n)]


def test_besteck_stoesse(plan, shapes, tag):
    ok_all = True
    segs = plan.segmente
    # Segmente in Weltkoordinaten
    placed = {}
    for seg in segs:
        name = "Segment_%d_%d" % (seg.ix + 1, seg.iy + 1)
        sh = shapes[name].copy()
        sh.translate(VEC(seg.x0, seg.y0, 0))
        placed[(seg.ix, seg.iy)] = (seg, sh)
    # benachbarte Paare
    seen = set()
    for seg, sh in placed.values():
        for other in segs:
            if other is seg:
                continue
            key = tuple(sorted([(seg.ix, seg.iy), (other.ix, other.iy)]))
            if key in seen:
                continue
            dx = abs((seg.ix) - (other.ix)) + abs((seg.iy) - (other.iy))
            if dx != 1:
                continue
            # nur wirklich anstossend
            touch_x = abs(seg.x1 - other.x0) < 0.05 or abs(other.x1 - seg.x0) < 0.05
            touch_y = abs(seg.y1 - other.y0) < 0.05 or abs(other.y1 - seg.y0) < 0.05
            overlap_y = min(seg.y1, other.y1) - max(seg.y0, other.y0) > 5
            overlap_x = min(seg.x1, other.x1) - max(seg.x0, other.x0) > 5
            if not ((touch_x and overlap_y) or (touch_y and overlap_x)):
                continue
            seen.add(key)
            osh = placed[(other.ix, other.iy)][1]
            ok_all &= interference(sh, osh, "%s_stoss_%d_%d__%d_%d" % (tag, seg.ix, seg.iy, other.ix, other.iy))
            # ein Clip in der Fuge
            clip = make_segmentverbinder_clip(plan and VERBINDER_SPIEL_STANDARD)
            if touch_x and overlap_y:
                xj = seg.x1 if abs(seg.x1 - other.x0) < 0.05 else other.x1
                y0 = max(seg.y0, other.y0)
                length = min(seg.y1, other.y1) - y0
                y = y0 + pocket_ys(length)[0]
                z = 1.2
                clip.translate(VEC(xj, y, 1.0))
            else:
                yj = seg.y1 if abs(seg.y1 - other.y0) < 0.05 else other.y1
                x0 = max(seg.x0, other.x0)
                length = min(seg.x1, other.x1) - x0
                x = x0 + pocket_ys(length)[0]
                clip.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 90)
                clip.translate(VEC(x, yj, 1.0))
            ok_all &= interference(sh, clip, "%s_clip_a_%d_%d" % (tag, seg.ix, seg.iy))
            ok_all &= interference(osh, clip, "%s_clip_b_%d_%d" % (tag, other.ix, other.iy))
    if not seen and len(segs) > 1:
        log(tag + "_stoesse", "NICHT BESTANDEN", "keine anstossenden Segmentpaare gefunden")
        return False
    if len(segs) == 1:
        log(tag + "_stoesse", "BESTANDEN", "einteilig, keine Segmentfuge")
    return ok_all


def test_spice_stoesse(plan, shapes, tag, typ):
    teile_x = plan.segmente_x
    teile_y = list(getattr(plan, "segmente_y", None) or [])
    if typ != "schraege":
        teile_y = [plan.tiefe]
    elif not teile_y:
        teile_y = [plan.tiefe]
    if len(teile_x) * len(teile_y) == 1:
        log(tag + "_stoesse", "BESTANDEN", "einteilig, keine Segmentfuge")
        return True
    ok_all = True
    placed = {}
    y = 0.0
    for iy, dy in enumerate(teile_y, 1):
        x = 0.0
        for ix, w in enumerate(teile_x, 1):
            key = "Segment_%d_%d" % (ix, iy) if typ == "schraege" else "Segment_%d" % ix
            sh = shapes[key].copy()
            sh.translate(VEC(x, y, 0))
            placed[(ix, iy)] = (x, y, w, dy, sh)
            x += w
        y += dy
        if typ != "schraege":
            break
    for (ix, iy), (x, y, w, dy, sh) in placed.items():
        right = (ix + 1, iy)
        back = (ix, iy + 1)
        if right in placed:
            x2, y2, w2, dy2, sh2 = placed[right]
            ok_all &= interference(sh, sh2, "%s_stoss_x_%d_%d" % (tag, ix, iy))
            clip = make_segmentverbinder_clip()
            # hinterer Steg der Zelle, Mitte der Naht
            clip.translate(VEC(x + w, y + max(14.0, dy - 14.0), 1.0))
            ok_all &= interference(sh, clip, "%s_clip_x_a_%d_%d" % (tag, ix, iy))
            ok_all &= interference(sh2, clip, "%s_clip_x_b_%d_%d" % (tag, ix, iy))
        if back in placed:
            x2, y2, w2, dy2, sh2 = placed[back]
            ok_all &= interference(sh, sh2, "%s_stoss_y_%d_%d" % (tag, ix, iy))
            clip = make_segmentverbinder_clip()
            clip.rotate(VEC(0, 0, 0), VEC(0, 0, 1), 90)
            clip.translate(VEC(x + w / 2.0, y + dy, 1.0))
            ok_all &= interference(sh, clip, "%s_clip_y_a_%d_%d" % (tag, ix, iy))
            ok_all &= interference(sh2, clip, "%s_clip_y_b_%d_%d" % (tag, ix, iy))
    return ok_all


# ---------------------------------------------------------------------------
# Varianten
# ---------------------------------------------------------------------------
besteck_variants = [
    {"Schubladenbreite": 450, "Schubladentiefe": 350, "Einsatzhoehe": 45},
    {"Schubladenbreite": 500, "Schubladentiefe": 400, "Einsatzhoehe": 45},
    {"Schubladenbreite": 240, "Schubladentiefe": 200, "Einsatzhoehe": 45},
]
stufen_variants = [
    {"Gesamtbreite": 180, "Gesamttiefe": 120, "Ebenenanzahl": 3, "Glasdurchmesser": 55},
    {"Gesamtbreite": 400, "Gesamttiefe": 180, "Ebenenanzahl": 4, "Glasdurchmesser": 55},
    {"Gesamtbreite": 250, "Gesamttiefe": 150, "Ebenenanzahl": 3, "Glasdurchmesser": 55},
]
schraege_variants = [
    {"Schubladenbreite": 450, "Schubladentiefe": 350, "Neigungswinkel": 15, "Verfuegbare_Hoehe": 90},
    {"Schubladenbreite": 300, "Schubladentiefe": 250, "Neigungswinkel": 15, "Verfuegbare_Hoehe": 90},
    {"Schubladenbreite": 200, "Schubladentiefe": 200, "Neigungswinkel": 15, "Verfuegbare_Hoehe": 90},
]
halter_variants = [
    {"Glasdurchmesser": 45, "Frontausschnitt": 1},
    {"Glasdurchmesser": 55, "Frontausschnitt": 1},
    {"Glasdurchmesser": 70, "Frontausschnitt": 1},
]

all_ok = True
built = {}

# --- Besteck ---
for params in besteck_variants:
    tag = "besteck_%dx%d" % (params["Schubladenbreite"], params["Schubladentiefe"])
    try:
        pfull = dict(params)
        pfull["Modelltyp"] = "besteck"
        plan, shapes = besteck_teile(pfull)
        built[tag] = (plan, shapes, pfull)
        for seg in plan.segmente:
            name = "Segment_%d_%d" % (seg.ix + 1, seg.iy + 1)
            all_ok &= check_shape(
                "%s_%s" % (tag, name), shapes[name],
                soll_size=(seg.breite, seg.tiefe, plan.hoehe),
            )
        all_ok &= check_shape(tag + "_clip", shapes["Segmentverbinder"], soll_size=(16.0, 12.0, SEGMENT_CLIP_H), tol=0.15)
        if tag == "besteck_240x200":
            all_ok &= wall_probes_besteck(plan, shapes["Segment_1_1"], tag + "_wandstaerke")
        all_ok &= test_besteck_stoesse(plan, shapes, tag)
        bemerkung = (
            "Bestecksortierer %d × %d mm (lichte Schublade). %s\nHinweise:\n- %s"
            % (params["Schubladenbreite"], params["Schubladentiefe"],
               plan_als_text(plan), "\n- ".join(plan.hinweise) if plan.hinweise else "keine")
        )
        stem = "HR_Bestecksortierer_%dx%d" % (params["Schubladenbreite"], params["Schubladentiefe"])
        # Spreadsheet-Parameter vollständig
        sheet = {
            "Modelltyp": "besteck",
            "Schubladenbreite": params["Schubladenbreite"],
            "Schubladentiefe": params["Schubladentiefe"],
            "Verfuegbare_Hoehe": 80,
            "Schubladenspiel": 1.0,
            "Einsatzhoehe": params["Einsatzhoehe"],
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
            "Fach_1_Breite": 48.0, "Fach_1_Laenge": 0.0,
            "Fach_2_Breite": 55.0, "Fach_2_Laenge": 0.0,
            "Fach_3_Breite": 55.0, "Fach_3_Laenge": 0.0,
            "Fach_4_Breite": 50.0, "Fach_4_Laenge": 0.0,
            "Fach_5_Breite": 0.0, "Fach_5_Laenge": 0.0,
        }
        save_part(DIR_BEST, stem, sheet, shapes, bemerkung)
        # Plantext
        (DIR_BEST / (stem + "_Plan.txt")).write_text(plan_als_text(plan) + "\n\n" + "\n".join(plan.hinweise), encoding="utf-8")
    except Exception:
        all_ok = False
        log(tag, "NICHT BESTANDEN", traceback.format_exc())

# Parametrik: Höhe und Füsse am 240er
try:
    p_h = {"Schubladenbreite": 240, "Schubladentiefe": 200, "Einsatzhoehe": 55, "Modelltyp": "besteck"}
    plan_h, shapes_h = besteck_teile(p_h)
    sh = shapes_h["Segment_1_1"]
    all_ok &= check_shape("besteck_param_hoehe55", sh, soll_size=(plan_h.nutz_x, plan_h.nutz_y, 55.0))
except Exception:
    all_ok = False
    log("besteck_param_hoehe55", "NICHT BESTANDEN", traceback.format_exc())

try:
    p_f = {"Schubladenbreite": 240, "Schubladentiefe": 200, "Einsatzhoehe": 45, "Fuesse": 1, "Modelltyp": "besteck"}
    plan_f, shapes_f = besteck_teile(p_f)
    sh = shapes_f["Segment_1_1"]
    soll_z = 45.0 + FUSS_PROFIL_HOEHE
    all_ok &= check_shape("besteck_param_fuesse", sh, soll_size=(plan_f.nutz_x, plan_f.nutz_y, soll_z), tol=0.5)
except Exception:
    all_ok = False
    log("besteck_param_fuesse", "NICHT BESTANDEN", traceback.format_exc())

try:
    p_n = {"Schubladenbreite": 240, "Schubladentiefe": 200, "Einsatzhoehe": 45,
           "Trennwande_herausnehmbar": 1, "Modelltyp": "besteck"}
    plan_n, shapes_n = besteck_teile(p_n)
    ok_n = plan_n.herausnehmbar and any(k.startswith("Trennwand_") for k in shapes_n)
    for k, sh in shapes_n.items():
        if not (sh.isValid() and len(sh.Solids) == 1):
            ok_n = False
    log("besteck_param_nuten", "BESTANDEN" if ok_n else "NICHT BESTANDEN",
        "%d Trennwände, Körper gültig=%s" % (sum(1 for k in shapes_n if k.startswith("Trennwand_")), ok_n))
    all_ok &= ok_n
except Exception:
    all_ok = False
    log("besteck_param_nuten", "NICHT BESTANDEN", traceback.format_exc())

# --- Stufenregal ---
for params in stufen_variants:
    tag = "stufen_%dx%d_e%d" % (params["Gesamtbreite"], params["Gesamttiefe"], params["Ebenenanzahl"])
    try:
        pfull = dict(params)
        pfull["Modelltyp"] = "stufenregal"
        plan, shapes = stufen_teile(pfull)
        built[tag] = (plan, shapes, pfull)
        x = 0.0
        for i, w in enumerate(plan.segmente_x, 1):
            all_ok &= check_shape("%s_Segment_%d" % (tag, i), shapes["Segment_%d" % i],
                                  soll_size=(w, plan.tiefe, plan.hoehe), tol=0.6)
            x += w
        all_ok &= test_spice_stoesse(plan, shapes, tag, "stufen")
        sheet = {
            "Modelltyp": "stufenregal",
            "Gesamtbreite": params["Gesamtbreite"],
            "Gesamttiefe": params["Gesamttiefe"],
            "Ebenenanzahl": params["Ebenenanzahl"],
            "Stufenhoehe": 35.0,
            "Stufentiefe": 0.0,
            "Glasanzahl": 0,
            "Glasdurchmesser": params["Glasdurchmesser"],
            "Glasabstand": 4.0,
            "Stufenlippe": 12.0,
            "Hinterlippe": 25.0,
            "Wandstaerke": 1.2,
            "Bodenstaerke": 1.6,
            "Verbinder_Spiel": 0.20,
            "Max_Segmentmass": 250.0,
        }
        stem = "HR_Stufenregal_%dx%d_E%d" % (params["Gesamtbreite"], params["Gesamttiefe"], params["Ebenenanzahl"])
        bemerkung = "Stufenregal %s. Hinweise:\n- %s" % (tag, "\n- ".join(plan.hinweise))
        save_part(DIR_GEW, stem, sheet, shapes, bemerkung)
    except Exception:
        all_ok = False
        log(tag, "NICHT BESTANDEN", traceback.format_exc())

# --- Schräge ---
for params in schraege_variants:
    tag = "schraege_%dx%d" % (params["Schubladenbreite"], params["Schubladentiefe"])
    try:
        pfull = dict(params)
        pfull["Modelltyp"] = "schraege"
        plan, shapes = schraege_teile(pfull)
        built[tag] = (plan, shapes, pfull)
        teile_y = plan.segmente_y or [plan.tiefe]
        for iy, dy in enumerate(teile_y, 1):
            for ix, w in enumerate(plan.segmente_x, 1):
                sh = shapes["Segment_%d_%d" % (ix, iy)]
                all_ok &= check_shape("%s_Segment_%d_%d" % (tag, ix, iy), sh, soll_size=None, tol=1.2)
                # Getrimmte Rinnenflächen blähen die CAD-Bounding-Box um ~1 mm auf.
                # Massprüfung daher zusätzlich mit Sonden: hinter der Sollkante darf kein Material liegen.
                over_y = Part.makeBox(w + 20.0, 2.0, 200.0, VEC(-10, dy + 0.2, -1))
                over_x = Part.makeBox(2.0, dy + 20.0, 200.0, VEC(w + 0.2, -10, -1))
                try:
                    vy = float(sh.common(over_y).Volume)
                    vx = float(sh.common(over_x).Volume)
                except Exception as exc:
                    vy, vx = 1, 1
                    log("%s_Segment_%d_%d_mass" % (tag, ix, iy), "NICHT BESTANDEN", "Sonde fehlgeschlagen: %s" % exc)
                else:
                    bb = sh.BoundBox
                    okm = vy <= 0.05 and vx <= 0.05 and abs(bb.XLength - w) <= 1.2 and abs(bb.YLength - dy) <= 1.2
                    log("%s_Segment_%d_%d_mass" % (tag, ix, iy), "BESTANDEN" if okm else "NICHT BESTANDEN",
                        "Sonde hinter Sollkante X/Y %.4f/%.4f mm³; CAD-BBox %.2f×%.2f (Soll %.2f×%.2f, Höhe %.2f, Plan hinten %.2f)"
                        % (vx, vy, bb.XLength, bb.YLength, w, dy, bb.ZLength, plan.hoehe),
                        extra={"sonde_x_mm3": vx, "sonde_y_mm3": vy})
                    all_ok &= okm
        all_ok &= test_spice_stoesse(plan, shapes, tag, "schraege")
        sheet = {
            "Modelltyp": "schraege",
            "Schubladenbreite": params["Schubladenbreite"],
            "Schubladentiefe": params["Schubladentiefe"],
            "Schubladenspiel": 1.0,
            "Verfuegbare_Hoehe": params["Verfuegbare_Hoehe"],
            "Neigungswinkel": params["Neigungswinkel"],
            "Glasdurchmesser": 55.0,
            "Glaslange": 110.0,
            "Glasabstand": 4.0,
            "Reihen": 0,
            "Wandstaerke": 1.2,
            "Verbinder_Spiel": 0.20,
            "Max_Segmentmass": 250.0,
        }
        stem = "HR_Schraege_%dx%d" % (params["Schubladenbreite"], params["Schubladentiefe"])
        bemerkung = "Schräger Schubladeneinsatz %s. Hinweise:\n- %s" % (tag, "\n- ".join(plan.hinweise))
        save_part(DIR_GEW, stem, sheet, shapes, bemerkung)
    except Exception:
        all_ok = False
        log(tag, "NICHT BESTANDEN", traceback.format_exc())

# --- Halter ---
for params in halter_variants:
    tag = "halter_d%d" % params["Glasdurchmesser"]
    try:
        pfull = dict(params)
        pfull["Modelltyp"] = "halter"
        plan, shapes = halter_teile(pfull)
        built[tag] = (plan, shapes, pfull)
        all_ok &= check_shape(tag, shapes["Halter"], soll_size=None)
        # zwei Halter über den Clip: Ansätze stossen
        a = shapes["Halter"].copy()
        b = shapes["Halter"].copy()
        # Aussenbecher  Innen_D+2*wand, Pad steht VERBINDER_TIEFE+0.4 über
        pad = VERBINDER_TIEFE + 0.4
        aussen = plan.parameter["Aussenmass"]
        # Abstand der Mittelpunkte: aussen + 2*pad
        b.translate(VEC(aussen + 2 * pad, 0, 0))
        all_ok &= interference(a, b, tag + "_zwei_halter")
        clip = make_segmentverbinder_clip()
        clip.translate(VEC(aussen / 2.0 + pad, 0, 1.0))
        all_ok &= interference(a, clip, tag + "_clip_a")
        all_ok &= interference(b, clip, tag + "_clip_b")
        sheet = {
            "Modelltyp": "halter",
            "Glasdurchmesser": params["Glasdurchmesser"],
            "Glasspiel": 2.0,
            "Wandhoehe": 28.0,
            "Wandstaerke": 1.2,
            "Bodenstaerke": 1.6,
            "Frontausschnitt": params["Frontausschnitt"],
            "Verbinder_Spiel": 0.20,
        }
        stem = "HR_Gewuerzhalter_D%d" % params["Glasdurchmesser"]
        bemerkung = (
            "Modularer Einzelhalter Ø %d mm (Annahme). "
            "Seitliche Verbinder-Ansätze vergrössern das Aussenmass gegenüber dem Becher. Hinweise:\n- %s"
            % (params["Glasdurchmesser"], "\n- ".join(plan.hinweise))
        )
        save_part(DIR_GEW, stem, sheet, shapes, bemerkung)
    except Exception:
        all_ok = False
        log(tag, "NICHT BESTANDEN", traceback.format_exc())

# --- Testdruck Segmentverbinder ---
try:
    a, b, c = make_passung_segmentverbinder({"Verbinder_Spiel": 0.20})
    all_ok &= check_shape("passung_schiene0", a, soll_size=(28.0, 50.0, 12.0), tol=0.2)
    all_ok &= check_shape("passung_schiene1", b, soll_size=(28.0, 50.0, 12.0), tol=0.2)
    all_ok &= check_shape("passung_clip", c, soll_size=(16.0, 12.0, 8.0), tol=0.15)
    # zusammengefügt: Schiene 0 rechts bei x=14, Schiene 1 ist um 40 verschoben
    # und hat die Tasche links. Zum Fügen Schiene 1 an x=14 (Kante an Kante) schieben:
    # aktuell Mitte Schiene1 bei 40, linke Kante bei 26. Soll linke Kante bei 14 → um -12 schieben.
    b2 = b.copy()
    b2.translate(VEC(-12.0, 0, 0))
    all_ok &= interference(a, b2, "passung_schienen_stoss")
    clip = c.copy()
    # Clip liegt in der Druckanordnung bei x=20; Fuge nach dem Schieben bei x=14
    clip.translate(VEC(-6.0, 0, 1.0))
    all_ok &= interference(a, clip, "passung_clip_a")
    all_ok &= interference(b2, clip, "passung_clip_b")
    shapes = {"Schiene_A": a, "Schiene_B": b, "Segmentverbinder": c}
    # Druckanordnung: die drei Teile wie erzeugt (mit Abstand)
    sheet = {"Modelltyp": "segmentverbinder", "Verbinder_Spiel": 0.20}
    bemerkung = (
        "Kurzer Testdruck der Segmentverbindung (gleiches Schwalbenschwanz-Profil wie der "
        "Plattenverbinder, Höhe 8 mm). Schienen mit Abstand zum getrennten Druck; zum Fügen "
        "an den Taschenkanten stossen und den Clip von oben einsetzen."
    )
    save_part(DIR_TEST, "HR_Passung_Segmentverbinder", sheet, shapes, bemerkung)
    (DIR_TEST / "HR_Passung_Segmentverbinder_Anleitung.md").write_text(
        "# Testdruck Segmentverbinder\n\n"
        "Zwei kurze Schienen und ein Clip, gleiches Profil wie der Hausraster-Plattenverbinder, "
        "aber 8 mm hoch (für Einsätze, nicht für 5,45-mm-Platten).\n\n"
        "- Drucklage: Schienen auf den flachen Boden, Clip flach (die 8-mm-Höhe steht nach oben).\n"
        "- Stützen: konstruktiv nicht nötig. Vorschau trotzdem prüfen.\n"
        "- Nach dem Druck: Grate an den Taschen entfernen, Schienen an der Taschenkante stossen, "
        "Clip von oben in die Fuge schieben.\n"
        "- Passung: Standardspiel 0,20 mm je Seite, nicht durch Testdruck bestätigt.\n"
        "- Masse: Schätzung bei 100 % Füllung, siehe Testprotokoll.\n",
        encoding="utf-8",
    )
except Exception:
    all_ok = False
    log("passung_segmentverbinder", "NICHT BESTANDEN", traceback.format_exc())

# Recompute: FCStd öffnen und gespeicherte Körper prüfen
try:
    path = DIR_BEST / "HR_Bestecksortierer_240x200.FCStd"
    doc = App.openDocument(str(path))
    doc.recompute()
    ok_r = True
    n = 0
    for obj in doc.Objects:
        if hasattr(obj, "Shape") and obj.Shape and not obj.Shape.isNull():
            n += 1
            if not obj.Shape.isValid() or len(obj.Shape.Solids) != 1:
                ok_r = False
    App.closeDocument(doc.Name)
    log("recompute_fcstd_240", "BESTANDEN" if ok_r and n >= 2 else "NICHT BESTANDEN",
        "geöffnet, recompute, %d gültige Körper" % n)
    all_ok &= ok_r and n >= 2
except Exception:
    all_ok = False
    log("recompute_fcstd_240", "NICHT BESTANDEN", traceback.format_exc())

passed = sum(1 for r in protocol if r["status"] == "BESTANDEN")
failed = sum(1 for r in protocol if r["status"] == "NICHT BESTANDEN")
out = {
    "version": PHASE3_VERSION,
    "passed": passed,
    "failed": failed,
    "all_ok": all_ok and failed == 0,
    "tests": protocol,
    "masses": masses,
}
(DIR_TESTS / "phase3_protokoll.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
(DIR_TESTS / "phase3_exit.txt").write_text("0" if out["all_ok"] else "1", encoding="utf-8")
print("PROTOKOLL %d bestanden, %d nicht bestanden, all_ok=%s" % (passed, failed, out["all_ok"]), flush=True)
