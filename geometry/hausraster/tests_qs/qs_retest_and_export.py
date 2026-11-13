# -*- coding: utf-8 -*-
"""Nachtest der Korrekturen und Export der QS1-Dateien sowie des physischen Testsatzes."""
from __future__ import annotations
import json, sys, traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (HERE, ROOT/"src", ROOT/"FreeCAD_Mod/Hausraster", ROOT/"FreeCAD_Mod/HausrasterPhase3"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import FreeCAD as App
import Part
from hausraster_const import default_params, pruefe_parameter, box_hoehe, SYSTEM_VERSION, RASTER_MM, PLA_DICHTE_G_CM3
from hausraster_geom import (
    make_plate_shape, make_box_shape, make_verbinder_clip_shape, make_rastclip_shape,
    make_passung_verbinder_shape, plate_outer_size, box_outer_size, seated_box_z_on_plate,
)
from hausraster_fcstd import create_document, export_stl, export_step
from hausraster_phase3_fcstd import params_from_sheet
from hausraster_phase3_plan import plane_halter
from hausraster_phase3_geom import halter_teile

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
QS_DIR = ROOT / "08_qs1_korrekturen"
QS_DIR.mkdir(exist_ok=True)
TEST_DIR = ROOT / "06_testdrucke" / "QS_Minimaltestsatz"
TEST_DIR.mkdir(parents=True, exist_ok=True)
SRC = ROOT / "src"

results = []

def rec(name, status, details="", **mw):
    results.append({"name": name, "status": status, "details": details, "messwerte": mw})
    print("RETTEST", status, name, details[:120], flush=True)


def vol_common(a, b):
    c = a.common(b)
    return 0.0 if c is None or c.isNull() else abs(float(c.Volume) or 0.0)


def place(sh, x, y, z):
    s = sh.copy()
    s.translate(App.Vector(x, y, z))
    return s


def test_fixes():
    # 8x8 in 2x2 now rejected
    e = pruefe_parameter(default_params(Einheiten_X=2, Einheiten_Y=2, Fachanzahl_X=8, Fachanzahl_Y=8))
    rec("8x8 Faecher in 2x2 abgelehnt", "BESTANDEN" if e else "FEHLERHAFT", "; ".join(e or []))

    # 1u with lip allowed, without lip rejected
    e_lip = pruefe_parameter(default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=1, Stapellippe=1))
    e_nol = pruefe_parameter(default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=1, Stapellippe=0))
    rec("1u-Box mit Lippe erlaubt", "BESTANDEN" if not e_lip else "FEHLERHAFT", "; ".join(e_lip or []))
    rec("1u-Box ohne Lippe abgelehnt", "BESTANDEN" if e_nol else "FEHLERHAFT", "; ".join(e_nol or []))

    # Apostroph
    doc = App.newDocument("qs_apo")
    try:
        sh = doc.addObject("Spreadsheet::Sheet", "HIER_MASSE_AENDERN")
        sh.set("A2", "Modelltyp"); sh.set("B2", "schraege")
        try: sh.setAlias("B2", "Modelltyp")
        except Exception: pass
        sh.set("A3", "Schubladenbreite"); sh.set("B3", "200")
        doc.recompute()
        params = params_from_sheet(sh)
        typ = params.get("Modelltyp")
        rec("params_from_sheet Modelltyp", "BESTANDEN" if typ in ("schraege", "schräge") else "FEHLERHAFT",
            typ=typ, get=repr(sh.get("B2")))
    finally:
        App.closeDocument(doc.Name)

    # Halter bbox
    plan = plane_halter({"Glasdurchmesser": 55})
    _p, shapes = halter_teile({"Glasdurchmesser": 55})
    body = shapes["Halter"]
    bb = body.BoundBox
    rec("Halter D55 Mass inkl. Ansaetze",
        "BESTANDEN" if abs(bb.XLength - plan.breite) < 0.4 and abs(bb.YLength - plan.tiefe) < 0.4 else "FEHLERHAFT",
        soll=[plan.breite, plan.tiefe, plan.hoehe], ist=[bb.XLength, bb.YLength, bb.ZLength],
        hinweise=plan.hinweise)

    # Verbinder Drucklage
    clip_p = make_verbinder_clip_shape(default_params(), drucklage=True)
    clip_m = make_verbinder_clip_shape(default_params(), drucklage=False)
    rec("Verbinder Drucklage ZMin=0", "BESTANDEN" if abs(clip_p.BoundBox.ZMin) < 0.05 else "FEHLERHAFT",
        zmin_druck=clip_p.BoundBox.ZMin, zmin_fuege=clip_m.BoundBox.ZMin)

    # Rib pockets + engagement on 3x3
    p = default_params(Einheiten_X=3, Einheiten_Y=3, Verbinder=1, Verriegelung=1)
    pl = make_plate_shape(p)
    sx, sy, sz = plate_outer_size(p)
    # Rib at y=+21 (k=2? k=1 -> y=cy0+rand+1*42 = -63+42=-21; k=2 -> +21)
    # Probe 2mm cube in rib near right edge, should have a pocket (air at edge mid-rib)
    # and material beside it.
    def cube(x,y,z=2.2,s=1.8):
        return Part.makeBox(s,s,s, App.Vector(x-s/2,y-s/2,z))
    air_rib = vol_common(pl, cube(sx/2 - 4, 21))
    mat_cell = vol_common(pl, cube(sx/2 - 4, 0))  # cell center still the well (air)
    rec("Rippen-Tasche rechts y=21 (Luft in Tasche)", "BESTANDEN" if air_rib < 0.5 else "FEHLERHAFT",
        air_rib=air_rib, air_zellmitte=mat_cell)

    pl_r = place(pl, sx, 0, 0)
    clip = place(clip_m, sx/2.0, 21.0, 0)
    v_l = vol_common(pl, clip)
    v_r = vol_common(pl_r, clip)
    # clearance fit: little collision
    rec("Clip auf Rippe, Kollision mit Plattenkoerper",
        "BESTANDEN" if v_l < 20 and v_r < 20 else "FEHLERHAFT",
        common_l=v_l, common_r=v_r, clip_vol=float(clip_m.Volume))
    # form closure: grow clip
    try:
        grown = clip.makeOffsetShape(0.35, 0.05, inter=False, self_inter=False)
        vg = vol_common(pl.fuse(pl_r), grown) if grown and not grown.isNull() else 0
    except Exception as exc:
        grown = None
        vg = -1
        rec("Offset-Clip", "EINGESCHRAENKT", str(exc))
    rec("Aufgewachsener Clip trifft Material (Formschluss-Hinweis)",
        "BESTANDEN" if vg > 20 else ("FEHLERHAFT" if vg >= 0 else "EINGESCHRAENKT"),
        grown_common=vg)
    # pull-out +X (out of left plate, into right): leftover
    pulled = place(clip_m, sx/2.0 + 6.0, 21.0, 0)
    rec("Clip 6 mm aus der Fuge gezogen, Kollision",
        "BESTANDEN" if vol_common(pl, pulled) + vol_common(pl_r, pulled) > 20 else "FEHLERHAFT",
        common=vol_common(pl, pulled)+vol_common(pl_r, pulled))

    # schale module importable from Mod path
    import hausraster_phase3_schale
    rec("Schalen-Modul importierbar", "BESTANDEN", path=hausraster_phase3_schale.__file__)

    # Init.py has except
    init = (ROOT/"FreeCAD_Mod/Hausraster/Init.py").read_text(encoding="utf-8")
    rec("Init.py hat __file__-Fallback", "BESTANDEN" if "except NameError" in init else "FEHLERHAFT")
    p3m = (ROOT/"macros/Hausraster_Phase3_NeuBerechnen.FCMacro").read_text(encoding="utf-8")
    rec("Phase-3-Makro schuetzt FreeCADGui und kennt Schale",
        "BESTANDEN" if "except ImportError" in p3m and "Schalenwand" in p3m else "FEHLERHAFT")
    p4m = (ROOT/"macros/Hausraster_Phase4_NeuBerechnen.FCMacro").read_text(encoding="utf-8")
    rec("Phase-4-Makro kennt APPDATA", "BESTANDEN" if "APPDATA" in p4m else "FEHLERHAFT")


def export_part(name, shape, dest: Path, bemerkung, params):
    dest.mkdir(parents=True, exist_ok=True)
    stl = dest / (name + ".stl")
    step = dest / (name + ".step")
    fc = dest / (name + ".FCStd")
    export_stl(shape, stl)
    export_step(shape, step)
    create_document(name, params, {name.split("HR_")[-1].split("_QS1")[0] or "Teil": shape}, fc, SRC, bemerkung)
    return stl, step, fc, float(shape.Volume)


def generate_qs1():
    infos = []
    bemerk = "QS1-Korrektur: Verbinder-Taschen sitzen auf den Rippen zwischen den Zellen, nicht in der Rastervertiefung. " + SYSTEM_VERSION
    plates = [
        (ROOT/"01_rastersystem", "HR_Grundplatte_3x3_QS1", dict(Einheiten_X=3, Einheiten_Y=3, Verbinder=1, Verriegelung=1)),
        (ROOT/"01_rastersystem"/ "Plan_450x350", "HR_Grundplatte_5x4_T1_QS1", dict(Einheiten_X=5, Einheiten_Y=4, Rand_X_links=14, Rand_Y_vorne=6, Verbinder=1, Verriegelung=1)),
        (ROOT/"01_rastersystem"/ "Plan_450x350", "HR_Grundplatte_5x4_T2_QS1", dict(Einheiten_X=5, Einheiten_Y=4, Rand_X_links=14, Rand_Y_hinten=6, Verbinder=1, Verriegelung=1)),
        (ROOT/"01_rastersystem"/ "Plan_450x350", "HR_Grundplatte_5x4_T3_QS1", dict(Einheiten_X=5, Einheiten_Y=4, Rand_X_rechts=14, Rand_Y_vorne=6, Verbinder=1, Verriegelung=1)),
        (ROOT/"01_rastersystem"/ "Plan_450x350", "HR_Grundplatte_5x4_T4_QS1", dict(Einheiten_X=5, Einheiten_Y=4, Rand_X_rechts=14, Rand_Y_hinten=6, Verbinder=1, Verriegelung=1)),
        (ROOT/"01_rastersystem"/ "Plan_500x400", "HR_Grundplatte_5x4_T1_QS1", dict(Einheiten_X=5, Einheiten_Y=4, Rand_X_links=36, Rand_Y_vorne=10, Verbinder=1, Verriegelung=1)),
        (ROOT/"01_rastersystem"/ "Plan_500x400", "HR_Grundplatte_5x5_T2_QS1", dict(Einheiten_X=5, Einheiten_Y=5, Rand_X_links=36, Rand_Y_hinten=10, Verbinder=1, Verriegelung=1)),
        (ROOT/"01_rastersystem"/ "Plan_500x400", "HR_Grundplatte_6x4_T3_QS1", dict(Einheiten_X=6, Einheiten_Y=4, Rand_Y_vorne=10, Verbinder=1, Verriegelung=1)),
        (ROOT/"01_rastersystem"/ "Plan_500x400", "HR_Grundplatte_6x5_T4_QS1", dict(Einheiten_X=6, Einheiten_Y=5, Rand_Y_hinten=10, Verbinder=1, Verriegelung=1)),
    ]
    for dest, name, kw in plates:
        p = default_params(**kw)
        sh = make_plate_shape(p)
        stl, step, fc, vol = export_part(name, sh, dest, bemerk, p)
        anl = dest / (name + "_Anleitung.md")
        anl.write_text(
            "# %s\n\n%s\n\nAussenmass: %.2f × %.2f × %.2f mm.\n"
            "Die Verbinder-Taschen liegen auf den Rippen zwischen den Zellen.\n"
            "Ein-Zellen-Kanten haben keinen Plattenverbinder (keine Rippe).\n"
            "Bitte die ältere Datei ohne _QS1 nicht mehr für neue Drucke verwenden.\n" % (
                name, bemerk, *plate_outer_size(p)
            ),
            encoding="utf-8",
        )
        infos.append({"name": name, "vol": vol, "size": list(plate_outer_size(p)), "pfad": str(stl.relative_to(ROOT))})
        print("exported", name, flush=True)

    # Verbinder print-flat
    p = default_params()
    clip = make_verbinder_clip_shape(p, drucklage=True)
    dest = ROOT/"01_rastersystem"
    export_part("HR_Plattenverbinder_QS1", clip, dest,
                "QS1: Clip liegt auf Z=0 (Drucklage), Taschen spielen bleibt in der Platte.", p)
    (dest/"HR_Plattenverbinder_QS1_Anleitung.md").write_text(
        "# HR_Plattenverbinder_QS1\n\nDrucklage auf Z=0, ohne Stützen flach auf das Bett legen.\n"
        "Der Clip passt in die Rippen-Taschen der QS1-Grundplatten.\n"
        "ZMin der alten Datei ohne _QS1 lag bei 1,3 mm (Fügeposition, nicht druckfertig).\n",
        encoding="utf-8",
    )
    infos.append({"name": "HR_Plattenverbinder_QS1", "vol": float(clip.Volume), "zmin": clip.BoundBox.ZMin})
    return infos


def generate_testsatz():
    """Minimaler physischer Testsatz, eine Druckplatte 256er."""
    p2 = default_params(Einheiten_X=2, Einheiten_Y=2, Verbinder=1, Verriegelung=1)
    p21 = default_params(Einheiten_X=2, Einheiten_Y=1, Verbinder=1, Verriegelung=1)
    p11 = default_params(Einheiten_X=1, Einheiten_Y=1, Einheiten_Z=2, Stapellippe=1)
    pl22 = make_plate_shape(p2)
    pl21a = make_plate_shape(p21)
    pl21b = make_plate_shape(p21)
    box_a = make_box_shape(p11)
    box_b = make_box_shape(p11)
    clip = make_verbinder_clip_shape(default_params(), drucklage=True)
    rast = make_rastclip_shape(default_params())
    # Rastclip auf die Seite legen: XZ -> flach, rotate 90 around Y or X so thin dim is Z
    rast_flat = rast.copy()
    rast_flat.rotate(App.Vector(0, 0, 0), App.Vector(0, 1, 0), 90)
    rast_flat.translate(App.Vector(0, 0, -rast_flat.BoundBox.ZMin))
    leiste, clips, spiele = make_passung_verbinder_shape(default_params())

    # Arrange on bed z=0, with gaps
    gap = 6.0
    parts = {}
    # row 1: 2x2 plate
    def park(name, sh, x, y):
        s = sh.copy()
        s.translate(App.Vector(-s.BoundBox.XMin + x, -s.BoundBox.YMin + y, -s.BoundBox.ZMin))
        parts[name] = s
        return s.BoundBox

    x = 2.0
    y = 2.0
    bb = park("Grundplatte_2x2", pl22, x, y)
    x2 = bb.XMax + gap
    bb2 = park("Grundplatte_2x1_A", pl21a, x2, y)
    park("Grundplatte_2x1_B", pl21b, x2, bb2.YMax + gap)
    # boxes
    yb = bb.YMax + gap
    bb3 = park("Box_1x1x2_A", box_a, x, yb)
    park("Box_1x1x2_B", box_b, bb3.XMax + gap, yb)
    # clips
    xc = x2 + 90
    park("Plattenverbinder", clip, xc, y)
    park("Rastclip_drucklage", rast_flat, xc, y + 20)
    # spielstufen
    park("Spielstufen_Leiste", leiste, 2.0, yb + 50)
    for i, c in enumerate(clips):
        park("Clip_Spiel_%.2f" % spiele[i], c, 2.0 + 40 + i * 18, yb + 50)

    # union for layout stl
    fused = None
    vols = {}
    for name, sh in parts.items():
        vols[name] = float(sh.Volume)
        export_stl(sh, TEST_DIR / (name + ".stl"))
        export_step(sh, TEST_DIR / (name + ".step"))
        fused = sh if fused is None else fused.fuse(sh)
    export_stl(fused, TEST_DIR / "HR_QS_Minimaltestsatz_Druckplatte.stl")
    # bbox of layout
    bb = fused.BoundBox
    total_vol = sum(vols.values())
    # Vollmaterial-Schätzung plus typischer 15%-Infill-Abschlag ist ungeeignet,
    # weil die Teile schon hohl sind. Angabe: Volumen * Dichte = Obergrenze (100 % Füllung).
    g_voll = total_vol / 1000.0 * PLA_DICHTE_G_CM3
    g_15 = g_voll  # already mostly walls; estimate 15% only for solid-ish? No: shapes are hollow solids of the actual plastic if printed 100% of the CAD volume.
    # CAD volume IS the plastic volume (hollow boxes already subtracted interior). 100% infill ≈ this mass.
    # With 15% infill, walls still dominate; use 1.0 * volume as conservative upper, 0.85 as typical for these thin parts? 
    # Honest: Masse bei 100 % Füllung des CAD-Volumens; im Slicer typischerweise etwas weniger durch Raster-Infill in dicken Zonen.
    meta = {
        "teile": {k: {"volumen_mm3": v, "masse_100pct_pla_g": v/1000.0*PLA_DICHTE_G_CM3} for k,v in vols.items()},
        "volumen_summe_mm3": total_vol,
        "masse_obere_grenze_pla_100pct_g": g_voll,
        "layout_bbox_mm": [bb.XLength, bb.YLength, bb.ZLength],
        "passt_auf_p2s": bb.XLength <= 256 and bb.YLength <= 256 and bb.ZLength <= 256,
        "dichtenhinweis": "PLA-Dichte 1,24 g/cm³ ist ein typischer Katalogwert, keine Messung.",
    }
    (TEST_DIR / "masse_schaetzung.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta, parts


def write_test_anleitung(meta):
    lines = []
    lines.append("# Prüf- und Messanleitung – Hausraster Minimal-Testsatz (QS1)")
    lines.append("")
    lines.append("Stand: 12. November 2026, Europe/Berlin. Digital geprüft, **nicht physisch erprobt**.")
    lines.append("")
    lines.append("## Was liegt auf der Druckplatte")
    lines.append("")
    lines.append("Eine Anordnung `HR_QS_Minimaltestsatz_Druckplatte.stl` für den Bambu Lab P2S (256 × 256 mm), plus Einzel-STLs.")
    lines.append("")
    for k, v in meta["teile"].items():
        lines.append("- **%s**: CAD-Volumen %.0f mm³, obere Massengrenze (PLA, 100 %% des CAD-Volumens) **%.1f g**" % (k, v["volumen_mm3"], v["masse_100pct_pla_g"]))
    lines.append("")
    lines.append("Summe obere Grenze: **%.1f g PLA**. Im Slicer (Bambu PLA Basic, 0,20 mm Schicht, 3 Wände, 15 %% Infill) kann der Wert etwas darunter liegen, weil dicke Zonen nicht voll gefüllt werden; dünnwandige Teile liegen nahe an dieser Grenze." % meta["masse_obere_grenze_pla_100pct_g"])
    lines.append("Layout-BBox: %.1f × %.1f × %.1f mm, passt auf den P2S: %s." % (*meta["layout_bbox_mm"], "ja" if meta["passt_auf_p2s"] else "NEIN"))
    lines.append("")
    lines.append("## Druck")
    lines.append("")
    lines.append("- Material: PLA oder PETG, Düse 0,4 mm, Schicht 0,20 mm, 3 Wände, 15 % Infill, 0,8 mm Boden/Deckel.")
    lines.append("- Orientierung: alle Teile liegen bereits druckfertig auf Z=0. Den Rastclip nicht erneut umlegen.")
    lines.append("- Stützen: nicht vorgesehen. Falls der Slicer welche vorschlägt, zuerst die Lage prüfen.")
    lines.append("- Brim: 3–5 mm, besonders bei der 2×2-Platte und den Boxen.")
    lines.append("- Nach dem Druck: Brim entfernen, keine scharfen Grate an den Füßen und in den Taschen stehen lassen.")
    lines.append("")
    lines.append("## Sollwerte und Toleranzen (Messschieber)")
    lines.append("")
    lines.append("| Teil | Maß | Soll | Toleranz |")
    lines.append("|---|---|---:|---|")
    lines.append("| Grundplatte 2×2 | Außen X und Y | 84,00 mm | ±0,30 mm |")
    lines.append("| Grundplatte 2×2 | Höhe | 5,45 mm | ±0,15 mm |")
    lines.append("| Grundplatte 2×1 | Außen | 84,00 × 42,00 mm | ±0,30 mm |")
    lines.append("| Box 1×1×2 mit Lippe | Außen X und Y | 41,50 mm | ±0,20 mm |")
    lines.append("| Box 1×1×2 | Höhe inkl. Lippe | 18,40 mm (2×7 + 4,4) | ±0,25 mm |")
    lines.append("| Rasterabstand Taschenmitten | von Mitte zu Mitte | 42,00 mm | ±0,15 mm |")
    lines.append("| Plattenverbinder | Länge über beide Köpfe | 16,00 mm | ±0,20 mm |")
    lines.append("| Spielstufen-Noppen | 1 bis 5 Noppen | Spiel 0,10 / 0,15 / 0,20 / 0,25 / 0,30 mm je Seite | – |")
    lines.append("")
    lines.append("## Funktionsprüfungen")
    lines.append("")
    lines.append("### 1) Box auf die 2×2-Platte")
    lines.append("")
    lines.append("- Die Box soll in eine beliebige Zelle **ohne Kraft** einsinken und plan auf dem Taschenboden sitzen.")
    lines.append("- **Passt:** Füße stehen auf dem Boden, die Box lässt sich mit zwei Fingern gerade herausheben, seitliches Spiel merkbar, aber nicht so groß, dass sie in der Nachbarzelle klemmt.")
    lines.append("- **Klemmt:** zum Einsetzen ist Druck nötig oder sie verkantet. Dann `Passungsspiel` um 0,05 mm erhöhen (je Seite) und die Box neu erzeugen.")
    lines.append("- **Zu locker:** die Box rutscht schon bei leichtem Neigen der Platte aus der Zelle. `Passungsspiel` verringern oder bei 0,00 belassen und den Testdruck (Schwindung, Temperatur) prüfen.")
    lines.append("")
    lines.append("### 2) Zwei 2×1-Platten verbinden")
    lines.append("")
    lines.append("- Die 84-mm-Kanten mit der Rippe (Mitte der langen oder der 2er-Kante) aneinanderlegen. Der QS1-Clip gehört **auf die Rippe zwischen den zwei Zellen**, nicht in eine Zellmitte.")
    lines.append("- Clip von oben in beide Taschen schieben.")
    lines.append("- **Passt:** Clip gleitet mit leichtem Widerstand ein, Platten fluchten, lassen sich an der Fuge nicht seitlich versetzen, Clip ist ohne Werkzeug wieder lösbar.")
    lines.append("- **Klemmt:** nicht mit Gewalt. Denjenigen Spielwert aus dem Spielstufen-Test verwenden (siehe unten) und als `Verbinder_Spiel` eintragen, Platten neu erzeugen.")
    lines.append("- **Zu locker:** Fuge klafft oder die Platten lassen sich unter leichtem Zug trennen. Nächstkleineres Spiel wählen.")
    lines.append("")
    lines.append("### 3) Rastclip")
    lines.append("")
    lines.append("- Den Clip auf die Außenkante der 2×2-Platte an der Nut schieben, optional mit einer eingesetzten Box.")
    lines.append("- **Passt:** er hörbar oder fühlbar in die Nut greift und die Box nicht von selbst nach oben lässt, lässt sich aber abziehen.")
    lines.append("- **Klemmt / zu locker:** dies ist ein fest konstruiertes Spiel von 0,15 mm in der Nut. Klemmen oft durch Grat; zu locker durch Unterextrusion. Kein eigener Parameter; zuerst den Druck prüfen.")
    lines.append("")
    lines.append("### 4) Spielstufen-Leiste")
    lines.append("")
    lines.append("- Die fünf Clips haben 1 bis 5 Noppen für 0,10 bis 0,30 mm Spiel.")
    lines.append("- Jeden Clip in die zugehörige Tasche stecken (Noppenzahl = Stufe).")
    lines.append("- Den Wert der Stufe notieren, die **fest sitzt und sich ohne Werkzeug lösen lässt**. Diesen Wert als `Verbinder_Spiel` in `HIER_MASSE_AENDERN` eintragen und die Platten mit dem QS1-Makro neu berechnen.")
    lines.append("")
    lines.append("## Was dieser Testsatz nicht prüft")
    lines.append("")
    lines.append("- Bestecksegmente, Gewürzschalen, Deckel und Trennwände.")
    lines.append("- Langzeit-Haltekraft, Wärmebelastung in der Küche, Spülmaschinen-Tauglichkeit.")
    lines.append("- Gridfinity-Fremdteile (geometrisch an der 1×1-Platte digital geprüft, nicht mit diesem Satz gedruckt).")
    lines.append("")
    (TEST_DIR / "Pruefanleitung_Minimaltestsatz.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    print("SYSTEM", SYSTEM_VERSION, flush=True)
    test_fixes()
    infos = generate_qs1()
    meta, _ = generate_testsatz()
    write_test_anleitung(meta)
    report = {"version": SYSTEM_VERSION, "retests": results, "qs1": infos, "testsatz": meta}
    (OUT / "retest_qs1.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("RETEST FERTIG", json.dumps({r["name"]: r["status"] for r in results}, ensure_ascii=False), flush=True)

try:
    main()
except Exception:
    traceback.print_exc()
    sys.exit(1)
sys.exit(0)
