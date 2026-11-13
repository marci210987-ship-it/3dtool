# -*- coding: utf-8 -*-
"""FCStd-Dokumente mit Spreadsheet, Exporten und eingebettetem Quellcode."""

from __future__ import annotations

import os
from pathlib import Path

import FreeCAD as App
import Part
import Mesh
import MeshPart

from hausraster_const import SYSTEM_NAME, SYSTEM_VERSION, default_params, pruefe_parameter
from hausraster_geom import (
    make_plate_shape,
    make_box_shape,
    make_fuss_stumpf_shape,
    make_verbinder_clip_shape,
    make_rastclip_shape,
    make_passung_verbinder_shape,
    plate_outer_size,
    box_outer_size,
)

HINWEISE = {
    "Raster_mm": ("mm", "Fest, Gridfinity-kompatibel – nicht ändern"),
    "Hoeheneinheit_mm": ("mm", "Fest, Gridfinity-kompatibel – nicht ändern"),
    "Einheiten_X": ("1", "Rastereinheiten in der Breite (1–6)"),
    "Einheiten_Y": ("1", "Rastereinheiten in der Tiefe (1–6)"),
    "Einheiten_Z": ("1", "Höheneinheiten der Box (1–12), 1 Einheit = 7 mm"),
    "Wandstaerke": ("mm", "Vielfaches von 0,4 mm, empfohlen 1,2"),
    "Bodenstaerke_Platte": ("mm", "Platte: empfohlen 0,8; Gesamthöhe = Boden + 4,65"),
    "Bodenstaerke_Box": ("mm", "Dicke über dem Fussprofil, Standard 2,25 (Hohlraum ab 7 mm)"),
    "Passungsspiel": ("mm", "Zusätzliches Spiel je Seite, Standard 0 (dann 0,25 mm wie Gridfinity)"),
    "Rand_X_links": ("mm", "Integrierter Rand links, 0 wenn die Seite an eine andere Platte stößt"),
    "Rand_X_rechts": ("mm", "Integrierter Rand rechts"),
    "Rand_Y_vorne": ("mm", "Integrierter Rand vorne"),
    "Rand_Y_hinten": ("mm", "Integrierter Rand hinten"),
    "Fachanzahl_X": ("1", "Nur Box: Fächer in der Breite"),
    "Fachanzahl_Y": ("1", "Nur Box: Fächer in der Tiefe"),
    "Trennwandstaerke": ("mm", "Nur Box, empfohlen 1,2"),
    "Verbinder_Spiel": ("mm", "Spiel je Kontaktfläche des Plattenverbinders, Standard 0,20"),
    "Innenradius": ("mm", "Innenecken der Box, erleichtert die Reinigung"),
    "Stapellippe": ("0/1", "1 = Lippe oben, Boxen sind stapelbar"),
    "Verriegelung": ("0/1", "1 = Aussennut für den Rastclip"),
    "Verbinder": ("0/1", "1 = Schwalbenschwanz-Taschen an randoffenen Kanten"),
    "Schubladenspiel": ("mm", "Nur Planung: Spiel je Schubladenseite, Standard 1,0"),
    "Profil_Platte_P0": ("mm", "Aufnahmeprofil Platte, nicht ändern"),
    "Profil_Platte_P1": ("mm", "Aufnahmeprofil Platte, nicht ändern"),
    "Profil_Platte_P2": ("mm", "Aufnahmeprofil Platte, nicht ändern"),
    "Profil_Fuss_P0": ("mm", "Fussprofil Box, nicht ändern"),
    "Profil_Fuss_P1": ("mm", "Fussprofil Box, nicht ändern"),
    "Profil_Fuss_P2": ("mm", "Fussprofil Box, nicht ändern"),
    "Eckenradius_Platte": ("mm", "Standard 4,0, Gridfinity-kompatibel"),
    "Eckenradius_Box": ("mm", "Standard 3,75, Gridfinity-kompatibel"),
}


def add_spreadsheet(doc, params: dict):
    sheet = doc.addObject("Spreadsheet::Sheet", "HIER_MASSE_AENDERN")
    sheet.set("A1", "Parameter")
    sheet.set("B1", "Wert")
    sheet.set("C1", "Einheit")
    sheet.set("D1", "Hinweis")
    sheet.setStyle("A1:D1", "bold", "add")
    row = 2
    for name, value in params.items():
        sheet.set("A%d" % row, name)
        if isinstance(value, int) and not isinstance(value, bool):
            sheet.set("B%d" % row, "%d" % value)
        else:
            sheet.set("B%d" % row, "%.4f" % float(value))
        try:
            sheet.setAlias("B%d" % row, name)
        except Exception:
            # Alias kann bei reservierten Namen scheitern
            pass
        einheit, hinweis = HINWEISE.get(name, ("", ""))
        sheet.set("C%d" % row, einheit)
        sheet.set("D%d" % row, hinweis)
        row += 1
    row += 1
    sheet.set("A%d" % row, "NACH DEM AENDERN")
    sheet.set("B%d" % row, "Macro Hausraster_NeuBerechnen.FCMacro starten (FreeCAD-Mod Hausraster). Die aktuelle Geometrie ist gespeichert und sofort nutzbar.")
    try:
        sheet.setColumnWidth("A", 200)
        sheet.setColumnWidth("B", 100)
        sheet.setColumnWidth("C", 80)
        sheet.setColumnWidth("D", 420)
    except Exception:
        pass
    return sheet


def embed_source(doc, src_dir: Path):
    td = doc.addObject("App::TextDocument", "HausrasterQuellcode")
    pieces = []
    for name in (
        "hausraster_const.py",
        "hausraster_plan.py",
        "hausraster_geom.py",
        "hausraster_fcstd.py",
    ):
        path = src_dir / name
        if path.exists():
            pieces.append("# ===== %s =====\n%s" % (name, path.read_text(encoding="utf-8")))
    td.Text = "\n\n".join(pieces)[:200000]
    return td


def add_shape_object(doc, name, shape):
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


def export_stl(shape, path, deflection=0.08):
    path = str(path)
    mesh = MeshPart.meshFromShape(
        Shape=shape, LinearDeflection=deflection, AngularDeflection=0.174, Relative=False
    )
    mesh.write(path)
    return path


def export_step(shape, path):
    path = str(path)
    shape.exportStep(path)
    return path


def create_document(title, params, shapes: dict, out_fcstd: Path, src_dir: Path, bemerkung: str = ""):
    """shapes: {objektname: Part.Shape}"""
    p = default_params(**params)
    if out_fcstd.exists():
        out_fcstd.unlink()
    doc = App.newDocument(title)
    add_spreadsheet(doc, p)
    for name, shape in shapes.items():
        add_shape_object(doc, name, shape)
    embed_source(doc, src_dir)
    note = doc.addObject("App::TextDocument", "Lesen")
    note.Text = (
        "%s %s\n\n%s\n\n"
        "Masse nur im Tabellenblatt HIER_MASSE_AENDERN ändern, keine Skizzen anfassen.\n"
        "Danach das Macro Hausraster_NeuBerechnen.FCMacro ausführen, damit die Geometrie neu entsteht.\n"
        "Ohne das Macro bleibt die zuletzt gespeicherte Geometrie erhalten (STL/STEP-Export möglich).\n"
    ) % (SYSTEM_NAME, SYSTEM_VERSION, bemerkung)
    doc.recompute()
    out_fcstd.parent.mkdir(parents=True, exist_ok=True)
    doc.saveAs(str(out_fcstd))
    # Shape-Tests vor dem Schliessen zurückgeben
    info = {}
    for name, obj in ((o.Name, o) for o in doc.Objects if hasattr(o, "Shape") and o.Shape and not o.Shape.isNull()):
        sh = obj.Shape
        bb = sh.BoundBox
        info[name] = {
            "is_valid": bool(sh.isValid()),
            "solids": len(sh.Solids),
            "volume_mm3": float(sh.Volume) if sh.Volume else 0.0,
            "bbox": [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax],
            "size": [bb.XLength, bb.YLength, bb.ZLength],
        }
    App.closeDocument(doc.Name)
    return info
