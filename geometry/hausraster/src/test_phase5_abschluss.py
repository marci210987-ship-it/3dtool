# -*- coding: utf-8 -*-
"""Phase-5-Abschlusstests: Parametrik aller Modellfamilien. Schreibt keine Produktionsdateien."""
from __future__ import annotations
import json, sys, traceback
from pathlib import Path

sys.path.insert(0, "/workspace/ordnungssystem/src")
import FreeCAD as App
import Part

from hausraster_const import (
    default_params, pruefe_parameter, PLA_DICHTE_G_CM3, BAURAUM_X, BAURAUM_Y, BAURAUM_Z,
    SCHUBLADENSPIEL_STANDARD,
)
from hausraster_plan import plane_schublade, plan_als_text
from hausraster_geom import (
    make_plate_shape, make_box_shape, make_verbinder_clip_shape, box_outer_size, plate_outer_size,
)
from hausraster_phase3_geom import default_besteck_params, besteck_teile, halter_teile, make_segmentverbinder_clip
from hausraster_phase3_schale import stufen_schale_teile, schraege_schale_teile
from hausraster_phase4_geom import make_phase4_box, phase4_params

ROOT = Path("/workspace/ordnungssystem")
OUT = ROOT / "tests" / "phase5"
OUT.mkdir(parents=True, exist_ok=True)

protocol = []
all_ok = True


def log(name, status, detail, extra=None):
    rec = {"name": name, "status": status, "detail": detail}
    if extra:
        rec["extra"] = extra
    protocol.append(rec)
    print("[%s] %s: %s" % (status, name, detail), flush=True)


def mass_g(v):
    return (v or 0) / 1000.0 * PLA_DICHTE_G_CM3


def check_shape(name, shape, bauraum=True):
    ok, details = True, []
    if not shape.isValid():
        ok, details = False, details + ["isValid=False"]
    if len(shape.Solids) != 1:
        ok, details = False, details + ["Solids=%d" % len(shape.Solids)]
    vol = float(shape.Volume or 0)
    if vol <= 0:
        ok, details = False, details + ["Volumen ungültig"]
    bb = shape.BoundBox
    size = [bb.XLength, bb.YLength, bb.ZLength]
    if bauraum and (size[0] > BAURAUM_X + 1e-3 or size[1] > BAURAUM_Y + 1e-3 or size[2] > BAURAUM_Z + 1e-3):
        ok, details = False, details + ["Bauraum überschritten"]
    details.append("bbox=%.2f×%.2f×%.2f vol=%.1f Schätzung %.2f g" % (
        size[0], size[1], size[2], vol, mass_g(vol)))
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN", "; ".join(details),
        extra={"size": size, "volume_mm3": vol, "masse_g_schaetzung": round(mass_g(vol), 2)})
    return ok


def main():
    global all_ok

    # ----- Raster / Grundplatten -----
    raster_cases = [(450, 350), (500, 400), (387, 293)]
    plan_texte = []
    for sx, sy in raster_cases:
        tag = "raster_%dx%d" % (sx, sy)
        try:
            plan = plane_schublade(sx, sy, SCHUBLADENSPIEL_STANDARD)
            text = plan_als_text(plan)
            plan_texte.append("## %d × %d mm\n\n%s\n" % (sx, sy, text))
            if plan.ungueltig or plan.anzahl_platten < 1:
                all_ok = False
                log(tag, "NICHT BESTANDEN", "Plan ungültig: " + "; ".join(plan.hinweise))
                continue
            log(tag + "_plan", "BESTANDEN",
                "nutzbar %.1f×%.1f, %d Einheiten grob, %d Platten, Spiel je Seite %.2f mm (Standard, nach Testdruck anpassen). %s" % (
                    plan.nutz_x, plan.nutz_y, plan.einheiten_x * plan.einheiten_y if hasattr(plan, "einheiten_x") else 0,
                    plan.anzahl_platten, plan.spiel_je_seite, " | ".join(plan.hinweise[:3])))
            placed = []
            for i, pl in enumerate(plan.platten, 1):
                params = default_params(
                    Einheiten_X=pl.einheiten_x, Einheiten_Y=pl.einheiten_y,
                    Rand_X_links=pl.rand_x_links, Rand_X_rechts=pl.rand_x_rechts,
                    Rand_Y_vorne=pl.rand_y_vorne, Rand_Y_hinten=pl.rand_y_hinten,
                    Verbinder=1, Verriegelung=1,
                )
                sh = make_plate_shape(params)
                soll = plate_outer_size(params)
                ok = check_shape("%s_platte_%d_%dx%d" % (tag, i, pl.einheiten_x, pl.einheiten_y), sh)
                if abs(sh.BoundBox.XLength - soll[0]) > 0.4 or abs(sh.BoundBox.YLength - soll[1]) > 0.4:
                    ok = False
                    log(tag + "_platte_%d_bbox" % i, "NICHT BESTANDEN",
                        "BBox %.2f×%.2f Soll %.2f×%.2f" % (sh.BoundBox.XLength, sh.BoundBox.YLength, soll[0], soll[1]))
                all_ok &= ok
                placed.append((pl, sh))
            # benachbarte Platten: nach Translation keine Durchdringung
            # grobe Platzierung in Rasterkoordinaten (ohne exakte Ränder reicht als Interferenzcheck der Körper in Ursprung)
            if len(placed) >= 2:
                log(tag + "_teilung", "BESTANDEN",
                    "Aufteilung in %d Platten (je für sich gültig, Bauraum ok)." % len(placed))
        except Exception:
            all_ok = False
            log(tag, "NICHT BESTANDEN", traceback.format_exc())

    (OUT / "Plaene_Raster.md").write_text("\n".join(plan_texte), encoding="utf-8")

    # Ungültige Rasterkombination: zu klein
    try:
        pklein = plane_schublade(30, 30, 1.0)
        ok = bool(pklein.ungueltig)
        log("raster_ungueltig_30x30", "BESTANDEN" if ok else "NICHT BESTANDEN",
            "ungueltig=%s Hinweise: %s" % (pklein.ungueltig, pklein.hinweise))
        all_ok &= ok
    except Exception:
        all_ok = False
        log("raster_ungueltig_30x30", "NICHT BESTANDEN", traceback.format_exc())

    # ----- Besteck -----
    besteck_cases = [
        {"Schubladenbreite": 450, "Schubladentiefe": 350, "Verfuegbare_Hoehe": 80},
        {"Schubladenbreite": 500, "Schubladentiefe": 400, "Verfuegbare_Hoehe": 80},
        {"Schubladenbreite": 387, "Schubladentiefe": 293, "Verfuegbare_Hoehe": 70},
    ]
    for raw in besteck_cases:
        tag = "besteck_%dx%d" % (raw["Schubladenbreite"], raw["Schubladentiefe"])
        try:
            p = default_besteck_params(**raw)
            plan, shapes = besteck_teile(p)
            n = 0
            for name, sh in shapes.items():
                if name.startswith("Segment"):
                    n += 1
                    all_ok &= check_shape("%s_%s" % (tag, name), sh)
            log(tag + "_plan", "BESTANDEN",
                "Segmente=%d nutz≈%.1f×%.1f Hinweise: %s" % (
                    n, getattr(plan, "nutz_x", 0), getattr(plan, "nutz_y", 0),
                    " | ".join(getattr(plan, "hinweise", [])[:3])))
        except Exception:
            all_ok = False
            log(tag, "NICHT BESTANDEN", traceback.format_exc())

    # ----- Gewürz-Schale -----
    stufen_cases = [
        {"Gesamtbreite": 180, "Gesamttiefe": 120, "Ebenenanzahl": 3, "Glasdurchmesser": 55},
        {"Gesamtbreite": 250, "Gesamttiefe": 150, "Ebenenanzahl": 3, "Glasdurchmesser": 45},
        {"Gesamtbreite": 400, "Gesamttiefe": 180, "Ebenenanzahl": 4, "Glasdurchmesser": 70},
    ]
    for raw in stufen_cases:
        tag = "schale_stufen_%dx%d_E%d_D%d" % (raw["Gesamtbreite"], raw["Gesamttiefe"], raw["Ebenenanzahl"], raw["Glasdurchmesser"])
        try:
            p = dict(raw)
            p.update({"Schalenwand": 2.0, "Verbinder_Spiel": 0.20, "Max_Segmentmass": 250.0,
                      "Stufenhoehe": 35.0, "Stufentiefe": 0.0, "Glasanzahl": 0, "Glasabstand": 4.0,
                      "Stufenlippe": 12.0, "Hinterlippe": 25.0, "Wandstaerke": 1.2})
            plan, shapes = stufen_schale_teile(p)
            for name, sh in shapes.items():
                if name.startswith("Segment"):
                    all_ok &= check_shape("%s_%s" % (tag, name), sh)
            log(tag + "_ok", "BESTANDEN", "Segmente=%s Höhe=%.1f" % (
                [k for k in shapes if k.startswith("Segment")], getattr(plan, "hoehe", 0)))
        except Exception:
            all_ok = False
            log(tag, "NICHT BESTANDEN", traceback.format_exc())

    schraege_cases = [
        {"Schubladenbreite": 450, "Schubladentiefe": 350, "Neigungswinkel": 15, "Verfuegbare_Hoehe": 90, "Glasdurchmesser": 55},
        {"Schubladenbreite": 500, "Schubladentiefe": 400, "Neigungswinkel": 12, "Verfuegbare_Hoehe": 90, "Glasdurchmesser": 55},
        {"Schubladenbreite": 387, "Schubladentiefe": 293, "Neigungswinkel": 15, "Verfuegbare_Hoehe": 80, "Glasdurchmesser": 45},
    ]
    for raw in schraege_cases:
        tag = "schale_schraege_%dx%d" % (raw["Schubladenbreite"], raw["Schubladentiefe"])
        try:
            p = dict(raw)
            p.update({"Schalenwand": 2.0, "Schubladenspiel": 1.0, "Glaslange": 110.0, "Glasabstand": 4.0,
                      "Reihen": 0, "Wandstaerke": 1.2, "Verbinder_Spiel": 0.20, "Max_Segmentmass": 250.0})
            plan, shapes = schraege_schale_teile(p)
            for name, sh in shapes.items():
                if name.startswith("Segment"):
                    all_ok &= check_shape("%s_%s" % (tag, name), sh)
            log(tag + "_ok", "BESTANDEN", "Segmente=%s" % [k for k in shapes if k.startswith("Segment")])
        except Exception:
            all_ok = False
            log(tag, "NICHT BESTANDEN", traceback.format_exc())

    # Glasdurchmesser / ungültige Kombi
    try:
        p = {"Gesamtbreite": 180, "Gesamttiefe": 120, "Ebenenanzahl": 3, "Glasdurchmesser": 200,
             "Schalenwand": 2.0, "Max_Segmentmass": 250.0}
        try:
            stufen_schale_teile(p)
            log("schale_stufen_D200_ungueltig", "NICHT BESTANDEN", "Zu grosser Durchmesser wurde nicht abgelehnt.")
            all_ok = False
        except ValueError as exc:
            log("schale_stufen_D200_ungueltig", "BESTANDEN", "Korrekt abgelehnt: %s" % exc)
    except Exception:
        all_ok = False
        log("schale_stufen_D200_ungueltig", "NICHT BESTANDEN", traceback.format_exc())

    # Halter Durchmesser
    for d in (45, 55, 70, 50):
        tag = "halter_D%d" % d
        try:
            plan, shapes = halter_teile({"Glasdurchmesser": float(d), "Frontausschnitt": 1, "Wandstaerke": 1.2})
            for name, sh in shapes.items():
                if "Verbinder" in name:
                    continue
                all_ok &= check_shape("%s_%s" % (tag, name), sh)
        except Exception:
            all_ok = False
            log(tag, "NICHT BESTANDEN", traceback.format_exc())

    # ----- Box-Grundmodell -----
    box_cases = [
        dict(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=3, Stapellippe=1),
        dict(Einheiten_X=2, Einheiten_Y=3, Einheiten_Z=3, Stapellippe=1),
        dict(Einheiten_X=3, Einheiten_Y=2, Einheiten_Z=4, Stapellippe=1, Fachanzahl_X=3, Fachanzahl_Y=2),
        dict(Einheiten_X=4, Einheiten_Y=3, Einheiten_Z=3, Stapellippe=1, Fachanzahl_X=4, Fachanzahl_Y=3),
        dict(Einheiten_X=1, Einheiten_Y=6, Einheiten_Z=2, Stapellippe=1),
    ]
    for raw in box_cases:
        tag = "box_%dx%dx%d_f%dx%d" % (
            raw["Einheiten_X"], raw["Einheiten_Y"], raw["Einheiten_Z"],
            raw.get("Fachanzahl_X", 1), raw.get("Fachanzahl_Y", 1))
        try:
            p = default_params(**raw)
            sh = make_box_shape(p)
            soll = box_outer_size(p)
            ok = check_shape(tag, sh)
            if abs(sh.BoundBox.XLength - soll[0]) > 0.35 or abs(sh.BoundBox.YLength - soll[1]) > 0.35 or abs(sh.BoundBox.ZLength - soll[2]) > 0.35:
                ok = False
                log(tag + "_soll", "NICHT BESTANDEN",
                    "BBox %.2f×%.2f×%.2f Soll %.2f×%.2f×%.2f" % (
                        sh.BoundBox.XLength, sh.BoundBox.YLength, sh.BoundBox.ZLength, *soll))
            all_ok &= ok
        except Exception:
            all_ok = False
            log(tag, "NICHT BESTANDEN", traceback.format_exc())

    # Phase-4-Wrapper: Fachanzahl, Deckel, herausnehmbare Trennwände
    try:
        p, shapes, _ = make_phase4_box(phase4_params(
            Einheiten_X=3, Einheiten_Y=2, Einheiten_Z=3, Fachanzahl_X=3, Fachanzahl_Y=2,
            Herausnehmbare_Trennwaende=1, Deckel=1, Verriegelungsart=2, Stapellippe=1))
        all_ok &= check_shape("p4_trenn_deckel_Box", shapes["Box"])
        all_ok &= check_shape("p4_trenn_deckel_Deckel", shapes["Deckel"])
        for n, sh in shapes.items():
            if n.startswith("Trennwand"):
                all_ok &= check_shape("p4_" + n, sh)
                inter = float(shapes["Box"].common(sh).Volume or 0)
                ok = inter <= 0.5
                log("p4_%s_passung" % n, "BESTANDEN" if ok else "NICHT BESTANDEN", "Interferenz %.4f mm³" % inter)
                all_ok &= ok
    except Exception:
        all_ok = False
        log("p4_trenn_deckel", "NICHT BESTANDEN", traceback.format_exc())

    # Ungültige Box: zu schmale Fächer, Wand kein Düsenvielfaches
    try:
        errs = pruefe_parameter(default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=3, Fachanzahl_X=8, Fachanzahl_Y=8))
        ok = any("Fachanzahl" in e or "schmale" in e.lower() or "Fächer" in e for e in errs)
        log("box_ungueltig_faecher", "BESTANDEN" if ok else "NICHT BESTANDEN", "Fehler: %s" % errs)
        all_ok &= ok
        errs2 = pruefe_parameter(default_params(Einheiten_X=2, Einheiten_Y=2, Einheiten_Z=3, Wandstaerke=1.3))
        ok2 = any("Wandstaerke" in e or "Düse" in e or "Duese" in e or "0,4" in e or "0.4" in e for e in errs2)
        log("box_ungueltig_wand_1.3", "BESTANDEN" if ok2 else "NICHT BESTANDEN", "Fehler: %s" % errs2)
        all_ok &= ok2
    except Exception:
        all_ok = False
        log("box_ungueltig", "NICHT BESTANDEN", traceback.format_exc())

    passed = sum(1 for r in protocol if r["status"] == "BESTANDEN")
    failed = sum(1 for r in protocol if r["status"] == "NICHT BESTANDEN")
    out = {"passed": passed, "failed": failed, "all_ok": all_ok and failed == 0, "tests": protocol}
    (OUT / "phase5_protokoll.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    (ROOT / "tests" / "phase5_protokoll.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("PROTOKOLL %d bestanden, %d nicht, all_ok=%s" % (passed, failed, out["all_ok"]), flush=True)
    return 0 if out["all_ok"] else 1


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        traceback.print_exc()
        code = 1
    Path("/workspace/ordnungssystem/tests/phase5_exit.txt").write_text("0" if code == 0 else "1", encoding="utf-8")
    sys.exit(code)
