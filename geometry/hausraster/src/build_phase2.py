# -*- coding: utf-8 -*-
"""Phase 2: Referenzsysteme erzeugen, geometrisch prüfen und exportieren."""

from __future__ import annotations

import json
import math
import sys
import traceback
from pathlib import Path

sys.path.insert(0, "/workspace/ordnungssystem/src")

import FreeCAD as App
import Part

from hausraster_const import (
    SYSTEM_NAME, SYSTEM_VERSION, default_params, plattenhoehe, pruefe_parameter,
    PLA_DICHTE_G_CM3, BAURAUM_X, BAURAUM_Y, BAURAUM_Z, RASTER_MM,
    kasten_aussen, box_hoehe,
)
from hausraster_geom import (
    make_plate_shape, make_box_shape, make_fuss_stumpf_shape,
    make_verbinder_clip_shape, make_rastclip_shape, make_passung_verbinder_shape,
    plate_outer_size, box_outer_size, seated_box_z_on_plate, VEC,
)
from hausraster_fcstd import create_document, export_stl, export_step
from hausraster_plan import plane_schublade, plan_als_text

ROOT = Path("/workspace/ordnungssystem")
SRC = ROOT / "src"
DIR_PLATTE = ROOT / "01_rastersystem"
DIR_BOX = ROOT / "02_boxen"
DIR_TEST = ROOT / "06_testdrucke"
DIR_DOK = ROOT / "07_dokumentation"
DIR_TESTS = ROOT / "tests"
for d in (DIR_PLATTE, DIR_BOX, DIR_TEST, DIR_DOK, DIR_TESTS):
    d.mkdir(parents=True, exist_ok=True)

protocol = []


def log(name, status, detail, extra=None):
    rec = {"name": name, "status": status, "detail": detail}
    if extra:
        rec["extra"] = extra
    protocol.append(rec)
    print("[%s] %s: %s" % (status, name, detail))


def mass_schaetzung_g(volume_mm3):
    """Obere Schätzung bei 100 % Füllung, PLA 1,24 g/cm³ (typischer Herstellerwert)."""
    return volume_mm3 / 1000.0 * PLA_DICHTE_G_CM3


def bauraum_ok(size):
    return size[0] <= BAURAUM_X + 1e-3 and size[1] <= BAURAUM_Y + 1e-3 and size[2] <= BAURAUM_Z + 1e-3


def check_shape(name, shape, soll_size, tol=0.25):
    ok = True
    details = []
    if not shape.isValid():
        ok = False
        details.append("Shape.isValid()=False")
    nsol = len(shape.Solids)
    if nsol != 1:
        ok = False
        details.append("Solids=%d (erwartet 1)" % nsol)
    if shape.Volume is None or shape.Volume <= 0:
        ok = False
        details.append("Volumen ungültig")
    bb = shape.BoundBox
    size = [bb.XLength, bb.YLength, bb.ZLength]
    for a, b, achse in zip(size, soll_size, "XYZ"):
        if abs(a - b) > tol:
            ok = False
            details.append("%s %.3f ≠ Soll %.3f" % (achse, a, b))
    if not bauraum_ok(size):
        ok = False
        details.append("überschreitet P2S-Bauraum")
    details.append("bbox=%.3f×%.3f×%.3f Soll=%.3f×%.3f×%.3f vol=%.1f mm³  Schätzung %.2f g PLA (100 %% Füllung)"
                   % (size[0], size[1], size[2], soll_size[0], soll_size[1], soll_size[2],
                      shape.Volume, mass_schaetzung_g(shape.Volume)))
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN", "; ".join(details),
        extra={"size": size, "soll": list(soll_size), "volume_mm3": float(shape.Volume),
               "masse_g_schaetzung": round(mass_schaetzung_g(shape.Volume), 2)})
    return ok


def save_part(folder, stem, params, shapes, bemerkung, stl_deflection=0.08):
    fcstd = folder / (stem + ".FCStd")
    info = create_document(stem, params, shapes, fcstd, SRC, bemerkung)
    exports = {"fcstd": str(fcstd)}
    for name, shape in shapes.items():
        suffix = "" if len(shapes) == 1 else ("_" + name)
        stl = folder / (stem + suffix + ".stl")
        step = folder / (stem + suffix + ".step")
        export_stl(shape, stl, stl_deflection)
        export_step(shape, step)
        exports[name] = {"stl": str(stl), "step": str(step), "size_bytes_stl": stl.stat().st_size}
    return info, exports


def passung_box_platte(name, plate, box, z_sitz, min_xy=0.10, max_xy=0.40):
    box_s = box.copy()
    box_s.translate(App.Vector(0, 0, z_sitz))
    common = plate.common(box_s)
    vol = float(common.Volume) if common and not common.isNull() else 0.0
    dist0 = plate.distToShape(box_s)[0]
    box_l = box.copy()
    box_l.translate(App.Vector(0, 0, z_sitz + 1.0))
    dist_xy = plate.distToShape(box_l)[0]
    ok = vol < 0.5 and dist_xy >= min_xy
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN",
        "Interferenz=%.4f mm³, Abstand aufsitzend=%.4f mm, seitliches Spiel≈%.4f mm (Ziel %.2f–%.2f mm)"
        % (vol, dist0, dist_xy, min_xy, max_xy),
        extra={"interferenz_mm3": vol, "abstand_aufsitzend": dist0, "spiel_seitlich": dist_xy})
    return ok


def main():
    results_ok = True

    # ----- Referenz-Grundplatte 3x3 -----
    p_pl = default_params(Einheiten_X=3, Einheiten_Y=3, Verbinder=1, Verriegelung=1)
    errs = [e for e in pruefe_parameter(p_pl) if "Bodenstaerke_Box" not in e and "Lichter" not in e and "Fachanzahl" not in e and "Wandstaerke" not in e and "Einheiten_Z" not in e]
    if errs:
        log("Parameter Platte 3x3", "NICHT BESTANDEN", "; ".join(errs))
        results_ok = False
    plate = make_plate_shape(p_pl)
    ok = check_shape("Grundplatte 3x3 Recompute/Validität/BBox", plate, plate_outer_size(p_pl))
    results_ok = results_ok and ok
    save_part(DIR_PLATTE, "HR_Grundplatte_3x3", p_pl, {"Grundplatte": plate},
              "Referenz-Grundplatte 3×3 mit Verbinder-Taschen und Aussennut für den Rastclip. "
              "Gridfinity-kompatibles Aufnahmeprofil, magnetfrei.")

    # ----- Kleine Box 1x1x3 -----
    p_s = default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=3, Stapellippe=1, Fachanzahl_X=1, Fachanzahl_Y=1)
    box_s = make_box_shape(p_s)
    ok = check_shape("Box 1x1x3 Recompute/Validität/BBox", box_s, box_outer_size(p_s))
    results_ok = results_ok and ok
    save_part(DIR_BOX, "HR_Box_1x1x3", p_s, {"Box": box_s},
              "Kleine Referenz-Sortierbox 1×1×3 Höheneinheiten mit Stapellippe. "
              "Passend zur Hausraster- und zu üblichen Gridfinity-Grundplatten.")

    # ----- Grosse Box 2x2x3 -----
    p_l = default_params(Einheiten_X=2, Einheiten_Y=2, Einheiten_Z=3, Stapellippe=1, Fachanzahl_X=1, Fachanzahl_Y=1)
    box_l = make_box_shape(p_l)
    ok = check_shape("Box 2x2x3 Recompute/Validität/BBox", box_l, box_outer_size(p_l))
    results_ok = results_ok and ok
    save_part(DIR_BOX, "HR_Box_2x2x3", p_l, {"Box": box_l},
              "Große Referenz-Sortierbox 2×2×3 Höheneinheiten mit Stapellippe.")

    # Passung auf der 3x3-Platte: 1x1 in die Mittelzelle (Ursprung)
    z = seated_box_z_on_plate(p_pl)
    results_ok = passung_box_platte("Passung Box 1x1x3 in Platte 3x3 (Mitte)", plate, box_s, z) and results_ok
    # 2x2: Mittelpunkt um 21 mm versetzen, damit sie vier Zellen (nicht die Mitte zwischen Zellen der 3x3-Aussenkante) trifft
    # Eine 2x2-Box mittig auf 3x3 würde auf den Stegen sitzen. Versatz um eine halbe Zelle:
    box_l_pos = box_l.copy()
    box_l_pos.translate(App.Vector(-RASTER_MM / 2.0, -RASTER_MM / 2.0, 0))
    results_ok = passung_box_platte("Passung Box 2x2x3 in Platte 3x3 (versetzt)", plate, box_l_pos, z) and results_ok

    # ----- Plattenverbinder -----
    clip = make_verbinder_clip_shape(p_pl)
    # Sollgrösse: 16 x 12 x (hoehe - boden - abstand - frei)
    cbb = clip.BoundBox
    ok = clip.isValid() and clip.Volume > 0 and cbb.XLength > 15 and cbb.YLength > 11
    log("Plattenverbinder gültig", "BESTANDEN" if ok else "NICHT BESTANDEN",
        "valid=%s vol=%.1f size=%.2f×%.2f×%.2f  Schätzung %.2f g"
        % (clip.isValid(), clip.Volume, cbb.XLength, cbb.YLength, cbb.ZLength, mass_schaetzung_g(clip.Volume)),
        extra={"volume_mm3": float(clip.Volume), "masse_g_schaetzung": round(mass_schaetzung_g(clip.Volume), 2)})
    results_ok = results_ok and ok
    save_part(DIR_PLATTE, "HR_Plattenverbinder", p_pl, {"Plattenverbinder": clip},
              "Werkzeugloser Schwalbenschwanz-Clip (Doppelschwalbenschwanz). "
              "Von oben in die Taschen zweier aneinanderstoßender Platten einschieben. "
              "Spiel sitzt in der Tasche (Standard 0,20 mm je Seite).")

    # Verbinder gegen zwei 2x2-Platten
    p2 = default_params(Einheiten_X=2, Einheiten_Y=2, Verbinder=1, Verriegelung=0)
    pa = make_plate_shape(p2)
    pb = make_plate_shape(p2)
    pa.translate(App.Vector(-42.0, 0, 0))
    pb.translate(App.Vector(42.0, 0, 0))
    inter_ab = pa.common(pb)
    vol_ab = float(inter_ab.Volume) if inter_ab and not inter_ab.isNull() else 0.0
    log("Zwei 2x2-Platten stossen ohne Durchdringung",
        "BESTANDEN" if vol_ab < 0.5 else "NICHT BESTANDEN",
        "Interferenz der Platten untereinander: %.4f mm³" % vol_ab)

    clip_j = clip.copy()
    # Eine Tasche liegt bei y = +21 an der gemeinsamen Kante x=0
    clip_j.translate(App.Vector(0, 21.0, 0))
    inter_c = clip_j.common(pa.fuse(pb))
    vol_c = float(inter_c.Volume) if inter_c and not inter_c.isNull() else 0.0
    dist_c = clip_j.distToShape(pa.fuse(pb))[0]
    ok = vol_c < 0.5 and dist_c > 0.05
    log("Passung Verbinder in zwei 2x2-Platten",
        "BESTANDEN" if ok else "NICHT BESTANDEN",
        "Interferenz Clip/Platten=%.4f mm³, Mindestabstand=%.4f mm (Soll ca. 0,20 mm je Seite)"
        % (vol_c, dist_c),
        extra={"interferenz_mm3": vol_c, "abstand": dist_c})
    results_ok = results_ok and ok

    # ----- Rastclip -----
    rast = make_rastclip_shape(p_s)
    ok = rast.isValid() and rast.Volume > 0
    log("Rastclip gültig", "BESTANDEN" if ok else "NICHT BESTANDEN",
        "valid=%s vol=%.1f size=%.2f×%.2f×%.2f  Schätzung %.2f g"
        % (rast.isValid(), rast.Volume, rast.BoundBox.XLength, rast.BoundBox.YLength,
           rast.BoundBox.ZLength, mass_schaetzung_g(rast.Volume)),
        extra={"volume_mm3": float(rast.Volume), "masse_g_schaetzung": round(mass_schaetzung_g(rast.Volume), 2)})
    results_ok = results_ok and ok
    save_part(DIR_PLATTE, "HR_Rastclip", p_s, {"Rastclip": rast},
              "Mechanische Verriegelung ohne Magnete: C-Clip, der in die Aussennut der "
              "Grundplatte einhakt und über die Stapellippe der Box greift. Referenzgrösse für Box 3u. "
              "Im Slicer flach auf die Seite legen (C-Profil in die XY-Ebene). "
              "Ob der Clip im Alltag fest genug und leicht lösbar ist, zeigt erst der Testdruck.")

    # ----- Passungstest Fuss 1x1 -----
    p1 = default_params(Einheiten_X=1, Einheiten_Y=1, Verbinder=0, Verriegelung=0)
    plate1 = make_plate_shape(p1)
    fuss = make_fuss_stumpf_shape(p1)
    results_ok = check_shape("Passungsplatte 1x1", plate1, plate_outer_size(p1)) and results_ok
    ok = fuss.isValid() and fuss.Volume > 0
    log("Fussstumpf gültig", "BESTANDEN" if ok else "NICHT BESTANDEN",
        "valid=%s vol=%.1f h=%.2f  Schätzung %.2f g" % (
            fuss.isValid(), fuss.Volume, fuss.BoundBox.ZLength, mass_schaetzung_g(fuss.Volume)))
    results_ok = results_ok and ok
    results_ok = passung_box_platte("Passung Fussstumpf in Platte 1x1", plate1, fuss, seated_box_z_on_plate(p1)) and results_ok
    # Zum Drucken nebeneinander legen
    plate1_p = plate1.copy()
    fuss_p = fuss.copy()
    fuss_p.translate(App.Vector(42.0 + 8.0, 0, 0))
    save_part(DIR_TEST, "HR_Passung_Fuss_1x1", p1,
              {"Grundplatte_1x1": plate1, "Fussstumpf": fuss, "Druckanordnung": plate1_p.fuse(fuss_p)},
              "Testdruck mit minimalem Filamentverbrauch: 1×1-Plattenausschnitt und Box-Fussstumpf. "
              "Druckanordnung bereits nebeneinander platziert. Erst dieser Druck zeigt, ob das "
              "seitliche Spiel von 0,20 mm auf dem P2S greifbar und nicht zu locker ist.")

    # ----- Verbinder-Spielstufen -----
    leiste, clips, spiele = make_passung_verbinder_shape(p_pl)
    ok = leiste.isValid() and all(c.isValid() for c in clips)
    log("Verbinder-Spielstufen gültig", "BESTANDEN" if ok else "NICHT BESTANDEN",
        "Leiste valid=%s vol=%.1f, %d Clips, Spiele=%s  Schätzung Leiste+Clips %.2f g"
        % (leiste.isValid(), leiste.Volume, len(clips), spiele,
           mass_schaetzung_g(leiste.Volume + sum(c.Volume for c in clips))))
    results_ok = results_ok and ok
    shapes_vs = {"Leiste": leiste}
    for sp, c in zip(spiele, clips):
        shapes_vs["Clip_%.2f" % sp] = c
    angeordnet = leiste
    for c in clips:
        angeordnet = angeordnet.fuse(c)
    shapes_vs["Druckanordnung"] = angeordnet
    save_part(DIR_TEST, "HR_Passung_Verbinder_Spielstufen", p_pl, shapes_vs,
              "Fünf Verbinder-Taschen und fünf Clips mit Spiel 0,10 / 0,15 / 0,20 / 0,25 / 0,30 mm je Seite. "
              "Identifikation: 1 bis 5 Noppen. Den fest sitzenden, aber werkzeuglos lösbaren Clip merken "
              "und Verbinder_Spiel im Tabellenblatt entsprechend setzen.")

    # ----- Parametrik: drei Masse -----
    plate_cases = [
        default_params(Einheiten_X=1, Einheiten_Y=1, Verbinder=0, Verriegelung=0),
        default_params(Einheiten_X=3, Einheiten_Y=3, Verbinder=1, Verriegelung=1),
        default_params(Einheiten_X=4, Einheiten_Y=2, Verbinder=1, Verriegelung=1,
                       Rand_X_rechts=12.0, Rand_Y_hinten=8.0),
    ]
    for i, pc in enumerate(plate_cases, 1):
        try:
            sh = make_plate_shape(pc)
            ok = check_shape("Parametrik Platte Fall %d (%dx%d)" % (i, pc["Einheiten_X"], pc["Einheiten_Y"]),
                             sh, plate_outer_size(pc))
            results_ok = results_ok and ok
        except Exception:
            log("Parametrik Platte Fall %d" % i, "NICHT BESTANDEN", traceback.format_exc())
            results_ok = False

    box_cases = [
        default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=3, Stapellippe=1),
        default_params(Einheiten_X=2, Einheiten_Y=2, Einheiten_Z=3, Stapellippe=1),
        default_params(Einheiten_X=3, Einheiten_Y=1, Einheiten_Z=6, Stapellippe=1, Fachanzahl_X=3, Fachanzahl_Y=1),
    ]
    for i, pc in enumerate(box_cases, 1):
        try:
            sh = make_box_shape(pc)
            ok = check_shape("Parametrik Box Fall %d (%dx%dx%d, Fächer %dx%d)" % (
                i, pc["Einheiten_X"], pc["Einheiten_Y"], pc["Einheiten_Z"],
                pc["Fachanzahl_X"], pc["Fachanzahl_Y"]), sh, box_outer_size(pc), tol=0.30)
            results_ok = results_ok and ok
        except Exception:
            log("Parametrik Box Fall %d" % i, "NICHT BESTANDEN", traceback.format_exc())
            results_ok = False

    # ----- Schubladenplaner 450x350 und 500x400 -----
    for sx, sy in ((450, 350), (500, 400)):
        plan = plane_schublade(sx, sy)
        text = plan_als_text(plan)
        outp = DIR_PLATTE / ("Plan_%dx%d" % (sx, sy))
        outp.mkdir(exist_ok=True)
        (outp / "Plan.txt").write_text(text, encoding="utf-8")
        log("Schubladenplan %d×%d mm" % (sx, sy),
            "BESTANDEN" if not plan.ungueltig and all(pl.passt_in_bauraum for pl in plan.platten) else "NICHT BESTANDEN",
            text.replace("\n", " | "))
        # Platten erzeugen
        for i, pl in enumerate(plan.platten, 1):
            params = default_params(
                Einheiten_X=pl.einheiten_x, Einheiten_Y=pl.einheiten_y,
                Rand_X_links=pl.rand_x_links, Rand_X_rechts=pl.rand_x_rechts,
                Rand_Y_vorne=pl.rand_y_vorne, Rand_Y_hinten=pl.rand_y_hinten,
                Verbinder=1, Verriegelung=1,
            )
            try:
                sh = make_plate_shape(params)
                soll = plate_outer_size(params)
                ok = check_shape("Plan %d×%d Platte %d (%dx%d)" % (sx, sy, i, pl.einheiten_x, pl.einheiten_y),
                                 sh, soll)
                results_ok = results_ok and ok
                stem = "HR_Grundplatte_%dx%d_T%d" % (pl.einheiten_x, pl.einheiten_y, i)
                save_part(outp, stem, params, {"Grundplatte": sh},
                          "Erzeugt vom Schubladenplaner für %d×%d mm. Rasterposition (%d, %d). %s" % (
                              sx, sy, pl.pos_einheit_x, pl.pos_einheit_y, pl.hinweis))
            except Exception:
                log("Plan %d×%d Platte %d" % (sx, sy, i), "NICHT BESTANDEN", traceback.format_exc())
                results_ok = False

    (DIR_TESTS / "phase2_protokoll.json").write_text(
        json.dumps(protocol, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    failed = [r for r in protocol if r["status"] != "BESTANDEN"]
    print("----")
    print("Phase 2 intern: %d bestanden, %d nicht bestanden" % (len(protocol) - len(failed), len(failed)))
    # Datei als Exit-Hinweis
    (DIR_TESTS / "phase2_exit.txt").write_text("0" if not failed else "1", encoding="utf-8")
    return 0 if not failed else 1


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        traceback.print_exc()
        Path("/workspace/ordnungssystem/tests/phase2_exit.txt").write_text("1", encoding="utf-8")
        code = 1
    # FreeCADCmd ignoriert sys.exit manchmal; Datei ist massgeblich.
    sys.exit(code)
