# -*- coding: utf-8 -*-
"""Phase 4: fehlende Boxvarianten und Haushaltsorganizer. Bestehende Dateien bleiben unberührt."""
from __future__ import annotations
import json, math, sys, traceback
from pathlib import Path

sys.path.insert(0, "/workspace/ordnungssystem/src")
import FreeCAD as App
import Part

from hausraster_const import PLA_DICHTE_G_CM3, BAURAUM_X, BAURAUM_Y, BAURAUM_Z, WANDSTAERKE_STANDARD
from hausraster_geom import make_plate_shape, make_rastclip_shape, box_outer_size, plate_outer_size, seated_box_z_on_plate
from hausraster_phase4_geom import make_phase4_box, phase4_params, PHASE4_VERSION, VEC
from hausraster_phase4_fcstd import create_document_phase4
from hausraster_phase3_fcstd import export_stl, export_step  # identisch, Phase-2-Modul unberührt nutzen wir auch
from hausraster_fcstd import export_stl as export_stl2, export_step as export_step2

ROOT = Path("/workspace/ordnungssystem")
SRC = ROOT / "src"
DIR_BOX = ROOT / "02_boxen"
DIR_HAUS = ROOT / "05_haushalt"
DIR_DOK = ROOT / "07_dokumentation"
DIR_TESTS = ROOT / "tests"
GESCHUETZT = {
    "HR_Box_1x1x3.FCStd", "HR_Box_1x1x3.stl", "HR_Box_1x1x3.step", "HR_Box_1x1x3.png",
    "HR_Box_1x1x3_Anleitung.md",
    "HR_Box_2x2x3.FCStd", "HR_Box_2x2x3.stl", "HR_Box_2x2x3.step", "HR_Box_2x2x3.png",
    "HR_Box_2x2x3_Anleitung.md",
    "HINWEIS.txt",
}

protocol = []
masses = {}
all_ok = True


def log(name, status, detail, extra=None):
    rec = {"name": name, "status": status, "detail": detail}
    if extra:
        rec["extra"] = extra
    protocol.append(rec)
    print("[%s] %s: %s" % (status, name, detail), flush=True)


def mass_g(v):
    return (v or 0) / 1000.0 * PLA_DICHTE_G_CM3


def check_shape(name, shape, soll=None, tol=0.35):
    ok, details = True, []
    if not shape.isValid():
        ok = False
        details.append("isValid=False")
    if len(shape.Solids) != 1:
        ok = False
        details.append("Solids=%d" % len(shape.Solids))
    vol = float(shape.Volume or 0)
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
    if size[0] > BAURAUM_X + 1e-3 or size[1] > BAURAUM_Y + 1e-3 or size[2] > BAURAUM_Z + 1e-3:
        ok = False
        details.append("Bauraum 256 überschritten")
    details.append("bbox=%.2f×%.2f×%.2f vol=%.1f mm³ Schätzung %.2f g PLA (100 %% Füllung)"
                   % (size[0], size[1], size[2], vol, mass_g(vol)))
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN", "; ".join(details),
        extra={"size": size, "volume_mm3": vol, "masse_g_schaetzung": round(mass_g(vol), 2)})
    return ok


def passung_box_platte(name, plate, box, z_sitz, min_xy=0.10, max_xy=0.40):
    box_s = box.copy()
    box_s.translate(App.Vector(0, 0, z_sitz))
    common = plate.common(box_s)
    vol = float(common.Volume) if common and not common.isNull() else 0.0
    box_l = box.copy()
    box_l.translate(App.Vector(0, 0, z_sitz + 1.0))
    dist_xy = plate.distToShape(box_l)[0]
    ok = vol < 0.5 and dist_xy >= min_xy
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN",
        "Interferenz=%.4f mm³, seitliches Spiel≈%.4f mm (Ziel %.2f–%.2f mm)"
        % (vol, dist_xy, min_xy, max_xy),
        extra={"interferenz_mm3": vol, "spiel_seitlich": dist_xy})
    return ok


def wand_sonde(name, box, p):
    """Kleine Sonde in der Mitte der +X-Wand, knapp über dem Boden."""
    from hausraster_const import kasten_aussen, FUSS_PROFIL_HOEHE
    ax = kasten_aussen(int(p["Einheiten_X"]), float(p["Passungsspiel"]))
    wand = float(p["Wandstaerke"])
    z = FUSS_PROFIL_HOEHE + float(p["Bodenstaerke_Box"]) + 2.0
    # Sonde 0,4×0,4×2 in der Wandmitte
    sonde = Part.makeBox(0.4, 0.4, 2.0, App.Vector(ax / 2.0 - wand / 2.0 - 0.2, -0.2, z))
    vol = float(box.common(sonde).Volume or 0)
    ok = vol >= 0.15  # der 0,32 mm³-Würfel sollte weitgehend in der Wand liegen
    log(name, "BESTANDEN" if ok else "NICHT BESTANDEN",
        "Wandsonde %.3f mm³ (erwartet ≥ 0,15)" % vol)
    return ok


def save_part(folder, stem, params, shapes, bemerkung):
    for ext in (".FCStd", ".stl", ".step", ".png", "_Anleitung.md"):
        # nur der Stem selbst, nicht Unterteile mit Suffix, aber FCStd/Anleitung
        candidate = stem + (ext if ext != "_Anleitung.md" else "_Anleitung.md")
        if candidate in GESCHUETZT or (folder / candidate).name in GESCHUETZT:
            raise RuntimeError("Geschützte Datei würde überschrieben: %s" % candidate)
    fcstd = folder / (stem + ".FCStd")
    if fcstd.name in GESCHUETZT:
        raise RuntimeError("Geschützt: %s" % fcstd)
    info = create_document_phase4(stem, params, shapes, fcstd, SRC, bemerkung)
    for name, shape in shapes.items():
        suffix = "" if len(shapes) == 1 else ("_" + name)
        stl = folder / (stem + suffix + ".stl")
        step = folder / (stem + suffix + ".step")
        if stl.name in GESCHUETZT or step.name in GESCHUETZT:
            raise RuntimeError("Geschützt: %s" % stl)
        export_stl2(shape, stl, 0.08)
        export_step2(shape, step)
        masses[str(stl.relative_to(ROOT))] = {
            "volume_mm3": float(shape.Volume or 0),
            "masse_g_schaetzung": round(mass_g(shape.Volume or 0), 2),
            "size": [shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength],
        }
    # Kurzanleitung
    lines = ["# %s" % stem.replace("_", " "), "", bemerkung.strip(), "", "Teile und Schätzungen (PLA 1,24 g/cm³, 100 % Füllung, keine Messwerte):", ""]
    for name, shape in shapes.items():
        bb = shape.BoundBox
        lines.append("- **%s**: %.2f × %.2f × %.2f mm, Schätzung **%.2f g**" % (
            name, bb.XLength, bb.YLength, bb.ZLength, mass_g(shape.Volume or 0)))
    lines += [
        "",
        "Masse nur im Tabellenblatt `HIER_MASSE_AENDERN` ändern, danach Macro `Hausraster_Phase4_NeuBerechnen.FCMacro`.",
        "Stehend auf den Füssen drucken, ohne Stützen. Deckel und Trennwände separat, flach auf die grosse Fläche.",
        "PLA für den Schreibtisch, PETG wenn Feuchtigkeit oder milde Wärme (Bad, Küche) zu erwarten ist.",
    ]
    anl = folder / (stem + "_Anleitung.md")
    if anl.name in GESCHUETZT:
        raise RuntimeError("Geschützt: %s" % anl)
    anl.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("export_" + stem, "BESTANDEN", "FCStd/STL/STEP/Anleitung (%d Körper)" % len(shapes))
    return info


# --- Katalog ---
# (ordner, stem, params, titel/bemerkung)
KATALOG = [
    (DIR_BOX, "HR_Box_2x3x3_mittel", dict(
        Einheiten_X=2, Einheiten_Y=3, Einheiten_Z=3, Stapellippe=1,
        Fachanzahl_X=1, Fachanzahl_Y=1, Verriegelungsart=1, Deckel=0,
        Herausnehmbare_Trennwaende=0, Modelltyp="mittel",
    ), "Mittlere Box 2×3×3 auf dem gemeinsamen Grundmodell, stapelbar, Rastclip-kompatibel."),
    (DIR_BOX, "HR_Box_1x6x3_lang", dict(
        Einheiten_X=1, Einheiten_Y=6, Einheiten_Z=3, Stapellippe=1,
        Fachanzahl_X=1, Fachanzahl_Y=1, Verriegelungsart=1, Modelltyp="lang_schmal",
    ), "Lange schmale Box 1×6×3, etwa für Stifte, Feilen oder Kabelbinder."),
    (DIR_BOX, "HR_Box_3x3x3_Faecher", dict(
        Einheiten_X=3, Einheiten_Y=3, Einheiten_Z=3, Stapellippe=1,
        Fachanzahl_X=3, Fachanzahl_Y=2, Verriegelungsart=1, Modelltyp="faecher",
    ), "Box 3×3×3 mit mehreren festen Fächern (3×2). Trennwandstärke und Fachanzahl sind Parameter."),
    (DIR_BOX, "HR_Box_3x2x3_Trennwaende", dict(
        Einheiten_X=3, Einheiten_Y=2, Einheiten_Z=3, Stapellippe=1,
        Fachanzahl_X=3, Fachanzahl_Y=2, Herausnehmbare_Trennwaende=1,
        Trennwand_Spiel=0.25, Verriegelungsart=1, Modelltyp="trennwaende",
    ), "Box 3×2×3 mit herausnehmbaren Trennwänden. Nuten sitzen in Innenrippen, die Aussenwand bleibt geschlossen."),
    (DIR_BOX, "HR_Box_2x2x4_stapelbar", dict(
        Einheiten_X=2, Einheiten_Y=2, Einheiten_Z=4, Stapellippe=1,
        Fachanzahl_X=1, Fachanzahl_Y=1, Verriegelungsart=1, Modelltyp="stapelbar",
    ), "Stapelbare Box 2×2×4 (eine Einheit höher als die Phase-2-Referenz 2×2×3). Lippe zum Stapeln."),
    (DIR_BOX, "HR_Box_2x3x3_Deckel", dict(
        Einheiten_X=2, Einheiten_Y=3, Einheiten_Z=3, Stapellippe=1,
        Fachanzahl_X=1, Fachanzahl_Y=1, Deckel=1, Deckelstaerke=2.0, Deckel_Spiel=0.25,
        Verriegelungsart=2, Modelltyp="deckel",
    ), "Box 2×3×3 mit abnehmbarem Deckel auf dem Lippen-Sims und seitlichen Deckelrasten (Verriegelungsart 2)."),
    (DIR_BOX, "HR_Box_3x3x2_Schrauben", dict(
        Einheiten_X=3, Einheiten_Y=3, Einheiten_Z=2, Stapellippe=1,
        Fachanzahl_X=4, Fachanzahl_Y=4, Deckel=1, Deckelstaerke=2.0, Deckel_Spiel=0.25,
        Verriegelungsart=2, Modelltyp="schrauben",
    ), "Schrauben- und Kleinteilebox 3×3×2 mit 4×4 Fächern und abnehmbarem Deckel."),
    (DIR_BOX, "HR_Box_4x3x3_Organizer", dict(
        Einheiten_X=4, Einheiten_Y=3, Einheiten_Z=3, Stapellippe=1,
        Fachanzahl_X=4, Fachanzahl_Y=3, Verriegelungsart=1, Modelltyp="organizer",
    ), "Universeller Organizer-Einsatz 4×3×3 mit 4×3 Fächern, passt auf das Hausraster."),
    (DIR_HAUS, "HR_Schreibtisch_4x3x3", dict(
        Einheiten_X=4, Einheiten_Y=3, Einheiten_Z=3, Stapellippe=1,
        Fachanzahl_X=4, Fachanzahl_Y=2, Verriegelungsart=1, Modelltyp="schreibtisch",
    ), "Schreibtisch-Schubladenorganizer 4×3×3, 4×2 Fächer für Stifte, Klammern und Kleinteile."),
    (DIR_HAUS, "HR_Werkzeug_4x3x4", dict(
        Einheiten_X=4, Einheiten_Y=3, Einheiten_Z=4, Stapellippe=1,
        Fachanzahl_X=3, Fachanzahl_Y=2, Verriegelungsart=1, Modelltyp="werkzeug",
    ), "Werkzeug-Schubladeneinsatz 4×3×4, höhere 3×2 Fächer für Zangen, Bits und Masswerkzeug."),
    (DIR_HAUS, "HR_Kosmetik_3x3x5", dict(
        Einheiten_X=3, Einheiten_Y=3, Einheiten_Z=5, Stapellippe=1,
        Fachanzahl_X=3, Fachanzahl_Y=2, Verriegelungsart=1, Modelltyp="kosmetik",
        Wandstaerke=1.6,
    ), "Bad- und Kosmetikorganizer 3×3×5, 3×2 Fächer für Tuben und Flaschen. Wand 1,6 mm. PETG empfohlen."),
    (DIR_HAUS, "HR_Kabelbox_3x3x4", dict(
        Einheiten_X=3, Einheiten_Y=3, Einheiten_Z=4, Stapellippe=1,
        Fachanzahl_X=2, Fachanzahl_Y=2, Kabelkerben=1, Deckel=1,
        Deckelstaerke=2.0, Deckel_Spiel=0.25, Verriegelungsart=1, Modelltyp="kabel",
    ), "Kabel- und Ladegerätebox 3×3×4 mit 2×2 Fächern, Kabelkerben in den Trennwänden und Deckel."),
    (DIR_HAUS, "HR_Vorratsbox_3x2x4", dict(
        Einheiten_X=3, Einheiten_Y=2, Einheiten_Z=4, Stapellippe=1,
        Fachanzahl_X=1, Fachanzahl_Y=1, Deckel=1, Deckelstaerke=2.0, Deckel_Spiel=0.25,
        Verriegelungsart=1, Modelltyp="vorrat",
    ), "Stapelbare Vorrats- und Kleinteilebox 3×2×4 mit Deckel. Mehrere Lagen übereinander möglich."),
    (DIR_HAUS, "HR_Haushalt_4x3x3", dict(
        Einheiten_X=4, Einheiten_Y=3, Einheiten_Z=3, Stapellippe=1,
        Fachanzahl_X=3, Fachanzahl_Y=3, Verriegelungsart=1, Modelltyp="haushalt",
    ), "Haushaltsutensilien-Organizer 4×3×3 mit 3×3 Fächern für Schubladen in Küche oder Flur."),
]


def main():
    global all_ok
    gebaut = []
    for folder, stem, raw, bemerkung in KATALOG:
        tag = stem
        try:
            p = phase4_params(**raw)
            p, shapes, hinweise = make_phase4_box(p)
            box = shapes["Box"]
            soll = box_outer_size(p)
            ok = check_shape(tag + "_Box", box, soll=soll, tol=0.35)
            all_ok &= ok
            all_ok &= wand_sonde(tag + "_Wand", box, p)
            # Rasterpassung
            pp = dict(p)
            pp["Verbinder"] = 0
            pp["Verriegelung"] = 0
            plate = make_plate_shape(pp)
            all_ok &= passung_box_platte(tag + "_Raster", plate, box, seated_box_z_on_plate(pp))
            for name, sh in shapes.items():
                if name == "Box":
                    continue
                all_ok &= check_shape(tag + "_" + name, sh, soll=None, tol=1.0)
            if "Deckel" in shapes:
                deckel = shapes["Deckel"]
                inter = float(box.common(deckel).Volume or 0)
                # Verriegelungsart 2 darf leicht klemmen
                limit = 8.0 if int(p.get("Verriegelungsart", 0)) == 2 else 0.5
                okd = inter <= limit
                log(tag + "_Deckelpassung", "BESTANDEN" if okd else "NICHT BESTANDEN",
                    "Interferenz Deckel/Box %.4f mm³ (Grenze %.1f)" % (inter, limit),
                    extra={"interferenz_mm3": inter})
                all_ok &= okd
            for name, sh in shapes.items():
                if not name.startswith("Trennwand"):
                    continue
                inter = float(box.common(sh).Volume or 0)
                okt = inter <= 0.5
                log(tag + "_" + name + "_Passung", "BESTANDEN" if okt else "NICHT BESTANDEN",
                    "Interferenz Trennwand/Box %.4f mm³" % inter)
                all_ok &= okt
            text = bemerkung + "\nHinweise:\n- " + "\n- ".join(hinweise)
            save_part(folder, stem, p, shapes, text)
            gebaut.append(stem)
        except Exception:
            all_ok = False
            log(tag, "NICHT BESTANDEN", traceback.format_exc())

    # Parametrik: Höhe und Fachanzahl an einem Grundmodell
    try:
        p = phase4_params(Einheiten_X=2, Einheiten_Y=2, Einheiten_Z=5, Stapellippe=1,
                          Fachanzahl_X=2, Fachanzahl_Y=2, Modelltyp="param_test")
        p, shapes, _ = make_phase4_box(p)
        soll = box_outer_size(p)
        ok = check_shape("param_2x2x5_faecher", shapes["Box"], soll=soll, tol=0.35)
        all_ok &= ok
        p2 = phase4_params(Einheiten_X=2, Einheiten_Y=3, Einheiten_Z=3, Stapellippe=0,
                           Fachanzahl_X=1, Fachanzahl_Y=1, Verriegelungsart=0, Deckel=0,
                           Modelltyp="param_ohne_lippe")
        p2, shapes2, _ = make_phase4_box(p2)
        soll2 = box_outer_size(p2)
        ok = check_shape("param_2x3x3_ohne_lippe", shapes2["Box"], soll=soll2, tol=0.35)
        all_ok &= ok
    except Exception:
        all_ok = False
        log("parametrik", "NICHT BESTANDEN", traceback.format_exc())

    # Recompute eines neuen FCStd
    try:
        path = DIR_BOX / "HR_Box_2x3x3_mittel.FCStd"
        doc = App.openDocument(str(path))
        doc.recompute()
        n, ok_r = 0, True
        for obj in doc.Objects:
            if hasattr(obj, "Shape") and obj.Shape and not obj.Shape.isNull():
                n += 1
                if not obj.Shape.isValid() or len(obj.Shape.Solids) != 1:
                    ok_r = False
        App.closeDocument(doc.Name)
        log("recompute_mittelbox", "BESTANDEN" if ok_r and n >= 1 else "NICHT BESTANDEN",
            "geöffnet, recompute, %d gültige Körper" % n)
        all_ok &= ok_r and n >= 1
    except Exception:
        all_ok = False
        log("recompute_mittelbox", "NICHT BESTANDEN", traceback.format_exc())

    # Rastclip bleibt das Phase-2-Teil; nur gültig und erwähnt
    try:
        rast = make_rastclip_shape(phase4_params(Einheiten_Z=3, Stapellippe=1))
        ok = rast.isValid() and rast.Volume > 0
        log("rastclip_phase2_referenz", "BESTANDEN" if ok else "NICHT BESTANDEN",
            "valid=%s vol=%.1f Schätzung %.2f g (bestehendes Phase-2-Teil, nicht neu abgelegt)"
            % (rast.isValid(), rast.Volume, mass_g(rast.Volume)))
        all_ok &= ok
    except Exception:
        all_ok = False
        log("rastclip_phase2_referenz", "NICHT BESTANDEN", traceback.format_exc())

    passed = sum(1 for r in protocol if r["status"] == "BESTANDEN")
    failed = sum(1 for r in protocol if r["status"] == "NICHT BESTANDEN")
    out = {
        "version": PHASE4_VERSION,
        "passed": passed,
        "failed": failed,
        "all_ok": all_ok and failed == 0,
        "tests": protocol,
        "masses": masses,
        "modelle": gebaut,
    }
    (DIR_TESTS / "phase4_protokoll.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("PROTOKOLL %d bestanden, %d nicht, all_ok=%s, modelle=%s" % (passed, failed, out["all_ok"], gebaut), flush=True)
    return 0 if out["all_ok"] else 1


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        traceback.print_exc()
        code = 1
    Path("/workspace/ordnungssystem/tests/phase4_exit.txt").write_text("0" if code == 0 else "1", encoding="utf-8")
    sys.exit(code)
