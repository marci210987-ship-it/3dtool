# -*- coding: utf-8 -*-
"""Bestandsaufnahme und FreeCAD-Ladetests je FCStd."""
from __future__ import annotations

import json
import re
from pathlib import Path

import FreeCAD as App
import Part

from qs_common import (
    ROOT, REPORT, _rec, sha256_file, object_states, expressions_on_shapes,
    shape_info, export_and_reimport, load_existing_stl_quality,
)

MODEL_DIRS = [
    "01_rastersystem", "02_boxen", "03_besteck",
    "04_gewuerz", "05_haushalt", "06_testdrucke",
]


def related_files(fc: Path):
    stem = fc.stem
    parent = fc.parent
    stls = sorted(parent.glob(stem + "*.stl"))
    steps = sorted(list(parent.glob(stem + "*.step")) + list(parent.glob(stem + "*.stp")))
    pngs = sorted(parent.glob(stem + "*.png"))
    mds = sorted(set(list(parent.glob(stem + "*.md")) + list(parent.glob("*Anleitung*")) + list(parent.glob("Anleitung*"))))
    return {"stl": stls, "step": steps, "png": pngs, "anleitung": mds}


def inventory():
    models = []
    for folder in MODEL_DIRS:
        base = ROOT / folder
        if not base.exists():
            _rec("Bestand", "Ordner fehlt: " + folder, "FEHLERHAFT", modell=folder)
            continue
        for fc in sorted(base.rglob("*.FCStd")):
            rel = str(fc.relative_to(ROOT))
            rels = related_files(fc)
            item = {
                "id": fc.stem,
                "pfad": rel,
                "ordner": folder,
                "fcstd_bytes": fc.stat().st_size,
                "fcstd_sha256": sha256_file(fc),
                "stl_anzahl": len(rels["stl"]),
                "step_anzahl": len(rels["step"]),
                "png_anzahl": len(rels["png"]),
                "anleitung_anzahl": len(rels["anleitung"]),
                "stl": [str(p.relative_to(ROOT)) for p in rels["stl"]],
                "step": [str(p.relative_to(ROOT)) for p in rels["step"]],
                "png": [str(p.relative_to(ROOT)) for p in rels["png"]],
                "anleitung": [str(p.relative_to(ROOT)) for p in rels["anleitung"]],
                "luecken": [],
                "status": "NICHT GETESTET",
                "befunde": [],
            }
            if not rels["stl"]:
                item["luecken"].append("STL")
            if not rels["step"]:
                item["luecken"].append("STEP")
            if not rels["png"]:
                item["luecken"].append("PNG")
            if not rels["anleitung"]:
                item["luecken"].append("Anleitung")
            models.append(item)
            REPORT["modelle"][item["id"] + "::" + rel] = item
            if item["luecken"]:
                _rec("Bestand", rel + ": fehlend " + ", ".join(item["luecken"]), "FEHLERHAFT", modell=item["id"])
            else:
                _rec("Bestand", rel + ": FCStd+STL+STEP+PNG+Anleitung vorhanden", "BESTANDEN",
                     modell=item["id"],
                     messwerte={"stl": item["stl_anzahl"], "step": item["step_anzahl"], "png": item["png_anzahl"]})
    doc_names = set()
    doku = ROOT / "07_dokumentation"
    if doku.exists():
        for p in doku.glob("*.md"):
            doc_names |= set(re.findall(r"HR_[A-Za-z0-9_]+", p.read_text(encoding="utf-8", errors="replace")))
    fc_stems = {m["id"] for m in models}
    fehlt = []
    for n in sorted(doc_names):
        if n in fc_stems:
            continue
        if any(n.startswith(s) or s.startswith(n) for s in fc_stems):
            continue
        fehlt.append(n)
    if fehlt:
        _rec("Bestand", "In der Dokumentation genannte Modelle ohne Datei", "FEHLERHAFT", details=", ".join(fehlt))
    else:
        _rec("Bestand", "Alle in der Doku namentlich genannten HR-Modelle sind als Datei oder Teilstueck vorhanden",
             "BESTANDEN", messwerte={"doc_tokens": len(doc_names), "fcstd": len(models)})

    needed = {
        "macros/Hausraster_NeuBerechnen.FCMacro": ROOT / "macros" / "Hausraster_NeuBerechnen.FCMacro",
        "macros/Hausraster_Phase3_NeuBerechnen.FCMacro": ROOT / "macros" / "Hausraster_Phase3_NeuBerechnen.FCMacro",
        "macros/Hausraster_Phase4_NeuBerechnen.FCMacro": ROOT / "macros" / "Hausraster_Phase4_NeuBerechnen.FCMacro",
        "macros/Schubladenplaner.FCMacro": ROOT / "macros" / "Schubladenplaner.FCMacro",
        "Mod/Hausraster/Init.py": ROOT / "FreeCAD_Mod" / "Hausraster" / "Init.py",
        "Mod/HausrasterPhase3/Init.py": ROOT / "FreeCAD_Mod" / "HausrasterPhase3" / "Init.py",
        "Mod/HausrasterPhase4/Init.py": ROOT / "FreeCAD_Mod" / "HausrasterPhase4" / "Init.py",
        "src/hausraster_phase3_schale.py": ROOT / "src" / "hausraster_phase3_schale.py",
        "Mod/HausrasterPhase3/hausraster_phase3_schale.py": ROOT / "FreeCAD_Mod" / "HausrasterPhase3" / "hausraster_phase3_schale.py",
    }
    for label, path in needed.items():
        if path.exists():
            _rec("Bestand", "Abhaengigkeit vorhanden: " + label, "BESTANDEN")
        else:
            _rec("Bestand", "Abhaengigkeit fehlt: " + label, "FEHLERHAFT",
                 details="Ohne diese Datei kann ein Anwender die Geometrie nach Parameteraenderung nicht vollstaendig neu erzeugen.")
            REPORT["fehler"].append({"id": "ABH_FEHLT", "datei": label,
                                     "schwere": "hoch" if "schale" in label.lower() else "mittel"})
    return models


def set_model_status(models, fc_path, status, befund):
    rel = str(Path(fc_path).resolve().relative_to(ROOT)) if Path(fc_path).is_absolute() else str(fc_path)
    rank = {"FEHLERHAFT": 3, "EINGESCHRÄNKT": 2, "EINGESCHRAENKT": 2, "BESTANDEN": 1, "NICHT GETESTET": 0}
    for m in models:
        if m["pfad"] == rel or m["pfad"].endswith(rel):
            cur = rank.get(m["status"], 0)
            if rank.get(status, 0) >= cur:
                m["status"] = status
            m["befunde"].append(befund)
            return m
    return None


def test_open_fcstd(models):
    for m in models:
        path = ROOT / m["pfad"]
        tag = m["id"]
        try:
            doc = App.openDocument(str(path))
        except Exception as exc:
            _rec("FreeCAD-Laden", tag, "FEHLERHAFT", details=str(exc), modell=tag)
            set_model_status(models, m["pfad"], "FEHLERHAFT", "Laden fehlgeschlagen: " + str(exc))
            continue
        try:
            try:
                doc.recompute()
            except Exception as exc:
                _rec("FreeCAD-Recompute", tag, "FEHLERHAFT", details=str(exc), modell=tag)
                set_model_status(models, m["pfad"], "FEHLERHAFT", "Recompute fehlgeschlagen: " + str(exc))

            states = object_states(doc)
            bad = [s for s in states if any(x in s["state"] for x in ("Invalid", "Error", "RestoreError"))]
            touched = [s for s in states if "Touched" in s["state"] and s not in bad]
            if bad:
                _rec("Modellbaum", tag, "FEHLERHAFT", details=json.dumps(bad, ensure_ascii=False), modell=tag)
                set_model_status(models, m["pfad"], "FEHLERHAFT", "Ungueltige Objekte: " + str(bad))
            else:
                _rec("Modellbaum", tag, "BESTANDEN",
                     details=("Touched verblieben: " + ", ".join(s["name"] for s in touched)) if touched else "kein Invalid/Error",
                     modell=tag)

            sheet = doc.getObject("HIER_MASSE_AENDERN")
            if sheet is None:
                _rec("Parameter", tag + ": kein Tabellenblatt HIER_MASSE_AENDERN", "FEHLERHAFT", modell=tag)
                set_model_status(models, m["pfad"], "FEHLERHAFT", "Spreadsheet fehlt")
            else:
                aliases = []
                for r in range(2, 90):
                    try:
                        al = sheet.getAlias("B%d" % r)
                    except Exception:
                        al = None
                    if al:
                        aliases.append(al)
                exprs = expressions_on_shapes(doc)
                if exprs:
                    _rec("Parameterbindung", tag, "BESTANDEN",
                         details="Expressions an Shape-Objekten vorhanden",
                         messwerte={"aliases": aliases, "expressions": exprs}, modell=tag)
                else:
                    _rec("Parameterbindung", tag, "EINGESCHRAENKT",
                         details=(
                             "Die Tabellenblatt-Aliase existieren (%d Stueck), sind aber nicht ueber Expressions "
                             "mit der Geometrie verknuepft. Eine Aenderung der Masse aendert die Koerper erst, "
                             "wenn das zustaendige NeuBerechnen-Makro ausgefuehrt wird."
                         ) % len(aliases),
                         messwerte={"aliases": aliases, "expression_anzahl": 0},
                         modell=tag)
                    set_model_status(models, m["pfad"], "EINGESCHRÄNKT",
                                     "Keine Expression-Bindung; Geometrie nur ueber Makro neu berechenbar")

            solids_ok = True
            for obj in doc.Objects:
                if not hasattr(obj, "Shape") or obj.Shape is None or obj.Shape.isNull():
                    continue
                info = shape_info(obj.Shape)
                if not info["valid"] or not info["closed"] or info["solids"] < 1 or info["volume_mm3"] <= 0:
                    solids_ok = False
                    _rec("Geometrie", tag + "/" + obj.Name, "FEHLERHAFT", messwerte=info, modell=tag)
                    set_model_status(models, m["pfad"], "FEHLERHAFT", obj.Name + " ungueltig/offen/vol=0")
                else:
                    _rec("Geometrie", tag + "/" + obj.Name, "BESTANDEN", messwerte=info, modell=tag)
                try:
                    q = export_and_reimport(obj.Shape, tag + "__" + obj.Name)
                    ok = q.get("solid") is True and not q.get("nonmanifold") and (
                        q.get("volume_rel_diff") is None or q["volume_rel_diff"] < 0.08
                    )
                    status = "BESTANDEN" if ok else "FEHLERHAFT"
                    if q.get("solid") is not True:
                        status = "FEHLERHAFT"
                    _rec("STL-Export-Reimport", tag + "/" + obj.Name, status, messwerte=q, modell=tag)
                    if status == "FEHLERHAFT":
                        set_model_status(models, m["pfad"], "FEHLERHAFT", "STL " + obj.Name)
                        solids_ok = False
                except Exception as exc:
                    _rec("STL-Export-Reimport", tag + "/" + obj.Name, "FEHLERHAFT", details=str(exc), modell=tag)
                    set_model_status(models, m["pfad"], "FEHLERHAFT", "STL-Export " + obj.Name + ": " + str(exc))

            for stl in (ROOT / s for s in m["stl"]):
                if not stl.exists():
                    continue
                try:
                    q = load_existing_stl_quality(stl)
                    ok = q.get("solid") is True and not q.get("nonmanifold")
                    _rec("STL-Bestand", str(stl.relative_to(ROOT)), "BESTANDEN" if ok else "FEHLERHAFT",
                         messwerte=q, modell=tag)
                    if not ok:
                        set_model_status(models, m["pfad"], "FEHLERHAFT", "Bestands-STL nicht wasserdicht: " + stl.name)
                except Exception as exc:
                    _rec("STL-Bestand", str(stl.relative_to(ROOT)), "FEHLERHAFT", details=str(exc), modell=tag)

            for step in (ROOT / s for s in m["step"]):
                if not step.exists():
                    continue
                try:
                    sh = Part.Shape()
                    sh.read(str(step))
                    info = shape_info(sh)
                    ok = info.get("valid") and info.get("closed") and info.get("volume_mm3", 0) > 0
                    _rec("STEP-Bestand", str(step.relative_to(ROOT)), "BESTANDEN" if ok else "FEHLERHAFT",
                         messwerte=info, modell=tag)
                    if not ok:
                        set_model_status(models, m["pfad"], "FEHLERHAFT", "STEP ungueltig: " + step.name)
                except Exception as exc:
                    _rec("STEP-Bestand", str(step.relative_to(ROOT)), "FEHLERHAFT", details=str(exc), modell=tag)

            if solids_ok and m["status"] != "FEHLERHAFT":
                if m["status"] == "NICHT GETESTET":
                    set_model_status(models, m["pfad"], "BESTANDEN", "Laden, Recompute, Solids, STL/STEP geprueft")
        finally:
            try:
                App.closeDocument(doc.Name)
            except Exception:
                pass
